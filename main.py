
import os
import sys
import time
import asyncio
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput, Select
from math import ceil

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ANNOUNCE_CHANNEL_ID = os.getenv("ANNOUNCE_CHANNEL_ID")

if not TOKEN or not WEBHOOK_URL or not ANNOUNCE_CHANNEL_ID:
    print("❌ โปรดตั้งค่า environment variables (TOKEN, WEBHOOK_URL, ANNOUNCE_CHANNEL_ID)")
    sys.exit(1)

AUTODELETE_CONFIRM_AFTER = 5

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


async def send_anon_message(interaction, user_id: int, message_body: str):
    try:
        announce_channel = await bot.fetch_channel(int(ANNOUNCE_CHANNEL_ID))
        mention_user = f"<@{user_id}>"
        content = f"{mention_user}\n{message_body}"

        await announce_channel.send(content, allowed_mentions=discord.AllowedMentions(users=True))
        msg = await interaction.response.send_message("✅ พรี่โตส่งข้อความให้เรียบร้อยแล้วนะ!", ephemeral=False)

        followup = await interaction.followup.send(
            f"🕓 ข้อความจะหายไปใน {AUTODELETE_CONFIRM_AFTER} วินาที เพื่อความเป็นส่วนตัวนะ!",
            ephemeral=False
        )

        await log_message(f"📩 ส่งถึง {user_id} โดย {interaction.user}: {message_body}")
        await asyncio.sleep(AUTODELETE_CONFIRM_AFTER)

        try:
            await followup.delete()
        except discord.NotFound:
            print("⚠️ ข้อความ followup ถูกลบไปแล้ว")
        except Exception as e:
            print(f"❌ ลบ followup ไม่สำเร็จ: {e}")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการส่งข้อความ: {e}")


        announce_channel = await bot.fetch_channel(int(ANNOUNCE_CHANNEL_ID))
        mention_user = f"<@{user_id}>"
        content = f"{mention_user}\n{message_body}"

        await announce_channel.send(content, allowed_mentions=discord.AllowedMentions(users=True))
        await interaction.response.send_message("✅ พรี่โตส่งข้อความให้เรียบร้อยแล้วนะ!", ephemeral=False)
        await interaction.followup.send(
            f"🕓 ข้อความจะหายไปใน {AUTODELETE_CONFIRM_AFTER} วินาที เพื่อความเป็นส่วนตัวนะ!",
            ephemeral=True
        )
        await log_message(f"📩 ส่งถึง {user_id} โดย {interaction.user}: {message_body}")

        await asyncio.sleep(AUTODELETE_CONFIRM_AFTER)
        try:
            msg = await interaction.original_response()
            await msg.delete()
        except discord.NotFound:
            pass
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการส่งข้อความ: {e}")

class AnonymousMessageModal(Modal, title="ส่งข้อความนิรนาม"):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self.message = TextInput(label="ข้อความ", style=discord.TextStyle.paragraph, required=True)
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        message_body = self.message.value.strip()
        if not message_body:
            await interaction.response.send_message("❌ กรุณาใส่ข้อความ", ephemeral=True)
            return
        await send_anon_message(interaction, self.user_id, message_body)

class NameInputModal(Modal, title="พิมพ์ชื่อสมาชิก"):
    name = TextInput(label="ชื่อผู้ใช้ (หรือบางส่วน)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        input_name = self.name.value.lower()
        matched = [m for m in interaction.guild.members if not m.bot and input_name in m.display_name.lower()]

        if not matched:
            await interaction.response.send_message("❌ ไม่พบผู้ใช้ที่ตรงกับชื่อที่ป้อน", ephemeral=True)
            return

        if len(matched) > 1:
            await interaction.response.send_message(
                f"⚠️ พบผู้ใช้หลายคนที่ชื่อคล้ายกัน: {', '.join(m.display_name for m in matched[:5])}...",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(AnonymousMessageModal(user_id=matched[0].id))




@bot.tree.command(name="setup", description="ตั้งค่าระบบส่งข้อความลับ")
async def setup(interaction: discord.Interaction):
    print(f"[DEBUG] /setup called by {interaction.user} ({interaction.user.id})")
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        await log_message(f"⚠️ ผู้ใช้ {interaction.user} ({interaction.user.id}) พยายามใช้คำสั่ง setup โดยไม่มีสิทธิ์")
        return

    embed = discord.Embed(
        title="📬 ส่งข้อความลับแบบนิรนาม",
        description="พิมพ์ชื่อสมาชิกที่คุณอยากส่งข้อความถึง แล้วพรี่โตจะส่งให้แทนโดยไม่มีใครรู้ว่าใครส่ง!",
        color=discord.Color.blurple()
    )

    await interaction.channel.send(embed=embed, view=SetupView())
    await log_message(f"⚙️ คำสั่ง setup ถูกใช้งานในเซิร์ฟเวอร์: {interaction.guild.name} โดย {interaction.user} ({interaction.user.id})")


@bot.event
async def on_ready():
    print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
    await bot.tree.sync()
    await log_message("✅ บอทเริ่มทำงานเรียบร้อย")

bot.run(TOKEN)
