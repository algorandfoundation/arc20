import re
from collections.abc import Callable
from dataclasses import replace

import pytest
from algokit_utils import AlgoAmount, CommonAppCallParams, LogicError, SigningAccount
from algosdk.constants import ZERO_ADDRESS

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AssetConfigArgs,
    SmartAsaClient,
)
from tests.conftest import SmartASAConfig
from tests.support import BOTH_DEFAULT_FROZEN, DEFAULT_FROZEN, balance, transfer

NEW_ASA_CONFIG = SmartASAConfig(
    total=42,
    decimals=69,
    default_frozen=False,
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
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    manager: SigningAccount,
    asa_config: SmartASAConfig,
) -> None:
    # As for native ASA, a new `default_frozen` is ignored (set on creation only)
    new_config = replace(NEW_ASA_CONFIG, default_frozen=not asa_config.default_frozen)
    smart_asa_client.send.asset_config(
        AssetConfigArgs(
            config_asset=smart_asa_id,
            **new_config.dictify(),
        ),
        params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
    )

    state = smart_asa_client.state.global_state

    assert state.total == new_config.total
    assert state.decimals == new_config.decimals
    assert state.default_frozen == asa_config.default_frozen
    assert state.unit_name == new_config.unit_name
    assert state.name == new_config.name
    assert state.url == new_config.url
    assert state.metadata_hash == new_config.metadata_hash
    assert state.manager_addr == new_config.manager_addr
    assert state.reserve_addr == new_config.reserve_addr
    assert state.freeze_addr == new_config.freeze_addr
    assert state.clawback_addr == new_config.clawback_addr


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
    account_with_supply: SigningAccount,  # Issues the whole total
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


@DEFAULT_FROZEN
def test_pass_soulbound(
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    manager: SigningAccount,
    reserve: SigningAccount,
    clawback: SigningAccount,
    asa_config: SmartASAConfig,
    opted_in_account_factory: Callable[[], SigningAccount],
) -> None:
    # Created default frozen, then Freeze disabled: holdings are frozen forever
    asa_config.freeze_addr = ZERO_ADDRESS
    smart_asa_client.send.asset_config(
        AssetConfigArgs(config_asset=smart_asa_id, **asa_config.dictify()),
        params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
    )
    holder = opted_in_account_factory()
    with pytest.raises(LogicError, match=err.RECEIVER_FROZEN):
        transfer(
            smart_asa_client,
            smart_asa_id,
            signer=reserve,
            asset_sender=smart_asa_client.app_address,
            asset_receiver=holder.address,
            asset_amount=1,
        )

    # Issuance: the Reserve (approved before) issues to itself, the Clawback delivers
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
