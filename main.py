from myserver import server_on
from log_utils import setup_logging, send_log_to_discord
import os
import bot_setup
import event_handlers  # Ensure event handlers are imported to register events
import config  # Import the config file to use constants like MESSAGE_INPUT_CHANNEL_ID and ANNOUNCE_CHANNEL_ID

# ตั้งค่า logging
logger = setup_logging()
webhook_url = "https://discord.com/api/webhooks/1350546611327078464/17AFMw_4NM7bvaArtO52Sl1CkThz9gJqai5V4CwJS2J0UD_H3up1nyDsheFSD93ODxbu"

try:
    logger.info("Starting server")
    send_log_to_discord(webhook_url, "Starting server")
    server_on()

    # Get the bot token from the environment variable
    token = os.getenv('TOKEN')
    if not token:
        raise ValueError("No TOKEN found in environment variables")

    logger.info("Starting bot")
    send_log_to_discord(webhook_url, "Starting bot")
    bot_setup.bot.run(token)

except Exception as e:
    logger.error("Error occurred", exc_info=e)
    send_log_to_discord(webhook_url, f"Error occurred: {str(e)}")
