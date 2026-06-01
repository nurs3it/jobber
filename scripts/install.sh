#!/usr/bin/env bash
# Jobber — установка для нового пользователя.
# Ставит зависимости, создаёт .env из шаблона, инициализирует структуру.
# Идемпотентно: можно запускать повторно.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Jobber install (dir: $ROOT)"

# --- 1. Python окружение (uv предпочтительно, иначе venv) ---
if command -v uv >/dev/null 2>&1; then
  echo "==> uv найден — создаю окружение и ставлю зависимости"
  uv venv --python 3.11 2>/dev/null || true
  uv pip install -e ".[dev]"
else
  echo "==> uv не найден — использую python venv"
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -e ".[dev]"
fi

# --- 2. .env из шаблона (не перезатираем существующий) ---
if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> Создан .env из .env.example — заполните TG_API_ID / TG_API_HASH / TG_PHONE"
else
  echo "==> .env уже существует — пропускаю"
fi

# --- 3. Структура рабочих папок (gitignored) ---
mkdir -p storage logs profile/uploads vault/Jobber
echo "==> Папки storage/ logs/ profile/uploads/ vault/Jobber готовы"

# --- 4. Подсказка ---
cat <<'EOF'

✅ Установка завершена.

Дальше:
  1. Заполните .env (ключи с https://my.telegram.org).
  2. В Claude Code выполните: /onboard  (резюме + первый логин Telegram).
  3. Затем: /scan  и  /digest.

Документация: README.md, .claude/docs/setup.md
EOF
