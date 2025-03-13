import logging
from typing import Final

import algokit_utils
from algokit_utils.config import config

logger = logging.getLogger(__name__)

ASA_TOTAL: Final[int] = 420
ASA_DECIMALS: Final[int] = 1
ASA_DEFAULT_FROZEN: Final[bool] = False
ASA_UNIT_NAME: Final[str] = "ARC-20"
ASA_NAME: Final[str] = "ARC-20 Smart ASA"
ASA_URL: Final[str] = "https://arc.algorand.foundation/ARCs/arc-0020"
ASA_METADATA_HASH: Final[bytes] = (420).to_bytes(length=32)


# define deployment behaviour based on supplied app spec
def deploy() -> None:
    from smart_contracts.artifacts.smart_asa.smart_asa_client import (
        AssetCreateArgs,
        SmartAsaFactory,
    )

    config.configure(debug=False)

    algorand = algokit_utils.AlgorandClient.from_environment()
    deployer = algorand.account.from_environment("DEPLOYER")

    factory = algorand.client.get_typed_app_factory(
        SmartAsaFactory, default_sender=deployer.address
    )

    app_client, _ = factory.deploy(
        on_schema_break=algokit_utils.OnSchemaBreak.AppendApp,
        on_update=algokit_utils.OnUpdate.AppendApp,
    )

    sp = app_client.algorand.client.algod.suggested_params()
    sp.flat_fee = True
    sp.fee = sp.min_fee * 2  # type: ignore

    app_client.send.asset_create(
        AssetCreateArgs(
            total=ASA_TOTAL,
            decimals=ASA_DECIMALS,
            default_frozen=ASA_DEFAULT_FROZEN,
            unit_name=ASA_UNIT_NAME,
            name=ASA_NAME,
            url=ASA_URL,
            metadata_hash=ASA_METADATA_HASH,
            manager_addr=deployer.address,
            reserve_addr=app_client.app_address,
            clawback_addr=deployer.address,
            freeze_addr=deployer.address,
        ),
        params=algokit_utils.CommonAppCallParams(
            static_fee=algokit_utils.AlgoAmount.from_micro_algo(sp.fee)  # type: ignore
        ),
    )
