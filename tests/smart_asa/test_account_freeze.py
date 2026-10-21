import pytest
from algokit_utils import LogicError, SigningAccount

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import SmartAsaClient
from tests.conftest import SmartASAConfig
from tests.support import BOTH_DEFAULT_FROZEN, NOT_OPTED_IN, UNREACHABLE, account_freeze


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
    assert (
        smart_asa_client.state.local_state(receiver.address).account_frozen
        != asa_config.default_frozen
    )


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


def test_fail_not_opted_in(
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    eve: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=NOT_OPTED_IN):
        account_freeze(smart_asa_client, smart_asa_id, freeze, eve.address)


@pytest.mark.skip(reason=UNREACHABLE)
def test_fail_invalid_current_ctrl_asa() -> None:
    pass
