from __future__ import annotations

import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dnd_game.ai.story_writer import DEFAULT_MODEL, DEFAULT_REASONING_EFFORT
from dnd_game.ai.story_writer_studio_support import (
    ENV_API_KEY,
    ENV_MODEL,
    ENV_REASONING_EFFORT,
    STORY_WRITER_STUDIO_ENV_KEYS,
    STORY_WRITER_STUDIO_MODE_OPTIONS,
    STORY_WRITER_STUDIO_MODEL_OPTIONS,
    STORY_WRITER_STUDIO_REASONING_OPTIONS,
    StoryWriterLaunchOptions,
    build_story_writer_command,
    display_command,
    generated_story_output_dir,
    load_dotenv_values,
    relative_or_absolute_path,
    split_multivalue_text,
    suggested_story_output_path,
    update_dotenv_file,
)

SUGGESTED_CONTEXTS = (
    PROJECT_ROOT / "information" / "Story" / "STORY_CONTENT_SUMMARY.md",
    PROJECT_ROOT / "information" / "Story" / "ACT1_CONTENT_REFERENCE.md",
    PROJECT_ROOT / "information" / "Story" / "ACT2_CONTENT_REFERENCE.md",
    PROJECT_ROOT / "information" / "Story" / "ACT1_DIALOGUE_REFERENCE.md",
)


class StoryWriterStudioApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Aethrune Story Writer Studio")
        self.root.geometry("1360x920")
        self.root.minsize(1120, 760)

        self.project_root = PROJECT_ROOT
        self.env_path = self.project_root / ".env"
        self.output_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.current_process: subprocess.Popen[str] | None = None
        self.current_worker: threading.Thread | None = None
        self.current_command_captures_draft = False
        self.current_command_output_lines: list[str] = []

        self.api_key_var = tk.StringVar()
        self.show_api_key_var = tk.BooleanVar(value=False)
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.reasoning_var = tk.StringVar(value=DEFAULT_REASONING_EFFORT)
        self.mode_var = tk.StringVar(value="revision")
        self.title_var = tk.StringVar()
        self.scene_key_var = tk.StringVar()
        self.tone_var = tk.StringVar()
        self.save_path_var = tk.StringVar()
        self.no_default_context_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready.")

        self.context_paths: list[Path] = []

        self.configure_style()
        self.build_ui()
        self.load_env_values_into_form()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.process_output_queue)

    def configure_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Studio.TFrame", padding=8)
        style.configure("Studio.TLabelframe", padding=10)
        style.configure("Studio.TButton", padding=(10, 6))
        style.configure("Status.TLabel", padding=(8, 6))

    def build_ui(self) -> None:
        container = ttk.Frame(self.root, style="Studio.TFrame")
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        settings_frame = ttk.LabelFrame(container, text="OpenAI Setup", style="Studio.TLabelframe")
        settings_frame.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 8))
        for column in range(5):
            settings_frame.columnconfigure(column, weight=1 if column in (1, 3) else 0)

        ttk.Label(settings_frame, text="API key").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.api_key_entry = ttk.Entry(settings_frame, textvariable=self.api_key_var, show="*")
        self.api_key_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=4)
        ttk.Checkbutton(
            settings_frame,
            text="Show",
            variable=self.show_api_key_var,
            command=self.toggle_api_key_visibility,
        ).grid(row=0, column=2, sticky="w", padx=(0, 12), pady=4)

        ttk.Label(settings_frame, text="Model").grid(row=0, column=3, sticky="w", padx=(0, 8), pady=4)
        self.model_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.model_var,
            values=STORY_WRITER_STUDIO_MODEL_OPTIONS,
            state="normal",
        )
        self.model_combo.grid(row=0, column=4, sticky="ew", pady=4)

        ttk.Label(settings_frame, text="Reasoning").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.reasoning_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.reasoning_var,
            values=STORY_WRITER_STUDIO_REASONING_OPTIONS,
            state="normal",
        )
        self.reasoning_combo.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=4)

        ttk.Label(settings_frame, text="Mode").grid(row=1, column=3, sticky="w", padx=(0, 8), pady=4)
        self.mode_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.mode_var,
            values=STORY_WRITER_STUDIO_MODE_OPTIONS,
            state="readonly",
        )
        self.mode_combo.grid(row=1, column=4, sticky="ew", pady=4)

        ttk.Checkbutton(
            settings_frame,
            text="Disable story_writer default context",
            variable=self.no_default_context_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

        button_bar = ttk.Frame(settings_frame)
        button_bar.grid(row=2, column=3, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Button(
            button_bar,
            text="Save API Settings",
            command=self.save_api_settings,
            style="Studio.TButton",
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            button_bar,
            text="Install OpenAI SDK",
            command=self.install_openai_sdk,
            style="Studio.TButton",
        ).pack(side="left")

        details_frame = ttk.LabelFrame(container, text="Rewrite Brief", style="Studio.TLabelframe")
        details_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 8))
        for column in range(4):
            details_frame.columnconfigure(column, weight=1 if column in (1, 3) else 0)

        ttk.Label(details_frame, text="Title").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(details_frame, textvariable=self.title_var).grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=4)
        ttk.Label(details_frame, text="Scene key").grid(row=0, column=2, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(details_frame, textvariable=self.scene_key_var).grid(row=0, column=3, sticky="ew", pady=4)

        ttk.Label(details_frame, text="Tone notes").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(details_frame, textvariable=self.tone_var).grid(row=1, column=1, columnspan=3, sticky="ew", pady=4)

        ttk.Label(details_frame, text="Speakers").grid(row=2, column=0, sticky="nw", padx=(0, 8), pady=(4, 0))
        self.speakers_text = ScrolledText(details_frame, height=4, wrap="word")
        self.speakers_text.grid(row=2, column=1, columnspan=3, sticky="ew", pady=4)

        ttk.Label(details_frame, text="Rewrite brief").grid(row=3, column=0, sticky="nw", padx=(0, 8), pady=(4, 0))
        self.brief_text = ScrolledText(details_frame, height=8, wrap="word")
        self.brief_text.grid(row=3, column=1, columnspan=3, sticky="nsew", pady=4)
        details_frame.rowconfigure(3, weight=1)

        lower_pane = ttk.Panedwindow(container, orient="horizontal")
        lower_pane.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0, 8))

        context_frame = ttk.LabelFrame(lower_pane, text="Context Files", style="Studio.TLabelframe")
        output_frame = ttk.LabelFrame(lower_pane, text="Command Console", style="Studio.TLabelframe")
        lower_pane.add(context_frame, weight=1)
        lower_pane.add(output_frame, weight=2)

        context_frame.columnconfigure(0, weight=1)
        context_frame.rowconfigure(1, weight=1)
        ttk.Label(
            context_frame,
            text="Add the scene file or draft docs you want ChatGPT to read before rewriting.",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        context_list_frame = ttk.Frame(context_frame)
        context_list_frame.grid(row=1, column=0, sticky="nsew")
        context_list_frame.columnconfigure(0, weight=1)
        context_list_frame.rowconfigure(0, weight=1)
        self.context_list = tk.Listbox(context_list_frame, height=10, selectmode="extended")
        self.context_list.grid(row=0, column=0, sticky="nsew")
        context_scrollbar = ttk.Scrollbar(context_list_frame, orient="vertical", command=self.context_list.yview)
        context_scrollbar.grid(row=0, column=1, sticky="ns")
        self.context_list.configure(yscrollcommand=context_scrollbar.set)

        context_button_column = ttk.Frame(context_frame)
        context_button_column.grid(row=1, column=1, sticky="ns", padx=(8, 0))
        ttk.Button(
            context_button_column,
            text="Add Files",
            command=self.add_context_files,
            style="Studio.TButton",
        ).pack(fill="x", pady=(0, 6))
        ttk.Button(
            context_button_column,
            text="Add Story Summary",
            command=lambda: self.add_known_context(SUGGESTED_CONTEXTS[0]),
            style="Studio.TButton",
        ).pack(fill="x", pady=6)
        ttk.Button(
            context_button_column,
            text="Add Act 1 Ref",
            command=lambda: self.add_known_context(SUGGESTED_CONTEXTS[1]),
            style="Studio.TButton",
        ).pack(fill="x", pady=6)
        ttk.Button(
            context_button_column,
            text="Add Act 2 Ref",
            command=lambda: self.add_known_context(SUGGESTED_CONTEXTS[2]),
            style="Studio.TButton",
        ).pack(fill="x", pady=6)
        ttk.Button(
            context_button_column,
            text="Add Dialogue Ref",
            command=lambda: self.add_known_context(SUGGESTED_CONTEXTS[3]),
            style="Studio.TButton",
        ).pack(fill="x", pady=6)
        ttk.Button(
            context_button_column,
            text="Remove Selected",
            command=self.remove_selected_context,
            style="Studio.TButton",
        ).pack(fill="x", pady=6)
        ttk.Button(
            context_button_column,
            text="Clear Context",
            command=self.clear_context,
            style="Studio.TButton",
        ).pack(fill="x", pady=(6, 0))

        ttk.Label(output_frame, text="Saved output path").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(2, weight=1)
        output_frame.rowconfigure(3, weight=1)
        save_row = ttk.Frame(output_frame)
        save_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        save_row.columnconfigure(0, weight=1)
        ttk.Entry(save_row, textvariable=self.save_path_var).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(
            save_row,
            text="Browse",
            command=self.choose_save_path,
            style="Studio.TButton",
        ).grid(row=0, column=1, sticky="e")

        console_actions = ttk.Frame(output_frame)
        console_actions.grid(row=0, column=1, rowspan=2, sticky="ne", padx=(12, 0))
        self.run_button = ttk.Button(
            console_actions,
            text="Run Rewrite",
            command=self.run_rewrite,
            style="Studio.TButton",
        )
        self.run_button.pack(fill="x", pady=(0, 6))
        self.stop_button = ttk.Button(
            console_actions,
            text="Stop",
            command=self.stop_process,
            style="Studio.TButton",
            state="disabled",
        )
        self.stop_button.pack(fill="x", pady=6)
        ttk.Button(
            console_actions,
            text="Save Draft",
            command=self.save_generated_draft,
            style="Studio.TButton",
        ).pack(fill="x", pady=6)
        ttk.Button(
            console_actions,
            text="Clear Console",
            command=self.clear_console,
            style="Studio.TButton",
        ).pack(fill="x", pady=6)

        draft_frame = ttk.LabelFrame(output_frame, text="Rewritten Draft", style="Studio.TLabelframe")
        draft_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        draft_frame.columnconfigure(0, weight=1)
        draft_frame.rowconfigure(0, weight=1)
        self.generated_draft_text = ScrolledText(draft_frame, height=14, wrap="word")
        self.generated_draft_text.grid(row=0, column=0, sticky="nsew")

        self.console = ScrolledText(output_frame, height=10, wrap="word", state="disabled", font=("Consolas", 10))
        self.console.grid(row=3, column=0, columnspan=2, sticky="nsew")

        status_bar = ttk.Label(container, textvariable=self.status_var, style="Status.TLabel", anchor="w")
        status_bar.grid(row=3, column=0, sticky="ew", padx=4, pady=(0, 4))

    def load_env_values_into_form(self) -> None:
        file_values = load_dotenv_values(self.env_path, STORY_WRITER_STUDIO_ENV_KEYS)
        self.api_key_var.set(file_values.get(ENV_API_KEY, os.environ.get(ENV_API_KEY, "")))
        self.model_var.set(file_values.get(ENV_MODEL, os.environ.get(ENV_MODEL, DEFAULT_MODEL)))
        self.reasoning_var.set(
            file_values.get(ENV_REASONING_EFFORT, os.environ.get(ENV_REASONING_EFFORT, DEFAULT_REASONING_EFFORT))
        )

    def toggle_api_key_visibility(self) -> None:
        self.api_key_entry.configure(show="" if self.show_api_key_var.get() else "*")

    def append_console(self, text: str) -> None:
        self.console.configure(state="normal")
        self.console.insert("end", text)
        self.console.see("end")
        self.console.configure(state="disabled")

    def clear_console(self) -> None:
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def generated_draft(self) -> str:
        return self.generated_draft_text.get("1.0", "end").strip()

    def set_generated_draft(self, text: str) -> None:
        self.generated_draft_text.delete("1.0", "end")
        if text:
            self.generated_draft_text.insert("1.0", text)

    def add_context_path(self, path: Path) -> None:
        resolved = path.resolve()
        if resolved in self.context_paths:
            return
        self.context_paths.append(resolved)
        self.context_list.insert("end", relative_or_absolute_path(resolved, self.project_root))

    def add_known_context(self, path: Path) -> None:
        if not path.exists():
            messagebox.showerror("Missing file", f"Could not find:\n{path}")
            return
        self.add_context_path(path)

    def add_context_files(self) -> None:
        selected = filedialog.askopenfilenames(
            parent=self.root,
            title="Choose context files",
            initialdir=str(self.project_root),
        )
        for item in selected:
            self.add_context_path(Path(item))

    def remove_selected_context(self) -> None:
        selected_indexes = list(self.context_list.curselection())
        if not selected_indexes:
            return
        for index in reversed(selected_indexes):
            del self.context_paths[index]
            self.context_list.delete(index)

    def clear_context(self) -> None:
        self.context_paths.clear()
        self.context_list.delete(0, "end")

    def choose_save_path(self) -> None:
        current_value = self.save_path_var.get().strip()
        current_path = None
        if current_value:
            current_path = Path(current_value)
            if not current_path.is_absolute():
                current_path = (self.project_root / current_path).resolve()
        elif self.title_var.get().strip() or self.scene_key_var.get().strip():
            current_path = suggested_story_output_path(
                self.project_root,
                title=self.title_var.get().strip(),
                scene_key=self.scene_key_var.get().strip(),
                mode=self.mode_var.get().strip() or "revision",
            )
        initial_dir = current_path.parent if current_path is not None else generated_story_output_dir(self.project_root)
        initial_dir.mkdir(parents=True, exist_ok=True)
        selected = filedialog.asksaveasfilename(
            parent=self.root,
            title="Choose where to save the generated draft",
            initialdir=str(initial_dir),
            initialfile=current_path.name if current_path is not None else "",
            defaultextension=".md",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if selected:
            self.save_path_var.set(relative_or_absolute_path(Path(selected), self.project_root))

    def collect_launch_options(self) -> StoryWriterLaunchOptions:
        brief = self.brief_text.get("1.0", "end").strip()
        speakers = split_multivalue_text(self.speakers_text.get("1.0", "end"))
        save_path = Path(self.save_path_var.get().strip()) if self.save_path_var.get().strip() else None
        if save_path is not None and not save_path.is_absolute():
            save_path = (self.project_root / save_path).resolve()
        return StoryWriterLaunchOptions(
            brief=brief,
            mode=self.mode_var.get().strip() or "revision",
            title=self.title_var.get().strip(),
            scene_key=self.scene_key_var.get().strip(),
            speakers=speakers,
            tone_notes=self.tone_var.get().strip(),
            context_paths=tuple(self.context_paths),
            no_default_context=bool(self.no_default_context_var.get()),
            model=self.model_var.get().strip() or DEFAULT_MODEL,
            reasoning_effort=self.reasoning_var.get().strip() or DEFAULT_REASONING_EFFORT,
            save_path=save_path,
        )

    def current_subprocess_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        if self.api_key_var.get().strip():
            env[ENV_API_KEY] = self.api_key_var.get().strip()
        if self.model_var.get().strip():
            env[ENV_MODEL] = self.model_var.get().strip()
        if self.reasoning_var.get().strip():
            env[ENV_REASONING_EFFORT] = self.reasoning_var.get().strip()
        return env

    def save_api_settings(self) -> None:
        updates = {
            ENV_API_KEY: self.api_key_var.get().strip(),
            ENV_MODEL: self.model_var.get().strip(),
            ENV_REASONING_EFFORT: self.reasoning_var.get().strip(),
        }
        update_dotenv_file(self.env_path, updates)
        self.status_var.set(f"Saved API settings to {self.env_path.name}.")
        self.append_console(f"[studio] Saved API settings to {self.env_path.name}\n")

    def set_process_state(self, *, running: bool) -> None:
        self.run_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")

    def install_openai_sdk(self) -> None:
        command = [sys.executable, "-m", "pip", "install", "openai"]
        self.launch_command(command, description="Installing or upgrading the OpenAI SDK", capture_generated_output=False)

    def run_rewrite(self) -> None:
        options = self.collect_launch_options()
        if not options.brief:
            messagebox.showerror("Missing brief", "Enter a rewrite brief before running the studio.")
            return
        command = build_story_writer_command(
            sys.executable,
            project_root=self.project_root,
            options=options,
        )
        self.launch_command(command, description="Running story_writer.py", capture_generated_output=True)

    def launch_command(self, command: list[str], *, description: str, capture_generated_output: bool) -> None:
        if self.current_process is not None:
            messagebox.showinfo("Busy", "A command is already running in the studio console.")
            return

        self.current_command_captures_draft = capture_generated_output
        self.current_command_output_lines = []
        self.set_process_state(running=True)
        self.status_var.set(description + "...")
        self.append_console(f"\n[studio] {description}\n")
        self.append_console(f"[command] {display_command(command)}\n\n")

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            process = subprocess.Popen(
                command,
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creationflags,
                env=self.current_subprocess_env(),
            )
        except Exception as exc:
            self.append_console(f"[studio] Failed to launch command: {exc}\n")
            self.status_var.set("Failed to launch command.")
            self.set_process_state(running=False)
            return
        self.current_process = process
        worker = threading.Thread(target=self.stream_process_output, args=(process,), daemon=True)
        self.current_worker = worker
        worker.start()

    def stream_process_output(self, process: subprocess.Popen[str]) -> None:
        assert process.stdout is not None
        try:
            for line in process.stdout:
                self.output_queue.put(("line", line))
        finally:
            return_code = process.wait()
            self.output_queue.put(("done", str(return_code)))

    def process_output_queue(self) -> None:
        while True:
            try:
                kind, payload = self.output_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "line":
                if self.current_command_captures_draft:
                    self.current_command_output_lines.append(payload)
                self.append_console(payload)
            elif kind == "done":
                return_code = int(payload)
                if return_code == 0:
                    if self.current_command_captures_draft:
                        rewritten_text = "".join(self.current_command_output_lines).strip()
                        self.set_generated_draft(rewritten_text)
                        if rewritten_text:
                            if not self.save_path_var.get().strip():
                                suggested_path = suggested_story_output_path(
                                    self.project_root,
                                    title=self.title_var.get().strip(),
                                    scene_key=self.scene_key_var.get().strip(),
                                    mode=self.mode_var.get().strip() or "revision",
                                )
                                self.save_path_var.set(relative_or_absolute_path(suggested_path, self.project_root))
                            self.append_console("[studio] Rewritten draft loaded into the editor pane.\n")
                    self.status_var.set("Command finished successfully.")
                    self.append_console("\n[studio] Command finished successfully.\n")
                else:
                    self.status_var.set(f"Command exited with code {return_code}.")
                    self.append_console(f"\n[studio] Command exited with code {return_code}.\n")
                self.current_command_captures_draft = False
                self.current_command_output_lines = []
                self.current_process = None
                self.current_worker = None
                self.set_process_state(running=False)
        self.root.after(100, self.process_output_queue)

    def save_generated_draft(self) -> None:
        draft = self.generated_draft()
        if not draft:
            messagebox.showerror("No rewritten text", "Run a rewrite first, or paste draft text into the rewritten draft pane.")
            return
        current_value = self.save_path_var.get().strip()
        destination: Path | None = None
        if current_value:
            destination = Path(current_value)
            if not destination.is_absolute():
                destination = (self.project_root / destination).resolve()
        else:
            suggested = suggested_story_output_path(
                self.project_root,
                title=self.title_var.get().strip(),
                scene_key=self.scene_key_var.get().strip(),
                mode=self.mode_var.get().strip() or "revision",
            )
            generated_story_output_dir(self.project_root).mkdir(parents=True, exist_ok=True)
            selected = filedialog.asksaveasfilename(
                parent=self.root,
                title="Save rewritten markdown",
                initialdir=str(suggested.parent),
                initialfile=suggested.name,
                defaultextension=".md",
                filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")],
            )
            if not selected:
                return
            destination = Path(selected)
        if destination.suffix.strip() == "":
            destination = destination.with_suffix(".md")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(draft + "\n", encoding="utf-8")
        self.save_path_var.set(relative_or_absolute_path(destination, self.project_root))
        self.status_var.set(f"Saved rewritten draft to {relative_or_absolute_path(destination, self.project_root)}.")
        self.append_console(
            f"[studio] Saved rewritten draft to {relative_or_absolute_path(destination, self.project_root)}\n"
        )

    def stop_process(self) -> None:
        if self.current_process is None:
            return
        self.append_console("\n[studio] Stopping the running command...\n")
        self.current_process.terminate()
        self.status_var.set("Stopping command...")

    def on_close(self) -> None:
        if self.current_process is not None:
            should_close = messagebox.askyesno(
                "Quit studio",
                "A command is still running. Stop it and close the studio?",
            )
            if not should_close:
                return
            try:
                self.current_process.terminate()
            except Exception:
                pass
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    StoryWriterStudioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
