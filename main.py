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

async def log_message(sender: discord.Member, recipients: list, message: str):
    """บันทึก log ของการส่งข้อความ"""
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    log_text = (f"📌 **ข้อความนิรนามถูกส่ง**\n"
                f"👤 **ผู้ส่ง:** {sender} (ID: {sender.id})\n"
                f"🎯 **ผู้รับ:** {', '.join([f'{user} (ID: {user.id})' for user in recipients])}\n"
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

class SetupButtonView(discord.ui.View):
    """View สำหรับปุ่มส่งข้อความนิรนาม"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 ส่งข้อความนิรนาม", style=discord.ButtonStyle.primary)
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MessageModal())

class MessageModal(discord.ui.Modal, title="📩 ฝากข้อความ"):
    message = discord.ui.TextInput(label="ข้อความ", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        all_members = [m for m in interaction.guild.members if not m.bot]
        if not all_members:
            await interaction.response.send_message("❌ ไม่มีสมาชิกในเซิร์ฟเวอร์", ephemeral=True)
            return
        await interaction.response.send_message("📌 เลือกผู้รับ:", view=RecipientSelectView(self.message.value, interaction.user, all_members), ephemeral=True)

class RecipientSelectView(discord.ui.View):
    """View สำหรับเลือกผู้รับ"""
    def __init__(self, message, sender, members, page=0):
        super().__init__(timeout=60)
        self.message = message
        self.sender = sender
        self.members = members
        self.page = page
        self.page_size = 25
        self.update_select_menu()

    def update_select_menu(self):
        self.clear_items()
        start, end = self.page * self.page_size, (self.page + 1) * self.page_size
        paged_members = self.members[start:end]
        options = [discord.SelectOption(label=m.display_name, value=str(m.id)) for m in paged_members]
        
        if options:
            select_menu = discord.ui.Select(
                placeholder=f"เลือกผู้รับ... (หน้า {self.page + 1})",
                min_values=1, max_values=min(3, len(options)),
                options=options
            )
            select_menu.callback = self.select_recipient_callback
            self.add_item(select_menu)

    async def select_recipient_callback(self, interaction: discord.Interaction):
        recipients = [interaction.guild.get_member(int(user_id)) for user_id in interaction.data["values"]]
        recipients = [user for user in recipients if user]
        if not recipients:
            await interaction.response.send_message("❌ ไม่พบผู้รับ", ephemeral=True)
            return
        
        mentions = " ".join([user.mention for user in recipients])
        final_message = f"{mentions}\n{self.message}"
        announce_channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
        
        if announce_channel:
            await announce_channel.send(final_message)
        else:
            for user in recipients:
                try:
                    await user.send(self.message)
                except discord.Forbidden:
                    logging.error(f"ส่งข้อความถึง {user.display_name} ไม่สำเร็จ")
        
        await log_message(self.sender, recipients, self.message)
        await interaction.response.send_message("✅ ข้อความถูกส่งแล้ว!", ephemeral=True)

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
