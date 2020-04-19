import os
import shutil
from dependency_injector import containers, providers
from argparse import ArgumentParser
from simplekv.memory import DictStore
from simplekv.cache import CacheDecorator
from simplekv.memory.redisstore import RedisStore
from simplekv.fs import FilesystemStore
from redis import Redis
from boltons.cacheutils import LRU
from boltons.funcutils import wraps

from google.cloud import error_reporting

from .id_hasher import IdHasher
from .local_document_store import LocalDocumentStore
from .serving_document_store import ServingDocumentStore
from .cloud_storage_document_store import CloudStorageDocumentStore
from .gcloud_storage_store import GcloudStorageStore
from . import nsn_logging
from .nsn_logging import info, error, warning


def _redis_store(redis_ip):
  # initialize redis instance
  r = Redis(host=redis_ip)
  return RedisStore(r)


def _cloud_store():
  pass


def _kv(config: dict):
  # return CacheDecorator(cache=DictStore(), store= GcloudStorageStore('kv_store_test'))
  if config['mode'] == 'test':
    info('test: Using simple DictStore')
    return DictStore(d=LRU(max_size=1024))
  dir_ = os.path.join(config['data_dir'], 'kv')
  if not os.path.exists(dir_):
    os.makedirs(dir_)
  if config['mode'] == 'local':
    info('local: Using simple DictStore + FS')
    return CacheDecorator(cache=DictStore(), store=FilesystemStore(dir_))
  # TODO: Use Gcloud storage instead.
  info('prod: Using simple Redis+GS')
  return CacheDecorator(
      cache=_redis_store(config['redis_ip']),
      store=GcloudStorageStore('kv_store_test'))

def exception_wrapper(reporter, consume_exception=False):
  def meta_wrapper(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
      try:
        return fn(*args, **kwargs)
      except Exception:
        reporter.report_exception()
        raise
    return wrapper
  return meta_wrapper

def instance_exception_wrapper(consume_exception=False):
  def meta_wrapper(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
      try:
        return fn(self, *args, **kwargs)
      except Exception:
        self.container.error_reporter().report_exception()
        raise
    return wrapper
  return meta_wrapper


def _dynamic_container(config: providers.Configuration):
  out = containers.DynamicContainer()
  out.config = config
  if not config.is_gce() or config.test():
    out.error_reporter = providers.ThreadSafeSingleton(LoggingErrorReporter)
  else:
    # Log to both GCP & the error log.
    gcp_reporter = error_reporting.Client(service=config.service_name())
    logging_reporter = LoggingErrorReporter()
    out.error_reporter = providers.ThreadSafeSingleton(MultiErrorReporter,
                                                       gcp_reporter,
                                                       logging_reporter)

  out.hasher = providers.ThreadSafeSingleton(IdHasher)
  # Note that out.config() -> dict.
  out.kv_store = providers.ThreadSafeSingleton(_kv, out.config)
  out.source_document_store = providers.ThreadSafeSingleton(
      LocalDocumentStore.load, os.path.join(config.data_dir(), 'source'))
  out.cluster_document_store = providers.ThreadSafeSingleton(
      LocalDocumentStore.load, os.path.join(config.data_dir(), 'cluster'))
  out.user_document_store = providers.ThreadSafeSingleton(
      LocalDocumentStore.load, os.path.join(config.data_dir(), 'user'))
  if config.test():
    from .fake_serving_document_store import FakeServingDocumentStore
    from .document_store import NoopDocumentStore
    out.serving_document_store = providers.ThreadSafeSingleton(
        FakeServingDocumentStore)
    # DocumentStore == NoopDocumentStore
    out.cloud_storage_document_store = providers.ThreadSafeSingleton(
        NoopDocumentStore)
  else:  # not test.
    out.serving_document_store = providers.ThreadSafeSingleton(
        ServingDocumentStore, config.serving_append_endpoint,
        out.error_reporter)
    out.cloud_storage_document_store = providers.ThreadSafeSingleton(
        CloudStorageDocumentStore, config.bucket_name)

  return out


def cleanup(config):
  if not config.test():
    warning('no cleanup to do for non-test configs')
    return

  if os.path.exists(config.data_dir()):
    shutil.rmtree(config.data_dir())


class LoggingErrorReporter:

  def report(self, message, *args, **kwargs):
    error(f'Logging error: {message}')

  def report_exception(self, *args, **kwargs):
    import sys
    type_, value, traceback = sys.exc_info()
    error(f'Logging: Reporting exception of type {type}: {value}')


class MultiErrorReporter:

  def __init__(self, reporter_a, reporter_b):
    self.reporter_a = reporter_a
    self.reporter_a = reporter_a

  def report(self, *args, **kwargs):
    self.reporter_a.report(*args, **kwargs)
    self.reporter_b.report(*args, **kwargs)

  def report_exception(self, *args, **kwargs):
    self.reporter_a.report_exception(*args, **kwargs)
    self.reporter_b.report_exception(*args, **kwargs)


def arg_container(*, overrides={}, test=False):
  config = _default_config().copy()
  parser = ArgumentParser()
  parser.add_argument(
      '--verbosity',
      type=str,
      nargs='?',
      default=config['verbosity'],
      choices=['info', 'debug', 'warning', 'error'])
  parser.add_argument('--debug-mode', action='store_true', dest='debug_mode')
  parser.add_argument('--clear-user', action='store_true', dest='clear_user')

  args, _ = parser.parse_known_args()
  if test:
    config['mode'] = 'test'
  config.update(vars(args))
  _update_config_for_mode(config)
  # Apply args provided directly to function last to overwrite anything else.
  config.update(overrides)
  _apply_secondary_config(config)
  nsn_logging.set_verbosity(config['verbosity'])
  provider_config = providers.Configuration('config')
  provider_config.override(config)
  info(f'Configuration is: {config}')
  return _dynamic_container(provider_config)


def _apply_secondary_config(config):
  '''Applies configuration values which are directly dependent on earlier ones.'''

  config['serving_append_endpoint'] = f'{config["serving_address"]}/ingest'


def _update_config_for_mode(config):
  mode = config['mode']  # prod, local, test
  if mode == 'prod':
    config['serving_address'] = _external_static_ip()
    config['redis_ip'] = '10.214.155.187'
    config['data_dir'] = './tmp'
  else:  # local, test
    config['serving_address'] = _local_address()
    config['redis_ip'] = 'localhost'
    if mode == 'test':
      config['verbosity'] = 'debug'
      tmp_dir = './tmp'
      if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
      os.makedirs(tmp_dir)
      config['data_dir'] = tmp_dir
    else:  # local
      if not config['is_gce'] and os.getenv('DATA'):
        data_dir = os.path.join(os.getenv('DATA'), 'recommender')
      else:
        data_dir = './data'
      config['data_dir'] = data_dir


def _default_config():
  is_gce = _is_gce()

  mode = 'prod' if is_gce else 'local'

  # Note: These are sorted and clustered by relatedness and relevance for debugging.
  # This is to make it easier to debug configuration issue when this is printed at runtime.
  return {
      'is_gce': is_gce,
      'mode': mode,
      'debug_mode': False,
      'clear_user': False,
      'verbosity': 'info',
      'project_id': 'recommender-270613',
      'version': _get_git_commit(),
      'service_name': _get_service_name(),
      'bucket_name': 'recommender_collections',
  }


def _get_service_name():
  # Name of project dir.
  return os.path.basename(
      os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
  return f'http://{instance_name}.{zone}.c.{project_id}.internal:{port}'


def _external_static_ip():
  port = 5000
  return f'http://34.94.210.159:{port}'


def _local_address():
  return 'http://localhost:5000'


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
