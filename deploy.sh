# https://cloud.google.com/compute/docs/containers/deploying-containers#updating_a_container_on_a_vm_instance
docker build --tag serving:latest .
docker tag serving:latest gcr.io/recommender-270613/serving
docker push gcr.io/recommender-270613/serving
gcloud compute instances update-container serving-1 --container-image gcr.io/recommender-270613/serving
