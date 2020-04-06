from .nsn_logging import debug, error, info, warning
from .utils import cached_fn


# def setup_cloud_logging():
#   import google.cloud.logging
#   from google.oauth2 import service_account
#   import os
#   if _is_gce:
#     client = google.cloud.logging.Client()
#   else:
#     credentials_path = os.path.join(
#         os.getenv('CONFIG'), 'recommender_firestore_service_acct.json')
#     credentials = service_account.Credentials.from_service_account_file(
#         credentials_path)
#     scoped_credentials = credentials.with_scopes(
#         ['https://www.googleapis.com/auth/cloud-platform'])
#     client = google.cloud.logging.Client(
#         project='recommender-270613', credentials=scoped_credentials)
#   error('Final log to console! Moving to cloud logger')
#   client.setup_logging()
#   info(f'Logging configured. Project at: {get_git_commit()}')





def setup_cloud_profiling(service_name):
  info(f'Setting up cloud profiler with service_name {service_name}')
  # TODO: For some reason, importing googlecloudprofiler causes logs to appear twice...
  import googlecloudprofiler
  # Profiler initialization. It starts a daemon thread which continuously
  # collects and uploads profiles. Best done as early as possible.
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


# @cached_fn
# def get_serving_address(localhost=False):
#   from argparse import ArgumentParser
#   parser = ArgumentParser()
#   args, _ = parser.parse_known_args()


#   # NOTE / WARNING: This function is cached without it's argument - so whoever calls this first
#   # dictates the value of |localhost|. This is a helpful hack for allowing interactive sessions
#   # to force a local serving instance.
#   port = 5000
#   if localhost or args.local:
#     address = f'http://localhost:{port}'
#     warning(f'Using localhost as serving IP. {address}')
#   elif is_gce:

#     info(f'Using VPC internal DNS name: {address}')
#   else:
#     address = f"http://34.94.222.40:{port}"
#     warning(f'Using static IP!!! May not work... {address}')
#   return address
