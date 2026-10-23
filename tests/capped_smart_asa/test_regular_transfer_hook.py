import re

import pytest
from algokit_utils import AlgoAmount, LogicError, SigningAccount

import smart_contracts.capped_smart_asa.config as capped_cfg
import smart_contracts.capped_smart_asa.errors as capped_err
import smart_contracts.errors as err
from smart_contracts.artifacts.capped_smart_asa.capped_smart_asa_client import (
    CappedSmartAsaClient,
)
from tests.support import account_freeze, balance, transfer

CAP = capped_cfg.MAX_HOLDING


def _regular_transfer(
    client: CappedSmartAsaClient,
    asset_id: int,
    holder: SigningAccount,
    receiver: str,
    amount: int,
    fee: AlgoAmount,
) -> None:
    transfer(
        client,
        asset_id,
        signer=holder,
        asset_sender=holder.address,
        asset_receiver=receiver,
        asset_amount=amount,
        fee=fee,
    )


def test_pass_up_to_cap(
    min_fee_2x: AlgoAmount,
    capped_client: CappedSmartAsaClient,
    capped_asa_id: int,
    holder: SigningAccount,
    receiver: SigningAccount,
) -> None:
    _regular_transfer(
        capped_client, capped_asa_id, holder, receiver.address, CAP, min_fee_2x
    )
    assert balance(capped_client, capped_asa_id, receiver) == CAP


def test_fail_above_cap(
    min_fee_2x: AlgoAmount,
    capped_client: CappedSmartAsaClient,
    capped_asa_id: int,
    holder: SigningAccount,
    receiver: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=capped_err.HOLDING_CAP_EXCEEDED):
        _regular_transfer(
            capped_client, capped_asa_id, holder, receiver.address, CAP + 1, min_fee_2x
        )


def test_fail_built_in_checks_first(
    min_fee_2x: AlgoAmount,
    capped_client: CappedSmartAsaClient,
    capped_asa_id: int,
    freeze: SigningAccount,
    holder: SigningAccount,
    receiver: SigningAccount,
) -> None:
    # The reference checks still apply, before the hook
    account_freeze(capped_client, capped_asa_id, freeze, holder.address)
    with pytest.raises(LogicError, match=err.SENDER_FROZEN):
        _regular_transfer(
            capped_client, capped_asa_id, holder, receiver.address, CAP + 1, min_fee_2x
        )


def test_pass_zero_between_non_holders(
    min_fee_2x: AlgoAmount,
    capped_client: CappedSmartAsaClient,
    capped_asa_id: int,
    creator: SigningAccount,
    eve: SigningAccount,
) -> None:
    # The hook reads holdings without failing on non-holders, as native ASA allows
    _regular_transfer(capped_client, capped_asa_id, eve, creator.address, 0, min_fee_2x)


def test_pass_other_paths_skip_hook(
    min_fee_2x: AlgoAmount,
    capped_client: CappedSmartAsaClient,
    capped_asa_id: int,
    reserve: SigningAccount,
    clawback: SigningAccount,
    holder: SigningAccount,
) -> None:
    # Issued above the cap (see the `holder` fixture), clawed back above the cap, and
    # redeemed by the Reserve: the hook only runs on regular transfers
    assert balance(capped_client, capped_asa_id, holder) == 2 * CAP
    transfer(
        capped_client,
        capped_asa_id,
        signer=clawback,
        asset_sender=holder.address,
        asset_receiver=reserve.address,
        asset_amount=2 * CAP,
        fee=min_fee_2x,
    )
    assert balance(capped_client, capped_asa_id, reserve) == 2 * CAP
    transfer(
        capped_client,
        capped_asa_id,
        signer=reserve,
        asset_sender=reserve.address,
        asset_receiver=capped_client.app_address,
        asset_amount=2 * CAP,
        fee=min_fee_2x,
    )
    assert balance(capped_client, capped_asa_id, reserve) == 0


def test_error_code_is_distinct() -> None:
    # Extension codes follow ARC-65 and never shadow the reference ones
    code = capped_err.HOLDING_CAP_EXCEEDED
    reference = [value for name, value in vars(err).items() if name.isupper()]
    assert re.fullmatch(r"[a-z][A-Za-z0-9]*", code)
    assert len(f"ERR:{code}") not in (8, 32)
    assert not [r for r in reference if code.startswith(r) or r.startswith(code)]
