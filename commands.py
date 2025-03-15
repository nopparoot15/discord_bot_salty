import discord
from discord.ext import commands
from bot_setup import bot
from log_utils import log_message

@bot.command()
async def ping(ctx):
    """Ping command to check if the bot is online."""
    await ctx.send('🏓 Pong! บอทยังออนไลน์อยู่!')
    await log_message(bot, f"🏓 Pong! มีการใช้คำสั่ง ping โดย {ctx.author} ({ctx.author.id})")

@bot.tree.command(name="setup", description="ตั้งค่าระบบส่งข้อความนิรนาม")
async def setup(interaction: discord.Interaction):
    """Setup command to initialize the anonymous message system."""
    async for message in interaction.channel.history(limit=10):
        if message.author == bot.user and message.embeds:
            await interaction.response.send_message("⚠️ ระบบได้ถูกตั้งค่าไว้แล้ว", ephemeral=True)
            return
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้", ephemeral=True)
        await log_message(bot, f"⚠️ ผู้ใช้ {interaction.user} ({interaction.user.id}) พยายามใช้คำสั่ง setup โดยไม่มีสิทธิ์")
        return

    embed = discord.Embed(
        title="📩 ให้พรี่โตส่งข้อความแทนคุณ",
        description="พิมพ์ข้อความในช่องนี้เพื่อส่งข้อความแบบไม่ระบุตัวตน\nสามารถส่งข้อความที่ต้องการได้โดยไม่ต้องเปิดเผยตัวตน",
        color=discord.Color.blue()
    )

    await interaction.channel.send(embed=embed)
    await log_message(bot, f"⚙️ ระบบ setup ถูกตั้งค่าในช่อง: {interaction.channel.name}")

@bot.command()
async def update(ctx):
    """Command to update and restart the bot."""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้")
        return
    
    await ctx.send("🔄 กำลังอัปเดตบอท โปรดรอสักครู่...")
    await log_message(bot, "🔄 บอทกำลังรีสตาร์ทตามคำสั่งอัปเดต")
    try:
        os._exit(0)  # ใช้วิธีปิดบอท ให้โฮสต์รันใหม่เอง
    except Exception as e:
        await ctx.send(f"❌ ไม่สามารถรีสตาร์ทบอทได้: {e}")
        await log_message(bot, f"❌ รีสตาร์ทบอทล้มเหลว: {e}")

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
        await log_message(bot, f"🔇 ปิดแจ้งเตือนและ @mention สำหรับชาแนลที่มี ID {channel_id} โดย {ctx.author} ({ctx.author.id})")
    except discord.errors.Forbidden:
        await ctx.send("❌ บอทไม่มีสิทธิ์เปลี่ยนการตั้งค่าของชาแนลนี้")
        await log_message(bot, f"❌ บอทไม่มีสิทธิ์เปลี่ยนการตั้งค่าของชาแนลที่มี ID {channel_id}")

@bot.command()
async def delete(ctx, target: discord.Member = None, number: int = 0):
    """Command to delete messages from a specified user or a specified number of messages in the current channel."""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้")
        return

    if target is not None:
        def is_target_user(m):
            return m.author == target

        deleted = await ctx.channel.purge(limit=100, check=is_target_user)
        await ctx.send(f"🗑️ ลบข้อความทั้งหมด {len(deleted)} ข้อความจาก {target.display_name} ({target.id}) เรียบร้อยแล้ว", delete_after=5)
        await log_message(bot, f"🗑️ {ctx.author} ({ctx.author.id}) ลบข้อความทั้งหมด {len(deleted)} ข้อความจาก {target.display_name} ({target.id}) ในช่อง {ctx.channel.name}")
    elif number > 0:
        deleted = await ctx.channel.purge(limit=number)
        await ctx.send(f"🗑️ ลบข้อความทั้งหมด {len(deleted)} ข้อความเรียบร้อยแล้ว", delete_after=5)
        await log_message(bot, f"🗑️ {ctx.author} ({ctx.author.id}) ลบข้อความทั้งหมด {len(deleted)} ข้อความในช่อง {ctx.channel.name}")
    else:
        await ctx.send("❌ ระบุจำนวนข้อความที่ต้องการลบหรือผู้ใช้ที่ต้องการลบข้อความ")