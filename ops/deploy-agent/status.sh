#!/usr/bin/env bash
set -euo pipefail

state=${IHOS_DEPLOY_AGENT_STATE_ROOT:-/var/lib/iron-house-os/deploy-agent}/last-success.json
if [[ -f "$state" ]]; then
  cat "$state"
else
  echo '{"status":"no_successful_deployment_recorded"}'
fi
systemctl --no-pager --full status ihos-deploy-agent.timer || true
journalctl -u ihos-deploy-agent.service -n 30 --no-pager
