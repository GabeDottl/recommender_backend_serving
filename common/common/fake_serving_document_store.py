'''A fake DocumentStore which wraps the REST API of the serving repo.'''
from .document_store import DocumentStore, Collection
from .standard_keys import REQUIRED_SOURCE_KEYS


class FakeServingCollection(Collection):
  def append_documents(self, documents):
    for doc in documents:
      for k in REQUIRED_SOURCE_KEYS:
        assert k in doc


class FakeServingDocumentStore(DocumentStore):
  collection = FakeServingCollection()

  def get_collection(self, name):
    return self.collection
