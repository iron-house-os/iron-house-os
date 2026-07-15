#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this script as root." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get upgrade -y
apt-get install -y \
  ca-certificates \
  certbot \
  curl \
  docker-compose-v2 \
  docker.io \
  git \
  jq \
  nginx \
  python3-certbot-nginx \
  unzip \
  ufw

if ! command -v aws >/dev/null; then
  aws_installer=$(mktemp -d)
  curl -fsSLo "${aws_installer}/awscliv2.zip" \
    https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip
  unzip -q "${aws_installer}/awscliv2.zip" -d "${aws_installer}"
  "${aws_installer}/aws/install" \
    --install-dir /usr/local/aws-cli \
    --bin-dir /usr/local/bin
  rm -rf "${aws_installer}"
fi
aws --version

install -d -m 0700 /etc/iron-house-os
install -d -m 0755 \
  /opt/iron-house-os \
  /var/backups/iron-house-os \
  /var/lib/iron-house-os \
  /var/www/letsencrypt

cat >/etc/iron-house-os/README <<'EOF'
Production secrets belong in /etc/iron-house-os/production.env with mode 0600.
Do not place credentials in bootstrap commands, Git, shell history, or support messages.
EOF

systemctl enable --now docker
systemctl enable --now nginx

ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow "Nginx Full"
ufw --force enable

source_dir=/opt/iron-house-os/source
if [[ -d "${source_dir}/.git" ]]; then
  git -C "${source_dir}" fetch origin main
  git -C "${source_dir}" checkout main
  git -C "${source_dir}" reset --hard origin/main
elif [[ -e "${source_dir}" ]]; then
  echo "${source_dir} exists but is not a Git checkout." >&2
  exit 1
else
  git clone --branch main --single-branch \
    https://github.com/iron-house-os/iron-house-os.git \
    "${source_dir}"
fi

cp "${source_dir}/ops/digitalocean/nginx-maintenance.conf" \
  /etc/nginx/sites-available/iron-house-os
ln -sfn /etc/nginx/sites-available/iron-house-os \
  /etc/nginx/sites-enabled/iron-house-os
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

touch /var/lib/iron-house-os/cloud-init-complete
echo "Iron House OS host bootstrap completed; production secrets and cutover are still pending."
