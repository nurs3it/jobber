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

    async def iter_new_messages(self, dialog, cursor, since=None):
        self.last_since = since
        for m in self._messages.get(dialog.id, []):
            if cursor is not None and int(m.message_id) <= int(cursor):
                continue
            if since is not None and m.date < since:
                break   # новые→старые: первое старое обрывает перебор
            yield m


def _msg(did, mid, text, date=None):
    return RawMessage(source="telegram", dialog_id=did, message_id=str(mid),
                      date=date or datetime(2026, 5, 1, tzinfo=timezone.utc), text=text)


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


@pytest.mark.asyncio
async def test_collect_candidates_since_excludes_old_messages(tmp_path):
    """`since` прокидывается в источник и обрывает старые сообщения (фикс B на уровне pipeline)."""
    dialog = Dialog(source="telegram", id="-100777", title="Jobs", kind=DialogKind.channel,
                    username="jobs")
    cutoff = datetime(2026, 5, 5, tzinfo=timezone.utc)
    messages = {"-100777": [                                   # новые→старые
        _msg("-100777", 12, "Ищем Frontend", date=datetime(2026, 5, 10, tzinfo=timezone.utc)),
        _msg("-100777", 11, "Ищем разработчика", date=datetime(2026, 5, 2, tzinfo=timezone.utc)),
    ]}
    store = Store(tmp_path / "db.sqlite")
    src = FakeSource([dialog], messages)
    cands = await collect_candidates(CONFIG, src, store, since=cutoff)

    assert [c.message_id for c in cands] == ["12"]   # старое (id 11, 2 мая) обрезано по cutoff
    assert src.last_since == cutoff                  # cutoff действительно дошёл до источника
