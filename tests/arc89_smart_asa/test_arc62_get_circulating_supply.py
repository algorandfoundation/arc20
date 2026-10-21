from algokit_utils import SigningAccount

from smart_contracts.artifacts.arc89_smart_asa.arc89_smart_asa_client import (
    Arc62GetCirculatingSupplyArgs,
    Arc89SmartAsaClient,
)
from tests.support import balance


def _arc62_circulating_supply(client: Arc89SmartAsaClient, asset_id: int) -> int | None:
    return client.send.arc62_get_circulating_supply(
        Arc62GetCirculatingSupplyArgs(asset_id=asset_id)
    ).abi_return


def test_pass_no_circulating_supply(
    arc89_smart_asa_client: Arc89SmartAsaClient, smart_asa_id: int
) -> None:
    assert _arc62_circulating_supply(arc89_smart_asa_client, smart_asa_id) == 0


def test_pass_circulating_supply(
    arc89_smart_asa_client: Arc89SmartAsaClient,
    smart_asa_id: int,
    reserve_with_supply: SigningAccount,
) -> None:
    assert _arc62_circulating_supply(arc89_smart_asa_client, smart_asa_id) == balance(
        arc89_smart_asa_client, smart_asa_id, reserve_with_supply
    )
