from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from cardano_mass_payments.constants.common import ScriptMethod
from cardano_mass_payments.constants.exceptions import (
    InvalidMethod,
    InvalidNetwork,
    InvalidType,
    ScriptError,
)
from cardano_mass_payments.utils.cli_utils import get_staking_address
from tests.mock_responses import MOCK_TEST_RESPONSES
from tests.mock_utils import (
    INVALID_INT_TYPE,
    MOCK_FULL_ADDRESS,
    MOCK_STAKE_ADDRESS,
    generate_mock_popen_function,
    mock_raise_internal_error,
)


class TestProcess(TestCase):
    def test_missing_full_address(self):
        try:
            result = get_staking_address()
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_invalid_full_address(self):
        try:
            result = get_staking_address(full_address=-1)
        except Exception as e:
            result = e

        assert isinstance(result, InvalidType)
        assert result.message == "Invalid Full Address Type."
        assert result.additional_context["type"] == INVALID_INT_TYPE

    def test_invalid_network(self):
        try:
            result = get_staking_address(
                full_address=MOCK_FULL_ADDRESS,
                network="invalid",
            )
        except Exception as e:
            result = e

        assert isinstance(result, InvalidNetwork)
        assert result.additional_context["network"] == "invalid"

    def test_invalid_method(self):
        try:
            result = get_staking_address(
                full_address=MOCK_FULL_ADDRESS,
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
                result = get_staking_address(
                    full_address=MOCK_FULL_ADDRESS,
                    method=ScriptMethod.METHOD_DOCKER_CLI,
                )
            except Exception as e:
                result = e

        assert isinstance(result, ScriptError)

    def test_success(self):
        mock_responses = deepcopy(MOCK_TEST_RESPONSES)
        mock_responses[("cardano-address", "address")] = {
            "stake_key_hash": "test_stake_key_hash",
        }
        mock_responses['"bech32'] = MOCK_STAKE_ADDRESS

        with patch(
            "cardano_mass_payments.utils.cli_utils.subprocess_popen",
            side_effect=generate_mock_popen_function(mock_responses),
        ):
            try:
                result = get_staking_address(
                    full_address=MOCK_FULL_ADDRESS,
                    method=ScriptMethod.METHOD_DOCKER_CLI,
                )
            except Exception as e:
                result = e

        assert isinstance(result, str)
        assert result == MOCK_STAKE_ADDRESS

    def test_success_pycardano(self):
        try:
            result = get_staking_address(
                full_address=MOCK_FULL_ADDRESS,
                method=ScriptMethod.METHOD_PYCARDANO,
            )
        except Exception as e:
            result = e

        assert isinstance(result, str)
        assert result == MOCK_STAKE_ADDRESS
