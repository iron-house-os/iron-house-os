#!/usr/bin/env bash
set -euo pipefail

if [ "${EUID}" -ne 0 ]; then
  echo "Run as root: sudo bash ops/agent/install.sh [--start]" >&2
  exit 1
fi

AGENT_USER="ih-agent"
AGENT_REPOSITORY="/srv/iron-house-agents/iron-house-os"
STATE_DIRECTORY="/var/lib/iron-house-agent"
WORKTREES_DIRECTORY="/srv/iron-house-agents/worktrees"
RUNTIME_REGISTRY="${STATE_DIRECTORY}/projects.json"
START_SERVICE="false"

if [ "${1:-}" = "--start" ]; then
  START_SERVICE="true"
elif [ "$#" -gt 0 ]; then
  echo "Usage: sudo bash ops/agent/install.sh [--start]" >&2
  exit 2
fi

if ! id -u "${AGENT_USER}" >/dev/null 2>&1; then
  echo "Missing required user: ${AGENT_USER}" >&2
  exit 1
fi

if [ ! -f "${AGENT_REPOSITORY}/ops/agent/projects.json" ]; then
  echo "Missing agent repository at ${AGENT_REPOSITORY}" >&2
  exit 1
fi

install -d -m 0700 -o "${AGENT_USER}" -g "${AGENT_USER}" "${STATE_DIRECTORY}"
install -d -m 0700 -o "${AGENT_USER}" -g "${AGENT_USER}" "${STATE_DIRECTORY}/logs"
install -d -m 0700 -o "${AGENT_USER}" -g "${AGENT_USER}" "${WORKTREES_DIRECTORY}"
if [ ! -f "${RUNTIME_REGISTRY}" ]; then
  install -m 0600 -o "${AGENT_USER}" -g "${AGENT_USER}" \
    "${AGENT_REPOSITORY}/ops/agent/projects.json" "${RUNTIME_REGISTRY}"
fi
install -m 0755 "${AGENT_REPOSITORY}/ops/agent/iron-house-agent" /usr/local/bin/iron-house-agent
install -m 0644 "${AGENT_REPOSITORY}/ops/agent/iron-house-agent.service" \
  /etc/systemd/system/iron-house-agent.service

sudo -u "${AGENT_USER}" /usr/local/bin/iron-house-agent init
systemctl daemon-reload

if [ "${START_SERVICE}" = "true" ]; then
  sudo -u "${AGENT_USER}" /usr/local/bin/iron-house-agent preflight
  systemctl enable --now iron-house-agent.service
  systemctl --no-pager --full status iron-house-agent.service
else
  echo "Installed but not started. Authenticate Codex for ih-agent, run preflight, then:"
  echo "sudo systemctl enable --now iron-house-agent.service"
fi
