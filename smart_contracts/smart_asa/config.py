from typing import Final

# State Schema
GLOBAL_BYTES: Final[int] = 8
GLOBAL_UINTS: Final[int] = 5
LOCAL_BYTES: Final[int] = 0
LOCAL_UINTS: Final[int] = 0

# Controlled ASA
TOTAL: Final[int] = 2**64 - 1
DECIMALS: Final[int] = 0
DEFAULT_FROZEN: Final[bool] = True

# Smart ASA
METADATA_HASH_LENGTH: Final[int] = 32

# Freeze exception boxes: key prefix + address (32 bytes), with an empty value
FREEZE_EXCEPTION_KEY_PREFIX: Final[bytes] = b"f"
FREEZE_EXCEPTION_BOX_MBR: Final[int] = 2_500 + 400 * (1 + 32)
