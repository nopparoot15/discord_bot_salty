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
    
    log_text = f"📌 **ข้อความนิรนามถูกส่ง**\n👤 **ผู้ส่ง:** {sender} (ID: {sender.id})\n" \
               f"🎯 **ผู้รับ:** {', '.join([f'{user} (ID: {user.id})' for user in recipients])}\n" \
               f"💬 **เนื้อหา:** {message}"
    
    if log_channel:
        try:
            await log_channel.send(log_text)
        except discord.Forbidden:
            logging.error("❌ บอทไม่มีสิทธิ์ส่ง log ไปยังห้อง logs!")
    else:
        logging.info(log_text)

class RecipientSelectView(discord.ui.View):
    """เมนูเลือกผู้รับแบบแบ่งหน้า"""
    def __init__(self, message_content, sender, members, page=0):
        super().__init__(timeout=60)
        self.message_content = message_content
        self.sender = sender  # เก็บข้อมูลผู้ส่ง
        self.members = members
        self.page = page
        self.page_size = 25  # จำกัดไม่เกิน 25 คนต่อหน้า
        self.update_select_menu()

    def update_select_menu(self):
        """อัปเดต Select Menu ตามหน้าปัจจุบัน"""
        self.clear_items()  # ลบปุ่มก่อนหน้า
        start = self.page * self.page_size
        end = start + self.page_size
        paged_members = self.members[start:end]

        options = [
            discord.SelectOption(label=member.display_name, value=str(member.id))
            for member in paged_members
        ]

        if options:
            select_menu = discord.ui.Select(
                placeholder=f"เลือกผู้รับ... (หน้า {self.page + 1}/{(len(self.members) - 1) // self.page_size + 1})",
                min_values=1,
                max_values=min(3, len(options)),  # จำกัดเลือกสูงสุด 3 คน
                options=options
            )
            select_menu.callback = self.select_recipient
            self.add_item(select_menu)

        # เพิ่มปุ่มเปลี่ยนหน้า
        if self.page > 0:
            self.add_item(PreviousPageButton(self))
        if end < len(self.members):
            self.add_item(NextPageButton(self))

    async def select_recipient(self, interaction: discord.Interaction):
        recipients = [interaction.guild.get_member(int(user_id)) for user_id in interaction.data["values"]]
        recipients = [user for user in recipients if user]  # ตรวจสอบว่าผู้ใช้มีอยู่จริง
        if not recipients:
            await interaction.response.send_message("❌ ไม่พบผู้รับ กรุณาลองใหม่", ephemeral=True)
            return

        mentions = " ".join([user.mention for user in recipients])
        final_message = f"{mentions}\n{self.message_content}"

        try:
            announce_channel = await bot.fetch_channel(ANNOUNCE_CHANNEL_ID)
            if announce_channel:
                await announce_channel.send(final_message)
                await interaction.response.send_message("✅ ข้อความถูกส่งเรียบร้อย!", ephemeral=True)
            else:
                raise ValueError("ไม่พบช่องที่กำหนด")
        except (discord.Forbidden, ValueError):
            logging.warning("ไม่สามารถส่งข้อความไปยัง ANNOUNCE_CHANNEL_ID ได้, กำลังส่งผ่าน DM")
            for user in recipients:
                try:
                    await user.send(self.message_content)
                except discord.Forbidden:
                    logging.error(f"ไม่สามารถส่งข้อความถึง {user.display_name}")

            await interaction.response.send_message("✅ ข้อความถูกส่งผ่าน DM แล้ว!", ephemeral=True)

        # บันทึก log
        await log_message(self.sender, recipients, self.message_content)

class MessageModal(discord.ui.Modal, title="📩 ฝากข้อความถึงใครบางคน"):
    """Modal ให้ผู้ใช้พิมพ์ข้อความ"""
    message = discord.ui.TextInput(label="พิมพ์ข้อความที่ต้องการส่ง", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        all_members = [member for member in interaction.guild.members if not member.bot]
        if not all_members:
            await interaction.response.send_message("❌ ไม่พบสมาชิกในเซิร์ฟเวอร์", ephemeral=True)
            return
        await interaction.response.send_message("📌 กรุณาเลือกผู้รับ:", view=RecipientSelectView(self.message.value, interaction.user, all_members), ephemeral=True)

@bot.event
async def on_ready():
    print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
    try:
        await bot.tree.sync()
        print("✅ คำสั่ง Slash ถูกซิงค์แล้ว!")
    except Exception as e:
        logging.error(f"❌ ไม่สามารถซิงค์คำสั่ง Slash: {e}")

@bot.tree.command(name="ping", description="เช็คสถานะบอท")
async def ping(interaction: discord.Interaction):
    """คำสั่ง /ping เพื่อตรวจสอบว่าบอทยังออนไลน์อยู่และแสดงค่า latency"""
    latency = round(bot.latency * 1000, 2)  # คำนวณ latency (แปลงเป็น ms)
    await interaction.response.send_message(f"🏓 Pong! บอทยังออนไลน์อยู่! (Latency: {latency}ms)")

@bot.tree.command(name="setup", description="ตั้งค่าการส่งข้อความนิรนาม")
async def setup(interaction: discord.Interaction):
    """ให้แอดมินพิมพ์ /setup เพื่อสร้างปุ่มใช้งานบอท"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        return

    embed = discord.Embed(
        title="📩 ฝากข้อความนิรนาม",
        description="กดปุ่มด้านล่างเพื่อส่งข้อความแบบไม่ระบุตัวตน!",
        color=discord.Color.blue()
    )

    await interaction.channel.send(embed=embed, view=MessageButtonView())
    await interaction.response.send_message("✅ ปุ่มถูกสร้างเรียบร้อยแล้ว!", ephemeral=True)

bot.run(TOKEN)
