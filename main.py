import os
import sys
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
from datetime import datetime, timezone, timedelta
from collections import deque
import difflib

# Constants
LOG_CHANNEL_ID = 1350531209377349662

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
        input_name = self.search_input.value.strip().lower()
        if not input_name:
            await interaction.response.send_message("❌ กรุณาใส่ชื่อ", ephemeral=True)
            return

        member_names = {
            m.display_name.lower(): m
            for m in interaction.guild.members
            if not m.bot
        }
        close_matches = difflib.get_close_matches(input_name, member_names.keys(), n=5, cutoff=0.4)

        matched = [member_names[name] for name in close_matches]
        if not matched:
            await interaction.response.send_message("❌ หาไม่เจอเลย~ ลองพิมพ์ใหม่อีกทีน้า", ephemeral=True)
            return

        await interaction.response.send_message(
            "🔍 เจอชื่อคล้ายกันหลายคนเลย~ เลือกคนที่ใช่ด้านล่างนี้นะ!",
            view=UserSelect(matched), ephemeral=True
        )


class SetupView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 ส่งข้อความลับเลย!", style=discord.ButtonStyle.primary, custom_id="send_secret_btn")
    async def send_secret_message(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(NameInputModal())


TOKEN = os.getenv("TOKEN")
ANNOUNCE_CHANNEL_ID_STR = os.getenv("ANNOUNCE_CHANNEL_ID")

if not TOKEN or not ANNOUNCE_CHANNEL_ID_STR or not ANNOUNCE_CHANNEL_ID_STR.isdigit():
    print("❌ โปรดตั้งค่า environment variables (TOKEN, ANNOUNCE_CHANNEL_ID)")
    sys.exit(1)

ANNOUNCE_CHANNEL_ID = int(ANNOUNCE_CHANNEL_ID_STR)

LOG_LIMIT_PERIOD = timedelta(minutes=1)
LOG_LIMIT_COUNT = 5

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.log_queue = deque()
        self._is_logging = False

    async def setup_hook(self):
        self.add_view(SetupView())  # Register persistent view
        await self.tree.sync()

    async def log_message(self, sender_user: discord.abc.User, recipient: str, message_body: str):
        sender_name = sender_user.display_name
        if sender_name == "พรี่โต_log" or recipient == "นรินาม-logs":
            return

        if self._is_logging:
            return

        self._is_logging = True
        try:
            now = datetime.now(timezone.utc)
            while self.log_queue and self.log_queue[0] < now - LOG_LIMIT_PERIOD:
                self.log_queue.popleft()

            if len(self.log_queue) < LOG_LIMIT_COUNT:
                if len(message_body) > 1024:
                    message_body = message_body[:1021] + "..."

                embed = discord.Embed(
                    title="📨 มีข้อความลับถูกส่ง",
                    color=discord.Color.purple(),
                    timestamp=now
                )
                embed.set_author(name=sender_name, icon_url=sender_user.display_avatar.url)
                embed.add_field(name="🎯 ถึง", value=recipient, inline=True)
                embed.add_field(name="💬 ข้อความ", value=message_body, inline=False)

                log_channel = self.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(embed=embed)
                self.log_queue.append(now)
                print(f"[LOG] {sender_name} -> {recipient}: {message_body}")
            else:
                print("[LOG] การส่ง log ถูกจำกัดเนื่องจากมี log มากเกินไปในช่วงเวลาที่กำหนด")
        except Exception as e:
            print(f"[ERROR] Failed to send log: {e}")
        finally:
            self._is_logging = False

bot = MyBot()

async def send_anon_message(interaction, user_id: int, message_body: str):
    try:
        user = await bot.fetch_user(user_id)
        announce_channel = await bot.fetch_channel(ANNOUNCE_CHANNEL_ID)
        if user and announce_channel:
            await announce_channel.send(
                f"💌 มีข้อความถึง {user.mention}:\n>>> {message_body}" 
            )
            await interaction.response.send_message("✅ ข้อความถูกส่งประกาศเรียบร้อย", ephemeral=True)
            await bot.log_message(interaction.user, user.display_name, message_body)
        else:
            await interaction.response.send_message("❌ ผู้ใช้นี้ไม่อยู่ในเซิร์ฟเวอร์หรือไม่สามารถเข้าถึงช่องประกาศได้", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("❌ ไม่พบผู้ใช้หรือช่องประกาศ", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ ไม่มีสิทธิ์ในการเข้าถึงผู้ใช้หรือช่องประกาศ", ephemeral=True)
    except discord.HTTPException:
        await interaction.response.send_message("❌ เกิดข้อผิดพลาดในการส่งข้อความ", ephemeral=True)

class AnonymousMessageModal(Modal, title="ส่งข้อความนิรนาม"):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self.body = TextInput(
            label="พิมพ์ข้อความลับของคุณที่นี่เลยน้า~",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.body)

    async def on_submit(self, interaction: discord.Interaction):
        message_body = self.body.value.strip()
        if not message_body:
            await interaction.response.send_message("❌ กรุณาใส่ข้อความ", ephemeral=True)
            return
        await send_anon_message(interaction, self.user_id, message_body)

class UserSelect(View):
    def __init__(self, matched_users):
        super().__init__(timeout=None)
        options = [discord.SelectOption(label=user.display_name, value=str(user.id)) for user in matched_users]
        self.select = Select(placeholder="เลือกเพื่อนที่คุณอยากส่งข้อความลับถึง", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        selected_user_id = int(self.select.values[0])
        if selected_user_id == interaction.user.id:
            await interaction.response.send_message("❌ คุณไม่สามารถส่งข้อความลับถึงตัวเองได้นะ!", ephemeral=True)
            return
        await interaction.response.send_modal(AnonymousMessageModal(user_id=selected_user_id))

@bot.tree.command(name="setup", description="ตั้งค่าระบบส่งข้อความลับ")
async def setup(interaction: discord.Interaction):
    print(f"[DEBUG] /setup called by {interaction.user} ({interaction.user.id})")
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        await bot.log_message(interaction.user, "ระบบ", "พยายามใช้คำสั่ง setup โดยไม่มีสิทธิ์")
        return

    embed = discord.Embed(
        title="📬 ส่งข้อความลับถึงใครบางคนแบบเนียน ๆ",
        description="พิมพ์ชื่อเพื่อน แล้วพรี่โตจะช่วยส่งข้อความลับให้แบบไม่มีใครรู้ว่าใครส่งเลย~",
        color=discord.Color.blurple()
    )

    await interaction.channel.send(embed=embed, view=SetupView())
    await bot.log_message(interaction.user, "ระบบ", f"คำสั่ง setup ถูกใช้งานในเซิร์ฟเวอร์: {interaction.guild.name}")

@bot.event
async def on_ready():
    print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
    await bot.log_message(bot.user, "ระบบ", "บอทเริ่มทำงานเรียบร้อย")

bot.run(TOKEN)
