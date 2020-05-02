build:
  bash -c "docker build --tag serving:latest ."

run: build
  bash -c "docker run --rm  --network='host' serving:latest"

debug:
  bash -c "python3 main.py --debug-mode --verbosity debug --clear-user --local"

test: build
  bash -c "docker run --rm  --network='host' serving:latest pipenv run pytest"