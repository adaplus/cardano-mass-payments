import json
import tempfile
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.classes import InputUTXO
from cardano_mass_payments.constants.common import (
    CardanoNetwork,
    DustCollectionMethod,
    ScriptMethod,
)
from cardano_mass_payments.constants.exceptions import (
    InvalidMethod,
    InvalidNetwork,
    InvalidType,
    ScriptError,
)
from cardano_mass_payments.utils.pycardano_utils import CardanoCLIChainContext
from cardano_mass_payments.utils.script_utils import dust_collect
from tests.mock_responses import MOCK_TEST_RESPONSES
from tests.mock_utils import (
    INVALID_INT_TYPE,
    INVALID_STRING_TYPE,
    MOCK_ADDRESS,
    MOCK_ADDRESS2,
    MOCK_PROTOCOL_PARAMETERS,
    MOCK_SKEY_CONTENT,
    generate_mock_popen_function,
    mock_raise_internal_error,
)


class TestProcess(TestCase):
    def test_missing_input_utxos(self):
        try:
            result = dust_collect(
                payment_group_details=[],
                transaction_draft_filename="test_tx.draft",
                max_tx_size=1000,
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_missing_transaction_draft_filename(self):
        try:
            result = dust_collect(
                input_utxos=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=i,
                        amount=1000,
                    )
                    for i in range(1000)
                ],
                payment_group_details=[],
                max_tx_size=1000,
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_missing_max_tx_size(self):
        try:
            result = dust_collect(
                input_utxos=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=i,
                        amount=1000,
                    )
                    for i in range(1000)
                ],
                payment_group_details=[],
                transaction_draft_filename="test_tx.draft",
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_missing_source_address(self):
        try:
            result = dust_collect(
                input_utxos=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=i,
                        amount=1000,
                    )
                    for i in range(1000)
                ],
                payment_group_details=[],
                transaction_draft_filename="test_tx.draft",
                max_tx_size=1000,
                source_details={MOCK_ADDRESS: ["test.skey"]},
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_missing_source_details(self):
        try:
            result = dust_collect(
                input_utxos=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=i,
                        amount=1000,
                    )
                    for i in range(1000)
                ],
                payment_group_details=[],
                transaction_draft_filename="test_tx.draft",
                max_tx_size=1000,
                source_address=MOCK_ADDRESS,
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_invalid_input_utxos(self):
        try:
            result = dust_collect(
                input_utxos="invalid",
                payment_group_details=[],
                transaction_draft_filename="test_tx.draft",
                max_tx_size=1000,
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Input UTXO List Type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_transaction_draft_filename(self):
        try:
            result = dust_collect(
                input_utxos=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=i,
                        amount=1000,
                    )
                    for i in range(1000)
                ],
                transaction_draft_filename=-1,
                max_tx_size=1000,
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Transaction Draft Filename Type."
        assert result.additional_context["type"] == INVALID_INT_TYPE

    def test_invalid_max_tx_size(self):
        try:
            result = dust_collect(
                input_utxos=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=i,
                        amount=1000,
                    )
                    for i in range(1000)
                ],
                transaction_draft_filename="test_tx.draft",
                max_tx_size="invalid",
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Max Transaction Size Type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_source_address(self):
        try:
            result = dust_collect(
                input_utxos=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=i,
                        amount=1000,
                    )
                    for i in range(1000)
                ],
                transaction_draft_filename="test_tx.draft",
                max_tx_size=1000,
                source_address=-1,
                source_details={MOCK_ADDRESS: ["test.skey"]},
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Source Address Type."
        assert result.additional_context["type"] == INVALID_INT_TYPE

    def test_invalid_source_details(self):
        try:
            result = dust_collect(
                input_utxos=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=i,
                        amount=1000,
                    )
                    for i in range(1000)
                ],
                transaction_draft_filename="test_tx.draft",
                max_tx_size=1000,
                source_address=MOCK_ADDRESS,
                source_details=-1,
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Source Details Type."
        assert result.additional_context["type"] == INVALID_INT_TYPE

    def test_invalid_network(self):
        try:
            result = dust_collect(
                input_utxos=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=i,
                        amount=1000,
                    )
                    for i in range(1000)
                ],
                transaction_draft_filename="test_tx.draft",
                max_tx_size=1000,
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
                network="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidNetwork)
        assert result.additional_context["network"] == "invalid"

    def test_invalid_method(self):
        try:
            result = dust_collect(
                input_utxos=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=i,
                        amount=1000,
                    )
                    for i in range(1000)
                ],
                transaction_draft_filename="test_tx.draft",
                max_tx_size=1000,
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
                method="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidMethod)
        assert result.additional_context["method"] == "invalid"

    def test_invalid_dust_collection_method(self):
        try:
            result = dust_collect(
                input_utxos=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=i,
                        amount=1000,
                    )
                    for i in range(1000)
                ],
                transaction_draft_filename="test_tx.draft",
                max_tx_size=1000,
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
                dust_collection_method="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Dust Collection Method Type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_dust_collection_threshold(self):
        try:
            result = dust_collect(
                input_utxos=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=i,
                        amount=1000,
                    )
                    for i in range(1000)
                ],
                transaction_draft_filename="test_tx.draft",
                max_tx_size=1000,
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
                dust_collection_threshold="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Dust Threshold Type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_reward_details(self):
        try:
            result = dust_collect(
                input_utxos=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=i,
                        amount=1000,
                    )
                    for i in range(1000)
                ],
                transaction_draft_filename="test_tx.draft",
                max_tx_size=1000,
                source_address=MOCK_ADDRESS,
                source_details={MOCK_ADDRESS: ["test.skey"]},
                reward_details="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Reward Details Type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_unexpected_error_during_command_execution(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = dust_collect(
                    input_utxos=[
                        InputUTXO(
                            address=MOCK_ADDRESS,
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=i,
                            amount=1000,
                        )
                        for i in range(1000)
                    ],
                    transaction_draft_filename="test_tx.draft",
                    max_tx_size=1000,
                    source_address=MOCK_ADDRESS,
                    source_details={MOCK_ADDRESS: ["test.skey"]},
                )
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)

    def test_error_during_get_transaction_fee(self):
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
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.script_utils.get_transaction_fee",
            side_effect=Exception("Internal Error"),
        ):
            try:
                result = dust_collect(
                    input_utxos=[
                        InputUTXO(
                            address=MOCK_ADDRESS,
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=i,
                            amount=1000,
                        )
                        for i in range(1000)
                    ],
                    transaction_draft_filename="test_tx.draft",
                    max_tx_size=1000,
                    source_address=MOCK_ADDRESS,
                    source_details={MOCK_ADDRESS: ["test.skey"]},
                )
            except Exception as e:
                result = e

        assert isinstance(result, Exception)

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
        mock_responses["build-raw"] = {}
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.script_utils.get_transaction_byte_size",
            side_effect=Exception("Internal Error"),
        ):
            try:
                result = dust_collect(
                    input_utxos=[
                        InputUTXO(
                            address=MOCK_ADDRESS,
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=i,
                            amount=1000,
                        )
                        for i in range(1000)
                    ],
                    transaction_draft_filename="test_tx.draft",
                    max_tx_size=1000,
                    source_address=MOCK_ADDRESS,
                    source_details={MOCK_ADDRESS: ["test.skey"]},
                )
            except Exception as e:
                result = e

        assert isinstance(result, Exception)

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

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = dust_collect(
                    input_utxos=[
                        InputUTXO(
                            address=(MOCK_ADDRESS if i % 10 == 0 else MOCK_ADDRESS2),
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=i,
                            amount=1000,
                        )
                        for i in range(1000)
                    ],
                    transaction_draft_filename="test_tx.draft",
                    max_tx_size=1000,
                    source_address=MOCK_ADDRESS,
                    source_details={
                        MOCK_ADDRESS: "test.skey",
                        MOCK_ADDRESS2: "test.skey",
                    },
                    dust_collection_method=DustCollectionMethod.COLLECT_TO_SOURCE,
                )
            except Exception as e:
                result = e

        assert isinstance(result, dict)
        dust_group_details = result.get("dust_group_details", {})
        assert len(dust_group_details) == 1

    def test_success_collect_per_address(self):
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

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = dust_collect(
                    input_utxos=[
                        InputUTXO(
                            address=(MOCK_ADDRESS if i % 10 == 0 else MOCK_ADDRESS2),
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=i,
                            amount=1000,
                        )
                        for i in range(1000)
                    ],
                    transaction_draft_filename="test_tx.draft",
                    max_tx_size=1000,
                    source_address=MOCK_ADDRESS,
                    source_details={
                        MOCK_ADDRESS: "test.skey",
                        MOCK_ADDRESS2: "test.skey",
                    },
                    dust_collection_method=DustCollectionMethod.COLLECT_PER_ADDRESS,
                )
            except Exception as e:
                result = e

        assert isinstance(result, dict)
        dust_group_details = result.get("dust_group_details", {})
        assert len(dust_group_details) == 2

    def test_other_payment_group_details_value_type(self):
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

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = dust_collect(
                    input_utxos=[
                        InputUTXO(
                            address=(MOCK_ADDRESS if i % 10 == 0 else MOCK_ADDRESS2),
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=i,
                            amount=1000,
                        )
                        for i in range(1000)
                    ],
                    payment_group_details="other_value",
                    transaction_draft_filename="test_tx.draft",
                    max_tx_size=1000,
                    source_address=MOCK_ADDRESS,
                    source_details={
                        MOCK_ADDRESS: "test.skey",
                        MOCK_ADDRESS2: "test.skey",
                    },
                    dust_collection_method=DustCollectionMethod.COLLECT_TO_SOURCE,
                )
            except Exception as e:
                result = e

        assert isinstance(result, dict)
        dust_group_details = result.get("dust_group_details", {})
        assert len(dust_group_details) == 1
        assert result.get("output_details") == "other_value"

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

        mock_skey_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".skey")
        mock_skey_file.write(json.dumps(MOCK_SKEY_CONTENT))
        mock_skey_file.seek(0)

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
                result = dust_collect(
                    input_utxos=[
                        InputUTXO(
                            address=(MOCK_ADDRESS if i % 10 == 0 else MOCK_ADDRESS2),
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=i,
                            amount=1000,
                        )
                        for i in range(5)
                    ],
                    transaction_draft_filename="test_tx.draft",
                    max_tx_size=1000,
                    source_address=MOCK_ADDRESS,
                    source_details={
                        MOCK_ADDRESS: [mock_skey_file.name],
                        MOCK_ADDRESS2: [mock_skey_file.name],
                    },
                    method=ScriptMethod.METHOD_PYCARDANO,
                )
            except Exception as e:
                result = e

        assert isinstance(result, dict)
        dust_group_details = result.get("dust_group_details", {})
        assert len(dust_group_details) == 1

    def test_success_with_reward_details(self):
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

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = dust_collect(
                    input_utxos=[
                        InputUTXO(
                            address=(MOCK_ADDRESS if i % 10 == 0 else MOCK_ADDRESS2),
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=i,
                            amount=1000,
                        )
                        for i in range(1000)
                    ],
                    transaction_draft_filename="test_tx.draft",
                    max_tx_size=1000,
                    source_address=MOCK_ADDRESS,
                    source_details={
                        MOCK_ADDRESS: "test.skey",
                        MOCK_ADDRESS2: "test.skey",
                    },
                    dust_collection_method=DustCollectionMethod.COLLECT_TO_SOURCE,
                    reward_details={
                        "stake_address": "test_stake_address",
                        "stake_amount": 1000,
                    },
                )
            except Exception as e:
                result = e

        assert isinstance(result, dict)
        dust_group_details = result.get("dust_group_details", {})
        assert len(dust_group_details) == 1
