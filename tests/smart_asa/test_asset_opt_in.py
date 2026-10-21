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


def test_pass_asset_opt_in(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    creator: SigningAccount,
) -> None:
    state = smart_asa_client.state.global_state
    smart_asa_id = state.smart_asa_id
    smart_asa_client.send.opt_in.asset_opt_in(
        AssetOptInArgs(
            asset=smart_asa_id,
            ctrl_asa_opt_in=TransactionWithSigner(
                txn=algorand.create_transaction.asset_opt_in(
                    AssetOptInParams(sender=creator.address, asset_id=smart_asa_id)
                ),
                signer=creator.signer,
            ),
        ),
    )

    local_state = smart_asa_client.state.local_state(creator.address)
    assert local_state.account_smart_asa_id == smart_asa_id
    if state.default_frozen:
        assert local_state.account_frozen
    else:
        assert not local_state.account_frozen


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
    creator: SigningAccount,
    dummy_asa: int,
) -> None:
    smart_asa_id = smart_asa_client.state.global_state.smart_asa_id
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
    algorand: AlgorandClient, smart_asa_client: SmartAsaClient, creator: SigningAccount
) -> None:
    # Built with the low level SDK: the ATC rejects a wrong txn type argument client-side
    smart_asa_id = smart_asa_client.state.global_state.smart_asa_id
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
    with pytest.raises(AlgodHTTPError, match="assert failed"):
        algorand.client.algod.send_transactions(signed)


def test_fail_opt_in_wrong_asa(
    algorand: AlgorandClient,
    smart_asa_client: SmartAsaClient,
    creator: SigningAccount,
    dummy_asa: int,
) -> None:
    smart_asa_id = smart_asa_client.state.global_state.smart_asa_id
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
    eve: SigningAccount,
) -> None:
    smart_asa_id = smart_asa_client.state.global_state.smart_asa_id
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
    creator: SigningAccount,
    eve: SigningAccount,
) -> None:
    smart_asa_id = smart_asa_client.state.global_state.smart_asa_id
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
    creator: SigningAccount,
) -> None:
    smart_asa_id = smart_asa_client.state.global_state.smart_asa_id
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
    creator: SigningAccount,
) -> None:
    smart_asa_id = smart_asa_client.state.global_state.smart_asa_id
    # The ARC-4 router asserts the OnComplete action (no error message)
    with pytest.raises(LogicError, match="assert failed"):
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
