# ARC-20 Reference Implementation

This is the reference implementation of Smart ASA based on the [ARC-20 specification](https://dev.algorand.co/arc-standards/arc-0020/).

The implementation offers:

- A basic [Smart ASA](#smart-asa);

- A [Smart ASA with ASA Metadata Registry integration](#smart-asa-with-asa-metadata-registry-integration)
(**RECOMMENDED**).

The reference implementation:

- Stores Smart ASA opt-in state in the Local State of the Smart ASA Application;
- Allows a single Controlled ASA per Smart ASA Application.

Future application enhancements may include:

- Storing Smart ASA opt-in state in Boxes;
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
  desired operation (e.g., create or update the Asset Metadata) with eventual MBR
  payments (if needed);

- `[Txn: N+1]`: `AssetConfig` transaction that returns the Controlled ASA RBAC
  back to the original Smart ASA Application.

The Smart ASA Application ensures that the Controlled ASA Manager role is granted
to the Smart ASA Manager, only for the duration of the atomic interaction with the
ASA Metadata Registry (of any kind), and that it is revoked immediately after.

## Roles and Transfers

Both Smart ASA variants share the same roles and transfer rules.

### Roles

| Role     | Can                                                                                                                                                                                                                      | If set to `ZeroAddress`                        |
|:---------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------|
| Creator  | Create the Smart ASA (`asset_create`), once                                                                                                                                                                              | –                                              |
| Manager  | Configure (`asset_config`) and destroy (`asset_destroy`, which also deletes the Application and sends its ALGO to the Manager) the Smart ASA, and interact with the ASA Metadata Registry (`asa_metadata_registry_init`) | Configuration is locked, destroy is impossible |
| Reserve  | Mint and burn                                                                                                                                                                                                            | Minting and burning are disabled for good      |
| Freeze   | Freeze the whole Smart ASA (`asset_freeze`) or an account (`account_freeze`)                                                                                                                                             | The current freeze state is permanent          |
| Clawback | Move units between holders, regardless of freezes                                                                                                                                                                        | Clawback is disabled for good                  |

The Smart ASA Application holds the units not minted yet and all the Controlled ASA
roles. A role set to the Application address can't be used either (the Application
can't sign transactions), but, unlike `ZeroAddress`, the Manager can reassign it.

### Transfer paths

`asset_transfer` takes the first matching path:

| Path     | When                        | Signer         | Opted-in accounts | Freeze checks               | Other checks                                          |
|:---------|:----------------------------|:---------------|:------------------|:----------------------------|:------------------------------------------------------|
| Mint     | `asset_sender` is the App   | Reserve        | Receiver          | Smart ASA; receiver ¹       | Receiver is not the App; circulating supply ≤ `total` |
| Burn     | `asset_receiver` is the App | Reserve        | Sender ¹          | Smart ASA; sender ¹         | Sender is the Reserve ¹                               |
| Clawback | Signer is the Clawback      | Clawback       | Receiver          | None                        | –                                                     |
| Regular  | Otherwise                   | `asset_sender` | Sender, receiver  | Smart ASA, sender, receiver | –                                                     |

¹ Skipped if the Reserve is also the Clawback.

"Opted-in" refers to the Smart ASA Application. Accounts must also be opted in to
the Controlled ASA, as required by the protocol.

Holders close out with `asset_close_out` (OnComplete `CloseOut`), followed in the
same group by a Controlled ASA close-out (amount `0`) to the Smart ASA Application:

- To another account: the whole balance moves there, with the same checks as a regular
  transfer;
- To the Smart ASA Application: the whole balance is burned, regardless of freezes.

Transfers from or to the Smart ASA Application are always mints or burns, so a regular
holder or the Clawback can't use it as a counterparty.

### Burning

Burning is not exclusive to the Reserve. Any holder can return its whole balance to
the Smart ASA Application at any time, even if frozen or if the Smart ASA is globally
frozen: with `asset_close_out` to the Smart ASA Application, or with a plain Controlled
ASA close-out to its creator (the protocol allows it on frozen holdings). The Clawback
can do the same for any holder, by first clawing the units back to itself.

Holders can't burn part of their balance: `asset_transfer` to the Smart ASA Application
is reserved to the Reserve.

### Role combinations

- A Reserve that is also the Clawback can mint into frozen accounts and burn from any
  holder in a single transaction. Separate Reserve and Clawback accounts can do the
  same in two steps.
- A holder that is also the Clawback ignores freezes on its own units.
- The Manager can assign itself any role, use it and restore the roles within one
  atomic group: role separation is only as strong as the Manager.

### Freezing

- Accounts opt in frozen if the Smart ASA is `default_frozen`, or if they already hold
  units (e.g. after a `ClearState`), so a `ClearState` can't unfreeze units.
- As for native ASA, a freeze applies to the current holding: once an account holds
  no units, it can clear its App Local State and opt in again with the default freeze
  state.
- An account without App Local State counts as frozen (`get_account_is_frozen` returns
  `True`). The Clawback can still move its units.

### Wallets

The Controlled ASA has `0` decimals and a total of `2^64-1` units, regardless of
the Smart ASA configuration. Wallets not supporting ARC-20 display raw base units
and that total; ARC-20 aware clients should read the Smart ASA configuration with
`get_asset_config`.

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
