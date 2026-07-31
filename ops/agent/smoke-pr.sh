#!/usr/bin/env bash
set -euo pipefail

if [ "${EUID}" -eq 0 ]; then
  echo "Run as ih-agent: sudo -u ih-agent -H bash ops/agent/smoke-pr.sh" >&2
  exit 1
fi

PROJECT_KEY="${1:-ihos}"
ISSUE_NUMBER="${2:-107}"
REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SMOKE_STATE="${IH_AGENT_SMOKE_STATE:-${HOME}/.local/state/iron-house-agent-smoke}"
SMOKE_WORKTREES="${IH_AGENT_SMOKE_WORKTREES:-${HOME}/.cache/iron-house-agent-worktrees}"

umask 077
mkdir -p "${SMOKE_STATE}" "${SMOKE_WORKTREES}"

export PYTHONPATH="${REPOSITORY_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

exec python3 -m ops.agent.iron_house_agent.cli \
  --registry "${REPOSITORY_ROOT}/ops/agent/projects.json" \
  --state-directory "${SMOKE_STATE}" \
  --worktrees-directory "${SMOKE_WORKTREES}" \
  smoke --project "${PROJECT_KEY}" --issue "${ISSUE_NUMBER}"
