from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import random
import re
import sys
import time

try:
    import msvcrt
except ImportError:  # pragma: no cover - Windows-only polling
    msvcrt = None

from ..content import (
    ACTS,
    create_bryn_underbough,
    create_elira_dawnmantle,
    create_tolan_ironshield,
)
from ..data.story.lore import LORE_INTRO, TITLE_LORE_SECTIONS, manual_text_for_entry
from ..dice import roll
from ..items import (
    EQUIPMENT_SLOTS,
    ITEMS,
    LEGACY_ITEM_NAMES,
    canonical_equipment_slot,
    initial_merchant_stock,
    starter_item_ids_for_character,
)
from ..models import Character, GameState, SKILL_TO_ABILITY, Weapon
from ..ui.colors import rich_style_name, strip_ansi
from ..ui.rich_render import Columns, Group, Panel, Table, Text, box, render_rich_lines
from .constants import InputFn, LEVEL_XP_THRESHOLDS, MENU_PAGE_SIZE, OutputFn


class GameInterrupted(Exception):
    pass


class ReturnToTitleMenu(Exception):
    pass


class ResumeLoadedGame(Exception):
    pass


class QuitProgram(Exception):
    pass


class GameBase:
    SETTINGS_FILENAME = "settings.json"
    AUTOSAVE_PREFIX = "autosave__"
    AUTOSAVE_LIMIT = 15
    BOOLEAN_SETTINGS_KEYS = (
        "sound_effects_enabled",
        "music_enabled",
        "dice_animations_enabled",
        "typed_dialogue_enabled",
        "pacing_pauses_enabled",
        "staggered_reveals_enabled",
        "animations_and_delays_enabled",
    )
    DICE_ANIMATION_MODES = ("off", "minimal", "full")
    DICE_ANIMATION_MODE_LABELS = {
        "off": "Off",
        "minimal": "Minimal",
        "full": "Full",
    }
    SETTINGS_KEYS = (*BOOLEAN_SETTINGS_KEYS, "dice_animation_mode")
    DEFAULT_SETTINGS_PAYLOAD = {
        "sound_effects_enabled": False,
        "music_enabled": True,
        "dice_animations_enabled": True,
        "dice_animation_mode": "full",
        "typed_dialogue_enabled": True,
        "pacing_pauses_enabled": True,
        "staggered_reveals_enabled": True,
        "animations_and_delays_enabled": True,
    }
    ACT_LABELS = {
        1: "I",
        2: "II",
        3: "III",
    }
    SCENE_LABELS = {
        "background_prologue": "Prologue",
        "wayside_luck_shrine": "Wayside Luck Shrine",
        "greywake_triage_yard": "Greywake Yard",
        "greywake_road_breakout": "Greywake Breakout",
        "neverwinter_briefing": "Neverwinter",
        "road_ambush": "High Road",
        "high_road_liars_circle": "Liar's Circle",
        "high_road_false_checkpoint": "False Checkpoint",
        "high_road_false_tollstones": "False Tollstones",
        "phandalin_hub": "Phandalin",
        "old_owl_well": "Old Owl Well",
        "wyvern_tor": "Wyvern Tor",
        "ashfall_watch": "Ashfall Watch",
        "tresendar_manor": "Tresendar Manor",
        "emberhall_cellars": "Emberhall Cellars",
        "act1_complete": "Phandalin",
        "act2_claims_council": "Stonehill Claims Council",
        "act2_expedition_hub": "Act II Expedition Hub",
        "conyberry_agatha": "Conyberry",
        "neverwinter_wood_survey_camp": "Neverwinter Wood",
        "stonehollow_dig": "Stonehollow Dig",
        "act2_midpoint_convergence": "Sabotage Night",
        "broken_prospect": "Broken Prospect",
        "south_adit": "South Adit",
        "wave_echo_outer_galleries": "Wave Echo Cave",
        "black_lake_causeway": "Black Lake Causeway",
        "forge_of_spells": "Forge of Spells",
        "act2_scaffold_complete": "Wave Echo Cave",
        "act3_ninth_ledger_opens": "Ninth Ledger",
        "act3_ninth_ledger_aftermath": "Ledger Aftermath",
    }
    SCENE_OBJECTIVES = {
        "background_prologue": "Finish your origin story and answer the road's first test.",
        "wayside_luck_shrine": "Meet Elira Dawnmantle and steady the first wounded travelers.",
        "greywake_triage_yard": "Stabilize Greywake Yard before the road pressure breaks open.",
        "greywake_road_breakout": "Protect the wounded or the proof when the Ashen Brand attacks.",
        "neverwinter_briefing": "Hear Mira Thann out and take the road south.",
        "blackwake_crossing": "Trace the Blackwake supply cell before committing to the High Road.",
        "road_decision_post_blackwake": "Choose whether to report back to Neverwinter or press south after Blackwake.",
        "road_ambush": "Survive the High Road attack and reach Phandalin.",
        "high_road_liars_circle": "Solve the four-statue liar's puzzle or leave the circle alone.",
        "high_road_false_checkpoint": "Expose or outtalk the fake roadwardens demanding travel papers.",
        "high_road_false_tollstones": "Break or outtalk the false roadwarden toll at the broken milemarker.",
        "phandalin_hub": "Choose which pressure in Phandalin to answer next.",
        "old_owl_well": "Break the grave-salvage line at Old Owl Well.",
        "wyvern_tor": "Break the Wyvern Tor raiders.",
        "ashfall_watch": "Break Ashfall Watch and reopen the road.",
        "tresendar_manor": "Push through Tresendar Manor.",
        "emberhall_cellars": "Finish the fight beneath Emberhall.",
        "act1_complete": "Close out Act I and prepare for the next march.",
        "act2_claims_council": "Hold the claims council together and set the expedition's direction.",
        "act2_expedition_hub": "Pick the next Act II lead and keep the expedition moving.",
        "conyberry_agatha": "Learn what Conyberry's dead still remember.",
        "neverwinter_wood_survey_camp": "Secure the survey route through the woods.",
        "stonehollow_dig": "Stabilize Stonehollow and recover the missing team.",
        "act2_midpoint_convergence": "Keep Phandalin from tearing itself apart overnight.",
        "broken_prospect": "Push deeper toward Wave Echo's broken claim.",
        "south_adit": "Free the prisoners from the South Adit.",
        "wave_echo_outer_galleries": "Break into the deeper galleries safely.",
        "black_lake_causeway": "Cross the Black Lake route and keep the line intact.",
        "forge_of_spells": "Break the Quiet Choir's hold on the Forge.",
        "act2_scaffold_complete": "Bring the truth back out of Wave Echo Cave.",
        "act3_ninth_ledger_opens": "Expose the route that Varyn did not design.",
        "act3_ninth_ledger_aftermath": "Track revealed Ledger pressure and unrecorded choices.",
    }
    HUD_QUEST_FOCUSED_SCENES = {
        "phandalin_hub",
        "act1_complete",
        "act2_claims_council",
        "act2_expedition_hub",
        "act2_scaffold_complete",
    }
    DEV_GOD_MODE_FLAG = "dev_god_mode"
    DEV_PASS_CHECKS_FLAG = "dev_pass_every_dice_check"
    STORY_SKILL_MODIFIER_KEY = "story_skill_modifiers"
    LIARS_BLESSING_MODIFIER_ID = "liars_blessing"
    LIARS_CURSE_MODIFIER_ID = "liars_curse"
    NAMED_CHARACTER_INTROS = {
        "Mira Thann": "Mira Thann is a sharp-eyed Neverwinter officer who wears quiet authority like armor and studies every answer for weakness or leverage.",
        "Tessa Harrow": "Tessa Harrow is Phandalin's exhausted steward, all ink-stained hands, sleepless focus, and frontier resolve held together by sheer will.",
        "Bryn Underbough": "Bryn Underbough is a halfling trail scout with quick eyes, a quicker tongue, and the watchful stillness of someone who trusts exits before promises.",
        "Elira Dawnmantle": "Elira Dawnmantle is a priestess of Tymora whose steady hands and road-worn faith make the shrine feel more like a field hospital than a sanctuary.",
        "Barthen": "Barthen is a broad-shouldered provisioner with a merchant's apron, a teamster's worry, and the tired patience of a man rationing hope as carefully as flour.",
        "Halia Thornton": "Halia Thornton is a polished guild agent with perfectly measured calm, sharp ledgers, and the kind of smile that always seems to know one more thing than it says.",
        "Daran Edermath": "Daran Edermath is a retired half-elf adventurer tending his orchard like a quiet fortification, all old reflexes, weathered patience, and the easy economy of someone who has survived uglier frontiers.",
        "Linene Graywind": "Linene Graywind is a hard-edged quartermaster who keeps her post like a disciplined armory, missing nothing and trusting earned results over charm.",
        "Kaelis Starling": "Kaelis Starling is a lean half-elf ranger whose attention never stops moving, as if every doorway and hedgeline is already a map in his head.",
        "Rhogar Valeguard": "Rhogar Valeguard is a bronze-scaled dragonborn paladin who carries himself like a sworn roadwarden, proud-backed and visibly made of vows.",
        "Tolan Ironshield": "Tolan Ironshield is a battle-scarred dwarven caravan guard with a wall of a shield, a gravel voice, and the look of someone who has outlived too many ambushes.",
        "Vaelith Marr": "Vaelith Marr is a soot-handed gravecaller in scavenged ritual cloth, moving with the calm precision of someone who finds other people's dead more useful than the living.",
        "Brughor Skullcleaver": "Brughor Skullcleaver is a broad orc blood-chief in battered scale, grinning like every fight is a feast he intends to survive.",
        "Cragmaw-Ogre Thane": "The Cragmaw-Ogre Thane is a huge scar-latticed brute dragging a stone-shaved club, all stubborn muscle and habitually casual violence.",
        "Cistern Eye": "The Cistern Eye is a warped cellar horror with one wet reflective gaze and a posture that suggests it has spent too long feeding on secrets in the dark.",
        "Rukhar Cinderfang": "Rukhar Cinderfang is a broad hobgoblin sergeant in disciplined mail, every movement controlled with the hard efficiency of a drilled war captain.",
        "Sereth Vane": "Sereth Vane is a road-dusted Ashen Brand quartermaster with a negotiator's smile, a fixer's eyes, and hands that never drift far from hidden ash capsules.",
        "Varyn Sable": "Varyn Sable is a poised, sharp-featured brigand captain dressed better than the rest of the gang, with a duelist's balance and a smile that never warms.",
        "Ashen Brand Runner": "The Ashen Brand Runner is a wiry courier with road dust on their boots and the twitchy focus of someone used to escaping before blades can reach them.",
        "Ashen Brand Collector": "The Ashen Brand Collector looks like a dockside broker turned enforcer, weighed down by stolen papers, quiet greed, and a hand never far from steel.",
        "Archive Cutout": "The Archive Cutout is a hired bow-hand with ink-smudged fingers and a scavenger's posture, more accustomed to theft and flight than a fair fight.",
        "Ashen Brand Fixer": "The Ashen Brand Fixer dresses like a market broker but scans the crowd like a knife fighter, always measuring who can be bought, fooled, or buried.",
        "Ashen Brand Teamster": "The Ashen Brand Teamster looks like a wagon hand gone bad, all road calluses, hidden tension, and the hunted eyes of someone already planning an escape.",
        "Goblin Cutthroat": "The Goblin Cutthroat is smaller than the others but moves with nasty confidence, grinning around a blade nicked by too much eager use.",
        "Ashen Brand Enforcer": "The Ashen Brand Enforcer is a thick-shouldered bruiser in scavenged gear, built to hold a doorway and make fear do half the work.",
        "Goblin Scavenger": "The Goblin Scavenger is a soot-streaked little raider with a sack on one shoulder and the quick, hungry stare of something that lives off battle's leftovers.",
    }

    def __init__(
        self,
        *,
        input_fn: InputFn = input,
        output_fn: OutputFn = print,
        save_dir: str | Path | None = None,
        rng: random.Random | None = None,
        animate_dice: bool | None = None,
        pace_output: bool | None = None,
        type_dialogue: bool | None = None,
        play_music: bool | None = None,
        play_sfx: bool | None = None,
    ) -> None:
        self.input_fn = input_fn
        self.output_fn = output_fn
        self._uses_default_save_dir = save_dir is None
        self.save_dir = Path(save_dir or Path.cwd() / "saves")
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.save_dir / self.SETTINGS_FILENAME
        self.rng = rng or random.Random()
        self._interactive_output = input_fn is input and output_fn is print
        self.autosaves_enabled = self._interactive_output
        should_apply_persisted_settings = self._interactive_output or not self._uses_default_save_dir
        persisted_settings = self.load_persisted_settings() if should_apply_persisted_settings else {}
        default_settings = self.default_settings_payload()
        default_presentation = persisted_settings.get(
            "animations_and_delays_enabled",
            default_settings["animations_and_delays_enabled"] if should_apply_persisted_settings else self._interactive_output,
        )
        stored_dice_mode = persisted_settings.get("dice_animation_mode")
        if animate_dice is None:
            if isinstance(stored_dice_mode, str) and stored_dice_mode in self.DICE_ANIMATION_MODES:
                requested_dice_mode = stored_dice_mode
            elif "dice_animations_enabled" in persisted_settings:
                requested_dice_mode = "full" if bool(persisted_settings["dice_animations_enabled"]) else "off"
            else:
                requested_dice_mode = "full" if default_presentation else "off"
        else:
            requested_dice_mode = "full" if animate_dice else "off"
        requested_pacing = (
            persisted_settings.get("pacing_pauses_enabled", default_presentation)
            if pace_output is None
            else pace_output
        )
        requested_dialogue_typing = (
            persisted_settings.get("typed_dialogue_enabled", default_presentation)
            if type_dialogue is None
            else type_dialogue
        )
        requested_staggered_reveals = persisted_settings.get("staggered_reveals_enabled", default_presentation)
        self._dice_animation_mode_preference = (
            requested_dice_mode if requested_dice_mode in self.DICE_ANIMATION_MODES else "off"
        )
        self._dice_animations_preference = self._dice_animation_mode_preference != "off"
        self._pacing_pauses_preference = bool(requested_pacing)
        self._typed_dialogue_preference = bool(requested_dialogue_typing)
        self._staggered_reveals_preference = bool(requested_staggered_reveals)
        self._animations_and_delays_preference = bool(
            self._dice_animations_preference
            and self._pacing_pauses_preference
            and self._typed_dialogue_preference
            and self._staggered_reveals_preference
        )
        self.animate_dice = self._dice_animations_preference
        self.apply_dice_animation_mode_profile()
        self.pace_output = self._pacing_pauses_preference
        self.type_dialogue = bool(self._typed_dialogue_preference and output_fn is print)
        self.staggered_reveals_enabled = self._staggered_reveals_preference
        self._dice_animation_width = 0
        self._choice_pause_seconds = 1.0
        self._combat_transition_pause_seconds = 1.0
        self._option_reveal_pause_seconds = 0.5
        self._loot_reveal_pause_seconds = 0.75
        self._health_bar_width = 12
        self._health_bar_animation_step_seconds = 0.08
        self._dialogue_character_delay_seconds = 0.03
        self._dialogue_seconds_per_sentence = 2.5
        self._narration_seconds_per_sentence = 2.5
        self._typing_sentence_pause_seconds = 0.75
        self._animation_skip_latched = False
        self._animation_skip_scope_depth = 0
        self._compact_hud_last_scene_key: tuple[int, str] | None = None
        self._compact_hud_requested = False
        self._latest_narration_lines: list[str] = []
        self._pending_act1_dungeon_map_refresh = False
        self._pending_act1_dungeon_movement_text = ""
        self._pending_act2_dungeon_map_refresh = False
        self._pending_act2_dungeon_movement_text = ""
        self._music_enabled_preference = bool(
            persisted_settings.get(
                "music_enabled",
                default_settings["music_enabled"] if should_apply_persisted_settings else self._interactive_output,
            )
            if play_music is None
            else play_music
        )
        initialize_music_system = getattr(self, "initialize_music_system", None)
        if callable(initialize_music_system):
            initialize_music_system(self._music_enabled_preference)
        self._sound_effects_enabled_preference = bool(
            persisted_settings.get(
                "sound_effects_enabled",
                default_settings["sound_effects_enabled"] if should_apply_persisted_settings else self._interactive_output,
            )
            if play_sfx is None
            else play_sfx
        )
        initialize_sound_effects_system = getattr(self, "initialize_sound_effects_system", None)
        if callable(initialize_sound_effects_system):
            initialize_sound_effects_system(self._sound_effects_enabled_preference)
        if self.animate_dice:
            try:
                setattr(self.rng, "dice_roll_animator", self.animate_dice_roll)
            except Exception:
                self.animate_dice = False
                self._dice_animations_preference = False
        self.state: GameState | None = None
        self._in_combat = False
        self._at_title_screen = False
        self._scene_handlers = {
            "background_prologue": self.scene_background_prologue,
            "wayside_luck_shrine": self.scene_wayside_luck_shrine,
            "greywake_triage_yard": self.scene_greywake_triage_yard,
            "greywake_road_breakout": self.scene_greywake_road_breakout,
            "neverwinter_briefing": self.scene_neverwinter_briefing,
            "blackwake_crossing": self.scene_blackwake_crossing,
            "road_decision_post_blackwake": self.scene_road_decision_post_blackwake,
            "road_ambush": self.scene_road_ambush,
            "high_road_liars_circle": self.scene_high_road_liars_circle,
            "high_road_false_checkpoint": self.scene_high_road_false_checkpoint,
            "high_road_false_tollstones": self.scene_high_road_false_tollstones,
            "phandalin_hub": self.scene_phandalin_hub,
            "old_owl_well": self.scene_old_owl_well,
            "wyvern_tor": self.scene_wyvern_tor,
            "ashfall_watch": self.scene_ashfall_watch,
            "tresendar_manor": self.scene_tresendar_manor,
            "emberhall_cellars": self.scene_emberhall_cellars,
            "act1_complete": self.scene_act1_complete,
            "act2_claims_council": self.scene_act2_claims_council,
            "act2_expedition_hub": self.scene_act2_expedition_hub,
            "conyberry_agatha": self.scene_conyberry_agatha,
            "neverwinter_wood_survey_camp": self.scene_neverwinter_wood_survey_camp,
            "stonehollow_dig": self.scene_stonehollow_dig,
            "act2_midpoint_convergence": self.scene_act2_midpoint_convergence,
            "broken_prospect": self.scene_broken_prospect,
            "south_adit": self.scene_south_adit,
            "wave_echo_outer_galleries": self.scene_wave_echo_outer_galleries,
            "black_lake_causeway": self.scene_black_lake_causeway,
            "forge_of_spells": self.scene_forge_of_spells,
            "act2_scaffold_complete": self.scene_act2_scaffold_complete,
            "act3_ninth_ledger_opens": self.scene_act3_ninth_ledger_opens,
            "act3_ninth_ledger_aftermath": self.scene_act3_ninth_ledger_aftermath,
        }

    def load_persisted_settings(self) -> dict[str, object]:
        if not self.settings_path.exists():
            return {}
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        settings: dict[str, object] = {}
        for key in self.BOOLEAN_SETTINGS_KEYS:
            if key in data:
                settings[key] = bool(data[key])
        dice_mode = data.get("dice_animation_mode")
        if isinstance(dice_mode, str) and dice_mode in self.DICE_ANIMATION_MODES:
            settings["dice_animation_mode"] = dice_mode
        return settings

    @classmethod
    def default_settings_payload(cls) -> dict[str, object]:
        return dict(cls.DEFAULT_SETTINGS_PAYLOAD)

    def current_settings_payload(self) -> dict[str, object]:
        presentation_bundle = bool(
            getattr(self, "_dice_animations_preference", self.animate_dice)
            and getattr(self, "_typed_dialogue_preference", self.type_dialogue)
            and getattr(self, "_pacing_pauses_preference", self.pace_output)
            and getattr(self, "_staggered_reveals_preference", getattr(self, "staggered_reveals_enabled", False))
        )
        return {
            "sound_effects_enabled": bool(
                getattr(self, "_sound_effects_enabled_preference", getattr(self, "sound_effects_enabled", False))
            ),
            "music_enabled": bool(getattr(self, "_music_enabled_preference", getattr(self, "music_enabled", False))),
            "dice_animations_enabled": bool(getattr(self, "_dice_animations_preference", self.animate_dice)),
            "dice_animation_mode": self.current_dice_animation_mode(),
            "typed_dialogue_enabled": bool(getattr(self, "_typed_dialogue_preference", self.type_dialogue)),
            "pacing_pauses_enabled": bool(getattr(self, "_pacing_pauses_preference", self.pace_output)),
            "staggered_reveals_enabled": bool(
                getattr(self, "_staggered_reveals_preference", getattr(self, "staggered_reveals_enabled", False))
            ),
            "animations_and_delays_enabled": presentation_bundle,
        }

    def current_dice_animation_mode(self) -> str:
        mode = getattr(self, "_dice_animation_mode_preference", "off")
        return mode if mode in self.DICE_ANIMATION_MODES else "off"

    def dice_animation_mode_label(self, mode: str | None = None) -> str:
        return self.DICE_ANIMATION_MODE_LABELS.get(mode or self.current_dice_animation_mode(), "Off")

    def apply_dice_animation_mode_profile(self) -> None:
        mode = self.current_dice_animation_mode()
        profiles = {
            "off": {
                "min_seconds": 0.0,
                "max_seconds": 0.0,
                "total_pause": 0.0,
                "final_pause": 0.0,
                "min_frames": 0,
                "max_frames": 0,
                "frame_rate": 0.0,
            },
            "minimal": {
                "min_seconds": 0.4,
                "max_seconds": 0.9,
                "total_pause": 0.14,
                "final_pause": 0.2,
                "min_frames": 7,
                "max_frames": 11,
                "frame_rate": 10.0,
            },
            "full": {
                "min_seconds": 0.85,
                "max_seconds": 1.75,
                "total_pause": 0.28,
                "final_pause": 0.42,
                "min_frames": 11,
                "max_frames": 20,
                "frame_rate": 14.0,
            },
        }
        profile = profiles[mode]
        self._dice_animations_preference = mode != "off"
        self.animate_dice = self._dice_animations_preference
        self._dice_animation_min_seconds = profile["min_seconds"]
        self._dice_animation_max_seconds = profile["max_seconds"]
        self._dice_total_reveal_pause_seconds = profile["total_pause"]
        self._dice_animation_final_pause_seconds = profile["final_pause"]
        self._dice_animation_min_frames = profile["min_frames"]
        self._dice_animation_max_frames = profile["max_frames"]
        self._dice_animation_frame_rate = profile["frame_rate"]

    def persist_settings(self) -> None:
        try:
            self.settings_path.write_text(
                json.dumps(self.current_settings_payload(), indent=2),
                encoding="utf-8",
            )
        except OSError:
            return

    MERCHANT_ATTITUDE_DEFAULTS = {
        "barthen_provisions": 20,
        "linene_graywind": 15,
    }

    def run(self) -> None:
        try:
            title_options = [
                "Start a new game",
                "Save Files",
                "Read the lore notes",
                "Settings",
                "Quit",
            ]
            title_option_details = {
                "Start a new game": "Build a new character and ride south toward Phandalin.",
                "Save Files": "Browse save files, load a run, or delete old journals.",
                "Read the lore notes": "Browse Forgotten Realms context, rules guidance, and item basics.",
                "Settings": "Adjust audio, animations, typed narration, and presentation pacing.",
                "Quit": "Leave the frontier for now.",
            }
            while True:
                try:
                    self._at_title_screen = True
                    refresh_scene_music = getattr(self, "refresh_scene_music", None)
                    if callable(refresh_scene_music):
                        refresh_scene_music(default_to_menu=True)
                    choice = self.choose_title_menu(
                        "Sword Coast",
                        "Acts I-II: Frontier Roads and Echoing Depths",
                        (
                            "A choice-driven D&D-inspired text adventure spanning the road from "
                            "Neverwinter to Phandalin and the dangers beneath Wave Echo Cave."
                        ),
                        title_options,
                        option_details=title_option_details,
                    )
                    if choice == 1:
                        self._at_title_screen = False
                        self.start_new_game()
                        self.play_current_state()
                    elif choice == 2:
                        self._at_title_screen = False
                        loaded = self.open_save_files_menu()
                        if loaded:
                            self.play_current_state()
                    elif choice == 3:
                        self.show_lore_notes()
                    elif choice == 4:
                        self.open_settings_menu()
                    else:
                        self.say("Safe travels, adventurer.")
                        return
                except ResumeLoadedGame:
                    self._at_title_screen = False
                    if self.state is not None:
                        self.play_current_state()
                except ReturnToTitleMenu:
                    self.state = None
                    self._compact_hud_last_scene_key = None
                    self._at_title_screen = True
                    continue
                except QuitProgram:
                    self.say("Safe travels, adventurer.")
                    return
        except GameInterrupted:
            self.say("Input interrupted. Closing the game cleanly.")
            self.state = None
        finally:
            self._at_title_screen = False

    def play_current_state(self) -> None:
        try:
            while self.state is not None:
                try:
                    self._at_title_screen = False
                    handler = self._scene_handlers.get(self.state.current_scene)
                    if handler is None:
                        self.say(f"Unknown scene '{self.state.current_scene}'. Returning to the title screen.")
                        self.state = None
                        return
                    refresh_scene_music = getattr(self, "refresh_scene_music", None)
                    if callable(refresh_scene_music):
                        refresh_scene_music()
                    handler()
                except ResumeLoadedGame:
                    self._compact_hud_last_scene_key = None
                    continue
                except ReturnToTitleMenu:
                    self.state = None
                    self._compact_hud_last_scene_key = None
                    return
        except GameInterrupted:
            self.say("Input interrupted. Returning to the title screen.")
            self.state = None

    def skill_tag(self, tag: str, text: str) -> str:
        return f"[{tag}] {text}"

    def quoted_option(self, tag: str, text: str) -> str:
        return self.skill_tag(tag, f"\"{text}\"")

    def action_option(self, text: str) -> str:
        return f"*{text}"

    def choice_text(self, option: str) -> str:
        return re.sub(r"^\[[^\]]+\]\s*", "", option).strip()

    def read_input(self, prompt: str) -> str:
        self._animation_skip_latched = False
        self._animation_skip_scope_depth = 0
        try:
            return self.input_fn(prompt)
        except KeyboardInterrupt as exc:
            self.output_fn("")
            raise GameInterrupted() from exc

    def pause_for_choice_resolution(self) -> None:
        if self.pace_output:
            time.sleep(self._choice_pause_seconds)

    def pause_for_combat_transition(self) -> None:
        if self.pace_output:
            time.sleep(self._combat_transition_pause_seconds)

    def pause_for_loot_reveal(self) -> None:
        if self.pace_output:
            self.sleep_for_animation(self._loot_reveal_pause_seconds)

    def pause_for_option_reveal(self) -> None:
        if getattr(self, "staggered_reveals_enabled", False):
            self.sleep_for_animation(self._option_reveal_pause_seconds)

    def health_bar_color(self, current_hp: int, max_hp: int) -> str:
        if max_hp <= 0:
            return "light_red"
        percent = max(0.0, min(100.0, (current_hp / max_hp) * 100))
        if percent > 50:
            return "light_green"
        if percent > 25:
            return "yellow"
        return "light_red"

    def format_health_bar(self, current_hp: int, max_hp: int, *, width: int | None = None) -> str:
        width = width or self._health_bar_width
        if max_hp <= 0:
            max_hp = 1
        clamped = max(0, min(current_hp, max_hp))
        filled = int(round((clamped / max_hp) * width))
        filled = max(0, min(width, filled))
        empty = width - filled
        bar = self.style_text("█" * filled, self.health_bar_color(clamped, max_hp)) + (" " * empty)
        digits = len(str(max_hp))
        return f"HP [{bar}] {clamped:>{digits}}/{max_hp}"

    def health_status_suffix(self, current_hp: int, *, dead: bool = False) -> str:
        if dead:
            return " (dead)"
        if current_hp == 0:
            return " (down)"
        return ""

    def should_animate_health_bars(self) -> bool:
        return self.pace_output and self.output_fn is print

    def begin_animation_skip_scope(self) -> None:
        self._animation_skip_scope_depth += 1
        if self._animation_skip_scope_depth == 1:
            self._animation_skip_latched = False

    def end_animation_skip_scope(self) -> None:
        if self._animation_skip_scope_depth > 0:
            self._animation_skip_scope_depth -= 1
        if self._animation_skip_scope_depth == 0:
            self._animation_skip_latched = False

    def drain_animation_keys(self) -> bool:
        requested = False
        while msvcrt.kbhit():
            key = msvcrt.getwch()
            if key in {"\r", "\n"}:
                requested = True
        return requested

    def animation_skip_requested(self, *, require_animation: bool = False) -> bool:
        if require_animation and not self.animate_dice:
            return False
        if not self._interactive_output or msvcrt is None:
            return False
        if hasattr(sys.stdin, "isatty") and not sys.stdin.isatty():
            return False
        if self._animation_skip_latched:
            self.drain_animation_keys()
            return False
        requested = self.drain_animation_keys()
        if requested:
            self._animation_skip_latched = True
        return requested

    def sleep_for_animation(self, duration: float, *, require_animation: bool = False) -> bool:
        started_scope = self._animation_skip_scope_depth == 0
        if started_scope:
            self.begin_animation_skip_scope()
        try:
            end_time = time.perf_counter() + max(0.0, duration)
            while True:
                if self.animation_skip_requested(require_animation=require_animation):
                    return True
                remaining = end_time - time.perf_counter()
                if remaining <= 0:
                    return False
                time.sleep(min(0.03, remaining))
        finally:
            if started_scope:
                self.end_animation_skip_scope()

    def animate_health_bar_loss(self, target, previous_hp: int, new_hp: int) -> None:
        if not self.should_animate_health_bars() or new_hp >= previous_hp or target.max_hp <= 0:
            return
        self.begin_animation_skip_scope()
        try:
            width = 0
            steps = max(1, min(12, previous_hp - new_hp))
            values: list[int] = []
            for index in range(1, steps + 1):
                progress = index / steps
                candidate = previous_hp - int(round((previous_hp - new_hp) * progress))
                candidate = max(new_hp, min(previous_hp, candidate))
                if not values or candidate != values[-1]:
                    values.append(candidate)
            if not values or values[-1] != new_hp:
                values.append(new_hp)
            for value in values:
                text = f"{self.style_name(target)} {self.format_health_bar(value, target.max_hp)}{self.health_status_suffix(value, dead=target.dead)}"
                visible_width = len(strip_ansi(text))
                padding = max(0, width - visible_width)
                sys.stdout.write("\r" + text + (" " * padding))
                sys.stdout.flush()
                width = max(width, visible_width)
                if self.sleep_for_animation(self._health_bar_animation_step_seconds):
                    final_text = (
                        f"{self.style_name(target)} {self.format_health_bar(new_hp, target.max_hp)}"
                        f"{self.health_status_suffix(new_hp, dead=target.dead)}"
                    )
                    final_width = len(strip_ansi(final_text))
                    final_padding = max(0, width - final_width)
                    sys.stdout.write("\r" + final_text + (" " * final_padding))
                    sys.stdout.flush()
                    break
            sys.stdout.write("\n")
            sys.stdout.flush()
        finally:
            self.end_animation_skip_scope()

    def dialogue_sentence_count(self, text: str) -> int:
        parts = re.findall(r"[^.!?]+[.!?]+(?:['\"])?|[^.!?]+$", text)
        return max(1, sum(1 for part in parts if part.strip()))

    def dialogue_typing_duration(self, text: str) -> float:
        return self._dialogue_character_delay_seconds * max(1, len(text))

    def is_sentence_boundary(self, text: str, index: int) -> bool:
        character = text[index]
        if character not in ".!?":
            return False
        next_index = index + 1
        while next_index < len(text) and text[next_index] in {'"', "'"}:
            next_index += 1
        return next_index >= len(text) or text[next_index].isspace()

    def typewrite_text(self, text: str, *, delay: float) -> None:
        self.begin_animation_skip_scope()
        try:
            for index, character in enumerate(text):
                if self.animation_skip_requested():
                    remainder = text[index:]
                    if remainder:
                        sys.stdout.write(remainder)
                        sys.stdout.flush()
                    return
                sys.stdout.write(character)
                sys.stdout.flush()
                if self.sleep_for_animation(delay):
                    remainder = text[index + 1 :]
                    if remainder:
                        sys.stdout.write(remainder)
                        sys.stdout.flush()
                    return
                if self.is_sentence_boundary(text, index):
                    if self.sleep_for_animation(self._typing_sentence_pause_seconds):
                        remainder = text[index + 1 :]
                        if remainder:
                            sys.stdout.write(remainder)
                            sys.stdout.flush()
                        return
        finally:
            self.end_animation_skip_scope()

    def typewrite_dialogue_line(self, speaker_name: str, text: str) -> None:
        self.output_fn("")
        prefix = f'{speaker_name}: "'
        sys.stdout.write(prefix)
        sys.stdout.flush()
        self.typewrite_text(text, delay=self._dialogue_character_delay_seconds)
        sys.stdout.write('"\n\n')
        sys.stdout.flush()

    def narration_typing_duration(self, text: str) -> float:
        return self._narration_seconds_per_sentence * self.dialogue_sentence_count(text)

    def typewrite_narration(self, text: str) -> None:
        delay = self.narration_typing_duration(text) / max(1, len(text))
        self.typewrite_text(text, delay=delay)
        sys.stdout.write("\n")
        sys.stdout.flush()

    def dice_animation_skip_requested(self) -> bool:
        return self.animation_skip_requested(require_animation=True)

    def sleep_for_dice_animation(self, duration: float) -> bool:
        return self.sleep_for_animation(duration, require_animation=True)

    @contextmanager
    def temporary_roll_animation_metadata(self, **metadata):
        effective_metadata = {key: value for key, value in metadata.items() if value is not None}
        if not effective_metadata:
            yield
            return
        sentinel = object()
        previous_values: dict[str, object] = {}
        for key, value in effective_metadata.items():
            attr_name = f"dice_roll_{key}"
            previous_values[attr_name] = getattr(self.rng, attr_name, sentinel)
            setattr(self.rng, attr_name, value)
        try:
            yield
        finally:
            for attr_name, previous in previous_values.items():
                if previous is sentinel:
                    try:
                        delattr(self.rng, attr_name)
                    except AttributeError:
                        pass
                else:
                    setattr(self.rng, attr_name, previous)

    @contextmanager
    def suspend_dice_roll_animation(self):
        sentinel = object()
        previous_animator = getattr(self.rng, "dice_roll_animator", sentinel)
        if previous_animator is sentinel:
            yield
            return
        try:
            delattr(self.rng, "dice_roll_animator")
        except AttributeError:
            pass
        try:
            yield
        finally:
            setattr(self.rng, "dice_roll_animator", previous_animator)

    def roll_with_animation_context(
        self,
        expression: str,
        *,
        bonus: int | None = None,
        critical: bool = False,
        style: str | None = None,
        context_label: str | None = None,
        outcome_kind: str | None = None,
    ):
        metadata: dict[str, object] = {}
        if bonus is not None:
            metadata["display_bonus"] = bonus
        if style is not None:
            metadata["style"] = style
        if context_label is not None:
            metadata["context_label"] = context_label
        if outcome_kind is not None:
            metadata["outcome_kind"] = outcome_kind
        with self.temporary_roll_animation_metadata(**metadata):
            return roll(expression, self.rng, critical=critical)

    def rich_dice_panel_enabled(self) -> bool:
        return (
            self.current_dice_animation_mode() == "full"
            and callable(getattr(self, "emit_rich", None))
            and callable(getattr(self, "rich_text", None))
            and callable(getattr(self, "rich_enabled", None))
            and self.rich_enabled()
            and Columns is not None
            and Group is not None
            and Panel is not None
            and Table is not None
            and Text is not None
            and box is not None
        )

    def dice_animation_theme(self, kind: str, style: str | None) -> tuple[str, str]:
        style_key = style or ("attack" if kind == "d20" else "utility")
        themes = {
            "attack": ("Attack Roll", "light_red"),
            "damage": ("Damage Roll", "light_red"),
            "healing": ("Healing Roll", "light_green"),
            "save": ("Saving Throw", "light_yellow"),
            "skill": ("Skill Check", "light_aqua"),
            "initiative": ("Initiative", "yellow"),
            "utility": ("Dice Roll", "light_yellow"),
        }
        return themes.get(style_key, ("Dice Roll", "light_yellow"))

    def dice_animation_label(
        self,
        kind: str,
        expression: str,
        *,
        style: str | None = None,
        critical: bool,
        advantage_state: int,
    ) -> str:
        if kind == "d20":
            base_label = {
                "attack": "Attack roll",
                "save": "Saving throw",
                "skill": "Skill check",
                "initiative": "Initiative",
            }.get(style or "", "Rolling d20")
            if advantage_state > 0:
                return f"{base_label} (advantage)"
            if advantage_state < 0:
                return f"{base_label} (disadvantage)"
            return base_label
        if style == "damage":
            return "Rolling damage"
        if style == "healing":
            return "Rolling healing"
        if critical:
            return f"Rolling {expression} (critical)"
        return f"Rolling {expression}"

    def dice_animation_final_label(
        self,
        kind: str,
        expression: str,
        *,
        style: str | None = None,
        critical: bool,
        advantage_state: int,
    ) -> str:
        if kind == "d20":
            base_label = {
                "attack": "Attack roll",
                "save": "Saving throw",
                "skill": "Skill check",
                "initiative": "Initiative",
            }.get(style or "", "Rolled d20")
            if advantage_state > 0:
                return f"{base_label} (advantage)"
            if advantage_state < 0:
                return f"{base_label} (disadvantage)"
            return base_label
        if style == "damage":
            return "Damage roll"
        if style == "healing":
            return "Healing roll"
        if critical:
            return f"Rolled {expression} (critical)"
        return f"Rolled {expression}"

    def dice_kept_index(self, rolls: list[int], kept: int | None) -> int | None:
        if kept is None:
            return None
        for index, value in enumerate(rolls):
            if value == kept:
                return index
        return None

    def dice_preview_rolls(
        self,
        final_rolls: list[int],
        *,
        sides: int,
        preview_rng: random.Random,
        progress: float,
    ) -> list[int]:
        if progress <= 0:
            return [preview_rng.randint(1, sides) for _ in final_rolls]
        lock_chance = max(0.0, (progress - 0.58) / 0.42)
        shown: list[int] = []
        for final_value in final_rolls:
            if preview_rng.random() < lock_chance:
                shown.append(final_value)
            else:
                shown.append(preview_rng.randint(1, sides))
        return shown

    def initiative_preview_rolls(
        self,
        final_rolls: list[int],
        *,
        preview_rng: random.Random,
        progress: float,
    ) -> list[int]:
        return self.dice_preview_rolls(final_rolls, sides=20, preview_rng=preview_rng, progress=progress)

    def dice_frame_core(self, kind: str, rolls: list[int], *, kept: int | None = None, final: bool = False) -> str:
        if kind == "d20":
            if len(rolls) == 1:
                return f"Die: {rolls[0]}"
            kept_index = self.dice_kept_index(rolls, kept) if final else None
            lanes: list[str] = []
            for index, value in enumerate(rolls):
                lane = f"Die {chr(65 + index)}: {value}"
                if kept_index == index:
                    lane += " [kept]"
                lanes.append(lane)
            return " | ".join(lanes)
        return " + ".join(str(value) for value in rolls)

    def dice_breakdown_text(self, kind: str, rolls: list[int], *, modifier: int, kept: int | None = None) -> str:
        if kind == "d20":
            base_value = kept if kept is not None else (rolls[-1] if rolls else 0)
        else:
            base_value = sum(rolls)
        if modifier > 0:
            return f"{base_value} + {modifier}"
        if modifier < 0:
            return f"{base_value} - {abs(modifier)}"
        return str(base_value)

    def dice_outcome_details(
        self,
        *,
        kind: str,
        rolls: list[int],
        modifier: int,
        kept: int | None = None,
        target_number: int | None = None,
        style: str | None = None,
        outcome_kind: str | None = None,
        critical: bool = False,
    ) -> tuple[str, str, str | None]:
        if kind == "d20":
            natural = kept if kept is not None else (rolls[-1] if rolls else 0)
            total = natural + modifier
            note: str | None = None
            if natural == 20:
                note = "Natural 20"
            elif natural == 1:
                note = "Natural 1"
            if outcome_kind == "initiative":
                return (f"Ready on {total}", "yellow", note)
            if target_number is not None:
                success = total >= target_number
                if outcome_kind == "attack":
                    if natural == 20:
                        return ("Critical Hit", "yellow", note)
                    if natural == 1:
                        return ("Miss", "light_red", note)
                    return ("Hit" if success else "Miss", "light_green" if success else "light_red", note)
                return ("Success" if success else "Failure", "light_green" if success else "light_red", note)
            if note is not None:
                return (note, "yellow" if natural == 20 else "light_red", None)
            return (f"Total {total}", "light_yellow", None)
        total = sum(rolls) + modifier
        if style == "healing":
            note = "Critical healing roll" if critical else None
            return (f"Restore {total} HP", "light_green", note)
        if style == "damage":
            note = "Critical damage roll" if critical else None
            return (f"{total} damage", "light_red", note)
        return (f"Total {total}", "light_yellow", None)

    def render_dice_result_panel(
        self,
        *,
        kind: str,
        expression: str,
        rolls: list[int],
        modifier: int,
        kept: int | None = None,
        rerolls: list[tuple[int, int]] | None = None,
        target_number: int | None = None,
        target_label: str | None = None,
        context_label: str | None = None,
        style: str | None = None,
        outcome_kind: str | None = None,
        critical: bool = False,
        advantage_state: int = 0,
    ) -> None:
        rerolls = rerolls or []
        total = (kept if kept is not None else sum(rolls)) + modifier
        panel_title, accent_color = self.dice_animation_theme(kind, style)
        panel_heading = context_label or panel_title
        outcome_label, outcome_color, outcome_note = self.dice_outcome_details(
            kind=kind,
            rolls=rolls,
            modifier=modifier,
            kept=kept,
            target_number=target_number,
            style=style,
            outcome_kind=outcome_kind,
            critical=critical,
        )
        breakdown = self.dice_breakdown_text(kind, rolls, modifier=modifier, kept=kept)
        reroll_text = ", ".join(f"{old}->{new}" for old, new in rerolls)

        if self.rich_dice_panel_enabled():
            kept_index = self.dice_kept_index(rolls, kept)
            dice_panels = []
            for index, value in enumerate(rolls):
                die_title = "Kept" if kept_index == index else (f"Die {chr(65 + index)}" if kind == "d20" and len(rolls) > 1 else "Die")
                border = outcome_color if kept_index == index else accent_color
                die_text = Text(str(value), style=f"bold {rich_style_name(border)}", justify="center")
                dice_panels.append(
                    Panel(
                        die_text,
                        title=self.rich_text(die_title, border, bold=True),
                        border_style=rich_style_name(border),
                        box=box.ROUNDED,
                        padding=(0, 2),
                    )
                )
            summary = Table.grid(expand=True, padding=(0, 1))
            summary.add_column(style=f"bold {rich_style_name(accent_color)}", width=10)
            summary.add_column(ratio=1)
            summary.add_row("Roll", self.dice_animation_final_label(kind, expression, style=style, critical=critical, advantage_state=advantage_state))
            summary.add_row("Breakdown", breakdown)
            summary.add_row("Total", str(total))
            if target_number is not None:
                summary.add_row("Target", target_label or str(target_number))
            summary.add_row("Outcome", self.rich_text(outcome_label, outcome_color, bold=True))
            if outcome_note is not None:
                summary.add_row("Note", outcome_note)
            if reroll_text:
                summary.add_row("Reroll", reroll_text)
            rendered = self.emit_rich(
                Panel(
                    Group(Columns(dice_panels, expand=True, equal=True), summary),
                    title=self.rich_text(panel_heading, accent_color, bold=True),
                    border_style=rich_style_name(accent_color),
                    box=box.DOUBLE if kind == "d20" and outcome_kind == "attack" else box.ROUNDED,
                    padding=(0, 1),
                ),
                width=max(96, min(118, self.rich_console_width())),
            )
            if rendered:
                return

        self.output_fn(f"{panel_heading}: {self.dice_frame_core(kind, rolls, kept=kept, final=True)}")
        self.output_fn(f"Total: {total} ({breakdown})")
        if target_number is not None:
            self.output_fn(f"Target: {target_label or target_number}")
        self.output_fn(f"Outcome: {outcome_label}")
        if outcome_note is not None:
            self.output_fn(f"Note: {outcome_note}")
        if reroll_text:
            self.output_fn(f"Reroll: {reroll_text}")

    def initiative_actor_summary_name(self, actor):
        if callable(getattr(self, "rich_from_ansi", None)):
            return self.rich_from_ansi(self.style_name(actor))
        return strip_ansi(self.style_name(actor))

    def initiative_entry_note(self, entry: dict[str, object]) -> str:
        outcome = entry["outcome"]
        kept = getattr(outcome, "kept", 0)
        rerolls = getattr(outcome, "rerolls", [])
        if rerolls:
            reroll_text = ", ".join(f"{old}->{new}" for old, new in rerolls)
            return f"reroll {reroll_text}"
        if kept == 20:
            return "Natural 20"
        if kept == 1:
            return "Natural 1"
        return ""

    def can_render_initiative_panel_animation(self) -> bool:
        return (
            getattr(self, "_interactive_output", False)
            and callable(getattr(sys.stdout, "write", None))
            and Panel is not None
            and Table is not None
            and box is not None
        )

    def build_initiative_panel_lines(
        self,
        entries: list[dict[str, object]],
        *,
        shown_rolls: list[int] | None = None,
        final: bool,
    ) -> list[str]:
        display_rolls = shown_rolls or [getattr(entry["outcome"], "kept", 0) for entry in entries]
        if (
            callable(getattr(self, "rich_enabled", None))
            and self.rich_enabled()
            and callable(getattr(self, "rich_text", None))
        ):
            table = Table(box=box.SIMPLE_HEAVY, expand=True, pad_edge=False)
            table.add_column("#", justify="right", style=f"bold {rich_style_name('yellow')}", width=3)
            table.add_column("Combatant", ratio=2)
            table.add_column("Roll", justify="center", width=6)
            table.add_column("Mod", justify="center", width=6)
            table.add_column("Total", justify="center", style=f"bold {rich_style_name('yellow')}", width=7)
            table.add_column("Status", ratio=2)
            for index, (entry, shown) in enumerate(zip(entries, display_rolls), start=1):
                modifier = int(entry["modifier"])
                if final:
                    total_text = str(entry["total"])
                    status_text = self.initiative_entry_note(entry)
                else:
                    total_text = str(shown + modifier)
                    status_text = "Rolling..."
                table.add_row(
                    str(index),
                    self.initiative_actor_summary_name(entry["actor"]),
                    str(shown),
                    f"{modifier:+d}",
                    total_text,
                    status_text,
                )
            title = "Initiative Order" if final else "Rolling Initiative"
            renderable = Panel(
                table,
                title=self.rich_text(title, "yellow", bold=True),
                border_style=rich_style_name("yellow"),
                box=box.ROUNDED,
                padding=(0, 1),
            )
            return render_rich_lines(
                renderable,
                width=max(96, min(118, self.rich_console_width())),
                force_terminal=getattr(self, "_interactive_output", False),
            )

        lines = ["Initiative Order:" if final else "Rolling Initiative:"]
        for index, (entry, shown) in enumerate(zip(entries, display_rolls), start=1):
            modifier = int(entry["modifier"])
            total_text = entry["total"] if final else shown + modifier
            note = self.initiative_entry_note(entry) if final else "rolling"
            suffix = f" [{note}]" if note else ""
            lines.append(f"{index}. {strip_ansi(self.style_name(entry['actor']))}: {shown}{modifier:+d} = {total_text}{suffix}")
        return lines

    def draw_initiative_panel_lines(self, lines: list[str], *, previous_line_count: int = 0) -> None:
        if previous_line_count > 0:
            sys.stdout.write(f"\x1b[{previous_line_count}F")
        total_lines = max(previous_line_count, len(lines))
        for index in range(total_lines):
            sys.stdout.write("\x1b[2K")
            if index < len(lines):
                sys.stdout.write(lines[index])
            if index < total_lines - 1:
                sys.stdout.write("\n")
        sys.stdout.write("\n")
        sys.stdout.flush()

    def render_initiative_result_panel(self, entries: list[dict[str, object]]) -> None:
        if not entries:
            return
        if (
            callable(getattr(self, "emit_rich", None))
            and callable(getattr(self, "rich_enabled", None))
            and self.rich_enabled()
            and Panel is not None
            and Table is not None
            and box is not None
        ):
            table = Table(box=box.SIMPLE_HEAVY, expand=True, pad_edge=False)
            table.add_column("#", justify="right", style=f"bold {rich_style_name('yellow')}", width=3)
            table.add_column("Combatant", ratio=2)
            table.add_column("Roll", justify="center", width=6)
            table.add_column("Mod", justify="center", width=6)
            table.add_column("Total", justify="center", style=f"bold {rich_style_name('yellow')}", width=7)
            table.add_column("Note", ratio=2)
            for index, entry in enumerate(entries, start=1):
                outcome = entry["outcome"]
                modifier = int(entry["modifier"])
                kept = getattr(outcome, "kept", 0)
                table.add_row(
                    str(index),
                    self.initiative_actor_summary_name(entry["actor"]),
                    str(kept),
                    f"{modifier:+d}",
                    str(entry["total"]),
                    self.initiative_entry_note(entry),
                )
            if self.emit_rich(
                Panel(
                    table,
                    title=self.rich_text("Initiative Order", "yellow", bold=True),
                    border_style=rich_style_name("yellow"),
                    box=box.ROUNDED,
                    padding=(0, 1),
                ),
                width=max(96, min(118, self.rich_console_width())),
            ):
                return

        self.output_fn("Initiative Order:")
        for index, entry in enumerate(entries, start=1):
            actor = self.style_name(entry["actor"])
            outcome = entry["outcome"]
            modifier = int(entry["modifier"])
            note = self.initiative_entry_note(entry)
            suffix = f" [{note}]" if note else ""
            self.output_fn(
                f"{index}. {actor}: {outcome.kept}{modifier:+d} = {entry['total']}{suffix}"
            )

    def animate_initiative_rolls(self, entries: list[dict[str, object]]) -> None:
        if not self.animate_dice or not entries:
            return
        self.begin_animation_skip_scope()
        try:
            can_preview_in_panel = self.can_render_initiative_panel_animation()
            duration = min(
                self._dice_animation_max_seconds + 0.2,
                max(
                    self._dice_animation_min_seconds + 0.08,
                    self._dice_animation_min_seconds + 0.06 * max(0, len(entries) - 1) + 0.16,
                ),
            )
            play_dice_roll_sound = getattr(self, "play_dice_roll_sound", None)
            if callable(play_dice_roll_sound):
                play_dice_roll_sound(duration, cooldown=0.08)
            frames = min(
                max(self._dice_animation_max_frames, 1),
                max(self._dice_animation_min_frames, int(max(1.0, duration) * max(1.0, self._dice_animation_frame_rate))),
            )
            preview_rng = random.Random(time.perf_counter_ns() ^ len(entries) ^ (id(entries) << 1))
            final_rolls = [getattr(entry["outcome"], "kept", 0) for entry in entries]
            weights = [0.16 + ((index / max(1, frames - 1)) ** 3) * 2.75 for index in range(frames)]
            scale = duration / sum(weights)
            rendered_line_count = 0
            for index, delay in enumerate(weights):
                shown = self.initiative_preview_rolls(
                    final_rolls,
                    preview_rng=preview_rng,
                    progress=(index + 1) / max(1, frames),
                )
                if can_preview_in_panel:
                    lines = self.build_initiative_panel_lines(entries, shown_rolls=shown, final=False)
                    self.draw_initiative_panel_lines(lines, previous_line_count=rendered_line_count)
                    rendered_line_count = len(lines)
                if self.sleep_for_dice_animation(delay * scale):
                    break
            if can_preview_in_panel:
                lines = self.build_initiative_panel_lines(entries, shown_rolls=final_rolls, final=True)
                self.draw_initiative_panel_lines(lines, previous_line_count=rendered_line_count)
            else:
                self.render_initiative_result_panel(entries)
            if self._dice_total_reveal_pause_seconds > 0:
                self.sleep_for_animation(self._dice_total_reveal_pause_seconds, require_animation=True)
            if not can_preview_in_panel:
                pass
            if self._dice_animation_final_pause_seconds > 0:
                self.sleep_for_animation(self._dice_animation_final_pause_seconds, require_animation=True)
        finally:
            self.end_animation_skip_scope()

    def animate_dice_roll(
        self,
        *,
        kind: str,
        expression: str,
        sides: int,
        rolls: list[int],
        modifier: int = 0,
        display_modifier: int | None = None,
        critical: bool = False,
        advantage_state: int = 0,
        rerolls: list[tuple[int, int]] | None = None,
        kept: int | None = None,
        target_number: int | None = None,
        target_label: str | None = None,
        context_label: str | None = None,
        style: str | None = None,
        outcome_kind: str | None = None,
    ) -> None:
        if not self.animate_dice or not rolls:
            return
        self.begin_animation_skip_scope()
        try:
            rerolls = rerolls or []
            effective_modifier = modifier if display_modifier is None else display_modifier
            mode = self.current_dice_animation_mode()
            show_total_frame = (
                mode == "full"
                or kind == "d20"
                or effective_modifier != 0
                or len(rolls) > 1
                or style in {"damage", "healing"}
            )
            emphasis = 0.0
            if critical:
                emphasis += 0.18
            if style in {"attack", "damage", "save", "skill"}:
                emphasis += 0.12
            if target_number is not None or advantage_state:
                emphasis += 0.08
            duration = min(
                self._dice_animation_max_seconds,
                max(
                    self._dice_animation_min_seconds,
                    self._dice_animation_min_seconds
                    + 0.14 * max(0, len(rolls) - 1)
                    + (0.12 if advantage_state else 0.0)
                    + emphasis,
                ),
            )
            play_dice_roll_sound = getattr(self, "play_dice_roll_sound", None)
            if callable(play_dice_roll_sound):
                play_dice_roll_sound(duration, cooldown=0.05)
            frames = min(
                self._dice_animation_max_frames,
                max(self._dice_animation_min_frames, int(max(1.0, duration) * max(1.0, self._dice_animation_frame_rate))),
            )
            preview_rng = random.Random(time.perf_counter_ns() ^ id(rolls) ^ (sides << 8))
            label = self.dice_animation_label(
                kind,
                expression,
                style=style,
                critical=critical,
                advantage_state=advantage_state,
            )
            weights = [0.14 + ((index / max(1, frames - 1)) ** 3) * 2.6 for index in range(frames)]
            scale = duration / sum(weights)
            for index, delay in enumerate(weights):
                shown = self.dice_preview_rolls(
                    rolls,
                    sides=sides,
                    preview_rng=preview_rng,
                    progress=(index + 1) / max(1, frames),
                )
                self.render_dice_animation_frame(
                    label,
                    shown,
                    kind=kind,
                    final=False,
                    kept=kept,
                    style=style,
                    outcome_kind=outcome_kind,
                    target_number=target_number,
                    target_label=target_label,
                    context_label=context_label,
                )
                if self.sleep_for_dice_animation(delay * scale):
                    break
            self.render_dice_animation_frame(
                self.dice_animation_final_label(
                    kind,
                    expression,
                    style=style,
                    critical=critical,
                    advantage_state=advantage_state,
                ),
                rolls,
                kind=kind,
                final=True,
                modifier=modifier,
                kept=kept,
                rerolls=rerolls,
                style=style,
                outcome_kind=outcome_kind,
                target_number=target_number,
                target_label=target_label,
                show_total=not show_total_frame,
                context_label=context_label,
            )
            if show_total_frame and self._dice_total_reveal_pause_seconds > 0:
                self.sleep_for_animation(self._dice_total_reveal_pause_seconds, require_animation=True)
            if kind == "d20" and show_total_frame:
                self.render_dice_animation_total_frame(
                    rolls=list(rolls),
                    kept=kept if kept is not None else rolls[-1],
                    modifier=effective_modifier,
                    rerolls=list(rerolls),
                    target_number=target_number,
                    target_label=target_label,
                    context_label=context_label,
                    expression=expression,
                    style=style,
                    outcome_kind=outcome_kind,
                    critical=critical,
                    advantage_state=advantage_state,
                )
            elif show_total_frame:
                self.render_roll_animation_total_frame(
                    rolls=list(rolls),
                    modifier=effective_modifier,
                    rerolls=list(rerolls),
                    context_label=context_label,
                    expression=expression,
                    style=style,
                    outcome_kind=outcome_kind,
                    critical=critical,
                )
            if self._dice_animation_final_pause_seconds > 0:
                self.sleep_for_animation(self._dice_animation_final_pause_seconds, require_animation=True)
        finally:
            self.end_animation_skip_scope()

    def render_dice_animation_frame(
        self,
        label: str,
        rolls: list[int],
        *,
        kind: str = "roll",
        final: bool,
        modifier: int = 0,
        kept: int | None = None,
        rerolls: list[tuple[int, int]] | None = None,
        style: str | None = None,
        outcome_kind: str | None = None,
        target_number: int | None = None,
        target_label: str | None = None,
        show_total: bool = True,
        context_label: str | None = None,
    ) -> None:
        rerolls = rerolls or []
        core = self.dice_frame_core(kind, rolls, kept=kept, final=final)
        text = f"{context_label}: {core}" if context_label else f"{label}: {core}"
        if target_number is not None:
            suffix = target_label or str(target_number)
            text += f" vs {suffix}"
        if final and show_total:
            text += f" | {self.dice_breakdown_text(kind, rolls, modifier=modifier, kept=kept)}"
            if kind == "d20":
                text += f" = {(kept if kept is not None else rolls[-1]) + modifier}"
            else:
                text += f" = {sum(rolls) + modifier}"
        if final and rerolls:
            reroll_text = ", ".join(f"{old}->{new}" for old, new in rerolls)
            text += f" | reroll {reroll_text}"
        visible_length = len(strip_ansi(text))
        padding = max(0, self._dice_animation_width - visible_length)
        sys.stdout.write("\r" + text + (" " * padding))
        if final:
            sys.stdout.write("\n")
            self._dice_animation_width = 0
        else:
            self._dice_animation_width = max(self._dice_animation_width, visible_length)
        sys.stdout.flush()

    def render_dice_animation_total_frame(
        self,
        *,
        rolls: list[int] | None = None,
        kept: int,
        modifier: int,
        rerolls: list[tuple[int, int]] | None = None,
        target_number: int | None = None,
        target_label: str | None = None,
        context_label: str | None = None,
        expression: str = "d20",
        style: str | None = None,
        outcome_kind: str | None = None,
        critical: bool = False,
        advantage_state: int = 0,
    ) -> None:
        self.render_dice_result_panel(
            kind="d20",
            expression=expression,
            rolls=list(rolls or [kept]),
            modifier=modifier,
            kept=kept,
            rerolls=rerolls,
            target_number=target_number,
            target_label=target_label,
            context_label=context_label,
            style=style,
            outcome_kind=outcome_kind,
            critical=critical,
            advantage_state=advantage_state,
        )

    def render_roll_animation_total_frame(
        self,
        *,
        rolls: list[int],
        modifier: int,
        rerolls: list[tuple[int, int]] | None = None,
        context_label: str | None = None,
        expression: str = "roll",
        style: str | None = None,
        outcome_kind: str | None = None,
        critical: bool = False,
    ) -> None:
        self.render_dice_result_panel(
            kind="roll",
            expression=expression,
            rolls=list(rolls),
            modifier=modifier,
            rerolls=rerolls,
            context_label=context_label,
            style=style,
            outcome_kind=outcome_kind,
            critical=critical,
        )

    def ensure_state_integrity(self) -> None:
        if self.state is None:
            return
        self.state.inventory = dict(self.state.inventory)
        self.state.short_rests_remaining = max(0, self.state.short_rests_remaining)
        ensure_quest_log = getattr(self, "ensure_quest_log", None)
        if callable(ensure_quest_log):
            ensure_quest_log()
        for member in [self.state.player, *self.state.all_companions()]:
            if not member.equipment_slots:
                member.equipment_slots = {slot: None for slot in EQUIPMENT_SLOTS}
                starter_slots = starter_item_ids_for_character(member)
                for slot, item_id in starter_slots.items():
                    member.equipment_slots[slot] = item_id
                    if item_id is not None:
                        self.state.inventory[item_id] = self.state.inventory.get(item_id, 0) + 1
            self.normalize_member_equipment_slots(member)
            for legacy_name, quantity in list(member.inventory.items()):
                item_id = LEGACY_ITEM_NAMES.get(legacy_name)
                if item_id is None:
                    continue
                self.state.inventory[item_id] = self.state.inventory.get(item_id, 0) + quantity
            member.inventory.clear()
            self.reconcile_level_progression(member)
            self.sync_equipment(member)
            self.rebuild_story_skill_bonuses(member)
            refresh_companion_state = getattr(self, "refresh_companion_state", None)
            if callable(refresh_companion_state):
                refresh_companion_state(member)

    def get_merchant_stock(self, merchant_id: str) -> dict[str, int]:
        assert self.state is not None
        merchant_stocks = self.state.flags.setdefault("merchant_stocks", {})
        if merchant_id not in merchant_stocks:
            merchant_stocks[merchant_id] = initial_merchant_stock(merchant_id, rng=self.rng)
        stock = merchant_stocks[merchant_id]
        for item_id in list(stock):
            if stock[item_id] <= 0:
                stock.pop(item_id, None)
        return stock

    def get_merchant_attitude(self, merchant_id: str) -> int:
        assert self.state is not None
        attitudes = self.state.flags.setdefault("merchant_attitudes", {})
        if merchant_id not in attitudes:
            attitudes[merchant_id] = self.MERCHANT_ATTITUDE_DEFAULTS.get(merchant_id, 0)
        attitudes[merchant_id] = max(0, min(100, int(attitudes[merchant_id])))
        return attitudes[merchant_id]

    def adjust_merchant_attitude(self, merchant_id: str, amount: int, *, reason: str = "") -> int:
        assert self.state is not None
        updated = max(0, min(100, self.get_merchant_attitude(merchant_id) + amount))
        self.state.flags.setdefault("merchant_attitudes", {})[merchant_id] = updated
        if amount and reason:
            direction = "improves" if amount > 0 else "drops"
            self.say(f"{reason} {direction} their attitude to {updated}/100.")
        return updated

    def trade_negotiator(self) -> Character:
        assert self.state is not None
        party = self.state.party_members()
        return max(
            party,
            key=lambda member: (
                member.skill_bonus("Persuasion"),
                1 if member is self.state.player else 0,
                member.ability_mod("CHA"),
            ),
        )

    def trade_persuasion(self) -> int:
        return self.trade_negotiator().skill_bonus("Persuasion")

    def buy_price_multiplier(self, merchant_id: str) -> float:
        persuasion = self.trade_persuasion()
        attitude = self.get_merchant_attitude(merchant_id)
        return max(1.0, 2.5 - (0.1 * persuasion) - (0.005 * attitude))

    def sell_price_multiplier(self, merchant_id: str) -> float:
        return 1.0 / self.buy_price_multiplier(merchant_id)

    def merchant_buy_price(self, merchant_id: str, item_id: str) -> int:
        return max(1, int(ITEMS[item_id].value * self.buy_price_multiplier(merchant_id) + 0.5))

    def merchant_sell_price(self, merchant_id: str, item_id: str) -> int:
        return max(1, int(ITEMS[item_id].value / self.buy_price_multiplier(merchant_id) + 0.5))

    def merchant_trade_summary(self, merchant_id: str, merchant_name: str) -> str:
        negotiator = self.trade_negotiator()
        return (
            f"Trade terms with {merchant_name}: face {negotiator.name} "
            f"(Persuasion +{negotiator.skill_bonus('Persuasion')}), attitude {self.get_merchant_attitude(merchant_id)}/100, "
            f"buy x{self.buy_price_multiplier(merchant_id):.2f}, sell x{self.sell_price_multiplier(merchant_id):.2f}."
        )

    def normalize_member_equipment_slots(self, member: Character) -> None:
        normalized = {slot: None for slot in EQUIPMENT_SLOTS}
        for raw_slot, item_id in dict(member.equipment_slots or {}).items():
            if item_id is None:
                continue
            slot = canonical_equipment_slot(raw_slot)
            if slot == "ring":
                slot = "ring_1" if normalized["ring_1"] is None else "ring_2"
            if slot not in normalized:
                continue
            if slot in {"ring_1", "ring_2"} and normalized[slot] is not None:
                fallback = "ring_2" if slot == "ring_1" else "ring_1"
                if normalized[fallback] is None:
                    slot = fallback
                else:
                    continue
            normalized[slot] = item_id
        member.equipment_slots = normalized

    def sync_equipment(self, member: Character) -> None:
        member.gear_bonuses = {}
        member.shield = False
        if not member.equipment_slots:
            member.equipment_slots = {slot: None for slot in EQUIPMENT_SLOTS}
        self.normalize_member_equipment_slots(member)
        for slot in EQUIPMENT_SLOTS:
            member.equipment_slots.setdefault(slot, None)
        main_hand_id = member.equipment_slots.get("main_hand")
        if main_hand_id is not None and main_hand_id in ITEMS and ITEMS[main_hand_id].weapon is not None:
            member.weapon = ITEMS[main_hand_id].weapon
            if member.weapon.hands_required >= 2:
                member.equipment_slots["off_hand"] = None
        else:
            member.weapon = Weapon(name="Unarmed Strike", damage="1d1", ability="STR")
        chest_id = member.equipment_slots.get("chest")
        if chest_id is not None and chest_id in ITEMS and ITEMS[chest_id].armor is not None:
            member.armor = ITEMS[chest_id].armor
        else:
            member.armor = None

        off_hand_id = member.equipment_slots.get("off_hand")
        if off_hand_id is not None and off_hand_id in ITEMS:
            off_hand_item = ITEMS[off_hand_id]
            if off_hand_item.shield_bonus and member.weapon.hands_required == 1:
                member.shield = True
                member.gear_bonuses["AC"] = member.gear_bonuses.get("AC", 0) + max(0, off_hand_item.shield_bonus - 2)
            elif off_hand_item.weapon is not None and member.weapon.hands_required == 1 and off_hand_item.weapon.hands_required == 1:
                pass
            else:
                member.equipment_slots["off_hand"] = None

        for slot in EQUIPMENT_SLOTS:
            item_id = member.equipment_slots.get(slot)
            if item_id is None or item_id not in ITEMS:
                continue
            item = ITEMS[item_id]
            for skill, bonus in (item.skill_bonuses or {}).items():
                member.gear_bonuses[skill] = member.gear_bonuses.get(skill, 0) + bonus
            for save_key, bonus in (item.save_bonuses or {}).items():
                member.gear_bonuses[save_key] = member.gear_bonuses.get(save_key, 0) + bonus
            if item.ac_bonus:
                member.gear_bonuses["AC"] = member.gear_bonuses.get("AC", 0) + item.ac_bonus
            if item.attack_bonus:
                member.gear_bonuses["attack"] = member.gear_bonuses.get("attack", 0) + item.attack_bonus
            if item.damage_bonus:
                member.gear_bonuses["damage"] = member.gear_bonuses.get("damage", 0) + item.damage_bonus
            if item.initiative_bonus:
                member.gear_bonuses["initiative"] = member.gear_bonuses.get("initiative", 0) + item.initiative_bonus
            if item.spell_attack_bonus:
                member.gear_bonuses["spell_attack"] = member.gear_bonuses.get("spell_attack", 0) + item.spell_attack_bonus
            if item.spell_damage_bonus:
                member.gear_bonuses["spell_damage"] = member.gear_bonuses.get("spell_damage", 0) + item.spell_damage_bonus
            if item.healing_bonus:
                member.gear_bonuses["healing_received"] = member.gear_bonuses.get("healing_received", 0) + item.healing_bonus
            if item.stealth_advantage:
                member.gear_bonuses["stealth_advantage"] = 1
            if item.crit_immunity:
                member.gear_bonuses["crit_immunity"] = 1
            for damage_type in item.damage_resistances or []:
                member.gear_bonuses[f"resist_{damage_type}"] = 1

    def handle_meta_command(self, raw: str) -> bool:
        lowered = raw.lower()
        if lowered == "load":
            if self.open_save_files_menu():
                self._compact_hud_last_scene_key = None
                raise ResumeLoadedGame()
            return True
        if lowered in {"saves", "save files"}:
            if self.open_save_files_menu():
                self._compact_hud_last_scene_key = None
                raise ResumeLoadedGame()
            return True
        if lowered == "quit":
            if getattr(self, "_at_title_screen", False):
                if self.confirm("Quit the program and close the main menu?"):
                    raise QuitProgram()
                self.say("You remain at the main menu.")
                return True
            if self.confirm("Return to the main menu? Unsaved progress since your last save will be lost."):
                self.state = None
                self._compact_hud_last_scene_key = None
                raise ReturnToTitleMenu()
            self.say("You stay with the current adventure.")
            return True
        if lowered == "help":
            self.show_global_commands()
            return True
        if lowered == "dev":
            if self.open_developer_tools_menu():
                self._compact_hud_last_scene_key = None
                raise ResumeLoadedGame()
            return True
        if lowered == "settings":
            self.open_settings_menu()
            return True
        if lowered == "save":
            self.inline_save()
            return True
        if lowered == "party":
            if self.state is None:
                self.say("There is no active party to review yet.")
            else:
                self.show_party()
            return True
        if lowered == "journal":
            if self.state is None:
                self.say("There is no active journal yet.")
            else:
                self.show_journal()
            return True
        if lowered in {"inventory", "backpack", "bag"}:
            if self.state is None:
                self.say("There is no shared inventory yet.")
            else:
                self.manage_inventory()
            return True
        if lowered in {"equipment", "gear"}:
            if self.state is None:
                self.say("There is no active party gear to manage yet.")
            elif self._in_combat:
                self.say("You cannot reorganize equipment in the middle of combat.")
            else:
                self.manage_equipment()
            return True
        if lowered in {"sheet", "sheets", "character", "characters"}:
            if self.state is None:
                self.say("There is no active party to inspect yet.")
            elif self._in_combat:
                self.say("Use `party` for quick combat status. Full character sheets are only available out of combat.")
            else:
                self.show_character_sheets()
            return True
        if lowered == "camp":
            if self.state is None:
                self.say("There is no active adventure yet, so camp is not available.")
            elif self._in_combat:
                self.say("You cannot head to camp during combat.")
            else:
                self.open_camp_menu()
            return True
        return False

    def is_party_member_actor(self, actor) -> bool:
        if self.state is None:
            return False
        return any(member is actor for member in self.state.party_members())

    def is_player_actor(self, actor) -> bool:
        return self.state is not None and actor is self.state.player

    def story_skill_modifier_payloads(self, actor: Character) -> dict[str, dict[str, object]]:
        raw_modifiers = actor.bond_flags.get(self.STORY_SKILL_MODIFIER_KEY)
        if not isinstance(raw_modifiers, dict):
            raw_modifiers = {}
        normalized: dict[str, dict[str, object]] = {}
        for modifier_id, raw_payload in raw_modifiers.items():
            if not isinstance(modifier_id, str) or not isinstance(raw_payload, dict):
                continue
            bonuses_payload = raw_payload.get("bonuses") if "bonuses" in raw_payload else raw_payload
            if not isinstance(bonuses_payload, dict):
                continue
            bonuses: dict[str, int] = {}
            for skill, value in bonuses_payload.items():
                if not isinstance(skill, str) or skill not in SKILL_TO_ABILITY:
                    continue
                try:
                    amount = int(value)
                except (TypeError, ValueError):
                    continue
                if amount:
                    bonuses[skill] = amount
            if not bonuses:
                continue
            normalized[modifier_id] = {
                "bonuses": bonuses,
                "source": str(raw_payload.get("source") or modifier_id),
                "duration": str(raw_payload.get("duration") or ""),
            }
        actor.bond_flags[self.STORY_SKILL_MODIFIER_KEY] = normalized
        return normalized

    def rebuild_story_skill_bonuses(self, actor: Character) -> None:
        totals: dict[str, int] = {}
        for payload in self.story_skill_modifier_payloads(actor).values():
            bonuses = payload.get("bonuses", {})
            if not isinstance(bonuses, dict):
                continue
            for skill, value in bonuses.items():
                if isinstance(skill, str) and skill in SKILL_TO_ABILITY:
                    totals[skill] = totals.get(skill, 0) + int(value)
        actor.story_skill_bonuses = totals

    def apply_story_skill_modifier(
        self,
        actor: Character,
        modifier_id: str,
        bonuses: dict[str, int],
        *,
        source: str,
        duration: str,
    ) -> bool:
        clean_bonuses: dict[str, int] = {}
        for skill, amount in bonuses.items():
            if skill not in SKILL_TO_ABILITY:
                continue
            try:
                numeric_amount = int(amount)
            except (TypeError, ValueError):
                continue
            if numeric_amount:
                clean_bonuses[skill] = numeric_amount
        if not clean_bonuses:
            return self.remove_story_skill_modifier(actor, modifier_id)
        modifiers = self.story_skill_modifier_payloads(actor)
        previous = modifiers.get(modifier_id)
        modifiers[modifier_id] = {"bonuses": clean_bonuses, "source": source, "duration": duration}
        actor.bond_flags[self.STORY_SKILL_MODIFIER_KEY] = modifiers
        self.rebuild_story_skill_bonuses(actor)
        return previous != modifiers[modifier_id]

    def remove_story_skill_modifier(self, actor: Character, modifier_id: str) -> bool:
        modifiers = self.story_skill_modifier_payloads(actor)
        if modifier_id not in modifiers:
            return False
        modifiers.pop(modifier_id, None)
        actor.bond_flags[self.STORY_SKILL_MODIFIER_KEY] = modifiers
        self.rebuild_story_skill_bonuses(actor)
        return True

    def has_story_skill_modifier(self, actor: Character, modifier_id: str) -> bool:
        return modifier_id in self.story_skill_modifier_payloads(actor)

    def story_skill_modifier_display_lines(self, actor: Character) -> list[str]:
        lines: list[str] = []
        for modifier_id, payload in sorted(self.story_skill_modifier_payloads(actor).items()):
            bonuses = payload.get("bonuses", {})
            if not isinstance(bonuses, dict):
                continue
            bonus_parts = [
                f"{skill} {int(amount):+d}"
                for skill, amount in sorted(bonuses.items())
                if isinstance(skill, str) and skill in SKILL_TO_ABILITY and int(amount) != 0
            ]
            if not bonus_parts:
                continue
            source = str(payload.get("source") or modifier_id)
            duration = str(payload.get("duration") or "").strip()
            suffix = f" ({duration})" if duration else ""
            lines.append(f"{source}: {', '.join(bonus_parts)}{suffix}")
        return lines

    def story_skill_modifier_summary(self, actor: Character) -> str:
        lines = self.story_skill_modifier_display_lines(actor)
        return "; ".join(lines) if lines else "None"

    def apply_liars_blessing(self) -> None:
        assert self.state is not None
        player = self.state.player
        self.remove_story_skill_modifier(player, self.LIARS_CURSE_MODIFIER_ID)
        changed = self.apply_story_skill_modifier(
            player,
            self.LIARS_BLESSING_MODIFIER_ID,
            {"Deception": 2, "Persuasion": 1},
            source="Liar's Blessing",
            duration="until death",
        )
        self.state.flags["liars_blessing_active"] = True
        self.state.flags["liars_curse_active"] = False
        if changed:
            self.say("The answer settles on your tongue as Liar's Blessing: +2 Deception and +1 Persuasion until death.")
            self.add_journal("Liar's Blessing grants +2 Deception and +1 Persuasion until death.")

    def apply_liars_curse(self) -> None:
        assert self.state is not None
        player = self.state.player
        self.remove_story_skill_modifier(player, self.LIARS_BLESSING_MODIFIER_ID)
        changed = self.apply_story_skill_modifier(
            player,
            self.LIARS_CURSE_MODIFIER_ID,
            {"Deception": -1, "Persuasion": -1},
            source="Liar's Curse",
            duration="until long rest",
        )
        self.state.flags["liars_blessing_active"] = False
        self.state.flags["liars_curse_active"] = True
        if changed:
            self.say("The statues' laughter leaves Liar's Curse behind: -1 Deception and -1 Persuasion until your next long rest.")
            self.add_journal("Liar's Curse imposes -1 Deception and -1 Persuasion until the next long rest.")

    def clear_liars_curse_after_long_rest(self) -> bool:
        if self.state is None:
            return False
        cleared = self.remove_story_skill_modifier(self.state.player, self.LIARS_CURSE_MODIFIER_ID)
        if cleared or self.state.flags.get("liars_curse_active"):
            self.state.flags["liars_curse_active"] = False
            self.say("By morning, Liar's Curse has thinned from your voice.")
            self.add_journal("A long rest cleared Liar's Curse.")
        return cleared

    def clear_liars_blessing_on_player_death(self) -> bool:
        if self.state is None or not self.state.player.dead:
            return False
        cleared = self.remove_story_skill_modifier(self.state.player, self.LIARS_BLESSING_MODIFIER_ID)
        if cleared or self.state.flags.get("liars_blessing_active"):
            self.state.flags["liars_blessing_active"] = False
            self.state.flags["liars_blessing_lost_to_death"] = True
            self.say("Liar's Blessing goes silent as death closes around you.")
            self.add_journal("Death ended Liar's Blessing.")
        return cleared

    def developer_flag_enabled(self, flag_key: str) -> bool:
        if self.state is None:
            return False
        return bool(self.state.flags.get(flag_key, False))

    def god_mode_enabled(self) -> bool:
        return self.developer_flag_enabled(self.DEV_GOD_MODE_FLAG)

    def always_pass_dice_checks_enabled(self) -> bool:
        return self.developer_flag_enabled(self.DEV_PASS_CHECKS_FLAG)

    def set_developer_flag(self, flag_key: str, enabled: bool) -> None:
        assert self.state is not None
        self.state.flags[flag_key] = bool(enabled)

    def toggle_god_mode(self) -> bool:
        assert self.state is not None
        enabled = not self.god_mode_enabled()
        self.set_developer_flag(self.DEV_GOD_MODE_FLAG, enabled)
        if enabled:
            for member in self.state.party_members():
                if member.dead:
                    continue
                if member.current_hp <= 0:
                    member.current_hp = 1
                    member.stable = False
                    member.death_successes = 0
                    member.death_failures = 0
        self.say(f"God mode for the party is now {'ON' if enabled else 'OFF'}.")
        return enabled

    def toggle_pass_every_dice_check(self) -> bool:
        assert self.state is not None
        enabled = not self.always_pass_dice_checks_enabled()
        self.set_developer_flag(self.DEV_PASS_CHECKS_FLAG, enabled)
        self.say(f"Pass every player dice check is now {'ON' if enabled else 'OFF'}.")
        return enabled

    def add_developer_gold(self, amount: int = 10_000) -> int:
        assert self.state is not None
        self.state.gold += amount
        self.say(f"Developer tools add {amount:,} gp. Total gold: {self.state.gold:,} gp.")
        return self.state.gold

    def level_up_party_instantly(self, *, target_level: int | None = None, randomize_skill_choices: bool = True) -> int | None:
        assert self.state is not None
        max_level = max(LEVEL_XP_THRESHOLDS)
        desired_level = target_level if target_level is not None else self.state.player.level + 1
        desired_level = max(1, min(desired_level, max_level))
        company = [self.state.player, *self.state.all_companions()]
        if all(member.level >= desired_level for member in company):
            if desired_level >= max_level:
                self.say(f"The company is already at the maximum implemented level ({max_level}).")
            else:
                self.say(f"The company is already at level {desired_level} or higher.")
            return None
        self.state.xp = max(self.state.xp, LEVEL_XP_THRESHOLDS[desired_level])
        for member in company:
            for next_level in range(member.level + 1, desired_level + 1):
                self.level_up_character_automatically(
                    member,
                    next_level,
                    randomize_skill_choice=randomize_skill_choices,
                )
        self.ensure_state_integrity()
        self.say(f"The company is now level {desired_level}.")
        return desired_level

    def reset_party_for_developer_snapshot(self) -> None:
        assert self.state is not None
        for member in self.state.party_members():
            member.reset_for_rest()
        self.state.short_rests_remaining = 2
        self._in_combat = False

    def jump_to_act2_developer_start(self) -> bool:
        if self.state is None:
            self.say("Start or load an adventure before jumping to the Act II test snapshot.")
            return False
        if self._in_combat:
            self.say("Finish or leave combat before rebuilding the run into the Act II test snapshot.")
            return False
        if not self.confirm(
            "Reset this run into a level 4 Act II test start? Current scene progress, quest state, journal, and roster setup will be replaced."
        ):
            self.say("The current run stays where it is.")
            return False

        preserved_flags = {
            self.DEV_GOD_MODE_FLAG: self.god_mode_enabled(),
            self.DEV_PASS_CHECKS_FLAG: self.always_pass_dice_checks_enabled(),
        }
        self.state.companions = []
        self.state.camp_companions = []
        self.state.flags = {
            "act1_started": True,
            "briefing_seen": True,
            "phandalin_council_seen": True,
            "steward_vow_made": True,
            "miners_exchange_dispute_resolved": True,
            "miners_exchange_ledgers_checked": True,
            "elira_helped": True,
            **preserved_flags,
        }
        self.state.completed_acts = [1]
        self.state.clues = []
        self.state.journal = [
            "You broke the Ashen Brand and secured Phandalin through the end of Act 1.",
        ]
        self.state.quests = {}

        for factory in (create_bryn_underbough, create_elira_dawnmantle, create_tolan_ironshield):
            self.recruit_companion(factory())

        self.level_up_party_instantly(target_level=4, randomize_skill_choices=True)
        self.reset_party_for_developer_snapshot()
        self.start_act2_scaffold()
        self.ensure_state_integrity()
        self._compact_hud_last_scene_key = None
        refresh_scene_music = getattr(self, "refresh_scene_music", None)
        if callable(refresh_scene_music):
            refresh_scene_music()
        self.say("Developer snapshot loaded: Act II begins with Bryn, Elira, and Tolan at level 4.")
        return True

    def open_developer_tools_menu(self) -> bool:
        if self.state is None:
            self.say("Start or load an adventure before using developer tools.")
            return False
        while True:
            self.banner("Developer Tools")
            self.say("These tools affect the current run immediately and any save made afterward will keep the changes.")
            options = [
                f"Toggle god mode for the party [{'ON' if self.god_mode_enabled() else 'OFF'}]",
                f"Toggle pass every dice check [{'ON' if self.always_pass_dice_checks_enabled() else 'OFF'}]",
                "Add 10,000 gp instantly",
                "Level up the company instantly",
                "Jump to the start of Act II with a level 4 test company",
                "Back",
            ]
            choice = self.choose("Choose a developer tool.", options, allow_meta=False, show_hud=False)
            if choice == 1:
                self.toggle_god_mode()
            elif choice == 2:
                self.toggle_pass_every_dice_check()
            elif choice == 3:
                self.add_developer_gold()
            elif choice == 4:
                self.level_up_party_instantly()
            elif choice == 5:
                if self.jump_to_act2_developer_start():
                    return True
            else:
                return False

    def show_global_commands(self) -> None:
        commands = [
            ("help", "Show the list of global commands and what they do."),
            ("dev", "Open developer tools for debug toggles, instant leveling, and the Act II test snapshot."),
            ("settings", "Open the settings menu for audio and presentation toggles."),
            ("save", "Save the current run to a named slot."),
            ("load", "Load another save slot immediately and continue from there."),
            ("saves / save files", "Open the Save Files manager to load or delete save slots."),
            ("quit", "Return to the main menu, or close the program if you are already there."),
            ("map / maps / map menu", "Open the map menu, including Travel Ledger, overworld, and current-site views when available."),
            ("party", "Review quick party combat stats, statuses, and roster state."),
            ("journal", "Open the journal and clues log."),
            ("inventory / backpack / bag", "Open the shared inventory and item management view."),
            ("equipment / gear", "Open the full equipment manager for any company member."),
            ("sheet / sheets", "Open full character sheets for the company."),
            ("camp", "Open camp when you are not in combat."),
        ]
        if self.should_use_rich_ui() and Group is not None and Panel is not None and Table is not None and box is not None:
            table = Table(box=box.SIMPLE_HEAVY, expand=True, pad_edge=False)
            table.add_column("Command", style=f"bold {rich_style_name('light_yellow')}", width=24)
            table.add_column("Use", ratio=1)
            for command, description in commands:
                table.add_row(self.rich_text(command, "light_yellow", bold=True), description)
            guidance = self.rich_text(
                "Type any of these at most prompts. `map`, `maps`, and `map menu` all open the same map menu.",
                "cyan",
            )
            if self.emit_rich(
                Panel(
                    Group(table, guidance),
                    title=self.rich_text("Global Commands", "light_yellow", bold=True),
                    border_style=rich_style_name("light_yellow"),
                    box=box.ROUNDED,
                    padding=(0, 1),
                )
            ):
                self.output_fn("")
                return
        self.banner("Global Commands")
        self.say("These commands can be typed at most prompts.")
        for command, description in commands:
            self.output_fn(f"- {command}: {description}")

    def refresh_presentation_bundle_preference(self) -> None:
        self._animations_and_delays_preference = bool(
            getattr(self, "_dice_animations_preference", self.animate_dice)
            and getattr(self, "_typed_dialogue_preference", self.type_dialogue)
            and getattr(self, "_pacing_pauses_preference", self.pace_output)
            and getattr(self, "_staggered_reveals_preference", getattr(self, "staggered_reveals_enabled", False))
        )

    def apply_dice_animation_preference(self) -> None:
        self.apply_dice_animation_mode_profile()
        if self.animate_dice:
            try:
                setattr(self.rng, "dice_roll_animator", self.animate_dice_roll)
            except Exception:
                self.animate_dice = False
                self._dice_animation_mode_preference = "off"
                self._dice_animations_preference = False
                self.apply_dice_animation_mode_profile()
        else:
            try:
                delattr(self.rng, "dice_roll_animator")
            except AttributeError:
                pass

    def apply_typed_dialogue_preference(self) -> None:
        self.type_dialogue = bool(getattr(self, "_typed_dialogue_preference", self.type_dialogue) and self.output_fn is print)

    def apply_pacing_preference(self) -> None:
        self.pace_output = bool(getattr(self, "_pacing_pauses_preference", self.pace_output))

    def apply_staggered_reveal_preference(self) -> None:
        self.staggered_reveals_enabled = bool(
            getattr(self, "_staggered_reveals_preference", getattr(self, "staggered_reveals_enabled", False))
        )

    def set_dice_animations_enabled(self, enabled: bool) -> None:
        self.set_dice_animation_mode("full" if enabled else "off")

    def toggle_dice_animations(self) -> None:
        self.set_dice_animations_enabled(not getattr(self, "_dice_animations_preference", self.animate_dice))

    def set_dice_animation_mode(self, mode: str) -> None:
        selected = mode if mode in self.DICE_ANIMATION_MODES else "off"
        self._dice_animation_mode_preference = selected
        self._dice_animations_preference = selected != "off"
        self.apply_dice_animation_preference()
        self.refresh_presentation_bundle_preference()
        self.persist_settings()
        self.say(f"Dice animation style set to {self.dice_animation_mode_label(selected)}.")

    def open_dice_animation_settings(self) -> None:
        while True:
            options = [
                f"Off ({'Current' if self.current_dice_animation_mode() == 'off' else 'Set'})",
                f"Minimal ({'Current' if self.current_dice_animation_mode() == 'minimal' else 'Set'})",
                f"Full ({'Current' if self.current_dice_animation_mode() == 'full' else 'Set'})",
                "Back",
            ]
            choice = self.choose("Dice animation style", options, allow_meta=False)
            if choice == 4:
                return
            self.set_dice_animation_mode(self.DICE_ANIMATION_MODES[choice - 1])
            return

    def set_typed_dialogue_enabled(self, enabled: bool) -> None:
        self._typed_dialogue_preference = bool(enabled)
        self.apply_typed_dialogue_preference()
        self.refresh_presentation_bundle_preference()
        self.persist_settings()
        state_label = "enabled" if self.type_dialogue else "disabled"
        self.say(f"Typed dialogue and narration {state_label}.")

    def toggle_typed_dialogue(self) -> None:
        self.set_typed_dialogue_enabled(not getattr(self, "_typed_dialogue_preference", self.type_dialogue))

    def set_pacing_pauses_enabled(self, enabled: bool) -> None:
        self._pacing_pauses_preference = bool(enabled)
        self.apply_pacing_preference()
        self.refresh_presentation_bundle_preference()
        self.persist_settings()
        self.say("Pacing pauses enabled." if self.pace_output else "Pacing pauses disabled.")

    def toggle_pacing_pauses(self) -> None:
        self.set_pacing_pauses_enabled(not getattr(self, "_pacing_pauses_preference", self.pace_output))

    def set_staggered_reveals_enabled(self, enabled: bool) -> None:
        self._staggered_reveals_preference = bool(enabled)
        self.apply_staggered_reveal_preference()
        self.refresh_presentation_bundle_preference()
        self.persist_settings()
        state_label = "enabled" if self.staggered_reveals_enabled else "disabled"
        self.say(f"Staggered option reveals {state_label}.")

    def toggle_staggered_reveals(self) -> None:
        self.set_staggered_reveals_enabled(
            not getattr(self, "_staggered_reveals_preference", getattr(self, "staggered_reveals_enabled", False))
        )

    def set_animations_and_delays_enabled(self, enabled: bool) -> None:
        self._dice_animation_mode_preference = "full" if enabled else "off"
        self._dice_animations_preference = bool(enabled)
        self._typed_dialogue_preference = bool(enabled)
        self._pacing_pauses_preference = bool(enabled)
        self._staggered_reveals_preference = bool(enabled)
        self.apply_dice_animation_preference()
        self.apply_typed_dialogue_preference()
        self.apply_pacing_preference()
        self.apply_staggered_reveal_preference()
        self.refresh_presentation_bundle_preference()
        self.persist_settings()
        self.say("Animations and delays enabled." if enabled else "Animations and delays disabled.")

    def toggle_animations_and_delays(self) -> None:
        self.set_animations_and_delays_enabled(
            not bool(
                getattr(self, "_dice_animations_preference", self.animate_dice)
                and getattr(self, "_typed_dialogue_preference", self.type_dialogue)
                and getattr(self, "_pacing_pauses_preference", self.pace_output)
                and getattr(self, "_staggered_reveals_preference", getattr(self, "staggered_reveals_enabled", False))
            )
        )

    def settings_toggle_label(self, enabled: bool, *, unavailable: bool = False) -> str:
        if unavailable:
            return "Unavailable"
        return "On" if enabled else "Off"

    def open_settings_menu(self) -> None:
        while True:
            music_available = bool(getattr(self, "_music_assets_ready", False))
            options = [
                f"Toggle sound effects ({self.settings_toggle_label(getattr(self, 'sound_effects_enabled', False))})",
                (
                    f"Toggle music ({self.settings_toggle_label(getattr(self, 'music_enabled', False), unavailable=not music_available)})"
                ),
                f"Dice animation style ({self.dice_animation_mode_label()})",
                f"Toggle typed dialogue and narration ({self.settings_toggle_label(getattr(self, '_typed_dialogue_preference', self.type_dialogue))})",
                f"Toggle pacing pauses ({self.settings_toggle_label(getattr(self, '_pacing_pauses_preference', self.pace_output))})",
                f"Toggle staggered option reveals ({self.settings_toggle_label(getattr(self, '_staggered_reveals_preference', getattr(self, 'staggered_reveals_enabled', False)))})",
                "Back",
            ]
            choice = self.choose("Settings", options, allow_meta=False)
            if choice == 1:
                toggle_sound_effects = getattr(self, "toggle_sound_effects", None)
                if callable(toggle_sound_effects):
                    toggle_sound_effects()
                else:
                    self.say("Sound effects are not supported in this build.")
                continue
            if choice == 2:
                toggle_music = getattr(self, "toggle_music", None)
                if callable(toggle_music):
                    toggle_music()
                else:
                    self.say("Music playback is not supported in this build.")
                continue
            if choice == 3:
                self.open_dice_animation_settings()
                continue
            if choice == 4:
                self.toggle_typed_dialogue()
                continue
            if choice == 5:
                self.toggle_pacing_pauses()
                continue
            if choice == 6:
                self.toggle_staggered_reveals()
                continue
            return

    def emit_dialogue_line(self, speaker_name: str, text: str, *, color: str, typed: bool = True) -> None:
        styled_name = self.style_text(speaker_name, color)
        if typed and self.type_dialogue:
            self.typewrite_dialogue_line(styled_name, text)
            return
        self.output_fn("")
        self.say(f'{styled_name}: "{text}"')
        self.output_fn("")

    def speaker(self, name: str, text: str) -> None:
        self.introduce_character(name)
        self.emit_dialogue_line(name, text, color="green", typed=True)

    def player_speaker(self, text: str) -> None:
        speaker_name = self.state.player.name if self.state is not None else "You"
        self.emit_dialogue_line(speaker_name, text, color="blue", typed=False)
        self.pause_for_choice_resolution()

    def player_action(self, text: str) -> None:
        cleaned = text.strip()
        if cleaned.startswith("*"):
            cleaned = cleaned[1:].strip()
        self.say(self.action_option(cleaned))
        self.output_fn("")
        self.pause_for_choice_resolution()

    def player_choice_output(self, text: str) -> None:
        cleaned = self.choice_text(text).strip()
        if cleaned.startswith("*"):
            self.player_action(cleaned)
        else:
            self.player_speaker(cleaned.strip('"'))

    def should_introduce_character(self, subject) -> bool:
        if self.state is None:
            return False
        name = subject.name if hasattr(subject, "name") else str(subject)
        seen = set(self.state.flags.get("introduced_characters", []))
        return name not in seen

    def mark_character_introduced(self, name: str) -> None:
        assert self.state is not None
        seen = set(self.state.flags.get("introduced_characters", []))
        if name in seen:
            return
        seen.add(name)
        self.state.flags["introduced_characters"] = sorted(seen)

    def character_intro_text(self, subject) -> str:
        if hasattr(subject, "name"):
            name = subject.name
            if name in self.NAMED_CHARACTER_INTROS:
                return self.NAMED_CHARACTER_INTROS[name]
            notes = list(getattr(subject, "notes", []))
            if notes:
                return notes[0]
            if getattr(subject, "tags", None) and "leader" in subject.tags:
                return (
                    f"{name} stands out immediately: a {subject.race.lower()} {subject.class_name.lower()} "
                    f"carrying themselves like the center of the whole fight."
                )
        else:
            name = str(subject)
            if name in self.NAMED_CHARACTER_INTROS:
                return self.NAMED_CHARACTER_INTROS[name]
        return ""

    def introduce_character(self, subject) -> None:
        if not self.should_introduce_character(subject):
            return
        name = subject.name if hasattr(subject, "name") else str(subject)
        intro = self.character_intro_text(subject)
        self.mark_character_introduced(name)
        if intro:
            self.say(intro, typed=True)

    def introduce_encounter_characters(self, enemies) -> None:
        for enemy in enemies:
            name = getattr(enemy, "name", "")
            if not name:
                continue
            if "leader" in getattr(enemy, "tags", []):
                self.introduce_character(enemy)
                continue
            if name in self.NAMED_CHARACTER_INTROS and name != getattr(enemy, "archetype", ""):
                self.introduce_character(enemy)

    def format_feature_name(self, feature: str) -> str:
        return feature.replace("_", " ").title()

    def lore_menu_label(self, name: str, entry: dict[str, str]) -> str:
        menu = entry.get("menu", "").strip()
        return f"{name}: {menu}" if menu else name

    def item_manual_entries(self) -> dict[str, dict[str, str]]:
        return {
            "Weapons": {
                "menu": "Held in hand and used for attack rolls and weapon damage.",
                "text": (
                    "Weapons are used for melee or ranged attacks and follow the core 5e idea that you wield them in "
                    "one or two hands depending on the weapon. In this game, weapons set your main attack profile, "
                    "including damage dice, attack stat, and any magical hit or damage bonuses.\n\n"
                    "Light one-handed weapons can support off-hand fighting, while two-handed weapons lock out the "
                    "off-hand slot. Ranged weapons and finesse weapons still follow their normal identity: bows shoot "
                    "from range, and finesse weapons can reward Dexterity-focused builds."
                ),
            },
            "Armor and Shields": {
                "menu": "Armor sets base AC, while shields protect the off hand.",
                "text": (
                    "Armor works like the official 5e categories: it defines your base Armor Class and may limit how "
                    "much Dexterity helps. Shields are handled separately in the off-hand slot and improve survivability "
                    "when your other hand is free.\n\n"
                    "Heavy or two-handed weapon setups can conflict with shields, so the game checks those hand-use rules "
                    "when gear is equipped. Magical armor and shields can also add resistances or extra defensive traits."
                ),
            },
            "Worn Equipment": {
                "menu": "Head, neck, rings, gloves, boots, chest, and cape pieces add passive bonuses.",
                "text": (
                    "Worn gear follows the same general logic as official D&D magic items: boots go on the feet, gloves "
                    "on the hands, rings on the fingers, a cloak or cape on the shoulders, and similar items only work "
                    "when worn in the right place. This game simplifies that into clear slots for head, neck, chest, "
                    "gloves, boots, cape, and two ring slots.\n\n"
                    "Most of these pieces grant passive bonuses such as Armor Class, skill bonuses, saving throw boosts, "
                    "initiative bonuses, resistances, or other always-on utility effects."
                ),
            },
            "Consumables and Potions": {
                "menu": "Single-use items that heal, restore, protect, or clear conditions.",
                "text": (
                    "Consumables are one-use resources modeled after the official idea of potions, elixirs, and other "
                    "adventuring aids. In this game they usually restore hit points, temporary hit points, spell slots, "
                    "or remove harmful conditions.\n\n"
                    "Most are best saved for emergencies because they are consumed immediately on use. Healing potions "
                    "follow the game-specific combat timing rules already shown elsewhere: drinking one yourself is faster "
                    "than administering one to someone else."
                ),
            },
            "Scrolls": {
                "menu": "Single-use magical effects that release a spell-like burst or support effect.",
                "text": (
                    "Scrolls are disposable magical items inspired by official D&D spell scrolls. Instead of teaching a "
                    "full spell list system, this game uses named scrolls as focused one-use effects such as healing, "
                    "resource restoration, protection, or camp-only resurrection.\n\n"
                    "They are consumed when activated and are best treated like strategic emergency tools rather than "
                    "ordinary gear."
                ),
            },
            "Supplies and Trade Goods": {
                "menu": "Food, camp staples, and practical inventory items that support travel and resting.",
                "text": (
                    "Not every important item is combat gear. Supplies represent the broader 5e adventuring idea of rations, "
                    "packs, and practical travel resources. In this game they matter for carrying weight, supply value, and "
                    "long-rest readiness.\n\n"
                    "Trade goods and mundane items may also matter for merchants, quest rewards, and inventory economy even "
                    "when they do not give direct combat bonuses."
                ),
            },
        }

    def browse_lore_section(self, title: str, entries: dict[str, dict[str, str]]) -> None:
        names = list(entries)
        visible_slots = max(1, MENU_PAGE_SIZE - 3)
        page = 0
        while True:
            start = page * visible_slots
            visible_names = names[start : start + visible_slots]
            labels = ["Return to lore categories", *[self.lore_menu_label(name, entries[name]) for name in visible_names]]
            nav_map: dict[int, str] = {}
            if page > 0:
                labels.append("Previous page")
                nav_map[len(labels)] = "prev"
            if start + visible_slots < len(names):
                labels.append("Next page")
                nav_map[len(labels)] = "next"
            self.output_fn("")
            self.say(f"Browse {title}. (page {page + 1})")
            for index, option in enumerate(labels, start=1):
                self.output_fn(f"  {index}. {self.format_option_text(option)}")
            raw = self.read_input("> ").strip()
            if self.handle_meta_command(raw):
                continue
            if not raw.isdigit():
                self.say("Please enter a listed number.")
                continue
            choice = int(raw)
            if choice == 1:
                return
            if choice in nav_map:
                page = page - 1 if nav_map[choice] == "prev" else page + 1
                continue
            entry_index = choice - 2
            if 0 <= entry_index < len(visible_names):
                selected = visible_names[entry_index]
                return_to_categories = self.show_lore_entry(title, selected, entries[selected])
                if return_to_categories:
                    return
                continue
            self.say("Please enter a listed number.")

    def show_lore_entry(self, section_title: str, entry_name: str, entry: dict[str, str]) -> bool:
        self.banner(f"{section_title}: {entry_name}")
        self.say(entry["text"])
        manual_text = manual_text_for_entry(section_title, entry_name)
        if manual_text:
            self.say(manual_text)
        choice = self.choose(
            "What next?",
            [
                "Back to this section",
                "Return to lore categories",
            ],
            allow_meta=False,
        )
        return choice == 2

    def show_lore_notes(self) -> None:
        while True:
            self.banner("Lore Codex")
            self.say(LORE_INTRO)
            self.say(
                "Mechanically, the game still follows core 2014 D&D 5e structure for ability checks, "
                "proficiency, initiative, attack rolls, saving throws, spell save DCs, conditions, "
                "weapon damage, healing, potions, and death saves, while compressing positioning and "
                "encounter flow to fit a text adventure."
            )
            self.say(
                "Campaign status:\n"
                + "\n".join(f"- Act {act['number']}: {act['title']} ({act['status']})" for act in ACTS)
            )
            sections = [*TITLE_LORE_SECTIONS, ("Items & Equipment", self.item_manual_entries())]
            options = [f"{title} ({len(entries)})" for title, entries in sections]
            options.append("Return to the title screen")
            choice = self.choose("Choose a lore section.", options, allow_meta=False)
            if choice == len(options):
                return
            section_title, entries = sections[choice - 1]
            self.browse_lore_section(section_title, dict(entries))
