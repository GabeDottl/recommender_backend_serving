# https://cloud.google.com/compute/docs/containers/deploying-containers#updating_a_container_on_a_vm_instance
docker build --tag gcr.io/recommender-270613/serving:latest .
docker push gcr.io/recommender-270613/serving:latest
gcloud compute instances update-container serving-1 --container-image gcr.io/recommender-270613/serving:latest
