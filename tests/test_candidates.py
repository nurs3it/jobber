"""Тест сбора кандидатов (prefilter без LLM) — главный сценарий, где классифицирует Claude Code."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.models import Dialog, DialogKind, RawMessage
from pipeline import collect_candidates
from storage.store import Store


class FakeSource:
    name = "telegram"

    def __init__(self, dialogs, messages):
        self._dialogs = dialogs
        self._messages = messages

    async def iter_dialogs(self, include_archived=True):
        for d in self._dialogs:
            if d.archived and not include_archived:
                continue
            yield d

    async def iter_new_messages(self, dialog, cursor):
        for m in self._messages.get(dialog.id, []):
            if cursor is not None and int(m.message_id) <= int(cursor):
                continue
            yield m


def _msg(did, mid, text):
    return RawMessage(source="telegram", dialog_id=did, message_id=str(mid),
                      date=datetime(2026, 5, 1, tzinfo=timezone.utc), text=text)


CONFIG = {"prefilter": {"enabled": True, "keywords_ru": ["вакансия", "ищем"], "keywords_en": [],
                        "hashtags": []},
          "sources": {"telegram": {"exclude_dialogs": []}}}


@pytest.mark.asyncio
async def test_collect_candidates_prefilters_and_advances_cursor(tmp_path):
    dialog = Dialog(source="telegram", id="-100777", title="Jobs", kind=DialogKind.channel,
                    username="jobs")
    messages = {"-100777": [
        _msg("-100777", 10, "привет всем"),                 # отсеян предфильтром
        _msg("-100777", 11, "Ищем Frontend-разработчика"),  # кандидат
    ]}
    store = Store(tmp_path / "db.sqlite")
    cands = await collect_candidates(CONFIG, FakeSource([dialog], messages), store)

    assert len(cands) == 1
    assert cands[0].message_id == "11"
    assert cands[0].dialog_title == "Jobs"
    # курсор продвинулся до максимального просмотренного id (12-> здесь 11)
    assert store.get_cursor("telegram", "-100777") == "11"
    # повторный сбор ничего не вернёт (seen + cursor)
    cands2 = await collect_candidates(CONFIG, FakeSource([dialog], messages), store)
    assert cands2 == []
