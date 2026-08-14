from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import ContractReport, GenerationResult


def app_data_dir() -> Path:
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "LocalPromptStudio"
    return Path.home() / ".local" / "share" / "local-prompt-studio"


def safe_slug(value: str, maximum: int = 48) -> str:
    compact = re.sub(r"\s+", "-", value.strip().lower())
    compact = re.sub(r"[^a-z0-9._-]+", "-", compact)
    compact = re.sub(r"-+", "-", compact).strip("-._")
    return compact[:maximum].rstrip("-._") or "prompt"


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def save_history_record(
    *,
    idea: str,
    system_prompt_name: str,
    image_paths: list[str | Path],
    settings: dict[str, Any],
    result: GenerationResult,
    report: ContractReport | None,
    history_root: str | Path | None = None,
    created_at: datetime | None = None,
) -> Path:
    timestamp = created_at or datetime.now(UTC)
    root = Path(history_root) if history_root else app_data_dir() / "history"
    record_dir = root / f"{timestamp:%Y%m%dT%H%M%SZ}_{safe_slug(idea)}"
    record_dir.mkdir(parents=True, exist_ok=False)

    public_settings = dict(settings)
    public_settings.pop("api_key", None)
    metadata = {
        "schema_version": 1,
        "created_at": timestamp.isoformat(),
        "system_prompt_name": system_prompt_name,
        "attached_files": [Path(path).name for path in image_paths],
        "settings": public_settings,
        "generation": {
            "finish_reason": result.finish_reason,
            "model": result.model,
            "continuations": result.continuations,
        },
        "validation": report.to_dict() if report else None,
    }
    atomic_write_text(record_dir / "idea.txt", idea.strip() + "\n")
    atomic_write_text(record_dir / "output.txt", result.content.rstrip() + "\n")
    atomic_write_text(
        record_dir / "record.json",
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
    )
    return record_dir
