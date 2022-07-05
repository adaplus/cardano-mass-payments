import argparse
import json
import os
import stat
import tempfile
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.classes import TransactionPlan
from cardano_mass_payments.commands.mass_payments import (
    adjust_metadata_message,
    dust_collect,
    generate_script_process,
)
from cardano_mass_payments.constants.common import (
    CardanoNetwork,
    DustCollectionMethod,
    ScriptMethod,
    ScriptOutputFormats,
)
from cardano_mass_payments.constants.exceptions import (
    InsufficientBalance,
    InvalidFileError,
    ScriptError,
)
from tests.mock_responses import MOCK_TEST_RESPONSES, USE_SUBPROCESS_FUNCTION_FLAG
from tests.mock_utils import (
    MOCK_ADDRESS,
    MOCK_METADATA_CONTENT,
    MOCK_PROTOCOL_PARAMETERS,
    MOCK_STAKE_ADDRESS,
    assert_not_called_with,
    create_test_payment_csv,
    generate_mock_popen_function,
    mock_sign_tx_file_cli,
)


class TestProcess(TestCase):
    def create_test_source_csv(self):
        f = tempfile.NamedTemporaryFile(mode="w+", suffix=".csv")
        line = f"{MOCK_ADDRESS},test.skey"
        f.write(line.strip())
        f.seek(0)
        return f

    def generate_command_arguments(
        self,
        sources_csv,
        payments_csv,
        cardano_network=CardanoNetwork.TESTNET.value,
        script_method=ScriptMethod.METHOD_DOCKER_CLI.value,
        output_type=ScriptOutputFormats.JSON.value,
        add_comments=False,
        enable_dust_collection=False,
        execute_script_now=False,
        allowed_ttl_slots=1000,
        dust_collection_method=DustCollectionMethod.COLLECT_TO_SOURCE.value,
        dust_collection_threshold=10000000,
        source_address=None,
        source_signing_key_file=None,
        metadata_json_file=None,
        metadata_message_file=None,
        transaction_plan_file=None,
        magic_number=1,
        include_rewards=False,
    ):
        command_arguments = argparse.Namespace()

        command_arguments.cardano_network = cardano_network
        command_arguments.script_method = script_method
        command_arguments.output_type = output_type
        command_arguments.sources_csv = sources_csv
        command_arguments.payments_csv = payments_csv
        command_arguments.add_comments = add_comments
        command_arguments.enable_dust_collection = enable_dust_collection
        command_arguments.execute_script_now = execute_script_now
        command_arguments.allowed_ttl_slots = allowed_ttl_slots
        command_arguments.dust_collection_method = dust_collection_method
        command_arguments.dust_collection_threshold = dust_collection_threshold
        command_arguments.source_address = source_address
        command_arguments.source_signing_key_file = source_signing_key_file
        command_arguments.metadata_json_file = metadata_json_file
        command_arguments.metadata_message_file = metadata_message_file
        command_arguments.transaction_plan_file = transaction_plan_file
        command_arguments.magic_number = magic_number
        command_arguments.include_rewards = include_rewards

        return command_arguments

    def test_1_input_30_payments_success(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            transaction_plan = generate_script_process(command_arguments)

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()

    def test_1_input_2000_payments_success(self):
        payment_file = create_test_payment_csv(2000)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            transaction_plan = generate_script_process(command_arguments)

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()

    def test_1_input_5000_payments_success(self):
        payment_file = create_test_payment_csv(5000)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            transaction_plan = generate_script_process(command_arguments)

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()

    def test_50_input_30_payments_success(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_wallet_utxo = {}
        for i in range(50):
            mock_wallet_utxo[
                f"85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#{i}"
            ] = {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 9806},
            }

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[
            (
                "cat",
                f"/tmp/utxo-{MOCK_ADDRESS}.json",
            )
        ] = mock_wallet_utxo
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            transaction_plan = generate_script_process(command_arguments)

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()

    def test_50_input_2000_payments_success(self):
        payment_file = create_test_payment_csv(2000)
        source_file = self.create_test_source_csv()

        mock_wallet_utxo = {}
        for i in range(50):
            mock_wallet_utxo[
                f"85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#{i}"
            ] = {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 236114},
            }

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[
            (
                "cat",
                f"/tmp/utxo-{MOCK_ADDRESS}.json",
            )
        ] = mock_wallet_utxo
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            transaction_plan = generate_script_process(command_arguments)

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()

    def test_50_input_5000_payments_success(self):
        payment_file = create_test_payment_csv(5000)
        source_file = self.create_test_source_csv()

        mock_wallet_utxo = {}
        for i in range(50):
            mock_wallet_utxo[
                f"85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#{i}"
            ] = {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 575254},
            }

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[
            (
                "cat",
                f"/tmp/utxo-{MOCK_ADDRESS}.json",
            )
        ] = mock_wallet_utxo
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            transaction_plan = generate_script_process(command_arguments)

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()

    def test_20_input_500_payments_fail(self):
        payment_file = create_test_payment_csv(500)
        source_file = self.create_test_source_csv()

        mock_wallet_utxo = {}
        for i in range(20):
            mock_wallet_utxo[
                f"85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#{i}"
            ] = {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 100},
            }

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[
            (
                "cat",
                f"/tmp/utxo-{MOCK_ADDRESS}.json",
            )
        ] = mock_wallet_utxo
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            try:
                transaction_plan = generate_script_process(command_arguments)
            except Exception as e:
                transaction_plan = e

        assert isinstance(transaction_plan, InsufficientBalance)
        assert (
            transaction_plan.additional_context.get("current_amount") == 2000
        )  # 100 * 20

    def test_nonexistent_transaction_plan(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            transaction_plan_file="nonexistent.json",
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            try:
                transaction_plan = generate_script_process(command_arguments)
            except Exception as e:
                transaction_plan = e

        assert isinstance(transaction_plan, InvalidFileError)
        assert transaction_plan.additional_context["file"] == "nonexistent.json"
        source_file.close()
        payment_file.close()

    def test_unaccessible_file(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }

        unaccessible_tx_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
        # Remove read permission
        os.chmod(unaccessible_tx_file.name, ~stat.S_IRUSR)

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            transaction_plan_file=unaccessible_tx_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            try:
                transaction_plan = generate_script_process(command_arguments)
            except Exception as e:
                transaction_plan = e

        assert isinstance(transaction_plan, InvalidFileError)
        assert transaction_plan.additional_context["file"] == unaccessible_tx_file.name
        unaccessible_tx_file.close()
        source_file.close()
        payment_file.close()

    def test_invalid_transaction_plan(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }

        invalid_tx_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
        line = "invalid json details"
        invalid_tx_file.write(line.strip())
        invalid_tx_file.seek(0)

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            transaction_plan_file=invalid_tx_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            try:
                transaction_plan = generate_script_process(command_arguments)
            except Exception as e:
                transaction_plan = e

        assert isinstance(transaction_plan, InvalidFileError)
        assert transaction_plan.additional_context["file"] == invalid_tx_file.name
        invalid_tx_file.close()
        source_file.close()
        payment_file.close()

    def test_valid_transaction_plan_success(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
        )

        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {"metadata_file": None},
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            try:
                init_transaction_plan = generate_script_process(command_arguments)
            except Exception as e:
                init_transaction_plan = e

            assert isinstance(init_transaction_plan, TransactionPlan)
            assert os.path.exists(init_transaction_plan.filename)
            # Change (generated after the bash script generation) is not included in the transaction plan file
            del init_transaction_plan.prep_detail.prep_output[-1]

            valid_tx_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
            valid_tx_file.write(init_transaction_plan.json())
            valid_tx_file.seek(0)
            command_arguments.transaction_plan_file = valid_tx_file.name

            try:
                transaction_plan = generate_script_process(command_arguments)
            except Exception as e:
                transaction_plan = e

            assert isinstance(transaction_plan, TransactionPlan)
            assert os.path.exists(transaction_plan.filename)

            os.remove(init_transaction_plan.filename)
            os.remove(transaction_plan.filename)
            os.remove(f"{transaction_plan.uuid}.sh")

        source_file.close()
        payment_file.close()

    def test_error_during_prep_step(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ), patch(
            "cardano_mass_payments.commands.mass_payments.preparation_step",
            side_effect=Exception("Internal error."),
        ):
            try:
                transaction_plan = generate_script_process(command_arguments)
            except Exception as e:
                transaction_plan = e

        source_file.close()
        payment_file.close()

        assert isinstance(transaction_plan, Exception)

    def test_error_during_group_utxo_step(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ), patch(
            "cardano_mass_payments.utils.script_utils.group_output_utxo",
            side_effect=Exception("Internal error."),
        ):
            try:
                transaction_plan = generate_script_process(command_arguments)
            except Exception as e:
                transaction_plan = e

        source_file.close()
        payment_file.close()

        assert isinstance(transaction_plan, ScriptError)

    def test_error_during_dust_collection_step(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_wallet_utxos = {}
        for i in range(500):
            mock_wallet_utxos[
                f"85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#{i}"
            ] = {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 700},
            }
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = mock_wallet_utxos

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            enable_dust_collection=True,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ), patch(
            "cardano_mass_payments.commands.mass_payments.dust_collect",
            side_effect=Exception("Internal error."),
        ):
            try:
                transaction_plan = generate_script_process(command_arguments)
            except Exception as e:
                transaction_plan = e

        source_file.close()
        payment_file.close()

        assert isinstance(transaction_plan, Exception)

    def test_error_during_adjust_utxo_step(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ), patch(
            "cardano_mass_payments.commands.mass_payments.adjust_utxos",
            side_effect=Exception("Internal error."),
        ):
            try:
                transaction_plan = generate_script_process(command_arguments)
            except Exception as e:
                transaction_plan = e

        source_file.close()
        payment_file.close()

        assert isinstance(transaction_plan, Exception)

    def test_error_during_generate_bash_script(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ), patch(
            "cardano_mass_payments.commands.mass_payments.generate_bash_script",
            side_effect=Exception("Internal error."),
        ) as mock_generate_bash_script:
            try:
                transaction_plan = generate_script_process(command_arguments)
            except Exception as e:
                transaction_plan = e

            mock_call_args, _ = mock_generate_bash_script.call_args
            os.remove(
                mock_call_args[0].filename,
            )  # Transaction Plan is the first argument in the function

        source_file.close()
        payment_file.close()

        assert isinstance(transaction_plan, Exception)

    def test_success_with_rewards(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("query", "protocol-parameters")] = MOCK_PROTOCOL_PARAMETERS
        mock_responses[("cardano-address", "address")] = {
            "stake_key_hash": "test_stake_key_hash",
        }
        mock_responses['"bech32'] = MOCK_STAKE_ADDRESS
        mock_responses[("query", "stake-address-info")] = [
            {
                "rewardAccountBalance": 1000000,
            },
        ]

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            include_rewards=True,
        )

        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {"metadata_file": None},
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            transaction_plan = generate_script_process(command_arguments)

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()

    def test_immediate_execution_yes_response(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters
        mock_responses["bash"] = "DONE"

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            execute_script_now=True,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.commands.mass_payments.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ), patch(
            "cardano_mass_payments.commands.mass_payments.input",
            return_value="yes",
        ), patch(
            "cardano_mass_payments.commands.mass_payments.print",
        ) as print_function:
            transaction_plan = generate_script_process(command_arguments)

            assert_not_called_with(
                print_function,
                "Thank you for using the MassPayments Script",
            )

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()

    def test_immediate_execution_no_response(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters
        mock_responses["bash"] = "DONE"

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            execute_script_now=True,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.commands.mass_payments.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ), patch(
            "cardano_mass_payments.commands.mass_payments.input",
            return_value="no",
        ), patch(
            "cardano_mass_payments.commands.mass_payments.print",
        ) as print_function:
            transaction_plan = generate_script_process(command_arguments)

            print_function.assert_called_with(
                "Thank you for using the MassPayments Script",
            )

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()

    def test_immediate_execution_invalid_response(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters
        mock_responses["bash"] = "DONE"

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            execute_script_now=True,
        )

        def mock_execute_response_now_input(statement):
            if (
                "You specified immediate execution of the transaction plan."
                in statement
            ):
                return "invalid"
            return "yes"

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.commands.mass_payments.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ), patch(
            "cardano_mass_payments.commands.mass_payments.input",
            side_effect=mock_execute_response_now_input,
        ) as mock_input:
            transaction_plan = generate_script_process(command_arguments)

            mock_input.assert_called_with(
                "Please select from the following options [YES/No] : ",
            )

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()

    def test_metadata_template_inclusion(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        metadata_template_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
        metadata_template_file.write(json.dumps(MOCK_METADATA_CONTENT))
        metadata_template_file.seek(0)

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters
        mock_responses["sk"] = USE_SUBPROCESS_FUNCTION_FLAG

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            metadata_json_file=metadata_template_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            transaction_plan = generate_script_process(command_arguments)

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)
        assert transaction_plan.metadata == MOCK_METADATA_CONTENT

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()
        metadata_template_file.close()

    def test_metadata_message_inclusion(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        metadata_message_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".txt")
        metadata_message = "test_message " * 20
        metadata_message_file.write(metadata_message.strip())
        metadata_message_file.seek(0)

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses["sk"] = USE_SUBPROCESS_FUNCTION_FLAG
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            metadata_message_file=metadata_message_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            transaction_plan = generate_script_process(command_arguments)

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)
        assert transaction_plan.metadata != MOCK_METADATA_CONTENT
        assert transaction_plan.metadata == {
            "674": {
                "msg": adjust_metadata_message(metadata_message.strip().split("\n")),
            },
        }

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()
        metadata_message_file.close()

    def test_metadata_message_and_template_inclusion(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        metadata_template_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".json")
        metadata_content = deepcopy(MOCK_METADATA_CONTENT)
        metadata_template_file.write(json.dumps(metadata_content))
        metadata_template_file.seek(0)

        metadata_message_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".txt")
        metadata_message = "test_message " * 20
        metadata_message_file.write(metadata_message.strip())
        metadata_message_file.seek(0)

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters
        mock_responses["sk"] = USE_SUBPROCESS_FUNCTION_FLAG

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            metadata_json_file=metadata_template_file.name,
            metadata_message_file=metadata_message_file.name,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            transaction_plan = generate_script_process(command_arguments)

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)
        assert transaction_plan.metadata != MOCK_METADATA_CONTENT
        metadata_content.update(
            {
                "674": {
                    "msg": adjust_metadata_message(
                        metadata_message.strip().split("\n"),
                    ),
                },
            },
        )
        assert transaction_plan.metadata == metadata_content

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()
        metadata_message_file.close()
        metadata_template_file.close()

    def test_output_format_bash_script(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            output_type=ScriptOutputFormats.BASH_SCRIPT.value,
        )

        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {"metadata_file": None},
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ), patch(
            "cardano_mass_payments.commands.mass_payments.print_to_console",
        ) as print_function:
            transaction_plan = generate_script_process(command_arguments)

            print_function.assert_any_call(
                f"Script Generated, stored in {transaction_plan.uuid}.sh",
                ScriptOutputFormats.BASH_SCRIPT,
            )

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()

    def test_output_format_console(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            output_type=ScriptOutputFormats.CONSOLE.value,
        )

        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {"metadata_file": None},
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ), patch(
            "cardano_mass_payments.commands.mass_payments.print_to_console",
        ) as print_function:
            transaction_plan = generate_script_process(command_arguments)

            print_function.assert_any_call(
                "Generated Script:",
                ScriptOutputFormats.CONSOLE,
            )

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        source_file.close()
        payment_file.close()

    def test_output_format_json(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            output_type=ScriptOutputFormats.JSON.value,
        )

        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {"metadata_file": None},
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ), patch(
            "cardano_mass_payments.commands.mass_payments.print_to_console",
        ) as print_function:
            transaction_plan = generate_script_process(command_arguments)

            print_function.assert_any_call(
                json.dumps(
                    {
                        "script_file": f"{transaction_plan.uuid}.sh",
                    },
                ),
                ScriptOutputFormats.JSON,
            )

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()

    def test_output_format_transaction_plan(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            output_type=ScriptOutputFormats.TRANSACTION_PLAN.value,
        )

        with patch.dict(
            "cardano_mass_payments.cache.CACHE_VALUES",
            {"metadata_file": None},
        ), patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ), patch(
            "cardano_mass_payments.commands.mass_payments.print_to_console",
        ) as print_function:
            transaction_plan = generate_script_process(command_arguments)

            print_function.assert_any_call(
                json.dumps(
                    {
                        "transaction_plan_file": transaction_plan.filename,
                    },
                ),
                ScriptOutputFormats.TRANSACTION_PLAN,
            )

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        source_file.close()
        payment_file.close()

    def test_dust_collection_enabled_and_not_required(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            enable_dust_collection=True,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            transaction_plan = generate_script_process(command_arguments)

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()

    def test_dust_collection_enabled_and_required(self):
        payment_file = create_test_payment_csv(1000)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_input_details = {}
        for i in range(100):
            mock_input_details[
                f"85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#{i}"
            ] = {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 2000000},
            }
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = mock_input_details
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            enable_dust_collection=True,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ), patch(
            "cardano_mass_payments.commands.mass_payments.dust_collect",
            side_effect=dust_collect,
        ) as mock_dust_collect:
            transaction_plan = generate_script_process(command_arguments)
            mock_dust_collect.assert_called()

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()

    def test_dust_collection_disabled_and_required(self):
        payment_file = create_test_payment_csv(1000)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_input_details = {}
        for i in range(100):
            mock_input_details[
                f"85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#{i}"
            ] = {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 2000000},
            }
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = mock_input_details
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            enable_dust_collection=False,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ), patch(
            "cardano_mass_payments.commands.mass_payments.dust_collect",
            side_effect=dust_collect,
        ) as mock_dust_collect:
            try:
                transaction_plan = generate_script_process(command_arguments)
            except Exception as e:
                transaction_plan = e
            mock_dust_collect.assert_not_called()

        assert isinstance(transaction_plan, ScriptError)

        source_file.close()
        payment_file.close()

    def test_dust_collection_disabled_and_not_required(self):
        payment_file = create_test_payment_csv(30)
        source_file = self.create_test_source_csv()

        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses["calculate-min-fee"] = "100 Lovelace"
        mock_responses[("cat", f"/tmp/utxo-{MOCK_ADDRESS}.json")] = {
            "85d0364b65cd68e259cd93a33253e322a0d02a67338f85dc1b67b09791e35905#1": {
                "address": MOCK_ADDRESS,
                "value": {"lovelace": 1000000000},
            },
        }
        mock_responses[("query", "tip")] = {"slot": 1}
        mock_parameters = deepcopy(MOCK_PROTOCOL_PARAMETERS)
        mock_parameters["maxTxSize"] = 10000
        mock_responses[("query", "protocol-parameters")] = mock_parameters

        command_arguments = self.generate_command_arguments(
            sources_csv=source_file.name,
            payments_csv=payment_file.name,
            enable_dust_collection=False,
        )

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ), patch(
            "cardano_mass_payments.utils.cli_utils.sign_tx_file",
            side_effect=mock_sign_tx_file_cli,
        ):
            transaction_plan = generate_script_process(command_arguments)

        assert isinstance(transaction_plan, TransactionPlan)
        assert os.path.exists(transaction_plan.filename)

        os.remove(transaction_plan.filename)
        os.remove(f"{transaction_plan.uuid}.sh")
        source_file.close()
        payment_file.close()
