import os
from dependency_injector import containers, providers
from argparse import ArgumentParser

from google.cloud import error_reporting

from .local_document_store import LocalDocumentStore
from .serving_document_store import ServingDocumentStore
from .cloud_storage_document_store import CloudStorageDocumentStore
from . import nsn_logging
from .nsn_logging import info, error


# TODO: Add test to ensure the providers in this match _dynamic_container.
def _test_container(config: providers.Configuration):
  from .fake_serving_document_store import FakeServingDocumentStore
  from .document_store import NoopDocumentStore
  out = containers.DynamicContainer()
  out.config = config
  out.error_reporter = providers.Singleton(NoOpErrorReporter)
  out.cluster_document_store = providers.Singleton(LocalDocumentStore.load,
                                                   os.path.join(config.data_dir(), 'cluster'))
  out.source_document_store = providers.Singleton(LocalDocumentStore.load,
                                                   os.path.join(config.data_dir(), 'source'))
  out.user_document_store = providers.Singleton(LocalDocumentStore.load,
                                                 os.path.join(config.data_dir(), 'user'))
  out.serving_document_store = providers.Singleton(FakeServingDocumentStore)
  # DocumentStore == NoopDocumentStore
  out.cloud_storage_document_store = providers.Singleton(NoopDocumentStore)
  print(config.local())
  return out


def _dynamic_container(config: providers.Configuration):
  out = containers.DynamicContainer()
  out.config = config
  if not config.is_gce():
    out.error_reporter = providers.Singleton(NoOpErrorReporter)
  else:
    out.error_reporter = providers.Singleton(error_reporting.Client, service=config.service_name)

  out.source_document_store = providers.Singleton(LocalDocumentStore.load,
                                                   os.path.join(config.data_dir(), 'source'))
  out.cluster_document_store = providers.Singleton(LocalDocumentStore.load,
                                                   os.path.join(config.data_dir(), 'cluster'))
  out.user_document_store = providers.Singleton(LocalDocumentStore.load,
                                                 os.path.join(config.data_dir(), 'user'))
  out.serving_document_store = providers.Singleton(ServingDocumentStore, config.serving_append_endpoint,
                                                   out.error_reporter)
  out.cloud_storage_document_store = providers.Singleton(CloudStorageDocumentStore, config.bucket_name)

  return out


class NoOpErrorReporter:
  def report(self, *args, **kwargs):
    print('Reporting')
    pass

  def report_exception(self, *args, **kwargs):
    pass


def arg_container(*, overrides={}, test=False):
  if test:
    assert 'data_dir' in overrides, 'data_dir must be provided by tests so they can perform cleanup.  '
  config = _default_config().copy()
  parser = ArgumentParser()
  parser.add_argument('--local', action='store_true')
  parser.add_argument('--verbosity',
                      type=str,
                      nargs='?',
                      default=config['verbosity'],
                      choices=['info', 'debug', 'warning', 'error'])
  parser.add_argument('--local-persistence', action='store_true', dest='local_persistence')
  parser.add_argument('--debug-mode', action='store_true', dest='debug_mode')
  # parser.add_argument('--clear')
  args, _ = parser.parse_known_args()
  if test:
    config['verbosity'] = 'debug'
  config.update(vars(args))
  config.update(overrides)
  # if test:
  #   config['data_dir']
  # config['local'] = config['local']

  if config['local'] and 'serving_address' not in overrides:
    config['serving_address'] = _local_address()
  _apply_secondary_config(config)
  nsn_logging.set_verbosity(config['verbosity'])
  provider_config = providers.Configuration('config')
  provider_config.override(config)
  info(f'Configuration is: {config}')
  if test:
    return _test_container(provider_config)
  return _dynamic_container(provider_config)


def _apply_secondary_config(config):
  '''Applies configuration values which are directly dependent on earlier ones.'''

  config['serving_append_endpoint'] = f'{config["serving_address"]}/ingest'
  nsn_logging.set_verbosity(config['verbosity'])


def _default_config():
  is_gce = _is_gce()
  if not is_gce and os.getenv('DATA'):
    data_dir = os.path.join(os.getenv('DATA'), 'recommender')
  else:
    data_dir = './data'

  # Note: These are sorted and clustered by relatedness and relevance for debugging.
  # This is to make it easier to debug configuration issue when this is printed at runtime.
  return {
      'is_gce': is_gce,
      'serving_address': _external_static_ip(),
      'local': False,
      'local_persistence': False,
      'debug_mode': False,
      'data_dir': data_dir,
      'verbosity': 'info',
      'project_id': 'recommender-270613',
      'version': _get_git_commit(),
      'service_name': _get_service_name(),
      'bucket_name': 'recommender_collections'
  }


def _get_service_name():
  # Name of project dir.
  return os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_git_commit():
  import subprocess
  try:
    # Need to decode (binary returned) and drop new-lines at the end.
    # These functions turn out to be pretty cheap to run - ~10ms.
    commit_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode()[:-1]
    return subprocess.check_output(['git', 'show-branch', commit_hash]).decode()[:-1]
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
  return f'http://{instance_name}.{zone}.c.{project_id}.internal:{port}'


def _external_static_ip():
  port = 5000
  return f'http://34.94.222.40:{port}'


def _local_address():
  return 'http://localhost:5000'


def _is_gce():
  import os
  import socket
  hostname = socket.gethostname()
  local = os.getenv(
      'IS_LOCAL') is not None or hostname == 'gabe-ubuntu' or hostname == 'Gabes-MacBook-Pro.local'
  info(
      f'Running on {hostname} - treated as {"non-GCE/local" if local else "GCE"}. Project at git-commit {_get_git_commit()}'
  )
  return not local
