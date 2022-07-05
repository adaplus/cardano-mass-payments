from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.classes import (
    InputUTXO,
    PaymentDetail,
    PaymentGroup,
    TransactionPlan,
)
from cardano_mass_payments.constants.common import CardanoNetwork, ScriptMethod
from cardano_mass_payments.constants.exceptions import (
    InsufficientBalance,
    InvalidFileError,
    InvalidMethod,
    InvalidNetwork,
    InvalidType,
    ScriptError,
)
from cardano_mass_payments.utils.pycardano_utils import CardanoCLIChainContext
from cardano_mass_payments.utils.script_utils import adjust_utxos
from tests.mock_responses import MOCK_TEST_RESPONSES
from tests.mock_utils import (
    INVALID_INT_TYPE,
    INVALID_STRING_TYPE,
    MOCK_ADDRESS,
    MOCK_PROTOCOL_PARAMETERS,
    generate_mock_popen_function,
    mock_raise_internal_error,
)


class TestProcess(TestCase):
    def test_missing_output_utxo_details(self):
        try:
            result = adjust_utxos(
                input_utxo_list=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=0,
                        amount=1000000,
                    ),
                ],
                prep_tx_file="test_prep_file.draft",
                source_address=MOCK_ADDRESS,
                max_tx_size=1000,
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_missing_input_utxo_list(self):
        try:
            result = adjust_utxos(
                output_utxo_details=[
                    PaymentGroup(
                        payment_details=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                            for _ in range(100)
                        ],
                        index=1,
                    ),
                ],
                prep_tx_file="test_prep_file.draft",
                source_address=MOCK_ADDRESS,
                max_tx_size=1000,
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_missing_prep_tx_file(self):
        try:
            result = adjust_utxos(
                output_utxo_details=[
                    PaymentGroup(
                        payment_details=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                            for _ in range(100)
                        ],
                        index=1,
                    ),
                ],
                input_utxo_list=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=0,
                        amount=1000000,
                    ),
                ],
                source_address=MOCK_ADDRESS,
                max_tx_size=1000,
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_missing_source_address(self):
        try:
            result = adjust_utxos(
                output_utxo_details=[
                    PaymentGroup(
                        payment_details=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                            for _ in range(100)
                        ],
                        index=1,
                    ),
                ],
                input_utxo_list=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=0,
                        amount=1000000,
                    ),
                ],
                prep_tx_file="test_prep_file.draft",
                max_tx_size=1000,
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_missing_max_tx_size(self):
        try:
            result = adjust_utxos(
                output_utxo_details=[
                    PaymentGroup(
                        payment_details=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                            for _ in range(100)
                        ],
                        index=1,
                    ),
                ],
                input_utxo_list=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=0,
                        amount=1000000,
                    ),
                ],
                prep_tx_file="test_prep_file.draft",
                source_address=MOCK_ADDRESS,
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_invalid_output_utxo_details(self):
        try:
            result = adjust_utxos(
                output_utxo_details="invalid",
                input_utxo_list=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=0,
                        amount=1000000,
                    ),
                ],
                prep_tx_file="test_prep_file.draft",
                source_address=MOCK_ADDRESS,
                max_tx_size=1000,
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Output UTxO Details List Type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_input_utxo_list(self):
        try:
            result = adjust_utxos(
                output_utxo_details=[
                    PaymentGroup(
                        payment_details=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                            for _ in range(100)
                        ],
                        index=1,
                    ),
                ],
                input_utxo_list="invalid",
                prep_tx_file="test_prep_file.draft",
                source_address=MOCK_ADDRESS,
                max_tx_size=1000,
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Input UTxO Details List Type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_prep_tx_file(self):
        try:
            result = adjust_utxos(
                output_utxo_details=[
                    PaymentGroup(
                        payment_details=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                            for _ in range(100)
                        ],
                        index=1,
                    ),
                ],
                input_utxo_list=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=0,
                        amount=1000000,
                    ),
                ],
                prep_tx_file=-1,
                source_address=MOCK_ADDRESS,
                max_tx_size=1000,
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidFileError)

    def test_invalid_source_address(self):
        try:
            result = adjust_utxos(
                output_utxo_details=[
                    PaymentGroup(
                        payment_details=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                            for _ in range(100)
                        ],
                        index=1,
                    ),
                ],
                input_utxo_list=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=0,
                        amount=1000000,
                    ),
                ],
                prep_tx_file="test_prep_file.draft",
                source_address=-1,
                max_tx_size=1000,
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Source Address Type."
        assert result.additional_context["type"] == INVALID_INT_TYPE

    def test_invalid_max_tx_size(self):
        try:
            result = adjust_utxos(
                output_utxo_details=[
                    PaymentGroup(
                        payment_details=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                            for _ in range(100)
                        ],
                        index=1,
                    ),
                ],
                input_utxo_list=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=0,
                        amount=1000000,
                    ),
                ],
                prep_tx_file="test_prep_file.draft",
                source_address=MOCK_ADDRESS,
                max_tx_size="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Max Transaction Size Type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_allow_ttl_slots(self):
        try:
            result = adjust_utxos(
                output_utxo_details=[
                    PaymentGroup(
                        payment_details=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                            for _ in range(100)
                        ],
                        index=1,
                    ),
                ],
                input_utxo_list=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=0,
                        amount=1000000,
                    ),
                ],
                prep_tx_file="test_prep_file.draft",
                source_address=MOCK_ADDRESS,
                max_tx_size=1000,
                allow_ttl_slots="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Allow TTL Slots Type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_reward_details(self):
        try:
            result = adjust_utxos(
                output_utxo_details=[
                    PaymentGroup(
                        payment_details=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                            for _ in range(100)
                        ],
                        index=1,
                    ),
                ],
                input_utxo_list=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=0,
                        amount=1000000,
                    ),
                ],
                prep_tx_file="test_prep_file.draft",
                source_address=MOCK_ADDRESS,
                max_tx_size=1000,
                reward_details="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Reward Details Type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_network(self):
        try:
            result = adjust_utxos(
                output_utxo_details=[
                    PaymentGroup(
                        payment_details=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                            for _ in range(100)
                        ],
                        index=1,
                    ),
                ],
                input_utxo_list=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=0,
                        amount=1000000,
                    ),
                ],
                prep_tx_file="test_prep_file.draft",
                source_address=MOCK_ADDRESS,
                max_tx_size=1000,
                network="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidNetwork)
        assert result.additional_context["network"] == "invalid"

    def test_invalid_method(self):
        try:
            result = adjust_utxos(
                output_utxo_details=[
                    PaymentGroup(
                        payment_details=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                            for _ in range(100)
                        ],
                        index=1,
                    ),
                ],
                input_utxo_list=[
                    InputUTXO(
                        address=MOCK_ADDRESS,
                        tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                        tx_index=0,
                        amount=1000000,
                    ),
                ],
                prep_tx_file="test_prep_file.draft",
                source_address=MOCK_ADDRESS,
                max_tx_size=1000,
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
                result = adjust_utxos(
                    output_utxo_details=[
                        PaymentGroup(
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                            index=1,
                        ),
                    ],
                    input_utxo_list=[
                        InputUTXO(
                            address=MOCK_ADDRESS,
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=0,
                            amount=1000000,
                        ),
                    ],
                    prep_tx_file="test_prep_file.draft",
                    source_address=MOCK_ADDRESS,
                    max_tx_size=1000,
                )
            except Exception as e:
                result = e

        assert isinstance(result, Exception)

    def test_insufficient_balance(self):
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
        ):
            try:
                result = adjust_utxos(
                    output_utxo_details=[
                        PaymentGroup(
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                            index=1,
                        ),
                    ],
                    input_utxo_list=[
                        InputUTXO(
                            address=MOCK_ADDRESS,
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=0,
                            amount=1000,
                        ),
                    ],
                    prep_tx_file="test_prep_file.draft",
                    source_address=MOCK_ADDRESS,
                    max_tx_size=1000,
                )
            except Exception as e:
                result = e

        assert isinstance(result, InsufficientBalance)

    def test_error_during_get_latest_slot_number(self):
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
            "cardano_mass_payments.utils.cli_utils.get_latest_slot_number",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = adjust_utxos(
                    output_utxo_details=[
                        PaymentGroup(
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                            index=1,
                        ),
                    ],
                    input_utxo_list=[
                        InputUTXO(
                            address=MOCK_ADDRESS,
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=0,
                            amount=1000000,
                        ),
                    ],
                    prep_tx_file="test_prep_file.draft",
                    source_address=MOCK_ADDRESS,
                    max_tx_size=1000,
                )
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)
        assert result.message == "Unexpected Error Getting Latest Slot Number."

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
            side_effect=Exception("Internal Error."),
        ):
            try:
                result = adjust_utxos(
                    output_utxo_details=[
                        PaymentGroup(
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                            index=1,
                        ),
                    ],
                    input_utxo_list=[
                        InputUTXO(
                            address=MOCK_ADDRESS,
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=0,
                            amount=1000000,
                        ),
                    ],
                    prep_tx_file="test_prep_file.draft",
                    source_address=MOCK_ADDRESS,
                    max_tx_size=1000,
                )
            except Exception as e:
                result = e

        assert isinstance(result, Exception)

    def test_error_during_get_total_amount_plus_fee(self):
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
            "cardano_mass_payments.utils.script_utils.get_total_amount_plus_fee",
            side_effect=Exception("Internal Error."),
        ):
            try:
                result = adjust_utxos(
                    output_utxo_details=[
                        PaymentGroup(
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                            index=1,
                        ),
                    ],
                    input_utxo_list=[
                        InputUTXO(
                            address=MOCK_ADDRESS,
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=0,
                            amount=1000000,
                        ),
                    ],
                    prep_tx_file="test_prep_file.draft",
                    source_address=MOCK_ADDRESS,
                    max_tx_size=1000,
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
                result = adjust_utxos(
                    output_utxo_details=[
                        PaymentGroup(
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                            index=1,
                        ),
                    ],
                    input_utxo_list=[
                        InputUTXO(
                            address=MOCK_ADDRESS,
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=0,
                            amount=1000000,
                        ),
                    ],
                    prep_tx_file="test_prep_file.draft",
                    source_address=MOCK_ADDRESS,
                    max_tx_size=1000,
                )
            except Exception as e:
                result = e

        assert isinstance(result, TransactionPlan)

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
                result = adjust_utxos(
                    output_utxo_details=[
                        PaymentGroup(
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(10)
                            ],
                            index=1,
                        ),
                    ],
                    input_utxo_list=[
                        InputUTXO(
                            address=MOCK_ADDRESS,
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=0,
                            amount=1000000,
                        ),
                    ],
                    prep_tx_file="test_prep_file.draft",
                    source_address=MOCK_ADDRESS,
                    max_tx_size=1000,
                    method=ScriptMethod.METHOD_PYCARDANO,
                )
            except Exception as e:
                result = e

        assert isinstance(result, TransactionPlan)

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
                result = adjust_utxos(
                    output_utxo_details=[
                        PaymentGroup(
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                            index=1,
                        ),
                    ],
                    input_utxo_list=[
                        InputUTXO(
                            address=MOCK_ADDRESS,
                            tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                            tx_index=0,
                            amount=1000000,
                        ),
                    ],
                    prep_tx_file="test_prep_file.draft",
                    source_address=MOCK_ADDRESS,
                    max_tx_size=1000,
                    reward_details={
                        "stake_address": "test_stake_address",
                        "stake_amount": 1000,
                    },
                )
            except Exception as e:
                result = e

        assert isinstance(result, TransactionPlan)
        assert result.prep_detail.reward_details == {
            "stake_address": "test_stake_address",
            "stake_amount": 1000,
        }
