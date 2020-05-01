from http import HTTPStatus

import orjson

from common import common_container
from common.nsn_logging import debug, error, warning
from common.data_types import item_from_article, article_from_dict
from common.store_utils import post_store, put, safe_get, tag_store
from converters import document_to_item
from document_info import is_reddit


def is_cluster_item(item):
  return item['item_type'] == 'CLUSTER'

class Ingestion:

  def __init__(self, container):
    self.container = container
    # Bad early optimization, but just retrieving the hasher takes ~20us - so prefer caching.
    self.hash_id = container.hasher().hash
    self.ps = post_store(self.container.kv_store())
    self.ts = tag_store(self.container.kv_store())

  # def _get_or_create_cluster(self, id_):
  #   try:
  #     cluster = orjson.loads(self.ps.get(id_))
  #     if not isinstance(cluster, dict):
  #       raise KeyError()
  #   except KeyError:
  #     self._add_cluster_name(id_)
  #     cluster = {'id': id_, 'posts': [], 'title_text': id_, 'type': 'CLUSTER'}
  #   return cluster

  def _add_to_tag(self, tag_name, item):
    tags = safe_get(self.ts, tag_name, list)
    tags.append(item.global_id)
    put(self.ts, tag_name, tags)

  def _add_tags(self, source_name, document, item):
    self._add_to_tag(source_name, item)
    # if is_cluster_item(item):
    #   for post in item['posts']:
    #     self._add_to_tag(f'{source_name}_cluster_posts', post['id'])
    if is_reddit(document):
      self._add_to_tag(document['subreddit_name'], item)


  def _ingest_article(self, source_name, article):
    item = item_from_article(article)
    # document_to_item(document, lambda d: self.hash_id(
    #     f'{source_name}{d["article_url"]}{d["local_id"]}'))
    # TODO: Log original document with same ID?
    # TODO: Split cluster & inner-posts?
    put(self.ps, item.global_id, item.to_dict())
    self._add_tags(source_name, article.to_dict(), item)

  def ingest(self, content):
    debug(f'Ingesting data!!: {content}')
    assert isinstance(content, dict), type(content)
    source_name = content['source_name']
    articles = [article_from_dict(a) for a in content['articles']]
    try:
      # TODO: Consider being more nuanced here in handling partial ingestion - feels very arbitrary
      # to ingest first N articles until a single bad doc is hit...
      for article in articles:
        self._ingest_article(source_name, article)
      return ''  # Return something so Response is marked successful.
    except Exception as e:
      message = f'Ingested data does not match expected format: [{{doc}}, {{doc}}, ...]. Got: {content}. Error: {e}'
      error(message)
      self.container.error_reporter().report_exception()
      return message, HTTPStatus.BAD_REQUEST
