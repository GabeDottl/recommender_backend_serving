# For use within main repos - e.g. serving, news_api, etc.
# Use this script if you make changes in a main repo to common/ and need to push those changes back
# to the common repo and all subbranches.
# Alternatively, just do `git subrepo push` to avoid triggering new commits across 
git subrepo push
# TODO: This is going to really muck up git histories...
./synchronize_common.sh