from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import sys
import textwrap
import time

try:
    import msvcrt
except ImportError:  # pragma: no cover - Windows-only keyboard support
    msvcrt = None

from ..models import GameState
from ..ui.colors import ANSI_RE, colorize, rarity_color, rich_style_name, strip_ansi
from ..ui.rich_render import Columns, Console, Group, Live, Panel, RICH_AVAILABLE, Table, Text, box, render_rich_lines, text_from_ansi
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

    def rich_enabled(self) -> bool:
        return RICH_AVAILABLE and all(component is not None for component in (Group, Panel, Text, box))

    def should_use_rich_ui(self) -> bool:
        return self.rich_enabled() and bool(getattr(self, "_interactive_output", False))

    def rich_console_width(self) -> int:
        fallback = 108 if getattr(self, "_interactive_output", False) else 100
        try:
            return max(88, min(shutil.get_terminal_size((fallback, 30)).columns, 132))
        except OSError:
            return fallback

    def detected_terminal_width(self) -> int:
        fallback = 108 if getattr(self, "_interactive_output", False) else 100
        try:
            return max(1, shutil.get_terminal_size((fallback, 30)).columns)
        except OSError:
            return fallback

    def terminal_render_width(self, requested_width: int | None = None) -> int:
        requested = self.rich_console_width() if requested_width is None else requested_width
        try:
            requested = int(requested)
        except (TypeError, ValueError):
            requested = self.rich_console_width()
        terminal_width = self.detected_terminal_width()
        if terminal_width > 1:
            terminal_width -= 1
        return max(1, min(max(1, requested), terminal_width))

    def safe_rich_render_width(self) -> int:
        return self.terminal_render_width(self.rich_console_width())

    def plain_text_wrap_width(self) -> int:
        terminal_width = self.detected_terminal_width()
        if terminal_width > 1:
            terminal_width -= 1
        return max(1, min(88, terminal_width))

    def wrap_plain_paragraph(self, text: str) -> str:
        return textwrap.fill(
            text,
            width=self.plain_text_wrap_width(),
            break_long_words=False,
            break_on_hyphens=False,
        )

    def dialogue_terminal_lines(self, speaker_name: str, text: str) -> list[str]:
        prefix = f'{speaker_name}: "'
        wrap_width = self.plain_text_wrap_width()
        prefix_width = len(strip_ansi(prefix))
        body_width = max(1, wrap_width - prefix_width - 1)
        body_lines = textwrap.wrap(
            text,
            width=body_width,
            break_long_words=False,
            break_on_hyphens=False,
        ) or [""]
        indent = " " * min(prefix_width, max(0, wrap_width - 1))
        lines = [f"{prefix}{body_lines[0]}", *(f"{indent}{line}" for line in body_lines[1:])]
        lines[-1] = f'{lines[-1]}"'
        return lines

    def emit_rich(self, renderable, *, width: int | None = None) -> bool:
        if not self.rich_enabled():
            return False
        render_width = self.terminal_render_width(width)
        rendered_lines = render_rich_lines(
            renderable,
            width=render_width,
            force_terminal=getattr(self, "_interactive_output", False),
        )
        if not rendered_lines:
            return False
        for line in rendered_lines:
            self.output_fn(line)
        return True

    def rich_panel_row_renderable(
        self,
        panels: list[object],
        *,
        ratios: list[int] | None = None,
        padding: tuple[int, int] = (0, 1),
    ):
        if not panels or Table is None:
            return None
        resolved_ratios = ratios or [1] * len(panels)
        if len(resolved_ratios) != len(panels):
            raise ValueError("Panel ratios must match the number of panels.")
        row = Table.grid(expand=True, padding=padding)
        for ratio in resolved_ratios:
            row.add_column(ratio=ratio, vertical="top")
        row.add_row(*panels)
        return row

    def emit_rich_panel_row(
        self,
        panels: list[object],
        *,
        ratios: list[int] | None = None,
        width: int | None = None,
        padding: tuple[int, int] = (0, 1),
    ) -> bool:
        renderable = self.rich_panel_row_renderable(panels, ratios=ratios, padding=padding)
        if renderable is None:
            return False
        return self.emit_rich(renderable, width=width or self.safe_rich_render_width())

    def begin_keyboard_choice_session(self) -> bool:
        show_instructions = not bool(getattr(self, "_keyboard_choice_instructions_seen", False))
        self._keyboard_choice_instructions_seen = True
        return show_instructions

    def keyboard_choice_menu_width(self) -> int:
        return self.terminal_render_width(min(120, self.rich_console_width()))

    def keyboard_choice_key_ready(self) -> bool:
        reader = getattr(self, "read_keyboard_choice_key")
        if getattr(reader, "__func__", None) is not GameIOMixin.read_keyboard_choice_key:
            return True
        if msvcrt is None:
            return True
        try:
            return bool(msvcrt.kbhit())
        except Exception:
            return True

    def refresh_keyboard_choice_live_if_resized(self, live, console, renderable_factory, width_factory) -> bool:
        next_width = width_factory()
        try:
            current_width = int(console.width)
        except (TypeError, ValueError):
            current_width = next_width
        if next_width == current_width:
            return False
        live_render = getattr(live, "_live_render", None)
        previous_shape = getattr(live_render, "_shape", None)
        if live_render is not None and previous_shape is not None and next_width < current_width:
            previous_width, previous_height = previous_shape
            previous_width = max(1, int(max(previous_width, current_width)))
            previous_height = max(1, int(previous_height))
            reflow_factor = max(1, (previous_width + max(1, next_width) - 1) // max(1, next_width))
            live_render._shape = (max(1, next_width), previous_height * reflow_factor)
        console.width = next_width
        live.update(renderable_factory(), refresh=True)
        return True

    def read_keyboard_choice_key_with_resize_poll(self, live, console, renderable_factory, width_factory) -> tuple[str, str | None]:
        while True:
            self.refresh_keyboard_choice_live_if_resized(live, console, renderable_factory, width_factory)
            if self.keyboard_choice_key_ready():
                return self.read_keyboard_choice_key()
            time.sleep(float(getattr(self, "_keyboard_choice_resize_poll_seconds", 0.05)))

    def rich_text(self, text: object, color: str | None = None, *, bold: bool = False, dim: bool = False):
        content = strip_ansi(str(text))
        if not self.rich_enabled():
            return content
        style_bits: list[str] = []
        if color is not None:
            style_bits.append(rich_style_name(color))
        if bold:
            style_bits.append("bold")
        if dim:
            style_bits.append("dim")
        style = " ".join(style_bits) or None
        return Text(content, style=style)

    def rich_from_ansi(self, text: str):
        if not self.rich_enabled():
            return strip_ansi(text)
        return text_from_ansi(text)

    def rich_title_screen_enabled(self) -> bool:
        return self.rich_enabled() and Columns is not None and Table is not None

    def title_screen_save_summary(self) -> tuple[str, str]:
        saves = self.loadable_save_paths()
        if not saves:
            return ("No save files yet", "Forge a new hero to create your first journal entry.")
        save_label = "save" if len(saves) == 1 else "saves"
        return (f"{len(saves)} {save_label} available", f"Latest: {self.save_display_label(saves[0])}")

    def title_screen_audio_summary(self) -> str:
        sound_label = "On" if getattr(self, "sound_effects_enabled", False) else "Off"
        music_ready = bool(getattr(self, "_music_assets_ready", False))
        if not music_ready:
            music_label = "Unavailable"
        else:
            music_label = "On" if getattr(self, "music_enabled", False) else "Off"
        return f"SFX {sound_label} | Music {music_label}"

    def title_screen_presentation_summary(self) -> str:
        presentation = "On" if getattr(self, "_animations_and_delays_preference", False) else "Off"
        dice_mode_label = (
            self.dice_animation_mode_label()
            if callable(getattr(self, "dice_animation_mode_label", None))
            else ("On" if getattr(self, "_dice_animations_preference", False) else "Off")
        )
        typed = "On" if getattr(self, "_typed_dialogue_preference", getattr(self, "type_dialogue", False)) else "Off"
        return f"Animations {presentation} | Dice {dice_mode_label} | Typed text {typed}"

    def render_title_screen(
        self,
        title: str,
        subtitle: str,
        intro_text: str,
        options: list[str],
        option_details: dict[str, str] | None = None,
    ) -> None:
        option_details = option_details or {}
        self.output_fn("")
        save_summary, save_detail = self.title_screen_save_summary()
        campaign_summary = "Acts I and II are playable now, with later acts scaffolded for expansion."

        if self.rich_title_screen_enabled():
            header = Text(justify="center")
            header.append(f"{title}\n", style="bold bright_yellow")
            header.append(f"{subtitle}\n", style="bold bright_cyan")
            header.append("Frontier roads. Hard bargains. Consequences that travel.\n", style="white")
            header.append(intro_text, style="dim")

            status_table = Table.grid(expand=True, padding=(0, 1))
            status_table.add_column(style="bold bright_yellow", ratio=1)
            status_table.add_column(ratio=3)
            status_table.add_row("Campaign", campaign_summary)
            status_table.add_row("Saves", save_summary)
            status_table.add_row("", save_detail)
            status_table.add_row("Audio", self.title_screen_audio_summary())
            status_table.add_row("Presentation", self.title_screen_presentation_summary())

            options_table = Table.grid(expand=True, padding=(0, 1))
            options_table.add_column(style="bold bright_yellow", width=3)
            options_table.add_column(style="bold")
            options_table.add_column(style="dim", ratio=1)
            for index, option in enumerate(options, start=1):
                options_table.add_row(f"{index}.", strip_ansi(option), option_details.get(option, ""))

            rendered = self.emit_rich(
                Group(
                    Panel(
                        header,
                        border_style=rich_style_name("light_yellow"),
                        box=box.DOUBLE,
                        padding=(1, 2),
                        title=self.rich_text("Roads That Remember", "light_yellow", bold=True),
                    ),
                    Columns(
                        [
                            Panel(
                                status_table,
                                title=self.rich_text("Campaign Ledger", "light_aqua", bold=True),
                                border_style=rich_style_name("light_aqua"),
                                box=box.ROUNDED,
                                padding=(0, 1),
                            ),
                            Panel(
                                options_table,
                                title=self.rich_text("What Would You Like To Do?", "light_green", bold=True),
                                border_style=rich_style_name("light_green"),
                                box=box.ROUNDED,
                                padding=(0, 1),
                            ),
                        ],
                        expand=True,
                        equal=False,
                    ),
                ),
                width=max(108, self.rich_console_width()),
            )
            if rendered:
                return

        self.output_fn(f"=== {title} ===")
        self.output_fn(subtitle)
        self.say("Frontier roads. Hard bargains. Consequences that travel.")
        self.say(intro_text)
        self.say(f"Campaign: {campaign_summary}")
        self.say(f"Saves: {save_summary}")
        self.say(save_detail)
        self.say(f"Audio: {self.title_screen_audio_summary()}")
        self.say(f"Presentation: {self.title_screen_presentation_summary()}")
        self.output_fn("")
        self.say("What would you like to do?")
        self.render_choice_options(options, staggered=False)

    def choose_title_menu(
        self,
        title: str,
        subtitle: str,
        intro_text: str,
        options: list[str],
        *,
        option_details: dict[str, str] | None = None,
    ) -> int:
        while True:
            self.render_title_screen(title, subtitle, intro_text, options, option_details)
            raw = self.read_input("> ").strip()
            lowered = raw.lower()
            if lowered == "quit":
                if self.confirm("Quit the program and close the main menu?"):
                    from .base import QuitProgram

                    raise QuitProgram()
                self.say("You remain at the main menu.")
                continue
            if lowered in {"load", "saves", "save files"}:
                if self.open_save_files_menu():
                    from .base import ResumeLoadedGame

                    raise ResumeLoadedGame()
                continue
            if raw.isdigit():
                value = int(raw)
                if 1 <= value <= len(options):
                    return value
            self.say("Please enter a listed number.")

    def choose(
        self,
        prompt: str,
        options: list[str],
        *,
        allow_meta: bool = True,
        show_hud: bool = True,
        sticky_trailing_options: int = 0,
    ) -> int:
        return self.choose_with_display_mode(
            prompt,
            options,
            allow_meta=allow_meta,
            staggered=False,
            show_hud=show_hud,
            sticky_trailing_options=sticky_trailing_options,
        )

    def scenario_choice(
        self,
        prompt: str,
        options: list[str],
        *,
        allow_meta: bool = True,
        show_hud: bool = True,
        sticky_trailing_options: int = 0,
    ) -> int:
        return self.choose_with_display_mode(
            prompt,
            options,
            allow_meta=allow_meta,
            staggered=True,
            show_hud=show_hud,
            sticky_trailing_options=sticky_trailing_options,
        )

    def keyboard_choice_menu_supported(self) -> bool:
        if not self.should_use_rich_ui():
            return False
        if Console is None or Live is None or msvcrt is None:
            return False
        try:
            stdin_ready = not hasattr(sys.stdin, "isatty") or sys.stdin.isatty()
            stdout_ready = not hasattr(sys.stdout, "isatty") or sys.stdout.isatty()
        except Exception:
            return False
        return bool(stdin_ready and stdout_ready)

    def should_use_keyboard_choice_menu(self) -> bool:
        return self.keyboard_choice_menu_supported()

    def keyboard_choice_menu_title(self) -> str:
        if self.state is None:
            return "Choice Menu"
        current_scene = str(self.state.current_scene)
        scene_label = getattr(self, "SCENE_LABELS", {}).get(current_scene)
        if scene_label:
            return scene_label
        return "Choice Menu"

    def build_keyboard_choice_menu(
        self,
        prompt: str,
        options: list[str],
        *,
        title: str,
        selected_index: int,
        typed_buffer: str,
        feedback: str | None,
        show_instructions: bool,
    ):
        prompt_block = Text()
        prompt_block.append(prompt, style="bold bright_white")
        if show_instructions:
            prompt_block.append("\n", style="dim")
            prompt_block.append("Arrows move. Enter confirms. ", style="dim")
            if len(options) <= 9:
                prompt_block.append("1-9 jumps. ", style="dim")
            prompt_block.append("Type a number or command. Esc clears.", style="dim")

        option_table = Table.grid(expand=True, padding=(0, 0))
        option_table.add_column(width=2)
        option_table.add_column(width=3)
        option_table.add_column(ratio=1)
        for index, option in enumerate(options, start=1):
            active = index - 1 == selected_index
            marker = self.rich_text("> ", "light_green", bold=True) if active else self.rich_text("  ", dim=True)
            number = self.rich_text(f"{index}.", "light_yellow" if active else "white", bold=active)
            label = self.rich_from_ansi(self.format_option_text(option))
            if Text is not None and isinstance(label, Text) and active:
                label.stylize("bold")
            row_style = "on rgb(28,36,46)" if active else None
            option_table.add_row(marker, number, label, style=row_style)

        if typed_buffer:
            input_line = self.rich_text(f"> {typed_buffer}_", "light_green", bold=True)
        else:
            input_line = self.rich_text("> ", "white")

        footer_items = [input_line]
        if feedback:
            footer_items.append(self.rich_text(feedback, "light_red"))

        return Panel(
            Group(
                prompt_block,
                self.rich_text("", dim=True),
                option_table,
                self.rich_text("", dim=True),
                *footer_items,
            ),
            title=self.rich_text(title, "light_yellow", bold=True),
            subtitle=self.rich_text("Keyboard Choice Menu", "light_aqua", bold=True),
            border_style=rich_style_name("light_green"),
            box=box.ROUNDED,
            padding=(0, 1),
        )

    def read_keyboard_choice_wchar(self) -> str:
        assert msvcrt is not None
        try:
            key = msvcrt.getwch()
        except KeyboardInterrupt as exc:
            self.output_fn("")
            from .base import GameInterrupted

            raise GameInterrupted() from exc
        if key == "\x03":
            self.output_fn("")
            from .base import GameInterrupted

            raise GameInterrupted()
        return key

    def read_keyboard_choice_key(self) -> tuple[str, str | None]:
        assert msvcrt is not None
        key = self.read_keyboard_choice_wchar()
        if key in {"\x00", "\xe0"}:
            extended = self.read_keyboard_choice_wchar()
            keymap = {
                "H": "up",
                "P": "down",
            }
            return (keymap.get(extended, "noop"), None)
        if key == "\r":
            return ("enter", None)
        if key == "\x08":
            return ("backspace", None)
        if key == "\x1b":
            return ("escape", None)
        if key == "\t":
            return ("down", None)
        if key.isprintable():
            return ("char", key)
        return ("noop", None)

    def run_keyboard_choice_menu(
        self,
        prompt: str,
        options: list[str],
        *,
        title: str | None = None,
    ) -> int | None:
        if not options or not self.should_use_keyboard_choice_menu():
            return None

        selected_index = 0
        typed_buffer = ""
        feedback: str | None = None
        menu_width = self.keyboard_choice_menu_width()
        console = Console(
            force_terminal=True,
            color_system="truecolor",
            legacy_windows=False,
            highlight=False,
            width=menu_width,
        )
        resolved_title = title or self.keyboard_choice_menu_title()
        show_instructions = self.begin_keyboard_choice_session()

        while True:
            submitted_text: str | None = None
            renderable_factory = lambda: self.build_keyboard_choice_menu(
                prompt,
                options,
                title=resolved_title,
                selected_index=selected_index,
                typed_buffer=typed_buffer,
                feedback=feedback,
                show_instructions=show_instructions,
            )
            with Live(
                renderable_factory(),
                console=console,
                transient=True,
                auto_refresh=False,
            ) as live:
                while True:
                    action, payload = self.read_keyboard_choice_key_with_resize_poll(
                        live,
                        console,
                        renderable_factory,
                        self.keyboard_choice_menu_width,
                    )
                    hide_instructions_after_update = show_instructions
                    if action == "up":
                        selected_index = (selected_index - 1) % len(options)
                        feedback = None
                    elif action == "down":
                        selected_index = (selected_index + 1) % len(options)
                        feedback = None
                    elif action == "backspace":
                        typed_buffer = typed_buffer[:-1]
                        feedback = None
                    elif action == "escape":
                        typed_buffer = ""
                        feedback = None
                    elif action == "char" and payload is not None:
                        if not typed_buffer and len(options) <= 9 and payload.isdigit():
                            value = int(payload)
                            if 1 <= value <= len(options):
                                return value
                        typed_buffer += payload
                        feedback = None
                    elif action == "enter":
                        if typed_buffer.strip():
                            submitted_text = typed_buffer.strip()
                            typed_buffer = ""
                            show_instructions = False
                            break
                        return selected_index + 1
                    if hide_instructions_after_update:
                        show_instructions = False
                    live.update(renderable_factory(), refresh=True)

            if submitted_text is None:
                continue
            if submitted_text.isdigit():
                value = int(submitted_text)
                if 1 <= value <= len(options):
                    return value
            if self.handle_meta_command(submitted_text):
                feedback = None
                continue
            feedback = "Type a listed number, use the arrows, or enter a global command."

    def render_choice_options(self, options: list[str], *, staggered: bool) -> None:
        pause = getattr(self, "pause_for_option_reveal", None)
        for index, option in enumerate(options, start=1):
            self.output_fn(f"  {index}. {self.format_option_text(option)}")
            if staggered and index < len(options) and callable(pause):
                pause()

    def compact_hud_scene_key(self) -> tuple[int, str] | None:
        if self.state is None or getattr(self, "_in_combat", False):
            return None
        return (id(self.state), str(self.state.current_scene))

    def should_render_compact_hud(self) -> bool:
        return self.compact_hud_scene_key() is not None

    def request_compact_hud(self) -> None:
        self._compact_hud_requested = True

    def hud_act_label(self) -> str:
        assert self.state is not None
        act_labels = getattr(self, "ACT_LABELS", {})
        return f"Act {act_labels.get(self.state.current_act, self.state.current_act)}"

    def hud_location_label(self) -> str:
        assert self.state is not None
        scene_labels = getattr(self, "SCENE_LABELS", {})
        current_scene = str(self.state.current_scene)
        return scene_labels.get(current_scene, current_scene.replace("_", " ").title())

    def hud_objective_label(self) -> str:
        assert self.state is not None
        refresh_quest_statuses = getattr(self, "refresh_quest_statuses", None)
        if callable(refresh_quest_statuses):
            refresh_quest_statuses(announce=False)
        ready_quests = getattr(self, "quest_entries_by_status", lambda status: [])("ready_to_turn_in")
        if ready_quests:
            return f"Turn in {ready_quests[0][0].title}"
        active_quests = getattr(self, "quest_entries_by_status", lambda status: [])("active")
        quest_focused_scenes = set(getattr(self, "HUD_QUEST_FOCUSED_SCENES", set()))
        if self.state.current_scene in quest_focused_scenes and active_quests:
            return active_quests[0][0].title
        scene_objectives = getattr(self, "SCENE_OBJECTIVES", {})
        current_scene = str(self.state.current_scene)
        if current_scene in scene_objectives:
            return str(scene_objectives[current_scene])
        if active_quests:
            return active_quests[0][0].title
        return "Press on."

    def hud_short_name(self, member) -> str:
        return str(getattr(member, "name", "")).split()[0] or str(getattr(member, "name", "Party"))

    def hud_member_health_text(self, member) -> str:
        if getattr(member, "dead", False):
            return self.style_text("DEAD", "light_red")
        if getattr(member, "current_hp", 0) <= 0:
            return self.style_text("DOWN", "light_red")
        health = f"{member.current_hp}/{member.max_hp}"
        styled = self.style_text(health, self.health_bar_color(member.current_hp, member.max_hp))
        if getattr(member, "temp_hp", 0):
            styled += self.style_text(f"+{member.temp_hp}t", "light_aqua")
        return styled

    def hud_party_summary(self) -> str:
        assert self.state is not None
        return " | ".join(
            f"{self.hud_short_name(member)} {self.hud_member_health_text(member)}"
            for member in self.state.party_members()
        )

    def render_compact_hud(self) -> None:
        scene_key = self.compact_hud_scene_key()
        if scene_key is None:
            return
        objective = textwrap.shorten(self.hud_objective_label(), width=40, placeholder="...")
        header_line = (
            f"{self.style_text(f'[{self.hud_act_label()}]', 'light_yellow')} "
            f"{self.style_text(self.hud_location_label(), 'light_aqua')} | "
            f"{self.style_text('Objective:', 'light_yellow')} {objective}"
        )
        resources_line = (
            f"{self.style_text('Resources:', 'light_yellow')} {self.state.gold} gp | "
            f"Short rests: {self.state.short_rests_remaining} | "
            f"Carry: {self.current_inventory_weight():.1f}/{self.carrying_capacity()} lb"
        )
        party_line = f"{self.style_text('Party:', 'light_yellow')} {self.hud_party_summary()}"
        if not self.emit_rich(
            Panel(
                Group(
                    self.rich_from_ansi(header_line),
                    self.rich_from_ansi(resources_line),
                    self.rich_from_ansi(party_line),
                ),
                title=self.rich_text("Travel Ledger", "light_yellow", bold=True),
                border_style=rich_style_name("light_yellow"),
                box=box.ROUNDED,
                padding=(0, 1),
            )
        ):
            self.output_fn(header_line)
            self.output_fn(resources_line)
            self.output_fn(party_line)
        self.output_fn("")
        self._compact_hud_last_scene_key = scene_key

    def maybe_render_compact_hud(self, *, show_hud: bool) -> bool:
        if not show_hud:
            return False
        if not getattr(self, "_compact_hud_requested", False):
            return False
        scene_key = self.compact_hud_scene_key()
        if scene_key is None:
            self._compact_hud_requested = False
            return False
        self.render_compact_hud()
        self._compact_hud_requested = False
        return True

    def replay_prompt_context(self, lines: tuple[str, ...]) -> None:
        for line in lines:
            self.output_fn(line)

    def choose_with_display_mode(
        self,
        prompt: str,
        options: list[str],
        *,
        allow_meta: bool = True,
        staggered: bool = False,
        show_hud: bool = True,
        sticky_trailing_options: int = 0,
    ) -> int:
        if not options:
            raise ValueError("Choice lists must contain at least one option.")
        prompt_context_lines = tuple(getattr(self, "_latest_narration_lines", ()))
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
                if self.maybe_render_compact_hud(show_hud=show_hud) and prompt_context_lines:
                    self.replay_prompt_context(prompt_context_lines)
                paged_prompt = f"{prompt} (page {page + 1})"
                if self.should_use_keyboard_choice_menu():
                    selected = self.run_keyboard_choice_menu(paged_prompt, labels)
                    if selected is None:
                        continue
                    if selected in nav_map:
                        page = page - 1 if nav_map[selected] == "prev" else page + 1
                        continue
                    if selected in sticky_map:
                        return sticky_map[selected]
                    if 1 <= selected <= len(visible):
                        return start + selected
                    self.say("Please enter a listed number.")
                    continue
                self.say(paged_prompt)
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
            if self.maybe_render_compact_hud(show_hud=show_hud) and prompt_context_lines:
                self.replay_prompt_context(prompt_context_lines)
            if self.should_use_keyboard_choice_menu():
                selected = self.run_keyboard_choice_menu(prompt, options)
                if selected is not None:
                    return selected
                continue
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
        return self.choose(prompt, ["Yes", "No"], allow_meta=False, show_hud=False) == 1

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
        self.maybe_render_compact_hud(show_hud=True)

    def say(self, text: str, *, typed: bool = False) -> None:
        if not text:
            self.output_fn("")
            return
        narrator = getattr(self, "typewrite_narration", None)
        rendered_lines: list[str] = []
        for paragraph in text.split("\n"):
            if not paragraph.strip():
                self.output_fn("")
                continue
            if ANSI_RE.search(paragraph):
                self.output_fn(paragraph)
                rendered_lines.append(paragraph)
                continue
            wrapped = self.wrap_plain_paragraph(paragraph)
            if typed and callable(narrator) and getattr(self, "type_dialogue", False):
                narrator(wrapped)
            else:
                self.output_fn(wrapped)
            rendered_lines.append(wrapped)
        if rendered_lines:
            self._latest_narration_lines = rendered_lines

    def inline_save(self) -> None:
        if self.state is None:
            self.say("There is no active game to save.")
            return
        slot_name = self.ask_text("Save slot name")
        path = self.save_game(slot_name=slot_name)
        self.say(f"Saved to {path.name}.")

    def save_game(self, *, slot_name: str) -> Path:
        assert self.state is not None
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", slot_name).strip("_") or "save"
        path = self.save_dir / f"{safe_name}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(self.state.to_dict(), handle, indent=2)
        return path

    def is_autosave_path(self, path: Path) -> bool:
        return path.stem.startswith(getattr(self, "AUTOSAVE_PREFIX", "autosave__"))

    def autosave_paths(self) -> list[Path]:
        settings_path = getattr(self, "settings_path", None)
        candidates = [
            path
            for path in self.save_dir.glob(f"{getattr(self, 'AUTOSAVE_PREFIX', 'autosave__')}*.json")
            if path != settings_path
        ]
        return sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)

    def autosave_slot_name(self, label: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_label = re.sub(r"[^A-Za-z0-9_-]+", "_", label).strip("_") or "autosave"
        return f"{getattr(self, 'AUTOSAVE_PREFIX', 'autosave__')}{stamp}_{safe_label}"

    def prune_old_autosaves(self) -> None:
        limit = int(getattr(self, "AUTOSAVE_LIMIT", 15))
        for stale_path in self.autosave_paths()[limit:]:
            try:
                stale_path.unlink(missing_ok=True)
            except OSError:
                continue

    def create_autosave(self, *, label: str) -> Path | None:
        if self.state is None or not getattr(self, "autosaves_enabled", True):
            return None
        path = self.save_game(slot_name=self.autosave_slot_name(label))
        self.prune_old_autosaves()
        return path

    def loadable_save_paths(self) -> list[Path]:
        settings_path = getattr(self, "settings_path", None)
        saves = sorted(
            (path for path in self.save_dir.glob("*.json") if path != settings_path),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        manual_saves = [path for path in saves if not self.is_autosave_path(path)]
        autosaves = [path for path in saves if self.is_autosave_path(path)]
        return [*manual_saves, *autosaves]

    def save_display_label(self, path: Path) -> str:
        if not self.is_autosave_path(path):
            return path.stem
        prefix = getattr(self, "AUTOSAVE_PREFIX", "autosave__")
        stem = path.stem[len(prefix):]
        match = re.match(r"^(?P<date>\d{8})_(?P<time>\d{6})_(?P<micro>\d{6})_(?P<label>.+)$", stem)
        if match is None:
            return f"[Autosave] {stem.replace('_', ' ')}"
        date_code = match.group("date")
        time_code = match.group("time")
        label = match.group("label").replace("_", " ").strip() or "autosave"
        timestamp = (
            f"{date_code[:4]}-{date_code[4:6]}-{date_code[6:8]} "
            f"{time_code[:2]}:{time_code[2:4]}:{time_code[4:6]}"
        )
        return f"[Autosave] {label.title()} | {timestamp}"

    def load_save_path(self, path: Path) -> None:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        self.state = GameState.from_dict(data)
        self.ensure_state_integrity()
        self._compact_hud_last_scene_key = None
        refresh_scene_music = getattr(self, "refresh_scene_music", None)
        if callable(refresh_scene_music):
            refresh_scene_music()
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
