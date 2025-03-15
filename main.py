import discord
from discord.ext import commands
import os
from myserver import server_on

TOKEN = os.getenv("DISCORD_TOKEN")  # token จาก Environment
ANNOUNCE_CHANNEL_ID = 1350128705648984197
MESSAGE_INPUT_CHANNEL_ID = 1234567890123456789  # เปลี่ยนเป็น ID ห้องที่ใช้รับข้อความ

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

server_on()  # สำหรับให้บอทออนไลน์บน Render

@bot.event
async def on_ready():
    print(f'✅ บอทพร้อมใช้งาน: {bot.user}')

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != MESSAGE_INPUT_CHANNEL_ID:
        return

    content = message.content
    mentions = []
    words = content.split()
    remaining_words = []

    for word in words:
        if word.startswith('@'):
            username = word[1:]
            member = discord.utils.get(message.guild.members, name=username)
            if member:
                mentions.append(member.mention)
            else:
                remaining_words.append(word)
        else:
            remaining_words.append(word)

    mention_text = " ".join(mentions)
    final_message = " ".join(remaining_words)

    if mentions:
        final_message = f"{mention_text}\n{final_message}"

    announce_channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if announce_channel:
        await announce_channel.send(final_message)
        await message.delete()

    await bot.process_commands(message)  # เพิ่มตรงนี้เพื่อให้คำสั่งทำงาน

@bot.command()
async def ping(ctx):
    await ctx.send('🏓 Pong! บอทยังออนไลน์อยู่!')

bot.run(os.getenv('DISCORD_TOKEN'))
