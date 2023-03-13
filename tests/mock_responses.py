from tests.mock_utils import MOCK_ADDRESS, MOCK_FULL_ADDRESS

USE_SUBPROCESS_FUNCTION_FLAG = (
    None  # Will be used as flag for using the subprocess function
)

MOCK_TEST_RESPONSES = {
    ("query", "utxo"): {},
    (
        "cat",
        f"/tmp-files/utxo-{MOCK_ADDRESS}.json",
    ): {},
    (
        "rm",
        f"/tmp-files/utxo-{MOCK_ADDRESS}.json",
    ): {},
    (
        "cat",
        f"/tmp-files/utxo-{MOCK_FULL_ADDRESS}.json",
    ): {},
    (
        "rm",
        f"/tmp-files/utxo-{MOCK_FULL_ADDRESS}.json",
    ): {},
    "build-raw": USE_SUBPROCESS_FUNCTION_FLAG,
    "calculate-min-fee": USE_SUBPROCESS_FUNCTION_FLAG,
    "sign": USE_SUBPROCESS_FUNCTION_FLAG,
    ("query", "protocol-parameters"): USE_SUBPROCESS_FUNCTION_FLAG,
    ("query", "tip"): USE_SUBPROCESS_FUNCTION_FLAG,
    "cat": USE_SUBPROCESS_FUNCTION_FLAG,
    "rm": USE_SUBPROCESS_FUNCTION_FLAG,
    ("cardano-address", "address"): USE_SUBPROCESS_FUNCTION_FLAG,
    '"bech32': USE_SUBPROCESS_FUNCTION_FLAG,
    ("query", "stake-address-info"): USE_SUBPROCESS_FUNCTION_FLAG,
}
