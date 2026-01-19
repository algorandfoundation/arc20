# mypy: ignore-errors

from algokit_utils import (
    AlgoAmount,
    AssetConfigParams,
    CommonAppCallParams,
    SendAtomicTransactionComposerResults,
    SigningAccount,
)
from asa_metadata_registry._generated.asa_metadata_registry_client import (
    AsaMetadataRegistryComposer,
)

from smart_contracts.artifacts.arc89_smart_asa.arc89_smart_asa_client import (
    Arc89SmartAsaClient,
    AsaMetadataRegistryInitArgs,
)


def call_asa_metadata_registry(
    *,
    arc89_smart_asa_client: Arc89SmartAsaClient,
    manager: SigningAccount,
    metadata_composer: AsaMetadataRegistryComposer,
    has_mbr_payment: bool = False,
) -> SendAtomicTransactionComposerResults:
    sp = arc89_smart_asa_client.algorand.client.algod.suggested_params()
    sp.fee = sp.min_fee * 2
    min_fee_2x = AlgoAmount.from_micro_algo(sp.fee)

    smart_asa_id = arc89_smart_asa_client.state.global_state.smart_asa_id

    ctrl_asa_reconfig = arc89_smart_asa_client.algorand.create_transaction.asset_config(
        AssetConfigParams(
            sender=manager.address,
            asset_id=smart_asa_id,
            manager=arc89_smart_asa_client.app_address,
            reserve=arc89_smart_asa_client.app_address,
            freeze=arc89_smart_asa_client.app_address,
            clawback=arc89_smart_asa_client.app_address,
        )
    )

    metadata_group = metadata_composer.composer().build().atc.clone().txn_list

    composer = arc89_smart_asa_client.new_group()
    composer.asa_metadata_registry_init(
        args=AsaMetadataRegistryInitArgs(
            asset=smart_asa_id,
            calls=len(metadata_group) - 1 if has_mbr_payment else len(metadata_group),
            has_mbr_payment=has_mbr_payment,
        ),
        params=CommonAppCallParams(
            sender=manager.address,
            static_fee=min_fee_2x,
        ),
    )
    for m in metadata_group:
        composer.add_transaction(m.txn)
    composer.add_transaction(ctrl_asa_reconfig)
    return composer.send()
