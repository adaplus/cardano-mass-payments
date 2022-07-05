from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.constants.common import CardanoNetwork, ScriptMethod
from cardano_mass_payments.constants.exceptions import (
    InsufficientBalance,
    InvalidMethod,
    InvalidNetwork,
    InvalidType,
    ScriptError,
)
from cardano_mass_payments.utils.pycardano_utils import CardanoCLIChainContext
from cardano_mass_payments.utils.script_utils import preparation_step
from tests.mock_responses import MOCK_TEST_RESPONSES
from tests.mock_utils import (
    INVALID_INT_TYPE,
    INVALID_STRING_TYPE,
    MOCK_ADDRESS,
    MOCK_PROTOCOL_PARAMETERS,
    MOCK_STAKE_ADDRESS,
    create_test_payment_csv,
    generate_mock_popen_function,
    mock_raise_internal_error,
)


class TestProcess(TestCase):
    def test_missing_source_address(self):
        payments_file = create_test_payment_csv(100)
        try:
            result = preparation_step(
                source_details={MOCK_ADDRESS: ["test.skey"]},
                payments_utxo_file=payments_file.name,
            )
        except Exception as e:
            result = e

        payments_file.close()
        assert isinstance(result, TypeError)

    def test_missing_source_details(self):
        payments_file = create_test_payment_csv(100)
        try:
            result = preparation_step(
                source_address=MOCK_ADDRESS,
                payments_utxo_file=payments_file.name,
            )
        except Exception as e:
            result = e

        payments_file.close()
        assert isinstance(result, TypeError)

    def test_missing_payments_utxo_file(self):
        try:
            result = preparation_step(
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_invalid_source_address(self):
        payments_file = create_test_payment_csv(100)
        try:
            result = preparation_step(
                source_address=-1,
                source_details={MOCK_ADDRESS: ["test.skey"]},
                payments_utxo_file=payments_file.name,
            )
        except Exception as e:
            result = e

        payments_file.close()
        assert isinstance(result, InvalidType)
        assert result.message == "Invalid source address type."
        assert result.additional_context["type"] == INVALID_INT_TYPE

    def test_invalid_source_details(self):
        payments_file = create_test_payment_csv(100)
        try:
            result = preparation_step(
                source_address=MOCK_ADDRESS,
                source_details=-1,
                payments_utxo_file=payments_file.name,
            )
        except Exception as e:
            result = e

        payments_file.close()
        assert isinstance(result, InvalidType)
        assert result.message == "Invalid source details type."
        assert result.additional_context["type"] == INVALID_INT_TYPE

    def test_invalid_payments_utxo_file(self):
        try:
            result = preparation_step(
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
                payments_utxo_file=-1,
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid payments UTxO file type."
        assert result.additional_context["type"] == INVALID_INT_TYPE

    def test_invalid_network(self):
        payments_file = create_test_payment_csv(100)
        try:
            result = preparation_step(
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
                payments_utxo_file=payments_file.name,
                network="invalid",
            )
        except Exception as e:
            result = e

        payments_file.close()
        assert isinstance(result, InvalidNetwork)
        assert result.additional_context["network"] == "invalid"

    def test_invalid_method(self):
        payments_file = create_test_payment_csv(100)
        try:
            result = preparation_step(
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
                payments_utxo_file=payments_file.name,
                method="invalid",
            )
        except Exception as e:
            result = e

        payments_file.close()
        assert isinstance(result, InvalidMethod)
        assert result.additional_context["method"] == "invalid"

    def test_invalid_include_rewards(self):
        payments_file = create_test_payment_csv(100)
        try:
            result = preparation_step(
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
                payments_utxo_file=payments_file.name,
                include_rewards="invalid",
            )
        except Exception as e:
            result = e

        payments_file.close()
        assert isinstance(result, InvalidType)
        assert result.message == "Invalid include rewards type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_unexpected_error_during_command_execution(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=mock_raise_internal_error,
        ):
            payments_file = create_test_payment_csv(100)
            try:
                result = preparation_step(
                    source_address=MOCK_ADDRESS,
                    source_details={MOCK_ADDRESS: ["test.skey"]},
                    payments_utxo_file=payments_file.name,
                )
            except Exception as e:
                result = e
            payments_file.close()

        assert isinstance(result, ScriptError)

    def test_error_during_parse_payment_utxo_file(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.script_utils.parse_payment_utxo_file",
            side_effect=mock_raise_internal_error,
        ):
            payments_file = create_test_payment_csv(100)
            try:
                result = preparation_step(
                    source_address=MOCK_ADDRESS,
                    source_details={MOCK_ADDRESS: ["test.skey"]},
                    payments_utxo_file=payments_file.name,
                )
            except Exception as e:
                result = e
            payments_file.close()

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Parsing UTxO File."

    def test_error_during_get_wallet_utxos(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.script_utils.get_wallet_utxo",
            side_effect=mock_raise_internal_error,
        ):
            payments_file = create_test_payment_csv(100)
            try:
                result = preparation_step(
                    source_address=MOCK_ADDRESS,
                    source_details={MOCK_ADDRESS: ["test.skey"]},
                    payments_utxo_file=payments_file.name,
                )
            except Exception as e:
                result = e
            payments_file.close()

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Fetching Wallet UTxO."

    def test_error_during_group_output_utxos(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.script_utils.group_output_utxo",
            side_effect=mock_raise_internal_error,
        ):
            payments_file = create_test_payment_csv(100)
            try:
                result = preparation_step(
                    source_address=MOCK_ADDRESS,
                    source_details={MOCK_ADDRESS: ["test.skey"]},
                    payments_utxo_file=payments_file.name,
                )
            except Exception as e:
                result = e
            payments_file.close()

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Grouping Output UTxOs."

    def test_error_during_get_total_amount_and_fee(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses["sign"] = {}
        mock_responses["rm"] = {}
        mock_responses["cat"] = {}
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS

        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {
                "metadata_file": None,
                "source_signing_key_file": ["test.skey"],
            },
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.script_utils.get_total_amount_plus_fee",
            side_effect=mock_raise_internal_error,
        ):
            payments_file = create_test_payment_csv(100)
            try:
                result = preparation_step(
                    source_address=MOCK_ADDRESS,
                    source_details={MOCK_ADDRESS: ["test.skey"]},
                    payments_utxo_file=payments_file.name,
                )
            except Exception as e:
                result = e
            payments_file.close()

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Getting Total Amount and Fee."

    def test_error_during_create_transaction_file(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses["sign"] = {}
        mock_responses["rm"] = {}
        mock_responses["cat"] = {}
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS

        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {
                "metadata_file": None,
                "source_signing_key_file": ["test.skey"],
            },
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.script_utils.get_total_amount_plus_fee",
            side_effect=mock_raise_internal_error,
        ):
            payments_file = create_test_payment_csv(100)
            try:
                result = preparation_step(
                    source_address=MOCK_ADDRESS,
                    source_details={MOCK_ADDRESS: ["test.skey"]},
                    payments_utxo_file=payments_file.name,
                )
            except Exception as e:
                result = e
            payments_file.close()

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Getting Total Amount and Fee."

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
            payments_file = create_test_payment_csv(100)
            try:
                result = preparation_step(
                    source_address=MOCK_ADDRESS,
                    source_details={MOCK_ADDRESS: ["test.skey"]},
                    payments_utxo_file=payments_file.name,
                )
            except Exception as e:
                result = e
            payments_file.close()

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Getting Protocol Parameters."

    def test_error_during_get_transaction_size(self):
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
            payments_file = create_test_payment_csv(100)
            try:
                result = preparation_step(
                    source_address=MOCK_ADDRESS,
                    source_details={MOCK_ADDRESS: ["test.skey"]},
                    payments_utxo_file=payments_file.name,
                )
            except Exception as e:
                result = e
            payments_file.close()

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Getting TX Byte Size."

    def test_insufficient_balance(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000},
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
            {"source_signing_key_file": ["test.skey"]},
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            payments_file = create_test_payment_csv(100)
            try:
                result = preparation_step(
                    source_address=MOCK_ADDRESS,
                    source_details={MOCK_ADDRESS: ["test.skey"]},
                    payments_utxo_file=payments_file.name,
                )
            except Exception as e:
                result = e
            payments_file.close()

        assert isinstance(result, InsufficientBalance)

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
            {"source_signing_key_file": ["test.skey"]},
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            payments_file = create_test_payment_csv(100)
            try:
                result = preparation_step(
                    source_address=MOCK_ADDRESS,
                    source_details={MOCK_ADDRESS: ["test.skey"]},
                    payments_utxo_file=payments_file.name,
                )
            except Exception as e:
                result = e
            payments_file.close()

        assert isinstance(result, dict)

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

        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {
                "metadata_file": None,
            },
        ), patch(
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
            },
        ):
            payments_file = create_test_payment_csv(100)
            try:
                result = preparation_step(
                    source_address=MOCK_ADDRESS,
                    source_details={MOCK_ADDRESS: ["test.skey"]},
                    payments_utxo_file=payments_file.name,
                    method=ScriptMethod.METHOD_PYCARDANO,
                )
            except Exception as e:
                result = e
            payments_file.close()

        assert isinstance(result, dict)

    def test_success_with_rewards(self):
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
        mock_protocol_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_protocol_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_protocol_parameters
        mock_responses[("cardano-address", "address")] = {
            "stake_key_hash": "test_stake_key_hash",
        }
        mock_responses['"bech32'] = MOCK_STAKE_ADDRESS
        mock_responses[("query", "stake-address-info")] = [
            {
                "rewardAccountBalance": 1000000,
            },
        ]

        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {"source_signing_key_file": ["test.skey"]},
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            payments_file = create_test_payment_csv(100)
            try:
                result = preparation_step(
                    source_address=MOCK_ADDRESS,
                    source_details={MOCK_ADDRESS: ["test.skey"]},
                    payments_utxo_file=payments_file.name,
                    include_rewards=True,
                )
            except Exception as e:
                result = e
            payments_file.close()

        assert isinstance(result, dict)
