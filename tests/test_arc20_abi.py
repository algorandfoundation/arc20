import json
from pathlib import Path

import pytest

ARTIFACTS = Path(__file__).parents[1] / "smart_contracts" / "artifacts"

# ARC-20 Full ABI Spec: method selectors are derived from these signatures
ASA_FIELDS = (
    "uint64,uint32,bool,string,string,string,byte[],address,address,address,address"
)
ARC20_SIGNATURES = [
    f"asset_create({ASA_FIELDS})uint64",
    f"asset_config(asset,{ASA_FIELDS})void",
    f"get_asset_config(asset)({ASA_FIELDS})",
    "asset_transfer(asset,uint64,account,account)void",
    "asset_freeze(asset,bool)void",
    "account_freeze(asset,account,bool)void",
    "get_asset_is_frozen(asset)bool",
    "get_account_is_frozen(asset,account)bool",
    "asset_destroy(asset)void",
    "get_circulating_supply(asset)uint64",
]


def _signature(method: dict) -> str:
    args = ",".join(arg["type"] for arg in method["args"])
    return f"{method['name']}({args}){method['returns']['type']}"


@pytest.mark.parametrize(
    "app_spec",
    ["smart_asa/SmartAsa.arc56.json", "arc89_smart_asa/Arc89SmartAsa.arc56.json"],
)
def test_arc20_method_signatures(app_spec: str) -> None:
    spec = json.loads((ARTIFACTS / app_spec).read_text())
    signatures = {_signature(method) for method in spec["methods"]}
    assert set(ARC20_SIGNATURES) - signatures == set()
