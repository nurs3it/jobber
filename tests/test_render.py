"""Тесты рендера дайджеста в Markdown для Obsidian (Фаза 5)."""

from __future__ import annotations

from datetime import datetime, timezone

from core.models import Contact, CoverLetter, MatchResult, ScoredVacancy, Vacancy
from digest.render import render_markdown, write_digest


def _item():
    return ScoredVacancy(
        vacancy=Vacancy(
            source="telegram", dialog_id="-100777", message_id="55",
            title="Frontend Developer", company="Acme",
            text="Ищем Frontend на React, удалённо",
            link="https://t.me/jobs/55",
            contact=Contact(found=True, username="hr_anna"),
            location="Алматы", remote=True, salary="до 2000 USD",
            posted_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            dialog_title="Jobs Channel",
        ),
        match=MatchResult(score=82, reason="React совпадает с резюме"),
        cover_letter=CoverLetter(text="Привет! Заинтересовала ваша вакансия по React."),
    )


def test_render_with_items_has_all_userflow_fields():
    md = render_markdown([_item()], {"date": "2026-06-01", "scanned": 120})
    assert "Frontend Developer" in md           # заголовок
    assert "82" in md                            # скор
    assert "React совпадает" in md               # причина
    assert "https://t.me/jobs/55" in md          # ссылка
    assert "@hr_anna" in md                      # контакт
    assert "Привет! Заинтересовала" in md        # сопроводительное (черновик)
    assert "Jobs Channel" in md                  # источник


def test_render_contact_not_found_shows_note():
    item = _item()
    item.vacancy.contact = Contact(found=False, note="контакт не указан")
    md = render_markdown([item], {"date": "2026-06-01"})
    assert "контакт не указан" in md


def test_render_empty_is_not_blank():
    md = render_markdown([], {"date": "2026-06-01"})
    assert md.strip() != ""
    assert "нет" in md.lower() or "не найдено" in md.lower()


def test_write_digest_creates_dated_file(tmp_path):
    cfg = {
        "digest": {
            "vault_path": str(tmp_path / "vault"),
            "subfolder": "Jobber",
            "filename_format": "%Y-%m-%d-jobber.md",
        }
    }
    when = datetime(2026, 6, 1, tzinfo=timezone.utc)
    path = write_digest("# Дайджест\nтест", cfg, when)
    assert path.exists()
    assert path.name == "2026-06-01-jobber.md"
    assert "Jobber" in str(path.parent)
    assert path.read_text(encoding="utf-8") == "# Дайджест\nтест"
