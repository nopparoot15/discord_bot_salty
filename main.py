import os
import time
import asyncio
import discord
from discord.ext import commands

from myserver import server_on

# Configuration
TOKEN = os.getenv("TOKEN")
ANNOUNCE_CHANNEL_ID = 1350128705648984197
MESSAGE_INPUT_CHANNEL_ID = 1350161594985746567
LOG_CHANNEL_ID = 1350380441504448512

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def log_message(content):
    """Log a message to the log channel."""
    print(f"[LOG] {content}")
    await _send_log(content)

async def _send_log(content):
    try:
        log_channel = await bot.fetch_channel(LOG_CHANNEL_ID)
        await log_channel.send(content)
    except discord.errors.NotFound:
        print("❌ ไม่พบช่อง logs กรุณาตรวจสอบ LOG_CHANNEL_ID")
    except discord.errors.Forbidden:
        print("❌ บอทไม่มีสิทธิ์ส่งข้อความไปยังช่อง logs")

@bot.event
async def on_ready():
    """Event handler for when the bot is ready."""
    if not getattr(bot, 'synced', False):
        await bot.tree.sync()
        bot.synced = True
        print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
        await log_message("✅ บอทเริ่มทำงานเรียบร้อย")

@bot.event
async def on_message(message):
    """Event handler for when a message is received."""
    if message.author.bot:
        return

    if message.channel.id == MESSAGE_INPUT_CHANNEL_ID:
        content = message.content
        mentions = []
        remaining_words = []

        # Process mentions
        for word in content.split():
            if word.startswith('@'):
                username = word[1:]
                member = discord.utils.get(message.guild.members, name=username) or discord.utils.get(message.guild.members, display_name=username)
                if member:
                    mentions.append(f"<{member.display_name}>")
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
            current_time = time.time()
            if not getattr(bot, 'last_message_content', None) or (bot.last_message_content != final_message and current_time - getattr(bot, 'last_message_time', 0) > 2):
                bot.last_message_content = final_message
                bot.last_message_time = current_time
                await announce_channel.send(final_message, allowed_mentions=discord.AllowedMentions(users=True, roles=True, everyone=False))

            # Log message content and mentions
            log_entry = f"📩 ข้อความถูกส่งโดย {message.author} ({message.author.id}) : {content}"
            if mentions:
                log_entry += f" | Mentions: {', '.join(mentions)}"
            await log_message(log_entry)

            # Delete the original message
            try:
                await message.delete()
            except discord.errors.Forbidden:
                print("❌ บอทไม่มีสิทธิ์ลบข้อความในห้องนี้")

        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            error_msg = f"❌ เกิดข้อผิดพลาดในการส่งข้อความ: {str(e)}"
            print(error_msg)
            await log_message(error_msg)

    await bot.process_commands(message)

@bot.command()
async def ping(ctx):
    """Ping command to check if the bot is online."""
    await ctx.send('🏓 Pong! บอทยังออนไลน์อยู่!')
    await log_message(f"🏓 Pong! มีการใช้คำสั่ง ping โดย {ctx.author} ({ctx.author.id})")

@bot.tree.command(name="setup", description="ตั้งค่าระบบส่งข้อความนิรนาม")
async def setup(interaction: discord.Interaction):
    """Setup command to initialize the anonymous message system."""
    async for message in interaction.channel.history(limit=10):
        if message.author == bot.user and message.embeds:
            await interaction.response.send_message("⚠️ ระบบได้ถูกตั้งค่าไว้แล้ว", ephemeral=True)
            return
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        await log_message(f"⚠️ ผู้ใช้ {interaction.user} ({interaction.user.id}) พยายามใช้คำสั่ง setup โดยไม่มีสิทธิ์")
        return

    embed = discord.Embed(
        title="📩 ให้พรี่โตส่งข้อความแทนคุณ",
        description="พิมพ์ข้อความในช่องนี้เพื่อส่งข้อความแบบไม่ระบุตัวตน\nสามารถส่งข้อความที่ต้องการได้โดยไม่ต้องเปิดเผยตัวตน",
        color=discord.Color.blue()
    )

    await interaction.channel.send(embed=embed)
    await log_message(f"⚙️ ระบบ setup ถูกตั้งค่าในช่อง: {interaction.channel.name}")

@bot.command()
async def update(ctx):
    """Command to update and restart the bot."""
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

@bot.command()
async def mute_channel(ctx):
    """Command to mute a specific channel."""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้")
        return

    channel_id = 1350161594985746567  # ID ของชาแนลที่ต้องการปิดแจ้งเตือน
    channel = bot.get_channel(channel_id)
    if not channel:
        await ctx.send(f"❌ ไม่พบช่องที่มี ID {channel_id}")
        return

    try:
        await channel.set_permissions(ctx.guild.default_role, send_messages=False, mention_everyone=False)
        await ctx.send(f"🔇 ปิดแจ้งเตือนและ @mention สำหรับชาแนลที่มี ID {channel_id} เรียบร้อยแล้ว")
        await log_message(f"🔇 ปิดแจ้งเตือนและ @mention สำหรับชาแนลที่มี ID {channel_id} โดย {ctx.author} ({ctx.author.id})")
    except discord.errors.Forbidden:
        await ctx.send("❌ บอทไม่มีสิทธิ์เปลี่ยนการตั้งค่าของชาแนลนี้")
        await log_message(f"❌ บอทไม่มีสิทธิ์เปลี่ยนการตั้งค่าของชาแนลที่มี ID {channel_id}")

# Start the server and run the bot
server_on()
bot.run(TOKEN)
