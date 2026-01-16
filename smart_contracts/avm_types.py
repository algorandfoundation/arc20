from algopy import Account, Bytes, String, Struct, UInt64, arc4


class AssetConfig(Struct, kw_only=True):
    """Smart ASA Configuration"""

    total: UInt64
    decimals: arc4.UInt32
    default_frozen: bool
    unit_name: String
    name: String
    url: String
    metadata_hash: Bytes
    manager_addr: Account
    reserve_addr: Account
    freeze_addr: Account
    clawback_addr: Account
