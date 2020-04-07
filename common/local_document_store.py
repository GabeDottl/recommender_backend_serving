'''A thread-safe module for wrapping document storage.

In production, RedisDocumentStore or even a FirestoreDocumentStore should be used instead.

Note that this achieves threadsafety primarily by relying on thread-safe operations on native python
objects and a careful API.

This site provides some helpful reference here:
http://effbot.org/pyfaq/what-kinds-of-global-value-mutation-are-thread-safe.htm

'''
import os
import json

from itertools import chain

from .utils import cached_fn
from .nsn_logging import debug, error, info
from .standard_keys import REQUIRED_SOURCE_KEYS
from . import document_store


class LocalDocumentStore(document_store.DocumentStore):
  def __init__(self, collections_path):
    self.collections_path = collections_path
    self.collections = {}

  def has_collection(self, collection_name):
    return collection_name in self.collections

  def get(self, name):
    if name in self.collections:
      return self.collections[name]
    out = self.collections[name] = Collection.load(name_to_path(self.collections_path, name))
    return out

  def get_all_documents(self):
    '''TODO: Parameters for early-filtering. This should be the source for candidate generation -
    if we know the user doesn't like certain broad categories of content, this would be a logical
    place to handle that.'''
    return chain.from_iterable(source for source in self.collections.values())

  def get_documents(self, collection_names):
    '''TODO: Parameters for early-filtering. This should be the source for candidate generation -
    if we know the user doesn't like certain broad categories of content, this would be a logical
    place to handle that.'''
    # Only return results for existing collections.
    names = filter(lambda n: n in self.collections, collection_names)
    collections = [self.collections[name] for name in names]
    return chain.from_iterable(collection.documents for collection in collections)

  def save(self):
    # TODO: Support cloud storage.
    # path = os.path.join(os.getenv('DATA'), 'recommender')
    for collection in self.collections.values():
      collection.save()

  @staticmethod
  def load(path) -> 'LocalDocumentStore':
    import os
    out = LocalDocumentStore(path)
    debug(f'Loading local data from {path}')
    if os.path.exists(path):
      from glob import glob
      for json_file in glob(os.path.join(path, '*json')):
        collection = Collection.load(json_file)
        out.collections[collection.name] = collection
        debug(f'collection_name: {collection.name}')

    return out


def path_to_name(path) -> str:
  return os.path.splitext(os.path.basename(path))[0]


def name_to_path(base_path, name) -> str:
  return f'{base_path}/{name}.json'


class LocalCollection(document_store.Collection):
  def __init__(self, path):
    self.path = path
    self.name = path_to_name(path)
    self.documents = []

  def append_documents(self, documents, dont_mutate_input=True):
    try:
      self.documents.extend(documents)
    except KeyError:
      if dont_mutate_input:
        # We wrap documents in a list() so we don't mutate it.
        self.documents = list(documents)
      else:
        # This can be much faster for large lists and is worthwhile if |documents| is throwaway.
        self.documents = documents

  @staticmethod
  def load(path, create_on_fail=True) -> 'Collection':
    out = Collection(path_to_name(path))
    try:
      with open(path, 'r') as f:
        out.documents = json.load(f)
        debug(f'out.documents: {len(out.documents)}')
    except Exception as e:
      if not create_on_fail:
        error(f'Failed to load {path}. {e}')
        raise e
    return out

  def save(self):
    with open(self.path, 'w') as f:
      json.dump(self.documents, f)
