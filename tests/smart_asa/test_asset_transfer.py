import pytest
from algokit_utils import AlgoAmount, CommonAppCallParams, LogicError, SigningAccount

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import (
    AccountFreezeArgs,
    AssetFreezeArgs,
    AssetTransferArgs,
    GetCirculatingSupplyArgs,
    SmartAsaClient,
)

# Local state read of an account that is not opted in to the app
NOT_OPTED_IN = "cannot fetch key"


def _global_freeze(client: SmartAsaClient, freeze: SigningAccount) -> None:
    client.send.asset_freeze(
        AssetFreezeArgs(
            freeze_asset=client.state.global_state.smart_asa_id,
            asset_frozen=True,
        ),
        params=CommonAppCallParams(signer=freeze.signer, sender=freeze.address),
    )


def _account_freeze(
    client: SmartAsaClient, freeze: SigningAccount, account: SigningAccount
) -> None:
    client.send.account_freeze(
        AccountFreezeArgs(
            freeze_asset=client.state.global_state.smart_asa_id,
            freeze_account=account.address,
            asset_frozen=True,
        ),
        params=CommonAppCallParams(signer=freeze.signer, sender=freeze.address),
    )


def _transfer(
    client: SmartAsaClient,
    *,
    signer: SigningAccount,
    asset_sender: str,
    asset_receiver: str,
    asset_amount: int,
    xfer_asset: int | None = None,
    fee: AlgoAmount | None = None,
) -> None:
    client.send.asset_transfer(
        AssetTransferArgs(
            xfer_asset=(
                xfer_asset
                if xfer_asset is not None
                else client.state.global_state.smart_asa_id
            ),
            asset_amount=asset_amount,
            asset_sender=asset_sender,
            asset_receiver=asset_receiver,
        ),
        params=CommonAppCallParams(
            static_fee=fee, signer=signer.signer, sender=signer.address
        ),
    )


class TestMint:
    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_pass_as_reserve(
        self,
        min_fee_2x: AlgoAmount,
        reserve: SigningAccount,
        smart_asa_client: SmartAsaClient,
        receiver: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state
        assert (
            smart_asa_client.send.get_circulating_supply(
                GetCirculatingSupplyArgs(asset=smart_asa.smart_asa_id)
            ).abi_return
            == 0
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                receiver, smart_asa.smart_asa_id
            ).balance
            == 0
        )

        smart_asa_client.send.asset_transfer(
            AssetTransferArgs(
                xfer_asset=smart_asa.smart_asa_id,
                asset_amount=smart_asa.total,
                asset_sender=smart_asa_client.app_address,
                asset_receiver=receiver.address,
            ),
            params=CommonAppCallParams(
                static_fee=min_fee_2x,
                signer=reserve.signer,
                sender=reserve.address,
            ),
        )
        assert (
            smart_asa_client.send.get_circulating_supply(
                GetCirculatingSupplyArgs(asset=smart_asa.smart_asa_id)
            ).abi_return
            == smart_asa.total
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                receiver, smart_asa.smart_asa_id
            ).balance
            == smart_asa.total
        )

    def test_pass_as_reserve_and_clawback(
        self,
        min_fee_2x: AlgoAmount,
        smart_asa_client: SmartAsaClient,
        reserve_and_clawback: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state
        assert (
            smart_asa_client.send.get_circulating_supply(
                GetCirculatingSupplyArgs(asset=smart_asa.smart_asa_id)
            ).abi_return
            == 0
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                receiver, smart_asa.smart_asa_id
            ).balance
            == 0
        )

        smart_asa_client.send.asset_transfer(
            AssetTransferArgs(
                xfer_asset=smart_asa.smart_asa_id,
                asset_amount=smart_asa.total,
                asset_sender=smart_asa_client.app_address,
                asset_receiver=receiver.address,
            ),
            params=CommonAppCallParams(
                static_fee=min_fee_2x,
                signer=reserve_and_clawback.signer,
                sender=reserve_and_clawback.address,
            ),
        )
        assert (
            smart_asa_client.send.get_circulating_supply(
                GetCirculatingSupplyArgs(asset=smart_asa.smart_asa_id),
            ).abi_return
            == smart_asa.total
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                receiver, smart_asa.smart_asa_id
            ).balance
            == smart_asa.total
        )

    def test_fail_unauthorized(
        self,
        min_fee_2x: AlgoAmount,
        eve: SigningAccount,
        smart_asa_client: SmartAsaClient,
        receiver: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state

        with pytest.raises(LogicError, match=err.UNAUTHORIZED_RESERVE):
            smart_asa_client.send.asset_transfer(
                AssetTransferArgs(
                    xfer_asset=smart_asa.smart_asa_id,
                    asset_amount=smart_asa.total,
                    asset_sender=smart_asa_client.app_address,
                    asset_receiver=receiver.address,
                ),
                params=CommonAppCallParams(
                    static_fee=min_fee_2x,
                    signer=eve.signer,
                    sender=eve.address,
                ),
            )

    def test_fail_as_clawback(
        self,
        min_fee_2x: AlgoAmount,
        clawback: SigningAccount,
        smart_asa_client: SmartAsaClient,
        receiver: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state

        with pytest.raises(LogicError, match=err.UNAUTHORIZED_RESERVE):
            smart_asa_client.send.asset_transfer(
                AssetTransferArgs(
                    xfer_asset=smart_asa.smart_asa_id,
                    asset_amount=smart_asa.total,
                    asset_sender=smart_asa_client.app_address,
                    asset_receiver=receiver.address,
                ),
                params=CommonAppCallParams(
                    static_fee=min_fee_2x,
                    signer=clawback.signer,
                    sender=clawback.address,
                ),
            )

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_fail_global_frozen(
        self,
        min_fee_2x: AlgoAmount,
        reserve: SigningAccount,
        freeze: SigningAccount,
        smart_asa_client: SmartAsaClient,
        receiver: SigningAccount,
    ) -> None:
        _global_freeze(smart_asa_client, freeze)
        with pytest.raises(LogicError, match=err.GLOBAL_FROZEN):
            _transfer(
                smart_asa_client,
                signer=reserve,
                asset_sender=smart_asa_client.app_address,
                asset_receiver=receiver.address,
                asset_amount=1,
                fee=min_fee_2x,
            )

    @pytest.mark.parametrize("asa_config", [True], indirect=True)
    def test_fail_frozen_receiver(
        self,
        min_fee_2x: AlgoAmount,
        reserve: SigningAccount,
        smart_asa_client: SmartAsaClient,
        receiver: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state

        with pytest.raises(LogicError, match=err.RECEIVER_FROZEN):
            smart_asa_client.send.asset_transfer(
                AssetTransferArgs(
                    xfer_asset=smart_asa.smart_asa_id,
                    asset_amount=smart_asa.total,
                    asset_sender=smart_asa_client.app_address,
                    asset_receiver=receiver.address,
                ),
                params=CommonAppCallParams(
                    static_fee=min_fee_2x,
                    signer=reserve.signer,
                    sender=reserve.address,
                ),
            )

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_fail_self_minting(
        self,
        min_fee_2x: AlgoAmount,
        reserve: SigningAccount,
        smart_asa_client: SmartAsaClient,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state

        with pytest.raises(LogicError, match=err.SELF_MINT):
            smart_asa_client.send.asset_transfer(
                AssetTransferArgs(
                    xfer_asset=smart_asa.smart_asa_id,
                    asset_amount=smart_asa.total,
                    asset_sender=smart_asa_client.app_address,
                    asset_receiver=smart_asa_client.app_address,
                ),
                params=CommonAppCallParams(
                    static_fee=min_fee_2x,
                    signer=reserve.signer,
                    sender=reserve.address,
                ),
            )

    def test_fail_over_minting(
        self,
        min_fee_2x: AlgoAmount,
        reserve: SigningAccount,
        smart_asa_client: SmartAsaClient,
        receiver: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state
        with pytest.raises(LogicError, match=err.OVER_MINT):
            smart_asa_client.send.asset_transfer(
                AssetTransferArgs(
                    xfer_asset=smart_asa.smart_asa_id,
                    asset_amount=smart_asa.total + 1,
                    asset_sender=smart_asa_client.app_address,
                    asset_receiver=receiver.address,
                ),
                params=CommonAppCallParams(
                    static_fee=min_fee_2x,
                    signer=reserve.signer,
                    sender=reserve.address,
                ),
            )


class TestBurn:
    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_pass_as_reserve(
        self,
        min_fee_2x: AlgoAmount,
        smart_asa_client: SmartAsaClient,
        reserve_with_supply: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state
        assert (
            smart_asa_client.send.get_circulating_supply(
                GetCirculatingSupplyArgs(asset=smart_asa.smart_asa_id)
            ).abi_return
            == smart_asa.total
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                reserve_with_supply, smart_asa.smart_asa_id
            ).balance
            == smart_asa.total
        )

        smart_asa_client.send.asset_transfer(
            AssetTransferArgs(
                xfer_asset=smart_asa.smart_asa_id,
                asset_amount=smart_asa.total,
                asset_sender=reserve_with_supply.address,
                asset_receiver=smart_asa_client.app_address,
            ),
            params=CommonAppCallParams(
                static_fee=min_fee_2x,
                signer=reserve_with_supply.signer,
                sender=reserve_with_supply.address,
            ),
        )
        assert (
            smart_asa_client.send.get_circulating_supply(
                GetCirculatingSupplyArgs(asset=smart_asa.smart_asa_id)
            ).abi_return
            == 0
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                reserve_with_supply, smart_asa.smart_asa_id
            ).balance
            == 0
        )

    def test_pass_as_reserve_and_clawback(
        self,
        min_fee_2x: AlgoAmount,
        smart_asa_client: SmartAsaClient,
        reserve_and_clawback: SigningAccount,
        account_with_supply: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state
        assert (
            smart_asa_client.send.get_circulating_supply(
                GetCirculatingSupplyArgs(asset=smart_asa.smart_asa_id)
            ).abi_return
            == smart_asa.total
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                account_with_supply, smart_asa.smart_asa_id
            ).balance
            == smart_asa.total
        )

        smart_asa_client.send.asset_transfer(
            AssetTransferArgs(
                xfer_asset=smart_asa.smart_asa_id,
                asset_amount=smart_asa.total,
                asset_sender=account_with_supply.address,
                asset_receiver=smart_asa_client.app_address,
            ),
            params=CommonAppCallParams(
                static_fee=min_fee_2x,
                signer=reserve_and_clawback.signer,
                sender=reserve_and_clawback.address,
            ),
        )
        assert (
            smart_asa_client.send.get_circulating_supply(
                GetCirculatingSupplyArgs(asset=smart_asa.smart_asa_id)
            ).abi_return
            == 0
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                account_with_supply, smart_asa.smart_asa_id
            ).balance
            == 0
        )

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_fail_unauthorized(
        self,
        min_fee_2x: AlgoAmount,
        smart_asa_client: SmartAsaClient,
        account_with_supply: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state

        with pytest.raises(LogicError, match=err.UNAUTHORIZED_RESERVE):
            smart_asa_client.send.asset_transfer(
                AssetTransferArgs(
                    xfer_asset=smart_asa.smart_asa_id,
                    asset_amount=smart_asa.total,
                    asset_sender=account_with_supply.address,
                    asset_receiver=smart_asa_client.app_address,
                ),
                params=CommonAppCallParams(
                    static_fee=min_fee_2x,
                    signer=account_with_supply.signer,
                    sender=account_with_supply.address,
                ),
            )

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_fail_as_clawback(
        self,
        min_fee_2x: AlgoAmount,
        smart_asa_client: SmartAsaClient,
        clawback: SigningAccount,
        account_with_supply: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state
        with pytest.raises(LogicError, match=err.UNAUTHORIZED_RESERVE):
            smart_asa_client.send.asset_transfer(
                AssetTransferArgs(
                    xfer_asset=smart_asa.smart_asa_id,
                    asset_amount=smart_asa.total,
                    asset_sender=account_with_supply.address,
                    asset_receiver=smart_asa_client.app_address,
                ),
                params=CommonAppCallParams(
                    static_fee=min_fee_2x,
                    signer=clawback.signer,
                    sender=clawback.address,
                ),
            )

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_fail_global_frozen(
        self,
        min_fee_2x: AlgoAmount,
        freeze: SigningAccount,
        smart_asa_client: SmartAsaClient,
        reserve_with_supply: SigningAccount,
    ) -> None:
        _global_freeze(smart_asa_client, freeze)
        with pytest.raises(LogicError, match=err.GLOBAL_FROZEN):
            _transfer(
                smart_asa_client,
                signer=reserve_with_supply,
                asset_sender=reserve_with_supply.address,
                asset_receiver=smart_asa_client.app_address,
                asset_amount=1,
                fee=min_fee_2x,
            )

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_fail_frozen_reserve(
        self,
        min_fee_2x: AlgoAmount,
        freeze: SigningAccount,
        smart_asa_client: SmartAsaClient,
        reserve_with_supply: SigningAccount,
    ) -> None:
        _account_freeze(smart_asa_client, freeze, reserve_with_supply)
        with pytest.raises(LogicError, match=err.SENDER_FROZEN):
            _transfer(
                smart_asa_client,
                signer=reserve_with_supply,
                asset_sender=reserve_with_supply.address,
                asset_receiver=smart_asa_client.app_address,
                asset_amount=1,
                fee=min_fee_2x,
            )

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_fail_clawback_burn(
        self,
        min_fee_2x: AlgoAmount,
        smart_asa_client: SmartAsaClient,
        reserve: SigningAccount,
        account_with_supply: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state
        with pytest.raises(LogicError, match=err.CLAWBACK_BURN):
            smart_asa_client.send.asset_transfer(
                AssetTransferArgs(
                    xfer_asset=smart_asa.smart_asa_id,
                    asset_amount=smart_asa.total,
                    asset_sender=account_with_supply.address,
                    asset_receiver=smart_asa_client.app_address,
                ),
                params=CommonAppCallParams(
                    static_fee=min_fee_2x,
                    signer=reserve.signer,
                    sender=reserve.address,
                ),
            )


class TestClawback:
    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_pass(
        self,
        min_fee_2x: AlgoAmount,
        smart_asa_client: SmartAsaClient,
        clawback: SigningAccount,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                account_with_supply, smart_asa.smart_asa_id
            ).balance
            == smart_asa.total
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                receiver, smart_asa.smart_asa_id
            ).balance
            == 0
        )

        smart_asa_client.send.asset_transfer(
            AssetTransferArgs(
                xfer_asset=smart_asa.smart_asa_id,
                asset_amount=smart_asa.total,
                asset_sender=account_with_supply.address,
                asset_receiver=receiver.address,
            ),
            params=CommonAppCallParams(
                static_fee=min_fee_2x,
                signer=clawback.signer,
                sender=clawback.address,
            ),
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                account_with_supply, smart_asa.smart_asa_id
            ).balance
            == 0
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                receiver, smart_asa.smart_asa_id
            ).balance
            == smart_asa.total
        )

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_pass_global_frozen(
        self,
        min_fee_2x: AlgoAmount,
        smart_asa_client: SmartAsaClient,
        clawback: SigningAccount,
        freeze: SigningAccount,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state
        _global_freeze(smart_asa_client, freeze)
        _transfer(
            smart_asa_client,
            signer=clawback,
            asset_sender=account_with_supply.address,
            asset_receiver=receiver.address,
            asset_amount=smart_asa.total,
            fee=min_fee_2x,
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                receiver, smart_asa.smart_asa_id
            ).balance
            == smart_asa.total
        )

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_pass_frozen_accounts(
        self,
        min_fee_2x: AlgoAmount,
        smart_asa_client: SmartAsaClient,
        clawback: SigningAccount,
        freeze: SigningAccount,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state
        _account_freeze(smart_asa_client, freeze, account_with_supply)
        _account_freeze(smart_asa_client, freeze, receiver)
        _transfer(
            smart_asa_client,
            signer=clawback,
            asset_sender=account_with_supply.address,
            asset_receiver=receiver.address,
            asset_amount=smart_asa.total,
            fee=min_fee_2x,
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                receiver, smart_asa.smart_asa_id
            ).balance
            == smart_asa.total
        )

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_fail_unauthorized(
        self,
        min_fee_2x: AlgoAmount,
        smart_asa_client: SmartAsaClient,
        eve: SigningAccount,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state
        with pytest.raises(LogicError, match=err.UNAUTHORIZED_CLAWBACK):
            smart_asa_client.send.asset_transfer(
                AssetTransferArgs(
                    xfer_asset=smart_asa.smart_asa_id,
                    asset_amount=smart_asa.total,
                    asset_sender=account_with_supply.address,
                    asset_receiver=receiver.address,
                ),
                params=CommonAppCallParams(
                    static_fee=min_fee_2x,
                    signer=eve.signer,
                    sender=eve.address,
                ),
            )


class TestRegularTransfer:
    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_pass_transfer(
        self,
        min_fee_2x: AlgoAmount,
        smart_asa_client: SmartAsaClient,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        smart_asa = smart_asa_client.state.global_state
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                account_with_supply, smart_asa.smart_asa_id
            ).balance
            == smart_asa.total
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                receiver, smart_asa.smart_asa_id
            ).balance
            == 0
        )

        smart_asa_client.send.asset_transfer(
            AssetTransferArgs(
                xfer_asset=smart_asa.smart_asa_id,
                asset_amount=smart_asa.total,
                asset_sender=account_with_supply.address,
                asset_receiver=receiver.address,
            ),
            params=CommonAppCallParams(
                static_fee=min_fee_2x,
                signer=account_with_supply.signer,
                sender=account_with_supply.address,
            ),
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                account_with_supply, smart_asa.smart_asa_id
            ).balance
            == 0
        )
        assert (
            smart_asa_client.algorand.asset.get_account_information(
                receiver, smart_asa.smart_asa_id
            ).balance
            == smart_asa.total
        )

    def test_fail_missing_ctrl_asa(
        self,
        smart_asa_client_no_asset: SmartAsaClient,
        eve: SigningAccount,
        dummy_asa: int,
    ) -> None:
        with pytest.raises(LogicError, match=err.MISSING_CTRL_ASA):
            _transfer(
                smart_asa_client_no_asset,
                signer=eve,
                asset_sender=eve.address,
                asset_receiver=eve.address,
                asset_amount=0,
                xfer_asset=dummy_asa,
            )

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_fail_invalid_ctrl_asa(
        self,
        smart_asa_client: SmartAsaClient,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
        dummy_asa: int,
    ) -> None:
        with pytest.raises(LogicError, match=err.INVALID_CTRL_ASA):
            _transfer(
                smart_asa_client,
                signer=account_with_supply,
                asset_sender=account_with_supply.address,
                asset_receiver=receiver.address,
                asset_amount=1,
                xfer_asset=dummy_asa,
            )

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_fail_no_opted_in_sender(
        self,
        smart_asa_client: SmartAsaClient,
        eve: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        with pytest.raises(LogicError, match=NOT_OPTED_IN):
            _transfer(
                smart_asa_client,
                signer=eve,
                asset_sender=eve.address,
                asset_receiver=receiver.address,
                asset_amount=0,
            )

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_fail_no_opted_in_receiver(
        self,
        smart_asa_client: SmartAsaClient,
        account_with_supply: SigningAccount,
        eve: SigningAccount,
    ) -> None:
        with pytest.raises(LogicError, match=NOT_OPTED_IN):
            _transfer(
                smart_asa_client,
                signer=account_with_supply,
                asset_sender=account_with_supply.address,
                asset_receiver=eve.address,
                asset_amount=1,
            )

    @pytest.mark.skip(
        reason="Unreachable: asset_create is one-shot and asset_destroy deletes the app, so local state can't go stale"
    )
    def test_fail_invalid_current_ctrl_asa(self) -> None:
        pass

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_fail_global_frozen(
        self,
        min_fee_2x: AlgoAmount,
        smart_asa_client: SmartAsaClient,
        freeze: SigningAccount,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        smart_asa_client.send.asset_freeze(
            AssetFreezeArgs(
                freeze_asset=smart_asa_client.state.global_state.smart_asa_id,
                asset_frozen=True,
            ),
            params=CommonAppCallParams(
                signer=freeze.signer,
                sender=freeze.address,
            ),
        )
        smart_asa = smart_asa_client.state.global_state

        with pytest.raises(LogicError, match=err.GLOBAL_FROZEN):
            smart_asa_client.send.asset_transfer(
                AssetTransferArgs(
                    xfer_asset=smart_asa.smart_asa_id,
                    asset_amount=smart_asa.total,
                    asset_sender=account_with_supply.address,
                    asset_receiver=receiver.address,
                ),
                params=CommonAppCallParams(
                    static_fee=min_fee_2x,
                    signer=account_with_supply.signer,
                    sender=account_with_supply.address,
                ),
            )

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_fail_frozen_sender(
        self,
        min_fee_2x: AlgoAmount,
        smart_asa_client: SmartAsaClient,
        freeze: SigningAccount,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        smart_asa_client.send.account_freeze(
            AccountFreezeArgs(
                freeze_asset=smart_asa_client.state.global_state.smart_asa_id,
                freeze_account=account_with_supply.address,
                asset_frozen=True,
            ),
            params=CommonAppCallParams(
                signer=freeze.signer,
                sender=freeze.address,
            ),
        )
        smart_asa = smart_asa_client.state.global_state

        with pytest.raises(LogicError, match=err.SENDER_FROZEN):
            smart_asa_client.send.asset_transfer(
                AssetTransferArgs(
                    xfer_asset=smart_asa.smart_asa_id,
                    asset_amount=smart_asa.total,
                    asset_sender=account_with_supply.address,
                    asset_receiver=receiver.address,
                ),
                params=CommonAppCallParams(
                    static_fee=min_fee_2x,
                    signer=account_with_supply.signer,
                    sender=account_with_supply.address,
                ),
            )

    @pytest.mark.parametrize("asa_config", [False], indirect=True)
    def test_fail_frozen_receiver(
        self,
        min_fee_2x: AlgoAmount,
        smart_asa_client: SmartAsaClient,
        freeze: SigningAccount,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        smart_asa_client.send.account_freeze(
            AccountFreezeArgs(
                freeze_asset=smart_asa_client.state.global_state.smart_asa_id,
                freeze_account=receiver.address,
                asset_frozen=True,
            ),
            params=CommonAppCallParams(
                signer=freeze.signer,
                sender=freeze.address,
            ),
        )
        smart_asa = smart_asa_client.state.global_state

        with pytest.raises(LogicError, match=err.RECEIVER_FROZEN):
            smart_asa_client.send.asset_transfer(
                AssetTransferArgs(
                    xfer_asset=smart_asa.smart_asa_id,
                    asset_amount=smart_asa.total,
                    asset_sender=account_with_supply.address,
                    asset_receiver=receiver.address,
                ),
                params=CommonAppCallParams(
                    static_fee=min_fee_2x,
                    signer=account_with_supply.signer,
                    sender=account_with_supply.address,
                ),
            )
