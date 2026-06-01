"""Тесты извлечения контакта из текста вакансии (Фаза 4, модуль mapping.extract_contact)."""

from __future__ import annotations

from sources.telegram import mapping


def test_extract_username():
    c = mapping.extract_contact("Пишите @hr_anna по вакансии")
    assert c.found is True
    assert c.username == "hr_anna"


def test_extract_tme_link():
    c = mapping.extract_contact("Контакт: https://t.me/recruiter_io")
    assert c.found is True
    assert c.url == "https://t.me/recruiter_io"


def test_extract_bot():
    c = mapping.extract_contact("Откликнуться через @jobs_apply_bot")
    assert c.found is True
    assert c.bot == "jobs_apply_bot"


def test_extract_email():
    c = mapping.extract_contact("Резюме на hr@company.com")
    assert c.found is True
    assert c.raw == "hr@company.com"


def test_extract_phone_only():
    c = mapping.extract_contact("Звоните +7 700 123 45 67")
    assert c.found is True
    assert "700" in (c.raw or "")


def test_no_contact():
    c = mapping.extract_contact("Ищем разработчика, подробности позже")
    assert c.found is False
    assert c.note == "контакт не указан"


def test_empty_text():
    c = mapping.extract_contact("")
    assert c.found is False


def test_email_not_mistaken_for_username():
    # @ внутри email не должен дать ложный username
    c = mapping.extract_contact("hr@company.com")
    assert c.username is None
    assert c.raw == "hr@company.com"
