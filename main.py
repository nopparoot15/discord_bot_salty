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


class NameInputModal(Modal):
    def __init__(self):
        super().__init__(title="ส่งข้อความลับถึงใครดีน้า~")
        self.search_input = TextInput(
            label="ชื่อเล่นของเพื่อนที่คุณอยากส่งถึง",
            style=discord.TextStyle.short,
            required=True
        )
        self.add_item(self.search_input)

    async def on_submit(self, interaction: discord.Interaction):
        input_name = self.search_input.value.lower()
        matched = [
            m for m in interaction.guild.members
            if not m.bot and input_name in m.display_name.lower()
        ]

        if not matched:
            response_message = await interaction.response.send_message("❌ หาไม่เจอเลย~ ลองพิมพ์ใหม่อีกทีน้า", ephemeral=True)
            await asyncio.sleep(AUTODELETE_CONFIRM_AFTER)
            try:
                await response_message.delete()
            except discord.NotFound:
                print("⚠️ ข้อความถูกลบไปแล้ว")
            except Exception as e:
                print(f"❌ ลบข้อความไม่สำเร็จ: {e}")
            return

        response_message = await interaction.response.send_message(
            "🔍 เจอชื่อคล้ายกันหลายคนเลย~ เลือกคนที่ใช่ด้านล่างนี้นะ!",
            view=UserSelect(matched),
            ephemeral=True
        )

        await asyncio.sleep(AUTODELETE_CONFIRM_AFTER)

        try:
            await response_message.delete()
        except discord.NotFound:
            print("⚠️ ข้อความถูกลบไปแล้ว")
        except Exception as e:
            print(f"❌ ลบข้อความไม่สำเร็จ: {e}")


class SetupView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 ส่งข้อความลับเลย!", style=discord.ButtonStyle.primary)
    async def send_secret_message(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(NameInputModal())


TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ANNOUNCE_CHANNEL_ID = os.getenv("ANNOUNCE_CHANNEL_ID")

if not TOKEN or not WEBHOOK_URL หรือ ANNOUNCE_CHANNEL_ID:
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
        response_message = await interaction.response.send_message("✅ พรี่โตส่งข้อความให้เรียบร้อยแล้วนะ!", ephemeral=True)

        followup = await interaction.followup.send(
            f"🕓 ข้อความจะหายไปใน {AUTODELETE_CONFIRM_AFTER} วินาที เพื่อความเป็นส่วนตัวนะ!",
            ephemeral=True
        )

        await log_message(f"📩 ส่งถึง {user_id} โดย {interaction.user}: {message_body}")

        await asyncio.sleep(AUTODELETE_CONFIRM_AFTER)

        try:
            await response_message.delete()
            await followup.delete()
        except discord.NotFound:
            print("⚠️ ข้อความ follow-up ถูกลบไปแล้ว")
        except Exception as e:
            print(f"❌ ลบข้อความ follow-up ไม่สำเร็จ: {e}")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการส่งข้อความ: {e}")


class AnonymousMessageModal(Modal, title="ส่งข้อความนิรนาม"):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self.body = TextInput(label="พิมพ์ข้อความลับของคุณที่นี่เลยน้า~", style=discord.TextStyle.paragraph, required=True)
        self.add_item(self.body)

    async def on_submit(self, interaction: discord.Interaction):
        message_body = self.body.value.strip()
        if not message_body:
            response_message = await interaction.response.send_message("❌ กรุณาใส่ข้อความ", ephemeral=True)
            await asyncio.sleep(AUTODELETE_CONFIRM_AFTER)
            try:
                await response_message.delete()
            except discord.NotFound:
                print("⚠️ ข้อความถูกลบไปแล้ว")
            except Exception as e:
                print(f"❌ ลบข้อความไม่สำเร็จ: {e}")
            return
        await send_anon_message(interaction, self.user_id, message_body)
        
        # ลบข้อความ "🔍 เจอชื่อคล้ายกันหลายคนเลย~" หลังจากกดปุ่มส่งข้อความ
        try:
            await interaction.message.delete()
        except discord.NotFound:
            print("⚠️ ข้อความถูกลบไปแล้ว")
        except Exception as e:
            print(f"❌ ลบข้อความไม่สำเร็จ: {e}")


class UserSelect(View):
    def __init__(self, matched_users):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=user.display_name, value=str(user.id)) for user in matched_users]
        self.select = Select(placeholder="เลือกเพื่อนที่คุณอยากส่งข้อความลับถึง", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        selected_user_id = int(self.select.values[0])
        await interaction.response.send_modal(AnonymousMessageModal(user_id=selected_user_id))


@bot.tree.command(name="setup", description="ตั้งค่าระบบส่งข้อความลับ")
async def setup(interaction: discord.Interaction):
    print(f"[DEBUG] /setup called by {interaction.user} ({interaction.user.id})")
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        await log_message(f"⚠️ ผู้ใช้ {interaction.user} ({interaction.user.id}) พยายามใช้คำสั่ง setup โดยไม่มีสิทธิ์")
        return

    embed = discord.Embed(
        title="📬 ส่งข้อความลับถึงใครบางคนแบบเนียน ๆ",
        description="พิมพ์ชื่อเพื่อน แล้วพรี่โตจะช่วยส่งข้อความลับให้แบบไม่มีใครรู้ว่าใครส่งเลย~",
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
