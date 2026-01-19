import pytest
from algokit_utils import (
    AlgoAmount,
    AssetConfigParams,
    CommonAppCallParams,
    LogicError,
    SigningAccount,
)
from asa_metadata_registry import (
    AsaMetadataRegistry,
    AssetMetadata,
    IrreversibleFlags,
    MetadataBody,
    MetadataFlags,
    ReversibleFlags,
)

import smart_contracts.errors as err
from helpers.metadata import call_asa_metadata_registry
from smart_contracts.artifacts.arc89_smart_asa.arc89_smart_asa_client import (
    Arc89SmartAsaClient,
    AsaMetadataRegistryInitArgs,
)


@pytest.mark.parametrize("metadata_body", [b"", b"X" * 4096])
def test_registry_call(
    min_fee_2x: AlgoAmount,
    manager: SigningAccount,
    asa_metadata_registry: AsaMetadataRegistry,
    arc89_smart_asa_client: Arc89SmartAsaClient,
    metadata_body: bytes,
) -> None:

    smart_asa_metadata = AssetMetadata(
        asset_id=arc89_smart_asa_client.state.global_state.smart_asa_id,
        body=MetadataBody(metadata_body),
        flags=MetadataFlags(
            irreversible=IrreversibleFlags(arc89_native=True),
            reversible=ReversibleFlags(arc20=True, arc62=True),
        ),
        deprecated_by=0,
    )

    metadata_composer = asa_metadata_registry.write.build_create_metadata_group(
        asset_manager=manager,
        metadata=smart_asa_metadata,
    )

    call_asa_metadata_registry(
        arc89_smart_asa_client=arc89_smart_asa_client,
        manager=manager,
        metadata_composer=metadata_composer,
        has_mbr_payment=True,
    )

    smart_asa_info = arc89_smart_asa_client.algorand.asset.get_by_id(
        asset_id=smart_asa_metadata.asset_id
    )
    assert smart_asa_info.manager == arc89_smart_asa_client.app_address
    assert smart_asa_info.reserve == arc89_smart_asa_client.app_address
    assert smart_asa_info.freeze == arc89_smart_asa_client.app_address
    assert smart_asa_info.clawback == arc89_smart_asa_client.app_address


def test_invalid_has_payment() -> None:
    pass


def test_invalid_calls() -> None:
    pass


def test_invalid_call_app_id() -> None:
    pass


def test_invalid_reconfig(
    min_fee_2x: AlgoAmount,
    arc89_smart_asa_client: Arc89SmartAsaClient,
    manager: SigningAccount,
    dummy_asa: int,
) -> None:
    smart_asa_id = arc89_smart_asa_client.state.global_state.smart_asa_id

    ctrl_asa_reconfig = arc89_smart_asa_client.algorand.create_transaction.asset_config(
        AssetConfigParams(
            sender=manager.address,
            asset_id=smart_asa_id,
            manager=manager.address,
            reserve=arc89_smart_asa_client.app_address,
            freeze=arc89_smart_asa_client.app_address,
            clawback=arc89_smart_asa_client.app_address,
        )
    )

    composer = arc89_smart_asa_client.new_group()
    composer.asa_metadata_registry_init(
        args=AsaMetadataRegistryInitArgs(
            asset=smart_asa_id, calls=0, has_mbr_payment=False
        ),
        params=CommonAppCallParams(
            sender=manager.address,
            static_fee=min_fee_2x,
        ),
    )
    composer.add_transaction(ctrl_asa_reconfig)

    with pytest.raises(LogicError, match=err.INVALID_CTRL_ASA_RBAC_RECONFIG):
        composer.send()

    ctrl_asa_reconfig = arc89_smart_asa_client.algorand.create_transaction.asset_config(
        AssetConfigParams(
            sender=manager.address,
            asset_id=dummy_asa,
            manager=arc89_smart_asa_client.app_address,
            reserve=arc89_smart_asa_client.app_address,
            freeze=arc89_smart_asa_client.app_address,
            clawback=arc89_smart_asa_client.app_address,
        )
    )

    composer = arc89_smart_asa_client.new_group()
    composer.asa_metadata_registry_init(
        args=AsaMetadataRegistryInitArgs(
            asset=smart_asa_id, calls=0, has_mbr_payment=False
        ),
        params=CommonAppCallParams(
            sender=manager.address,
            static_fee=min_fee_2x,
        ),
    )
    composer.add_transaction(ctrl_asa_reconfig)

    with pytest.raises(LogicError, match=err.INVALID_CTRL_ASA_RBAC_RECONFIG):
        composer.send()
