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
        await interaction.response.send_message("✅ ข้อความถูกส่งเรียบร้อย!", ephemeral=False)
        await interaction.followup.send(
            f"✅ ข้อความถูกส่งเรียบร้อย! (จะลบใน {AUTODELETE_CONFIRM_AFTER} วินาที)",
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

class PaginatedMemberDropdown(View):
    def __init__(self, members, per_page=25, current_page=0):
        super().__init__(timeout=300)
        self.members = [m for m in members if not m.bot]
        self.per_page = per_page
        self.current_page = current_page
        self.max_page = ceil(len(self.members) / self.per_page)
        self.dropdown = None
        self.update_dropdown()

    def update_dropdown(self):
        start = self.current_page * self.per_page
        end = start + self.per_page
        options = [
            discord.SelectOption(label=member.display_name, value=str(member.id))
            for member in self.members[start:end]
        ]
        if self.dropdown:
            self.remove_item(self.dropdown)
        self.dropdown = Select(placeholder="เลือกผู้รับ...", options=options, custom_id="select_user")
        self.dropdown.callback = self.select_user
        self.add_item(self.dropdown)

    async def select_user(self, interaction: discord.Interaction):
        selected_id = int(self.dropdown.values[0])
        try:
            await interaction.message.delete()
        except discord.NotFound:
            print("⚠️ ข้อความ dropdown ถูกลบไปแล้วก่อน interaction")
        await interaction.response.send_modal(AnonymousMessageModal(selected_id))

    @discord.ui.button(label="⬅️ ย้อนกลับ", style=discord.ButtonStyle.secondary, row=1)
    async def prev_page(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_dropdown()
            await interaction.response.edit_message(view=self)

    @discord.ui.button(label="➡️ ถัดไป", style=discord.ButtonStyle.secondary, row=1)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        if self.current_page < self.max_page - 1:
            self.current_page += 1
            self.update_dropdown()
            await interaction.response.edit_message(view=self)

class SetupView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 เปิดเมนูส่งข้อความ", style=discord.ButtonStyle.primary)
    async def open_dropdown(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "👤 เลือกผู้รับที่ต้องการส่งข้อความถึง:",
            view=PaginatedMemberDropdown(interaction.guild.members),
            ephemeral=True
        )

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

    await interaction.channel.send(embed=embed, view=SetupView())
    await log_message(f"⚙️ คำสั่ง setup ถูกใช้งานในเซิร์ฟเวอร์: {interaction.guild.name} โดย {interaction.user} ({interaction.user.id})")

@bot.command(name="delete")
@commands.has_permissions(administrator=True)
async def delete_messages(ctx, amount: int):
    if amount < 1:
        await ctx.send("❌ กรุณาระบุจำนวนข้อความที่ต้องการลบมากกว่า 0")
        return

    deleted = await ctx.channel.purge(limit=amount + 1)
    confirm_msg = await ctx.send(f"✅ ลบข้อความจำนวน {len(deleted) - 1} ข้อความใน <#{ctx.channel.id}> เรียบร้อย")

    await log_message(
        f"🗑️ ผู้ดูแล {ctx.author} ({ctx.author.id}) ลบข้อความ {len(deleted) - 1} ข้อความ "
        f"ในห้อง {ctx.channel.name} (ID: {ctx.channel.id})"
    )

    await asyncio.sleep(AUTODELETE_CONFIRM_AFTER)
    await confirm_msg.delete()


async def user_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=member.display_name, value=str(member.id))
        for member in interaction.guild.members
        if not member.bot and current.lower() in member.display_name.lower()
    ][:25]


@bot.tree.command(name="send_anon", description="ส่งข้อความนิรนามถึงสมาชิกที่เลือก")
@app_commands.describe(user="เลือกผู้ใช้ที่ต้องการส่งข้อความถึง")
@app_commands.autocomplete(user=user_autocomplete)
async def send_anon(interaction: discord.Interaction, user: str):
    await interaction.response.send_modal(AnonymousMessageModal(int(user)))

@bot.event
async def on_ready():
    print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
    await log_message("✅ บอทเริ่มทำงานเรียบร้อย")

bot.run(TOKEN)
