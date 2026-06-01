"""Оркестратор конвейера Jobber: источник → предфильтр → LLM → дедуп → письма → дайджест.

Это автономный (программный) путь, используемый MCP-сервером и расписанием. Все зависимости
инъектируются (source, profile, llm, store), поэтому конвейер целиком тестируется на фейках.

Поток: iter_dialogs(archived) → iter_new_messages(cursor) → seen-store → prefilter →
classify_and_score → порог min_score → (опц.) cover letter → collapse_duplicates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.llm import LLM
from core.models import Profile, RawMessage, ScoredVacancy
from cover.generator import generate_cover_letter
from digest.dedup import collapse_duplicates
from digest.render import render_markdown, write_digest
from matching.classifier import classify_and_score
from matching.prefilter import looks_like_vacancy
from storage.store import Store


@dataclass
class ScanOutcome:
    items: list[ScoredVacancy] = field(default_factory=list)
    scanned: int = 0


async def run_scan(
    config: dict[str, Any],
    source: Any,
    profile: Profile,
    llm: LLM,
    store: Store,
    *,
    include_archived: bool = True,
    generate_covers: bool = False,
    since: datetime | None = None,
) -> ScanOutcome:
    """Пройти по диалогам источника, найти и оценить вакансии. Обновляет курсоры/seen.

    ``since`` — нижняя граница по дате (из depth_days), как в ``collect_candidates``.
    """
    min_score = int(config.get("scoring", {}).get("min_score", 55))
    cover_threshold = int(config.get("scoring", {}).get("cover_letter_threshold", 60))
    exclude = set(config.get("sources", {}).get(source.name, {}).get("exclude_dialogs", []))

    outcome = ScanOutcome()

    async for dialog in source.iter_dialogs(include_archived=include_archived):
        if dialog.id in exclude or dialog.username in exclude or dialog.title in exclude:
            continue

        cursor = store.get_cursor(source.name, dialog.id)
        max_id = _to_int(cursor)

        async for msg in source.iter_new_messages(dialog, cursor, since=since):
            if store.is_seen(source.name, dialog.id, msg.message_id):
                continue
            store.mark_seen(source.name, dialog.id, msg.message_id)
            outcome.scanned += 1
            max_id = _max_id(max_id, msg.message_id)

            if not looks_like_vacancy(msg, config):
                continue

            vacancy, match = classify_and_score(msg, profile, config, llm)
            if vacancy is None or match.score < min_score:
                continue

            vacancy.dialog_title = dialog.title
            vacancy.archived = dialog.archived

            cover = None
            if generate_covers and match.score >= cover_threshold:
                cover = generate_cover_letter(vacancy, profile, config, llm)

            outcome.items.append(
                ScoredVacancy(vacancy=vacancy, match=match, cover_letter=cover)
            )

        if max_id is not None:
            store.set_cursor(source.name, dialog.id, str(max_id))

    outcome.items = collapse_duplicates(outcome.items, config)
    outcome.items.sort(key=lambda sv: sv.match.score, reverse=True)
    return outcome


async def collect_candidates(
    config: dict[str, Any],
    source: Any,
    store: Store,
    *,
    include_archived: bool = True,
    since: datetime | None = None,
) -> list[RawMessage]:
    """Собрать сообщения-кандидаты (после предфильтра, БЕЗ LLM). Главный сценарий: дальше
    классификацию/скоринг/письма делает сам Claude Code (через MCP). Обновляет seen/курсоры.

    ``since`` — нижняя граница по дате (из depth_days): источник обрывает перебор на первом
    сообщении старше cutoff, поэтому узкий проход не тянет всю историю диалога.
    """
    exclude = set(config.get("sources", {}).get(source.name, {}).get("exclude_dialogs", []))
    candidates: list[RawMessage] = []

    async for dialog in source.iter_dialogs(include_archived=include_archived):
        if dialog.id in exclude or dialog.username in exclude or dialog.title in exclude:
            continue

        cursor = store.get_cursor(source.name, dialog.id)
        max_id = _to_int(cursor)

        async for msg in source.iter_new_messages(dialog, cursor, since=since):
            if store.is_seen(source.name, dialog.id, msg.message_id):
                continue
            store.mark_seen(source.name, dialog.id, msg.message_id)
            max_id = _max_id(max_id, msg.message_id)

            if not looks_like_vacancy(msg, config):
                continue

            msg.dialog_title = dialog.title
            msg.archived = dialog.archived
            candidates.append(msg)

        if max_id is not None:
            store.set_cursor(source.name, dialog.id, str(max_id))

    return candidates


async def run_digest(
    config: dict[str, Any],
    source: Any,
    profile: Profile,
    llm: LLM,
    store: Store,
    when: datetime,
    *,
    include_archived: bool = True,
):
    """Собрать дайджест: scan c письмами → рендер → запись в Obsidian. Возвращает (path, outcome)."""
    outcome = await run_scan(
        config, source, profile, llm, store,
        include_archived=include_archived, generate_covers=True,
    )
    markdown = render_markdown(
        outcome.items, {"date": when.strftime("%Y-%m-%d"), "scanned": outcome.scanned}
    )
    path = write_digest(markdown, config, when)
    return path, outcome


def _to_int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _max_id(current: int | None, message_id: str) -> int | None:
    mid = _to_int(message_id)
    if mid is None:
        return current
    return mid if current is None else max(current, mid)
