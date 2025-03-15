from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Discord Bot is Running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def server_on():
    thread = Thread(target=app.run, kwargs={"host":"0.0.0.0","port":8080})
    thread.start()
