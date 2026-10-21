import pytest
from algokit_utils import CommonAppCallParams, LogicError, SigningAccount

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AccountFreezeArgs,
    GetAccountIsFrozenArgs,
    SmartAsaClient,
)


def test_pass_get_account_is_frozen(
    smart_asa_client: SmartAsaClient,
    freeze: SigningAccount,
    receiver: SigningAccount,
) -> None:
    smart_asa = smart_asa_client.state.global_state
    default_frozen = bool(smart_asa.default_frozen)
    args = GetAccountIsFrozenArgs(
        freeze_asset=smart_asa.smart_asa_id, freeze_account=receiver.address
    )
    assert (
        smart_asa_client.send.get_account_is_frozen(args).abi_return == default_frozen
    )

    smart_asa_client.send.account_freeze(
        AccountFreezeArgs(
            freeze_asset=smart_asa.smart_asa_id,
            freeze_account=receiver.address,
            asset_frozen=not default_frozen,
        ),
        params=CommonAppCallParams(signer=freeze.signer, sender=freeze.address),
    )
    assert smart_asa_client.send.get_account_is_frozen(args).abi_return == (
        not default_frozen
    )


def test_fail_invalid_ctrl_asa(
    smart_asa_client: SmartAsaClient, receiver: SigningAccount, dummy_asa: int
) -> None:
    with pytest.raises(LogicError, match=err.INVALID_CTRL_ASA):
        smart_asa_client.send.get_account_is_frozen(
            GetAccountIsFrozenArgs(
                freeze_asset=dummy_asa, freeze_account=receiver.address
            )
        )


def test_fail_not_opted_in(
    smart_asa_client: SmartAsaClient, eve: SigningAccount
) -> None:
    # Current behaviour: the getter fails instead of reporting a missing flag as frozen
    with pytest.raises(LogicError, match="cannot fetch key"):
        smart_asa_client.send.get_account_is_frozen(
            GetAccountIsFrozenArgs(
                freeze_asset=smart_asa_client.state.global_state.smart_asa_id,
                freeze_account=eve.address,
            )
        )
