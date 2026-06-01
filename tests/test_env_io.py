"""Тесты записи секретов в .env (Фаза 1): создание, обновление, добавление ключей.

Инвариант: обновление одного ключа не теряет остальные строки и комментарии.
"""

from __future__ import annotations

from core import config


def test_update_env_creates_when_missing(tmp_path):
    env = tmp_path / ".env"
    config.update_env({"TG_API_ID": "123"}, env)
    assert "TG_API_ID=123" in env.read_text(encoding="utf-8")


def test_update_env_updates_existing_key_preserving_others(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment\nTG_API_ID=old\nTG_PHONE=+700\n", encoding="utf-8")
    config.update_env({"TG_API_ID": "new"}, env)
    content = env.read_text(encoding="utf-8")
    assert "TG_API_ID=new" in content
    assert "TG_API_ID=old" not in content
    assert "TG_PHONE=+700" in content
    assert "# comment" in content


def test_update_env_appends_new_key(tmp_path):
    env = tmp_path / ".env"
    env.write_text("TG_API_ID=1\n", encoding="utf-8")
    config.update_env({"TG_API_HASH": "abc"}, env)
    content = env.read_text(encoding="utf-8")
    assert "TG_API_ID=1" in content
    assert "TG_API_HASH=abc" in content


def test_update_env_multiple_keys(tmp_path):
    env = tmp_path / ".env"
    config.update_env({"TG_API_ID": "1", "TG_API_HASH": "h", "TG_PHONE": "+7"}, env)
    content = env.read_text(encoding="utf-8")
    assert "TG_API_ID=1" in content
    assert "TG_API_HASH=h" in content
    assert "TG_PHONE=+7" in content
