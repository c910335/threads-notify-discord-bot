"""Configuration settings for the Threads Notification Discord Bot."""

import os
import sys

import dotenv

# Load .env file (skip loading during unit tests to ensure isolation)
if "unittest" not in sys.modules:
    dotenv.load_dotenv()

# Discord Bot Token
DISCORD_TOKEN = os.getenv("TNDB_DISCORD_TOKEN", "YOUR_DISCORD_TOKEN_HERE")

# Discord channel ID to report bot errors to (admin channel)
ADMIN_CHANNEL_ID = int(os.getenv("TNDB_ADMIN_CHANNEL_ID", "0"))

# How often to check for updates (in seconds)
HEARTBEAT_DELAY_SECONDS = int(os.getenv("TNDB_HEARTBEAT_DELAY_SECONDS", "300"))

# Cooldown sleep between checking individual targets (in seconds)
CHECK_DELAY_SECONDS = int(os.getenv("TNDB_CHECK_DELAY_SECONDS", "5"))

# Predefined message templates offered as autocomplete choices for /subscribe
NOTIFICATION_MESSAGE_TEMPLATES = [
    "{mention} {name} 有新貼文！",
    "{name} 發文囉！",
    "{mention} {name} 發布了新貼文： {url}",
    "{mention} **{name}** 發文囉！{text}",
    "{mention} **{name}** 發文囉！{preview_text}",
    "**{name}**:{quoted_text}",
    "**{name}**:{quoted_preview_text}",
    "{text}",
]
