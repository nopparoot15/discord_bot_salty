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
GUILD_ID = 123456789012345678  # ใส่ ID ของเซิร์ฟเวอร์ที่ต้องการให้บอททำงาน

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

@bot.event
async def on_ready():
    logging.info(f"✅ บอทออนไลน์: {bot.user}")
    try:
        guild = discord.Object(id=GUILD_ID)
        await bot.tree.sync(guild=guild)
        logging.info(f"✅ ซิงค์คำสั่ง Slash ให้เซิร์ฟเวอร์ {GUILD_ID} สำเร็จ!")
    except Exception as e:
        logging.error(f"❌ ไม่สามารถซิงค์คำสั่ง Slash: {e}")

@bot.tree.command(name="sync", description="ซิงค์คำสั่ง Slash (Admin เท่านั้น)")
async def sync(interaction: discord.Interaction):
    if interaction.user.guild_permissions.administrator:
        guild = discord.Object(id=GUILD_ID)
        await bot.tree.sync(guild=guild)
        await interaction.response.send_message("✅ คำสั่ง Slash ซิงค์แล้ว!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)

@bot.tree.command(name="ping", description="เช็คสถานะบอท")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000, 2)
    await interaction.response.send_message(f"🏓 Pong! บอทยังออนไลน์อยู่! (Latency: {latency}ms)")

@bot.tree.command(name="setup", description="ตั้งค่าการส่งข้อความนิรนาม")
async def setup(interaction: discord.Interaction):
    logging.info(f"🔹 คำสั่ง /setup ถูกเรียกโดย {interaction.user} ใน {interaction.channel}")
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        return

    embed = discord.Embed(
        title="📩 ฝากข้อความนิรนาม",
        description="กดปุ่มด้านล่างเพื่อส่งข้อความแบบไม่ระบุตัวตน!",
        color=discord.Color.blue()
    )

    try:
        await interaction.channel.send(embed=embed, view=MessageButtonView())
        await interaction.response.send_message("✅ ปุ่มถูกสร้างเรียบร้อยแล้ว!", ephemeral=True)
    except Exception as e:
        logging.error(f"❌ เกิดข้อผิดพลาดใน /setup: {e}")
        await interaction.response.send_message("❌ มีข้อผิดพลาด ลองตรวจสอบ log", ephemeral=True)

bot.run(TOKEN)
