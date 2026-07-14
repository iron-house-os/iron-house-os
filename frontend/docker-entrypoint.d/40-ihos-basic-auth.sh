#!/bin/sh
set -eu

: "${IHOS_ADMIN_USERNAME:?IHOS_ADMIN_USERNAME is required}"
: "${IHOS_ADMIN_PASSWORD:?IHOS_ADMIN_PASSWORD is required}"

printf '%s\n' "$IHOS_ADMIN_PASSWORD" | \
  htpasswd -ciB /etc/nginx/.htpasswd "$IHOS_ADMIN_USERNAME"
chmod 600 /etc/nginx/.htpasswd
