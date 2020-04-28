gunicorn 192.168.1.4:5000 "main:main_gunicorn()"
-e git+ssh://git@github.com/gabedottl/recommender_backend_common.git#egg=common


docker container kill $(docker ps | grep "serving:latest" | awk '{print $1}') && docker run -it --rm --network="host" gcr.io/recommender-270613/serving:latest bash
