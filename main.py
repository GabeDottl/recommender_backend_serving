import mimetypes
import uuid
import os 
import base64
from collections import defaultdict
from http import HTTPStatus
from itertools import islice

import orjson
from flask import Flask, jsonify, make_response, request, session
from flask_cors import CORS
from simplekv.decorator import PrefixDecorator

from common import common_container
from common.nsn_logging import debug, error, info, warning
from common.store_utils import post_store, safe_get, tag_store
from ingest import Ingestion


from google.auth.transport import requests as google_requests
from google.cloud import pubsub_v1
from google.oauth2 import id_token


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


# [START push]

# Configure the following environment variables via app.yaml
# This is used in the push request handler to verify that the request came from
# pubsub and originated from a trusted source.
# app.config['PUBSUB_VERIFICATION_TOKEN'] = \
#     os.environ['PUBSUB_VERIFICATION_TOKEN']
app.config['PUBSUB_TOPIC'] = 'projects/recommender-270613/topics/ingestable' #os.environ['PUBSUB_TOPIC']
app.config['GCLOUD_PROJECT'] = 'recommender-270613'

# Global list to store messages, tokens, etc. received by this instance.
MESSAGES = []
TOKENS = []
CLAIMS = []


@app.route('/push-handlers/receive_messages', methods=['POST'])
def receive_messages_handler():
    # Verify that the request originates from the application.
    # if (request.args.get('token', '') !=
    #         app.config['PUBSUB_VERIFICATION_TOKEN']):
    #     return 'Invalid request', 400

    # Verify that the push request originates from Cloud Pub/Sub.
    try:
        # Get the Cloud Pub/Sub-generated JWT in the "Authorization" header.
        bearer_token = request.headers.get('Authorization')
        token = bearer_token.split(' ')[1]
        TOKENS.append(token)

        # Verify and decode the JWT. `verify_oauth2_token` verifies
        # the JWT signature, the `aud` claim, and the `exp` claim.
        # Note: For high volume push requests, it would save some network
        # overhead if you verify the tokens offline by downloading Google's
        # Public Cert and decode them using the `google.auth.jwt` module;
        # caching already seen tokens works best when a large volume of
        # messages have prompted a single push server to handle them, in which
        # case they would all share the same token for a limited time window.
        claim = id_token.verify_oauth2_token(token, google_requests.Request(),
                                             audience='example.com')
        # Must also verify the `iss` claim.
        if claim['iss'] not in [
            'accounts.google.com',
            'https://accounts.google.com'
        ]:
            raise ValueError('Wrong issuer.')
        CLAIMS.append(claim)
    except Exception as e:
        return 'Invalid token: {}\n'.format(e), 400

    envelope = orjson.loads(request.data.decode('utf-8'))
    payload = base64.b64decode(envelope['message']['data'])
    MESSAGES.append(payload)
    # Returning any 2xx status indicates successful receipt of the message.
    return 'OK', 200
# [END push]

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


def _get_items():
  if 'id' not in session:
    id = uuid.uuid4()
    debug(f'No id in session; creating id: {id}')
    session['id'] = id
  else:
    id = session['id']
    debug(f'Reusing id: {id}')
  store = _container.kv_store()
  # cs = cluster_store(store)
  ps = post_store(store)
  ts = tag_store(store)
  user_history = safe_get(store, 'user', list)
  sent_set = set(user_history)
  # cluster_names = safe_get(store, '_cluster_names', list)

  items = []

  post_count = 0
  MAX_POST_SEND = 30

  cnn_source_ids = safe_get(ts, 'news_api', list)
  for id_ in cnn_source_ids:
    items.append(get_client_item_dict(ps, id_))

  # for name in cluster_names:
  #   cluster = client_cluster_from_cluster_name(ps, name)
  #   if len(cluster['posts']) < 2:
  #     debug('Skipping small cluster')
  #     continue
  #   # for post_id in cluster:
  #   #   if post_id in sent_set:
  #   #     continue
  #   #   sent_set.add(post_id)
  #   items.append(cluster)
  #   post_count += len(cluster['posts'])
  #   if post_count >= MAX_POST_SEND:
  #     break

  # TODO: make sent_set an LRU cache.
  # user_history += [d['id'] for d in posts]
  store.put('user', orjson.dumps(list(sent_set)))
  return items

  

@app.route('/items/<page>', methods=['GET'])
@app.route('/items', methods=['GET'], defaults={'page': None})
def items(page):
  
  items = _get_items()
      
  if len(items) == 0:
    _container.error_reporter().report('No items to serve!')
    return make_response('500: No items', 500)

  # if _container.config.debug_mode():
  #   from common import data_types
  #   assert all(data_types.is_valid_item(i) for i in items)

  return app.response_class(response=orjson.dumps(items), status=200, mimetype='application/json; charset=utf-8')

def get_client_item_dict(ps, id_):
  return orjson.loads(ps.get(id_))
  # item_dict = orjson.loads(ps.get(id_))
  # if item_dict['item_type'] == 'CLUSTER':
  #   return client_cluster_from_cluster(ps, item_dict)
  # assert item_dict['item_type'] == 'POST'
  # return item_dict  # Post store as client post

# def client_cluster_from_cluster(ps, cluster):
#   client_cluster = {}
#   client_cluster['item_type'] = 'CLUSTER'
#   client_cluster['id'] = cluster['id']  # TODO?
#   client_cluster['name'] = cluster['title_text'] # TODO: Rename
#   cluster_items = client_cluster['items'] = []
#   for post in cluster['posts']:
#     # post = safe_get(ps, post_id, dict)
#     if post:
#       cluster_items.append(post)
#     else:
#       _container.error_reporter().report(f'Found no post for {post}')
#   return client_cluster

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
  global _get_items
  _main()
  from argparse import ArgumentParser
  parser = ArgumentParser()
  parser.add_argument('--items_file')
  parser.add_argument('--port', type=int, default=-1)
  args, _ = parser.parse_known_args()
  port = args.port if args.port != -1 else 5000
  items_file = args.items_file
  if items_file:
    info(f'Returing from item-file - {items_file}')
    with open(items_file) as f:
      items = orjson.loads(''.join(f.readlines()))
      def get_items():
        return items
      _get_items = get_items
    
      # return items
      # Note that we must explicitly mark the mimetype as utf-8
  # Note: debug=True triggers hot-reloading!
  app.run(host='0.0.0.0', port=port, debug=True)


def main_gunicorn(*args):
  _main()
  # #performance #security Migrate to gunicorn? https://quintagroup.com/cms/python/web-server
  # from gunicorn import serve
  # serve(app, host='0.0.0.0', port=5000)
  info(f'Running in guincorn mode (this will be last log if not wrapped w/guincorn.) Alt - use --debug-mode')
  return app


if __name__ == '__main__':
  print(f'Hello! - {__file__}')
  if _container.config()['debug_mode']:
    _debug_app()
  else:
    main_gunicorn()
