'''A Storage abstraction for recording data.

Initially, a simple wrapper over Firestore.
https://firebase.google.com/docs/firestore/quickstart
'''

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import attr
import os

from .utils import cached_fn
from .settings import is_gce
from .nsn_logging import info, debug, error, warning


class _Storage:
  db = None

  def __init__(self):
    self.db = self._gce_db() if is_gce else self._local_db()

  def _gce_db(self):  # , project_id='recommender-270613'):
    # Use the application default credentials
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)

    return firestore.client()

  def _local_db(self):
    # Use a service account

    cred = credentials.Certificate(
        os.path.join(
            os.getenv('CONFIG'), 'recommender_firestore_service_acct.json'))
    firebase_admin.initialize_app(cred)

    return firestore.client()


@cached_fn
def db():
  info(f'Initializing firestore.')
  return _Storage().db


def save_stream(stream, collection_name):
  c = db().collection(collection_name)
  count = 0
  for article in stream:
    if article:
      count += 1
      url = article['source_url']
      c.document(url.replace('/', '-').replace(':', '.')).set(article)
  info(f'Wrote a total of {count} articles to collection {collection_name}')


# @attr.
# class Collection:
#   def append_doc(self, doc):
#     pass
