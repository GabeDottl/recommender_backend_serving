docker build --tag serving:latest .
docker run --rm  --network="host" serving:latest pipenv run pytest /usr/src/app
