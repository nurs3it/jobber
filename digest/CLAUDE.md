# digest/ — дедуп, агрегация, рендер в Obsidian

**Назначение.** Собрать оценённые вакансии в датированный Markdown-файл для Obsidian
и продублировать краткий отчёт в чат Claude Code.

**Ключевые файлы.**
- `dedup.py` — `dedup_key()` + `collapse_duplicates()`: точный seen-store (storage/) +
  fuzzy-схлопывание одной вакансии, репостнутой в разных каналах (`config.digest.dedup_similarity`).
- `render.py` — `render_markdown()` + `write_digest()`: сводка сверху + карточки.

**Карточка вакансии (поля user-flow).**
ссылка · кому писать (контакт или «не указан») · сопроводительное (черновик) ·
скор + причина · источник · дата.

**Инварианты / подводные камни.**
- Нет новых вакансий → короткая пометка, **НЕ пустой файл**.
- Путь: `config.digest.vault_path` / `subfolder` / `filename_format` (strftime). По умолчанию `./vault/Jobber`.
- ⚠️ Никогда не печатать в дайджест секреты, сессию или сырой CV.

**Статус:** ✅ реализовано. Тесты — `tests/test_dedup.py`, `tests/test_render.py`.
