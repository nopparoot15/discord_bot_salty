import discord
from discord.ext import commands
from myserver import server_on


ANNOUNCE_CHANNEL_ID = 1350128705648984197
MESSAGE_INPUT_CHANNEL_ID = 1350161594985746567  # 🔹 ตั้งค่า ID ห้องที่ให้ผู้ใช้พิมพ์ข้อความที่นี่

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'✅ บอทพร้อมใช้งาน: {bot.user}')

@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != MESSAGE_INPUT_CHANNEL_ID:
        return

    content = message.content
    mentions = []

    words = content.split()
    remaining_words = []

    for word in words:
        if word.startswith('@'):
            username = word[1:]
            member = discord.utils.get(message.guild.members, name=username)
            if member:
                mentions.append(member.mention)
            else:
                remaining_words.append(word)
        else:
            remaining_words.append(word)

    mention_text = " ".join(mentions)
    final_message = " ".join(remaining_words)

    if mentions:
        final_message = f"{mention_text}\n{final_message}"

    announce_channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if announce_channel:
        await announce_channel.send(final_message)
        await message.delete()

server_on

bot.run(os.getenv('TOKEN'))