from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from .models import GenerationResult

EventCallback = Callable[[str, str], None]
UrlOpener = Callable[..., BinaryIO]


@dataclass(frozen=True)
class StudioSettings:
    base_url: str = "http://127.0.0.1:1234/v1"
    model: str = "local-model"
    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: int = 4096
    seed: int | None = None
    timeout_seconds: int = 1800
    api_key_env: str | None = None
    continue_empty_reasoning: bool = True

    @property
    def completion_url(self) -> str:
        cleaned = self.base_url.rstrip("/")
        if cleaned.endswith("/chat/completions"):
            return cleaned
        return f"{cleaned}/chat/completions"

    def validate(self) -> None:
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        if not self.model.strip():
            raise ValueError("model must not be empty")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        if not 0 < self.top_p <= 1:
            raise ValueError("top_p must be greater than 0 and at most 1")
        if not 1 <= self.max_tokens <= 131_072:
            raise ValueError("max_tokens must be between 1 and 131072")
        if self.timeout_seconds < 1:
            raise ValueError("timeout_seconds must be positive")


def image_to_data_url(path: str | Path) -> str:
    image_path = Path(path).expanduser().resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"Image was not found: {image_path}")
    mime_type, _ = mimetypes.guess_type(image_path.name)
    if mime_type not in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
        raise ValueError(f"Unsupported image type: {image_path.suffix or image_path.name}")
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def build_user_content(
    prompt: str, image_paths: Iterable[str | Path]
) -> str | list[dict[str, Any]]:
    paths = list(image_paths)
    if not paths:
        return prompt
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for path in paths:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": image_to_data_url(path)},
            }
        )
    return content


def parse_sse_lines(lines: Iterable[bytes | str]) -> Iterator[dict[str, Any]]:
    for raw_line in lines:
        line = (
            raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, bytes) else raw_line
        )
        line = line.strip()
        if not line or line.startswith(":") or not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            return
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError as error:
            raise RuntimeError("The local server returned invalid streaming JSON.") from error
        if isinstance(decoded, dict):
            yield decoded


class OpenAICompatibleClient:
    def __init__(self, settings: StudioSettings, opener: UrlOpener | None = None):
        settings.validate()
        self.settings = settings
        self._opener = opener or urllib.request.urlopen

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        if self.settings.api_key_env:
            token = os.environ.get(self.settings.api_key_env, "").strip()
            if not token:
                raise RuntimeError(
                    f"Environment variable {self.settings.api_key_env!r} is not set."
                )
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _request_body(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
            "max_tokens": self.settings.max_tokens,
            "stream": True,
        }
        if self.settings.seed is not None and self.settings.seed >= 0:
            body["seed"] = self.settings.seed
        return body

    def _stream_once(
        self,
        body: dict[str, Any],
        on_event: EventCallback | None = None,
    ) -> GenerationResult:
        request = urllib.request.Request(
            self.settings.completion_url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        finish_reason: str | None = None
        response_model: str | None = None

        try:
            with self._opener(request, timeout=self.settings.timeout_seconds) as response:
                for event in parse_sse_lines(response):
                    response_model = str(event.get("model") or response_model or "") or None
                    choices = event.get("choices") or []
                    if not choices:
                        continue
                    choice = choices[0]
                    delta = choice.get("delta") or {}
                    reasoning = str(delta.get("reasoning_content") or delta.get("reasoning") or "")
                    content = str(delta.get("content") or "")
                    if reasoning:
                        reasoning_parts.append(reasoning)
                        if on_event:
                            on_event("reasoning", reasoning)
                    if content:
                        content_parts.append(content)
                        if on_event:
                            on_event("content", content)
                    if choice.get("finish_reason") is not None:
                        finish_reason = str(choice["finish_reason"])
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")[:2000]
            raise RuntimeError(f"Local server returned HTTP {error.code}: {details}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(
                f"Could not reach the local model server at {self.settings.completion_url}: "
                f"{error.reason}"
            ) from error

        return GenerationResult(
            content="".join(content_parts).strip(),
            reasoning="".join(reasoning_parts).strip(),
            finish_reason=finish_reason,
            model=response_model,
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        image_paths: Iterable[str | Path] = (),
        on_event: EventCallback | None = None,
    ) -> GenerationResult:
        if not system_prompt.strip():
            raise ValueError("system_prompt must not be empty")
        if not user_prompt.strip():
            raise ValueError("user_prompt must not be empty")

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": build_user_content(user_prompt.strip(), image_paths)},
        ]
        first = self._stream_once(self._request_body(messages), on_event)
        should_continue = (
            self.settings.continue_empty_reasoning
            and not first.content
            and first.finish_reason == "length"
            and bool(first.reasoning)
        )
        if not should_continue:
            if not first.content:
                raise RuntimeError(
                    "The local model returned no final content "
                    f"(finish_reason={first.finish_reason})."
                )
            return first

        if on_event:
            on_event("status", "Reasoning filled the first token budget; continuing the same turn.")
        reasoning_prefill = f"<think>\n{first.reasoning}\n</think>\n\n"
        continuation_messages = [
            *messages,
            {"role": "assistant", "content": reasoning_prefill},
        ]
        continuation_body = self._request_body(continuation_messages)
        continuation_body.update(
            {
                "add_generation_prompt": False,
                "continue_final_message": True,
            }
        )
        second = self._stream_once(continuation_body, on_event)
        if not second.content:
            raise RuntimeError(
                "The local model returned no final content after same-turn continuation."
            )
        return GenerationResult(
            content=second.content,
            reasoning="\n".join(part for part in (first.reasoning, second.reasoning) if part),
            finish_reason=second.finish_reason,
            model=second.model or first.model,
            continuations=1,
        )
