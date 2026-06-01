"""Тесты LLM-классификации/скоринга и extract_json (Фаза 4). LLM — фейк с канон-ответами."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.llm import extract_json
from core.models import Profile, RawMessage
from matching.classifier import classify_and_score


# --- extract_json ---

def test_extract_json_plain():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_code_fence():
    raw = "Вот ответ:\n```json\n{\"is_vacancy\": true, \"score\": 80}\n```\nконец"
    assert extract_json(raw)["score"] == 80


def test_extract_json_with_preamble_and_braces_in_string():
    raw = 'Анализ: {"title": "Dev {senior}", "score": 50}'
    data = extract_json(raw)
    assert data["title"] == "Dev {senior}"


def test_extract_json_invalid_raises():
    with pytest.raises(ValueError):
        extract_json("нет json здесь")


# --- classify_and_score ---

class FakeLLM:
    def __init__(self, response: str):
        self._response = response
        self.calls = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self._response


def _msg(text: str) -> RawMessage:
    return RawMessage(
        source="telegram", dialog_id="-100777", message_id="55",
        date=datetime(2026, 5, 1, tzinfo=timezone.utc), text=text,
        link="https://t.me/jobs/55",
    )


PROFILE = Profile(raw_markdown="# CV\nFrontend, React, TypeScript", role="Frontend")
CONFIG = {"scoring": {"min_score": 55}}


def test_classifies_vacancy_and_extracts_fields():
    llm = FakeLLM(
        '{"is_vacancy": true, "title": "Frontend Developer", "company": "Acme", '
        '"location": "Алматы", "remote": true, "salary": "до 2000 USD", '
        '"score": 82, "reason": "React совпадает"}'
    )
    msg = _msg("Ищем Frontend (React). Пишите @hr_anna. Удалённо.")
    vacancy, match = classify_and_score(msg, PROFILE, CONFIG, llm)

    assert match.is_vacancy is True
    assert match.score == 82
    assert vacancy is not None
    assert vacancy.title == "Frontend Developer"
    assert vacancy.company == "Acme"
    assert vacancy.remote is True
    assert vacancy.link == "https://t.me/jobs/55"
    assert vacancy.dialog_id == "-100777"
    # контакт извлечён из текста сообщения
    assert vacancy.contact.found is True
    assert vacancy.contact.username == "hr_anna"


def test_non_vacancy_returns_none():
    llm = FakeLLM('{"is_vacancy": false, "score": 0, "reason": "обсуждение"}')
    vacancy, match = classify_and_score(_msg("кто-нибудь искал работу?"), PROFILE, CONFIG, llm)
    assert vacancy is None
    assert match.is_vacancy is False


def test_score_clamped_to_range():
    llm = FakeLLM('{"is_vacancy": true, "title": "X", "score": 150, "reason": "r"}')
    _, match = classify_and_score(_msg("вакансия X"), PROFILE, CONFIG, llm)
    assert match.score == 100


def test_missing_contact_marked_not_found():
    llm = FakeLLM('{"is_vacancy": true, "title": "X", "score": 70, "reason": "r"}')
    vacancy, _ = classify_and_score(_msg("Ищем X, деталей нет"), PROFILE, CONFIG, llm)
    assert vacancy.contact.found is False
    assert vacancy.contact.note == "контакт не указан"
