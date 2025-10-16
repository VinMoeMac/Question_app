#!/bin/bash
set -e

# Configuration
# -------------
# - Set your GCP project ID here.
# - The VM will be created in the us-central1-a zone.
# - The VM will have 2 vCPUs and 8GB of RAM (e2-standard-2).
GCP_PROJECT="your-gcp-project-id"
VM_NAME="question-app-vm"
ZONE="us-central1-a"
MACHINE_TYPE="e2-standard-2"

# - This is the full path to the CSV file on your local machine.
# - It will be uploaded to the VM at ~/question-app/data/source.csv
LOCAL_CSV_PATH="C:/Users/vinmo/Downloads/geo-research/dataset-derived-prompts/results_filtered_all_dumps_IN_PROGRESS.csv"

# - These credentials will be used for the basic authentication protecting the app.
APP_USERNAME="your-username"

echo -n "Enter password for $APP_USERNAME: "
read -s APP_PASSWORD
echo

# 1. Create a new Google Cloud VM
# -------------------------------
echo ">>> Creating Google Cloud VM..."
gcloud compute instances create "$VM_NAME" \
  --project="$GCP_PROJECT" \
  --zone="$ZONE" \
  --machine-type="$MACHINE_TYPE" \
  --image-family="debian-11" \
  --image-project="debian-cloud" \
  --boot-disk-size="20GB" \
  --tags="http-server,https-server"

# Wait for the VM to be ready
echo ">>> Waiting for VM to be ready..."
sleep 20

# 2. Transfer application files to the VM
# ---------------------------------------
echo ">>> Transferring application files..."
gcloud compute scp --recurse ./app "$VM_NAME":~/question-app/app
gcloud compute scp ./requirements.txt "$VM_NAME":~/question-app/
gcloud compute scp ./setup_vm.sh "$VM_NAME":~/question-app/

# 3. Transfer the CSV file to the VM
# ----------------------------------
echo ">>> Transferring CSV file..."
gcloud compute scp "$LOCAL_CSV_PATH" "$VM_NAME":~/question-app/data/source.csv

# 4. Execute the setup script on the VM
# -------------------------------------
echo ">>> Executing setup script on the VM..."
gcloud compute ssh "$VM_NAME" --command="cd ~/question-app && chmod +x setup_vm.sh && ./setup_vm.sh '$APP_USERNAME' '$APP_PASSWORD'"

echo ">>> Deployment complete!"
echo ">>> You should be able to access the app at http://$(gcloud compute instances describe "$VM_NAME" --format='get(networkInterfaces[0].accessConfigs[0].natIP)')"
