from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.constants.common import CardanoNetwork
from cardano_mass_payments.constants.exceptions import (
    InvalidMethod,
    InvalidNetwork,
    InvalidType,
)
from cardano_mass_payments.utils.cli_utils import get_protocol_parameters
from tests.mock_responses import MOCK_TEST_RESPONSES
from tests.mock_utils import (
    INVALID_STRING_TYPE,
    MOCK_PROTOCOL_PARAMETERS,
    generate_mock_popen_function,
    mock_raise_internal_error,
)


class TestProcess(TestCase):
    def test_invalid_network(self):
        try:
            result = get_protocol_parameters(network="invalid")
        except Exception as e:
            result = e

        assert isinstance(result, InvalidNetwork)
        assert result.additional_context.get("network") == "invalid"

    def test_invalid_method(self):
        try:
            result = get_protocol_parameters(method="invalid")
        except Exception as e:
            result = e

        assert isinstance(result, InvalidMethod)
        assert result.additional_context.get("method") == "invalid"

    def test_invalid_return_file(self):
        try:
            result = get_protocol_parameters(return_file="invalid")
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid return file argument type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_unexpected_error_during_command_execution(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = get_protocol_parameters()
            except Exception as e:
                result = e

        assert isinstance(result, Exception)
        assert str(result) == "Internal Error"

    def test_success_no_file_returned(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = get_protocol_parameters()
            except Exception as e:
                result = e

        assert result == {
            "max_tx_size": MOCK_PROTOCOL_PARAMETERS["maxTxSize"],
            "min_fee_per_transaction": MOCK_PROTOCOL_PARAMETERS["txFeeFixed"],
            "fee_per_byte": MOCK_PROTOCOL_PARAMETERS["txFeePerByte"],
        }

    def test_success_file_returned(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                testnet_result = get_protocol_parameters(return_file=True)
                mainnet_result = get_protocol_parameters(
                    network=CardanoNetwork.MAINNET,
                    return_file=True,
                )
            except Exception as e:
                testnet_result = e
                mainnet_result = e

        assert testnet_result == "testnet-protocol.json"
        assert mainnet_result == "mainnet-protocol.json"
