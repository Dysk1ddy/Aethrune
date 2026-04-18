from __future__ import annotations

from pathlib import Path
import random

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

SCENE_MUSIC_CONTEXTS: dict[str, str] = {
    "background_prologue": "wilderness",
    "neverwinter_briefing": "city",
    "blackwake_crossing": "dungeon",
    "road_decision_post_blackwake": "wilderness",
    "road_ambush": "wilderness",
    "phandalin_hub": "city",
    "old_owl_well": "dungeon",
    "wyvern_tor": "dungeon",
    "cinderfall_ruins": "dungeon",
    "ashfall_watch": "dungeon",
    "tresendar_manor": "dungeon",
    "emberhall_cellars": "dungeon",
    "act1_complete": "city",
    "act2_claims_council": "city",
    "act2_expedition_hub": "city",
    "conyberry_agatha": "dungeon",
    "neverwinter_wood_survey_camp": "dungeon",
    "stonehollow_dig": "dungeon",
    "act2_midpoint_convergence": "dungeon",
    "broken_prospect": "dungeon",
    "south_adit": "dungeon",
    "wave_echo_outer_galleries": "dungeon",
    "black_lake_causeway": "dungeon",
    "forge_of_spells": "dungeon",
    "act2_scaffold_complete": "city",
}


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

    def choose_music_file(self, context: str) -> Path | None:
        candidates = self.music_files_for_context(context)
        if not candidates:
            return None
        last_track = self._last_music_track_by_context.get(context)
        if len(candidates) > 1 and last_track is not None:
            filtered = [candidate for candidate in candidates if candidate.name != last_track]
            if filtered:
                candidates = filtered
        chooser = getattr(self.rng, "choice", random.choice)
        return chooser(candidates)

    def play_music_for_context(self, context: str, *, restart: bool = False) -> None:
        if not self.music_enabled or not self._music_supported:
            return
        if not restart and self._music_context == context and self._music_track_name is not None:
            return
        track_path = self.choose_music_file(context)
        if track_path is None:
            return
        if not audio_backend.play_music(track_path, loops=-1):
            return
        self._music_context = context
        self._music_track_name = track_path.name
        self._last_music_track_by_context[context] = track_path.name

    def stop_music(self) -> None:
        if not self._music_supported:
            return
        audio_backend.stop_music()
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
