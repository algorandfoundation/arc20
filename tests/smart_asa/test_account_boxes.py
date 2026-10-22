import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AssetTransferParams,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)

import smart_contracts.errors as err
import smart_contracts.smart_asa.config as cfg
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AccountFreezeArgs,
    GetAccountIsFrozenArgs,
    SmartAsaClient,
    SmartAsaComposer,
)
from tests.conftest import SmartASAConfig
from tests.support import (
    BOTH_DEFAULT_FROZEN,
    account_freeze,
    arc65_errors,
    box_deposit,
    opt_in,
    transfer,
)

BOX_MBR = cfg.FREEZE_EXCEPTION_BOX_MBR


def _balances(algorand: AlgorandClient, address: str) -> tuple[int, int]:
    info = algorand.client.algod.account_info(address)
    return info["amount"], info["min-balance"]


def _amount(algorand: AlgorandClient, address: str) -> int:
    return _balances(algorand, address)[0]


def _is_frozen(client: SmartAsaClient, asset_id: int, address: str) -> bool | None:
    return client.send.get_account_is_frozen(
        GetAccountIsFrozenArgs(freeze_asset=asset_id, freeze_account=address)
    ).abi_return


def _add_freeze(
    group: SmartAsaComposer,
    asset_id: int,
    freeze: SigningAccount,
    account: str,
    *,
    frozen: bool = True,
) -> SmartAsaComposer:
    return group.account_freeze(
        AccountFreezeArgs(
            freeze_asset=asset_id, freeze_account=account, asset_frozen=frozen
        ),
        params=CommonAppCallParams(sender=freeze.address, signer=freeze.signer),
    )


@BOTH_DEFAULT_FROZEN
def test_pass_box_only_for_exceptions(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    asa_config: SmartASAConfig,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    receiver: SigningAccount,
) -> None:
    app, fee = smart_asa_client.app_address, min_fee_2x.micro_algo
    default = asa_config.default_frozen
    app_balance, app_mbr = _balances(algorand, app)
    freeze_balance = _amount(algorand, freeze.address)

    # Differing from the default creates an empty box, paid by Freeze's deposit
    account_freeze(
        smart_asa_client, smart_asa_id, freeze, receiver.address, frozen=not default
    )
    box_name = cfg.FREEZE_EXCEPTION_KEY_PREFIX + receiver.public_key
    assert algorand.app.get_box_value(smart_asa_client.app_id, box_name) == b""
    assert _balances(algorand, app) == (app_balance + BOX_MBR, app_mbr + BOX_MBR)
    assert _amount(algorand, freeze.address) == freeze_balance - BOX_MBR - fee
    assert _is_frozen(smart_asa_client, smart_asa_id, receiver.address) == (not default)

    # Back to the default deletes the box, refunding the deposit to Freeze
    account_freeze(
        smart_asa_client, smart_asa_id, freeze, receiver.address, frozen=default
    )
    assert _balances(algorand, app) == (app_balance, app_mbr)
    assert _amount(algorand, freeze.address) == freeze_balance - 2 * fee
    assert _is_frozen(smart_asa_client, smart_asa_id, receiver.address) == default

    # Resetting again finds no box: nothing changes, a 0 refund
    account_freeze(
        smart_asa_client, smart_asa_id, freeze, receiver.address, frozen=default
    )
    assert _balances(algorand, app) == (app_balance, app_mbr)
    assert _amount(algorand, freeze.address) == freeze_balance - 3 * fee


@BOTH_DEFAULT_FROZEN
def test_pass_refreeze_needs_no_deposit(
    algorand: AlgorandClient,
    min_fee: AlgoAmount,
    min_fee_2x: AlgoAmount,
    asa_config: SmartASAConfig,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    receiver: SigningAccount,
) -> None:
    app, exception = smart_asa_client.app_address, not asa_config.default_frozen
    account_freeze(
        smart_asa_client, smart_asa_id, freeze, receiver.address, frozen=exception
    )
    app_balance, app_mbr = _balances(algorand, app)
    freeze_balance = _amount(algorand, freeze.address)

    # The box exists: setting the same state again needs no deposit
    group = smart_asa_client.new_group()
    _add_freeze(group, smart_asa_id, freeze, receiver.address, frozen=exception).send()
    assert _balances(algorand, app) == (app_balance, app_mbr)
    freeze_balance -= min_fee.micro_algo
    assert _amount(algorand, freeze.address) == freeze_balance

    # An unneeded deposit stays in the App as spare balance for the Manager
    account_freeze(
        smart_asa_client, smart_asa_id, freeze, receiver.address, frozen=exception
    )
    assert _balances(algorand, app) == (app_balance + BOX_MBR, app_mbr)
    assert _amount(algorand, freeze.address) == (
        freeze_balance - BOX_MBR - min_fee_2x.micro_algo
    )


def test_pass_freeze_before_asa_opt_in(
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    reserve: SigningAccount,
    eve: SigningAccount,
) -> None:
    # Any address can be frozen, e.g. from a sanctions list, before it holds the asset
    account_freeze(smart_asa_client, smart_asa_id, freeze, eve.address)
    opt_in(smart_asa_client, smart_asa_id, eve)
    with pytest.raises(LogicError, match=err.RECEIVER_FROZEN):
        transfer(
            smart_asa_client,
            smart_asa_id,
            signer=reserve,
            asset_sender=smart_asa_client.app_address,
            asset_receiver=eve.address,
            asset_amount=1,
        )


def test_pass_freeze_survives_leaving(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    reserve: SigningAccount,
    account_with_supply: SigningAccount,
) -> None:
    # A frozen holder can surrender its units and opt in again: still frozen
    account_freeze(smart_asa_client, smart_asa_id, freeze, account_with_supply.address)
    algorand.send.asset_transfer(
        AssetTransferParams(
            sender=account_with_supply.address,
            signer=account_with_supply.signer,
            asset_id=smart_asa_id,
            receiver=smart_asa_client.app_address,
            amount=0,
            close_asset_to=smart_asa_client.app_address,
        )
    )
    opt_in(smart_asa_client, smart_asa_id, account_with_supply)
    assert _is_frozen(smart_asa_client, smart_asa_id, account_with_supply.address)
    with pytest.raises(LogicError, match=err.RECEIVER_FROZEN):
        transfer(
            smart_asa_client,
            smart_asa_id,
            signer=reserve,
            asset_sender=smart_asa_client.app_address,
            asset_receiver=account_with_supply.address,
            asset_amount=1,
        )


def test_pass_deposit_by_anyone(
    algorand: AlgorandClient,
    min_fee: AlgoAmount,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    receiver: SigningAccount,
    eve: SigningAccount,
) -> None:
    app, fee = smart_asa_client.app_address, min_fee.micro_algo
    app_balance, app_mbr = _balances(algorand, app)
    freeze_balance = _amount(algorand, freeze.address)
    eve_balance = _amount(algorand, eve.address)

    # Any sender, at least the MBR: the surplus is spare balance for the Manager
    group = smart_asa_client.new_group().add_transaction(
        box_deposit(smart_asa_client, eve, amount=2 * BOX_MBR), signer=eve.signer
    )
    _add_freeze(group, smart_asa_id, freeze, receiver.address).send()
    assert _balances(algorand, app) == (app_balance + 2 * BOX_MBR, app_mbr + BOX_MBR)
    assert _amount(algorand, eve.address) == eve_balance - 2 * BOX_MBR - fee
    assert _amount(algorand, freeze.address) == freeze_balance - fee

    # The reset refunds the box MBR to Freeze, whoever deposited it
    account_freeze(
        smart_asa_client, smart_asa_id, freeze, receiver.address, frozen=False
    )
    assert _balances(algorand, app) == (app_balance + BOX_MBR, app_mbr)
    assert _amount(algorand, eve.address) == eve_balance - 2 * BOX_MBR - fee
    assert _amount(algorand, freeze.address) == (
        freeze_balance - fee + BOX_MBR - min_fee_2x.micro_algo
    )


def test_pass_batch(
    algorand: AlgorandClient,
    min_fee: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    receiver: SigningAccount,
    eve: SigningAccount,
) -> None:
    app = smart_asa_client.app_address
    app_balance, app_mbr = _balances(algorand, app)
    freeze_balance = _amount(algorand, freeze.address)

    # Each new box needs its own deposit (unique in the group), just before its freeze
    group = smart_asa_client.new_group()
    for account in (receiver, eve):
        payment = box_deposit(smart_asa_client, freeze, note=account.public_key)
        group.add_transaction(payment, freeze.signer)
        _add_freeze(group, smart_asa_id, freeze, account.address)
    group.send()
    assert _is_frozen(smart_asa_client, smart_asa_id, receiver.address)
    assert _is_frozen(smart_asa_client, smart_asa_id, eve.address)
    assert _balances(algorand, app) == (
        app_balance + 2 * BOX_MBR,
        app_mbr + 2 * BOX_MBR,
    )
    assert _amount(algorand, freeze.address) == (
        freeze_balance - 2 * BOX_MBR - 4 * min_fee.micro_algo
    )


@pytest.mark.parametrize(
    "deposit", ["missing", "too low", "not to the App", "not just before"]
)
def test_fail_box_mbr_unfunded(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    receiver: SigningAccount,
    eve: SigningAccount,
    deposit: str,
) -> None:
    # The App spare balance never pays for a new box
    group = smart_asa_client.new_group()
    match deposit:
        case "too low":
            payment = box_deposit(smart_asa_client, freeze, amount=BOX_MBR - 1)
            group.add_transaction(payment, freeze.signer)
        case "not to the App":
            payment = box_deposit(smart_asa_client, freeze, receiver=eve.address)
            group.add_transaction(payment, freeze.signer)
        case "not just before":
            payment = box_deposit(smart_asa_client, freeze, amount=2 * BOX_MBR)
            _add_freeze(
                group.add_transaction(payment, freeze.signer),
                smart_asa_id,
                freeze,
                eve.address,
            )
    _add_freeze(group, smart_asa_id, freeze, receiver.address)
    assert arc65_errors(algorand, group.composer()) == [f"ERR:{err.BOX_MBR_UNFUNDED}"]
