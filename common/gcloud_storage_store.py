#!/usr/bin/env python
# coding=utf8

import http
import os
from contextlib import contextmanager

from google.cloud import storage
# from .._compat import imap
from simplekv import KeyValueStore

from .nsn_logging import error, warning


@contextmanager
def map_gcloud_exceptions(key=None, exc_pass=()):
  try:
    yield
  except Exception as e:
    raise e


class GcloudStorageStore(KeyValueStore):

  def __init__(self, bucket, prefix=''):
    self.prefix = prefix.strip()  #.lstrip('/')
    client = storage.Client()
    self.bucket = client.bucket(bucket)


  def iter_keys(self, prefix=u""):
    # with map_gcloud_exceptions():
    #   prefix_len = len(self.prefix)
      # In order to get 'top-level dirs' we kind of need to hack Storage since it's actually a flat
      # namespace...
      # https://github.com/googleapis/google-cloud-python/issues/920
    iterator = self.bucket.list_blobs(delimiter='/', prefix=self.prefix)
    for blob in iterator:
      yield blob.name

  def _has_key(self, key):
    with map_gcloud_exceptions(key=key):
      return self.bucket.blob(key).exists()

  def _delete(self, key):
    try:
      self.bucket.blob(key).delete()
    except Exception as e:
      warning(f'Failed to delete {key}. {e}')

  def _get(self, key):
    with map_gcloud_exceptions(key=key):
      try:
        return self.bucket.blob(key).download_as_string()
      except Exception as e:
        # warning(f'Failed to download {key}. {e}')
        raise KeyError(key)

  def _get_file(self, key, file):
    with map_gcloud_exceptions(key=key):
      try:
        return self.bucket.blob(key).download_as_file(file)
      except Exception as e:
        # warning(f'Failed to download {key}. {e}')
        raise KeyError(key)

  def _get_filename(self, key, filename):
    with map_gcloud_exceptions(key=key):
      try:
        return self.bucket.blob(key).download_as_filename(filename)
      except Exception as e:
        # warning(f'Failed to download {key}. {e}')
        raise KeyError(key)

  def _put(self, key, data):
    with map_gcloud_exceptions(key=key):
      self.bucket.blob(key).upload_from_string(data)
      return key

  def _put_file(self, key, file):
    with map_gcloud_exceptions(key=key):
      self.bucket.blob(key).upload_from_file(file)
      return key

  def _put_filename(self, key, filename):
    with map_gcloud_exceptions(key=key):
      self.bucket.blob(key).upload_from_filename(filename)
      return key


  # def _open(self, key):
  #   from boto.s3.keyfile import KeyFile

  #   class SimpleKeyFile(KeyFile):

  #     def read(self, size=-1):
  #       if self.closed:
  #         raise ValueError("I/O operation on closed file")
  #       if size < 0:
  #         size = self.key.size - self.location
  #       return KeyFile.read(self, size)

  #     def seekable(self):
  #       return False

  #     def readable(self):
  #       return True

  #   k = self.__new_key(key)
  #   with map_gcloud_exceptions(key=key):
  #     return SimpleKeyFile(k)

  # def _copy(self, source, dest):
  #   if not self._has_key(source):
  #     raise KeyError(source)
  #   with map_gcloud_exceptions(key=source):
  #     self.bucket.copy_key(self.prefix + dest, self.bucket.name,
  #                          self.prefix + source)

  # def _url_for(self, key):
  #   k = self.__new_key(key)
  #   with map_gcloud_exceptions(key=key):
  #     return k.generate_url(expires_in=self.url_valid_time, query_auth=False)
