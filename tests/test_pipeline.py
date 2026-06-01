"""Интеграционный тест конвейера scan→digest на фейках (Фаза 5).

Проверяет всю цепочку: источник → предфильтр → классификация → порог скоринга →
дедуп → сопроводительное → курсоры/seen.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.models import Dialog, DialogKind, Profile, RawMessage
from pipeline import run_scan
from storage.store import Store


class FakeSource:
    name = "telegram"

    def __init__(self, dialogs, messages):
        self._dialogs = dialogs
        self._messages = messages
        self.cursors_seen = []

    async def connect(self):
        pass

    async def close(self):
        pass

    async def iter_dialogs(self, include_archived=True):
        for d in self._dialogs:
            if d.archived and not include_archived:
                continue
            yield d

    async def iter_new_messages(self, dialog, cursor):
        self.cursors_seen.append((dialog.id, cursor))
        for m in self._messages.get(dialog.id, []):
            if cursor is not None and int(m.message_id) <= int(cursor):
                continue
            yield m


class RoutingLLM:
    """Фейк: для классификатора отдаёт JSON по ключевым словам, для письма — текст."""

    def complete(self, system, user):
        if "сопроводительное" in system.lower():
            return "Привет! Заинтересовала ваша вакансия, у меня релевантный опыт на React."
        u = user.lower()
        if "привет" in u and "вакансия" not in u and "ищем" not in u:
            return '{"is_vacancy": false, "score": 0, "reason": "болтовня"}'
        if "devops" in u:
            return '{"is_vacancy": true, "title": "DevOps", "score": 40, "reason": "не профиль"}'
        return '{"is_vacancy": true, "title": "Frontend Developer", "score": 85, "reason": "React"}'


def _msg(dialog_id, mid, text):
    return RawMessage(
        source="telegram", dialog_id=dialog_id, message_id=str(mid),
        date=datetime(2026, 5, 1, tzinfo=timezone.utc), text=text,
        link=f"https://t.me/jobs/{mid}",
    )


CONFIG = {
    "prefilter": {"enabled": True, "keywords_ru": ["вакансия", "ищем"], "keywords_en": ["hiring"],
                  "hashtags": ["job"]},
    "scoring": {"min_score": 55, "cover_letter_threshold": 60},
    "digest": {"dedup_similarity": 0.85},
    "sources": {"telegram": {"exclude_dialogs": []}},
    "cover_letter": {"language": "ru"},
}


@pytest.mark.asyncio
async def test_run_scan_full_chain(tmp_path):
    dialog = Dialog(source="telegram", id="-100777", title="Jobs", kind=DialogKind.channel,
                    username="jobs", archived=False)
    messages = {
        "-100777": [
            _msg("-100777", 10, "Привет, как дела?"),                          # не вакансия (prefilter)
            _msg("-100777", 11, "Ищем Frontend на React, удалённо @hr_anna"),  # вакансия, скор 85
            _msg("-100777", 12, "Ищем DevOps инженера, Kubernetes"),           # вакансия, скор 40 < порог
        ]
    }
    source = FakeSource([dialog], messages)
    store = Store(tmp_path / "db.sqlite")
    profile = Profile(raw_markdown="# CV\nFrontend, React")

    outcome = await run_scan(CONFIG, source, profile, RoutingLLM(), store, generate_covers=True)

    # одна подходящая вакансия (85), DevOps отсеян порогом, болтовня — предфильтром
    assert len(outcome.items) == 1
    item = outcome.items[0]
    assert item.match.score == 85
    assert item.vacancy.title == "Frontend Developer"
    assert item.vacancy.dialog_title == "Jobs"
    assert item.vacancy.contact.username == "hr_anna"
    # сопроводительное сгенерировано (скор ≥ порога)
    assert item.cover_letter is not None
    assert "React" in item.cover_letter.text
    # просмотрено 3 сообщения
    assert outcome.scanned == 3
    # курсор продвинулся до максимального id
    assert store.get_cursor("telegram", "-100777") == "12"


@pytest.mark.asyncio
async def test_second_scan_skips_seen_via_cursor(tmp_path):
    dialog = Dialog(source="telegram", id="-100777", title="Jobs", kind=DialogKind.channel,
                    username="jobs")
    messages = {"-100777": [_msg("-100777", 11, "Ищем Frontend на React")]}
    source = FakeSource([dialog], messages)
    store = Store(tmp_path / "db.sqlite")
    store.set_cursor("telegram", "-100777", "11")   # уже видели до id=11
    profile = Profile(raw_markdown="# CV\nFrontend")

    outcome = await run_scan(CONFIG, source, profile, RoutingLLM(), store, generate_covers=False)
    assert outcome.scanned == 0
    assert outcome.items == []
