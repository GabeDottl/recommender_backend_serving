import uuid
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


def _strip_and_save_for_serving(collection_name, documents):
  posts = [_document_to_post(d) for d in documents]
  c = _container.source_document_store().get_collection(collection_name)
  c.append_documents(posts)
  if _container.config.local_persistence():
    info(f'Saving')
    c.save()


@app.route('/ingest', methods=['POST'])
def ingest():
  '''json={'collection': collection, 'documents': documents}'''
  # global _clusters
  try:
    content = request.json
    debug(f'Ingesting data!!: {content}')
    collection_name = content['collection']
    documents = content['documents']
    _maybe_write_to_long_term_storage(collection_name, documents)
    _strip_and_save_for_serving(collection_name, documents)
    s = _container.cluster_document_store()
    for document in documents:
      if 'subreddit_name' in document:
        c = s.get_collection(document['subreddit_name'])
        # TODO: Normalize this?
        # Given virtually infinite data - sorta.
        c.append_documents([_document_to_post(document)])
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

  user_collection = _container.user_document_store().get_collection('user')
  sent_set = set(user_collection.documents)
  posts = list(
      islice(
          filter(lambda d: d['id'] not in sent_set,
                 _container.source_document_store().get_all_documents()), 10))
  cluster_collections = _container.cluster_document_store().get_collections()

  items = []
  # #hack #performance - we copy to avoid threading issues with concurrent adding in ingestion.
  for name, c in cluster_collections.copy().items():
    client_cluster = {}
    client_cluster['type'] = 'CLUSTER'
    client_cluster['id'] = name # TODO?
    client_cluster['name'] = name
    client_cluster['posts'] = c.get_documents()
    items.append(client_cluster)
    info(f'client_cluster: {client_cluster}')
  user_collection.append_documents([d['id'] for d in posts])
  items += posts

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
      'thumbnail': doc['image_url'],  # URL to thumbnail image.
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

if __name__ == '__main__':
  print(f'Hello! - {__file__}')
  _debug_app()
