"""Рендер дайджеста в Markdown для Obsidian.

Датированный файл в vault (config.digest.vault_path/subfolder/filename_format):
  - сверху сводка;
  - ниже карточки по каждой вакансии с полями user-flow:
      ссылка · кому писать (контакт или «не указан») · сопроводительное (черновик) ·
      скор + причина · источник · дата.
Нет новых вакансий — короткая пометка, НЕ пустой файл.

⚠️ Никогда не печатать в дайджест секреты, сессию или сырой CV.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from core.config import ROOT
from core.models import Contact, ScoredVacancy


def _contact_line(contact: Contact) -> str:
    if not contact or not contact.found:
        return "контакт не указан"
    parts: list[str] = []
    if contact.username:
        parts.append(f"@{contact.username}")
    if contact.url:
        parts.append(contact.url)
    if contact.bot:
        parts.append(f"бот @{contact.bot}")
    if contact.raw:
        parts.append(contact.raw)
    return " · ".join(parts) if parts else "контакт не указан"


def _card(item: ScoredVacancy) -> str:
    v = item.vacancy
    m = item.match
    title = v.title or "Вакансия"
    head = f"## {title}"
    if v.company:
        head += f" — {v.company}"

    lines = [head, ""]
    lines.append(f"- **Скор:** {m.score}/100 — {m.reason}")
    lines.append(f"- **Ссылка:** {v.link or '—'}")
    lines.append(f"- **Кому писать:** {_contact_line(v.contact)}")

    meta_bits = []
    if v.location:
        meta_bits.append(v.location)
    if v.remote:
        meta_bits.append("удалённо")
    if v.salary:
        meta_bits.append(v.salary)
    if meta_bits:
        lines.append(f"- **Условия:** {' · '.join(meta_bits)}")

    src = v.dialog_title or v.dialog_id
    date = v.posted_at.strftime("%Y-%m-%d") if v.posted_at else ""
    lines.append(f"- **Источник:** {src}{(' · ' + date) if date else ''}")

    if item.cover_letter:
        lines.append("")
        lines.append("> **Сопроводительное (черновик — отправляете сами):**")
        for cl_line in item.cover_letter.text.splitlines() or [item.cover_letter.text]:
            lines.append(f"> {cl_line}")

    lines.append("")
    return "\n".join(lines)


def render_markdown(items: list[ScoredVacancy], meta: dict[str, Any]) -> str:
    """Собрать Markdown дайджеста (сводка + карточки или пометка «новых нет»)."""
    date = meta.get("date", "")
    header = [f"# Jobber — дайджест {date}".rstrip(), ""]

    if not items:
        header.append("_Новых подходящих вакансий не найдено._")
        if meta.get("scanned") is not None:
            header.append("")
            header.append(f"Просмотрено сообщений: {meta['scanned']}.")
        return "\n".join(header) + "\n"

    summary = f"Найдено подходящих вакансий: **{len(items)}**."
    if meta.get("scanned") is not None:
        summary += f" Просмотрено сообщений: {meta['scanned']}."
    header.append(summary)
    header.append("")
    header.append("---")
    header.append("")

    body = "\n".join(_card(i) for i in items)
    return "\n".join(header) + "\n" + body


def write_digest(markdown: str, config: dict[str, Any], when: datetime) -> Path:
    """Записать дайджест в vault по filename_format (strftime). Возвращает путь."""
    digest = config.get("digest", {})
    base = Path(digest.get("vault_path", "./vault"))
    if not base.is_absolute():
        base = ROOT / base
    folder = base / digest.get("subfolder", "Jobber")
    folder.mkdir(parents=True, exist_ok=True)

    filename = when.strftime(digest.get("filename_format", "%Y-%m-%d-jobber.md"))
    path = folder / filename
    path.write_text(markdown, encoding="utf-8")
    return path
