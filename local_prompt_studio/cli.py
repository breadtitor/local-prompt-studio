from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .client import OpenAICompatibleClient, StudioSettings
from .contracts import PromptContract, validate_output
from .skills import SkillPackage, load_skill_package
from .storage import atomic_write_text, save_history_record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="local-prompt-studio",
        description=" ".join(
            [
                "Run a user-supplied prompt-writing skill against an",
                "OpenAI-compatible local server.",
            ]
        ),
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--skill", help="Skill directory, SKILL.md, or ZIP package")
    source.add_argument("--system", help="Plain system-prompt text file")
    idea = parser.add_mutually_exclusive_group()
    idea.add_argument("--idea", help="Raw request to transform")
    idea.add_argument("--idea-file", help="UTF-8 text file containing the raw request")
    parser.add_argument("--image", action="append", default=[], help="Reference image; repeatable")
    parser.add_argument(
        "--contract", help="Optional output-contract JSON; overrides skill contract"
    )
    parser.add_argument("--base-url", default=os.getenv("LPS_BASE_URL", "http://127.0.0.1:1234/v1"))
    parser.add_argument("--model", default=os.getenv("LPS_MODEL", "local-model"))
    parser.add_argument(
        "--api-key-env", help="Environment variable containing an optional bearer token"
    )
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", "-o", help="Write final output to this file")
    parser.add_argument("--history-dir", help="Override the private local history directory")
    parser.add_argument("--no-save", action="store_true", help="Do not create a history record")
    parser.add_argument("--show-reasoning", action="store_true", help="Stream reasoning to stderr")
    parser.add_argument(
        "--inspect-skill",
        action="store_true",
        help="Validate and summarize the skill without calling a model",
    )
    parser.add_argument(
        "--validate-only", help="Validate an existing output file without calling a model"
    )
    return parser


def _load_plain_system(path: str) -> SkillPackage:
    system_path = Path(path).expanduser().resolve()
    text = system_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("System-prompt file is empty")
    return SkillPackage(
        name=system_path.stem,
        source=str(system_path),
        prompt_text=text,
        included_files=(system_path.name,),
    )


def _contract(args: argparse.Namespace, package: SkillPackage) -> PromptContract | None:
    if args.contract:
        return PromptContract.from_json_file(args.contract)
    return package.contract


def _skill_summary(package: SkillPackage) -> dict[str, object]:
    return {
        "name": package.name,
        "source": package.source,
        "format_version": package.format_version,
        "provenance": package.provenance,
        "included_files": list(package.included_files),
        "prompt_characters": len(package.prompt_text),
        "contract": package.contract.name if package.contract else None,
        "warnings": list(package.warnings),
        "scripts_executed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if not args.skill and not args.system:
            parser.error("one of --skill or --system is required")
        package = load_skill_package(args.skill) if args.skill else _load_plain_system(args.system)
        contract = _contract(args, package)

        if args.inspect_skill:
            print(json.dumps(_skill_summary(package), ensure_ascii=False, indent=2))
            return 0

        if args.validate_only:
            if contract is None:
                parser.error("--validate-only requires a skill contract or --contract")
            text = Path(args.validate_only).read_text(encoding="utf-8")
            report = validate_output(text, contract, len(args.image))
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
            return 0 if report.valid else 2

        if args.idea_file:
            idea = Path(args.idea_file).read_text(encoding="utf-8")
        else:
            idea = args.idea or ""
        if not idea.strip():
            parser.error("one of --idea or --idea-file is required for generation")

        settings = StudioSettings(
            base_url=args.base_url,
            model=args.model,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            seed=args.seed,
            api_key_env=args.api_key_env,
        )

        def on_event(kind: str, text: str) -> None:
            if kind == "reasoning" and args.show_reasoning:
                sys.stderr.write(text)
                sys.stderr.flush()
            elif kind == "status":
                sys.stderr.write(f"\n[{text}]\n")

        result = OpenAICompatibleClient(settings).generate(
            package.prompt_text,
            idea,
            args.image,
            on_event,
        )
        report = validate_output(result.content, contract, len(args.image)) if contract else None
        if args.output:
            atomic_write_text(Path(args.output), result.content.rstrip() + "\n")
        else:
            print(result.content)

        if not args.no_save:
            record_dir = save_history_record(
                idea=idea,
                system_prompt_name=package.name,
                image_paths=args.image,
                settings={
                    "base_url": settings.base_url,
                    "model": settings.model,
                    "temperature": settings.temperature,
                    "top_p": settings.top_p,
                    "max_tokens": settings.max_tokens,
                    "seed": settings.seed,
                    "api_key_env": settings.api_key_env,
                },
                result=result,
                report=report,
                history_root=args.history_dir,
            )
            sys.stderr.write(f"History: {record_dir}\n")
        if report and not report.valid:
            sys.stderr.write(
                "Output failed the selected contract; inspect the saved validation report.\n"
            )
            return 2
        return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        sys.stderr.write(f"Local Prompt Studio failed: {error}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
