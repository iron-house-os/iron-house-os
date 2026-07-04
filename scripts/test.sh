#!/usr/bin/env bash
set -euo pipefail

pushd backend
ruff check .
pytest
popd

pushd frontend
npm run lint
npm run build
popd
