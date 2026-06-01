# matching/ — детекция вакансий и скоринг

**Назначение.** Двухступенчатая детекция (экономит токены): эвристика → LLM.

**Ключевые файлы.**
- `prefilter.py` — `looks_like_vacancy(msg, config)`: regex/ключевые слова RU+EN из `config.prefilter`.
- `classifier.py` — `classify_and_score(msg, profile, config)`: вакансия ли это, извлечение полей,
  скор релевантности 0–100 с причиной (по `profile/cv.md`).

**Конвейер.** `сообщение → prefilter (дёшево) → если прошло, LLM-классификация/скоринг`.

**Кто запускает LLM.**
- Основной сценарий: классификацию/скоринг делает САМ Claude Code (через MCP + правила
  `.claude/commands/scan.md`), без отдельного API-ключа.
- Автономный запуск по расписанию: программный путь через `ANTHROPIC_API_KEY`.

**Инварианты / подводные камни.**
- Предфильтр настраивается ТОЛЬКО через `config.yaml` (не хардкодить ключевые слова).
- Скор сверяется с `config.scoring.min_score`; письма — только при `cover_letter_threshold`.
- `prefilter.enabled=False` — пропускать все сообщения в LLM (дороже, для отладки).

**Статус:** ✅ реализовано. Тесты — `tests/test_prefilter.py`, `tests/test_classifier.py` (LLM — фейк).
