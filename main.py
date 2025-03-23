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

from math import ceil
from discord.ui import Select


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
        members = interaction.guild.members
        view = PaginatedMemberDropdown(members)
        await interaction.response.send_message("👤 เลือกผู้รับที่ต้องการส่งข้อความถึง:", view=view, ephemeral=True)

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

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    async def select_user(self, interaction: discord.Interaction):
        selected_id = int(self.dropdown.values[0])
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

class AnonymousMessageModal(Modal, title="ส่งข้อความนิรนาม"):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self.message = TextInput(label="ข้อความ", style=discord.TextStyle.paragraph, required=True)
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        announce_channel = await bot.fetch_channel(int(ANNOUNCE_CHANNEL_ID))
        mention_user = f"<@{self.user_id}>"
        content = f"{mention_user}\n{self.message.value}"
        await announce_channel.send(content, allowed_mentions=discord.AllowedMentions(users=True))
        await interaction.response.send_message("✅ ข้อความถูกส่งเรียบร้อย!", ephemeral=True)
        await log_message(f"📩 ส่งถึง {self.user_id} โดย {interaction.user}: {self.message.value}")

# แก้ปุ่มใน SetupView เพื่อเปิด dropdown view แทน modal เดิม
SetupView.open_modal.callback = lambda self, interaction, button: asyncio.create_task(
    interaction.response.send_message(
        "เลือกผู้รับ:", view=PaginatedMemberDropdown(interaction.guild.members), ephemeral=True
    )
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



@bot.event
async def on_ready():
    print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
    await log_message("✅ บอทเริ่มทำงานเรียบร้อย")


bot.run(TOKEN)
