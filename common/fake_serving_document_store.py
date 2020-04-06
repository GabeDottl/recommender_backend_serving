'''A fake DocumentStore which wraps the REST API of the serving repo.'''
from .document_store import DocumentStore, Collection
from .standard_keys import REQUIRED_SOURCE_KEYS

class FakeServingDocumentStore(DocumentStore):
  def get_collection(self, name):
    return FakeServingCollection()

class FakeServingCollection(Collection):
  def append_documents(self, documents):
    for doc in documents:
      for k in REQUIRED_SOURCE_KEYS:
        assert k in doc
