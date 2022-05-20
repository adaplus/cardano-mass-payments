import enum


class CardanoNetwork(enum.Enum):
    MAINNET = "MAINNET"
    TESTNET = "TESTNET"


class ScriptMethod(enum.Enum):
    METHOD_HOST_CLI = "HOST_CLI"
    METHOD_DOCKER_CLI = "DOCKER_CLI"
    METHOD_PYCARDANO = "PYCARDANO"


class ScriptOutputFormats(enum.Enum):
    BASH_SCRIPT = "BASH_SCRIPT"
    CONSOLE = "CONSOLE"
    JSON = "JSON"
    TRANSACTION_PLAN = "TRANSACTION_PLAN"


class BashColor(enum.Enum):
    NO_COLOR = "\\033[0m"
    BOLD_RED = "\\033[1;31m"
    BOLD_GREEN = "\\033[1;32m"
    BOLD_YELLOW = "\\033[1;33m"


class TransactionStatus(enum.Enum):
    NOT_YET_SUBMITTED = "NOT_YET_SUBMITTED"
    SUBMISSION_ONGOING = "SUBMISSION_ONGOING"
    TTL_EXPIRED = "TTL_EXPIRED"
    SUBMISSION_DONE = "SUBMISSION_DONE"


class DustCollectionMethod(enum.Enum):
    COLLECT_TO_SOURCE = "COLLECT_TO_SOURCE"
    COLLECT_PER_ADDRESS = "COLLECT_PER_ADDRESS"
