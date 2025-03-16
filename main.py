import os
import sys
import time
import asyncio
import requests
import discord
from discord.ext import commands
from discord import app_commands
from myserver import server_on

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
INPUT_CHANNEL_ID = os.getenv("INPUT_CHANNEL_ID")
ANNOUNCE_CHANNEL_ID = os.getenv("ANNOUNCE_CHANNEL_ID")

if not TOKEN or not WEBHOOK_URL or not INPUT_CHANNEL_ID or not ANNOUNCE_CHANNEL_ID:
    print("❌ โปรดตั้งค่า environment variables (TOKEN, WEBHOOK_URL, INPUT_CHANNEL_ID และ ANNOUNCE_CHANNEL_ID)")
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

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
    print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
    await log_message("✅ บอทเริ่มทำงานเรียบร้อย")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == int(INPUT_CHANNEL_ID):
        content = message.content
        mentions = []
        remaining_words = []

        for word in content.split():
            if word.startswith('@'):
                username = word[1:]
                member = discord.utils.get(message.guild.members, name=username) or discord.utils.get(message.guild.members, display_name=username)
                if member:
                    mentions.append(f"@{member.display_name}")
                else:
                    remaining_words.append(word)
            else:
                remaining_words.append(word)

        mention_text = " ".join(mentions)
        final_message = " ".join(remaining_words)

        if mentions and final_message.strip():
            final_message = f"{mention_text}\n{final_message}"

        try:
            announce_channel = await bot.fetch_channel(int(ANNOUNCE_CHANNEL_ID))
            
            current_time = time.time()
            if not getattr(bot, 'last_message_content', None) or (bot.last_message_content != final_message and current_time - getattr(bot, 'last_message_time', 0) > 2):
                bot.last_message_content = final_message
                bot.last_message_time = current_time
                await announce_channel.send(final_message, allowed_mentions=discord.AllowedMentions(users=True, roles=True, everyone=False))

            log_entry = f"📩 ข้อความถูกส่งโดย {message.author} ({message.author.id}) : {content}"
            if mentions:
                log_entry += f" | Mentions: {', '.join(mentions)}"
            await log_message(log_entry)
            
            try:
                await message.delete()
            except discord.errors.Forbidden:
                print("❌ บอทไม่มีสิทธิ์ลบข้อความในห้องนี้")

        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            error_msg = f"❌ เกิดข้อผิดพลาดในการส่งข้อความ: {str(e)}"
            print(error_msg)
            await log_message(error_msg)

    await bot.process_commands(message)

@bot.tree.command(name="setup", description="ตั้งค่าระบบส่งข้อความนิรนาม")
async def setup(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        await log_message(f"⚠️ ผู้ใช้ {interaction.user} ({interaction.user.id}) พยายามใช้คำสั่ง setup โดยไม่มีสิทธิ์")
        return

    embed = discord.Embed(
        title="📩 การตั้งค่าระบบส่งข้อความนิรนาม",
        description=(
            "ยินดีต้อนรับสู่ระบบส่งข้อความนิรนาม! ระบบนี้ช่วยให้คุณสามารถส่งข้อความแบบไม่ระบุตัวตนได้ เพื่อให้คุณสามารถแสดงความคิดเห็นหรือส่งข้อความถึงสมาชิกในเซิร์ฟเวอร์ได้อย่างปลอดภัย\n\n"
            "📋 **วิธีการใช้งานห้องส่งข้อความนิรนาม**:\n"
            "1. **พิมพ์ข้อความของคุณ**: เข้าไปที่ช่องที่กำหนดสำหรับส่งข้อความนิรนามและพิมพ์ข้อความที่คุณต้องการส่ง\n"
            "2. **@mention สมาชิก** (ถ้าต้องการ): คุณสามารถ @mention สมาชิกได้โดยพิมพ์ @username เพื่อให้ข้อความถูกส่งถึงสมาชิกที่คุณต้องการ\n"
            "3. **ข้อความจะถูกส่งไปยังช่องประกาศ**: ข้อความของคุณจะถูกส่งไปยังช่องประกาศโดยอัตโนมัติหลังจากที่คุณส่งข้อความในช่องที่กำหนด\n\n"
            "📢 **โปรดทราบ**: ข้อความต้นฉบับของคุณจะถูกลบออกจากช่องที่กำหนดหลังจากที่ข้อความถูกส่งไปยังช่องประกาศเรียบร้อยแล้ว เพื่อรักษาความเป็นส่วนตัวของคุณ"
        ),
        color=discord.Color.blue()
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)
    await log_message(f"⚙️ คำสั่ง setup ถูกใช้งานในเซิร์ฟเวอร์: {interaction.guild.name} โดย {interaction.user} ({interaction.user.id})")

server_on()
bot.run(TOKEN)
