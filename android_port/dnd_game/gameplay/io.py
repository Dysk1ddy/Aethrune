from __future__ import annotations

import json
from pathlib import Path
import re
import textwrap

from ..models import GameState
from ..ui.colors import ANSI_RE, colorize, rarity_color
from .constants import MENU_PAGE_SIZE


class GameIOMixin:
    def style_text(self, text: object, color: str) -> str:
        return colorize(text, color)

    def style_damage(self, amount: int) -> str:
        return self.style_text(amount, "light_red")

    def style_healing(self, amount: int) -> str:
        return self.style_text(amount, "light_green")

    def style_skill_label(self, skill: str) -> str:
        return self.style_text(skill, "light_yellow")

    def style_rarity_text(self, text: str, rarity: str) -> str:
        return self.style_text(text, rarity_color(rarity))

    def style_name(self, subject) -> str:
        if not hasattr(subject, "name"):
            return str(subject)
        name = subject.name
        if self.state is not None and subject is self.state.player:
            return self.style_text(name, "aqua")
        tags = set(getattr(subject, "tags", []))
        if "enemy" in tags:
            return self.style_text(name, "light_red")
        if getattr(subject, "companion_id", "") or "companion" in tags:
            return self.style_text(name, "light_aqua")
        return name

    def format_option_text(self, option: str) -> str:
        match = re.match(r"^(\[[^\]]+\])(\s*)(.*)$", option)
        if match is None:
            return option
        tag, spacing, rest = match.groups()
        return f"{self.style_text(tag, 'light_yellow')}{spacing}{rest}"

    def choose(
        self,
        prompt: str,
        options: list[str],
        *,
        allow_meta: bool = True,
        sticky_trailing_options: int = 0,
    ) -> int:
        clear_pending_story_check_choice_attempt = getattr(self, "clear_pending_story_check_choice_attempt", None)
        if callable(clear_pending_story_check_choice_attempt):
            clear_pending_story_check_choice_attempt()
        return self.choose_with_display_mode(
            prompt,
            options,
            allow_meta=allow_meta,
            staggered=False,
            sticky_trailing_options=sticky_trailing_options,
        )

    def scenario_choice(
        self,
        prompt: str,
        options: list[str],
        *,
        allow_meta: bool = True,
        sticky_trailing_options: int = 0,
    ) -> int:
        clear_pending_story_check_choice_attempt = getattr(self, "clear_pending_story_check_choice_attempt", None)
        if callable(clear_pending_story_check_choice_attempt):
            clear_pending_story_check_choice_attempt()
        indexed_options = list(enumerate(options, start=1))
        story_check_choice_attempted = getattr(self, "story_check_choice_attempted", None)
        if callable(story_check_choice_attempted):
            available_options = [
                (index, option)
                for index, option in indexed_options
                if not story_check_choice_attempted(prompt, option)
            ]
            if available_options:
                indexed_options = available_options
        visible_options = [option for _, option in indexed_options]
        choice = self.choose_with_display_mode(
            prompt,
            visible_options,
            allow_meta=allow_meta,
            staggered=True,
            sticky_trailing_options=sticky_trailing_options,
        )
        original_index, selected_option = indexed_options[choice - 1]
        queue_story_check_choice_attempt = getattr(self, "queue_story_check_choice_attempt", None)
        if callable(queue_story_check_choice_attempt):
            queue_story_check_choice_attempt(prompt, selected_option)
        return original_index

    def render_choice_options(self, options: list[str], *, staggered: bool) -> None:
        pause = getattr(self, "pause_for_option_reveal", None)
        for index, option in enumerate(options, start=1):
            self.output_fn(f"  {index}. {self.format_option_text(option)}")
            if staggered and index < len(options) and callable(pause):
                pause()

    def choose_with_display_mode(
        self,
        prompt: str,
        options: list[str],
        *,
        allow_meta: bool = True,
        staggered: bool = False,
        sticky_trailing_options: int = 0,
    ) -> int:
        if not options:
            raise ValueError("Choice lists must contain at least one option.")
        sticky_count = max(0, min(sticky_trailing_options, len(options) - 1))
        sticky_options = options[-sticky_count:] if sticky_count else []
        paged_options = options[:-sticky_count] if sticky_count else options
        page_size = max(1, MENU_PAGE_SIZE - sticky_count)
        if len(paged_options) > page_size:
            page = 0
            while True:
                start = page * page_size
                visible = paged_options[start : start + page_size]
                labels = [*visible, *sticky_options]
                nav_map: dict[int, str] = {}
                sticky_map = {
                    len(visible) + offset + 1: len(paged_options) + offset + 1
                    for offset in range(len(sticky_options))
                }
                if page > 0:
                    labels.append("Previous page")
                    nav_map[len(labels)] = "prev"
                if start + page_size < len(paged_options):
                    labels.append("Next page")
                    nav_map[len(labels)] = "next"
                self.output_fn("")
                self.say(f"{prompt} (page {page + 1})")
                self.render_choice_options(labels, staggered=staggered)
                raw = self.read_input("> ").strip()
                if self.handle_meta_command(raw):
                    continue
                if raw.isdigit():
                    value = int(raw)
                    if value in nav_map:
                        page = page - 1 if nav_map[value] == "prev" else page + 1
                        continue
                    if value in sticky_map:
                        return sticky_map[value]
                    if 1 <= value <= len(visible):
                        return start + value
                self.say("Please enter a listed number.")
        while True:
            self.output_fn("")
            self.say(prompt)
            self.render_choice_options(options, staggered=staggered)
            raw = self.read_input("> ").strip()
            if self.handle_meta_command(raw):
                continue
            if raw.isdigit():
                value = int(raw)
                if 1 <= value <= len(options):
                    return value
            self.say("Please enter a listed number.")

    def confirm(self, prompt: str) -> bool:
        return self.choose(prompt, ["Yes", "No"], allow_meta=False) == 1

    def ask_text(self, prompt: str) -> str:
        while True:
            self.output_fn("")
            value = self.read_input(f"{prompt}: ").strip()
            if self.handle_meta_command(value):
                continue
            if value:
                return value
            self.say("Please enter a value.")

    def banner(self, title: str) -> None:
        self.output_fn("")
        self.output_fn(f"=== {title} ===")

    def say(self, text: str, *, typed: bool = False) -> None:
        if not text:
            self.output_fn("")
            return
        narrator = getattr(self, "typewrite_narration", None)
        for paragraph in text.split("\n"):
            if not paragraph.strip():
                self.output_fn("")
                continue
            if ANSI_RE.search(paragraph):
                self.output_fn(paragraph)
                continue
            wrapped = textwrap.fill(paragraph, width=88)
            if typed and callable(narrator) and getattr(self, "type_dialogue", False):
                narrator(wrapped)
            else:
                self.output_fn(wrapped)

    def inline_save(self) -> None:
        if self.state is None:
            self.say("There is no active game to save.")
            return
        slot_name = self.ask_text("Save slot name")
        path = self.save_path_for_slot_name(slot_name)
        if path.exists() and not self.confirm(f"Overwrite {path.name}?"):
            self.say("The existing save stays untouched.")
            return
        path = self.save_game(slot_name=slot_name)
        self.say(f"Saved to {path.name}.")

    def save_path_for_slot_name(self, slot_name: str) -> Path:
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", slot_name).strip("_") or "save"
        return self.save_dir / f"{safe_name}.json"

    def save_game(self, *, slot_name: str) -> Path:
        assert self.state is not None
        path = self.save_path_for_slot_name(slot_name)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(self.state.to_dict(), handle, indent=2)
        return path

    def loadable_save_paths(self) -> list[Path]:
        return sorted(self.save_dir.glob("*.json"))

    def save_display_label(self, path: Path) -> str:
        return path.stem

    def load_save_path(self, path: Path) -> None:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        self.state = GameState.from_dict(data)
        self.ensure_state_integrity()
        self.say(f"Loaded {self.save_display_label(path)}.")

    def delete_save_path(self, path: Path) -> bool:
        label = self.save_display_label(path)
        if not self.confirm(f"Delete {label}? This cannot be undone."):
            self.say("The save file remains.")
            return False
        try:
            path.unlink()
        except OSError:
            self.say(f"Could not delete {label}.")
            return False
        self.say(f"Deleted {label}.")
        return True

    def open_save_files_menu(self) -> bool:
        while True:
            saves = self.loadable_save_paths()
            if not saves:
                self.say("No save files were found yet.")
                return False
            choice = self.choose(
                "Save Files",
                [self.save_display_label(path) for path in saves] + ["Back"],
                allow_meta=False,
                sticky_trailing_options=1,
            )
            if choice == len(saves) + 1:
                return False
            selected = saves[choice - 1]
            label = self.save_display_label(selected)
            action = self.choose(
                f"{label}",
                [
                    "Load this save",
                    "Delete this save",
                    "Back",
                ],
                allow_meta=False,
            )
            if action == 1:
                self.load_save_path(selected)
                return True
            if action == 2:
                self.delete_save_path(selected)

    def load_from_menu(self) -> bool:
        return self.open_save_files_menu()
