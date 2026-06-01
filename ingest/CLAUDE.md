# ingest/ — импорт резюме → profile/cv.md

**Назначение.** Принять CV в pdf/docx/img и превратить в структурированный `profile/cv.md`.

**Ключевые файлы.**
- `cv_import.py` — `extract_text(path)` (pdf/docx/img/txt) и `write_cv_markdown(md, dest)`
  (атомарная запись + бэкап `cv.md.bak`).
- `__main__.py` — CLI: `python -m ingest extract <file>` печатает извлечённый текст (для /onboard).
- Сохранение TG-ключей — `core.config.update_env({...})` (обновляет .env, не теряя другие строки).

**Статус:** ✅ реализовано (Фаза 1). Тесты — `tests/test_cv_import.py`, `test_env_io.py`, `test_ingest_cli.py`
(реальные docx/pdf round-trip, без моков).

**Извлечение текста.**
- PDF → `pypdf` (fallback `pdfplumber` для сложных макетов).
- DOCX → `python-docx` (параграфы + таблицы).
- IMG → в Claude Code читает зрение Claude (лучший вариант); программный fallback — `pytesseract` (extra `ocr`).

**Как это работает в продукте.**
- Структурирование «сырой текст → cv.md» в основном сценарии делает САМ Claude Code
  по правилам из `.claude/commands/onboard.md`. Главное правило: **ничего не упускать** —
  перенести в cv.md все факты резюме (опыт, навыки, образование, контакты, прочее).
- Этот модуль гарантирует надёжное извлечение текста и даёт программный fallback.

**Инварианты / подводные камни.**
- ⚠️ Резюме — личные данные. `profile/cv.md` и `profile/uploads/` в `.gitignore`. Не логировать содержимое.
- Разные резюме = разные структуры. Не навязывать жёсткую схему — сохранять все секции исходника.
- Плохой OCR картинок — частая проблема; см. `.claude/docs/troubleshooting.md`.
