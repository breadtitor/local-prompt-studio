from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .client import OpenAICompatibleClient, StudioSettings
from .contracts import validate_output
from .models import ContractReport, GenerationResult
from .skills import SkillPackage, load_skill_package
from .storage import app_data_dir, atomic_write_text, save_history_record


class PromptStudioApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Local Prompt Studio")
        self.root.geometry("1120x760")
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.skill: SkillPackage | None = None
        self.image_paths: list[str] = []
        self.generating = False

        self.base_url = tk.StringVar(value="http://127.0.0.1:1234/v1")
        self.model = tk.StringVar(value="local-model")
        self.api_key_env = tk.StringVar(value="")
        self.temperature = tk.StringVar(value="0.20")
        self.top_p = tk.StringVar(value="0.90")
        self.max_tokens = tk.StringVar(value="4096")
        self.seed = tk.StringVar(value="-1")
        self.skill_label = tk.StringVar(value="No skill selected")
        self.status = tk.StringVar(value="Select a Skill package to begin.")

        self._load_settings()
        self._build_ui()
        self.root.after(80, self._poll_events)

    @property
    def settings_path(self) -> Path:
        return app_data_dir() / "settings.json"

    def _load_settings(self) -> None:
        try:
            value = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for variable, key in (
            (self.base_url, "base_url"),
            (self.model, "model"),
            (self.api_key_env, "api_key_env"),
            (self.temperature, "temperature"),
            (self.top_p, "top_p"),
            (self.max_tokens, "max_tokens"),
            (self.seed, "seed"),
        ):
            if key in value:
                variable.set(str(value[key]))

    def _save_settings(self) -> None:
        value = {
            "schema_version": 1,
            "base_url": self.base_url.get().strip(),
            "model": self.model.get().strip(),
            "api_key_env": self.api_key_env.get().strip(),
            "temperature": self.temperature.get().strip(),
            "top_p": self.top_p.get().strip(),
            "max_tokens": self.max_tokens.get().strip(),
            "seed": self.seed.get().strip(),
        }
        atomic_write_text(self.settings_path, json.dumps(value, indent=2) + "\n")

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        connection = ttk.LabelFrame(outer, text="Local model server", padding=10)
        connection.pack(fill="x")
        for column in range(8):
            connection.columnconfigure(column, weight=1 if column in {1, 3} else 0)
        ttk.Label(connection, text="Base URL").grid(row=0, column=0, sticky="w")
        ttk.Entry(connection, textvariable=self.base_url).grid(
            row=0, column=1, columnspan=2, sticky="ew", padx=(6, 12)
        )
        ttk.Label(connection, text="Model").grid(row=0, column=3, sticky="w")
        ttk.Entry(connection, textvariable=self.model).grid(
            row=0, column=4, columnspan=2, sticky="ew", padx=(6, 12)
        )
        ttk.Label(connection, text="Token env (optional)").grid(row=0, column=6, sticky="w")
        ttk.Entry(connection, textvariable=self.api_key_env, width=18).grid(
            row=0, column=7, sticky="ew", padx=(6, 0)
        )

        for label, variable, column in (
            ("Temperature", self.temperature, 0),
            ("Top P", self.top_p, 2),
            ("Max tokens", self.max_tokens, 4),
            ("Seed (-1=random)", self.seed, 6),
        ):
            ttk.Label(connection, text=label).grid(row=1, column=column, sticky="w", pady=(8, 0))
            ttk.Entry(connection, textvariable=variable, width=12).grid(
                row=1, column=column + 1, sticky="ew", padx=(6, 12), pady=(8, 0)
            )

        source = ttk.LabelFrame(outer, text="Prompt-writing Skill", padding=10)
        source.pack(fill="x", pady=(10, 0))
        source.columnconfigure(0, weight=1)
        ttk.Label(source, textvariable=self.skill_label).grid(row=0, column=0, sticky="w")
        ttk.Button(source, text="Open SKILL.md or ZIP", command=self._choose_skill_file).grid(
            row=0, column=1, padx=(8, 0)
        )
        ttk.Button(source, text="Open Skill folder", command=self._choose_skill_folder).grid(
            row=0, column=2, padx=(8, 0)
        )
        ttk.Button(source, text="Inspect", command=self._show_skill_info).grid(
            row=0, column=3, padx=(8, 0)
        )

        body = ttk.Panedwindow(outer, orient="horizontal")
        body.pack(fill="both", expand=True, pady=(10, 0))
        left = ttk.Frame(body, padding=(0, 0, 8, 0))
        right = ttk.Frame(body)
        body.add(left, weight=2)
        body.add(right, weight=3)

        ttk.Label(left, text="Raw request").pack(anchor="w")
        self.idea = tk.Text(left, wrap="word", height=16, undo=True)
        self.idea.pack(fill="both", expand=True, pady=(4, 8))

        attachments = ttk.LabelFrame(left, text="Reference images", padding=8)
        attachments.pack(fill="x")
        self.image_list = tk.Listbox(attachments, height=5)
        self.image_list.pack(fill="x")
        image_buttons = ttk.Frame(attachments)
        image_buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(image_buttons, text="Add", command=self._add_images).pack(side="left")
        ttk.Button(image_buttons, text="Remove", command=self._remove_images).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(image_buttons, text="Clear", command=self._clear_images).pack(
            side="left", padx=(6, 0)
        )

        actions = ttk.Frame(left)
        actions.pack(fill="x", pady=(10, 0))
        self.generate_button = ttk.Button(actions, text="Generate locally", command=self._generate)
        self.generate_button.pack(side="left")
        ttk.Button(actions, text="Save output", command=self._save_output).pack(
            side="left", padx=(8, 0)
        )

        notebook = ttk.Notebook(right)
        notebook.pack(fill="both", expand=True)
        self.output_text = self._text_tab(notebook, "Final output")
        self.reasoning_text = self._text_tab(notebook, "Live reasoning")
        self.validation_text = self._text_tab(notebook, "Validation")
        self.log_text = self._text_tab(notebook, "Log")

        status_bar = ttk.Label(outer, textvariable=self.status, relief="sunken", anchor="w")
        status_bar.pack(fill="x", pady=(8, 0))

    @staticmethod
    def _text_tab(notebook: ttk.Notebook, title: str) -> tk.Text:
        frame = ttk.Frame(notebook, padding=6)
        text = tk.Text(frame, wrap="word")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        notebook.add(frame, text=title)
        return text

    def _choose_skill_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select SKILL.md or ZIP",
            filetypes=[("Skill packages", "SKILL.md *.zip"), ("All files", "*.*")],
        )
        if path:
            self._load_skill(path)

    def _choose_skill_folder(self) -> None:
        path = filedialog.askdirectory(title="Select Skill folder")
        if path:
            self._load_skill(path)

    def _load_skill(self, path: str) -> None:
        try:
            self.skill = load_skill_package(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            messagebox.showerror("Skill could not be loaded", str(error))
            return
        contract = self.skill.contract.name if self.skill.contract else "no output contract"
        self.skill_label.set(
            f"{self.skill.name} · {len(self.skill.included_files)} text file(s) · {contract}"
        )
        self.status.set("Skill loaded. Its scripts and binaries will not be executed.")
        self._log(f"Loaded Skill from {self.skill.source}")
        for warning in self.skill.warnings:
            self._log(f"Warning: {warning}")

    def _show_skill_info(self) -> None:
        if not self.skill:
            messagebox.showinfo("Skill", "No Skill is loaded.")
            return
        details = [
            f"Name: {self.skill.name}",
            f"Source: {self.skill.source}",
            f"Format version: {self.skill.format_version}",
            f"Text characters: {len(self.skill.prompt_text)}",
            f"Contract: {self.skill.contract.name if self.skill.contract else 'none'}",
        ]
        if self.skill.provenance:
            provenance_lines = [f"  {key}: {value}" for key, value in self.skill.provenance.items()]
            details.extend(["Provenance:", *provenance_lines])
        details.extend(
            [
                "Files:",
                *[f"  - {name}" for name in self.skill.included_files],
                "",
                "Scripts executed: no",
            ]
        )
        messagebox.showinfo("Skill inspection", "\n".join(details))

    def _add_images(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select reference images",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.gif"), ("All files", "*.*")],
        )
        for path in paths:
            if path not in self.image_paths:
                self.image_paths.append(path)
                self.image_list.insert("end", Path(path).name)

    def _remove_images(self) -> None:
        for index in reversed(self.image_list.curselection()):
            self.image_list.delete(index)
            self.image_paths.pop(index)

    def _clear_images(self) -> None:
        self.image_paths.clear()
        self.image_list.delete(0, "end")

    def _settings(self) -> StudioSettings:
        seed_value = int(self.seed.get())
        return StudioSettings(
            base_url=self.base_url.get().strip(),
            model=self.model.get().strip(),
            api_key_env=self.api_key_env.get().strip() or None,
            temperature=float(self.temperature.get()),
            top_p=float(self.top_p.get()),
            max_tokens=int(self.max_tokens.get()),
            seed=seed_value if seed_value >= 0 else None,
        )

    def _generate(self) -> None:
        if self.generating:
            return
        if not self.skill:
            messagebox.showwarning("Skill required", "Select a Skill package first.")
            return
        idea = self.idea.get("1.0", "end").strip()
        if not idea:
            messagebox.showwarning("Request required", "Enter a raw request first.")
            return
        try:
            settings = self._settings()
            settings.validate()
            self._save_settings()
        except (OSError, ValueError) as error:
            messagebox.showerror("Invalid settings", str(error))
            return

        self.generating = True
        self.generate_button.state(["disabled"])
        for widget in (self.output_text, self.reasoning_text, self.validation_text):
            widget.delete("1.0", "end")
        self.status.set("Calling the local model server…")
        skill = self.skill
        images = list(self.image_paths)

        def event(kind: str, text: str) -> None:
            self.events.put((kind, text))

        def worker() -> None:
            try:
                result = OpenAICompatibleClient(settings).generate(
                    skill.prompt_text,
                    idea,
                    images,
                    event,
                )
                report = (
                    validate_output(result.content, skill.contract, len(images))
                    if skill.contract
                    else None
                )
                record_dir = save_history_record(
                    idea=idea,
                    system_prompt_name=skill.name,
                    image_paths=images,
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
                )
                self.events.put(("complete", (result, report, record_dir)))
            except Exception as error:  # Keep worker exceptions inside the UI boundary.
                self.events.put(("error", error))

        threading.Thread(target=worker, name="local-prompt-generation", daemon=True).start()

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "reasoning":
                    self.reasoning_text.insert("end", str(payload))
                    self.reasoning_text.see("end")
                elif kind == "content":
                    self.output_text.insert("end", str(payload))
                    self.output_text.see("end")
                elif kind == "status":
                    self.status.set(str(payload))
                    self._log(str(payload))
                elif kind == "complete":
                    result, report, record_dir = payload  # type: ignore[misc]
                    self._complete(result, report, record_dir)
                elif kind == "error":
                    self.generating = False
                    self.generate_button.state(["!disabled"])
                    self.status.set("Generation failed.")
                    self._log(f"Error: {payload}")
                    messagebox.showerror("Generation failed", str(payload))
        except queue.Empty:
            pass
        self.root.after(80, self._poll_events)

    def _complete(
        self,
        result: GenerationResult,
        report: ContractReport | None,
        record_dir: Path,
    ) -> None:
        self.generating = False
        self.generate_button.state(["!disabled"])
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", result.content)
        if report:
            self.validation_text.insert(
                "1.0", json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
            )
        else:
            self.validation_text.insert("1.0", "No output contract was supplied by this Skill.")
        validation = "passed" if not report or report.valid else "failed"
        self.status.set(f"Complete · validation {validation} · history saved privately")
        self._log(f"Saved history to {record_dir}")

    def _save_output(self) -> None:
        content = self.output_text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("Nothing to save", "Generate or paste an output first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save final output",
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("Markdown", "*.md"), ("All files", "*.*")],
        )
        if path:
            atomic_write_text(Path(path), content + "\n")
            self.status.set(f"Saved output to {path}")

    def _log(self, message: str) -> None:
        self.log_text.insert("end", message.rstrip() + "\n")
        self.log_text.see("end")


def main() -> None:
    root = tk.Tk()
    PromptStudioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
