from collections.abc import Callable
from dataclasses import dataclass

import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AppClientMethodCallParams,
    LogicError,
    PaymentParams,
    SigningAccount,
)
from algosdk.atomic_transaction_composer import TransactionWithSigner
from algosdk.transaction import OnComplete

import smart_contracts.errors as err
import smart_contracts.smart_asa.config as cfg
from smart_contracts.artifacts.smart_asa.smart_asa_client import SmartAsaClient
from tests.conftest import SmartASAConfig
from tests.support import (
    ASSERT_FAILED,
    account_freeze,
    asa_close_out_txn,
    balance,
    close_out,
    close_out_call,
    global_freeze,
)


@dataclass(frozen=True)
class _NextTxn:
    """Builds the transaction that follows the `asset_close_out` call."""

    client: SmartAsaClient
    asset_id: int
    holder: SigningAccount
    other: SigningAccount
    dummy_asa: int

    def asa_close_out(
        self,
        sender: SigningAccount | None = None,
        asset_id: int | None = None,
        **overrides: object,
    ) -> TransactionWithSigner:
        sender = sender or self.holder
        txn = asa_close_out_txn(
            self.client, asset_id or self.asset_id, sender, **overrides
        )
        return TransactionWithSigner(txn, sender.signer)

    def payment(self) -> TransactionWithSigner:
        txn = self.client.algorand.create_transaction.payment(
            PaymentParams(
                sender=self.holder.address,
                receiver=self.holder.address,
                amount=AlgoAmount.from_micro_algo(0),
            )
        )
        return TransactionWithSigner(txn, self.holder.signer)


# (transaction after the close-out call, expected error)
INVALID_CLOSE_OUT_GROUPS = [
    pytest.param(
        lambda g: None, err.INVALID_CLOSE_OUT_GROUP_SIZE, id="no asset close-out"
    ),
    pytest.param(
        lambda g: g.payment(), "transaction type is axfer", id="not an asset transfer"
    ),
    pytest.param(
        lambda g: g.asa_close_out(asset_id=g.dummy_asa),
        err.CLOSE_OUT_WRONG_ASA,
        id="wrong asset",
    ),
    pytest.param(
        lambda g: g.asa_close_out(sender=g.other),
        err.CLOSE_OUT_WRONG_SENDER,
        id="wrong sender",
    ),
    pytest.param(
        lambda g: g.asa_close_out(amount=1),
        err.CLOSE_OUT_WRONG_AMOUNT,
        id="non-zero amount",
    ),
    pytest.param(
        lambda g: g.asa_close_out(close_asset_to=None),
        err.CLOSE_OUT_WRONG_CLOSE_TO,
        id="no close-to",
    ),
    pytest.param(
        lambda g: g.asa_close_out(close_asset_to=g.other.address),
        err.CLOSE_OUT_WRONG_CLOSE_TO,
        id="close-to not the creator",
    ),
]


def test_pass_regular_close_out(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    asa_config: SmartASAConfig,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
) -> None:
    assert (
        balance(smart_asa_client, smart_asa_id, account_with_supply) == asa_config.total
    )
    assert balance(smart_asa_client, smart_asa_id, receiver) == 0

    close_out(
        smart_asa_client,
        smart_asa_id,
        account_with_supply,
        close_to=receiver.address,
        fee=min_fee_2x,
    )
    assert (
        smart_asa_id
        not in algorand.account.get_information(account_with_supply.address).assets
    )
    assert balance(smart_asa_client, smart_asa_id, receiver) == asa_config.total


def test_pass_close_out_frozen_asset(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    account_with_supply: SigningAccount,
) -> None:
    # Closing out to the Creator is allowed while the Smart ASA is globally frozen
    global_freeze(smart_asa_client, smart_asa_id, freeze)
    close_out(
        smart_asa_client,
        smart_asa_id,
        account_with_supply,
        close_to=smart_asa_client.app_address,
        fee=min_fee_2x,
    )
    assert (
        smart_asa_id
        not in algorand.account.get_information(account_with_supply.address).assets
    )
    assert (
        balance(smart_asa_client, smart_asa_id, smart_asa_client.app_address)
        == cfg.TOTAL
    )


def test_pass_close_out_account_frozen(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    account_with_supply: SigningAccount,
) -> None:
    # Closing out to the Creator is allowed while the account is frozen
    account_freeze(smart_asa_client, smart_asa_id, freeze, account_with_supply.address)
    close_out(
        smart_asa_client,
        smart_asa_id,
        account_with_supply,
        close_to=smart_asa_client.app_address,
        fee=min_fee_2x,
    )
    assert (
        smart_asa_id
        not in algorand.account.get_information(account_with_supply.address).assets
    )


def test_pass_close_out_to_creator_without_inner_fee(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    account_with_supply: SigningAccount,
) -> None:
    # No inner transfer when closing out to the Creator: the minimum fee is enough
    close_out(
        smart_asa_client,
        smart_asa_id,
        account_with_supply,
        close_to=smart_asa_client.app_address,
    )
    assert (
        smart_asa_id
        not in algorand.account.get_information(account_with_supply.address).assets
    )
    assert (
        balance(smart_asa_client, smart_asa_id, smart_asa_client.app_address)
        == cfg.TOTAL
    )


def test_fail_wrong_on_complete(
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=ASSERT_FAILED):
        smart_asa_client.app_client.send.call(
            AppClientMethodCallParams(
                method="asset_close_out",
                args=[smart_asa_id, receiver.address],
                on_complete=OnComplete.NoOpOC,
                signer=account_with_supply.signer,
                sender=account_with_supply.address,
            )
        )


def test_fail_invalid_ctrl_asa(
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    account_with_supply: SigningAccount,
    dummy_asa: int,
) -> None:
    composer = close_out_call(
        smart_asa_client,
        dummy_asa,
        account_with_supply,
        close_to=smart_asa_client.app_address,
    )
    composer.add_transaction(
        asa_close_out_txn(smart_asa_client, smart_asa_id, account_with_supply),
        signer=account_with_supply.signer,
    )
    with pytest.raises(LogicError, match=err.INVALID_CTRL_ASA):
        composer.send()


@pytest.mark.parametrize(("next_txn", "error"), INVALID_CLOSE_OUT_GROUPS)
def test_fail_invalid_close_out_group(
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
    dummy_asa: int,
    next_txn: Callable[[_NextTxn], TransactionWithSigner | None],
    error: str,
) -> None:
    composer = close_out_call(
        smart_asa_client,
        smart_asa_id,
        account_with_supply,
        close_to=smart_asa_client.app_address,
    )
    txn = next_txn(
        _NextTxn(
            smart_asa_client, smart_asa_id, account_with_supply, receiver, dummy_asa
        )
    )
    if txn is not None:
        composer.add_transaction(txn.txn, signer=txn.signer)
    with pytest.raises(LogicError, match=error):
        composer.send()


def test_fail_close_out_frozen_asset(
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
) -> None:
    global_freeze(smart_asa_client, smart_asa_id, freeze)
    with pytest.raises(LogicError, match=err.GLOBAL_FROZEN):
        close_out(
            smart_asa_client,
            smart_asa_id,
            account_with_supply,
            close_to=receiver.address,
        )


def test_fail_close_out_sender_frozen(
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
) -> None:
    account_freeze(smart_asa_client, smart_asa_id, freeze, account_with_supply.address)
    with pytest.raises(LogicError, match=err.SENDER_FROZEN):
        close_out(
            smart_asa_client,
            smart_asa_id,
            account_with_supply,
            close_to=receiver.address,
        )


def test_fail_close_out_target_frozen(
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
) -> None:
    account_freeze(smart_asa_client, smart_asa_id, freeze, receiver.address)
    with pytest.raises(LogicError, match=err.RECEIVER_FROZEN):
        close_out(
            smart_asa_client,
            smart_asa_id,
            account_with_supply,
            close_to=receiver.address,
        )
