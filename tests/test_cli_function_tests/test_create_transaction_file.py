from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.classes import InputUTXO, PaymentDetail
from cardano_mass_payments.constants.common import ScriptMethod
from cardano_mass_payments.constants.exceptions import InvalidMethod, ScriptError
from cardano_mass_payments.utils.cli_utils import create_transaction_file
from tests.mock_utils import generate_mock_popen_function, mock_raise_internal_error


class TestProcess(TestCase):
    def test_missing_input_arg(self):
        try:
            result = create_transaction_file(
                input_arg=None,
                output_arg=10,
                method=ScriptMethod.METHOD_DOCKER_CLI,
                is_draft=True,
                fee=None,
                ttl=None,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid input argument type."
        assert result.additional_context == {"type": type(None)}

    def test_missing_output_arg(self):
        try:
            result = create_transaction_file(
                input_arg=1,
                output_arg=None,
                method=ScriptMethod.METHOD_DOCKER_CLI,
                is_draft=True,
                fee=None,
                ttl=None,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid output argument type."
        assert result.additional_context == {"type": type(None)}

    def test_invalid_input_arg(self):
        try:
            result = create_transaction_file(
                input_arg="invalid",
                output_arg=10,
                method=ScriptMethod.METHOD_DOCKER_CLI,
                is_draft=True,
                fee=None,
                ttl=None,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid input argument type."
        assert result.additional_context == {"type": type("invalid")}

    def test_invalid_output_arg(self):
        try:
            result = create_transaction_file(
                input_arg=1,
                output_arg="invalid",
                method=ScriptMethod.METHOD_DOCKER_CLI,
                is_draft=True,
                fee=None,
                ttl=None,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid output argument type."
        assert result.additional_context == {"type": type("invalid")}

    def test_invalid_method(self):
        try:
            result = create_transaction_file(
                input_arg=1,
                output_arg=10,
                method="invalid",
                is_draft=True,
                fee=None,
                ttl=None,
            )
        except Exception as e:
            result = e

        invalid_method_error = InvalidMethod(method="invalid")
        assert isinstance(result, InvalidMethod)
        assert result.message == invalid_method_error.message
        assert result.additional_context == invalid_method_error.additional_context

    def test_invalid_is_draft(self):
        try:
            result = create_transaction_file(
                input_arg=1,
                output_arg=10,
                method=ScriptMethod.METHOD_DOCKER_CLI,
                is_draft="invalid",
                fee=None,
                ttl=None,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid is draft argument type."
        assert result.additional_context == {"type": type("invalid")}

    def test_invalid_fee(self):
        try:
            result = create_transaction_file(
                input_arg=1,
                output_arg=10,
                method=ScriptMethod.METHOD_DOCKER_CLI,
                is_draft=False,
                fee=0.1,
                ttl=100,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid Fee argument type."
        assert result.additional_context == {"type": type(0.1)}

    def test_invalid_ttl(self):
        try:
            result = create_transaction_file(
                input_arg=1,
                output_arg=10,
                method=ScriptMethod.METHOD_DOCKER_CLI,
                is_draft=False,
                fee=100,
                ttl=0.1,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid TTL argument type."
        assert result.additional_context == {"type": type(0.1)}

    def test_invalid_reward_details(self):
        try:
            result = create_transaction_file(
                input_arg=1,
                output_arg=10,
                method=ScriptMethod.METHOD_DOCKER_CLI,
                is_draft=False,
                fee=100,
                ttl=100,
                reward_details=-1,
            )
        except Exception as e:
            result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Invalid reward details type."
        assert result.additional_context == {"type": type(-1)}

    def test_unexpected_error_during_command_execution(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = create_transaction_file(
                    input_arg=1,
                    output_arg=10,
                )
            except Exception as e:
                result = e

        assert isinstance(result, Exception)
        assert str(result) == "Internal Error"

    def test_success_only_required(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function({"build-raw": {}}),
        ):
            try:
                result = create_transaction_file(
                    input_arg=1,
                    output_arg=10,
                )
            except Exception as e:
                result = e

        assert not isinstance(result, ScriptError)

    def test_success_with_optionals(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function({"build-raw": {}}),
        ):
            try:
                result = create_transaction_file(
                    input_arg=1,
                    output_arg=10,
                    method=ScriptMethod.METHOD_HOST_CLI,
                    is_draft=False,
                    fee=100,
                    ttl=100,
                    reward_details={
                        "stake_address": "test_stake_address",
                        "stake_amount": 1000,
                    },
                )
            except Exception as e:
                result = e

        assert not isinstance(result, ScriptError)

    def test_success_input_list(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function({"build-raw": {}}),
        ):
            try:
                result = create_transaction_file(
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
                )
            except Exception as e:
                result = e

        assert not isinstance(result, ScriptError)

    def test_success_output_list(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function({"build-raw": {}}),
        ):
            try:
                result = create_transaction_file(
                    input_arg=1,
                    output_arg=[
                        PaymentDetail(
                            address="test_target_address",
                            amount=1000,  # Will be ignored as this is a draft
                        )
                        for _ in range(10)
                    ],
                )
            except Exception as e:
                result = e

        assert not isinstance(result, ScriptError)
