USE_SUBPROCESS_FUNCTION_FLAG = (
    None  # Will be used as flag for using the subprocess function
)

MOCK_TEST_RESPONSES = {
    ("query", "utxo"): {},
    (
        "cat",
        "/tmp/utxo-addr_test1vpv2u2aqrvp4qnsw93qck3xagvwlleqs29erxtz3322t8ls46s7ew.json",
    ): {},
    (
        "rm",
        "/tmp/utxo-addr_test1vpv2u2aqrvp4qnsw93qck3xagvwlleqs29erxtz3322t8ls46s7ew.json",
    ): {},
    "build-raw": USE_SUBPROCESS_FUNCTION_FLAG,
    "calculate-min-fee": USE_SUBPROCESS_FUNCTION_FLAG,
    "sign": USE_SUBPROCESS_FUNCTION_FLAG,
    ("query", "protocol-parameters"): USE_SUBPROCESS_FUNCTION_FLAG,
    ("query", "tip"): USE_SUBPROCESS_FUNCTION_FLAG,
    "cat": USE_SUBPROCESS_FUNCTION_FLAG,
    "rm": USE_SUBPROCESS_FUNCTION_FLAG,
}
