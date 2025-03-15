import discord
from discord.ext import commands
import os
from myserver import server_on

TOKEN = os.getenv("TOKEN")
ANNOUNCE_CHANNEL_ID = 1350128705648984197  # ห้องที่บอทจะส่งข้อความไป

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

server_on()  # เปิดเซิร์ฟเวอร์ HTTP สำหรับ Render

class RecipientSelectView(discord.ui.View):
    """เมนูเลือกผู้รับแบบแบ่งหน้า"""
    def __init__(self, message_content, members, page=0):
        super().__init__(timeout=60)
        self.message_content = message_content
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
        mentions = " ".join([user.mention for user in recipients if user])
        final_message = f"{mentions}\n{self.message_content}"

        announce_channel = await bot.fetch_channel(ANNOUNCE_CHANNEL_ID)
        if announce_channel:
            await announce_channel.send(final_message)
            await interaction.response.send_message("✅ ข้อความถูกส่งเรียบร้อย!", ephemeral=True)

class PreviousPageButton(discord.ui.Button):
    """ปุ่มย้อนกลับ"""
    def __init__(self, view):
        super().__init__(label="◀️", style=discord.ButtonStyle.secondary)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page -= 1
        self.view_ref.update_select_menu()
        await interaction.response.edit_message(view=self.view_ref)

class NextPageButton(discord.ui.Button):
    """ปุ่มไปหน้าถัดไป"""
    def __init__(self, view):
        super().__init__(label="▶️", style=discord.ButtonStyle.secondary)
        self.view_ref = view

    async def callback(self, interaction: discord.Interaction):
        self.view_ref.page += 1
        self.view_ref.update_select_menu()
        await interaction.response.edit_message(view=self.view_ref)

class MessageModal(discord.ui.Modal, title="📩 ฝากข้อความถึงใครบางคน"):
    """Modal ให้ผู้ใช้พิมพ์ข้อความ"""
    message = discord.ui.TextInput(label="พิมพ์ข้อความที่ต้องการส่ง", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        all_members = [member for member in interaction.guild.members if not member.bot]
        await interaction.response.send_message("📌 กรุณาเลือกผู้รับ:", view=RecipientSelectView(self.message.value, all_members), ephemeral=True)

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

@bot.command()
async def ping(ctx):
    """เช็คสถานะบอท"""
    await ctx.send("🏓 Pong! บอทยังออนไลน์อยู่!")

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
