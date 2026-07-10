#!.venv/bin/python
import sys
from config import Config
from bot import bot

def main():
    sys.stdout.reconfigure(line_buffering=True)
    token = Config.DISCORD_TOKEN
    if not token or token == "YOUR_DISCORD_TOKEN_HERE":
        print("ERROR: DISCORD_TOKEN is not set in the environment or config.py.", file=sys.stderr)
        print("Please configure DISCORD_TOKEN before starting the bot.", file=sys.stderr)
        sys.exit(1)
        
    print("Starting Threads Notification Discord Bot...")
    try:
        bot.run(token)
    except Exception as e:
        print(f"Error running bot: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
