import os
import sys
import time
import asyncio
import requests
import discord
from discord.ext import commands
from discord import app_commands
from myserver import server_on
import psycopg2

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# เชื่อมต่อกับ PostgreSQL
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# สร้างตารางสำหรับบันทึกการตั้งค่า guild_settings
cur.execute("""
    CREATE TABLE IF NOT EXISTS guild_settings (
        guild_id BIGINT PRIMARY KEY,
        input_channel_id BIGINT,
        announce_channel_id BIGINT
    )
""")
conn.commit()

# ฟังก์ชันบันทึกการตั้งค่า
def save_guild_settings(guild_id, input_channel_id, announce_channel_id):
    cur.execute("""
        INSERT INTO guild_settings (guild_id, input_channel_id, announce_channel_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (guild_id) DO UPDATE
        SET input_channel_id = EXCLUDED.input_channel_id,
            announce_channel_id = EXCLUDED.announce_channel_id
    """, (guild_id, input_channel_id, announce_channel_id))
    conn.commit()

# ฟังก์ชันโหลดการตั้งค่า
def load_guild_settings(guild_id):
    cur.execute("SELECT input_channel_id, announce_channel_id FROM guild_settings WHERE guild_id = %s", (guild_id,))
    return cur.fetchone()

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

    guild_id = message.guild.id
    settings = load_guild_settings(guild_id)
    if settings:
        input_channel_id, announce_channel_id = settings
        if message.channel.id == input_channel_id:
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
                announce_channel = await bot.fetch_channel(announce_channel_id)
                
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

@bot.tree.command(name="setup", description="ตั้งค่าระบบส่งข้อความนิรนาม")
async def setup(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        await log_message(f"⚠️ ผู้ใช้ {interaction.user} ({interaction.user.id}) พยายามใช้คำสั่ง setup โดยไม่มีสิทธิ์")
        return

    guild_id = interaction.guild.id

    try:
        category = await interaction.guild.create_category("ข้อความนิรนาม")
        input_channel = await category.create_text_channel("ส่งข้อความนิรนาม")
        announce_channel = await category.create_text_channel("ประกาศข้อความนิรนาม")

        save_guild_settings(guild_id, input_channel.id, announce_channel.id)

        embed = discord.Embed(
            title="📩 ให้พรี่โตส่งข้อความแทนคุณ",
            description="พิมพ์ข้อความในช่องนี้เพื่อส่งข้อความแบบไม่ระบุตัวตน\nสามารถ @mention สมาชิกได้โดยพิมพ์ @username",
            color=discord.Color.blue()
        )

        await input_channel.send(embed=embed)
        await interaction.response.send_message("✅ ระบบ setup ถูกตั้งค่าเรียบร้อย\n\n(สามารถเปลี่ยนชื่อห้องและจัดเรียงตามสะดวกได้เลย)", ephemeral=True)
        await log_message(f"⚙️ ระบบ setup ถูกตั้งค่าในเซิร์ฟเวอร์: {interaction.guild.name} โดย {interaction.user} ({interaction.user.id})")
    except discord.errors.NotFound as e:
        await log_message(f"❌ เกิดข้อผิดพลาดในการตั้งค่าระบบ: {e}")
        await interaction.followup.send("❌ เกิดข้อผิดพลาดในการตั้งค่าระบบ", ephemeral=True)
    except Exception as e:
        await log_message(f"❌ เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}")
        await interaction.followup.send("❌ เกิดข้อผิดพลาดที่ไม่คาดคิด", ephemeral=True)

@bot.command()
async def update(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้")
        return
    
    await ctx.send("🔄 กำลังอัปเดตบอท โปรดรอสักครู่...")
    await log_message("🔄 บอทกำลังรีสตาร์ทตามคำสั่งอัปเดต")
    try:
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

@bot.tree.command(name="help", description="แสดงข้อมูลการใช้งานคำสั่งต่างๆ ของบอท")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📄 คำสั่งการใช้งานบอท",
        description="คำสั่งต่างๆ ที่สามารถใช้ได้กับบอทนี้",
        color=discord.Color.green()
    )
    embed.add_field(name="/ping", value="ตรวจสอบว่าบอทยังออนไลน์อยู่", inline=False)
    embed.add_field(name="/setup", value="ตั้งค่าระบบส่งข้อความนิรนาม (เฉพาะผู้ดูแลระบบ)", inline=False)
    embed.add_field(name="/update", value="รีสตาร์ทบอท (เฉพาะผู้ดูแลระบบ)", inline=False)
    embed.add_field(name="/delete", value="ลบข้อความตามจำนวนที่กำหนด (เฉพาะผู้ดูแลระบบ)", inline=False)
    embed.set_footer(text="พิมพ์ /help เพื่อตรวจสอบคำสั่งทั้งหมดที่สามารถใช้ได้")

    await interaction.response.send_message(embed=embed, ephemeral=True)

server_on()
bot.run(TOKEN)

# ปิดการเชื่อมต่อเมื่อไม่ใช้งานแล้ว
def close_connection():
    cur.close()
    conn.close()
