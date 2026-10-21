import pytest
from algokit_utils import LogicError, SigningAccount

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    GetAssetIsFrozenArgs,
    SmartAsaClient,
)
from tests.support import global_freeze


def test_pass_get_asset_is_frozen(
    smart_asa_client: SmartAsaClient, smart_asa_id: int, freeze: SigningAccount
) -> None:
    args = GetAssetIsFrozenArgs(freeze_asset=smart_asa_id)
    assert not smart_asa_client.send.get_asset_is_frozen(args).abi_return

    global_freeze(smart_asa_client, smart_asa_id, freeze)
    assert smart_asa_client.send.get_asset_is_frozen(args).abi_return


def test_fail_invalid_ctrl_asa(
    smart_asa_client: SmartAsaClient, dummy_asa: int
) -> None:
    with pytest.raises(LogicError, match=err.INVALID_CTRL_ASA):
        smart_asa_client.send.get_asset_is_frozen(
            GetAssetIsFrozenArgs(freeze_asset=dummy_asa)
        )
