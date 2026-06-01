"""Дедупликация вакансий для дайджеста.

Две ступени:
  1. seen-store по (source, dialog_id, message_id) — точное «уже видели» (storage/).
  2. fuzzy-схлопывание одинаковых вакансий, репостнутых в разных каналах
     (по нормализованному тексту, порог digest.dedup_similarity).
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from core.models import ScoredVacancy, Vacancy

_NORM_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    text = (text or "").lower()
    text = _NORM_RE.sub(" ", text)      # убрать пунктуацию
    text = _WS_RE.sub(" ", text).strip()
    return text


def dedup_key(vacancy: Vacancy) -> str:
    """Стабильный ключ для сравнения: нормализованные первые ~200 символов заголовка+текста."""
    base = f"{vacancy.title or ''} {vacancy.text or ''}"
    return _normalize(base)[:200]


def _similar(a: str, b: str, threshold: float) -> bool:
    if a == b:
        return True
    return SequenceMatcher(None, a, b).ratio() >= threshold


def collapse_duplicates(
    items: list[ScoredVacancy], config: dict[str, Any]
) -> list[ScoredVacancy]:
    """Схлопнуть повторы одной вакансии (из разных источников), оставив вариант с лучшим скором."""
    threshold = float(config.get("digest", {}).get("dedup_similarity", 0.85))
    kept: list[tuple[str, ScoredVacancy]] = []

    for item in items:
        key = dedup_key(item.vacancy)
        item.dedup_key = key
        match_index = None
        for i, (existing_key, _) in enumerate(kept):
            if _similar(key, existing_key, threshold):
                match_index = i
                break

        if match_index is None:
            kept.append((key, item))
        else:
            _, existing = kept[match_index]
            if item.match.score > existing.match.score:
                kept[match_index] = (key, item)  # оставляем лучший скор

    return [sv for _, sv in kept]
