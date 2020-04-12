import orjson

from simplekv.decorator import PrefixDecorator


def safe_get(store, name, fallback_fn):
  try:
    return orjson.loads(store.get(name))
  except KeyError:
    return fallback_fn()

def post_store(store):
  return PrefixDecorator('post_', store)


def cluster_store(store):
  return PrefixDecorator('cluster_', store)
