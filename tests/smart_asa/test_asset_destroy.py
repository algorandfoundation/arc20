import pytest
from algokit_utils import AlgoAmount, CommonAppCallParams, LogicError, SigningAccount
from algosdk.error import AlgodHTTPError

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AssetDestroyArgs,
    SmartAsaClient,
)
from tests.conftest import SmartASAConfig
from tests.support import claw_back_and_burn, clear_state


def _micro_algo(client: SmartAsaClient, address: str) -> int:
    return client.algorand.account.get_information(address).amount.micro_algo


def test_pass_destroy(
    min_fee_3x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    manager: SigningAccount,
) -> None:
    app_balance = _micro_algo(smart_asa_client, smart_asa_client.app_address)
    manager_balance = _micro_algo(smart_asa_client, manager.address)

    smart_asa_client.send.delete.asset_destroy(
        AssetDestroyArgs(destroy_asset=smart_asa_id),
        params=CommonAppCallParams(
            static_fee=min_fee_3x,  # Asset destroy and App account close
            signer=manager.signer,
            sender=manager.address,
        ),
    )
    algod = smart_asa_client.algorand.client.algod
    with pytest.raises(AlgodHTTPError, match="application does not exist"):
        algod.application_info(smart_asa_client.app_id)
    with pytest.raises(AlgodHTTPError, match="asset does not exist"):
        smart_asa_client.algorand.asset.get_by_id(smart_asa_id)

    # The App account is closed to the Manager, who paid the fees
    assert _micro_algo(smart_asa_client, smart_asa_client.app_address) == 0
    assert (
        _micro_algo(smart_asa_client, manager.address)
        == manager_balance + app_balance - min_fee_3x.micro_algo
    )


def test_pass_destroy_after_recovering_from_holder_without_local_state(
    min_fee_2x: AlgoAmount,
    min_fee_3x: AlgoAmount,
    asa_config: SmartASAConfig,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    manager: SigningAccount,
    reserve_and_clawback: SigningAccount,
    account_with_supply: SigningAccount,
) -> None:
    # A holder that cleared its App Local State can't block the destroy
    clear_state(smart_asa_client, account_with_supply)
    claw_back_and_burn(
        smart_asa_client,
        smart_asa_id,
        signer=reserve_and_clawback,
        holder=account_with_supply.address,
        asset_amount=asa_config.total,
        fee=min_fee_2x,
    )
    smart_asa_client.send.delete.asset_destroy(
        AssetDestroyArgs(destroy_asset=smart_asa_id),
        params=CommonAppCallParams(
            static_fee=min_fee_3x,
            signer=manager.signer,
            sender=manager.address,
        ),
    )
    with pytest.raises(AlgodHTTPError, match="asset does not exist"):
        smart_asa_client.algorand.asset.get_by_id(smart_asa_id)


def test_fail_missing_ctrl_asa(
    min_fee_2x: AlgoAmount,
    smart_asa_client_no_asset: SmartAsaClient,
    manager: SigningAccount,
    dummy_asa: int,
) -> None:
    with pytest.raises(LogicError, match=err.MISSING_CTRL_ASA):
        smart_asa_client_no_asset.send.delete.asset_destroy(
            AssetDestroyArgs(destroy_asset=dummy_asa),
            params=CommonAppCallParams(
                static_fee=min_fee_2x,
                signer=manager.signer,
                sender=manager.address,
            ),
        )


def test_fail_invalid_ctrl_asa(
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    manager: SigningAccount,
    dummy_asa: int,
) -> None:
    with pytest.raises(LogicError, match=err.INVALID_CTRL_ASA):
        smart_asa_client.send.delete.asset_destroy(
            AssetDestroyArgs(destroy_asset=dummy_asa),
            params=CommonAppCallParams(
                static_fee=min_fee_2x,
                signer=manager.signer,
                sender=manager.address,
            ),
        )


def test_fail_unauthorized_manager(
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    eve: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=err.UNAUTHORIZED_MANAGER):
        smart_asa_client.send.delete.asset_destroy(
            AssetDestroyArgs(destroy_asset=smart_asa_id),
            params=CommonAppCallParams(
                static_fee=min_fee_2x,
                signer=eve.signer,
                sender=eve.address,
            ),
        )


def test_fail_still_in_circulation(
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    manager: SigningAccount,
    account_with_supply: SigningAccount,  # To have circulating supply
) -> None:
    with pytest.raises(LogicError, match="creator is holding only"):
        smart_asa_client.send.delete.asset_destroy(
            AssetDestroyArgs(destroy_asset=smart_asa_id),
            params=CommonAppCallParams(
                static_fee=min_fee_2x,
                signer=manager.signer,
                sender=manager.address,
            ),
        )
