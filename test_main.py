import os
import shutil

import orjson
import pytest
from datetime import datetime

import main
from common import common_container
from common.data_types import Cluster, Post, RedditPost, item_from_json, item_from_dict
from common.store_utils import safe_get, tag_store


def _gen_post_test_data():
  return [
      Post(
          local_id=str(i),
          image_url=str(i),
          title_text=str(i),
          secondary_text=str(i),
          created_utc_sec=i,
          article_url='a').to_dict() for i in range(20)
  ]


def _gen_reddit_test_data():
  return [
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


def _gen_cluster_test_data():
  return [
      Cluster(
          local_id='1',
          title_text='title_text',
          article_url='http://whatever.com',
          created_utc_sec=int(
              datetime.now().timestamp()),  # TODO Extract from actual post.
          articles=_gen_post_test_data(),
      ).to_dict()
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
    # test.append_articles(_gen_post_test_data())
    yield client
    common_container.cleanup(main._container.config)
    # store = Localarticlestore('./tmp')
    # shutils.rmtree('tmp')


def test_root(client):
  """Start with a blank database."""
  resp = client.get('/')
  assert b'This is' in resp.data


def test_post_ingest(client):
  test_data = _gen_post_test_data()
  resp = client.post(
      '/ingest', json={
          'source_name': 'test_source',
          'articles': test_data
      })
  assert resp.status_code == 200
  kv_store = main._container.kv_store()
  test2 = safe_get(tag_store(kv_store), 'test_source', list)
  assert len(test2) == len(test_data)


def test_reddit_ingest(client):
  '''Ingest + Serving.'''
  test_data = _gen_reddit_test_data()
  resp = client.post(
      '/ingest', json={
          'source_name': 'test_source',
          'articles': test_data
      })
  assert resp.status_code == 200
  kv_store = main._container.kv_store()
  for i in range(4):
    subreddit_i = safe_get(tag_store(kv_store), f'subreddit_{i}', list)
    assert len(subreddit_i) == 5, (i, kv_store.keys())


def test_cluster_ingest(client):
  '''Ingest + Serving.'''
  test_data = _gen_cluster_test_data()
  resp = client.post(
      '/ingest', json={
          'source_name': 'test_source',
          'articles': test_data
      })
  assert resp.status_code == 200
  kv_store = main._container.kv_store()
  test2 = safe_get(tag_store(kv_store), 'test_source', list)
  assert len(test2) == len(test_data)


def test_serve_items(client):
  # Ingestion copied from test_ingest.
  test_data = _gen_post_test_data()
  resp = client.post(
      '/ingest', json={
          'source_name': 'news_api',
          'articles': test_data
      })
  assert resp.status_code == 200
  resp = client.get('/items')
  assert resp.status_code == 200
  items_dict = resp.json
  client_items = list(map(item_from_dict, items_dict))
  assert len(client_items) == len(test_data)


def test_liked(client):
  resp = client.post('/liked', query_string={'liked': 1, 'id': 'asdf'})
  # TODO: Check internal state.
  assert resp.status_code == 200
