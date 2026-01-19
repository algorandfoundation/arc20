from abc import ABC, abstractmethod

from algopy import Account, ARC4Contract, Asset, Bytes, String, UInt64, arc4, gtxn

from .avm_types import AssetConfig


class Arc20Interface(ARC4Contract, ABC):
    """
    ARC-0020 (Smart ASA) - Interface
    """

    @abstractmethod
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
        pass

    @abstractmethod
    @arc4.abimethod(allow_actions=["OptIn"])
    def asset_opt_in(
        self, *, asset: Asset, ctrl_asa_opt_in: gtxn.AssetTransferTransaction
    ) -> None:
        pass

    @abstractmethod
    @arc4.abimethod
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
        manager_addr: Account,
        reserve_addr: Account,
        freeze_addr: Account,
        clawback_addr: Account,
    ) -> None:
        pass

    @abstractmethod
    @arc4.abimethod
    def asset_transfer(
        self,
        *,
        xfer_asset: Asset,
        asset_amount: UInt64,
        asset_sender: Account,
        asset_receiver: Account,
    ) -> None:
        pass

    @abstractmethod
    @arc4.abimethod
    def asset_freeze(self, *, freeze_asset: Asset, asset_frozen: bool) -> None:
        pass

    @abstractmethod
    @arc4.abimethod
    def account_freeze(
        self, *, freeze_asset: Asset, freeze_account: Account, asset_frozen: bool
    ) -> None:
        pass

    @abstractmethod
    @arc4.abimethod(allow_actions=["CloseOut"])
    def asset_close_out(self, *, close_asset: Asset, close_to: Account) -> None:
        pass

    @abstractmethod
    @arc4.abimethod(allow_actions=["DeleteApplication"])
    def asset_destroy(self, *, destroy_asset: Asset) -> None:
        pass

    @abstractmethod
    @arc4.abimethod(readonly=True)
    def get_asset_config(self, *, asset: Asset) -> AssetConfig:
        pass

    @abstractmethod
    @arc4.abimethod(readonly=True)
    def get_asset_is_frozen(self, *, freeze_asset: Asset) -> bool:
        pass

    @abstractmethod
    @arc4.abimethod(readonly=True)
    def get_account_is_frozen(
        self, *, freeze_asset: Asset, freeze_account: Account
    ) -> bool:
        pass

    @abstractmethod
    @arc4.abimethod(readonly=True)
    def get_circulating_supply(self, *, asset: Asset) -> UInt64:
        pass
