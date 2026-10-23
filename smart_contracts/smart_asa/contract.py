from algopy import (
    Account,
    Asset,
    BoxMap,
    Bytes,
    Global,
    StateTotals,
    String,
    TransactionType,
    Txn,
    UInt64,
    arc4,
    gtxn,
    logged_assert,
)

from smart_contracts import errors as err
from smart_contracts.arc20_interface import Arc20Interface
from smart_contracts.avm_library import (
    inner_asset_create,
    inner_asset_destroy,
    inner_asset_transfer,
    inner_close_account,
    inner_payment,
)
from smart_contracts.avm_types import AssetConfig

from . import config as cfg


class SmartAsa(
    Arc20Interface,
    state_totals=StateTotals(
        global_bytes=cfg.GLOBAL_BYTES,
        global_uints=cfg.GLOBAL_UINTS,
        local_bytes=cfg.LOCAL_BYTES,
        local_uints=cfg.LOCAL_UINTS,
    ),
):
    """
    Smart ASA (ARC-20) Reference Implementation
    """

    def __init__(self) -> None:
        # Preconditions
        logged_assert(
            Txn.global_num_byte_slice == cfg.GLOBAL_BYTES, err.WRONG_GLOBAL_BYTES
        )
        logged_assert(Txn.global_num_uint == cfg.GLOBAL_UINTS, err.WRONG_GLOBAL_UINTS)
        logged_assert(
            Txn.local_num_byte_slice == cfg.LOCAL_BYTES, err.WRONG_LOCAL_BYTES
        )
        logged_assert(Txn.local_num_uint == cfg.LOCAL_UINTS, err.WRONG_LOCAL_UINTS)

        # GLOBAL STATE
        # ASA Fields
        self.total = UInt64()
        self.decimals = UInt64()
        self.default_frozen = False
        self.unit_name = String()
        self.name = String()
        self.url = String()
        self.metadata_hash = Bytes()
        self.manager_addr = Account()
        self.reserve_addr = Account()
        self.freeze_addr = Account()
        self.clawback_addr = Account()
        # Smart ASA Fields
        self.smart_asa_id = UInt64()
        self.global_frozen = False

        # BOXES
        # Accounts not in the default freeze state: empty boxes (MBR paid by the App)
        self.freeze_exceptions = BoxMap(
            Account, Bytes, key_prefix=cfg.FREEZE_EXCEPTION_KEY_PREFIX
        )

    def _issued_supply(self, ctrl_asset: Asset) -> UInt64:
        # The App holds the units not issued yet: the total caps the issued ones
        return cfg.TOTAL - ctrl_asset.balance(Global.current_application_address)

    def _circulating_supply(self, ctrl_asset: Asset) -> UInt64:
        """
        Extension point for subclasses: the circulating supply, the issued supply by
        default. Every circulating supply getter returns it, so they always agree.
        """
        return self._issued_supply(ctrl_asset)

    def _assert_common_preconditions(self, asset: Asset) -> None:
        logged_assert(self.smart_asa_id != 0, err.MISSING_CTRL_ASA)
        logged_assert(self.smart_asa_id == asset.id, err.INVALID_CTRL_ASA)

    def _is_frozen(self, account: Account) -> bool:
        # A box flips the default freeze state of its account
        return self.default_frozen != (account in self.freeze_exceptions)

    def _assert_box_deposit(self, *, box_mbr: UInt64) -> None:
        # A payment of at least the box MBR to the App just before this call, by anyone
        logged_assert(Txn.group_index > 0, err.BOX_MBR_UNFUNDED)
        deposit = gtxn.Transaction(Txn.group_index - 1)
        logged_assert(
            deposit.type == TransactionType.Payment
            and deposit.receiver == Global.current_application_address
            and deposit.amount >= box_mbr,
            err.BOX_MBR_UNFUNDED,
        )

    def _assert_issuing_preconditions(
        self, *, asset_receiver: Account, asset_amount: UInt64
    ) -> None:
        # Issue permission restricted to Reserve.
        logged_assert(Txn.sender == self.reserve_addr, err.UNAUTHORIZED_RESERVE)
        # Forbidden self-issue (to Creator) and over-issue (> total).
        logged_assert(
            asset_receiver != Global.current_application_address, err.SELF_ISSUE
        )
        logged_assert(
            asset_amount + self._issued_supply(Asset(self.smart_asa_id)) <= self.total,
            err.OVER_ISSUE,
        )
        logged_assert(not self.global_frozen, err.GLOBAL_FROZEN)
        self._assert_reserve_not_frozen()
        logged_assert(not self._is_frozen(asset_receiver), err.RECEIVER_FROZEN)

    def _assert_redeeming_preconditions(self, *, asset_sender: Account) -> None:
        # Redeem permission restricted to Reserve.
        logged_assert(Txn.sender == self.reserve_addr, err.UNAUTHORIZED_RESERVE)
        logged_assert(not self.global_frozen, err.GLOBAL_FROZEN)
        # Forbidden clawback through redeeming (redeemed amount not from Reserve).
        logged_assert(asset_sender == self.reserve_addr, err.CLAWBACK_REDEEM)
        self._assert_reserve_not_frozen()

    def _assert_reserve_not_frozen(self) -> None:
        # The Reserve obeys account freezes, even if it is also the Clawback
        logged_assert(not self._is_frozen(self.reserve_addr), err.RESERVE_FROZEN)

    def _assert_regular_transfer_preconditions(
        self, *, asset_sender: Account, asset_receiver: Account
    ) -> None:
        logged_assert(Txn.sender == asset_sender, err.UNAUTHORIZED_CLAWBACK)
        logged_assert(not self.global_frozen, err.GLOBAL_FROZEN)
        logged_assert(not self._is_frozen(asset_sender), err.SENDER_FROZEN)
        logged_assert(not self._is_frozen(asset_receiver), err.RECEIVER_FROZEN)

    def _regular_transfer_hook(
        self, *, asset_sender: Account, asset_receiver: Account, asset_amount: UInt64
    ) -> None:
        """
        Extension point for subclasses: custom checks on regular transfers, run after the
        built-in ones. The reference implementation adds none (no program cost).
        """

    def _assert_valid_metadata_hash(self, metadata_hash: Bytes) -> None:
        # Non-normative: stricter than ARC-20, which allows any `byte[]` length
        logged_assert(
            metadata_hash.length == cfg.METADATA_HASH_LENGTH,
            err.INVALID_METADATA_HASH_LENGTH,
        )

    def _configure_smart_asa(
        self,
        *,
        total: UInt64,
        decimals: UInt64,
        unit_name: String,
        name: String,
        url: String,
        metadata_hash: Bytes,
        manager_addr: Account,
        reserve_addr: Account,
        freeze_addr: Account,
        clawback_addr: Account,
    ) -> None:
        self.total = total
        self.decimals = decimals
        self.unit_name = unit_name
        self.name = name
        self.url = url
        self.metadata_hash = metadata_hash
        self.manager_addr = manager_addr
        self.reserve_addr = reserve_addr
        self.freeze_addr = freeze_addr
        self.clawback_addr = clawback_addr

    @arc4.abimethod
    def asset_create(
        self,
        *,
        total: UInt64,
        decimals: arc4.UInt32,
        default_frozen: bool,
        unit_name: String,
        name: String,
        url: String,
        metadata_hash: Bytes,
        manager_addr: Account,
        reserve_addr: Account,
        freeze_addr: Account,
        clawback_addr: Account,
    ) -> UInt64:
        """
        Create the Controlled ASA

        Args:
            total: The total number of base units of the Smart ASA to create
            decimals: The number of digits to use after the decimal point when displaying the Smart ASA
            default_frozen: Smart ASA default frozen (True to freeze holdings by default)
            unit_name: The name of a unit of Smart ASA
            name: The name of the Smart ASA
            url: Smart ASA external URL
            metadata_hash: Smart ASA metadata hash
            manager_addr: Account that can manage the configuration of the Smart ASA and destroy it
            reserve_addr: Account that can issue and redeem units of the Smart ASA
            freeze_addr: Account that can freeze/unfreeze holdings of the Smart ASA globally or locally
            clawback_addr: Account that can clawback holdings of the Smart ASA

        Returns:
            Controlled ASA ID
        """
        # Preconditions
        logged_assert(Txn.sender == Global.creator_address, err.UNAUTHORIZED_CREATOR)
        logged_assert(not self.smart_asa_id, err.EXISTING_CTRL_ASA)
        self._assert_valid_metadata_hash(metadata_hash)

        # Create the underlying Controlled ASA
        self.smart_asa_id = inner_asset_create(
            total=UInt64(cfg.TOTAL),
            decimals=UInt64(cfg.DECIMALS),
            default_frozen=cfg.DEFAULT_FROZEN,
            unit_name=unit_name,
            name=name,
            url=url,
            metadata_hash=metadata_hash,
            manager=Global.current_application_address,
            reserve=Global.current_application_address,
            freeze=Global.current_application_address,
            clawback=Global.current_application_address,
        )

        # Configure Smart ASA (`default_frozen` is set on creation only)
        self.default_frozen = default_frozen
        self._configure_smart_asa(
            total=total,
            decimals=decimals.as_uint64(),
            unit_name=unit_name,
            name=name,
            url=url,
            metadata_hash=metadata_hash,
            manager_addr=manager_addr,
            reserve_addr=reserve_addr,
            freeze_addr=freeze_addr,
            clawback_addr=clawback_addr,
        )

        return self.smart_asa_id

    @arc4.abimethod(resource_encoding="index")
    def asset_config(
        self,
        *,
        config_asset: Asset,
        total: UInt64,
        decimals: arc4.UInt32,
        default_frozen: bool,
        unit_name: String,
        name: String,
        url: String,
        metadata_hash: Bytes,
        manager_addr: arc4.Address,
        reserve_addr: arc4.Address,
        freeze_addr: arc4.Address,
        clawback_addr: arc4.Address,
    ) -> None:
        """
        Configure Smart ASA (for unchanged parameters use existing value - no optional args on AVM)

        Args:
            config_asset: Smart ASA ID to configure
            total: Total number of base units of the Smart ASA. It can not be less than current circulating supply
            decimals: The number of digits to use after the decimal point when displaying the Smart ASA
            default_frozen: Ignored, as for native ASA (set on creation only)
            unit_name: The name of a unit of Smart ASA
            name: The name of the Smart ASA
            url: Smart ASA external URL
            metadata_hash: Smart ASA metadata hash
            manager_addr: Account that can manage the configuration of the Smart ASA and destroy it
            reserve_addr: Account that can issue and redeem units of the Smart ASA
            freeze_addr: Account that can freeze/unfreeze holdings of the Smart ASA globally or locally
            clawback_addr: Account that can clawback holdings of the Smart ASA
        """
        # Preconditions
        self._assert_common_preconditions(config_asset)
        logged_assert(Txn.sender == self.manager_addr, err.UNAUTHORIZED_MANAGER)
        self._assert_valid_metadata_hash(metadata_hash)
        if reserve_addr.native != self.reserve_addr:
            logged_assert(
                self.reserve_addr != Global.zero_address, err.DISABLED_RESERVE
            )
        if freeze_addr.native != self.freeze_addr:
            logged_assert(self.freeze_addr != Global.zero_address, err.DISABLED_FREEZE)
        if clawback_addr.native != self.clawback_addr:
            logged_assert(
                self.clawback_addr != Global.zero_address, err.DISABLED_CLAWBACK
            )
        logged_assert(total >= self._issued_supply(config_asset), err.INVALID_TOTAL)

        # Configure Smart ASA
        self._configure_smart_asa(
            total=total,
            decimals=decimals.as_uint64(),
            unit_name=unit_name,
            name=name,
            url=url,
            metadata_hash=metadata_hash,
            manager_addr=manager_addr.native,
            reserve_addr=reserve_addr.native,
            freeze_addr=freeze_addr.native,
            clawback_addr=clawback_addr.native,
        )

    @arc4.abimethod(resource_encoding="index")
    def asset_transfer(
        self,
        *,
        xfer_asset: Asset,
        asset_amount: UInt64,
        asset_sender: Account,
        asset_receiver: Account,
    ) -> None:
        """
        Smart ASA transfers: regular, clawback, issue, redeem

        Args:
            xfer_asset: Smart ASA ID to transfer
            asset_amount: Amount to transfer
            asset_sender: Smart ASA sender
            asset_receiver: Smart ASA receiver
        """
        # Preconditions
        self._assert_common_preconditions(xfer_asset)
        if asset_sender == Global.current_application_address:
            self._assert_issuing_preconditions(
                asset_receiver=asset_receiver, asset_amount=asset_amount
            )
        elif asset_receiver == Global.current_application_address:
            self._assert_redeeming_preconditions(asset_sender=asset_sender)
        elif Txn.sender == self.clawback_addr:
            pass  # The Clawback ignores freezes
        else:
            self._assert_regular_transfer_preconditions(
                asset_sender=asset_sender, asset_receiver=asset_receiver
            )
            self._regular_transfer_hook(
                asset_sender=asset_sender,
                asset_receiver=asset_receiver,
                asset_amount=asset_amount,
            )

        # Effects
        inner_asset_transfer(
            xfer_asset=xfer_asset,
            asset_amount=asset_amount,
            asset_sender=asset_sender,
            asset_receiver=asset_receiver,
        )

    @arc4.abimethod(resource_encoding="index")
    def asset_freeze(self, *, freeze_asset: Asset, asset_frozen: bool) -> None:
        """
        Smart ASA global freeze (all accounts)

        Args:
            freeze_asset: Smart ASA ID to globally freeze/unfreeze
            asset_frozen: Smart ASA frozen status
        """
        # Preconditions
        self._assert_common_preconditions(freeze_asset)
        logged_assert(Txn.sender == self.freeze_addr, err.UNAUTHORIZED_FREEZE)

        # Effects
        self.global_frozen = asset_frozen

    @arc4.abimethod(resource_encoding="index")
    def account_freeze(
        self, *, freeze_asset: Asset, freeze_account: Account, asset_frozen: bool
    ) -> None:
        """
        Smart ASA local freeze (account specific)

        Args:
            freeze_asset: Smart ASA ID to locally freeze/unfreeze
            freeze_account: Account to freeze/unfreeze
            asset_frozen: Smart ASA frozen status
        """
        # Preconditions
        self._assert_common_preconditions(freeze_asset)
        logged_assert(Txn.sender == self.freeze_addr, err.UNAUTHORIZED_FREEZE)

        # Effects
        # Only the exceptions to the default freeze state have a box, deposited by
        # anyone on creation and refunded to Freeze on deletion
        app = Global.current_application_address
        min_balance = app.min_balance
        if asset_frozen == self.default_frozen:
            # box_del doesn't fail: an account without a box gets a 0 refund
            del self.freeze_exceptions[freeze_account]
            inner_payment(receiver=Txn.sender, amount=min_balance - app.min_balance)
        else:
            created = self.freeze_exceptions.box(key=freeze_account).create(size=0)
            if created:
                self._assert_box_deposit(box_mbr=app.min_balance - min_balance)

    @arc4.abimethod(allow_actions=["DeleteApplication"], resource_encoding="index")
    def asset_destroy(self, *, destroy_asset: Asset) -> None:
        """
        Destroy the Smart ASA

        Args:
            destroy_asset: Smart ASA ID to destroy
        """
        # Preconditions
        self._assert_common_preconditions(destroy_asset)
        logged_assert(Txn.sender == self.manager_addr, err.UNAUTHORIZED_MANAGER)
        logged_assert(self._issued_supply(destroy_asset) == 0, err.UNITS_ISSUED)
        # Deleting the App with boxes left would orphan them, locking their MBR
        logged_assert(
            Global.current_application_address.total_boxes == 0, err.FREEZE_BOXES_LEFT
        )

        # Effects
        inner_asset_destroy(destroy_asset=destroy_asset)
        # The App is deleted with this call: close its account to the Manager
        inner_close_account(close_remainder_to=Txn.sender)

    @arc4.abimethod
    def withdraw_excess_algo(self) -> None:
        """
        Withdraw the App ALGO above its MBR to the Manager (non-normative)
        """
        # Preconditions
        logged_assert(Txn.sender == self.manager_addr, err.UNAUTHORIZED_MANAGER)

        # Effects
        app = Global.current_application_address
        inner_payment(receiver=Txn.sender, amount=app.balance - app.min_balance)

    @arc4.abimethod(readonly=True, resource_encoding="index")
    def get_asset_config(self, *, asset: Asset) -> AssetConfig:
        """
        Get Smart ASA configuration

        Args:
            asset: Smart ASA ID

        Returns:
            Smart ASA configuration parameters
        """
        # Preconditions
        self._assert_common_preconditions(asset)

        # Effects
        return AssetConfig(
            total=self.total,
            decimals=arc4.UInt32(self.decimals),
            default_frozen=self.default_frozen,
            unit_name=self.unit_name,
            name=self.name,
            url=self.url,
            metadata_hash=self.metadata_hash,
            manager_addr=self.manager_addr,
            reserve_addr=self.reserve_addr,
            freeze_addr=self.freeze_addr,
            clawback_addr=self.clawback_addr,
        )

    @arc4.abimethod(readonly=True, resource_encoding="index")
    def get_asset_is_frozen(self, *, freeze_asset: Asset) -> bool:
        """
        Get Smart ASA global frozen status

        Args:
            freeze_asset: Smart ASA ID

        Returns:
            Smart ASA global frozen status
        """
        # Preconditions
        self._assert_common_preconditions(freeze_asset)

        # Effects
        return self.global_frozen

    @arc4.abimethod(readonly=True, resource_encoding="index")
    def get_account_is_frozen(
        self, *, freeze_asset: Asset, freeze_account: Account
    ) -> bool:
        """
        Get Smart ASA account frozen status

        Args:
            freeze_asset: Smart ASA ID
            freeze_account: Account to check

        Returns:
            Smart ASA account frozen status
        """
        # Preconditions
        self._assert_common_preconditions(freeze_asset)

        # Effects
        return self._is_frozen(freeze_account)

    @arc4.abimethod(readonly=True, resource_encoding="index")
    def get_circulating_supply(self, *, asset: Asset) -> UInt64:
        """
        Get Smart ASA circulating supply

        Args:
            asset: Smart ASA ID

        Returns:
            Smart ASA circulating supply
        """
        # Preconditions
        self._assert_common_preconditions(asset)

        # Effects
        return self._circulating_supply(asset)
