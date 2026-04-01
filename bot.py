import os
import logging
import alldebrid
import discord
from discord.ext import commands
from dotenv import load_dotenv
import aiohttp
import asyncio
from slugify import slugify
from bs4 import BeautifulSoup
import re
import csv

from parser import Parser

# Configuration logging structuré
import sys
from pathlib import Path

log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

# Formatter commun
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Handler fichier INFO
file_handler = logging.FileHandler(log_dir / 'bot.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Handler fichier ERRORS
error_handler = logging.FileHandler(log_dir / 'errors.log')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)

# Handler console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Logger principal
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(error_handler)
logger.addHandler(console_handler)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DOWNLOAD_PATH = os.getenv('DOWNLOAD_PATH')
WAWACITY_URL = os.getenv('WAWACITY_URL')
SELECT_PROVIDER = '1fichier'
PROVIDERS = ['DailyUploads', '1fichier', 'Turbobit', 'Rapidgator']

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
histories = []




def create_embed(item, index, count):
    """
    Crée un embed Discord pour afficher un résultat de recherche.
    
    Args:
        item (dict): Dictionnaire contenant {title, image, year, quality, language}
        index (int): Index du résultat (pour pagination)
        count (int): Nombre total de résultats
    
    Returns:
        discord.Embed: Embed formaté prêt à envoyer
    
    Note:
        Affiche en pied de page : "Page X/Y"
    """
    embed = discord.Embed(color=0x0099ff, title=item["title"], )
    
    embed.set_image(url=item["image"])
    
    embed.add_field(name='Année', value=item['year'], inline=True)
    embed.add_field(name='Qualité', value=item['quality'], inline=True)
    embed.add_field(name='Langue', value=item['language'], inline=True)
    
    embed.set_footer(text=f'Page {index + 1}/{count}')
    
    return embed


async def download_by_url(url, type):
    """
    Télécharge un fichier via AllDebrid et l'enregistre localement.
    
    Args:
        url (str): URL protégée à débrier
        type (str): Type de contenu ('movie' ou 'serie')
    
    Returns:
        str: Nom du fichier téléchargé (ou False en cas d'erreur)
    
    Raises:
        AssertionError: En cas d'erreur AllDebrid
    
    Process:
        1. Débridage du lien via AllDebrid API
        2. Renaming (espaces → points)
        3. Organisation en dossiers (Movies/Shows/Saison)
        4. Pour séries: extraction titre/saison via regex
        5. Téléchargement asynchrone du fichier
    
    TODO:
        - Ajouter vérification d'espace disque
        - Implémenter resume de téléchargement
        - Meilleure gestion des timeouts (configurable)
        - Logging structuré (pas de print)
    """
    alldebrid_client = alldebrid.AllDebrid()
    
    try:
        data = alldebrid_client.debrid_link(url)
    except AssertionError as e:
        print(f'Error #DBU1: {e}')
        return False
    
    filename = data['filename']
    if not filename:
        print(f'Error: No filename')
        return False
    
    filename = filename.replace(' ', '.')
    
    print(f'Debrid {filename} / {data["link"]}')
    
    if type == 'movie':
        path = os.path.join(DOWNLOAD_PATH, 'Movies')
    elif type == 'serie':
        path = os.path.join(DOWNLOAD_PATH, 'Shows')
        regex_series = r"(.*).(S[0-9]{1,2})(E[0-9]{1,4}).*(\.[a-z0-9]*)"
        matches = re.match(regex_series, filename)
        if matches:
            matches = matches.groups()
            if len(matches) == 4:
                folder = matches[0].replace('.', ' ')
                season = f"{folder} - {matches[1]}"
                path = os.path.join(path, folder)
                if not os.path.exists(path):
                    os.makedirs(path)
                path = os.path.join(path, season)
                if not os.path.exists(path):
                    os.makedirs(path)
                filename = f"{matches[0]}-{matches[1]}{matches[2]}{matches[3]}"
    else:
        print(f'Error: Invalid type')
        return False
    
    async with aiohttp.ClientSession() as session:
        async with session.get(data['link']) as resp:
            if resp.status != 200:
                print(f'Error: {resp.status}')
                return False
            
            print(path, filename)
            with open(os.path.join(path, filename), 'wb') as f:
                while True:
                    chunk = await resp.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)
    return filename


def match_language(source_language):
    """
    Convertit un code de langue en emoji drapeau Discord.
    
    Args:
        source_language (str): Classe CSS comme 'flag-fr', 'flag-en', etc.
    
    Returns:
        str: Emoji drapeau correspondant
    
    Mapping:
        FR → 🇫🇷 (Français)
        EN → 🇬🇧 (Anglais)
        VOSTFR → 🇬🇧🇫🇷 (Version originale)
        MULTI → 🇪🇺 (Multilingue)
        Autre → 🌐 (Inconnu)
    """
    language = source_language.replace('flag-', '').upper()
    
    match language:
        case 'FR':
            language = '🇫🇷'
        case 'EN':
            language = '🇬🇧'
        case 'VOSTFR':
            language = '🇬🇧🇫🇷'
        case 'MULTI':
            language = '🇪🇺'
        case _:
            language = '🌐'
    
    return language


def get_results(data, max_results):
    """
    Parse les résultats HTML de Wawacity.
    
    Args:
        data (bytes): Contenu HTML brut
        max_results (int): Nombre maximum de résultats à retourner
    
    Returns:
        list: Liste de dictionnaires {title, quality, year, language, image, url}
    
    Parsing Details:
        - Extraction via BeautifulSoup des divs 'wa-post-detail-item'
        - Regex pour séparer titre et qualité (format: "Title [QUALITY]")
        - Construction des URLs complètes (ajout de WAWACITY_URL)
        - Conversion des flags de langue en emojis
    
    NOTE:
        HTML-dependent - breakable en cas de changement de structure du site
    """
    amount = 0
    pattern = re.compile(r'^(.*?)\s\[(.*?)\]')
    results = []
    
    soup = BeautifulSoup(data, 'html.parser')
    
    for element in soup.find_all('div', class_='wa-post-detail-item'):
        if amount >= max_results:
            break
        
        post_title = element.find('div', class_='wa-sub-block-title')
        
        title = post_title.find('a').text
        match = pattern.match(title)
        quality = None
        image = element.find('img')['src']
        
        if match:
            title = match.group(1).strip()
            quality = match.group(2).strip()
        
        url = post_title.find('a').get("href")
        year = post_title.parent.parent.find('span', string="Année:").find_next_sibling('b').text
        
        language = match_language(post_title.find('i').get('class')[1])
        
        amount += 1
        
        results.append(
            {'title': title, 'quality': quality, 'year': year, 'language': language, 'image': f'{WAWACITY_URL}{image}',
             'url':   f'{WAWACITY_URL}{url}'})
    
    return results


async def search_wawacity(ctx, query, category, year):
    """
    Recherche du contenu sur Wawacity via requête HTTP.
    
    Args:
        ctx: Contexte Discord
        query (str): Terme de recherche (titre du film/série)
        category (str): 'films', 'series', ou 'mangas'
        year (int or None): Année de sortie (optionnel)
    
    Returns:
        bytes: Contenu HTML brut ou False si erreur
    
    Parameters:
        - search: requête utilisateur
        - p: catégorie (films/series/mangas)
        - year: année de sortie
        - s: sorting (tri par qualité)
          - films: 'blu-ray_1080p-720p'
          - autres: 'vostfr-hq'
    
    URL Status Codes:
        200 OK → retourne le contenu
        Autre → envoie message d'erreur Discord
    """
    params = {}
    params['search'] = query
    params['p'] = category
    if year is not None:
        params['year'] = year
    
    if category == 'films':
        params['s'] = 'blu-ray_1080p-720p'
    else:
        params['s'] = 'vostfr-hq'
    
    async with (aiohttp.ClientSession() as session):
        async with session.get(WAWACITY_URL, params=params) as resp:
            if resp.status != 200:
                await ctx.send(f'Error: {resp.status}')
                return False
            
            await ctx.send(f"Try to parse : {resp.real_url}")
            data = await resp.content.read()
            
            return data


def is_already_downloaded(url):
    """
    Vérifie si une URL a déjà été téléchargée.
    
    Args:
        url (str): URL à vérifier
    
    Returns:
        bool: True si déjà dans l'historique, False sinon
    
    NOTE:
        Implémentation inefficace - O(n)
        TODO: Utiliser set ou dictionnaire pour O(1)
    """
    for history in histories:
        if history['url'] == url:
            return True
    return False


async def download_url_selected(ctx, url_selected, folder, providers_list=None):
    if providers_list is None:
        providers_list = PROVIDERS

    logger.info(f'URL selectionnee: {url_selected}')
    await ctx.send(f'URL: {url_selected[:100]}...')

    parser = Parser(show_logs=True)

    if folder == 'serie':
        # ── SÉRIES : grouper par épisode, fallback provider par épisode ──
        main_title, episodes = parser.get_all_episodes_links(url_selected)

        if not episodes:
            await ctx.send('Aucun épisode trouvé sur la page.')
            return

        await ctx.send(f'{main_title} — {len(episodes)} épisode(s) trouvé(s)')

        for episode_name, provider_links in episodes.items():
            await ctx.send(f'⬇Épisode: {episode_name}')

            if is_already_downloaded(episode_name):
                await ctx.send(f'⏭ Déjà téléchargé, skip')
                continue

            downloaded = False
            for provider in providers_list:
                if provider not in provider_links:
                    continue

                dl_protect_url = provider_links[provider]
                logger.info(f'Essai {provider} pour {episode_name}')
                await ctx.send(f'Essai provider: {provider}')

                try:
                    real_url = parser.dl_protect(dl_protect_url)
                    filename = await download_by_url(real_url, folder)

                    if filename:
                        histories.append({'title': filename, 'url': episode_name})
                        _write_history_csv(histories)
                        await ctx.send(f'✅ {filename} — OK ({provider})')
                        downloaded = True
                        break  # ← épisode OK, on passe au suivant
                    else:
                        await ctx.send(f'Échec {provider}, essai suivant...')

                except Exception as e:
                    logger.error(f'Erreur {provider} / {episode_name}: {e}', exc_info=True)
                    await ctx.send(f'Erreur {provider}: {str(e)[:100]}, essai suivant...')

            if not downloaded:
                await ctx.send(f'💀 Aucun provider n\'a fonctionné pour {episode_name}')

    else:
        # ── FILMS : essai provider par provider, stop au premier qui marche ──
        for provider in providers_list:
            await ctx.send(f'Trying provider: {provider}')

            try:
                parser.select_provider = provider
                main_title, urls = parser.get_dl_protect_url(url_selected)

                if not urls:
                    await ctx.send(f'No links found with {provider}')
                    continue

                await ctx.send(f'Found {len(urls)} link(s) with {provider}')

                for url in urls:
                    if is_already_downloaded(url):
                        await ctx.send(f'⏭️ Déjà téléchargé, skip')
                        continue

                    try:
                        filename = await download_by_url(url, folder)
                        if filename:
                            histories.append({'title': filename, 'url': url})
                            _write_history_csv(histories)
                            await ctx.send(f'✅ {filename} — OK ({provider})')
                            return  # ← film OK, on s'arrête
                        else:
                            await ctx.send(f'❌ Échec {provider}, essai suivant...')
                    except Exception as e:
                        logger.error(f'Exception: {e}', exc_info=True)
                        await ctx.send(f'❌ Erreur: {str(e)[:100]}')

            except Exception as e:
                logger.error(f'Erreur provider {provider}: {e}', exc_info=True)
                await ctx.send(f'Erreur avec {provider}: {str(e)[:100]}')

        await ctx.send('❌ Aucun provider n\'a fonctionné pour ce film.')

@bot.command(name='url', help='Download a file by url')
async def url(ctx, url=None, folder=None):
    """
    Commande: !url <url> <folder>
    
    Télécharge un contenu via URL Wawacity directe.
    
    Params:
        url (str): URL du contenu sur Wawacity
        folder (str): 'movie' ou 'serie'
    
    Example:
        !url https://wawacity.sc/... movie
    
    Validation:
        ✓ URL non None
        ✓ folder in ['movie', 'serie']
    
    BUG CRITIQUE À FIXER:
        Ligne actuelle: if folder is None and folder not in ['movie', 'serie']
        Devrait être:   if folder is None or folder not in ['movie', 'serie']
    """
    # BUGFIX: Correction "and" -> "or"
    if url is None:
        logger.error(f'{ctx.author}: URL invalide')
        await ctx.send('URL invalide')
        return
    
    if folder is None or folder not in ['movie', 'serie']:
        logger.error(f'{ctx.author}: Dossier invalide: {folder}')
        embed = discord.Embed(
            title='Dossier Invalide',
            description='Utilise: `!url <url> movie` ou `!url <url> serie`',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    logger.info(f'{ctx.author} telecharge: {url[:50]}... ({folder})')
    await download_url_selected(ctx, url, folder, PROVIDERS)


@bot.command(name='search', help='Search a series, films or manga')
async def search(ctx, query=None, category=None, year=None, count=3):
    """
    Commande: !search <query> <category> [year] [count]
    
    Recherche du contenu sur Wawacity et affiche résultats avec réactions.
    
    Params:
        query (str): Terme de recherche (titre)
        category (str): 'films', 'series', ou 'mangas'
        year (int): Année de sortie (optionnel)
        count (int): Nombre de résultats (défaut: 3)
    
    Example:
        !search "Dragon Ball" series
        !search "Inception" films 2010 5
    
    Flow Interactif:
        1. Recherche et affichage 1 embed par résultat
        2. Ajout réactions numéros (1️⃣-9️⃣🔟)
        3. Attente réaction utilisateur (timeout: 30s)
        4. Sélection → téléchargement auto
    
    Validation:
        ✓ query non None
        ✓ category in ['films', 'series', 'mangas']
    
    BUG CRITIQUE À FIXER:
        Même problème "and" au lieu de "or" 
        - Ligne query: if query is None and query not in [...]
        - Ligne category: if category is None and category not in [...]
    
    TODO:
        - Meilleure gestion timeout (utilisateur informé)
        - Pagination si count > 10 (limite emojis disponibles)
    """
    
    # BUGFIX: Correction "and" -> "or" pour query
    if query is None:
        logger.error(f'{ctx.author}: Requete vide')
        await ctx.send('Erreur: Requete vide')
        return
    
    # BUGFIX: Correction "and" -> "or" pour category
    if category is None or category not in ['films', 'series', 'mangas']:
        logger.error(f'{ctx.author}: Categorie invalide: {category}')
        embed = discord.Embed(
            title='Categorie Invalide',
            description='Categories disponibles: `films`, `series`, `mangas`\nEx: `!search Dragon Ball series`',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Validation du nombre de resultats
    if count > 10:
        logger.warning(f'{ctx.author}: count trop eleve ({count}), limite a 10')
        count = 10
        await ctx.send('Nombre de resultats limite a 10 (maximum d\'emojis)')
    
    logger.info(f'{ctx.author} recherche: {query} ({category}, {count} resultats)')
    
    data = await search_wawacity(ctx, query, category, year)
    
    if not data:
        await ctx.send('Error: No results found')
        return
    
    results = get_results(data, count)
    
    if not results:
        await ctx.send('Error: No results found')
        return
    
    # Create embeds message
    count = len(results)
    result_message = None
    for index, result in enumerate(results):
        result_message = await ctx.send(embed=create_embed(result, index, count))
    
    if result_message is None:
        await ctx.send('Error: No messages created')
        return
    
    # Add reactions
    for i in range(len(results)):
        await result_message.add_reaction(numbers[i])
    
    def check(r, u):
        return u == ctx.message.author and str(r.emoji) in numbers
    
    # Wait for reaction
    to_download = None
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
        await result_message.remove_reaction(reaction.emoji, user)
    except asyncio.TimeoutError:
        await ctx.send('Error: No reaction')
    else:
        selected_option = numbers.index(reaction.emoji) + 1
        to_download = results[selected_option - 1]
    finally:
        await result_message.delete()
    
    # if download selected
    if to_download is not None:
        await ctx.send(f'You selected: {to_download["title"]}')
        
        url = to_download['url']
        folder = 'movie' if category == 'films' else 'serie'
        
        await download_url_selected(ctx, url, folder, PROVIDERS)
    else:
        await ctx.send('Error: No selection')


_HISTORY_CSV = Path('history.csv')
_HISTORY_FIELDNAMES = ['title', 'url']


def _read_history_csv() -> list[dict]:
    if not _HISTORY_CSV.exists():
        return []
    with _HISTORY_CSV.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _write_history_csv(histories: list[dict]) -> None:
    with _HISTORY_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=_HISTORY_FIELDNAMES)
        writer.writeheader()
        writer.writerows(histories)


if __name__ == '__main__':
    """
    Point d'entrée du bot Discord.
    
    Process:
        1. Charge l'historique depuis history.csv
        2. Remplit la liste globale histories
        3. Lance le bot avec le token Discord
    
    Environment Variables Requises:
        - DISCORD_TOKEN: Token d'authentification Discord
        - DOWNLOAD_PATH: Chemin racine des téléchargements
        - WAWACITY_URL: URL de base Wawacity (avec /)
    
    TODO:
        - Valider l'existence du fichier history.csv
        - Gérer cas où le fichier est corrompu
        - Implémenter reconnexion automatique
    """
    histories = _read_history_csv()
    
    bot.run(TOKEN)
