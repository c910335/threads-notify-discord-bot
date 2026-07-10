import os

class Config:
    # Discord Bot Token
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_DISCORD_TOKEN_HERE")
    
    # Discord channel ID to report bot errors to (admin channel)
    ADMIN_CHANNEL_ID = int(os.getenv("ADMIN_CHANNEL_ID", "0"))
    
    # How often to check for updates (in seconds)
    HEARTBEAT_DELAY_SECONDS = int(os.getenv("HEARTBEAT_DELAY_SECONDS", "300"))
    
    # Cooldown sleep between checking individual targets (in seconds)
    CHECK_DELAY_SECONDS = int(os.getenv("CHECK_DELAY_SECONDS", "5"))

    # Predefined message templates offered as autocomplete choices for /subscribe
    NOTIFICATION_MESSAGE_TEMPLATES = [
        "{mention} {name} 有新貼文！",
    ]
