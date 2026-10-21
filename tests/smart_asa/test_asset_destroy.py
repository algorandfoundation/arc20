import pytest
from algokit_utils import AlgoAmount, CommonAppCallParams, LogicError, SigningAccount
from algosdk.error import AlgodHTTPError

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AssetDestroyArgs,
    SmartAsaClient,
)


def test_pass_destroy(
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    manager: SigningAccount,
) -> None:
    smart_asa_client.send.delete.asset_destroy(
        AssetDestroyArgs(destroy_asset=smart_asa_id),
        params=CommonAppCallParams(
            static_fee=min_fee_2x,
            signer=manager.signer,
            sender=manager.address,
        ),
    )
    algod = smart_asa_client.algorand.client.algod
    with pytest.raises(AlgodHTTPError, match="application does not exist"):
        algod.application_info(smart_asa_client.app_id)
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
