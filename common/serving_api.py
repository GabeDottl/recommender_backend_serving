import requests
from . import settings
from .utils import request_wrapper

@request_wrapper
def push_documents(collection, documents):
  url = f'{settings.get_serving_address()}/ingest'
  return requests.post(url, json={'collection': collection, 'documents': documents})
