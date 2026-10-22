from algopy import Account, StateTotals, UInt64, logged_assert, op

from smart_contracts.smart_asa import config as cfg
from smart_contracts.smart_asa.contract import SmartAsa

from . import config as capped_cfg
from . import errors as capped_err


class CappedSmartAsa(
    SmartAsa,
    # Same schema as the Smart ASA: custom state goes in boxes
    state_totals=StateTotals(
        global_bytes=cfg.GLOBAL_BYTES,
        global_uints=cfg.GLOBAL_UINTS,
        local_bytes=cfg.LOCAL_BYTES,
        local_uints=cfg.LOCAL_UINTS,
    ),
):
    """
    Example extension of the Smart ASA: regular transfers can't take a holding above a cap
    """

    def _regular_transfer_hook(
        self, *, asset_sender: Account, asset_receiver: Account, asset_amount: UInt64
    ) -> None:
        # Runs after the built-in checks. A non-holder holds 0 units: the protocol then
        # rejects any amount but 0
        holding, _holds = op.AssetHoldingGet.asset_balance(
            asset_receiver, self.smart_asa_id
        )
        logged_assert(
            holding + asset_amount <= capped_cfg.MAX_HOLDING,
            capped_err.HOLDING_CAP_EXCEEDED,
        )
