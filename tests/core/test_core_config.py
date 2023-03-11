import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import patch

from futuresboard.core.config import Config, load_config


class TestCoreConfig(unittest.TestCase):
    def test_Config_validators(self):
        with self.assertRaises(ValueError):
            Config(
                accounts=[],
                scrape_interval=59,
                database_name="futuresboard",
            )

        with self.assertRaises(ValueError):
            Config(
                accounts=None,
                scrape_interval=60,
                database_name="futuresboard",
            )

    @patch("builtins.open")
    @patch("pathlib.Path.is_file")
    def test_load_config(self, mock_is_file, mock_open):
        path = Path("testfile.json")

        mock_is_file.return_value = False
        with self.assertRaises(ValueError) as cm:
            load_config(path)
            assert "testfile.json does not exist" == str(cm.exception)

        mock_is_file.return_value = True
        opener = mock.mock_open(read_data="")
        mock_open.side_effect = opener.side_effect
        mock_open.return_value = opener.return_value
        with self.assertRaises(ValueError) as cm:
            load_config(path)
            assert "ERROR: Invalid JSON: Expecting value, line 1, column 1" == str(
                cm.exception
            )

        opener = mock.mock_open(read_data='{"scrape_interval":0}')
        mock_open.side_effect = opener.side_effect
        mock_open.return_value = opener.return_value
        with self.assertRaises(ValueError) as cm:
            load_config(path)
            assert "ValueError: 2 validation errors for Config" == str(cm.exception)


if __name__ == "__main__":
    unittest.main()
