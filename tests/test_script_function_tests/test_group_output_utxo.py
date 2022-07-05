from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.classes import PaymentDetail
from cardano_mass_payments.constants.common import CardanoNetwork, ScriptMethod
from cardano_mass_payments.constants.exceptions import (
    InvalidMethod,
    InvalidNetwork,
    InvalidType,
    ScriptError,
)
from cardano_mass_payments.utils.pycardano_utils import CardanoCLIChainContext
from cardano_mass_payments.utils.script_utils import group_output_utxo
from tests.mock_responses import MOCK_TEST_RESPONSES
from tests.mock_utils import (
    INVALID_INT_TYPE,
    MOCK_ADDRESS,
    MOCK_PROTOCOL_PARAMETERS,
    generate_mock_popen_function,
    mock_raise_internal_error,
)


class TestProcess(TestCase):
    def test_missing_output_list(self):
        try:
            result = group_output_utxo()
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_invalid_output_list(self):
        try:
            result = group_output_utxo(output_list=-1)
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid output list type."
        assert result.additional_context["type"] == INVALID_INT_TYPE

    def test_invalid_network(self):
        try:
            result = group_output_utxo(
                output_list=[
                    PaymentDetail(address="test_address", amount=1000)
                    for _ in range(100)
                ],
                network="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidNetwork)
        assert result.additional_context["network"] == "invalid"

    def test_invalid_method(self):
        try:
            result = group_output_utxo(
                output_list=[
                    PaymentDetail(address="test_address", amount=1000)
                    for _ in range(100)
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
                result = group_output_utxo(
                    output_list=[
                        PaymentDetail(address="test_address", amount=1000)
                        for _ in range(100)
                    ],
                )
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)

    def test_error_during_get_protocol_parameters(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses["sign"] = {}
        mock_responses["rm"] = {}
        mock_responses["cat"] = {}

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.script_utils.get_protocol_parameters",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = group_output_utxo(
                    output_list=[
                        PaymentDetail(address="test_address", amount=1000)
                        for _ in range(100)
                    ],
                )
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Getting Protocol Parameters."

    def test_error_during_get_transaction_byte_size(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses["sign"] = {}
        mock_responses["rm"] = {}
        mock_responses["cat"] = {}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.script_utils.get_transaction_byte_size",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = group_output_utxo(
                    output_list=[
                        PaymentDetail(address="test_address", amount=1000)
                        for _ in range(100)
                    ],
                )
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Getting TX Byte Size."

    def test_success(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses["sign"] = {}
        mock_responses["rm"] = {}
        mock_responses["cat"] = {}
        mock_responses["build-raw"] = {}
        mock_responses["calculate-min-fee"] = "100 Lovelace"
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
                result = group_output_utxo(
                    output_list=[
                        PaymentDetail(address="test_address", amount=1000)
                        for _ in range(100)
                    ],
                )
            except Exception as e:
                result = e

        assert isinstance(result, list)

    def test_success_pycardano(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses["sign"] = {}
        mock_responses["rm"] = {}
        mock_responses["cat"] = {}
        mock_responses["build-raw"] = {}
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS

        mock_pycardano_context = CardanoCLIChainContext(
            cardano_network=CardanoNetwork.TESTNET,
            use_docker_cli=True,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.pycardano_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {
                "pycardano_context": mock_pycardano_context,
                "source_address": MOCK_ADDRESS,
                "metadata_file": None,
            },
        ):
            try:
                result = group_output_utxo(
                    output_list=[
                        PaymentDetail(address="test_address", amount=1000)
                        for _ in range(100)
                    ],
                    method=ScriptMethod.METHOD_PYCARDANO,
                )
            except Exception as e:
                result = e

        assert isinstance(result, list)
