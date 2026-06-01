---
description: Показать источники вакансий и их capability-флаги (can_scan / can_search / can_apply).
---

# /sources — источники

Перечислить зарегистрированные источники и их возможности.

## Шаги

1. Вызвать MCP-инструмент `sources()` (читает `config.yaml → sources` и отдаёт флаги).
2. Для каждого источника показать: имя, enabled, `Capabilities` (can_scan / can_search / can_apply), статус.
3. `telegram` — рабочий (read-only); `linkedin`, `webboards` — заглушки (Фаза 7).

Ожидаемый вид:

| Источник | Вкл. | can_scan | can_search | can_apply | Статус |
|---|---|---|---|---|---|
| telegram | да | ✓ | ✓ | ✗ | рабочий, read-only |
| linkedin | нет | ✗ | ? | ✗ | заглушка |
| webboards | нет | ✗ | ? | ✗ | заглушка |

> Все источники read-only по платформе: `can_apply=False`. Отклик — всегда вручную.
