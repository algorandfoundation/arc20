from algokit_utils import SigningAccount

from smart_contracts.artifacts.smart_asa.smart_asa_client import SmartAsaClient
from tests.support import balance, circulating_supply


def test_pass_no_circulating_supply(
    smart_asa_client: SmartAsaClient, smart_asa_id: int
) -> None:
    assert circulating_supply(smart_asa_client, smart_asa_id) == 0


def test_pass_circulating_supply(
    smart_asa_client: SmartAsaClient,
    smart_asa_id: int,
    reserve_with_supply: SigningAccount,
) -> None:
    assert circulating_supply(smart_asa_client, smart_asa_id) == balance(
        smart_asa_client, smart_asa_id, reserve_with_supply
    )
