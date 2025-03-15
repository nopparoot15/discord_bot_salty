import uvicorn
from fastapi import FastAPI
from log_utils import setup_logging, send_log_to_discord

app = FastAPI()
logger = setup_logging()
webhook_url = "https://discord.com/api/webhooks/1350546611327078464/17AFMw_4NM7bvaArtO52Sl1CkThz9gJqai5V4CwJS2J0UD_H3up1nyDsheFSD93ODxbu"

@app.get("/")
def read_root():
    logger.info("Root endpoint was called")
    send_log_to_discord(webhook_url, "Root endpoint was called")
    return {"Hello": "World"}

def server_on():
    try:
        logger.info("Server is starting")
        send_log_to_discord(webhook_url, "Server is starting")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error("Error occurred while starting the server", exc_info=e)
        send_log_to_discord(webhook_url, f"Error occurred while starting the server: {str(e)}")
