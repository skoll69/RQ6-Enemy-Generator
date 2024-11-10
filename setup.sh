sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install nginx unzip python3.11 python3.11-venv build-essential libssl-dev libffi-dev python-dev-is-python3 mariadb-server libcairo2 libcairo2-dev libpangocairo-1.0-0 -y
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws configure
aws configure set default.s3.use_dualstack_endpoint true
aws configure set default.ec2.use_dualstack_endpoint true
aws configure set default.logs.use_dualstack_endpoint true
mkdir /meg
cd /meg
mkdir temp
python3.11 -m venv /meg/venv
source /meg/venv/bin/activate
pip install -r requirements.txt
sudo mysql_secure_installation

sudo cat > /etc/systemd/system/gunicorn.socket <<EOF
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/meg/gunicorn.sock

[Install]
WantedBy=sockets.target
EOF

sudo cat > /etc/systemd/system/gunicorn.service <<EOF
[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
User=meg
Group=www-data
WorkingDirectory=/meg
ExecStart=/meg/venv/bin/gunicorn --access-logfile - \
          --workers 3 --bind unix:/meg/gunicorn.sock mythras_eg.wsgi:application

[Install]
WantedBy=multi-user.target
EOF


sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.socket
