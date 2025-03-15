import time
import discord
from bot_setup import bot
from log_utils import log_message
from config import MESSAGE_INPUT_CHANNEL_ID, ANNOUNCE_CHANNEL_ID

@bot.event
async def on_ready():
    """Event handler for when the bot is ready."""
    if not getattr(bot, 'synced', False):
        await bot.tree.sync()
        bot.synced = True
        print(f'✅ บอทพร้อมใช้งาน: {bot.user}')
        await log_message(bot, "✅ บอทเริ่มทำงานเรียบร้อย")

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
                    mentions.append(f"{member.display_name}")  # ใช้ชื่อผู้ใช้แทน @mention ใน log
                    remaining_words.append(f"@{member.display_name}")
                else:
                    remaining_words.append(word)
            else:
                remaining_words.append(word)

        final_message = " ".join(remaining_words)

        try:
            announce_channel = await bot.fetch_channel(ANNOUNCE_CHANNEL_ID)
            current_time = time.time()
            if not getattr(bot, 'last_message_content', None) or (bot.last_message_content != final_message and current_time - getattr(bot, 'last_message_time', 0) > 2):
                bot.last_message_content = final_message
                bot.last_message_time = current_time
                await announce_channel.send(final_message, allowed_mentions=discord.AllowedMentions(users=True, roles=True, everyone=False))

            # Log message content without @mentions but with usernames
            log_entry = f"📩 ข้อความถูกส่งโดย {message.author} ({message.author.id}) : {content}"
            for mention in mentions:
                log_entry = log_entry.replace(f"@{mention}", mention)
            await log_message(bot, log_entry)

            # Delete the original message
            try:
                await message.delete()
            except discord.errors.Forbidden:
                print("❌ บอทไม่มีสิทธิ์ลบข้อความในห้องนี้")

        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
            error_msg = f"❌ เกิดข้อผิดพลาดในการส่งข้อความ: {str(e)}"
            print(error_msg)
            await log_message(bot, error_msg)

    await bot.process_commands(message)