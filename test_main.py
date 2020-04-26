import os
import shutil

import orjson
import pytest

import main
from common import common_container
from common.data_types import Post, RedditPost, item_from_json, item_from_dict
from common.store_utils import safe_get, tag_store


def _gen_source_test_data():
  return [
      Post(
          local_id=str(i),
          image_url=str(i),
          title_text=str(i),
          secondary_text=str(i),
          created_utc_sec=i,
          article_url='a').to_dict() for i in range(20)
  ]


@pytest.fixture
def client():
  #   db_fd, main.app.config['DATABASE'] = tempfile.mkstemp()
  main.app.config['TESTING'] = True

  with main.app.test_client() as client:
    # Setup document store with some basic data.
    main._container = common_container.arg_container(test=True)
    # source = store.get_or_create_source_name('source')
    # source.append_articles(['test'])
    # test = main._container.source_document_store().get_source_name('test')
    # test.append_articles(_gen_source_test_data())
    yield client
    common_container.cleanup(main._container.config)
    # store = Localarticlestore('./tmp')
    # shutils.rmtree('tmp')


def test_root(client):
  """Start with a blank database."""
  resp = client.get('/')
  assert b'This is' in resp.data


def test_ingest(client):
  test_data = _gen_source_test_data()
  resp = client.post(
      '/ingest', json={
          'source_name': 'test2',
          'articles': test_data
      })
  assert resp.status_code == 200
  kv_store = main._container.kv_store()
  test2 = safe_get(tag_store(kv_store), 'test2', list)
  # assert 'cluster_test2' in kv_store
  # test2 = orjson.loads(kv_store.get('cluster_test2'))
  assert len(test2) == len(test_data)


def test_reddit_ingest(client):
  '''Ingest + Serving.'''
  test_data = [
      RedditPost(
          local_id=str(i),
          image_url=str(i),
          title_text=str(i),
          subreddit_name=f'subreddit_{i // 5}',  # 4 subreddits, 0, 1, 2, 3, 4.
          author_name='Joe',
          score=1,
          secondary_text=str(i),
          created_utc_sec=i,
          article_url=str(i),
          # retrieved_utc_sec=str(i),
      ).to_dict() for i in range(20)
  ]
  resp = client.post(
      '/ingest', json={
          'source_name': 'test',
          'articles': test_data
      })
  assert resp.status_code == 200
  kv_store = main._container.kv_store()
  for i in range(4):
    subreddit_i = safe_get(tag_store(kv_store), f'subreddit_{i}', list)
    assert len(subreddit_i) == 5, (i, kv_store.keys())

def test_post(client):
  # Ingestion copied from test_ingest.
  test_data = _gen_source_test_data()
  resp = client.post(
      '/ingest', json={
          'source_name': 'cnn_source',
          'articles': test_data
      })
  assert resp.status_code == 200
  resp = client.get('/posts')
  assert resp.status_code == 200
  items_dict = resp.json # TODO: orjson decode?
  client_items = list(map(item_from_dict, items_dict))
  assert len(client_items) == len(test_data)
  # # Ensure there are 4 clusters in the out.
  # assert len(list(filter(lambda i: i['type'] == 'CLUSTER', items))) == 4
  # for cluster in items:
  #   assert len(cluster['posts']) == 5


# def test_posts(client):
#   resp = client.post('/ingest', json={'source_name': 'test', 'articles': _gen_source_test_data()})
#   assert resp.status_code == 200
#   resp = client.get('/posts')
#   assert resp.status_code == 200
#   assert isinstance(resp.json, list)
#   assert len(resp.json) == 10
#   user_source_name = main._container.user_document_store().get_source_name('user')
#   assert len(user_source_name.articles) == 10
#   ids = [d['id'] for d in resp.json]
#   _check_format(resp.json)
#   # Ensure only unique results are returned
#   resp = client.get('/posts')
#   assert isinstance(resp.json, list)
#   assert len(resp.json) == 10
#   user_source_name = main._container.user_document_store().get_source_name('user')
#   assert len(user_source_name.articles) == 20
#   _check_format(resp.json)
#   ids.extend([d['id'] for d in resp.json])
#   # Ensure all ids are unique.
#   assert len(set(ids)) == 20
