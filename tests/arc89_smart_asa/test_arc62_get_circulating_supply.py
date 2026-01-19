from algokit_utils import SigningAccount

from smart_contracts.artifacts.arc89_smart_asa.arc89_smart_asa_client import (
    Arc62GetCirculatingSupplyArgs,
    Arc89SmartAsaClient,
)


def test_pass_no_circulating_supply(
    arc89_smart_asa_client: Arc89SmartAsaClient,
) -> None:
    circulating_supply = arc89_smart_asa_client.send.arc62_get_circulating_supply(
        Arc62GetCirculatingSupplyArgs(
            asset_id=arc89_smart_asa_client.state.global_state.smart_asa_id
        )
    ).abi_return
    assert circulating_supply == 0


def test_pass_circulating_supply(
    arc89_smart_asa_client: Arc89SmartAsaClient, reserve_with_supply: SigningAccount
) -> None:
    smart_asa_id = arc89_smart_asa_client.state.global_state.smart_asa_id
    circulating_supply = arc89_smart_asa_client.send.arc62_get_circulating_supply(
        Arc62GetCirculatingSupplyArgs(
            asset_id=arc89_smart_asa_client.state.global_state.smart_asa_id
        )
    ).abi_return
    assert (
        circulating_supply
        == arc89_smart_asa_client.algorand.asset.get_account_information(
            reserve_with_supply, smart_asa_id
        ).balance
    )
