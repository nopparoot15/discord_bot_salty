import discord
from discord.ext import commands
from log_utils import setup_logging, send_log_to_discord

logger = setup_logging()
webhook_url = "https://discord.com/api/webhooks/1350546611327078464/17AFMw_4NM7bvaArtO52Sl1CkThz9gJqai5V4CwJS2J0UD_H3up1nyDsheFSD93ODxbu"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name}')
    send_log_to_discord(webhook_url, f'Logged in as {bot.user.name}')
    print(f'Logged in as {bot.user.name}')

@bot.event
async def on_command_error(ctx, error):
    logger.error(f'Error: {str(error)}')
    send_log_to_discord(webhook_url, f'Error: {str(error)}')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

# Replace 'TOKEN' with your actual bot token
bot.run('TOKEN')
