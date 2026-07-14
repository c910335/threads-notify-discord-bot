"""Unit tests for formatting and logging utility functions."""

import unittest
from unittest import mock

import discord

import config
import data
import utils


class UtilsTest(unittest.IsolatedAsyncioTestCase):
    """Test cases for utils.py helper functions including async interaction logs."""

    def test_format_notification_with_all_placeholders(self) -> None:
        """Verifies replacement of all supported variables in a template."""
        sub: data.SubscriptionDict = {
            "username": "testuser",
            "channel_id": 123,
            "server_id": 456,
            "message": "{mention} **{name}** posted: {text} - Link: {url}",
            "mention": "<@&789>",
        }
        post: data.PostDict = {
            "id": "post123",
            "code": "C123",
            "username": "testuser",
            "display_name": "Test User",
            "text": "Hello World!",
            "timestamp": 1600000000,
            "url": "https://www.threads.com/@testuser/post/C123",
            "media_urls": [],
        }

        result = utils.format_notification(sub, post, "Test User")
        expected = (
            "<@&789> **Test User** posted: Hello World! - "
            "Link: https://www.threads.com/@testuser/post/C123"
        )
        self.assertEqual(result, expected)

    def test_format_notification_prepends_url_if_not_in_message(self) -> None:
        """Verifies that URL is prepended if {url} is missing from the template."""
        sub: data.SubscriptionDict = {
            "username": "testuser",
            "channel_id": 123,
            "server_id": 456,
            "message": "{name} 有新貼文！",
            "mention": "",
        }
        post: data.PostDict = {
            "id": "post123",
            "code": "C123",
            "username": "testuser",
            "display_name": "Test User",
            "text": "Hello!",
            "timestamp": 1600000000,
            "url": "https://www.threads.com/@testuser/post/C123",
            "media_urls": [],
        }

        result = utils.format_notification(sub, post, "Test User")
        expected = "https://www.threads.com/@testuser/post/C123\nTest User 有新貼文！"
        self.assertEqual(result, expected)

    def test_format_notification_prepends_mention_if_not_in_message(self) -> None:
        """Verifies that mention is prepended if {mention} is not in template."""
        sub: data.SubscriptionDict = {
            "username": "testuser",
            "channel_id": 123,
            "server_id": 456,
            "message": "{name} 發文囉！ {url}",
            "mention": "<@&789>",
        }
        post: data.PostDict = {
            "id": "post123",
            "code": "C123",
            "username": "testuser",
            "display_name": "Test User",
            "text": "Hello!",
            "timestamp": 1600000000,
            "url": "https://www.threads.com/@testuser/post/C123",
            "media_urls": [],
        }

        result = utils.format_notification(sub, post, "Test User")
        expected = (
            "<@&789> Test User 發文囉！ https://www.threads.com/@testuser/post/C123"
        )
        self.assertEqual(result, expected)

    async def test_log_interaction_sends_to_admin(self) -> None:
        """Verifies logging command sends notification to admin channel."""
        mock_interaction = mock.MagicMock()
        mock_interaction.user.name = "testuser"
        mock_interaction.user.mention = "<@123>"
        mock_interaction.channel_id = 456
        mock_interaction.guild_id = 789
        mock_interaction.command.name = "subscribe"

        mock_client = mock.MagicMock()
        mock_channel = mock.MagicMock()
        mock_channel.send = mock.AsyncMock()
        mock_client.get_channel.return_value = None
        mock_client.fetch_channel = mock.AsyncMock(return_value=mock_channel)
        mock_interaction.client = mock_client

        with mock.patch.object(config, "ADMIN_CHANNEL_ID", 999):
            await utils.log_interaction(mock_interaction, username="targetuser")

        mock_client.get_channel.assert_called_once_with(999)
        mock_client.fetch_channel.assert_called_once_with(999)
        mock_channel.send.assert_called_once()
        self.assertIn("targetuser", mock_channel.send.call_args[0][0])

    async def test_log_interaction_handles_exception_gracefully(self) -> None:
        """Verifies that an error in sending to admin doesn't crash log_interaction."""
        mock_interaction = mock.MagicMock()
        mock_interaction.user.name = "testuser"
        mock_interaction.user.mention = "<@123>"
        mock_interaction.channel_id = 456
        mock_interaction.guild_id = 789
        mock_interaction.command.name = "subscribe"

        mock_client = mock.MagicMock()
        mock_client.get_channel.side_effect = discord.DiscordException("Discord Error")
        mock_interaction.client = mock_client

        with mock.patch.object(config, "ADMIN_CHANNEL_ID", 999):
            # This should not raise an exception
            await utils.log_interaction(mock_interaction, username="targetuser")


if __name__ == "__main__":
    unittest.main()
