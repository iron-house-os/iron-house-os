#!/usr/bin/env bash
set -euo pipefail

if [ "${EUID}" -ne 0 ]; then
  echo "Run as root: sudo bash ops/agent/bootstrap.sh" >&2
  exit 1
fi

AGENT_USER="ih-agent"
WORKSPACE="/srv/iron-house-agents"
REPOS=(
  "https://github.com/iron-house-os/iron-house-os.git"
  "https://github.com/iron-house-os/Dumper.git"
)

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git gh jq unzip build-essential

if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi

npm install -g @openai/codex

if ! id -u "${AGENT_USER}" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "${AGENT_USER}"
fi

install -d -o "${AGENT_USER}" -g "${AGENT_USER}" "${WORKSPACE}"

for repo in "${REPOS[@]}"; do
  name="$(basename "${repo}" .git)"
  dest="${WORKSPACE}/${name}"
  if [ ! -d "${dest}/.git" ]; then
    sudo -u "${AGENT_USER}" git clone "${repo}" "${dest}" || true
  else
    sudo -u "${AGENT_USER}" git -C "${dest}" fetch --all --prune || true
  fi
done

cat >/etc/iron-house-agent.env.example <<'EOF'
# Copy to /etc/iron-house-agent.env and set securely.
# Never commit real values.
OPENAI_API_KEY=
GH_TOKEN=
EOF
chmod 600 /etc/iron-house-agent.env.example

cat >/usr/local/bin/iron-house-agent-check <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'codex: '; codex --version
printf 'node: '; node --version
printf 'npm: '; npm --version
printf 'git: '; git --version
printf 'gh: '; gh --version | head -n 1
for repo in /srv/iron-house-agents/*; do
  [ -d "$repo/.git" ] || continue
  echo "repo: $repo"
  git -C "$repo" status --short --branch
 done
EOF
chmod 755 /usr/local/bin/iron-house-agent-check

cat <<EOF
Bootstrap complete.

Next required secure steps:
1. Create /etc/iron-house-agent.env from the example and add repository-limited credentials.
2. Run: sudo -u ${AGENT_USER} gh auth status
3. Authenticate Codex with an API key or supported login flow.
4. Run: iron-house-agent-check

Workspace: ${WORKSPACE}
User: ${AGENT_USER}
EOF
