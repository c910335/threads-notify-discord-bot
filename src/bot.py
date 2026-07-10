"""Main Discord Bot client setup and extension loader."""

import discord
from discord.ext import commands


class ThreadsBot(commands.Bot):
    """Subclassed commands.Bot to load configuration and cogs."""

    def __init__(self) -> None:
        """Initializes the bot client with default intents."""
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        """Loads all extension cogs and syncs slash commands globally."""
        await self.load_extension("cogs.threads_commands")
        await self.load_extension("cogs.monitor")
        await self.tree.sync()
        print("Slash commands synced globally.")

    async def on_ready(self) -> None:
        """Handles bot ready event."""
        print(f"Logged in as {self.user} (ID: {self.user.id})")
