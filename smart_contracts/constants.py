from typing import Final

# Algorand Network
MAINNET_GH_B64: Final[str] = "wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8="
TESTNET_GH_B64: Final[str] = "SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI="

# ARC-90
ARC90_URI_SCHEME_NAME: Final[bytes] = b"algorand"
ARC90_URI_APP_PATH_NAME: Final[bytes] = b"app"
ARC90_URI_BOX_QUERY_NAME: Final[bytes] = b"box"

ARC90_URI_PATH_SEP: Final[bytes] = b"/"

ARC90_URI_SCHEME: Final[bytes] = ARC90_URI_SCHEME_NAME + b"://"
ARC90_URI_APP_PATH: Final[bytes] = ARC90_URI_APP_PATH_NAME + ARC90_URI_PATH_SEP
ARC90_URI_BOX_QUERY: Final[bytes] = b"?" + ARC90_URI_BOX_QUERY_NAME + b"="
