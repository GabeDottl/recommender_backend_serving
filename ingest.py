import orjson

from http import HTTPStatus

from common import common_container
from common.nsn_logging import debug, error, info, warning
from common import common_container
from common.store_utils import post_store, cluster_store, safe_get

MAX_CLUSTER_SIZE = 1000


def _is_reddit(doc):
  return 'subreddit_name' in doc


class Ingestion:
  def __init__(self, container):
    self.container = container
    # Bad early optimization, but just retrieving the hasher takes ~20us - so prefer caching.
    self.hash_id = container.hasher().hash
    self.ps = post_store(self.container.kv_store())
    self.cs = cluster_store(self.container.kv_store())

  def _maybe_write_to_long_term_storage(self, collection_name, documents):
    if self.container.config.local():
      # TODO log-once
      info(f'Configured for local - not logging to cloud storage.')
      return
    store = self.container.cloud_storage_document_store()
    collection = store.get_collection(collection_name)
    collection.append_documents(documents)

  @common_container.instance_exception_wrapper()
  def _document_to_post(self, doc):
    return {
        'type': 'POST',
        'title_text': doc['title_text'],
        'secondary_text': doc['secondary_text'],
        'id': doc['id'],  # UID of the post for tracking.
        # TODO: Generate URL for content where applicable, e.g. Reddit?
        'url': doc['source_url'] if 'source_url' in doc else '',  # Optional.
        # URL to thumbnail image.
        'thumbnail':
        doc['image_url'] if 'image_url' in doc else doc['thumbnail'] if 'thumbnail' in doc else '',
        # May come in as float - we want to send out as an int.
        'created_utc_sec': int(float(doc['created_utc_sec'])),
        'liked': 0  # 0 or 1.
    }

  @common_container.instance_exception_wrapper()
  def _document_to_reddit_post(self, doc):
    out = self._document_to_post(doc)
    out['type'] = 'REDDIT_POST'
    out['subreddit'] = doc['subreddit_name']
    out['author'] = doc['author_name']
    out['score'] = int(doc['score'])
    return out

  def _add_cluster_name(self, n):
    s = self.container.kv_store()
    cluster_names = safe_get(s, '_cluster_names', list)
    cluster_names.append(n)
    s.put('_cluster_names', orjson.dumps(cluster_names))

  def _process_post(self, collection_name, document):
    try:
      if _is_reddit(document):
        p = self._document_to_reddit_post(document)
      else:
        p = self._document_to_post(document)
    except Exception:
      warning(f'Failed to parse post; skipping.')
      return
    self.ps.put(document['id'], orjson.dumps(p))
    self._add_to_cluster(collection_name, document)

  def _process_cluster(self, collection_name, document):
    assert len(document['posts']) > 0, document
    cluster = self._get_or_create_cluster(document['id'])
    cluster['title_text'] = document['title_text']
    posts = cluster['posts'] = []
    for post in document['posts']:
      if 'created_utc_sec' not in post:
        post['created_utc_sec'] = document['created_utc_sec']
      self._process_post(f'{collection_name}_posts', post)
      posts.append(post)
    self.cs.put(document['id'], orjson.dumps(cluster))

  def _get_or_create_cluster(self, id_):
    try:
      cluster = orjson.loads(self.cs.get(id_))
      if not isinstance(cluster, dict):
        raise KeyError()
    except KeyError:
      self._add_cluster_name(id_)
      cluster = {'id': id_, 'posts': [], 'title_text': id_}
    return cluster

  def _add_to_cluster(self, n, document):
    cluster = self._get_or_create_cluster(n)
    # TODO: PriorityQueue.
    # Keep old for dev perf.
    if len(cluster['posts']) < MAX_CLUSTER_SIZE:
      cluster['posts'].append(document['id'])
      self.cs.put(n, orjson.dumps(cluster))
    return cluster

  def ingest(self, content):
    try:
      debug(f'Ingesting data!!: {content}')
      collection_name = content['collection']
      documents = content['documents']
      for document in documents:
        if 'id' in document:
          document['id'] = self.hash_id(f'{collection_name}{document["source_url"]}{document["id"]}')
        else:  # Fallback
          document['id'] = self.hash_id(f'{collection_name}{document["source_url"]}{document["title_text"]}')

        type_ = 'POST' if 'type' not in document else document['type']
        if type_ == 'POST':
          self._process_post(collection_name, document)
          # TODO: Migrate Reddit to use Cluster API for subreddits.
          # if 'subreddit_name' in document:
          #   n = f'reddit_{document["subreddit_name"]}'
          # else:
          #   n = collection_name
        assert type_ == 'CLUSTER', type_
        self._process_cluster(collection_name, document)
      self._maybe_write_to_long_term_storage(collection_name, documents)
      return ''  # Return something so Response is marked successful.
    except Exception as e:
      message = f'Ingested data does not match expected format: [{{doc}}, {{doc}}, ...]. Got: {content}. Error: {e}'
      error(message)
      self.container.error_reporter().report_exception()
      return message, HTTPStatus.BAD_REQUEST
