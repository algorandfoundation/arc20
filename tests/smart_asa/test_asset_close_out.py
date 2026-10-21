import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AppClientMethodCallParams,
    AssetTransferParams,
    CommonAppCallParams,
    LogicError,
    PaymentParams,
    SigningAccount,
)
from algosdk.transaction import OnComplete, Transaction

import smart_contracts.errors as err
import smart_contracts.smart_asa.config as cfg
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AccountFreezeArgs,
    AssetCloseOutArgs,
    AssetFreezeArgs,
    SmartAsaClient,
    SmartAsaComposer,
)

# ARC-4 router OnComplete assertion (no error message)
ROUTER_REJECTED = "assert failed"
# Reading a transaction index beyond the group size
GTXN_OUT_OF_RANGE = r"len\(group\) is"

UNREACHABLE = "Unreachable: asset_create is one-shot and asset_destroy deletes the app"


def _close_out_call(
    client: SmartAsaClient,
    account: SigningAccount,
    *,
    close_to: str,
    fee: AlgoAmount,
    close_asset: int | None = None,
) -> SmartAsaComposer:
    return client.new_group().close_out.asset_close_out(
        AssetCloseOutArgs(
            close_asset=(
                close_asset
                if close_asset is not None
                else client.state.global_state.smart_asa_id
            ),
            close_to=close_to,
        ),
        params=CommonAppCallParams(
            static_fee=fee, signer=account.signer, sender=account.address
        ),
    )


def _asa_close_out_txn(
    algorand: AlgorandClient,
    client: SmartAsaClient,
    sender: SigningAccount,
    *,
    asset_id: int | None = None,
    amount: int = 0,
    close_asset_to: str | None = None,
) -> Transaction:
    return algorand.create_transaction.asset_transfer(
        AssetTransferParams(
            sender=sender.address,
            asset_id=(
                asset_id
                if asset_id is not None
                else client.state.global_state.smart_asa_id
            ),
            receiver=client.app_address,
            close_asset_to=close_asset_to,
            amount=amount,
        )
    )


def _close_out(
    algorand: AlgorandClient,
    client: SmartAsaClient,
    account: SigningAccount,
    *,
    close_to: str,
    fee: AlgoAmount,
) -> None:
    composer = _close_out_call(client, account, close_to=close_to, fee=fee)
    composer.add_transaction(
        _asa_close_out_txn(
            algorand, client, account, close_asset_to=client.app_address
        ),
        signer=account.signer,
    )
    composer.send()


def _global_freeze(client: SmartAsaClient, freeze: SigningAccount) -> None:
    client.send.asset_freeze(
        AssetFreezeArgs(
            freeze_asset=client.state.global_state.smart_asa_id,
            asset_frozen=True,
        ),
        params=CommonAppCallParams(signer=freeze.signer, sender=freeze.address),
    )


def _account_freeze(
    client: SmartAsaClient, freeze: SigningAccount, account: SigningAccount
) -> None:
    client.send.account_freeze(
        AccountFreezeArgs(
            freeze_asset=client.state.global_state.smart_asa_id,
            freeze_account=account.address,
            asset_frozen=True,
        ),
        params=CommonAppCallParams(signer=freeze.signer, sender=freeze.address),
    )


@pytest.mark.parametrize("asa_config", [False], indirect=True)
def test_pass_regular_close_out(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
) -> None:
    smart_asa = smart_asa_client.state.global_state
    smart_asa_id = smart_asa.smart_asa_id
    account_asset_balance = algorand.asset.get_account_information(
        account_with_supply, smart_asa_id
    ).balance
    receiver_asset_balance = algorand.asset.get_account_information(
        receiver, smart_asa_id
    ).balance
    assert account_asset_balance == smart_asa.total
    assert receiver_asset_balance == 0

    close_out = smart_asa_client.new_group().close_out.asset_close_out(
        AssetCloseOutArgs(
            close_asset=smart_asa_id,
            close_to=receiver.address,
        ),
        params=CommonAppCallParams(
            static_fee=min_fee_2x,
            signer=account_with_supply.signer,
            sender=account_with_supply.address,
        ),
    )
    close_out.add_transaction(
        txn=algorand.create_transaction.asset_transfer(
            AssetTransferParams(
                sender=account_with_supply.address,
                asset_id=smart_asa_id,
                receiver=smart_asa_client.app_address,
                close_asset_to=smart_asa_client.app_address,
                amount=0,
            )
        ),
        signer=account_with_supply.signer,
    )
    close_out.send()
    receiver_asset_balance = algorand.asset.get_account_information(
        receiver, smart_asa_id
    ).balance
    assert (
        smart_asa_id
        not in algorand.account.get_information(account_with_supply.address).assets
    )
    assert receiver_asset_balance == smart_asa.total


@pytest.mark.parametrize("asa_config", [False], indirect=True)
def test_pass_close_out_frozen_asset(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    freeze: SigningAccount,
    account_with_supply: SigningAccount,
) -> None:
    # Closing out to the Creator is allowed while the Smart ASA is globally frozen
    smart_asa_id = smart_asa_client.state.global_state.smart_asa_id
    _global_freeze(smart_asa_client, freeze)
    _close_out(
        algorand,
        smart_asa_client,
        account_with_supply,
        close_to=smart_asa_client.app_address,
        fee=min_fee_2x,
    )
    assert (
        smart_asa_id
        not in algorand.account.get_information(account_with_supply.address).assets
    )
    assert (
        algorand.asset.get_account_information(
            smart_asa_client.app_address, smart_asa_id
        ).balance
        == cfg.TOTAL
    )


@pytest.mark.parametrize("asa_config", [False], indirect=True)
def test_pass_close_out_account_frozen(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    freeze: SigningAccount,
    account_with_supply: SigningAccount,
) -> None:
    # Closing out to the Creator is allowed while the account is frozen
    smart_asa_id = smart_asa_client.state.global_state.smart_asa_id
    _account_freeze(smart_asa_client, freeze, account_with_supply)
    _close_out(
        algorand,
        smart_asa_client,
        account_with_supply,
        close_to=smart_asa_client.app_address,
        fee=min_fee_2x,
    )
    assert (
        smart_asa_id
        not in algorand.account.get_information(account_with_supply.address).assets
    )


@pytest.mark.skip(reason=UNREACHABLE)
def test_pass_destroyed_asset() -> None:
    pass


@pytest.mark.parametrize("asa_config", [False], indirect=True)
def test_fail_wrong_on_complete(
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=ROUTER_REJECTED):
        smart_asa_client.app_client.send.call(
            AppClientMethodCallParams(
                method="asset_close_out",
                args=[
                    smart_asa_client.state.global_state.smart_asa_id,
                    receiver.address,
                ],
                on_complete=OnComplete.NoOpOC,
                static_fee=min_fee_2x,
                signer=account_with_supply.signer,
                sender=account_with_supply.address,
            )
        )


@pytest.mark.parametrize("asa_config", [False], indirect=True)
def test_fail_invalid_local_ctrl_asa(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    account_with_supply: SigningAccount,
    dummy_asa: int,
) -> None:
    composer = _close_out_call(
        smart_asa_client,
        account_with_supply,
        close_to=smart_asa_client.app_address,
        fee=min_fee_2x,
        close_asset=dummy_asa,
    )
    composer.add_transaction(
        _asa_close_out_txn(
            algorand,
            smart_asa_client,
            account_with_supply,
            close_asset_to=smart_asa_client.app_address,
        ),
        signer=account_with_supply.signer,
    )
    with pytest.raises(LogicError, match=err.INVALID_CTRL_ASA):
        composer.send()


@pytest.mark.parametrize("asa_config", [False], indirect=True)
def test_fail_group_wrong_size(
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    account_with_supply: SigningAccount,
) -> None:
    composer = _close_out_call(
        smart_asa_client,
        account_with_supply,
        close_to=smart_asa_client.app_address,
        fee=min_fee_2x,
    )
    # The next transaction is read before the group size is checked
    with pytest.raises(LogicError, match=GTXN_OUT_OF_RANGE):
        composer.send()


@pytest.mark.parametrize("asa_config", [False], indirect=True)
def test_fail_group_wrong_txn_type(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    account_with_supply: SigningAccount,
) -> None:
    composer = _close_out_call(
        smart_asa_client,
        account_with_supply,
        close_to=smart_asa_client.app_address,
        fee=min_fee_2x,
    )
    composer.add_transaction(
        algorand.create_transaction.payment(
            PaymentParams(
                sender=account_with_supply.address,
                receiver=account_with_supply.address,
                amount=AlgoAmount.from_micro_algo(0),
            )
        ),
        signer=account_with_supply.signer,
    )
    with pytest.raises(LogicError, match="transaction type is axfer"):
        composer.send()


@pytest.mark.parametrize("asa_config", [False], indirect=True)
def test_fail_group_wrong_asset(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    account_with_supply: SigningAccount,
    dummy_asa: int,
) -> None:
    composer = _close_out_call(
        smart_asa_client,
        account_with_supply,
        close_to=smart_asa_client.app_address,
        fee=min_fee_2x,
    )
    composer.add_transaction(
        _asa_close_out_txn(
            algorand,
            smart_asa_client,
            account_with_supply,
            asset_id=dummy_asa,
            close_asset_to=smart_asa_client.app_address,
        ),
        signer=account_with_supply.signer,
    )
    with pytest.raises(LogicError, match=err.CLOSE_OUT_WRONG_ASA):
        composer.send()


@pytest.mark.parametrize("asa_config", [False], indirect=True)
def test_fail_group_wrong_sender(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
) -> None:
    composer = _close_out_call(
        smart_asa_client,
        account_with_supply,
        close_to=smart_asa_client.app_address,
        fee=min_fee_2x,
    )
    composer.add_transaction(
        _asa_close_out_txn(
            algorand,
            smart_asa_client,
            receiver,
            close_asset_to=smart_asa_client.app_address,
        ),
        signer=receiver.signer,
    )
    with pytest.raises(LogicError, match=err.CLOSE_OUT_WRONG_SENDER):
        composer.send()


@pytest.mark.parametrize("asa_config", [False], indirect=True)
def test_fail_group_wrong_amount(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    account_with_supply: SigningAccount,
) -> None:
    composer = _close_out_call(
        smart_asa_client,
        account_with_supply,
        close_to=smart_asa_client.app_address,
        fee=min_fee_2x,
    )
    composer.add_transaction(
        _asa_close_out_txn(
            algorand,
            smart_asa_client,
            account_with_supply,
            amount=1,
            close_asset_to=smart_asa_client.app_address,
        ),
        signer=account_with_supply.signer,
    )
    with pytest.raises(LogicError, match=err.CLOSE_OUT_WRONG_AMOUNT):
        composer.send()


@pytest.mark.parametrize("asa_config", [False], indirect=True)
@pytest.mark.parametrize("close_target", ["none", "receiver"])
def test_fail_group_wrong_close_to(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
    close_target: str,
) -> None:
    composer = _close_out_call(
        smart_asa_client,
        account_with_supply,
        close_to=smart_asa_client.app_address,
        fee=min_fee_2x,
    )
    composer.add_transaction(
        _asa_close_out_txn(
            algorand,
            smart_asa_client,
            account_with_supply,
            close_asset_to=receiver.address if close_target == "receiver" else None,
        ),
        signer=account_with_supply.signer,
    )
    with pytest.raises(LogicError, match=err.CLOSE_OUT_WRONG_CLOSE_TO):
        composer.send()


@pytest.mark.skip(reason=UNREACHABLE)
def test_fail_invalid_ctrl_asa() -> None:
    pass


@pytest.mark.parametrize("asa_config", [False], indirect=True)
def test_fail_close_out_frozen_asset(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    freeze: SigningAccount,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
) -> None:
    _global_freeze(smart_asa_client, freeze)
    with pytest.raises(LogicError, match=err.GLOBAL_FROZEN):
        _close_out(
            algorand,
            smart_asa_client,
            account_with_supply,
            close_to=receiver.address,
            fee=min_fee_2x,
        )


@pytest.mark.parametrize("asa_config", [False], indirect=True)
def test_fail_close_out_sender_frozen(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    freeze: SigningAccount,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
) -> None:
    _account_freeze(smart_asa_client, freeze, account_with_supply)
    with pytest.raises(LogicError, match=err.SENDER_FROZEN):
        _close_out(
            algorand,
            smart_asa_client,
            account_with_supply,
            close_to=receiver.address,
            fee=min_fee_2x,
        )


@pytest.mark.parametrize("asa_config", [False], indirect=True)
def test_fail_close_out_target_frozen(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    freeze: SigningAccount,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
) -> None:
    _account_freeze(smart_asa_client, freeze, receiver)
    with pytest.raises(LogicError, match=err.CLOSE_TO_FROZEN):
        _close_out(
            algorand,
            smart_asa_client,
            account_with_supply,
            close_to=receiver.address,
            fee=min_fee_2x,
        )
