# mypy: ignore-errors


import logging
from typing import Final

from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AppClientCompilationParams,
    CommonAppCallParams,
    OnSchemaBreak,
    OnUpdate,
)
from algokit_utils.config import config
from asa_metadata_registry import (
    DEFAULT_DEPLOYMENTS,
    Arc90Compliance,
    Arc90Uri,
    AsaMetadataRegistry,
    AssetMetadata,
    IrreversibleFlags,
    MetadataFlags,
    ReversibleFlags,
)
from asa_metadata_registry._generated.asa_metadata_registry_client import (
    AsaMetadataRegistryClient,
    AsaMetadataRegistryFactory,
)
from asa_metadata_registry.deployments import RegistryDeployment

from helpers.metadata import call_asa_metadata_registry
from smart_contracts.arc89_smart_asa.template_vars import ARC89_APP_ID

logger = logging.getLogger(__name__)

APP_FUNDS: Final[AlgoAmount] = AlgoAmount(micro_algo=100_000)

# ==============================================================================
# ASSET CREATION PARAMETERS
# ==============================================================================

ASA_TOTAL: Final[int] = 420
ASA_DECIMALS: Final[int] = 1
ASA_DEFAULT_FROZEN: Final[bool] = False
ASA_UNIT_NAME: Final[str] = "ARC-20"
ASA_NAME: Final[str] = "Smart ASA with Metadata@arc3"
ASA_METADATA_HASH: Final[bytes] = 32 * b"\x00"  # Mutable metadata

# ==============================================================================
# ASSET METADATA
# ==============================================================================

METADATA_FLAGS = MetadataFlags(
    reversible=ReversibleFlags(arc20=True, arc62=True),
    irreversible=IrreversibleFlags(arc3=True, arc89_native=True, immutable=False),
)

ARC3_METADATA_JSON = {
    "name": ASA_NAME,
    "description": "Smart ASA with metadata on the ASA Metadata Registry",
    "decimals": ASA_DECIMALS,
    "unitName": ASA_UNIT_NAME,
    "properties": {
        "arc-20": {"application-id": 0},  # Update after Smart ASA App deployment
        "arc-62": {"application-id": 0},  # Update after Smart ASA App deployment
    },
}

DEPRECATED_BY = 0

# ==============================================================================
# ARC-89 SMART ASA DEPLOYMENT
# ==============================================================================


def deploy() -> None:
    from smart_contracts.artifacts.arc89_smart_asa.arc89_smart_asa_client import (
        Arc89SmartAsaFactory,
        AssetCreateArgs,
    )

    config.configure(debug=False)

    algorand = AlgorandClient.from_environment()
    deployer = algorand.account.from_environment("DEPLOYER")
    logger.info(f"Deployer address: {deployer.address}")

    if algorand.client.is_localnet():
        registry_app_factory = algorand.client.get_typed_app_factory(
            AsaMetadataRegistryFactory,
            default_sender=deployer.address,
        )

        registry_app_client, _ = registry_app_factory.deploy(
            compilation_params=AppClientCompilationParams(
                deploy_time_params={
                    "TRUSTED_DEPLOYER": deployer.public_key,
                    "ARC90_NETAUTH": "net:" + algorand.client.network().genesis_id,
                }
            )
        )

        algorand.account.ensure_funded_from_environment(
            account_to_fund=registry_app_client.app_address,
            min_spending_balance=APP_FUNDS,
        )

        registry_client = AsaMetadataRegistry.from_app_client(
            app_client=registry_app_client, algod=algorand.client.algod
        )

        registry_deployment = RegistryDeployment(
            network=algorand.client.network().genesis_id,
            genesis_hash_b64=algorand.client.network().genesis_hash,
            app_id=registry_app_client.app_id,
            arc90_uri_netauth="net:" + algorand.client.network().genesis_id,
            creator_address=deployer.address,
        )
    elif algorand.client.is_testnet():
        registry_deployment = DEFAULT_DEPLOYMENTS["testnet"]
        registry_app_client = algorand.client.get_typed_app_client_by_id(
            AsaMetadataRegistryClient,
            app_id=registry_deployment.app_id,
            default_sender=deployer.address,
            default_signer=deployer.signer,
        )
        registry_client = AsaMetadataRegistry.from_app_client(
            app_client=registry_app_client, algod=algorand.client.algod
        )
    else:
        raise OSError("Unsupported network for deployment")
    logger.info(f"ASA Metadata Registry deployment: {registry_deployment}")

    factory = algorand.client.get_typed_app_factory(
        Arc89SmartAsaFactory,
        default_sender=deployer.address,
        compilation_params=AppClientCompilationParams(
            deploy_time_params={
                ARC89_APP_ID: registry_deployment.app_id,
            }
        ),
    )

    arc89_smart_asa_app_client, _ = factory.deploy(
        on_schema_break=OnSchemaBreak.AppendApp,
        on_update=OnUpdate.AppendApp,
    )
    logger.info(f"Smart ASA Application ID: {arc89_smart_asa_app_client.app_id}")

    smart_asa_id = arc89_smart_asa_app_client.state.global_state.smart_asa_id

    if not smart_asa_id:
        algorand.account.ensure_funded_from_environment(
            account_to_fund=arc89_smart_asa_app_client.app_address,
            min_spending_balance=APP_FUNDS,
        )

        arc90_uri = Arc90Uri(
            netauth=registry_deployment.arc90_uri_netauth,
            app_id=registry_deployment.app_id,
            box_name=None,
            compliance=Arc90Compliance((20, 89)),  # ARC-20, ARC-89
        )
        assert arc90_uri.is_partial
        logger.info(f"Smart ASA Metadata Partial URI: {arc90_uri.to_uri()}")

        sp = arc89_smart_asa_app_client.algorand.client.algod.suggested_params()
        sp.flat_fee = True
        sp.fee = sp.min_fee * 2  # type: ignore

        smart_asa_id = arc89_smart_asa_app_client.send.asset_create(
            AssetCreateArgs(
                total=ASA_TOTAL,
                decimals=ASA_DECIMALS,
                default_frozen=ASA_DEFAULT_FROZEN,
                unit_name=ASA_UNIT_NAME,
                name=ASA_NAME,
                metadata_hash=ASA_METADATA_HASH,
                url=arc90_uri.to_uri(),
                manager_addr=deployer.address,
                reserve_addr=arc89_smart_asa_app_client.app_address,
                clawback_addr=deployer.address,
                freeze_addr=deployer.address,
            ),
            params=CommonAppCallParams(static_fee=AlgoAmount.from_micro_algo(sp.fee)),
        ).abi_return
        logger.info(f"Smart ASA ID: {smart_asa_id}")

    metadata_exists = registry_client.read.arc89_check_metadata_exists(
        asset_id=smart_asa_id
    ).metadata_exists
    if not metadata_exists:
        # Update Asset Metadata
        ARC3_METADATA_JSON["properties"]["arc-20"][
            "application-id"
        ] = arc89_smart_asa_app_client.app_id
        ARC3_METADATA_JSON["properties"]["arc-62"][
            "application-id"
        ] = arc89_smart_asa_app_client.app_id

        smart_asa_metadata = AssetMetadata.from_json(
            asset_id=smart_asa_id,
            json_obj=ARC3_METADATA_JSON,
            flags=METADATA_FLAGS,
            deprecated_by=DEPRECATED_BY,
            arc3_compliant=METADATA_FLAGS.irreversible.arc3,
        )
        metadata_composer = registry_client.write.build_create_metadata_group(
            asset_manager=deployer,
            metadata=smart_asa_metadata,
        )

        call_asa_metadata_registry(
            arc89_smart_asa_client=arc89_smart_asa_app_client,
            manager=deployer,
            metadata_composer=metadata_composer,
            has_mbr_payment=True,
        )

    metadata = registry_client.read.get_asset_metadata(asset_id=smart_asa_id)
    logger.info(f"ARC-89 Smart ASA Metadata: {metadata.json}")
