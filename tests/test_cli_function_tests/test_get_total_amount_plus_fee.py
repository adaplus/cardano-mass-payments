from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.classes import InputUTXO, PaymentDetail
from cardano_mass_payments.constants.exceptions import (
    EmptyList,
    InvalidMethod,
    InvalidNetwork,
    InvalidType,
    ScriptError,
)
from cardano_mass_payments.utils.cli_utils import get_total_amount_plus_fee
from tests.mock_responses import MOCK_TEST_RESPONSES
from tests.mock_utils import (
    INVALID_STRING_TYPE,
    MOCK_PROTOCOL_PARAMETERS,
    generate_mock_popen_function,
    mock_raise_internal_error,
)


class TestProcess(TestCase):
    def test_missing_input_arg(self):
        try:
            result = get_total_amount_plus_fee(
                output_list=[
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                ],
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_missing_output_list(self):
        try:
            result = get_total_amount_plus_fee(input_arg=1)
        except Exception as e:
            result = e
        assert isinstance(result, TypeError)

    def test_invalid_input_arg(self):
        try:
            result = get_total_amount_plus_fee(
                input_arg="invalid",
                output_list=[
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                ],
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid input argument type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_output_list(self):
        try:
            result = get_total_amount_plus_fee(input_arg=1, output_list="invalid")
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid output argument type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_num_witness(self):
        try:
            result = get_total_amount_plus_fee(
                input_arg=1,
                output_list=[
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                ],
                num_witness="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid number of witness value type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_input_arg_less_than_1(self):
        try:
            result = get_total_amount_plus_fee(
                input_arg=-1,
                output_list=[
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                ],
            )
        except Exception as e:
            result = e

        assert isinstance(result, EmptyList)
        assert result.additional_context.get("field") == "Input UTxO List"

    def test_empty_output_list(self):
        try:
            result = get_total_amount_plus_fee(input_arg=1, output_list=[])
        except Exception as e:
            result = e

        assert isinstance(result, EmptyList)
        assert result.additional_context.get("field") == "Output UTxO List"

    def test_num_witness_less_than_1(self):
        try:
            result = get_total_amount_plus_fee(
                input_arg=1,
                output_list=[
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                ],
                num_witness=-1,
            )
        except Exception as e:
            result = e

        assert isinstance(result, EmptyList)
        assert result.additional_context.get("field") == "Witness List"

    def test_invalid_network(self):
        try:
            result = get_total_amount_plus_fee(
                input_arg=1,
                output_list=[
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                ],
                network="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidNetwork)
        assert result.additional_context["network"] == "invalid"

    def test_invalid_method(self):
        try:
            result = get_total_amount_plus_fee(
                input_arg=1,
                output_list=[
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                ],
                method="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidMethod)
        assert result.additional_context["method"] == "invalid"

    def test_unexpected_error_during_command_execution(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = get_total_amount_plus_fee(
                    input_arg=1,
                    output_list=[
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                    ],
                )
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Creating Draft TX File."

    def test_error_during_draft_creation(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.create_transaction_file",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = get_total_amount_plus_fee(
                    input_arg=1,
                    output_list=[
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                    ],
                )
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Creating Draft TX File."

    def test_error_during_get_transaction_fee(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["build-raw"] = {}
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.get_transaction_fee",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = get_total_amount_plus_fee(
                    input_arg=1,
                    output_list=[
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                    ],
                )
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Getting TX Fee."

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
                result = get_total_amount_plus_fee(
                    input_arg=1,
                    output_list=[
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                    ],
                )
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Deleting UTxO File."

    def test_success(self):
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
                result = get_total_amount_plus_fee(
                    input_arg=1,
                    output_list=[
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                    ],
                )
            except Exception as e:
                result = e

        assert isinstance(result, tuple)
        assert result == (5000, 100)

    def test_success_input_arg_list(self):
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
                result = get_total_amount_plus_fee(
                    input_arg=[
                        InputUTXO(
                            address="test_source_address",
                            tx_hash="test_hash",
                            tx_index=0,
                            amount=10000,
                        ),
                    ],
                    output_list=[
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                    ],
                )
            except Exception as e:
                result = e

        assert isinstance(result, tuple)
        assert result == (5000, 100)
