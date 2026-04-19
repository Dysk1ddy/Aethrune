from __future__ import annotations

import io
import json
from pathlib import Path
import random
import re
from types import SimpleNamespace
import unittest
from collections import Counter
from unittest.mock import patch

import dnd_game.gameplay.base as gameplay_base
import dnd_game.gameplay.audio_backend as audio_backend
from dnd_game.content import (
    BACKGROUNDS,
    CLASSES,
    PRESET_CHARACTERS,
    RACES,
    build_character,
    create_bryn_underbough,
    create_elira_dawnmantle,
    create_enemy,
    create_kaelis_starling,
    create_nim_ardentglass,
    create_rhogar_valeguard,
    create_irielle_ashwake,
    create_tolan_ironshield,
    point_buy_total,
)
from dnd_game.dice import roll, roll_d20
from dnd_game.game import Encounter, TextDnDGame
from dnd_game.gameplay.combat_flow import TurnState
from dnd_game.gameplay.sound_effects import (
    DICE_ROLL_SOUND_EFFECTS,
    DICE_ROLL_SOUND_MAX_SECONDS,
    DICE_ROLL_SOUND_MIN_SECONDS,
    SFX_ASSET_DIR,
    SOUND_EFFECT_FILES,
    closest_dice_roll_sound_effect,
)
from dnd_game.gameplay.music import (
    MUSIC_AREA_TRANSITION_SECONDS,
    MUSIC_BOSS_TRANSITION_SECONDS,
    MUSIC_COMBAT_EXIT_TRANSITION_SECONDS,
    MUSIC_COMBAT_TRANSITION_SECONDS,
    MUSIC_INITIAL_FADE_SECONDS,
    MUSIC_LOCAL_TRANSITION_SECONDS,
    MUSIC_RANDOM_ENCOUNTER_TRANSITION_SECONDS,
    MUSIC_ASSET_EXTENSIONS,
    MUSIC_CONTEXT_FOLDERS,
    MUSIC_TRANSITION_CURVE,
    SCENE_MUSIC_CONTEXTS,
    music_files_for_context,
    music_transition_seconds,
)
from dnd_game.gameplay.spell_slots import spell_slot_counts
from dnd_game.drafts.map_system.runtime import (
    DraftMapState,
    FlagCountRequirement,
    FlagValueRequirement,
    NumericFlagRequirement,
    Requirement,
    build_dungeon_panel,
    build_overworld_panel,
    build_overworld_panel_text,
    requirement_met,
    room_exit_directions,
    room_travel_path,
)
from dnd_game.drafts.map_system import ACT2_ENEMY_DRIVEN_MAP
from dnd_game.drafts.map_system.data.act1_hybrid_map import ACT1_HYBRID_MAP
from dnd_game.data.story.lore import APPENDIX_LORE
from dnd_game.data.quests import QUESTS, QuestLogEntry
from dnd_game.data.items.catalog import LOOT_TABLES
from dnd_game.items import ITEMS, format_inventory_line
from dnd_game.models import GameState
from dnd_game.gameplay.status_effects import STATUS_DEFINITIONS
from dnd_game.ui.colors import colorize, strip_ansi
from dnd_game.ui.rich_render import RICH_AVAILABLE, render_rich_lines


class CoreTests(unittest.TestCase):
    class _SceneExit(RuntimeError):
        pass

    def plain_output(self, lines: list[str]) -> str:
        return strip_ansi("\n".join(lines))

    def option_index_containing(self, options: list[str], needle: str) -> int:
        plain_options = [strip_ansi(option) for option in options]
        for index, option in enumerate(plain_options, start=1):
            if needle in option:
                return index
        raise AssertionError(f"Could not find option containing {needle!r} in {plain_options!r}")

    def assert_dungeon_map_header_is_balanced(self, rendered: str) -> None:
        self.assertNotIn("Compass", rendered)
        rendered_lines = rendered.splitlines()
        header_line = next(line for line in rendered_lines if line.startswith("| ") and "NORTH" in line)
        west_line = next(line for line in rendered_lines if line.startswith("| ") and "WEST-+-EAST" in line)
        south_line = next(line for line in rendered_lines if line.startswith("| ") and "SOUTH" in line)
        panel_body = header_line[2:-2]
        map_start = panel_body.find("+")
        map_end = panel_body.find("+", map_start + 1)
        compass_start = panel_body.rfind("NORTH")
        west_body = west_line[2:-2]
        south_body = south_line[2:-2]
        cross_index = west_body.rfind("+")
        panel_center = (len(panel_body) - 1) / 2
        map_center = (map_start + map_end) / 2
        self.assertNotEqual(map_start, -1)
        self.assertNotEqual(map_end, -1)
        self.assertGreaterEqual(compass_start, len(panel_body) - len("   NORTH   ") - 2)
        self.assertLess(map_end, compass_start)
        self.assertEqual(panel_body.rfind("NORTH") + len("NORTH") // 2, cross_index)
        self.assertEqual(south_body.rfind("SOUTH") + len("SOUTH") // 2, cross_index)
        self.assertLessEqual(abs(map_center - panel_center), 1.0)

    def assert_rich_compass_block_is_fixed_width(self, rendered: str) -> None:
        self.assertNotIn("Compass", rendered)
        rendered_lines = rendered.splitlines()
        north_line = next(line for line in rendered_lines if "NORTH" in line)
        west_line = next(line for line in rendered_lines if "WEST-+-EAST" in line)
        south_line = next(line for line in rendered_lines if "SOUTH" in line)
        pipe_lines = [line for line in rendered_lines if line.rfind("|") != -1]
        cross_index = west_line.rfind("+")
        self.assertEqual(north_line.rfind("NORTH") + len("NORTH") // 2, cross_index)
        self.assertEqual(south_line.rfind("SOUTH") + len("SOUTH") // 2, cross_index)
        self.assertGreaterEqual(len(pipe_lines), 2)
        self.assertTrue(all(line.rfind("|") == cross_index for line in pipe_lines[:2]))

    def test_point_buy_total(self) -> None:
        scores = {"STR": 15, "DEX": 14, "CON": 13, "INT": 10, "WIS": 10, "CHA": 8}
        self.assertEqual(point_buy_total(scores), 25)

    def test_roll_functions_use_rng_animation_hook(self) -> None:
        rng = random.Random(9001)
        calls: list[str] = []
        rng.dice_roll_animator = lambda **payload: calls.append(payload["kind"])
        roll("1d6", rng)
        roll_d20(rng)
        self.assertEqual(calls, ["roll", "d20"])

    def test_roll_animation_payload_can_include_display_bonus(self) -> None:
        rng = random.Random(90011)
        payloads: list[dict[str, object]] = []
        rng.dice_roll_display_bonus = 3
        rng.dice_roll_animator = lambda **payload: payloads.append(payload)
        roll("1d8", rng)
        self.assertEqual(payloads[-1]["modifier"], 0)
        self.assertEqual(payloads[-1]["display_modifier"], 3)

    def test_game_disables_dice_animation_for_custom_io_by_default(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9002))
        self.assertFalse(game.animate_dice)
        self.assertFalse(hasattr(game.rng, "dice_roll_animator"))

    def test_game_can_enable_dice_animation_explicitly(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9003), animate_dice=True)
        self.assertTrue(game.animate_dice)
        self.assertTrue(callable(getattr(game.rng, "dice_roll_animator", None)))

    def test_game_disables_output_pacing_and_dialogue_typing_for_custom_io_by_default(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90031))
        self.assertFalse(game.pace_output)
        self.assertFalse(game.type_dialogue)

    def test_game_disables_sound_effects_for_custom_io_by_default(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900311))
        self.assertFalse(game.sound_effects_enabled)

    def test_game_disables_music_for_custom_io_by_default(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900312))
        self.assertFalse(game.music_enabled)

    def test_music_contexts_use_named_subfolder_assets(self) -> None:
        self.assertEqual(MUSIC_CONTEXT_FOLDERS["boss_combat"], ("Miniboss combat",))
        self.assertEqual(MUSIC_CONTEXT_FOLDERS["random_encounter"], ("Wilderness exploration",))
        self.assertEqual(MUSIC_CONTEXT_FOLDERS["city"], ("Town",))
        self.assertEqual(MUSIC_CONTEXT_FOLDERS["dungeon"], ("Dungeon",))
        self.assertEqual(MUSIC_CONTEXT_FOLDERS["main_menu"], ("Main menu",))
        self.assertEqual(MUSIC_CONTEXT_FOLDERS["camp"], ("Camp",))
        self.assertEqual(SCENE_MUSIC_CONTEXTS["phandalin_hub"], "city")
        self.assertEqual(SCENE_MUSIC_CONTEXTS["tresendar_manor"], "dungeon")
        self.assertEqual(SCENE_MUSIC_CONTEXTS["blackwake_crossing"], "dungeon")
        self.assertEqual(SCENE_MUSIC_CONTEXTS["road_ambush"], "wilderness")
        for node in ACT1_HYBRID_MAP.nodes.values():
            if node.enters_dungeon_id is not None:
                self.assertEqual(SCENE_MUSIC_CONTEXTS[node.scene_key], "dungeon")
        for node in ACT2_ENEMY_DRIVEN_MAP.nodes.values():
            if node.enters_dungeon_id is not None:
                self.assertEqual(SCENE_MUSIC_CONTEXTS[node.scene_key], "dungeon")

        for context in (
            "main_menu",
            "camp",
            "city",
            "dungeon",
            "combat",
            "miniboss_combat",
            "boss_combat",
            "random_encounter",
        ):
            tracks = music_files_for_context(context)
            self.assertTrue(tracks, context)
            self.assertTrue(all(path.suffix.lower() in MUSIC_ASSET_EXTENSIONS for path in tracks))

        self.assertEqual(
            {path.resolve() for path in music_files_for_context("boss_combat")},
            {path.resolve() for path in music_files_for_context("miniboss_combat")},
        )
        self.assertEqual(
            {path.resolve() for path in music_files_for_context("random_encounter")},
            {path.resolve() for path in music_files_for_context("wilderness")},
        )

    def test_music_picker_exhausts_folder_tracks_before_repeating(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9003140))
        tracks = [
            Path("Town/first.mp3"),
            Path("Town/second.mp3"),
            Path("Town/third.mp3"),
        ]
        game.music_files_for_context = lambda context: list(tracks)

        first_cycle = [game.choose_music_file("city") for _ in tracks]
        next_pick = game.choose_music_file("city")

        self.assertEqual({track.name for track in first_cycle if track is not None}, {track.name for track in tracks})
        self.assertIsNotNone(next_pick)
        self.assertNotEqual(next_pick, first_cycle[-1])

    def test_music_picker_shares_history_across_contexts_for_same_folder(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9003141))
        tracks = [
            Path("Town/market.mp3"),
            Path("Town/inn.mp3"),
        ]
        game.music_files_for_context = lambda context: list(tracks)

        town_pick = game.choose_music_file("city")
        inn_pick = game.choose_music_file("inn")

        self.assertIsNotNone(town_pick)
        self.assertIsNotNone(inn_pick)
        self.assertNotEqual(inn_pick, town_pick)

    def test_music_backend_uses_mci_when_pygame_is_missing(self) -> None:
        commands: list[str] = []
        fake_winmm = SimpleNamespace(
            mciSendStringW=lambda command, buffer, buffer_size, callback: commands.append(command) or 0,
        )
        track = music_files_for_context("main_menu")[0]
        with (
            patch.object(audio_backend, "pygame", None),
            patch.object(audio_backend, "_WINMM", fake_winmm),
            patch.object(audio_backend, "_MCI_MUSIC_OPEN", False),
        ):
            self.assertTrue(audio_backend.music_is_available())
            self.assertTrue(audio_backend.music_file_is_supported(track))
            self.assertFalse(audio_backend.music_file_is_supported(Path("track.ogg")))
            self.assertTrue(audio_backend.play_music(track))
            audio_backend.stop_music()

        self.assertTrue(any(command.startswith('open "') and "Main menu" in command for command in commands))
        self.assertTrue(any("type mpegvideo" in command for command in commands))
        self.assertIn("play dnd_game_music repeat", commands)
        self.assertIn("stop dnd_game_music", commands)
        self.assertIn("close dnd_game_music", commands)

    def test_music_settings_enable_with_mci_fallback(self) -> None:
        commands: list[str] = []
        fake_winmm = SimpleNamespace(
            mciSendStringW=lambda command, buffer, buffer_size, callback: commands.append(command) or 0,
        )
        with (
            patch.object(audio_backend, "pygame", None),
            patch.object(audio_backend, "_WINMM", fake_winmm),
            patch.object(audio_backend, "_MCI_MUSIC_OPEN", False),
        ):
            game = TextDnDGame(input_fn=lambda _: "1", output_fn=print, rng=random.Random(900314), play_music=False)
            messages: list[str] = []
            game.say = messages.append
            game.persist_settings = lambda: None
            game.set_music_enabled(True)

        self.assertTrue(game._music_supported)
        self.assertTrue(game._music_assets_ready)
        self.assertTrue(game.music_enabled)
        self.assertEqual(messages, ["Music enabled."])
        self.assertTrue(any(command.startswith('open "') and "Main menu" in command for command in commands))
        self.assertIn("play dnd_game_music repeat", commands)

    def test_pygame_channel_music_does_not_fallback_when_channel_play_returns_none(self) -> None:
        class FakeMusic:
            def __init__(self) -> None:
                self.load_calls: list[str] = []
                self.play_calls: list[dict[str, int]] = []

            def get_busy(self) -> bool:
                return False

            def stop(self) -> None:
                pass

            def unload(self) -> None:
                pass

            def load(self, path: str) -> None:
                self.load_calls.append(path)

            def play(self, **kwargs: int) -> None:
                self.play_calls.append(kwargs)

        class FakeChannel:
            def __init__(self) -> None:
                self.busy = False
                self.play_calls: list[tuple[object, int]] = []
                self.volumes: list[float] = []

            def stop(self) -> None:
                self.busy = False

            def set_volume(self, volume: float) -> None:
                self.volumes.append(volume)

            def play(self, sound: object, *, loops: int = 0) -> None:
                self.busy = True
                self.play_calls.append((sound, loops))

            def get_busy(self) -> bool:
                return self.busy

        class FakeMixer:
            def __init__(self) -> None:
                self.music = FakeMusic()
                self.channels = {0: FakeChannel(), 1: FakeChannel()}

            def get_init(self) -> tuple[int, int, int]:
                return (44100, -16, 2)

            def Channel(self, index: int) -> FakeChannel:
                return self.channels[index]

        fake_mixer = FakeMixer()
        fake_pygame = SimpleNamespace(error=RuntimeError, mixer=fake_mixer)
        fake_sound = object()
        threads: list[tuple[object, tuple[object, ...], bool]] = []

        class FakeThread:
            def __init__(self, *, target, args: tuple[object, ...], daemon: bool) -> None:
                self.target = target
                self.args = args
                self.daemon = daemon

            def start(self) -> None:
                threads.append((self.target, self.args, self.daemon))

        with (
            patch.object(audio_backend, "pygame", fake_pygame),
            patch.object(audio_backend.threading, "Thread", FakeThread),
            patch.object(audio_backend, "ensure_mixer", return_value=True),
            patch.object(audio_backend, "load_music_sound", return_value=fake_sound),
            patch.object(audio_backend, "_MUSIC_ACTIVE_CHANNEL_INDEX", None),
            patch.object(audio_backend, "_MUSIC_CHANNEL_MODE", False),
            patch.object(audio_backend, "_MUSIC_TRANSITION_TOKEN", 0),
            patch.object(audio_backend, "_MCI_MUSIC_OPEN", False),
        ):
            self.assertTrue(audio_backend.play_pygame_channel_music(Path("town.mp3"), fade_ms=800))

        self.assertEqual(fake_mixer.channels[0].play_calls, [])
        self.assertEqual(fake_mixer.channels[0].volumes, [0.0])
        self.assertEqual(len(threads), 1)
        self.assertIs(threads[0][0], audio_backend._finish_sequential_transition)
        self.assertEqual(threads[0][1][1:6], (None, 0, fake_sound, -1, 800))
        self.assertTrue(threads[0][2])
        self.assertEqual(fake_mixer.music.load_calls, [])
        self.assertEqual(fake_mixer.music.play_calls, [])

    def test_pygame_music_stream_fades_out_waits_then_fades_in_next_track(self) -> None:
        calls: list[tuple[object, ...]] = []
        sleeps: list[float] = []

        class FakeMusic:
            def get_busy(self) -> bool:
                return True

            def fadeout(self, fade_ms: int) -> None:
                calls.append(("fadeout", fade_ms))

            def unload(self) -> None:
                calls.append(("unload",))

            def load(self, path: str) -> None:
                calls.append(("load", Path(path).name))

            def play(self, **kwargs: int) -> None:
                calls.append(("play", kwargs))

        class FakeChannel:
            def stop(self) -> None:
                calls.append(("channel_stop",))

        class FakeMixer:
            def __init__(self) -> None:
                self.music = FakeMusic()
                self.channels = {0: FakeChannel(), 1: FakeChannel()}

            def get_init(self) -> tuple[int, int, int]:
                return (44100, -16, 2)

            def Channel(self, index: int) -> FakeChannel:
                return self.channels[index]

        fake_pygame = SimpleNamespace(error=RuntimeError, mixer=FakeMixer())
        with (
            patch.object(audio_backend, "pygame", fake_pygame),
            patch.object(audio_backend.time, "sleep", sleeps.append),
            patch.object(audio_backend, "_MUSIC_ACTIVE_CHANNEL_INDEX", None),
            patch.object(audio_backend, "_MUSIC_CHANNEL_MODE", False),
            patch.object(audio_backend, "_MUSIC_TRANSITION_TOKEN", 0),
            patch.object(audio_backend, "_MCI_MUSIC_OPEN", False),
        ):
            self.assertTrue(audio_backend.play_music(Path("next_theme.mp3"), fade_ms=2500, curve="linear"))

        self.assertEqual(sleeps, [2.5 + audio_backend._MUSIC_SILENCE_GAP_SECONDS])
        self.assertEqual(
            calls,
            [
                ("channel_stop",),
                ("channel_stop",),
                ("fadeout", 2500),
                ("unload",),
                ("load", "next_theme.mp3"),
                ("play", {"loops": -1, "fade_ms": 2500}),
            ],
        )

    def test_pygame_channel_music_fades_out_then_starts_next_track(self) -> None:
        events: list[tuple[object, ...]] = []

        class FakeChannel:
            def __init__(self, name: str) -> None:
                self.name = name

            def set_volume(self, volume: float) -> None:
                events.append((self.name, "volume", round(volume, 3)))

            def stop(self) -> None:
                events.append((self.name, "stop"))

            def play(self, sound: object, *, loops: int = 0) -> None:
                events.append((self.name, "play", sound, loops))

        class FakeMixer:
            def __init__(self) -> None:
                self.channels = {0: FakeChannel("old"), 1: FakeChannel("new")}

            def get_init(self) -> tuple[int, int, int]:
                return (44100, -16, 2)

            def Channel(self, index: int) -> FakeChannel:
                return self.channels[index]

        fake_pygame = SimpleNamespace(error=RuntimeError, mixer=FakeMixer())
        fake_sound = object()
        sleeps: list[float] = []
        with (
            patch.object(audio_backend, "pygame", fake_pygame),
            patch.object(audio_backend, "_MUSIC_TRANSITION_TOKEN", 1),
            patch.object(audio_backend, "_MUSIC_ACTIVE_CHANNEL_INDEX", 0),
            patch.object(audio_backend.time, "perf_counter", side_effect=[0.0, 0.0, 1.0, 1.0, 1.0, 2.0]),
            patch.object(audio_backend.time, "sleep", sleeps.append),
        ):
            audio_backend._finish_sequential_transition(1, 0, 1, fake_sound, -1, 1000, "linear")

        old_stop_index = events.index(("old", "stop"))
        new_play_index = events.index(("new", "play", fake_sound, -1))
        self.assertLess(old_stop_index, new_play_index)
        self.assertEqual(events[old_stop_index - 1], ("old", "volume", 0.0))
        self.assertEqual(events[new_play_index - 1], ("new", "volume", 0.0))
        self.assertIn(("new", "volume", 1.0), events[new_play_index + 1 :])
        self.assertIn(audio_backend._MUSIC_SILENCE_GAP_SECONDS, sleeps)

    def test_music_transition_profiles_match_scene_energy(self) -> None:
        self.assertEqual(MUSIC_TRANSITION_CURVE, "linear")
        self.assertEqual(music_transition_seconds("wilderness", "combat"), MUSIC_COMBAT_TRANSITION_SECONDS)
        self.assertEqual(music_transition_seconds("dungeon", "boss_combat"), MUSIC_BOSS_TRANSITION_SECONDS)
        self.assertEqual(music_transition_seconds("combat", "city"), MUSIC_COMBAT_EXIT_TRANSITION_SECONDS)
        self.assertEqual(music_transition_seconds("wilderness", "random_encounter"), MUSIC_RANDOM_ENCOUNTER_TRANSITION_SECONDS)
        self.assertEqual(music_transition_seconds("city", "inn"), MUSIC_LOCAL_TRANSITION_SECONDS)
        self.assertEqual(music_transition_seconds("wilderness", "dungeon"), MUSIC_AREA_TRANSITION_SECONDS)
        self.assertLess(MUSIC_BOSS_TRANSITION_SECONDS, MUSIC_COMBAT_TRANSITION_SECONDS)
        self.assertLess(MUSIC_RANDOM_ENCOUNTER_TRANSITION_SECONDS, MUSIC_COMBAT_EXIT_TRANSITION_SECONDS)
        self.assertGreater(music_transition_seconds("city", "dungeon"), MUSIC_COMBAT_TRANSITION_SECONDS)

    def test_play_music_for_context_passes_contextual_crossfade(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900315))
        game.music_enabled = True
        game._music_supported = True
        game._music_context = "wilderness"
        game._music_track_name = "old.mp3"
        game._last_music_transition_at = 0.0
        game.choose_music_file = lambda context: Path(f"{context}.mp3")

        with patch.object(audio_backend, "play_music", return_value=True) as play_music:
            game.play_music_for_context("combat", restart=True)

        play_music.assert_called_once()
        _, kwargs = play_music.call_args
        self.assertEqual(kwargs["fade_ms"], int(MUSIC_COMBAT_TRANSITION_SECONDS * 1000))
        self.assertEqual(kwargs["curve"], MUSIC_TRANSITION_CURVE)
        self.assertEqual(game._music_context, "combat")
        self.assertEqual(game._music_track_name, "combat.mp3")

    def test_refresh_scene_music_fades_in_main_menu_by_default(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9003150))
        game.music_enabled = True
        game._music_supported = True
        game._music_context = None
        game._music_track_name = None
        game.choose_music_file = lambda context: Path(f"{context}.mp3")

        with patch.object(audio_backend, "play_music", return_value=True) as play_music:
            game.refresh_scene_music(default_to_menu=True)

        play_music.assert_called_once()
        track_path, kwargs = play_music.call_args.args[0], play_music.call_args.kwargs
        self.assertEqual(track_path, Path("main_menu.mp3"))
        self.assertEqual(kwargs["fade_ms"], int(MUSIC_INITIAL_FADE_SECONDS * 1000))
        self.assertEqual(kwargs["curve"], MUSIC_TRANSITION_CURVE)
        self.assertEqual(game._music_context, "main_menu")
        self.assertEqual(game._music_track_name, "main_menu.mp3")

    def test_rapid_combat_scene_random_encounter_music_transitions_all_fire(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9003151))
        game.state = GameState(player=player, current_scene="road_ambush")
        game.music_enabled = True
        game._music_supported = True
        game._music_context = "wilderness"
        game._music_track_name = "wilderness_old.mp3"
        game._last_music_transition_at = 90.0
        calls: list[tuple[str, int, str]] = []
        game.choose_music_file = lambda context: Path(f"{context}_{len(calls)}.mp3")

        def capture_music(path: Path, **kwargs: object) -> bool:
            calls.append((path.name, int(kwargs["fade_ms"]), str(kwargs["curve"])))
            return True

        encounter = Encounter(
            title="Roadside Snap Fight",
            description="The danger arrives before the dust settles.",
            enemies=[],
        )
        with (
            patch("dnd_game.gameplay.music.time.perf_counter", side_effect=[100.0, 100.12, 100.24]),
            patch.object(audio_backend, "play_music", side_effect=capture_music),
        ):
            game.play_encounter_music(encounter)
            game.refresh_scene_music()
            game._random_encounter_active = True
            game.refresh_scene_music()

        self.assertEqual(
            calls,
            [
                ("combat_0.mp3", int(MUSIC_COMBAT_TRANSITION_SECONDS * 1000), MUSIC_TRANSITION_CURVE),
                ("wilderness_1.mp3", int(MUSIC_COMBAT_EXIT_TRANSITION_SECONDS * 1000), MUSIC_TRANSITION_CURVE),
                ("random_encounter_2.mp3", int(MUSIC_RANDOM_ENCOUNTER_TRANSITION_SECONDS * 1000), MUSIC_TRANSITION_CURVE),
            ],
        )
        self.assertEqual(game._music_context, "random_encounter")
        self.assertEqual(game._music_track_name, "random_encounter_2.mp3")
        self.assertEqual(game._last_music_transition_at, 100.24)

    def test_stop_music_fades_to_silence(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900316))
        game._music_supported = True
        game._music_context = "city"
        game._music_track_name = "town.mp3"

        with patch.object(audio_backend, "stop_music") as stop_music:
            game.stop_music(fade_seconds=1.5)

        stop_music.assert_called_once_with(fade_ms=1500, curve=MUSIC_TRANSITION_CURVE)
        self.assertIsNone(game._music_context)
        self.assertIsNone(game._music_track_name)

    def test_restarting_same_music_context_obeys_switch_cooldown(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900317))
        game.music_enabled = True
        game._music_supported = True
        game._music_context = "combat"
        game._music_track_name = "combat.mp3"
        game._last_music_transition_at = 4.8
        game.choose_music_file = lambda context: Path(f"{context}.mp3")

        with (
            patch("dnd_game.gameplay.music.time.perf_counter", return_value=5.0),
            patch.object(audio_backend, "play_music", return_value=True) as play_music,
        ):
            game.play_music_for_context("combat", restart=True)

        play_music.assert_not_called()

    def test_sound_effect_library_contains_expected_files(self) -> None:
        self.assertEqual(set(SOUND_EFFECT_FILES), {effect.key for effect in DICE_ROLL_SOUND_EFFECTS})
        self.assertTrue(all(key.startswith("dice_roll_") for key in SOUND_EFFECT_FILES))
        self.assertTrue(
            all(
                DICE_ROLL_SOUND_MIN_SECONDS <= effect.duration_seconds <= DICE_ROLL_SOUND_MAX_SECONDS
                for effect in DICE_ROLL_SOUND_EFFECTS
            )
        )

    def test_dice_roll_sound_selector_uses_closest_duration(self) -> None:
        self.assertEqual(closest_dice_roll_sound_effect(0.41), "dice_roll_040")
        self.assertEqual(closest_dice_roll_sound_effect(0.82), "dice_roll_070")
        self.assertEqual(closest_dice_roll_sound_effect(1.12), "dice_roll_095")
        self.assertEqual(closest_dice_roll_sound_effect(1.48), "dice_roll_130")
        self.assertEqual(closest_dice_roll_sound_effect(1.70), "dice_roll_175")

    def test_sound_effect_settings_enable_with_winsound_fallback(self) -> None:
        fake_winsound = SimpleNamespace(
            SND_FILENAME=1,
            SND_ASYNC=2,
            PlaySound=lambda path, flags: None,
        )
        with patch.object(audio_backend, "pygame", None), patch.object(audio_backend, "winsound", fake_winsound):
            game = TextDnDGame(input_fn=lambda _: "1", output_fn=print, rng=random.Random(900313), play_sfx=False)
            messages: list[str] = []
            game.say = messages.append
            game.persist_settings = lambda: None
            game.set_sound_effects_enabled(True)
        self.assertTrue(game._sfx_supported)
        self.assertTrue(game._sfx_assets_ready)
        self.assertTrue(game.sound_effects_enabled)
        self.assertEqual(messages, ["Sound effects enabled."])

    def test_sound_effect_backend_uses_winsound_when_pygame_is_missing(self) -> None:
        calls: list[tuple[str, int]] = []
        fake_winsound = SimpleNamespace(
            SND_FILENAME=1,
            SND_ASYNC=2,
            PlaySound=lambda path, flags: calls.append((Path(path).name, flags)),
        )
        with patch.object(audio_backend, "pygame", None), patch.object(audio_backend, "winsound", fake_winsound):
            self.assertTrue(audio_backend.sound_effects_are_available())
            self.assertTrue(audio_backend.play_sound(SFX_ASSET_DIR / "dice_roll_040.wav"))
        self.assertEqual(calls, [("dice_roll_040.wav", 3)])

    def test_generated_sound_effect_manifest_matches_asset_files(self) -> None:
        manifest = json.loads((SFX_ASSET_DIR / "manifest.json").read_text(encoding="utf-8"))
        generated = {entry["filename"] for entry in manifest["effects"]}
        expected = set(SOUND_EFFECT_FILES.values())
        self.assertEqual(generated, expected)
        self.assertEqual({path.name for path in SFX_ASSET_DIR.glob("*.wav")}, expected)
        self.assertEqual(manifest["roll_duration_window_seconds"]["minimum"], DICE_ROLL_SOUND_MIN_SECONDS)
        self.assertEqual(manifest["roll_duration_window_seconds"]["maximum"], DICE_ROLL_SOUND_MAX_SECONDS)
        self.assertTrue(
            all(
                DICE_ROLL_SOUND_MIN_SECONDS <= entry["duration_seconds"] <= DICE_ROLL_SOUND_MAX_SECONDS
                for entry in manifest["effects"]
            )
        )

    def test_attack_and_heal_sound_routing_matches_actor_side(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900312))
        played: list[str] = []
        game.play_sound_effect = lambda effect_name, cooldown=0.0: played.append(effect_name)
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        enemy = create_enemy("bandit")
        game.play_attack_sound_for(player)
        game.play_attack_sound_for(enemy)
        game.play_heal_sound_for(player)
        game.play_heal_sound_for(enemy)
        self.assertEqual(played, ["player_attack", "enemy_attack", "player_heal", "enemy_heal"])

    def test_d20_animation_payload_includes_target_number_for_checks(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        payloads: list[dict[str, object]] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9004))
        game.rng.dice_roll_animator = lambda **payload: payloads.append(payload)
        game.skill_check(player, "Athletics", 14, context="to scale the wall")
        self.assertEqual(payloads[-1]["kind"], "d20")
        self.assertEqual(payloads[-1]["target_number"], 14)
        self.assertEqual(payloads[-1]["target_label"], "DC 14")
        self.assertEqual(payloads[-1]["modifier"], player.skill_bonus("Athletics"))

    def test_initiative_rolls_are_batched_into_shared_animation(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        enemy = create_enemy("goblin_skirmisher")
        payloads: list[dict[str, object]] = []
        batched_entries: list[dict[str, object]] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90041))
        game.rng.dice_roll_animator = lambda **payload: payloads.append(payload)
        game.animate_initiative_rolls = lambda entries: batched_entries.extend(entries)
        initiative = game.roll_initiative([player], [enemy])
        self.assertEqual([actor.name for actor in initiative], [player.name, enemy.name])
        self.assertEqual(payloads, [])
        self.assertEqual([entry["actor"].name for entry in batched_entries], [player.name, enemy.name])
        self.assertTrue(all(entry["outcome"].kept + entry["modifier"] == entry["total"] for entry in batched_entries))

    def test_game_uses_updated_dice_animation_timing_window(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9005), animate_dice=True)
        self.assertEqual(game._dice_animation_min_seconds, 0.85)
        self.assertEqual(game._dice_animation_max_seconds, 1.75)

    def test_dialogue_typewriter_uses_fixed_character_rate(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9006))
        delays: list[float] = []
        game.typewrite_text = lambda text, *, delay: delays.append(delay)
        with patch("dnd_game.gameplay.base.sys.stdout", io.StringIO()):
            game.typewrite_dialogue_line("Mira Thann", "Hold the line.")
            game.typewrite_dialogue_line("Mira Thann", "Hold the line. Fall back to the cart.")
        self.assertEqual(delays, [0.03, 0.03])

    def test_typewriter_pauses_after_each_sentence_for_dialogue_and_narration(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=print, rng=random.Random(90063), type_dialogue=True)
        game.output_fn = lambda _: None
        buffer = io.StringIO()
        sleeps: list[float] = []
        game.sleep_for_animation = lambda duration, require_animation=False: sleeps.append(duration) or False
        with patch("dnd_game.gameplay.base.sys.stdout", buffer):
            game.typewrite_dialogue_line("Mira Thann", "Hold the line. Fall back!")
            game.typewrite_narration("A shape moves in the fog. Steel flashes!")
        pause_calls = [duration for duration in sleeps if duration == 0.75]
        self.assertEqual(len(pause_calls), 4)

    def test_health_bar_summary_uses_blocks_and_numbers(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90064))
        summary = strip_ansi(game.format_health_bar(9, 12))
        self.assertEqual(summary, "HP [█████████   ]  9/12")

    def test_health_bar_thresholds_match_requested_breakpoints(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900641))
        self.assertEqual(game.health_bar_color(11, 20), "light_green")
        self.assertEqual(game.health_bar_color(10, 20), "yellow")
        self.assertEqual(game.health_bar_color(5, 20), "light_red")

    def test_typewriter_skip_fast_forwards_remaining_text(self) -> None:
        game = TextDnDGame(input_fn=input, output_fn=print, rng=random.Random(900642), type_dialogue=True)
        game.output_fn = lambda _: None
        buffer = io.StringIO()
        skip_calls = iter([False, True])
        game.animation_skip_requested = lambda **kwargs: next(skip_calls, True)
        game.sleep_for_animation = lambda duration, require_animation=False: False
        with patch("dnd_game.gameplay.base.sys.stdout", buffer):
            game.typewrite_text("Hold fast.", delay=0.1)
        self.assertEqual(buffer.getvalue(), "Hold fast.")

    def test_animation_skip_scope_consumes_only_one_enter_press(self) -> None:
        game = TextDnDGame(input_fn=input, output_fn=print, rng=random.Random(900643), animate_dice=True)
        queued_keys = ["\r", "\r"]
        fake_console = SimpleNamespace(
            kbhit=lambda: bool(queued_keys),
            getwch=lambda: queued_keys.pop(0),
        )
        fake_stdin = SimpleNamespace(isatty=lambda: True)
        with patch.object(gameplay_base, "msvcrt", fake_console), patch.object(gameplay_base.sys, "stdin", fake_stdin):
            game.begin_animation_skip_scope()
            try:
                self.assertTrue(game.animation_skip_requested())
                self.assertFalse(game.animation_skip_requested())
                self.assertEqual(queued_keys, [])
                queued_keys.append("\r")
            finally:
                game.end_animation_skip_scope()
            game.begin_animation_skip_scope()
            try:
                self.assertTrue(game.animation_skip_requested())
            finally:
                game.end_animation_skip_scope()

    def test_typed_scenario_text_uses_narration_typewriter_path(self) -> None:
        log: list[str] = []
        typed: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=print, rng=random.Random(90062), type_dialogue=True)
        game.output_fn = log.append
        game.typewrite_narration = lambda text: typed.append(text)
        game.say("A new danger waits on the road.", typed=True)
        self.assertEqual(typed, ["A new danger waits on the road."])
        self.assertEqual(log, [])

    def test_only_npc_dialogue_uses_typewriter_path(self) -> None:
        log: list[str] = []
        typed: list[tuple[str, str]] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=print, rng=random.Random(90061), type_dialogue=True)
        game.output_fn = log.append
        game.typewrite_dialogue_line = lambda speaker_name, text: typed.append((speaker_name, text))
        game.speaker("Mira Thann", "Move quickly.")
        game.player_speaker("I am moving.")
        self.assertEqual(len(typed), 1)
        self.assertEqual(typed[0][1], "Move quickly.")
        rendered = self.plain_output(log)
        self.assertIn('You: "I am moving."', rendered)

    def test_player_choice_output_calls_choice_pause_hook(self) -> None:
        pauses: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9007))
        game.pause_for_choice_resolution = lambda: pauses.append("pause")
        game.player_choice_output(game.action_option("Take the ridge and move."))
        self.assertEqual(pauses, ["pause"])

    def test_scenario_choice_reveals_options_one_by_one(self) -> None:
        pauses: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90073))
        game.pause_for_option_reveal = lambda: pauses.append("pause")
        choice = game.scenario_choice("Choose a path.", ["First", "Second", "Third"], allow_meta=False)
        self.assertEqual(choice, 1)
        self.assertEqual(pauses, ["pause", "pause"])

    def test_non_combat_choose_uses_keyboard_menu_when_supported(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900731))
        captured: dict[str, object] = {}
        game.keyboard_choice_menu_supported = lambda: True

        def fake_run(prompt, options, *, title=None):
            captured["prompt"] = prompt
            captured["options"] = list(options)
            captured["title"] = title
            return 2

        game.run_keyboard_choice_menu = fake_run
        choice = game.choose("Choose a path.", ["First", "Second"], allow_meta=False, show_hud=False)
        self.assertEqual(choice, 2)
        self.assertEqual(captured["prompt"], "Choose a path.")
        self.assertEqual(captured["options"], ["First", "Second"])
        self.assertIsNone(captured["title"])

    def test_combat_choose_uses_keyboard_menu_when_supported(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900732))
        captured: dict[str, object] = {}
        game.keyboard_choice_menu_supported = lambda: True

        def fake_run(prompt, options, *, title=None):
            captured["prompt"] = prompt
            captured["options"] = list(options)
            captured["title"] = title
            return 2

        game.run_keyboard_choice_menu = fake_run
        game._in_combat = True
        choice = game.choose("Choose a path.", ["First", "Second"], allow_meta=False)
        self.assertEqual(choice, 2)
        self.assertEqual(captured["prompt"], "Choose a path.")
        self.assertEqual(captured["options"], ["First", "Second"])
        self.assertIsNone(captured["title"])

    def test_keyboard_choice_reader_treats_ctrl_c_as_game_interrupted(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900733))
        with patch("dnd_game.gameplay.io.msvcrt", SimpleNamespace(getwch=lambda: "\x03")):
            with self.assertRaises(gameplay_base.GameInterrupted):
                game.read_keyboard_choice_wchar()

    def test_keyboard_choice_menu_hides_instructions_after_first_prompt(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900734))
        game.should_use_keyboard_choice_menu = lambda: True
        seen: list[bool] = []
        actions = iter([("down", None), ("enter", None), ("enter", None)])
        game.read_keyboard_choice_key = lambda: next(actions)
        game.build_keyboard_choice_menu = (
            lambda prompt, options, *, title, selected_index, typed_buffer, feedback, show_instructions: (
                seen.append(show_instructions) or "menu"
            )
        )
        self.assertEqual(game.run_keyboard_choice_menu("Choose a path.", ["First", "Second"]), 2)
        self.assertEqual(game.run_keyboard_choice_menu("Choose another path.", ["First", "Second"]), 1)
        self.assertEqual(seen, [True, False, False])

    def test_safe_rich_render_width_does_not_exceed_detected_terminal_width(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900735))
        game.rich_console_width = lambda: 120
        game.detected_terminal_width = lambda: 94
        self.assertEqual(game.safe_rich_render_width(), 94)

    def test_dice_animation_skip_fast_forwards_but_keeps_final_pause(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90071), animate_dice=True)
        rendered: list[bool] = []
        waits: list[tuple[float, bool]] = []
        game.render_dice_animation_frame = lambda *args, **kwargs: rendered.append(kwargs["final"])
        game.sleep_for_dice_animation = lambda duration: True
        game.sleep_for_animation = lambda duration, require_animation=False: waits.append((duration, require_animation)) or False
        sounds: list[str] = []
        game.play_sound_effect = lambda effect_name, cooldown=0.0: sounds.append(effect_name)
        game.animate_dice_roll(kind="d20", expression="d20", sides=20, rolls=[14], kept=14)
        self.assertEqual(rendered, [False, True])
        self.assertEqual(sounds, [closest_dice_roll_sound_effect(0.85)])
        self.assertEqual(waits, [(0.28, True), (0.42, True)])

    def test_skill_check_plays_success_and_failure_sounds(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900711))
        sounds: list[str] = []
        game.play_sound_effect = lambda effect_name, cooldown=0.0: sounds.append(effect_name)
        game.roll_with_advantage = lambda actor, advantage_state: SimpleNamespace(kept=18)
        self.assertTrue(game.skill_check(player, "Athletics", 12, context="to clear the ledge"))
        game.roll_with_advantage = lambda actor, advantage_state: SimpleNamespace(kept=2)
        self.assertFalse(game.skill_check(player, "Athletics", 20, context="to clear the ledge"))
        self.assertEqual(sounds, ["skill_success", "skill_fail"])

    def test_d20_animation_shows_raw_roll_then_final_total_after_pause(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90072), animate_dice=True)
        rendered: list[tuple[str, bool, int, int | None]] = []
        totals: list[tuple[int, int, int | None, str | None]] = []
        game.render_dice_animation_frame = (
            lambda label, rolls, **kwargs: rendered.append((label, kwargs["final"], rolls[-1], kwargs.get("target_number")))
        )
        game.render_dice_animation_total_frame = (
            lambda **kwargs: totals.append(
                (kwargs["kept"], kwargs["modifier"], kwargs.get("target_number"), kwargs.get("target_label"))
            )
        )
        game.sleep_for_dice_animation = lambda duration: True
        waits: list[tuple[float, bool]] = []
        game.sleep_for_animation = lambda duration, require_animation=False: waits.append((duration, require_animation)) or False
        game.animate_dice_roll(
            kind="d20",
            expression="d20",
            sides=20,
            rolls=[9],
            kept=9,
            modifier=5,
            target_number=14,
            target_label="DC 14",
        )
        self.assertEqual(len(rendered), 2)
        self.assertEqual(rendered[0][0], "Rolling d20")
        self.assertFalse(rendered[0][1])
        self.assertEqual(rendered[0][3], 14)
        self.assertEqual(rendered[1], ("Rolled d20", True, 9, 14))
        self.assertEqual(totals, [(9, 5, 14, "DC 14")])
        self.assertEqual(waits, [(0.28, True), (0.42, True)])

    def test_damage_roll_animation_shows_final_total_after_pause(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90074), animate_dice=True)
        rendered: list[tuple[str, bool, list[int]]] = []
        totals: list[tuple[list[int], int]] = []
        game.render_dice_animation_frame = lambda label, rolls, **kwargs: rendered.append((label, kwargs["final"], list(rolls)))
        game.render_roll_animation_total_frame = lambda **kwargs: totals.append((list(kwargs["rolls"]), kwargs["modifier"]))
        game.sleep_for_dice_animation = lambda duration: True
        waits: list[tuple[float, bool]] = []
        game.sleep_for_animation = lambda duration, require_animation=False: waits.append((duration, require_animation)) or False
        game.animate_dice_roll(kind="roll", expression="1d8", sides=8, rolls=[7], modifier=0, display_modifier=3)
        self.assertEqual(len(rendered), 2)
        self.assertEqual(rendered[0][0], "Rolling 1d8")
        self.assertFalse(rendered[0][1])
        self.assertEqual(rendered[1], ("Rolled 1d8", True, [7]))
        self.assertEqual(totals, [([7], 3)])
        self.assertEqual(waits, [(0.28, True), (0.42, True)])

    def test_run_encounter_calls_combat_transition_pause_hook(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        enemy = create_enemy("goblin_skirmisher")
        enemy.current_hp = 0
        enemy.dead = True
        pauses: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9008))
        game.state = GameState(player=player, current_scene="road_ambush")
        game.pause_for_combat_transition = lambda: pauses.append("pause")
        outcome = game.run_encounter(Encounter(title="Spent Ambush", description="The danger is already over.", enemies=[enemy]))
        self.assertEqual(outcome, "victory")
        self.assertEqual(pauses, ["pause", "pause"])

    def test_run_encounter_starts_combat_music_and_restores_scene_music(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        enemy = create_enemy("goblin_skirmisher")
        enemy.current_hp = 0
        enemy.dead = True
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90081))
        game.state = GameState(player=player, current_scene="forge_of_spells")
        game.pause_for_combat_transition = lambda: None
        calls: list[tuple[str, object]] = []
        game.play_encounter_music = lambda encounter: calls.append(
            ("encounter", game.encounter_music_context(encounter))
        )
        game.refresh_scene_music = lambda default_to_menu=False: calls.append(("scene", default_to_menu))

        outcome = game.run_encounter(
            Encounter(
                title="Boss: Test Fight",
                description="The danger is already over.",
                enemies=[enemy],
                allow_post_combat_random_encounter=False,
            )
        )

        self.assertEqual(outcome, "victory")
        self.assertEqual(calls, [("encounter", "boss_combat"), ("scene", False)])

    def test_run_encounter_starts_combat_music_after_description(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        enemy = create_enemy("goblin_skirmisher")
        enemy.current_hp = 0
        enemy.dead = True
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900811))
        game.state = GameState(player=player, current_scene="road_ambush")
        events: list[tuple[str, str]] = []
        game.banner = lambda title: events.append(("banner", title))
        game.say = lambda text, **_: events.append(("say", text))
        game.pause_for_combat_transition = lambda: events.append(("pause", "combat"))
        game.play_encounter_music = lambda encounter: events.append(("music", game.encounter_music_context(encounter)))
        game.refresh_scene_music = lambda default_to_menu=False: events.append(("scene", str(default_to_menu)))

        game.run_encounter(
            Encounter(
                title="Road Ambush",
                description="A shadow lunges at you from the ditch.",
                enemies=[enemy],
                allow_post_combat_random_encounter=False,
            )
        )

        self.assertLess(events.index(("say", "A shadow lunges at you from the ditch.")), events.index(("music", "combat")))
        self.assertLess(events.index(("music", "combat")), events.index(("pause", "combat")))

    def test_start_new_game_keeps_main_menu_music_context(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90082))
        calls: list[tuple[str, bool]] = []
        game.play_music_for_context = lambda context, restart=False: calls.append((context, restart))
        game.banner = lambda title: None
        game.choose = lambda *args, **kwargs: (_ for _ in ()).throw(self._SceneExit())

        with self.assertRaises(self._SceneExit):
            game.start_new_game()

        self.assertEqual(calls, [("main_menu", False)])

    def test_apply_damage_triggers_health_bar_animation_on_hp_loss(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90085))
        seen: list[tuple[int, int]] = []
        game.animate_health_bar_loss = lambda target, previous_hp, new_hp: seen.append((previous_hp, new_hp))
        actual = game.apply_damage(player, 3)
        self.assertEqual(actual, 3)
        self.assertEqual(seen, [(player.max_hp, player.max_hp - 3)])

    def test_health_bar_animation_skip_jumps_to_final_value(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=input, output_fn=print, rng=random.Random(90086))
        game.pace_output = True
        buffer = io.StringIO()
        calls = iter([False, True])
        game.sleep_for_animation = lambda duration, require_animation=False: next(calls, True)
        with patch("dnd_game.gameplay.base.sys.stdout", buffer):
            game.animate_health_bar_loss(player, player.max_hp, player.max_hp - 4)
        rendered = strip_ansi(buffer.getvalue())
        self.assertIn(f"{player.max_hp - 4}/{player.max_hp}", rendered)

    def test_collect_loot_reveals_each_drop_with_pause_hook(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90082))
        game.state = GameState(player=player, current_scene="road_ambush", inventory={})
        pauses: list[str] = []
        game.pause_for_loot_reveal = lambda: pauses.append("pause")
        with patch("dnd_game.gameplay.inventory_core.roll_loot_for_enemy", return_value={"bread_round": 1, "potion_healing": 1}):
            game.collect_loot([create_enemy("bandit")], source="Roadside Ambush")
        self.assertEqual(pauses, ["pause", "pause"])

    def test_encounter_scaling_adds_minimum_enemies_for_three_member_party(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companions = [create_kaelis_starling(), create_elira_dawnmantle()]
        for member in [player, *companions]:
            member.level = 3
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90094))
        game.state = GameState(player=player, companions=companions, current_scene="road_ambush")
        encounter = Encounter(
            title="Scaling Probe",
            description="A small fight should grow for a three-member party.",
            enemies=[create_enemy("goblin_skirmisher")],
            allow_post_combat_random_encounter=False,
        )

        game.prepare_encounter_for_party(encounter)

        self.assertEqual(len(encounter.enemies), 3)
        self.assertEqual(encounter.enemies[0].level, 3)
        self.assertGreater(encounter.enemies[0].max_hp, 6)
        self.assertGreater(encounter.enemies[0].xp_value, 50)
        self.assertTrue(any("Added by party-size encounter scaling." in note for enemy in encounter.enemies[1:] for note in enemy.notes))

    def test_encounter_scaling_raises_two_enemies_when_four_or_more_are_present(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companions = [create_kaelis_starling(), create_elira_dawnmantle()]
        for member in [player, *companions]:
            member.level = 4
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90095))
        game.state = GameState(player=player, companions=companions, current_scene="road_ambush")
        encounter = Encounter(
            title="Large Scaling Probe",
            description="A larger fight should scale two enemies.",
            enemies=[
                create_enemy("bandit"),
                create_enemy("goblin_skirmisher"),
                create_enemy("wolf"),
                create_enemy("brand_saboteur"),
            ],
            allow_post_combat_random_encounter=False,
        )

        game.prepare_encounter_for_party(encounter)

        scaled = [enemy for enemy in encounter.enemies if any(note.startswith("Pseudo-scaled") for note in enemy.notes)]
        self.assertEqual(len(scaled), 2)
        self.assertTrue(all(enemy.level == 4 for enemy in scaled))

    def test_scaled_enemy_rewards_are_paid_from_encounter_victory(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companions = [create_kaelis_starling(), create_elira_dawnmantle()]
        for member in [player, *companions]:
            member.level = 3
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90096))
        game.state = GameState(player=player, companions=companions, current_scene="road_ambush", inventory={})
        encounter = Encounter(
            title="Scaled Reward Probe",
            description="Scaled enemies should pay scaled rewards.",
            enemies=[create_enemy("bandit")],
            allow_post_combat_random_encounter=False,
        )
        game.prepare_encounter_for_party(encounter)
        expected_xp = sum(enemy.xp_value for enemy in encounter.enemies)
        expected_gold = sum(enemy.gold_value for enemy in encounter.enemies)
        for enemy in encounter.enemies:
            enemy.current_hp = 0

        game.resolve_encounter_victory(encounter, encounter.enemies)

        self.assertEqual(game.state.xp, expected_xp)
        self.assertEqual(game.state.gold, expected_gold)

    def test_act2_enemy_archetypes_have_loot_tables(self) -> None:
        required_tables = {
            "cult_lookout",
            "choir_adept",
            "expedition_reaver",
            "grimlock_tunneler",
            "starblighted_miner",
            "animated_armor",
            "spectral_foreman",
            "blacklake_pincerling",
            "caldra_voss",
        }
        self.assertLessEqual(required_tables, set(LOOT_TABLES))
        for archetype in required_tables:
            self.assertTrue(LOOT_TABLES[archetype])
            self.assertTrue(any(ITEMS[entry.item_id].is_equippable() for entry in LOOT_TABLES[archetype]))

    def test_speaker_introduces_new_named_npc_once(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(90083))
        game.state = GameState(player=player, current_scene="neverwinter_briefing")
        game.speaker("Mira Thann", "The road south is failing.")
        game.speaker("Mira Thann", "We need it secured.")
        rendered = self.plain_output(log)
        self.assertEqual(rendered.count("Mira Thann is a sharp-eyed Neverwinter officer"), 1)

    def test_run_encounter_introduces_unique_enemy_before_fight(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        enemy = create_enemy("rukhar")
        enemy.current_hp = 0
        enemy.dead = True
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(90084))
        game.state = GameState(player=player, current_scene="ashfall_watch")
        outcome = game.run_encounter(Encounter(title="Rukhar Test", description="The sergeant waits in smoke.", enemies=[enemy]))
        self.assertEqual(outcome, "victory")
        rendered = self.plain_output(log)
        self.assertIn("Rukhar Cinderfang is a broad hobgoblin sergeant", rendered)

    def test_phandalin_arrival_action_choice_renders_as_action_not_speech(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["3", "10", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(90081))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            clues=["one", "two"],
            flags={"miners_exchange_lead": True},
        )
        game.skill_check = lambda actor, skill, dc, context: False
        game.scene_phandalin_hub()
        rendered = self.plain_output(log)
        self.assertIn("*Show me the tracks, barricades, and weak points first.", rendered)
        self.assertNotIn('Velkor: "Show me the tracks, barricades, and weak points first."', rendered)

    def test_map_state_initializes_for_phandalin_hub(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90082))
        game.state = GameState(player=player, current_scene="phandalin_hub", flags={"phandalin_arrived": True})
        game.ensure_state_integrity()
        map_state = game.state.flags["map_state"]
        self.assertEqual(map_state["current_node_id"], "phandalin_hub")
        self.assertIsNone(map_state["current_dungeon_id"])
        self.assertIn("wayside_luck_shrine", map_state["visited_nodes"])
        self.assertIn("greywake_triage_yard", map_state["visited_nodes"])
        self.assertIn("greywake_road_breakout", map_state["visited_nodes"])
        self.assertIn("neverwinter_briefing", map_state["visited_nodes"])
        self.assertIn("high_road_ambush", map_state["visited_nodes"])
        self.assertIn("phandalin_hub", map_state["visited_nodes"])
        self.assertEqual(map_state["node_history"], ["neverwinter_briefing", "high_road_ambush"])

        rendered_map = build_overworld_panel_text(
            ACT1_HYBRID_MAP,
            DraftMapState(
                current_node_id=map_state["current_node_id"],
                visited_nodes=set(map_state["visited_nodes"]),
            ),
        )
        self.assertIn("WAYSIDE", rendered_map)
        self.assertIn("GREYWAKE", rendered_map)
        self.assertIn("BREAKOUT", rendered_map)
        self.assertIn("NEVERWINTER", rendered_map)
        self.assertIn("HIGH ROAD", rendered_map)
        self.assertIn("(  PHANDALIN  )", rendered_map)

    def test_act1_overworld_map_places_blackwake_as_right_branch_from_neverwinter(self) -> None:
        rendered_map = build_overworld_panel_text(
            ACT1_HYBRID_MAP,
            DraftMapState(
                current_node_id="neverwinter_briefing",
                visited_nodes=set(ACT1_HYBRID_MAP.nodes),
            ),
        )
        lines = rendered_map.splitlines()

        def token_position(token: str) -> tuple[int, int]:
            for row_index, line in enumerate(lines):
                column = line.find(token)
                if column != -1:
                    return row_index, column
            raise AssertionError(f"{token} was not rendered in the overworld map")

        neverwinter_row, neverwinter_column = token_position("NEVERWINTER")
        blackwake_row, blackwake_column = token_position("BLACKWAKE")
        road_choice_row, road_choice_column = token_position("ROAD CHOICE")
        high_road_row, high_road_column = token_position("HIGH ROAD")
        phandalin_row, phandalin_column = token_position("PHANDALIN")

        self.assertGreater(blackwake_column, neverwinter_column)
        self.assertGreater(road_choice_column, high_road_column)
        self.assertGreater(blackwake_row, neverwinter_row)
        self.assertLess(blackwake_row, high_road_row)
        self.assertAlmostEqual(high_road_column, neverwinter_column, delta=6)
        self.assertAlmostEqual(phandalin_column, high_road_column, delta=4)

    def test_act1_overworld_map_uses_fixed_grid_alignment(self) -> None:
        rendered_map = build_overworld_panel_text(
            ACT1_HYBRID_MAP,
            DraftMapState(
                current_node_id="neverwinter_briefing",
                visited_nodes=set(ACT1_HYBRID_MAP.nodes),
            ),
        )
        rendered_lines = rendered_map.splitlines()
        sidebar_column = min(
            (line.find("Route Key") for line in rendered_lines if line.find("Route Key") != -1),
            default=None,
        )
        map_lines = []
        for line in rendered_lines:
            if line.startswith("| "):
                map_lines.append(line[:sidebar_column] if sidebar_column is not None else line)

        def token_span(label: str) -> tuple[int, int, int, int]:
            for row_index, line in enumerate(map_lines):
                label_column = line.find(label)
                if label_column == -1:
                    continue
                left = max(line.rfind("[", 0, label_column), line.rfind("(", 0, label_column))
                right_candidates = [
                    index
                    for index in (line.find("]", label_column), line.find(")", label_column))
                    if index != -1
                ]
                assert right_candidates
                right = min(right_candidates)
                return row_index, left, right, (left + right) // 2
            raise AssertionError(f"{label} was not rendered in the overworld map")

        self.assertEqual(len({len(line) for line in map_lines}), 1)

        wayside_row, _, _, wayside_center = token_span("WAYSIDE")
        greywake_row, _, _, greywake_center = token_span("GREYWAKE")
        breakout_row, _, _, breakout_center = token_span("BREAKOUT")
        neverwinter_row, neverwinter_left, neverwinter_right, neverwinter_center = token_span("NEVERWINTER")
        high_road_row, _, _, high_road_center = token_span("HIGH ROAD")
        phandalin_row, _, _, phandalin_center = token_span("PHANDALIN")
        blackwake_row, _, _, blackwake_center = token_span("BLACKWAKE")
        road_choice_row, _, _, road_choice_center = token_span("ROAD CHOICE")

        token_widths = []
        for line in map_lines:
            for match in re.finditer(r"[\[(][^\])]+[\])]", line):
                token_widths.append(len(match.group(0)))
        self.assertEqual(set(token_widths), {neverwinter_right - neverwinter_left + 1})

        self.assertEqual(wayside_center, greywake_center)
        self.assertEqual(greywake_center, breakout_center)
        self.assertEqual(breakout_center, neverwinter_center)
        self.assertLess(wayside_row, greywake_row)
        self.assertLess(greywake_row, breakout_row)
        self.assertLess(breakout_row, neverwinter_row)
        self.assertEqual(neverwinter_center, high_road_center)
        self.assertEqual(high_road_center, phandalin_center)
        self.assertGreater(blackwake_center, neverwinter_center)
        self.assertEqual(blackwake_center, road_choice_center)
        for row in map_lines[neverwinter_row + 1 : high_road_row]:
            self.assertIn(row[neverwinter_center], {"|", "+"})
        self.assertIn("-", map_lines[high_road_row][high_road_center + 1 : road_choice_center])

    @unittest.skipUnless(RICH_AVAILABLE, "Rich rendering is optional")
    def test_rich_act1_overworld_map_preserves_fixed_grid_alignment(self) -> None:
        state = DraftMapState(
            current_node_id="neverwinter_briefing",
            visited_nodes=set(ACT1_HYBRID_MAP.nodes),
            flags={
                "act1_started",
                "wayside_luck_shrine_seen",
                "greywake_triage_yard_seen",
                "greywake_breakout_resolved",
                "road_ambush_cleared",
                "phandalin_arrived",
            },
        )
        rendered_lines = [
            strip_ansi(line)
            for line in render_rich_lines(build_overworld_panel(ACT1_HYBRID_MAP, state), width=140)
        ]

        def token_center(label: str) -> tuple[int, int]:
            for row_index, line in enumerate(rendered_lines):
                label_column = line.find(label)
                if label_column == -1:
                    continue
                left = max(line.rfind("[", 0, label_column), line.rfind("(", 0, label_column))
                right_candidates = [index for index in (line.find("]", label_column), line.find(")", label_column)) if index != -1]
                assert right_candidates
                return row_index, (left + min(right_candidates)) // 2
            raise AssertionError(f"{label} was not rendered in the rich overworld map")

        self.assertEqual(len({len(line) for line in rendered_lines}), 1)
        wayside_row, wayside_center = token_center("WAYSIDE")
        greywake_row, greywake_center = token_center("GREYWAKE")
        breakout_row, breakout_center = token_center("BREAKOUT")
        neverwinter_row, neverwinter_center = token_center("NEVERWINTER")
        high_road_row, high_road_center = token_center("HIGH ROAD")
        phandalin_row, phandalin_center = token_center("PHANDALIN")
        _, blackwake_center = token_center("BLACKWAKE")

        self.assertEqual(wayside_center, greywake_center)
        self.assertEqual(greywake_center, breakout_center)
        self.assertEqual(breakout_center, neverwinter_center)
        self.assertEqual(neverwinter_center, high_road_center)
        self.assertEqual(high_road_center, phandalin_center)
        self.assertLess(wayside_row, greywake_row)
        self.assertLess(greywake_row, breakout_row)
        self.assertLess(breakout_row, neverwinter_row)
        self.assertLess(neverwinter_row, high_road_row)
        self.assertLess(high_road_row, phandalin_row)
        self.assertGreater(blackwake_center, neverwinter_center)

    def test_act1_overworld_panel_groups_route_key_and_travel_top_right(self) -> None:
        rendered_map = build_overworld_panel_text(
            ACT1_HYBRID_MAP,
            DraftMapState(
                current_node_id="neverwinter_briefing",
                visited_nodes={"neverwinter_briefing"},
            ),
        )
        lines = rendered_map.splitlines()

        def token_position(token: str) -> tuple[int, int]:
            for row_index, line in enumerate(lines):
                column = line.find(token)
                if column != -1:
                    return row_index, column
            raise AssertionError(f"{token} was not rendered in the overworld panel")

        neverwinter_row, neverwinter_column = token_position("NEVERWINTER")
        route_key_row, route_key_column = token_position("Route Key")
        travel_row, travel_column = token_position("Travel")
        empty_travel_row, empty_travel_column = token_position("- No unlocked travel from here")

        self.assertLessEqual(route_key_row, neverwinter_row + 1)
        self.assertGreater(route_key_column, neverwinter_column)
        self.assertGreater(travel_row, route_key_row)
        self.assertAlmostEqual(travel_column, route_key_column, delta=2)
        self.assertGreater(empty_travel_row, travel_row)
        self.assertGreaterEqual(empty_travel_column, travel_column)

    def test_blackwake_map_nodes_and_dungeon_exist(self) -> None:
        self.assertIn("blackwake_crossing", ACT1_HYBRID_MAP.nodes)
        self.assertIn("road_decision_post_blackwake", ACT1_HYBRID_MAP.nodes)
        self.assertIn("blackwake_crossing_branch", ACT1_HYBRID_MAP.dungeons)

        dungeon = ACT1_HYBRID_MAP.dungeons["blackwake_crossing_branch"]
        self.assertEqual(dungeon.entrance_room_id, "charred_tollhouse")
        self.assertEqual(dungeon.exit_to_node_id, "road_decision_post_blackwake")
        self.assertIn("millers_ford_flooded_approach", dungeon.rooms["charred_tollhouse"].exits)
        self.assertIn("gallows_hanging_path", dungeon.rooms["charred_tollhouse"].exits)
        self.assertEqual(dungeon.rooms["floodgate_chamber"].encounter_key, "sereth_vane_boss")

    def test_phandalin_arrival_mentions_blackwake_resolution_once(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(9201))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            flags={
                "blackwake_completed": True,
                "blackwake_resolution": "evidence",
                "blackwake_sereth_fate": "escaped",
            },
        )

        def choose_once(prompt, options, **kwargs):
            if prompt == "How do you enter town?":
                return 1
            raise self._SceneExit()

        game.scenario_choice = choose_once  # type: ignore[method-assign]
        game.skill_check = lambda actor, skill, dc, context: True
        with self.assertRaises(self._SceneExit):
            game.scene_phandalin_hub()
        rendered = self.plain_output(log)
        self.assertIn("The copied seals and ledgers from Blackwake", rendered)
        self.assertIn("Sereth Vane's name", rendered)
        self.assertTrue(game.state.flags["phandalin_blackwake_arrival_seen"])

    def blackwake_finale_game(
        self,
        *,
        final_choice: int,
        companions=None,
        encounter_outcome: str = "victory",
        flags: dict[str, object] | None = None,
    ):
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        player.inventory.clear()
        companion_list = list(companions or [])
        for companion in companion_list:
            companion.inventory.clear()
        log: list[str] = []
        base_flags: dict[str, object] = {
            "act1_started": True,
            "blackwake_started": True,
            "blackwake_ash_office_searched": True,
        }
        if flags:
            base_flags.update(flags)
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(9206 + final_choice))
        game.state = GameState(
            player=player,
            companions=companion_list,
            current_scene="blackwake_crossing",
            inventory={},
            flags=base_flags,
        )
        game.ensure_state_integrity()
        game.grant_quest("trace_blackwake_cell")

        def choose_finale_option(prompt, options, **kwargs):
            if prompt == "Sereth waits to see whether this becomes bargain, threat, or blood.":
                return len(options)
            if prompt == "The chamber is collapsing into smoke, shouting, and floodwater. What matters most now?":
                return final_choice
            raise AssertionError(f"Unexpected prompt: {prompt}")

        game.scenario_choice = choose_finale_option  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounter_outcome  # type: ignore[method-assign]
        dungeon = ACT1_HYBRID_MAP.dungeons["blackwake_crossing_branch"]
        game._blackwake_floodgate_chamber(dungeon, dungeon.rooms["floodgate_chamber"])
        return game, log

    def test_blackwake_floodgate_rescue_resolution_sets_people_first_flags(self) -> None:
        elira = create_elira_dawnmantle()
        rhogar = create_rhogar_valeguard()
        game, _ = self.blackwake_finale_game(final_choice=1, companions=[elira, rhogar])

        self.assertEqual(game.state.current_scene, "road_decision_post_blackwake")
        self.assertTrue(game.state.flags["blackwake_completed"])
        self.assertEqual(game.state.flags["blackwake_resolution"], "rescue")
        self.assertEqual(game.state.flags["blackwake_sereth_fate"], "dead")
        self.assertEqual(game.state.inventory["potion_healing"], 1)
        self.assertEqual(game.state.gold, 8)
        self.assertEqual(elira.disposition, 2)
        self.assertEqual(rhogar.disposition, 1)
        self.assertEqual(game.state.quests["trace_blackwake_cell"].status, "ready_to_turn_in")

    def test_blackwake_floodgate_evidence_resolution_sets_proof_flags(self) -> None:
        bryn = create_bryn_underbough()
        elira = create_elira_dawnmantle()
        game, _ = self.blackwake_finale_game(final_choice=2, companions=[bryn, elira])

        self.assertTrue(game.state.flags["blackwake_completed"])
        self.assertEqual(game.state.flags["blackwake_resolution"], "evidence")
        self.assertTrue(game.state.flags["blackwake_evidence_secured"])
        self.assertTrue(game.state.flags["blackwake_ledgers_secured"])
        self.assertEqual(game.state.gold, 22)
        self.assertEqual(bryn.disposition, 1)
        self.assertEqual(elira.disposition, -1)
        self.assertTrue(any("organized route corruption" in clue for clue in game.state.clues))

    def test_blackwake_floodgate_sabotage_resolution_weakens_supply_line(self) -> None:
        kaelis = create_kaelis_starling()
        bryn = create_bryn_underbough()
        game, _ = self.blackwake_finale_game(final_choice=3, companions=[kaelis, bryn])

        self.assertTrue(game.state.flags["blackwake_completed"])
        self.assertEqual(game.state.flags["blackwake_resolution"], "sabotage")
        self.assertTrue(game.state.flags["blackwake_cache_sabotaged"])
        self.assertEqual(game.act1_metric_value("act1_ashen_strength"), 2)
        self.assertTrue(game.act1_relay_sabotaged())
        self.assertEqual(game.state.inventory["antitoxin_vial"], 1)
        self.assertEqual(kaelis.disposition, 1)
        self.assertEqual(bryn.disposition, -1)

    def test_blackwake_floodgate_flee_marks_sereth_escaped(self) -> None:
        game, _ = self.blackwake_finale_game(final_choice=1, encounter_outcome="fled")

        self.assertEqual(game.state.current_scene, "road_decision_post_blackwake")
        self.assertTrue(game.state.flags["blackwake_completed"])
        self.assertEqual(game.state.flags["blackwake_sereth_fate"], "escaped")
        self.assertNotIn("blackwake_resolution", game.state.flags)
        self.assertEqual(game.state.quests["trace_blackwake_cell"].status, "ready_to_turn_in")

    def test_blackwake_contract_house_intel_corners_sereth_without_skill_check(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9220))
        game.state = GameState(
            player=player,
            current_scene="blackwake_crossing",
            flags={
                "act1_started": True,
                "blackwake_started": True,
                "neverwinter_private_room_intel": True,
            },
        )
        game.grant_quest("trace_blackwake_cell")

        def fail_skill_check(actor, skill, dc, context):
            raise AssertionError("Contract-house Blackwake option should not require a skill check")

        def choose_contract_house(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "Sereth waits to see whether this becomes bargain, threat, or blood.":
                return self.option_index_containing(options, "CONTRACT HOUSE INTEL")
            if prompt == "The chamber is collapsing into smoke, shouting, and floodwater. What matters most now?":
                return self.option_index_containing(options, "Secure the ledgers")
            raise AssertionError(prompt)

        captured: list[Encounter] = []
        game.skill_check = fail_skill_check
        game.scenario_choice = choose_contract_house  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: captured.append(encounter) or "victory"  # type: ignore[method-assign]
        game.resolve_level_ups = lambda: None  # type: ignore[method-assign]
        dungeon = ACT1_HYBRID_MAP.dungeons["blackwake_crossing_branch"]

        game._blackwake_floodgate_chamber(dungeon, dungeon.rooms["floodgate_chamber"])

        self.assertTrue(game.state.flags["blackwake_sereth_cornered_by_contract_house"])
        self.assertEqual(game.state.flags["blackwake_sereth_fate"], "captured")
        self.assertEqual(captured[0].enemies[0].conditions.get("reeling"), 2)
        self.assertTrue(any("Sereth Vane's Blackwake command line" in clue for clue in game.state.clues))

    def test_mira_report_mobilizes_contract_house_witnesses(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(9221))
        game.state = GameState(
            player=player,
            current_scene="road_decision_post_blackwake",
            flags={
                "act1_started": True,
                "blackwake_started": True,
                "blackwake_completed": True,
                "blackwake_resolution": "evidence",
                "blackwake_sereth_fate": "captured",
                "neverwinter_private_room_intel": True,
            },
        )
        game.resolve_level_ups = lambda: None  # type: ignore[method-assign]
        game.grant_quest("trace_blackwake_cell")

        game.scene_road_decision_post_blackwake()

        self.assertTrue(game.state.flags["neverwinter_contract_house_blackwake_reported"])
        self.assertTrue(game.state.flags["neverwinter_contract_house_political_callback"])
        self.assertEqual(game.state.quests["trace_blackwake_cell"].status, "completed")
        rendered = self.plain_output(log)
        self.assertIn("Sabra Kestrel", rendered)
        self.assertIn("Oren Vale", rendered)
        self.assertIn("Vessa Marr", rendered)
        self.assertIn("Garren Flint", rendered)
        self.assertIn("Neverwinter political pressure", " ".join(game.state.journal))

    def blackwake_navigation_game(
        self,
        *,
        route_titles: list[str],
        room_choices: dict[str, int],
        final_choice: int,
    ):
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        player.inventory.clear()
        log: list[str] = []
        encounters: list[Encounter] = []
        route_iter = iter(route_titles)
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(9210 + final_choice))
        game.state = GameState(
            player=player,
            current_scene="blackwake_crossing",
            inventory={},
            flags={"act1_started": True, "blackwake_started": True},
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        def choose_route(prompt: str, options: list[str], **kwargs) -> int:
            plain_options = [strip_ansi(option) for option in options]
            if prompt.startswith("What do you do from "):
                target = next(route_iter)
                for index, option in enumerate(plain_options, start=1):
                    if target in option:
                        return index
                raise AssertionError(f"Could not find route target {target!r} in {plain_options!r}")
            if prompt == "Sereth waits to see whether this becomes bargain, threat, or blood.":
                for index, option in enumerate(plain_options, start=1):
                    if "Confront Sereth" in option:
                        return index
                return len(options)
            if prompt == "The chamber is collapsing into smoke, shouting, and floodwater. What matters most now?":
                return final_choice
            for key, choice in room_choices.items():
                if key in prompt:
                    return choice
            raise AssertionError(f"Unexpected Blackwake prompt: {prompt}")

        game.scenario_choice = choose_route  # type: ignore[method-assign]
        game.scene_blackwake_crossing()
        return game, encounters, log

    def test_blackwake_navigation_can_finish_with_millers_ford_only(self) -> None:
        game, encounters, _ = self.blackwake_navigation_game(
            route_titles=[
                "Flooded Approach",
                "Reedbank Camp",
                "Ford Ledger Post",
                "Outer Cache",
                "Seal Workshop",
                "Ash Office",
                "Floodgate Chamber",
            ],
            room_choices={
                "burned tollhouse": 1,
                "Miller's Ford": 1,
                "forged checkpoint tent": 3,
                "ledger post": 4,
                "outer cache": 2,
                "forgery workshop": 1,
                "record do you focus": 2,
            },
            final_choice=2,
        )

        self.assertEqual(game.state.current_scene, "road_decision_post_blackwake")
        self.assertTrue(game.state.flags["blackwake_completed"])
        self.assertEqual(game.state.flags["blackwake_resolution"], "evidence")
        self.assertTrue(game.state.flags["blackwake_forged_papers_found"])
        self.assertNotIn("blackwake_transfer_list_found", game.state.flags)
        self.assertEqual(game.state.flags["blackwake_sereth_fate"], "captured")
        self.assertEqual([encounter.title for encounter in encounters], ["Charred Tollhouse Breakout", "Boss: Sereth Vane"])
        self.assertCountEqual(
            game.state.flags["map_state"]["cleared_rooms"],
            [
                "charred_tollhouse",
                "millers_ford_flooded_approach",
                "reedbank_camp",
                "ford_ledger_post",
                "outer_cache",
                "seal_workshop",
                "ash_office",
                "floodgate_chamber",
            ],
        )

    def test_blackwake_navigation_can_finish_with_gallows_copse_only(self) -> None:
        game, encounters, _ = self.blackwake_navigation_game(
            route_titles=[
                "Hanging Path",
                "Cage Clearing",
                "Root Cellar Hollow",
                "Outer Cache",
                "Prison Pens",
                "Ash Office",
                "Floodgate Chamber",
            ],
            room_choices={
                "burned tollhouse": 4,
                "hanging path": 3,
                "captives": 1,
                "root cellar hollow": 2,
                "outer cache": 1,
                "prisoners": 1,
                "record do you focus": 3,
            },
            final_choice=1,
        )

        self.assertEqual(game.state.current_scene, "road_decision_post_blackwake")
        self.assertTrue(game.state.flags["blackwake_completed"])
        self.assertEqual(game.state.flags["blackwake_resolution"], "rescue")
        self.assertTrue(game.state.flags["blackwake_transfer_list_found"])
        self.assertNotIn("blackwake_forged_papers_found", game.state.flags)
        self.assertEqual(game.state.flags["blackwake_sereth_fate"], "captured")
        self.assertEqual([encounter.title for encounter in encounters], ["Blackwake Outer Cache", "Boss: Sereth Vane"])
        self.assertCountEqual(
            game.state.flags["map_state"]["cleared_rooms"],
            [
                "charred_tollhouse",
                "gallows_hanging_path",
                "cage_clearing",
                "root_cellar_hollow",
                "outer_cache",
                "prison_pens",
                "ash_office",
                "floodgate_chamber",
            ],
        )

    def test_blackwake_room_resolution_flows_directly_into_navigation_prompt(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["1"])

        def fake_input(_: str) -> str:
            try:
                return next(answers)
            except StopIteration as exc:
                raise self._SceneExit() from exc

        game = TextDnDGame(input_fn=fake_input, output_fn=log.append, rng=random.Random(9217))
        game.state = GameState(
            player=player,
            current_scene="blackwake_crossing",
            flags={"act1_started": True, "blackwake_started": True},
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: "victory"  # type: ignore[method-assign]
        with self.assertRaises(self._SceneExit):
            game.scene_blackwake_crossing()
        rendered = self.plain_output(log)
        scene_index = rendered.rfind("Two routes remain readable through the damage")
        prompt_index = rendered.rfind("What do you do from Charred Tollhouse?")
        self.assertNotEqual(scene_index, -1)
        self.assertNotEqual(prompt_index, -1)
        between = rendered[scene_index:prompt_index]
        self.assertNotIn("=== Blackwake Crossing ===", between)
        self.assertNotIn("Current room:", between)
        self.assertNotIn("Blackwake Crossing --------------------------------", between)

    def test_blackwake_entry_renders_dungeon_map_before_first_room_scene(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []

        def fake_input(_: str) -> str:
            raise self._SceneExit()

        game = TextDnDGame(input_fn=fake_input, output_fn=log.append, rng=random.Random(92171))
        game.state = GameState(
            player=player,
            current_scene="blackwake_crossing",
            flags={"act1_started": True, "blackwake_started": True},
        )
        game.ensure_state_integrity()
        with self.assertRaises(self._SceneExit):
            game.scene_blackwake_crossing()
        rendered = self.plain_output(log)
        compass_index = rendered.find("NORTH")
        map_index = rendered.find("Current room: Charred Tollhouse")
        scene_index = rendered.find("The tollhouse at the river cut")
        prompt_index = rendered.find("What do you do first at the burned tollhouse?")
        self.assertNotEqual(compass_index, -1)
        self.assertNotEqual(map_index, -1)
        self.assertNotEqual(scene_index, -1)
        self.assertNotEqual(prompt_index, -1)
        self.assertLess(compass_index, scene_index)
        self.assertLess(map_index, scene_index)
        self.assertLess(scene_index, prompt_index)
        self.assert_dungeon_map_header_is_balanced(rendered)

    def test_act2_room_resolution_flows_directly_into_navigation_prompt(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["1"])

        def fake_input(_: str) -> str:
            try:
                return next(answers)
            except StopIteration as exc:
                raise self._SceneExit() from exc

        game = TextDnDGame(input_fn=fake_input, output_fn=log.append, rng=random.Random(9218))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="stonehollow_dig",
            flags={
                "act2_started": True,
                "act2_town_stability": 3,
                "act2_route_control": 2,
                "act2_whisper_pressure": 2,
            },
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        with self.assertRaises(self._SceneExit):
            game.scene_stonehollow_dig()
        rendered = self.plain_output(log)
        scene_index = rendered.rfind("You mark the honest braces and the whole entry stops feeling like a mouth about to\nclose.")
        prompt_index = rendered.rfind("What do you do from Survey Mouth?")
        self.assertNotEqual(scene_index, -1)
        self.assertNotEqual(prompt_index, -1)
        between = rendered[scene_index:prompt_index]
        self.assertNotIn("=== Stonehollow Dig ===", between)
        self.assertNotIn("Current room:", between)
        self.assertNotIn("Act II Pressures", between)

    def test_act2_entry_renders_dungeon_map_before_first_room_scene(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []

        def fake_input(_: str) -> str:
            raise self._SceneExit()

        game = TextDnDGame(input_fn=fake_input, output_fn=log.append, rng=random.Random(92181))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="stonehollow_dig",
            flags={
                "act2_started": True,
                "act2_town_stability": 3,
                "act2_route_control": 2,
                "act2_whisper_pressure": 2,
            },
        )
        game.ensure_state_integrity()
        with self.assertRaises(self._SceneExit):
            game.scene_stonehollow_dig()
        rendered = self.plain_output(log)
        compass_index = rendered.find("NORTH")
        map_index = rendered.find("Current room: Survey Mouth")
        scene_index = rendered.find("Stonehollow is a half-legitimate dig site")
        prompt_index = rendered.find("How do you take the first measure of the dig?")
        self.assertNotEqual(compass_index, -1)
        self.assertNotEqual(map_index, -1)
        self.assertNotEqual(scene_index, -1)
        self.assertNotEqual(prompt_index, -1)
        self.assertLess(compass_index, scene_index)
        self.assertLess(map_index, scene_index)
        self.assertLess(scene_index, prompt_index)
        self.assert_dungeon_map_header_is_balanced(rendered)

    def test_map_requirement_supports_flag_count_groups(self) -> None:
        requirement = Requirement(
            flag_count_requirements=(
                FlagCountRequirement(
                    flags=("agatha_truth_secured", "woodland_survey_cleared", "stonehollow_dig_cleared"),
                    minimum=2,
                ),
            ),
        )

        self.assertFalse(requirement_met(DraftMapState(current_node_id="act2_expedition_hub"), requirement))
        self.assertFalse(
            requirement_met(
                DraftMapState(current_node_id="act2_expedition_hub", flags={"agatha_truth_secured"}),
                requirement,
            )
        )
        self.assertTrue(
            requirement_met(
                DraftMapState(
                    current_node_id="act2_expedition_hub",
                    flags={"agatha_truth_secured", "woodland_survey_cleared"},
                ),
                requirement,
            )
        )

    def test_map_requirement_supports_metric_and_value_checks(self) -> None:
        requirement = Requirement(
            flag_value_requirements=(
                FlagValueRequirement("act2_first_late_route", "broken_prospect"),
            ),
            numeric_flag_requirements=(
                NumericFlagRequirement("act2_whisper_pressure", minimum=4),
            ),
        )

        self.assertFalse(
            requirement_met(
                DraftMapState(
                    current_node_id="forge_of_spells",
                    flag_values={
                        "act2_first_late_route": "south_adit",
                        "act2_whisper_pressure": 5,
                    },
                ),
                requirement,
            )
        )
        self.assertFalse(
            requirement_met(
                DraftMapState(
                    current_node_id="forge_of_spells",
                    flag_values={
                        "act2_first_late_route": "broken_prospect",
                        "act2_whisper_pressure": 3,
                    },
                ),
                requirement,
            )
        )
        self.assertTrue(
            requirement_met(
                DraftMapState(
                    current_node_id="forge_of_spells",
                    flag_values={
                        "act2_first_late_route": "broken_prospect",
                        "act2_whisper_pressure": 4,
                    },
                ),
                requirement,
            )
        )

    def test_old_owl_well_branching_tracks_cleared_rooms(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["1", "1", "2", "1", "1", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(90083))
        game.state = GameState(
            player=player,
            current_scene="old_owl_well",
            flags={"miners_exchange_lead": True},
        )
        game.run_encounter = lambda encounter: "victory"
        game.scene_old_owl_well()
        self.assertEqual(game.state.current_scene, "phandalin_hub")
        self.assertEqual(game.state.flags["map_state"]["current_node_id"], "phandalin_hub")
        self.assertCountEqual(
            game.state.flags["map_state"]["cleared_rooms"],
            ["well_ring", "supply_trench", "gravecaller_lip"],
        )

    def test_old_owl_well_vaelith_miniboss_uses_buffed_encounter_setup(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companions = [create_tolan_ironshield(), create_elira_dawnmantle(), create_kaelis_starling()]
        answers = iter(["1", "1", "2", "1", "1", "1"])
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(900831))
        game.state = GameState(
            player=player,
            companions=companions,
            current_scene="old_owl_well",
            flags={"miners_exchange_lead": True},
        )

        def capture_encounter(encounter):
            encounters.append(encounter)
            return "victory"

        game.run_encounter = capture_encounter  # type: ignore[method-assign]
        game.scene_old_owl_well()
        boss_encounter = next(encounter for encounter in encounters if encounter.title == "Miniboss: Vaelith Marr")
        self.assertTrue(game.state.flags["old_owl_ritual_sabotaged"])
        self.assertEqual(len(boss_encounter.enemies), 3)
        self.assertEqual(boss_encounter.enemies[0].name, "Vaelith Marr")
        self.assertEqual(boss_encounter.enemies[0].archetype, "vaelith_marr")
        self.assertEqual(boss_encounter.enemies[0].current_hp, boss_encounter.enemies[0].max_hp - 4)
        self.assertIn("reeling", boss_encounter.enemies[0].conditions)
        self.assertGreater(boss_encounter.enemies[0].max_hp, 26)
        self.assertTrue(any(enemy.name == "Carrion Lash Crawler" for enemy in boss_encounter.enemies[1:]))

    def test_old_owl_notes_unlock_cinderfall_route_and_reduce_ashen_strength(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900833))
        game.state = GameState(
            player=player,
            current_scene="old_owl_well",
            flags={"miners_exchange_lead": True},
        )
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None
        game.complete_map_room(dungeon, "well_ring")
        game._old_owl_supply_trench(dungeon, dungeon.rooms["supply_trench"])
        self.assertTrue(game.state.flags["hidden_route_unlocked"])
        self.assertTrue(game.state.flags["old_owl_notes_found"])
        self.assertTrue(game.state.flags["varyn_filter_logic_seen"])
        self.assertEqual(game.act1_metric_value("act1_ashen_strength"), 3)
        self.assertTrue(any("Cinderfall" in clue for clue in game.state.clues))

    def test_act1_personal_quests_unlock_for_trusted_companions(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        bryn = create_bryn_underbough()
        bryn.disposition = 3
        elira = create_elira_dawnmantle()
        elira.disposition = 3
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9008331))
        game.state = GameState(player=player, companions=[bryn, elira], current_scene="phandalin_hub")
        game.maybe_offer_act1_personal_quests()
        self.assertIn("bryn_loose_ends", game.state.quests)
        self.assertIn("elira_faith_under_ash", game.state.quests)

    def test_bryn_loose_ends_resolution_completes_quest(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        bryn = create_bryn_underbough()
        starting_disposition = bryn.disposition
        answers = iter(["1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(9008332))
        game.state = GameState(
            player=player,
            companions=[bryn],
            current_scene="phandalin_hub",
            flags={"bryn_cache_found": True, "act1_town_fear": 2},
        )
        game.grant_quest("bryn_loose_ends")
        game.maybe_resolve_bryn_loose_ends()
        self.assertEqual(game.state.quests["bryn_loose_ends"].status, "completed")
        self.assertTrue(game.state.flags["bryn_ledger_burned"])
        self.assertEqual(game.state.flags["act1_town_fear"], 1)
        self.assertGreater(bryn.disposition, starting_disposition)

    def test_cinderfall_conflict_event_splits_bryn_and_rhogar(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        bryn = create_bryn_underbough()
        bryn.disposition = 6
        rhogar = create_rhogar_valeguard()
        rhogar.disposition = 6
        bryn_before = bryn.disposition
        rhogar_before = rhogar.disposition
        answers = iter(["2"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(9008333))
        game.state = GameState(
            player=player,
            companions=[bryn, rhogar],
            current_scene="phandalin_hub",
            flags={"cinderfall_relay_destroyed": True},
        )
        game.maybe_run_act1_companion_conflict()
        self.assertEqual(game.state.flags["act1_companion_conflict_side"], "rhogar")
        self.assertEqual(rhogar.disposition, rhogar_before + 1)
        self.assertEqual(bryn.disposition, bryn_before - 1)

    def test_wyvern_followup_flags_buff_brughor_setup(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "3", output_fn=lambda _: None, rng=random.Random(9008334))
        game.state = GameState(
            player=player,
            companions=[create_tolan_ironshield()],
            current_scene="wyvern_tor",
            flags={"edermath_orchard_lead": True},
        )
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None
        answers = iter(["3", "3", "3"])
        encounters: list[Encounter] = []
        game.input_fn = lambda _: next(answers)
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]
        game._wyvern_drover_hollow(dungeon, dungeon.rooms["drover_hollow"])
        game._wyvern_high_shelf(dungeon, dungeon.rooms["high_shelf"])
        boss_encounter = encounters[-1]
        self.assertTrue(game.state.flags["wyvern_beast_stampede"])
        self.assertTrue(game.state.flags["varyn_detour_logic_seen"])
        self.assertIn("surprised", boss_encounter.enemies[1].conditions)
        self.assertLess(boss_encounter.enemies[1].current_hp, boss_encounter.enemies[1].max_hp)

    def test_phandalin_hub_marks_wyvern_tor_as_recommended_level_three_when_underleveled(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        captured: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900832))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            flags={"phandalin_arrived": True, "edermath_orchard_lead": True, "miners_exchange_lead": True},
        )
        game.run_phandalin_council_event = lambda: None  # type: ignore[method-assign]
        game.run_after_watch_gathering = lambda: None  # type: ignore[method-assign]

        def capture_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "Where do you go next?":
                captured.extend(options)
                raise self._SceneExit()
            return 1

        game.scenario_choice = capture_choice  # type: ignore[method-assign]
        with self.assertRaises(self._SceneExit):
            game.scene_phandalin_hub()
        self.assertIn("*Hunt the raiders at Wyvern Tor (recommended level 3)", captured)

    def test_confirm_wyvern_tor_departure_can_cancel_underleveled_trip(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900833))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.scenario_choice = lambda prompt, options, **kwargs: 2  # type: ignore[method-assign]
        self.assertFalse(game.confirm_wyvern_tor_departure())

    def test_tresendar_encounters_scale_up_for_full_party(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companions = [create_tolan_ironshield(), create_elira_dawnmantle(), create_kaelis_starling()]
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900834))
        game.state = GameState(
            player=player,
            companions=companions,
            current_scene="tresendar_manor",
            flags={"tresendar_revealed": True},
        )
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]
        game._tresendar_cellar_intake(dungeon, dungeon.rooms["cellar_intake"])
        game._tresendar_nothic_lair(dungeon, dungeon.rooms["nothic_lair"])
        self.assertEqual(len(encounters[0].enemies), 4)
        self.assertEqual(len(encounters[1].enemies), 3)
        self.assertGreater(encounters[1].enemies[0].max_hp, 29)

    def test_tresendar_nothic_kill_route_records_choice_and_tolan_approval(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        tolan = create_tolan_ironshield()
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9008341))
        game.state = GameState(player=player, companions=[tolan], current_scene="tresendar_manor", flags={"tresendar_revealed": True})
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None
        game.scenario_choice = lambda prompt, options, **kwargs: 1  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        game._tresendar_nothic_lair(dungeon, dungeon.rooms["nothic_lair"])

        self.assertEqual(game.state.flags["tresendar_nothic_route"], "kill")
        self.assertTrue(game.state.flags["tresendar_nothic_tolan_kill_approved"])
        self.assertEqual(tolan.disposition, 1)
        self.assertEqual(len(encounters), 1)

    def test_tresendar_nothic_deception_failure_sets_ambush_fallback(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Charlatan",
            base_ability_scores={"STR": 14, "DEX": 14, "CON": 13, "INT": 10, "WIS": 10, "CHA": 15},
            class_skill_choices=["Athletics", "Survival"],
        )
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "4", output_fn=lambda _: None, rng=random.Random(9008342))
        game.state = GameState(player=player, current_scene="tresendar_manor", flags={"tresendar_revealed": True})
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None
        game.scenario_choice = lambda prompt, options, **kwargs: 4  # type: ignore[method-assign]
        game.skill_check = lambda actor, skill, dc, context: False  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        game._tresendar_nothic_lair(dungeon, dungeon.rooms["nothic_lair"])

        self.assertEqual(game.state.flags["tresendar_nothic_route"], "deceive")
        self.assertTrue(game.state.flags["tresendar_nothic_deception_failed"])
        self.assertEqual(encounters[0].enemy_initiative_bonus, 2)
        self.assertIn("surprised", player.conditions)
        self.assertIn("reeling", player.conditions)

    def test_tresendar_nothic_memory_trade_reads_background_and_costs_player(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Cleric",
            background="Acolyte",
            base_ability_scores={"STR": 10, "DEX": 12, "CON": 13, "INT": 10, "WIS": 15, "CHA": 14},
            class_skill_choices=["Insight", "Medicine"],
        )
        log: list[str] = []
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(9008343))
        game.state = GameState(player=player, current_scene="tresendar_manor", flags={"tresendar_revealed": True})
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None

        def choose_memory_trade(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "The Cistern Eye waits to learn what kind of answer you are.":
                return self.option_index_containing(options, "TRADE")
            if prompt == "What price do you let the Cistern Eye taste?":
                return self.option_index_containing(options, "memory from your own past")
            raise AssertionError(prompt)

        game.scenario_choice = choose_memory_trade  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        game._tresendar_nothic_lair(dungeon, dungeon.rooms["nothic_lair"])

        rendered = self.plain_output(log)
        self.assertIn("You washed blood from temple cloth", rendered)
        self.assertEqual(game.state.flags["tresendar_nothic_route"], "trade")
        self.assertEqual(game.state.flags["tresendar_nothic_trade"], "memory")
        self.assertTrue(game.state.flags["tresendar_nothic_memory_paid"])
        self.assertTrue(game.state.flags["tresendar_nothic_trade_info_gained"])
        self.assertEqual(game.state.flags["deep_ledger_hint_count"], 1)
        self.assertIn("reeling", player.conditions)
        self.assertTrue(any("The Cistern Eye names Emberhall" in clue for clue in game.state.clues))
        self.assertEqual(encounters[0].hero_initiative_bonus, 0)

    def test_tresendar_nothic_self_truth_trade_grants_clear_eyed_wound(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Wizard",
            background="Sage",
            base_ability_scores={"STR": 8, "DEX": 13, "CON": 12, "INT": 15, "WIS": 14, "CHA": 10},
            class_skill_choices=["Arcana", "History"],
        )
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9008344))
        game.state = GameState(player=player, current_scene="tresendar_manor", flags={"tresendar_revealed": True})
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None

        def choose_truth_trade(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "The Cistern Eye waits to learn what kind of answer you are.":
                return self.option_index_containing(options, "TRADE")
            if prompt == "What price do you let the Cistern Eye taste?":
                return self.option_index_containing(options, "truth I keep walking around")
            raise AssertionError(prompt)

        game.scenario_choice = choose_truth_trade  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        game._tresendar_nothic_lair(dungeon, dungeon.rooms["nothic_lair"])

        self.assertEqual(game.state.flags["tresendar_nothic_trade"], "self_truth")
        self.assertTrue(game.state.flags["tresendar_nothic_self_truth_spoken"])
        self.assertEqual(player.story_skill_bonuses, {"Arcana": 1, "Insight": 1, "Persuasion": 1})
        self.assertEqual(encounters[0].hero_initiative_bonus, 1)
        self.assertIn(
            "Clear-Eyed Wound grants +1 Arcana, +1 Insight, and +1 Persuasion through the Act 1 finale.",
            game.state.journal,
        )

    def test_tresendar_nothic_bryn_betrayal_exposes_secret_and_penalizes_active_quest(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        bryn = create_bryn_underbough()
        bryn.disposition = 3
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9008345))
        game.state = GameState(player=player, companions=[bryn], current_scene="tresendar_manor", flags={"tresendar_revealed": True})
        game.ensure_state_integrity()
        game.grant_quest("bryn_loose_ends")
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None

        def choose_bryn_trade(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "The Cistern Eye waits to learn what kind of answer you are.":
                return self.option_index_containing(options, "TRADE")
            if prompt == "What price do you let the Cistern Eye taste?":
                return self.option_index_containing(options, "BETRAY BRYN")
            raise AssertionError(prompt)

        game.scenario_choice = choose_bryn_trade  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        game._tresendar_nothic_lair(dungeon, dungeon.rooms["nothic_lair"])

        self.assertEqual(game.state.flags["tresendar_nothic_trade"], "betray_bryn")
        self.assertTrue(game.state.flags["bryn_secret_exposed"])
        self.assertTrue(game.state.flags["tresendar_nothic_trade_info_gained"])
        self.assertEqual(bryn.disposition, 0)
        self.assertEqual(len(encounters), 1)

    def test_tresendar_nothic_rhogar_betrayal_sets_conflict_arc(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        rhogar = create_rhogar_valeguard()
        rhogar.disposition = 4
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9008346))
        game.state = GameState(player=player, companions=[rhogar], current_scene="tresendar_manor", flags={"tresendar_revealed": True})
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None

        def choose_rhogar_trade(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "The Cistern Eye waits to learn what kind of answer you are.":
                return self.option_index_containing(options, "TRADE")
            if prompt == "What price do you let the Cistern Eye taste?":
                return self.option_index_containing(options, "BETRAY RHOGAR")
            raise AssertionError(prompt)

        game.scenario_choice = choose_rhogar_trade  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        game._tresendar_nothic_lair(dungeon, dungeon.rooms["nothic_lair"])

        self.assertEqual(game.state.flags["tresendar_nothic_trade"], "betray_rhogar")
        self.assertTrue(game.state.flags["rhogar_secret_exposed"])
        self.assertTrue(game.state.flags["rhogar_cistern_conflict_pending"])
        self.assertEqual(rhogar.disposition, 2)
        self.assertEqual(len(encounters), 1)

    def test_tresendar_nothic_bargain_tier_two_reveals_cinderfall_and_costs_trust(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Outlander",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        bryn = create_bryn_underbough()
        tolan = create_tolan_ironshield()
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9008347))
        game.state = GameState(
            player=player,
            companions=[bryn, tolan],
            current_scene="tresendar_manor",
            flags={"tresendar_revealed": True, "cinderfall_relay_destroyed": True},
        )
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None

        def choose_cinderfall_bargain(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "The Cistern Eye waits to learn what kind of answer you are.":
                return self.option_index_containing(options, "every secret")
            if prompt == "The Eye's first truth leaves another shape under the water.":
                return self.option_index_containing(options, "Cinderfall")
            if prompt == "The second truth tastes like ash, but the Eye is still grinning.":
                return self.option_index_containing(options, "Stop before")
            raise AssertionError(prompt)

        game.scenario_choice = choose_cinderfall_bargain  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        game._tresendar_nothic_lair(dungeon, dungeon.rooms["nothic_lair"])

        self.assertEqual(game.state.flags["tresendar_nothic_route"], "bargain")
        self.assertEqual(game.state.flags["tresendar_nothic_bargain_tier"], 2)
        self.assertEqual(game.state.flags["tresendar_nothic_sanity_cost"], 2)
        self.assertTrue(game.state.flags["tresendar_nothic_cinderfall_lore"])
        self.assertNotIn("tresendar_nothic_wave_echo_lore", game.state.flags)
        self.assertEqual(game.state.flags["deep_ledger_hint_count"], 2)
        self.assertTrue(any("destroying it cut Ashfall's reserve channel" in clue for clue in game.state.clues))
        self.assertIn("reeling", player.conditions)
        self.assertIn("frightened", player.conditions)
        self.assertEqual(bryn.disposition, -1)
        self.assertEqual(tolan.disposition, -1)
        self.assertEqual(encounters[0].enemy_initiative_bonus, 1)

    def test_tresendar_nothic_bargain_tier_three_reveals_wave_echo_and_whispers_through(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        rhogar = create_rhogar_valeguard()
        rhogar.disposition = 4
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9008348))
        game.state = GameState(player=player, companions=[rhogar], current_scene="tresendar_manor", flags={"tresendar_revealed": True})
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None

        def choose_wave_echo_bargain(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "The Cistern Eye waits to learn what kind of answer you are.":
                return self.option_index_containing(options, "every secret")
            if prompt == "The Eye's first truth leaves another shape under the water.":
                return self.option_index_containing(options, "Cinderfall")
            if prompt == "The second truth tastes like ash, but the Eye is still grinning.":
                return self.option_index_containing(options, "past the Ashen Brand")
            raise AssertionError(prompt)

        game.scenario_choice = choose_wave_echo_bargain  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        game._tresendar_nothic_lair(dungeon, dungeon.rooms["nothic_lair"])

        self.assertEqual(game.state.flags["tresendar_nothic_bargain_tier"], 3)
        self.assertEqual(game.state.flags["tresendar_nothic_sanity_cost"], 3)
        self.assertTrue(game.state.flags["tresendar_nothic_cinderfall_lore"])
        self.assertTrue(game.state.flags["tresendar_nothic_wave_echo_lore"])
        self.assertTrue(game.state.flags["tresendar_nothic_bargain_whispered_through"])
        self.assertEqual(game.state.flags["deep_ledger_hint_count"], 3)
        self.assertTrue(any("keeping Wave Echo unreachable" in clue for clue in game.state.clues))
        self.assertTrue(any("Forge of Spells can listen" in clue for clue in game.state.clues))
        self.assertEqual(player.story_skill_bonuses, {"Insight": -1, "Persuasion": -1})
        self.assertEqual(player.conditions["reeling"], 2)
        self.assertEqual(player.conditions["frightened"], 2)
        self.assertEqual(rhogar.disposition, 2)
        self.assertEqual(encounters[0].enemy_initiative_bonus, 3)

    def test_tresendar_nothic_deception_success_grants_full_lore_without_sanity_cost(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Rogue",
            background="Charlatan",
            base_ability_scores={"STR": 8, "DEX": 15, "CON": 12, "INT": 10, "WIS": 13, "CHA": 14},
            class_skill_choices=["Acrobatics", "Perception", "Sleight of Hand", "Stealth"],
        )
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "4", output_fn=lambda _: None, rng=random.Random(9008349))
        game.state = GameState(player=player, current_scene="tresendar_manor", flags={"tresendar_revealed": True})
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None
        game.scenario_choice = lambda prompt, options, **kwargs: 4  # type: ignore[method-assign]
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        game._tresendar_nothic_lair(dungeon, dungeon.rooms["nothic_lair"])

        self.assertEqual(game.state.flags["tresendar_nothic_route"], "deceive")
        self.assertTrue(game.state.flags["tresendar_nothic_deceived"])
        self.assertTrue(game.state.flags["tresendar_nothic_trade_info_gained"])
        self.assertTrue(game.state.flags["tresendar_nothic_cinderfall_lore"])
        self.assertTrue(game.state.flags["tresendar_nothic_wave_echo_lore"])
        self.assertEqual(game.state.flags["deep_ledger_hint_count"], 3)
        self.assertNotIn("tresendar_nothic_sanity_cost", game.state.flags)
        self.assertEqual(player.conditions, {})
        self.assertEqual(player.story_skill_bonuses, {})
        self.assertEqual(encounters[0].hero_initiative_bonus, 2)
        self.assertIn("reeling", encounters[0].enemies[0].conditions)

    def test_emberhall_and_forge_encounters_reinforce_for_full_party(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        act1_companions = [create_tolan_ironshield(), create_elira_dawnmantle(), create_kaelis_starling()]
        act2_companions = [create_rhogar_valeguard(), create_elira_dawnmantle(), create_nim_ardentglass()]
        encounters: list[Encounter] = []

        act1_game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900835))
        act1_game.state = GameState(player=player, companions=act1_companions, current_scene="emberhall_cellars")
        act1_game.ensure_state_integrity()
        dungeon = act1_game.current_act1_dungeon()
        assert dungeon is not None
        act1_game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]
        act1_game._emberhall_antechamber(dungeon, dungeon.rooms["antechamber"])
        act1_game._emberhall_black_reserve(dungeon, dungeon.rooms["black_reserve"])
        act1_game._emberhall_varyn_sanctum(dungeon, dungeon.rooms["varyn_sanctum"])
        self.assertEqual(len(encounters[0].enemies), 4)
        self.assertEqual(len(encounters[1].enemies), 4)
        self.assertEqual(len(encounters[2].enemies), 5)
        self.assertGreater(encounters[2].enemies[0].max_hp, 38)

        act2_game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900836))
        act2_game.state = GameState(
            player=build_character(
                name="Vale",
                race="Human",
                class_name="Fighter",
                background="Soldier",
                base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
                class_skill_choices=["Athletics", "Survival"],
            ),
            companions=act2_companions,
            camp_companions=[create_tolan_ironshield(), create_bryn_underbough(), create_irielle_ashwake()],
            current_scene="forge_of_spells",
            current_act=2,
            flags={"black_lake_barracks_raided": True},
        )
        act2_game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]
        act2_game.scene_black_lake_causeway()
        assert act2_game.state is not None
        act2_game.state.inventory["sigil_anchor_ring_rare"] = 1
        act2_game.scene_forge_of_spells()
        self.assertEqual(encounters[3].title, "Black Lake Waterline")
        self.assertEqual(len(encounters[3].enemies), 3)
        self.assertEqual(encounters[4].title, "Black Lake Causeway")
        self.assertEqual(len(encounters[4].enemies), 3)
        self.assertEqual(encounters[5].title, "Forge Choir Pit")
        self.assertEqual(len(encounters[5].enemies), 3)
        self.assertEqual(encounters[6].title, "Boss: Sister Caldra Voss")
        self.assertEqual(len(encounters[6].enemies), 4)
        self.assertGreater(encounters[6].enemies[0].max_hp, 42)

    def test_varyn_finale_records_route_displacement_without_killing_act1_victory(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "3", output_fn=log.append, rng=random.Random(9008351))
        game.state = GameState(
            player=player,
            current_scene="emberhall_cellars",
            flags={
                "emberhall_ledger_read": True,
                "act1_town_fear": 4,
                "act1_ashen_strength": 3,
                "act1_survivors_saved": 0,
            },
        )
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None
        game.run_encounter = lambda encounter: "victory"  # type: ignore[method-assign]
        game.save_game = lambda slot_name: ""  # type: ignore[method-assign]

        game._emberhall_varyn_sanctum(dungeon, dungeon.rooms["varyn_sanctum"])

        rendered = self.plain_output(log)
        self.assertTrue(game.state.flags["varyn_body_defeated_act1"])
        self.assertTrue(game.state.flags["varyn_route_displaced"])
        self.assertTrue(game.state.flags["act1_ashen_brand_broken"])
        self.assertTrue(game.state.flags["emberhall_impossible_exit_seen"])
        self.assertEqual(game.state.flags["act1_victory_tier"], "fractured_victory")
        self.assertIn("folds the wrong way", rendered)
        self.assertIn("appears in the ledger only after Varyn is gone", rendered)
        self.assertNotIn("Varyn is dead", rendered)

    def test_pre_act3_runtime_text_does_not_name_secret_villain(self) -> None:
        runtime_paths = [
            Path("dnd_game/gameplay/story_intro.py"),
            Path("dnd_game/gameplay/story_act1_expanded.py"),
            Path("dnd_game/gameplay/story_act2_scaffold.py"),
            Path("dnd_game/gameplay/story_act3_scaffold.py"),
            Path("dnd_game/gameplay/map_system.py"),
        ]
        forbidden_terms = ("Malzurath", "Keeper of the Ninth Ledger", "Quiet Architect", "true master", "second villain")
        runtime_chunks: list[str] = []
        for path in runtime_paths:
            text = path.read_text(encoding="utf-8")
            if path.name == "story_act3_scaffold.py":
                text = re.sub(
                    r"# ACT3_POST_REVEAL_TEXT_START.*?# ACT3_POST_REVEAL_TEXT_END",
                    "",
                    text,
                    flags=re.S,
                )
            runtime_chunks.append(text)
        runtime_text = "\n".join(runtime_chunks)
        for term in forbidden_terms:
            self.assertNotIn(term, runtime_text)

    def test_black_lake_barracks_raid_removes_forge_reserve_without_strong_gear(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "3", output_fn=lambda _: None, rng=random.Random(900837))
        game.state = GameState(
            player=player,
            companions=[create_rhogar_valeguard(), create_elira_dawnmantle(), create_nim_ardentglass()],
            current_act=2,
            current_scene="forge_of_spells",
            flags={
                "act2_started": True,
                "black_lake_crossed": True,
                "black_lake_barracks_raided": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
            inventory={},
        )
        encounters: list[Encounter] = []
        game.ensure_state_integrity()
        game.travel_to_act2_node("forge_of_spells")
        dungeon = game.current_act2_dungeon()
        assert dungeon is not None
        game.scenario_choice = lambda prompt, options, **kwargs: 3  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]
        game._forge_caldra_dais(dungeon, dungeon.rooms["caldra_dais"])

        self.assertEqual(encounters[0].title, "Boss: Sister Caldra Voss")
        self.assertEqual(len(encounters[0].enemies), 3)

    def test_act1_room_navigation_options_show_direction_tags(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90084))
        game.state = GameState(
            player=player,
            current_scene="old_owl_well",
            flags={"miners_exchange_lead": True},
        )
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None
        game.complete_map_room(dungeon, "well_ring")
        option_labels = [label for _, _, label in game.act1_room_navigation_options(dungeon)]
        self.assertIn("[MOVE EAST] *Advance to Salt Cart Hollow", option_labels)
        self.assertIn("[MOVE SOUTH] *Advance to Supply Trench", option_labels)
        self.assertIn("*Withdraw to Phandalin", option_labels)

    def test_blackwake_room_navigation_uses_vertical_split_labels_at_tollhouse(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(900841))
        game.state = GameState(
            player=player,
            current_scene="blackwake_crossing",
            flags={"act1_started": True, "blackwake_started": True},
        )
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None
        game.complete_map_room(dungeon, "charred_tollhouse")
        game.render_act1_dungeon_map(dungeon, force=True)
        option_labels = [label for _, _, label in game.act1_room_navigation_options(dungeon)]
        self.assertIn("[MOVE EAST-NORTH] *Advance to Flooded Approach", option_labels)
        self.assertIn("[MOVE EAST-SOUTH] *Advance to Hanging Path", option_labels)
        self.assertNotIn("[MOVE EAST] *Advance to Flooded Approach", option_labels)
        self.assertNotIn("[MOVE EAST] *Advance to Hanging Path", option_labels)
        rendered = self.plain_output(log)
        self.assertIn("WEST-+-EAST", rendered)
        self.assert_dungeon_map_header_is_balanced(rendered)
        self.assertIn("EAST-NORTH -> Flooded Approach", rendered)
        self.assertIn("EAST-SOUTH -> Hanging Path", rendered)

    def test_blackwake_entrance_offers_overworld_backtrack_to_neverwinter(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9008491))
        game.state = GameState(
            player=player,
            current_scene="neverwinter_briefing",
            flags={"act1_started": True, "blackwake_started": True},
        )
        game.ensure_state_integrity()
        game.travel_to_act1_node("blackwake_crossing")
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None
        game.complete_map_room(dungeon, "charred_tollhouse")

        options = game.act1_room_navigation_options(dungeon)
        option_labels = [label for _, _, label in options]
        self.assertIn(("overworld_backtrack", "neverwinter_briefing", "[BACKTRACK] *Backtrack to Neverwinter Briefing"), options)
        self.assertIn("[BACKTRACK] *Backtrack to Neverwinter Briefing", option_labels)
        self.assertIn("*Withdraw to the Blackwake road decision", option_labels)

    @unittest.skipUnless(RICH_AVAILABLE, "Rich rendering is optional")
    def test_rich_dungeon_compass_renders_as_fixed_width_block(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9008411))
        game.state = GameState(
            player=player,
            current_scene="blackwake_crossing",
            flags={"act1_started": True, "blackwake_started": True},
        )
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None
        rendered = "\n".join(strip_ansi(line) for line in render_rich_lines(build_dungeon_panel(dungeon, game.act1_map_state()), width=108))
        self.assert_rich_compass_block_is_fixed_width(rendered)

    def test_act1_dungeon_backtrack_uses_precise_direction_and_consumes_history(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900842))
        game.state = GameState(
            player=player,
            current_scene="blackwake_crossing",
            flags={"act1_started": True, "blackwake_started": True},
        )
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None
        game.complete_map_room(dungeon, "charred_tollhouse")
        game.set_current_map_room("millers_ford_flooded_approach")
        game.complete_map_room(dungeon, "millers_ford_flooded_approach")

        option_labels = [label for _, _, label in game.act1_room_navigation_options(dungeon)]
        self.assertIn("[BACKTRACK WEST-SOUTH] *Backtrack to Charred Tollhouse", option_labels)
        self.assertIn("[MOVE EAST-SOUTH] *Advance to Reedbank Camp", option_labels)
        self.assertIn("[MOVE EAST] *Advance to Wagon Snarl", option_labels)
        self.assertNotIn("[MOVE SOUTH] *Advance to Reedbank Camp", option_labels)

        self.assertTrue(game.backtrack_map_room(dungeon))
        self.assertEqual(game.current_act1_room(dungeon).room_id, "charred_tollhouse")
        self.assertEqual(game._map_state_payload()["room_history"], [])
        self.assertEqual(game._pending_act1_dungeon_movement_text, "You backtrack west-south toward Charred Tollhouse.")

    def test_act2_dungeon_backtrack_uses_true_backtrack_action(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900843))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="stonehollow_dig",
            flags={
                "act2_started": True,
                "act2_town_stability": 3,
                "act2_route_control": 2,
                "act2_whisper_pressure": 2,
            },
        )
        game.ensure_state_integrity()
        dungeon = game.current_act2_dungeon()
        assert dungeon is not None
        game.complete_act2_map_room(dungeon, "survey_mouth")
        game.set_current_act2_map_room("slime_cut")
        game.complete_act2_map_room(dungeon, "slime_cut")

        option_labels = [label for _, _, label in game.act2_room_navigation_options(dungeon)]
        self.assertIn("[BACKTRACK WEST] *Backtrack to Survey Mouth", option_labels)
        self.assertIn("[MOVE EAST-NORTH] *Advance to Collapse Lift", option_labels)
        self.assertIn("[MOVE EAST] *Advance to Scholar Pocket", option_labels)

        self.assertTrue(game.backtrack_act2_map_room(dungeon))
        self.assertEqual(game.current_act2_room(dungeon).room_id, "survey_mouth")
        self.assertEqual(game._act2_map_state_payload()["room_history"], [])
        self.assertEqual(game._pending_act2_dungeon_movement_text, "You backtrack west toward Survey Mouth.")

    def test_room_exit_direction_labels_only_duplicate_for_truly_cardinal_overlaps(self) -> None:
        for blueprint in (ACT1_HYBRID_MAP, ACT2_ENEMY_DRIVEN_MAP):
            for dungeon in blueprint.dungeons.values():
                for room in dungeon.rooms.values():
                    exits = [dungeon.rooms[room_id] for room_id in room.exits]
                    if not exits:
                        continue
                    directions = room_exit_directions(room, exits, dungeon=dungeon)
                    grouped: dict[str, list[tuple[int, int]]] = {}
                    for exit_room in exits:
                        grouped.setdefault(directions[exit_room.room_id], []).append((exit_room.x - room.x, exit_room.y - room.y))
                    for vectors in grouped.values():
                        if len(vectors) < 2:
                            continue
                        self.assertTrue(
                            all(dx == 0 or dy == 0 for dx, dy in vectors),
                            f"Expected duplicate labels to remain only for shared cardinal lanes from {room.title}, got {vectors!r}",
                        )

    def test_room_exit_direction_labels_match_path_order_for_all_dungeons(self) -> None:
        def expected_direction(dungeon, room, exit_room) -> str:
            path = room_travel_path(dungeon, room, exit_room)
            if not path:
                dx = exit_room.x - room.x
                dy = exit_room.y - room.y
                parts: list[str] = []
                if dy < 0:
                    parts.append("NORTH")
                elif dy > 0:
                    parts.append("SOUTH")
                if dx < 0:
                    parts.append("WEST")
                elif dx > 0:
                    parts.append("EAST")
                return "-".join(parts) or "HERE"
            previous = (room.x * 2, room.y * 2)
            directions: list[str] = []
            seen: set[str] = set()
            for step in path:
                dx = step[0] - previous[0]
                dy = step[1] - previous[1]
                previous = step
                direction = "EAST" if dx > 0 else "WEST" if dx < 0 else "SOUTH" if dy > 0 else "NORTH" if dy < 0 else "HERE"
                if direction == "HERE" or direction in seen:
                    continue
                directions.append(direction)
                seen.add(direction)
            return "-".join(directions) or "HERE"

        for blueprint in (ACT1_HYBRID_MAP, ACT2_ENEMY_DRIVEN_MAP):
            for dungeon in blueprint.dungeons.values():
                for room in dungeon.rooms.values():
                    exits = [dungeon.rooms[room_id] for room_id in room.exits]
                    directions = room_exit_directions(room, exits, dungeon=dungeon)
                    for exit_room in exits:
                        self.assertEqual(
                            directions[exit_room.room_id],
                            expected_direction(dungeon, room, exit_room),
                            f"{dungeon.title}: {room.title} -> {exit_room.title} should reflect traversable path order",
                        )

    def test_dungeon_map_renders_once_per_room_until_room_changes(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(90085))
        game.state = GameState(
            player=player,
            current_scene="old_owl_well",
            flags={"miners_exchange_lead": True},
        )
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None
        game.render_act1_dungeon_map(dungeon)
        first_render_count = len(log)
        game.render_act1_dungeon_map(dungeon)
        self.assertEqual(len(log), first_render_count)
        game.complete_map_room(dungeon, "well_ring")
        game.render_act1_dungeon_map(dungeon)
        self.assertGreater(len(log), first_render_count)
        rerender_count = len(log)
        game.render_act1_dungeon_map(dungeon)
        self.assertEqual(len(log), rerender_count)
        game.set_current_map_room("salt_cart")
        self.assertEqual(len(log), rerender_count)
        game.render_act1_dungeon_map(dungeon)
        self.assertGreater(len(log), rerender_count)

    def test_travel_to_act1_node_updates_state_and_renders_the_overworld_map(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(900851))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            flags={"phandalin_arrived": True, "miners_exchange_lead": True},
        )
        game.ensure_state_integrity()
        game.travel_to_act1_node("old_owl_well")
        rendered = self.plain_output(log)
        self.assertEqual(game.state.current_scene, "old_owl_well")
        self.assertIn("Overworld Route Map", rendered)
        self.assertIn("Old Owl Well", rendered)

    def test_travel_to_act1_dungeon_node_refreshes_dungeon_music(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9008511))
        game.state = GameState(
            player=player,
            current_scene="neverwinter_briefing",
            flags={"act1_started": True, "blackwake_started": True},
        )
        game.ensure_state_integrity()
        calls: list[tuple[str, str | None, bool]] = []
        game.refresh_scene_music = lambda default_to_menu=False: calls.append(
            (game.state.current_scene, game.scene_music_context(game.state.current_scene), default_to_menu)
        )

        game.travel_to_act1_node("blackwake_crossing")

        self.assertEqual(game.state.current_scene, "blackwake_crossing")
        self.assertIn(("blackwake_crossing", "dungeon", False), calls)

    def test_act1_overworld_backtrack_returns_to_previous_site_with_context_text(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(9008512))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            flags={"phandalin_arrived": True, "miners_exchange_lead": True},
        )
        game.ensure_state_integrity()
        game.travel_to_act1_node("old_owl_well")
        game.return_to_phandalin("You withdraw from Old Owl Well and ride back to Phandalin to regroup.")

        candidate = game.peek_act1_overworld_backtrack_node()
        assert candidate is not None
        self.assertEqual(candidate.node_id, "old_owl_well")
        self.assertTrue(game.backtrack_act1_overworld_node())
        self.assertEqual(game.state.current_scene, "old_owl_well")
        self.assertEqual(game._map_state_payload()["node_history"], ["neverwinter_briefing", "high_road_ambush", "phandalin_hub"])
        rendered = self.plain_output(log)
        self.assertIn("You leave Phandalin by the same track you used before", rendered)
        self.assertIn("Tessa's runners argue supplies", rendered)
        self.assertIn("Overworld Route Map", rendered)

    def test_act1_overworld_backtrack_can_return_to_neverwinter(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(9008513))
        game.state = GameState(
            player=player,
            current_scene="neverwinter_briefing",
            flags={"act1_started": True, "blackwake_started": True},
        )
        game.ensure_state_integrity()
        game.travel_to_act1_node("blackwake_crossing")

        candidate = game.peek_act1_overworld_backtrack_node()
        assert candidate is not None
        self.assertEqual(candidate.node_id, "neverwinter_briefing")
        self.assertTrue(game.backtrack_act1_overworld_node())
        self.assertEqual(game.state.current_scene, "neverwinter_briefing")
        self.assertEqual(game._map_state_payload()["current_node_id"], "neverwinter_briefing")
        self.assertEqual(game._map_state_payload()["node_history"], [])
        rendered = self.plain_output(log)
        self.assertIn("backtrack north toward Neverwinter", rendered)
        self.assertIn("Mira is waiting in the background", rendered)
        self.assertIn("Overworld Route Map", rendered)

    def test_act1_overworld_backtrack_from_phandalin_returns_to_high_road_then_neverwinter(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(9008514))
        game.state = GameState(player=player, current_scene="phandalin_hub", flags={"phandalin_arrived": True})
        game.ensure_state_integrity()

        candidate = game.peek_act1_overworld_backtrack_node()
        assert candidate is not None
        self.assertEqual(candidate.node_id, "high_road_ambush")
        self.assertTrue(game.backtrack_act1_overworld_node())
        self.assertEqual(game.state.current_scene, "road_ambush")
        self.assertEqual(game._map_state_payload()["node_history"], ["neverwinter_briefing"])

        candidate = game.peek_act1_overworld_backtrack_node()
        assert candidate is not None
        self.assertEqual(candidate.node_id, "neverwinter_briefing")
        self.assertTrue(game.backtrack_act1_overworld_node())
        self.assertEqual(game.state.current_scene, "neverwinter_briefing")
        self.assertEqual(game._map_state_payload()["node_history"], [])
        rendered = self.plain_output(log)
        self.assertIn("backtrack north along the High Road", rendered)
        self.assertIn("backtrack north toward Neverwinter", rendered)

    def test_cleared_high_road_scene_can_backtrack_to_neverwinter(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["2"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(9008515))
        game.state = GameState(
            player=player,
            current_scene="road_ambush",
            flags={"act1_started": True, "road_ambush_cleared": True},
        )
        game.ensure_state_integrity()

        game.scene_road_ambush()
        self.assertEqual(game.state.current_scene, "neverwinter_briefing")
        self.assertEqual(game._map_state_payload()["node_history"], [])
        rendered = self.plain_output(log)
        self.assertIn("Where do you go from the High Road?", rendered)
        self.assertIn("[BACKTRACK] *Backtrack to Neverwinter Briefing", rendered)

    def test_act1_overworld_travel_renders_map_before_next_scene_and_prompt(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []

        def fake_input(_: str) -> str:
            raise self._SceneExit()

        game = TextDnDGame(input_fn=fake_input, output_fn=log.append, rng=random.Random(9008511))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            flags={"phandalin_arrived": True, "miners_exchange_lead": True},
        )
        game.ensure_state_integrity()
        game.travel_to_act1_node("old_owl_well")
        with self.assertRaises(self._SceneExit):
            game.scene_old_owl_well()
        rendered = self.plain_output(log)
        map_index = rendered.rfind("Overworld Route Map")
        scene_index = rendered.rfind("The old watchtower rises from the scrub like a cracked finger of Netherese stone.")
        prompt_index = rendered.rfind("How do you work the edge of the dig ring?")
        self.assertNotEqual(map_index, -1)
        self.assertNotEqual(scene_index, -1)
        self.assertNotEqual(prompt_index, -1)
        self.assertLess(map_index, scene_index)
        self.assertLess(scene_index, prompt_index)

    def test_set_current_map_room_queues_transition_feedback_without_printing_immediately(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(900852))
        game.state = GameState(
            player=player,
            current_scene="old_owl_well",
            flags={"miners_exchange_lead": True, "old_owl_ring_cleared": True},
        )
        game.ensure_state_integrity()
        game.set_current_map_room("salt_cart", announce=True)
        rendered = self.plain_output(log)
        self.assertEqual(rendered.strip(), "")
        self.assertTrue(game._pending_act1_dungeon_map_refresh)
        self.assertEqual(game._pending_act1_dungeon_movement_text, "You move toward salt cart.")
        self.assertNotIn("Current room: Salt Cart Hollow", rendered)

    def test_act1_movement_renders_updated_map_before_next_room_scene_and_prompt(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["1", "1"])

        def fake_input(_: str) -> str:
            try:
                return next(answers)
            except StopIteration as exc:
                raise self._SceneExit() from exc

        game = TextDnDGame(input_fn=fake_input, output_fn=log.append, rng=random.Random(900853))
        game.state = GameState(
            player=player,
            current_scene="blackwake_crossing",
            flags={"act1_started": True, "blackwake_started": True},
        )
        game.ensure_state_integrity()
        dungeon = game.current_act1_dungeon()
        assert dungeon is not None
        game.complete_map_room(dungeon, "charred_tollhouse")
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        with self.assertRaises(self._SceneExit):
            game.run_act1_dungeon("blackwake_crossing")
        rendered = self.plain_output(log)
        prior_prompt_index = rendered.rfind("What do you do from Charred Tollhouse?")
        map_index = rendered.rfind("Current room: Flooded Approach")
        movement_index = rendered.rfind("You move east-north toward Flooded Approach.")
        scene_index = rendered.rfind("Cold floodwater chews at the ford stones while wrecked carts pin draft horses")
        prompt_index = rendered.rfind("How do you approach Miller's Ford?")
        self.assertNotEqual(prior_prompt_index, -1)
        self.assertNotEqual(map_index, -1)
        self.assertNotEqual(movement_index, -1)
        self.assertNotEqual(scene_index, -1)
        self.assertNotEqual(prompt_index, -1)
        self.assertLess(prior_prompt_index, map_index)
        self.assertLess(map_index, movement_index)
        self.assertLess(movement_index, scene_index)
        self.assertLess(scene_index, prompt_index)

    def test_act2_overworld_travel_renders_map_before_next_scene_and_prompt(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []

        def fake_input(_: str) -> str:
            raise self._SceneExit()

        game = TextDnDGame(input_fn=fake_input, output_fn=log.append, rng=random.Random(9008541))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="act2_expedition_hub",
            flags={
                "act2_started": True,
                "act2_town_stability": 3,
                "act2_route_control": 2,
                "act2_whisper_pressure": 2,
            },
        )
        game.ensure_state_integrity()
        game.travel_to_act2_node("stonehollow_dig")
        with self.assertRaises(self._SceneExit):
            game.scene_stonehollow_dig()
        rendered = self.plain_output(log)
        map_index = rendered.rfind("Overworld Route Map")
        scene_index = rendered.rfind("Stonehollow is a half-legitimate dig site turned excavation wound.")
        prompt_index = rendered.rfind("How do you take the first measure of the dig?")
        self.assertNotEqual(map_index, -1)
        self.assertNotEqual(scene_index, -1)
        self.assertNotEqual(prompt_index, -1)
        self.assertLess(map_index, scene_index)
        self.assertLess(scene_index, prompt_index)

    def test_travel_to_act2_dungeon_node_refreshes_dungeon_music(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90085411))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="act2_expedition_hub",
            flags={
                "act2_started": True,
                "act2_town_stability": 3,
                "act2_route_control": 2,
                "act2_whisper_pressure": 2,
            },
        )
        game.ensure_state_integrity()
        calls: list[tuple[str, str | None, bool]] = []
        game.refresh_scene_music = lambda default_to_menu=False: calls.append(
            (game.state.current_scene, game.scene_music_context(game.state.current_scene), default_to_menu)
        )

        game.travel_to_act2_node("stonehollow_dig")

        self.assertEqual(game.state.current_scene, "stonehollow_dig")
        self.assertIn(("stonehollow_dig", "dungeon", False), calls)

    def test_act2_overworld_backtrack_returns_to_previous_site_with_context_text(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(9008542))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="act2_expedition_hub",
            flags={
                "act2_started": True,
                "act2_town_stability": 3,
                "act2_route_control": 2,
                "act2_whisper_pressure": 2,
            },
        )
        game.ensure_state_integrity()
        game.travel_to_act2_node("stonehollow_dig")
        game.return_to_act2_hub("You withdraw from Stonehollow Dig and return to Phandalin's expedition table.")

        candidate = game.peek_act2_overworld_backtrack_node()
        assert candidate is not None
        self.assertEqual(candidate.node_id, "stonehollow_dig")
        self.assertTrue(game.backtrack_act2_overworld_node())
        self.assertEqual(game.state.current_scene, "stonehollow_dig")
        self.assertEqual(game._act2_map_state_payload()["node_history"], ["act2_expedition_hub"])
        rendered = self.plain_output(log)
        self.assertIn("backtracking toward Stonehollow Dig", rendered)
        self.assertIn("Halia, Linene, Elira, and Daran", rendered)
        self.assertIn("Overworld Route Map", rendered)

    def test_act2_overworld_backtrack_can_return_to_expedition_hub(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(9008543))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="act2_expedition_hub",
            flags={
                "act2_started": True,
                "act2_town_stability": 3,
                "act2_route_control": 2,
                "act2_whisper_pressure": 2,
            },
        )
        game.ensure_state_integrity()
        game.travel_to_act2_node("stonehollow_dig")

        candidate = game.peek_act2_overworld_backtrack_node()
        assert candidate is not None
        self.assertEqual(candidate.node_id, "act2_expedition_hub")
        self.assertTrue(game.backtrack_act2_overworld_node())
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertEqual(game._act2_map_state_payload()["current_node_id"], "act2_expedition_hub")
        self.assertEqual(game._act2_map_state_payload()["node_history"], [])
        rendered = self.plain_output(log)
        self.assertIn("You backtrack from Stonehollow Dig toward Act II Expedition Hub", rendered)
        self.assertIn("Overworld Route Map", rendered)

    def test_act2_movement_renders_updated_map_before_next_room_scene_and_prompt(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["1", "1"])

        def fake_input(_: str) -> str:
            try:
                return next(answers)
            except StopIteration as exc:
                raise self._SceneExit() from exc

        game = TextDnDGame(input_fn=fake_input, output_fn=log.append, rng=random.Random(900854))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="stonehollow_dig",
            flags={
                "act2_started": True,
                "act2_town_stability": 3,
                "act2_route_control": 2,
                "act2_whisper_pressure": 2,
            },
        )
        game.ensure_state_integrity()
        dungeon = game.current_act2_dungeon()
        assert dungeon is not None
        game.complete_act2_map_room(dungeon, "survey_mouth")
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: "victory"  # type: ignore[method-assign]
        with self.assertRaises(self._SceneExit):
            game.run_act2_dungeon("stonehollow_dig")
        rendered = self.plain_output(log)
        prior_prompt_index = rendered.rfind("What do you do from Survey Mouth?")
        map_index = rendered.rfind("Current room: Slime Cut")
        movement_index = rendered.rfind("You move east toward Slime Cut.")
        scene_index = rendered.rfind("The main cut narrows around spilled lantern oil, acid-eaten timber")
        prompt_index = rendered.rfind("How do you cross the slime cut?")
        self.assertNotEqual(prior_prompt_index, -1)
        self.assertNotEqual(map_index, -1)
        self.assertNotEqual(movement_index, -1)
        self.assertNotEqual(scene_index, -1)
        self.assertNotEqual(prompt_index, -1)
        self.assertLess(prior_prompt_index, map_index)
        self.assertLess(map_index, movement_index)
        self.assertLess(movement_index, scene_index)
        self.assertLess(scene_index, prompt_index)

    def test_map_menu_offers_overworld_and_dungeon_views(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        captured: dict[str, list[str]] = {}
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(90086))
        game.state = GameState(
            player=player,
            current_scene="old_owl_well",
            flags={"miners_exchange_lead": True},
        )
        game.ensure_state_integrity()

        def fake_choose(prompt: str, options: list[str], **kwargs) -> int:
            captured["options"] = options
            return 4

        game.choose = fake_choose  # type: ignore[method-assign]
        game.open_map_menu()
        self.assertEqual(captured["options"], ["Travel Ledger", "Overworld", "Old Owl Well Dig Ring", "Back"])

    def test_act2_map_menu_offers_read_only_route_map(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        captured: dict[str, list[str]] = {}
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900861))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="act2_expedition_hub",
            flags={"act2_started": True},
        )

        def fake_choose(prompt: str, options: list[str], **kwargs) -> int:
            captured["options"] = options
            return 4

        game.choose = fake_choose  # type: ignore[method-assign]
        game.open_map_menu()
        self.assertEqual(captured["options"], ["Travel Ledger", "Act II Route Map", "Current Site (not available here)", "Back"])

    def test_act2_route_map_unlocks_sabotage_from_any_two_early_leads(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(900862))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="act2_expedition_hub",
            flags={
                "act2_started": True,
                "agatha_truth_secured": True,
                "woodland_survey_cleared": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )
        game.render_act2_overworld_map(force=True)
        rendered = self.plain_output(log)
        self.assertIn("Act II Pressures", rendered)
        self.assertIn("Town Stability: Holding (3/5)", rendered)
        self.assertIn("Route Control: Firm (3/5)", rendered)
        self.assertIn("Whisper Pressure: Present (2/5)", rendered)
        self.assertIn("Trigger sabotage night", rendered)
        self.assertIn("Sabotage Night", rendered)

    def test_stonehollow_dig_uses_playable_act2_room_map(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900863))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="stonehollow_dig",
            flags={
                "act2_started": True,
                "act2_town_stability": 3,
                "act2_route_control": 2,
                "act2_whisper_pressure": 2,
            },
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "What do you do from Slime Cut?":
                for index, option in enumerate(options, start=1):
                    if "Scholar Pocket" in strip_ansi(option):
                        return index
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_stonehollow_dig()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["stonehollow_dig_cleared"])
        self.assertTrue(game.state.flags["stonehollow_scholars_found"])
        self.assertIn("act2_map_state", game.state.flags)
        self.assertEqual(game.state.flags["map_state"]["cleared_rooms"], [])
        self.assertCountEqual(
            game.state.flags["act2_map_state"]["cleared_rooms"],
            ["survey_mouth", "slime_cut", "scholar_pocket", "lower_breakout"],
        )
        self.assertTrue(
            game.state.inventory.get("delver_lantern_hood_uncommon", 0)
            or game.state.inventory.get("forgehand_gauntlets_uncommon", 0)
        )
        self.assertEqual([encounter.title for encounter in encounters], ["Stonehollow Slime Cut", "Stonehollow Breakout"])

    def test_south_adit_uses_playable_act2_room_map_and_recruits_irielle(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        encounters: list[Encounter] = []
        drainage_offered = False
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900864))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="south_adit",
            flags={
                "act2_started": True,
                "phandalin_sabotage_resolved": True,
                "act2_first_late_route": "broken_prospect",
                "act2_captive_outcome": "captives_endangered",
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            nonlocal drainage_offered
            plain_options = [strip_ansi(option) for option in options]
            if prompt == "What do you do from South Adit Mouth?":
                drainage_offered = any("Drainage Exit" in option for option in plain_options)
                for index, option in enumerate(plain_options, start=1):
                    if "Silent Cells" in option:
                        return index
            if prompt == "What do you do from Silent Cells?":
                for index, option in enumerate(plain_options, start=1):
                    if "Augur Cell" in option:
                        return index
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_south_adit()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(drainage_offered)
        self.assertTrue(game.state.flags["south_adit_cleared"])
        self.assertTrue(game.state.flags["wave_echo_reached"])
        self.assertTrue(game.state.flags["quiet_choir_identified"])
        self.assertTrue(game.state.flags["irielle_contact_made"])
        self.assertTrue(game.state.flags["counter_cadence_known"])
        self.assertEqual(game.state.flags["act2_captive_outcome"], "few_saved")
        self.assertIsNotNone(game.find_companion("Irielle Ashwake"))
        self.assertCountEqual(
            game.state.flags["act2_map_state"]["cleared_rooms"],
            ["adit_mouth", "silent_cells", "augur_cell", "warden_nave"],
        )
        self.assertEqual(game.state.inventory.get("choirward_amulet_uncommon"), 1)
        self.assertEqual([encounter.title for encounter in encounters], ["South Adit Wardens"])

    def test_act2_hub_warns_before_first_late_route_choice(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        confirmations = 0
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(900865))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="act2_expedition_hub",
            flags={
                "act2_started": True,
                "agatha_truth_secured": True,
                "woodland_survey_cleared": True,
                "stonehollow_dig_cleared": True,
                "phandalin_sabotage_resolved": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            nonlocal confirmations
            plain_options = [strip_ansi(option) for option in options]
            if prompt == "Where do you push next?":
                for index, option in enumerate(plain_options, start=1):
                    if "Broken Prospect" in option:
                        return index
            if prompt == "This first late-route choice will change the other route. Proceed?":
                confirmations += 1
                return 2 if confirmations == 1 else 1
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_act2_expedition_hub()

        assert game.state is not None
        rendered = self.plain_output(log)
        self.assertEqual(confirmations, 2)
        self.assertIn("Choosing Broken Prospect first commits the expedition to the cleaner cave approach", rendered)
        self.assertEqual(game.state.current_scene, "broken_prospect")
        self.assertNotIn("act2_first_late_route", game.state.flags)

    def test_broken_prospect_uses_playable_act2_room_map(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900866))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="broken_prospect",
            flags={
                "act2_started": True,
                "phandalin_sabotage_resolved": True,
                "south_adit_cleared": True,
                "act2_first_late_route": "south_adit",
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            plain_options = [strip_ansi(option) for option in options]
            if prompt == "What do you do from Broken Shelf?":
                for index, option in enumerate(plain_options, start=1):
                    if "Rival Survey Shelf" in option:
                        return index
            if prompt == "What do you do from Rival Survey Shelf?":
                for index, option in enumerate(plain_options, start=1):
                    if "Sealed Approach" in option:
                        return index
            if prompt == "What do you do from Sealed Approach?":
                for index, option in enumerate(plain_options, start=1):
                    if "Dead Foreman's Shift" in option:
                        return index
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_broken_prospect()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["broken_prospect_cleared"])
        self.assertTrue(game.state.flags["wave_echo_reached"])
        self.assertCountEqual(
            game.state.flags["act2_map_state"]["cleared_rooms"],
            ["broken_shelf", "rival_survey_shelf", "sealed_approach", "foreman_shift"],
        )
        self.assertEqual([encounter.title for encounter in encounters], ["Broken Prospect Rival Shelf", "Broken Prospect"])

    def test_wave_echo_outer_galleries_uses_playable_act2_room_map(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900867))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="wave_echo_outer_galleries",
            flags={
                "act2_started": True,
                "broken_prospect_cleared": True,
                "south_adit_cleared": True,
                "wave_echo_reached": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            plain_options = [strip_ansi(option) for option in options]
            if prompt == "What do you do from Rail Junction?":
                for index, option in enumerate(plain_options, start=1):
                    if "Slime Sluice" in option:
                        return index
            if prompt == "What do you do from Slime Sluice?":
                for index, option in enumerate(plain_options, start=1):
                    if "False Echo Loop" in option:
                        return index
            if prompt == "What do you do from False Echo Loop?":
                for index, option in enumerate(plain_options, start=1):
                    if "Deep Haul Gate" in option:
                        return index
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_wave_echo_outer_galleries()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["wave_echo_outer_cleared"])
        self.assertCountEqual(
            game.state.flags["act2_map_state"]["cleared_rooms"],
            ["rail_junction", "slime_sluice", "false_echo_loop", "deep_haul_gate"],
        )
        self.assertEqual([encounter.title for encounter in encounters], ["Wave Echo Slime Sluice", "Outer Gallery Pressure"])

    def test_black_lake_causeway_uses_playable_act2_room_map(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900868))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="black_lake_causeway",
            flags={
                "act2_started": True,
                "wave_echo_outer_cleared": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            plain_options = [strip_ansi(option) for option in options]
            if prompt == "What do you do from Causeway Lip?":
                for index, option in enumerate(plain_options, start=1):
                    if "Choir Barracks" in option:
                        return index
            if prompt == "What do you do from Choir Barracks?":
                for index, option in enumerate(plain_options, start=1):
                    if "Blackwater Edge" in option:
                        return index
            if prompt == "What do you do from Blackwater Edge?":
                for index, option in enumerate(plain_options, start=1):
                    if "Far Landing" in option:
                        return index
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_black_lake_causeway()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["black_lake_crossed"])
        self.assertTrue(game.state.flags["black_lake_barracks_raided"])
        self.assertCountEqual(
            game.state.flags["act2_map_state"]["cleared_rooms"],
            ["causeway_lip", "choir_barracks", "blackwater_edge", "far_landing"],
        )
        self.assertEqual(game.state.inventory.get("fireward_elixir"), 1)
        self.assertEqual(
            [encounter.title for encounter in encounters],
            ["Black Lake Barracks", "Black Lake Waterline", "Black Lake Causeway"],
        )

    def test_forge_of_spells_uses_playable_act2_room_map_and_black_lake_changes_route(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        encounters: list[Encounter] = []
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(900870))
        game.state = GameState(
            player=player,
            companions=[create_nim_ardentglass(), create_irielle_ashwake()],
            current_act=2,
            current_scene="forge_of_spells",
            flags={
                "act2_started": True,
                "black_lake_crossed": True,
                "black_lake_shrine_purified": True,
                "black_lake_barracks_raided": True,
                "black_lake_barracks_orders_taken": True,
                "black_lake_causeway_shaken": True,
                "nim_countermeasure_notes": True,
                "south_adit_counter_cadence_learned": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            plain_options = [strip_ansi(option) for option in options]
            if prompt == "What do you do from Forge Threshold?":
                for index, option in enumerate(plain_options, start=1):
                    if "Shard Channels" in option:
                        return index
            if prompt == "What do you do from Shard Channels?":
                for index, option in enumerate(plain_options, start=1):
                    if "Resonance Lens" in option:
                        return index
            if prompt == "What do you do from Resonance Lens?":
                for index, option in enumerate(plain_options, start=1):
                    if "Caldra's Dais" in option:
                        return index
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_forge_of_spells()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["forge_shard_route_exposed"])
        self.assertTrue(game.state.flags["forge_lens_mapped"])
        self.assertTrue(game.state.flags["caldra_defeated"])
        self.assertTrue(game.state.flags["irielle_counter_cadence"])
        self.assertTrue(game.state.flags["counter_cadence_known"])
        self.assertTrue(game.state.flags["act3_signal_carried"])
        self.assertTrue(game.state.flags["act3_lens_understood"])
        self.assertNotIn("act3_lens_blinded", game.state.flags)
        self.assertCountEqual(
            game.state.flags["act2_map_state"]["cleared_rooms"],
            ["forge_threshold", "shard_channels", "resonance_lens", "caldra_dais"],
        )
        self.assertEqual([encounter.title for encounter in encounters], ["Forge Shard Channels", "Boss: Sister Caldra Voss"])
        self.assertEqual(encounters[1].parley_dc, 13)
        self.assertIn(
            "The Forge's real reinforcement traffic still runs through the choir pit, which means Caldra's dais is not the only thing holding her ritual up.",
            game.state.clues,
        )
        self.assertIn(
            "The resonance lens only held because Caldra was braiding witness, ritual, and shard pressure into one engineered lie.",
            game.state.clues,
        )
        self.assertIn(
            "You used the Black Lake orders to read the Forge threshold and find the chamber's real support traffic.",
            game.state.journal,
        )
        self.assertIn(
            "You broke the shard channels and turned the Forge's hidden pressure seam into a wound instead of a weapon.",
            game.state.journal,
        )
        rendered = self.plain_output(log)
        self.assertIn("The chamber's still honest in the margins. Read the traffic, not the glow", rendered)
        self.assertIn("The lens wants one obedience note under everything else.", rendered)
        self.assertIn("The Forge does not create. It clarifies.", rendered)

    def test_act2_status_and_journal_summarize_rescues_and_route_intel(self) -> None:
        player = build_character(
            name="Iri",
            race="Human",
            class_name="Wizard",
            background="Sage",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10},
            class_skill_choices=["Arcana", "Investigation"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(900869))
        game.state = GameState(
            player=player,
            companions=[create_irielle_ashwake()],
            current_act=2,
            current_scene="act2_expedition_hub",
            flags={
                "act2_started": True,
                "phandalin_sabotage_resolved": True,
                "act2_first_late_route": "broken_prospect",
                "south_adit_cleared": True,
                "act2_captive_outcome": "few_saved",
                "stonehollow_scholars_found": True,
                "stonehollow_notes_preserved": True,
                "nim_countermeasure_notes": True,
                "irielle_contact_made": True,
                "quiet_choir_identified": True,
                "black_lake_barracks_orders_taken": True,
                "black_lake_barracks_raided": True,
                "wave_echo_outer_cleared": True,
                "act2_town_stability": 3,
                "act2_route_control": 4,
                "act2_whisper_pressure": 2,
            },
        )

        game.show_act2_campaign_status()
        game.show_journal()

        rendered = self.plain_output(log)
        self.assertIn("Late-route commitment: Broken Prospect first; South Adit only yielded partial rescues.", rendered)
        self.assertIn("Rescue summary: Stonehollow scholars escaped with usable survey testimony; South Adit only yielded partial rescues; Irielle Ashwake is traveling with the active party.", rendered)
        self.assertIn("Route intelligence: Nim's Stonehollow countermeasure notes survived; the outer galleries now hold as a real expedition line; the Black Lake crossing is being prepared from multiple angles.", rendered)
        self.assertIn("Choir intelligence: captives have named the Quiet Choir's prison cadence; barracks orders confirm the Forge-side reserve plan.", rendered)
        self.assertIn("Campaign Snapshot:", rendered)

    def test_act2_start_records_escaped_sereth_callback(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(9212))
        game.state = GameState(
            player=player,
            current_scene="act1_complete",
            flags={
                "blackwake_completed": True,
                "blackwake_sereth_fate": "escaped",
                "blackwake_sereth_road_note_seen": True,
            },
        )
        game.start_act2_scaffold()
        game.show_act2_campaign_status()
        game.show_journal()

        rendered = self.plain_output(log)
        self.assertTrue(game.state.flags["act2_sereth_shadow_active"])
        self.assertTrue(game.state.flags["act2_sereth_callback_recorded"])
        self.assertIn("Blackwake callback: Sereth Vane escaped the crossing", rendered)
        self.assertIn("Blackwake consequence: Sereth Vane escaped into Act 2's route war", rendered)

    def test_act2_start_records_neverwinter_contract_house_political_callback(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(9222))
        game.state = GameState(
            player=player,
            current_scene="act1_complete",
            flags={"neverwinter_contract_house_political_callback": True},
        )

        game.start_act2_scaffold()
        game.show_act2_campaign_status()
        game.show_journal()

        rendered = self.plain_output(log)
        self.assertEqual(game.state.flags["act2_route_control"], 3)
        self.assertTrue(game.state.flags["act2_neverwinter_witness_pressure_active"])
        self.assertTrue(game.state.flags["act2_neverwinter_witness_callback_recorded"])
        self.assertIn("Neverwinter politics: Oren, Sabra, Vessa, and Garren", rendered)
        self.assertIn("Neverwinter callback: Oren, Sabra, Vessa, and Garren kept pressure", rendered)

    def test_act2_scaffold_complete_mentions_forge_subroutes_in_handoff(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(900871))
        state = GameState(
            player=player,
            current_act=2,
            current_scene="act2_scaffold_complete",
            flags={
                "act2_started": True,
                "caldra_defeated": True,
                "act2_sponsor": "lionshield",
                "act2_captive_outcome": "few_saved",
                "act2_town_stability": 3,
                "act2_route_control": 4,
                "act2_whisper_pressure": 2,
                "forge_choir_pit_silenced": True,
                "forge_pact_rhythm_found": True,
                "forge_lens_mapped": True,
            },
        )
        game.state = state
        game.choose = lambda prompt, options, **kwargs: 2  # type: ignore[method-assign]
        game.save_game = lambda slot_name: None  # type: ignore[method-assign]

        game.scene_act2_scaffold_complete()

        rendered = self.plain_output(log)
        self.assertEqual(state.flags["act3_forge_route_state"], "broken")
        self.assertEqual(state.flags["act3_forge_subroutes_cleared"], ["forge_choir_pit_silenced", "forge_pact_rhythm_found"])
        self.assertEqual(state.flags["act3_forge_lens_state"], "mapped")
        self.assertTrue(state.flags["act3_lens_understood"])
        self.assertNotIn("act3_lens_blinded", state.flags)
        self.assertIn("hazardous cargo corridors that must stay locked down.", rendered)
        self.assertIn("Inside the Forge, you silenced the choir pit and recovered the Pact anvil's rhythm", rendered)
        self.assertIn("one live subroute stayed dangerous to the end.", rendered)
        self.assertIn("mapped the resonance lens from inside before the chamber broke.", rendered)
        self.assertIn("Act 3 inherits a Forge where you already silenced the choir pit", rendered)
        self.assertIn("one forge line still escaped a clean ruin.", rendered)
        self.assertIn("reliable read on how Caldra held witness, ritual", rendered)

    def test_act2_record_epilogue_flags_marks_carried_signal_and_blind_lens(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900872))
        game.state = GameState(
            player=player,
            current_act=2,
            flags={
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 4,
                "caldra_defeated": True,
            },
        )

        game.act2_record_epilogue_flags()

        assert game.state is not None
        self.assertEqual(game.state.flags["act3_whisper_state"], "carried_out")
        self.assertEqual(game.state.flags["act3_forge_lens_state"], "shattered_blind")
        self.assertTrue(game.state.flags["act3_signal_carried"])
        self.assertTrue(game.state.flags["act3_lens_blinded"])
        self.assertNotIn("act3_lens_understood", game.state.flags)

    def test_sabotage_night_records_midpoint_pattern_from_choice(self) -> None:
        pattern_cases = [
            (1, "pattern_preserves_institutions"),
            (2, "pattern_preserves_people"),
            (3, "pattern_hunts_systems"),
        ]
        pattern_flags = [expected for _, expected in pattern_cases]
        for choice, expected_flag in pattern_cases:
            with self.subTest(choice=choice):
                player = build_character(
                    name="Vale",
                    race="Human",
                    class_name="Fighter",
                    background="Soldier",
                    base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
                    class_skill_choices=["Athletics", "Survival"],
                )
                game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900873 + choice))
                game.state = GameState(
                    player=player,
                    current_act=2,
                    current_scene="act2_midpoint_convergence",
                    flags={
                        "act2_started": True,
                        "agatha_truth_secured": True,
                        "stonehollow_dig_cleared": True,
                        "woodland_survey_cleared": True,
                        "act2_town_stability": 3,
                        "act2_route_control": 3,
                        "act2_whisper_pressure": 2,
                    },
                )
                game.scenario_choice = lambda prompt, options, **kwargs: choice  # type: ignore[method-assign]
                game.skill_check = lambda actor, skill, dc, context: False  # type: ignore[method-assign]
                game.run_encounter = lambda encounter: "victory"  # type: ignore[method-assign]

                game.scene_act2_midpoint_convergence()

                assert game.state is not None
                self.assertTrue(game.state.flags[expected_flag])
                self.assertEqual([flag for flag in pattern_flags if game.state.flags.get(flag)], [expected_flag])
                self.assertNotIn("act2_midpoint_priority", game.state.flags)

    def test_act3_scaffold_map_integrity_formula_uses_existing_handoff_flags(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900874))
        game.state = GameState(
            player=player,
            current_act=2,
            flags={
                "act1_victory_tier": "clean_victory",
                "act3_claims_balance": "secured",
                "act3_forge_route_state": "mastered",
                "act3_forge_lens_state": "mapped",
                "act3_whisper_state": "lingering",
            },
        )
        self.assertEqual(game.act3_map_integrity(), 5)

        game.state.flags = {
            "act1_victory_tier": "fractured_victory",
            "act3_claims_balance": "chaotic",
            "act3_forge_route_state": "direct",
            "act3_forge_lens_state": "shattered_blind",
            "act3_whisper_state": "carried_out",
        }
        self.assertEqual(game.act3_map_integrity(), 1)

    def test_act3_scaffold_player_pattern_profile_derives_varyn_read(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        profile_cases = [
            (
                {
                    "pattern_preserves_people": True,
                    "elira_mercy_blessing": True,
                    "act2_sponsor": "wardens",
                    "act2_first_late_route": "south_adit",
                },
                "mercy_first",
            ),
            (
                {
                    "pattern_hunts_systems": True,
                    "act2_first_late_route": "broken_prospect",
                    "act2_sponsor": "lionshield",
                },
                "route_first",
            ),
            ({}, "balanced"),
        ]
        for flags, expected_profile in profile_cases:
            with self.subTest(expected_profile=expected_profile):
                game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900875))
                game.state = GameState(player=player, current_act=3, flags=dict(flags))
                self.assertEqual(game.act3_player_pattern_profile(), expected_profile)

    def test_act3_scaffold_records_setup_flags_and_round_trips(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        bryn = create_bryn_underbough()
        bryn.disposition = 6
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900876))
        game.state = GameState(
            player=player,
            companions=[bryn],
            current_act=2,
            flags={
                "act1_victory_tier": "clean_victory",
                "act3_claims_balance": "secured",
                "act3_forge_route_state": "broken",
                "act3_forge_lens_state": "mapped",
                "act3_whisper_state": "lingering",
                "counter_cadence_known": True,
                "act3_lens_understood": True,
                "pattern_preserves_institutions": True,
                "act2_sponsor": "lionshield",
                "bryn_ledger_burned": True,
                "bryn_loose_ends_resolved": True,
            },
        )

        game.act3_record_scaffold_flags()

        assert game.state is not None
        self.assertEqual(game.state.current_act, 3)
        self.assertTrue(game.state.flags["act3_started"])
        self.assertFalse(game.state.flags["malzurath_revealed"])
        self.assertTrue(game.state.flags["act3_varyn_apparent_primary"])
        self.assertEqual(game.state.flags["act3_map_integrity"], 5)
        self.assertEqual(game.state.flags["player_pattern_profile"], "institution_first")
        self.assertEqual(game.state.flags["unrecorded_choice_tokens"], 5)
        self.assertNotIn("ninth_ledger_pressure", game.state.flags)

        restored = GameState.from_dict(game.state.to_dict())
        self.assertEqual(restored.flags["act3_map_integrity"], 5)
        self.assertEqual(restored.flags["player_pattern_profile"], "institution_first")
        self.assertEqual(restored.flags["unrecorded_choice_tokens"], 5)
        self.assertTrue(restored.flags["act3_varyn_apparent_primary"])

    def test_act3_hidden_pressure_label_stays_masked_before_reveal(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        label_cases = [
            ({"act3_signal_carried": True}, "Signal Pressure"),
            ({"act3_whisper_state": "lingering"}, "Whisper Pressure"),
            ({}, "Map Pressure"),
        ]
        for flags, expected_label in label_cases:
            with self.subTest(expected_label=expected_label):
                game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900877))
                game.state = GameState(player=player, current_act=3, flags=dict(flags))
                label = game.act3_hidden_pressure_label()
                self.assertEqual(label, expected_label)
                self.assertNotIn("Ninth Ledger", label)

        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900878))
        game.state = GameState(player=player, current_act=3, flags={"malzurath_revealed": True})
        self.assertEqual(game.act3_hidden_pressure_label(), "Ninth Ledger Pressure")

    def test_act3_ninth_ledger_opens_reveals_secret_villain_and_converts_pressure(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        irielle = create_irielle_ashwake()
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(900879))
        game.state = GameState(
            player=player,
            companions=[irielle],
            current_act=3,
            current_scene="act3_ninth_ledger_opens",
            flags={
                "act1_victory_tier": "clean_victory",
                "act3_claims_balance": "secured",
                "act3_forge_route_state": "broken",
                "act3_forge_lens_state": "mapped",
                "act3_whisper_state": "carried_out",
                "act3_signal_carried": True,
                "act3_lens_understood": True,
                "counter_cadence_known": True,
                "pattern_hunts_systems": True,
                "act2_first_late_route": "broken_prospect",
            },
        )
        game.scenario_choice = lambda prompt, options, **kwargs: 2  # type: ignore[method-assign]
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]

        game.scene_act3_ninth_ledger_opens()

        assert game.state is not None
        self.assertTrue(game.state.flags["malzurath_revealed"])
        self.assertTrue(game.state.flags["act3_ninth_ledger_opened"])
        self.assertFalse(game.state.flags["act3_varyn_apparent_primary"])
        self.assertTrue(game.state.flags["act3_reveal_false_author_named"])
        self.assertEqual(game.state.flags["act3_reveal_profile_named"], "route_first")
        self.assertEqual(game.state.flags["ninth_ledger_pressure"], 1)
        self.assertEqual(game.state.flags["unrecorded_choice_tokens"], 2)
        self.assertEqual(game.state.current_scene, "act3_ninth_ledger_aftermath")
        self.assertTrue(
            any("Malzurath, Keeper of the Ninth Ledger, has been using route logic" in clue for clue in game.state.clues)
        )
        rendered = self.plain_output(log)
        self.assertIn("No. That route is not mine.", rendered)
        self.assertIn("Malzurath, Keeper of the Ninth Ledger", rendered)
        self.assertIn("Ninth Ledger Pressure 1/5", rendered)

    def test_act3_ninth_ledger_pressure_rewards_lens_and_counter_cadence(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900880))
        game.state = GameState(
            player=player,
            current_act=3,
            flags={
                "act3_signal_carried": True,
                "act3_whisper_state": "carried_out",
                "act3_lens_blinded": True,
                "act3_forge_lens_state": "shattered_blind",
                "act3_map_integrity": 1,
            },
        )
        self.assertEqual(game.act3_ninth_ledger_pressure(), 5)

        game.state.flags = {
            "act3_signal_carried": True,
            "act3_whisper_state": "carried_out",
            "act3_lens_understood": True,
            "act3_forge_lens_state": "mapped",
            "counter_cadence_known": True,
            "act3_map_integrity": 5,
            "act3_reveal_resistance_bonus": 1,
        }
        self.assertEqual(game.act3_ninth_ledger_pressure(), 1)

    def test_act3_unrecorded_choice_tokens_can_be_spent_after_reveal(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900881))
        game.state = GameState(player=player, current_act=3, flags={"unrecorded_choice_tokens": 1})
        self.assertFalse(game.act3_use_unrecorded_choice_token("before reveal"))
        self.assertEqual(game.state.flags["unrecorded_choice_tokens"], 1)

        game.state.flags["malzurath_revealed"] = True
        self.assertTrue(game.act3_use_unrecorded_choice_token("refuse a recorded outcome"))
        self.assertEqual(game.state.flags["unrecorded_choice_tokens"], 0)
        self.assertIn("Unrecorded choice spent: refuse a recorded outcome", game.state.journal)
        self.assertFalse(game.act3_use_unrecorded_choice_token("no tokens left"))

    def test_act3_reveal_scene_is_registered_in_scene_handlers(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900882))
        self.assertIn("act3_ninth_ledger_opens", game._scene_handlers)
        self.assertIn("act3_ninth_ledger_aftermath", game._scene_handlers)

    def test_help_menu_lists_map_command(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(90087))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        if RICH_AVAILABLE:
            game._interactive_output = True
        game.show_global_commands()
        rendered = self.plain_output(log)
        self.assertIn("Global Commands", rendered)
        self.assertIn("map", rendered)

    def test_build_character_applies_racial_bonus(self) -> None:
        character = build_character(
            name="Nim",
            race="Halfling",
            class_name="Rogue",
            background="Criminal",
            base_ability_scores={"STR": 8, "DEX": 15, "CON": 12, "INT": 10, "WIS": 14, "CHA": 13},
            class_skill_choices=["Acrobatics", "Perception", "Sleight of Hand", "Stealth"],
            expertise_choices=["Stealth", "Perception"],
        )
        self.assertEqual(character.ability_scores["DEX"], 17)
        self.assertIn("lucky", character.features)
        self.assertEqual(character.armor_class, 14)

    def test_save_round_trip(self) -> None:
        player = build_character(
            name="Iri",
            race="Human",
            class_name="Wizard",
            background="Sage",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10},
            class_skill_choices=["Arcana", "Investigation"],
        )
        state = GameState(
            player=player,
            current_scene="phandalin_hub",
            flags={
                "varyn_body_defeated_act1": True,
                "varyn_route_displaced": True,
                "act1_ashen_brand_broken": True,
                "deep_ledger_hint_count": 2,
            },
            clues=["one"],
            journal=["entry"],
            xp=125,
            gold=37,
            inventory={"potion_healing": 2, "bread_round": 3},
            short_rests_remaining=1,
        )
        save_dir = Path.cwd() / "tests_output"
        save_dir.mkdir(exist_ok=True)
        game = TextDnDGame(
            input_fn=lambda _: "2",
            output_fn=lambda _: None,
            save_dir=save_dir,
            rng=random.Random(3),
        )
        game.state = state
        path = game.save_game(slot_name="roundtrip")
        loaded = json.loads(Path(path).read_text(encoding="utf-8"))
        restored = GameState.from_dict(loaded)
        self.assertEqual(restored.player.name, "Iri")
        self.assertEqual(restored.current_scene, "phandalin_hub")
        self.assertTrue(restored.flags["varyn_body_defeated_act1"])
        self.assertTrue(restored.flags["varyn_route_displaced"])
        self.assertTrue(restored.flags["act1_ashen_brand_broken"])
        self.assertEqual(restored.flags["deep_ledger_hint_count"], 2)
        self.assertEqual(restored.clues, ["one"])
        self.assertEqual(restored.xp, 125)
        self.assertEqual(restored.gold, 37)
        self.assertEqual(restored.inventory["potion_healing"], 2)
        self.assertEqual(restored.short_rests_remaining, 1)
        Path(path).unlink(missing_ok=True)

    def test_information_dialogue_can_grant_quest_and_show_in_journal(self) -> None:
        player = build_character(
            name="Iri",
            race="Human",
            class_name="Wizard",
            background="Sage",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10},
            class_skill_choices=["Arcana", "Investigation"],
        )
        answers = iter(["1", "3"])
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(301))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.visit_steward()
        self.assertIn("secure_miners_road", game.state.quests)
        game.show_journal()
        rendered = self.plain_output(log)
        self.assertIn("Quest Added: Stop the Watchtower Raids", rendered)
        self.assertIn("Active Quests:", rendered)
        self.assertIn("Stop the Watchtower Raids", rendered)

    def test_journal_groups_snapshot_clues_and_recent_updates(self) -> None:
        player = build_character(
            name="Iri",
            race="Human",
            class_name="Wizard",
            background="Sage",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10},
            class_skill_choices=["Arcana", "Investigation"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(3011))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            clues=["A hidden tunnel runs under the shrine."],
            journal=[
                "Clue: A hidden tunnel runs under the shrine.",
                "Spoke with Sister Garaele about the old shrine.",
                "Recovered a scorched map scrap from the roadside.",
            ],
        )
        game.show_journal()
        rendered = self.plain_output(log)
        self.assertIn("Campaign Snapshot:", rendered)
        self.assertIn("Clue Board:", rendered)
        self.assertIn("Recent Updates:", rendered)
        self.assertIn("Spoke with Sister Garaele", rendered)
        self.assertIn("Recovered a scorched map scrap", rendered)
        self.assertNotIn("Clue: A hidden tunnel runs under the shrine.", rendered)

    def test_ashfall_watch_returns_to_phandalin_and_marks_quests_ready(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["3", "3", "1", "3"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(302))
        game.state = GameState(player=player, current_scene="ashfall_watch", clues=["one", "two"])
        game.grant_quest("secure_miners_road")
        game.run_encounter = lambda encounter: "victory"
        game.scene_ashfall_watch()
        self.assertEqual(game.state.current_scene, "phandalin_hub")
        self.assertTrue(game.state.flags["ashfall_watch_cleared"])
        self.assertEqual(game.state.quests["secure_miners_road"].status, "ready_to_turn_in")

    def test_phandalin_hub_can_travel_to_cinderfall_when_hidden_route_is_unlocked(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        selected: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(900834))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            flags={"phandalin_arrived": True, "hidden_route_unlocked": True},
        )
        game.run_phandalin_council_event = lambda: None  # type: ignore[method-assign]
        game.run_after_watch_gathering = lambda: None  # type: ignore[method-assign]

        def choose_route(prompt: str, options: list[str], **kwargs) -> int:
            self.assertEqual(prompt, "Where do you go next?")
            return next(index for index, option in enumerate(options, start=1) if "Cinderfall Ruins" in option)

        game.scenario_choice = choose_route  # type: ignore[method-assign]
        game.travel_to_act1_node = lambda node_id: selected.append(node_id)  # type: ignore[method-assign]
        game.scene_phandalin_hub()
        self.assertEqual(selected, ["cinderfall_ruins"])

    def test_post_combat_random_encounter_pool_has_fifteen_plus_entries(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(810))
        self.assertGreaterEqual(len(game.post_combat_random_encounter_ids()), 15)

    def test_run_encounter_triggers_post_combat_random_event_after_victory(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(811))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        enemy = create_enemy("bandit")
        enemy.current_hp = 0
        enemy.dead = True
        seen: list[str] = []
        game.maybe_run_post_combat_random_encounter = lambda encounter: seen.append(encounter.title)
        outcome = game.run_encounter(Encounter(title="Spent Ambushers", description="The danger is already over.", enemies=[enemy]))
        self.assertEqual(outcome, "victory")
        self.assertEqual(seen, ["Spent Ambushers"])

    def test_victory_autosaves_are_created_and_pruned_to_limit(self) -> None:
        save_dir = Path.cwd() / "tests_output" / "autosave_rotation"
        save_dir.mkdir(parents=True, exist_ok=True)
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(
            input_fn=lambda _: "1",
            output_fn=lambda _: None,
            save_dir=save_dir,
            rng=random.Random(3031),
        )
        game.autosaves_enabled = True
        game.state = GameState(player=player, current_scene="road_ambush")

        try:
            for index in range(17):
                enemy = create_enemy("goblin_skirmisher")
                enemy.dead = True
                enemy.current_hp = 0
                outcome = game.run_encounter(
                    Encounter(
                        title=f"Spent Ambush {index}",
                        description="The danger is already over.",
                        enemies=[enemy],
                    )
                )
                self.assertEqual(outcome, "victory")

            autosaves = sorted(save_dir.glob("autosave__*.json"))
            self.assertEqual(len(autosaves), 15)
            self.assertTrue(all(path.name.startswith("autosave__") for path in autosaves))
        finally:
            for path in save_dir.glob("*.json"):
                path.unlink(missing_ok=True)
            save_dir.rmdir()

    def test_post_combat_random_event_skips_when_roll_misses(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(812))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        calls: list[str] = []
        game.run_named_post_combat_random_encounter = lambda encounter_id: calls.append(encounter_id)
        game.rng = SimpleNamespace(random=lambda: 0.99, choice=lambda options: options[0])
        game.maybe_run_post_combat_random_encounter(Encounter(title="Skipped", description="", enemies=[]))
        self.assertEqual(calls, [])

    def test_post_combat_random_event_skips_for_chained_encounter(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(813))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        calls: list[str] = []
        game.run_named_post_combat_random_encounter = lambda encounter_id: calls.append(encounter_id)
        game.rng = SimpleNamespace(random=lambda: 0.0, choice=lambda options: options[0])
        game.maybe_run_post_combat_random_encounter(
            Encounter(title="Chained", description="", enemies=[], allow_post_combat_random_encounter=False)
        )
        self.assertEqual(calls, [])

    def test_locked_chest_random_encounter_can_award_loot_without_combat(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Rogue",
            background="Criminal",
            base_ability_scores={"STR": 8, "DEX": 15, "CON": 12, "INT": 10, "WIS": 14, "CHA": 13},
            class_skill_choices=["Acrobatics", "Perception", "Sleight of Hand", "Stealth"],
            expertise_choices=["Sleight of Hand", "Stealth"],
        )
        answers = iter(["2"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(814))
        game.state = GameState(player=player, current_scene="phandalin_hub", inventory={}, gold=0)
        game.skill_check = lambda actor, skill, dc, context: True
        game.run_named_post_combat_random_encounter("locked_chest_under_ferns")
        self.assertGreater(game.state.gold, 0)
        self.assertEqual(game.state.inventory["potion_healing"], 1)

    def test_random_encounter_rewards_reveal_results_line_by_line(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Rogue",
            background="Criminal",
            base_ability_scores={"STR": 8, "DEX": 15, "CON": 12, "INT": 10, "WIS": 14, "CHA": 13},
            class_skill_choices=["Acrobatics", "Perception", "Sleight of Hand", "Stealth"],
            expertise_choices=["Stealth", "Perception"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(812))
        game.state = GameState(player=player, current_scene="phandalin_hub", inventory={})
        pauses: list[str] = []
        game.pause_for_loot_reveal = lambda: pauses.append("pause")
        game.grant_random_encounter_rewards(reason="the fern-hidden chest", gold=9, items={"potion_healing": 1, "bread_round": 1})
        self.assertEqual(pauses, ["pause", "pause", "pause"])

    def test_random_event_spawned_fight_disables_follow_up_random_encounters(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["3"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(815))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        captured: list[Encounter] = []

        def fake_run_encounter(encounter: Encounter) -> str:
            captured.append(encounter)
            return "victory"

        game.run_encounter = fake_run_encounter
        game.run_named_post_combat_random_encounter("abandoned_cottage")
        self.assertEqual(len(captured), 1)
        self.assertFalse(captured[0].allow_post_combat_random_encounter)

    def test_seen_random_encounters_are_weighted_far_lower_than_unseen_ones(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(817))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            flags={"random_encounters_seen": ["locked_chest_under_ferns"]},
        )
        pool = game.weighted_post_combat_random_encounter_pool()
        seen_count = sum(1 for entry in pool if entry[0] == "locked_chest_under_ferns")
        unseen_count = sum(1 for entry in pool if entry[0] == "abandoned_cottage")
        self.assertEqual(seen_count, 1)
        self.assertEqual(unseen_count, 10)

    def test_saved_messenger_unlocks_follow_up_reward_until_claimed(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(8171))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            flags={"saved_wounded_messenger": True},
        )
        unlocked_pool = game.weighted_post_combat_random_encounter_pool()
        self.assertTrue(any(entry[0] == "messenger_returns_with_reward" for entry in unlocked_pool))
        game.state.flags["messenger_return_paid"] = True
        locked_pool = game.weighted_post_combat_random_encounter_pool()
        self.assertFalse(any(entry[0] == "messenger_returns_with_reward" for entry in locked_pool))

    def test_smuggler_cookfire_unlocks_bryn_cache_and_revenge_chain(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        bryn = create_bryn_underbough()
        answers = iter(["2"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(8172))
        game.state = GameState(player=player, companions=[bryn], current_scene="phandalin_hub")
        game.grant_quest("bryn_loose_ends")
        game.skill_check = lambda actor, skill, dc, context: True
        game.random_encounter_smuggler_cookfire()
        pool = game.weighted_post_combat_random_encounter_pool()
        self.assertTrue(game.state.flags["bryn_cache_found"])
        self.assertTrue(game.state.flags["smuggler_revenge_pending"])
        self.assertTrue(any(entry[0] == "smuggler_revenge_squad" for entry in pool))

    def test_random_encounter_intro_uses_typed_narration(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        typed: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=print, rng=random.Random(818), type_dialogue=True)
        game.output_fn = lambda _: None
        game.typewrite_narration = lambda text: typed.append(text)
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.random_encounter_intro("A hidden danger waits in the reeds.")
        self.assertEqual(typed, ["A hidden danger waits in the reeds."])

    def test_ashfall_watch_marks_first_encounter_as_chained_for_random_events(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["3", "2", "1", "3"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(816))
        game.state = GameState(player=player, current_scene="ashfall_watch", clues=["one", "two"])
        captured: list[Encounter] = []

        def fake_run_encounter(encounter: Encounter) -> str:
            captured.append(encounter)
            return "victory"

        game.run_encounter = fake_run_encounter
        game.scene_ashfall_watch()
        self.assertEqual(len(captured), 3)
        self.assertFalse(captured[0].allow_post_combat_random_encounter)
        self.assertFalse(captured[1].allow_post_combat_random_encounter)
        self.assertFalse(captured[2].allow_post_combat_random_encounter)

    def test_cinderfall_ruins_clear_relay_and_update_act1_metrics(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["1", "1", "1", "1", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(900835))
        game.state = GameState(
            player=player,
            current_scene="cinderfall_ruins",
            flags={
                "hidden_route_unlocked": True,
                "act1_ashen_strength": 1,
                "act1_town_fear": 2,
                "act1_survivors_saved": 1,
            },
        )
        game.run_encounter = lambda encounter: "victory"
        game.scene_cinderfall_ruins()
        self.assertEqual(game.state.current_scene, "phandalin_hub")
        self.assertTrue(game.state.flags["cinderfall_ruins_cleared"])
        self.assertTrue(game.state.flags["cinderfall_relay_destroyed"])
        self.assertTrue(game.state.flags["varyn_relay_broken"])
        self.assertEqual(game.state.flags["act1_ashen_strength"], 0)
        self.assertEqual(game.state.flags["act1_survivors_saved"], 3)
        self.assertEqual(game.state.flags["act1_town_fear"], 1)

    def test_cinderfall_sabotage_thins_ashfall_barracks_and_removes_rukhar_temp_hp(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = ["3", "3", "1", "3"]
        baseline_encounters: list[Encounter] = []
        sabotage_encounters: list[Encounter] = []

        baseline_game = TextDnDGame(input_fn=lambda _: answers.pop(0), output_fn=lambda _: None, rng=random.Random(900836))
        baseline_game.state = GameState(
            player=player,
            current_scene="ashfall_watch",
            flags={"act1_ashen_strength": 1},
        )
        baseline_game.run_encounter = lambda encounter: baseline_encounters.append(encounter) or "victory"  # type: ignore[method-assign]
        baseline_game.scene_ashfall_watch()

        answers = ["3", "3", "1", "3"]
        sabotage_game = TextDnDGame(input_fn=lambda _: answers.pop(0), output_fn=lambda _: None, rng=random.Random(900837))
        sabotage_game.state = GameState(
            player=build_character(
                name="Vale",
                race="Human",
                class_name="Fighter",
                background="Soldier",
                base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
                class_skill_choices=["Athletics", "Survival"],
            ),
            current_scene="ashfall_watch",
            flags={"act1_ashen_strength": 0, "cinderfall_relay_destroyed": True},
        )
        sabotage_game.run_encounter = lambda encounter: sabotage_encounters.append(encounter) or "victory"  # type: ignore[method-assign]
        sabotage_game.scene_ashfall_watch()

        self.assertEqual(len(baseline_encounters[1].enemies), len(sabotage_encounters[1].enemies) + 1)
        self.assertEqual(baseline_encounters[2].enemies[0].temp_hp, 4)
        self.assertEqual(sabotage_encounters[2].enemies[0].temp_hp, 0)

    def test_act1_epilogue_flags_capture_clean_and_fractured_victories(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9008371))
        game.state = GameState(
            player=player,
            current_scene="emberhall_cellars",
            flags={"act1_town_fear": 1, "act1_ashen_strength": 1, "act1_survivors_saved": 3},
        )
        self.assertEqual(game.act1_record_epilogue_flags(), "clean_victory")
        self.assertEqual(game.state.flags["act2_starting_pressure"], 0)
        game.state.flags.update(
            {
                "act1_town_fear": 4,
                "act1_ashen_strength": 3,
                "act1_survivors_saved": 0,
                "bryn_ledger_sold": True,
            }
        )
        self.assertEqual(game.act1_record_epilogue_flags(), "fractured_victory")
        self.assertEqual(game.state.flags["act2_starting_pressure"], 4)

    def test_edermath_old_cache_stealth_success_grants_reward_and_hook(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Rogue",
            background="Criminal",
            base_ability_scores={"STR": 8, "DEX": 15, "CON": 12, "INT": 10, "WIS": 13, "CHA": 14},
            class_skill_choices=["Acrobatics", "Perception", "Sleight of Hand", "Stealth"],
            expertise_choices=["Stealth", "Perception"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(3031))
        game.state = GameState(player=player, current_scene="phandalin_hub", inventory={})
        checks: list[tuple[str, int, str]] = []
        encounters: list[Encounter] = []
        game.skill_check = lambda actor, skill, dc, context: checks.append((skill, dc, context)) or True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        game.run_edermath_old_cache_scene()

        self.assertEqual(checks, [("Stealth", 12, "to reach Daran's buried adventuring cache without alerting the orchard watchers")])
        self.assertEqual(encounters, [])
        self.assertEqual(game.state.inventory["edermath_cache_compass"], 1)
        self.assertEqual(game.state.gold, 12)
        self.assertEqual(game.state.xp, 35)
        self.assertTrue(game.state.flags["edermath_old_cache_recovered"])
        self.assertTrue(game.state.flags["edermath_old_cache_quiet"])
        self.assertTrue(game.state.flags["edermath_old_cache_trust"])
        self.assertTrue(game.state.flags["act2_edermath_cache_routework"])

    def test_edermath_old_cache_reacts_to_completed_wyvern_tor(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Rogue",
            background="Criminal",
            base_ability_scores={"STR": 8, "DEX": 15, "CON": 12, "INT": 10, "WIS": 13, "CHA": 14},
            class_skill_choices=["Acrobatics", "Perception", "Sleight of Hand", "Stealth"],
            expertise_choices=["Stealth", "Perception"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(30311))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            inventory={},
            flags={"wyvern_tor_cleared": True},
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]

        game.run_edermath_old_cache_scene()

        rendered = self.plain_output(log)
        self.assertIn("After Wyvern Tor, I believe you can follow ugly ground", rendered)
        self.assertIn("After Wyvern Tor, I hoped you knew patience as well as pressure", rendered)
        self.assertTrue(game.state.flags["edermath_old_cache_recovered"])

    def test_edermath_old_cache_failed_stealth_runs_watcher_encounter(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(3032))
        game.state = GameState(player=player, current_scene="phandalin_hub", inventory={})
        encounters: list[Encounter] = []
        game.skill_check = lambda actor, skill, dc, context: False  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        game.run_edermath_old_cache_scene()

        self.assertEqual(len(encounters), 1)
        self.assertEqual(encounters[0].title, "Edermath Orchard Watchers")
        self.assertFalse(encounters[0].allow_post_combat_random_encounter)
        self.assertEqual([enemy.archetype for enemy in encounters[0].enemies], ["brand_saboteur", "bandit_archer"])
        self.assertEqual(game.state.inventory["edermath_cache_compass"], 1)
        self.assertTrue(game.state.flags["edermath_old_cache_recovered"])
        self.assertTrue(game.state.flags["edermath_old_cache_watchers_defeated"])
        self.assertTrue(game.state.flags["edermath_old_cache_trust"])
        self.assertTrue(game.state.flags["act2_edermath_cache_routework"])
        self.assertNotIn("edermath_old_cache_quiet", game.state.flags)

    def test_edermath_old_cache_routework_improves_act2_starting_control(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(3033))
        game.state = GameState(player=player, current_act=2, flags={"act2_edermath_cache_routework": True})

        game.act2_initialize_metrics(force=True)

        self.assertEqual(game.state.flags["act2_route_control"], 3)
        self.assertIn(
            "Route intelligence: Daran's old cache map preserves a quiet orchard-to-highland control line.",
            game.act2_campaign_focus_lines(),
        )

    def test_turning_in_quest_grants_rewards(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["1", "3"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(303))
        game.state = GameState(player=player, current_scene="phandalin_hub", flags={"ashfall_watch_cleared": True})
        game.grant_quest("restore_barthen_supplies")
        game.refresh_quest_statuses(announce=False)
        self.assertEqual(game.state.quests["restore_barthen_supplies"].status, "ready_to_turn_in")
        self.assertEqual(game.state.gold, 0)
        self.assertEqual(game.state.xp, 0)
        self.assertNotIn("bread_round", game.state.inventory)
        game.visit_barthen_provisions()
        self.assertEqual(game.state.quests["restore_barthen_supplies"].status, "completed")
        self.assertEqual(game.state.gold, 35)
        self.assertEqual(game.state.xp, 75)
        self.assertEqual(game.state.inventory["barthen_resupply_token"], 1)
        self.assertEqual(game.state.inventory["bread_round"], 4)
        self.assertEqual(game.state.inventory["camp_stew_jar"], 2)
        self.assertTrue(game.state.flags["quest_reward_barthen_resupply_credit"])
        self.assertEqual(game.get_merchant_attitude("barthen_provisions"), 40)

    def test_quest_rewards_require_original_giver(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        output: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=output.append, rng=random.Random(303))
        game.state = GameState(player=player, current_scene="phandalin_hub", flags={"ashfall_watch_cleared": True})
        game.grant_quest("restore_barthen_supplies")
        game.refresh_quest_statuses(announce=False)

        self.assertFalse(game.turn_in_quest("restore_barthen_supplies", giver="Linene Graywind"))
        self.assertEqual(game.state.quests["restore_barthen_supplies"].status, "ready_to_turn_in")
        self.assertEqual(game.state.gold, 0)
        self.assertEqual(game.state.xp, 0)
        self.assertNotIn("bread_round", game.state.inventory)
        self.assertNotIn("barthen_resupply_token", game.state.inventory)
        self.assertNotIn("quest_reward_barthen_resupply_credit", game.state.flags)
        self.assertTrue(any("has to be turned in to Barthen" in line for line in output))

    def test_act2_turnins_are_selected_by_original_giver(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(303))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="act2_expedition_hub",
            flags={"agatha_truth_secured": True, "wave_echo_reached": True},
        )
        game.grant_quest("recover_pact_waymap")
        game.grant_quest("seek_agathas_truth")
        game.refresh_quest_statuses(announce=False)

        game.run_act2_council_turnins()

        self.assertEqual(game.state.quests["recover_pact_waymap"].status, "completed")
        self.assertEqual(game.state.quests["seek_agathas_truth"].status, "ready_to_turn_in")
        self.assertEqual(game.state.gold, 75)
        self.assertEqual(game.state.xp, 140)
        self.assertEqual(game.state.inventory["pact_waymap_case"], 1)
        self.assertEqual(game.state.inventory["resonance_tonic"], 2)
        self.assertTrue(game.state.flags["quest_reward_pact_routes_mastered"])
        self.assertEqual(game.state.flags["act2_route_control"], 3)
        self.assertNotIn("scroll_quell_the_deep", game.state.inventory)

    def test_quest_reward_items_are_cataloged(self) -> None:
        for definition in QUESTS.values():
            for item_id in definition.reward.items:
                self.assertIn(item_id, ITEMS, f"{definition.quest_id} rewards unknown item {item_id}")

        unique_reward_ids = {
            "miras_blackwake_seal",
            "roadwarden_cloak",
            "barthen_resupply_token",
            "lionshield_quartermaster_badge",
            "innkeeper_credit_token",
            "sella_ballad_token",
            "blackseal_taster_pin",
            "harl_road_knot",
            "kestrel_ledger_clasp",
            "gravequiet_amulet",
            "edermath_scout_buckle",
            "edermath_cache_compass",
            "bryns_cache_keyring",
            "dawnmantle_mercy_charm",
            "pact_waymap_case",
            "agathas_truth_lantern",
            "stonehollow_survey_lantern",
            "woodland_wayfinder_boots",
            "claims_accord_brooch",
            "freed_captive_prayer_beads",
            "forgeheart_cinder",
        }
        for item_id in unique_reward_ids:
            self.assertIn(item_id, ITEMS)
            self.assertTrue(ITEMS[item_id].is_equippable(), item_id)

    def test_act1_reward_unlocks_improve_act2_starting_position(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(304))
        game.state = GameState(
            player=player,
            current_act=2,
            flags={
                "quest_reward_miners_road_open": True,
                "quest_reward_lionshield_logistics": True,
                "quest_reward_elira_mercy_blessing": True,
            },
        )

        game.act2_initialize_metrics(force=True)

        self.assertEqual(game.state.flags["act2_town_stability"], 4)
        self.assertEqual(game.state.flags["act2_route_control"], 4)
        self.assertEqual(game.state.flags["act2_whisper_pressure"], 1)

    def test_enemy_template_smoke(self) -> None:
        enemy = create_enemy("rukhar")
        self.assertEqual(enemy.name, "Rukhar Cinderfang")
        self.assertGreater(enemy.max_hp, 20)
        saboteur = create_enemy("brand_saboteur")
        self.assertEqual(saboteur.name, "Ashen Brand Saboteur")
        self.assertEqual(saboteur.resources["flash_ash"], 1)
        sereth = create_enemy("sereth_vane")
        self.assertEqual(sereth.name, "Sereth Vane")
        self.assertGreaterEqual(sereth.max_hp, 30)
        self.assertIn("leader", sereth.tags)

    def test_new_race_and_class_options_available(self) -> None:
        self.assertIn("Dragonborn", RACES)
        self.assertIn("Gnome", RACES)
        self.assertIn("Tiefling", RACES)
        self.assertIn("Goliath", RACES)
        self.assertIn("Orc", RACES)
        self.assertIn("Half-Orc", RACES)
        self.assertIn("Barbarian", CLASSES)
        self.assertIn("Bard", CLASSES)
        self.assertIn("Monk", CLASSES)
        self.assertIn("Paladin", CLASSES)
        self.assertIn("Druid", CLASSES)
        self.assertIn("Sorcerer", CLASSES)
        self.assertIn("Warlock", CLASSES)
        self.assertIn("Outlander", BACKGROUNDS)
        self.assertIn("Guild Artisan", BACKGROUNDS)

    def test_item_rarity_distribution_favors_lower_tiers(self) -> None:
        counts = Counter(item.rarity for item in ITEMS.values())
        self.assertGreater(counts["common"], counts["uncommon"])
        self.assertGreater(counts["uncommon"], counts["rare"])
        self.assertGreater(counts["rare"], counts["epic"])
        self.assertGreater(counts["epic"], counts["legendary"])
        self.assertLessEqual(counts["legendary"], 5)

    def test_inventory_line_shows_weapon_damage_and_enchantment_rules(self) -> None:
        line = strip_ansi(format_inventory_line("rapier_rare", 1))
        self.assertIn("1d8 piercing", line)
        self.assertIn("enchantment Vicious", line)
        self.assertIn("+2d6 on crit", line)

    def test_sync_equipment_applies_magic_item_traits(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(500))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        player.equipment_slots = {slot: None for slot in ["head", "ring_1", "ring_2", "neck", "chest", "gloves", "boots", "main_hand", "off_hand", "cape"]}
        player.equipment_slots["main_hand"] = "longsword_uncommon"
        player.equipment_slots["boots"] = "silent_step_boots_uncommon"
        player.equipment_slots["chest"] = "breastplate_epic"
        game.sync_equipment(player)
        self.assertEqual(player.gear_bonuses["initiative"], 1)
        self.assertEqual(player.gear_bonuses["stealth_advantage"], 1)
        self.assertEqual(player.gear_bonuses["resist_lightning"], 1)

    def test_consumable_can_grant_temporary_resistance(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(501))
        game.state = GameState(player=player, current_scene="phandalin_hub", inventory={"fireward_elixir": 1})
        used = game.use_item_from_inventory()
        self.assertTrue(used)
        self.assertIn("resist_fire", player.conditions)
        self.assertEqual(game.apply_damage(player, 10, damage_type="fire"), 5)

    def test_character_creation_and_briefing_flow(self) -> None:
        answers = iter(
            [
                "2",  # custom character
                "Aric",  # name
                "1", "1",  # race select + confirm
                "1", "1",  # class select + confirm
                "1", "1",  # background select + confirm
                "1",  # standard array
                "1", "1", "1", "1", "1", "1",  # assign array
                "1", "1",  # fighter skills
                "1",  # confirm character
                "1",  # soldier prologue choice
                "4",  # keep the wayside shrine moving
                "2",  # let Elira stay with the wounded for now
                "3",  # steady Greywake Yard
                "2",  # let Elira keep the line breathing
                "2",  # seize the manifest runner
                "7",  # take the writ
                "1",  # recruit Kaelis on departure
                "1",  # inspect the milehouse writs
                "1",  # silence the signal cairn
                "1",  # take the direct road at the route fork
            ]
        )
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(7))
        game.start_new_game()
        self.assertIsNotNone(game.state)
        self.assertEqual(game.state.current_scene, "background_prologue")
        game.run_encounter = lambda encounter: "victory"
        game.skill_check = lambda actor, skill, dc, context: True
        game.scene_background_prologue()
        self.assertEqual(game.state.current_scene, "wayside_luck_shrine")
        game.scene_wayside_luck_shrine()
        self.assertEqual(game.state.current_scene, "greywake_triage_yard")
        game.scene_greywake_triage_yard()
        self.assertEqual(game.state.current_scene, "greywake_road_breakout")
        game.scene_greywake_road_breakout()
        self.assertEqual(game.state.current_scene, "neverwinter_briefing")
        game.scene_neverwinter_briefing()
        self.assertEqual(game.state.current_scene, "road_ambush")
        self.assertTrue(any(companion.name in {"Kaelis Starling", "Rhogar Valeguard"} for companion in game.state.companions))

    def test_can_recruit_companion_before_first_fight(self) -> None:
        answers = iter(
            [
                "2",
                "Aric",
                "1", "1",
                "1", "1",
                "1", "1",
                "1",
                "1", "1", "1", "1", "1", "1",
                "1", "1",
                "1",
                "1",  # soldier prologue choice
                "4",  # keep the wayside shrine moving
                "2",  # let Elira stay with the wounded for now
                "3",  # steady Greywake Yard
                "2",  # let Elira keep the line breathing
                "2",  # seize the manifest runner
                "7",  # take the writ
                "1",  # recruit Kaelis on departure
                "1",  # inspect the milehouse writs
                "1",  # silence the signal cairn
                "1",  # take the direct road at the route fork
            ]
        )
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(8))
        game.start_new_game()
        game.run_encounter = lambda encounter: "victory"
        game.skill_check = lambda actor, skill, dc, context: True
        game.scene_background_prologue()
        game.scene_wayside_luck_shrine()
        game.scene_greywake_triage_yard()
        game.scene_greywake_road_breakout()
        game.scene_neverwinter_briefing()
        self.assertEqual(game.state.current_scene, "road_ambush")
        self.assertTrue(any(companion.name == "Kaelis Starling" for companion in game.state.companions))

    def test_departure_fork_can_start_blackwake_branch(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["2"])
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(8042))
        game.state = GameState(
            player=player,
            current_scene="neverwinter_briefing",
            flags={
                "act1_started": True,
                "early_companion_recruited": "Kaelis Starling",
                "neverwinter_tymora_shrine_seen": True,
                "neverwinter_high_road_milehouse_seen": True,
                "neverwinter_signal_cairn_seen": True,
            },
        )
        game.handle_neverwinter_departure_fork()
        self.assertEqual(game.state.current_scene, "blackwake_crossing")
        self.assertTrue(game.state.flags["blackwake_started"])
        self.assertIn("trace_blackwake_cell", game.state.quests)
        rendered = self.plain_output(log)
        self.assertIn("Overworld Route Map", rendered)
        self.assertIn("Blackwake Crossing", rendered)

    def test_departure_fork_rumor_backtracks_to_neverwinter(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["3"])
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(8043))
        game.state = GameState(
            player=player,
            current_scene="neverwinter_briefing",
            flags={
                "act1_started": True,
                "early_companion_recruited": "Kaelis Starling",
                "neverwinter_tymora_shrine_seen": True,
                "neverwinter_high_road_milehouse_seen": True,
                "neverwinter_signal_cairn_seen": True,
            },
        )
        game.handle_neverwinter_departure_fork()
        self.assertEqual(game.state.current_scene, "neverwinter_briefing")
        self.assertTrue(game.state.flags["blackwake_neverwinter_rumor"])
        self.assertTrue(any("forged river-cut inspections" in clue for clue in game.state.clues))
        rendered = self.plain_output(log)
        self.assertIn("[BACKTRACK]", rendered)
        self.assertIn("good-looking papers and bad patience", rendered)

    def test_road_ambush_approach_can_backtrack_to_neverwinter(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "4", output_fn=log.append, rng=random.Random(8044))
        game.state = GameState(player=player, current_scene="road_ambush", flags={"act1_started": True})
        encounters: list[Encounter] = []
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"
        game.scene_road_ambush()
        self.assertEqual(game.state.current_scene, "neverwinter_briefing")
        self.assertFalse(game.state.flags.get("road_approach_chosen", False))
        self.assertEqual(encounters, [])
        rendered = self.plain_output(log)
        self.assertIn("Backtrack toward Neverwinter and reconsider the river smoke", rendered)
        self.assertIn("Mira is waiting", rendered)

    def test_road_ambush_flow_recruits_tolan(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(4))
        game.state = GameState(player=player, current_scene="road_ambush", clues=[], journal=[])
        encounters: list[Encounter] = []
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"
        game.scene_road_ambush()
        self.assertEqual(game.state.current_scene, "phandalin_hub")
        self.assertTrue(any(companion.name == "Tolan Ironshield" for companion in game.state.companions))
        self.assertEqual([encounter.title for encounter in encounters], ["Roadside Ambush: First Wave", "High Road Second Wave"])
        rendered = self.plain_output(log)
        self.assertIn("Tolan Ironshield: \"Good. Give me a minute to cinch the shield", rendered)

    def test_sereth_escape_leaves_high_road_followup_note(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["1", "2"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(9209))
        game.state = GameState(
            player=player,
            current_scene="road_ambush",
            clues=[],
            journal=[],
            flags={
                "blackwake_completed": True,
                "blackwake_sereth_fate": "escaped",
            },
        )
        game.skill_check = lambda actor, skill, dc, context: True
        game.run_encounter = lambda encounter: "victory"
        game.scene_road_ambush()
        rendered = self.plain_output(log)
        self.assertIn("S.V. mark", rendered)
        self.assertTrue(game.state.flags["blackwake_sereth_road_note_seen"])
        self.assertTrue(any("Sereth Vane survived Blackwake" in clue for clue in game.state.clues))
        self.assertTrue(any("Sereth Vane's initials surfaced" in entry for entry in game.state.journal))

    def test_cleared_high_road_can_branch_to_liars_circle(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "3", output_fn=log.append, rng=random.Random(9210))
        game.state = GameState(
            player=player,
            current_scene="road_ambush",
            flags={
                "act1_started": True,
                "road_ambush_cleared": True,
                "liars_circle_branch_available": True,
            },
        )
        game.scene_road_ambush()
        self.assertEqual(game.state.current_scene, "high_road_liars_circle")
        self.assertEqual(game.state.flags["map_state"]["current_node_id"], "liars_circle")
        rendered = self.plain_output(log)
        self.assertIn("[PUZZLE] *Follow the overgrown statue trail into the wilderness.", rendered)

    def test_liars_circle_correct_answer_grants_blessing(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 14},
            class_skill_choices=["Athletics", "Survival"],
        )
        deception_before = player.skill_bonus("Deception")
        persuasion_before = player.skill_bonus("Persuasion")
        answers = iter(["5", "3"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(9211))
        game.state = GameState(
            player=player,
            current_scene="high_road_liars_circle",
            flags={"act1_started": True, "road_ambush_cleared": True, "liars_circle_branch_available": True},
        )
        game.scene_high_road_liars_circle()
        self.assertTrue(game.state.flags["liars_circle_solved"])
        self.assertTrue(game.state.flags["liars_circle_locked"])
        self.assertTrue(game.state.flags["liars_blessing_active"])
        self.assertFalse(game.state.flags["liars_circle_branch_available"])
        self.assertEqual(player.skill_bonus("Deception"), deception_before + 2)
        self.assertEqual(player.skill_bonus("Persuasion"), persuasion_before + 1)
        self.assertEqual(player.story_skill_bonuses, {"Deception": 2, "Persuasion": 1})

    def test_liars_circle_wrong_answer_applies_curse(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 14},
            class_skill_choices=["Athletics", "Survival"],
        )
        deception_before = player.skill_bonus("Deception")
        persuasion_before = player.skill_bonus("Persuasion")
        answers = iter(["5", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(9212))
        game.state = GameState(
            player=player,
            current_scene="high_road_liars_circle",
            flags={"act1_started": True, "road_ambush_cleared": True, "liars_circle_branch_available": True},
        )
        game.scene_high_road_liars_circle()
        self.assertTrue(game.state.flags["liars_circle_failed"])
        self.assertTrue(game.state.flags["liars_circle_locked"])
        self.assertTrue(game.state.flags["liars_curse_active"])
        self.assertEqual(game.state.flags["liars_circle_answer"], "knight")
        self.assertEqual(player.skill_bonus("Deception"), deception_before - 1)
        self.assertEqual(player.skill_bonus("Persuasion"), persuasion_before - 1)
        self.assertEqual(player.story_skill_bonuses, {"Deception": -1, "Persuasion": -1})

    def test_liars_curse_clears_on_long_rest(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 14},
            class_skill_choices=["Athletics", "Survival"],
        )
        deception_before = player.skill_bonus("Deception")
        persuasion_before = player.skill_bonus("Persuasion")
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9213))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            inventory={"camp_stew_jar": 3, "bread_round": 4, "goat_cheese": 2},
        )
        game.apply_liars_curse()
        self.assertEqual(player.skill_bonus("Deception"), deception_before - 1)
        self.assertEqual(player.skill_bonus("Persuasion"), persuasion_before - 1)
        game.long_rest()
        self.assertFalse(game.state.flags["liars_curse_active"])
        self.assertEqual(player.story_skill_bonuses, {})
        self.assertEqual(player.skill_bonus("Deception"), deception_before)
        self.assertEqual(player.skill_bonus("Persuasion"), persuasion_before)

    def test_liars_blessing_is_removed_when_player_dies(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 14},
            class_skill_choices=["Athletics", "Survival"],
        )
        deception_before = player.skill_bonus("Deception")
        persuasion_before = player.skill_bonus("Persuasion")
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9214))
        game.state = GameState(player=player, current_scene="road_ambush")
        game.apply_liars_blessing()
        player.current_hp = 0
        player.death_failures = 2
        game.apply_damage(player, 1)
        self.assertTrue(player.dead)
        self.assertFalse(game.state.flags["liars_blessing_active"])
        self.assertTrue(game.state.flags["liars_blessing_lost_to_death"])
        self.assertEqual(player.story_skill_bonuses, {})
        self.assertEqual(player.skill_bonus("Deception"), deception_before)
        self.assertEqual(player.skill_bonus("Persuasion"), persuasion_before)

    def test_story_modifiers_show_on_party_status_and_character_sheet(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 14},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["1", "2"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(9215))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.apply_liars_blessing()
        game.show_party()
        game.show_character_sheets()
        rendered = self.plain_output(log)
        self.assertIn("Story modifiers: Liar's Blessing: Deception +2, Persuasion +1 (until death)", rendered)
        self.assertIn("Story Modifiers:\n- Liar's Blessing: Deception +2, Persuasion +1 (until death)", rendered)

    def test_false_tollstones_without_blessing_uses_harder_deception_check(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 14},
            class_skill_choices=["Athletics", "Survival"],
        )
        checks: list[tuple[str, int]] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(9216))
        game.state = GameState(
            player=player,
            current_scene="high_road_false_tollstones",
            flags={"act1_started": True, "road_ambush_cleared": True, "high_road_tollstones_branch_available": True},
        )

        def fake_skill_check(actor, skill, dc, context):
            checks.append((skill, dc))
            return True

        game.skill_check = fake_skill_check
        game.scene_high_road_false_tollstones()
        self.assertEqual(checks, [("Deception", 14)])
        self.assertTrue(game.state.flags["high_road_tollstones_ledger_taken"])
        self.assertTrue(game.state.flags["system_profile_seeded"])
        self.assertTrue(game.state.flags["varyn_route_pattern_seen"])
        self.assertEqual(game.state.flags["high_road_tollstones_resolution"], "deception")
        self.assertEqual(game.state.current_scene, "phandalin_hub")

    def test_false_tollstones_blessing_path_skips_check_and_adds_passphrase(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 14},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(9217))
        game.state = GameState(
            player=player,
            current_scene="high_road_false_tollstones",
            flags={"act1_started": True, "road_ambush_cleared": True, "high_road_tollstones_branch_available": True},
        )
        game.apply_liars_blessing()

        def fail_skill_check(actor, skill, dc, context):
            raise AssertionError("Liar's Blessing path should not require a skill check")

        game.skill_check = fail_skill_check
        game.scene_high_road_false_tollstones()
        self.assertTrue(game.state.flags["high_road_tollstones_blessing_used"])
        self.assertTrue(game.state.flags["high_road_tollstones_passphrase_known"])
        self.assertTrue(game.state.flags["system_profile_seeded"])
        self.assertTrue(game.state.flags["varyn_route_pattern_seen"])
        self.assertEqual(game.state.flags["high_road_tollstones_resolution"], "blessing")
        self.assertEqual(game.state.inventory.get("antitoxin_vial"), 1)
        self.assertEqual(game.state.xp, 25)
        self.assertEqual(game.state.gold, 16)
        rendered = self.plain_output(log)
        self.assertIn("[LIAR'S BLESSING]", rendered)
        self.assertIn("The false paint almost seems to arrange itself", rendered)

    def test_cleared_high_road_can_branch_to_false_checkpoint(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(92171))
        game.state = GameState(
            player=player,
            current_scene="road_ambush",
            flags={"act1_started": True, "road_ambush_cleared": True},
        )

        def choose_checkpoint(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "Where do you go from the High Road?":
                return self.option_index_containing(options, "false roadwarden checkpoint")
            raise AssertionError(prompt)

        game.scenario_choice = choose_checkpoint  # type: ignore[method-assign]

        game.scene_road_ambush()

        self.assertEqual(game.state.current_scene, "high_road_false_checkpoint")
        self.assertEqual(game.state.flags["map_state"]["current_node_id"], "false_checkpoint")
        rendered = self.plain_output(log)
        self.assertIn("*Challenge the false roadwarden checkpoint.", rendered)

    def test_false_checkpoint_contract_house_proof_skips_skill_check_and_sets_blackwake_leads(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 12},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(92172))
        game.state = GameState(
            player=player,
            current_scene="high_road_false_checkpoint",
            flags={
                "act1_started": True,
                "road_ambush_cleared": True,
                "high_road_false_checkpoint_available": True,
                "false_manifest_oren_detail": True,
                "false_manifest_garren_detail": True,
            },
        )
        game.grant_quest("false_manifest_circuit")

        def fail_skill_check(actor, skill, dc, context):
            raise AssertionError("Contract-house checkpoint proof should not require a skill check")

        game.skill_check = fail_skill_check

        game.scene_high_road_false_checkpoint()

        self.assertTrue(game.state.flags["high_road_false_checkpoint_contract_proof_used"])
        self.assertTrue(game.state.flags["neverwinter_contract_house_checkpoint_pressure"])
        self.assertTrue(game.state.flags["blackwake_false_checkpoint_exposed"])
        self.assertTrue(game.state.flags["blackwake_millers_ford_lead"])
        self.assertTrue(game.state.flags["blackwake_gallows_copse_lead"])
        self.assertTrue(game.state.flags["road_patrol_writ"])
        self.assertTrue(game.state.flags["system_profile_seeded"])
        self.assertTrue(game.state.flags["varyn_route_pattern_seen"])
        self.assertEqual(game.state.flags["high_road_false_checkpoint_resolution"], "proof")
        self.assertEqual(game.state.xp, 30)
        self.assertEqual(game.state.gold, 14)
        self.assertEqual(game.state.current_scene, "phandalin_hub")
        rendered = self.plain_output(log)
        self.assertIn("[CONTRACT HOUSE PROOF]", rendered)
        self.assertIn("Oren's room line, Sabra's corrected manifest", rendered)

    def test_false_checkpoint_insight_path_uses_social_check(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 12},
            class_skill_choices=["Athletics", "Survival"],
        )
        checks: list[tuple[str, int, str]] = []
        game = TextDnDGame(input_fn=lambda _: "2", output_fn=lambda _: None, rng=random.Random(92173))
        game.state = GameState(
            player=player,
            current_scene="high_road_false_checkpoint",
            flags={
                "act1_started": True,
                "road_ambush_cleared": True,
                "high_road_false_checkpoint_available": True,
            },
        )

        def fake_skill_check(actor, skill: str, dc: int, context: str) -> bool:
            checks.append((skill, dc, context))
            return True

        game.skill_check = fake_skill_check  # type: ignore[method-assign]

        game.scene_high_road_false_checkpoint()

        self.assertEqual(checks, [("Insight", 12, "to expose the false roadwarden cadence in their demand")])
        self.assertEqual(game.state.flags["high_road_false_checkpoint_resolution"], "insight")
        self.assertTrue(game.state.flags["blackwake_millers_ford_lead"])
        self.assertTrue(game.state.flags["road_patrol_writ"])
        self.assertTrue(game.state.flags["system_profile_seeded"])
        self.assertTrue(game.state.flags["varyn_route_pattern_seen"])
        self.assertEqual(game.state.current_scene, "phandalin_hub")

    def test_point_buy_character_creation_flow(self) -> None:
        answers = iter(
            [
                "2",
                "Mira",
                "1", "1",
                "1", "1",
                "1", "1",
                "2",
                "15",
                "14",
                "13",
                "10",
                "10",
                "8",
                "1",
                "1",       # skill 1
                "1",       # skill 2
                "1",       # confirm character
            ]
        )
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(9))
        game.start_new_game()
        self.assertIsNotNone(game.state)
        self.assertEqual(game.state.player.ability_scores["STR"], 16)
        self.assertEqual(game.state.player.ability_scores["CHA"], 9)

    def test_preset_character_creation_flow(self) -> None:
        answers = iter(
            [
                "1",  # preset character
                "3",  # Fighter preset
                "1",  # lock preset
                "1",  # begin adventure
            ]
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(44))
        game.start_new_game()
        self.assertIsNotNone(game.state)
        self.assertEqual(game.state.player.class_name, "Fighter")
        self.assertEqual(game.state.player.name, PRESET_CHARACTERS["Fighter"]["name"])
        rendered = self.plain_output(log)
        self.assertIn("3. Fighter", rendered)
        self.assertNotIn(f"3. Fighter: {PRESET_CHARACTERS['Fighter']['description']}", rendered)
        self.assertIn(PRESET_CHARACTERS["Fighter"]["name"], rendered)
        self.assertIn("Preset abilities:", rendered)
        self.assertIn("Starting point:", rendered)

    def test_background_prologues_converge_to_wayside_luck_shrine(self) -> None:
        for background in BACKGROUNDS:
            with self.subTest(background=background):
                player = build_character(
                    name="Vale",
                    race="Human",
                    class_name="Fighter",
                    background=background,
                    base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
                    class_skill_choices=["Athletics", "Survival"],
                )
                game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(445))
                game.state = GameState(player=player, current_scene="background_prologue")
                game.skill_check = lambda actor, skill, dc, context: True
                game.run_encounter = lambda encounter: "victory"
                game.scene_background_prologue()
                self.assertEqual(game.state.current_scene, "wayside_luck_shrine")
                self.assertEqual(game.state.flags["background_prologue_completed"], background)
                self.assertTrue(game.state.flags["system_profile_seeded"])

    def test_background_prologue_shows_starting_rundown(self) -> None:
        player = build_character(
            name="Ash",
            race="Human",
            class_name="Cleric",
            background="Acolyte",
            base_ability_scores={"STR": 10, "DEX": 12, "CON": 13, "INT": 10, "WIS": 15, "CHA": 14},
            class_skill_choices=["Medicine", "Persuasion"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(446))
        game.state = GameState(player=player, current_scene="background_prologue")
        game.skill_check = lambda actor, skill, dc, context: True
        game.run_encounter = lambda encounter: "victory"
        game.scene_background_prologue()
        rendered = self.plain_output(log)
        self.assertIn("Acolyte Prologue: Hall of Justice Hospice", rendered)
        self.assertIn("Starting point:", rendered)
        self.assertIn("poisoned teamster", rendered)

    def test_lore_codex_can_browse_world_entry(self) -> None:
        answers = iter(["1", "4", "2", "10", "2"])
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(440))
        game.show_lore_notes()
        rendered = self.plain_output(log)
        self.assertIn("=== Lore Codex ===", rendered)
        self.assertIn("=== World & Locations: Neverwinter ===", rendered)
        self.assertIn("Jewel of the North", rendered)

    def test_lore_codex_skills_section_has_visible_exit(self) -> None:
        answers = iter(["6", "1", "10", "2"])
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(442))
        game.show_lore_notes()
        rendered = self.plain_output(log)
        self.assertIn("Browse Skills. (page 1)", rendered)
        self.assertIn("1. Return to lore categories", rendered)

    def test_lore_codex_class_entry_includes_gameplay_manual(self) -> None:
        answers = iter(["2", "2", "2", "10", "2"])
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(443))
        game.show_lore_notes()
        rendered = self.plain_output(log).replace("\n", " ")
        self.assertIn("Main stats: Strength, Constitution", rendered)
        self.assertIn("Hit die: d12", rendered)
        self.assertIn("Starting abilities:", rendered)
        self.assertIn("Level 2:", rendered)

    def test_lore_codex_includes_appendix_reference_entries(self) -> None:
        answers = iter(["8", "2", "2", "10", "2"])
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(445))
        game.show_lore_notes()
        rendered = self.plain_output(log)
        self.assertIn("=== Appendices: Appendix A: Conditions ===", rendered)
        self.assertIn("Contents:", rendered)
        self.assertIn("- Unconscious", rendered)
        self.assertGreaterEqual(len(APPENDIX_LORE), 30)
        self.assertIn("Appendix B: Forgotten Realms Deities", APPENDIX_LORE)
        self.assertIn("Appendix D: Demiplanes", APPENDIX_LORE)

    def test_lore_codex_includes_item_manual_entries(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "10", output_fn=lambda _: None, rng=random.Random(444))
        entries = game.item_manual_entries()
        self.assertIn("Weapons", entries)
        self.assertIn("Consumables and Potions", entries)
        self.assertIn("Scrolls", entries)
        self.assertIn("one-use", entries["Consumables and Potions"]["text"])

    def test_class_choice_displays_expanded_lore(self) -> None:
        answers = iter(["2", "1"])
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(441))
        selected = game.choose_named_option("Choose a class", CLASSES)
        self.assertEqual(selected, "Bard")
        rendered = self.plain_output(log).replace("\n", " ")
        self.assertIn("song of creation", rendered)
        self.assertIn("read a room", rendered)

    def test_class_identity_option_appears_in_briefing(self) -> None:
        player = build_character(
            name="Mira",
            race="Human",
            class_name="Bard",
            background="Charlatan",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 13, "INT": 10, "WIS": 12, "CHA": 15},
            class_skill_choices=["Insight", "Performance", "Persuasion"],
        )
        log: list[str] = []
        answers = iter(["1", "3", "5", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(3010))
        game.state = GameState(
            player=player,
            current_scene="neverwinter_briefing",
            flags={
                "early_companion_recruited": "Kaelis Starling",
                "neverwinter_tymora_shrine_seen": True,
                "neverwinter_high_road_milehouse_seen": True,
                "neverwinter_signal_cairn_seen": True,
            },
        )
        game.scene_neverwinter_briefing()
        rendered = self.plain_output(log)
        self.assertIn("better story and a sharper tongue", rendered)
        self.assertIn("Reward gained for Bard identity choice: 10 XP, 6 gp.", rendered)

    def test_neverwinter_briefing_routes_response_menu_through_keyboard_choice_menu(self) -> None:
        player = build_character(
            name="Vale",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(3011))
        game.state = GameState(player=player, current_scene="neverwinter_briefing", flags={"briefing_seen": True})
        game.scene_identity_options = lambda scene_key: []
        game.offer_early_companion = lambda: None
        game.handle_neverwinter_departure_fork = lambda: setattr(game.state, "current_scene", "road_ambush")
        game.player_choice_output = lambda text: None
        game.keyboard_choice_menu_supported = lambda: True
        seen: dict[str, object] = {}
        game.add_journal = lambda entry: seen.setdefault("journal_entries", []).append(entry)

        def fake_run(prompt, options, *, title=None):
            seen["prompt"] = prompt
            seen["options"] = list(options)
            seen["title"] = title
            return len(options)

        game.run_keyboard_choice_menu = fake_run
        game.scene_neverwinter_briefing()
        self.assertEqual(seen["prompt"], "Choose your response to Mira.")
        self.assertIn("*Take the writ and head for the High Road.", seen["options"])
        self.assertEqual(game.state.current_scene, "road_ambush")

    def test_race_identity_option_appears_on_phandalin_arrival(self) -> None:
        player = build_character(
            name="Cairn",
            race="Tiefling",
            class_name="Warlock",
            background="Charlatan",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 13, "INT": 10, "WIS": 12, "CHA": 15},
            class_skill_choices=["Intimidation", "Investigation"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(3011))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        option_key, option_text = game.scene_identity_options("phandalin_arrival")[0]
        self.assertIn("look ominous enough to trust", option_text)
        game.handle_scene_identity_action("phandalin_arrival", option_key)
        rendered = self.plain_output(log)
        self.assertIn("Embarrassed honesty starts doing", rendered)

    def test_point_buy_can_repick_scores_at_end(self) -> None:
        answers = iter(
            [
                "2",
                "8",
                "8",
                "8",
                "8",
                "8",
                "8",
                "2",
                "15",
                "14",
                "13",
                "10",
                "10",
                "8",
                "1",
            ]
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(31))
        scores = game.choose_ability_scores()
        self.assertEqual(scores, {"STR": 15, "DEX": 14, "CON": 13, "INT": 10, "WIS": 10, "CHA": 8})
        rendered = self.plain_output(log)
        self.assertIn("Points left:", rendered)
        self.assertIn("Let's repick the full stat spread.", rendered)

    def test_background_choice_hides_descriptions_until_selected(self) -> None:
        answers = iter(["1", "1"])
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(32))
        selected = game.choose_named_option("Choose a background", BACKGROUNDS)
        self.assertEqual(selected, "Soldier")
        rendered = self.plain_output(log)
        self.assertIn("  1. Soldier", rendered)
        self.assertNotIn("1. Soldier: A veteran of militia drills", rendered)
        self.assertIn("Extra proficiencies: Land Vehicles, Gaming", rendered)

    def test_build_character_includes_background_bonus_proficiencies(self) -> None:
        character = build_character(
            name="Nim",
            race="Halfling",
            class_name="Rogue",
            background="Criminal",
            base_ability_scores={"STR": 8, "DEX": 15, "CON": 12, "INT": 10, "WIS": 14, "CHA": 13},
            class_skill_choices=["Acrobatics", "Perception", "Sleight of Hand", "Stealth"],
            expertise_choices=["Stealth", "Perception"],
        )
        self.assertEqual(character.bonus_proficiencies, ["Thieves' Tools", "Disguise Kit"])

    def test_party_limit_sends_extra_companion_to_camp(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(33))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.recruit_companion(create_tolan_ironshield())
        game.recruit_companion(create_kaelis_starling())
        game.recruit_companion(create_elira_dawnmantle())
        self.assertEqual(len(game.state.companions), 3)
        game.recruit_companion(create_rhogar_valeguard())
        self.assertEqual(len(game.state.companions), 3)
        self.assertEqual(len(game.state.camp_companions), 1)
        self.assertEqual(game.state.camp_companions[0].name, "Rhogar Valeguard")

    def test_active_party_recruit_catches_up_to_current_party_level(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(
            input_fn=lambda _: (_ for _ in ()).throw(AssertionError("companion catch-up should not prompt")),
            output_fn=lambda _: None,
            rng=random.Random(331),
        )
        game.state = GameState(player=player, current_scene="phandalin_hub")
        for next_level in (2, 3):
            game.level_up_character_automatically(player, next_level, announce=False)
        companion = create_tolan_ironshield()
        self.assertEqual(companion.level, 1)
        game.recruit_companion(companion)
        self.assertEqual(companion.level, 3)
        self.assertIs(game.state.companions[0], companion)

    def test_companion_from_camp_catches_up_when_joining_active_party(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(
            input_fn=lambda _: (_ for _ in ()).throw(AssertionError("companion catch-up should not prompt")),
            output_fn=lambda _: None,
            rng=random.Random(332),
        )
        game.state = GameState(player=player, current_scene="phandalin_hub")
        for next_level in (2, 3, 4):
            game.level_up_character_automatically(player, next_level, announce=False)
        game.recruit_companion(create_tolan_ironshield())
        game.recruit_companion(create_kaelis_starling())
        game.recruit_companion(create_elira_dawnmantle())
        game.recruit_companion(create_rhogar_valeguard())
        rhogar = game.state.camp_companions[0]
        self.assertEqual(rhogar.level, 1)
        game.move_companion_to_camp(game.state.companions[0])
        self.assertTrue(game.move_companion_to_party(rhogar))
        self.assertEqual(rhogar.level, 4)
        self.assertIn(rhogar, game.state.companions)

    def test_talking_to_companion_improves_disposition(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companion = create_tolan_ironshield()
        answers = iter(["1", "1", "5"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(34))
        game.state = GameState(player=player, companions=[companion], current_scene="phandalin_hub")
        game.talk_to_companion()
        self.assertEqual(companion.disposition, 1)
        self.assertIn("old_road", companion.bond_flags["talked_topics"])

    def test_companion_talk_uses_quotes_and_actions(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companion = create_tolan_ironshield()
        log: list[str] = []
        answers = iter(["1", "1", "4", "5"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(341))
        game.state = GameState(player=player, companions=[companion], current_scene="phandalin_hub")
        game.talk_to_companion()
        rendered = self.plain_output(log)
        self.assertIn('"Tell me about the worst road you ever guarded."', rendered)
        self.assertIn('Tolan Ironshield: "Sleet, broken axles', rendered)
        self.assertIn("*Ask how they see you now.", rendered)

    def test_blackwake_camp_topics_are_flag_gated(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        first_log: list[str] = []
        first_answers = iter(["1", "5"])
        first_companion = create_kaelis_starling()
        first_game = TextDnDGame(input_fn=lambda _: next(first_answers), output_fn=first_log.append, rng=random.Random(9202))
        first_game.state = GameState(player=player, companions=[first_companion], current_scene="camp")
        first_game.talk_to_companion()
        self.assertNotIn("What happened at the crossing?", self.plain_output(first_log))

        second_log: list[str] = []
        second_answers = iter(["1", "4", "6"])
        second_companion = create_kaelis_starling()
        second_game = TextDnDGame(input_fn=lambda _: next(second_answers), output_fn=second_log.append, rng=random.Random(9203))
        second_game.state = GameState(
            player=player,
            companions=[second_companion],
            current_scene="camp",
            flags={"blackwake_completed": True},
        )
        second_game.talk_to_companion()
        rendered = self.plain_output(second_log)
        self.assertIn("What happened at the crossing?", rendered)
        self.assertIn("That is not banditry. That is logistics with a knife.", rendered)
        self.assertIn("blackwake_crossing", second_companion.bond_flags["talked_topics"])

    def test_campfire_banter_applies_relationship_lore_and_consequences(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        elira = create_elira_dawnmantle()
        tolan = create_tolan_ironshield()
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(9204))
        game.state = GameState(
            player=player,
            companions=[elira, tolan],
            current_scene="camp",
            flags={
                "greywake_triage_yard_seen": True,
                "greywake_manifest_preserved": True,
                "greywake_wounded_stabilized": True,
                "act1_town_fear": 2,
                "act1_ashen_strength": 3,
                "act1_survivors_saved": 0,
            },
        )
        banter = next(
            entry for entry in game.available_camp_banters() if entry["id"] == "camp_banter_elira_tolan_greywake"
        )
        game.run_camp_banter(banter)
        rendered = self.plain_output(log)
        self.assertIn("The Wounded Line", rendered)
        self.assertIn("Names sorted into outcomes. Tymora hates a loaded die.", rendered)
        self.assertTrue(game.state.flags["camp_banter_elira_tolan_greywake_seen"])
        self.assertTrue(game.state.flags["camp_greywake_testimony_threaded"])
        self.assertTrue(game.state.flags["camp_greywake_manifest_read_as_schedule"])
        self.assertEqual(elira.disposition, 1)
        self.assertEqual(tolan.disposition, 1)
        self.assertEqual(game.state.flags["act1_town_fear"], 1)
        self.assertEqual(player.conditions.get("blessed"), 1)
        self.assertIn("camp_banter_elira_tolan_greywake", elira.bond_flags["camp_banters"])
        self.assertTrue(any("witness protection" in entry for entry in elira.lore))
        self.assertIn(
            "Elira and Tolan agree Greywake was a pre-sorted outcome system, not ordinary panic or battlefield accident.",
            game.state.clues,
        )
        self.assertFalse(
            any(entry["id"] == "camp_banter_elira_tolan_greywake" for entry in game.available_camp_banters())
        )

    def test_dialogue_inputs_require_active_companions_and_mark_seen(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        tolan = create_tolan_ironshield()
        bryn = create_bryn_underbough()
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(92041))
        game.state = GameState(
            player=player,
            companions=[tolan],
            camp_companions=[bryn],
            current_scene="phandalin_hub",
        )

        self.assertEqual(game.run_dialogue_input("barthen_shortage"), 1)
        self.assertEqual(game.run_dialogue_input("barthen_shortage"), 0)

        rendered = self.plain_output(log)
        self.assertIn("Empty shelves are a siege by another name.", rendered)
        self.assertNotIn("Roads fail quietly first.", rendered)
        self.assertTrue(game.state.flags["dialogue_input_tolan_barthen_shortage_seen"])
        self.assertIn("dialogue_input_tolan_barthen_shortage", tolan.bond_flags["dialogue_inputs"])
        self.assertNotIn("dialogue_inputs", bryn.bond_flags)

    def test_barthen_shortage_runs_active_companion_input(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(92042))
        game.state = GameState(
            player=player,
            companions=[create_tolan_ironshield()],
            current_scene="phandalin_hub",
        )

        def choose_barthen(prompt: str, options: list[str], **kwargs) -> int:
            if any("run short" in strip_ansi(option) for option in options):
                return self.option_index_containing(options, "run short")
            return self.option_index_containing(options, "Leave the provision house")

        game.scenario_choice = choose_barthen  # type: ignore[method-assign]

        game.visit_barthen_provisions()

        rendered = self.plain_output(log)
        self.assertIn("Food that keeps, bandages, lamp oil", rendered)
        self.assertIn("Empty shelves are a siege by another name.", rendered)
        self.assertTrue(game.state.flags["barthen_shortage_asked"])
        self.assertTrue(game.has_quest("restore_barthen_supplies"))

    def test_act2_claims_council_runs_opening_and_sponsor_inputs(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["1", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(92043))
        game.state = GameState(
            player=player,
            companions=[create_rhogar_valeguard(), create_tolan_ironshield(), create_bryn_underbough()],
            current_act=2,
            current_scene="act2_claims_council",
            flags={"act2_started": True, "act2_town_stability": 3, "act2_route_control": 3, "act2_whisper_pressure": 2},
        )
        game.skill_check = lambda actor, skill, dc, context: False  # type: ignore[method-assign]

        game.scene_act2_claims_council()

        rendered = self.plain_output(log)
        self.assertIn("If this room wants a claim, make it name who the claim protects.", rendered)
        self.assertIn("Maps are useful. So are hands to carry the wounded", rendered)
        self.assertIn("Halia will move fast. Fast gets answers.", rendered)
        self.assertEqual(game.state.flags["act2_sponsor"], "exchange")
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")

    def test_act2_forge_dialogue_inputs_emit_top_priorities(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(92044))
        game.state = GameState(
            player=player,
            companions=[create_irielle_ashwake(), create_nim_ardentglass(), create_elira_dawnmantle()],
            current_act=2,
            current_scene="forge_of_spells",
        )

        self.assertEqual(game.run_dialogue_input("act2_forge_entry", max_entries=2), 2)

        rendered = self.plain_output(log)
        self.assertIn("Do not let her speak uninterrupted.", rendered)
        self.assertIn("The Forge was made to shape possibility.", rendered)
        self.assertNotIn("If she calls suffering clarity", rendered)

    def test_camp_menu_keeps_break_camp_at_seven_when_banter_is_available(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["7"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(9205))
        game.state = GameState(
            player=player,
            companions=[create_elira_dawnmantle(), create_tolan_ironshield()],
            current_scene="camp",
            flags={"greywake_triage_yard_seen": True, "greywake_wounded_stabilized": True},
        )
        game.open_camp_menu()
        rendered = self.plain_output(log)
        self.assertIn("Listen around the campfire", rendered)
        self.assertIn("The campfire is banked", rendered)
        self.assertFalse(game.state.flags.get("camp_banter_elira_tolan_greywake_seen", False))

    def test_act3_camp_banter_hides_malzurath_until_reveal(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )

        hidden_log: list[str] = []
        hidden_game = TextDnDGame(input_fn=lambda _: "1", output_fn=hidden_log.append, rng=random.Random(9206))
        hidden_game.state = GameState(
            player=player,
            companions=[create_bryn_underbough(), create_elira_dawnmantle()],
            current_scene="camp",
            current_act=3,
            flags={"act3_started": True, "varyn_route_displaced": True},
        )
        hidden_banter = next(
            entry
            for entry in hidden_game.available_camp_banters()
            if entry["id"] == "camp_banter_bryn_elira_route_displacement"
        )
        hidden_game.run_camp_banter(hidden_banter)
        hidden_rendered = self.plain_output(hidden_log)
        self.assertIn("Roads should not have intentions.", hidden_rendered)
        self.assertNotIn("Malzurath", hidden_rendered)
        self.assertFalse(hidden_game.state.flags.get("act3_companion_testimony_count"))

        revealed_log: list[str] = []
        revealed_game = TextDnDGame(input_fn=lambda _: "1", output_fn=revealed_log.append, rng=random.Random(9207))
        revealed_game.state = GameState(
            player=player,
            companions=[create_bryn_underbough(), create_elira_dawnmantle()],
            current_scene="camp",
            current_act=3,
            flags={"act3_started": True, "varyn_route_displaced": True, "malzurath_revealed": True},
        )
        revealed_banter = next(
            entry
            for entry in revealed_game.available_camp_banters()
            if entry["id"] == "camp_banter_bryn_elira_route_displacement"
        )
        revealed_game.run_camp_banter(revealed_banter)
        revealed_rendered = self.plain_output(revealed_log)
        self.assertIn("Malzurath sorts meaning.", revealed_rendered)
        self.assertEqual(revealed_game.state.flags["act3_companion_testimony_count"], 1)
        self.assertEqual(revealed_game.state.flags["act3_mercy_or_contradiction_count"], 1)

    def test_terrible_relationship_causes_companion_to_leave(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companion = create_tolan_ironshield()
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(35))
        game.state = GameState(player=player, companions=[companion], current_scene="phandalin_hub")
        game.adjust_companion_disposition(companion, -6, "testing cruelty")
        self.assertFalse(any(member.name == "Tolan Ironshield" for member in game.state.all_companions()))
        self.assertIn("Tolan Ironshield", game.state.flags["departed_companions"])

    def test_magic_mirror_respec_costs_gold_and_preserves_level(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        player.level = 2
        answers = iter(
            [
                "1",  # confirm respec
                "3", "1",  # Elf
                "1", "1",  # Fighter
                "4", "1",  # Sage
                "2",  # point buy
                "15", "14", "13", "10", "10", "8",
                "1",  # keep scores
                "1", "1",  # fighter skills
                "1",  # level-up skill at level 2
            ]
        )
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(36))
        game.state = GameState(player=player, current_scene="phandalin_hub", gold=150)
        game.visit_magic_mirror()
        self.assertEqual(game.state.gold, 50)
        self.assertEqual(game.state.player.level, 2)
        self.assertEqual(game.state.player.race, "Elf")
        self.assertEqual(game.state.player.background, "Sage")

    def test_choose_paginates_when_list_is_long(self) -> None:
        answers = iter(["10", "2"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(2))
        result = game.choose("Pick one", [f"Option {index}" for index in range(1, 12)], allow_meta=False)
        self.assertEqual(result, 11)

    def test_single_option_still_requires_manual_selection(self) -> None:
        answers = iter(["2", "1"])
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(204))
        result = game.choose("Only one path is open.", ["Continue"], allow_meta=False)
        self.assertEqual(result, 1)
        rendered = self.plain_output(log)
        self.assertIn("Only one path is open.", rendered)
        self.assertIn("1. Continue", rendered)
        self.assertIn("Please enter a listed number.", rendered)

    def test_road_ambush_scales_for_solo_party(self) -> None:
        player = build_character(
            name="Nyra",
            race="Elf",
            class_name="Wizard",
            background="Sage",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10},
            class_skill_choices=["Arcana", "Investigation"],
        )
        captures: list[dict[str, object]] = []

        def fake_run(encounter):
            captures.append(
                {
                    "enemy_count": len(encounter.enemies),
                    "parley_dc": encounter.parley_dc,
                    "temp_hp": game.state.player.temp_hp,
                    "title": encounter.title,
                }
            )
            return "victory"

        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(5))
        game.state = GameState(player=player, current_scene="road_ambush", clues=[], journal=[])
        game.run_encounter = fake_run
        game.scene_road_ambush()
        self.assertEqual(captures[0]["title"], "Roadside Ambush: First Wave")
        self.assertEqual(captures[0]["enemy_count"], 2)
        self.assertEqual(captures[0]["parley_dc"], 12)
        self.assertGreaterEqual(captures[0]["temp_hp"], 6)
        self.assertEqual(captures[1]["title"], "High Road Second Wave")

    def test_road_ambush_scales_for_two_member_party(self) -> None:
        player = build_character(
            name="Nyra",
            race="Elf",
            class_name="Wizard",
            background="Sage",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10},
            class_skill_choices=["Arcana", "Investigation"],
        )
        companion = create_kaelis_starling()
        captures: list[dict[str, object]] = []

        def fake_run(encounter):
            captures.append({"enemy_count": len(encounter.enemies), "parley_dc": encounter.parley_dc, "title": encounter.title})
            return "victory"

        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(45))
        game.state = GameState(player=player, companions=[companion], current_scene="road_ambush", clues=[], journal=[])
        game.run_encounter = fake_run
        game.scene_road_ambush()
        self.assertEqual(captures[0]["title"], "Roadside Ambush: First Wave")
        self.assertEqual(captures[0]["enemy_count"], 2)
        self.assertEqual(captures[0]["parley_dc"], 12)
        self.assertEqual(captures[1]["title"], "High Road Second Wave")

    def test_road_ambush_intimidation_works_for_solo_party(self) -> None:
        player = build_character(
            name="Velkor",
            race="Half-Orc",
            class_name="Paladin",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 10, "CON": 13, "INT": 8, "WIS": 12, "CHA": 14},
            class_skill_choices=["Athletics", "Intimidation"],
        )
        answers = iter(["3", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(11))
        game.state = GameState(player=player, current_scene="road_ambush", clues=[], journal=[])
        game.run_encounter = lambda encounter: "victory"
        game.scene_road_ambush()
        self.assertEqual(game.state.current_scene, "phandalin_hub")

    def test_road_ambush_athletics_success_grants_real_combat_advantage(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["1", "1"])
        captures: list[list[dict[str, int]]] = []

        def fake_run(encounter):
            captures.append([dict(enemy.conditions) for enemy in encounter.enemies])
            return "victory"

        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(111))
        game.state = GameState(player=player, current_scene="road_ambush", clues=[], journal=[])
        game.skill_check = lambda actor, skill, dc, context: skill == "Athletics"
        game.run_encounter = fake_run
        game.scene_road_ambush()
        self.assertEqual(player.conditions.get("emboldened"), 2)
        self.assertEqual(captures[0][0].get("prone"), 1)

    def test_road_ambush_intimidation_failure_emboldens_enemies(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["3", "1"])
        captures: list[list[dict[str, int]]] = []

        def fake_run(encounter):
            captures.append([dict(enemy.conditions) for enemy in encounter.enemies])
            return "victory"

        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(112))
        game.state = GameState(player=player, current_scene="road_ambush", clues=[], journal=[])
        game.skill_check = lambda actor, skill, dc, context: False
        game.run_encounter = fake_run
        game.scene_road_ambush()
        self.assertTrue(all("emboldened" in conditions for conditions in captures[0]))

    def test_road_ambush_intimidation_choice_renders_as_action(self) -> None:
        player = build_character(
            name="Riven Ashguard",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["3", "1"])
        log: list[str] = []

        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(113))
        game.state = GameState(player=player, current_scene="road_ambush", clues=[], journal=[])
        game.skill_check = lambda actor, skill, dc, context: False
        game.run_encounter = lambda encounter: "victory"
        game.scene_road_ambush()
        rendered = self.plain_output(log)
        self.assertIn("*Break their nerve with a warning shout.", rendered)
        self.assertNotIn('Riven Ashguard: "Break their nerve with a warning shout."', rendered)

    def test_all_heroes_use_player_controlled_turns(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companion = build_character(
            name="Kaelis",
            race="Half-Elf",
            class_name="Ranger",
            background="Criminal",
            base_ability_scores={"STR": 10, "DEX": 15, "CON": 13, "INT": 11, "WIS": 14, "CHA": 12},
            class_skill_choices=["Perception", "Stealth", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(12))
        game.state = GameState(player=player, companions=[companion], current_scene="road_ambush")
        called: list[str] = []

        def fake_player_turn(actor, heroes, enemies, encounter, dodging):
            called.append(actor.name)
            return None

        game.player_turn = fake_player_turn
        result = game.hero_turn(companion, [player, companion], [create_enemy("goblin_skirmisher")], None, set())
        self.assertIsNone(result)
        self.assertEqual(called, ["Kaelis"])

    def test_knockout_message_happens_after_hit_message(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companion = build_character(
            name="Kaelis",
            race="Half-Elf",
            class_name="Ranger",
            background="Criminal",
            base_ability_scores={"STR": 10, "DEX": 15, "CON": 13, "INT": 11, "WIS": 14, "CHA": 12},
            class_skill_choices=["Perception", "Stealth", "Survival"],
        )
        companion.current_hp = 4
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(13))
        game.roll_with_advantage = lambda actor, advantage_state: SimpleNamespace(kept=18)
        enemy = create_enemy("bandit")
        enemy.weapon.damage = "1d4+3"
        game.perform_enemy_attack(enemy, companion, [player, companion], [enemy], set())
        hit_index = next(index for index, line in enumerate(log) if "hits Kaelis for" in line)
        down_index = next(index for index, line in enumerate(log) if "Kaelis falls unconscious" in line)
        self.assertLess(hit_index, down_index)

    def test_reward_party_grants_xp_gold_and_levels_player(self) -> None:
        answers = iter(["1"])
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(14))
        game.state = GameState(player=player, current_scene="phandalin_hub", clues=[], journal=[], xp=290, gold=5)
        game.reward_party(xp=20, gold=7, reason="testing rewards")
        self.assertEqual(game.state.xp, 310)
        self.assertEqual(game.state.gold, 12)
        self.assertEqual(game.state.player.level, 2)
        self.assertIn("action_surge", game.state.player.features)
        self.assertEqual(game.state.player.resources.get("action_surge"), 1)

    def test_combat_options_only_tag_skill_check_actions(self) -> None:
        player = build_character(
            name="Velkor",
            race="Dragonborn",
            class_name="Paladin",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 10, "CON": 13, "INT": 8, "WIS": 12, "CHA": 14},
            class_skill_choices=["Athletics", "Intimidation"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(15))
        game.state = GameState(player=player, inventory={"potion_healing": 1}, current_scene="road_ambush")
        options = game.get_player_combat_options(player, SimpleNamespace(allow_parley=True, allow_flee=True))
        self.assertIn("Attack with Divine Smite", options)
        self.assertIn("[PERSUASION / INTIMIDATION] Attempt Parley", options)
        self.assertIn("[STEALTH] Try to Flee", options)
        self.assertIn("Drink a Healing Potion", options)
        self.assertFalse(options[0].startswith("["))

    def test_second_wind_is_a_bonus_action_and_still_allows_attack(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        enemy = create_enemy("bandit")
        player.current_hp = max(1, player.current_hp - 5)
        answers = iter(["3", "1", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(8151))
        game.state = GameState(player=player, current_scene="road_ambush")
        game.perform_weapon_attack = lambda attacker, target, heroes, enemies, dodging, use_smite=False: setattr(target, "current_hp", target.current_hp - 1)
        game.player_turn(player, [player], [enemy], Encounter(title="Test", description="", enemies=[enemy], allow_flee=False), set())
        self.assertGreater(player.current_hp, 5)
        self.assertLess(enemy.current_hp, enemy.max_hp)

    def test_drinking_healing_potion_is_bonus_action_and_feeding_one_is_action(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Rogue",
            background="Criminal",
            base_ability_scores={"STR": 8, "DEX": 15, "CON": 12, "INT": 10, "WIS": 14, "CHA": 13},
            class_skill_choices=["Acrobatics", "Perception", "Sleight of Hand", "Stealth"],
            expertise_choices=["Stealth", "Perception"],
        )
        ally = create_tolan_ironshield()
        ally.current_hp = max(1, ally.current_hp - 5)
        enemy = create_enemy("bandit")

        self_answers = iter(["4", "1", "1"])
        self_game = TextDnDGame(input_fn=lambda _: next(self_answers), output_fn=lambda _: None, rng=random.Random(8152))
        self_game.state = GameState(player=player, companions=[ally], current_scene="road_ambush", inventory={"potion_healing": 1})
        player.current_hp = max(1, player.current_hp - 4)
        player_before = player.current_hp
        self_game.perform_weapon_attack = lambda attacker, target, heroes, enemies, dodging, use_smite=False: setattr(target, "current_hp", target.current_hp - 1)
        self_game.player_turn(player, [player, ally], [enemy], Encounter(title="Test", description="", enemies=[enemy], allow_flee=False), set())
        self.assertGreater(player.current_hp, player_before)
        self.assertLess(enemy.current_hp, enemy.max_hp)

        feed_answers = iter(["2", "1"])
        feed_game = TextDnDGame(input_fn=lambda _: next(feed_answers), output_fn=lambda _: None, rng=random.Random(8153))
        feed_player = build_character(
            name="Velkor",
            race="Human",
            class_name="Rogue",
            background="Criminal",
            base_ability_scores={"STR": 8, "DEX": 15, "CON": 12, "INT": 10, "WIS": 14, "CHA": 13},
            class_skill_choices=["Acrobatics", "Perception", "Sleight of Hand", "Stealth"],
            expertise_choices=["Stealth", "Perception"],
        )
        feed_ally = create_tolan_ironshield()
        feed_ally.current_hp = max(1, feed_ally.current_hp - 5)
        ally_before = feed_ally.current_hp
        feed_enemy = create_enemy("bandit")
        feed_game.state = GameState(player=feed_player, companions=[feed_ally], current_scene="road_ambush", inventory={"potion_healing": 1})
        feed_game.player_turn(feed_player, [feed_player, feed_ally], [feed_enemy], Encounter(title="Test", description="", enemies=[feed_enemy], allow_flee=False), set())
        self.assertGreater(feed_ally.current_hp, ally_before)
        self.assertEqual(feed_enemy.current_hp, feed_enemy.max_hp)

    def test_bonus_action_spell_allows_cantrip_but_blocks_leveled_action_spell(self) -> None:
        player = build_character(
            name="Ash",
            race="Human",
            class_name="Cleric",
            background="Acolyte",
            base_ability_scores={"STR": 10, "DEX": 12, "CON": 13, "INT": 10, "WIS": 15, "CHA": 14},
            class_skill_choices=["Medicine", "Persuasion"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(8154))
        game.state = GameState(player=player, current_scene="road_ambush")
        options = game.get_player_combat_options(
            player,
            SimpleNamespace(allow_parley=False, allow_flee=False),
            turn_state=TurnState(bonus_action_spell_cast=True),
            heroes=[player],
        )
        self.assertIn("Cast Sacred Flame", options)
        self.assertNotIn("Cast Cure Wounds", options)

    def test_healing_word_is_bonus_action_and_still_allows_action_cantrip(self) -> None:
        player = build_character(
            name="Ash",
            race="Human",
            class_name="Cleric",
            background="Acolyte",
            base_ability_scores={"STR": 10, "DEX": 12, "CON": 13, "INT": 10, "WIS": 15, "CHA": 14},
            class_skill_choices=["Medicine", "Persuasion"],
        )
        ally = create_tolan_ironshield()
        ally.current_hp = max(1, ally.current_hp - 5)
        enemy = create_enemy("bandit")
        answers = iter(["5", "2", "2", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(8155))
        game.state = GameState(player=player, companions=[ally], current_scene="road_ambush")
        game.saving_throw = lambda actor, ability, dc, context, against_poison=False: False
        ally_before = ally.current_hp
        game.player_turn(player, [player, ally], [enemy], Encounter(title="Test", description="", enemies=[enemy], allow_flee=False), set())
        self.assertGreater(ally.current_hp, ally_before)
        self.assertLess(enemy.current_hp, enemy.max_hp)

    def test_monk_attack_can_chain_into_martial_arts_bonus_strike(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Monk",
            background="Hermit",
            base_ability_scores={"STR": 10, "DEX": 15, "CON": 13, "INT": 10, "WIS": 14, "CHA": 8},
            class_skill_choices=["Acrobatics", "Insight"],
        )
        enemy = create_enemy("bandit")
        answers = iter(["1", "1", "1", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(8156))
        game.state = GameState(player=player, current_scene="road_ambush")
        game.player_turn(player, [player], [enemy], Encounter(title="Test", description="", enemies=[enemy], allow_flee=False), set())
        self.assertLessEqual(enemy.current_hp, enemy.max_hp - 2)

    def test_dual_wield_off_hand_attack_unlocks_after_attack_action(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Rogue",
            background="Criminal",
            base_ability_scores={"STR": 8, "DEX": 15, "CON": 12, "INT": 10, "WIS": 14, "CHA": 13},
            class_skill_choices=["Acrobatics", "Perception", "Sleight of Hand", "Stealth"],
            expertise_choices=["Stealth", "Perception"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(8157))
        game.state = GameState(player=player, current_scene="road_ambush", inventory={"shortsword_common": 1, "dagger_common": 1})
        player.equipment_slots = {slot: None for slot in ["head", "ring_1", "ring_2", "neck", "chest", "gloves", "boots", "main_hand", "off_hand", "cape"]}
        player.equipment_slots["main_hand"] = "shortsword_common"
        player.equipment_slots["off_hand"] = "dagger_common"
        game.sync_equipment(player)
        options = game.get_player_combat_options(
            player,
            SimpleNamespace(allow_parley=False, allow_flee=False),
            turn_state=TurnState(attack_action_taken=True),
            heroes=[player],
        )
        self.assertIn("Make Off-Hand Attack", options)

    def test_level_two_rogue_gets_cunning_action_option(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Rogue",
            background="Criminal",
            base_ability_scores={"STR": 8, "DEX": 15, "CON": 12, "INT": 10, "WIS": 14, "CHA": 13},
            class_skill_choices=["Acrobatics", "Perception", "Sleight of Hand", "Stealth"],
            expertise_choices=["Stealth", "Perception"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(8158))
        game.state = GameState(player=player, current_scene="road_ambush")
        game.level_up_character(player, 2)
        options = game.get_player_combat_options(
            player,
            SimpleNamespace(allow_parley=False, allow_flee=False),
            turn_state=TurnState(),
            heroes=[player],
        )
        self.assertIn("Use Cunning Action", options)

    def test_level_two_monk_gets_ki_bonus_action_options(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Monk",
            background="Hermit",
            base_ability_scores={"STR": 10, "DEX": 15, "CON": 13, "INT": 10, "WIS": 14, "CHA": 8},
            class_skill_choices=["Acrobatics", "Insight"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(8159))
        game.state = GameState(player=player, current_scene="road_ambush")
        game.level_up_character(player, 2)
        options = game.get_player_combat_options(
            player,
            SimpleNamespace(allow_parley=False, allow_flee=False),
            turn_state=TurnState(attack_action_taken=True),
            heroes=[player],
        )
        self.assertIn("Use Flurry of Blows", options)
        self.assertIn("Use Patient Defense", options)
        self.assertIn("Use Step of the Wind", options)

    def test_help_downed_ally_can_restore_them_to_one_hp(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        ally = build_character(
            name="Tolan",
            race="Dwarf",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 10, "CON": 14, "INT": 8, "WIS": 12, "CHA": 13},
            class_skill_choices=["Perception", "Survival"],
        )
        ally.current_hp = 0
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(16))
        game.skill_check = lambda actor, skill, dc, context: True
        game.help_downed_ally(player, ally)
        self.assertEqual(ally.current_hp, 1)

    def test_god_mode_prevents_party_damage(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        enemy = create_enemy("goblin_skirmisher")
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(161))
        game.state = GameState(player=player, current_scene="road_ambush")
        game.state.flags[game.DEV_GOD_MODE_FLAG] = True
        before = player.current_hp
        self.assertEqual(game.apply_damage(player, 9, damage_type="slashing"), 0)
        self.assertEqual(player.current_hp, before)
        self.assertEqual(game.apply_damage(enemy, 9, damage_type="slashing"), 9)

    def test_pass_every_dice_check_forces_player_skill_and_save_success(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(
            input_fn=lambda _: (_ for _ in ()).throw(AssertionError("developer auto-leveling should not prompt")),
            output_fn=lambda _: None,
            rng=random.Random(162),
        )
        game.state = GameState(player=player, current_scene="road_ambush")
        game.state.flags[game.DEV_PASS_CHECKS_FLAG] = True
        game.auto_fail_save = lambda actor, ability: True
        self.assertTrue(game.skill_check(player, "Athletics", 35, context="to bully an impossible gate open"))
        self.assertTrue(game.saving_throw(player, "DEX", 99, context="against a dev-test trap"))

    def test_level_up_party_instantly_levels_company_without_prompting(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companion = create_tolan_ironshield()
        game = TextDnDGame(
            input_fn=lambda _: (_ for _ in ()).throw(AssertionError("developer auto-leveling should not prompt")),
            output_fn=lambda _: None,
            rng=random.Random(163),
        )
        game.state = GameState(player=player, companions=[companion], current_scene="phandalin_hub")
        leveled = game.level_up_party_instantly()
        self.assertEqual(leveled, 2)
        self.assertEqual(game.state.xp, 300)
        self.assertEqual(player.level, 2)
        self.assertEqual(companion.level, 2)

    def test_jump_to_act2_developer_start_builds_level_four_test_company(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(164))
        game.state = GameState(player=player, current_scene="neverwinter_briefing", gold=25)
        game.confirm = lambda prompt: True
        self.assertTrue(game.jump_to_act2_developer_start())
        self.assertEqual(game.state.current_act, 2)
        self.assertEqual(game.state.current_scene, "act2_claims_council")
        self.assertEqual(game.state.completed_acts, [1])
        self.assertTrue(game.state.flags["act2_started"])
        self.assertTrue(game.state.flags["act2_scaffold_enabled"])
        self.assertTrue(game.state.flags["elira_helped"])
        self.assertTrue(game.state.flags["miners_exchange_dispute_resolved"])
        self.assertEqual(
            {companion.name for companion in game.state.companions},
            {"Bryn Underbough", "Elira Dawnmantle", "Tolan Ironshield"},
        )
        self.assertEqual(len(game.state.companions), 3)
        self.assertEqual(len(game.state.camp_companions), 0)
        self.assertTrue(all(member.level == 4 for member in game.state.party_members()))
        self.assertTrue(all(member.current_hp == member.max_hp for member in game.state.party_members()))

    def test_dev_prompt_jump_to_act2_restarts_current_scene_loop(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["dev", "5", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(165))
        game.state = GameState(player=player, current_scene="phandalin_hub", gold=25)

        with self.assertRaises(gameplay_base.ResumeLoadedGame):
            game.choose("Where do you go next?", ["Stay in Phandalin", "Ride out"])

        self.assertEqual(game.state.current_act, 2)
        self.assertEqual(game.state.current_scene, "act2_claims_council")
        self.assertEqual(
            {companion.name for companion in game.state.companions},
            {"Bryn Underbough", "Elira Dawnmantle", "Tolan Ironshield"},
        )
        self.assertTrue(all(member.level == 4 for member in game.state.party_members()))

    def test_spell_slots_start_with_bg3_style_class_tables(self) -> None:
        wizard = build_character(
            name="Nyra",
            race="Elf",
            class_name="Wizard",
            background="Sage",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10},
            class_skill_choices=["Arcana", "Investigation"],
        )
        warlock = build_character(
            name="Cairn",
            race="Tiefling",
            class_name="Warlock",
            background="Charlatan",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 13, "INT": 10, "WIS": 12, "CHA": 15},
            class_skill_choices=["Intimidation", "Investigation"],
        )
        paladin = build_character(
            name="Velkor",
            race="Half-Orc",
            class_name="Paladin",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 10, "CON": 13, "INT": 8, "WIS": 12, "CHA": 14},
            class_skill_choices=["Athletics", "Intimidation"],
        )
        self.assertEqual(spell_slot_counts(wizard, maximum=True), {1: 2})
        self.assertEqual(spell_slot_counts(warlock, maximum=True), {1: 1})
        self.assertEqual(spell_slot_counts(paladin, maximum=True), {})
        self.assertNotIn("spell_slots", wizard.resources)
        self.assertNotIn("spell_slots", warlock.resources)

    def test_scale_level_resources_grows_spell_slots_by_level(self) -> None:
        wizard = build_character(
            name="Nyra",
            race="Elf",
            class_name="Wizard",
            background="Sage",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10},
            class_skill_choices=["Arcana", "Investigation"],
        )
        paladin = build_character(
            name="Velkor",
            race="Half-Orc",
            class_name="Paladin",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 10, "CON": 13, "INT": 8, "WIS": 12, "CHA": 14},
            class_skill_choices=["Athletics", "Intimidation"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(1601))
        wizard.level = 3
        paladin.level = 5
        game.scale_level_resources(wizard)
        game.scale_level_resources(paladin)
        self.assertEqual(spell_slot_counts(wizard, maximum=True), {1: 4, 2: 2})
        self.assertEqual(spell_slot_counts(paladin, maximum=True), {1: 4, 2: 2})

    def test_warlock_short_rest_restores_pact_slots(self) -> None:
        warlock = build_character(
            name="Cairn",
            race="Tiefling",
            class_name="Warlock",
            background="Charlatan",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 13, "INT": 10, "WIS": 12, "CHA": 15},
            class_skill_choices=["Intimidation", "Investigation"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(1602))
        warlock.level = 3
        game.scale_level_resources(warlock)
        warlock.resources["spell_slots_2"] = 0
        game.state = GameState(player=warlock, current_scene="phandalin_hub", short_rests_remaining=2)
        game.short_rest()
        self.assertEqual(warlock.resources["spell_slots_2"], warlock.max_resources["spell_slots_2"])
        self.assertEqual(game.state.short_rests_remaining, 1)

    def test_long_rest_consumes_supply_points_and_resets_short_rests(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        player.current_hp = 3
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(17))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            inventory={"camp_stew_jar": 3, "bread_round": 4, "goat_cheese": 2},
            short_rests_remaining=0,
        )
        game.long_rest()
        self.assertEqual(game.state.player.current_hp, game.state.player.max_hp)
        self.assertEqual(game.state.short_rests_remaining, 2)
        self.assertLessEqual(game.current_supply_points(), 8)

    def test_paid_inn_long_rest_charges_party_without_consuming_supplies(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companion = create_kaelis_starling()
        player.current_hp = 2
        companion.current_hp = 3
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(172))
        game.state = GameState(
            player=player,
            companions=[companion],
            current_scene="phandalin_hub",
            gold=20,
            inventory={"camp_stew_jar": 3, "bread_round": 4, "goat_cheese": 2},
            short_rests_remaining=0,
        )
        supply_points = game.current_supply_points()
        self.assertTrue(game.paid_inn_long_rest("Stonehill Inn"))
        self.assertEqual(game.state.gold, 0)
        self.assertEqual(game.current_supply_points(), supply_points)
        self.assertEqual(player.current_hp, player.max_hp)
        self.assertEqual(companion.current_hp, companion.max_hp)
        self.assertEqual(game.state.short_rests_remaining, 2)
        rendered = self.plain_output(log)
        self.assertIn("will cost 20 gp total", rendered)
        self.assertIn("Will long rest: Velkor, Kaelis Starling.", rendered)
        self.assertIn("Spend 20 gp at Stonehill Inn and long rest this company?", rendered)

    def test_paid_inn_long_rest_can_be_declined_after_cost_confirmation(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companion = create_tolan_ironshield()
        companion.dead = True
        companion.current_hp = 0
        player.current_hp = 2
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "2", output_fn=log.append, rng=random.Random(1721))
        game.state = GameState(
            player=player,
            companions=[companion],
            current_scene="phandalin_hub",
            gold=20,
            short_rests_remaining=0,
        )
        self.assertFalse(game.paid_inn_long_rest("Stonehill Inn"))
        self.assertEqual(game.state.gold, 20)
        self.assertEqual(player.current_hp, 2)
        self.assertTrue(companion.dead)
        self.assertEqual(game.state.short_rests_remaining, 0)
        rendered = self.plain_output(log)
        self.assertIn("Will long rest: Velkor.", rendered)
        self.assertIn("Will not be restored by resting: Tolan Ironshield (dead).", rendered)
        self.assertIn("You keep your gold and do not rent beds.", rendered)

    def test_paid_inn_long_rest_requires_enough_gold(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        player.current_hp = 2
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(173))
        game.state = GameState(player=player, current_scene="phandalin_hub", gold=4, short_rests_remaining=0)
        self.assertFalse(game.paid_inn_long_rest("Stonehill Inn"))
        self.assertEqual(game.state.gold, 4)
        self.assertEqual(player.current_hp, 2)
        self.assertEqual(game.state.short_rests_remaining, 0)
        self.assertIn("costs 10 gp", self.plain_output(log))

    def test_short_rest_heals_half_maximum_hp_rounded_up(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        player.current_hp = 1
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(1701))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            short_rests_remaining=2,
        )
        game.short_rest()
        self.assertEqual(game.state.player.current_hp, min(player.max_hp, 1 + ((player.max_hp + 1) // 2)))
        self.assertEqual(game.state.short_rests_remaining, 1)

    def test_long_rest_restores_spell_slots_for_player_and_companion(self) -> None:
        player = build_character(
            name="Nyra",
            race="Elf",
            class_name="Wizard",
            background="Sage",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10},
            class_skill_choices=["Arcana", "Investigation"],
        )
        companion = build_character(
            name="Elira",
            race="Human",
            class_name="Cleric",
            background="Acolyte",
            base_ability_scores={"STR": 10, "DEX": 12, "CON": 13, "INT": 10, "WIS": 15, "CHA": 14},
            class_skill_choices=["Insight", "Medicine"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(1603))
        player.level = 3
        companion.level = 4
        game.scale_level_resources(player)
        game.scale_level_resources(companion)
        player.resources["spell_slots_1"] = 0
        player.resources["spell_slots_2"] = 1
        companion.resources["spell_slots_1"] = 1
        companion.resources["spell_slots_2"] = 0
        game.state = GameState(
            player=player,
            companions=[companion],
            current_scene="phandalin_hub",
            inventory={"camp_stew_jar": 3, "bread_round": 4, "goat_cheese": 2},
        )
        game.long_rest()
        self.assertEqual(spell_slot_counts(player), spell_slot_counts(player, maximum=True))
        self.assertEqual(spell_slot_counts(companion), spell_slot_counts(companion, maximum=True))

    def test_long_rest_does_not_revive_dead_companions(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companion = create_tolan_ironshield()
        companion.dead = True
        companion.current_hp = 0
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(171))
        game.state = GameState(
            player=player,
            companions=[companion],
            current_scene="phandalin_hub",
            inventory={"camp_stew_jar": 3, "bread_round": 4, "goat_cheese": 2},
        )
        game.long_rest()
        self.assertTrue(companion.dead)
        self.assertEqual(companion.current_hp, 0)

    def test_magic_missile_uses_highest_available_slot_when_lower_slots_are_empty(self) -> None:
        wizard = build_character(
            name="Nyra",
            race="Elf",
            class_name="Wizard",
            background="Sage",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10},
            class_skill_choices=["Arcana", "Investigation"],
        )
        target = create_enemy("goblin_skirmisher")
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(1604))
        wizard.level = 3
        game.scale_level_resources(wizard)
        wizard.resources["spell_slots_1"] = 0
        wizard.resources["spell_slots_2"] = 2
        expressions: list[str] = []
        game.roll_with_display_bonus = lambda expression, **kwargs: expressions.append(expression) or SimpleNamespace(total=10)
        game.cast_magic_missile(wizard, target)
        self.assertEqual(expressions, ["4d4+4"])
        self.assertEqual(wizard.resources["spell_slots_2"], 1)

    def test_camp_menu_shows_revivify_option_for_dead_companion(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companion = create_kaelis_starling()
        companion.dead = True
        companion.current_hp = 0
        log: list[str] = []
        answers = iter(["3", "4", "7"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(172))
        game.state = GameState(
            player=player,
            camp_companions=[companion],
            current_scene="phandalin_hub",
            inventory={"scroll_revivify": 1},
        )
        game.open_camp_menu()
        rendered = self.plain_output(log)
        self.assertIn("Rest and recovery", rendered)
        self.assertIn("Take a short rest", rendered)
        self.assertIn("Use Scroll of Revivify on a dead ally", rendered)

    def test_camp_menu_shows_compact_act2_digest(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["7"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(1721))
        game.state = GameState(
            player=player,
            companions=[create_irielle_ashwake()],
            camp_companions=[create_nim_ardentglass()],
            current_scene="phandalin_hub",
            current_act=2,
            flags={
                "act2_started": True,
                "act2_first_late_route": "broken_prospect",
                "south_adit_cleared": True,
                "act2_captive_outcome": "few_saved",
                "stonehollow_scholars_found": True,
                "stonehollow_notes_preserved": True,
                "south_adit_counter_cadence_learned": True,
                "black_lake_shrine_purified": True,
                "black_lake_barracks_raided": True,
                "act2_town_stability": 3,
                "act2_route_control": 4,
                "act2_whisper_pressure": 2,
            },
        )
        game.open_camp_menu()
        rendered = self.plain_output(log)
        self.assertIn("Act II Digest:", rendered)
        self.assertIn("Town 3/5 (Holding) | Route 4/5 (Dominant) | Whisper 2/5 (Present)", rendered)
        self.assertIn("Broken Prospect went first, and South Adit never recovered cleanly from that delay.", rendered)
        self.assertIn(
            "Company state: Nim Ardentglass is at camp turning Stonehollow's salvage into usable maps; Irielle Ashwake is with the active party carrying the adit's counter-cadence.",
            rendered,
        )
        self.assertIn("Rescue summary: Stonehollow scholars escaped with usable survey testimony; South Adit only yielded partial rescues.", rendered)

    def test_camp_revivify_restores_dead_companion(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companion = create_kaelis_starling()
        companion.dead = True
        companion.current_hp = 0
        log: list[str] = []
        answers = iter(["1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(173))
        game.state = GameState(
            player=player,
            camp_companions=[companion],
            current_scene="phandalin_hub",
            inventory={"scroll_revivify": 1},
        )
        self.assertTrue(game.use_scroll_of_revivify())
        rendered = self.plain_output(log)
        self.assertFalse(companion.dead)
        self.assertEqual(companion.current_hp, 1)
        self.assertNotIn("scroll_revivify", game.state.inventory)
        self.assertIn("returns to life at 1 HP", rendered)

    def test_scroll_of_revivify_exists_with_uncommon_pricing(self) -> None:
        item = ITEMS["scroll_revivify"]
        self.assertEqual(item.name, "Scroll of Revivify")
        self.assertEqual(item.rarity, "uncommon")
        self.assertEqual(item.value, 200)
        self.assertTrue(item.revive_dead)

    def test_two_handed_weapon_clears_offhand_slot(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(18))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            inventory={"longbow_common": 1, "shield_common": 1},
        )
        player.equipment_slots = {
            "head": None,
            "ring_1": None,
            "ring_2": None,
            "neck": None,
            "chest": None,
            "gloves": None,
            "boots": None,
            "main_hand": "longbow_common",
            "off_hand": "shield_common",
            "cape": None,
        }
        game.sync_equipment(player)
        self.assertIsNone(player.equipment_slots["off_hand"])
        self.assertEqual(player.weapon.hands_required, 2)

    def test_ensure_state_integrity_migrates_legacy_equipment_slots(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        player.equipment_slots = {
            "helmet": "iron_cap_common",
            "ring_1": None,
            "ring_2": None,
            "amulet": "soldiers_amulet_common",
            "chest": "chain_mail_common",
            "pants": "reinforced_breeches_common",
            "gloves": None,
            "boots": None,
            "main_hand": "longsword_common",
            "off_hand": None,
        }
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(181))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            inventory={
                "iron_cap_common": 1,
                "soldiers_amulet_common": 1,
                "reinforced_breeches_common": 1,
                "chain_mail_common": 1,
                "longsword_common": 1,
            },
        )
        game.ensure_state_integrity()
        self.assertEqual(player.equipment_slots["head"], "iron_cap_common")
        self.assertEqual(player.equipment_slots["neck"], "soldiers_amulet_common")
        self.assertEqual(player.equipment_slots["cape"], "reinforced_breeches_common")
        self.assertNotIn("helmet", player.equipment_slots)
        self.assertNotIn("amulet", player.equipment_slots)
        self.assertNotIn("pants", player.equipment_slots)

    def test_manage_equipment_can_assign_companion_offhand_weapon(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companion = create_tolan_ironshield()
        answers = iter(["2", "9", "2", "10", "2", "3"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(182))
        game.state = GameState(player=player, companions=[companion], current_scene="phandalin_hub", inventory={"dagger_common": 1})
        game.ensure_state_integrity()
        game.state.inventory["dagger_common"] = 1
        game.manage_equipment()
        self.assertEqual(companion.equipment_slots["off_hand"], "dagger_common")

    def test_character_sheets_can_show_companion_details(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companion = create_kaelis_starling()
        log: list[str] = []
        answers = iter(["2", "2"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(183))
        game.state = GameState(player=player, companions=[companion], current_scene="phandalin_hub")
        game.ensure_state_integrity()
        game.show_character_sheets()
        rendered = self.plain_output(log)
        self.assertIn("Character Sheet: Kaelis Starling", rendered)
        self.assertIn("Ability Scores:", rendered)
        self.assertIn("Ability Scores:\n- STR", rendered)
        self.assertIn("\n\nCombat:", rendered)
        self.assertIn("Combat:\n- Weapon", rendered)
        self.assertIn("\n\nSaving Throws:", rendered)
        self.assertIn("Saving Throws:\n- STR", rendered)
        self.assertIn("\n\nSkills:", rendered)
        self.assertIn("Skills:\n- Acrobatics", rendered)
        self.assertIn("Equipment:", rendered)

    def test_character_sheet_rich_layout_uses_a_compact_aligned_stat_grid(self) -> None:
        if not RICH_AVAILABLE:
            self.skipTest("Rich is not available")

        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companion = create_kaelis_starling()
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(184))
        game.state = GameState(player=player, companions=[companion], current_scene="phandalin_hub")

        renderable = game.build_character_sheet_rich_renderable(companion)
        lines = render_rich_lines(renderable, width=game.character_sheet_render_width())

        top_titles = next(line for line in lines if "Ability Scores" in line and "Saving Throws" in line)
        bottom_titles = next(line for line in lines if "Combat" in line and "Skills" in line)
        saving_throws_start = top_titles.index("Saving Throws")
        skills_start = bottom_titles.index("Skills")

        self.assertLess(saving_throws_start - top_titles.index("Ability Scores"), 52)
        self.assertLess(skills_start - bottom_titles.index("Combat"), 52)
        self.assertLess(abs(saving_throws_start - skills_start), 4)

    def test_selling_item_adds_gold_with_merchant(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(19))
        game.state = GameState(player=player, current_scene="phandalin_hub", gold=0, inventory={"bread_round": 1})
        player.equipment_slots = {slot: None for slot in ["head", "ring_1", "ring_2", "neck", "chest", "gloves", "boots", "main_hand", "off_hand", "cape"]}
        game.sell_items(merchant_id="linene_graywind", merchant_name="Linene Graywind")
        self.assertEqual(game.state.gold, 1)
        self.assertNotIn("bread_round", game.state.inventory)

    def test_cannot_sell_away_from_merchant(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(20))
        game.state = GameState(player=player, current_scene="phandalin_hub", gold=0, inventory={"bread_round": 1})
        player.equipment_slots = {slot: None for slot in ["head", "ring_1", "ring_2", "neck", "chest", "gloves", "boots", "main_hand", "off_hand", "cape"]}
        game.sell_items()
        self.assertEqual(game.state.gold, 0)
        self.assertEqual(game.state.inventory["bread_round"], 1)

    def test_sell_menu_allows_backing_out(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["2"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(21))
        game.state = GameState(player=player, current_scene="phandalin_hub", gold=0, inventory={"bread_round": 1})
        player.equipment_slots = {slot: None for slot in ["head", "ring_1", "ring_2", "neck", "chest", "gloves", "boots", "main_hand", "off_hand", "cape"]}
        game.sell_items(merchant_id="linene_graywind", merchant_name="Linene Graywind")
        self.assertEqual(game.state.gold, 0)
        self.assertEqual(game.state.inventory["bread_round"], 1)

    def test_general_inventory_menu_hides_sell_option(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "6", output_fn=log.append, rng=random.Random(22))
        game.state = GameState(player=player, current_scene="phandalin_hub", inventory={"bread_round": 1})
        game.manage_inventory()
        rendered = "\n".join(log)
        self.assertNotIn("Sell items", rendered)
        self.assertIn("View inventory by category", rendered)

    def test_merchant_inventory_menu_shows_trade_tags(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "9", output_fn=log.append, rng=random.Random(221))
        game.state = GameState(player=player, current_scene="phandalin_hub", inventory={"bread_round": 1})
        game.manage_inventory(merchant_id="barthen_provisions", merchant_name="Barthen")
        rendered = self.plain_output(log)
        self.assertIn("[TRADE] Browse Barthen's wares", rendered)
        self.assertIn("[TRADE] Buy items from Barthen", rendered)
        self.assertIn("[TRADE] Sell items to Barthen", rendered)
        self.assertIn("Trade terms with Barthen", rendered)

    def test_inventory_filter_view_can_focus_on_consumables(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(2211))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            inventory={"potion_healing": 2, "bread_round": 1, "longsword_common": 1},
        )
        game.show_inventory(filter_key="consumables")
        rendered = self.plain_output(log)
        self.assertIn("View: Consumables", rendered)
        self.assertIn("Potion of Healing", rendered)
        self.assertNotIn("Bread Round", rendered)
        self.assertNotIn("Longsword", rendered)

    def test_inventory_storefront_view_exposes_table_headers(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(2212))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            inventory={"potion_healing": 2, "longsword_common": 1},
        )
        game.show_inventory()
        rendered = self.plain_output(log)
        self.assertIn("On hand: Potion of Healing x2, Roadworn Longsword x1", rendered)
        if RICH_AVAILABLE:
            self.assertIn("Shared Inventory", rendered)
            self.assertIn("Qty", rendered)
            self.assertIn("Value", rendered)
            self.assertIn("Rules", rendered)

    def test_merchant_catalog_renders_trade_desk_columns(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(2213))
        game.state = GameState(player=player, current_scene="phandalin_hub", inventory={})
        stock = game.get_merchant_stock("barthen_provisions")
        stock.clear()
        stock["bread_round"] = 3
        game.show_merchant_stock("barthen_provisions", "Barthen")
        rendered = self.plain_output(log)
        self.assertIn("Trade terms with Barthen", rendered)
        self.assertIn("Bread Round", rendered)
        if RICH_AVAILABLE:
            self.assertIn("Trade Desk", rendered)
            self.assertIn("Stock", rendered)
            self.assertIn("Buy", rendered)

    def test_merchant_pricing_uses_persuasion_and_attitude_formula(self) -> None:
        player = build_character(
            name="Mira",
            race="Human",
            class_name="Bard",
            background="Charlatan",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 13, "INT": 10, "WIS": 12, "CHA": 16},
            class_skill_choices=["Insight", "Performance", "Persuasion"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(222))
        game.state = GameState(player=player, current_scene="phandalin_hub", inventory={})
        game.state.flags["merchant_attitudes"] = {"barthen_provisions": 50}
        self.assertEqual(game.trade_persuasion(), 5)
        self.assertAlmostEqual(game.buy_price_multiplier("barthen_provisions"), 1.75)
        self.assertAlmostEqual(game.sell_price_multiplier("barthen_provisions"), 1 / 1.75)

    def test_can_buy_multiple_items_from_merchant(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["1", "3"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(23))
        game.state = GameState(player=player, current_scene="phandalin_hub", gold=15, inventory={})
        stock = game.get_merchant_stock("barthen_provisions")
        stock.clear()
        stock["bread_round"] = 5
        game.buy_items("barthen_provisions", "Barthen")
        self.assertEqual(game.state.inventory["bread_round"], 3)
        self.assertEqual(game.state.gold, 0)
        self.assertEqual(stock["bread_round"], 2)

    def test_early_item_prices_are_more_affordable(self) -> None:
        self.assertEqual(ITEMS["potion_healing"].value, 15)
        self.assertLess(ITEMS["longbow_common"].value, 50)
        self.assertLess(ITEMS["chain_shirt_uncommon"].value, 100)

    def test_can_sell_multiple_items_to_merchant(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["1", "2"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(24))
        game.state = GameState(player=player, current_scene="phandalin_hub", gold=0, inventory={"bread_round": 3})
        player.equipment_slots = {slot: None for slot in ["head", "ring_1", "ring_2", "neck", "chest", "gloves", "boots", "main_hand", "off_hand", "cape"]}
        stock = game.get_merchant_stock("barthen_provisions")
        stock.clear()
        game.sell_items(merchant_id="barthen_provisions", merchant_name="Barthen")
        self.assertEqual(game.state.gold, 2)
        self.assertEqual(game.state.inventory["bread_round"], 1)
        self.assertEqual(stock["bread_round"], 2)

    def test_failed_skill_check_grants_no_xp(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(25))
        game.state = GameState(player=player, current_scene="neverwinter_briefing", xp=0, gold=0)
        game.skill_check = lambda actor, skill, dc, context: False
        game.handle_neverwinter_prep()
        self.assertEqual(game.state.xp, 0)

    def test_returning_from_ashfall_watch_guarantees_level_two_before_emberhall(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["1", "3", "10", "3"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(52))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            clues=["one", "two"],
            xp=180,
            flags={"ashfall_watch_cleared": True, "phandalin_arrived": True, "tresendar_cleared": True},
        )
        game.scene_phandalin_hub()
        self.assertEqual(game.state.player.level, 2)
        self.assertEqual(game.state.current_scene, "emberhall_cellars")

    def test_neverwinter_prep_skill_check_has_situation_specific_failure_text(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(251))
        game.state = GameState(player=player, current_scene="neverwinter_briefing", xp=0, gold=0)
        game.skill_check = lambda actor, skill, dc, context: False
        game.handle_neverwinter_prep()
        rendered = self.plain_output(log)
        self.assertIn("The ledgers are too incomplete and hastily corrected", rendered)

    def test_shrine_skill_choice_cannot_be_repeated(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["1", "4"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(26))
        game.state = GameState(player=player, current_scene="phandalin_hub", xp=0, gold=0)
        game.skill_check = lambda actor, skill, dc, context: True
        game.visit_shrine()
        rendered = self.plain_output(log)
        self.assertEqual(rendered.count('1. [MEDICINE] "Let me examine the poisoned miner."'), 1)

    def test_steward_question_cannot_be_repeated(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["1", "3"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(29))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.visit_steward()
        rendered = self.plain_output(log)
        self.assertEqual(rendered.count('1. "Where is the Ashen Brand hurting you the most?"'), 1)

    def test_steward_accepts_blackwake_report_once(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["1", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(9204))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            flags={
                "steward_seen": True,
                "steward_pressure_asked": True,
                "steward_ruins_asked": True,
                "steward_vow_made": True,
                "blackwake_completed": True,
                "blackwake_resolution": "evidence",
                "blackwake_sereth_fate": "escaped",
            },
        )
        game.visit_steward()
        rendered = self.plain_output(log)
        self.assertIn("*Share what happened at Blackwake Crossing.", rendered)
        self.assertIn("False seals this close to Neverwinter", rendered)
        self.assertIn("Sereth Vane is still breathing", rendered)
        self.assertTrue(game.state.flags["steward_blackwake_asked"])
        self.assertEqual(game.state.gold, 8)

    def test_inn_question_cannot_be_repeated(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["1", "9"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(30))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.visit_stonehill_inn()
        rendered = self.plain_output(log)
        self.assertEqual(rendered.count('1. "Mind if I buy you a drink and ask a few questions?"'), 1)

    def test_inn_blackwake_rumor_reflects_resolution_once(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["1", "7"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(9205))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            flags={
                "inn_seen": True,
                "inn_buy_drink_asked": True,
                "inn_road_rumors_asked": True,
                "inn_recruit_bryn_attempted": True,
                "inn_recruit_bryn_second_attempted": True,
                "blackwake_completed": True,
                "blackwake_resolution": "sabotage",
                "blackwake_sereth_fate": "escaped",
            },
        )
        game.visit_stonehill_inn()
        rendered = self.plain_output(log)
        self.assertIn('"What are people saying about Blackwake Crossing?"', rendered)
        self.assertIn("someone taught the Brand what a supply loss feels like", rendered)
        self.assertIn("Sereth Vane", rendered)
        self.assertTrue(game.state.flags["inn_blackwake_rumor_asked"])

    def test_stonehill_marked_keg_quest_can_be_resolved_and_turned_in(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(411))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "Choose what you say to Mara Stonehill.":
                if game.quest_is_completed("marked_keg_investigation"):
                    return self.option_index_containing(options, "Leave Mara to the floor")
                if game.quest_is_ready("marked_keg_investigation"):
                    return self.option_index_containing(options, "Tell Mara who marked the keg")
                if not game.has_quest("marked_keg_investigation"):
                    return self.option_index_containing(options, "watching the kegs instead of the door")
                return self.option_index_containing(options, "Read the room around Mara's marked keg.")
            if prompt == "How do you handle Mara's marked keg?":
                return self.option_index_containing(options, "Examine the keg chalk")
            raise AssertionError(prompt)

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.stonehill_talk_mara()

        self.assertEqual(game.state.quests["marked_keg_investigation"].status, "completed")
        self.assertTrue(game.state.flags["marked_keg_resolved"])
        self.assertTrue(game.state.flags["quest_reward_stonehill_common_room_welcome"])
        self.assertEqual(game.state.inventory["innkeeper_credit_token"], 1)
        self.assertEqual(game.state.gold, 24)
        self.assertEqual(game.state.xp, 70)
        rendered = self.plain_output(log)
        self.assertIn("fresh chalk no cellar hand will claim", rendered)
        self.assertIn("Additional quest reward: Innkeeper Credit Token x1.", rendered)

    def test_stonehill_marked_keg_blessing_path_skips_skill_check(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Charlatan",
            base_ability_scores={"STR": 10, "DEX": 15, "CON": 13, "INT": 10, "WIS": 12, "CHA": 14},
            class_skill_choices=["Deception", "Insight", "Stealth"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(412))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.apply_liars_blessing()

        def fail_skill_check(actor, skill, dc, context):
            raise AssertionError("Liar's Blessing path should not require a skill check")

        game.skill_check = fail_skill_check
        game.scenario_choice = lambda prompt, options, **kwargs: self.option_index_containing(options, "LIAR'S BLESSING")  # type: ignore[method-assign]
        game.stonehill_investigate_marked_keg()

        self.assertTrue(game.state.flags["marked_keg_resolved"])

    def test_stonehill_songs_for_the_missing_can_be_completed(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(413))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]

        def first_sella_choice(prompt: str, options: list[str], **kwargs) -> int:
            if "Sella Quill" in prompt:
                if not game.has_quest("songs_for_the_missing"):
                    return self.option_index_containing(options, "Can a song do anything for the missing?")
                return self.option_index_containing(options, "Leave Sella Quill")
            raise AssertionError(prompt)

        game.scenario_choice = first_sella_choice  # type: ignore[method-assign]
        game.stonehill_talk_sella()

        def jerek_choice(prompt: str, options: list[str], **kwargs) -> int:
            if "Jerek Harl" in prompt:
                if not game.state.flags.get("songs_for_missing_jerek_detail"):
                    return self.option_index_containing(options, "Tell me the missing man's name")
                return self.option_index_containing(options, "Leave Jerek")
            raise AssertionError(prompt)

        game.scenario_choice = jerek_choice  # type: ignore[method-assign]
        game.stonehill_talk_jerek()

        def tam_choice(prompt: str, options: list[str], **kwargs) -> int:
            if "Old Tam Veller" in prompt:
                if not game.state.flags.get("songs_for_missing_tam_detail"):
                    return self.option_index_containing(options, "Stay with the part")
                return self.option_index_containing(options, "Leave Old Tam")
            raise AssertionError(prompt)

        game.scenario_choice = tam_choice  # type: ignore[method-assign]
        game.stonehill_talk_old_tam()

        def nera_song_choice(prompt: str, options: list[str], **kwargs) -> int:
            if "Nera Doss" in prompt:
                if not game.state.flags.get("stonehill_nera_treated"):
                    return self.option_index_containing(options, "Let me look at that split lip")
                return self.option_index_containing(options, "Leave Nera Doss")
            raise AssertionError(prompt)

        game.scenario_choice = nera_song_choice  # type: ignore[method-assign]
        game.stonehill_talk_nera()

        def final_sella_choice(prompt: str, options: list[str], **kwargs) -> int:
            if "Sella Quill" in prompt:
                if game.quest_is_ready("songs_for_the_missing"):
                    return self.option_index_containing(options, "Bring Sella the three true details")
                return self.option_index_containing(options, "Leave Sella Quill")
            raise AssertionError(prompt)

        game.scenario_choice = final_sella_choice  # type: ignore[method-assign]
        game.stonehill_talk_sella()

        self.assertEqual(game.state.quests["songs_for_the_missing"].status, "completed")
        self.assertEqual(game.state.inventory["sella_ballad_token"], 1)
        self.assertTrue(game.state.flags["quest_reward_sella_names_carried"])
        self.assertTrue(game.state.flags["songs_for_missing_jerek_detail"])
        self.assertTrue(game.state.flags["songs_for_missing_tam_detail"])
        self.assertTrue(game.state.flags["songs_for_missing_nera_detail"])
        rendered = self.plain_output(log)
        self.assertIn("three true details", rendered)
        self.assertIn("Additional quest reward: Sella's Ballad Token x1.", rendered)

    def test_stonehill_quiet_table_failure_can_roll_into_barfight_and_turn_in(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(414))
        game.state = GameState(player=player, current_scene="phandalin_hub")

        def selective_skill_check(actor, skill, dc, context):
            if skill == "Stealth":
                return False
            return True

        game.skill_check = selective_skill_check  # type: ignore[method-assign]

        def nera_first_choice(prompt: str, options: list[str], **kwargs) -> int:
            if "Nera Doss" in prompt:
                if not game.has_quest("quiet_table_sharp_knives"):
                    return self.option_index_containing(options, "Who wanted your message changed?")
                if game.state.flags.get("stonehill_barfight_ready"):
                    return self.option_index_containing(options, "Leave Nera Doss")
                return self.option_index_containing(options, "Shadow the quiet table")
            if prompt == "How do you work the quiet table?":
                return self.option_index_containing(options, "Move around the beams")
            raise AssertionError(prompt)

        game.scenario_choice = nera_first_choice  # type: ignore[method-assign]
        game.stonehill_talk_nera()

        self.assertTrue(game.state.flags["stonehill_barfight_ready"])

        game.scenario_choice = lambda prompt, options, **kwargs: self.option_index_containing(options, "Name the real instigator")  # type: ignore[method-assign]
        game.stonehill_resolve_barfight()

        self.assertTrue(game.state.flags["quiet_table_knives_resolved"])
        self.assertFalse(game.state.flags["stonehill_barfight_ready"])

        def nera_turnin_choice(prompt: str, options: list[str], **kwargs) -> int:
            if "Nera Doss" in prompt:
                if game.quest_is_ready("quiet_table_sharp_knives"):
                    return self.option_index_containing(options, "Tell Nera what the quiet table was really doing")
                return self.option_index_containing(options, "Leave Nera Doss")
            raise AssertionError(prompt)

        game.scenario_choice = nera_turnin_choice  # type: ignore[method-assign]
        game.stonehill_talk_nera()

        self.assertEqual(game.state.quests["quiet_table_sharp_knives"].status, "completed")
        self.assertEqual(game.state.inventory["blackseal_taster_pin"], 1)
        self.assertTrue(game.state.flags["quest_reward_stonehill_quiet_room_access"])
        rendered = self.plain_output(log)
        self.assertIn("folded payment note", rendered)
        self.assertIn("Additional quest reward: Blackseal Taster Pin x1.", rendered)

    def test_jerek_missing_brother_quest_can_be_found_at_ashfall_and_turned_in(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(415))
        game.state = GameState(player=player, current_scene="phandalin_hub", flags={"act1_town_fear": 2})

        def jerek_accept_choice(prompt: str, options: list[str], **kwargs) -> int:
            if "Jerek Harl" in prompt:
                if not game.has_quest("find_dain_harl"):
                    return self.option_index_containing(options, "what truth do you want carried back")
                return self.option_index_containing(options, "Leave Jerek")
            raise AssertionError(prompt)

        game.scenario_choice = jerek_accept_choice  # type: ignore[method-assign]
        game.stonehill_talk_jerek()

        self.assertTrue(game.has_quest("find_dain_harl"))
        self.assertEqual(game.state.quests["find_dain_harl"].status, "active")

        dungeon = ACT1_HYBRID_MAP.dungeons["ashfall_watch_fort"]
        room = dungeon.rooms["prisoner_yard"]
        game.state.current_scene = "ashfall_watch"
        game.scenario_choice = lambda prompt, options, **kwargs: self.option_index_containing(options, "Cut the locks")  # type: ignore[method-assign]
        game._ashfall_prisoner_yard(dungeon, room)

        self.assertTrue(game.state.flags["ashfall_blue_scarf_truth_found"])
        self.assertTrue(game.state.flags["dain_harl_truth_found"])
        self.assertEqual(game.state.quests["find_dain_harl"].status, "ready_to_turn_in")

        game.state.current_scene = "phandalin_hub"

        def jerek_turnin_choice(prompt: str, options: list[str], **kwargs) -> int:
            if "Jerek Harl" in prompt:
                if game.quest_is_ready("find_dain_harl"):
                    return self.option_index_containing(options, "Tell Jerek what you found of Dain Harl")
                return self.option_index_containing(options, "Leave Jerek")
            raise AssertionError(prompt)

        game.scenario_choice = jerek_turnin_choice  # type: ignore[method-assign]
        game.stonehill_talk_jerek()

        self.assertEqual(game.state.quests["find_dain_harl"].status, "completed")
        self.assertEqual(game.state.inventory["harl_road_knot"], 1)
        self.assertTrue(game.state.flags["quest_reward_jerek_road_knot"])
        self.assertEqual(game.state.flags["act1_town_fear"], 1)
        rendered = self.plain_output(log)
        self.assertIn("blue scarf", rendered)
        self.assertIn("Additional quest reward: Harl Road-Knot x1.", rendered)

    def test_stonehill_quiet_room_scene_unlocks_packet_intel(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Rogue",
            background="Charlatan",
            base_ability_scores={"STR": 10, "DEX": 15, "CON": 12, "INT": 14, "WIS": 13, "CHA": 12},
            class_skill_choices=["Investigation", "Insight", "Stealth"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(416))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            flags={
                "inn_seen": True,
                "inn_buy_drink_asked": True,
                "inn_road_rumors_asked": True,
                "inn_recruit_bryn_attempted": True,
                "inn_recruit_bryn_second_attempted": True,
                "quest_reward_stonehill_quiet_room_access": True,
            },
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]

        def quiet_room_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "The common room quiets for a moment as you enter.":
                if game.state.flags.get("stonehill_quiet_room_scene_done"):
                    return self.option_index_containing(options, "Leave the common room")
                return self.option_index_containing(options, "upstairs quiet room")
            if prompt == "How do you work the quiet-room packet?":
                return self.option_index_containing(options, "payment note beside the courier strip")
            raise AssertionError(prompt)

        game.scenario_choice = quiet_room_choice  # type: ignore[method-assign]
        game.visit_stonehill_inn()

        self.assertTrue(game.state.flags["stonehill_quiet_room_scene_done"])
        self.assertTrue(game.state.flags["stonehill_quiet_room_intel_decoded"])
        self.assertEqual(game.state.xp, 15)
        rendered = self.plain_output(log)
        self.assertIn("what your reward really buys", rendered)
        self.assertIn("quiet-room packet", rendered)

    def test_ashfall_quiet_room_intel_option_weakens_rukhar(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(417))
        game.state = GameState(
            player=player,
            current_scene="ashfall_watch",
            flags={
                "stonehill_quiet_room_intel_decoded": True,
                "ashfall_lower_barracks_cleared": True,
                "ashfall_signal_basin_silenced": True,
            },
        )
        dungeon = ACT1_HYBRID_MAP.dungeons["ashfall_watch_fort"]
        room = dungeon.rooms["rukhar_command"]
        captured: list[Encounter] = []
        game.scenario_choice = lambda prompt, options, **kwargs: self.option_index_containing(options, "QUIET ROOM INTEL")  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: captured.append(encounter) or "victory"  # type: ignore[method-assign]
        game.return_to_phandalin = lambda text: None  # type: ignore[method-assign]

        game._ashfall_rukhar_command(dungeon, room)

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].enemies[0].current_hp, 23)

    def test_emberhall_quiet_room_intel_option_reads_ledgers_without_check(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(418))
        game.state = GameState(player=player, current_scene="emberhall_cellars", flags={"stonehill_quiet_room_intel_decoded": True})
        dungeon = ACT1_HYBRID_MAP.dungeons["emberhall_depths"]
        room = dungeon.rooms["ledger_chain"]

        def fail_skill_check(actor, skill, dc, context):
            raise AssertionError("Quiet-room ledger option should not require a skill check")

        game.skill_check = fail_skill_check
        game.scenario_choice = lambda prompt, options, **kwargs: self.option_index_containing(options, "QUIET ROOM INTEL")  # type: ignore[method-assign]

        game._emberhall_ledger_chain(dungeon, room)

        self.assertTrue(game.state.flags["emberhall_ledger_read"])

    def test_neverwinter_contract_house_quest_can_unlock_private_room(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Rogue",
            background="Charlatan",
            base_ability_scores={"STR": 10, "DEX": 15, "CON": 12, "INT": 14, "WIS": 13, "CHA": 14},
            class_skill_choices=["Insight", "Investigation", "Sleight of Hand"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(419))
        game.state = GameState(player=player, current_scene="neverwinter_briefing")
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]

        def contract_house_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "The contract house room keeps three conversations going at once.":
                if not game.has_quest("false_manifest_circuit"):
                    return self.option_index_containing(options, "Sabra Kestrel")
                if not game.state.flags.get("false_manifest_oren_detail"):
                    return self.option_index_containing(options, "Oren Vale")
                if not game.state.flags.get("false_manifest_vessa_detail"):
                    return self.option_index_containing(options, "Vessa Marr")
                if not game.state.flags.get("false_manifest_garren_detail"):
                    return self.option_index_containing(options, "Garren Flint")
                if game.quest_is_ready("false_manifest_circuit") and not game.quest_is_completed("false_manifest_circuit"):
                    return self.option_index_containing(options, "Sabra Kestrel")
                if game.state.flags.get("quest_reward_neverwinter_private_room_access") and not game.state.flags.get("neverwinter_private_room_scene_done"):
                    return self.option_index_containing(options, "upstairs private room")
                return self.option_index_containing(options, "Leave the contract house")
            if "Sabra Kestrel" in prompt:
                if not game.has_quest("false_manifest_circuit"):
                    return self.option_index_containing(options, "Which ledger line")
                if game.quest_is_ready("false_manifest_circuit") and not game.quest_is_completed("false_manifest_circuit"):
                    return self.option_index_containing(options, "Bring Sabra")
                return self.option_index_containing(options, "Leave Sabra")
            if "Oren Vale" in prompt:
                if not game.state.flags.get("false_manifest_oren_detail"):
                    return self.option_index_containing(options, "written by someone expecting never to be checked")
                return self.option_index_containing(options, "Leave Oren")
            if "Vessa Marr" in prompt:
                if not game.state.flags.get("false_manifest_vessa_detail"):
                    return self.option_index_containing(options, "seal-color")
                return self.option_index_containing(options, "Leave Vessa")
            if "Garren Flint" in prompt:
                if not game.state.flags.get("false_manifest_garren_detail"):
                    return self.option_index_containing(options, "real roadwarden would never write")
                return self.option_index_containing(options, "Leave Garren")
            if prompt == "How do you read the upstairs contract room?":
                return self.option_index_containing(options, "corrected manifests over the room register")
            raise AssertionError(prompt)

        game.scenario_choice = contract_house_choice  # type: ignore[method-assign]
        game.visit_neverwinter_contract_house()

        self.assertEqual(game.state.quests["false_manifest_circuit"].status, "completed")
        self.assertEqual(game.state.inventory["kestrel_ledger_clasp"], 1)
        self.assertTrue(game.state.flags["quest_reward_neverwinter_private_room_access"])
        self.assertTrue(game.state.flags["neverwinter_private_room_scene_done"])
        self.assertTrue(game.state.flags["neverwinter_private_room_intel"])
        rendered = self.plain_output(log)
        self.assertIn("Additional quest reward: Kestrel Ledger Clasp x1.", rendered)
        self.assertIn("Upstairs Contract Room", rendered)

    def test_act2_claims_council_mentions_harl_knot_and_quiet_room_intel(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["1", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(420))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="act2_claims_council",
            flags={
                "act2_started": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
                "quest_reward_jerek_road_knot": True,
                "stonehill_quiet_room_intel_decoded": True,
                "act2_neverwinter_witness_pressure_active": True,
            },
        )
        game.skill_check = lambda actor, skill, dc, context: False  # type: ignore[method-assign]

        game.scene_act2_claims_council()

        rendered = self.plain_output(log)
        self.assertIn("blue road-knot", rendered)
        self.assertIn("courier packet", rendered)
        self.assertIn("Neverwinter sent a witness packet", rendered)

    def test_stonehollow_harl_road_knot_option_marks_supports_without_skill_check(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(421))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="stonehollow_dig",
            flags={
                "act2_started": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
                "quest_reward_jerek_road_knot": True,
            },
        )
        dungeon = ACT2_ENEMY_DRIVEN_MAP.dungeons["stonehollow_dig_site"]
        room = dungeon.rooms["survey_mouth"]

        def fail_skill_check(actor, skill, dc, context):
            raise AssertionError("Harl Road-Knot route option should not require a skill check")

        game.skill_check = fail_skill_check
        game.scenario_choice = lambda prompt, options, **kwargs: self.option_index_containing(options, "HARL ROAD-KNOT")  # type: ignore[method-assign]

        game._stonehollow_survey_mouth(dungeon, room)

        self.assertTrue(game.state.flags["stonehollow_supports_stabilized"])
        self.assertEqual(game.state.xp, 10)

    def test_black_lake_quiet_room_intel_option_takes_orders_without_skill_check(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(422))
        game.state = GameState(
            player=player,
            current_act=2,
            current_scene="black_lake_causeway",
            flags={
                "act2_started": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
                "stonehill_quiet_room_intel_decoded": True,
            },
        )
        dungeon = ACT2_ENEMY_DRIVEN_MAP.dungeons["black_lake_crossing"]
        room = dungeon.rooms["choir_barracks"]
        captured: list[Encounter] = []

        def fail_skill_check(actor, skill, dc, context):
            raise AssertionError("Quiet-room Act II barracks option should not require a skill check")

        game.skill_check = fail_skill_check
        game.scenario_choice = lambda prompt, options, **kwargs: self.option_index_containing(options, "QUIET ROOM INTEL")  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: captured.append(encounter) or "victory"  # type: ignore[method-assign]

        game._black_lake_choir_barracks(dungeon, room)

        self.assertTrue(game.state.flags["black_lake_barracks_orders_taken"])
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].enemies[1].conditions.get("surprised"), 1)

    def test_sella_song_changes_after_dain_truth_returns(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Bard",
            background="Charlatan",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 13, "INT": 10, "WIS": 12, "CHA": 16},
            class_skill_choices=["Insight", "Performance", "Persuasion"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(423))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            flags={"quest_reward_jerek_road_knot": True},
            quests={
                "songs_for_the_missing": QuestLogEntry(quest_id="songs_for_the_missing", status="completed", notes=[]),
                "find_dain_harl": QuestLogEntry(quest_id="find_dain_harl", status="completed", notes=[]),
            },
        )

        def sella_memorial_choice(prompt: str, options: list[str], **kwargs) -> int:
            if "Sella Quill" in prompt:
                if not game.state.flags.get("stonehill_sella_dain_memorial_done"):
                    return self.option_index_containing(options, "Dain Harl's true ending")
                return self.option_index_containing(options, "Leave Sella")
            raise AssertionError(prompt)

        game.scenario_choice = sella_memorial_choice  # type: ignore[method-assign]
        game.stonehill_talk_sella()

        self.assertTrue(game.state.flags["stonehill_sella_dain_memorial_done"])
        rendered = self.plain_output(log)
        self.assertIn("Dain Harl", rendered)
        self.assertIn("second chorus changes", rendered)

    def test_briefing_question_cannot_be_repeated(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["1", "6", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(27))
        game.state = GameState(
            player=player,
            current_scene="neverwinter_briefing",
            flags={
                "briefing_seen": True,
                "early_companion_recruited": "Kaelis Starling",
                "neverwinter_tymora_shrine_seen": True,
                "neverwinter_high_road_milehouse_seen": True,
                "neverwinter_signal_cairn_seen": True,
            },
        )
        game.scene_neverwinter_briefing()
        rendered = self.plain_output(log)
        self.assertEqual(rendered.count('1. "How is Neverwinter holding together these days?"'), 1)

    def test_show_party_displays_xp_to_next_level(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(28))
        game.state = GameState(player=player, current_scene="phandalin_hub", xp=120, gold=9)
        game.show_party()
        rendered = self.plain_output(log)
        self.assertIn("Next level in 180 XP", rendered)
        self.assertIn("HP [", rendered)
        self.assertIn("conditions [none]", rendered)
        self.assertNotIn("Features:", rendered)

    def test_roll_initiative_handles_ties_without_character_comparison(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        companion = build_character(
            name="Kaelis",
            race="Half-Elf",
            class_name="Ranger",
            background="Criminal",
            base_ability_scores={"STR": 10, "DEX": 15, "CON": 13, "INT": 11, "WIS": 14, "CHA": 12},
            class_skill_choices=["Perception", "Stealth", "Survival"],
        )
        enemy = create_enemy("goblin_skirmisher")
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(23))
        game.roll_with_advantage = lambda actor, advantage_state: SimpleNamespace(kept=10)
        order = game.roll_initiative([player, companion], [enemy])
        self.assertEqual(len(order), 3)
        self.assertEqual(order[0].name, "Kaelis")
        self.assertIn(enemy, order)

    def test_offer_early_companion_lists_companion_classes(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(24))
        game.state = GameState(player=player, current_scene="neverwinter_briefing")
        game.offer_early_companion()
        rendered = self.plain_output(log)
        self.assertIn("Kaelis Starling, a ranger scout", rendered)
        self.assertIn("Rhogar Valeguard, a paladin caravan-guard", rendered)
        self.assertNotIn("Handle the road alone for now.", rendered)

    def test_neverwinter_tymora_shrine_can_recruit_elira_before_phandalin(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["1", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(90090))
        game.state = GameState(
            player=player,
            companions=[create_kaelis_starling()],
            current_scene="neverwinter_briefing",
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]

        game.handle_neverwinter_tymora_shrine()

        self.assertTrue(game.has_companion("Elira Dawnmantle"))
        self.assertTrue(game.state.flags["elira_neverwinter_recruited"])
        self.assertTrue(game.state.flags["elira_helped"])
        self.assertEqual(len(game.state.party_members()), 3)

    def test_wayside_luck_shrine_can_recruit_elira_as_first_companion(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["1", "1"])
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(90110))
        game.state = GameState(player=player, current_scene="wayside_luck_shrine")
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]

        game.scene_wayside_luck_shrine()

        elira = game.find_companion("Elira Dawnmantle")
        self.assertTrue(game.has_companion("Elira Dawnmantle"))
        self.assertIsNotNone(elira)
        self.assertEqual(elira.disposition, 1)
        self.assertTrue(game.state.flags["elira_first_contact"])
        self.assertEqual(game.state.flags["elira_first_read"], "triage_competence")
        self.assertTrue(game.state.flags["wayside_luck_bell_seen"])
        self.assertEqual(game.state.flags["wayside_aid_route"], "wounded")
        self.assertEqual(game.state.flags["elira_initial_trust_reason"], "warm_trust")
        self.assertTrue(game.state.flags["elira_first_companion"])
        self.assertTrue(game.state.flags["elira_pre_neverwinter_recruited"])
        self.assertTrue(game.state.flags["elira_neverwinter_recruited"])
        self.assertTrue(game.state.flags["wayside_luck_bell_promised"])
        self.assertNotIn("early_companion_recruited", game.state.flags)
        self.assertEqual(game.state.current_scene, "greywake_triage_yard")
        rendered = self.plain_output(log)
        self.assertIn("cracked luck bell", rendered)
        self.assertIn("You have seen triage before", rendered)
        self.assertIn("Elira ties the cracked luck bell once", rendered)

    def test_wayside_elira_first_read_reflects_background_or_class(self) -> None:
        cases = [
            ("Acolyte", "Cleric", ["Medicine", "Religion"], "faith_action", "faith can move your hands"),
            ("Soldier", "Fighter", ["Athletics", "Survival"], "triage_competence", "You have seen triage before"),
            ("Criminal", "Rogue", ["Stealth", "Persuasion"], "unwatched_mercy", "No one important is watching"),
            ("Sage", "Wizard", ["Arcana", "Investigation"], "knowledge_vs_saving", "do not mistake knowing it for saving him"),
        ]
        for background, class_name, skills, expected_read, expected_text in cases:
            with self.subTest(background=background, class_name=class_name):
                player = build_character(
                    name="Velkor",
                    race="Human",
                    class_name=class_name,
                    background=background,
                    base_ability_scores={"STR": 12, "DEX": 13, "CON": 14, "INT": 15, "WIS": 11, "CHA": 10},
                    class_skill_choices=skills,
                )
                answers = iter(["4", "2"])
                log: list[str] = []
                game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(901101))
                game.state = GameState(player=player, current_scene="wayside_luck_shrine")

                def fail_skill_check(actor, skill: str, dc: int, context: str) -> bool:
                    raise AssertionError("Skipping aid and declining recruitment should not roll checks")

                game.skill_check = fail_skill_check  # type: ignore[method-assign]

                game.scene_wayside_luck_shrine()

                self.assertEqual(game.state.flags["elira_first_read"], expected_read)
                self.assertEqual(game.state.flags["wayside_aid_route"], "none")
                self.assertEqual(game.state.flags["elira_initial_trust_reason"], "reserved_kindness")
                self.assertIn(expected_text, self.plain_output(log))

    def test_greywake_triage_yard_offers_second_elira_recruitment_chance(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["2", "1"])
        checks: list[tuple[str, int, str]] = []
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(90111))
        game.state = GameState(
            player=player,
            current_scene="greywake_triage_yard",
            flags={"elira_first_contact": True, "elira_wayside_recruit_failed": True},
        )

        def capture_check(actor, skill: str, dc: int, context: str) -> bool:
            checks.append((skill, dc, context))
            return True

        game.skill_check = capture_check  # type: ignore[method-assign]

        game.scene_greywake_triage_yard()

        self.assertTrue(game.has_companion("Elira Dawnmantle"))
        self.assertTrue(game.state.flags["greywake_outcome_sorting_seen"])
        self.assertTrue(game.state.flags["greywake_wounded_stabilized"])
        self.assertTrue(game.state.flags["greywake_outcome_tags_matched_wounds"])
        self.assertTrue(game.state.flags["greywake_attack_imminent"])
        self.assertTrue(game.state.flags["system_profile_seeded"])
        self.assertEqual(game.state.flags["greywake_mira_evidence_kind"], "matched_triage_tags")
        self.assertTrue(game.state.flags["elira_greywake_recruited"])
        self.assertEqual(game.state.current_scene, "greywake_road_breakout")
        self.assertEqual(
            checks,
            [
                ("Medicine", 9, "to stabilize the Greywake wounded line"),
                ("Persuasion", 6, "to convince Elira to join before Greywake breaks"),
            ],
        )
        rendered = self.plain_output(log)
        self.assertIn("prewritten triage tags", rendered)
        self.assertIn("This is not a ledger mistake", rendered)
        self.assertIn("first arrow cuts the quarantine line", rendered)

    def test_greywake_road_breakout_preserves_manifest_and_reaches_neverwinter(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "2", output_fn=lambda _: None, rng=random.Random(90112))
        game.state = GameState(
            player=player,
            companions=[create_elira_dawnmantle()],
            current_scene="greywake_road_breakout",
            flags={"greywake_yard_steadied": True},
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        game.scene_greywake_road_breakout()

        self.assertTrue(game.state.flags["greywake_breakout_resolved"])
        self.assertTrue(game.state.flags["greywake_manifest_preserved"])
        self.assertTrue(game.state.flags["system_profile_seeded"])
        self.assertTrue(game.state.flags["varyn_route_pattern_seen"])
        self.assertEqual(game.state.flags["greywake_mira_evidence_kind"], "marked_manifest")
        self.assertEqual(game.state.current_scene, "neverwinter_briefing")
        self.assertEqual([encounter.title for encounter in encounters], ["Greywake Road Breakout"])

    def test_neverwinter_briefing_reacts_to_greywake_outcome_manifest(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["6"])
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(90114))
        game.state = GameState(
            player=player,
            current_scene="neverwinter_briefing",
            flags={
                "greywake_breakout_resolved": True,
                "greywake_manifest_preserved": True,
                "greywake_wounded_line_guarded": True,
                "elira_greywake_recruited": True,
                "greywake_mira_evidence_kind": "marked_manifest",
            },
            companions=[create_elira_dawnmantle()],
        )
        game.scene_identity_options = lambda scene_key: []
        game.handle_neverwinter_departure_fork = lambda: setattr(game.state, "current_scene", "road_ambush")

        game.scene_neverwinter_briefing()

        rendered = self.plain_output(log)
        self.assertTrue(game.state.flags["greywake_mira_reacted"])
        self.assertIn("You found Dawnmantle before I could send anyone for her", rendered)
        self.assertIn("This is not a forged report. This is a schedule.", rendered)
        self.assertIn("People will talk because they lived long enough to be angry.", rendered)
        self.assertTrue(any("pre-sorting road casualties" in clue for clue in game.state.clues))
        self.assertTrue(any("survivors can testify" in clue for clue in game.state.clues))
        self.assertTrue(any("coordinating losses" in entry for entry in game.state.journal))

    def test_neverwinter_briefing_reacts_to_burned_greywake_manifest(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["6"])
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(90115))
        game.state = GameState(
            player=player,
            current_scene="neverwinter_briefing",
            flags={
                "greywake_manifest_destroyed": True,
                "greywake_mira_evidence_kind": "burned_manifest_corner",
            },
        )
        game.scene_identity_options = lambda scene_key: []
        game.handle_neverwinter_departure_fork = lambda: setattr(game.state, "current_scene", "road_ambush")

        game.scene_neverwinter_briefing()

        rendered = self.plain_output(log)
        self.assertTrue(game.state.flags["greywake_mira_reacted"])
        self.assertIn("Then we work from witnesses. Less clean, but sometimes harder to kill.", rendered)
        self.assertTrue(any("witness testimony" in clue for clue in game.state.clues))

    def test_neverwinter_briefing_greywake_question_uses_preserved_manifest_details(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(90116))
        game.state = GameState(
            player=player,
            current_scene="neverwinter_briefing",
            flags={
                "briefing_seen": True,
                "greywake_outcome_sorting_seen": True,
                "greywake_manifest_preserved": True,
                "greywake_wounded_line_guarded": True,
                "greywake_yard_steadied": True,
            },
        )
        game.scene_identity_options = lambda scene_key: []
        game.handle_neverwinter_departure_fork = lambda: setattr(game.state, "current_scene", "road_ambush")

        def choose_mira_option(prompt: str, options: list[str], **kwargs) -> int:
            if any("What do you make of Greywake" in option for option in options):
                return self.option_index_containing(options, "What do you make of Greywake")
            return self.option_index_containing(options, "Take the writ")

        game.scenario_choice = choose_mira_option  # type: ignore[method-assign]

        game.scene_neverwinter_briefing()

        rendered = self.plain_output(log)
        self.assertTrue(game.state.flags["mira_q_greywake_initial"])
        self.assertIn("orders wearing ink", rendered)
        self.assertIn("With the manifest intact", rendered)
        self.assertIn("preserved memory under pressure", rendered)
        self.assertIn("public witnesses", rendered)

    def test_neverwinter_briefing_elira_question_reflects_prior_trust(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Cleric",
            background="Acolyte",
            base_ability_scores={"STR": 10, "DEX": 12, "CON": 13, "INT": 11, "WIS": 15, "CHA": 14},
            class_skill_choices=["Medicine", "Persuasion"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(90117))
        game.state = GameState(
            player=player,
            current_scene="neverwinter_briefing",
            flags={
                "briefing_seen": True,
                "elira_first_contact": True,
                "elira_initial_trust_reason": "spiritual_kinship",
                "elira_phandalin_fallback_pending": True,
            },
        )
        game.scene_identity_options = lambda scene_key: []
        game.handle_neverwinter_departure_fork = lambda: setattr(game.state, "current_scene", "road_ambush")

        def choose_mira_option(prompt: str, options: list[str], **kwargs) -> int:
            if any("You know Elira Dawnmantle" in option for option in options):
                return self.option_index_containing(options, "You know Elira Dawnmantle")
            return self.option_index_containing(options, "Take the writ")

        game.scenario_choice = choose_mira_option  # type: ignore[method-assign]

        game.scene_neverwinter_briefing()

        rendered = self.plain_output(log)
        self.assertTrue(game.state.flags["mira_q_elira_initial"])
        self.assertIn("find her at the shrine", rendered)
        self.assertIn("Faith that keeps people alive is useful", rendered)
        self.assertIn("With a life, yes", rendered)

    def test_neverwinter_briefing_elira_question_lets_present_elira_answer(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(901171))
        game.state = GameState(
            player=player,
            current_scene="neverwinter_briefing",
            flags={
                "briefing_seen": True,
                "elira_first_contact": True,
                "elira_greywake_recruited": True,
            },
            companions=[create_elira_dawnmantle()],
        )
        game.scene_identity_options = lambda scene_key: []
        game.handle_neverwinter_departure_fork = lambda: setattr(game.state, "current_scene", "road_ambush")

        def choose_mira_option(prompt: str, options: list[str], **kwargs) -> int:
            if any("You know Elira Dawnmantle" in option for option in options):
                return self.option_index_containing(options, "You know Elira Dawnmantle")
            return self.option_index_containing(options, "Take the writ")

        game.scenario_choice = choose_mira_option  # type: ignore[method-assign]

        game.scene_neverwinter_briefing()

        rendered = self.plain_output(log)
        self.assertTrue(game.state.flags["mira_q_elira_initial"])
        self.assertIn("Harmless is what people call you", rendered)
        self.assertIn("The wounded are people first", rendered)
        self.assertIn("Trust me with breath, blood, and bad odds", rendered)
        self.assertIn("With a life, yes", rendered)
        self.assertNotIn("find her at the shrine", rendered)

    def test_neverwinter_return_after_phandalin_uses_return_debrief(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(90118))
        game.state = GameState(
            player=player,
            current_scene="neverwinter_briefing",
            flags={
                "briefing_seen": True,
                "phandalin_arrived": True,
                "steward_seen": True,
                "steward_vow_made": True,
                "blackwake_completed": True,
                "blackwake_resolution": "evidence",
            },
        )

        def choose_mira_option(prompt: str, options: list[str], **kwargs) -> int:
            if any("Phandalin is worse" in option for option in options):
                return self.option_index_containing(options, "Phandalin is worse")
            return self.option_index_containing(options, "Return to Phandalin")

        game.scenario_choice = choose_mira_option  # type: ignore[method-assign]

        game.scene_neverwinter_briefing()

        rendered = self.plain_output(log)
        self.assertTrue(game.state.flags["mira_return_intro_phandalin_return"])
        self.assertTrue(game.state.flags["mira_q_phandalin_return"])
        self.assertIn("town pressure is not collateral", rendered)
        self.assertIn("Tessa Harrow usually sounds tired", rendered)
        self.assertIn("You made her a vow", rendered)
        self.assertIn("The Blackwake ledgers will make the merchants angrier", rendered)
        self.assertEqual(game.state.current_scene, "phandalin_hub")

    def test_neverwinter_return_after_act1_reports_varyn_displacement(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(90119))
        game.state = GameState(
            player=player,
            current_scene="neverwinter_briefing",
            flags={
                "briefing_seen": True,
                "phandalin_arrived": True,
                "varyn_body_defeated_act1": True,
                "varyn_route_displaced": True,
                "act1_victory_tier": "fractured_victory",
                "emberhall_impossible_exit_seen": True,
            },
        )

        def choose_mira_option(prompt: str, options: list[str], **kwargs) -> int:
            if any("Varyn is beaten" in option for option in options):
                return self.option_index_containing(options, "Varyn is beaten")
            return self.option_index_containing(options, "Return to Phandalin")

        game.scenario_choice = choose_mira_option  # type: ignore[method-assign]

        game.scene_neverwinter_briefing()

        rendered = self.plain_output(log)
        self.assertTrue(game.state.flags["mira_return_intro_post_act1_return"])
        self.assertTrue(game.state.flags["mira_q_act1_after_report"])
        self.assertIn("Beaten, yes. Finished, I am less sure.", rendered)
        self.assertIn("Routes that fold wrong", rendered)
        self.assertIn("Phandalin will spend months learning what the word cost", rendered)
        self.assertIn("the exit that should not have worked", rendered)

    def test_phandalin_shrine_recruits_elira_after_failed_early_attempts(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "4", output_fn=log.append, rng=random.Random(90113))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            flags={
                "elira_first_contact": True,
                "elira_wayside_recruit_failed": True,
                "elira_greywake_recruit_failed": True,
                "elira_phandalin_fallback_pending": True,
                "wayside_luck_bell_seen": True,
            },
        )

        def fail_skill_check(actor, skill: str, dc: int, context: str) -> bool:
            raise AssertionError("Fallback Elira recruitment should not require another skill check")

        game.skill_check = fail_skill_check  # type: ignore[method-assign]

        game.visit_shrine()

        self.assertTrue(game.has_companion("Elira Dawnmantle"))
        self.assertTrue(game.state.flags["elira_phandalin_recruited"])
        self.assertNotIn("elira_phandalin_fallback_pending", game.state.flags)
        rendered = self.plain_output(log).replace("\n", " ")
        self.assertIn("green road-ribbon from the cracked luck bell", rendered)

    def test_neverwinter_tymora_shrine_elira_checks_are_dc_8(self) -> None:
        check_cases = [
            ("1", "2", "Medicine", "to slow the ash-bitter poison"),
            ("2", "2", "Religion", "to steady the shrine and caravan"),
            ("3", "2", "Investigation", "to connect poison, harness marks, and forged authority"),
            ("4", "1", "Persuasion", "to convince Elira the field needs her now"),
        ]
        for shrine_choice, recruit_choice, expected_skill, expected_context in check_cases:
            with self.subTest(expected_skill=expected_skill):
                player = build_character(
                    name="Velkor",
                    race="Human",
                    class_name="Fighter",
                    background="Soldier",
                    base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
                    class_skill_choices=["Athletics", "Survival"],
                )
                answers = iter([shrine_choice, recruit_choice])
                checks: list[tuple[str, int, str]] = []
                game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(900901))
                game.state = GameState(player=player, current_scene="neverwinter_briefing")

                def capture_check(actor, skill: str, dc: int, context: str) -> bool:
                    checks.append((skill, dc, context))
                    return False

                game.skill_check = capture_check  # type: ignore[method-assign]

                game.handle_neverwinter_tymora_shrine()

                self.assertEqual(checks, [(expected_skill, 8, expected_context)])

    def test_phandalin_shrine_elira_checks_are_dc_8(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["1", "1", "2", "2"])
        checks: list[tuple[str, int, str]] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(900902))
        game.state = GameState(player=player, current_scene="phandalin_hub")

        def capture_check(actor, skill: str, dc: int, context: str) -> bool:
            checks.append((skill, dc, context))
            return False

        game.skill_check = capture_check  # type: ignore[method-assign]

        game.visit_shrine()

        self.assertEqual(
            checks,
            [
                ("Medicine", 8, "to stabilize the miner"),
                ("Religion", 8, "to guide a steady prayer"),
                ("Persuasion", 8, "to ask Elira into danger"),
            ],
        )

    def test_neverwinter_high_road_milehouse_sets_route_effect_for_three_member_party(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "2", output_fn=lambda _: None, rng=random.Random(90091))
        game.state = GameState(
            player=player,
            companions=[create_kaelis_starling(), create_elira_dawnmantle()],
            current_scene="neverwinter_briefing",
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        game.handle_neverwinter_high_road_milehouse()

        self.assertTrue(game.state.flags["neverwinter_woodline_path"])
        self.assertTrue(game.state.flags["road_ambush_scouted"])
        self.assertEqual([encounter.title for encounter in encounters], ["High Road Milehouse Intercept"])
        self.assertEqual(len(encounters[0].enemies), 2)

    def test_neverwinter_signal_cairn_sets_second_wave_edge(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        encounters: list[Encounter] = []
        game = TextDnDGame(input_fn=lambda _: "2", output_fn=lambda _: None, rng=random.Random(90093))
        game.state = GameState(
            player=player,
            companions=[create_kaelis_starling(), create_elira_dawnmantle()],
            current_scene="neverwinter_briefing",
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        game.handle_neverwinter_signal_cairn()

        self.assertTrue(game.state.flags["road_reinforcement_signal_cut"])
        self.assertTrue(game.state.flags["road_second_wave_trail_read"])
        self.assertEqual([encounter.title for encounter in encounters], ["Neverwinter Wood Signal Cairn"])
        self.assertEqual(len(encounters[0].enemies), 2)

    def test_phandalin_shrine_defers_when_elira_joined_in_neverwinter(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(90092))
        game.state = GameState(
            player=player,
            companions=[create_elira_dawnmantle()],
            current_scene="phandalin_hub",
            flags={"elira_neverwinter_recruited": True, "wayside_luck_bell_promised": True},
        )

        game.visit_shrine()

        rendered = self.plain_output(log).replace("\n", " ")
        self.assertIn("Elira's field kit is not waiting", rendered)
        self.assertIn("promise Elira tied to the cracked luck bell", rendered)
        self.assertNotIn("Choose what you say to Elira.", rendered)

    def test_help_command_lists_global_commands(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["help", "2"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(40))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.choose("Choose one.", ["First", "Second"])
        rendered = self.plain_output(log)
        self.assertIn("Global Commands", rendered)
        self.assertIn("load: Load another save slot immediately and continue from there.", rendered)
        self.assertIn("quit: Return to the main menu, or close the program if you are already there.", rendered)
        self.assertIn("camp: Open camp when you are not in combat.", rendered)
        self.assertIn("inventory / backpack / bag", rendered)
        self.assertIn("dev: Open developer tools", rendered)
        self.assertIn("settings: Open the settings menu", rendered)

    def test_dev_command_opens_developer_tools_menu_from_prompt(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["dev", "2"])
        opened: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(4011))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.open_developer_tools_menu = lambda: opened.append("dev")
        choice = game.choose("Choose one.", ["First", "Second"])
        self.assertEqual(choice, 2)
        self.assertEqual(opened, ["dev"])

    def test_choose_hides_compact_hud_for_active_game_prompts_by_default(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "2", output_fn=log.append, rng=random.Random(4001))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            gold=9,
            inventory={"bread_round": 1},
            quests={"secure_miners_road": QuestLogEntry(quest_id="secure_miners_road")},
        )
        choice = game.choose("Choose one.", ["First", "Second"])
        self.assertEqual(choice, 2)
        rendered = self.plain_output(log)
        self.assertNotIn("[Act I] Phandalin | Objective: Stop the Watchtower Raids", rendered)
        self.assertIn("Choose one.", rendered)

    def test_map_command_opens_map_menu_and_can_show_travel_ledger(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["map", "1", "4", "2"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(40011))
        game.state = GameState(player=player, current_scene="blackwake_crossing", gold=9)
        game.say("Cold floodwater chews at the ford stones while wrecked carts pin draft horses against the current.")
        choice = game.choose("How do you approach Miller's Ford?", ["First", "Second"])
        self.assertEqual(choice, 2)
        rendered = self.plain_output(log)
        menu_index = rendered.find("Map menu")
        ledger_index = rendered.rfind("[Act I] Blackwake Crossing")
        prompt_index = rendered.rfind("How do you approach Miller's Ford?")
        self.assertNotEqual(menu_index, -1)
        self.assertNotEqual(ledger_index, -1)
        self.assertLess(menu_index, ledger_index)
        self.assertLess(ledger_index, prompt_index)

    def test_map_family_commands_open_map_menu_from_prompt(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        for command in ("map", "maps", "map menu"):
            answers = iter([command, "2"])
            opened: list[str] = []
            game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(40012))
            game.state = GameState(player=player, current_scene="old_owl_well", flags={"miners_exchange_lead": True})
            game.ensure_state_integrity()
            game.open_map_menu = lambda: opened.append("map-menu")  # type: ignore[method-assign]
            choice = game.choose("Choose one.", ["First", "Second"])
            self.assertEqual(choice, 2)
            self.assertEqual(opened, ["map-menu"])

    def test_target_selection_suppresses_compact_hud(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        enemy = create_enemy("goblin_skirmisher")
        log: list[str] = []
        answers = iter(["1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(4002))
        game.state = GameState(player=player, current_scene="road_ambush")
        target = game.choose_target([enemy], prompt="Choose a target.", allow_back=True)
        self.assertIs(target, enemy)
        rendered = self.plain_output(log)
        self.assertNotIn("[Act I]", rendered)
        self.assertIn("Choose a target.", rendered)

    def test_choose_target_uses_keyboard_menu_in_combat(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        enemy = create_enemy("goblin_skirmisher")
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(40021))
        game.state = GameState(player=player, current_scene="road_ambush")
        game._in_combat = True
        captured: dict[str, object] = {}
        game.keyboard_choice_menu_supported = lambda: True

        def fake_run(prompt, options, *, title=None):
            captured["prompt"] = prompt
            captured["options"] = list(options)
            captured["title"] = title
            return 1

        game.run_keyboard_choice_menu = fake_run
        target = game.choose_target([enemy], prompt="Choose a target.", allow_back=True)
        self.assertIs(target, enemy)
        self.assertEqual(captured["prompt"], "Choose a target.")
        self.assertEqual(captured["options"], [game.describe_combatant(enemy), "Back"])
        self.assertIsNone(captured["title"])

    def test_grouped_combat_menu_renders_action_sections(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(4005))
        game.state = GameState(player=player, current_scene="road_ambush", inventory={"potion_healing": 1})
        game._in_combat = True
        enemy = create_enemy("goblin_skirmisher")
        options = game.get_player_combat_options(
            player,
            SimpleNamespace(allow_parley=True, allow_flee=True),
            turn_state=TurnState(),
            heroes=[player],
        )
        selected = game.choose_grouped_combat_option("Your turn.", options, actor=player, heroes=[player], enemies=[enemy])
        self.assertEqual(selected, f"Attack with {player.weapon.name}")
        rendered = self.plain_output(log)
        self.assertIn("Action:", rendered)
        self.assertIn("Bonus Action:", rendered)
        self.assertIn("Tactical:", rendered)
        if RICH_AVAILABLE:
            self.assertIn("Party", rendered)
            self.assertIn("Enemies", rendered)

    def test_choose_grouped_combat_option_uses_single_row_panel_layout(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(40051))
        game.state = GameState(player=player, current_scene="road_ambush", inventory={"potion_healing": 1})
        game._in_combat = True
        enemy = create_enemy("goblin_skirmisher")
        options = game.get_player_combat_options(
            player,
            SimpleNamespace(allow_parley=True, allow_flee=True),
            turn_state=TurnState(),
            heroes=[player],
        )
        captured: dict[str, object] = {}

        def fake_panel_row(panels, *, ratios=None, width=None, padding=(0, 1)):
            captured["panel_count"] = len(panels)
            captured["ratios"] = ratios
            captured["width"] = width
            captured["padding"] = padding
            return False

        game.emit_rich_panel_row = fake_panel_row
        selected = game.choose_grouped_combat_option("Your turn.", options, actor=player, heroes=[player], enemies=[enemy])
        self.assertEqual(selected, f"Attack with {player.weapon.name}")
        self.assertEqual(captured["panel_count"], 3)
        self.assertEqual(captured["ratios"], [3, 4, 3])
        self.assertEqual(captured["width"], game.safe_rich_render_width())

    def test_choose_grouped_combat_option_uses_keyboard_combat_menu_when_supported(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(40052))
        game.state = GameState(player=player, current_scene="road_ambush", inventory={"potion_healing": 1})
        game._in_combat = True
        enemy = create_enemy("goblin_skirmisher")
        options = game.get_player_combat_options(
            player,
            SimpleNamespace(allow_parley=True, allow_flee=True),
            turn_state=TurnState(),
            heroes=[player],
        )
        captured: dict[str, object] = {}
        expected = options[-1]

        def fake_run(prompt, menu_options, sections, *, actor, heroes, enemies):
            captured["prompt"] = prompt
            captured["options"] = list(menu_options)
            captured["sections"] = [(section, list(grouped)) for section, grouped in sections]
            captured["actor"] = actor
            captured["heroes"] = list(heroes)
            captured["enemies"] = list(enemies)
            return expected

        game.run_grouped_combat_keyboard_menu = fake_run
        selected = game.choose_grouped_combat_option("Your turn.", options, actor=player, heroes=[player], enemies=[enemy])
        self.assertEqual(selected, expected)
        self.assertEqual(captured["prompt"], "Your turn.")
        self.assertEqual(captured["options"], options)
        self.assertEqual(captured["actor"], player)
        self.assertEqual(captured["heroes"], [player])
        self.assertEqual(captured["enemies"], [enemy])
        self.assertTrue(any(section == "Action" for section, _ in captured["sections"]))

    def test_equipment_comparison_preview_shows_deltas(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["3"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(4006))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            inventory={"traveler_hood_common": 1, "iron_cap_common": 1},
        )
        game.ensure_state_integrity()
        player.equipment_slots["head"] = "iron_cap_common"
        game.sync_equipment(player)
        game.manage_equipment_slot(player, "head")
        rendered = self.plain_output(log)
        self.assertIn("Current Head: Roadworn Iron Cap", rendered)
        self.assertIn("Roadworn Traveler's Hood", rendered)
        self.assertIn("AC -1", rendered)
        self.assertIn("Perception +1", rendered)

    def test_map_command_opens_map_menu_each_time_it_is_requested(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        answers = iter(["map", "map", "1"])
        opened: list[str] = []
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(4003))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.open_map_menu = lambda: opened.append("map-menu")  # type: ignore[method-assign]
        game.choose("Choose one.", ["First", "Second"])
        self.assertEqual(opened, ["map-menu", "map-menu"])

    def test_compact_hud_is_hidden_during_combat(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["map", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(4004))
        game.state = GameState(player=player, current_scene="road_ambush")
        game._in_combat = True
        game.banner("Ambush")
        game.choose("Choose one.", ["First"])
        rendered = self.plain_output(log)
        self.assertNotIn("[Act I]", rendered)
        self.assertIn("=== Ambush ===", rendered)
        self.assertIn("Maps are unavailable during combat.", rendered)
        self.assertIn("Choose one.", rendered)

    def test_settings_command_opens_settings_menu_from_prompt(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["settings", "7", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(401))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        choice = game.choose("Choose one.", ["First", "Second"])
        self.assertEqual(choice, 1)
        rendered = self.plain_output(log)
        self.assertIn("Settings", rendered)
        self.assertIn("Toggle sound effects", rendered)
        self.assertIn("Dice animation style", rendered)
        self.assertIn("Toggle typed dialogue and narration", rendered)
        self.assertIn("Toggle pacing pauses", rendered)
        self.assertIn("Toggle staggered option reveals", rendered)

    def test_settings_menu_can_disable_presentation_toggles(self) -> None:
        answers = iter(["3", "1", "4", "5", "6", "7"])
        game = TextDnDGame(
            input_fn=lambda _: next(answers),
            output_fn=print,
            rng=random.Random(402),
            animate_dice=True,
            pace_output=True,
            type_dialogue=True,
        )
        game._staggered_reveals_preference = True
        game.apply_staggered_reveal_preference()
        game.refresh_presentation_bundle_preference()
        game.persist_settings = lambda: None
        with patch("sys.stdout", io.StringIO()):
            game.open_settings_menu()
        self.assertFalse(game.animate_dice)
        self.assertFalse(game.pace_output)
        self.assertFalse(game.type_dialogue)
        self.assertFalse(game.staggered_reveals_enabled)
        self.assertFalse(hasattr(game.rng, "dice_roll_animator"))
        self.assertFalse(game.current_settings_payload()["animations_and_delays_enabled"])

    def test_settings_persist_across_game_restarts(self) -> None:
        save_dir = Path.cwd() / "tests_output" / "settings_persistence"
        save_dir.mkdir(parents=True, exist_ok=True)
        settings_path = save_dir / "settings.json"
        settings_path.unlink(missing_ok=True)

        first_game = TextDnDGame(
            input_fn=lambda _: "1",
            output_fn=print,
            save_dir=save_dir,
            rng=random.Random(404),
        )
        first_game._music_supported = True
        first_game._music_assets_ready = True
        first_game._sfx_supported = True
        first_game._sfx_assets_ready = True
        first_game.refresh_scene_music = lambda default_to_menu=False: None

        with patch("sys.stdout", io.StringIO()):
            first_game.set_sound_effects_enabled(False)
            first_game.set_music_enabled(True)
            first_game.set_animations_and_delays_enabled(False)

        stored_settings = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertEqual(
            stored_settings,
            {
                "sound_effects_enabled": False,
                "music_enabled": True,
                "dice_animations_enabled": False,
                "dice_animation_mode": "off",
                "typed_dialogue_enabled": False,
                "pacing_pauses_enabled": False,
                "staggered_reveals_enabled": False,
                "animations_and_delays_enabled": False,
            },
        )

        second_game = TextDnDGame(
            input_fn=lambda _: "1",
            output_fn=lambda _: None,
            save_dir=save_dir,
            rng=random.Random(405),
        )
        self.assertFalse(second_game.animate_dice)
        self.assertFalse(second_game.pace_output)
        self.assertFalse(second_game.type_dialogue)
        self.assertFalse(second_game.staggered_reveals_enabled)
        self.assertFalse(second_game.current_settings_payload()["sound_effects_enabled"])
        self.assertTrue(second_game.current_settings_payload()["music_enabled"])
        self.assertFalse(second_game.current_settings_payload()["dice_animations_enabled"])
        self.assertEqual(second_game.current_settings_payload()["dice_animation_mode"], "off")
        self.assertFalse(second_game.current_settings_payload()["typed_dialogue_enabled"])
        self.assertFalse(second_game.current_settings_payload()["pacing_pauses_enabled"])
        self.assertFalse(second_game.current_settings_payload()["staggered_reveals_enabled"])
        self.assertFalse(second_game.current_settings_payload()["animations_and_delays_enabled"])

        settings_path.unlink(missing_ok=True)
        save_dir.rmdir()

    def test_missing_settings_default_to_music_and_presentation_on_sfx_off(self) -> None:
        save_dir = Path.cwd() / "tests_output" / "settings_defaults"
        save_dir.mkdir(parents=True, exist_ok=True)
        settings_path = save_dir / "settings.json"
        settings_path.unlink(missing_ok=True)

        game = TextDnDGame(
            input_fn=lambda _: "1",
            output_fn=print,
            save_dir=save_dir,
            rng=random.Random(407),
        )

        self.assertFalse(game.current_settings_payload()["sound_effects_enabled"])
        self.assertTrue(game.current_settings_payload()["music_enabled"])
        self.assertTrue(game.current_settings_payload()["dice_animations_enabled"])
        self.assertEqual(game.current_settings_payload()["dice_animation_mode"], "full")
        self.assertTrue(game.current_settings_payload()["typed_dialogue_enabled"])
        self.assertTrue(game.current_settings_payload()["pacing_pauses_enabled"])
        self.assertTrue(game.current_settings_payload()["staggered_reveals_enabled"])
        self.assertTrue(game.current_settings_payload()["animations_and_delays_enabled"])
        self.assertEqual(gameplay_base.GameBase.default_settings_payload(), game.current_settings_payload())

        settings_path.unlink(missing_ok=True)
        save_dir.rmdir()

    def test_load_menu_ignores_settings_file(self) -> None:
        save_dir = Path.cwd() / "tests_output" / "settings_menu_filter"
        save_dir.mkdir(parents=True, exist_ok=True)
        settings_path = save_dir / "settings.json"
        settings_path.write_text(
            json.dumps(
                {
                    "sound_effects_enabled": False,
                    "music_enabled": False,
                    "animations_and_delays_enabled": False,
                }
            ),
            encoding="utf-8",
        )

        player = build_character(
            name="Iri",
            race="Human",
            class_name="Wizard",
            background="Sage",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10},
            class_skill_choices=["Arcana", "Investigation"],
        )
        state = GameState(player=player, current_scene="phandalin_hub")
        writer = TextDnDGame(
            input_fn=lambda _: "1",
            output_fn=lambda _: None,
            save_dir=save_dir,
            rng=random.Random(406),
        )
        writer.state = state
        save_path = writer.save_game(slot_name="campaign")

        log: list[str] = []
        reader = TextDnDGame(
            input_fn=lambda _: "1",
            output_fn=log.append,
            save_dir=save_dir,
            rng=random.Random(407),
        )
        loaded = reader.load_from_menu()
        rendered = self.plain_output(log)
        self.assertTrue(loaded)
        self.assertIn("campaign", rendered)
        self.assertNotIn("settings", rendered)

        Path(save_path).unlink(missing_ok=True)
        settings_path.unlink(missing_ok=True)
        save_dir.rmdir()

    def test_main_menu_includes_settings_option(self) -> None:
        log: list[str] = []
        answers = iter(["4", "7", "5"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(403))
        game.run()
        rendered = self.plain_output(log)
        self.assertIn("4.", rendered)
        self.assertIn("Settings", rendered)

    def test_load_command_can_replace_active_game_mid_prompt(self) -> None:
        save_dir = Path.cwd() / "tests_output" / "midgame_load"
        save_dir.mkdir(parents=True, exist_ok=True)
        player = build_character(
            name="Iri",
            race="Human",
            class_name="Wizard",
            background="Sage",
            base_ability_scores={"STR": 8, "DEX": 14, "CON": 12, "INT": 15, "WIS": 13, "CHA": 10},
            class_skill_choices=["Arcana", "Investigation"],
        )
        writer = TextDnDGame(
            input_fn=lambda _: "1",
            output_fn=lambda _: None,
            save_dir=save_dir,
            rng=random.Random(501),
        )
        writer.state = GameState(player=player, current_scene="phandalin_hub", gold=27)
        save_path = writer.save_game(slot_name="campaign")

        other_player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        reader = TextDnDGame(
            input_fn=lambda _: "1",
            output_fn=lambda _: None,
            save_dir=save_dir,
            rng=random.Random(502),
        )
        reader.state = GameState(player=other_player, current_scene="road_ambush", gold=3)

        with self.assertRaises(gameplay_base.ResumeLoadedGame):
            reader.handle_meta_command("load")

        self.assertEqual(reader.state.player.name, "Iri")
        self.assertEqual(reader.state.current_scene, "phandalin_hub")
        self.assertEqual(reader.state.gold, 27)

        Path(save_path).unlink(missing_ok=True)
        (save_dir / "settings.json").unlink(missing_ok=True)
        save_dir.rmdir()

    def test_quit_command_returns_to_title_from_active_game(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(503))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.confirm = lambda prompt: True

        with self.assertRaises(gameplay_base.ReturnToTitleMenu):
            game.handle_meta_command("quit")

        self.assertIsNone(game.state)

    def test_main_menu_quit_command_confirms_before_exit(self) -> None:
        log: list[str] = []
        answers = iter(["quit", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(504))
        game.run()
        rendered = self.plain_output(log)
        self.assertIn("Quit the program and close the main menu?", rendered)
        self.assertIn("Safe travels, adventurer.", rendered)

    def test_dialogue_uses_colored_names_and_extra_spacing(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(205))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.player_speaker("We should move.")
        game.speaker("Lantern Keeper", "Then move quickly.")
        rendered = "\n".join(log)
        self.assertIn(colorize("Velkor", "blue"), rendered)
        self.assertIn(colorize("Lantern Keeper", "green"), rendered)
        self.assertEqual(log[0], "")
        self.assertEqual(log[2], "")
        self.assertEqual(log[3], "")
        self.assertEqual(log[5], "")

    def test_camp_command_opens_camp_out_of_combat(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        answers = iter(["camp", "7", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(41))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.choose("Choose one.", ["First", "Second"])
        rendered = self.plain_output(log)
        self.assertIn("=== Camp ===", rendered)
        self.assertIn("Party and roster", rendered)
        self.assertIn("Supplies and equipment", rendered)
        self.assertIn("Choose one.", rendered)

    def test_combat_target_selection_can_back_out(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        enemy = create_enemy("goblin_skirmisher")
        answers = iter(["1", "2", "4"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(42))
        game.state = GameState(player=player, current_scene="road_ambush")
        called: list[str] = []

        def fake_attack(actor, target, heroes, enemies, dodging, use_smite=False):
            called.append(target.name)

        game.perform_weapon_attack = fake_attack
        game.player_turn(player, [player], [enemy], SimpleNamespace(allow_parley=False, allow_flee=False), set())
        self.assertEqual(called, [])

    def test_failed_skill_check_adds_extra_failure_text(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(43))
        game.roll_with_advantage = lambda actor, advantage_state: SimpleNamespace(kept=1)
        result = game.skill_check(player, "Persuasion", 20, context="to calm a crowd")
        self.assertFalse(result)
        rendered = self.plain_output(log)
        self.assertNotIn("The attempt falls short", rendered)
        self.assertEqual(log[-1], "")

    def test_action_choice_output_adds_trailing_blank_line(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(430))
        game.state = GameState(player=player, current_scene="phandalin_hub")
        game.player_choice_output(game.action_option("Take the writ and head for the High Road."))
        self.assertEqual(log[-2], "*Take the writ and head for the High Road.")
        self.assertEqual(log[-1], "")

    def test_companion_combat_openers_apply_shadow_volley_and_hold_the_line(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        kaelis = create_kaelis_starling()
        kaelis.disposition = 6
        tolan = create_tolan_ironshield()
        tolan.disposition = 6
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(4301))
        game.state = GameState(player=player, companions=[kaelis, tolan], current_scene="road_ambush")
        heroes = [player, kaelis, tolan]
        game.apply_companion_combat_openers(
            heroes,
            [create_enemy("bandit")],
            Encounter(title="Openers", description="", enemies=[create_enemy("bandit")], allow_flee=False),
        )
        for hero in heroes:
            self.assertIn("invisible", hero.conditions)
            self.assertIn("guarded", hero.conditions)

    def test_ash_brand_enforcer_prioritizes_buffed_hero_when_no_mark_exists(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        player.current_hp = 5
        companion = create_tolan_ironshield()
        companion.current_hp = companion.max_hp
        enemy = create_enemy("ash_brand_enforcer")
        enemy.resources["punishing_strike"] = 0
        targeted: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(4302))
        game.state = GameState(player=player, companions=[companion], current_scene="road_ambush")
        game.apply_status(player, "blessed", 2, source="test setup")
        game.perform_enemy_attack = (
            lambda attacker, target, heroes, enemies, dodging: targeted.append(target.name) or False
        )
        game.enemy_turn(enemy, [player, companion], [enemy], SimpleNamespace(), set())
        self.assertEqual(targeted, [player.name])

    def test_official_conditions_are_all_defined(self) -> None:
        official_conditions = {
            "blinded",
            "charmed",
            "deafened",
            "exhaustion",
            "frightened",
            "grappled",
            "incapacitated",
            "invisible",
            "paralyzed",
            "petrified",
            "poisoned",
            "prone",
            "restrained",
            "stunned",
            "unconscious",
        }
        self.assertTrue(official_conditions.issubset(STATUS_DEFINITIONS))

    def test_varyn_binding_hex_can_incapacitate_target(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        varyn = create_enemy("varyn")
        log: list[str] = []
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=log.append, rng=random.Random(114))
        game.state = GameState(player=player, current_scene="emberhall_cellars")
        varyn.resources["silver_tongue"] = 0
        game.saving_throw = lambda actor, ability, dc, context, against_poison=False: False
        game.enemy_turn(varyn, [player], [varyn], SimpleNamespace(), set())
        self.assertIn("incapacitated", player.conditions)
        rendered = self.plain_output(log)
        self.assertIn("binding hex", rendered)
        self.assertIn("locks them in place", rendered)

    def test_restorative_items_clear_new_official_conditions(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        player.conditions.update({"restrained": 2, "prone": 1, "petrified": 1, "exhaustion": 2})
        answers = iter(["2", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=lambda _: None, rng=random.Random(115))
        game.state = GameState(
            player=player,
            current_scene="phandalin_hub",
            inventory={"giantfire_balm": 1, "scroll_resurgent_flame": 1},
        )
        self.assertTrue(game.use_item_from_inventory())
        self.assertNotIn("restrained", player.conditions)
        self.assertNotIn("prone", player.conditions)
        self.assertTrue(game.use_item_from_inventory())
        self.assertNotIn("petrified", player.conditions)
        self.assertEqual(player.conditions.get("exhaustion"), 1)

    def test_burning_ticks_and_battle_cleanup_preserves_only_curses(self) -> None:
        player = build_character(
            name="Velkor",
            race="Human",
            class_name="Fighter",
            background="Soldier",
            base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
            class_skill_choices=["Athletics", "Survival"],
        )
        player.conditions["burning"] = 1
        player.conditions["cursed"] = -1
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(113))
        game.state = GameState(player=player, current_scene="road_ambush")
        before = player.current_hp
        game.tick_conditions(player)
        self.assertLess(player.current_hp, before)
        self.assertNotIn("burning", player.conditions)
        enemy = create_enemy("goblin_skirmisher")
        enemy.current_hp = 0
        enemy.dead = True
        outcome = game.run_encounter(SimpleNamespace(title="Cleanup Test", description="done", enemies=[enemy], allow_flee=False, allow_parley=False, parley_dc=0, hero_initiative_bonus=0, enemy_initiative_bonus=0))
        self.assertEqual(outcome, "victory")
        self.assertIn("cursed", player.conditions)
        self.assertNotIn("burning", player.conditions)


if __name__ == "__main__":
    unittest.main()
