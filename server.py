import atexit
import os
from datetime import datetime, timedelta
from distutils.log import set_verbosity
from threading import RLock

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from jinja2.filters import ignore_case
from timeloop import Timeloop

from constants import DATA
from nsn_logging import debug, error, info, warning, set_verbosity
from reddit_source import RedditSource

app = Flask(__name__)
# TODO(gdottl): #security configure CORS.
CORS(app)  # Sets up Access-Control-Allow-Origin

_sources = []


@app.route('/')
def index():
  '''
    this is a root dir of my server
    :return: str
  '''

  import socket
  return f'This is {socket.gethostname()}!!!!'


@app.route('/posts')
def posts():
  out = []
  for source in _sources:
    tmp = source.get_posts(10)
    out += tmp
  return jsonify(out)


# POST
@app.route('/liked', methods=['POST'])
def liked():
  # TODO Browser cook for personalization.
  info(f'Got ID: {request.args["id"]}')
  return ''


def main():
  tl = Timeloop()
  _sources.append(RedditSource())
  for source in _sources:
    atexit.register(source.close)
    source.schedule_or_start(tl)
  # Scheduling
  tl.start(block=False)


# Running web app in local machine
if __name__ == '__main__':
  set_verbosity('info')
  main()
  app.run(host='0.0.0.0', port=5000)
