from collections.abc import Callable

import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    SigningAccount,
)
from algokit_utils.config import config

from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AssetConfigArgs,
    AssetCreateArgs,
    SmartAsaClient,
    SmartAsaFactory,
)
from tests.conftest import SmartASAConfig
from tests.support import (
    INITIAL_FUNDS,
    account_freeze,
    funded_account,
    opt_in,
    transfer,
)


@pytest.fixture(scope="function")
def smart_asa_client_no_asset(
    algorand: AlgorandClient,
    creator: SigningAccount,
) -> SmartAsaClient:
    config.configure(
        debug=False,
        populate_app_call_resources=True,
        # trace_all=True,
    )

    factory = algorand.client.get_typed_app_factory(
        SmartAsaFactory,
        default_sender=creator.address,
    )
    client, _ = factory.send.create.bare()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=client.app_address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return client


@pytest.fixture(scope="function")
def asa_config(
    manager: SigningAccount,
    reserve: SigningAccount,
    freeze: SigningAccount,
    clawback: SigningAccount,
    request: pytest.FixtureRequest,
) -> SmartASAConfig:
    # Not default frozen, unless parametrized indirectly (see tests.support)
    return SmartASAConfig(
        manager_addr=manager.address,
        reserve_addr=reserve.address,
        freeze_addr=freeze.address,
        clawback_addr=clawback.address,
        url="ipfs://<asa-metadata-uri>",
        default_frozen=getattr(request, "param", False),
    )


@pytest.fixture(scope="function")
def smart_asa_client(
    min_fee_2x: AlgoAmount,
    reserve: SigningAccount,
    freeze: SigningAccount,
    smart_asa_client_no_asset: SmartAsaClient,
    asa_config: SmartASAConfig,
) -> SmartAsaClient:
    client = smart_asa_client_no_asset
    client.send.asset_create(
        AssetCreateArgs(**asa_config.dictify()),
        params=CommonAppCallParams(static_fee=min_fee_2x),
    )
    # The Reserve mints and burns only if opted in and not frozen (approved by Freeze
    # if the Smart ASA is default frozen)
    smart_asa_id = client.state.global_state.smart_asa_id
    opt_in(client, smart_asa_id, reserve)
    if asa_config.default_frozen:
        account_freeze(client, smart_asa_id, freeze, reserve.address, frozen=False)
    return client


@pytest.fixture(scope="function")
def smart_asa_id(smart_asa_client: SmartAsaClient) -> int:
    # Read once: the typed global state is fetched lazily from the app on each access
    return smart_asa_client.state.global_state.smart_asa_id


@pytest.fixture(scope="function")
def opted_in_account_factory(
    algorand: AlgorandClient, smart_asa_client: SmartAsaClient, smart_asa_id: int
) -> Callable[[], SigningAccount]:
    def _factory() -> SigningAccount:
        account = funded_account(algorand)
        opt_in(smart_asa_client, smart_asa_id, account)
        return account

    return _factory


@pytest.fixture(scope="function")
def receiver(
    opted_in_account_factory: Callable[[], SigningAccount],
) -> SigningAccount:
    return opted_in_account_factory()


@pytest.fixture(scope="function")
def reserve_and_clawback(
    manager: SigningAccount,
    reserve: SigningAccount,
    asa_config: SmartASAConfig,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
) -> SigningAccount:
    asa_config.clawback_addr = asa_config.reserve_addr
    smart_asa_client.send.asset_config(
        AssetConfigArgs(config_asset=smart_asa_id, **asa_config.dictify()),
        params=CommonAppCallParams(signer=manager.signer, sender=manager.address),
    )
    return reserve


@pytest.fixture(scope="function")
def reserve_with_supply(
    min_fee_2x: AlgoAmount,
    reserve: SigningAccount,
    asa_config: SmartASAConfig,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
) -> SigningAccount:
    transfer(
        smart_asa_client,
        smart_asa_id,
        signer=reserve,
        asset_sender=smart_asa_client.app_address,
        asset_receiver=reserve.address,
        asset_amount=asa_config.total,
        fee=min_fee_2x,
    )
    return reserve


@pytest.fixture(scope="function")
def account_with_supply(
    min_fee_2x: AlgoAmount,
    reserve: SigningAccount,
    asa_config: SmartASAConfig,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    opted_in_account_factory: Callable[[], SigningAccount],
) -> SigningAccount:
    account = opted_in_account_factory()
    transfer(
        smart_asa_client,
        smart_asa_id,
        signer=reserve,
        asset_sender=smart_asa_client.app_address,
        asset_receiver=account.address,
        asset_amount=asa_config.total,
        fee=min_fee_2x,
    )
    return account
