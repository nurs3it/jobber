# Runbook — эксплуатация

## Ежедневный сценарий

- Ручной: `/scan` → `/digest` в Claude Code.
- По расписанию: `claude -p "/digest"` из папки проекта (см. ниже).

## Расписание

Запускает `claude -p "/digest"` (обёртка `scripts/run-digest.sh`) в `config.digest.schedule_time`.

- **macOS:** LaunchAgent plist `~/Library/LaunchAgents/com.jobber.digest.plist`.
- **Linux:** cron-запись.
- Установка: `bash scripts/install-schedule.sh`; снятие: `bash scripts/uninstall-schedule.sh`.
- Логи запусков: `logs/schedule.log`, `logs/launchd.*.log`.
- Требуется установленный `claude` CLI (LLM-шаги делает он сам).

## Где что лежит

| Что | Путь |
|---|---|
| Конфиг поведения | `config.yaml` |
| Секреты | `.env` (gitignored) |
| Файл сессии Telegram | `*.session` (gitignored) 🔒 |
| Профиль | `profile/cv.md` (gitignored) |
| Загруженные резюме | `profile/uploads/` (gitignored) |
| Курсоры / seen-store | `storage/jobber.db` (gitignored) |
| Логи | `logs/` (ротация, gitignored) |
| Дайджесты (Obsidian) | `vault/Jobber/ГГГГ-ММ-ДД-jobber.md` |

## Типовые операции

- **Сбросить состояние** (пересканировать заново): `/seen-reset`.
- **Поправить профиль:** `/profile-edit`.
- **Переписать письмо:** `/cover <id>`.
- **Глубокий разовый проход:** `/scan 30`.
- **Посмотреть источники:** `/sources`.

## Логи

Уровень и ротация — `config.logging`. ⚠️ В логах не должно быть секретов, сессии или содержимого CV.

> Проблемы и их решения — `troubleshooting.md`.
