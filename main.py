import uuid
import orjson

from collections import defaultdict
from http import HTTPStatus
from itertools import islice

from flask import Flask, jsonify, make_response, request, session
from flask_cors import CORS

from common import common_container
from common.nsn_logging import debug, error, info, warning

# Flask API cheatsheet: https://s3.us-east-2.amazonaws.com/prettyprinted/flask_cheatsheet.pdf
# http://flask-cheat-sheet.herokuapp.com/
app = Flask(__name__)
# TODO(gdottl): #security configure CORS.
CORS(app)  # Sets up Access-Control-Allow-Origin

# TODO #security Figure out what to do with this... Seems sho
app.secret_key = b'_5#y2L"F4Qs8z\n\xec]/'
_container = None

MAX_CLUSTER_SIZE = 1000

# ########################## PRIVATE ENDPOINTS ############################
# N.b.: THIS IS NOT LOCKED DOWN AT ALL!!!!
# #security #hack This is allowed mostly for experimentation before committing to a more proper
# communication mechanism.


def _maybe_write_to_long_term_storage(collection_name, documents):
  if _container.config.local():
    # TODO log-once
    info(f'Configured for local - not logging to cloud storage.')
    return
  store = _container.cloud_storage_document_store()
  collection = store.get_collection(collection_name)
  collection.append_documents(documents)


def _post_store():
  from simplekv.decorator import PrefixDecorator
  return PrefixDecorator('post_', _container.kv_store())


def _cluster_store():
  from simplekv.decorator import PrefixDecorator
  return PrefixDecorator('cluster_', _container.kv_store())


def _strip_and_save_for_serving(collection_name, documents):
  ps = _post_store()
  for d in documents:
    p = _document_to_post(d)
    ps.put(d['id'], orjson.dumps(p))
  # c = _container.source_document_store().get_collection(collection_name)
  # c.append_documents(posts)
  # # TODO: Consider something else here...
  # if _container.config.mode() == 'local':
  #   info(f'Saving')
  #   c.save()


def _add_cluster_name(n):
  s = _container.kv_store()
  cluster_names = _safe_get(s, '_cluster_names', list)
  cluster_names.append(n)
  s.put('_cluster_names', orjson.dumps(cluster_names))


def _safe_get(store, name, fallback_fn):
  try:
    return orjson.loads(store.get(name))
  except KeyError:
    return fallback_fn()


@app.route('/ingest', methods=['POST'])
def ingest():
  '''json={'collection': collection, 'documents': documents}'''
  # global _clusters
  try:
    content = request.json
    debug(f'Ingesting data!!: {content}')
    collection_name = content['collection']
    documents = content['documents']
    for document in documents:
      document['id'] = hash_id(document['id'])
    _maybe_write_to_long_term_storage(collection_name, documents)
    _strip_and_save_for_serving(collection_name, documents)
    # s = _container.cluster_document_store()
    cs = _cluster_store()
    for document in documents:
      if 'subreddit_name' in document:
        n = f'reddit_{document["subreddit_name"]}'
      else:
        n = collection_name
      try:
        cluster = orjson.loads(cs.get(n))
      except KeyError:
        _add_cluster_name(n)
        cluster = []
      # TODO: PriorityQueue.
      cluster.append(document['id'])
      if len(cluster) > MAX_CLUSTER_SIZE:
        cluster = cluster[1:]  # pop off head to keep size reasonable
      cs.put(n, orjson.dumps(cluster))
    return ''  # Return something so Response is marked successful.
  except Exception as e:
    message = f'Ingested data does not match expected format: [{{doc}}, {{doc}}, ...]. Got: {content}. Error: {e}'
    error(message)
    _container.error_reporter().report_exception()
    import traceback
    traceback.print_exc()
    return message, HTTPStatus.BAD_REQUEST


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

  user_history = _safe_get(_container.kv_store(), 'user', list)
  sent_set = set(user_history)
  # posts = list(
  #     islice(
  #         filter(lambda d: d['id'] not in sent_set,
  #                _container.source_document_store().get_all_documents()), 10))
  cluster_names = _safe_get(_container.kv_store(), '_cluster_names', list)

  items = []
  cs = _cluster_store()
  ps = _post_store()
  post_count = 0
  MAX_POST_SEND = 30
  for name in cluster_names:
    cluster = _safe_get(cs, name, list)
    client_cluster = {}
    client_cluster['type'] = 'CLUSTER'
    client_cluster['id'] = name  # TODO?
    client_cluster['name'] = name
    posts = client_cluster['posts'] = []
    for post_id in cluster:
      if post_id in sent_set:
        continue
      sent_set.add(post_id)
      post_count += 1
      posts.append(ps.get(post_id))
      if post_count >= MAX_POST_SEND:
        break
    debug(f'client_cluster: {client_cluster}')
    if not posts:
      continue
    items.append(client_cluster)
    if post_count >= MAX_POST_SEND:
      break

  # TODO: make sent_set an LRU cache.
  # user_history += [d['id'] for d in posts]
  _container.kv_store().put('user', orjson.dumps(list(sent_set)))

  if len(items) == 0:
    return make_response('500: No items', 500)

  if _container.config.debug_mode():
    from common import standard_keys
    assert all(standard_keys.is_valid_item(i) for i in items)

  return jsonify(items)


def _document_to_post(doc):
  return {
      'type': 'POST',
      'title_text': doc['title_text'],
      'secondary_text': doc['secondary_text'],
      'id': doc['id'],  # UID of the post for tracking.
      # TODO: Generate URL for content where applicable, e.g. Reddit?
      'url': doc['source_url'] if 'source_url' in doc else '',  # Optional.
      'thumbnail': doc['image_url'] if 'image_url' in doc else '',  # URL to thumbnail image.
      # 'media_embed': doc[''],
      'created_utc_sec': doc['created_utc_sec'],
      'liked': 0  # 0 or 1.
  }


# POST
@app.route('/liked', methods=['POST'])
def liked():
  # TODO Browser cook for personalization.
  info(f'Got ID: {request.args["id"]}')
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
  app.run(host='0.0.0.0', port=5000)


def main_waitress(*args):
  _main()
  # #performance #security Migrate to gunicorn? https://quintagroup.com/cms/python/web-server
  from waitress import serve
  serve(app, host='0.0.0.0', port=5000)


_container = common_container.arg_container()
# Bad early optimization, but just retrieving the hasher takes ~20us - so prefer caching.
hash_id = _container.hasher().hash

if __name__ == '__main__':
  print(f'Hello! - {__file__}')
  _debug_app()
