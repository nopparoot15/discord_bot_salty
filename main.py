import discord
from discord.ext import commands
import os
from myserver import server_on

TOKEN = os.getenv("TOKEN")  # ใส่ token ใน Environment
ANNOUNCE_CHANNEL_ID = 1350128705648984197
MESSAGE_INPUT_CHANNEL_ID = 1350161594985746567  # ID ห้องรับข้อความ
LOG_CHANNEL_ID = 1350380441504448512  # ID ห้องเก็บ logs

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

server_on()  # เปิดเซิร์ฟเวอร์ HTTP สำหรับ Render

async def log_message(content):
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
    await bot.tree.sync()
    await log_message("✅ บอทเริ่มทำงานเรียบร้อย")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.channel.id == MESSAGE_INPUT_CHANNEL_ID:
        content = message.content.replace('@', '＠')  # ป้องกันการ mention จริง
        mentions = []
        remaining_words = []

        for word in content.split():
            if word.startswith('＠'):
                username = word[1:]
                member = discord.utils.find(lambda m: m.name == username or m.display_name == username, message.guild.members)
                if member:
                    mentions.append(member.mention)  # ใช้ mention จริงใน ANNOUNCE_CHANNEL_ID
                else:
                    remaining_words.append(word)
            else:
                remaining_words.append(word)

        mention_text = " ".join(mentions)
        final_message = " ".join(remaining_words)

        if mentions:
            final_message = f"{mention_text}\n{final_message}"

        try:
            announce_channel = await bot.fetch_channel(ANNOUNCE_CHANNEL_ID)
            await announce_channel.send(final_message, allowed_mentions=discord.AllowedMentions(users=True, roles=True, everyone=False))
            await message.delete()
            await log_message(f"📩 ข้อความถูกส่งโดย {message.author} ({message.author.id}): {final_message}")
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
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        await log_message(f"⚠️ ผู้ใช้ {interaction.user} ({interaction.user.id}) พยายามใช้คำสั่ง setup โดยไม่มีสิทธิ์")
        return

    embed = discord.Embed(
        title="📩 ให้พรี่โตส่งข้อความแทนคุณ",
        description="พิมพ์ข้อความในช่องนี้เพื่อส่งข้อความแบบไม่ระบุตัวตน\nสามารถ @mention สมาชิกได้โดยพิมพ์ ＠username",
        color=discord.Color.blue()
    )

    await interaction.response.send_message(embed=embed)
    await log_message(f"⚙️ ระบบ setup ถูกตั้งค่าในช่อง: {interaction.channel.name} โดย {interaction.user} ({interaction.user.id})")

bot.run(TOKEN)
