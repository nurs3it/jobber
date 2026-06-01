# Jobber

Локальный персональный ассистент поиска работы по **Telegram**. Отдаёшь резюме и Telegram-ключи —
получаешь свежие подходящие вакансии из своих чатов, групп, сообществ и каналов (**включая архив**),
каждую с готовым черновиком сопроводительного письма и скором релевантности 0–100.

- **Минимум времени.** Настройка один раз (`/onboard`), дальше `/scan` или дайджест по расписанию.
- **Read-only.** Ничего не отправляется автоматически. Сопроводительные — только черновики под ревью.
- **Provider-agnostic.** Telegram сейчас; LinkedIn и веб-доски — заложены на будущее.

> Почему не HeadHunter: соискательский API закрыт с 15.12.2025. Источник — Telegram (user-session, MTProto).

## Быстрый старт

```bash
bash scripts/install.sh      # зависимости, .env из шаблона, структура
# в Claude Code:
/onboard                     # резюме (pdf/docx/img) + Telegram-ключи + первый логин
/scan                        # разовый проход по диалогам и архиву
/digest                      # дайджест в Obsidian + отчёт в чат
```

## Документация

- **Настройка:** [`.claude/docs/setup.md`](.claude/docs/setup.md) — api_id/api_hash, первый логин, импорт CV, первый scan.
- **Архитектура:** [`.claude/docs/architecture.md`](.claude/docs/architecture.md) — ядро, источники, конвейер, диаграмма.
- **Добавить источник:** [`.claude/docs/adding-a-source.md`](.claude/docs/adding-a-source.md) — интерфейс, capability-флаги, маппинг.
- **Эксплуатация:** [`.claude/docs/runbook.md`](.claude/docs/runbook.md) — расписание, где файлы.
- **Безопасность:** [`.claude/docs/security.md`](.claude/docs/security.md) — модель угроз, файл сессии, read-only.
- **Проблемы:** [`.claude/docs/troubleshooting.md`](.claude/docs/troubleshooting.md) — flood-wait, протухшая сессия, OCR, дубликаты, пустой дайджест.

## 🔒 Безопасность

Файл сессии Telethon (`*.session`) = полный доступ к Telegram-аккаунту. Только локально, в `.gitignore`,
никогда не коммитить и не логировать. Подробнее — `.claude/docs/security.md` и `CLAUDE.md`.
