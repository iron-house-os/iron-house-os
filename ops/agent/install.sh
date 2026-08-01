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

install_codex_sandbox_prerequisites() {
  if [ ! -r /etc/os-release ]; then
    echo "Cannot identify the operating system required for Codex sandbox setup" >&2
    exit 1
  fi

  # shellcheck disable=SC1091
  . /etc/os-release
  if [ "${ID:-}" != "ubuntu" ]; then
    if ! command -v bwrap >/dev/null 2>&1; then
      echo "Missing Bubblewrap. Install the distribution package before starting the agent." >&2
      exit 1
    fi
    return
  fi

  local packages=(bubblewrap)
  if [ "${VERSION_ID:-}" = "24.04" ]; then
    packages+=(apparmor-profiles apparmor-utils)
  fi
  if ! dpkg -s "${packages[@]}" >/dev/null 2>&1; then
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages[@]}"
  fi

  if [ "${VERSION_ID:-}" != "24.04" ]; then
    return
  fi
  if [ ! -r /sys/module/apparmor/parameters/enabled ] || \
    ! grep -q '^Y' /sys/module/apparmor/parameters/enabled; then
    return
  fi

  local source_profile="/usr/share/apparmor/extra-profiles/bwrap-userns-restrict"
  local installed_profile="/etc/apparmor.d/bwrap-userns-restrict"
  local disabled_profile="/etc/apparmor.d/disable/bwrap-userns-restrict"
  if [ ! -f "${source_profile}" ]; then
    echo "Ubuntu 24.04 Bubblewrap AppArmor profile is unavailable: ${source_profile}" >&2
    exit 1
  fi
  local prepared_profile
  prepared_profile="$(mktemp)"
  if ! python3 "${AGENT_REPOSITORY}/ops/agent/iron_house_agent/apparmor.py" \
    "${source_profile}" "${prepared_profile}"; then
    rm -f "${prepared_profile}"
    exit 1
  fi
  install -m 0644 "${prepared_profile}" "${installed_profile}"
  rm -f "${prepared_profile}"
  rm -f "${disabled_profile}"
  apparmor_parser -r "${installed_profile}"
}

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

if systemctl is-active --quiet iron-house-agent.service; then
  if [ "${START_SERVICE}" != "true" ]; then
    echo "Agent service is active; rerun with --start to update it safely." >&2
    exit 1
  fi
  # Fail closed: an old worker must not keep claiming jobs if repair or preflight fails.
  systemctl stop iron-house-agent.service
fi

install_codex_sandbox_prerequisites

install -d -m 0700 -o "${AGENT_USER}" -g "${AGENT_USER}" "${STATE_DIRECTORY}"
install -d -m 0700 -o "${AGENT_USER}" -g "${AGENT_USER}" "${STATE_DIRECTORY}/logs"
install -d -m 0700 -o "${AGENT_USER}" -g "${AGENT_USER}" "${WORKTREES_DIRECTORY}"
if [ ! -f "${RUNTIME_REGISTRY}" ]; then
  install -m 0600 -o "${AGENT_USER}" -g "${AGENT_USER}" \
    "${AGENT_REPOSITORY}/ops/agent/projects.json" "${RUNTIME_REGISTRY}"
fi
install -m 0755 "${AGENT_REPOSITORY}/ops/agent/iron-house-agent" /usr/local/bin/iron-house-agent
install -m 0755 "${AGENT_REPOSITORY}/ops/agent/iron-house-agent-register" \
  /usr/local/bin/iron-house-agent-register
install -m 0644 "${AGENT_REPOSITORY}/ops/agent/iron-house-agent.service" \
  /etc/systemd/system/iron-house-agent.service

sudo -u "${AGENT_USER}" -H /usr/local/bin/iron-house-agent init
systemctl daemon-reload

if [ "${START_SERVICE}" = "true" ]; then
  sudo -u "${AGENT_USER}" -H gh auth setup-git
  sudo -u "${AGENT_USER}" -H /usr/local/bin/iron-house-agent preflight
  systemctl enable iron-house-agent.service
  systemctl restart iron-house-agent.service
  systemctl --no-pager --full status iron-house-agent.service
else
  echo "Installed but not started. Authenticate Codex for ih-agent, run preflight, then:"
  echo "sudo systemctl enable --now iron-house-agent.service"
fi
