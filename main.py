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

class PreviousPageButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(label="⬅️ ก่อนหน้า", style=discord.ButtonStyle.primary)
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        self.view.page -= 1
        self.view.update_select_menu()
        await interaction.response.edit_message(view=self.view)

class NextPageButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(label="➡️ ถัดไป", style=discord.ButtonStyle.primary)
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        self.view.page += 1
        self.view.update_select_menu()
        await interaction.response.edit_message(view=self.view)

class RecipientSelectView(discord.ui.View):
    """เมนูเลือกผู้รับแบบแบ่งหน้า"""
    def __init__(self, message_content, sender, members, page=0):
        super().__init__(timeout=60)
        self.message_content = message_content
        self.sender = sender
        self.members = members
        self.page = page
        self.page_size = 25
        self.update_select_menu()

    def update_select_menu(self):
        self.clear_items()
        start, end = self.page * self.page_size, (self.page + 1) * self.page_size
        paged_members = self.members[start:end]
        options = [discord.SelectOption(label=member.display_name, value=str(member.id)) for member in paged_members]

        if options:
            select_menu = discord.ui.Select(
                placeholder=f"เลือกผู้รับ... (หน้า {self.page + 1}/{(len(self.members) - 1) // self.page_size + 1})",
                min_values=1, max_values=min(3, len(options)),
                options=options
            )
            select_menu.callback = self.select_recipient
            self.add_item(select_menu)

        if self.page > 0:
            self.add_item(PreviousPageButton(self))
        if end < len(self.members):
            self.add_item(NextPageButton(self))

    async def select_recipient(self, interaction: discord.Interaction):
        recipients = [interaction.guild.get_member(int(user_id)) for user_id in interaction.data["values"]]
        recipients = [user for user in recipients if user]
        if not recipients:
            await interaction.response.send_message("❌ ไม่พบผู้รับ กรุณาลองใหม่", ephemeral=True)
            return
        mentions = " ".join([user.mention for user in recipients])
        final_message = f"{mentions}\n{self.message_content}"
        announce_channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
        if announce_channel:
            await announce_channel.send(final_message)
        for user in recipients:
            try:
                await user.send(self.message_content)
            except discord.Forbidden:
                logging.error(f"ไม่สามารถส่งข้อความถึง {user.display_name}")
        await log_message(self.sender, recipients, self.message_content)
        await interaction.response.send_message("✅ ข้อความถูกส่งแล้ว!", ephemeral=True)

@bot.event
async def on_ready():
    logging.info(f"✅ บอทออนไลน์: {bot.user}")
    try:
        synced_guilds = await bot.tree.sync()
        logging.info(f"✅ ซิงค์คำสั่ง Slash สำเร็จใน {len(synced_guilds)} เซิร์ฟเวอร์!")
    except Exception as e:
        logging.error(f"❌ ไม่สามารถซิงค์คำสั่ง Slash: {e}")

@bot.tree.command(name="sync", description="ซิงค์คำสั่ง Slash (Admin เท่านั้น)")
async def sync(interaction: discord.Interaction):
    if interaction.user.guild_permissions.administrator:
        await bot.tree.sync()
        await interaction.response.send_message("✅ คำสั่ง Slash ซิงค์แล้ว!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)

@bot.tree.command(name="ping", description="เช็คสถานะบอท")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000, 2)
    await interaction.response.send_message(f"🏓 Pong! บอทยังออนไลน์อยู่! (Latency: {latency}ms)")

@bot.tree.command(name="setup", description="ตั้งค่าการส่งข้อความนิรนาม")
async def setup(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        return

    embed = discord.Embed(
        title="📩 ฝากข้อความนิรนาม",
        description="กดปุ่มด้านล่างเพื่อส่งข้อความแบบไม่ระบุตัวตน!",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=MessageModal())
    await interaction.response.send_message("✅ ปุ่มถูกสร้างเรียบร้อยแล้ว!", ephemeral=True)

bot.run(TOKEN)
