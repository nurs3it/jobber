# Архитектура

Jobber — **provider-agnostic**: ядро не знает о Telegram, источники реализуют общий интерфейс.

## Слои

- **core/** — доменные модели (pydantic) + интерфейс `JobSource`. Ни от чего не зависит.
- **sources/** — реализации источников. `telegram/` рабочий; `linkedin/`, `webboards/` — заглушки.
- **registry.py** — собирает включённые в `config.yaml` источники.
- **ingest/** — резюме (pdf/docx/img) → `profile/cv.md`.
- **matching/** — предфильтр (эвристика) → LLM-классификация/скоринг по профилю.
- **cover/** — генерация сопроводительных (черновики).
- **digest/** — дедуп → рендер в Obsidian.
- **storage/** — курсоры, seen-store (SQLite/JSON).
- **mcp_server/** — stdio MCP-сервер, мост к Claude Code.

## Конвейер данных

```
                 ┌──────────────┐
   config.yaml → │  registry    │ → [JobSource, ...]
   .env       →  └──────┬───────┘
                        │
                        ▼
   iter_dialogs(include_archived=True)        ← включая архив (Telegram folder_id 1)
                        │
                        ▼
   iter_new_messages(dialog, cursor)          ← per-dialog курсор из storage/
                        │
                        ▼
   prefilter (keywords RU/EN)  ── нет ──▶ отбросить
                        │ да
                        ▼
   LLM classify + score(profile cv.md)        ← вакансия? поля? контакт? скор 0–100
                        │ score ≥ min_score
                        ▼
   dedup (seen-store + fuzzy)
                        │
                        ▼
   cover letter (draft, тон из конфига)        ← только при score ≥ cover_letter_threshold
                        │
                        ▼
   render digest → Obsidian (.md)  +  отчёт в чат Claude Code
```

## Кто выполняет LLM-шаги

- **Основной сценарий:** классификацию, скоринг и письма делает сам **Claude Code** через
  MCP-инструменты и правила в `.claude/commands/*`. Отдельный API-ключ не нужен.
- **Автономный запуск по расписанию:** программный путь через `ANTHROPIC_API_KEY`.

## Оркестратор (pipeline.py)

`pipeline.py` связывает шаги для автономного пути:
- `collect_candidates(...)` — диалоги → seen/курсоры → предфильтр → список кандидатов (без LLM).
  Главный сценарий: дальше классифицирует сам Claude Code.
- `run_scan(...)` / `run_digest(...)` — полный конвейер с программной LLM (для запуска без человека).

## MCP-инструменты (mcp_server/)

Сервер `jobber` (stdio, `.mcp.json`) предоставляет Claude Code:
- `sources()` — источники и capability-флаги.
- `get_profile()` — текст `cv.md`.
- `scan_candidates(depth_days?, include_archived)` — собрать кандидатов (Telegram I/O + предфильтр).
- `write_digest(items, date?)` — дедуп + рендер + запись датированного файла в Obsidian.
- `seen_reset()` — сброс курсоров/seen.

## Управление через Claude Code

Команды (`/onboard`, `/scan`, `/digest`, `/cover`, `/profile-edit`, `/sources`, `/seen-reset`)
вызывают инструменты MCP-сервера и используют интеллект самого Claude Code для LLM-шагов.

> Как добавить источник — `adding-a-source.md`. Безопасность — `security.md`.
