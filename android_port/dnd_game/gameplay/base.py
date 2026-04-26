from __future__ import annotations

import hashlib
from pathlib import Path
import random
import re
import sys
import time

try:
    import msvcrt
except ImportError:  # pragma: no cover - Windows-only polling
    msvcrt = None

from ..content import ACTS
from ..data.story.lore import LORE_INTRO, TITLE_LORE_SECTIONS, manual_text_for_entry
from ..items import (
    EQUIPMENT_SLOTS,
    ITEMS,
    LEGACY_ITEM_NAMES,
    canonical_equipment_slot,
    initial_merchant_stock,
    starter_item_ids_for_character,
)
from ..models import Character, GameState, SKILL_TO_ABILITY, Weapon
from ..ui.colors import strip_ansi
from .constants import InputFn, MENU_PAGE_SIZE, OutputFn


class GameInterrupted(Exception):
    pass


class GameBase:
    STORY_CHECK_OPTION_FLAG_PREFIX = "story_check_option_attempt::"
    STORY_CHECK_OPTION_TAGS = frozenset(skill.upper() for skill in SKILL_TO_ABILITY)
    NAMED_CHARACTER_INTROS = {
        "Mira Thann": "Mira Thann is a sharp-eyed Neverwinter officer who wears quiet authority like armor and studies every answer for weakness or leverage.",
        "Tessa Harrow": "Tessa Harrow is Phandalin's exhausted steward, all ink-stained hands, sleepless focus, and frontier resolve held together by sheer will.",
        "Bryn Underbough": "Bryn Underbough is a halfling trail scout with quick eyes, a quicker tongue, and the watchful stillness of someone who trusts exits before promises.",
        "Elira Dawnmantle": "Elira Dawnmantle is a priestess of Tymora whose steady hands and road-worn faith make the shrine feel more like a field hospital than a sanctuary.",
        "Barthen": "Barthen is a broad-shouldered provisioner with a merchant's apron, a teamster's worry, and the tired patience of a man rationing hope as carefully as flour.",
        "Linene Graywind": "Linene Graywind is a hard-edged quartermaster who keeps her post like a disciplined armory, missing nothing and trusting earned results over charm.",
        "Kaelis Starling": "Kaelis Starling is a lean half-elf ranger whose attention never stops moving, as if every doorway and hedgeline is already a map in his head.",
        "Rhogar Valeguard": "Rhogar Valeguard is a bronze-scaled dragonborn paladin who carries himself like a sworn roadwarden, proud-backed and visibly made of vows.",
        "Tolan Ironshield": "Tolan Ironshield is a battle-scarred dwarven caravan guard with a wall of a shield, a gravel voice, and the look of someone who has outlived too many ambushes.",
        "Rukhar Cinderfang": "Rukhar Cinderfang is a broad hobgoblin sergeant in disciplined mail, every movement controlled with the hard efficiency of a drilled war captain.",
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
    ) -> None:
        self.input_fn = input_fn
        self.output_fn = output_fn
        self.save_dir = Path(save_dir or Path.cwd() / "saves")
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.rng = rng or random.Random()
        self._interactive_output = input_fn is input and output_fn is print
        self.animate_dice = self._interactive_output if animate_dice is None else animate_dice
        self.pace_output = self._interactive_output if pace_output is None else pace_output
        self.type_dialogue = (self._interactive_output if type_dialogue is None else type_dialogue) and output_fn is print
        self._dice_animation_min_seconds = 2.0
        self._dice_animation_max_seconds = 4.0
        self._dice_animation_width = 0
        self._dice_total_reveal_pause_seconds = 0.75
        self._choice_pause_seconds = 1.0
        self._combat_transition_pause_seconds = 1.0
        self._option_reveal_pause_seconds = 0.5
        self._loot_reveal_pause_seconds = 0.75
        self._health_bar_width = 12
        self._health_bar_animation_step_seconds = 0.08
        self._dialogue_seconds_per_sentence = 2.5
        self._narration_seconds_per_sentence = 2.5
        self._typing_sentence_pause_seconds = 0.75
        if self.animate_dice:
            try:
                setattr(self.rng, "dice_roll_animator", self.animate_dice_roll)
            except Exception:
                self.animate_dice = False
        self.state: GameState | None = None
        self._pending_story_check_option: tuple[str, str] | None = None
        self._in_combat = False
        self._scene_handlers = {
            "background_prologue": self.scene_background_prologue,
            "neverwinter_briefing": self.scene_neverwinter_briefing,
            "road_ambush": self.scene_road_ambush,
            "phandalin_hub": self.scene_phandalin_hub,
            "ashfall_watch": self.scene_ashfall_watch,
            "emberhall_cellars": self.scene_emberhall_cellars,
            "act1_complete": self.scene_act1_complete,
        }

    MERCHANT_ATTITUDE_DEFAULTS = {
        "barthen_provisions": 20,
        "linene_graywind": 15,
    }
    MERCHANT_BASE_BUY_MULTIPLIER = 2.1
    MERCHANT_PERSUASION_DISCOUNT = 0.05
    MERCHANT_ATTITUDE_DISCOUNT = 0.003

    def run(self) -> None:
        try:
            while True:
                self.banner("Aethrune: Acts I-II")
                self.say(
                    "An original choice-driven fantasy text adventure across the "
                    "Emberway, Iron Hollow, and the Resonant Vaults. "
                    "Acts I and II are playable now, with later acts scaffolded for expansion."
                )
                choice = self.choose(
                    "What would you like to do?",
                    [
                        "Start a new game",
                        "Save Files",
                        "Read the lore notes",
                        "Quit",
                    ],
                    allow_meta=False,
                )
                if choice == 1:
                    self.start_new_game()
                    self.play_current_state()
                elif choice == 2:
                    loaded = self.open_save_files_menu()
                    if loaded:
                        self.play_current_state()
                elif choice == 3:
                    self.show_lore_notes()
                else:
                    self.say("Safe travels, adventurer.")
                    return
        except GameInterrupted:
            self.say("Input interrupted. Closing the game cleanly.")
            self.state = None

    def play_current_state(self) -> None:
        try:
            while self.state is not None:
                handler = self._scene_handlers.get(self.state.current_scene)
                if handler is None:
                    self.say(f"Unknown scene '{self.state.current_scene}'. Returning to the title screen.")
                    self.state = None
                    return
                handler()
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

    def option_tag(self, option: str) -> str | None:
        match = re.match(r"^\[([^\]]+)\]\s*", strip_ansi(option))
        if match is None:
            return None
        return match.group(1).strip().upper()

    def option_is_story_skill_check(self, option: str) -> bool:
        tag = self.option_tag(option)
        if not tag:
            return False
        parts = [part.strip() for part in tag.split("/")]
        return bool(parts) and all(part in self.STORY_CHECK_OPTION_TAGS for part in parts)

    def story_check_choice_attempt_flag(self, prompt: str, option: str) -> str:
        scene_key = self.state.current_scene if self.state is not None else "unknown"
        payload = f"{scene_key}\n{strip_ansi(prompt).strip()}\n{strip_ansi(option).strip()}"
        digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
        return f"{self.STORY_CHECK_OPTION_FLAG_PREFIX}{digest}"

    def story_check_choice_attempted(self, prompt: str, option: str) -> bool:
        if self.state is None or not self.option_is_story_skill_check(option):
            return False
        return bool(self.state.flags.get(self.story_check_choice_attempt_flag(prompt, option)))

    def queue_story_check_choice_attempt(self, prompt: str, option: str) -> None:
        if self.option_is_story_skill_check(option):
            self._pending_story_check_option = (prompt, option)
        else:
            self._pending_story_check_option = None

    def clear_pending_story_check_choice_attempt(self) -> None:
        self._pending_story_check_option = None

    def commit_pending_story_check_choice_attempt(self) -> None:
        if self.state is None or self._pending_story_check_option is None:
            return
        prompt, option = self._pending_story_check_option
        self.state.flags[self.story_check_choice_attempt_flag(prompt, option)] = True
        self._pending_story_check_option = None

    def read_input(self, prompt: str) -> str:
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
        if self.pace_output:
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

    def animation_skip_requested(self, *, require_animation: bool = False) -> bool:
        if require_animation and not self.animate_dice:
            return False
        if not self._interactive_output or msvcrt is None:
            return False
        if hasattr(sys.stdin, "isatty") and not sys.stdin.isatty():
            return False
        requested = False
        while msvcrt.kbhit():
            key = msvcrt.getwch()
            if key in {"\r", "\n"}:
                requested = True
        return requested

    def sleep_for_animation(self, duration: float, *, require_animation: bool = False) -> bool:
        end_time = time.perf_counter() + max(0.0, duration)
        while True:
            if self.animation_skip_requested(require_animation=require_animation):
                return True
            remaining = end_time - time.perf_counter()
            if remaining <= 0:
                return False
            time.sleep(min(0.03, remaining))

    def animate_health_bar_loss(self, target, previous_hp: int, new_hp: int) -> None:
        if not self.should_animate_health_bars() or new_hp >= previous_hp or target.max_hp <= 0:
            return
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

    def dialogue_sentence_count(self, text: str) -> int:
        parts = re.findall(r"[^.!?]+[.!?]+(?:['\"])?|[^.!?]+$", text)
        return max(1, sum(1 for part in parts if part.strip()))

    def dialogue_typing_duration(self, text: str) -> float:
        return self._dialogue_seconds_per_sentence * self.dialogue_sentence_count(text)

    def is_sentence_boundary(self, text: str, index: int) -> bool:
        character = text[index]
        if character not in ".!?":
            return False
        next_index = index + 1
        while next_index < len(text) and text[next_index] in {'"', "'"}:
            next_index += 1
        return next_index >= len(text) or text[next_index].isspace()

    def typewrite_text(self, text: str, *, delay: float) -> None:
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

    def typewrite_dialogue_line(self, speaker_name: str, text: str) -> None:
        self.output_fn("")
        prefix = f'{speaker_name}: "'
        sys.stdout.write(prefix)
        sys.stdout.flush()
        delay = self.dialogue_typing_duration(text) / max(1, len(text))
        self.typewrite_text(text, delay=delay)
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
    ) -> None:
        if not self.animate_dice or not rolls:
            return
        rerolls = rerolls or []
        effective_modifier = modifier if display_modifier is None else display_modifier
        show_total_frame = (kind == "d20" and (effective_modifier or target_number is not None)) or (
            kind != "d20" and (effective_modifier != 0 or len(rolls) > 1)
        )
        duration = min(
            self._dice_animation_max_seconds,
            max(
                self._dice_animation_min_seconds,
                self._dice_animation_min_seconds + 0.35 * max(0, len(rolls) - 1) + (0.35 if advantage_state else 0.0),
            ),
        )
        frames = min(34, max(20, int(duration * 8)))
        preview_rng = random.Random(time.perf_counter_ns() ^ id(rolls) ^ (sides << 8))
        label = self.dice_animation_label(kind, expression, critical=critical, advantage_state=advantage_state)
        weights = [0.25 + ((index / max(1, frames - 1)) ** 2) * 2.0 for index in range(frames)]
        scale = duration / sum(weights)
        for delay in weights:
            shown = [preview_rng.randint(1, sides) for _ in rolls]
            self.render_dice_animation_frame(
                label,
                shown,
                final=False,
                target_number=target_number,
                target_label=target_label,
            )
            if self.sleep_for_dice_animation(delay * scale):
                break
        self.render_dice_animation_frame(
            self.dice_animation_final_label(kind, expression, critical=critical, advantage_state=advantage_state),
            rolls,
            final=True,
            modifier=modifier,
            kept=kept,
            rerolls=rerolls,
            target_number=target_number,
            target_label=target_label,
            show_total=not show_total_frame,
        )
        if kind == "d20" and show_total_frame:
            self.sleep_for_animation(self._dice_total_reveal_pause_seconds, require_animation=True)
            self.render_dice_animation_total_frame(
                kept=kept if kept is not None else rolls[-1],
                modifier=effective_modifier,
                target_number=target_number,
                target_label=target_label,
            )
        elif show_total_frame:
            self.sleep_for_animation(self._dice_total_reveal_pause_seconds, require_animation=True)
            self.render_roll_animation_total_frame(rolls=rolls, modifier=effective_modifier)
        self.sleep_for_animation(1.0, require_animation=True)

    def dice_animation_label(self, kind: str, expression: str, *, critical: bool, advantage_state: int) -> str:
        if kind == "d20":
            if advantage_state > 0:
                return "Rolling d20 (advantage)"
            if advantage_state < 0:
                return "Rolling d20 (disadvantage)"
            return "Rolling d20"
        if critical:
            return f"Rolling {expression} (critical)"
        return f"Rolling {expression}"

    def dice_animation_final_label(self, kind: str, expression: str, *, critical: bool, advantage_state: int) -> str:
        if kind == "d20":
            if advantage_state > 0:
                return "Rolled d20 (advantage)"
            if advantage_state < 0:
                return "Rolled d20 (disadvantage)"
            return "Rolled d20"
        if critical:
            return f"Rolled {expression} (critical)"
        return f"Rolled {expression}"

    def render_dice_animation_frame(
        self,
        label: str,
        rolls: list[int],
        *,
        final: bool,
        modifier: int = 0,
        kept: int | None = None,
        rerolls: list[tuple[int, int]] | None = None,
        target_number: int | None = None,
        target_label: str | None = None,
        show_total: bool = True,
    ) -> None:
        rerolls = rerolls or []
        core = " / ".join(str(value) for value in rolls) if "d20" in label else " + ".join(str(value) for value in rolls)
        text = f"{label}: {core}"
        if target_number is not None:
            suffix = target_label or str(target_number)
            text += f" vs {suffix}"
        if final and kept is not None:
            text += f" | kept {kept}"
        if final and show_total and modifier and kept is None:
            text += f" {'+' if modifier > 0 else '-'} {abs(modifier)}"
            text += f" = {sum(rolls) + modifier}"
        elif final and show_total and kept is None:
            text += f" = {sum(rolls) + modifier}"
        if final and rerolls:
            reroll_text = ", ".join(f"{old}->{new}" for old, new in rerolls)
            text += f" | reroll {reroll_text}"
        padding = max(0, self._dice_animation_width - len(text))
        sys.stdout.write("\r" + text + (" " * padding))
        if final:
            sys.stdout.write("\n")
            self._dice_animation_width = 0
        else:
            self._dice_animation_width = max(self._dice_animation_width, len(text))
        sys.stdout.flush()

    def render_dice_animation_total_frame(
        self,
        *,
        kept: int,
        modifier: int,
        target_number: int | None = None,
        target_label: str | None = None,
    ) -> None:
        total = kept + modifier
        modifier_text = f"{kept} {'+' if modifier >= 0 else '-'} {abs(modifier)}"
        text = f"Final total: {total} ({modifier_text})"
        if target_number is not None:
            suffix = target_label or str(target_number)
            text += f" vs {suffix}"
        self.output_fn(text)

    def render_roll_animation_total_frame(self, *, rolls: list[int], modifier: int) -> None:
        total = sum(rolls) + modifier
        breakdown = " + ".join(str(value) for value in rolls) if rolls else "0"
        if modifier > 0:
            breakdown += f" + {modifier}"
        elif modifier < 0:
            breakdown += f" - {abs(modifier)}"
        self.output_fn(f"Final total: {total} ({breakdown})")

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
        return max(
            1.0,
            self.MERCHANT_BASE_BUY_MULTIPLIER
            - (self.MERCHANT_PERSUASION_DISCOUNT * persuasion)
            - (self.MERCHANT_ATTITUDE_DISCOUNT * attitude),
        )

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
        if lowered == "help":
            self.show_global_commands()
            return True
        if lowered == "load":
            if self.open_save_files_menu():
                raise ResumeLoadedGame()
            return True
        if lowered == "save":
            self.inline_save()
            return True
        if lowered in {"saves", "save files"}:
            if self.open_save_files_menu():
                raise ResumeLoadedGame()
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

    def show_global_commands(self) -> None:
        self.banner("Global Commands")
        self.say("These commands can be typed at most prompts.")
        commands = [
            ("help", "Show the list of global commands and what they do."),
            ("save", "Save the current run to a named slot."),
            ("load", "Load another save slot immediately and continue from there."),
            ("saves / save files", "Open the Save Files manager to load or delete save slots."),
            ("party", "Review quick party combat stats, statuses, and roster state."),
            ("journal", "Open the journal and clues log."),
            ("inventory / backpack / bag", "Open the shared inventory and item management view."),
            ("equipment / gear", "Open the full equipment manager for any company member."),
            ("sheet / sheets", "Open full character sheets for the company."),
            ("camp", "Open camp when you are not in combat."),
        ]
        for command, description in commands:
            self.output_fn(f"- {command}: {description}")

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
        display_name = entry.get("label", name).strip() or name
        menu = entry.get("menu", "").strip()
        return f"{display_name}: {menu}" if menu else display_name

    def item_manual_entries(self) -> dict[str, dict[str, str]]:
        return {
            "Weapons": {
                "menu": "Held in hand and used for strike checks and weapon damage.",
                "text": (
                    "Weapons are used for melee or ranged strikes and define how a character turns training into "
                    "damage. In this game, weapons set your main attack profile, including damage dice, attack stat, "
                    "hand use, reach, and any relic bonuses.\n\n"
                    "Light one-handed weapons can support off-hand fighting, while two-handed weapons lock out the "
                    "off-hand slot. Ranged weapons and finesse weapons keep their familiar roles: bows pressure from "
                    "range, and finesse weapons reward Agility-focused builds."
                ),
            },
            "Armor and Shields": {
                "menu": "Armor sets base Defense, while shields protect the off hand.",
                "text": (
                    "Armor defines your base Defense and may limit how much Agility helps. Shields are handled separately "
                    "in the off-hand slot and improve survivability when your other hand is free.\n\n"
                    "Heavy or two-handed weapon setups can conflict with shields, so the game checks hand-use rules "
                    "when gear is equipped. Relic armor and shields can also add resistances or extra defensive traits."
                ),
            },
            "Worn Equipment": {
                "menu": "Head, neck, rings, gloves, boots, chest, and cape pieces add passive bonuses.",
                "text": (
                    "Worn gear follows clear body slots: boots go on the feet, gloves on the hands, rings on the "
                    "fingers, a cloak or cape on the shoulders, and similar pieces only work when worn in the right "
                    "place. This game simplifies that into clear slots for head, neck, chest, "
                    "gloves, boots, cape, and two ring slots.\n\n"
                    "Most of these pieces grant passive bonuses such as Defense, skill bonuses, resist boosts, "
                    "initiative bonuses, resistances, or other always-on utility effects."
                ),
            },
            "Consumables": {
                "menu": "Single-use items that heal, restore, protect, or clear conditions.",
                "text": (
                    "Consumables are one-use resources such as potions, field tonics, and travel aids. In this game "
                    "they usually restore hit points, temporary hit points, MP, or remove harmful "
                    "conditions.\n\n"
                    "Most are best saved for emergencies because they are consumed immediately on use. Healing potions "
                    "follow the game-specific combat timing rules already shown elsewhere: drinking one yourself is "
                    "faster than administering one to someone else."
                ),
            },
            "Scripts": {
                "menu": "Single-use channeling patterns that release a focused effect.",
                "text": (
                    "Scripts are disposable channeling patterns. Instead of teaching a full channel pool, this game "
                    "uses named scripts as focused one-use effects such as healing, resource restoration, protection, "
                    "or camp-only revival.\n\n"
                    "They are consumed when activated and are best treated like strategic emergency tools rather than "
                    "ordinary gear."
                ),
            },
            "Supplies and Trade Goods": {
                "menu": "Food, camp staples, and practical inventory items that support travel and resting.",
                "text": (
                    "Not every important item is combat gear. Supplies represent food, packs, repair bits, fuel, "
                    "and practical travel resources. In this game they matter for supply value and "
                    "camp readiness.\n\n"
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
        display_name = entry.get("label", entry_name).strip() or entry_name
        self.banner(f"{section_title}: {display_name}")
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
                "Under the hood, the game still uses an SRD-derived d20 chassis for ability checks, "
                "proficiency, initiative, strike checks, resist checks, channel difficulty, conditions, "
                "weapon damage, healing, draughts, and death saves, while compressing positioning and "
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
