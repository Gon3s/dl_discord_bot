import os

import alldebrid

import discord
from discord.ext import commands
from dotenv import load_dotenv
import aiohttp
import asyncio
from slugify import slugify

import yt_dlp

from parser import Parser

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DOWNLOAD_PATH = os.getenv('DOWNLOAD_PATH')

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())


async def download_by_url(ctx, url, type):
    alldebrid_client = alldebrid.AllDebrid()
    try:
        data = alldebrid_client.debrid_link(url)
    except AssertionError as e:
        await ctx.send(f'Error: {e}')
        return False
    
    filename = data['filename']
    await ctx.send(f'Debrid {filename} / {data["link"]}')
    
    async with aiohttp.ClientSession() as session:
        async with session.get(data['link']) as resp:
            if resp.status != 200:
                await ctx.send(f'Error: {resp.status}')
                return False
            
            if type == 'movie':
                path = os.path.join(DOWNLOAD_PATH, 'Movies')
            elif type == 'serie':
                path = os.path.join(DOWNLOAD_PATH, 'Shows')
            else:
                return False
            
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


@bot.command(name='wawacity', help='Download a movie')
async def wawacity(ctx, type, url):
    if type is None and url is None:
        await ctx.send('Invalid arguments')
        return
    
    if not (url.startswith('http://') or url.startswith('https://')):
        await ctx.send('Invalid url')
        return
    
    if not (type == 'movie' or type == 'serie'):
        await ctx.send('Invalid type')
        return
    
    parser = Parser(show_logs=True)

    title, urls = parser.get_dl_protect_url(url)
    if not urls:
        await ctx.send(f'Error: No link found')
        return
    
    await ctx.send(f'You want to download: {title}')
    print(urls)
    
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
                    title = await download_by_url(ctx, dl_protect_url, type)
                    if title:
                        download_status = 'OK'
                    else :
                        download_status = 'ERROR'
                        error = 'Download error'
                except Exception as e:
                    download_status = 'ERROR'
                    error = e
            else:
                download_status = 'ERROR'
                error = 'No link found'

        summary.append({
            'title': title,
            'url': url,
            'dl_protect_url': dl_protect_url,
            'download_status': download_status,
            'error': error
        })
        
    with open(f'summary/{slugify(title)}.txt', 'w') as f:
        for item in summary:
            f.write(f"URL: {item['url']}, DL Protect URL: {item['dl_protect_url']}, Download Status: {item['download_status']}")
            
    await ctx.send(f"Summary: {len(summary)} files downloaded")

bot.run(TOKEN)
