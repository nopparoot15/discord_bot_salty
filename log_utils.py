import logging
import requests

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    return logger

def send_log_to_discord(webhook_url, message):
    data = {
        "content": message
    }
    response = requests.post(webhook_url, json=data)
    if response.status_code != 204:
        raise Exception(f"Failed to send log to Discord: {response.status_code}, {response.text}")

# Example usage
if __name__ == "__main__":
    logger = setup_logging()
    webhook_url = "https://discord.com/api/webhooks/1350546611327078464/17AFMw_4NM7bvaArtO52Sl1CkThz9gJqai5V4CwJS2J0UD_H3up1nyDsheFSD93ODxbu"
    
    try:
        logger.info("This is an info message")
        send_log_to_discord(webhook_url, "This is an info message")
    except Exception as e:
        logger.error("Error sending log to Discord", exc_info=e)
