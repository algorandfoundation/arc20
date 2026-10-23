# ARC-20 Reference Implementation

This is the reference implementation of Smart ASA based on the [ARC-20 specification](https://dev.algorand.co/arc-standards/arc-0020/).
Where the specification leaves room, it is stricter (e.g., the metadata hash must be
32 bytes, and `default_frozen` is set on creation only).

> ⚠️ This reference implementation has not been audited: review and test it before
> using it in production.

The implementation offers:

- A basic [Smart ASA](#smart-asa);

- A [Smart ASA with ASA Metadata Registry integration](#smart-asa-with-asa-metadata-registry-integration)
(**RECOMMENDED**);

- An [example extension](#extending-regular-transfers) with custom regular transfer checks.

| Path                                | Content                                                       |
|:------------------------------------|:--------------------------------------------------------------|
| `smart_contracts/smart_asa/`        | Smart ASA: contract, configuration, deployment script         |
| `smart_contracts/arc89_smart_asa/`  | Smart ASA with ASA Metadata Registry integration              |
| `smart_contracts/capped_smart_asa/` | Example extension (not deployed)                              |
| `smart_contracts/errors.py`         | ARC-65 error codes                                            |
| `smart_contracts/artifacts/`        | Compiled TEAL, ARC-56 App Specs and typed Python clients      |
| `tests/`                            | Tests, a folder per contract                                  |

The reference implementation:

- Stores account freezes in [Boxes](#account-freeze-boxes): holders don't opt in to
  the Smart ASA Application;
- Allows a single Controlled ASA per Smart ASA Application.

Future application enhancements may include:

- Allowing multiple Controlled ASAs per Smart ASA Application.

## Smart ASA

The ASA URL (`au`) and the ASA Metadata Hash (`am`) fields of the underlying Controlled
ASA are initialized with the corresponding Smart ASA fields on creation.

The fields on the underlying Controlled ASA are _immutable_, while the fields of
the Smart ASA can be updated by the Smart ASA Manager after creation.

ARC-20 requires a Smart ASA to specify the ID of its controlling Application. The
basic Smart ASA does not publish it by itself: the Controlled ASA is configured only
by the Smart ASA Application, so no [ARC-69](https://dev.algorand.co/arc-standards/arc-0069/)
metadata can be attached later. To make the Smart ASA discoverable, either:

- Set the `url` and `metadata_hash` on creation to [ARC-3](https://dev.algorand.co/arc-standards/arc-0003/)
  metadata including the Application ID under `properties.arc-20.application-id`
  (the Application ID is known before calling `asset_create`); or
- Use the [Smart ASA with ASA Metadata Registry integration](#smart-asa-with-asa-metadata-registry-integration),
  which publishes it in the ASA Metadata Registry.

The basic Smart ASA deployment script does neither.

## Smart ASA with ASA Metadata Registry Integration

The Smart ASA implementation integrates with the ASA Metadata Registry.

The ASA URL (`au`) and the ASA Metadata Hash (`am`) fields of the underlying Controlled
ASA are initialized with the corresponding Smart ASA fields on creation and **MUST** be
set according to the [ARC-89 specification](https://dev.algorand.co/arc-standards/arc-0089/)

The Asset Metadata on the ASA Metadata Registry is managed by the ASA Manager.

Since the Controlled ASA Manager is assigned to the Smart ASA Application, the interaction
with the ASA Metadata Registry is achieved by a _"Flash Asset Metadata Manager"_
technique: the Smart ASA Application grants the Controlled ASA Manager to the Smart
ASA Manager, just for an atomic interaction with the ASA Metadata Registry and immediately
revokes it after the operation.

The following is the structure of a Smart ASA - ASA Metadata Registry atomic interaction:

- `[Txn: 0]`: Call to the Smart ASA `asa_metadata_registry_init`  method to initialize
  the interaction with ASA Metadata Registry, and granting the Controlled ASA Manager 
  role to the Smart ASA Manager;

- `[Txn: 1...N]`: Calls to the ASA Metadata Registry Application to perform the
  desired operation (e.g., create or update the Asset Metadata), optionally preceded
  by one MBR payment (operations needing more payments, or elsewhere, aren't supported);

- `[Txn: N+1]`: `AssetConfig` transaction that returns the Controlled ASA RBAC
  back to the original Smart ASA Application.

The Smart ASA Application ensures that the Controlled ASA Manager role is granted
to the Smart ASA Manager, only for the duration of the atomic interaction with the
ASA Metadata Registry (of any kind), and that it is revoked immediately after.

The ASA Metadata Registry App ID is set on deployment (`ARC89_APP_ID` template variable):
the Smart ASA Application creation fails if it's missing.

## Roles and Transfers

Both Smart ASA variants share the same roles and transfer rules.

### Roles

| Role     | Can                                                                                                                                                                                                                                                                                            | If set to `ZeroAddress`                                        |
|:---------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------|
| Creator  | Create the Smart ASA (`asset_create`), once                                                                                                                                                                                                                                                    | –                                                              |
| Manager  | Configure (`asset_config`) and destroy (`asset_destroy`, which also deletes the Application and sends its ALGO to the Manager) the Smart ASA, withdraw the Application ALGO above its MBR (`withdraw_excess_algo`), and interact with the ASA Metadata Registry (`asa_metadata_registry_init`) | Configuration is locked, destroy and withdrawal are impossible |
| Reserve  | Issue and redeem, if not frozen                                                                                                                                                                                                                                                                | Issuing and redeeming are disabled for good                    |
| Freeze   | Freeze the whole Smart ASA (`asset_freeze`) or any account (`account_freeze`)                                                                                                                                                                                                                  | Freezes are permanent                                          |
| Clawback | Move units between holders, regardless of freezes                                                                                                                                                                                                                                              | Clawback is disabled for good                                  |

The Smart ASA Application holds the units not issued yet and all the Controlled ASA
roles. A role set to the Application address can't be used either (the Application
can't sign transactions), but, unlike `ZeroAddress`, the Manager can reassign it.

The Manager can update any Smart ASA field (e.g., `decimals`), except that `total`
can't go below the issued supply, disabled roles stay disabled, and `default_frozen`
is set on creation only (as for native ASA, `asset_config` ignores it). The Manager
can also assign itself any role, use it and restore the roles within one atomic group:
role separation is only as strong as the Manager.

The Manager can destroy the Smart ASA once all units are back in the Smart ASA Application
(`ERR:unitsIssued`) and no account freeze box is left (`ERR:freezeBoxesLeft`,
see [MBR management](#mbr-management)).

### Transfer paths

`asset_transfer` takes the first matching path:

| Path     | When                        | Signer         | Freeze checks                | Other checks                                     |
|:---------|:----------------------------|:---------------|:-----------------------------|:-------------------------------------------------|
| Issue    | `asset_sender` is the App   | Reserve        | Smart ASA, Reserve, receiver | Receiver is not the App; issued supply ≤ `total` |
| Redeem   | `asset_receiver` is the App | Reserve        | Smart ASA, Reserve           | Sender is the Reserve                            |
| Clawback | Signer is the Clawback      | Clawback       | None                         | –                                                |
| Regular  | Otherwise                   | `asset_sender` | Smart ASA, sender, receiver  | –                                                |

Accounts must hold the Controlled ASA, as for any ASA, but don't opt in to the Smart
ASA Application. As for native ASA, transfers of `0` units need no holding (freeze
checks still apply).

Holders leave by closing out the Controlled ASA. Its holdings are frozen at protocol
level, so units can only be closed out to its creator, the Smart ASA Application,
which redeems them: to keep them, transfer them first (e.g., in the same group).

Transfers from or to the Smart ASA Application always issue or redeem units, so a regular
holder or the Clawback can't use it as a counterparty.

### Redeeming

Redeeming is not exclusive to the Reserve. Any holder can surrender its whole balance to
the Smart ASA Application at any time, even if frozen or if the Smart ASA is globally
frozen, by closing out the Controlled ASA to its creator (the protocol allows it on
frozen holdings). The Clawback can do the same for any holder, by first clawing the
units back to itself.

Holders can't redeem part of their balance: `asset_transfer` to the Smart ASA Application
is reserved to the Reserve. Redeemed units are not burned: they can be issued again.

### Supply

The _issued supply_ is the amount of units outside the Smart ASA Application, which
holds the units not issued yet: issuing and redeeming move units out of and into it.
Wallets applying the ASA convention (Controlled ASA `total` minus its reserve balance)
compute the same amount. The Smart ASA `total` caps the issued supply (`ERR:overIssue`,
`ERR:totalInvalid`), and `asset_destroy` requires none (`ERR:unitsIssued`).

The _circulating supply_ (`get_circulating_supply`) is:

- For the basic Smart ASA, the issued supply: units held by the Reserve circulate, so
  the Reserve should issue on demand rather than keep a float;
- For the Smart ASA with ASA Metadata Registry integration, the issued supply minus
  the units held by the Reserve: the Reserve can keep a treasury, issued but not
  circulating. This variant also implements [ARC-62](https://github.com/algorandfoundation/ARCs/blob/main/ARCs/arc-0062.md)
  (`arc62_get_circulating_supply`), and both getters always return the same value.
  Nothing is excluded while the Reserve is disabled or set to the Smart ASA Application,
  and reassigning the Reserve changes which holdings are excluded. The getters need the
  Reserve account reference (AlgoKit clients populate it by simulation).

### Freeze model

Freeze can stop units, never move them: at worst it affects availability, never balances.

| Movement                               | Account freeze                                   | Global freeze |
|:---------------------------------------|:-------------------------------------------------|:--------------|
| Regular transfer                       | Blocked if the sender or the receiver is frozen  | Blocked       |
| Issue                                  | Blocked if the Reserve or the receiver is frozen | Blocked       |
| Redeem                                 | Blocked if the Reserve is frozen                 | Blocked       |
| Clawback                               | Never blocked                                    | Never blocked |
| Surrender to the Smart ASA Application | Never blocked                                    | Never blocked |

- **The Reserve obeys Freeze.** Freeze is the circuit breaker of issuance: a halt means
  no new units, and freezing the Reserve stops a compromised issuance key without halting
  the market.
- **The Clawback ignores Freeze.** Seizures and recoveries are what freezes prepare
  for, often during a halt. Only the Manager can stop the Clawback, by replacing it.
- **Roles held by the same account compose.** Each action follows its own role's rules:
  a Reserve that is also the Clawback issues and redeems as Reserve, and claws back as Clawback.
- **Surrender is always possible.** The protocol lets holders return their whole balance
  to the creator: units can only flow back to the issuer.
- **A disabled role leaves its state as it is.** With Freeze set to `ZeroAddress`,
  freezes can't change anymore: e.g., a global freeze becomes permanent.

Multi-role operations run as one atomic group, so nobody can act in between, e.g.:

- Planned issuance during a halt: `[Freeze: unfreeze, Reserve: issue, Freeze: freeze]`;
- Forced redemption, by a Reserve that is also the Clawback: `[Clawback: holder → itself, Reserve: redeem]`.

### Freeze profiles

`default_frozen`, set on creation and immutable, is the freeze state of every account,
unless Freeze sets it otherwise (with an [account freeze box](#account-freeze-boxes)):

- **Blacklist** (`False`): accounts are unfrozen until Freeze freezes them.
- **Whitelist** (`True`): accounts are frozen until Freeze approves them. Recommended
  for regulated assets.

In both profiles, freezes belong to the address, not to its holding: Freeze can set
them before an account holds units (e.g., from a sanctions list), they survive the
account leaving and coming back, and only Freeze can change them.

### Scenarios

| Scenario                 | Setup                                                           | How it works                                                                                                                                                                                                     |
|:-------------------------|:----------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Tokenized security       | Whitelist; separate Reserve, Freeze and Clawback                | Freeze approves the Reserve and, after KYC, each investor. The Reserve issues to approved investors only. A trading halt stops trading and issuance; corporate actions run in atomic groups during the halt      |
| Court order, sanctions   | Any                                                             | Freeze freezes the named account, even before it holds units, and the freeze survives leaving. The Clawback seizes the units into custody, even during a halt. The holder can only surrender units to the issuer |
| Compromised issuance key | Any                                                             | Freeze freezes the Reserve, then the Manager replaces the Reserve                                                                                                                                                |
| Permissionless token     | Blacklist; Freeze and Clawback disabled while nothing is frozen | Holdings can never be frozen nor seized                                                                                                                                                                          |
| Soulbound token          | Whitelist; Freeze disabled after approving the Reserve          | Holdings stay frozen forever. The Reserve issues to itself and the Clawback delivers; holders can only surrender units                                                                                           |

### Wallets

The Controlled ASA has `0` decimals and a total of `2^64-1` units, regardless of
the Smart ASA configuration. Wallets not supporting ARC-20 display raw base units
and that total; ARC-20 aware clients should read the Smart ASA configuration with
`get_asset_config`.

Calls checking account freezes (`asset_transfer`, `account_freeze`, `get_account_is_frozen`)
must reference the boxes of the accounts involved, existing or not: a box name is `f`
followed by the account address (the `freeze_exceptions` box map of the ARC-56 App Spec).
AlgoKit clients populate the references by simulating the call.

## Account Freeze Boxes

The Smart ASA Application keeps an empty Box for each account whose freeze state differs
from `default_frozen`: the box existence is the exception. Accounts without a box have
the default freeze state.

Compared to App Local State, Boxes:

- Need no Smart ASA Application opt-in, as ARC-20 recommends: holders only opt in to
  the Controlled ASA, as for any ASA, locking 0.1 ALGO of MBR instead of 0.2285 ALGO;
- Can't be deleted by holders, as App Local State is by a `ClearState`: freezes stick
  in both profiles, so freezing the Reserve is reliable;
- Apply to any address, even before it holds units;
- Can be listed (e.g., with algod `/v2/applications/{app-id}/boxes`), to audit all
  the exceptions to `default_frozen`.

### MBR management

Each box locks 0.0157 ALGO of MBR (2,500 + 400 per byte of its 33-byte name, in µALGO)
in the Smart ASA Application account, besides the account and the Controlled ASA MBR
(0.1 ALGO each).

- **Boxes are deposits.** A freeze that creates a box needs a payment of at least its MBR
  to the Smart ASA Application just before `account_freeze` in the group, from any sender
  (`ERR:boxMbrUnfunded`): the Smart ASA Application never pays for boxes itself. Resetting
  the account to `default_frozen` deletes the box and refunds its MBR to Freeze, whoever
  deposited it. Deposits grow with the exceptions: a box per frozen account in a Blacklist,
  per approved account in a Whitelist.
- **Only the Manager gets the rest.** The Smart ASA Application doesn't track who paid, and
  callers cover its inner transaction fees. Any ALGO above the MBR (overpaid deposits,
  stray payments) only leaves to the Manager: at any time with `withdraw_excess_algo`
  (non-normative), or with `asset_destroy`, together with the account and Controlled ASA
  MBR. Deleting the Application also releases the Creator's own MBR for it (programs and
  global state).
- **No orphan boxes.** `asset_destroy` requires no box left (`ERR:freezeBoxesLeft`):
  Freeze resets all accounts to `default_frozen` first, getting the deposits back. If the
  Smart ASA can never be destroyed (Manager disabled, or Freeze disabled with boxes left),
  its ALGO is locked for good.

For example, Freeze freezes (Blacklist) or approves (Whitelist) an account without a box
with `[Freeze: pay 0.0157 ALGO to the App, Freeze: account_freeze]`, and resets it with
`[Freeze: account_freeze]`, whose fee also covers the refund (0 ALGO for an account
without a box). In a batch, each freeze follows its own deposit (identical deposits need
distinct notes).

## Extending Regular Transfers

Extensions can add checks to regular transfers, keeping all the rules above: override
`_regular_transfer_hook` in a subclass of either Smart ASA Application. It runs only on
regular transfers (not on issuances, redemptions or clawbacks), after the built-in checks, so it
can only reject more transfers. Holders can't bypass it: Controlled ASA holdings are
frozen, so every transfer between holders is a regular `asset_transfer`. The reference
implementation adds no checks, at no program cost.

For example, the [Capped Smart ASA](smart_contracts/capped_smart_asa/contract.py) caps
the holdings that regular transfers can reach (see its
[tests](tests/capped_smart_asa/test_regular_transfer_hook.py)):

```python
class CappedSmartAsa(SmartAsa, state_totals=...):  # Same schema as the Smart ASA
    def _regular_transfer_hook(
        self, *, asset_sender: Account, asset_receiver: Account, asset_amount: UInt64
    ) -> None:
        holding, _holds = op.AssetHoldingGet.asset_balance(
            asset_receiver, self.smart_asa_id
        )
        logged_assert(
            holding + asset_amount <= capped_cfg.MAX_HOLDING,
            capped_err.HOLDING_CAP_EXCEEDED,
        )
```

When writing a hook:

- Override only the hook, not `asset_transfer` or the `_assert_*` methods, and call
  `super()._regular_transfer_hook(...)` to chain hooks. Extensions can also refine
  `_circulating_supply`, as the Smart ASA with ASA Metadata Registry integration does
  (see [Supply](#supply));
- Fail with `logged_assert` and new ARC-65 codes, distinct from the reference ones;
- Handle transfers of `0` units, also between non-holders (e.g., read holdings with
  `AssetHoldingGet`, which doesn't fail on non-holders);
- Keep custom state in boxes, so the state schema (checked on creation) doesn't change.
  New boxes need their own MBR funding: the Smart ASA Application spare ALGO is the
  Manager's;
- Calls reading more boxes, accounts or Applications need their references (AlgoKit
  clients populate them by simulation), and heavy checks may need more opcode budget.

## Errors

Failed calls return [ARC-65](https://dev.algorand.co/arc-standards/arc-0065/) errors:
the Smart ASA Application logs `ERR:<code>` (e.g., `ERR:unauthorizedManager`) before
failing, and ARC-56 clients show the same code. The error codes are defined in
[`errors.py`](smart_contracts/errors.py).

Checks generated by the compiler (ARC-4 routing, ABI argument decoding, group transaction
types) fail without an ARC-65 error.

## Deployments

Deploy on LocalNet

```shell
algokit project deploy localnet arc89_smart_asa
algokit explore
```

1. Download the [ARC-56 App Spec JSON file](./smart_contracts/artifacts/arc89_smart_asa/Arc89SmartAsa.arc56.json);
1. Navigate to the [Lora App Lab](https://lora.algokit.io/testnet/app-lab);
1. Create the App Interface using the deployed App ID and App Spec JSON;
1. Explore the Smart ASA interface.

## Local Setup and Tests

This reference implementation is developed with [AlgoKit](https://algorand.co/algokit).

- Install AlgoKit
- Setup your virtual environment (managed with [Poetry](https://python-poetry.org/))

```shell
algokit bootstrap all
```

- Start your Algorand LocalNet (requires [Docker](https://www.docker.com/get-started/))

```shell
algokit localnet start
```

- Run tests (managed with PyTest)

```shell
algokit project run test
```

or, for verbose results:

```shell
poetry run pytest -s -v tests/<test_case>.py
```
