import pytest
from algokit_utils import AlgoAmount, LogicError, SigningAccount

import smart_contracts.errors as err
from smart_contracts.artifacts.smart_asa.smart_asa_client import SmartAsaClient
from tests.conftest import SmartASAConfig
from tests.support import (
    BOTH_DEFAULT_FROZEN,
    DEFAULT_FROZEN,
    NOT_OPTED_IN,
    UNREACHABLE,
    account_freeze,
    balance,
    circulating_supply,
    global_freeze,
    transfer,
)


class TestMint:
    def test_pass_as_reserve(
        self,
        min_fee_2x: AlgoAmount,
        reserve: SigningAccount,
        asa_config: SmartASAConfig,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        receiver: SigningAccount,
    ) -> None:
        assert circulating_supply(smart_asa_client, smart_asa_id) == 0
        assert balance(smart_asa_client, smart_asa_id, receiver) == 0

        transfer(
            smart_asa_client,
            smart_asa_id,
            signer=reserve,
            asset_sender=smart_asa_client.app_address,
            asset_receiver=receiver.address,
            asset_amount=asa_config.total,
            fee=min_fee_2x,
        )
        assert circulating_supply(smart_asa_client, smart_asa_id) == asa_config.total
        assert balance(smart_asa_client, smart_asa_id, receiver) == asa_config.total

    @BOTH_DEFAULT_FROZEN  # Reserve and Clawback can mint into frozen accounts
    def test_pass_as_reserve_and_clawback(
        self,
        min_fee_2x: AlgoAmount,
        asa_config: SmartASAConfig,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        reserve_and_clawback: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        assert circulating_supply(smart_asa_client, smart_asa_id) == 0
        assert balance(smart_asa_client, smart_asa_id, receiver) == 0

        transfer(
            smart_asa_client,
            smart_asa_id,
            signer=reserve_and_clawback,
            asset_sender=smart_asa_client.app_address,
            asset_receiver=receiver.address,
            asset_amount=asa_config.total,
            fee=min_fee_2x,
        )
        assert circulating_supply(smart_asa_client, smart_asa_id) == asa_config.total
        assert balance(smart_asa_client, smart_asa_id, receiver) == asa_config.total

    def test_fail_unauthorized(
        self,
        eve: SigningAccount,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        receiver: SigningAccount,
    ) -> None:
        with pytest.raises(LogicError, match=err.UNAUTHORIZED_RESERVE):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=eve,
                asset_sender=smart_asa_client.app_address,
                asset_receiver=receiver.address,
                asset_amount=1,
            )

    def test_fail_as_clawback(
        self,
        clawback: SigningAccount,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        receiver: SigningAccount,
    ) -> None:
        with pytest.raises(LogicError, match=err.UNAUTHORIZED_RESERVE):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=clawback,
                asset_sender=smart_asa_client.app_address,
                asset_receiver=receiver.address,
                asset_amount=1,
            )

    def test_fail_global_frozen(
        self,
        reserve: SigningAccount,
        freeze: SigningAccount,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        receiver: SigningAccount,
    ) -> None:
        global_freeze(smart_asa_client, smart_asa_id, freeze)
        with pytest.raises(LogicError, match=err.GLOBAL_FROZEN):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=reserve,
                asset_sender=smart_asa_client.app_address,
                asset_receiver=receiver.address,
                asset_amount=1,
            )

    @DEFAULT_FROZEN
    def test_fail_frozen_receiver(
        self,
        reserve: SigningAccount,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        receiver: SigningAccount,
    ) -> None:
        with pytest.raises(LogicError, match=err.RECEIVER_FROZEN):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=reserve,
                asset_sender=smart_asa_client.app_address,
                asset_receiver=receiver.address,
                asset_amount=1,
            )

    def test_fail_self_minting(
        self,
        reserve: SigningAccount,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
    ) -> None:
        with pytest.raises(LogicError, match=err.SELF_MINT):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=reserve,
                asset_sender=smart_asa_client.app_address,
                asset_receiver=smart_asa_client.app_address,
                asset_amount=1,
            )

    def test_fail_over_minting(
        self,
        reserve: SigningAccount,
        asa_config: SmartASAConfig,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        receiver: SigningAccount,
    ) -> None:
        with pytest.raises(LogicError, match=err.OVER_MINT):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=reserve,
                asset_sender=smart_asa_client.app_address,
                asset_receiver=receiver.address,
                asset_amount=asa_config.total + 1,
            )


class TestBurn:
    def test_pass_as_reserve(
        self,
        min_fee_2x: AlgoAmount,
        asa_config: SmartASAConfig,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        reserve_with_supply: SigningAccount,
    ) -> None:
        assert circulating_supply(smart_asa_client, smart_asa_id) == asa_config.total
        assert (
            balance(smart_asa_client, smart_asa_id, reserve_with_supply)
            == asa_config.total
        )

        transfer(
            smart_asa_client,
            smart_asa_id,
            signer=reserve_with_supply,
            asset_sender=reserve_with_supply.address,
            asset_receiver=smart_asa_client.app_address,
            asset_amount=asa_config.total,
            fee=min_fee_2x,
        )
        assert circulating_supply(smart_asa_client, smart_asa_id) == 0
        assert balance(smart_asa_client, smart_asa_id, reserve_with_supply) == 0

    @BOTH_DEFAULT_FROZEN  # Reserve and Clawback can burn from frozen accounts
    def test_pass_as_reserve_and_clawback(
        self,
        min_fee_2x: AlgoAmount,
        asa_config: SmartASAConfig,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        reserve_and_clawback: SigningAccount,
        account_with_supply: SigningAccount,
    ) -> None:
        assert circulating_supply(smart_asa_client, smart_asa_id) == asa_config.total
        assert (
            balance(smart_asa_client, smart_asa_id, account_with_supply)
            == asa_config.total
        )

        transfer(
            smart_asa_client,
            smart_asa_id,
            signer=reserve_and_clawback,
            asset_sender=account_with_supply.address,
            asset_receiver=smart_asa_client.app_address,
            asset_amount=asa_config.total,
            fee=min_fee_2x,
        )
        assert circulating_supply(smart_asa_client, smart_asa_id) == 0
        assert balance(smart_asa_client, smart_asa_id, account_with_supply) == 0

    def test_fail_unauthorized(
        self,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        account_with_supply: SigningAccount,
    ) -> None:
        with pytest.raises(LogicError, match=err.UNAUTHORIZED_RESERVE):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=account_with_supply,
                asset_sender=account_with_supply.address,
                asset_receiver=smart_asa_client.app_address,
                asset_amount=1,
            )

    def test_fail_as_clawback(
        self,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        clawback: SigningAccount,
        account_with_supply: SigningAccount,
    ) -> None:
        with pytest.raises(LogicError, match=err.UNAUTHORIZED_RESERVE):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=clawback,
                asset_sender=account_with_supply.address,
                asset_receiver=smart_asa_client.app_address,
                asset_amount=1,
            )

    def test_fail_global_frozen(
        self,
        freeze: SigningAccount,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        reserve_with_supply: SigningAccount,
    ) -> None:
        global_freeze(smart_asa_client, smart_asa_id, freeze)
        with pytest.raises(LogicError, match=err.GLOBAL_FROZEN):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=reserve_with_supply,
                asset_sender=reserve_with_supply.address,
                asset_receiver=smart_asa_client.app_address,
                asset_amount=1,
            )

    def test_fail_frozen_reserve(
        self,
        freeze: SigningAccount,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        reserve_with_supply: SigningAccount,
    ) -> None:
        account_freeze(
            smart_asa_client, smart_asa_id, freeze, reserve_with_supply.address
        )
        with pytest.raises(LogicError, match=err.SENDER_FROZEN):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=reserve_with_supply,
                asset_sender=reserve_with_supply.address,
                asset_receiver=smart_asa_client.app_address,
                asset_amount=1,
            )

    def test_fail_clawback_burn(
        self,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        reserve: SigningAccount,
        account_with_supply: SigningAccount,
    ) -> None:
        with pytest.raises(LogicError, match=err.CLAWBACK_BURN):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=reserve,
                asset_sender=account_with_supply.address,
                asset_receiver=smart_asa_client.app_address,
                asset_amount=1,
            )


class TestClawback:
    def test_pass(
        self,
        min_fee_2x: AlgoAmount,
        asa_config: SmartASAConfig,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        clawback: SigningAccount,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        assert (
            balance(smart_asa_client, smart_asa_id, account_with_supply)
            == asa_config.total
        )
        assert balance(smart_asa_client, smart_asa_id, receiver) == 0

        transfer(
            smart_asa_client,
            smart_asa_id,
            signer=clawback,
            asset_sender=account_with_supply.address,
            asset_receiver=receiver.address,
            asset_amount=asa_config.total,
            fee=min_fee_2x,
        )
        assert balance(smart_asa_client, smart_asa_id, account_with_supply) == 0
        assert balance(smart_asa_client, smart_asa_id, receiver) == asa_config.total

    def test_pass_global_frozen(
        self,
        min_fee_2x: AlgoAmount,
        asa_config: SmartASAConfig,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        clawback: SigningAccount,
        freeze: SigningAccount,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        global_freeze(smart_asa_client, smart_asa_id, freeze)
        transfer(
            smart_asa_client,
            smart_asa_id,
            signer=clawback,
            asset_sender=account_with_supply.address,
            asset_receiver=receiver.address,
            asset_amount=asa_config.total,
            fee=min_fee_2x,
        )
        assert balance(smart_asa_client, smart_asa_id, receiver) == asa_config.total

    def test_pass_frozen_accounts(
        self,
        min_fee_2x: AlgoAmount,
        asa_config: SmartASAConfig,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        clawback: SigningAccount,
        freeze: SigningAccount,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        account_freeze(
            smart_asa_client, smart_asa_id, freeze, account_with_supply.address
        )
        account_freeze(smart_asa_client, smart_asa_id, freeze, receiver.address)
        transfer(
            smart_asa_client,
            smart_asa_id,
            signer=clawback,
            asset_sender=account_with_supply.address,
            asset_receiver=receiver.address,
            asset_amount=asa_config.total,
            fee=min_fee_2x,
        )
        assert balance(smart_asa_client, smart_asa_id, receiver) == asa_config.total

    def test_fail_unauthorized(
        self,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        eve: SigningAccount,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        with pytest.raises(LogicError, match=err.UNAUTHORIZED_CLAWBACK):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=eve,
                asset_sender=account_with_supply.address,
                asset_receiver=receiver.address,
                asset_amount=1,
            )


class TestRegularTransfer:
    def test_pass_transfer(
        self,
        min_fee_2x: AlgoAmount,
        asa_config: SmartASAConfig,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        assert (
            balance(smart_asa_client, smart_asa_id, account_with_supply)
            == asa_config.total
        )
        assert balance(smart_asa_client, smart_asa_id, receiver) == 0

        transfer(
            smart_asa_client,
            smart_asa_id,
            signer=account_with_supply,
            asset_sender=account_with_supply.address,
            asset_receiver=receiver.address,
            asset_amount=asa_config.total,
            fee=min_fee_2x,
        )
        assert balance(smart_asa_client, smart_asa_id, account_with_supply) == 0
        assert balance(smart_asa_client, smart_asa_id, receiver) == asa_config.total

    def test_fail_missing_ctrl_asa(
        self,
        smart_asa_client_no_asset: SmartAsaClient,
        eve: SigningAccount,
        dummy_asa: int,
    ) -> None:
        with pytest.raises(LogicError, match=err.MISSING_CTRL_ASA):
            transfer(
                smart_asa_client_no_asset,
                dummy_asa,
                signer=eve,
                asset_sender=eve.address,
                asset_receiver=eve.address,
                asset_amount=0,
            )

    def test_fail_invalid_ctrl_asa(
        self,
        smart_asa_client: SmartAsaClient,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
        dummy_asa: int,
    ) -> None:
        with pytest.raises(LogicError, match=err.INVALID_CTRL_ASA):
            transfer(
                smart_asa_client,
                dummy_asa,
                signer=account_with_supply,
                asset_sender=account_with_supply.address,
                asset_receiver=receiver.address,
                asset_amount=1,
            )

    def test_fail_no_opted_in_sender(
        self,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        eve: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        with pytest.raises(LogicError, match=NOT_OPTED_IN):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=eve,
                asset_sender=eve.address,
                asset_receiver=receiver.address,
                asset_amount=0,
            )

    def test_fail_no_opted_in_receiver(
        self,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        account_with_supply: SigningAccount,
        eve: SigningAccount,
    ) -> None:
        with pytest.raises(LogicError, match=NOT_OPTED_IN):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=account_with_supply,
                asset_sender=account_with_supply.address,
                asset_receiver=eve.address,
                asset_amount=1,
            )

    @pytest.mark.skip(reason=UNREACHABLE)
    def test_fail_invalid_current_ctrl_asa(self) -> None:
        pass

    def test_fail_global_frozen(
        self,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        freeze: SigningAccount,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        global_freeze(smart_asa_client, smart_asa_id, freeze)
        with pytest.raises(LogicError, match=err.GLOBAL_FROZEN):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=account_with_supply,
                asset_sender=account_with_supply.address,
                asset_receiver=receiver.address,
                asset_amount=1,
            )

    def test_fail_frozen_sender(
        self,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        freeze: SigningAccount,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        account_freeze(
            smart_asa_client, smart_asa_id, freeze, account_with_supply.address
        )
        with pytest.raises(LogicError, match=err.SENDER_FROZEN):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=account_with_supply,
                asset_sender=account_with_supply.address,
                asset_receiver=receiver.address,
                asset_amount=1,
            )

    def test_fail_frozen_receiver(
        self,
        smart_asa_client: SmartAsaClient,
        smart_asa_id: int,
        freeze: SigningAccount,
        account_with_supply: SigningAccount,
        receiver: SigningAccount,
    ) -> None:
        account_freeze(smart_asa_client, smart_asa_id, freeze, receiver.address)
        with pytest.raises(LogicError, match=err.RECEIVER_FROZEN):
            transfer(
                smart_asa_client,
                smart_asa_id,
                signer=account_with_supply,
                asset_sender=account_with_supply.address,
                asset_receiver=receiver.address,
                asset_amount=1,
            )
