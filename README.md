Author's note (January 2022): This is a little backend serving system for the Recommender flutter app which aggregated news sources (Reddit, Twitter, custom feeds) and attempted to give you recommended 'Tl;Dr' versions by aggregating content about similar stories and summarizing into a short (e.g. 5-word) Tl;Dr. Code is public, but license is restricted to non-commercial use (if you want to fork and use it for your company - let me know).

gunicorn 192.168.1.4:5000 "main:main_gunicorn()"
-e git+ssh://git@github.com/gabedottl/recommender_backend_common.git#egg=common


docker container kill $(docker ps | grep "serving:latest" | awk '{print $1}') && docker run -it --rm --network="host" gcr.io/recommender-270613/serving:latest bash
