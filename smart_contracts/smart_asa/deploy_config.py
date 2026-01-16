# mypy: ignore-errors

import logging
from pathlib import Path
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
    AsaMetadataRegistry,
    AssetMetadata,
    IrreversibleFlags,
    MetadataFlags,
    ReversibleFlags,
)
from asa_metadata_registry._generated.asa_metadata_registry_client import (
    AsaMetadataRegistryClient,
)
from asa_metadata_registry.deployments import RegistryDeployment
from dotenv import load_dotenv

from smart_contracts.template_vars import ARC89_APP_ID, ARC90_NETAUTH

logger = logging.getLogger(__name__)

APP_FUNDS: Final[AlgoAmount] = AlgoAmount(algo=1)

# ==============================================================================
# ASSET CREATION PARAMETERS
# ==============================================================================

ASA_TOTAL: Final[int] = 420
ASA_DECIMALS: Final[int] = 1
ASA_DEFAULT_FROZEN: Final[bool] = False
ASA_UNIT_NAME: Final[str] = "ARC-20"
ASA_NAME: Final[str] = "ARC-20 Smart ASA"
ASA_URL: Final[str] = "https://arc.algorand.foundation/ARCs/arc-0020"
ASA_METADATA_HASH: Final[bytes] = 32 * b"\x00"

# ==============================================================================
# ASSET METADATA
# ==============================================================================

METADATA_FLAGS = MetadataFlags(
    reversible=ReversibleFlags(arc20=True, arc62=False),
    irreversible=IrreversibleFlags(arc3=True, arc89_native=True, immutable=False),
)

METADATA_JSON = {
    "name": ASA_NAME,
    "description": "Smart ASA with metadata on the ASA Metadata Registry",
    "decimals": ASA_DECIMALS,
    "unitName": ASA_UNIT_NAME,
    "properties": {
        "arc-20": {"application-id": 0}  # Update after Smart ASA App deployment
    },
}

DEPRECATED_BY = 0


def deploy() -> None:
    from smart_contracts.artifacts.smart_asa.smart_asa_client import (
        AssetCreateArgs,
        SmartAsaFactory,
    )

    config.configure(debug=False)

    algorand = AlgorandClient.from_environment()
    if algorand.client.is_localnet():
        env_path = Path(__file__).parent.parent.parent / ".env.localnet.template"
        deployer = algorand.account.from_environment("DEPLOYER")
        registry_deployment = RegistryDeployment(
            network=algorand.client.network().genesis_id,
            genesis_hash_b64=algorand.client.network().genesis_hash,
            app_id=0,
            arc90_uri_netauth="net:" + algorand.client.network().genesis_id,
            creator_address=deployer.address,
        )
    elif algorand.client.is_testnet():
        env_path = Path(__file__).parent.parent.parent / ".env.testnet.template"
        deployer = algorand.account.from_environment("DEPLOYER")
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
    load_dotenv(env_path)

    logger.info(f"Deployer address: {deployer.address}")
    logger.info(f"ASA Metadata Registry deployment: {registry_deployment}")

    factory = algorand.client.get_typed_app_factory(
        SmartAsaFactory,
        default_sender=deployer.address,
        compilation_params=AppClientCompilationParams(
            deploy_time_params={
                ARC89_APP_ID: registry_deployment.app_id,
                ARC90_NETAUTH: registry_deployment.arc90_uri_netauth,
            }
        ),
    )

    smart_asa_app_client, _ = factory.deploy(
        on_schema_break=OnSchemaBreak.AppendApp,
        on_update=OnUpdate.AppendApp,
    )

    algorand.account.ensure_funded_from_environment(
        account_to_fund=smart_asa_app_client.app_address,
        min_spending_balance=APP_FUNDS,
    )

    sp = smart_asa_app_client.algorand.client.algod.suggested_params()
    sp.flat_fee = True
    sp.fee = sp.min_fee * 2  # type: ignore

    asset_id = smart_asa_app_client.send.asset_create(
        AssetCreateArgs(
            total=ASA_TOTAL,
            decimals=ASA_DECIMALS,
            default_frozen=ASA_DEFAULT_FROZEN,
            unit_name=ASA_UNIT_NAME,
            name=ASA_NAME,
            url=ASA_URL,
            metadata_hash=ASA_METADATA_HASH,
            manager_addr=deployer.address,
            reserve_addr=smart_asa_app_client.app_address,
            clawback_addr=deployer.address,
            freeze_addr=deployer.address,
        ),
        params=CommonAppCallParams(static_fee=AlgoAmount.from_micro_algo(sp.fee)),
    ).abi_return
    logger.info(f"Smart ASA ID: {asset_id}")

    if algorand.client.is_testnet():
        # Update Asset Metadata
        METADATA_JSON["properties"]["arc-20"][
            "application-id"
        ] = smart_asa_app_client.app_id

        metadata = AssetMetadata.from_json(
            asset_id=asset_id,
            json_obj=METADATA_JSON,
            flags=METADATA_FLAGS,
            deprecated_by=DEPRECATED_BY,
            arc3_compliant=METADATA_FLAGS.irreversible.arc3,
        )

        mbr_result = registry_client.write.create_metadata(
            asset_manager=deployer, metadata=metadata
        )
        logger.info(f"Smart ASA Metadata MBR: {mbr_result}")
