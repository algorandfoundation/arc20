# This file is auto-generated, do not modify
# flake8: noqa
# fmt: off
import typing

import algopy

class AssetConfig(algopy.arc4.Struct):
    total: algopy.arc4.UIntN[typing.Literal[64]]
    decimals: algopy.arc4.UIntN[typing.Literal[32]]
    default_frozen: algopy.arc4.Bool
    unit_name: algopy.arc4.String
    name: algopy.arc4.String
    url: algopy.arc4.String
    metadata_hash: algopy.arc4.DynamicBytes
    manager_addr: algopy.arc4.Address
    reserve_addr: algopy.arc4.Address
    freeze_addr: algopy.arc4.Address
    clawback_addr: algopy.arc4.Address

class Arc89SmartAsa(algopy.arc4.ARC4Client, typing.Protocol):
    """

        Smart ASA (ARC-20) Reference Implementation, with ASA Metadata Registry (ARC-89) integration.
    
    """
    @algopy.arc4.abimethod
    def asa_metadata_registry_init(
        self,
        asset: algopy.arc4.UIntN[typing.Literal[64]],
        calls: algopy.arc4.UIntN[typing.Literal[64]],
        has_mbr_payment: algopy.arc4.Bool,
    ) -> None: ...

    @algopy.arc4.abimethod(readonly=True)
    def arc62_get_circulating_supply(
        self,
        asset_id: algopy.arc4.UIntN[typing.Literal[64]],
    ) -> algopy.arc4.UIntN[typing.Literal[64]]:
        """
        Get Smart ASA circulating supply
        """

    @algopy.arc4.abimethod
    def asset_create(
        self,
        total: algopy.arc4.UIntN[typing.Literal[64]],
        decimals: algopy.arc4.UIntN[typing.Literal[32]],
        default_frozen: algopy.arc4.Bool,
        unit_name: algopy.arc4.String,
        name: algopy.arc4.String,
        url: algopy.arc4.String,
        metadata_hash: algopy.arc4.DynamicBytes,
        manager_addr: algopy.arc4.Address,
        reserve_addr: algopy.arc4.Address,
        freeze_addr: algopy.arc4.Address,
        clawback_addr: algopy.arc4.Address,
    ) -> algopy.arc4.UIntN[typing.Literal[64]]:
        """
        Create the Controlled ASA
        """

    @algopy.arc4.abimethod(resource_encoding='index')
    def asset_config(
        self,
        config_asset: algopy.Asset,
        total: algopy.arc4.UIntN[typing.Literal[64]],
        decimals: algopy.arc4.UIntN[typing.Literal[32]],
        default_frozen: algopy.arc4.Bool,
        unit_name: algopy.arc4.String,
        name: algopy.arc4.String,
        url: algopy.arc4.String,
        metadata_hash: algopy.arc4.DynamicBytes,
        manager_addr: algopy.arc4.Address,
        reserve_addr: algopy.arc4.Address,
        freeze_addr: algopy.arc4.Address,
        clawback_addr: algopy.arc4.Address,
    ) -> None:
        """
        Configure Smart ASA (for unchanged parameters use existing value - no optional args on AVM)
        """

    @algopy.arc4.abimethod(resource_encoding='index')
    def asset_transfer(
        self,
        xfer_asset: algopy.Asset,
        asset_amount: algopy.arc4.UIntN[typing.Literal[64]],
        asset_sender: algopy.Account,
        asset_receiver: algopy.Account,
    ) -> None:
        """
        Smart ASA transfers: regular, clawback, issue, redeem
        """

    @algopy.arc4.abimethod(resource_encoding='index')
    def asset_freeze(
        self,
        freeze_asset: algopy.Asset,
        asset_frozen: algopy.arc4.Bool,
    ) -> None:
        """
        Smart ASA global freeze (all accounts)
        """

    @algopy.arc4.abimethod(resource_encoding='index')
    def account_freeze(
        self,
        freeze_asset: algopy.Asset,
        freeze_account: algopy.Account,
        asset_frozen: algopy.arc4.Bool,
    ) -> None:
        """
        Smart ASA local freeze (account specific)
        """

    @algopy.arc4.abimethod(resource_encoding='index', allow_actions=['DeleteApplication'])
    def asset_destroy(
        self,
        destroy_asset: algopy.Asset,
    ) -> None:
        """
        Destroy the Smart ASA
        """

    @algopy.arc4.abimethod
    def withdraw_excess_algo(
        self,
    ) -> None:
        """
        Withdraw the App ALGO above its MBR to the Manager (non-normative)
        """

    @algopy.arc4.abimethod(readonly=True, resource_encoding='index')
    def get_asset_config(
        self,
        asset: algopy.Asset,
    ) -> AssetConfig:
        """
        Get Smart ASA configuration
        """

    @algopy.arc4.abimethod(readonly=True, resource_encoding='index')
    def get_asset_is_frozen(
        self,
        freeze_asset: algopy.Asset,
    ) -> algopy.arc4.Bool:
        """
        Get Smart ASA global frozen status
        """

    @algopy.arc4.abimethod(readonly=True, resource_encoding='index')
    def get_account_is_frozen(
        self,
        freeze_asset: algopy.Asset,
        freeze_account: algopy.Account,
    ) -> algopy.arc4.Bool:
        """
        Get Smart ASA account frozen status
        """

    @algopy.arc4.abimethod(readonly=True, resource_encoding='index')
    def get_circulating_supply(
        self,
        asset: algopy.Asset,
    ) -> algopy.arc4.UIntN[typing.Literal[64]]:
        """
        Get Smart ASA circulating supply
        """
