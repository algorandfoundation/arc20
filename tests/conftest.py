from dataclasses import asdict, dataclass
from typing import Final

import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AssetCreateParams,
    SigningAccount,
)

INITIAL_FUNDS: Final[AlgoAmount] = AlgoAmount.from_algo(100)


@dataclass(kw_only=True)
class SmartASAConfig:
    manager_addr: str
    reserve_addr: str
    freeze_addr: str
    clawback_addr: str
    url: str
    total: int = 100
    decimals: int = 2
    default_frozen: bool = False
    unit_name: str = "TST"
    name: str = "Test"
    metadata_hash: bytes = b"\x00" * 32

    def dictify(self) -> dict[str, str | int | bytes | bool]:
        return asdict(self)


@pytest.fixture(scope="session")
def algorand() -> AlgorandClient:
    client = AlgorandClient.default_localnet()
    client.set_suggested_params_cache_timeout(0)
    return client


@pytest.fixture(scope="session")
def min_fee_2x(algorand: AlgorandClient) -> AlgoAmount:
    sp = algorand.client.algod.suggested_params()
    sp.fee = sp.min_fee * 2
    return AlgoAmount.from_micro_algo(sp.fee)


@pytest.fixture(scope="session")
def deployer(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.from_environment("DEPLOYER")
    return account


@pytest.fixture(scope="session")
def creator(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


@pytest.fixture(scope="session")
def manager(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


@pytest.fixture(scope="session")
def reserve(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


@pytest.fixture(scope="session")
def freeze(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


@pytest.fixture(scope="session")
def clawback(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


@pytest.fixture(scope="session")
def eve(algorand: AlgorandClient) -> SigningAccount:
    account = algorand.account.random()
    algorand.account.ensure_funded_from_environment(
        account_to_fund=account.address,
        min_spending_balance=INITIAL_FUNDS,
    )
    return account


@pytest.fixture(scope="session")
def dummy_asa(algorand: AlgorandClient, creator: SigningAccount) -> int:
    return algorand.send.asset_create(
        AssetCreateParams(sender=creator.address, signer=creator.signer, total=1)
    ).asset_id
