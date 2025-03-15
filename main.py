import discord
from discord.ext import commands
import os
from myserver import server_on

TOKEN = os.getenv("TOKEN")
ANNOUNCE_CHANNEL_ID = 1350128705648984197  # ห้องที่บอทจะส่งข้อความไป
MESSAGE_PROMPT_CHANNEL_ID = 1350161594985746567  # ห้องที่ส่ง Embed พร้อมปุ่ม

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

server_on()  # เปิดเซิร์ฟเวอร์ HTTP สำหรับ Render

class RecipientSelectView(discord.ui.View):
    """เมนูให้เลือกผู้รับข้อความ"""
    def __init__(self, message_content):
        super().__init__(timeout=60)
        self.message_content = message_content

        options = [
            discord.SelectOption(label=member.display_name, value=str(member.id))
            for member in bot.get_all_members() if not member.bot
        ]
        
        self.select_menu = discord.ui.Select(
            placeholder="เลือกผู้รับ...",
            min_values=1,
            max_values=3,
            options=options
        )
        self.select_menu.callback = self.select_recipient
        self.add_item(self.select_menu)

    async def select_recipient(self, interaction: discord.Interaction):
        recipients = [interaction.guild.get_member(int(user_id)) for user_id in self.select_menu.values]
        mentions = " ".join([user.mention for user in recipients if user])
        final_message = f"{mentions}\n{self.message_content}"

        announce_channel = await bot.fetch_channel(ANNOUNCE_CHANNEL_ID)
        if announce_channel:
            await announce_channel.send(final_message)
            await interaction.response.send_message("✅ ข้อความถูกส่งเรียบร้อย!", ephemeral=True)

class MessageModal(discord.ui.Modal, title="📩 ฝากข้อความถึงใครบางคน"):
    """Modal สำหรับให้ผู้ใช้พิมพ์ข้อความ"""
    message = discord.ui.TextInput(label="พิมพ์ข้อความที่ต้องการส่ง", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()  # ปิด Modal
        await interaction.followup.send("📌 กรุณาเลือกผู้รับ:", view=RecipientSelectView(self.message.value), ephemeral=True)

class MessageButtonView(discord.ui.View):
    """สร้างปุ่มให้ผู้ใช้กดเพื่อเปิด Modal"""
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="📩 ส่งข้อความนิรนาม", style=discord.ButtonStyle.primary)
    async def send_anonymous_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MessageModal())

@bot.event
async def on_ready():
    print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
    await bot.tree.sync()

    # ส่ง Embed พร้อมปุ่มกด
    message_channel = await bot.fetch_channel(MESSAGE_PROMPT_CHANNEL_ID)
    if message_channel:
        embed = discord.Embed(
            title="📩 ฝากข้อความนิรนาม",
            description="กดปุ่มด้านล่างเพื่อส่งข้อความแบบไม่ระบุตัวตน!",
            color=discord.Color.blue()
        )
        await message_channel.send(embed=embed, view=MessageButtonView())

bot.run(TOKEN)
