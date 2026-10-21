import pytest
from algokit_utils import LogicError

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    GetAssetConfigArgs,
    SmartAsaClient,
)
from tests.conftest import SmartASAConfig
from tests.support import BOTH_DEFAULT_FROZEN


@BOTH_DEFAULT_FROZEN
def test_pass_get_asset_config(
    asa_config: SmartASAConfig, smart_asa_client: SmartAsaClient, smart_asa_id: int
) -> None:
    config = smart_asa_client.send.get_asset_config(
        GetAssetConfigArgs(asset=smart_asa_id)
    ).abi_return
    assert config is not None
    assert config.total == asa_config.total
    assert config.decimals == asa_config.decimals
    assert config.default_frozen == asa_config.default_frozen
    assert config.unit_name == asa_config.unit_name
    assert config.name == asa_config.name
    assert config.url == asa_config.url
    assert bytes(config.metadata_hash) == asa_config.metadata_hash  # list[int]
    assert config.manager_addr == asa_config.manager_addr
    assert config.reserve_addr == asa_config.reserve_addr
    assert config.freeze_addr == asa_config.freeze_addr
    assert config.clawback_addr == asa_config.clawback_addr


def test_fail_missing_ctrl_asa(
    smart_asa_client_no_asset: SmartAsaClient, dummy_asa: int
) -> None:
    with pytest.raises(LogicError, match=err.MISSING_CTRL_ASA):
        smart_asa_client_no_asset.send.get_asset_config(
            GetAssetConfigArgs(asset=dummy_asa)
        )


def test_fail_invalid_ctrl_asa(
    smart_asa_client: SmartAsaClient, dummy_asa: int
) -> None:
    with pytest.raises(LogicError, match=err.INVALID_CTRL_ASA):
        smart_asa_client.send.get_asset_config(GetAssetConfigArgs(asset=dummy_asa))
