#!/usr/bin/env bash
# Jobber — установка расписания ежедневного дайджеста.
# macOS → launchd (LaunchAgent plist); Linux → cron.
# Время берётся из config.yaml (digest.schedule_time, формат HH:MM).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LABEL="com.jobber.digest"
WRAPPER="$ROOT/scripts/run-digest.sh"
chmod +x "$WRAPPER"

# --- Прочитать время из config.yaml (через python, без внешних зависимостей в PATH) ---
PY="python3"
[ -x "$ROOT/.venv/bin/python" ] && PY="$ROOT/.venv/bin/python"
SCHEDULE_TIME="$("$PY" - <<'PY'
import re, pathlib
text = pathlib.Path("config.yaml").read_text(encoding="utf-8")
m = re.search(r'schedule_time:\s*"?(\d{1,2}):(\d{2})"?', text)
print(f"{int(m.group(1))} {int(m.group(2))}" if m else "9 0")
PY
)"
HOUR="$(echo "$SCHEDULE_TIME" | awk '{print $1}')"
MIN="$(echo "$SCHEDULE_TIME" | awk '{print $2}')"
printf -v HH "%02d" "$HOUR"
printf -v MM "%02d" "$MIN"
echo "==> Дайджест по расписанию в $HH:$MM ежедневно"

OS="$(uname -s)"
if [ "$OS" = "Darwin" ]; then
  # --- macOS launchd ---
  PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$WRAPPER</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>$HOUR</integer>
    <key>Minute</key><integer>$MIN</integer>
  </dict>
  <key>StandardOutPath</key><string>$ROOT/logs/launchd.out.log</string>
  <key>StandardErrorPath</key><string>$ROOT/logs/launchd.err.log</string>
  <key>WorkingDirectory</key><string>$ROOT</string>
</dict>
</plist>
PLISTEOF
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  echo "✅ launchd LaunchAgent установлен: $PLIST"
  echo "   Проверить: launchctl list | grep $LABEL"
elif [ "$OS" = "Linux" ]; then
  # --- Linux cron ---
  CRON_LINE="$MM $HH * * * /bin/bash $WRAPPER"
  ( crontab -l 2>/dev/null | grep -v "$WRAPPER" ; echo "$CRON_LINE" ) | crontab -
  echo "✅ cron-запись установлена: $CRON_LINE"
  echo "   Проверить: crontab -l | grep jobber"
else
  echo "Неизвестная ОС: $OS. Поставьте расписание вручную на запуск $WRAPPER в $HH:$MM."
  exit 1
fi
