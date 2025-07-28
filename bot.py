from aiohttp import web
import os
import random
from datetime import datetime
import asyncio
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import discord
from discord.ext import commands
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')  # Your Discord bot token
TMDB_API_KEY = os.getenv('TMDB_API_KEY')    # Your TMDB API key
CHANNEL_ID = int(os.getenv('CHANNEL_ID', 0))  # Target channel ID for recommendations

# Ensure credentials are available
if not DISCORD_TOKEN or not TMDB_API_KEY or not CHANNEL_ID:
    raise EnvironmentError("Missing one or more required environment variables: DISCORD_TOKEN, TMDB_API_KEY, CHANNEL_ID")

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize scheduler
scheduler = AsyncIOScheduler()

async def fetch_recommendations(media_type: str = 'movie', count: int = 3):
    """
    Fetches random recommendations from TMDB.
    media_type: 'movie' or 'tv'
    count: number of items to return
    """
    base_url = 'https://api.themoviedb.org/3'
    async with aiohttp.ClientSession() as session:
        url = f"{base_url}/{media_type}/popular?api_key={TMDB_API_KEY}&language=en-US&page=1"
        async with session.get(url) as resp:
            data = await resp.json()
        results = data.get('results', [])
        if not results:
            return []
        picks = random.sample(results, min(count, len(results)))
        formatted = []
        for item in picks:
            title = item.get('title') if media_type == 'movie' else item.get('name')
            overview = item.get('overview', 'No description available.').strip()
            link = f"https://www.themoviedb.org/{media_type}/{item.get('id')}"
            formatted.append(f"**{title}**\n{overview}\n{link}")
        return formatted

async def send_daily_recommendations():
    """Fetch and send recommendations for both movies and series."""
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"Error: Channel ID {CHANNEL_ID} not found.")
        return
    movies = await fetch_recommendations('movie', 2)
    series = await fetch_recommendations('tv', 2)
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    content = [f"**Daily Recommendations for {now}**\n"]
    if movies:
        content.append("__**Movies:**__")
        content.extend(movies)
    if series:
        content.append("__**Series:**__")
        content.extend(series)
    await channel.send("\n".join(content))

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    scheduler.add_job(send_daily_recommendations, 'cron', hour=12, minute=0)
    scheduler.start()

@bot.command(name='recommend')
async def recommend(ctx, media_type: str = 'movie', count: int = 1):
    """!recommend [movie|tv] [count] - On-demand recommendations."""
    try:
        recs = await fetch_recommendations(media_type, int(count))
        await ctx.send("\n".join(recs) if recs else "No recommendations found.")
    except Exception as e:
        await ctx.send(f"Error fetching recommendations: {e}")

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)
    
async def handle_ping(request):
    return web.Response(text="OK")

async def start_webserver():
    app = web.Application()
    app.add_routes([web.get('/', handle_ping)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv('PORT', 3000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Webserver running on port {port}")

@bot.event
async def on_ready():
    # existing on_ready contents…
    # then start webserver:
    bot.loop.create_task(start_webserver())
