from pathlib import Path

from algokit_utils import AlgorandClient, AppCreateParams, SigningAccount

import smart_contracts.errors as err
import smart_contracts.smart_asa.config as cfg
from tests.support import arc65_errors

ARTIFACTS = (
    Path(__file__).parents[2] / "smart_contracts" / "artifacts" / "arc89_smart_asa"
)
APPROVAL = (ARTIFACTS / "Arc89SmartAsa.approval.teal").read_text()
CLEAR = (ARTIFACTS / "Arc89SmartAsa.clear.teal").read_text()
SCHEMA = {
    "global_ints": cfg.GLOBAL_UINTS,
    "global_byte_slices": cfg.GLOBAL_BYTES,
    "local_ints": cfg.LOCAL_UINTS,
    "local_byte_slices": cfg.LOCAL_BYTES,
}


def _create_params(creator: SigningAccount, app_id: int) -> AppCreateParams:
    # Raw creation from the TEAL, with the ASA Metadata Registry App ID template set
    return AppCreateParams(
        sender=creator.address,
        approval_program=APPROVAL.replace("TMPL_ARC89_APP_ID", str(app_id)),
        clear_state_program=CLEAR,
        schema=SCHEMA,  # type: ignore[typeddict-item]
    )


def test_pass_registry_app_id(
    algorand: AlgorandClient, creator: SigningAccount
) -> None:
    algorand.send.app_create(_create_params(creator, app_id=1))


def test_fail_missing_registry_app_id(
    algorand: AlgorandClient, creator: SigningAccount
) -> None:
    composer = algorand.new_group().add_app_create(_create_params(creator, app_id=0))
    assert arc65_errors(algorand, composer) == [
        f"ERR:{err.MISSING_ASA_METADATA_REGISTRY}"
    ]
