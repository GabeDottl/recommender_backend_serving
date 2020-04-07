import os
import shutil

import pytest

import main

from common.standard_keys import CLIENT_POST_KEYS
from common import common_container


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
    # TODO: encase the tmp_dir creation and destruction in wrapper.
    tmp_dir = os.path.abspath('./tmp')  # Abspath incase working dir changes.
    if os.path.exists(tmp_dir):
      shutil.rmtree(tmp_dir)

    os.makedirs(tmp_dir)
    main._container = common_container.arg_container(overrides={'data_dir': tmp_dir}, test=True)
    # sources = store.get_or_create_collection('sources')
    # sources.append_documents(['test'])
    test = main._container.sources_document_store().get_collection('test')
    test.append_documents(_gen_test_data())
    yield client
    print(f'Clearing {tmp_dir}')
    shutil.rmtree(tmp_dir)
    # store = LocalDocumentStore('./tmp')
    # shutils.rmtree('tmp')


def test_root(client):
  """Start with a blank database."""
  resp = client.get('/')
  assert b'This is' in resp.data


def test_ingest(client):
  test_data = _gen_test_data()
  resp = client.post('/ingest', json={'collection': 'test2', 'documents': test_data})
  assert resp.status_code == 200
  sources_store = main._container.sources_document_store()
  assert sources_store.has_collection('test2')
  test2 = sources_store.get_collection('test2')
  assert len(list(test2.get_documents())) == len(test_data)


def test_posts(client):
  resp = client.get('/posts')
  assert resp.status_code == 200
  assert isinstance(resp.json, list)
  assert len(resp.json) == 10
  user_collection = main._container.users_document_store().get_collection('user')
  assert len(user_collection.documents) == 10
  ids = [d['id'] for d in resp.json]
  _check_format(resp.json)
  # Ensure only unique results are returned
  resp = client.get('/posts')
  assert isinstance(resp.json, list)
  assert len(resp.json) == 10
  user_collection = main._container.users_document_store().get_collection('user')
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
