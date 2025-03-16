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

# Dictionary to store channel IDs for each guild
guild_settings = {}

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
    if not getattr(bot, 'synced', False):
        await bot.tree.sync()
        bot.synced = True
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

@bot.command()
async def ping(ctx):
    await ctx.send('🏓 Pong! บอทยังออนไลน์อยู่!')
    await log_message(f"🏓 Pong! มีการใช้คำสั่ง ping โดย {ctx.author} ({ctx.author.id})")

@bot.command()
async def update(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้")
        return
    
    await ctx.send("🔄 กำลังอัปเดตบอท โปรดรอสักครู่...")
    await log_message("🔄 บอทกำลังรีสตาร์ทตามคำสั่งอัปเดต")
    try:
        await bot.close()
        os._exit(0)
    except Exception as e:
        await ctx.send(f"❌ ไม่สามารถรีสตาร์ทบอทได้: {e}")
        await log_message(f"❌ รีสตาร์ทบอทล้มเหลว: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def delete(ctx, count: int, *, target: str = None):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้")
        return

    if target:
        if target.startswith('@'):
            username = target[1:]
            member = discord.utils.get(ctx.guild.members, name=username) or discord.utils.get(ctx.guild.members, display_name=username)
            if member:
                deleted = await ctx.channel.purge(limit=count, check=lambda m: m.author == member)
                await ctx.send(f"✅ ลบข้อความ {len(deleted)} ข้อความจาก {member.display_name}")
                await log_message(f"🗑️ ลบข้อความ {len(deleted)} ข้อความจาก {member.display_name} โดย {ctx.author} ({ctx.author.id})")
            else:
                await ctx.send(f"❌ ไม่พบผู้ใช้ที่ชื่อ {username}")
        else:
            await ctx.send("❌ กรุณาระบุชื่อผู้ใช้ที่ถูกต้อง")
    else:
        deleted = await ctx.channel.purge(limit=count)
        await ctx.send(f"✅ ลบข้อความ {len(deleted)} ข้อความ")
        await log_message(f"🗑️ ลบข้อความ {len(deleted)} ข้อความโดย {ctx.author} ({ctx.author.id})")

server_on()
bot.run(TOKEN)
