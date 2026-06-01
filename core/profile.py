"""Загрузка профиля соискателя из profile/cv.md.

Источник истины для скоринга и писем — markdown-файл. В модель кладём весь текст
(raw_markdown), чтобы LLM имела полный контекст; структурные поля заполняются по мере надобности.
"""

from __future__ import annotations

from pathlib import Path

from core.models import Profile

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CV_PATH = ROOT / "profile" / "cv.md"


def load_profile(path: Path | None = None) -> Profile:
    """Прочитать profile/cv.md в модель Profile (raw_markdown + summary).

    Бросает FileNotFoundError, если резюме ещё не импортировано (нужно сделать /onboard).
    """
    path = Path(path) if path is not None else DEFAULT_CV_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Профиль не найден: {path}. Сначала выполните /onboard (импорт резюме)."
        )
    text = path.read_text(encoding="utf-8")
    return Profile(raw_markdown=text, summary=_first_paragraph(text))


def _first_paragraph(markdown: str) -> str | None:
    """Грубое summary: первый непустой не-заголовочный абзац."""
    for line in markdown.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and not s.startswith(">"):
            return s
    return None
