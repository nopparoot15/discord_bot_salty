import os
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Server is running!"

def run():
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))

def keep_alive():
    t = Thread(target=run)
    t.start()
