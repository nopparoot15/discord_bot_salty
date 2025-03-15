import discord
from discord.ext import commands
import os
from myserver import server_on

TOKEN = os.getenv("TOKEN")  # ใส่ token ใน Environment
ANNOUNCE_CHANNEL_ID = 1350128705648984197
MESSAGE_INPUT_CHANNEL_ID = 1350161594985746567  # ID ห้องรับข้อความ

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

server_on()  # เปิดเซิร์ฟเวอร์ HTTP สำหรับ Render

@bot.event
async def on_ready():
    print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
    await bot.tree.sync()  # ซิงค์คำสั่ง Slash Commands

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.channel.id == MESSAGE_INPUT_CHANNEL_ID:
        content = message.content
        mentions = []
        remaining_words = []

        for word in content.split():
            if word.startswith('@'):
                username = word[1:]
                member = discord.utils.find(lambda m: m.name == username or m.display_name == username, message.guild.members)
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

        try:
            announce_channel = await bot.fetch_channel(ANNOUNCE_CHANNEL_ID)
            await announce_channel.send(final_message)
            await message.delete()
        except discord.errors.NotFound:
            print("❌ ไม่พบช่องประกาศ กรุณาตรวจสอบ ANNOUNCE_CHANNEL_ID")
        except discord.errors.Forbidden:
            print("❌ บอทไม่มีสิทธิ์ส่งข้อความไปยังช่องประกาศ")

    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    await ctx.send('🏓 Pong! บอทยังออนไลน์อยู่!')

@bot.tree.command(name="setup", description="ตั้งค่าระบบส่งข้อความนิรนาม")
async def setup(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        return

    embed = discord.Embed(
        title="📩 ให้พรี่โตส่งข้อความแทนคุณ",
        description="พิมพ์ข้อความในช่องนี้เพื่อส่งข้อความแบบไม่ระบุตัวตน\nสามารถ @mention สมาชิกได้โดยพิมพ์ @username",
        color=discord.Color.blue()
    )

    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ ตั้งค่าเรียบร้อยแล้ว!", ephemeral=True)

bot.run(TOKEN)
