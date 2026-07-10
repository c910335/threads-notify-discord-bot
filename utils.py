"""Helper utility functions for logging and message formatting."""

from typing import Any

import discord

import config
import data


async def log_interaction(
    interaction: discord.Interaction, **extra_options: Any
) -> None:
    """Logs slash command invocations to console and admin channel.

    Args:
        interaction: The Discord interaction object.
        **extra_options: Key-value parameters passed to the slash command.
    """
    server_part = f":{interaction.guild_id}" if interaction.guild_id else ""
    options_str = ", ".join(f"{k}: {v}" for k, v in extra_options.items())
    print(
        f"{interaction.user.name}@{interaction.channel_id}{server_part}: "
        f"/{interaction.command.name} {options_str}"
    )

    if config.ADMIN_CHANNEL_ID != 0:
        try:
            channel = interaction.client.get_channel(config.ADMIN_CHANNEL_ID)
            if not channel:
                channel = await interaction.client.fetch_channel(
                    config.ADMIN_CHANNEL_ID
                )
            msg = (
                f"**[Command Log]** {interaction.user.name} "
                f"({interaction.user.mention}) ran `/{interaction.command.name}` "
                f"in <#{interaction.channel_id}>. Options: `{extra_options}`"
            )
            await channel.send(msg)
        except Exception as e:  # pylint: disable=broad-except
            print(f"Failed to log to admin channel: {e}")


def format_notification(
    sub: data.SubscriptionDict, post: data.PostDict, display_name: str
) -> str:
    """Formats the notification payload for both live checks and test commands.

    Args:
        sub: The subscription configuration dictionary.
        post: The scraped post dictionary.
        display_name: The display name of the poster.

    Returns:
        The formatted notification message payload string.
    """
    mention_str = sub["mention"] if sub.get("mention") else ""
    url = (
        post["url"]
        or f"https://www.threads.com/@{post['username']}/post/{post['code']}"
    )

    message_template = sub["message"]
    if mention_str and "{mention}" not in message_template:
        message_template = f"{mention_str} {message_template}"

    msg = (
        message_template.replace("{name}", display_name)
        .replace("{text}", post.get("text") or "")
        .replace("{url}", url)
        .replace("{mention}", mention_str)
    )

    if "{url}" in sub["message"]:
        return msg
    return f"{url}\n{msg}"
