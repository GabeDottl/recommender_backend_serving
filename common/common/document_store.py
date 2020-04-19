from typing import List
from .nsn_logging import debug


class DocumentStore:

  def get_collections(self) -> 'Dict[str, Collection]':
    raise Exception(f'get_collections not implemented')

  def get_collection(self, name) -> 'Collection':
    raise Exception(f'get_collection not implemented')

  def has_collection(self, collection_name):
    raise Exception(f'has_collection not implemented')

  def get_all_documents(self, name) -> List:
    raise Exception(f'get_all_documents not implemented')


class Collection:
  # TODO: Flush? Would be nice to not make as many indiv. requests but also keep impl. detailt
  # abstracted away.

  def append_documents(self, documents):
    raise Exception(f'append_documents not implemented')

  def get_documents(self):
    raise Exception(f'get_documents not implemented')


class NoopDocumentStore:

  def get_collection(self, name) -> 'Collection':
    debug(f'Noop: get_collection')
    return NoopCollection()

  def get_all_documents(self, name) -> List:
    debug(f'Noop: get_all_documents')
    return []


class NoopCollection:

  def append_documents(self, documents):
    debug(f'Noop: append_documents')
    pass

  def get_documents(self):
    debug(f'Noop: get_documents')
    return []
