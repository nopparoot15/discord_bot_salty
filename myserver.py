from fastapi import FastAPI
import uvicorn
import os
import threading

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Discord Bot Server is Running!"}

def server_on():
    port = int(os.getenv("PORT", 8000))
    server_thread = threading.Thread(target=uvicorn.run, args=(app,), kwargs={"host": "0.0.0.0", "port": port}, daemon=True)
    server_thread.start()
