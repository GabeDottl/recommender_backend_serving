import atexit
import os
import uuid
from datetime import datetime, timedelta
from http import HTTPStatus
from itertools import islice

from flask import Flask, jsonify, make_response, request, session, g
from flask_cors import CORS
from rsa.randnum import randint

from common.nsn_logging import debug, error, info, set_verbosity, warning
from common import common_container

# Flask API cheatsheet: https://s3.us-east-2.amazonaws.com/prettyprinted/flask_cheatsheet.pdf
# http://flask-cheat-sheet.herokuapp.com/
app = Flask(__name__)
# TODO(gdottl): #security configure CORS.
CORS(app)  # Sets up Access-Control-Allow-Origin

# TODO #security Figure out what to do with this... Seems sho
app.secret_key = b'_5#y2L"F4Qs8z\n\xec]/'
_container = None

########################### PRIVATE ENDPOINTS ############################
# N.b.: THIS IS NOT LOCKED DOWN AT ALL!!!!
# #security #hack This is allowed mostly for experimentation before committing to a more proper
# communication mechanism.

# info(f'Wrote {filename}')


@app.route('/ingest', methods=['POST'])
def ingest():
  '''json={'collection': collection, 'documents': documents}'''
  try:
    content = request.json
    debug(f'Ingesting data!!: {content}')
    collection_name = content['collection']
    store = _container.cloud_storage_document_store()
    # if not store.has_collection(collection_name):
    #   sources = store.get_collection('sources')
    #   sources.append_documents([collection_name])
    collection = store.get_collection(collection_name)
    collection.append_documents(content['documents'])
    # collection.save()
    return ''  # Return something so Response is marked successful.
  except Exception as e:
    message = f'Ingested data does not match expected format: [{{doc}}, {{doc}}, ...]. Got: {content}. Error: {e}'
    error(message)
    import traceback
    traceback.print_exc()
    return message, HTTPStatus.BAD_REQUEST


########################### PUBLIC ENDPOINTS ############################


@app.route('/')
def index():
  '''
    This is a root dir of my server
    :return: str
  '''

  import socket
  from common.settings import get_git_commit
  version = get_git_commit()
  info(f'This is {socket.gethostname()} @ {version}!!!!')
  return f'This is {socket.gethostname()} @ {version}!!!!'


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

  user_collection = get_document_store().get_collection('user')
  sent_set = set(user_collection.documents)
  sources = get_document_store().get_collection('sources').documents
  documents = list(
      islice(
          filter(lambda d: d['id'] not in sent_set,
                 get_document_store().get_documents(sources)), 10))
  user_collection.append_documents([d['id'] for d in documents])

  if len(documents) == 0:
    return make_response('', 500)
  return jsonify([_document_to_post(doc) for doc in documents])


def _document_to_post(doc):
  # assert type(doc) == dict, doc
  # from common.standard_keys import REQUIRED_SOURCE_KEYS
  # for k in REQUIRED_SOURCE_KEYS:
  #   assert k in doc, (k, doc)
  return {
      'title_text': doc['title_text'],
      'secondary_text': doc['secondary_text'],
      'id': doc['id'],  # UID of the post for tracking.
      'url': doc['source_url'],
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
  global _container
  _container = common_container.arg_container()

def _debug_app(*args):
  _main()
  app.run(host="0.0.0.0", port=5000)


def main_waitress(*args):
  _main()
  # #performance #security Migrate to gunicorn? https://quintagroup.com/cms/python/web-server
  from waitress import serve
  serve(app, host="0.0.0.0", port=5000)


if __name__ == '__main__':
  main_waitress()
