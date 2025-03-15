import discord
from config import LOG_CHANNEL_ID

async def log_message(bot, content):
    """Log a message to the log channel."""
    print(f"[LOG] {content}")
    try:
        log_channel = await bot.fetch_channel(LOG_CHANNEL_ID)
        await log_channel.send(content)
    except discord.errors.NotFound:
        print("❌ ไม่พบช่อง logs กรุณาตรวจสอบ LOG_CHANNEL_ID")
    except discord.errors.Forbidden:
        print("❌ บอทไม่มีสิทธิ์ส่งข้อความไปยังช่อง logs")