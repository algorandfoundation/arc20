"""Shared helpers for the Smart ASA test suite."""

from typing import Final

import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AppClientBareCallParams,
    AssetOptInParams,
    AssetTransferParams,
    CommonAppCallParams,
    SigningAccount,
)
from algosdk.atomic_transaction_composer import TransactionWithSigner
from algosdk.transaction import Transaction

from smart_contracts.artifacts.arc89_smart_asa.arc89_smart_asa_client import (
    Arc89SmartAsaClient,
)
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AccountFreezeArgs,
    AssetCloseOutArgs,
    AssetFreezeArgs,
    AssetOptInArgs,
    AssetTransferArgs,
    GetCirculatingSupplyArgs,
    SmartAsaClient,
    SmartAsaComposer,
)

# The generated clients share the ABI argument layouts, so the helpers accept both
AnySmartAsaClient = SmartAsaClient | Arc89SmartAsaClient

INITIAL_FUNDS: Final[AlgoAmount] = AlgoAmount.from_algo(100)

# Expected failures that carry no contract error message
NOT_OPTED_IN: Final[str] = "cannot fetch key"  # Local state of a non opted-in account
ASSERT_FAILED: Final[str] = "assert failed"  # ARC-4 router checks and raw algod errors
GTXN_OUT_OF_RANGE: Final[str] = r"len\(group\) is"  # Group index past the last txn
APPROVAL_REJECTED: Final[str] = "rejected by ApprovalProgram"
UNREACHABLE: Final[str] = (
    "Unreachable: asset_create is one-shot and asset_destroy deletes the app"
)

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


def funded_account(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


def opt_in(client: AnySmartAsaClient, asset_id: int, account: SigningAccount) -> None:
    client.send.opt_in.asset_opt_in(
        AssetOptInArgs(
            asset=asset_id,
            ctrl_asa_opt_in=TransactionWithSigner(
                txn=client.algorand.create_transaction.asset_opt_in(
                    AssetOptInParams(asset_id=asset_id, sender=account.address)
                ),
                signer=account.signer,
            ),
        ),
        params=CommonAppCallParams(signer=account.signer, sender=account.address),
    )


def clear_state(client: AnySmartAsaClient, account: SigningAccount) -> None:
    """Drops the account's App Local State; its Controlled ASA holding is kept."""
    client.send.clear_state(
        AppClientBareCallParams(signer=account.signer, sender=account.address)
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
    client.send.asset_transfer(
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


def account_freeze(
    client: AnySmartAsaClient,
    asset_id: int,
    signer: SigningAccount,
    account: str,
    *,
    frozen: bool = True,
) -> None:
    client.send.account_freeze(
        AccountFreezeArgs(
            freeze_asset=asset_id, freeze_account=account, asset_frozen=frozen
        ),
        params=CommonAppCallParams(signer=signer.signer, sender=signer.address),
    )


def balance(
    client: AnySmartAsaClient, asset_id: int, account: str | SigningAccount
) -> int:
    return client.algorand.asset.get_account_information(account, asset_id).balance


def circulating_supply(client: AnySmartAsaClient, asset_id: int) -> int | None:
    return client.send.get_circulating_supply(
        GetCirculatingSupplyArgs(asset=asset_id)
    ).abi_return


def close_out_call(
    client: SmartAsaClient,
    asset_id: int,
    account: SigningAccount,
    *,
    close_to: str,
    fee: AlgoAmount | None = None,
) -> SmartAsaComposer:
    """A group with the `asset_close_out` call only: the ASA close-out must follow."""
    return client.new_group().close_out.asset_close_out(
        AssetCloseOutArgs(close_asset=asset_id, close_to=close_to),
        params=CommonAppCallParams(
            static_fee=fee, signer=account.signer, sender=account.address
        ),
    )


def asa_close_out_txn(
    client: SmartAsaClient,
    asset_id: int,
    sender: SigningAccount,
    **overrides: object,
) -> Transaction:
    """The Controlled ASA close-out expected after `asset_close_out`, as overridden."""
    fields: dict[str, object] = {
        "asset_id": asset_id,
        "receiver": client.app_address,
        "amount": 0,
        "close_asset_to": client.app_address,
    } | overrides
    return client.algorand.create_transaction.asset_transfer(
        AssetTransferParams(sender=sender.address, **fields)  # type: ignore[arg-type]
    )


def close_out(
    client: SmartAsaClient,
    asset_id: int,
    account: SigningAccount,
    *,
    close_to: str,
    fee: AlgoAmount | None = None,
) -> None:
    composer = close_out_call(client, asset_id, account, close_to=close_to, fee=fee)
    composer.add_transaction(
        asa_close_out_txn(client, asset_id, account), signer=account.signer
    )
    composer.send()
