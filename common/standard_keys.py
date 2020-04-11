'''This module mostly exists to establish some basic document keys that should be universal.'''
'''These keys define the expected keys in JSON documents provided by source (e.g. news_api, reddit).

Not all are required. More may be included by each source.

TODO: Consider formalizing this - e.g. SourceDocument class, protobuf, etc.
'''
REQUIRED_SOURCE_KEYS = (
    'id',  # Optional; auto-generated if not present.
    'image_url',
    'title_text',
    'secondary_text',  # E.g. Description, alt-text, etc.
    'created_utc_sec',
)

# Document
SOURCE_KEYS = (
    'id',  # Optional; auto-generated if not present.
    'image_url',
    'title_text',
    'secondary_text',  # E.g. Description, alt-text, etc.
    'created_utc_sec',
    'source_url',  # Optional; may be calculated depending on content.
    'retrieved_utc',  # Optional; TODO
)



def is_valid_item(item) -> bool:
    if not all(k in item for k in CLIENT_ITEM_KEYS):
      return False
    type_ = item['type']
    if type_ != 'POST' and type_ != 'CLUSTER':
      return False
    if item['type'] == 'POST' and not all(k in item for k in CLIENT_POST_KEYS):
      return False
    if item['type'] == 'CLUSTER' and not all(k in item for k in CLIENT_CLUSTER_KEYS):
      return False
    return True


CLIENT_ITEM_KEYS = ('type', 'id')

# Post
'''These define the contract of 'Posts' for the Client. Each JSON Post sent to the client should
have all of these except where explicitly marked optional.'''
CLIENT_POST_KEYS = (
    'type',  # 'POST',
    'title_text',
    'secondary_text',  # Secondary text to display under title. Should not exceed more than a few sentences.
    'id',  # UID of the post for tracking.
    'url',
    'thumbnail',  # URL to thumbnail image.
    # 'media_embed',
    'created_utc_sec',
    'liked'  # 0 or 1.
)

CLIENT_CLUSTER_KEYS = (
    'type',  # CLUSTER
    'name',
    'posts'  # List[Post]
)
