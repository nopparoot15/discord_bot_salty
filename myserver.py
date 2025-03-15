from fastapi import FastAPI
import uvicorn
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello from Railway!"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # ใช้ PORT จาก Environment Variables
    uvicorn.run(app, host="0.0.0.0", port=port)
