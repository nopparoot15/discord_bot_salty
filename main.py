import os
import discord
import asyncio  # เพิ่มการ import asyncio
from discord.ext import commands
from discord import app_commands
from discord.ui import Modal, TextInput, Button, View, Select

from myserver import server_on

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

class MessageModal(Modal):
    def __init__(self):
        super().__init__(title="ส่งข้อความนิรนาม")
        self.add_item(TextInput(label="พิมพ์ข้อความของคุณที่นี่"))

    async def callback(self, interaction: discord.Interaction):
        content = self.children[0].value
        members = interaction.guild.members
        view = SelectUserView(members, content)
        await interaction.response.send_message("กรุณาเลือกผู้ใช้:", view=view, ephemeral=True)

class SelectUser(Select):
    def __init__(self, members, content, placeholder="เลือกผู้ใช้ (สูงสุด 3 คน)"):
        options = [discord.SelectOption(label=member.display_name, value=str(member.id)) for member in members]
        super().__init__(placeholder=placeholder, min_values=1, max_values=3, options=options)
        self.content = content

    async def callback(self, interaction: discord.Interaction):
        selected_users = [interaction.guild.get_member(int(user_id)) for user_id in self.values]
        final_message = f"{self.content}\n\nส่งโดย: นิรนาม"
        announce_channel = bot.get_channel(interaction.guild.announce_channel_id)
        await announce_channel.send(final_message, allowed_mentions=discord.AllowedMentions(users=True, roles=True, everyone=False))
        await interaction.response.send_message(f"คุณเลือก: {', '.join([user.display_name for user in selected_users])}", ephemeral=True)

class SelectUserView(View):
    def __init__(self, members, content, page=0):
        super().__init__()
        self.page = page
        self.members = members
        self.per_page = 25
        self.max_pages = (len(members) - 1) // self.per_page + 1
        self.content = content
        self.update_select_menu()
        self.update_buttons()

    def update_select_menu(self):
        start = self.page * self.per_page
        end = start + self.per_page
        self.clear_items()
        self.add_item(SelectUser(self.members[start:end], self.content))

    def update_buttons(self):
        if self.page > 0:
            self.add_item(PreviousPageButton())
        if self.page < self.max_pages - 1:
            self.add_item(NextPageButton())

class PreviousPageButton(Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="ก่อนหน้า")

    async def callback(self, interaction: discord.Interaction):
        view: SelectUserView = self.view
        view.page -= 1
        view.update_select_menu()
        view.update_buttons()
        await interaction.response.edit_message(view=view)

class NextPageButton(Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="ถัดไป")

    async def callback(self, interaction: discord.Interaction):
        view: SelectUserView = self.view
        view.page += 1
        view.update_select_menu()
        view.update_buttons()
        await interaction.response.edit_message(view=view)

class StartMessageButton(Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="เริ่มการส่งข้อความ")

    async def callback(self, interaction: discord.Interaction):
        modal = MessageModal()
        await interaction.response.send_modal(modal)

@bot.tree.command(name="help", description="แสดงวิธีใช้บอทสำหรับบุคคลทั่วไป")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="วิธีใช้บอท",
        description="คำสั่งต่างๆ ที่สามารถใช้ได้กับบอทนี้:",
        color=discord.Color.green()
    )
    embed.add_field(name="/setup", value="ตั้งค่าระบบส่งข้อความนิรนาม โดยผู้ดูแลระบบ", inline=False)
    embed.add_field(name="/help", value="แสดงวิธีใช้บอทนี้", inline=False)
    embed.set_footer(text="หากมีคำถามเพิ่มเติม กรุณาติดต่อผู้ดูแลระบบ")

    await interaction.response.send_message(embed=embed, ephemeral=True)

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
    if not getattr(bot, 'synced', False):
        await bot.tree.sync()
        bot.synced = True
        print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
        await log_message("✅ บอทเริ่มทำงานเรียบร้อย")

@bot.tree.command(name="setup", description="ตั้งค่าระบบส่งข้อความนิรนาม")
async def setup(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        await log_message(f"⚠️ ผู้ใช้ {interaction.user} ({interaction.user.id}) พยายามใช้คำสั่ง setup โดยไม่มีสิทธิ์")
        return

    guild_id = interaction.guild.id

    category = await interaction.guild.create_category("ข้อความนิรนาม")
    input_channel = await category.create_text_channel("ส่งข้อความนิรนาม")
    announce_channel = await category.create_text_channel("ประกาศข้อความนิรนาม")

    guild_settings[guild_id] = {
        'input_channel_id': input_channel.id,
        'announce_channel_id': announce_channel.id
    }

    embed = discord.Embed(
        title="📩 ให้พรี่โตส่งข้อความแทนคุณ",
        description="กดปุ่มเพื่อเริ่มการส่งข้อความ",
        color=discord.Color.blue()
    )

    view = View()
    view.add_item(StartMessageButton())

    await input_channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ ระบบ setup ถูกตั้งค่าเรียบร้อย\n(สามารถเปลี่ยนชื่อห้องและจัดเรียงตามความสะดวกได้เลย)", ephemeral=True)
    await log_message(f"⚙️ ระบบ setup ถูกตั้งค่าในเซิร์ฟเวอร์: {interaction.guild.name} โดย {interaction.user} ({interaction.user.id})")

server_on()
bot.run(TOKEN)
