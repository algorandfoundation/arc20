import pytest
from algokit_utils import LogicError, SigningAccount

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import SmartAsaClient
from tests.support import global_freeze


def test_pass_global_frozen(
    smart_asa_client: SmartAsaClient, smart_asa_id: int, freeze: SigningAccount
) -> None:
    assert not smart_asa_client.state.global_state.global_frozen
    global_freeze(smart_asa_client, smart_asa_id, freeze)
    assert smart_asa_client.state.global_state.global_frozen


def test_fail_unauthorized(
    smart_asa_client: SmartAsaClient, smart_asa_id: int, eve: SigningAccount
) -> None:
    with pytest.raises(LogicError, match=err.UNAUTHORIZED_FREEZE):
        global_freeze(smart_asa_client, smart_asa_id, eve)
