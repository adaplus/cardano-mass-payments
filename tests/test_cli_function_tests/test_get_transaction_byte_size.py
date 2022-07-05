from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.classes import InputUTXO, PaymentDetail
from cardano_mass_payments.constants.common import CardanoNetwork, ScriptMethod
from cardano_mass_payments.constants.exceptions import (
    EmptyList,
    InvalidMethod,
    InvalidNetwork,
    InvalidType,
    ScriptError,
)
from cardano_mass_payments.utils.cli_utils import get_transaction_byte_size
from cardano_mass_payments.utils.pycardano_utils import CardanoCLIChainContext
from tests.mock_responses import MOCK_TEST_RESPONSES
from tests.mock_utils import (
    INVALID_STRING_TYPE,
    MOCK_ADDRESS,
    MOCK_PROTOCOL_PARAMETERS,
    generate_mock_popen_function,
    mock_raise_internal_error,
)


class TestProcess(TestCase):
    def test_missing_input_arg(self):
        try:
            result = get_transaction_byte_size(
                output_arg=[
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

    def test_missing_output_arg(self):
        try:
            result = get_transaction_byte_size(
                input_arg=1,
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_invalid_input_arg(self):
        try:
            result = get_transaction_byte_size(
                input_arg="invalid",
                output_arg=[
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

    def test_input_arg_less_than_1(self):
        try:
            result = get_transaction_byte_size(
                input_arg=-1,
                output_arg=[
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

    def test_invalid_output_arg(self):
        try:
            result = get_transaction_byte_size(
                input_arg=1,
                output_arg="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid output argument type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_empty_output_list(self):
        try:
            result = get_transaction_byte_size(input_arg=1, output_arg=[])
        except Exception as e:
            result = e

        assert isinstance(result, EmptyList)
        assert result.additional_context.get("field") == "Output UTxO List"

    def test_invalid_method(self):
        try:
            result = get_transaction_byte_size(
                input_arg=1,
                output_arg=[
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

    def test_invalid_network(self):
        try:
            result = get_transaction_byte_size(
                input_arg=1,
                output_arg=[
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

    def test_invalid_signing_key_files(self):
        try:
            result = get_transaction_byte_size(
                input_arg=1,
                output_arg=[
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                ],
                signing_key_files="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid signing key file list argument type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_reward_details(self):
        try:
            result = get_transaction_byte_size(
                input_arg=1,
                output_arg=[
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                    PaymentDetail(address="test_address", amount=1000),
                ],
                reward_details="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid reward details type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_unexpected_error_during_command_execution(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = get_transaction_byte_size(
                    input_arg=1,
                    output_arg=[
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
        assert result.message == "Unexpected Error Creating TX Draft File."

    def test_error_during_transaction_file_creation(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.create_transaction_file",
            side_effect=Exception("Internal error"),
        ):
            try:
                result = get_transaction_byte_size(
                    input_arg=1,
                    output_arg=[
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
        assert result.message == "Unexpected Error Creating TX Draft File."

    def test_error_during_transaction_fee_computation(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["build-raw"] = {}

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.get_transaction_fee",
            side_effect=Exception("Internal error"),
        ):
            try:
                result = get_transaction_byte_size(
                    input_arg=1,
                    output_arg=[
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

    def test_error_during_latest_slot_number_fetch(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["build-raw"] = {}
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.get_latest_slot_number",
            side_effect=Exception("Internal error"),
        ):
            try:
                result = get_transaction_byte_size(
                    input_arg=1,
                    output_arg=[
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
        assert result.message == "Unexpected Error Getting Latest Slot Number."

    def test_error_during_transaction_file_signing(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["build-raw"] = {}
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses["rm"] = {}
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=Exception("Internal error"),
        ):
            try:
                result = get_transaction_byte_size(
                    input_arg=1,
                    output_arg=[
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
        assert result.message == "Unexpected Error Signing TX File."

    def test_error_during_transaction_file_computation(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["build-raw"] = {}
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses["sign"] = {}
        mock_responses["rm"] = {}
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS

        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {
                "source_signing_key_file": ["test.skey"],
            },
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.get_tx_size",
            side_effect=Exception("Internal error"),
        ):
            try:
                result = get_transaction_byte_size(
                    input_arg=1,
                    output_arg=[
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
        assert result.message == "Unexpected Error Getting TX File Size."

    def test_error_during_transaction_file_deletion(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["build-raw"] = {}
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses["sign"] = {}
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS

        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {
                "source_signing_key_file": ["test.skey"],
            },
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.delete_temp_file",
            side_effect=Exception("Internal error"),
        ):
            try:
                result = get_transaction_byte_size(
                    input_arg=1,
                    output_arg=[
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
        assert result.message == "Unexpected Error Deleting Signing Key File."

    def test_success(self):
        cbor_hex_string = "test_cborhex".encode("utf-8").hex()
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["build-raw"] = {}
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses["sign"] = {}
        mock_responses["rm"] = {}
        mock_responses["cat"] = {"cborHex": cbor_hex_string}
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS

        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {
                "source_signing_key_file": ["test.skey"],
            },
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = get_transaction_byte_size(
                    input_arg=1,
                    output_arg=[
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                    ],
                )
            except Exception as e:
                result = e

        assert isinstance(result, int)
        assert result == len(bytearray.fromhex(cbor_hex_string))

    def test_success_pycardano_method_int_input_int_output(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS
        mock_responses["rm"] = {}

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.pycardano_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {
                "pycardano_context": CardanoCLIChainContext(
                    cardano_network=CardanoNetwork.TESTNET,
                    use_docker_cli=True,
                ),
                "source_address": MOCK_ADDRESS,
            },
        ):
            try:
                result = get_transaction_byte_size(
                    input_arg=1,
                    output_arg=10,
                    method=ScriptMethod.METHOD_PYCARDANO,
                )
            except Exception as e:
                result = e

        assert isinstance(result, int)
        assert result > 0

    def test_success_pycardano_method_int_input_list_output(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS
        mock_responses["rm"] = {}

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.pycardano_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {
                "pycardano_context": CardanoCLIChainContext(
                    cardano_network=CardanoNetwork.TESTNET,
                    use_docker_cli=True,
                ),
                "source_address": MOCK_ADDRESS,
            },
        ):
            try:
                result = get_transaction_byte_size(
                    input_arg=1,
                    output_arg=[
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                    ],
                    method=ScriptMethod.METHOD_PYCARDANO,
                )
            except Exception as e:
                result = e

        assert isinstance(result, int)
        assert result > 0

    def test_success_pycardano_method_list_input_int_output(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS
        mock_responses["rm"] = {}

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.pycardano_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {
                "pycardano_context": CardanoCLIChainContext(
                    cardano_network=CardanoNetwork.TESTNET,
                    use_docker_cli=True,
                ),
                "source_address": MOCK_ADDRESS,
            },
        ):
            try:
                result = get_transaction_byte_size(
                    input_arg=[
                        InputUTXO(
                            address=MOCK_ADDRESS,
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=0,
                            amount=10,
                        ),
                        InputUTXO(
                            address=MOCK_ADDRESS,
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=1,
                            amount=10,
                        ),
                    ],
                    output_arg=10,
                    method=ScriptMethod.METHOD_PYCARDANO,
                )
            except Exception as e:
                result = e

        assert isinstance(result, int)
        assert result > 0

    def test_success_pycardano_method_list_input_list_output(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS
        mock_responses["rm"] = {}

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.pycardano_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {
                "pycardano_context": CardanoCLIChainContext(
                    cardano_network=CardanoNetwork.TESTNET,
                    use_docker_cli=True,
                ),
                "source_address": MOCK_ADDRESS,
            },
        ):
            try:
                result = get_transaction_byte_size(
                    input_arg=[
                        InputUTXO(
                            address=MOCK_ADDRESS,
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=0,
                            amount=10,
                        ),
                        InputUTXO(
                            address=MOCK_ADDRESS,
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=1,
                            amount=10,
                        ),
                    ],
                    output_arg=[
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                    ],
                    method=ScriptMethod.METHOD_PYCARDANO,
                )
            except Exception as e:
                result = e

        assert isinstance(result, int)
        assert result > 0

    def test_success_with_reward_details(self):
        cbor_hex_string = "test_cborhex".encode("utf-8").hex()
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["build-raw"] = {}
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses["sign"] = {}
        mock_responses["rm"] = {}
        mock_responses["cat"] = {"cborHex": cbor_hex_string}
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS

        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {
                "source_signing_key_file": ["test.skey"],
            },
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = get_transaction_byte_size(
                    input_arg=1,
                    output_arg=[
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                        PaymentDetail(address="test_address", amount=1000),
                    ],
                    reward_details={
                        "stake_address": "test_stake_address",
                        "stake_amount": 1000,
                    },
                )
            except Exception as e:
                result = e

        assert isinstance(result, int)
        assert result == len(bytearray.fromhex(cbor_hex_string))
