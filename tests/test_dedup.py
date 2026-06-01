"""Тесты дедупликации вакансий (Фаза 3/5): fuzzy-схлопывание повторов из разных каналов."""

from __future__ import annotations

from core.models import MatchResult, ScoredVacancy, Vacancy
from digest.dedup import collapse_duplicates, dedup_key

CONFIG = {"digest": {"dedup_similarity": 0.85}}


def _sv(text, score, dialog="c1", title=None):
    return ScoredVacancy(
        vacancy=Vacancy(source="telegram", dialog_id=dialog, message_id="1", text=text, title=title),
        match=MatchResult(score=score, reason="ok"),
    )


def test_dedup_key_stable_and_normalized():
    a = _sv("Ищем  Frontend-разработчика!!!", 80)
    b = _sv("ищем frontend разработчика", 80)
    assert dedup_key(a.vacancy) == dedup_key(b.vacancy)


def test_collapse_identical_reposts_keeps_one():
    items = [
        _sv("Ищем Frontend-разработчика, React, удалённо", 70, dialog="c1"),
        _sv("Ищем Frontend-разработчика, React, удалённо", 90, dialog="c2"),
    ]
    out = collapse_duplicates(items, CONFIG)
    assert len(out) == 1
    # остаётся вариант с лучшим скором
    assert out[0].match.score == 90


def test_distinct_vacancies_not_collapsed():
    items = [
        _sv("Ищем Frontend-разработчика, React", 70),
        _sv("Требуется DevOps-инженер, Kubernetes", 75),
    ]
    out = collapse_duplicates(items, CONFIG)
    assert len(out) == 2


def test_near_duplicates_collapsed_by_threshold():
    items = [
        _sv("Ищем Frontend разработчика на React, удалённо, ЗП по итогам", 60),
        _sv("Ищем Frontend разработчика на React, удалённо, зарплата по итогам собеседования", 88),
    ]
    out = collapse_duplicates(items, CONFIG)
    assert len(out) == 1
    assert out[0].match.score == 88


def test_empty_list():
    assert collapse_duplicates([], CONFIG) == []
