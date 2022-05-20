import os
import stat
import tempfile
from unittest import TestCase

from cardano_mass_payments.constants.exceptions import EmptyList
from cardano_mass_payments.utils.script_utils import parse_payment_utxo_file
from tests.mock_utils import create_test_payment_csv


class TestProcess(TestCase):
    def test_missing_filename(self):
        try:
            result = parse_payment_utxo_file()
        except Exception as e:
            result = e

        assert isinstance(result, TypeError)

    def test_invalid_filename(self):
        try:
            result = parse_payment_utxo_file(-1)
        except Exception as e:
            result = e

        assert isinstance(result, ValueError)

    def test_nonexistent_file(self):
        try:
            result = parse_payment_utxo_file("nonexistent.csv")
        except Exception as e:
            result = e

        assert isinstance(result, FileNotFoundError)

    def test_inaccessible_file(self):
        unaccessible_sources_file = tempfile.NamedTemporaryFile(
            mode="w+",
            suffix=".csv",
        )

        # Remove read permission
        os.chmod(unaccessible_sources_file.name, ~stat.S_IRUSR)
        try:
            result = parse_payment_utxo_file(unaccessible_sources_file.name)
        except Exception as e:
            result = e

        assert isinstance(result, PermissionError)

    def test_empty_file(self):
        empty_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".csv")

        try:
            result = parse_payment_utxo_file(empty_file.name)
        except Exception as e:
            result = e

        assert isinstance(result, EmptyList)

    def test_invalid_file_content(self):
        invalid_content_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".csv")
        invalid_content_file.write("column_1")
        invalid_content_file.seek(0)

        try:
            result = parse_payment_utxo_file(invalid_content_file.name)
        except Exception as e:
            result = e

        assert isinstance(result, IndexError)

    def test_success(self):
        payment_file = create_test_payment_csv(30)

        try:
            result = parse_payment_utxo_file(payment_file.name)
        except Exception as e:
            result = e

        assert isinstance(result, list)
        assert len(result) == 30
