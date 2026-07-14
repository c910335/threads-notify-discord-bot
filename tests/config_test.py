"""Unit tests for configuration loading logic."""

import importlib
import os
import sys
import unittest
from unittest import mock

import config


class ConfigTest(unittest.TestCase):
    """Test cases for the configuration loader in config.py."""

    def setUp(self) -> None:
        """Saves a backup of os.environ."""
        self._environ_backup = dict(os.environ)

    def tearDown(self) -> None:
        """Restores os.environ and reloads config to pristine state."""
        os.environ.clear()
        os.environ.update(self._environ_backup)
        importlib.reload(config)

    def test_load_env_loads_successfully(self) -> None:
        """Verifies that config loads settings via python-dotenv load_dotenv."""

        def mock_load_dotenv():
            os.environ["TNDB_DISCORD_TOKEN"] = "dotenv_token"
            os.environ["TNDB_ADMIN_CHANNEL_ID"] = "987654"
            return True

        with mock.patch("dotenv.load_dotenv", side_effect=mock_load_dotenv):
            with mock.patch.dict(os.environ, {}, clear=True):
                # Remove unittest to simulate non-test environment
                unittest_module = sys.modules.pop("unittest", None)
                try:
                    importlib.reload(config)
                finally:
                    if unittest_module:
                        sys.modules["unittest"] = unittest_module

                self.assertEqual(config.DISCORD_TOKEN, "dotenv_token")
                self.assertEqual(config.ADMIN_CHANNEL_ID, 987654)
