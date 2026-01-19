# pyright: reportMissingModuleSource=false
from algopy import (
    Asset,
    Global,
    OnCompleteAction,
    StateTotals,
    TemplateVar,
    TransactionType,
    Txn,
    UInt64,
    arc4,
    gtxn,
    subroutine,
    urange,
)

from smart_contracts import errors as err
from smart_contracts.arc89_smart_asa.template_vars import ARC89_APP_ID
from smart_contracts.avm_library import inner_asset_config
from smart_contracts.smart_asa import config as cfg
from smart_contracts.smart_asa.contract import SmartAsa


@subroutine
def _is_mbr_payment(txn: gtxn.Transaction) -> bool:
    return (
        txn.type == TransactionType.Payment
    )  # Payment validation on ASA Metadata Registry


@subroutine
def _is_asa_metadata_registry_call(txn: gtxn.Transaction) -> bool:
    return (
        txn.type == TransactionType.ApplicationCall
        and txn.app_id.id == TemplateVar[UInt64](ARC89_APP_ID)
        and txn.on_completion == OnCompleteAction.NoOp
    )


@subroutine
def _assert_valid_controlled_asa_reconfig(txn: gtxn.Transaction, asset: Asset) -> None:
    assert (
        txn.type == TransactionType.AssetConfig
        and txn.config_asset == asset
        and txn.manager == Global.current_application_address
        and txn.reserve == Global.current_application_address
        and txn.freeze == Global.current_application_address
        and txn.clawback == Global.current_application_address
    ), err.INVALID_CTRL_ASA_RBAC_RECONFIG


class Arc89SmartAsa(
    SmartAsa,
    state_totals=StateTotals(
        global_bytes=cfg.GLOBAL_BYTES,
        global_uints=cfg.GLOBAL_UINTS,
        local_bytes=cfg.LOCAL_BYTES,
        local_uints=cfg.LOCAL_UINTS,
    ),
):
    """
    Smart ASA (ARC-20) Reference Implementation, with ASA Metadata Registry (ARC-89) integration.
    """

    def __init__(self) -> None:
        SmartAsa.__init__(self)

    @arc4.abimethod
    def asa_metadata_registry_init(
        self, *, asset: Asset, calls: UInt64, has_mbr_payment: bool
    ) -> None:
        # Preconditions
        self._assert_common_preconditions(asset)
        assert Txn.sender == self.manager_addr, err.UNAUTHORIZED_MANAGER

        # All the transactions after the ASA Metadata Registry init must be calls
        # to the ASA Metadata Registry (with an MBR payment, if required).
        group_index = Txn.group_index
        if has_mbr_payment:
            txn = gtxn.Transaction(group_index + 1)
            assert _is_mbr_payment(txn), err.INVALID_ASA_METADATA_REGISTRY_MBR_PAYMENT
            group_index += 1
        for idx in urange(group_index + 1, group_index + 1 + calls):
            txn = gtxn.Transaction(idx)
            assert _is_asa_metadata_registry_call(
                txn
            ), err.INVALID_ASA_METADATA_REGISTRY_CALL

        # The ASA Metadata Registry call group must terminate granting the Controlled
        # ASA RBAC back to the Smart ASA App.
        txn = gtxn.Transaction(group_index + 1 + calls)
        _assert_valid_controlled_asa_reconfig(txn, asset)

        # Grant the Controlled ASA Asset Manager role to the Smart ASA Manager, limited
        # to the ASA Metadata Registry interaction.
        inner_asset_config(
            config_asset=asset,
            manager=self.manager_addr,
            reserve=Global.current_application_address,
            freeze=Global.current_application_address,
            clawback=Global.current_application_address,
        )
