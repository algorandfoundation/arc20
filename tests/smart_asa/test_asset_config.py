import re
from collections.abc import Callable

import pytest
from algokit_utils import AlgoAmount, CommonAppCallParams, LogicError, SigningAccount
from algosdk.constants import ZERO_ADDRESS

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AssetConfigArgs,
    SmartAsaClient,
)
from tests.conftest import SmartASAConfig
from tests.support import BOTH_DEFAULT_FROZEN, balance, transfer

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


@pytest.mark.parametrize("hash_length", [0, 31, 33])
def test_fail_invalid_metadata_hash_length(
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    manager: SigningAccount,
    asa_config: SmartASAConfig,
    hash_length: int,
) -> None:
    asa_config.metadata_hash = b"\x00" * hash_length
    with pytest.raises(LogicError, match=err.INVALID_METADATA_HASH_LENGTH):
        smart_asa_client.send.asset_config(
            AssetConfigArgs(config_asset=smart_asa_id, **asa_config.dictify()),
            params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
        )


def test_fail_default_frozen_after_freeze_disabled(
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    manager: SigningAccount,
    asa_config: SmartASAConfig,
) -> None:
    asa_config.freeze_addr = ZERO_ADDRESS
    smart_asa_client.send.asset_config(
        AssetConfigArgs(config_asset=smart_asa_id, **asa_config.dictify()),
        params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
    )

    # A disabled Freeze leaves the freeze settings as they are
    asa_config.default_frozen = True
    with pytest.raises(LogicError, match=err.DISABLED_FREEZE):
        smart_asa_client.send.asset_config(
            AssetConfigArgs(config_asset=smart_asa_id, **asa_config.dictify()),
            params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
        )


def test_pass_disable_freeze_and_set_default_frozen(
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    manager: SigningAccount,
    reserve: SigningAccount,
    clawback: SigningAccount,
    asa_config: SmartASAConfig,
    opted_in_account_factory: Callable[[], SigningAccount],
) -> None:
    # Soulbound: holdings frozen forever, only the Clawback can move them
    asa_config.freeze_addr = ZERO_ADDRESS
    asa_config.default_frozen = True
    smart_asa_client.send.asset_config(
        AssetConfigArgs(config_asset=smart_asa_id, **asa_config.dictify()),
        params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
    )
    state = smart_asa_client.state.global_state
    assert state.freeze_addr == ZERO_ADDRESS
    assert state.default_frozen

    holder = opted_in_account_factory()  # Opts in frozen, forever
    with pytest.raises(LogicError, match=err.RECEIVER_FROZEN):
        transfer(
            smart_asa_client,
            smart_asa_id,
            signer=reserve,
            asset_sender=smart_asa_client.app_address,
            asset_receiver=holder.address,
            asset_amount=1,
        )

    # Issuance: the Reserve mints to itself, then the Clawback delivers
    transfer(
        smart_asa_client,
        smart_asa_id,
        signer=reserve,
        asset_sender=smart_asa_client.app_address,
        asset_receiver=reserve.address,
        asset_amount=1,
        fee=min_fee_2x,
    )
    transfer(
        smart_asa_client,
        smart_asa_id,
        signer=clawback,
        asset_sender=reserve.address,
        asset_receiver=holder.address,
        asset_amount=1,
        fee=min_fee_2x,
    )
    assert balance(smart_asa_client, smart_asa_id, holder) == 1
