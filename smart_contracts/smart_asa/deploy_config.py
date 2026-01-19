# mypy: ignore-errors

import logging
from typing import Final

from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    CommonAppCallParams,
    OnSchemaBreak,
    OnUpdate,
)
from algokit_utils.config import config

logger = logging.getLogger(__name__)

APP_FUNDS: Final[AlgoAmount] = AlgoAmount(algo=1)

# ==============================================================================
# ASSET CREATION PARAMETERS
# ==============================================================================

ASA_TOTAL: Final[int] = 420
ASA_DECIMALS: Final[int] = 1
ASA_DEFAULT_FROZEN: Final[bool] = False
ASA_UNIT_NAME: Final[str] = "ARC-20"
ASA_NAME: Final[str] = "Smart ASA"
ASA_URL: Final[str] = "https://dev.algorand.co/arc-standards/arc-0020/"
ASA_METADATA_HASH: Final[bytes] = 32 * b"\x00"

# ==============================================================================
# SMART ASA DEPLOYMENT
# ==============================================================================


def deploy() -> None:
    from smart_contracts.artifacts.smart_asa.smart_asa_client import (
        AssetCreateArgs,
        SmartAsaFactory,
    )

    config.configure(debug=False)

    algorand = AlgorandClient.from_environment()
    deployer = algorand.account.from_environment("DEPLOYER")
    logger.info(f"Deployer address: {deployer.address}")

    factory = algorand.client.get_typed_app_factory(
        SmartAsaFactory,
        default_sender=deployer.address,
    )

    smart_asa_app_client, _ = factory.deploy(
        on_schema_break=OnSchemaBreak.AppendApp,
        on_update=OnUpdate.AppendApp,
    )
    logger.info(f"Smart ASA Application ID: {smart_asa_app_client.app_id}")

    algorand.account.ensure_funded_from_environment(
        account_to_fund=smart_asa_app_client.app_address,
        min_spending_balance=APP_FUNDS,
    )

    sp = smart_asa_app_client.algorand.client.algod.suggested_params()
    sp.flat_fee = True
    sp.fee = sp.min_fee * 2  # type: ignore

    asset_id = smart_asa_app_client.send.asset_create(
        AssetCreateArgs(
            total=ASA_TOTAL,
            decimals=ASA_DECIMALS,
            default_frozen=ASA_DEFAULT_FROZEN,
            unit_name=ASA_UNIT_NAME,
            name=ASA_NAME,
            metadata_hash=ASA_METADATA_HASH,
            url=ASA_URL,
            manager_addr=deployer.address,
            reserve_addr=smart_asa_app_client.app_address,
            clawback_addr=deployer.address,
            freeze_addr=deployer.address,
        ),
        params=CommonAppCallParams(static_fee=AlgoAmount.from_micro_algo(sp.fee)),
    ).abi_return
    logger.info(f"Smart ASA ID: {asset_id}")
