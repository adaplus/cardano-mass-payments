from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.classes import InputUTXO, PaymentDetail
from cardano_mass_payments.constants.commands import TRANSACTION_BUILD
from cardano_mass_payments.constants.exceptions import ScriptError
from cardano_mass_payments.utils.cli_utils import create_transaction_command


class TestProcess(TestCase):
    def test_missing_input_arg(self):
        try:
            result = create_transaction_command(
                input_arg=None,
                output_arg=10,
                filename="test_filename",
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid input argument type."
        assert result.additional_context == {"type": type(None)}

    def test_missing_output_arg(self):
        try:
            result = create_transaction_command(
                input_arg=1,
                output_arg=None,
                filename="test_filename",
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid output argument type."
        assert result.additional_context == {"type": type(None)}

    def test_missing_filename(self):
        try:
            result = create_transaction_command(
                input_arg=1,
                output_arg=10,
                filename=None,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid filename argument type."
        assert result.additional_context == {"type": type(None)}

    def test_invalid_input_arg(self):
        try:
            result = create_transaction_command(
                input_arg="invalid",
                output_arg=10,
                filename="test_filename",
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid input argument type."
        assert result.additional_context == {"type": type("invalid")}

    def test_invalid_output_arg(self):
        try:
            result = create_transaction_command(
                input_arg=1,
                output_arg="invalid",
                filename="test_filename",
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid output argument type."
        assert result.additional_context == {"type": type("invalid")}

    def test_invalid_filename(self):
        try:
            result = create_transaction_command(
                input_arg=1,
                output_arg=10,
                filename=-1,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid filename argument type."
        assert result.additional_context == {"type": type(-1)}

    def test_invalid_prefix(self):
        try:
            result = create_transaction_command(
                input_arg=1,
                output_arg=10,
                filename="test_filename",
                prefix=-1,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid prefix argument type."
        assert result.additional_context == {"type": type(-1)}

    def test_invalid_fee(self):
        try:
            result = create_transaction_command(
                input_arg=1,
                output_arg=10,
                filename="test_filename",
                fee=0.1,
                ttl=100,
                is_draft=False,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid Fee argument type."
        assert result.additional_context == {"type": type(0.1)}

    def test_invalid_ttl(self):
        try:
            result = create_transaction_command(
                input_arg=1,
                output_arg=10,
                filename="test_filename",
                fee=100,
                ttl=0.1,
                is_draft=False,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid TTL argument type."
        assert result.additional_context == {"type": type(0.1)}

    def test_invalid_metadata_filename(self):
        try:
            result = create_transaction_command(
                input_arg=1,
                output_arg=10,
                filename="test_filename",
                metadata_filename=-1,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid metadata filename argument type."
        assert result.additional_context == {"type": type(-1)}

    def test_invalid_is_draft(self):
        try:
            result = create_transaction_command(
                input_arg=1,
                output_arg=10,
                filename="test_filename",
                is_draft=-1,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid is draft argument type."
        assert result.additional_context == {"type": type(-1)}

    def test_invalid_reward_details(self):
        try:
            result = create_transaction_command(
                input_arg=1,
                output_arg=10,
                filename="test_filename",
                reward_details=-1,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid reward details type."
        assert result.additional_context == {"type": type(-1)}

    def test_success_only_required(self):
        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {"source_address": "test_source_address"},
        ):
            try:
                result = create_transaction_command(
                    input_arg=1,
                    output_arg=10,
                    filename="test_filename",
                )
            except Exception as e:
                result = e

        assert not isinstance(result, ScriptError)
        assert result == TRANSACTION_BUILD.format(
            prefix="",
            tx_in_details="--tx-in 0000000000000000000000000000000000000000000000000000000000000000#1 ",
            tx_out_details="--tx-out test_source_address+0 " * 10,
            tx_filename="test_filename",
            extra_details="--fee 0 --invalid-hereafter 0 ",
        )

    def test_success_with_optionals(self):
        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {"source_address": "test_source_address"},
        ):
            try:
                result = create_transaction_command(
                    input_arg=1,
                    output_arg=10,
                    filename="test_filename",
                    prefix="test_prefix",
                    is_draft=False,
                    fee=100,
                    ttl=100,
                    metadata_filename="test_metadata",
                    reward_details={
                        "stake_address": "test_stake_address",
                        "stake_amount": 1000,
                    },
                )
            except Exception as e:
                result = e

        assert not isinstance(result, ScriptError)
        assert result == TRANSACTION_BUILD.format(
            prefix="test_prefix",
            tx_in_details="--tx-in 0000000000000000000000000000000000000000000000000000000000000000#1 ",
            tx_out_details="--tx-out test_source_address+0 " * 10,
            tx_filename="test_filename",
            extra_details="--withdrawal test_stake_address+1000 --fee 100 --invalid-hereafter 100 "
            "--metadata-json-file test_metadata ",
        )

    def test_success_input_list(self):
        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {"source_address": "test_source_address"},
        ):
            try:
                result = create_transaction_command(
                    input_arg=[
                        InputUTXO(
                            address="test_source_address",
                            tx_hash="test_hash",
                            tx_index=0,
                            amount=10,
                        ),
                        InputUTXO(
                            address="test_source_address",
                            tx_hash="test_hash",
                            tx_index=1,
                            amount=10,
                        ),
                    ],
                    output_arg=10,
                    filename="test_filename",
                )
            except Exception as e:
                result = e

        assert not isinstance(result, ScriptError)
        assert result == TRANSACTION_BUILD.format(
            prefix="",
            tx_in_details="--tx-in test_hash#0 --tx-in test_hash#1 ",
            tx_out_details="--tx-out test_source_address+0 " * 10,
            tx_filename="test_filename",
            extra_details="--fee 0 --invalid-hereafter 0 ",
        )

    def test_success_output_list(self):
        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {"source_address": "test_source_address"},
        ):
            try:
                result = create_transaction_command(
                    input_arg=1,
                    output_arg=[
                        PaymentDetail(
                            address="test_target_address",
                            amount=1000,  # Will be ignored as this is a draft
                        )
                        for _ in range(10)
                    ],
                    filename="test_filename",
                )
            except Exception as e:
                result = e

        assert not isinstance(result, ScriptError)
        assert result == TRANSACTION_BUILD.format(
            prefix="",
            tx_in_details="--tx-in 0000000000000000000000000000000000000000000000000000000000000000#1 ",
            tx_out_details="--tx-out test_target_address+0 " * 10,
            tx_filename="test_filename",
            extra_details="--fee 0 --invalid-hereafter 0 ",
        )
