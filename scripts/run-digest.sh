#!/usr/bin/env bash
# Jobber — обёртка для запуска дайджеста по расписанию.
# Активирует окружение и просит Claude Code выполнить /digest из папки проекта.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Активировать venv, если есть (для доступа к зависимостям/MCP-серверу).
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

mkdir -p logs

# Требуется установленный Claude Code CLI (`claude`). LLM-шаги делает он сам.
if ! command -v claude >/dev/null 2>&1; then
  echo "$(date '+%F %T') claude CLI не найден — пропуск дайджеста" >> logs/schedule.log
  exit 0
fi

echo "$(date '+%F %T') запуск /digest" >> logs/schedule.log
claude -p "/digest" >> logs/schedule.log 2>&1
echo "$(date '+%F %T') /digest завершён" >> logs/schedule.log
