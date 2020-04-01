import atexit
import os
from datetime import datetime, timedelta

from flask import Flask, jsonify, request
from flask_cors import CORS

from common.constants import DATA
from common.nsn_logging import debug, error, info, warning, set_verbosity

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
  from common.settings import get_git_commit
  version = get_git_commit()
  return f'This is {socket.gethostname()} @ {version}!!!!'


@app.route('/posts')
def posts():
  # XXX: list(range(10)) HACK
  out = list(range(10)) # []
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
  print('main')

# Running web app in local machine
if __name__ == '__main__':
  from common import settings
  import common
  service_name = os.path.basename(os.path.dirname(os.path.dirname(common.__file__)))
  settings.setup_cloud_profiling(service_name)
  set_verbosity('info')
  main()
  app.run(host='0.0.0.0', port=5000)
