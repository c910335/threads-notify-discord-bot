# Threads Notify Discord Bot

A Discord bot for [Threads](https://www.threads.com) profile post notifications.

## Installation

1. Create an application on the [Discord Developer Portal](https://discord.com/developers/applications/) with the following configuration.

- Installation:
  - Default Install Settings:
    - Guild Install
      - Scopes: `bot`
      - Permissions: `Send Messages`

2. Clone this repository.

```sh
git clone https://github.com/c910335/threads-notify-discord-bot.git
cd threads-notify-discord-bot
```

3. Initialize virtual environment and install dependencies.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Note: If you are running on Linux (e.g. Arch Linux), you may need to install additional system dependencies required by Chromium:
```sh
sudo pacman -S --needed nspr nss atk at-spi2-core libxcomposite libxdamage libxrandr libxkbcommon
```

4. Edit the configuration file.

```sh
cp src/config_sample.py src/config.py
# Set your DISCORD_TOKEN and ADMIN_CHANNEL_ID in src/config.py
```

## Usage

1. Run the bot.

```sh
.venv/bin/python src/main.py
```

2. Invite the bot to your server using the installation link generated from the [Discord Developer Portal](https://discord.com/developers/applications/).

3. Use the slash commands in your server.

## Testing

Run the unit test suite:

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p "*_test.py" -t .
```

## Commands

All commands are restricted to server administrators.

- `/subscribe`: Subscribe to a Threads user profile for the current channel.
  - `username` (String): The username of the Threads profile (e.g. `c910335`).
  - `message` (String): The message template to send when the user posts (supports `{name}`, `{text}`, `{url}`, `{mention}`, autocomplete templates available).
  - `mention` (Mentionable, Optional): The user or role to notify.
  - `overwrite` (Boolean, Optional): Whether to overwrite an existing subscription (defaults to `False`).
- `/unsubscribe`: Unsubscribe from a Threads profile for the current channel.
  - `username` (String): The Threads username to unsubscribe from.
- `/test`: Trigger a test notification to the current channel.
  - `username` (String): The Threads username to send a test notification for.
  - `silent` (Boolean): If true, the test notification will be visible only to you (ephemeral).
- `/list`: List the active subscriptions for the current channel (only visible to the command caller).

## Contributing

1. Fork it (<https://github.com/c910335/threads-notify-discord-bot/fork>)
2. Create your feature branch (`git checkout -b my-new-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Push to the branch (`git push origin my-new-feature`)
5. Create a new Pull Request

## Contributors

- [Tatsujin Chin](https://github.com/c910335) - creator and maintainer
