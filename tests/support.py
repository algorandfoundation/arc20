"""Shared helpers for the Smart ASA test suite."""

import base64
from typing import Final

import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AssetOptInParams,
    CommonAppCallParams,
    PaymentParams,
    SigningAccount,
    TransactionComposer,
)
from algosdk.constants import MIN_TXN_FEE
from algosdk.transaction import SignedTransaction, Transaction
from algosdk.v2client.models import SimulateRequest, SimulateRequestTransactionGroup

import smart_contracts.smart_asa.config as cfg
from smart_contracts.artifacts.arc89_smart_asa.arc89_smart_asa_client import (
    Arc89SmartAsaClient,
    Arc89SmartAsaComposer,
)
from smart_contracts.artifacts.capped_smart_asa.capped_smart_asa_client import (
    CappedSmartAsaClient,
    CappedSmartAsaComposer,
)
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AccountFreezeArgs,
    AssetFreezeArgs,
    AssetTransferArgs,
    GetCirculatingSupplyArgs,
    SmartAsaClient,
    SmartAsaComposer,
)

# The generated clients share the ABI argument layouts, so the helpers accept all
AnySmartAsaClient = SmartAsaClient | Arc89SmartAsaClient | CappedSmartAsaClient
AnySmartAsaComposer = SmartAsaComposer | Arc89SmartAsaComposer | CappedSmartAsaComposer

INITIAL_FUNDS: Final[AlgoAmount] = AlgoAmount.from_algo(100)

# Expected failures of compiler-generated checks (no ARC-65 error)
ASSERT_FAILED: Final[str] = "assert failed"  # ARC-4 router checks and raw algod errors
APPROVAL_REJECTED: Final[str] = "rejected by ApprovalProgram"

# `asa_config` is not default frozen unless parametrized with these
BOTH_DEFAULT_FROZEN = pytest.mark.parametrize(
    "asa_config",
    [False, True],
    ids=["Not Default Frozen", "Default Frozen"],
    indirect=True,
)
DEFAULT_FROZEN = pytest.mark.parametrize(
    "asa_config", [True], ids=["Default Frozen"], indirect=True
)


def arc65_errors(algorand: AlgorandClient, composer: TransactionComposer) -> list[str]:
    """Simulates a failing group and returns the ARC-65 errors logged by its App calls."""
    signed_txns = [
        SignedTransaction(txn_with_signer.txn, None)
        for txn_with_signer in composer.build().atc.build_group()
    ]
    response = algorand.client.algod.simulate_transactions(
        SimulateRequest(
            txn_groups=[SimulateRequestTransactionGroup(txns=signed_txns)],
            allow_empty_signatures=True,
            allow_unnamed_resources=True,
        )
    )
    group = response["txn-groups"][0]
    assert group.get("failure-message"), "The group did not fail"
    logs = [
        base64.b64decode(log)
        for result in group["txn-results"]
        for log in result["txn-result"].get("logs", [])
    ]
    return [log.decode() for log in logs if log.startswith((b"ERR:", b"AER:"))]


def funded_account(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


def opt_in(client: AnySmartAsaClient, asset_id: int, account: SigningAccount) -> None:
    """Holders only opt in to the Controlled ASA (no App opt-in)."""
    client.algorand.send.asset_opt_in(
        AssetOptInParams(
            asset_id=asset_id, sender=account.address, signer=account.signer
        )
    )


def add_transfer(
    composer: AnySmartAsaComposer,
    asset_id: int,
    *,
    signer: SigningAccount,
    asset_sender: str,
    asset_receiver: str,
    asset_amount: int,
    fee: AlgoAmount | None = None,
) -> AnySmartAsaComposer:
    """Appends an `asset_transfer` call to a group (e.g., two roles acting atomically)."""
    return composer.asset_transfer(
        AssetTransferArgs(
            xfer_asset=asset_id,
            asset_amount=asset_amount,
            asset_sender=asset_sender,
            asset_receiver=asset_receiver,
        ),
        params=CommonAppCallParams(
            static_fee=fee, signer=signer.signer, sender=signer.address
        ),
    )


def transfer(
    client: AnySmartAsaClient,
    asset_id: int,
    *,
    signer: SigningAccount,
    asset_sender: str,
    asset_receiver: str,
    asset_amount: int,
    fee: AlgoAmount | None = None,
) -> None:
    add_transfer(
        client.new_group(),
        asset_id,
        signer=signer,
        asset_sender=asset_sender,
        asset_receiver=asset_receiver,
        asset_amount=asset_amount,
        fee=fee,
    ).send()


def claw_back_and_redeem(
    client: AnySmartAsaClient,
    asset_id: int,
    *,
    signer: SigningAccount,
    holder: str,
    asset_amount: int,
    fee: AlgoAmount | None = None,
) -> None:
    """Forced redemption by a Reserve that is also Clawback: two calls, one group."""
    group = add_transfer(
        client.new_group(),
        asset_id,
        signer=signer,
        asset_sender=holder,
        asset_receiver=signer.address,
        asset_amount=asset_amount,
        fee=fee,
    )
    add_transfer(
        group,
        asset_id,
        signer=signer,
        asset_sender=signer.address,
        asset_receiver=client.app_address,
        asset_amount=asset_amount,
        fee=fee,
    ).send()


def global_freeze(
    client: AnySmartAsaClient,
    asset_id: int,
    signer: SigningAccount,
    *,
    frozen: bool = True,
) -> None:
    client.send.asset_freeze(
        AssetFreezeArgs(freeze_asset=asset_id, asset_frozen=frozen),
        params=CommonAppCallParams(signer=signer.signer, sender=signer.address),
    )


def box_deposit(
    client: AnySmartAsaClient,
    payer: SigningAccount,
    *,
    amount: int = cfg.FREEZE_EXCEPTION_BOX_MBR,
    receiver: str | None = None,
    note: bytes | None = None,
) -> Transaction:
    """The payment preceding an `account_freeze` that creates a box."""
    return client.algorand.create_transaction.payment(
        PaymentParams(
            sender=payer.address,
            receiver=receiver or client.app_address,
            amount=AlgoAmount.from_micro_algo(amount),
            note=note,
        )
    )


def account_freeze(
    client: AnySmartAsaClient,
    asset_id: int,
    signer: SigningAccount,
    account: str,
    *,
    frozen: bool = True,
) -> None:
    """Freeze path: a deposit before a new box, an extra fee for the refund on reset."""
    group = client.new_group()
    reset = frozen == client.state.global_state.default_frozen
    if not reset:
        group.add_transaction(box_deposit(client, signer), signer=signer.signer)
    group.account_freeze(
        AccountFreezeArgs(
            freeze_asset=asset_id, freeze_account=account, asset_frozen=frozen
        ),
        params=CommonAppCallParams(
            extra_fee=AlgoAmount.from_micro_algo(MIN_TXN_FEE) if reset else None,
            signer=signer.signer,
            sender=signer.address,
        ),
    ).send()


def balance(
    client: AnySmartAsaClient, asset_id: int, account: str | SigningAccount
) -> int:
    return client.algorand.asset.get_account_information(account, asset_id).balance


def circulating_supply(client: AnySmartAsaClient, asset_id: int) -> int | None:
    return client.send.get_circulating_supply(
        GetCirculatingSupplyArgs(asset=asset_id)
    ).abi_return
