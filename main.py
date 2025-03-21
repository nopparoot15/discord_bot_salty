import os
import sys
import time
import asyncio
import aiohttp
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
    async with aiohttp.ClientSession() as session:
        async with session.post(WEBHOOK_URL, json={"content": content}) as response:
            if response.status != 204:
                print(f"❌ ไม่สามารถส่ง webhook ได้: {response.status} - {await response.text()}")


@bot.event
async def on_ready():
    print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
    await log_message("✅ บอทเริ่มทำงานเรียบร้อย")

class AnonymousMessageModal(Modal, title="ส่งข้อความนิรนาม"):
    message = TextInput(label="ข้อความ", style=discord.TextStyle.paragraph, required=True)
    user_id = TextInput(label="User ID (เว้นว่างไว้หากไม่มี)", required=False)

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
        description="กดปุ่มด้านล่างเพื่อเปิดเมนูส่งข้อความแบบไม่ระบุตัวตน",
        color=discord.Color.blue()
    )
    
    channel = interaction.channel
    await channel.send(embed=embed, view=SetupView())
    await log_message(f"⚙️ คำสั่ง setup ถูกใช้งานในเซิร์ฟเวอร์: {interaction.guild.name} โดย {interaction.user} ({interaction.user.id})")

@bot.command(name="delete")
@commands.has_permissions(administrator=True)
async def delete_messages(ctx, amount: int):
    if amount < 1:
        await ctx.send("❌ กรุณาระบุจำนวนข้อความที่ต้องการลบมากกว่า 0")
        return

    # ลบจำนวนที่ระบุ + ข้อความคำสั่งเอง
    deleted = await ctx.channel.purge(limit=amount + 1)

    # ส่งข้อความยืนยันชั่วคราว
    confirm_msg = await ctx.send(f"✅ ลบข้อความจำนวน {len(deleted) - 1} ข้อความใน <#{ctx.channel.id}> เรียบร้อย")
    
    # log ผ่าน webhook
    await log_message(
        f"🗑️ ผู้ดูแล {ctx.author} ({ctx.author.id}) ลบข้อความ {len(deleted) - 1} ข้อความ "
        f"ในห้อง {ctx.channel.name} (ID: {ctx.channel.id})"
    )

    # ลบข้อความยืนยันภายใน 5 วินาที
    await asyncio.sleep(5)
    await confirm_msg.delete()


bot.run(TOKEN)
