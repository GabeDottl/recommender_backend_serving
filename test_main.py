import os
import tempfile

import pytest

import main

from common.standard_keys import CLIENT_POST_KEYS

def _gen_test_data():
  main._sources = {
      'test': [{
          'id': str(i),
          'image_url': str(i),
          'title': str(i),
          'secondary': str(i),
          'created_utc': str(i),
          'source_url': str(i),
          'retrieved_utc': str(i),
      } for i in range(5)]
  }


@pytest.fixture
def client():
  #   db_fd, main.app.config['DATABASE'] = tempfile.mkstemp()
  main.app.config['TESTING'] = True

  with main.app.test_client() as client:
    
    #     with main.app.app_context():
    #       main.init_db()
    yield client


#   os.close(db_fd)
#   os.unlink(main.app.config['DATABASE'])


def test_empty_db(client):
  """Start with a blank database."""
  resp = client.get('/')
  assert b'This is' in resp.data

def test_posts_empty(client):
  resp = client.get('/posts')
  assert isinstance(resp.json, list)
  assert len(resp.json) >= 1
  for doc in resp.json:
    # Check every expected key is present.
    for k in CLIENT_POST_KEYS:
      assert k in doc
  
