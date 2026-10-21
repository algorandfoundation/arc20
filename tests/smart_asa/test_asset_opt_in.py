import pytest
from algokit_utils import (
    AlgorandClient,
    AppClientMethodCallParams,
    AssetOptInParams,
    AssetTransferParams,
    LogicError,
    SigningAccount,
)
from algosdk import transaction
from algosdk.abi import Method
from algosdk.atomic_transaction_composer import TransactionWithSigner
from algosdk.error import AlgodHTTPError

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AssetOptInArgs,
    SmartAsaClient,
)
from tests.conftest import SmartASAConfig
from tests.support import ASSERT_FAILED, BOTH_DEFAULT_FROZEN, opt_in


@BOTH_DEFAULT_FROZEN
def test_pass_asset_opt_in(
    asa_config: SmartASAConfig,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    creator: SigningAccount,
) -> None:
    opt_in(smart_asa_client, smart_asa_id, creator)

    local_state = smart_asa_client.state.local_state(creator.address)
    assert local_state.account_smart_asa_id == smart_asa_id
    assert local_state.account_frozen == asa_config.default_frozen


def test_fail_missing_ctrl_asa(
    algorand: AlgorandClient,
    smart_asa_client_no_asset: SmartAsaClient,
    creator: SigningAccount,
    dummy_asa: int,
) -> None:
    with pytest.raises(LogicError, match=err.MISSING_CTRL_ASA):
        smart_asa_client_no_asset.send.opt_in.asset_opt_in(
            AssetOptInArgs(
                asset=dummy_asa,
                ctrl_asa_opt_in=TransactionWithSigner(
                    txn=algorand.create_transaction.asset_opt_in(
                        AssetOptInParams(sender=creator.address, asset_id=dummy_asa)
                    ),
                    signer=creator.signer,
                ),
            ),
        )


def test_fail_invalid_ctrl_asa(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    creator: SigningAccount,
    dummy_asa: int,
) -> None:
    with pytest.raises(LogicError, match=err.INVALID_CTRL_ASA):
        smart_asa_client.send.opt_in.asset_opt_in(
            AssetOptInArgs(
                asset=dummy_asa,
                ctrl_asa_opt_in=TransactionWithSigner(
                    txn=algorand.create_transaction.asset_opt_in(
                        AssetOptInParams(sender=creator.address, asset_id=smart_asa_id)
                    ),
                    signer=creator.signer,
                ),
            ),
        )


def test_fail_opt_in_wrong_type(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    creator: SigningAccount,
) -> None:
    # Built with the low level SDK: the ATC rejects a wrong txn type argument client-side
    sp = algorand.client.algod.suggested_params()
    payment = transaction.PaymentTxn(creator.address, sp, creator.address, 0)
    app_opt_in = transaction.ApplicationOptInTxn(
        creator.address,
        sp,
        smart_asa_client.app_id,
        app_args=[
            Method.from_signature("asset_opt_in(uint64,axfer)void").get_selector(),
            smart_asa_id.to_bytes(8, "big"),
        ],
        foreign_assets=[smart_asa_id],
    )
    group = transaction.assign_group_id([payment, app_opt_in])
    signed = creator.signer.sign_transactions(group, [0, 1])
    # Raw algod errors carry no source map: "transaction type is axfer" assertion
    with pytest.raises(AlgodHTTPError, match=ASSERT_FAILED):
        algorand.client.algod.send_transactions(signed)


def test_fail_opt_in_wrong_asa(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    creator: SigningAccount,
    dummy_asa: int,
) -> None:
    with pytest.raises(LogicError, match=err.OPT_IN_WRONG_ASA):
        smart_asa_client.send.opt_in.asset_opt_in(
            AssetOptInArgs(
                asset=smart_asa_id,
                ctrl_asa_opt_in=TransactionWithSigner(
                    txn=algorand.create_transaction.asset_opt_in(
                        AssetOptInParams(sender=creator.address, asset_id=dummy_asa)
                    ),
                    signer=creator.signer,
                ),
            ),
        )


def test_fail_opt_in_wrong_sender(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    eve: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=err.OPT_IN_WRONG_SENDER):
        smart_asa_client.send.opt_in.asset_opt_in(
            AssetOptInArgs(
                asset=smart_asa_id,
                ctrl_asa_opt_in=TransactionWithSigner(
                    txn=algorand.create_transaction.asset_opt_in(
                        AssetOptInParams(sender=eve.address, asset_id=smart_asa_id)
                    ),
                    signer=eve.signer,
                ),
            ),
        )


def test_fail_opt_in_wrong_receiver(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    creator: SigningAccount,
    eve: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=err.OPT_IN_WRONG_RECEIVER):
        smart_asa_client.send.opt_in.asset_opt_in(
            AssetOptInArgs(
                asset=smart_asa_id,
                ctrl_asa_opt_in=TransactionWithSigner(
                    txn=algorand.create_transaction.asset_transfer(
                        AssetTransferParams(
                            sender=creator.address,
                            asset_id=smart_asa_id,
                            receiver=eve.address,
                            amount=0,
                        )
                    ),
                    signer=creator.signer,
                ),
            ),
        )


# NOTE: Test opt-in with wrong amount skipped since the Controlled ASA is default frozen, any transfer > 0 would fail.


def test_fail_opt_in_forbidden_close_out(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    creator: SigningAccount,
) -> None:
    with pytest.raises(LogicError, match=err.OPT_IN_WRONG_CLOSE_TO):
        smart_asa_client.send.opt_in.asset_opt_in(
            AssetOptInArgs(
                asset=smart_asa_id,
                ctrl_asa_opt_in=TransactionWithSigner(
                    txn=algorand.create_transaction.asset_transfer(
                        AssetTransferParams(
                            sender=creator.address,
                            asset_id=smart_asa_id,
                            receiver=creator.address,
                            amount=0,
                            close_asset_to=smart_asa_client.app_address,
                        )
                    ),
                    signer=creator.signer,
                ),
            ),
        )


def test_fail_wrong_on_complete(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    creator: SigningAccount,
) -> None:
    # The ARC-4 router asserts the OnComplete action (no error message)
    with pytest.raises(LogicError, match=ASSERT_FAILED):
        smart_asa_client.app_client.send.call(
            AppClientMethodCallParams(
                method="asset_opt_in",
                args=[
                    smart_asa_id,
                    TransactionWithSigner(
                        txn=algorand.create_transaction.asset_opt_in(
                            AssetOptInParams(
                                sender=creator.address, asset_id=smart_asa_id
                            )
                        ),
                        signer=creator.signer,
                    ),
                ],
                on_complete=transaction.OnComplete.NoOpOC,
                sender=creator.address,
                signer=creator.signer,
            )
        )
