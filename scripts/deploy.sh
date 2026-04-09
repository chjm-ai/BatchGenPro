#!/usr/bin/env bash

set -euo pipefail

DEPLOY_HOST="${DEPLOY_HOST:-${1:-}}"
DEPLOY_USER="${DEPLOY_USER:-wesley}"
DEPLOY_PORT="${DEPLOY_PORT:-2222}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
DEPLOY_APP_DIR="${DEPLOY_APP_DIR:-/srv/core/apps/batchgenpro}"
DEPLOY_CORE_DIR="${DEPLOY_CORE_DIR:-/srv/core}"
DEPLOY_PROFILE="${DEPLOY_PROFILE:-batchgenpro}"

if [[ -z "${DEPLOY_HOST}" ]]; then
  echo "错误: 请通过 DEPLOY_HOST 环境变量或第一个参数提供服务器地址/SSH 别名。" >&2
  echo "示例: DEPLOY_HOST=my-server ./scripts/deploy.sh" >&2
  exit 1
fi

SSH_TARGET="${DEPLOY_USER}@${DEPLOY_HOST}"

echo "Deploy target: ${SSH_TARGET}:${DEPLOY_PORT}"
echo "Branch: ${DEPLOY_BRANCH}"
echo "App dir: ${DEPLOY_APP_DIR}"

ssh -p "${DEPLOY_PORT}" "${SSH_TARGET}" <<EOF
set -euo pipefail

cd "${DEPLOY_APP_DIR}"
git fetch origin
git checkout "${DEPLOY_BRANCH}"
git pull --ff-only origin "${DEPLOY_BRANCH}"

cd "${DEPLOY_CORE_DIR}"
docker compose --profile "${DEPLOY_PROFILE}" up -d --build \
  ${DEPLOY_PROFILE}-redis \
  ${DEPLOY_PROFILE}-backend \
  ${DEPLOY_PROFILE}-frontend
EOF
