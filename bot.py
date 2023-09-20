import os

import alldebrid

import discord
from discord.ext import commands
from dotenv import load_dotenv
import aiohttp

import yt_dlp



load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DOWNLOAD_PATH = os.getenv('DOWNLOAD_PATH')

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())


@bot.command(name='music', help="Download a music file")
async def music(ctx, url):
	if not (url.startswith('https://')):
		await ctx.send('Invalid url')
		return
	
	with yt_dlp.YoutubeDL({
		'extract_audio': True, 
		'format': 'bestaudio', 
		'outtmpl': '/home/gones/Musique/%(title)s.mp3'
	}) as video:
		info_dict = video.extract_info(url, download = True)
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

bot.run(TOKEN)
