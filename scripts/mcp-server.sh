#!/usr/bin/env bash
# Jobber — запуск MCP-сервера (stdio) для Claude Code.
# Активирует venv и стартует python -m mcp_server. Путь относительный — резолвится от корня проекта.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
exec python -m mcp_server
