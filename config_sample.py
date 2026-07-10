"""Configuration settings template for the Threads Notification Discord Bot.

Rename this file to `config.py` and populate your secrets.
"""

import os

# Discord Bot Token (e.g., "MTEyMjMzNDQ1NTY2...XXXXXX...YYYYYY...")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_DISCORD_TOKEN_HERE")

# Discord channel ID to report bot errors to (e.g., 123456789012345678)
ADMIN_CHANNEL_ID = int(os.getenv("ADMIN_CHANNEL_ID", "0"))

# How often to check for updates (in seconds)
HEARTBEAT_DELAY_SECONDS = int(os.getenv("HEARTBEAT_DELAY_SECONDS", "300"))

# Cooldown sleep between checking individual targets (in seconds)
CHECK_DELAY_SECONDS = int(os.getenv("CHECK_DELAY_SECONDS", "5"))

# Predefined message templates offered as autocomplete choices for /subscribe
NOTIFICATION_MESSAGE_TEMPLATES = [
    "{mention} {name} 有新貼文！",
    "{mention} {name} 發文囉！",
    "{name} 發布了新貼文： {url}",
    "{name} posted a new update: {url}",
    "{mention} {name} 發布了新貼文： {url}",
]
