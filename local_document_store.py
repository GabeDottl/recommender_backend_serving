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

from common.runtime_args import parser, parse_known_args
from common.utils import cached_fn
from common.nsn_logging import debug, error, info
from common.standard_keys import REQUIRED_SOURCE_KEYS

parser.add_argument('--local-data', action='store_true', dest='local_data')


@cached_fn
def get_document_store():
  args = parse_known_args()
  path = os.path.join(os.getenv('DATA'), 'recommender')
  if args.local_data:
    return LocalDocumentStore.load(path)

  return LocalDocumentStore(path)


class LocalDocumentStore:

  def __init__(self, collections_path):
    self.collections_path = collections_path
    self._collections = {}

  def get_or_create_collection(self, name):
    if name in self._collections:
      return self._collections[name]
    out = self._collections[name] = Collection.load(
        name_to_path(self.collections_path, name))
    return out

  def get_all_documents(self):
    '''TODO: Parameters for early-filtering. This should be the source for candidate generation -
    if we know the user doesn't like certain broad categories of content, this would be a logical
    place to handle that.'''
    return chain.from_iterable(source for source in self._collections.values())

  def get_documents(self, collection_names):
    '''TODO: Parameters for early-filtering. This should be the source for candidate generation -
    if we know the user doesn't like certain broad categories of content, this would be a logical
    place to handle that.'''
    # Only return results for existing collections.
    names = filter(lambda n: n in self._collections, collection_names)
    collections = [self._collections[name] for name in names]
    return chain.from_iterable(
        collection.documents for collection in collections)

  def save(self):
    # TODO: Support cloud storage.
    # path = os.path.join(os.getenv('DATA'), 'recommender')
    for collection in self._collections.values():
      collection.save()

  @staticmethod
  def load(path) -> 'LocalDocumentStore':
    import os
    out = LocalDocumentStore()
    debug(f'Loading local data from {path}')
    if os.path.exists(path):
      from glob import glob
      for json_file in glob(os.path.join(path, '*json')):
        collection = Collection.load(json_file)
        out._collections[collection.name] = collection
        debug(f'collection_name: {collection.name}')

    return out

  # @cached_fn
  # def get_collection(self):
  #   if 'user' in self._collections:
  #     return self._collections['user']
  #   path = os.path.join(os.getenv('DATA'), 'recommender', 'user.json')
  #   return Collection.load(path)


def path_to_name(path) -> str:
  return os.path.splitext(os.path.basename(path))[0]


def name_to_path(base_path, name) -> str:
  return f'{base_path}/{name}.json'


class Collection:

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
    # filename = os.path.join(path, f'{self.name}.json')
    with open(self.path, 'w') as f:
      json.dump(self.documents, f)


# def get_user_collection():
#   path = os.path.join(os.getenv('DATA'), 'recommender', 'sources.json')
#   try:
#     return Collection.load(path)
#   except FileNotFoundError:
#     return Collection(path)
