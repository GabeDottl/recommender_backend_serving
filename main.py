import uuid
import orjson

from collections import defaultdict
from http import HTTPStatus
from itertools import islice

from flask import Flask, jsonify, make_response, request, session
from flask_cors import CORS
from simplekv.decorator import PrefixDecorator

from common import common_container
from common.store_utils import safe_get, post_store, cluster_store
from common.nsn_logging import debug, error, info, warning
from ingest import Ingestion

# Flask API cheatsheet: https://s3.us-east-2.amazonaws.com/prettyprinted/flask_cheatsheet.pdf
# http://flask-cheat-sheet.herokuapp.com/
app = Flask(__name__)
# TODO(gdottl): #security configure CORS.
CORS(app)  # Sets up Access-Control-Allow-Origin

# TODO #security Figure out what to do with this... Seems sho
app.secret_key = b'_5#y2L"F4Qs8z\n\xec]/'

_container = common_container.arg_container()
if _container.config()['clear_user']:
  info('Clearing user history')
  _container.kv_store().put('user', orjson.dumps([]))



# ########################## PRIVATE ENDPOINTS ############################
# N.b.: THIS IS NOT LOCKED DOWN AT ALL!!!!
# #security #hack This is allowed mostly for experimentation before committing to a more proper
# communication mechanism.

@common_container.exception_wrapper(_container.error_reporter())
@app.route('/ingest', methods=['POST'])
def ingest():
  '''json={'collection': collection, 'documents': documents}'''
  content = request.json
  return Ingestion(_container).ingest(content)


# ########################## PUBLIC ENDPOINTS ############################


@app.route('/')
def index():
  '''
    This is a root dir of my server
    :return: str
  '''

  import socket
  version = _container.config.version()
  info(f'This is {socket.gethostname()} @ {version}!!!!')
  return f'This is {socket.gethostname()} @ {version}!!!!'


# TODO: Rename /posts to /items?
@app.route('/posts/<page>', methods=['GET'])
@app.route('/posts', methods=['GET'], defaults={'page': None})
def posts(page):
  if 'id' not in session:
    id = uuid.uuid4()
    debug(f'No id in session; creating id: {id}')
    session['id'] = id
  else:
    id = session['id']
    debug(f'Reusing id: {id}')
  store = _container.kv_store()
  cs = cluster_store(store)
  ps = post_store(store)
  user_history = safe_get(store, 'user', list)
  sent_set = set(user_history)
  cluster_names = safe_get(store, '_cluster_names', list)

  items = []

  post_count = 0
  MAX_POST_SEND = 30
  for name in cluster_names:
    cluster = safe_get(cs, name, list)
    if len(cluster) < 2:
      debug('Skipping small cluster')
      continue
    client_cluster = {}
    client_cluster['type'] = 'CLUSTER'
    client_cluster['id'] = name  # TODO?
    client_cluster['name'] = name
    cluster_items = client_cluster['items'] = []
    for post_id in cluster:
      if post_id in sent_set:
        continue
      sent_set.add(post_id)
      post = safe_get(ps, post_id, {})
      if post:
        post_count += 1
        cluster_items.append(post)
      else:
        _container.error_reporter().report(f'Found no post for {post_id}')
      if post_count >= MAX_POST_SEND:
        break
    if not cluster_items:
      continue
    items.append(client_cluster)
    if post_count >= MAX_POST_SEND:
      break

  # TODO: make sent_set an LRU cache.
  # user_history += [d['id'] for d in posts]
  store.put('user', orjson.dumps(list(sent_set)))

  if len(items) == 0:
    _container.error_reporter().report('No items to serve!')
    return make_response('500: No items', 500)

  if _container.config.debug_mode():
    from common import standard_keys
    assert all(standard_keys.is_valid_item(i) for i in items), items

  return orjson.dumps(items)


# POST
@app.route('/liked', methods=['POST'])
def liked():
  # TODO Browser cook for personalization.
  id_ = request.args['id']
  liked = request.args['liked']
  info(f'Got ID: {id_}. {"liked" if liked else "unliked"}')
  store = _container.kv_store()
  likes = set(safe_get(store, 'user_likes', list))
  # If the current state's already reflected - do nothing.
  if (liked and id_ in liked) or (not liked and id_ not in likes):
    return ''

  if liked:
    likes.add(id_)
  else:
    likes.remove(id_)
  # TODO #performance - bloomfilter? Something that scales better... Redis has set data type.
  store.put('user_likes', orjson.dumps(list(likes)))
  return ''  # Return something so Response is marked successful.


def _main():
  # https://cloud.google.com/debugger/docs/setup/python#gce
  if _container.config.is_gce():
    try:
      import googleclouddebugger
      googleclouddebugger.enable(module='serving', version='[VERSION]')
    except ImportError:
      print('Failed to import GCE')
      pass
  # TODO: Initialize local store?
  # if _container.config.local_data():
  #   info(f'Loading local data for serving')


def _debug_app(*args):
  _main()
  # Note: debug=True triggers hot-reloading!
  app.run(host='0.0.0.0', port=5000, debug=True)


def main_waitress(*args):
  _main()
  # #performance #security Migrate to gunicorn? https://quintagroup.com/cms/python/web-server
  from waitress import serve
  serve(app, host='0.0.0.0', port=5000)



if __name__ == '__main__':
  print(f'Hello! - {__file__}')
  if _container.config()['debug_mode']:
    _debug_app()
  else:
    main_waitress()
