"""Тесты генерации сопроводительных писем (Фаза 5). LLM — фейк."""

from __future__ import annotations

from core.models import Profile, Vacancy
from cover.generator import generate_cover_letter


class FakeLLM:
    def __init__(self, text="Привет! Увидел вашу вакансию —很 заинтересовало."):
        self.text = text
        self.calls = []

    def complete(self, system, user):
        self.calls.append((system, user))
        return self.text


PROFILE = Profile(raw_markdown="# CV\nFrontend, React, 5 лет опыта")


def _vac(text="Ищем Frontend на React, удалённо", title="Frontend Developer"):
    return Vacancy(source="telegram", dialog_id="1", message_id="1", text=text, title=title)


def test_returns_draft_cover_letter():
    cl = generate_cover_letter(_vac(), PROFILE, {"cover_letter": {"language": "ru"}}, FakeLLM("Текст"))
    assert cl.is_draft is True
    assert cl.text == "Текст"
    assert cl.language == "ru"


def test_tone_and_constraints_passed_to_llm():
    llm = FakeLLM()
    cfg = {"cover_letter": {"tone": "youthful", "youthful": True, "max_sentences": 5, "language": "ru"}}
    generate_cover_letter(_vac(), PROFILE, cfg, llm)
    system, user = llm.calls[0]
    combined = (system + user).lower()
    assert "5" in combined            # ограничение длины передано
    assert "youthful" in combined or "молод" in combined
    # профиль и текст вакансии переданы в промпт
    assert "react" in combined
    assert "frontend" in combined


def test_language_auto_detects_russian():
    cfg = {"cover_letter": {"language": "auto"}}
    cl = generate_cover_letter(_vac("Ищем разработчика, удалённо"), PROFILE, cfg, FakeLLM("текст"))
    assert cl.language == "ru"


def test_language_auto_detects_english():
    cfg = {"cover_letter": {"language": "auto"}}
    cl = generate_cover_letter(_vac("We are hiring a Frontend developer, remote"), PROFILE, cfg, FakeLLM("text"))
    assert cl.language == "en"
