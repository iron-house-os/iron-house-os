#!/usr/bin/env bash
set -euo pipefail

action=
release_sha=
evidence_file=
environment_file=/etc/iron-house-os/production.env
lock_file=/var/lock/iron-house-os-quickbooks-live-read-only.lock
domain=os.ironhousecivil.com

usage() {
  echo "Usage: ihos-quickbooks-live-read-only --action activate|force-disable --release 40_HEX_SHA --evidence FILE" >&2
}

while (($#)); do
  case "$1" in
    --action)
      action=${2:-}
      shift 2
      ;;
    --release)
      release_sha=${2:-}
      shift 2
      ;;
    --evidence)
      evidence_file=${2:-}
      shift 2
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if ((EUID != 0)) ||
  [[ "$action" != "activate" && "$action" != "force-disable" ]] ||
  [[ ! "$release_sha" =~ ^[0-9a-f]{40}$ ]] ||
  [[ -z "$evidence_file" ]]; then
  usage
  exit 2
fi

evidence_parent=$(cd "$(dirname "$evidence_file")" && pwd -P)
evidence_name=$(basename "$evidence_file")
if [[ "$evidence_parent" != "/opt/iron-house-os-actions-runner/_work/_temp" &&
      "$evidence_parent" != /opt/iron-house-os-actions-runner/_work/_temp/* ]] ||
  [[ ! "$evidence_name" =~ ^[A-Za-z0-9._-]+\.json$ ]]; then
  echo "Evidence output must be a JSON file inside the production runner temporary directory." >&2
  exit 1
fi
evidence_file="$evidence_parent/$evidence_name"

if [[ "$(hostname)" != "iron-house-os-prod-1" ]]; then
  echo "Refusing QuickBooks production configuration on an unexpected host." >&2
  exit 1
fi
if [[ ! -f "$environment_file" || -L "$environment_file" ]]; then
  echo "Missing protected production environment: $environment_file" >&2
  exit 1
fi
environment_identity=$(stat -c '%U:%G:%a' "$environment_file" 2>/dev/null || true)
if [[ "$environment_identity" != "root:root:600" &&
      "$environment_identity" != "root:root:400" ]]; then
  echo "Protected production environment ownership or permissions are invalid." >&2
  exit 1
fi

release_root="/opt/iron-house-os-releases/$release_sha"
if [[ ! -d "$release_root/.git" ]] ||
  [[ "$(git -C "$release_root" rev-parse HEAD)" != "$release_sha" ]] ||
  [[ -n "$(git -C "$release_root" status --porcelain)" ]]; then
  echo "The requested immutable production release is unavailable or unclean." >&2
  exit 1
fi

readiness_file=$(mktemp)
candidate_file=$(mktemp)
previous_file=$(mktemp)
evidence_candidate=$(mktemp)
cleanup() {
  rm -f "$readiness_file" "$candidate_file" "$previous_file" "$evidence_candidate"
}
trap cleanup EXIT

production_projects() {
  local include_stopped=${1:-0}
  local -a docker_ps=(docker ps)
  if ((include_stopped == 1)); then
    docker_ps+=(--all)
  fi
  docker_ps+=(--filter label=com.docker.compose.service=frontend --format '{{.ID}}')

  while IFS= read -r container_id; do
    config_files=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project.config_files" }}' "$container_id")
    if [[ "$config_files" == *docker-compose.production.yml* ]]; then
      docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$container_id"
    fi
  done < <("${docker_ps[@]}")
}

mapfile -t production_candidates < <(production_projects 0 | sed '/^$/d' | sort -u)
if (("${#production_candidates[@]}" == 0)); then
  mapfile -t production_candidates < <(production_projects 1 | sed '/^$/d' | sort -u)
fi
if (("${#production_candidates[@]}" != 1)); then
  echo "Exactly one production Compose project is required; found ${#production_candidates[@]}." >&2
  exit 1
fi
export COMPOSE_PROJECT_NAME=${production_candidates[0]}
export IHOS_RELEASE_ID="$release_sha"

production_port=$(ENVIRONMENT_FILE="$environment_file" python3 - <<'PY'
import os
from pathlib import Path

port = "8080"
for line in Path(os.environ["ENVIRONMENT_FILE"]).read_text().splitlines():
    if line.startswith("IHOS_PORT="):
        port = line.split("=", 1)[1].strip()
if not port.isdigit() or not (1 <= int(port) <= 65535):
    raise SystemExit("IHOS_PORT must be a valid TCP port.")
print(port)
PY
)

curl --fail --silent --show-error --connect-timeout 5 --max-time 15 \
  "http://127.0.0.1:$production_port/readiness" >"$readiness_file"
READINESS_FILE="$readiness_file" RELEASE_SHA="$release_sha" python3 - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads(Path(os.environ["READINESS_FILE"]).read_text())
expected = os.environ["RELEASE_SHA"]
actual = payload.get("checks", {}).get("release_id")
if payload.get("status") != "ready" or actual != expected:
    raise SystemExit(
        f"Production release verification failed: status={payload.get('status')}, "
        f"release_id={actual}, expected={expected}"
    )
PY

exec 9>"$lock_file"
if ! flock --wait 30 9; then
  echo "Another QuickBooks production configuration action is already running." >&2
  exit 1
fi

cp --preserve=mode,ownership "$environment_file" "$previous_file"
python3 "$release_root/ops/scripts/quickbooks_live_config.py" \
  --action "$action" \
  --source "$environment_file" \
  --candidate "$candidate_file"

chmod 0600 "$candidate_file"
compose=(docker compose --env-file "$candidate_file" -f "$release_root/docker-compose.production.yml")
"${compose[@]}" config --quiet

rollback_required=0
if [[ "$action" == "activate" ]]; then
  rollback_required=1
fi
rollback() {
  status=$?
  if ((status != 0 && rollback_required == 1)); then
    install -o root -g root -m 0600 "$previous_file" "$environment_file"
    docker compose --env-file "$environment_file" \
      -f "$release_root/docker-compose.production.yml" \
      up -d --no-build --no-deps --force-recreate backend >/dev/null || true
  fi
  cleanup
  exit "$status"
}
trap rollback EXIT

install -o root -g root -m 0600 "$candidate_file" "$environment_file"
"${compose[@]}" up -d --no-build --no-deps --force-recreate backend

ready=0
for _attempt in $(seq 1 24); do
  if curl --fail --silent --show-error --connect-timeout 5 --max-time 10 \
      "http://127.0.0.1:$production_port/readiness" >"$readiness_file" 2>/dev/null &&
    READINESS_FILE="$readiness_file" RELEASE_SHA="$release_sha" python3 - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads(Path(os.environ["READINESS_FILE"]).read_text())
if payload.get("status") != "ready":
    raise SystemExit(1)
if payload.get("checks", {}).get("release_id") != os.environ["RELEASE_SHA"]:
    raise SystemExit(1)
PY
  then
    ready=1
    break
  fi
  sleep 5
done
if ((ready != 1)); then
  echo "Production backend did not return exact-release readiness within 120 seconds." >&2
  exit 1
fi

ACTION="$action" RELEASE_SHA="$release_sha" EVIDENCE_FILE="$evidence_candidate" python3 - <<'PY'
import json
import os
from datetime import UTC, datetime
from pathlib import Path

action = os.environ["ACTION"]
payload = {
    "action": action,
    "feature_enabled": False,
    "force_disabled": action == "force-disable",
    "operation_boundary": "GET CompanyInfo only",
    "release_sha": os.environ["RELEASE_SHA"],
    "result": "verified",
    "timestamp_utc": datetime.now(UTC).isoformat(),
}
if action == "activate":
    payload.update(
        {
            "environment": "production",
            "ihos_live_read_only_approved": True,
            "token_encryption_key_present": True,
        }
    )
Path(os.environ["EVIDENCE_FILE"]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY
install -o ihos-runner -g ihos-runner -m 0640 "$evidence_candidate" "$evidence_file"
rollback_required=0
echo "QuickBooks live read-only production configuration verified for release $release_sha."
