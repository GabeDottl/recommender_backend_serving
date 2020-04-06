'''A DocumentStore which wraps the REST API of the serving repo.'''

import requests
from . import settings
from .utils import request_wrapper
from .document_store import DocumentStore, Collection

class ServingDocumentStore(DocumentStore):
  def __init__(self, remote_address):
    self.remote_address = remote_address

  def get_collection(self, name):
    return ServingCollection(self.remote_address, name)

class ServingCollection(Collection):
  def __init__(self, remote_address, name):
    self.remote_address = remote_address
    self.name = name

  @request_wrapper
  def append_documents(self, documents):
    return requests.post(self.remote_address, json={'collection': self.name, 'documents': documents})
