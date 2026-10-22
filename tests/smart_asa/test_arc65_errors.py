from algokit_utils import (
    AlgorandClient,
    AppClientMethodCallParams,
    CommonAppCallParams,
    SigningAccount,
)
from algosdk.transaction import OnComplete

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AssetConfigArgs,
    AssetTransferArgs,
    GetAssetConfigArgs,
    SmartAsaClient,
)
from tests.conftest import SmartASAConfig
from tests.support import account_freeze, arc65_errors, global_freeze


def test_fail_method_logs_arc65_error(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    eve: SigningAccount,
    asa_config: SmartASAConfig,
) -> None:
    composer = (
        smart_asa_client.new_group()
        .asset_config(
            AssetConfigArgs(config_asset=smart_asa_id, **asa_config.dictify()),
            params=CommonAppCallParams(sender=eve.address),
        )
        .composer()
    )
    assert arc65_errors(algorand, composer) == [f"ERR:{err.UNAUTHORIZED_MANAGER}"]


def test_fail_readonly_logs_arc65_error(
    algorand: AlgorandClient, smart_asa_client: SmartAsaClient, dummy_asa: int
) -> None:
    composer = (
        smart_asa_client.new_group()
        .get_asset_config(GetAssetConfigArgs(asset=dummy_asa))
        .composer()
    )
    assert arc65_errors(algorand, composer) == [f"ERR:{err.INVALID_CTRL_ASA}"]


def test_fail_transfer_logs_arc65_error(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
) -> None:
    global_freeze(smart_asa_client, smart_asa_id, freeze)
    composer = (
        smart_asa_client.new_group()
        .asset_transfer(
            AssetTransferArgs(
                xfer_asset=smart_asa_id,
                asset_amount=1,
                asset_sender=account_with_supply.address,
                asset_receiver=receiver.address,
            ),
            params=CommonAppCallParams(sender=account_with_supply.address),
        )
        .composer()
    )
    assert arc65_errors(algorand, composer) == [f"ERR:{err.GLOBAL_FROZEN}"]


def test_fail_account_freeze_logs_arc65_error(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    freeze: SigningAccount,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
) -> None:
    account_freeze(smart_asa_client, smart_asa_id, freeze, receiver.address)
    composer = (
        smart_asa_client.new_group()
        .asset_transfer(
            AssetTransferArgs(
                xfer_asset=smart_asa_id,
                asset_amount=1,
                asset_sender=account_with_supply.address,
                asset_receiver=receiver.address,
            ),
            params=CommonAppCallParams(sender=account_with_supply.address),
        )
        .composer()
    )
    assert arc65_errors(algorand, composer) == [f"ERR:{err.RECEIVER_FROZEN}"]


def test_fail_compiler_check_logs_no_arc65_error(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    account_with_supply: SigningAccount,
    receiver: SigningAccount,
) -> None:
    # Compiler-generated checks (here, the ARC-4 router OnComplete) fail without logs
    composer = algorand.new_group().add_app_call_method_call(
        smart_asa_client.app_client.params.call(
            AppClientMethodCallParams(
                method="asset_transfer",
                args=[smart_asa_id, 1, account_with_supply.address, receiver.address],
                on_complete=OnComplete.OptInOC,
                sender=account_with_supply.address,
            )
        )
    )
    assert arc65_errors(algorand, composer) == []
