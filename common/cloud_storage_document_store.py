from google.cloud import storage
from google.oauth2 import service_account
import json
import os.path
from datetime import datetime

from .document_store import DocumentStore, Collection
from .nsn_logging import debug, info, error, warning

class CloudStorageDocumentStore(DocumentStore):
  def __init__(self, bucket_name):
    client = storage.Client()
    self.bucket = client.get_bucket(bucket_name) # 'recommender_collections')

  def get_collections(self):
    # In order to get 'top-level dirs' we kind of need to hack Storage since it's actually a flat
    # namespace...
    # https://github.com/googleapis/google-cloud-python/issues/920
    iterator = self.bucket.list_blobs(delimiter='/', prefix='/')
    # Note iterator is curiously empty initially?
    resp = iterator._get_next_page_response()
    return list([p[1:-1] for p in resp['prefixes']])

  def has_collection(self, name):
    return name in self.get_collections()

  def get_collection(self, name):
    return CloudStorageCollection(self.bucket, name)

class CloudStorageCollection(Collection):
  def __init__(self, bucket, collection_name):
    self.bucket = bucket
    self.collection_name = collection_name
  
  def append_documents(self, documents):
    assert len(documents) >= 1
    blob_name = os.path.join('/',self.collection_name, datetime_to_name(datetime.now()), str(documents[0]["id"]))
    debug(f'Uploaded blob {blob_name}')
    blob = storage.Blob(bucket=self.bucket, name=blob_name)
    blob.upload_from_string(json.dumps(documents))


def datetime_to_name(dt: datetime):
  return dt.strftime('%y-%m-%dT%H:%M:%S')
