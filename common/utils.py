import os
from time import time, sleep
import requests
from boltons.funcutils import wraps
from functools import partial
from boltons.cacheutils import cachedproperty as lazy_property, cached # For exporting.

from .nsn_logging import info, debug, error, warning

# _fn_cache = {}
# cached_fn = cached(cache=_fn_cache)

def cached_fn(fn):
  '''A slightly fancy no-arg function cache.'''
  out = None
  run = False
  @wraps(fn)
  def wrapper(*args, **kwargs):
    nonlocal out, run
    if run:
      return out
    out = fn(*args, **kwargs)
    run = True
    return out
  return wrapper

def lazy_makedirs(func):
  @wraps(func)
  def wrapper(*args, **kwargs):
    path = func(*args, **kwargs)
    if not os.path.exists(path):
      os.makedirs(path)
    return path

  return wrapper


def request_wrapper(fn):
  '''Function for wrapping functions which make requests and return Responses.

  Logs errors.'''
  @wraps(fn)
  def wrapper(*args, **kwargs):
    try:
      resp = fn(*args, **kwargs)
      if resp.status_code != 200:
        warning(f'{fn.__qualname__}: {resp.reason}')
      return resp
    except Exception as e:
      warning(f'{fn.__qualname__}: {e}')
      return None
  return wrapper

def run_for_at_least_n_sec(fn, sec):
  start = time()
  fn()
  end = time()
  rem = sec - end - start
  if rem > 0:
    # Sleep the remainder
    sleep(rem)
