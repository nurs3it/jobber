"""MCP-сервер (stdio) — мост между Claude Code и ядром Jobber.

Главный сценарий: Telegram-I/O и запись дайджеста делает сервер, а классификацию/скоринг/
сопроводительные пишет САМ Claude Code (по cv.md), без отдельного API-ключа.

Инструменты:
  - sources()                      — источники и их capability-флаги.
  - get_profile()                  — текст profile/cv.md (для скоринга Claude'ом).
  - scan_candidates(...)           — собрать сообщения-кандидаты (после предфильтра, без LLM).
  - write_digest(items, date?)     — дедуп + рендер + запись датированного файла в Obsidian.
  - seen_reset()                   — сбросить курсоры/seen.

ИНВАРИАНТ: read-only по Telegram — НЕТ инструментов отправки сообщений. Секреты/сессия наружу
не отдаются.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from core.config import load_config, load_secrets
from core.interfaces import Capabilities
from core.models import Contact, CoverLetter, MatchResult, ScoredVacancy, Vacancy
from core.profile import DEFAULT_CV_PATH, load_profile
from digest.dedup import collapse_duplicates
from digest.render import render_markdown, write_digest as _write_digest
from pipeline import collect_candidates
from registry import build_sources
from storage.store import Store

mcp = FastMCP("jobber")


def _config() -> dict[str, Any]:
    return load_config()


def _telegram_source(config: dict[str, Any]):
    """Построить включённый Telegram-источник (или None, если выключен)."""
    for src in build_sources(config, load_secrets()):
        if src.name == "telegram":
            return src
    return None


@mcp.tool()
def sources() -> list[dict[str, Any]]:
    """Список источников и их capability-флаги (can_scan/can_search/can_apply)."""
    config = _config()
    out: list[dict[str, Any]] = []
    for name in ("telegram", "linkedin", "webboards"):
        enabled = bool(config.get("sources", {}).get(name, {}).get("enabled"))
        caps = Capabilities(can_scan=True, can_search=True, can_apply=False) if name == "telegram" \
            else Capabilities()
        out.append({
            "name": name,
            "enabled": enabled,
            "can_scan": caps.can_scan,
            "can_search": caps.can_search,
            "can_apply": caps.can_apply,  # всегда False — отклик только вручную
            "status": "рабочий, read-only" if name == "telegram" else "заглушка (Фаза 7)",
        })
    return out


@mcp.tool()
def get_profile() -> str:
    """Вернуть текст profile/cv.md (источник истины для скоринга). Без секретов."""
    if not DEFAULT_CV_PATH.exists():
        return "ПРОФИЛЬ НЕ НАЙДЕН. Сначала выполните /onboard (импорт резюме в profile/cv.md)."
    return load_profile().raw_markdown or ""


@mcp.tool()
async def scan_candidates(
    depth_days: int | None = None,
    include_archived: bool = True,
) -> dict[str, Any]:
    """Собрать сообщения-кандидаты на вакансии (после предфильтра, БЕЗ LLM).

    Дальше Claude Code сам классифицирует/скорит каждый по cv.md и пишет письма.
    Обновляет seen-store и курсоры. depth_days фильтрует слишком старые сообщения.
    """
    config = _config()
    source = _telegram_source(config)
    if source is None:
        return {"error": "Источник telegram выключен в config.yaml (sources.telegram.enabled)."}

    # cutoff из depth_days прокидывается ВНИЗ в источник, чтобы перебор обрывался по дате
    # на стороне сбора (а не пост-фильтровал уже скачанную историю каждого диалога).
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=depth_days) if depth_days is not None else None
    )

    store = Store()
    await source.connect()
    try:
        candidates = await collect_candidates(
            config, source, store, include_archived=include_archived, since=cutoff
        )
    finally:
        await source.close()

    if cutoff is not None:  # defense-in-depth: финальная отсечка по дате
        candidates = [c for c in candidates if c.date >= cutoff]

    return {
        "count": len(candidates),
        "candidates": [
            {
                "dialog_id": c.dialog_id,
                "dialog_title": c.dialog_title,
                "message_id": c.message_id,
                "date": c.date.isoformat(),
                "text": c.text,
                "link": c.link,
                "sender": c.sender,
                "archived": c.archived,
            }
            for c in candidates
        ],
    }


@mcp.tool()
def write_digest(items: list[dict[str, Any]], date: str | None = None) -> dict[str, Any]:
    """Дедуп + рендер + запись дайджеста в Obsidian.

    items — оценённые Claude'ом вакансии. Поля (все опц., кроме text/score):
      title, company, link, location, remote, salary, score, reason, cover_letter,
      dialog_title, message_id, dialog_id, text, contact{found,username,url,bot,raw,note}.
    """
    config = _config()
    scored = [_to_scored(it) for it in items]
    scored = collapse_duplicates(scored, config)
    scored.sort(key=lambda sv: sv.match.score, reverse=True)

    when = _parse_date(date)
    markdown = render_markdown(scored, {"date": when.strftime("%Y-%m-%d")})
    path: Path = _write_digest(markdown, config, when)
    return {"path": str(path), "count": len(scored)}


@mcp.tool()
def seen_reset() -> str:
    """Сбросить курсоры и seen-store (следующий scan пройдёт заново)."""
    Store().reset()
    return "Курсоры и seen-store сброшены. Следующий /scan пройдёт заново."


# --- helpers ---

def _to_scored(it: dict[str, Any]) -> ScoredVacancy:
    c = it.get("contact") or {}
    contact = Contact(
        found=bool(c.get("found", any(c.get(k) for k in ("username", "url", "bot", "raw")))),
        username=c.get("username"), url=c.get("url"), bot=c.get("bot"),
        raw=c.get("raw"), note=c.get("note") or (None if c else "контакт не указан"),
    )
    vacancy = Vacancy(
        source="telegram",
        dialog_id=str(it.get("dialog_id", "")),
        message_id=str(it.get("message_id", "")),
        title=it.get("title"), company=it.get("company"),
        text=it.get("text", ""), link=it.get("link"), contact=contact,
        location=it.get("location"), remote=it.get("remote"), salary=it.get("salary"),
        dialog_title=it.get("dialog_title"),
        posted_at=_parse_dt(it.get("date")),
    )
    match = MatchResult(score=int(it.get("score", 0)), reason=it.get("reason", ""))
    cl = it.get("cover_letter")
    cover = CoverLetter(text=cl) if cl else None
    return ScoredVacancy(vacancy=vacancy, match=match, cover_letter=cover)


def _parse_date(date: str | None) -> datetime:
    if date:
        try:
            return datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def main() -> None:
    """Точка входа stdio MCP-сервера."""
    mcp.run()


if __name__ == "__main__":
    main()
