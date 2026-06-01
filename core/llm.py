"""Абстракция LLM для автономного (программного) пути классификации и писем.

В основном сценарии LLM-шаги выполняет сам Claude Code; этот модуль нужен для запуска
конвейера по расписанию без участия человека (через ANTHROPIC_API_KEY).

  - `LLM` — протокол с единственным методом complete(system, user) -> str.
  - `AnthropicLLM` — реальная реализация на Anthropic SDK (ленивый импорт).
  - `extract_json` — достать JSON-объект из ответа модели (терпит ```-обёртки и преамбулу).
"""

from __future__ import annotations

import json
from typing import Any, Protocol


class LLM(Protocol):
    def complete(self, system: str, user: str) -> str: ...


def extract_json(text: str) -> dict[str, Any]:
    """Извлечь первый сбалансированный JSON-объект из текста ответа модели.

    Бросает ValueError, если объект не найден/не парсится.
    """
    if not text:
        raise ValueError("Пустой ответ модели")

    # Быстрый путь: весь текст — валидный JSON.
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Иначе ищем первый сбалансированный {...}.
    start = stripped.find("{")
    while start != -1:
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(stripped)):
            ch = stripped[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = stripped[start : i + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break
        start = stripped.find("{", start + 1)

    raise ValueError("В ответе модели не найден валидный JSON-объект")


class AnthropicLLM:
    """Реальная LLM поверх Anthropic SDK. Используется только в автономном режиме."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 1024,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, system: str, user: str) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key) if self._api_key else anthropic.Anthropic()
        resp = client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text
