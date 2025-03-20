import os
import sys
import time
import asyncio
import requests
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ANNOUNCE_CHANNEL_ID = os.getenv("ANNOUNCE_CHANNEL_ID")

if not TOKEN or not WEBHOOK_URL or not ANNOUNCE_CHANNEL_ID:
    print("❌ โปรดตั้งค่า environment variables (TOKEN, WEBHOOK_URL, ANNOUNCE_CHANNEL_ID)")
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

async def log_message(content):
    print(f"[LOG] {content}")
    asyncio.create_task(_send_webhook(content))

async def _send_webhook(content):
    if WEBHOOK_URL:
        try:
            response = requests.post(WEBHOOK_URL, json={"content": content})
            if response.status_code != 204:
                print(f"❌ ไม่สามารถส่ง webhook ได้: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดในการส่ง webhook: {e}")
    else:
        print("❌ ไม่พบ URL ของ webhook")

@bot.event
async def on_ready():
    print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
    await log_message("✅ บอทเริ่มทำงานเรียบร้อย")

class AnonymousMessageModal(Modal, title="ส่งข้อความนิรนาม"):
    message = TextInput(label="ข้อความ", style=discord.TextStyle.paragraph, required=True)
    user_id = TextInput(
        label="User ID (ถ้ามี)", 
        placeholder="เว้นว่างไว้ถ้าไม่มี\nตัวอย่าง user_id = 257693369604505600", 
        required=False

    async def on_submit(self, interaction: discord.Interaction):
        announce_channel = await bot.fetch_channel(int(ANNOUNCE_CHANNEL_ID))
        content = self.message.value
        user_id = self.user_id.value.strip()
        
        if user_id:
            try:
                mention_user = f"<@{int(user_id)}>"
                content = f"{mention_user}\n{content}"
            except ValueError:
                await interaction.response.send_message("❌ User ID ไม่ถูกต้อง", ephemeral=True)
                return
        
        await announce_channel.send(content, allowed_mentions=discord.AllowedMentions(users=True))
        await interaction.response.send_message("✅ ข้อความถูกส่งเรียบร้อย!", ephemeral=True)
        await log_message(f"📩 ข้อความถูกส่งไปยังห้องประกาศโดย {interaction.user} ({interaction.user.id}): {self.message.value}")

class SetupView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 เปิดเมนูส่งข้อความ", style=discord.ButtonStyle.primary)
    async def open_modal(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AnonymousMessageModal())

@bot.tree.command(name="setup", description="ตั้งค่าระบบส่งข้อความนิรนาม")
async def setup(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        await log_message(f"⚠️ ผู้ใช้ {interaction.user} ({interaction.user.id}) พยายามใช้คำสั่ง setup โดยไม่มีสิทธิ์")
        return

    embed = discord.Embed(
        title="📩 ให้พรี่โตส่งข้อความแทนคุณ",
        description="กดปุ่มด้านล่างเพื่อเปิดเมนูส่งข้อความ\nหากใส่ user_id ผิดจะไม่สามารถส่งได้\nสามารถเว้นว่างได้หากไม่มี user_id",
        color=discord.Color.blue()
    )
    
    channel = interaction.channel
    await channel.send(embed=embed, view=SetupView())
    await log_message(f"⚙️ คำสั่ง setup ถูกใช้งานในเซิร์ฟเวอร์: {interaction.guild.name} โดย {interaction.user} ({interaction.user.id})")

bot.run(TOKEN)
