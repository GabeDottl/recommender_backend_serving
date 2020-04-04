'''A thread-safe module for wrapping document storage.

In production, RedisDocumentStore or even a FirestoreDocumentStore should be used instead.

Note that this achieves threadsafety primarily by relying on thread-safe operations on native python
objects and a careful API.

This site provides some helpful reference here:
http://effbot.org/pyfaq/what-kinds-of-global-value-mutation-are-thread-safe.htm

'''
import os

from itertools import chain

from common.runtime_args import parser, parse_known_args
from common.utils import cached_fn
from common.nsn_logging import debug, error, info

parser.add_argument('--local-data', action='store_true', dest='local_data')


@cached_fn
def get_document_store():
  args = parse_known_args()
  if args.local_data:
    return LocalDocumentStore.load(
        os.path.join(os.getenv('DATA'), 'recommender'))

  return LocalDocumentStore()


class LocalDocumentStore:

  def __init__(self):
    self._sources = {}

  def append_documents(self,
                       collection_name,
                       documents,
                       dont_mutate_input=True):
    try:
      self._sources[collection_name].extend(documents)
    except KeyError:
      if dont_mutate_input:
        # We wrap documents in a list() so we don't mutate it.
        self._sources[collection_name] = list(documents)
      else:
        # This can be much faster for large lists and is worthwhile if |documents| is throwaway.
        self._sources[collection_name] = documents

  def get_documents(self):
    '''TODO: Parameters for early-filtering. This should be the source for candidate generation -
    if we know the user doesn't like certain broad categories of content, this would be a logical
    place to handle that.'''
    return chain([source[:5] for source in self._sources.values()])

  def save(self, path):
    # TODO: Support cloud storage.
    import os
    import json
    # path = os.path.join(os.getenv('DATA'), 'recommender')
    for collection, documents in self._sources.items():
      filename = os.path.join(path, f'{collection}.json')
      with open(filename, 'w') as f:
        json.dump(documents, f)

  @staticmethod
  def load(path) -> 'LocalDocumentStore':
    import os
    out = LocalDocumentStore()
    debug(f'Loading local data from {path}')
    if os.path.exists(path):
      from glob import glob
      for json_file in glob(os.path.join(path, '*json')):
        collection_name = os.path.splitext(os.path.basename(json_file))[0]
        debug(f'collection_name: {collection_name}')
        with open(json_file, 'r') as f:
          import json
          try:
            out._sources[collection_name] = json.load(f)
            debug(
                f'len(out._sources[collection_name]): {len(out._sources[collection_name])}'
            )
          except Exception as e:
            error(f'Failed to load {json_file}. {e}')
    return out
