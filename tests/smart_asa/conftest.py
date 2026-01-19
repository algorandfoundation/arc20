from collections.abc import Callable

import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AssetOptInParams,
    CommonAppCallParams,
    SigningAccount,
)
from algokit_utils.config import config
from algosdk.atomic_transaction_composer import TransactionWithSigner

from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AssetConfigArgs,
    AssetCreateArgs,
    AssetOptInArgs,
    AssetTransferArgs,
    SmartAsaClient,
    SmartAsaFactory,
)
from tests.conftest import INITIAL_FUNDS, SmartASAConfig


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


@pytest.fixture(
    scope="function", params=[False, True], ids=["Not Default Frozen", "Default Frozen"]
)
def asa_config(
    manager: SigningAccount,
    reserve: SigningAccount,
    freeze: SigningAccount,
    clawback: SigningAccount,
    request: pytest.FixtureRequest,
) -> SmartASAConfig:
    return SmartASAConfig(
        manager_addr=manager.address,
        reserve_addr=reserve.address,
        freeze_addr=freeze.address,
        clawback_addr=clawback.address,
        url="ipfs://<asa-metadata-uri>",
        default_frozen=request.param,
    )


@pytest.fixture(scope="function")
def smart_asa_client(
    min_fee_2x: AlgoAmount,
    smart_asa_client_no_asset: SmartAsaClient,
    asa_config: SmartASAConfig,
) -> SmartAsaClient:
    smart_asa_client_no_asset.send.asset_create(
        AssetCreateArgs(**asa_config.dictify()),
        params=CommonAppCallParams(static_fee=min_fee_2x),
    )
    return smart_asa_client_no_asset


@pytest.fixture(scope="function")
def opted_in_account_factory(
    algorand: AlgorandClient, smart_asa_client: SmartAsaClient
) -> Callable[..., SigningAccount]:
    def _factory() -> SigningAccount:
        account = algorand.account.random()
        algorand.account.ensure_funded_from_environment(
            account_to_fund=account.address,
            min_spending_balance=INITIAL_FUNDS,
        )
        smart_asa_id = smart_asa_client.state.global_state.smart_asa_id

        smart_asa_client.send.opt_in.asset_opt_in(
            AssetOptInArgs(
                asset=smart_asa_id,
                ctrl_asa_opt_in=TransactionWithSigner(
                    txn=algorand.create_transaction.asset_opt_in(
                        AssetOptInParams(asset_id=smart_asa_id, sender=account.address)
                    ),
                    signer=account.signer,
                ),
            ),
            params=CommonAppCallParams(
                signer=account.signer,
                sender=account.address,
            ),
        )
        return account

    return _factory


@pytest.fixture(scope="function")
def receiver(
    opted_in_account_factory: Callable[..., SigningAccount],
) -> SigningAccount:
    return opted_in_account_factory()


@pytest.fixture(scope="function")
def reserve_and_clawback(
    manager: SigningAccount,
    reserve: SigningAccount,
    asa_config: SmartASAConfig,
    smart_asa_client: SmartAsaClient,
) -> SigningAccount:
    asa_config.clawback_addr = asa_config.reserve_addr
    smart_asa_client.send.asset_config(
        AssetConfigArgs(
            config_asset=smart_asa_client.state.global_state.smart_asa_id,
            **asa_config.dictify(),
        ),
        params=CommonAppCallParams(
            signer=manager.signer,
            sender=manager.address,
        ),
    )
    return reserve


@pytest.fixture(scope="function")
def reserve_with_supply(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    reserve: SigningAccount,
    smart_asa_client: SmartAsaClient,
) -> SigningAccount:
    smart_asa = smart_asa_client.state.global_state
    smart_asa_id = smart_asa.smart_asa_id
    ctrl_asa_opt_in = TransactionWithSigner(
        txn=algorand.create_transaction.asset_opt_in(
            AssetOptInParams(asset_id=smart_asa_id, sender=reserve.address)
        ),
        signer=reserve.signer,
    )
    smart_asa_client.send.opt_in.asset_opt_in(
        AssetOptInArgs(
            asset=smart_asa_id,
            ctrl_asa_opt_in=ctrl_asa_opt_in,
        ),
        params=CommonAppCallParams(
            signer=reserve.signer,
            sender=reserve.address,
        ),
    )

    smart_asa_client.send.asset_transfer(
        AssetTransferArgs(
            xfer_asset=smart_asa_id,
            asset_amount=smart_asa.total,
            asset_sender=smart_asa_client.app_address,
            asset_receiver=reserve.address,
        ),
        params=CommonAppCallParams(
            static_fee=min_fee_2x,
            signer=reserve.signer,
            sender=reserve.address,
        ),
    )
    return reserve


@pytest.fixture(scope="function")
def account_with_supply(
    min_fee_2x: AlgoAmount,
    reserve: SigningAccount,
    smart_asa_client: SmartAsaClient,
    opted_in_account_factory: Callable[..., SigningAccount],
) -> SigningAccount:
    account = opted_in_account_factory()
    smart_asa = smart_asa_client.state.global_state

    smart_asa_client.send.asset_transfer(
        AssetTransferArgs(
            xfer_asset=smart_asa.smart_asa_id,
            asset_amount=smart_asa.total,
            asset_sender=smart_asa_client.app_address,
            asset_receiver=account.address,
        ),
        params=CommonAppCallParams(
            static_fee=min_fee_2x,
            signer=reserve.signer,
            sender=reserve.address,
        ),
    )
    return account
