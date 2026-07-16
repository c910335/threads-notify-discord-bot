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

    if config.ADMIN_CHANNEL_ID:
        try:
            channel = interaction.client.get_channel(config.ADMIN_CHANNEL_ID)
            if not channel:
                channel = await interaction.client.fetch_channel(
                    config.ADMIN_CHANNEL_ID
                )
            msg = (
                f"**[Command Log]** {interaction.user.name} "
                f"({interaction.user.mention}) "
                f"ran `/{interaction.command.name}` "
                f"in <#{interaction.channel_id}>. Options: `{extra_options}`"
            )
            await channel.send(msg)
        except (discord.DiscordException, OSError) as e:
            print(f"Failed to log to admin channel: {e}")


def get_preview_text(text: str) -> str:
    """Generates a preview of the post text.

    Truncates the text to at most 100 characters and 3 lines,
    appending '...' when truncated. A line break is added
    before '...' only if the first omitted character is itself
    a line break.

    Args:
        text: The full post text to preview.

    Returns:
        A truncated preview string, or empty string if the
        input is empty.
    """
    if not text:
        return ""
    lines = text.split("\n")
    has_more_lines = len(lines) > 3
    selected_lines = lines[:3]
    joined_text = "\n".join(selected_lines)
    if len(joined_text) > 100:
        ellipsis = "\n..." if joined_text[100] == "\n" else "..."
        return joined_text[:100] + ellipsis
    if has_more_lines:
        return joined_text + "\n..."
    return joined_text


def format_notification(
    sub: data.SubscriptionDict, post: data.PostDict, display_name: str
) -> str:
    """Formats the notification message for live and test alerts.

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

    preview_text = get_preview_text(post.get("text") or "")
    msg = (
        message_template.replace("{name}", display_name)
        .replace("{text}", post.get("text") or "")
        .replace("{preview_text}", preview_text)
        .replace("{url}", url)
        .replace("{mention}", mention_str)
    )

    if "{url}" not in sub["message"]:
        msg = f"{url}\n{msg}"

    media_urls = post.get("media_urls") or []
    if sub.get("include_media", True) and len(media_urls) > 10:
        omitted = len(media_urls) - 10
        msg = (
            f"{msg}\n*(Note: {omitted} additional media items were omitted "
            f"due to Discord limitations)*"
        )

    return msg


def get_media_gallery_view(
    sub: data.SubscriptionDict, post: data.PostDict, payload: str
) -> discord.ui.LayoutView | None:
    """Creates a discord.ui.LayoutView with a MediaGallery if media is enabled.

    The gallery is created only if media URLs are present.

    Args:
        sub: The subscription configuration dictionary.
        post: The scraped post dictionary.
        payload: The formatted text message content.

    Returns:
        A LayoutView containing the TextDisplay and MediaGallery, or None.
    """
    if not sub.get("include_media", False):
        return None

    media_urls = post.get("media_urls") or []
    if not media_urls:
        return None

    view = discord.ui.LayoutView(timeout=None)
    view.add_item(discord.ui.TextDisplay(payload))

    gallery = discord.ui.MediaGallery()
    # Discord media gallery supports up to 10 items
    for url in media_urls[:10]:
        gallery.add_item(media=url)

    view.add_item(gallery)
    return view
