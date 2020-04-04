import os
import tempfile

import pytest

import main

from common.standard_keys import CLIENT_POST_KEYS
from local_document_store import get_document_store


def _gen_test_data():
  return [{
      'id': str(i),
      'image_url': str(i),
      'title_text': str(i),
      'secondary_text': str(i),
      'created_utc_sec': str(i),
      'source_url': str(i),
      'retrieved_utc_sec': str(i),
  } for i in range(20)]


@pytest.fixture
def client():
  #   db_fd, main.app.config['DATABASE'] = tempfile.mkstemp()
  main.app.config['TESTING'] = True

  with main.app.test_client() as client:
    # Setup document store with some basic data.
    store = get_document_store()
    sources = store.get_or_create_collection('sources')
    sources.append_documents(['test'])
    test = store.get_or_create_collection('test')
    test.append_documents(_gen_test_data())
    yield client


def test_empty_db(client):
  """Start with a blank database."""
  resp = client.get('/')
  assert b'This is' in resp.data


def test_posts(client):
  resp = client.get('/posts')
  assert resp.status_code == 200
  assert isinstance(resp.json, list)
  assert len(resp.json) == 10
  user_collection = get_document_store().get_or_create_collection('user')
  assert len(user_collection.documents) == 10
  ids = [d['id'] for d in resp.json]
  _check_format(resp.json)
  # Ensure only unique results are returned
  resp = client.get('/posts')
  assert isinstance(resp.json, list)
  assert len(resp.json) == 10
  user_collection = get_document_store().get_or_create_collection('user')
  assert len(user_collection.documents) == 20
  _check_format(resp.json)
  ids.extend([d['id'] for d in resp.json])
  # Ensure all ids are unique.
  assert len(set(ids)) == 20


def _check_format(docs):
  for doc in docs:
    # Check every expected key is present.
    for k in CLIENT_POST_KEYS:
      assert k in doc
