# pylint: disable=missing-module-docstring,protected-access

import unittest
from unittest import mock

import discord
import bot


class ThreadsBotTest(unittest.IsolatedAsyncioTestCase):
    """Test cases for ThreadsBot subclassed client."""

    def test_init(self) -> None:
        """Verifies bot initializes with default intents."""
        bot_instance = bot.ThreadsBot()
        self.assertIsInstance(bot_instance.intents, discord.Intents)

    async def test_setup_hook(self) -> None:
        """Verifies setup_hook loads extensions and syncs commands."""
        bot_instance = bot.ThreadsBot()
        bot_instance.load_extension = mock.AsyncMock()
        bot_instance.tree.sync = mock.AsyncMock()

        await bot_instance.setup_hook()

        # Should load the commands and monitor extension cogs
        bot_instance.load_extension.assert_any_call("cogs.threads_commands")
        bot_instance.load_extension.assert_any_call("cogs.monitor")
        self.assertEqual(bot_instance.load_extension.call_count, 2)
        bot_instance.tree.sync.assert_called_once()

    async def test_on_ready(self) -> None:
        """Verifies on_ready event prints logging information."""
        bot_instance = bot.ThreadsBot()
        # Mock user object
        mock_user = mock.MagicMock()
        mock_user.__str__ = mock.Mock(return_value="ThreadsBot")
        mock_user.id = 12345
        bot_instance._connection.user = mock_user

        with mock.patch("builtins.print") as mock_print:
            await bot_instance.on_ready()
            mock_print.assert_called_once_with(
                "Logged in as ThreadsBot (ID: 12345)"
            )


if __name__ == "__main__":
    unittest.main()
