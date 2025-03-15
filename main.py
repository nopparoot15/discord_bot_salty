import discord
from discord.ext import commands
import os
import sys
import time
from myserver import server_on

TOKEN = os.getenv("TOKEN")  # ใส่ token ใน Environment
ANNOUNCE_CHANNEL_ID = 1350128705648984197
MESSAGE_INPUT_CHANNEL_ID = 1350161594985746567  # ID ห้องรับข้อความ
LOG_CHANNEL_ID = 1350380441504448512  # ID ห้องเก็บ logs

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def log_message(content):
    asyncio.create_task(_send_log(content))  # ทำให้ log ทำงานแบบ async
    try:
        log_channel = await bot.fetch_channel(LOG_CHANNEL_ID)
        await log_channel.send(content)
    except discord.errors.NotFound:
        print("❌ ไม่พบช่อง logs กรุณาตรวจสอบ LOG_CHANNEL_ID")
    except discord.errors.Forbidden:
        print("❌ บอทไม่มีสิทธิ์ส่งข้อความไปยังช่อง logs")

@bot.event
async def on_ready():
    print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
    if not hasattr(bot, 'synced'):
        await bot.tree.sync()
        bot.synced = True  # ป้องกันการ Sync ซ้ำ
    await log_message("✅ บอทเริ่มทำงานเรียบร้อย")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.channel.id == MESSAGE_INPUT_CHANNEL_ID:
        content = message.content
        mentions = []
        remaining_words = []

        for word in content.split():
            if word.startswith('@'):
                username = word[1:]
                member = discord.utils.get(message.guild.members, name=username) or discord.utils.get(message.guild.members, display_name=username)
                if member:
                    mentions.append(member.mention)  # แปลงเป็น mention จริงเฉพาะตอนส่งไปที่ ANNOUNCE_CHANNEL_ID
                else:
                    remaining_words.append(word)
            else:
                remaining_words.append(word)

        mention_text = " ".join(mentions)
        final_message = " ".join(remaining_words)

        if mentions and final_message.strip():
            final_message = f"{mention_text}\n{final_message}"

        try:
            announce_channel = await bot.fetch_channel(ANNOUNCE_CHANNEL_ID)
            import time

            if not hasattr(bot, 'last_message_content') or bot.last_message_content != final_message or time.time() - getattr(bot, 'last_message_time', 0) > 2:
                bot.last_message_content = final_message
                bot.last_message_time = time.time()
                
                await announce_channel.send(final_message, allowed_mentions=discord.AllowedMentions(users=True, roles=True, everyone=False))
            await message.delete()
            if not hasattr(bot, 'last_log_message') or bot.last_log_message != final_message:
                bot.last_log_message = final_message
                await log_message(f"📩 ข้อความถูกส่งโดย {message.author} ({message.author.id})")
            return  # ป้องกันบอท process command โดยไม่จำเป็น
        except discord.errors.NotFound:
            error_msg = "❌ ไม่พบช่องประกาศ กรุณาตรวจสอบ ANNOUNCE_CHANNEL_ID"
            print(error_msg)
            await log_message(error_msg)
        except discord.errors.Forbidden:
            error_msg = "❌ บอทไม่มีสิทธิ์ส่งข้อความไปยังช่องประกาศ"
            print(error_msg)
            await log_message(error_msg)

    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    await ctx.send('🏓 Pong! บอทยังออนไลน์อยู่!')
    await log_message(f"🏓 Pong! มีการใช้คำสั่ง ping โดย {ctx.author} ({ctx.author.id})")

@bot.tree.command(name="setup", description="ตั้งค่าระบบส่งข้อความนิรนาม")
async def setup(interaction: discord.Interaction):
    # ตรวจสอบว่าข้อความ Embed นี้มีอยู่แล้วหรือไม่
    async for message in interaction.channel.history(limit=10):  # ตรวจแค่ 10 ข้อความล่าสุด
        if message.author == bot.user and message.embeds:
            await interaction.response.send_message("⚠️ ระบบได้ถูกตั้งค่าไว้แล้ว", ephemeral=True)
            return
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        await log_message(f"⚠️ ผู้ใช้ {interaction.user} ({interaction.user.id}) พยายามใช้คำสั่ง setup โดยไม่มีสิทธิ์")
        return

    embed = discord.Embed(
        title="📩 ให้พรี่โตส่งข้อความแทนคุณ",
        description="พิมพ์ข้อความในช่องนี้เพื่อส่งข้อความแบบไม่ระบุตัวตน\nสามารถ @mention สมาชิกได้โดยพิมพ์ @username",
        color=discord.Color.blue()
    )

    await interaction.channel.send(embed=embed)
    await log_message(f"⚙️ ระบบ setup ถูกตั้งค่าในช่อง: {interaction.channel.name}")

@bot.command()
async def update(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้")
        return
    
    await ctx.send("🔄 กำลังอัปเดตบอท โปรดรอสักครู่...")
    await log_message("🔄 บอทกำลังรีสตาร์ทตามคำสั่งอัปเดต")
    try:
        os._exit(0)  # ใช้วิธีปิดบอท ให้โฮสต์รันใหม่เอง
    except Exception as e:
        await ctx.send(f"❌ ไม่สามารถรีสตาร์ทบอทได้: {e}")
        await log_message(f"❌ รีสตาร์ทบอทล้มเหลว: {e}")

server_on()  # เปิดเซิร์ฟเวอร์ HTTP สำหรับ Render
bot.run(TOKEN)
