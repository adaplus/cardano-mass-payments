import json
import tempfile
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.constants.common import CardanoNetwork, ScriptMethod
from cardano_mass_payments.constants.exceptions import (
    InvalidFileError,
    InvalidMethod,
    InvalidNetwork,
    InvalidType,
    ScriptError,
)
from cardano_mass_payments.utils.cli_utils import create_transaction_file, sign_tx_file
from cardano_mass_payments.utils.pycardano_utils import CardanoCLIChainContext
from tests.mock_responses import MOCK_TEST_RESPONSES
from tests.mock_utils import (
    INVALID_INT_TYPE,
    MOCK_ADDRESS,
    MOCK_SKEY_CONTENT,
    generate_mock_popen_function,
    mock_raise_internal_error,
)


class TestProcess(TestCase):
    def test_missing_tx_file(self):
        try:
            result = sign_tx_file(signing_key_files=["test.skey"])
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_missing_signing_key_files(self):
        try:
            result = sign_tx_file(tx_file="test.raw")
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_invalid_tx_file(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["cat"] = {}
        mock_responses["rm"] = {}

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = sign_tx_file(tx_file=-1, signing_key_files=["test.skey"])
            except Exception as e:
                result = e

        assert isinstance(result, InvalidFileError)
        assert result.message == "Unexpected Error During Transaction Signing."
        assert result.additional_context["file"] == -1

    def test_invalid_signing_key_files(self):
        try:
            result = sign_tx_file(tx_file="test.raw", signing_key_files=-1)
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid signing key file list argument type."
        assert result.additional_context["type"] == INVALID_INT_TYPE

    def test_invalid_method(self):
        try:
            result = sign_tx_file(
                tx_file="test.raw",
                signing_key_files=["test.skey"],
                method="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidMethod)
        assert result.additional_context["method"] == "invalid"

    def test_invalid_network(self):
        try:
            result = sign_tx_file(
                tx_file="test.raw",
                signing_key_files=["test.skey"],
                network="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidNetwork)
        assert result.additional_context["network"] == "invalid"

    def test_unexpected_error_during_command_execution(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = sign_tx_file(
                    tx_file="test.raw",
                    signing_key_files=["test.skey"],
                )
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)
        assert (
            result.message
            == "Unexpected Error Creating a temporary copy in Docker Container."
        )

    def test_error_during_copy_file_to_docker(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.create_file_copy_in_docker_container",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = sign_tx_file(
                    tx_file="test.raw",
                    signing_key_files=["test.skey"],
                    method=ScriptMethod.METHOD_DOCKER_CLI,
                )
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)
        assert (
            result.message
            == "Unexpected Error Creating a temporary copy in Docker Container."
        )

    def test_unexpected_error_during_delete_temp_file(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["sign"] = {}
        mock_responses["cat"] = {}

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.delete_temp_file",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = sign_tx_file(
                    tx_file="test.raw",
                    signing_key_files=["test.skey"],
                )
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Deleting Signing Key File."

    def test_success(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["sign"] = {}
        mock_responses["cat"] = {}
        mock_responses["rm"] = {}

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = sign_tx_file(
                    tx_file="test.raw",
                    signing_key_files=["test.skey"],
                    method=ScriptMethod.METHOD_DOCKER_CLI,
                )
            except Exception as e:
                result = e

        assert isinstance(result, str)
        assert result == "test.raw.signed"

    def test_success_pycardano(self):
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
        ):
            mock_tx_file = create_transaction_file(
                1,
                10,
                method=ScriptMethod.METHOD_PYCARDANO,
                is_draft=False,
            )
            mock_tx_witnesses = mock_tx_file.get(
                "transaction_object",
            ).transaction_witness_set.vkey_witnesses

            mock_skey_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".skey")
            mock_skey_file.write(json.dumps(MOCK_SKEY_CONTENT))
            mock_skey_file.seek(0)

            try:
                result = sign_tx_file(
                    tx_file=mock_tx_file,
                    signing_key_files=[mock_skey_file.name],
                    method=ScriptMethod.METHOD_PYCARDANO,
                )
            except Exception as e:
                result = e

            mock_skey_file.close()

        assert isinstance(result, dict)
        assert (
            mock_tx_witnesses
            != result.get("transaction_object").transaction_witness_set.vkey_witnesses
        )
