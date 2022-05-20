from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.classes import CardanoNetwork, ScriptMethod
from cardano_mass_payments.constants.exceptions import (
    InvalidMethod,
    InvalidNetwork,
    InvalidType,
    ScriptError,
)
from cardano_mass_payments.utils.cli_utils import get_wallet_utxo
from cardano_mass_payments.utils.pycardano_utils import CardanoCLIChainContext
from tests.mock_responses import MOCK_TEST_RESPONSES
from tests.mock_utils import (
    INVALID_INT_TYPE,
    MOCK_ADDRESS,
    generate_mock_popen_function,
    mock_raise_internal_error,
)


class TestProcess(TestCase):
    def test_missing_address(self):
        try:
            result = get_wallet_utxo()
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_invalid_address(self):
        try:
            result = get_wallet_utxo(-1)
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid address type."
        assert result.additional_context["type"] == INVALID_INT_TYPE

    def test_invalid_network(self):
        try:
            result = get_wallet_utxo(MOCK_ADDRESS, network="invalid")
        except Exception as e:
            result = e

        assert isinstance(result, InvalidNetwork)
        assert result.additional_context["network"] == "invalid"

    def test_invalid_method(self):
        try:
            result = get_wallet_utxo(MOCK_ADDRESS, method="invalid")
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
                result = get_wallet_utxo(MOCK_ADDRESS)
            except Exception as e:
                result = e

        assert isinstance(result, Exception)

    def test_error_during_read_file(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.read_file",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = get_wallet_utxo(MOCK_ADDRESS)
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error While Getting UTxO File Details."

    def test_error_during_delete_file(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["cat"] = {}
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.delete_temp_file",
            side_effect=mock_raise_internal_error,
        ) as mock_delete_temp_file:
            try:
                result = get_wallet_utxo(MOCK_ADDRESS)
            except Exception as e:
                result = e

            mock_delete_temp_file.assert_called()

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error While Getting UTxO File Details."

    def test_error_during_get_extra_utxo_details(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)

        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {
                    "lovelace": 1000000000,
                    "test_policy_id": {
                        "test_token1".encode().hex(): 1,
                        "test_token2".encode().hex(): 1,
                        "test_token3".encode().hex(): 1,
                        "test_token4".encode().hex(): 1,
                    },
                },
            },
        }
        mock_responses["rm"] = {}
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.get_utxo_extra_details",
            side_effect=mock_raise_internal_error,
        ) as mock_get_utxo_extra_details:
            try:
                result = get_wallet_utxo(MOCK_ADDRESS)
            except Exception as e:
                result = e

            mock_get_utxo_extra_details.assert_called()

        assert isinstance(result, Exception)

    def test_success_with_no_token_utxo(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {
                    "lovelace": 1000000000,
                },
            },
        }
        mock_responses["rm"] = {}

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = get_wallet_utxo(MOCK_ADDRESS)
            except Exception as e:
                result = e

        assert isinstance(result, list)
        assert len(result) == 1

    def test_success_with_token_utxos(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)

        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {
                    "lovelace": 1000000000,
                    "test_policy_id": {
                        "test_token1".encode().hex(): 1,
                        "test_token2".encode().hex(): 1,
                        "test_token3".encode().hex(): 1,
                        "test_token4".encode().hex(): 1,
                    },
                },
            },
        }
        mock_responses["rm"] = {}
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = get_wallet_utxo(MOCK_ADDRESS)
            except Exception as e:
                result = e

        assert isinstance(result, list)
        assert len(result) == 0

    def test_success_pycardano(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {
                    "lovelace": 1000000000,
                },
            },
        }
        mock_responses["rm"] = {}
        mock_pycardano_context = CardanoCLIChainContext(
            cardano_network=CardanoNetwork.TESTNET,
            use_docker_cli=True,
        )

        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {
                "pycardano_context": mock_pycardano_context,
                "source_address": MOCK_ADDRESS,
            },
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = get_wallet_utxo(
                    MOCK_ADDRESS,
                    method=ScriptMethod.METHOD_PYCARDANO,
                )
            except Exception as e:
                result = e

        assert isinstance(result, list)
        assert len(result) == 1
