from __future__ import annotations

from pathlib import Path
from queue import Queue
from threading import Thread
import traceback

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from dnd_game.game import TextDnDGame
from dnd_game.gameplay.constants import MENU_PAGE_SIZE
from dnd_game.ui.colors import strip_ansi


class WrappedLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(width=self._sync_text_size, texture_size=self._sync_height)
        self._sync_text_size()
        self._sync_height()

    def _sync_text_size(self, *_args) -> None:
        self.text_size = (max(0, self.width - dp(12)), None)

    def _sync_height(self, *_args) -> None:
        self.height = max(dp(32), self.texture_size[1] + dp(12))


class WrappedButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(width=self._sync_text_size, texture_size=self._sync_height)
        self._sync_text_size()
        self._sync_height()

    def _sync_text_size(self, *_args) -> None:
        self.text_size = (max(0, self.width - dp(24)), None)

    def _sync_height(self, *_args) -> None:
        self.height = max(dp(54), self.texture_size[1] + dp(24))


class MobileGameBridge:
    def __init__(self, screen: "GameScreen"):
        self.screen = screen
        self._responses: Queue[str] = Queue()
        self._worker: Thread | None = None
        self.waiting_for_input = False

    def start(self) -> None:
        if self._worker is not None:
            return
        self._worker = Thread(target=self._run_game, daemon=True)
        self._worker.start()

    def _run_game(self) -> None:
        app = App.get_running_app()
        save_dir = Path(app.user_data_dir) / "saves"
        game = AndroidTextDnDGame(self, save_dir=save_dir)
        try:
            game.run()
        except Exception:
            self.post_output("")
            self.post_output("The Android port hit an unexpected error.")
            for line in traceback.format_exc().splitlines():
                self.post_output(line)
        finally:
            self.finish()

    def finish(self) -> None:
        Clock.schedule_once(lambda _dt: self.screen.finish_session())

    def post_output(self, text: object = "") -> None:
        clean = strip_ansi(str(text))
        Clock.schedule_once(lambda _dt: self.screen.append_log(clean))

    def request_choice(self, prompt: str, options: list[str]) -> str:
        self.waiting_for_input = True
        Clock.schedule_once(lambda _dt: self.screen.show_choice_prompt(prompt, options))
        return self._responses.get()

    def request_text(self, prompt: str) -> str:
        self.waiting_for_input = True
        Clock.schedule_once(lambda _dt: self.screen.show_text_prompt(prompt))
        return self._responses.get()

    def submit(self, value: str) -> None:
        if not self.waiting_for_input:
            return
        self.waiting_for_input = False
        Clock.schedule_once(lambda _dt: self.screen.clear_prompt())
        self._responses.put(value)


class AndroidTextDnDGame(TextDnDGame):
    def __init__(self, bridge: MobileGameBridge, *, save_dir: Path):
        self.bridge = bridge
        super().__init__(
            input_fn=lambda _prompt="": "",
            output_fn=self.bridge.post_output,
            save_dir=save_dir,
            animate_dice=False,
            pace_output=False,
            type_dialogue=False,
        )

    def style_text(self, text: object, color: str) -> str:
        return str(text)

    def say(self, text: str, *, typed: bool = False) -> None:
        if not text:
            self.output_fn("")
            return
        for paragraph in str(text).split("\n"):
            self.output_fn(paragraph)

    def banner(self, title: str) -> None:
        self.output_fn("")
        self.output_fn(f"=== {title} ===")

    def ask_text(self, prompt: str) -> str:
        while True:
            value = self.bridge.request_text(f"{prompt}:").strip()
            if self.handle_meta_command(value):
                continue
            if value:
                return value
            self.say("Please enter a value.")

    def read_input(self, prompt: str) -> str:
        return self.bridge.request_text(prompt)

    def choose_with_display_mode(
        self,
        prompt: str,
        options: list[str],
        *,
        allow_meta: bool = True,
        staggered: bool = False,
    ) -> int:
        del allow_meta, staggered
        if not options:
            raise ValueError("Choice lists must contain at least one option.")

        if len(options) > MENU_PAGE_SIZE:
            page = 0
            page_size = MENU_PAGE_SIZE
            while True:
                start = page * page_size
                visible = options[start : start + page_size]
                labels = list(visible)
                nav_map: dict[int, str] = {}
                if page > 0:
                    labels.append("Previous page")
                    nav_map[len(labels)] = "prev"
                if start + page_size < len(options):
                    labels.append("Next page")
                    nav_map[len(labels)] = "next"
                raw = self.bridge.request_choice(f"{prompt} (page {page + 1})", labels).strip()
                if self.handle_meta_command(raw):
                    continue
                if raw.isdigit():
                    value = int(raw)
                    if value in nav_map:
                        page = page - 1 if nav_map[value] == "prev" else page + 1
                        continue
                    if 1 <= value <= len(visible):
                        return start + value
                self.say("Please choose one of the listed options.")

        while True:
            raw = self.bridge.request_choice(prompt, options).strip()
            if self.handle_meta_command(raw):
                continue
            if raw.isdigit():
                value = int(raw)
                if 1 <= value <= len(options):
                    return value
            self.say("Please choose one of the listed options.")


class GameScreen(BoxLayout):
    COMMANDS = [
        "help",
        "save",
        "party",
        "journal",
        "inventory",
        "gear",
        "camp",
    ]

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(12), spacing=dp(10), **kwargs)
        self._log_lines: list[str] = []
        self.bridge = MobileGameBridge(self)
        self._build_ui()

    def _build_ui(self) -> None:
        header = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(88), spacing=dp(4))
        header.add_widget(
            Label(
                text="Aethrune",
                color=(0.16, 0.11, 0.07, 1),
                font_size="24sp",
                bold=True,
                size_hint_y=None,
                height=dp(40),
            )
        )
        self.status_label = Label(
            text="Tap a choice button or type a response below.",
            color=(0.32, 0.25, 0.16, 1),
            font_size="14sp",
            halign="left",
            valign="middle",
        )
        self.status_label.bind(size=self._sync_status_label)
        header.add_widget(self.status_label)
        self.add_widget(header)

        log_shell = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6))
        with log_shell.canvas.before:
            pass
        self.log_label = WrappedLabel(
            text="Launching...",
            color=(0.18, 0.13, 0.08, 1),
            font_size="16sp",
            halign="left",
            valign="top",
            size_hint_y=None,
        )
        self.log_scroll = ScrollView(do_scroll_x=False, bar_width=dp(6))
        self.log_scroll.add_widget(self.log_label)
        log_shell.add_widget(self.log_scroll)
        self.add_widget(log_shell)

        self.prompt_label = WrappedLabel(
            text="",
            color=(0.28, 0.22, 0.14, 1),
            font_size="16sp",
            bold=True,
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(38),
        )
        self.add_widget(self.prompt_label)

        options_shell = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(220))
        self.options_grid = GridLayout(cols=1, spacing=dp(8), size_hint_y=None)
        self.options_grid.bind(minimum_height=self.options_grid.setter("height"))
        self.options_scroll = ScrollView(do_scroll_x=False, size_hint=(1, 1), bar_width=dp(6))
        self.options_scroll.add_widget(self.options_grid)
        options_shell.add_widget(self.options_scroll)
        self.add_widget(options_shell)

        input_row = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(8))
        self.text_input = TextInput(
            multiline=False,
            hint_text="Type your answer here",
            background_color=(0.98, 0.95, 0.88, 1),
            foreground_color=(0.16, 0.11, 0.07, 1),
            cursor_color=(0.40, 0.25, 0.10, 1),
            padding=[dp(12), dp(14), dp(12), dp(14)],
        )
        self.text_input.bind(on_text_validate=lambda *_args: self.submit_text())
        input_row.add_widget(self.text_input)
        send_button = Button(
            text="Send",
            size_hint_x=None,
            width=dp(96),
            background_normal="",
            background_color=(0.36, 0.22, 0.08, 1),
            color=(1, 0.98, 0.94, 1),
        )
        send_button.bind(on_release=lambda *_args: self.submit_text())
        input_row.add_widget(send_button)
        self.add_widget(input_row)

        commands = GridLayout(cols=4, spacing=dp(8), size_hint_y=None, height=dp(108))
        for command in self.COMMANDS:
            button = Button(
                text=command.title(),
                background_normal="",
                background_color=(0.74, 0.58, 0.37, 1),
                color=(0.16, 0.11, 0.07, 1),
            )
            button.bind(on_release=lambda _btn, value=command: self.submit_direct(value))
            commands.add_widget(button)
        self.add_widget(commands)

    def _sync_status_label(self, instance: Label, _value) -> None:
        instance.text_size = (instance.width, None)

    def append_log(self, text: str) -> None:
        self._log_lines.append(text)
        self.log_label.text = "\n".join(self._log_lines).strip("\n")
        Clock.schedule_once(lambda _dt: self._scroll_log_to_bottom(), 0)

    def _scroll_log_to_bottom(self) -> None:
        self.log_scroll.scroll_y = 0

    def show_choice_prompt(self, prompt: str, options: list[str]) -> None:
        self.prompt_label.text = prompt
        self.status_label.text = "Tap a choice button or type a number / command."
        self._rebuild_options(options)
        self.text_input.hint_text = "Type a number or a command like help"
        Clock.schedule_once(lambda _dt: self._focus_text_input(), 0)

    def show_text_prompt(self, prompt: str) -> None:
        self.prompt_label.text = prompt
        self.status_label.text = "Type a response below. Commands like save and journal still work."
        self._rebuild_options([])
        self.text_input.hint_text = "Type your answer here"
        Clock.schedule_once(lambda _dt: self._focus_text_input(), 0)

    def clear_prompt(self) -> None:
        self.prompt_label.text = ""
        self._rebuild_options([])
        self.text_input.text = ""
        self.text_input.hint_text = "Waiting for the story..."

    def finish_session(self) -> None:
        self.status_label.text = "Session finished. Restart the app to play again."
        self.prompt_label.text = ""
        self._rebuild_options([])
        self.text_input.disabled = True

    def _focus_text_input(self) -> None:
        self.text_input.focus = True

    def _rebuild_options(self, options: list[str]) -> None:
        self.options_grid.clear_widgets()
        for index, option in enumerate(options, start=1):
            button = WrappedButton(
                text=f"{index}. {option}",
                background_normal="",
                background_color=(0.20, 0.42, 0.34, 1),
                color=(1, 0.98, 0.94, 1),
                halign="left",
                valign="middle",
                size_hint_y=None,
            )
            button.bind(on_release=lambda _btn, value=str(index): self.submit_direct(value))
            self.options_grid.add_widget(button)

    def submit_direct(self, value: str) -> None:
        self.text_input.text = ""
        self.bridge.submit(value)

    def submit_text(self) -> None:
        value = self.text_input.text.strip()
        if not value:
            return
        self.text_input.text = ""
        self.bridge.submit(value)


class AndroidDnDApp(App):
    def build(self) -> GameScreen:
        self.title = "Aethrune"
        try:
            Window.clearcolor = (0.93, 0.89, 0.80, 1)
        except Exception:
            pass
        return GameScreen()

    def on_start(self) -> None:
        self.root.bridge.start()


if __name__ == "__main__":
    AndroidDnDApp().run()
