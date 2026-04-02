import asyncio
import logging

import discord
from discord.ext import commands

from client import BackendClient, BackendError

logger = logging.getLogger(__name__)

_NUMBERS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
_VALID_CATEGORIES = ["films", "series", "mangas"]
_CATEGORY_TO_MEDIA_TYPE = {"films": "movie", "series": "serie", "mangas": "manga"}


def _build_embed(result: dict, index: int, total: int) -> discord.Embed:
    embed = discord.Embed(color=0x0099FF, title=result["title"])
    if result.get("poster_url"):
        embed.set_image(url=result["poster_url"])
    embed.add_field(name="Année", value=result.get("year") or "—", inline=True)
    embed.add_field(name="Qualité", value=result.get("quality") or "—", inline=True)
    embed.add_field(name="Langue", value=result.get("language") or "—", inline=True)
    embed.set_footer(text=f"Page {index + 1}/{total}")
    return embed


class SearchCog(commands.Cog):
    def __init__(self, bot: commands.Bot, backend: BackendClient) -> None:
        self.bot = bot
        self.backend = backend

    @commands.command(name="search", help="Recherche: !search <query> <category> [year] [count=3]")
    async def search(
        self,
        ctx: commands.Context,
        query: str | None = None,
        category: str | None = None,
        year: int | None = None,
        count: int = 3,
    ) -> None:
        if query is None:
            await ctx.send("Erreur: requête vide")
            return

        if category is None or category not in _VALID_CATEGORIES:
            embed = discord.Embed(
                title="Catégorie invalide",
                description="Catégories disponibles: `films`, `series`, `mangas`\nEx: `!search Dragon Ball series`",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

        count = min(count, 10)

        try:
            response = await self.backend.search(query, category=category, year=year, limit=count)
        except BackendError as exc:
            logger.error("search backend error: %s", exc)
            await ctx.send(f"Erreur backend ({exc.status}): impossible d'effectuer la recherche.")
            return

        results = response.get("results", [])
        if not results:
            await ctx.send("Aucun résultat trouvé.")
            return

        # Send one embed per result; only the last one gets reactions
        last_msg: discord.Message | None = None
        for i, result in enumerate(results):
            last_msg = await ctx.send(embed=_build_embed(result, i, len(results)))

        if last_msg is None:
            return

        for i in range(len(results)):
            await last_msg.add_reaction(_NUMBERS[i])

        def check(r: discord.Reaction, u: discord.User) -> bool:
            return u == ctx.message.author and str(r.emoji) in _NUMBERS

        selected = None
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            await last_msg.remove_reaction(reaction.emoji, ctx.message.author)
            selected = results[_NUMBERS.index(str(reaction.emoji))]
        except asyncio.TimeoutError:
            await ctx.send("Temps écoulé — aucune sélection.")
        finally:
            await last_msg.delete()

        if selected is None:
            return

        await ctx.send(f"Sélectionné : **{selected['title']}**")

        media_type = _CATEGORY_TO_MEDIA_TYPE[category]
        try:
            result = await self.backend.create_download(
                source_url=selected["url"],
                title=selected["title"],
                media_type=media_type,
                destination="server",
            )
            await ctx.send(f"✅ Téléchargement enqueued — ID `{result['download_id']}` (statut: {result['status']})")
        except BackendError as exc:
            logger.error("create_download backend error: %s", exc)
            await ctx.send(f"Erreur lors de la mise en file ({exc.status}).")
