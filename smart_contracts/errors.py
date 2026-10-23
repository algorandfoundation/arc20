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

# ── Roles ─────────────────────────────────────────────────────────────────────
# The Reserve is disabled (ZeroAddress) for good
DISABLED_RESERVE: LiteralString = "reserveDisabled"

# The Freeze is disabled (ZeroAddress) for good
DISABLED_FREEZE: LiteralString = "freezeDisabled"

# The Clawback is disabled (ZeroAddress) for good
DISABLED_CLAWBACK: LiteralString = "clawbackDisabled"

# ── Account freeze boxes ──────────────────────────────────────────────────────
# A new account freeze box needs a payment of at least its MBR to the App, just
# before the call
BOX_MBR_UNFUNDED: LiteralString = "boxMbrUnfunded"

# ── Freeze ────────────────────────────────────────────────────────────────────
# The Smart ASA is globally frozen
GLOBAL_FROZEN: LiteralString = "globalFrozen"

# The sender account is frozen
SENDER_FROZEN: LiteralString = "senderFrozen"

# The receiver account is frozen
RECEIVER_FROZEN: LiteralString = "receiverFrozen"

# The Reserve account is frozen
RESERVE_FROZEN: LiteralString = "reserveFrozen"

# ── Configuration ─────────────────────────────────────────────────────────────
# Invalid total, it must not be lower than the issued supply
INVALID_TOTAL: LiteralString = "totalInvalid"

# Invalid metadata hash, it must be 32 bytes
INVALID_METADATA_HASH_LENGTH: LiteralString = "metadataHashInvalid"

# ── Transfers ─────────────────────────────────────────────────────────────────
# Issuing to the Smart ASA Application is forbidden
SELF_ISSUE: LiteralString = "selfIssue"

# Issuing above the total is forbidden
OVER_ISSUE: LiteralString = "overIssue"

# Redeeming units of another holder is forbidden (claw them back first)
CLAWBACK_REDEEM: LiteralString = "clawbackRedeem"

# ── Destroy ───────────────────────────────────────────────────────────────────
# Units are still issued: return them to the Smart ASA Application first
UNITS_ISSUED: LiteralString = "unitsIssued"

# Account freeze boxes are left: reset the accounts to the default freeze state first
FREEZE_BOXES_LEFT: LiteralString = "freezeBoxesLeft"

# ── ASA Metadata Registry ─────────────────────────────────────────────────────
# The ASA Metadata Registry App ID is not set
MISSING_ASA_METADATA_REGISTRY: LiteralString = "registryNotSet"

# The ASA Metadata Registry MBR payment is missing
INVALID_ASA_METADATA_REGISTRY_MBR_PAYMENT: LiteralString = "registryMbrPaymentInvalid"

# The transaction is not an ASA Metadata Registry call
INVALID_ASA_METADATA_REGISTRY_CALL: LiteralString = "registryCallInvalid"

# The group must return the Controlled ASA roles to the Smart ASA Application
INVALID_CTRL_ASA_RBAC_RECONFIG: LiteralString = "ctrlAsaRbacInvalid"
