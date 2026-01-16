from algopy import (
    Account,
    Asset,
    Bytes,
    Global,
    String,
    TemplateVar,
    UInt64,
    itxn,
    subroutine,
)

from .constants import (
    ARC90_URI_APP_PATH,
    ARC90_URI_BOX_QUERY,
    ARC90_URI_PATH_SEP,
    ARC90_URI_SCHEME,
    MAINNET_GH_B64,
)
from .template_vars import ARC90_NETAUTH


@subroutine
def itoa(i: UInt64) -> Bytes:
    # ASCII digits (valid UTF-8)
    digits = Bytes(b"0123456789")
    acc = Bytes(b"")

    while i > 0:
        d = i % UInt64(10)
        acc = digits[d : d + UInt64(1)] + acc
        i //= UInt64(10)

    return acc or Bytes(b"0")


@subroutine
def inner_asset_config(
    *,
    total: UInt64,
    decimals: UInt64,
    default_frozen: bool,
    unit_name: String,
    name: String,
    url: String,
    manager: Account,
    reserve: Account,
    freeze: Account,
    clawback: Account,
) -> UInt64:
    return (
        itxn.AssetConfig(
            fee=0,
            total=total,
            decimals=decimals,
            default_frozen=default_frozen,
            unit_name=unit_name,
            asset_name=name,
            url=url,
            manager=manager,
            reserve=reserve,
            freeze=freeze,
            clawback=clawback,
        )
        .submit()
        .created_asset.id
    )


@subroutine
def inner_asset_transfer(
    *,
    xfer_asset: Asset,
    asset_amount: UInt64,
    asset_sender: Account,
    asset_receiver: Account,
) -> None:
    itxn.AssetTransfer(
        fee=0,
        xfer_asset=xfer_asset.id,
        asset_amount=asset_amount,
        asset_sender=asset_sender,
        asset_receiver=asset_receiver,
    ).submit()


@subroutine
def inner_asset_destroy(*, destroy_asset: Asset) -> None:
    itxn.AssetConfig(
        fee=0,
        config_asset=destroy_asset,
    ).submit()


@subroutine
def arc90_box_query(app_id: UInt64, box_name: Bytes) -> Bytes:
    if Global.genesis_hash == Bytes.from_base64(MAINNET_GH_B64):
        arc90_netauth = Bytes()
    else:
        arc90_netauth = TemplateVar[Bytes](ARC90_NETAUTH) + ARC90_URI_PATH_SEP
    return (
        ARC90_URI_SCHEME
        + arc90_netauth
        + ARC90_URI_APP_PATH
        + itoa(app_id)
        + ARC90_URI_BOX_QUERY
        + box_name
    )
