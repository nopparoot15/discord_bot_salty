import discord
from discord.ext import commands
import os
import logging
from myserver import server_on

# ตั้งค่าระบบ logging เพื่อบันทึกข้อมูลลง console
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
ANNOUNCE_CHANNEL_ID = 1350128705648984197  # ห้องที่บอทจะส่งข้อความไป
LOG_CHANNEL_ID = 1350380441504448512  # ห้อง logs ที่ใช้บันทึกข้อมูล

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

server_on()  # เปิดเซิร์ฟเวอร์ HTTP สำหรับ Render

async def log_message(sender: discord.Member, recipients: list, message: str):
    """บันทึก log ว่าใครเป็นผู้ส่งข้อความไปหาใคร"""
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    log_text = (f"📌 **ข้อความนิรนามถูกส่ง**\n"
                f"👤 **ผู้ส่ง:** {sender} (ID: {sender.id})\n"
                f"🎯 **ผู้รับ:** {', '.join([f'{user} (ID: {user.id})' for user in recipients])}\n"
                f"💬 **เนื้อหา:** {message}")
    
    if log_channel:
        try:
            await log_channel.send(log_text)
        except discord.Forbidden:
            logging.error("❌ บอทไม่มีสิทธิ์ส่ง log ไปยังห้อง logs!")
    else:
        logging.info(log_text)

class MessageModal(discord.ui.Modal, title="📩 ฝากข้อความถึงใครบางคน"):
    message = discord.ui.TextInput(label="พิมพ์ข้อความที่ต้องการส่ง", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        all_members = [member for member in interaction.guild.members if not member.bot]
        if not all_members:
            await interaction.response.send_message("❌ ไม่พบสมาชิกในเซิร์ฟเวอร์", ephemeral=True)
            return
        await interaction.response.send_message("📌 กรุณาเลือกผู้รับ:", view=RecipientSelectView(self.message.value, interaction.user, all_members), ephemeral=True)

class SetupButton(discord.ui.View):
    """ปุ่มเปิด MessageModal สำหรับส่งข้อความนิรนาม"""
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="📩 ส่งข้อความนิรนาม", style=discord.ButtonStyle.primary)
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MessageModal())

@bot.event
async def on_ready():
    logging.info(f"✅ บอทออนไลน์: {bot.user}")
    try:
        synced_guilds = await bot.tree.sync()
        logging.info(f"✅ ซิงค์คำสั่ง Slash สำเร็จใน {len(synced_guilds)} เซิร์ฟเวอร์!")
    except Exception as e:
        logging.error(f"❌ ไม่สามารถซิงค์คำสั่ง Slash: {e}")

@bot.tree.command(name="sync", description="ซิงค์คำสั่ง Slash (Admin เท่านั้น)")
@commands.guild_only()
async def sync(interaction: discord.Interaction):
    if interaction.user.guild_permissions.administrator:
        await bot.tree.sync()
        await interaction.response.send_message("✅ คำสั่ง Slash ซิงค์แล้ว!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)

@bot.tree.command(name="ping", description="เช็คสถานะบอท")
@commands.guild_only()
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000, 2)
    await interaction.response.send_message(f"🏓 Pong! บอทยังออนไลน์อยู่! (Latency: {latency}ms)")

@bot.tree.command(name="setup", description="ตั้งค่าการส่งข้อความนิรนาม")
@commands.guild_only()
async def setup(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        return

    embed = discord.Embed(
        title="📩 ฝากข้อความนิรนาม",
        description="กดปุ่มด้านล่างเพื่อส่งข้อความแบบไม่ระบุตัวตน!",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=SetupButton())
    await interaction.response.send_message("✅ ปุ่มถูกสร้างเรียบร้อยแล้ว!", ephemeral=True)

bot.run(TOKEN)
