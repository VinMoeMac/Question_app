#!/bin/bash
set -e

# This script is executed remotely on the VM.
APP_USERNAME=$1
APP_PASSWORD=$2

# 1. Install dependencies
# -----------------------
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip nginx apache2-utils

# 2. Set up the application environment
# -------------------------------------
cd ~/question-app
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Configure the systemd service
# --------------------------------
# This will run the app as a background service and restart it on failure.
sudo bash -c "cat > /etc/systemd/system/question-app.service" << EOL
[Unit]
Description=Question App FastAPI Server
After=network.target

[Service]
User=$(whoami)
Group=$(whoami)
WorkingDirectory=$(pwd)
Environment="CSV_PATH=$(pwd)/data/source.csv"
ExecStart=$(pwd)/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable question-app
sudo systemctl start question-app

# 4. Configure Nginx as a reverse proxy with basic authentication
# ---------------------------------------------------------------
sudo htpasswd -cb /etc/nginx/.htpasswd "$APP_USERNAME" "$APP_PASSWORD"

sudo bash -c "cat > /etc/nginx/sites-available/default" << EOL
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        auth_basic "Restricted Content";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
EOL

sudo nginx -t
sudo systemctl restart nginx

