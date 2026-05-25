import logging
import os

import discord
from aiohttp import web

logger = logging.getLogger(__name__)

PORT = int(os.getenv("BOT_NOTIFY_PORT", "8766"))


async def _handle_notify(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid JSON"}, status=400)

    title = data.get("title", "Série inconnue")
    url = data.get("url", "")
    app_url = data.get("app_url", "")
    new_count = data.get("new_count", 0)
    total = data.get("total", 0)
    poster_url = data.get("poster_url")

    bot: discord.Client = request.app["bot"]

    # Lu à la demande pour être sûr que load_dotenv a été appelé avant
    channel_id = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
    channel = bot.get_channel(channel_id)
    if channel is None:
        logger.warning("DISCORD_CHANNEL_ID %d not found or bot not ready", channel_id)
        return web.json_response({"error": "channel not found"}, status=503)

    kwargs: dict = {
        "title": f"Nouveaux épisodes — {title}",
        "description": f"**{new_count}** nouvel(s) épisode(s) disponible(s) ({total} au total)",
        "color": 0xA7D129,
    }
    if url:
        kwargs["url"] = url

    embed = discord.Embed(**kwargs)
    if poster_url:
        embed.set_thumbnail(url=poster_url)

    view = None
    if url or app_url:
        view = discord.ui.View()
        if url:
            view.add_item(discord.ui.Button(label="Voir la série", url=url, style=discord.ButtonStyle.link))
        if app_url:
            view.add_item(discord.ui.Button(label="Télécharger dans l'app", url=app_url, style=discord.ButtonStyle.link))

    await channel.send(embed=embed, view=view)
    return web.json_response({"ok": True})


def create_notify_app(bot: discord.Client) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_post("/notify", _handle_notify)
    return app


async def start_notify_server(bot: discord.Client) -> web.AppRunner:
    app = create_notify_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info("Notify server listening on port %d", PORT)
    return runner
