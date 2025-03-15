from myserver import server_on
from log_utils import setup_logging, send_log_to_discord

# ตั้งค่า logging
logger = setup_logging()
webhook_url = "https://discord.com/api/webhooks/1350546611327078464/17AFMw_4NM7bvaArtO52Sl1CkThz9gJqai5V4CwJS2J0UD_H3up1nyDsheFSD93ODxbu"

try:
    logger.info("Starting server")
    send_log_to_discord(webhook_url, "Starting server")
    server_on()
except Exception as e:
    logger.error("Error occurred", exc_info=e)
    send_log_to_discord(webhook_url, f"Error occurred: {str(e)}")
