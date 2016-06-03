from werkzeug.serving import run_simple
from flask import Flask
from gevent import wsgi

app = Flask(__name__)

@app.route('/')
def index():
  return 'Hello World'

run_simple('0.0.0.0', 5000, app, use_reloader=False, use_debugger=False)
