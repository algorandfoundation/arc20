import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AppClientCompilationParams,
    CommonAppCallParams,
    SigningAccount,
)
from algokit_utils.config import config
from asa_metadata_registry import Arc90Compliance, Arc90Uri, AsaMetadataRegistry
from asa_metadata_registry._generated.asa_metadata_registry_client import (
    AsaMetadataRegistryFactory,
)

from smart_contracts.arc89_smart_asa.template_vars import ARC89_APP_ID
from smart_contracts.artifacts.arc89_smart_asa.arc89_smart_asa_client import (
    Arc89SmartAsaClient,
    Arc89SmartAsaFactory,
    AssetCreateArgs,
)
from tests.conftest import INITIAL_FUNDS, SmartASAConfig


@pytest.fixture(scope="session")
def asa_metadata_registry(
    algorand: AlgorandClient, deployer: SigningAccount
) -> AsaMetadataRegistry:
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
        min_spending_balance=INITIAL_FUNDS,
    )
    return AsaMetadataRegistry.from_app_client(registry_app_client)


@pytest.fixture(scope="function")
def arc89_smart_asa_client_no_asset(
    algorand: AlgorandClient,
    creator: SigningAccount,
    asa_metadata_registry: AsaMetadataRegistry,
) -> Arc89SmartAsaClient:
    config.configure(
        debug=False,
        populate_app_call_resources=True,
        # trace_all=True,
    )

    factory = algorand.client.get_typed_app_factory(
        Arc89SmartAsaFactory,
        default_sender=creator.address,
        compilation_params=AppClientCompilationParams(
            deploy_time_params={
                ARC89_APP_ID: asa_metadata_registry.config.app_id,
            }
        ),
    )
    client, _ = factory.send.create.bare()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=client.app_address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return client


@pytest.fixture(scope="function")
def arc89_asa_config(
    algorand: AlgorandClient,
    manager: SigningAccount,
    reserve: SigningAccount,
    freeze: SigningAccount,
    clawback: SigningAccount,
    asa_metadata_registry: AsaMetadataRegistry,
) -> SmartASAConfig:
    arc90_uri = Arc90Uri(
        netauth="net:" + algorand.client.network().genesis_id,
        app_id=asa_metadata_registry.config.app_id,
        box_name=None,
        compliance=Arc90Compliance((20, 89)),  # ARC-20, ARC-89
    )
    assert arc90_uri.is_partial

    return SmartASAConfig(
        manager_addr=manager.address,
        reserve_addr=reserve.address,
        freeze_addr=freeze.address,
        clawback_addr=clawback.address,
        url=arc90_uri.to_uri(),
    )


@pytest.fixture(scope="function")
def arc89_smart_asa_client(
    min_fee_2x: AlgoAmount,
    arc89_smart_asa_client_no_asset: Arc89SmartAsaClient,
    arc89_asa_config: SmartASAConfig,
) -> Arc89SmartAsaClient:
    arc89_smart_asa_client_no_asset.send.asset_create(
        AssetCreateArgs(**arc89_asa_config.dictify()),
        params=CommonAppCallParams(static_fee=min_fee_2x),
    )
    return arc89_smart_asa_client_no_asset
