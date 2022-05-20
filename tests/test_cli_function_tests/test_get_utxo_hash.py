from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.constants.common import CardanoNetwork, ScriptMethod
from cardano_mass_payments.constants.exceptions import (
    InvalidMethod,
    InvalidNetwork,
    InvalidType,
)
from cardano_mass_payments.utils.cli_utils import get_utxo_hash
from cardano_mass_payments.utils.pycardano_utils import CardanoCLIChainContext
from tests.mock_responses import MOCK_TEST_RESPONSES
from tests.mock_utils import (
    INVALID_INT_TYPE,
    MOCK_ADDRESS,
    generate_mock_popen_function,
    mock_raise_internal_error,
)


class TestProcess(TestCase):
    def test_missing_transaction_file(self):
        try:
            result = get_utxo_hash()
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_invalid_transaction_file(self):
        try:
            result = get_utxo_hash(-1)
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Transction File Type."
        assert result.additional_context["type"] == INVALID_INT_TYPE

    def test_invalid_network(self):
        try:
            result = get_utxo_hash("test_tx_file.raw", network="invalid")
        except Exception as e:
            result = e

        assert isinstance(result, InvalidNetwork)
        assert result.additional_context["network"] == "invalid"

    def test_invalid_method(self):
        try:
            result = get_utxo_hash("test_tx_file.raw", method="invalid")
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
                result = get_utxo_hash("test_tx_file.raw")
            except Exception as e:
                result = e

        assert isinstance(result, Exception)

    def test_success(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("transaction", "txid")] = "test_txid"
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = get_utxo_hash("test_tx_file.raw")
            except Exception as e:
                result = e

        assert isinstance(result, str)
        assert result == "test_txid"

    def test_success_pycardano(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("transaction", "txid")] = "test_txid"
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
                result = get_utxo_hash(
                    "test_tx_file.raw",
                    method=ScriptMethod.METHOD_PYCARDANO,
                )
            except Exception as e:
                result = e

        assert isinstance(result, str)
        assert result == "test_txid"
