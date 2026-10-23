import pytest
from algokit_utils import AlgoAmount, CommonAppCallParams, LogicError, SigningAccount
from algosdk.constants import ZERO_ADDRESS
from algosdk.error import AlgodHTTPError

import smart_contracts.errors as err
import smart_contracts.smart_asa.config as cfg
from smart_contracts.artifacts.arc89_smart_asa.arc89_smart_asa_client import (
    Arc62GetCirculatingSupplyArgs,
    Arc89SmartAsaClient,
    AssetConfigArgs,
    AssetDestroyArgs,
)
from tests.conftest import SmartASAConfig
from tests.support import circulating_supply, funded_account, opt_in, transfer


def _holding(client: Arc89SmartAsaClient, address: str, asset_id: int) -> int:
    try:
        info = client.algorand.asset.get_account_information(address, asset_id)
    except AlgodHTTPError:  # Not opted in
        return 0
    return info.balance


def _circulating_supply(client: Arc89SmartAsaClient, asset_id: int) -> int | None:
    # The ARC-20 and ARC-62 getters agree, and match the definition from the chain
    # state: the issued supply minus the Reserve holding, subtracted once, and only if
    # the Reserve is neither disabled nor the App (which holds the units not issued)
    arc62 = client.send.arc62_get_circulating_supply(
        Arc62GetCirculatingSupplyArgs(asset_id=asset_id)
    ).abi_return
    assert arc62 == circulating_supply(client, asset_id)
    issued = cfg.TOTAL - _holding(client, client.app_address, asset_id)
    reserve = client.state.global_state.reserve_addr
    excluded = (
        0
        if reserve in (ZERO_ADDRESS, client.app_address)
        else _holding(client, reserve, asset_id)
    )
    assert arc62 == issued - excluded
    assert arc62 is not None and 0 <= arc62 <= issued
    return arc62


def _issue(
    client: Arc89SmartAsaClient,
    asset_id: int,
    reserve: SigningAccount,
    receiver: str,
    amount: int,
    fee: AlgoAmount,
) -> None:
    transfer(
        client,
        asset_id,
        signer=reserve,
        asset_sender=client.app_address,
        asset_receiver=receiver,
        asset_amount=amount,
        fee=fee,
    )


def test_pass_no_circulating_supply(
    arc89_smart_asa_client: Arc89SmartAsaClient, smart_asa_id: int
) -> None:
    assert _circulating_supply(arc89_smart_asa_client, smart_asa_id) == 0


def test_pass_reserve_holdings_excluded(
    min_fee_2x: AlgoAmount,
    arc89_smart_asa_client: Arc89SmartAsaClient,
    smart_asa_id: int,
    reserve: SigningAccount,
) -> None:
    # Issued to a holder: circulating. Issued to the Reserve (a treasury): not
    holder = funded_account(arc89_smart_asa_client.algorand)
    opt_in(arc89_smart_asa_client, smart_asa_id, holder)
    opt_in(arc89_smart_asa_client, smart_asa_id, reserve)
    _issue(
        arc89_smart_asa_client, smart_asa_id, reserve, holder.address, 30, min_fee_2x
    )
    _issue(
        arc89_smart_asa_client, smart_asa_id, reserve, reserve.address, 40, min_fee_2x
    )
    assert _circulating_supply(arc89_smart_asa_client, smart_asa_id) == 30


def test_fail_total_caps_issued_supply(
    min_fee_2x: AlgoAmount,
    arc89_smart_asa_client: Arc89SmartAsaClient,
    smart_asa_id: int,
    reserve_with_supply: SigningAccount,
    manager: SigningAccount,
) -> None:
    # The Reserve holds the whole total: none circulates, yet all is issued
    client = arc89_smart_asa_client
    assert _circulating_supply(client, smart_asa_id) == 0
    with pytest.raises(LogicError, match=err.OVER_ISSUE):
        _issue(
            client,
            smart_asa_id,
            reserve_with_supply,
            reserve_with_supply.address,
            1,
            min_fee_2x,
        )
    with pytest.raises(LogicError, match=err.UNITS_ISSUED):
        client.send.delete.asset_destroy(
            AssetDestroyArgs(destroy_asset=smart_asa_id),
            params=CommonAppCallParams(
                static_fee=min_fee_2x, signer=manager.signer, sender=manager.address
            ),
        )


@pytest.mark.parametrize("new_reserve", ["disabled", "app", "not opted in"])
def test_pass_reserve_reassigned(
    min_fee_2x: AlgoAmount,
    arc89_smart_asa_client: Arc89SmartAsaClient,
    smart_asa_id: int,
    arc89_asa_config: SmartASAConfig,
    reserve_with_supply: SigningAccount,
    manager: SigningAccount,
    new_reserve: str,
) -> None:
    # Without a Reserve holding units, the circulating supply is the issued one
    client = arc89_smart_asa_client
    arc89_asa_config.reserve_addr = {
        "disabled": ZERO_ADDRESS,
        "app": client.app_address,
        "not opted in": funded_account(client.algorand).address,
    }[new_reserve]
    client.send.asset_config(
        AssetConfigArgs(config_asset=smart_asa_id, **arc89_asa_config.dictify()),
        params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
    )
    assert _circulating_supply(client, smart_asa_id) == arc89_asa_config.total


def test_pass_reserve_is_clawback(
    min_fee_2x: AlgoAmount,
    arc89_smart_asa_client: Arc89SmartAsaClient,
    smart_asa_id: int,
    arc89_asa_config: SmartASAConfig,
    manager: SigningAccount,
    reserve: SigningAccount,
) -> None:
    # One account with both roles: the units it claws back are excluded once
    client = arc89_smart_asa_client
    arc89_asa_config.clawback_addr = reserve.address
    client.send.asset_config(
        AssetConfigArgs(config_asset=smart_asa_id, **arc89_asa_config.dictify()),
        params=CommonAppCallParams(sender=manager.address, signer=manager.signer),
    )
    holder = funded_account(client.algorand)
    opt_in(client, smart_asa_id, holder)
    opt_in(client, smart_asa_id, reserve)
    _issue(client, smart_asa_id, reserve, holder.address, 30, min_fee_2x)
    transfer(
        client,
        smart_asa_id,
        signer=reserve,
        asset_sender=holder.address,
        asset_receiver=reserve.address,
        asset_amount=10,
        fee=min_fee_2x,
    )
    assert _circulating_supply(client, smart_asa_id) == 20
