from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.constants.exceptions import (
    InvalidMethod,
    InvalidNetwork,
    InvalidType,
    ScriptError,
)
from cardano_mass_payments.utils.cli_utils import get_transaction_fee
from tests.mock_responses import MOCK_TEST_RESPONSES
from tests.mock_utils import (
    INVALID_INT_TYPE,
    INVALID_STRING_TYPE,
    MOCK_PROTOCOL_PARAMETERS,
    generate_mock_popen_function,
    mock_raise_internal_error,
)


class TestProcess(TestCase):
    def test_missing_num_input(self):
        try:
            result = get_transaction_fee(num_output=10)
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_missing_num_output(self):
        try:
            result = get_transaction_fee(num_input=1)
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_invalid_num_input(self):
        try:
            result = get_transaction_fee(num_input="invalid", num_output=10)
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_invalid_num_output(self):
        try:
            result = get_transaction_fee(num_input=1, num_output="invalid")
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_invalid_draft_file(self):
        try:
            result = get_transaction_fee(num_input=1, num_output=10, draft_file=-1)
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid draft file type."
        assert result.additional_context["type"] == INVALID_INT_TYPE

    def test_invalid_num_witness(self):
        try:
            result = get_transaction_fee(
                num_input=1,
                num_output=10,
                num_witness="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid number of witness value type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_network(self):
        try:
            result = get_transaction_fee(num_input=1, num_output=10, network="invalid")
        except Exception as e:
            result = e

        assert isinstance(result, InvalidNetwork)
        assert result.additional_context.get("network") == "invalid"

    def test_invalid_method(self):
        try:
            result = get_transaction_fee(num_input=1, num_output=10, method="invalid")
        except Exception as e:
            result = e

        assert isinstance(result, InvalidMethod)
        assert result.additional_context.get("method") == "invalid"

    def test_unexpected_error_during_command_execution(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = get_transaction_fee(num_input=1, num_output=10)
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Creating TX Draft File."

    def test_error_during_draft_creation(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.create_transaction_file",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = get_transaction_fee(num_input=1, num_output=10)
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Creating TX Draft File."

    def test_error_during_get_protocol_parameters(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["build-raw"] = {}
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.get_protocol_parameters",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = get_transaction_fee(num_input=1, num_output=10)
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Getting Protocol Parameters."

    def test_error_during_temp_file_deletion(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses.update(
            {
                "build-raw": {},
                "calculate-min-fee": "100 Lovelace",
                ("query", "protocol-parameters"): MOCK_PROTOCOL_PARAMETERS,
            },
        )
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.delete_temp_file",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = get_transaction_fee(num_input=1, num_output=10)
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Deleting Draft TX File."

    def test_success_without_draft_file(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses.update(
            {
                "build-raw": {},
                "rm": {},
                "calculate-min-fee": "100 Lovelace",
                ("query", "protocol-parameters"): MOCK_PROTOCOL_PARAMETERS,
            },
        )
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = get_transaction_fee(num_input=1, num_output=10)
            except Exception as e:
                result = e

        assert isinstance(result, int)
        assert result == 100

    def test_success_with_draft_file(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses.update(
            {
                "build-raw": {},
                "rm": {},
                "calculate-min-fee": "100 Lovelace",
                ("query", "protocol-parameters"): MOCK_PROTOCOL_PARAMETERS,
            },
        )
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = get_transaction_fee(
                    num_input=1,
                    num_output=10,
                    draft_file="test_tx.draft",
                )
            except Exception as e:
                result = e

        assert isinstance(result, int)
        assert result == 100
