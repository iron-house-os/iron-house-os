#!/usr/bin/env bash
set -euo pipefail

if ((EUID != 0)); then
  echo "Run this installer as root." >&2
  exit 1
fi

repo=${IHOS_REPO_ROOT:-/opt/iron-house-os/source}
cd "$repo"

install -m 0644 ops/systemd/ihos-deploy-agent.service \
  /etc/systemd/system/ihos-deploy-agent.service
install -m 0644 ops/systemd/ihos-deploy-agent.timer \
  /etc/systemd/system/ihos-deploy-agent.timer
install -d -m 0700 /var/lib/iron-house-os/deploy-agent

systemctl daemon-reload
systemctl enable --now ihos-deploy-agent.timer
systemctl start ihos-deploy-agent.service
systemctl --no-pager status ihos-deploy-agent.service || true
echo "Iron House deploy agent installed."
