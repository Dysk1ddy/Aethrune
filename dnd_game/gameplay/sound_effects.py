from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

from . import audio_backend


SFX_ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "sfx"
DICE_ROLL_SOUND_MIN_SECONDS = 0.40
DICE_ROLL_SOUND_MAX_SECONDS = 1.75


@dataclass(frozen=True, slots=True)
class DiceRollSoundEffect:
    key: str
    filename: str
    duration_seconds: float


DICE_ROLL_SOUND_EFFECTS: tuple[DiceRollSoundEffect, ...] = (
    DiceRollSoundEffect("dice_roll_040", "dice_roll_040.wav", 0.40),
    DiceRollSoundEffect("dice_roll_070", "dice_roll_070.wav", 0.70),
    DiceRollSoundEffect("dice_roll_095", "dice_roll_095.wav", 0.95),
    DiceRollSoundEffect("dice_roll_130", "dice_roll_130.wav", 1.30),
    DiceRollSoundEffect("dice_roll_175", "dice_roll_175.wav", 1.75),
)

SOUND_EFFECT_FILES: dict[str, str] = {effect.key: effect.filename for effect in DICE_ROLL_SOUND_EFFECTS}


def closest_dice_roll_sound_effect(duration_seconds: float) -> str:
    return min(
        DICE_ROLL_SOUND_EFFECTS,
        key=lambda effect: (abs(effect.duration_seconds - duration_seconds), effect.duration_seconds),
    ).key


class SoundEffectsMixin:
    def initialize_sound_effects_system(self, play_sfx: bool | None = None) -> None:
        wants_sfx = self._interactive_output if play_sfx is None else play_sfx
        self._sound_effects_enabled_preference = bool(wants_sfx)
        self._sfx_supported = audio_backend.sound_effects_are_available()
        self._sfx_asset_dir = SFX_ASSET_DIR
        self._last_sfx_at: dict[str, float] = {}
        self._sfx_assets_ready = all(
            (self._sfx_asset_dir / filename).exists() for filename in SOUND_EFFECT_FILES.values()
        )
        self.sound_effects_enabled = bool(
            wants_sfx and self.output_fn is print and self._sfx_supported and self._sfx_assets_ready
        )

    def sound_effect_path(self, effect_name: str) -> Path | None:
        filename = SOUND_EFFECT_FILES.get(effect_name)
        if filename is None:
            return None
        path = self._sfx_asset_dir / filename
        return path if path.exists() else None

    def play_sound_effect(self, effect_name: str, *, cooldown: float = 0.0) -> None:
        if not self.sound_effects_enabled or not self._sfx_supported or not self._sfx_assets_ready:
            return
        path = self.sound_effect_path(effect_name)
        if path is None:
            return
        now = time.perf_counter()
        last_played = self._last_sfx_at.get(effect_name, 0.0)
        if cooldown > 0.0 and now - last_played < cooldown:
            return
        if not audio_backend.play_sound(path):
            return
        self._last_sfx_at[effect_name] = now

    def play_dice_roll_sound(self, duration_seconds: float, *, cooldown: float = 0.0) -> None:
        self.play_sound_effect(closest_dice_roll_sound_effect(duration_seconds), cooldown=cooldown)

    def set_sound_effects_enabled(self, enabled: bool) -> None:
        self._sound_effects_enabled_preference = bool(enabled)
        persist_settings = getattr(self, "persist_settings", None)
        if enabled and not self._sfx_supported:
            self.sound_effects_enabled = False
            if callable(persist_settings):
                persist_settings()
            self.say("Sound effects are not supported in this build.")
            return
        if enabled and not self._sfx_assets_ready:
            self.sound_effects_enabled = False
            if callable(persist_settings):
                persist_settings()
            self.say("Sound effects are not available yet.")
            return
        self.sound_effects_enabled = bool(enabled and self.output_fn is print and self._sfx_supported)
        if callable(persist_settings):
            persist_settings()
        self.say("Sound effects enabled." if self.sound_effects_enabled else "Sound effects muted.")

    def toggle_sound_effects(self) -> None:
        self.set_sound_effects_enabled(not self.sound_effects_enabled)

    def is_enemy_combatant(self, actor) -> bool:
        return actor is not None and "enemy" in getattr(actor, "tags", [])

    def play_attack_sound_for(self, actor) -> None:
        self.play_sound_effect("enemy_attack" if self.is_enemy_combatant(actor) else "player_attack", cooldown=0.05)

    def play_heal_sound_for(self, actor) -> None:
        self.play_sound_effect("enemy_heal" if self.is_enemy_combatant(actor) else "player_heal", cooldown=0.05)
