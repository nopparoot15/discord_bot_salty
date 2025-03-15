import discord
from discord.ext import commands
import os
from myserver import server_on

TOKEN = os.getenv("TOKEN")
ANNOUNCE_CHANNEL_ID = 1350128705648984197  # ห้องที่บอทจะส่งข้อความไป
REACTION_EMOJI = "📩"  # อีโมจิที่ต้องกด
MESSAGE_PROMPT_CHANNEL_ID = 1350161594985746567  # ห้องที่ส่ง Embed พร้อมปุ่ม

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

server_on()  # เปิดเซิร์ฟเวอร์ HTTP สำหรับ Render

class MessageModal(discord.ui.Modal, title="📩 ฝากข้อความถึงใครบางคน"):
    message = discord.ui.TextInput(label="พิมพ์ข้อความที่ต้องการส่ง", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()  # ปิด Modal
        await interaction.followup.send(view=RecipientSelectView(self.message.value), ephemeral=True)

class RecipientSelectView(discord.ui.View):
    def __init__(self, message_content):
        super().__init__(timeout=60)
        self.message_content = message_content

    @discord.ui.select(placeholder="เลือกผู้รับ...", min_values=1, max_values=3, options=[])
    async def select_recipient(self, interaction: discord.Interaction, select: discord.ui.Select):
        recipients = [interaction.guild.get_member(int(user_id)) for user_id in select.values]
        mentions = " ".join([user.mention for user in recipients if user])
        final_message = f"{mentions}\n{self.message_content}"

        announce_channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
        if announce_channel:
            await announce_channel.send(final_message)
            await interaction.response.send_message("✅ ข้อความถูกส่งเรียบร้อย!", ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """โหลดสมาชิกของเซิร์ฟเวอร์ลงไปใน Select Menu"""
        members = [
            discord.SelectOption(label=member.display_name, value=str(member.id))
            for member in interaction.guild.members if not member.bot
        ]
        self.children[0].options = members
        return True

@bot.event
async def on_ready():
    print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
    await bot.tree.sync()

    # ส่ง Embed พร้อมปุ่มกดอีโมจิ
    message_channel = await bot.fetch_channel(MESSAGE_PROMPT_CHANNEL_ID)
    if message_channel:
        embed = discord.Embed(
            title="📩 ฝากข้อความนิรนาม",
            description=f"กด {REACTION_EMOJI} ด้านล่างเพื่อส่งข้อความแบบไม่ระบุตัวตน!",
            color=discord.Color.blue()
        )
        msg = await message_channel.send(embed=embed)
        await msg.add_reaction(REACTION_EMOJI)

@bot.event
async def on_reaction_add(reaction, user):
    """เมื่อมีคนกดอีโมจิ บอทจะเปิด Modal"""
    if user.bot:
        return

    if reaction.message.channel.id == MESSAGE_PROMPT_CHANNEL_ID and str(reaction.emoji) == REACTION_EMOJI:
        channel = await bot.fetch_channel(reaction.message.channel.id)
        message = await channel.fetch_message(reaction.message.id)

        # เช็คว่า User กดอีโมจิจริง
        if user in [reactor for react in message.reactions for reactor in await react.users().flatten()]:
            # สร้าง Interaction ที่จำเป็นในการเปิด Modal
            class FakeInteraction:
                def __init__(self, user):
                    self.user = user

                async def response(self):
                    return self

                async def send_modal(self, modal):
                    await user.send("📩 กรุณาพิมพ์ข้อความของคุณ:", view=modal)

            interaction = FakeInteraction(user)
            await interaction.send_modal(MessageModal())

bot.run(TOKEN)
