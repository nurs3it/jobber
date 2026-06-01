#!/usr/bin/env bash
# Jobber — снятие расписания ежедневного дайджеста (launchd/cron).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.jobber.digest"
WRAPPER="$ROOT/scripts/run-digest.sh"

OS="$(uname -s)"
if [ "$OS" = "Darwin" ]; then
  PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
  if [ -f "$PLIST" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "✅ launchd LaunchAgent удалён: $PLIST"
  else
    echo "LaunchAgent не найден — нечего удалять."
  fi
elif [ "$OS" = "Linux" ]; then
  if crontab -l 2>/dev/null | grep -q "$WRAPPER"; then
    crontab -l 2>/dev/null | grep -v "$WRAPPER" | crontab -
    echo "✅ cron-запись удалена."
  else
    echo "cron-запись не найдена — нечего удалять."
  fi
else
  echo "Неизвестная ОС: $OS. Снимите расписание вручную."
fi
