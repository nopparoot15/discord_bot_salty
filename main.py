import discord
from discord.ext import commands
import os
import logging
from myserver import server_on

# ตั้งค่าระบบ logging
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
ANNOUNCE_CHANNEL_ID = 1350128705648984197
LOG_CHANNEL_ID = 1350380441504448512

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
server_on()  # เปิดเซิร์ฟเวอร์ HTTP

async def log_message(sender: discord.Member, recipient: discord.Member, message: str):
    """บันทึก log ของการส่งข้อความ"""
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    log_text = (f"📌 **ข้อความนิรนามถูกส่ง**\n"
                f"👤 **ผู้ส่ง:** {sender} (ID: {sender.id})\n"
                f"🎯 **ผู้รับ:** {recipient} (ID: {recipient.id})\n"
                f"💬 **เนื้อหา:** {message}")
    if log_channel:
        try:
            await log_channel.send(log_text)
        except discord.Forbidden:
            logging.error("❌ บอทไม่มีสิทธิ์ส่ง log!")
    else:
        logging.info(log_text)

@bot.event
async def on_ready():
    logging.info(f"✅ บอทออนไลน์: {bot.user}")
    try:
        await bot.tree.sync()
        logging.info("✅ คำสั่ง Slash ถูกซิงค์แล้ว!")
    except Exception as e:
        logging.error(f"❌ ซิงค์คำสั่ง Slash ล้มเหลว: {e}")

class MessageModal(discord.ui.Modal, title="📩 ฝากข้อความ"):
    recipient = discord.ui.TextInput(label="กรอก ID ผู้รับ", required=True)
    message = discord.ui.TextInput(label="ข้อความ", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        recipient_id = self.recipient.value.strip()
        message_content = self.message.value
        
        recipient = interaction.guild.get_member(int(recipient_id))
        if not recipient or recipient.bot:
            await interaction.response.send_message("❌ ไม่พบผู้รับ หรือไม่สามารถส่งหาบอทได้", ephemeral=True)
            return
        
        try:
            await recipient.send(message_content)
            await log_message(interaction.user, recipient, message_content)
            await interaction.response.send_message("✅ ข้อความถูกส่งแล้ว!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ ไม่สามารถส่งข้อความถึงผู้รับ", ephemeral=True)

class SetupButtonView(discord.ui.View):
    """View สำหรับปุ่มส่งข้อความนิรนาม"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 ส่งข้อความนิรนาม", style=discord.ButtonStyle.primary)
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MessageModal())

@bot.tree.command(name="setup", description="ตั้งค่าปุ่มส่งข้อความ")
async def setup(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📩 ฝากข้อความนิรนาม",
        description="กดปุ่มด้านล่างเพื่อส่งข้อความแบบไม่ระบุตัวตน!",
        color=discord.Color.blue()
    )
    await interaction.response.defer(thinking=True)
    
    try:
        await interaction.channel.send(embed=embed, view=SetupButtonView())
        await interaction.followup.send("✅ ปุ่มถูกสร้างแล้ว!", ephemeral=True)
        logging.info("✅ /setup ทำงานสำเร็จ!")
    except Exception as e:
        logging.error(f"❌ เกิดข้อผิดพลาดใน /setup: {e}")
        await interaction.followup.send("❌ มีข้อผิดพลาด", ephemeral=True)

bot.run(TOKEN)
