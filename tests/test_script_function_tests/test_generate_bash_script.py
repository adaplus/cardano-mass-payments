from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.classes import (
    InputUTXO,
    PaymentDetail,
    PaymentGroup,
    PreparationDetail,
    TransactionPlan,
    TransactionStatus,
)
from cardano_mass_payments.constants.common import CardanoNetwork, ScriptMethod
from cardano_mass_payments.constants.exceptions import (
    InvalidMethod,
    InvalidNetwork,
    InvalidType,
)
from cardano_mass_payments.utils.pycardano_utils import CardanoCLIChainContext
from cardano_mass_payments.utils.script_utils import generate_bash_script
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
    def test_missing_transaction_plan(self):
        try:
            result = generate_bash_script(
                signing_key_file_details={MOCK_ADDRESS: "test.skey"},
                source_address=MOCK_ADDRESS,
                store_in_file=False,
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_missing_signing_key_file_details(self):
        try:
            result = generate_bash_script(
                transaction_plan=TransactionPlan(
                    prep_detail=PreparationDetail(
                        prep_input=[
                            InputUTXO(
                                address=MOCK_ADDRESS,
                                tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                                tx_index=0,
                                amount=100000000,
                            ),
                        ],
                        prep_output=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000 * 100),
                        ],
                    ),
                    group_details=[
                        PaymentGroup(
                            index=0,
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                        ),
                    ],
                    network=CardanoNetwork.TESTNET,
                    script_method=ScriptMethod.METHOD_DOCKER_CLI,
                    allowed_ttl_slots=1000,
                    add_change_to_fee=False,
                ),
                source_address=MOCK_ADDRESS,
                store_in_file=False,
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_missing_source_address(self):
        try:
            result = generate_bash_script(
                transaction_plan=TransactionPlan(
                    prep_detail=PreparationDetail(
                        prep_input=[
                            InputUTXO(
                                address=MOCK_ADDRESS,
                                tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                                tx_index=0,
                                amount=100000000,
                            ),
                        ],
                        prep_output=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000 * 100),
                        ],
                    ),
                    group_details=[
                        PaymentGroup(
                            index=0,
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                        ),
                    ],
                    network=CardanoNetwork.TESTNET,
                    script_method=ScriptMethod.METHOD_DOCKER_CLI,
                    allowed_ttl_slots=1000,
                    add_change_to_fee=False,
                ),
                signing_key_file_details={MOCK_ADDRESS: "test.skey"},
                store_in_file=False,
            )
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_invalid_transaction_plan(self):
        try:
            result = generate_bash_script(
                transaction_plan="invalid",
                signing_key_file_details={MOCK_ADDRESS: "test.skey"},
                source_address=MOCK_ADDRESS,
                store_in_file=False,
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Transaction Plan Type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_signing_key_file_details(self):
        try:
            result = generate_bash_script(
                transaction_plan=TransactionPlan(
                    prep_detail=PreparationDetail(
                        prep_input=[
                            InputUTXO(
                                address=MOCK_ADDRESS,
                                tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                                tx_index=0,
                                amount=100000000,
                            ),
                        ],
                        prep_output=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000 * 100),
                        ],
                    ),
                    group_details=[
                        PaymentGroup(
                            index=0,
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                        ),
                    ],
                    network=CardanoNetwork.TESTNET,
                    script_method=ScriptMethod.METHOD_DOCKER_CLI,
                    allowed_ttl_slots=1000,
                    add_change_to_fee=False,
                ),
                signing_key_file_details="invalid",
                source_address=MOCK_ADDRESS,
                store_in_file=False,
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Signing Key File Details Type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_source_address(self):
        try:
            result = generate_bash_script(
                transaction_plan=TransactionPlan(
                    prep_detail=PreparationDetail(
                        prep_input=[
                            InputUTXO(
                                address=MOCK_ADDRESS,
                                tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                                tx_index=0,
                                amount=100000000,
                            ),
                        ],
                        prep_output=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000 * 100),
                        ],
                    ),
                    group_details=[
                        PaymentGroup(
                            index=0,
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                        ),
                    ],
                    network=CardanoNetwork.TESTNET,
                    script_method=ScriptMethod.METHOD_DOCKER_CLI,
                    allowed_ttl_slots=1000,
                    add_change_to_fee=False,
                ),
                signing_key_file_details={MOCK_ADDRESS: "test.skey"},
                source_address=-1,
                store_in_file=False,
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Source Address Type."
        assert result.additional_context["type"] == INVALID_INT_TYPE

    def test_invalid_allow_ttl_slots(self):
        try:
            result = generate_bash_script(
                transaction_plan=TransactionPlan(
                    prep_detail=PreparationDetail(
                        prep_input=[
                            InputUTXO(
                                address=MOCK_ADDRESS,
                                tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                                tx_index=0,
                                amount=100000000,
                            ),
                        ],
                        prep_output=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000 * 100),
                        ],
                    ),
                    group_details=[
                        PaymentGroup(
                            index=0,
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                        ),
                    ],
                    network=CardanoNetwork.TESTNET,
                    script_method=ScriptMethod.METHOD_DOCKER_CLI,
                    allowed_ttl_slots=1000,
                    add_change_to_fee=False,
                ),
                signing_key_file_details={MOCK_ADDRESS: "test.skey"},
                source_address=MOCK_ADDRESS,
                allow_ttl_slots="invalid",
                store_in_file=False,
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Allowable TTL Slots Type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_network(self):
        try:
            result = generate_bash_script(
                transaction_plan=TransactionPlan(
                    prep_detail=PreparationDetail(
                        prep_input=[
                            InputUTXO(
                                address=MOCK_ADDRESS,
                                tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                                tx_index=0,
                                amount=100000000,
                            ),
                        ],
                        prep_output=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000 * 100),
                        ],
                    ),
                    group_details=[
                        PaymentGroup(
                            index=0,
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                        ),
                    ],
                    network=CardanoNetwork.TESTNET,
                    script_method=ScriptMethod.METHOD_DOCKER_CLI,
                    allowed_ttl_slots=1000,
                    add_change_to_fee=False,
                ),
                signing_key_file_details={MOCK_ADDRESS: "test.skey"},
                source_address=MOCK_ADDRESS,
                network="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidNetwork)
        assert result.additional_context["network"] == "invalid"

    def test_invalid_method(self):
        try:
            result = generate_bash_script(
                transaction_plan=TransactionPlan(
                    prep_detail=PreparationDetail(
                        prep_input=[
                            InputUTXO(
                                address=MOCK_ADDRESS,
                                tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                                tx_index=0,
                                amount=100000000,
                            ),
                        ],
                        prep_output=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000 * 100),
                        ],
                    ),
                    group_details=[
                        PaymentGroup(
                            index=0,
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                        ),
                    ],
                    network=CardanoNetwork.TESTNET,
                    script_method=ScriptMethod.METHOD_DOCKER_CLI,
                    allowed_ttl_slots=1000,
                    add_change_to_fee=False,
                ),
                signing_key_file_details={MOCK_ADDRESS: "test.skey"},
                source_address=MOCK_ADDRESS,
                method="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidMethod)
        assert result.additional_context["method"] == "invalid"

    def test_invalid_store_in_file(self):
        try:
            result = generate_bash_script(
                transaction_plan=TransactionPlan(
                    prep_detail=PreparationDetail(
                        prep_input=[
                            InputUTXO(
                                address=MOCK_ADDRESS,
                                tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                                tx_index=0,
                                amount=100000000,
                            ),
                        ],
                        prep_output=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000 * 100),
                        ],
                    ),
                    group_details=[
                        PaymentGroup(
                            index=0,
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                        ),
                    ],
                    network=CardanoNetwork.TESTNET,
                    script_method=ScriptMethod.METHOD_DOCKER_CLI,
                    allowed_ttl_slots=1000,
                    add_change_to_fee=False,
                ),
                signing_key_file_details={MOCK_ADDRESS: "test.skey"},
                source_address=MOCK_ADDRESS,
                store_in_file="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Store in File Type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_invalid_add_comments(self):
        try:
            result = generate_bash_script(
                transaction_plan=TransactionPlan(
                    prep_detail=PreparationDetail(
                        prep_input=[
                            InputUTXO(
                                address=MOCK_ADDRESS,
                                tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                                tx_index=0,
                                amount=100000000,
                            ),
                        ],
                        prep_output=[
                            PaymentDetail(address=MOCK_ADDRESS, amount=1000 * 100),
                        ],
                    ),
                    group_details=[
                        PaymentGroup(
                            index=0,
                            payment_details=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                for _ in range(100)
                            ],
                        ),
                    ],
                    network=CardanoNetwork.TESTNET,
                    script_method=ScriptMethod.METHOD_DOCKER_CLI,
                    allowed_ttl_slots=1000,
                    add_change_to_fee=False,
                ),
                signing_key_file_details={MOCK_ADDRESS: "test.skey"},
                source_address=MOCK_ADDRESS,
                add_comments="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Add Comments Type."
        assert result.additional_context["type"] == INVALID_STRING_TYPE

    def test_unexpected_error_during_command_execution(self):
        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=mock_raise_internal_error,
        ):
            try:
                result = generate_bash_script(
                    transaction_plan=TransactionPlan(
                        prep_detail=PreparationDetail(
                            prep_input=[
                                InputUTXO(
                                    address=MOCK_ADDRESS,
                                    tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                                    tx_index=0,
                                    amount=100000000,
                                ),
                            ],
                            prep_output=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000 * 100),
                            ],
                        ),
                        group_details=[
                            PaymentGroup(
                                index=0,
                                payment_details=[
                                    PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                    for _ in range(100)
                                ],
                            ),
                        ],
                        network=CardanoNetwork.TESTNET,
                        script_method=ScriptMethod.METHOD_DOCKER_CLI,
                        allowed_ttl_slots=1000,
                        add_change_to_fee=False,
                    ),
                    signing_key_file_details={MOCK_ADDRESS: "test.skey"},
                    source_address=MOCK_ADDRESS,
                    store_in_file=False,
                )
            except Exception as e:
                result = e

        assert isinstance(result, Exception)

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
            "cardano_mass_payments.utils.script_utils.get_latest_slot_number",
            side_effect=Exception("Internal Error"),
        ):
            try:
                result = generate_bash_script(
                    transaction_plan=TransactionPlan(
                        prep_detail=PreparationDetail(
                            prep_input=[
                                InputUTXO(
                                    address=MOCK_ADDRESS,
                                    tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                                    tx_index=0,
                                    amount=100000000,
                                ),
                            ],
                            prep_output=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000 * 100),
                            ],
                        ),
                        group_details=[
                            PaymentGroup(
                                index=0,
                                payment_details=[
                                    PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                    for _ in range(100)
                                ],
                            ),
                        ],
                        network=CardanoNetwork.TESTNET,
                        script_method=ScriptMethod.METHOD_DOCKER_CLI,
                        allowed_ttl_slots=1000,
                        add_change_to_fee=False,
                    ),
                    signing_key_file_details={MOCK_ADDRESS: "test.skey"},
                    source_address=MOCK_ADDRESS,
                    store_in_file=False,
                )
            except Exception as e:
                result = e

        assert isinstance(result, Exception)

    def test_error_during_create_transaction_command(self):
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
            "cardano_mass_payments.utils.script_utils.create_transaction_command",
            side_effect=Exception("Internal Error"),
        ):
            try:
                result = generate_bash_script(
                    transaction_plan=TransactionPlan(
                        prep_detail=PreparationDetail(
                            prep_input=[
                                InputUTXO(
                                    address=MOCK_ADDRESS,
                                    tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                                    tx_index=0,
                                    amount=100000000,
                                ),
                            ],
                            prep_output=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000 * 100),
                            ],
                        ),
                        group_details=[
                            PaymentGroup(
                                index=0,
                                payment_details=[
                                    PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                    for _ in range(100)
                                ],
                            ),
                        ],
                        network=CardanoNetwork.TESTNET,
                        script_method=ScriptMethod.METHOD_DOCKER_CLI,
                        allowed_ttl_slots=1000,
                        add_change_to_fee=False,
                    ),
                    signing_key_file_details={MOCK_ADDRESS: "test.skey"},
                    source_address=MOCK_ADDRESS,
                    store_in_file=False,
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
                result = generate_bash_script(
                    transaction_plan=TransactionPlan(
                        prep_detail=PreparationDetail(
                            prep_input=[
                                InputUTXO(
                                    address=MOCK_ADDRESS,
                                    tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                                    tx_index=0,
                                    amount=100000000,
                                ),
                            ],
                            prep_output=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000 * 100),
                            ],
                        ),
                        group_details=[
                            PaymentGroup(
                                index=0,
                                payment_details=[
                                    PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                    for _ in range(100)
                                ],
                            ),
                        ],
                        network=CardanoNetwork.TESTNET,
                        script_method=ScriptMethod.METHOD_DOCKER_CLI,
                        allowed_ttl_slots=1000,
                        add_change_to_fee=False,
                    ),
                    signing_key_file_details={MOCK_ADDRESS: "test.skey"},
                    source_address=MOCK_ADDRESS,
                    store_in_file=False,
                )
            except Exception as e:
                result = e

        assert isinstance(result, str)
        assert "#!/bin/bash" in result

    def test_success_with_done_utxos(self):
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
                result = generate_bash_script(
                    transaction_plan=TransactionPlan(
                        prep_detail=PreparationDetail(
                            prep_input=[
                                InputUTXO(
                                    address=MOCK_ADDRESS,
                                    tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                                    tx_index=0,
                                    amount=100000000,
                                ),
                            ],
                            prep_output=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000 * 100),
                            ],
                            submission_status=TransactionStatus.SUBMISSION_DONE,
                            tx_hash_id="mock_prep_tx_id",
                        ),
                        group_details=[
                            PaymentGroup(
                                index=0,
                                payment_details=[
                                    PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                    for _ in range(100)
                                ],
                            ),
                        ],
                        network=CardanoNetwork.TESTNET,
                        script_method=ScriptMethod.METHOD_DOCKER_CLI,
                        allowed_ttl_slots=1000,
                        add_change_to_fee=False,
                    ),
                    signing_key_file_details={MOCK_ADDRESS: "test.skey"},
                    source_address=MOCK_ADDRESS,
                    store_in_file=False,
                )
            except Exception as e:
                result = e

        assert isinstance(result, str)
        assert "#!/bin/bash" in result
        assert "mock_prep_tx_id" in result

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
            },
        ):
            try:
                result = generate_bash_script(
                    transaction_plan=TransactionPlan(
                        prep_detail=PreparationDetail(
                            prep_input=[
                                InputUTXO(
                                    address=MOCK_ADDRESS,
                                    tx_hash="0000000000000000000000000000000000000000000000000000000000000000",
                                    tx_index=0,
                                    amount=100000000,
                                ),
                            ],
                            prep_output=[
                                PaymentDetail(address=MOCK_ADDRESS, amount=1000 * 100),
                            ],
                        ),
                        group_details=[
                            PaymentGroup(
                                index=0,
                                payment_details=[
                                    PaymentDetail(address=MOCK_ADDRESS, amount=1000)
                                    for _ in range(100)
                                ],
                            ),
                        ],
                        network=CardanoNetwork.TESTNET,
                        script_method=ScriptMethod.METHOD_DOCKER_CLI,
                        allowed_ttl_slots=1000,
                        add_change_to_fee=False,
                    ),
                    signing_key_file_details={MOCK_ADDRESS: "test.skey"},
                    source_address=MOCK_ADDRESS,
                    store_in_file=False,
                )
            except Exception as e:
                result = e

        assert isinstance(result, str)
        assert "#!/bin/bash" in result
