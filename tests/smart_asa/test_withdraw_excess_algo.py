import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import SmartAsaClient
from tests.support import account_freeze


def _withdraw(client: SmartAsaClient, signer: SigningAccount, fee: AlgoAmount) -> None:
    client.send.withdraw_excess_algo(
        params=CommonAppCallParams(
            static_fee=fee,  # Payment to the Manager
            sender=signer.address,
            signer=signer.signer,
        )
    )


def test_pass_withdraw_excess_algo(
    algorand: AlgorandClient,
    min_fee_2x: AlgoAmount,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    manager: SigningAccount,
    freeze: SigningAccount,
    receiver: SigningAccount,
) -> None:
    algod = algorand.client.algod
    app = smart_asa_client.app_address
    # A box keeps its MBR in the App
    account_freeze(smart_asa_client, smart_asa_id, freeze, receiver.address)
    app_info = algod.account_info(app)
    excess = app_info["amount"] - app_info["min-balance"]
    manager_balance = algod.account_info(manager.address)["amount"]

    _withdraw(smart_asa_client, manager, min_fee_2x)

    app_info = algod.account_info(app)
    assert app_info["amount"] == app_info["min-balance"]
    assert app_info["total-boxes"] == 1
    assert (
        algod.account_info(manager.address)["amount"]
        == manager_balance + excess - min_fee_2x.micro_algo
    )


def test_fail_unauthorized_manager(
    min_fee_2x: AlgoAmount, smart_asa_client: SmartAsaClient, eve: SigningAccount
) -> None:
    with pytest.raises(LogicError, match=err.UNAUTHORIZED_MANAGER):
        _withdraw(smart_asa_client, eve, min_fee_2x)


def test_fail_before_asset_create(
    min_fee_2x: AlgoAmount,
    smart_asa_client_no_asset: SmartAsaClient,
    creator: SigningAccount,
) -> None:
    # The Manager is set on creation: before it, nobody can withdraw
    with pytest.raises(LogicError, match=err.UNAUTHORIZED_MANAGER):
        _withdraw(smart_asa_client_no_asset, creator, min_fee_2x)
