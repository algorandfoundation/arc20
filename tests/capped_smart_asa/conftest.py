import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    SigningAccount,
)
from algokit_utils.config import config

import smart_contracts.capped_smart_asa.config as capped_cfg
from smart_contracts.artifacts.capped_smart_asa.capped_smart_asa_client import (
    AssetCreateArgs,
    CappedSmartAsaClient,
    CappedSmartAsaFactory,
)
from tests.conftest import SmartASAConfig
from tests.support import INITIAL_FUNDS, funded_account, opt_in, transfer


@pytest.fixture(scope="function")
def capped_client(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    creator: SigningAccount,
    manager: SigningAccount,
    reserve: SigningAccount,
    freeze: SigningAccount,
    clawback: SigningAccount,
) -> CappedSmartAsaClient:
    config.configure(debug=False, populate_app_call_resources=True)
    factory = algorand.client.get_typed_app_factory(
        CappedSmartAsaFactory, default_sender=creator.address
    )
    client, _ = factory.send.create.bare()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=client.app_address, min_spending_balance=INITIAL_FUNDS
    )
    asa_config = SmartASAConfig(
        manager_addr=manager.address,
        reserve_addr=reserve.address,
        freeze_addr=freeze.address,
        clawback_addr=clawback.address,
        url="ipfs://<asa-metadata-uri>",
        total=4 * capped_cfg.MAX_HOLDING,
    )
    client.send.asset_create(
        AssetCreateArgs(**asa_config.dictify()),
        params=CommonAppCallParams(static_fee=min_fee_2x),
    )
    opt_in(client, client.state.global_state.smart_asa_id, reserve)
    return client


@pytest.fixture(scope="function")
def capped_asa_id(capped_client: CappedSmartAsaClient) -> int:
    return capped_client.state.global_state.smart_asa_id


@pytest.fixture(scope="function")
def receiver(
    algorand: AlgorandClient, capped_client: CappedSmartAsaClient, capped_asa_id: int
) -> SigningAccount:
    account = funded_account(algorand)
    opt_in(capped_client, capped_asa_id, account)
    return account


@pytest.fixture(scope="function")
def holder(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    reserve: SigningAccount,
    capped_client: CappedSmartAsaClient,
    capped_asa_id: int,
) -> SigningAccount:
    # Minted above the cap: mints never reach the hook
    account = funded_account(algorand)
    opt_in(capped_client, capped_asa_id, account)
    transfer(
        capped_client,
        capped_asa_id,
        signer=reserve,
        asset_sender=capped_client.app_address,
        asset_receiver=account.address,
        asset_amount=2 * capped_cfg.MAX_HOLDING,
        fee=min_fee_2x,
    )
    return account
