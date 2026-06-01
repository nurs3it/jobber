# core/ — ядро (provider-agnostic)

**Назначение.** Доменные контракты, общие для всех источников. Ядро НЕ знает о Telegram.

**Ключевые файлы.**
- `models.py` — pydantic-модели: `Dialog`, `RawMessage`, `Contact`, `Profile`, `Vacancy`, `MatchResult`, `CoverLetter`, `ScoredVacancy`.
- `interfaces.py` — `JobSource` (Protocol) + `Capabilities` (флаги can_scan/can_search/can_apply).
- `config.py` — загрузка `config.yaml` и `.env` (единственная точка чтения настроек).

**Как расширять.**
- Новые поля вакансии/профиля — добавляй в `models.py`, не в источниках.
- Новый источник реализует `JobSource` (см. `.claude/docs/adding-a-source.md`).

**Инварианты / подводные камни.**
- ⚠️ `core/` НЕ импортирует ничего из `sources/`. Зависимость строго в одну сторону.
- `CoverLetter.is_draft` всегда True — ничего не отправляется автоматически.
- `Contact.found=False` + `note` — честная пометка «контакт не указан», не пустая строка.
- `Capabilities.can_apply` у read-only источников (Telegram) — всегда False.
