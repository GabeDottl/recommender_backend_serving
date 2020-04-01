from .nsn_logging import debug, error, info, warning
from .utils import cached_fn


def setup_cloud_logging():
  import google.cloud.logging
  from google.oauth2 import service_account
  import os
  if _is_gce:
    client = google.cloud.logging.Client()
  else:
    credentials_path = os.path.join(
        os.getenv('CONFIG'), 'recommender_firestore_service_acct.json')
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path)
    scoped_credentials = credentials.with_scopes(
        ['https://www.googleapis.com/auth/cloud-platform'])
    client = google.cloud.logging.Client(
        project='recommender-270613', credentials=scoped_credentials)
  error('Final log to console! Moving to cloud logger')
  client.setup_logging()
  info(f'Logging configured. Project at: {get_git_commit()}')


@cached_fn
def get_git_commit():
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


def setup_cloud_profiling(service_name):
  import googlecloudprofiler
  # Profiler initialization. It starts a daemon thread which continuously
  # collects and uploads profiles. Best done as early as possible.
  info(f'Setting up cloud profiler with service_name {service_name}')
  try:
    googlecloudprofiler.start(
        service=service_name,
        service_version=get_git_commit(),
        # verbose is the logging level. 0-error, 1-warning, 2-info,
        # 3-debug. It defaults to 0 (error) if not set.
        verbose=0,
        # project_id must be set if not running on GCP.
        project_id='recommender-270613',
    )
  except Exception as exc:
    error(exc)  # Handle errors here


def _is_gce():
  import os
  import socket
  hostname = socket.gethostname()
  local = os.getenv(
      'IS_LOCAL'
  ) is not None or hostname == 'gabe-ubuntu' or hostname == 'Gabes-MacBook-Pro.local'
  info(
      f'Running on {hostname} - treated as {"non-GCE/local" if local else "GCE"}. Project at git-commit {get_git_commit()}'
  )
  return not local


is_gce = _is_gce()
