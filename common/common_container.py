import os
from dependency_injector import containers, providers
from argparse import ArgumentParser

from .local_document_store import LocalDocumentStore
from .serving_document_store import ServingDocumentStore
from . import nsn_logging
from .nsn_logging import info, warning, error, debug

class BaseContainer(containers.DeclarativeContainer):

  config = providers.Configuration('config')

  local_document_store = providers.Singleton(LocalDocumentStore.load, config.data_dir)

  serving_document_store = providers.Singleton(ServingDocumentStore, config.serving_append_endpoint)

  document_store = local_document_store

def arg_container():
  config = _default_config().copy()
  parser = ArgumentParser()
  parser.add_argument('--local', action='store_true')
  parser.add_argument(
    '--verbosity',
    type=str,
    nargs='?',
    default=config['verbosity'],
    choices=['info', 'debug', 'warning', 'error'])
  parser.add_argument('--local-data', action='store_true', dest='local_data')
  args, _ = parser.parse_known_args()
  nsn_logging.set_verbosity(config['verbosity'])
  config.update(vars(args))
  if args.local:
    config['serving_address'] = _local_address()
  _apply_secondary_config(config)
  return BaseContainer(config=config)

def _apply_secondary_config(config):
  '''Applies configuration values which are directly dependent on earlier ones.'''
  config['serving_append_endpoint'] = f'{config["serving_address"]}/ingest'

def _default_config():
  is_gce = _is_gce()
  return {
    'serving_address': _external_static_ip(),
    'is_gce': is_gce,
    'version': _get_git_commit(),
    'verbosity': 'info',
    'data_dir': './data' if is_gce else os.path.join(os.getenv('DATA'), 'recommender'),
    'local_data': False
  }

def _get_git_commit():
  import subprocess
  try:
    # Need to decode (binary returned) and drop new-lines at the end.
    # These functions turn out to be pretty cheap to run - ~10ms.
    commit_hash = subprocess.check_output(
        ['git', 'rev-parse', '--short', 'HEAD']).decode()[:-1]
    return subprocess.check_output(['git', 'show-branch',
                                    commit_hash]).decode()[:-1]
  except Exception as e:
    error(f'Failed to get git hash; {e}')
  return 'Unknown commit'

def _gce_address():
  port = 5000
  # [INSTANCE_NAME].[ZONE].c.[PROJECT_ID].internal
  instance_name = 'serving-1'
  zone = 'us-west2-a'
  project_id = 'recommender-270613'
  # NOTE: This won't work with cloud-shell since it's not in our VPC.
  address = f'http://{instance_name}.{zone}.c.{project_id}.internal:{port}'

def _external_static_ip():
  port = 5000
  return f"http://34.94.222.40:{port}"

def _local_address(): return 'http://localhost:5000'

def _is_gce():
  import os
  import socket
  hostname = socket.gethostname()
  local = os.getenv(
      'IS_LOCAL'
  ) is not None or hostname == 'gabe-ubuntu' or hostname == 'Gabes-MacBook-Pro.local'
  info(
      f'Running on {hostname} - treated as {"non-GCE/local" if local else "GCE"}. Project at git-commit {_get_git_commit()}'
  )
  return not local

