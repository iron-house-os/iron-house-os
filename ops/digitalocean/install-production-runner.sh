#!/usr/bin/env bash
set -euo pipefail

repository=iron-house-os/iron-house-os
runner_user=ihos-runner
runner_root=/opt/iron-house-os-actions-runner
runner_name=iron-house-os-prod-1
runner_label=ihos-production
wrapper_source=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/production-deploy-wrapper.sh
wrapper_target=/usr/local/sbin/ihos-production-deploy
sudoers_target=/etc/sudoers.d/iron-house-os-production-runner

if ((EUID != 0)); then
  echo "Run this installer with sudo." >&2
  exit 1
fi
if [[ "$(hostname)" != "$runner_name" ]]; then
  echo "Refusing runner installation on unexpected host." >&2
  exit 1
fi
if [[ ! -f /etc/iron-house-os/production.env || ! -f "$wrapper_source" ]]; then
  echo "Production environment or deployment wrapper is missing." >&2
  exit 1
fi
if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  echo "GitHub CLI must already be authenticated for $repository." >&2
  exit 1
fi

install -o root -g root -m 0755 "$wrapper_source" "$wrapper_target"
printf '%s\n' \
  "$runner_user ALL=(root) NOPASSWD: $wrapper_target *" \
  >"$sudoers_target"
chmod 0440 "$sudoers_target"
visudo -cf "$sudoers_target" >/dev/null

if ! id "$runner_user" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "$runner_root" --shell /usr/sbin/nologin "$runner_user"
fi
install -d -o "$runner_user" -g "$runner_user" -m 0750 "$runner_root"

if systemctl list-unit-files --type=service | grep -q '^actions.runner.iron-house-os-iron-house-os'; then
  echo "Production deployment runner is already installed."
  systemctl --no-pager --full status 'actions.runner.iron-house-os-iron-house-os*' || true
  exit 0
fi

runner_version=$(gh api repos/actions/runner/releases/latest --jq '.tag_name | ltrimstr("v")')
runner_arch=x64
case "$(uname -m)" in
  x86_64) runner_arch=x64 ;;
  aarch64|arm64) runner_arch=arm64 ;;
  *)
    echo "Unsupported runner architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

archive="actions-runner-linux-${runner_arch}-${runner_version}.tar.gz"
download_url="https://github.com/actions/runner/releases/download/v${runner_version}/${archive}"
checksum_url="https://github.com/actions/runner/releases/download/v${runner_version}/sha256_checksums.txt"
temp_dir=$(mktemp -d)
trap 'rm -rf "$temp_dir"' EXIT

curl -fsSL "$download_url" -o "$temp_dir/$archive"
curl -fsSL "$checksum_url" -o "$temp_dir/sha256_checksums.txt"
expected_checksum=$(awk -v archive="$archive" '$2 == archive {print $1}' "$temp_dir/sha256_checksums.txt")
if [[ -z "$expected_checksum" ]]; then
  echo "Runner checksum was not published for $archive." >&2
  exit 1
fi
printf '%s  %s\n' "$expected_checksum" "$temp_dir/$archive" | sha256sum -c -

tar -xzf "$temp_dir/$archive" -C "$runner_root"
chown -R "$runner_user:$runner_user" "$runner_root"
registration_token=$(gh api --method POST "repos/$repository/actions/runners/registration-token" --jq .token)

sudo -u "$runner_user" "$runner_root/config.sh" \
  --unattended \
  --url "https://github.com/$repository" \
  --token "$registration_token" \
  --name "$runner_name" \
  --labels "$runner_label" \
  --work _work \
  --replace

"$runner_root/svc.sh" install "$runner_user"
"$runner_root/svc.sh" start
"$runner_root/svc.sh" status
echo "Production deployment runner installed: $runner_name [$runner_label]"
