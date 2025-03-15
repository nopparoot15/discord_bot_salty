import discord
from discord.ext import commands
from config import TOKEN

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

def run_bot():
    bot.run(TOKEN)