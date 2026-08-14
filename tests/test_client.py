from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from local_prompt_studio.client import (
    OpenAICompatibleClient,
    StudioSettings,
    build_user_content,
    image_to_data_url,
    parse_sse_lines,
)


class FakeResponse:
    def __init__(self, lines: list[bytes]):
        self.lines = lines

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def __iter__(self):
        return iter(self.lines)


def sse(*events: dict[str, Any]) -> list[bytes]:
    return [
        *(f"data: {json.dumps(event)}\n".encode() for event in events),
        b"data: [DONE]\n",
    ]


class ClientTests(unittest.TestCase):
    def test_sse_parser_ignores_comments_and_stops_at_done(self) -> None:
        events = list(
            parse_sse_lines(
                [
                    b": keepalive\n",
                    b"\n",
                    b'data: {"choices": []}\n',
                    b"data: [DONE]\n",
                    b'data: {"ignored": true}\n',
                ]
            )
        )
        self.assertEqual(events, [{"choices": []}])

    def test_empty_reasoning_completion_continues_same_turn(self) -> None:
        responses = [
            FakeResponse(
                sse(
                    {
                        "model": "reasoning-local",
                        "choices": [
                            {
                                "delta": {"reasoning_content": "plan carefully"},
                                "finish_reason": None,
                            }
                        ],
                    },
                    {"choices": [{"delta": {}, "finish_reason": "length"}]},
                )
            ),
            FakeResponse(
                sse(
                    {
                        "model": "reasoning-local",
                        "choices": [{"delta": {"content": "final prompt"}, "finish_reason": None}],
                    },
                    {"choices": [{"delta": {}, "finish_reason": "stop"}]},
                )
            ),
        ]
        requests: list[dict[str, Any]] = []

        def opener(request: Any, **_kwargs: Any) -> FakeResponse:
            requests.append(json.loads(request.data))
            return responses.pop(0)

        seen_events: list[tuple[str, str]] = []
        client = OpenAICompatibleClient(
            StudioSettings(model="reasoning-local", max_tokens=100),
            opener=opener,
        )
        result = client.generate(
            "write a prompt", "raw idea", on_event=lambda *item: seen_events.append(item)
        )

        self.assertEqual(result.content, "final prompt")
        self.assertEqual(result.reasoning, "plan carefully")
        self.assertEqual(result.continuations, 1)
        self.assertEqual(len(requests), 2)
        self.assertTrue(requests[1]["continue_final_message"])
        self.assertFalse(requests[1]["add_generation_prompt"])
        self.assertIn("<think>\nplan carefully\n</think>", requests[1]["messages"][-1]["content"])
        self.assertIn(
            ("status", "Reasoning filled the first token budget; continuing the same turn."),
            seen_events,
        )

    def test_image_content_uses_data_url_without_changing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reference.png"
            original = b"\x89PNG\r\n\x1a\nexample"
            path.write_bytes(original)
            data_url = image_to_data_url(path)
            content = build_user_content("use the image", [path])

            self.assertTrue(data_url.startswith("data:image/png;base64,"))
            self.assertEqual(path.read_bytes(), original)
            self.assertIsInstance(content, list)
            self.assertEqual(content[1]["image_url"]["url"], data_url)  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()
