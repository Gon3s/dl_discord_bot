import asyncio
import logging
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from client import BackendClient
from cogs.download import DownloadCog
from cogs.search import SearchCog
from notify_server import start_notify_server

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

TOKEN = os.getenv("DISCORD_TOKEN", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent / "bot.log"),
    ],
)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not TOKEN:
        logger.error("DISCORD_TOKEN non défini dans .env")
        sys.exit(1)

    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix="!", intents=intents)
    backend = BackendClient(BACKEND_URL)

    await bot.add_cog(SearchCog(bot, backend))
    await bot.add_cog(DownloadCog(bot, backend))

    @bot.event
    async def on_ready() -> None:
        logger.info("Bot connecté en tant que %s", bot.user)

    notify_runner = await start_notify_server(bot)
    try:
        await bot.start(TOKEN)
    finally:
        await notify_runner.cleanup()
        await backend.close()


if __name__ == "__main__":
    asyncio.run(main())
