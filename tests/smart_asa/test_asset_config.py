import re

import pytest
from algokit_utils import CommonAppCallParams, LogicError, SigningAccount
from algosdk.constants import ZERO_ADDRESS

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AssetConfigArgs,
    SmartAsaClient,
)
from tests.conftest import SmartASAConfig
from tests.support import BOTH_DEFAULT_FROZEN

NEW_ASA_CONFIG = SmartASAConfig(
    total=42,
    decimals=69,
    default_frozen=True,
    unit_name="FOO",
    name="Foo Asset",
    url="ipfs://<new-asa-metadata-uri>",
    metadata_hash=(420).to_bytes(length=32),
    manager_addr=ZERO_ADDRESS,
    reserve_addr=ZERO_ADDRESS,
    freeze_addr=ZERO_ADDRESS,
    clawback_addr=ZERO_ADDRESS,
)


@BOTH_DEFAULT_FROZEN
def test_pass_asset_config(
    smart_asa_client: SmartAsaClient, smart_asa_id: int, manager: SigningAccount
) -> None:
    smart_asa_client.send.asset_config(
        AssetConfigArgs(
            config_asset=smart_asa_id,
            **NEW_ASA_CONFIG.dictify(),
        ),
        params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
    )

    state = smart_asa_client.state.global_state

    assert state.total == NEW_ASA_CONFIG.total
    assert state.decimals == NEW_ASA_CONFIG.decimals
    assert state.default_frozen == NEW_ASA_CONFIG.default_frozen
    assert state.unit_name == NEW_ASA_CONFIG.unit_name
    assert state.name == NEW_ASA_CONFIG.name
    assert state.url == NEW_ASA_CONFIG.url
    assert state.metadata_hash == NEW_ASA_CONFIG.metadata_hash
    assert state.manager_addr == NEW_ASA_CONFIG.manager_addr
    assert state.reserve_addr == NEW_ASA_CONFIG.reserve_addr
    assert state.freeze_addr == NEW_ASA_CONFIG.freeze_addr
    assert state.clawback_addr == NEW_ASA_CONFIG.clawback_addr


def test_fail_missing_ctrl_asa(
    smart_asa_client_no_asset: SmartAsaClient, manager: SigningAccount, dummy_asa: int
) -> None:
    with pytest.raises(LogicError, match=err.MISSING_CTRL_ASA):
        smart_asa_client_no_asset.send.asset_config(
            AssetConfigArgs(
                config_asset=dummy_asa,
                **NEW_ASA_CONFIG.dictify(),
            ),
            params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
        )


def test_fail_invalid_ctrl_asa(
    smart_asa_client: SmartAsaClient, manager: SigningAccount, dummy_asa: int
) -> None:
    with pytest.raises(LogicError, match=err.INVALID_CTRL_ASA):
        smart_asa_client.send.asset_config(
            AssetConfigArgs(
                config_asset=dummy_asa,
                **NEW_ASA_CONFIG.dictify(),
            ),
            params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
        )


def test_fail_unauthorized_manager(
    smart_asa_client: SmartAsaClient, smart_asa_id: int
) -> None:
    with pytest.raises(LogicError, match=err.UNAUTHORIZED_MANAGER):
        smart_asa_client.send.asset_config(
            AssetConfigArgs(
                config_asset=smart_asa_id,
                **NEW_ASA_CONFIG.dictify(),
            ),
        )


def test_fail_disabled_roles(
    smart_asa_client: SmartAsaClient, smart_asa_id: int, manager: SigningAccount
) -> None:
    asa_config = NEW_ASA_CONFIG.dictify()
    asa_config["manager_addr"] = manager.address

    smart_asa_client.send.asset_config(
        AssetConfigArgs(
            config_asset=smart_asa_id,
            **asa_config,
        ),
        params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
    )

    asa_config["reserve_addr"] = smart_asa_client.app_address
    with pytest.raises(LogicError, match=err.DISABLED_RESERVE):
        smart_asa_client.send.asset_config(
            AssetConfigArgs(
                config_asset=smart_asa_id,
                **asa_config,
            ),
            params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
        )
    asa_config["reserve_addr"] = NEW_ASA_CONFIG.reserve_addr

    asa_config["freeze_addr"] = smart_asa_client.app_address
    with pytest.raises(LogicError, match=err.DISABLED_FREEZE):
        smart_asa_client.send.asset_config(
            AssetConfigArgs(
                config_asset=smart_asa_id,
                **asa_config,
            ),
            params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
        )
    asa_config["freeze_addr"] = NEW_ASA_CONFIG.freeze_addr

    asa_config["clawback_addr"] = smart_asa_client.app_address
    with pytest.raises(LogicError, match=err.DISABLED_CLAWBACK):
        smart_asa_client.send.asset_config(
            AssetConfigArgs(
                config_asset=smart_asa_id,
                **asa_config,
            ),
            params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
        )


def test_fail_invalid_total(
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    manager: SigningAccount,
    asa_config: SmartASAConfig,
    account_with_supply: SigningAccount,  # Mints the whole total
) -> None:
    asa_config.total -= 1  # Below the circulating supply
    with pytest.raises(LogicError, match=re.escape(err.INVALID_TOTAL)):
        smart_asa_client.send.asset_config(
            AssetConfigArgs(
                config_asset=smart_asa_id,
                **asa_config.dictify(),
            ),
            params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
        )
