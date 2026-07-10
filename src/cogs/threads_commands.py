"""Slash commands cog for managing Threads subscriptions."""

import traceback

import discord
from discord import app_commands
from discord.ext import commands

import config
import data
import scraper
import utils


class ThreadsCommands(commands.Cog):
    """Cog grouping all subscription configuration slash commands."""

    def __init__(self, bot: commands.Bot) -> None:
        """Initializes the commands cog.

        Args:
            bot: The commands.Bot instance.
        """
        self.bot = bot

    async def autocomplete_username(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Helper to autocomplete username choice from active channel subscriptions."""
        subs: list[data.SubscriptionDict] = data.db.list_subscriptions(
            interaction.channel_id
        )
        choices = []
        for sub in subs:
            u = sub["username"]
            display = data.db.get_display_name(u)
            label = f"{display} (@{u})"
            if current.lower() in u.lower() or current.lower() in display.lower():
                choices.append(app_commands.Choice(name=label, value=u))
        return choices[:25]

    async def autocomplete_message(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Helper to autocomplete message template options."""
        del interaction  # Unused
        return [
            app_commands.Choice(name=t, value=t)
            for t in config.NOTIFICATION_MESSAGE_TEMPLATES
            if current.lower() in t.lower()
        ][:25]

    @app_commands.command(
        name="subscribe",
        description="Subscribe to a Threads profile for the current channel.",
    )
    @app_commands.default_permissions()
    @app_commands.describe(
        username="The Threads username to subscribe to (e.g. c910335)",
        message="Notification message template (supports {name}, {text}, {url}, {mention})",
        mention="The role or user to notify when a new post is found",
        overwrite=(
            "Overwrite the existing subscription if one already exists (default:"
            " False)"
        ),
    )
    async def subscribe(
        self,
        interaction: discord.Interaction,
        username: str,
        message: str,
        mention: discord.Role | discord.Member | None = None,
        overwrite: bool = False,
    ) -> None:
        """Subscribes the current channel to a Threads user's new posts."""
        await utils.log_interaction(
            interaction,
            username=username,
            message=message,
            mention=mention,
            overwrite=overwrite,
        )
        channel_id = interaction.channel_id
        server_id = interaction.guild_id
        mention_str = mention.mention if mention else ""

        success = data.db.add_subscription(
            username=username,
            channel_id=channel_id,
            server_id=server_id,
            message=message,
            mention=mention_str,
            overwrite=overwrite,
        )

        if success:
            display_name = data.db.get_display_name(username) or username
            mention_desc = f" and will ping {mention_str}" if mention_str else ""
            await interaction.response.send_message(
                (
                    f"I will send notifications to <#{channel_id}> with the message"
                    f" (`{message}`){mention_desc} when **{display_name}** "
                    f"(@{username}) posts."
                ),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                (
                    f"Already subscribed to @{username} in this channel. "
                    f"Pass `overwrite: True` to update the configuration."
                ),
                ephemeral=True,
            )

    @subscribe.autocomplete("username")
    async def subscribe_username_auto(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocompletes username parameter for subscribe command."""
        return await self.autocomplete_username(interaction, current)

    @subscribe.autocomplete("message")
    async def subscribe_message_auto(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocompletes message parameter for subscribe command."""
        return await self.autocomplete_message(interaction, current)

    @app_commands.command(
        name="unsubscribe",
        description=(
            "Unsubscribe from a Threads profile for the current channel."
        ),
    )
    @app_commands.default_permissions()
    @app_commands.describe(username="The Threads username to unsubscribe from")
    async def unsubscribe(
        self, interaction: discord.Interaction, username: str
    ) -> None:
        """Unsubscribes the current channel from a Threads user's posts."""
        await utils.log_interaction(interaction, username=username)
        success = data.db.remove_subscription(username, interaction.channel_id)

        if success:
            await interaction.response.send_message(
                f"Unsubscribed from @{username} in this channel.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                (
                    f"No active subscription found for @{username} in this"
                    f" channel."
                ),
                ephemeral=True,
            )

    @unsubscribe.autocomplete("username")
    async def unsubscribe_username_auto(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocompletes username parameter for unsubscribe command."""
        return await self.autocomplete_username(interaction, current)

    @app_commands.command(
        name="list",
        description=(
            "List all Threads subscriptions active in the current channel."
        ),
    )
    @app_commands.default_permissions()
    async def list_subs(self, interaction: discord.Interaction) -> None:
        """Lists active subscription configurations in the channel."""
        await utils.log_interaction(interaction)
        subs: list[data.SubscriptionDict] = data.db.list_subscriptions(
            interaction.channel_id
        )

        if not subs:
            await interaction.response.send_message(
                "No active subscriptions in this channel.", ephemeral=True
            )
            return

        lines = ["**Active Subscriptions for this Channel:**"]
        for idx, sub in enumerate(subs):
            display_name = data.db.get_display_name(sub["username"])
            mention_desc = f" — pings {sub['mention']}" if sub["mention"] else ""
            lines.append(
                f"{idx + 1}. **{display_name}** (@{sub['username']}){mention_desc}:"
                f" `{sub['message']}`"
            )

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(
        name="test",
        description=(
            "Trigger a test notification for a subscribed Threads profile."
        ),
    )
    @app_commands.default_permissions()
    @app_commands.describe(
        username="The Threads username to test",
        silent="If true, the test notification will be visible only to you",
    )
    async def test_notify(
        self, interaction: discord.Interaction, username: str, silent: bool
    ) -> None:
        """Manually scrapes and outputs a test message using active templates."""
        await utils.log_interaction(interaction, username=username, silent=silent)
        await interaction.response.defer(ephemeral=silent)
        username = username.strip().lower()

        subs: list[data.SubscriptionDict] = data.db.get_subscriptions_for_user(
            username
        )
        channel_subs: list[data.SubscriptionDict] = [
            s for s in subs if s["channel_id"] == interaction.channel_id
        ]

        if not channel_subs:
            await interaction.followup.send(
                f"No subscription for @{username} in this channel.",
                ephemeral=silent,
            )
            return

        try:
            posts: list[data.PostDict] = await scraper.scrape_user_posts(
                username
            )
            if not posts:
                await interaction.followup.send(
                    (
                        f"No posts found for @{username} or profile was not"
                        f" accessible."
                    ),
                    ephemeral=silent,
                )
                return

            latest_post: data.PostDict = posts[0]
            display_name = latest_post.get(
                "display_name"
            ) or data.db.get_display_name(username)
            data.db.update_display_name(username, display_name)

            sub: data.SubscriptionDict = channel_subs[0]
            payload = utils.format_notification(sub, latest_post, display_name)

            print(
                f"Trigger a test notification for {display_name} (@{username}) "
                f"to {interaction.channel_id}:{interaction.guild_id}"
            )
            await interaction.followup.send(payload, ephemeral=silent)

        except Exception:  # pylint: disable=broad-except
            error_trace = traceback.format_exc()
            await interaction.followup.send(
                (
                    f"**Test Failed for @{username}!**\n"
                    f"Error details:\n```\n{error_trace[:1800]}\n```"
                ),
                ephemeral=silent,
            )

    @test_notify.autocomplete("username")
    async def test_username_auto(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocompletes username parameter for test command."""
        return await self.autocomplete_username(interaction, current)


async def setup(bot: commands.Bot) -> None:
    """Standard setup entrypoint for registering cogs in discord.py.

    Args:
        bot: The commands.Bot instance.
    """
    await bot.add_cog(ThreadsCommands(bot))
