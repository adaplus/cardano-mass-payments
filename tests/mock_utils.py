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
    "utxoCostPerByte": 1000,
    "costModels": {
        "PlutusScriptV1": {
            "addInteger-cpu-arguments-intercept": 205665,
            "addInteger-cpu-arguments-slope": 812,
            "addInteger-memory-arguments-intercept": 1,
            "addInteger-memory-arguments-slope": 1,
            "appendByteString-cpu-arguments-intercept": 1000,
            "appendByteString-cpu-arguments-slope": 571,
            "appendByteString-memory-arguments-intercept": 0,
            "appendByteString-memory-arguments-slope": 1,
            "appendString-cpu-arguments-intercept": 1000,
            "appendString-cpu-arguments-slope": 24177,
            "appendString-memory-arguments-intercept": 4,
            "appendString-memory-arguments-slope": 1,
            "bData-cpu-arguments": 1000,
            "bData-memory-arguments": 32,
            "blake2b_256-cpu-arguments-intercept": 117366,
            "blake2b_256-cpu-arguments-slope": 10475,
            "blake2b_256-memory-arguments": 4,
            "cekApplyCost-exBudgetCPU": 23000,
            "cekApplyCost-exBudgetMemory": 100,
            "cekBuiltinCost-exBudgetCPU": 23000,
            "cekBuiltinCost-exBudgetMemory": 100,
            "cekConstCost-exBudgetCPU": 23000,
            "cekConstCost-exBudgetMemory": 100,
            "cekDelayCost-exBudgetCPU": 23000,
            "cekDelayCost-exBudgetMemory": 100,
            "cekForceCost-exBudgetCPU": 23000,
            "cekForceCost-exBudgetMemory": 100,
            "cekLamCost-exBudgetCPU": 23000,
            "cekLamCost-exBudgetMemory": 100,
            "cekStartupCost-exBudgetCPU": 100,
            "cekStartupCost-exBudgetMemory": 100,
            "cekVarCost-exBudgetCPU": 23000,
            "cekVarCost-exBudgetMemory": 100,
            "chooseData-cpu-arguments": 19537,
            "chooseData-memory-arguments": 32,
            "chooseList-cpu-arguments": 175354,
            "chooseList-memory-arguments": 32,
            "chooseUnit-cpu-arguments": 46417,
            "chooseUnit-memory-arguments": 4,
            "consByteString-cpu-arguments-intercept": 221973,
            "consByteString-cpu-arguments-slope": 511,
            "consByteString-memory-arguments-intercept": 0,
            "consByteString-memory-arguments-slope": 1,
            "constrData-cpu-arguments": 89141,
            "constrData-memory-arguments": 32,
            "decodeUtf8-cpu-arguments-intercept": 497525,
            "decodeUtf8-cpu-arguments-slope": 14068,
            "decodeUtf8-memory-arguments-intercept": 4,
            "decodeUtf8-memory-arguments-slope": 2,
            "divideInteger-cpu-arguments-constant": 196500,
            "divideInteger-cpu-arguments-model-arguments-intercept": 453240,
            "divideInteger-cpu-arguments-model-arguments-slope": 220,
            "divideInteger-memory-arguments-intercept": 0,
            "divideInteger-memory-arguments-minimum": 1,
            "divideInteger-memory-arguments-slope": 1,
            "encodeUtf8-cpu-arguments-intercept": 1000,
            "encodeUtf8-cpu-arguments-slope": 28662,
            "encodeUtf8-memory-arguments-intercept": 4,
            "encodeUtf8-memory-arguments-slope": 2,
            "equalsByteString-cpu-arguments-constant": 245000,
            "equalsByteString-cpu-arguments-intercept": 216773,
            "equalsByteString-cpu-arguments-slope": 62,
            "equalsByteString-memory-arguments": 1,
            "equalsData-cpu-arguments-intercept": 1060367,
            "equalsData-cpu-arguments-slope": 12586,
            "equalsData-memory-arguments": 1,
            "equalsInteger-cpu-arguments-intercept": 208512,
            "equalsInteger-cpu-arguments-slope": 421,
            "equalsInteger-memory-arguments": 1,
            "equalsString-cpu-arguments-constant": 187000,
            "equalsString-cpu-arguments-intercept": 1000,
            "equalsString-cpu-arguments-slope": 52998,
            "equalsString-memory-arguments": 1,
            "fstPair-cpu-arguments": 80436,
            "fstPair-memory-arguments": 32,
            "headList-cpu-arguments": 43249,
            "headList-memory-arguments": 32,
            "iData-cpu-arguments": 1000,
            "iData-memory-arguments": 32,
            "ifThenElse-cpu-arguments": 80556,
            "ifThenElse-memory-arguments": 1,
            "indexByteString-cpu-arguments": 57667,
            "indexByteString-memory-arguments": 4,
            "lengthOfByteString-cpu-arguments": 1000,
            "lengthOfByteString-memory-arguments": 10,
            "lessThanByteString-cpu-arguments-intercept": 197145,
            "lessThanByteString-cpu-arguments-slope": 156,
            "lessThanByteString-memory-arguments": 1,
            "lessThanEqualsByteString-cpu-arguments-intercept": 197145,
            "lessThanEqualsByteString-cpu-arguments-slope": 156,
            "lessThanEqualsByteString-memory-arguments": 1,
            "lessThanEqualsInteger-cpu-arguments-intercept": 204924,
            "lessThanEqualsInteger-cpu-arguments-slope": 473,
            "lessThanEqualsInteger-memory-arguments": 1,
            "lessThanInteger-cpu-arguments-intercept": 208896,
            "lessThanInteger-cpu-arguments-slope": 511,
            "lessThanInteger-memory-arguments": 1,
            "listData-cpu-arguments": 52467,
            "listData-memory-arguments": 32,
            "mapData-cpu-arguments": 64832,
            "mapData-memory-arguments": 32,
            "mkCons-cpu-arguments": 65493,
            "mkCons-memory-arguments": 32,
            "mkNilData-cpu-arguments": 22558,
            "mkNilData-memory-arguments": 32,
            "mkNilPairData-cpu-arguments": 16563,
            "mkNilPairData-memory-arguments": 32,
            "mkPairData-cpu-arguments": 76511,
            "mkPairData-memory-arguments": 32,
            "modInteger-cpu-arguments-constant": 196500,
            "modInteger-cpu-arguments-model-arguments-intercept": 453240,
            "modInteger-cpu-arguments-model-arguments-slope": 220,
            "modInteger-memory-arguments-intercept": 0,
            "modInteger-memory-arguments-minimum": 1,
            "modInteger-memory-arguments-slope": 1,
            "multiplyInteger-cpu-arguments-intercept": 69522,
            "multiplyInteger-cpu-arguments-slope": 11687,
            "multiplyInteger-memory-arguments-intercept": 0,
            "multiplyInteger-memory-arguments-slope": 1,
            "nullList-cpu-arguments": 60091,
            "nullList-memory-arguments": 32,
            "quotientInteger-cpu-arguments-constant": 196500,
            "quotientInteger-cpu-arguments-model-arguments-intercept": 453240,
            "quotientInteger-cpu-arguments-model-arguments-slope": 220,
            "quotientInteger-memory-arguments-intercept": 0,
            "quotientInteger-memory-arguments-minimum": 1,
            "quotientInteger-memory-arguments-slope": 1,
            "remainderInteger-cpu-arguments-constant": 196500,
            "remainderInteger-cpu-arguments-model-arguments-intercept": 453240,
            "remainderInteger-cpu-arguments-model-arguments-slope": 220,
            "remainderInteger-memory-arguments-intercept": 0,
            "remainderInteger-memory-arguments-minimum": 1,
            "remainderInteger-memory-arguments-slope": 1,
            "sha2_256-cpu-arguments-intercept": 806990,
            "sha2_256-cpu-arguments-slope": 30482,
            "sha2_256-memory-arguments": 4,
            "sha3_256-cpu-arguments-intercept": 1927926,
            "sha3_256-cpu-arguments-slope": 82523,
            "sha3_256-memory-arguments": 4,
            "sliceByteString-cpu-arguments-intercept": 265318,
            "sliceByteString-cpu-arguments-slope": 0,
            "sliceByteString-memory-arguments-intercept": 4,
            "sliceByteString-memory-arguments-slope": 0,
            "sndPair-cpu-arguments": 85931,
            "sndPair-memory-arguments": 32,
            "subtractInteger-cpu-arguments-intercept": 205665,
            "subtractInteger-cpu-arguments-slope": 812,
            "subtractInteger-memory-arguments-intercept": 1,
            "subtractInteger-memory-arguments-slope": 1,
            "tailList-cpu-arguments": 41182,
            "tailList-memory-arguments": 32,
            "trace-cpu-arguments": 212342,
            "trace-memory-arguments": 32,
            "unBData-cpu-arguments": 31220,
            "unBData-memory-arguments": 32,
            "unConstrData-cpu-arguments": 32696,
            "unConstrData-memory-arguments": 32,
            "unIData-cpu-arguments": 43357,
            "unIData-memory-arguments": 32,
            "unListData-cpu-arguments": 32247,
            "unListData-memory-arguments": 32,
            "unMapData-cpu-arguments": 38314,
            "unMapData-memory-arguments": 32,
            "verifyEd25519Signature-cpu-arguments-intercept": 57996947,
            "verifyEd25519Signature-cpu-arguments-slope": 18975,
            "verifyEd25519Signature-memory-arguments": 10,
        },
    },
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
    network=CardanoNetwork.PREPROD,
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
    line = f"{MOCK_FULL_ADDRESS},1000\n" * num_output
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
