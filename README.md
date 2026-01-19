# ARC-20 Reference Implementation

This is the reference implementation of Smart ASA based on the [ARC-20 specification](https://dev.algorand.co/arc-standards/arc-0020/).

The implementation offers:

- A basic [Smart ASA](#smart-asa);

- A [Smart ASA with ASA Metadata Registry integration](#smart-asa-with-asa-metadata-registry-integration)
(**RECOMMENDED**).

## Smart ASA

The ASA URL (`au`) and the ASA Metadata Hash (`am`) fields of the underlying Controlled
ASA are initialized the corresponding Smart ASA fields on creation.

The fields on the underlying Controlled ASA are _immutable_, while the fields of
the Smart ASA can be updated by the Smart ASA Manager after creation.

## Smart ASA with ASA Metadata Registry Integration

The Smart ASA implementation integrates with the ASA Metadata Registry.

The ASA URL (`au`) and the ASA Metadata Hash (`am`) fields of the underlying Controlled
ASA are initialized the corresponding Smart ASA fields on creation and **MUST** be
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
to the Smart ASA Mnanger, only for the duration of the atomic interaction with the
ASA Metadata Registry (of any kind), and that it is revoked immediately after.

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
