# Pushing
Docker containers are built and pushed to the GCloud container registry.

Pushing to registry:
https://cloud.google.com/container-registry/docs/quickstart

# Docker
docker build --tag serving:latest .
docker run --network="host" --detach -t serving:latest 
docker container ls
docker container kill 8f61baa075c4


# requirements.txt
Note requirements.txt generated via:
# pip3 install pipreqs
pipreqs .
docker tag serving:latest gcr.io/recommender-270613/serving:tag1
