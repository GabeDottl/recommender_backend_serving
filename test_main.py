import os
import shutil
import orjson

import pytest

import main

from common.standard_keys import is_valid_item
from common import common_container


def _gen_source_test_data():
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
    main._container = common_container.arg_container(test=True)
    # source = store.get_or_create_collection('source')
    # source.append_documents(['test'])
    # test = main._container.source_document_store().get_collection('test')
    # test.append_documents(_gen_source_test_data())
    yield client
    common_container.cleanup(main._container.config)
    # store = LocalDocumentStore('./tmp')
    # shutils.rmtree('tmp')


def test_root(client):
  """Start with a blank database."""
  resp = client.get('/')
  assert b'This is' in resp.data


def test_ingest(client):
  test_data = _gen_source_test_data()
  resp = client.post('/ingest', json={'collection': 'test2', 'documents': test_data})
  assert resp.status_code == 200
  kv_store = main._container.kv_store()
  assert 'cluster_test2' in kv_store
  test2 = orjson.loads(kv_store.get('cluster_test2'))
  assert len(test2) == len(test_data)


def test_clusters(client):
  test_data = [
      {
          'id': str(i),
          'image_url': str(i),
          'title_text': str(i),
          'subreddit_name': f'subreddit_{i // 5}',  # 4 subreddits, 0, 1, 2, 3.
          'secondary_text': str(i),
          'created_utc_sec': str(i),
          'source_url': str(i),
          'retrieved_utc_sec': str(i),
      } for i in range(20)
  ]
  resp = client.post('/ingest', json={'collection': 'test', 'documents': test_data})
  assert resp.status_code == 200
  resp = client.get('/posts')
  assert resp.status_code == 200
  items = resp.json
  assert all(is_valid_item(i) for i in items)
  # Ensure there are 4 clusters in the out.
  assert len(list(filter(lambda i: i['type'] == 'CLUSTER', items))) == 4
  for cluster in items:
    assert len(cluster['posts']) == 5


# def test_posts(client):
#   resp = client.post('/ingest', json={'collection': 'test', 'documents': _gen_source_test_data()})
#   assert resp.status_code == 200
#   resp = client.get('/posts')
#   assert resp.status_code == 200
#   assert isinstance(resp.json, list)
#   assert len(resp.json) == 10
#   user_collection = main._container.user_document_store().get_collection('user')
#   assert len(user_collection.documents) == 10
#   ids = [d['id'] for d in resp.json]
#   _check_format(resp.json)
#   # Ensure only unique results are returned
#   resp = client.get('/posts')
#   assert isinstance(resp.json, list)
#   assert len(resp.json) == 10
#   user_collection = main._container.user_document_store().get_collection('user')
#   assert len(user_collection.documents) == 20
#   _check_format(resp.json)
#   ids.extend([d['id'] for d in resp.json])
#   # Ensure all ids are unique.
#   assert len(set(ids)) == 20


def _check_format(client_items):
  for item in client_items:
    # Check every expected key is present.
    assert is_valid_item(item)
