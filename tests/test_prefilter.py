"""Тесты эвристического предфильтра (Фаза 3)."""

from __future__ import annotations

from datetime import datetime, timezone

from core.models import RawMessage
from matching.prefilter import looks_like_vacancy

CONFIG = {
    "prefilter": {
        "enabled": True,
        "keywords_ru": ["вакансия", "ищем", "удалённо", "зарплата"],
        "keywords_en": ["hiring", "we're hiring", "remote"],
        "hashtags": ["вакансия", "hiring", "job"],
    }
}


def _msg(text: str) -> RawMessage:
    return RawMessage(
        source="telegram", dialog_id="1", message_id="1",
        date=datetime(2026, 5, 1, tzinfo=timezone.utc), text=text,
    )


def test_matches_russian_keyword():
    assert looks_like_vacancy(_msg("Открыта вакансия Frontend"), CONFIG) is True


def test_matches_case_insensitive():
    assert looks_like_vacancy(_msg("МЫ ИЩЕМ разработчика"), CONFIG) is True


def test_matches_english_keyword():
    assert looks_like_vacancy(_msg("We are hiring a backend dev"), CONFIG) is True


def test_matches_hashtag():
    assert looks_like_vacancy(_msg("#job senior react"), CONFIG) is True


def test_no_match_returns_false():
    assert looks_like_vacancy(_msg("Привет, как дела?"), CONFIG) is False


def test_empty_text_false():
    assert looks_like_vacancy(_msg(""), CONFIG) is False


def test_disabled_prefilter_passes_everything():
    cfg = {"prefilter": {"enabled": False}}
    assert looks_like_vacancy(_msg("любой текст"), cfg) is True
