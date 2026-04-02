import logging

import discord
from discord.ext import commands

from client import BackendClient, BackendError

logger = logging.getLogger(__name__)

_VALID_MEDIA_TYPES = ["movie", "serie", "manga"]
_STATUS_COLORS = {
    "pending": discord.Color.light_grey(),
    "downloading": discord.Color.blue(),
    "done": discord.Color.green(),
    "error": discord.Color.red(),
    "cancelled": discord.Color.orange(),
}


class DownloadCog(commands.Cog):
    def __init__(self, bot: commands.Bot, backend: BackendClient) -> None:
        self.bot = bot
        self.backend = backend

    @commands.command(name="url", help="Télécharge une URL: !url <url> <media_type>  (movie|serie|manga)")
    async def url(
        self,
        ctx: commands.Context,
        url: str | None = None,
        media_type: str | None = None,
    ) -> None:
        if url is None:
            await ctx.send("URL invalide.")
            return

        if media_type is None or media_type not in _VALID_MEDIA_TYPES:
            embed = discord.Embed(
                title="Type de média invalide",
                description="Types disponibles: `movie`, `serie`, `manga`\nEx: `!url https://... movie`",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

        logger.info("%s enqueue download: %s (%s)", ctx.author, url[:80], media_type)

        try:
            result = await self.backend.create_download(
                source_url=url,
                title=url,
                media_type=media_type,
                destination="server",
            )
        except BackendError as exc:
            logger.error("url backend error: %s", exc)
            await ctx.send(f"Erreur backend ({exc.status}): impossible d'enqueue le téléchargement.")
            return

        embed = discord.Embed(
            title="Téléchargement enqueued",
            color=discord.Color.green(),
        )
        embed.add_field(name="ID", value=f"`{result['download_id']}`", inline=False)
        embed.add_field(name="Statut", value=result["status"], inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="status", help="Affiche la file de téléchargement et le statut du serveur")
    async def status(self, ctx: commands.Context) -> None:
        try:
            status_data = await self.backend.get_status()
            downloads = await self.backend.get_downloads()
        except BackendError as exc:
            logger.error("status backend error: %s", exc)
            await ctx.send(f"Erreur backend ({exc.status}): impossible de récupérer le statut.")
            return

        alldebrid_icon = "✅" if status_data.get("alldebrid_ok") else "❌"

        embed = discord.Embed(title="Statut du serveur", color=discord.Color.blurple())
        embed.add_field(name="AllDebrid", value=alldebrid_icon, inline=True)
        embed.add_field(name="File", value=str(status_data.get("queue_size", 0)), inline=True)
        embed.add_field(name="Actifs", value=str(status_data.get("active", 0)), inline=True)
        embed.add_field(name="Disque libre", value=f"{status_data.get('disk_free_gb', 0):.1f} Go", inline=True)

        if downloads:
            lines = []
            for dl in downloads[:10]:
                pct = dl.get("progress_pct", 0)
                bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                lines.append(f"`{bar}` {pct:.0f}% — {dl.get('title', dl['id'])[:40]} [{dl['status']}]")
            embed.add_field(name="Téléchargements actifs", value="\n".join(lines), inline=False)

        await ctx.send(embed=embed)
