from __future__ import annotations

from pathlib import Path
import random
import time

from . import audio_backend


MUSIC_ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "music"
MUSIC_ASSET_EXTENSIONS = frozenset({".flac", ".mp3", ".ogg", ".wav"})

MUSIC_CONTEXT_FOLDERS: dict[str, tuple[str, ...]] = {
    "main_menu": ("Main menu",),
    "character_creation": ("Main menu",),
    "camp": ("Camp",),
    "city": ("Town",),
    "inn": ("Town",),
    "town": ("Town",),
    "wilderness": ("Wilderness exploration",),
    "dungeon": ("Dungeon",),
    "combat": ("Combat",),
    "miniboss_combat": ("Miniboss combat",),
    "boss_combat": ("Miniboss combat",),
    "random_encounter": ("Wilderness exploration",),
}

# Town music is reserved for settled hubs and interior city beats. Greywake's
# roadside triage sequence stays on wilderness tracks until the player reaches
# Mira's actual city briefing.
CITY_SCENE_KEYS: tuple[str, ...] = (
    "neverwinter_briefing",
    "phandalin_hub",
    "act1_complete",
    "act2_claims_council",
    "act2_expedition_hub",
    "act2_scaffold_complete",
)

WILDERNESS_SCENE_KEYS: tuple[str, ...] = (
    "background_prologue",
    "wayside_luck_shrine",
    "greywake_triage_yard",
    "greywake_road_breakout",
    "road_decision_post_blackwake",
    "road_ambush",
    "high_road_liars_circle",
    "high_road_false_checkpoint",
    "high_road_false_tollstones",
)

DUNGEON_SCENE_KEYS: tuple[str, ...] = (
    "blackwake_crossing",
    "old_owl_well",
    "wyvern_tor",
    "cinderfall_ruins",
    "ashfall_watch",
    "tresendar_manor",
    "emberhall_cellars",
    "conyberry_agatha",
    "neverwinter_wood_survey_camp",
    "stonehollow_dig",
    "glasswater_intake",
    "act2_midpoint_convergence",
    "broken_prospect",
    "south_adit",
    "wave_echo_outer_galleries",
    "black_lake_causeway",
    "forge_of_spells",
)

SCENE_MUSIC_CONTEXTS: dict[str, str] = {}
SCENE_MUSIC_CONTEXTS.update({scene_name: "city" for scene_name in CITY_SCENE_KEYS})
SCENE_MUSIC_CONTEXTS.update({scene_name: "wilderness" for scene_name in WILDERNESS_SCENE_KEYS})
SCENE_MUSIC_CONTEXTS.update({scene_name: "dungeon" for scene_name in DUNGEON_SCENE_KEYS})

MUSIC_TRANSITION_CURVE = "linear"
MUSIC_CONTEXT_SWITCH_COOLDOWN_SECONDS = 0.45
MUSIC_INITIAL_FADE_SECONDS = 3.0
MUSIC_COMBAT_TRANSITION_SECONDS = 2.5
MUSIC_BOSS_TRANSITION_SECONDS = 2.25
MUSIC_RANDOM_ENCOUNTER_TRANSITION_SECONDS = 2.6
MUSIC_COMBAT_EXIT_TRANSITION_SECONDS = 4.0
MUSIC_LOCAL_TRANSITION_SECONDS = 4.0
MUSIC_AREA_TRANSITION_SECONDS = 5.0
MUSIC_MUTE_FADE_SECONDS = 2.0
COMBAT_MUSIC_CONTEXTS = frozenset({"combat", "miniboss_combat", "boss_combat"})
LOCAL_MUSIC_CONTEXTS = frozenset({"camp", "inn", "town", "city"})


def music_transition_seconds(previous_context: str | None, next_context: str) -> float:
    if previous_context is None:
        return MUSIC_INITIAL_FADE_SECONDS
    if previous_context == next_context:
        return MUSIC_COMBAT_TRANSITION_SECONDS if next_context in COMBAT_MUSIC_CONTEXTS else MUSIC_LOCAL_TRANSITION_SECONDS
    if next_context == "boss_combat":
        return MUSIC_BOSS_TRANSITION_SECONDS
    if next_context in {"combat", "miniboss_combat"}:
        return MUSIC_COMBAT_TRANSITION_SECONDS
    if next_context == "random_encounter":
        return MUSIC_RANDOM_ENCOUNTER_TRANSITION_SECONDS
    if previous_context in COMBAT_MUSIC_CONTEXTS:
        return MUSIC_COMBAT_EXIT_TRANSITION_SECONDS
    if previous_context in LOCAL_MUSIC_CONTEXTS or next_context in LOCAL_MUSIC_CONTEXTS:
        return MUSIC_LOCAL_TRANSITION_SECONDS
    return MUSIC_AREA_TRANSITION_SECONDS


def music_files_for_context(context: str, asset_dir: Path = MUSIC_ASSET_DIR) -> list[Path]:
    tracks: list[Path] = []
    seen: set[Path] = set()
    for folder_name in MUSIC_CONTEXT_FOLDERS.get(context, ()):
        folder = asset_dir / folder_name
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*"), key=lambda item: str(item).lower()):
            if not path.is_file() or path.suffix.lower() not in MUSIC_ASSET_EXTENSIONS:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            tracks.append(path)
    return tracks


class MusicMixin:
    def initialize_music_system(self, play_music: bool | None = None) -> None:
        wants_music = self._interactive_output if play_music is None else play_music
        self._music_enabled_preference = bool(wants_music)
        self.music_enabled = False
        self._music_context: str | None = None
        self._music_track_name: str | None = None
        self._last_music_track_by_context: dict[str, str] = {}
        self._played_music_track_ids_by_folder: dict[tuple[str, ...], set[str]] = {}
        self._last_music_track_id_by_folder: dict[tuple[str, ...], str] = {}
        self._last_music_transition_at = 0.0
        self._music_asset_dir = MUSIC_ASSET_DIR
        self._music_supported = audio_backend.music_is_available()
        self._music_assets_ready = any(
            self.music_files_for_context(context)
            for context in MUSIC_CONTEXT_FOLDERS
        )
        self.music_enabled = bool(
            wants_music and self.output_fn is print and self._music_supported and self._music_assets_ready
        )

    def music_files_for_context(self, context: str) -> list[Path]:
        return [
            path
            for path in music_files_for_context(context, self._music_asset_dir)
            if audio_backend.music_file_is_supported(path)
        ]

    def _music_folder_key_for_context(self, context: str) -> tuple[str, ...]:
        folder_names = MUSIC_CONTEXT_FOLDERS.get(context, (context,))
        return (str(self._music_asset_dir.resolve()), *folder_names)

    def _music_track_id(self, path: Path) -> str:
        return str(path.resolve())

    def choose_music_file(self, context: str) -> Path | None:
        candidates = self.music_files_for_context(context)
        if not candidates:
            return None
        folder_key = self._music_folder_key_for_context(context)
        played_track_ids = self._played_music_track_ids_by_folder.setdefault(folder_key, set())
        current_track_ids = {self._music_track_id(candidate) for candidate in candidates}
        played_track_ids.intersection_update(current_track_ids)
        candidates_by_play_status = [
            candidate
            for candidate in candidates
            if self._music_track_id(candidate) not in played_track_ids
        ]
        if not candidates_by_play_status:
            last_track_id = self._last_music_track_id_by_folder.get(folder_key)
            played_track_ids.clear()
            if len(candidates) > 1 and last_track_id in current_track_ids:
                played_track_ids.add(last_track_id)
                candidates_by_play_status = [
                    candidate
                    for candidate in candidates
                    if self._music_track_id(candidate) != last_track_id
                ]
            else:
                candidates_by_play_status = candidates
        chooser = getattr(self.rng, "choice", random.choice)
        selected = chooser(candidates_by_play_status)
        selected_track_id = self._music_track_id(selected)
        played_track_ids.add(selected_track_id)
        self._last_music_track_id_by_folder[folder_key] = selected_track_id
        return selected

    def play_music_for_context(self, context: str, *, restart: bool = False, transition_seconds: float | None = None) -> None:
        if not self.music_enabled or not self._music_supported:
            return
        if not restart and self._music_context == context and self._music_track_name is not None:
            return
        now = time.perf_counter()
        if (
            restart
            and self._music_context == context
            and self._music_track_name is not None
            and now - self._last_music_transition_at < MUSIC_CONTEXT_SWITCH_COOLDOWN_SECONDS
        ):
            return
        track_path = self.choose_music_file(context)
        if track_path is None:
            return
        fade_seconds = (
            music_transition_seconds(self._music_context, context)
            if transition_seconds is None
            else max(0.0, transition_seconds)
        )
        if not audio_backend.play_music(
            track_path,
            loops=-1,
            fade_ms=int(fade_seconds * 1000),
            curve=MUSIC_TRANSITION_CURVE,
        ):
            return
        self._music_context = context
        self._music_track_name = track_path.name
        self._last_music_track_by_context[context] = track_path.name
        self._last_music_transition_at = now

    def stop_music(self, *, fade_seconds: float = MUSIC_MUTE_FADE_SECONDS) -> None:
        if not self._music_supported:
            return
        audio_backend.stop_music(
            fade_ms=int(max(0.0, fade_seconds) * 1000),
            curve=MUSIC_TRANSITION_CURVE,
        )
        self._music_context = None
        self._music_track_name = None

    def set_music_enabled(self, enabled: bool) -> None:
        self._music_enabled_preference = bool(enabled)
        persist_settings = getattr(self, "persist_settings", None)
        if enabled and not self._music_supported:
            self.music_enabled = False
            if callable(persist_settings):
                persist_settings()
            self.say("Music playback is not supported in this build.")
            return
        if enabled and not self._music_assets_ready:
            self.music_enabled = False
            if callable(persist_settings):
                persist_settings()
            self.say("Music assets are not available yet.")
            return
        self.music_enabled = bool(enabled and self.output_fn is print and self._music_supported)
        if callable(persist_settings):
            persist_settings()
        if not self.music_enabled:
            self.stop_music()
            self.say("Music muted.")
            return
        self.say("Music enabled.")
        self.refresh_scene_music(default_to_menu=True)

    def toggle_music(self) -> None:
        self.set_music_enabled(not self.music_enabled)

    def scene_music_context(self, scene_name: str | None) -> str | None:
        if scene_name is None:
            return None
        return SCENE_MUSIC_CONTEXTS.get(scene_name)

    def refresh_scene_music(self, *, default_to_menu: bool = False) -> None:
        if getattr(self, "_random_encounter_active", False):
            context = "random_encounter"
        else:
            scene_name = self.state.current_scene if self.state is not None else None
            context = self.scene_music_context(scene_name)
        if context is None and default_to_menu:
            context = "main_menu"
        if context is None:
            self.stop_music()
            return
        self.play_music_for_context(context)

    def encounter_music_context(self, encounter) -> str:
        title = getattr(encounter, "title", "").lower()
        if title.startswith("boss:"):
            return "boss_combat"
        if title.startswith("miniboss:"):
            return "miniboss_combat"
        return "combat"

    def play_encounter_music(self, encounter) -> None:
        self.play_music_for_context(self.encounter_music_context(encounter), restart=True)
