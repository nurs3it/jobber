"""Тесты storage: курсоры и seen-store (Фаза 3). SQLite во временном файле."""

from __future__ import annotations

from storage.store import Store


def test_cursor_roundtrip(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    assert s.get_cursor("telegram", "42") is None
    s.set_cursor("telegram", "42", "1000")
    assert s.get_cursor("telegram", "42") == "1000"
    s.set_cursor("telegram", "42", "1050")
    assert s.get_cursor("telegram", "42") == "1050"


def test_cursor_is_per_dialog_and_source(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    s.set_cursor("telegram", "1", "10")
    s.set_cursor("telegram", "2", "20")
    assert s.get_cursor("telegram", "1") == "10"
    assert s.get_cursor("telegram", "2") == "20"
    assert s.get_cursor("linkedin", "1") is None


def test_seen_roundtrip(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    assert s.is_seen("telegram", "1", "100") is False
    s.mark_seen("telegram", "1", "100")
    assert s.is_seen("telegram", "1", "100") is True
    # повторная отметка идемпотентна
    s.mark_seen("telegram", "1", "100")
    assert s.is_seen("telegram", "1", "100") is True


def test_seen_distinguishes_messages(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    s.mark_seen("telegram", "1", "100")
    assert s.is_seen("telegram", "1", "101") is False


def test_reset_clears_everything(tmp_path):
    s = Store(tmp_path / "db.sqlite")
    s.set_cursor("telegram", "1", "10")
    s.mark_seen("telegram", "1", "100")
    s.reset()
    assert s.get_cursor("telegram", "1") is None
    assert s.is_seen("telegram", "1", "100") is False


def test_persists_across_instances(tmp_path):
    db = tmp_path / "db.sqlite"
    Store(db).set_cursor("telegram", "1", "77")
    assert Store(db).get_cursor("telegram", "1") == "77"
