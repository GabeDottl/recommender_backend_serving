'''A DocumentStore which wraps the REST API of the serving repo.'''

import requests
from . import settings
from .utils import request_wrapper
from .document_store import DocumentStore, Collection
from .nsn_logging import debug, error


class ServingDocumentStore(DocumentStore):
  def __init__(self, remote_address, error_reporter):
    self.remote_address = remote_address
    self.error_reporter = error_reporter

  def get_collection(self, name):
    return ServingCollection(self.remote_address, self.error_reporter, name)


class ServingCollection(Collection):
  def __init__(self, remote_address, error_reporter, name):
    self.remote_address = remote_address
    self.error_reporter = error_reporter
    self.name = name

  def append_documents(self, documents):
    debug(f'Sending {len(documents)} to {self.remote_address}')
    try:
      resp = requests.post(self.remote_address, json={'collection': self.name, 'documents': documents})
      if resp.status_code != 200:
        message = f'Failed to send {len(documents)} to serving. Error code: {resp.status_code}: {resp.text}'
        error(message)
        self.error_reporter.report(message)
      return resp
    except Exception as e:
      message = f'Failed to send {len(documents)} to serving. Exception: {str(e)}'
      error(message)
      self.error_reporter.report_exception(e)
    return None
