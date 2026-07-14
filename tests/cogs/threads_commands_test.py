# pylint: disable=protected-access,duplicate-code,missing-module-docstring

import os
import tempfile
import unittest
from unittest import mock

import discord
from discord.ext import commands

import config
import data
from cogs import threads_commands


class ThreadsCommandsTest(unittest.IsolatedAsyncioTestCase):
    """Test cases for ThreadsCommands cog."""

    def setUp(self) -> None:
        """Sets up custom testing file paths and mock bot context."""
        self.test_dir = self.enterContext(tempfile.TemporaryDirectory())  # pylint: disable=consider-using-with
        data.DataStore.DATA_FILE = os.path.join(
            self.test_dir, "test_commands_data.json"
        )
        data.DataStore.SEEN_FILE = os.path.join(
            self.test_dir, "test_commands_seen.json"
        )
        data.DataStore.DISPLAY_NAMES_FILE = os.path.join(
            self.test_dir, "test_commands_display_names.json"
        )

        # Initialize clean data store
        self.db = data.db
        self.db.subscriptions = []
        self.db.seen_posts = {}
        self.db.display_names = {}

        # Mock Bot
        self.mock_bot = mock.MagicMock(spec=commands.Bot)
        self.mock_bot.browser = mock.MagicMock()
        self.commands_cog = threads_commands.ThreadsCommands(self.mock_bot)

    async def test_subscribe_command_success(self) -> None:
        """Verifies /subscribe command registers a new subscription successfully."""
        mock_interaction = mock.MagicMock(spec=discord.Interaction)
        mock_interaction.channel_id = 111
        mock_interaction.guild_id = 222
        mock_interaction.user.name = "adminuser"
        mock_interaction.user.mention = "<@admin>"
        mock_interaction.command.name = "subscribe"

        # Mock interaction response
        mock_interaction.response = mock.MagicMock()
        mock_interaction.response.send_message = mock.AsyncMock()

        # Set ADMIN_CHANNEL_ID to 0 to bypass interaction logging in tests
        with mock.patch.object(config, "ADMIN_CHANNEL_ID", 0):
            await self.commands_cog.subscribe.callback(
                self.commands_cog,
                interaction=mock_interaction,
                username="c910335",
                message="hello {name} {url}",
                mention=None,
                overwrite=False,
            )

        # Verify subscription was added
        subs = self.db.list_subscriptions(111)
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0]["username"], "c910335")
        mock_interaction.response.send_message.assert_called_once()
        self.assertIn(
            "I will send notifications",
            mock_interaction.response.send_message.call_args[0][0],
        )

    async def test_subscribe_command_conflict_without_overwrite(self) -> None:
        """Verifies /subscribe command rejects duplicate subscription without overwrite."""
        self.db.add_subscription("c910335", 111, 222, "msg", "", False)

        mock_interaction = mock.MagicMock(spec=discord.Interaction)
        mock_interaction.channel_id = 111
        mock_interaction.guild_id = 222
        mock_interaction.user.name = "adminuser"
        mock_interaction.user.mention = "<@admin>"
        mock_interaction.command.name = "subscribe"
        mock_interaction.response = mock.MagicMock()
        mock_interaction.response.send_message = mock.AsyncMock()

        with mock.patch.object(config, "ADMIN_CHANNEL_ID", 0):
            await self.commands_cog.subscribe.callback(
                self.commands_cog,
                interaction=mock_interaction,
                username="c910335",
                message="new msg",
                mention=None,
                overwrite=False,
            )

        # Verify subscription did not change
        subs = self.db.list_subscriptions(111)
        self.assertEqual(subs[0]["message"], "msg")
        mock_interaction.response.send_message.assert_called_once()
        self.assertIn(
            "Already subscribed",
            mock_interaction.response.send_message.call_args[0][0],
        )

    async def test_unsubscribe_command_success(self) -> None:
        """Verifies /unsubscribe command removes active subscription successfully."""
        self.db.add_subscription("c910335", 111, 222, "msg", "", False)

        mock_interaction = mock.MagicMock(spec=discord.Interaction)
        mock_interaction.channel_id = 111
        mock_interaction.guild_id = 222
        mock_interaction.user.name = "adminuser"
        mock_interaction.user.mention = "<@admin>"
        mock_interaction.command.name = "unsubscribe"
        mock_interaction.response = mock.MagicMock()
        mock_interaction.response.send_message = mock.AsyncMock()

        with mock.patch.object(config, "ADMIN_CHANNEL_ID", 0):
            await self.commands_cog.unsubscribe.callback(
                self.commands_cog, mock_interaction, "c910335"
            )

        subs = self.db.list_subscriptions(111)
        self.assertEqual(len(subs), 0)
        mock_interaction.response.send_message.assert_called_once()
        self.assertIn(
            "Unsubscribed from",
            mock_interaction.response.send_message.call_args[0][0],
        )

    async def test_unsubscribe_command_not_found(self) -> None:
        """Verifies /unsubscribe command reports failure when no subscription exists."""
        mock_interaction = mock.MagicMock(spec=discord.Interaction)
        mock_interaction.channel_id = 111
        mock_interaction.guild_id = 222
        mock_interaction.user.name = "adminuser"
        mock_interaction.user.mention = "<@admin>"
        mock_interaction.command.name = "unsubscribe"
        mock_interaction.response = mock.MagicMock()
        mock_interaction.response.send_message = mock.AsyncMock()

        with mock.patch.object(config, "ADMIN_CHANNEL_ID", 0):
            await self.commands_cog.unsubscribe.callback(
                self.commands_cog, mock_interaction, "c910335"
            )

        mock_interaction.response.send_message.assert_called_once()
        self.assertIn(
            "No active subscription",
            mock_interaction.response.send_message.call_args[0][0],
        )

    async def test_list_subs_command_empty(self) -> None:
        """Verifies /list command output when no subscriptions are present."""
        mock_interaction = mock.MagicMock(spec=discord.Interaction)
        mock_interaction.channel_id = 111
        mock_interaction.guild_id = 222
        mock_interaction.user.name = "adminuser"
        mock_interaction.user.mention = "<@admin>"
        mock_interaction.command.name = "list"
        mock_interaction.response = mock.MagicMock()
        mock_interaction.response.send_message = mock.AsyncMock()

        with mock.patch.object(config, "ADMIN_CHANNEL_ID", 0):
            await self.commands_cog.list_subs.callback(
                self.commands_cog, mock_interaction
            )

        mock_interaction.response.send_message.assert_called_once_with(
            "No active subscriptions in this channel.", ephemeral=True
        )

    async def test_list_subs_command_populated(self) -> None:
        """Verifies /list command formats and displays subscriptions correctly."""
        self.db.add_subscription("c910335", 111, 222, "msg", "<@&1>", False)

        mock_interaction = mock.MagicMock(spec=discord.Interaction)
        mock_interaction.channel_id = 111
        mock_interaction.guild_id = 222
        mock_interaction.user.name = "adminuser"
        mock_interaction.user.mention = "<@admin>"
        mock_interaction.command.name = "list"
        mock_interaction.response = mock.MagicMock()
        mock_interaction.response.send_message = mock.AsyncMock()

        with mock.patch.object(config, "ADMIN_CHANNEL_ID", 0):
            await self.commands_cog.list_subs.callback(
                self.commands_cog, mock_interaction
            )

        mock_interaction.response.send_message.assert_called_once()
        self.assertIn(
            "Active Subscriptions for this Channel:",
            mock_interaction.response.send_message.call_args[0][0],
        )
        self.assertIn(
            "c910335",
            mock_interaction.response.send_message.call_args[0][0],
        )

    async def test_test_notify_command_success(self) -> None:
        """Verifies /test command triggers a manual fetch and notification successfully."""
        self.db.add_subscription("c910335", 111, 222, "msg {url}", "", False)

        mock_interaction = mock.MagicMock(spec=discord.Interaction)
        mock_interaction.channel_id = 111
        mock_interaction.guild_id = 222
        mock_interaction.user.name = "adminuser"
        mock_interaction.user.mention = "<@admin>"
        mock_interaction.command.name = "test"
        mock_interaction.response = mock.MagicMock()
        mock_interaction.response.defer = mock.AsyncMock()
        mock_interaction.followup = mock.MagicMock()
        mock_interaction.followup.send = mock.AsyncMock()

        mock_posts = [
            {
                "id": "post123",
                "code": "C123",
                "username": "c910335",
                "display_name": "達人",
                "text": "Hello",
                "timestamp": 1600000000,
                "url": "https://www.threads.com/@c910335/post/C123",
                "media_urls": [],
            }
        ]

        with mock.patch.object(config, "ADMIN_CHANNEL_ID", 0):
            with mock.patch("scraper.scrape_user_posts", return_value=mock_posts):
                await self.commands_cog.test_notify.callback(
                    self.commands_cog, mock_interaction, "c910335", False
                )

        mock_interaction.response.defer.assert_called_once_with(ephemeral=False)
        mock_interaction.followup.send.assert_called_once()
        self.assertIn(
            "https://www.threads.com/@c910335/post/C123",
            mock_interaction.followup.send.call_args[0][0],
        )

    async def test_autocomplete_username_and_message(self) -> None:
        """Verifies username and message autocompleters return correct choices."""
        self.db.add_subscription("c910335", 111, 222, "msg", "", False)
        self.db.update_display_name("c910335", "達人")

        mock_interaction = mock.MagicMock(spec=discord.Interaction)
        mock_interaction.channel_id = 111

        # Test autocomplete username
        choices = await self.commands_cog.autocomplete_username(
            mock_interaction, "c91"
        )
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0].name, "達人 (@c910335)")
        self.assertEqual(choices[0].value, "c910335")

        # Test autocomplete message
        msg_choices = await self.commands_cog.autocomplete_message(
            mock_interaction, "update"
        )
        self.assertEqual(len(msg_choices), 1)
        self.assertIn("update", msg_choices[0].value)

    async def test_test_notify_no_posts_and_error(self) -> None:
        """Verifies /test command behavior when no posts are found or scrape fails."""
        self.db.add_subscription("c910335", 111, 222, "msg", "", False)

        mock_interaction = mock.MagicMock(spec=discord.Interaction)
        mock_interaction.channel_id = 111
        mock_interaction.guild_id = 222
        mock_interaction.user.name = "adminuser"
        mock_interaction.user.mention = "<@admin>"
        mock_interaction.command.name = "test"
        mock_interaction.response = mock.MagicMock()
        mock_interaction.response.defer = mock.AsyncMock()
        mock_interaction.followup = mock.MagicMock()
        mock_interaction.followup.send = mock.AsyncMock()

        # 1. No posts found
        with mock.patch.object(config, "ADMIN_CHANNEL_ID", 0):
            with mock.patch("scraper.scrape_user_posts", return_value=[]):
                await self.commands_cog.test_notify.callback(
                    self.commands_cog, mock_interaction, "c910335", False
                )
        self.assertIn(
            "No posts found", mock_interaction.followup.send.call_args[0][0]
        )

        # 2. Scraper raises exception
        mock_interaction.followup.send.reset_mock()
        with mock.patch.object(config, "ADMIN_CHANNEL_ID", 0):
            with mock.patch(
                "scraper.scrape_user_posts", side_effect=Exception("Scrape error")
            ):
                await self.commands_cog.test_notify.callback(
                    self.commands_cog, mock_interaction, "c910335", False
                )
        self.assertIn(
            "Test Failed", mock_interaction.followup.send.call_args[0][0]
        )

    async def test_autocomplete_username_with_active_subscription(self) -> None:
        """Verifies autocomplete_username returns the subscribed profile choices."""
        self.db.add_subscription("c910335", 111, 222, "msg1", "", False)
        self.db.update_display_name("c910335", "達人")

        mock_interaction = mock.MagicMock(spec=discord.Interaction)
        mock_interaction.channel_id = 111

        choices = await self.commands_cog.autocomplete_username(
            mock_interaction, "c91"
        )
        self.assertEqual(len(choices), 1)

    async def test_test_notify_not_subscribed(self) -> None:
        """Verifies /test command behavior when channel is not subscribed to profile."""
        mock_interaction = mock.MagicMock(spec=discord.Interaction)
        mock_interaction.channel_id = 111
        mock_interaction.guild_id = 222
        mock_interaction.user.name = "adminuser"
        mock_interaction.user.mention = "<@admin>"
        mock_interaction.command.name = "test"
        mock_interaction.response = mock.MagicMock()
        mock_interaction.response.defer = mock.AsyncMock()
        mock_interaction.followup = mock.MagicMock()
        mock_interaction.followup.send = mock.AsyncMock()

        # Target user is not subscribed
        with mock.patch.object(config, "ADMIN_CHANNEL_ID", 0):
            await self.commands_cog.test_notify.callback(
                self.commands_cog, mock_interaction, "c910335", False
            )

        self.assertIn(
            "No subscription for @c910335",
            mock_interaction.followup.send.call_args[0][0],
        )

    async def test_setup_commands(self) -> None:
        """Verifies setup registers ThreadsCommands cog."""
        mock_bot = mock.MagicMock(spec=commands.Bot)
        mock_bot.add_cog = mock.AsyncMock()
        await threads_commands.setup(mock_bot)
        mock_bot.add_cog.assert_called_once()

    async def test_autocomplete_wrappers(self) -> None:
        """Verifies autocomplete wrappers call the underlying handler."""
        mock_interaction = mock.MagicMock(spec=discord.Interaction)
        mock_interaction.channel_id = 111

        with mock.patch.object(
            self.commands_cog, "autocomplete_username", new_callable=mock.AsyncMock
        ) as mock_user:
            await self.commands_cog.subscribe_username_auto(
                mock_interaction, "foo"
            )
            mock_user.assert_called_once_with(mock_interaction, "foo")

            mock_user.reset_mock()
            await self.commands_cog.unsubscribe_username_auto(
                mock_interaction, "foo"
            )
            mock_user.assert_called_once_with(mock_interaction, "foo")

            mock_user.reset_mock()
            await self.commands_cog.test_username_auto(mock_interaction, "foo")
            mock_user.assert_called_once_with(mock_interaction, "foo")

        with mock.patch.object(
            self.commands_cog, "autocomplete_message", new_callable=mock.AsyncMock
        ) as mock_msg:
            await self.commands_cog.subscribe_message_auto(
                mock_interaction, "foo"
            )
            mock_msg.assert_called_once_with(mock_interaction, "foo")


if __name__ == "__main__":
    unittest.main()
