from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from local_prompt_studio.models import GenerationResult
from local_prompt_studio.storage import safe_slug, save_history_record


class StorageTests(unittest.TestCase):
    def test_safe_slug_never_returns_parent_components(self) -> None:
        self.assertEqual(safe_slug("../../ Secret Prompt "), "secret-prompt")
        self.assertEqual(safe_slug("中文标题"), "prompt")

    def test_history_stores_basenames_and_omits_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = save_history_record(
                idea="A safe sample",
                system_prompt_name="Example Skill",
                image_paths=[root / "private" / "reference.png"],
                settings={
                    "base_url": "http://127.0.0.1:1234/v1",
                    "model": "local-model",
                    "api_key_env": "LOCAL_TOKEN",
                    "api_key": "do-not-store",
                },
                result=GenerationResult(content="final result", model="local-model"),
                report=None,
                history_root=root / "history",
                created_at=datetime(2026, 8, 13, tzinfo=UTC),
            )
            metadata = json.loads((record / "record.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["attached_files"], ["reference.png"])
            self.assertNotIn("do-not-store", json.dumps(metadata))
            self.assertEqual((record / "output.txt").read_text(encoding="utf-8"), "final result\n")


if __name__ == "__main__":
    unittest.main()
