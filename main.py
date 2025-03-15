import discord
from discord.ext import commands
import os
from myserver import server_on

TOKEN = os.getenv("TOKEN")  # token จาก Environment
ANNOUNCE_CHANNEL_ID = 1350128705648984197
MESSAGE_INPUT_CHANNEL_ID = 123456789012345678  # ใส่ ID ห้องรับข้อความ

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

server_on()  # เปิดเซิร์ฟเวอร์ HTTP สำหรับ Render

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

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f'✅ บอทพร้อมใช้งาน: {bot.user}')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! 🏓')

@bot.tree.command(name="setup", description="สร้างกล่องข้อความแนะนำวิธีใช้")
@commands.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📩 ให้พรี่โตส่งข้อความแทนคุณ",
        description="พิมพ์ข้อความในช่องนี้เพื่อส่งข้อความแบบไม่ระบุตัวตน\nสามารถ @mention สมาชิกได้โดยพิมพ์ @username",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ สร้างกล่องข้อความเรียบร้อยแล้ว", ephemeral=True)

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! 🏓')

bot.run(os.getenv("TOKEN"))
