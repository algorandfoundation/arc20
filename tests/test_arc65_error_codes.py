import json
import re
from itertools import permutations
from pathlib import Path

import smart_contracts.errors as err

ARTIFACTS = Path(__file__).parents[1] / "smart_contracts" / "artifacts"
APP_SPECS = [
    "smart_asa/SmartAsa.arc56.json",
    "arc89_smart_asa/Arc89SmartAsa.arc56.json",
]

CODES = {name: value for name, value in vars(err).items() if name.isupper()}


def _logged_errors(app_spec: str) -> set[str]:
    spec = json.loads((ARTIFACTS / app_spec).read_text())
    return {
        info["errorMessage"]
        for info in spec["sourceInfo"]["approval"]["sourceInfo"]
        if info.get("errorMessage", "").startswith("ERR:")
    }


def test_codes_are_arc65_compliant() -> None:
    for code in CODES.values():
        assert re.fullmatch(r"[a-z][A-Za-z0-9]*", code), code  # camelCase, no ":"
        assert len(f"ERR:{code}") not in (8, 32), code  # ARC-65 recommendation


def test_codes_are_unambiguous() -> None:
    # Distinct, and none a prefix of another: test `match=` checks stay exact
    assert len(set(CODES.values())) == len(CODES)
    assert not [(a, b) for a, b in permutations(CODES.values(), 2) if b.startswith(a)]


def test_codes_are_used() -> None:
    logged = set().union(*(_logged_errors(app_spec) for app_spec in APP_SPECS))
    assert logged == {f"ERR:{code}" for code in CODES.values()}
