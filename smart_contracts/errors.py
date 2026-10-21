from typing import LiteralString

# ARC-65 error codes: the App logs `ERR:<code>` before failing

# ── Schema ────────────────────────────────────────────────────────────────────
# Wrong Global Bytes allocation
WRONG_GLOBAL_BYTES: LiteralString = "wrongGlobalBytes"

# Wrong Global UInts allocation
WRONG_GLOBAL_UINTS: LiteralString = "wrongGlobalUints"

# Wrong Local Bytes allocation
WRONG_LOCAL_BYTES: LiteralString = "wrongLocalBytes"

# Wrong Local UInts allocation
WRONG_LOCAL_UINTS: LiteralString = "wrongLocalUints"

# Wrong OnComplete action
WRONG_ON_COMPLETE: LiteralString = "wrongOnComplete"

# ── Auth ──────────────────────────────────────────────────────────────────────
# Unauthorized, it must be the Application creator
UNAUTHORIZED_CREATOR: LiteralString = "unauthorizedCreator"

# Unauthorized, it must be the Manager
UNAUTHORIZED_MANAGER: LiteralString = "unauthorizedManager"

# Unauthorized, it must be the Reserve
UNAUTHORIZED_RESERVE: LiteralString = "unauthorizedReserve"

# Unauthorized, it must be the Freeze
UNAUTHORIZED_FREEZE: LiteralString = "unauthorizedFreeze"

# Unauthorized, it must be the Clawback (or the asset sender)
UNAUTHORIZED_CLAWBACK: LiteralString = "unauthorizedClawback"

# ── Controlled ASA ────────────────────────────────────────────────────────────
# The Controlled ASA has not been created yet
MISSING_CTRL_ASA: LiteralString = "ctrlAsaNotExist"

# The Controlled ASA has already been created
EXISTING_CTRL_ASA: LiteralString = "ctrlAsaExist"

# The asset is not the Controlled ASA
INVALID_CTRL_ASA: LiteralString = "ctrlAsaInvalid"

# The account is not opted in to the Smart ASA Application
NOT_OPTED_IN: LiteralString = "accountNotOptedIn"

# ── Roles ─────────────────────────────────────────────────────────────────────
# The Reserve is disabled (ZeroAddress) for good
DISABLED_RESERVE: LiteralString = "reserveDisabled"

# The Freeze is disabled (ZeroAddress) for good
DISABLED_FREEZE: LiteralString = "freezeDisabled"

# The Clawback is disabled (ZeroAddress) for good
DISABLED_CLAWBACK: LiteralString = "clawbackDisabled"

# ── Freeze ────────────────────────────────────────────────────────────────────
# The Smart ASA is globally frozen
GLOBAL_FROZEN: LiteralString = "globalFrozen"

# The sender account is frozen
SENDER_FROZEN: LiteralString = "senderFrozen"

# The receiver account is frozen
RECEIVER_FROZEN: LiteralString = "receiverFrozen"

# The Reserve account is frozen
RESERVE_FROZEN: LiteralString = "reserveFrozen"

# ── Opt-in ────────────────────────────────────────────────────────────────────
# The Controlled ASA opt-in is for another asset
OPT_IN_WRONG_ASA: LiteralString = "optInWrongAsa"

# The Controlled ASA opt-in sender is not the caller
OPT_IN_WRONG_SENDER: LiteralString = "optInWrongSender"

# The Controlled ASA opt-in is a clawback
OPT_IN_WRONG_ASSET_SENDER: LiteralString = "optInWrongAssetSender"

# The Controlled ASA opt-in receiver is not the caller
OPT_IN_WRONG_RECEIVER: LiteralString = "optInWrongReceiver"

# The Controlled ASA opt-in amount is not 0
OPT_IN_WRONG_AMOUNT: LiteralString = "optInWrongAmount"

# The Controlled ASA opt-in closes out
OPT_IN_WRONG_CLOSE_TO: LiteralString = "optInWrongCloseTo"

# ── Close-out ─────────────────────────────────────────────────────────────────
# The Controlled ASA close-out is missing from the group
INVALID_CLOSE_OUT_GROUP_SIZE: LiteralString = "closeOutMissing"

# The Controlled ASA close-out is for another asset
CLOSE_OUT_WRONG_ASA: LiteralString = "closeOutWrongAsa"

# The Controlled ASA close-out sender is not the caller
CLOSE_OUT_WRONG_SENDER: LiteralString = "closeOutWrongSender"

# The Controlled ASA close-out amount is not 0
CLOSE_OUT_WRONG_AMOUNT: LiteralString = "closeOutWrongAmount"

# The Controlled ASA close-out is not to the Smart ASA Application
CLOSE_OUT_WRONG_CLOSE_TO: LiteralString = "closeOutWrongCloseTo"

# ── Configuration ─────────────────────────────────────────────────────────────
# Invalid total, it must not be lower than the circulating supply
INVALID_TOTAL: LiteralString = "totalInvalid"

# Invalid metadata hash, it must be 32 bytes
INVALID_METADATA_HASH_LENGTH: LiteralString = "metadataHashInvalid"

# ── Transfers ─────────────────────────────────────────────────────────────────
# Minting to the Smart ASA Application is forbidden
SELF_MINT: LiteralString = "selfMint"

# Minting above the total is forbidden
OVER_MINT: LiteralString = "overMint"

# Burning units of another holder is forbidden
CLAWBACK_BURN: LiteralString = "clawbackBurn"

# ── ASA Metadata Registry ─────────────────────────────────────────────────────
# The ASA Metadata Registry App ID is not set
MISSING_ASA_METADATA_REGISTRY: LiteralString = "registryNotSet"

# The ASA Metadata Registry MBR payment is missing
INVALID_ASA_METADATA_REGISTRY_MBR_PAYMENT: LiteralString = "registryMbrPaymentInvalid"

# The transaction is not an ASA Metadata Registry call
INVALID_ASA_METADATA_REGISTRY_CALL: LiteralString = "registryCallInvalid"

# The group must return the Controlled ASA roles to the Smart ASA Application
INVALID_CTRL_ASA_RBAC_RECONFIG: LiteralString = "ctrlAsaRbacInvalid"
