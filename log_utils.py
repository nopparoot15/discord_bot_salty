import discord
from config import LOG_CHANNEL_ID, LOG_SERVER_ID

async def log_message(bot, content):
    """Log a message to the log channel in the specified server."""
    print(f"[LOG] {content}")
    await send_log(bot, LOG_SERVER_ID, LOG_CHANNEL_ID, content)

async def send_log(bot, server_id, channel_id, content):
    """Send a log message to a specific channel in a specific server."""
    try:
        server = bot.get_guild(server_id)
        if server:
            log_channel = server.get_channel(channel_id)
            if log_channel:
                await log_channel.send(content)
            else:
                print(f"❌ ไม่พบช่อง logs ที่มี ID {channel_id} ในเซิร์ฟเวอร์ที่มี ID {server_id}")
        else:
            print(f"❌ ไม่พบเซิร์ฟเวอร์ที่มี ID {server_id}")
    except discord.errors.Forbidden:
        print(f"❌ บอทไม่มีสิทธิ์ส่งข้อความไปยังช่อง logs ที่มี ID {channel_id} ในเซิร์ฟเวอร์ที่มี ID {server_id}")