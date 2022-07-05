import json
import subprocess
import tempfile

from cardano_mass_payments.constants.common import CardanoNetwork, ScriptMethod
from cardano_mass_payments.utils.common import get_script_settings

MOCK_SKEY_CONTENT = {
    "type": "PaymentSigningKeyShelley_ed25519",
    "description": "Payment Signing Key",
    "cborHex": "5820b4ea04caeb58e1dbcb734dcf3522b634ac12bb09960dcebd9e79b32735679948",
}
MOCK_METADATA_CONTENT = {"1337": {"name": "hello world", "completed": 0}}
MOCK_ADDRESS = "addr_test1vpv2u2aqrvp4qnsw93qck3xagvwlleqs29erxtz3322t8ls46s7ew"
MOCK_ADDRESS2 = "addr_test1vqfvx50fxl8h57jyjsczhvw3u4j6lyecfexs40tkwz7kdcg6d6t3t"
MOCK_STAKE_ADDRESS = "stake_test1upwy8nx7zj0p3n3tzdrwd4f5f4d4rmwrzf9yq438e64vgdc5pkphd"
MOCK_FULL_ADDRESS = (
    "addr_test1qra9ls6le545hx58t4lj23la3zaufneynfm0rwtg384msz2ug0xdu9y7rr8zky6xum2ngn2m28"
    "kuxyj2gptz0n42csmstuujtp"
)
MOCK_PROTOCOL_PARAMETERS = {
    "maxTxSize": 1000,
    "txFeeFixed": 100,
    "txFeePerByte": 100,
    "protocolVersion": {"minor": 0, "major": 0},
    "maxTxExecutionUnits": {"memory": 100, "steps": 100},
    "executionUnitPrices": {"priceSteps": 100, "priceMemory": 100},
    "maxBlockExecutionUnits": {"memory": 100, "steps": 100},
}
INVALID_STRING_TYPE = type("invalid")
INVALID_INT_TYPE = type(-1)


def mock_sign_tx_file_cli(
    tx_file,
    signing_key_files,
    method=ScriptMethod.METHOD_DOCKER_CLI,
    network=CardanoNetwork.TESTNET,
):
    signed_filename = f"{tx_file}.signed"

    # Create a copy of raw file, but include the signed suffix
    masspayments_settings = get_script_settings()
    prefix = masspayments_settings.command_prefix(method)
    copy_command = f"{prefix} cp {tx_file} {signed_filename}"
    subprocess.Popen(
        copy_command.split(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).communicate()

    return signed_filename


def generate_mock_popen_function(mock_responses):
    def mock_popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        print_output=False,
    ):
        for key in mock_responses:
            command_part = key
            # Keys will only be either tuples or strings
            if isinstance(command_part, tuple):
                command_part = list(command_part)
            else:
                command_part = [key]

            command_list = command
            if isinstance(command, str):
                command_list = command.split()

            check_result = all(c in command_list for c in command_part)

            if check_result:
                response = mock_responses[key]
                if isinstance(response, dict) or isinstance(response, list):
                    response_str = json.dumps(response).strip()
                elif response:
                    response_str = response
                else:
                    return subprocess.Popen(
                        command,
                        stdout=stdout,
                        stderr=stderr,
                        shell=shell,
                    )
                return subprocess.Popen(
                    ["echo", response_str],
                    stdout=stdout,
                    stderr=stderr,
                    shell=False,
                )
        return subprocess.Popen(
            ["date", "-1"],
            stdout=stdout,
            stderr=stderr,
            shell=shell,
        )  # Should return an error

    return mock_popen


def mock_raise_internal_error(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    shell=False,
):
    raise Exception("Internal Error")


def create_test_payment_csv(num_output):
    f = tempfile.NamedTemporaryFile(mode="w+", suffix=".csv")
    line = f"{MOCK_ADDRESS},1000\n" * num_output
    f.write(line.strip())
    f.seek(0)
    return f


def assert_not_called_with(mock_function, *args, **kwargs):
    try:
        mock_function.assert_called_with(*args, **kwargs)
    except AssertionError:
        # No call with specific parameters (Success)
        return
    raise AssertionError(
        f"Expected {mock_function._format_mock_call_signature(args, kwargs)} to not have been called",
    )
