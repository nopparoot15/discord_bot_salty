import os
import sys
import time
import asyncio

import discord
from discord.ext import commands

from myserver import server_on

TOKEN = os.getenv("TOKEN")
ANNOUNCE_CHANNEL_ID = 1350128705648984197
LOG_CHANNEL_ID = 1350380441504448512

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def log_message(content):
    print(f"[LOG] {content}")
    asyncio.create_task(_send_log(content))

async def _send_log(content):
    try:
        log_channel = await bot.fetch_channel(LOG_CHANNEL_ID)
        await log_channel.send(content)
    except discord.errors.NotFound:
        print("❌ ไม่พบช่อง logs กรุณาตรวจสอบ LOG_CHANNEL_ID")
    except discord.errors.Forbidden:
        print("❌ บอทไม่มีสิทธิ์ส่งข้อความไปยังช่อง logs")

@bot.event
async def on_ready():
    if not getattr(bot, 'synced', False):
        await bot.tree.sync()
        bot.synced = True
        print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
        await log_message("✅ บอทเริ่มทำงานเรียบร้อย")

class MessageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="ส่งข้อความ", style=discord.ButtonStyle.green)
    async def send_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("กรุณาพิมพ์ข้อความที่ต้องการส่ง:", ephemeral=True)
        
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        
        try:
            message = await bot.wait_for('message', check=check, timeout=60)
            await interaction.channel.send("กรุณาพิมพ์ชื่อผู้ใช้ที่ต้องการ @mention (ถ้ามี):", ephemeral=True)
            
            mention_message = await bot.wait_for('message', check=check, timeout=60)
            mention_input = mention_message.content.split()
            mentions = [discord.utils.get(interaction.guild.members, name=username) or discord.utils.get(interaction.guild.members, display_name=username) for username in mention_input]
            mentions = [member.mention for member in mentions if member]

            final_message = f"{' '.join(mentions)}\n{message.content}" if mentions else message.content

            announce_channel = await bot.fetch_channel(ANNOUNCE_CHANNEL_ID)
            current_time = time.time()
            if not getattr(bot, 'last_message_content', None) or (bot.last_message_content != final_message and current_time - getattr(bot, 'last_message_time', 0) > 2):
                bot.last_message_content = final_message
                bot.last_message_time = current_time
                await announce_channel.send(final_message, allowed_mentions=discord.AllowedMentions(users=True, roles=True, everyone=False))

            log_entry = f"📩 ข้อความถูกส่งโดย {interaction.user} ({interaction.user.id}) : {message.content}"
            if mentions:
                log_entry += f" | Mentions: {', '.join([m.display_name for m in mentions])}"
            await log_message(log_entry)

            await interaction.followup.send("ข้อความถูกส่งเรียบร้อยแล้ว", ephemeral=True)

        except asyncio.TimeoutError:
            await interaction.followup.send("หมดเวลาในการตอบสนอง กรุณาลองใหม่อีกครั้ง", ephemeral=True)

@bot.command()
async def ping(ctx):
    await ctx.send('🏓 Pong! บอทยังออนไลน์อยู่!')
    await log_message(f"🏓 Pong! มีการใช้คำสั่ง ping โดย {ctx.author} ({ctx.author.id})")

@bot.command()
async def update(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้")
        return
    
    await ctx.send("🔄 กำลังอัปเดตบอท โปรดรอสักครู่...")
    await log_message("🔄 บอทกำลังรีสตาร์ทตามคำสั่งอัปเดต")
    try:
        os._exit(0)
    except Exception as e:
        await ctx.send(f"❌ ไม่สามารถรีสตาร์ทบอทได้: {e}")
        await log_message(f"❌ รีสตาร์ทบอทล้มเหลว: {e}")

@bot.command()
async def setup(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้")
        await log_message(f"⚠️ ผู้ใช้ {ctx.author} ({ctx.author.id}) พยายามใช้คำสั่ง setup โดยไม่มีสิทธิ์")
        return

    embed = discord.Embed(
        title="📩 ให้พรี่โตส่งข้อความแทนคุณ",
        description="กดปุ่มด้านล่างเพื่อส่งข้อความแบบไม่ระบุตัวตน\nสามารถ @mention ผู้ใช้ได้ด้วย",
        color=discord.Color.blue()
    )
    view = MessageView()
    await ctx.send(embed=embed, view=view)
    await log_message(f"⚙️ ระบบ setup ถูกตั้งค่าในช่อง: {ctx.channel.name}")

server_on()
bot.run(TOKEN)
