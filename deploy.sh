#!/bin/bash

LOCAL_DIR="/Users/kshitij.raj/git/test/deploy"     # 🔁 Replace with your actual local folder
EC2_HOST="ubuntu@csm8001.int.devsnc.com"
KEY_PATH="/Users/kshitij.raj/.ssh/csm_aws_devsnc_rsa_key.pem"            # 🔁 Replace with full path to your .pem file

REMOTE_DIR="/var/www/mcp/snow-embedding-issues"
SERVER_PORT=8005
PROXY_PATH="/mcp/servicenow"

echo "Deploying directory: $LOCAL_DIR to EC2: $EC2_HOST"

# === 1. Upload to EC2 ===
echo "Creating remote directory and uploading files..."
ssh -i "$KEY_PATH" "$EC2_HOST" "sudo mkdir -p $REMOTE_DIR && sudo chown -R \$USER:\$USER $REMOTE_DIR"
scp -i "$KEY_PATH" -r "$LOCAL_DIR"/* "$EC2_HOST:$REMOTE_DIR"

# # === 2. SSH into EC2 and run setup ===
# ssh -i "$KEY_PATH" "$EC2_HOST" <<EOF
# echo "Entering server setup..."

# cd $REMOTE_DIR

# # === 3. Setup Python environment ===
# echo "Creating virtual environment..."
# sudo su <<INNER
# cd $REMOTE_DIR
# python3 -m venv .venv
# source .venv/bin/activate
# pip install --upgrade pip
# pip install -r requirements.txt

# # === 4. Run the server temporarily to test ===
# echo "Running server temporarily..."
# python3 server.py &
# SERVER_PID=\$!
# sleep 5

# # === 5. Check if server is running on port $SERVER_PORT ===
# if lsof -i :$SERVER_PORT | grep LISTEN > /dev/null; then
#     echo "Server is running on port $SERVER_PORT. Killing it for now..."
#     kill \$SERVER_PID
# else
#     echo "Server failed to start on port $SERVER_PORT. Exiting."
#     exit 1
# fi

# # === 6. Apache Configuration ===
# echo "Configuring Apache reverse proxy..."
# APACHE_CONF="/etc/apache2/sites-available/000-default.conf"
# PROXY_ENTRY="
#     # MCP Server: Instance Embedding Issues
#     ProxyPass \\\"$PROXY_PATH/\\\" \\\"http://localhost:$SERVER_PORT/\\\"
#     ProxyPassReverse \\\"$PROXY_PATH/\\\" \\\"http://localhost:$SERVER_PORT/\\\"
# "
# grep -q "$PROXY_PATH" \$APACHE_CONF || echo "\$PROXY_ENTRY" >> \$APACHE_CONF

# sudo a2enmod proxy proxy_http headers
# sudo systemctl restart apache2
# INNER

# # === 7. Run server with nohup ===
# echo "Starting server with nohup..."
# cd $REMOTE_DIR
# source .venv/bin/activate
# nohup python3 server.py > server.log 2>&1 &

# EOF

# echo "✅ Deployment complete. Verify at: http://csm8001.int.devsnc.com$PROXY_PATH/"