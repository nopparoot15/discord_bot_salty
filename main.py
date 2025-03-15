import os
import sys
import time
import asyncio  # ✅ จัดให้อยู่กับ standard library

import discord
from discord.ext import commands  # ✅ จัดให้อยู่กับ third-party libraries

from myserver import server_on  # ✅ โมดูลภายในโปรเจกต์

TOKEN = os.getenv("TOKEN")  # ใส่ token ใน Environment
ANNOUNCE_CHANNEL_ID = 1350128705648984197
LOG_CHANNEL_ID = 1350380441504448512  # ID ห้องเก็บ logs

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def log_message(content):
    print(f"[LOG] {content}")  # ✅ Debugging log
    asyncio.create_task(_send_log(content))  # ทำให้ log ทำงานแบบ async

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
        bot.synced = True  # ป้องกันการ Sync ซ้ำ
        print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
        await log_message("✅ บอทเริ่มทำงานเรียบร้อย")

class SendMessageModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="ส่งข้อความนิรนาม")
        self.message_content = discord.ui.TextInput(label="ข้อความ", style=discord.TextStyle.paragraph)
        self.add_item(self.message_content)
        self.mention_user = discord.ui.TextInput(label="Mention ผู้ใช้ (ใส่ชื่อผู้ใช้, คั่นด้วยช่องว่าง)", style=discord.TextStyle.short)
        self.add_item(self.mention_user)

    async def on_submit(self, interaction: discord.Interaction):
        # Process the message and mentions
        content = self.message_content.value
        mention_input = self.mention_user.value.split()
        mentions = []
        remaining_words = []

        for username in mention_input:
            member = discord.utils.get(interaction.guild.members, name=username) or discord.utils.get(interaction.guild.members, display_name=username)
            if member:
                mentions.append(member.mention)  # ใช้ mention จริงใน message
            else:
                remaining_words.append(username)

        mention_text = " ".join(mentions)
        final_message = f"{mention_text}\n{content}" if mentions else content

        try:
            announce_channel = await bot.fetch_channel(ANNOUNCE_CHANNEL_ID)
            
            # Check if the message is new or sufficiently different from the last sent one
            current_time = time.time()
            if not getattr(bot, 'last_message_content', None) or (bot.last_message_content != final_message and current_time - getattr(bot, 'last_message_time', 0) > 2):
                bot.last_message_content = final_message
                bot.last_message_time = current_time
                await announce_channel.send(final_message, allowed_mentions=discord.AllowedMentions(users=True, roles=True, everyone=False))

            # Log message content and mentions
            log_entry = f"📩 ข้อความถูกส่งโดย {interaction.user} ({interaction.user.id}) : {content}"
            if mentions:
                log_entry += f" | Mentions: {', '.join([m.display_name for m in mentions])}"
            await log_message(log_entry)

            await interaction.response.send_message("ข้อความถูกส่งเรียบร้อยแล้ว", ephemeral=True)

        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            error_msg = f"❌ เกิดข้อผิดพลาดในการส่งข้อความ: {str(e)}"
            print(error_msg)
            await log_message(error_msg)

class ConfirmButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="ส่งข้อความ", style=discord.ButtonStyle.green)
    async def send_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SendMessageModal())

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
        os._exit(0)  # ใช้วิธีปิดบอท ให้โฮสต์รันใหม่เอง
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
    view = ConfirmButton()
    await ctx.send(embed=embed, view=view)
    await log_message(f"⚙️ ระบบ setup ถูกตั้งค่าในช่อง: {ctx.channel.name}")

server_on()  # เปิดเซิร์ฟเวอร์ HTTP สำหรับ Render
bot.run(TOKEN)
