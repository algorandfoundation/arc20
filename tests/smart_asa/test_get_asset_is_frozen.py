import pytest
from algokit_utils import CommonAppCallParams, LogicError, SigningAccount

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AssetFreezeArgs,
    GetAssetIsFrozenArgs,
    SmartAsaClient,
)


@pytest.mark.parametrize("asa_config", [False], indirect=True)
def test_pass_get_asset_is_frozen(
    smart_asa_client: SmartAsaClient, freeze: SigningAccount
) -> None:
    smart_asa_id = smart_asa_client.state.global_state.smart_asa_id
    args = GetAssetIsFrozenArgs(freeze_asset=smart_asa_id)
    assert not smart_asa_client.send.get_asset_is_frozen(args).abi_return

    smart_asa_client.send.asset_freeze(
        AssetFreezeArgs(freeze_asset=smart_asa_id, asset_frozen=True),
        params=CommonAppCallParams(signer=freeze.signer, sender=freeze.address),
    )
    assert smart_asa_client.send.get_asset_is_frozen(args).abi_return


def test_fail_invalid_ctrl_asa(
    smart_asa_client: SmartAsaClient, dummy_asa: int
) -> None:
    with pytest.raises(LogicError, match=err.INVALID_CTRL_ASA):
        smart_asa_client.send.get_asset_is_frozen(
            GetAssetIsFrozenArgs(freeze_asset=dummy_asa)
        )
