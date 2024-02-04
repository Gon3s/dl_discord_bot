import os

import alldebrid

import discord
from discord.ext import commands
from dotenv import load_dotenv
import aiohttp
import asyncio
from slugify import slugify
from bs4 import BeautifulSoup
import re

import yt_dlp

from parser import Parser

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DOWNLOAD_PATH = os.getenv('DOWNLOAD_PATH')
WAWACITY_URL = os.getenv('WAWACITY_URL')
SELECT_PROVIDER = '1fichier'

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']


def create_embed(item, index, count):
    embed = discord.Embed(color=0x0099ff, title=item["title"], )
    
    embed.set_image(url=item["image"])
    
    embed.add_field(name='Année', value=item['year'], inline=True)
    embed.add_field(name='Qualité', value=item['quality'], inline=True)
    embed.add_field(name='Langue', value=item['language'], inline=True)
    
    embed.set_footer(text=f'Page {index + 1}/{count}')
    
    return embed


async def download_by_url(ctx, url, type):
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
    
    print(f'Debrid {filename} / {data["link"]}')
    
    if type == 'movie':
        path = os.path.join(DOWNLOAD_PATH, 'Movies')
    elif type == 'serie':
        path = os.path.join(DOWNLOAD_PATH, 'Shows')
        regex_series = r"(.*).(S[0-9]{1,2})(E[0-9]{1,2}).*(\.[a-z]*)"
        matches = re.match(regex_series, filename).groups()
        if matches:
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


@bot.command(name='music', help="Download a music file")
async def music(ctx, url):
    if not (url.startswith('https://')):
        await ctx.send('Invalid url')
        return
    
    with yt_dlp.YoutubeDL(
        {'extract_audio': True, 'format': 'bestaudio', 'outtmpl': '/home/gones/Musique/%(title)s.mp3'}) as video:
        info_dict = video.extract_info(url, download=True)
        video_title = info_dict['title']
        
        await ctx.send(f'You want to download: {url}')
        
        video.download(url)
        
        await ctx.send(f'Download finished')


@bot.command(name='download', help='Download a file')
async def download(ctx, url):
    if not (url.startswith('http://') or url.startswith('https://')):
        await ctx.send('Invalid url')
        return
    
    await ctx.send(f'You want to download: {url}')
    
    alldebrid_client = alldebrid.AllDebrid()
    try:
        data = alldebrid_client.debrid_link(url)
    except AssertionError as e:
        await ctx.send(f'Error: {e}')
        return
    
    filename = data['filename']
    
    async with aiohttp.ClientSession() as session:
        async with session.get(data['link']) as resp:
            if resp.status != 200:
                await ctx.send(f'Error: {resp.status}')
                return
            with open(os.path.join(DOWNLOAD_PATH, filename), 'wb') as f:
                while True:
                    chunk = await resp.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)
    
    await ctx.send(f'Download finished: {filename}')


@bot.command(name='series', help='Download all episodes of a series')
async def series(ctx, url):
    if not (url.startswith('http://') or url.startswith('https://')):
        await ctx.send('Invalid url')
        return
    
    await ctx.send(f'You want to download: {url}')
    
    parser = Parser()
    urls = parser.download_all_series(url)
    for url in urls:
        await download_by_url(ctx, url)


async def search_wawacity(ctx, query, category, year):
    if year is None:
        year = ''
        
    async with (aiohttp.ClientSession() as session):
        async with session.get(WAWACITY_URL, params={'search': query, 'p': category, 'year': year,
            's':                                               'blu-ray_1080p-720p'}) as resp:
            if resp.status != 200:
                await ctx.send(f'Error: {resp.status}')
                return False
            
            await ctx.send(f"Try to parse : {resp.real_url}")
            data = await resp.content.read()
            
            return data


def match_language(source_language):
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


@bot.command(name='search', help='Search a series, films or manga')
async def search(ctx, query=None, category=None, year=None, count=3, select_provider=SELECT_PROVIDER):
    if query is None:
        await ctx.send('Invalid query')
        return
    
    if category is None and category not in ['films', 'series', 'mangas']:
        await ctx.send('Invalid category')
        return
    
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
        
        await download_url_selected(ctx, url, folder, select_provider)
    else:
        await ctx.send('Error: No selection')


async def download_url_selected(ctx, url, folder, select_provider):
    parser = Parser(show_logs=True, select_provider=select_provider)
    
    title, urls = parser.get_dl_protect_url(url)
    if not urls:
        await ctx.send(f'Error: No link found')
        return
    
    await ctx.send(f'You want to download: {title}')
    
    loop = asyncio.get_event_loop()
    summary = []
    
    for url in urls:
        print(f'You want to find url from {url}')
        tries = 0
        dl_protect_url = None
        error = None
        while tries < 3 and not dl_protect_url:
            try:
                future = loop.run_in_executor(None, parser.dl_protect, url)
                dl_protect_url = await future
            except Exception as e:
                tries += 1
                print(f"Tries {tries}/3: {e}")
                future = loop.run_in_executor(None, parser.dl_protect, url)
                dl_protect_url = await future
        
        print(f"Tries {tries}/3 - {dl_protect_url}")
        if tries == 3 and not dl_protect_url:
            download_status = 'ERROR'
            error = 'Too many tries'
        else:
            if dl_protect_url:
                try:
                    print(f'You want to download: {dl_protect_url}')
                    title = await download_by_url(ctx, dl_protect_url, folder)
                    if title:
                        download_status = 'OK'
                    else:
                        download_status = 'ERROR'
                        error = 'Download error'
                except Exception as e:
                    download_status = 'ERROR'
                    error = e
            else:
                download_status = 'ERROR'
                error = 'No link found'
        
        await ctx.send(f"{title} - {download_status} - {error}")
        summary.append(
            {'title': title, 'url': url, 'dl_protect_url': dl_protect_url, 'download_status': download_status,
             'error': error})
    
    with open(f'summary/{slugify(title)}.txt', 'w') as f:
        for item in summary:
            f.write(
                f"URL: {item['url']}, DL Protect URL: {item['dl_protect_url']}, Download Status: {item['download_status']}")
    
    await ctx.send(f"Summary: {len(summary)} files downloaded")


if __name__ == '__main__':
    bot.run(TOKEN)
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(download_by_url(None, 'https://1fichier.com/?4nryvtblgf0n10z0hlkm&af=4814702', 'serie'))
