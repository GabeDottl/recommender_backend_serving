from http import HTTPStatus

import orjson

from common import common_container
from common.nsn_logging import debug, error, warning
from common.standard_keys import item_from_source_dict
from common.store_utils import post_store, put, safe_get, tag_store
from converters import document_to_item
from document_info import is_reddit


def is_cluster_item(item):
  return item['type'] == 'CLUSTER'

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

  def _add_tags(self, collection_name, document, item):
    self._add_to_tag(collection_name, item)
    # if is_cluster_item(item):
    #   for post in item['posts']:
    #     self._add_to_tag(f'{collection_name}_cluster_posts', post['id'])
    if is_reddit(document):
      self._add_to_tag(document['subreddit_name'], item)


  def _ingest_document(self, collection_name, source_dict):
    item = item_from_source_dict(source_dict)
    # document_to_item(document, lambda d: self.hash_id(
    #     f'{collection_name}{d["source_url"]}{d["local_id"]}'))
    # TODO: Log original document with same ID?
    # TODO: Split cluster & inner-posts?
    put(self.ps, item.global_id, item.to_dict())
    self._add_tags(collection_name, source_dict, item)

  def ingest(self, content):
    debug(f'Ingesting data!!: {content}')
    collection_name = content['collection']
    documents = content['documents']
    try:
      # TODO: Consider being more nuanced here in handling partial ingestion - feels very arbitrary
      # to ingest first N documents until a single bad doc is hit...
      for document in documents:
        self._ingest_document(collection_name, document)
      return ''  # Return something so Response is marked successful.
    except Exception as e:
      message = f'Ingested data does not match expected format: [{{doc}}, {{doc}}, ...]. Got: {content}. Error: {e}'
      error(message)
      self.container.error_reporter().report_exception()
      return message, HTTPStatus.BAD_REQUEST
