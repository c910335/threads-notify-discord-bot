import asyncio
import traceback
import discord
from discord import app_commands
from discord.ext import tasks, commands
from config import Config
from data import DataStore
from scraper import scrape_user_posts

# Initialize Data Store
db = DataStore()


def log_interaction(interaction: discord.Interaction, **extra_options):
    """Log slash command invocations like the 17 notify bot does."""
    server_part = f":{interaction.guild_id}" if interaction.guild_id else ""
    options_str = ", ".join(f"{k}: {v}" for k, v in extra_options.items())
    print(
        f"{interaction.user.name}@{interaction.channel_id}{server_part}: "
        f"/{interaction.command.name} {options_str}"
    )


def format_notification(sub: dict, post: dict, display_name: str) -> str:
    """Build the notification payload the same way for both monitor and /test."""
    mention_str = sub["mention"] if sub.get("mention") else ""
    url = post["url"] or f"https://www.threads.com/@{post['username']}/post/{post['code']}"
    
    message_template = sub["message"]
    if mention_str and "{mention}" not in message_template:
        message_template = f"{mention_str} {message_template}"
        
    msg = (
        message_template
        .replace("{name}", display_name)
        .replace("{url}", url)
        .replace("{mention}", mention_str)
    )
    
    if "{url}" in sub["message"]:
        return msg
    else:
        return f"{url}\n{msg}"


class ThreadsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced globally.")
        self.monitor_loop.start()
        print("Background monitoring task started.")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")

    @tasks.loop(seconds=Config.HEARTBEAT_DELAY_SECONDS)
    async def monitor_loop(self):
        print("Heartbeat check started.")
        usernames = db.get_all_sub_usernames()

        for username in usernames:
            try:
                print(f"Checking updates for Threads profile: @{username}")
                posts = await scrape_user_posts(username)

                if not posts:
                    print(f"No posts found for @{username}, skipping.")
                    await asyncio.sleep(Config.CHECK_DELAY_SECONDS)
                    continue

                # Update display name cache from the latest scrape
                display_name = posts[0].get("display_name") or username
                db.update_display_name(username, display_name)

                # Extract all post IDs
                post_ids = [p["id"] for p in posts]

                # Newly tracked user: initialise cache without sending notifications
                if username not in db.seen_posts:
                    print(
                        f"Initializing seen posts cache for @{username} "
                        f"({display_name}) with {len(post_ids)} existing posts."
                    )
                    db.init_user_seen_posts(username, post_ids)
                    await asyncio.sleep(Config.CHECK_DELAY_SECONDS)
                    continue

                # Find new posts (oldest first)
                new_posts = [p for p in reversed(posts) if not db.is_post_seen(username, p["id"])]

                for post in new_posts:
                    print(
                        f"New post from {display_name} (@{username}): {post['url']}"
                    )
                    for sub in db.get_subscriptions_for_user(username):
                        channel = self.get_channel(sub["channel_id"])
                        if not channel:
                            try:
                                channel = await self.fetch_channel(sub["channel_id"])
                            except Exception:
                                continue

                        payload = format_notification(sub, post, display_name)
                        try:
                            await channel.send(payload)
                            print(
                                f"Sent notification to channel {sub['channel_id']} "
                                f"for post {post['url']}"
                            )
                        except Exception as e:
                            print(f"Failed to send to channel {sub['channel_id']}: {e}")

                    db.mark_post_seen(username, post["id"])

                await asyncio.sleep(Config.CHECK_DELAY_SECONDS)

            except Exception:
                error_trace = traceback.format_exc()
                print(f"Error checking updates for @{username}:\n{error_trace}")
                await self.report_error(
                    f"Error scraping @{username}:\n```\n{error_trace[:1800]}\n```"
                )

        print("Heartbeat check done.")

    @monitor_loop.before_loop
    async def before_monitor(self):
        await self.wait_until_ready()

    async def report_error(self, message: str):
        if Config.ADMIN_CHANNEL_ID == 0:
            return
        try:
            channel = self.get_channel(Config.ADMIN_CHANNEL_ID)
            if not channel:
                channel = await self.fetch_channel(Config.ADMIN_CHANNEL_ID)
            await channel.send(message)
        except Exception as e:
            print(f"Failed to report error to admin channel: {e}")


bot = ThreadsBot()

# ---------------------------------------------------------------------------
# Autocomplete helpers
# ---------------------------------------------------------------------------

async def autocomplete_username(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Suggest usernames from this channel's subscriptions."""
    subs = db.list_subscriptions(interaction.channel_id)
    choices = []
    seen = set()
    for sub in subs:
        u = sub["username"]
        if u in seen:
            continue
        seen.add(u)
        display = db.get_display_name(u)
        label = f"{display} (@{u})"
        if current.lower() in u.lower() or current.lower() in display.lower():
            choices.append(app_commands.Choice(name=label, value=u))
    return choices[:25]


async def autocomplete_message(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Suggest message templates from config."""
    return [
        app_commands.Choice(name=t, value=t)
        for t in Config.NOTIFICATION_MESSAGE_TEMPLATES
        if current.lower() in t.lower()
    ][:25]


# ---------------------------------------------------------------------------
# Slash Commands
# ---------------------------------------------------------------------------

@bot.tree.command(name="subscribe", description="Subscribe to a Threads profile for the current channel.")
@app_commands.default_permissions()
@app_commands.describe(
    username="The Threads username to subscribe to (e.g. c910335)",
    message="Notification message template (supports {name}, {url}, {mention})",
    mention="The role or user to notify when a new post is found",
    overwrite="Overwrite the existing subscription if one already exists (default: False)",
)
@app_commands.autocomplete(username=autocomplete_username, message=autocomplete_message)
async def subscribe(
    interaction: discord.Interaction,
    username: str,
    message: str,
    mention: discord.Role | discord.Member | None = None,
    overwrite: bool = False,
):
    log_interaction(interaction, username=username, message=message, mention=mention, overwrite=overwrite)
    channel_id = interaction.channel_id
    server_id = interaction.guild_id
    mention_str = mention.mention if mention else ""

    success = db.add_subscription(
        username=username,
        channel_id=channel_id,
        server_id=server_id,
        message=message,
        mention=mention_str,
        overwrite=overwrite,
    )

    if success:
        display_name = db.get_display_name(username) or username
        mention_desc = f" and will ping {mention_str}" if mention_str else ""
        await interaction.response.send_message(
            f"I will send notifications to <#{channel_id}> with the message "
            f"(`{message}`){mention_desc} when **{display_name}** (@{username}) posts.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            f"Already subscribed to @{username} in this channel. "
            f"Pass `overwrite: True` to update the configuration.",
            ephemeral=True,
        )


@bot.tree.command(name="unsubscribe", description="Unsubscribe from a Threads profile for the current channel.")
@app_commands.default_permissions()
@app_commands.describe(username="The Threads username to unsubscribe from")
@app_commands.autocomplete(username=autocomplete_username)
async def unsubscribe(interaction: discord.Interaction, username: str):
    log_interaction(interaction, username=username)
    success = db.remove_subscription(username, interaction.channel_id)

    if success:
        await interaction.response.send_message(
            f"Unsubscribed from @{username} in this channel.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"No active subscription found for @{username} in this channel.", ephemeral=True
        )


@bot.tree.command(name="list", description="List all Threads subscriptions active in the current channel.")
@app_commands.default_permissions()
async def list_subs(interaction: discord.Interaction):
    log_interaction(interaction)
    subs = db.list_subscriptions(interaction.channel_id)

    if not subs:
        await interaction.response.send_message("No active subscriptions in this channel.", ephemeral=True)
        return

    lines = ["**Active Subscriptions for this Channel:**"]
    for idx, sub in enumerate(subs):
        display_name = db.get_display_name(sub["username"])
        mention_desc = f" — pings {sub['mention']}" if sub["mention"] else ""
        lines.append(
            f"{idx + 1}. **{display_name}** (@{sub['username']}){mention_desc}: `{sub['message']}`"
        )

    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@bot.tree.command(name="test", description="Trigger a test notification for a subscribed Threads profile.")
@app_commands.default_permissions()
@app_commands.describe(
    username="The Threads username to test",
    silent="If true, the test notification will be visible only to you",
)
@app_commands.autocomplete(username=autocomplete_username)
async def test_notify(
    interaction: discord.Interaction, username: str, silent: bool
):
    log_interaction(interaction, username=username, silent=silent)
    await interaction.response.defer(ephemeral=silent)
    username = username.strip().lower()

    subs = db.get_subscriptions_for_user(username)
    # Filter to subscriptions in this channel
    channel_subs = [s for s in subs if s["channel_id"] == interaction.channel_id]

    if not channel_subs:
        await interaction.followup.send(
            f"No subscription for @{username} in this channel.", ephemeral=silent
        )
        return

    try:
        posts = await scrape_user_posts(username)
        if not posts:
            await interaction.followup.send(
                f"No posts found for @{username} or profile was not accessible.", ephemeral=silent
            )
            return

        latest_post = posts[0]
        display_name = latest_post.get("display_name") or db.get_display_name(username)
        db.update_display_name(username, display_name)

        sub = channel_subs[0]
        payload = format_notification(sub, latest_post, display_name)

        print(
            f"Trigger a test notification for {display_name} (@{username}) "
            f"to {interaction.channel_id}:{interaction.guild_id}"
        )
        await interaction.followup.send(payload, ephemeral=silent)

    except Exception:
        error_trace = traceback.format_exc()
        await interaction.followup.send(
            f"**Test Failed for @{username}!**\n"
            f"Error details:\n```\n{error_trace[:1800]}\n```",
            ephemeral=silent,
        )
