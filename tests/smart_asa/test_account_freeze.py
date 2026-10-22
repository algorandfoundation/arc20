import pytest
from algokit_utils import LogicError, SigningAccount

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    GetAccountIsFrozenArgs,
    SmartAsaClient,
)
from tests.conftest import SmartASAConfig
from tests.support import BOTH_DEFAULT_FROZEN, account_freeze


@BOTH_DEFAULT_FROZEN
def test_pass_change_account_frozen(
    asa_config: SmartASAConfig,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    receiver: SigningAccount,
) -> None:
    account_freeze(
        smart_asa_client,
        smart_asa_id,
        freeze,
        receiver.address,
        frozen=not asa_config.default_frozen,
    )
    assert smart_asa_client.send.get_account_is_frozen(
        GetAccountIsFrozenArgs(
            freeze_asset=smart_asa_id, freeze_account=receiver.address
        )
    ).abi_return == (not asa_config.default_frozen)


def test_fail_unauthorized(
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    eve: SigningAccount,
    receiver: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=err.UNAUTHORIZED_FREEZE):
        account_freeze(smart_asa_client, smart_asa_id, eve, receiver.address)


def test_fail_invalid_ctrl_asa(
    smart_asa_client: SmartAsaClient,
    freeze: SigningAccount,
    receiver: SigningAccount,
    dummy_asa: int,
) -> None:
    with pytest.raises(LogicError, match=err.INVALID_CTRL_ASA):
        account_freeze(smart_asa_client, dummy_asa, freeze, receiver.address)
