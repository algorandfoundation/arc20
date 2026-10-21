from pathlib import Path

import pytest
from algokit_utils import (
    AlgorandClient,
    AppCreateParams,
    AppDeleteParams,
    AppUpdateParams,
    SigningAccount,
)
from algosdk.constants import ZERO_ADDRESS
from algosdk.transaction import OnComplete

import smart_contracts.smart_asa.config as cfg
from smart_contracts.artifacts.smart_asa.smart_asa_client import SmartAsaClient

ARTIFACTS = Path(__file__).parents[2] / "smart_contracts" / "artifacts" / "smart_asa"
APPROVAL = (ARTIFACTS / "SmartAsa.approval.teal").read_text()
CLEAR = (ARTIFACTS / "SmartAsa.clear.teal").read_text()

# Raw app calls surface algod errors through algokit's simulate step (no source map)
REJECTED = "rejected by ApprovalProgram"


def test_pass_create(smart_asa_client_no_asset: SmartAsaClient) -> None:
    state = smart_asa_client_no_asset.state.global_state

    assert state.total == 0
    assert state.decimals == 0
    assert not state.default_frozen
    assert state.unit_name == ""
    assert state.name == ""
    assert state.url == ""
    assert state.metadata_hash == ""  # FIXME: The typed state should be bytes
    assert state.manager_addr == ZERO_ADDRESS
    assert state.reserve_addr == ZERO_ADDRESS
    assert state.freeze_addr == ZERO_ADDRESS
    assert state.clawback_addr == ZERO_ADDRESS
    assert state.smart_asa_id == 0
    assert not state.global_frozen


def test_fail_update(
    algorand: AlgorandClient,
    creator: SigningAccount,
    smart_asa_client_no_asset: SmartAsaClient,
) -> None:
    with pytest.raises(ValueError, match=REJECTED):
        algorand.send.app_update(
            AppUpdateParams(
                sender=creator.address,
                app_id=smart_asa_client_no_asset.app_id,
                approval_program=APPROVAL,
                clear_state_program=CLEAR,
                on_complete=OnComplete.UpdateApplicationOC,
            )
        )


def test_fail_delete(
    algorand: AlgorandClient,
    creator: SigningAccount,
    smart_asa_client_no_asset: SmartAsaClient,
) -> None:
    # Deletion is only possible through asset_destroy
    with pytest.raises(ValueError, match=REJECTED):
        algorand.send.app_delete(
            AppDeleteParams(
                sender=creator.address, app_id=smart_asa_client_no_asset.app_id
            )
        )


@pytest.mark.parametrize(
    "schema_field",
    ["global_ints", "global_byte_slices", "local_ints", "local_byte_slices"],
)
def test_wrong_state_schema(
    algorand: AlgorandClient, creator: SigningAccount, schema_field: str
) -> None:
    schema = {
        "global_ints": cfg.GLOBAL_UINTS,
        "global_byte_slices": cfg.GLOBAL_BYTES,
        "local_ints": cfg.LOCAL_UINTS,
        "local_byte_slices": cfg.LOCAL_BYTES,
    }
    schema[schema_field] += 1
    with pytest.raises(ValueError, match="assert failed"):
        algorand.send.app_create(
            AppCreateParams(
                sender=creator.address,
                approval_program=APPROVAL,
                clear_state_program=CLEAR,
                schema=schema,  # type: ignore[typeddict-item]
            )
        )
