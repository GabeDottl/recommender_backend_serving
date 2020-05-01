from document_info import is_reddit

def _document_to_post(doc, global_id_fn):
  post = {
      'type':
          'POST',
      'title_text':
          doc['title_text'],
      'secondary_text':
          doc['secondary_text'],
      'id':
          global_id_fn(doc),  # UID of the post for tracking.
      # TODO: Generate URL for content where applicable, e.g. Reddit?
      'url':
          doc['article_url'] if 'article_url' in doc else '',  # Optional.
      # URL to thumbnail image.
      'thumbnail':
          doc['image_url'] if 'image_url' in doc else
          doc['thumbnail'] if 'thumbnail' in doc else '',
      # May come in as float - we want to send out as an int.
      'created_utc_sec':
          doc['created_utc_sec'],
      'liked':
          0  # 0 or 1.
  }
  if is_reddit(doc):
    return _document_to_reddit_post(post, doc)
  return post

def _document_to_reddit_post(post, doc):
  post['item_type'] = 'REDDIT_POST'
  post['subreddit'] = doc['subreddit_name']
  post['author'] = doc['author_name']
  post['score'] = int(doc['score'])
  return post

def _document_to_cluster(doc, global_id_fn):
  assert len(doc['posts']) > 0, doc
  cluster = {}
  cluster['title_text'] = doc['title_text']
  cluster['id'] = global_id_fn(doc)
  posts = cluster['posts'] = []
  for post_doc in doc['posts']:
    posts.append(_document_to_post(post_doc, global_id_fn))
  return cluster

def document_to_item(doc, global_id_fn):
  if doc['article_type'] == 'POST':
    return _document_to_post(doc, global_id_fn)
  assert doc['item_type'] == 'CLUSTER'
  return _document_to_cluster(doc, global_id_fn)
