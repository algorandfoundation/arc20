import pytest
from algokit_utils import LogicError, SigningAccount

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    GetAccountIsFrozenArgs,
    SmartAsaClient,
)
from tests.conftest import SmartASAConfig
from tests.support import BOTH_DEFAULT_FROZEN, NOT_OPTED_IN, account_freeze


@BOTH_DEFAULT_FROZEN
def test_pass_get_account_is_frozen(
    asa_config: SmartASAConfig,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    receiver: SigningAccount,
) -> None:
    args = GetAccountIsFrozenArgs(
        freeze_asset=smart_asa_id, freeze_account=receiver.address
    )
    frozen = asa_config.default_frozen
    assert smart_asa_client.send.get_account_is_frozen(args).abi_return == frozen

    account_freeze(
        smart_asa_client, smart_asa_id, freeze, receiver.address, frozen=not frozen
    )
    assert smart_asa_client.send.get_account_is_frozen(args).abi_return == (not frozen)


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
    smart_asa_client: SmartAsaClient, smart_asa_id: int, eve: SigningAccount
) -> None:
    # Current behaviour: the getter fails instead of reporting a missing flag as frozen
    with pytest.raises(LogicError, match=NOT_OPTED_IN):
        smart_asa_client.send.get_account_is_frozen(
            GetAccountIsFrozenArgs(
                freeze_asset=smart_asa_id, freeze_account=eve.address
            )
        )
