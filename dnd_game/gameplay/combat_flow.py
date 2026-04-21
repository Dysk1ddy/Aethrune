from __future__ import annotations

from dataclasses import dataclass

from ..content import create_enemy
from ..items import get_item
from ..models import Character
from ..ui.colors import rich_style_name
from ..ui.rich_render import Console, Group, Live, Panel, Table, Text, box
from .encounter import Encounter
from .spell_slots import has_spell_slots


@dataclass(slots=True)
class TurnState:
    actions_remaining: int = 1
    bonus_action_available: bool = True
    attack_action_taken: bool = False
    bonus_action_spell_cast: bool = False
    non_cantrip_action_spell_cast: bool = False
    free_flee: bool = False


class CombatFlowMixin:
    def run_encounter(self, encounter: Encounter) -> str:
        assert self.state is not None
        previous_active_encounter = getattr(self, "_active_encounter", None)
        previous_active_heroes = getattr(self, "_active_combat_heroes", None)
        previous_active_enemies = getattr(self, "_active_combat_enemies", None)
        self._in_combat = True
        heroes: list[Character] = []
        enemies: list[Character] = []
        play_encounter_music = getattr(self, "play_encounter_music", None)
        refresh_scene_music = getattr(self, "refresh_scene_music", None)
        try:
            heroes = [member for member in self.state.party_members() if not member.dead]
            self.prepare_encounter_for_party(encounter, heroes=heroes)
            enemies = encounter.enemies
            self._active_encounter = encounter
            self._active_combat_heroes = heroes
            self._active_combat_enemies = enemies
            self.banner(encounter.title)
            self.say(encounter.description, typed=True)
            if callable(play_encounter_music):
                play_encounter_music(encounter)
            self.pause_for_combat_transition()
            self.introduce_encounter_characters(enemies)
            self.apply_companion_combat_openers(heroes, enemies, encounter)
            for enemy in enemies:
                if enemy.is_conscious() and enemy.archetype == "carrion_stalker" and not self.has_status(enemy, "invisible"):
                    self.apply_status(enemy, "invisible", 1, source=f"{enemy.name}'s stalking entry")
            dodging: set[str] = set()
            initiative = self.roll_initiative(
                heroes,
                enemies,
                hero_bonus=encounter.hero_initiative_bonus,
                enemy_bonus=encounter.enemy_initiative_bonus,
            )
            round_number = 1
            while True:
                if not any(enemy.is_conscious() for enemy in enemies):
                    return self.resolve_encounter_victory(encounter, enemies)
                if not any(hero.is_conscious() for hero in heroes):
                    return "defeat"

                self.say(f"Round {round_number}")
                round_start_hook = getattr(self, "on_encounter_round_start", None)
                if callable(round_start_hook):
                    round_start_hook(encounter, heroes, enemies, initiative, round_number)
                    if not any(enemy.is_conscious() for enemy in enemies):
                        return self.resolve_encounter_victory(encounter, enemies)
                    if not any(hero.is_conscious() for hero in heroes):
                        return "defeat"
                self.print_battlefield(heroes, enemies)
                for actor in initiative:
                    if actor.name in dodging:
                        dodging.discard(actor.name)
                    if actor.dead:
                        continue
                    if actor in heroes and actor.is_dying():
                        self.resolve_death_save(actor)
                        if actor.dead:
                            self.say(f"{self.style_name(actor)} slips away.")
                        self.tick_conditions(actor)
                        continue
                    if not actor.is_conscious():
                        continue
                    if not self.resolve_start_of_turn_statuses(actor):
                        self.tick_conditions(actor)
                        continue
                    if not any(hero.is_conscious() for hero in heroes):
                        return "defeat"
                    if not any(enemy.is_conscious() for enemy in enemies):
                        return self.resolve_encounter_victory(encounter, enemies)

                    if actor in heroes:
                        result = self.hero_turn(actor, heroes, enemies, encounter, dodging)
                        if result == "fled":
                            return "fled"
                    else:
                        self.enemy_turn(actor, heroes, enemies, encounter, dodging)
                    self.tick_conditions(actor)
                round_number += 1
        finally:
            self.clear_after_encounter([*heroes, *enemies])
            self._active_encounter = previous_active_encounter
            self._active_combat_heroes = previous_active_heroes
            self._active_combat_enemies = previous_active_enemies
            self._in_combat = False
            if callable(refresh_scene_music):
                refresh_scene_music()

    def prepare_encounter_for_party(self, encounter: Encounter, *, heroes: list[Character] | None = None) -> None:
        assert self.state is not None
        party = heroes if heroes is not None else [member for member in self.state.party_members() if not member.dead]
        if not party:
            return
        target_level = max(1, max(member.level for member in party))
        original_living_enemies = [enemy for enemy in encounter.enemies if "enemy" in enemy.tags and not enemy.dead]
        if not original_living_enemies:
            return

        scaling_slots = 2 if len(original_living_enemies) >= 4 else 1
        self.scale_encounter_enemies_to_party_level(original_living_enemies, target_level, slots=scaling_slots)

        if len(party) >= 3:
            self.ensure_minimum_encounter_enemies(encounter, target_level=target_level, minimum=3)

    def scale_encounter_enemies_to_party_level(
        self,
        enemies: list[Character],
        target_level: int,
        *,
        slots: int,
    ) -> None:
        candidates = [enemy for enemy in enemies if enemy.is_conscious() and enemy.level < target_level]
        candidates.sort(
            key=lambda enemy: (
                "leader" in enemy.tags,
                enemy.xp_value,
                enemy.max_hp,
                enemy.level,
            ),
            reverse=True,
        )
        for enemy in candidates[: max(0, slots)]:
            self.scale_enemy_to_party_level(enemy, target_level)

    def scale_enemy_to_party_level(self, enemy: Character, target_level: int) -> None:
        if target_level <= enemy.level:
            return
        original_level = enemy.level
        level_gap = target_level - original_level
        hp_deficit = max(0, enemy.max_hp - enemy.current_hp)
        for _ in range(level_gap):
            hp_gain = max(1, enemy.hit_die // 2 + 1 + enemy.ability_mod("CON"))
            enemy.max_hp += hp_gain
        enemy.level = target_level
        if enemy.current_hp > 0:
            enemy.current_hp = max(1, enemy.max_hp - hp_deficit)
        if level_gap >= 2:
            enemy.weapon.damage_bonus += level_gap // 2
        enemy.xp_value = self.scaled_enemy_reward(enemy.xp_value, level_gap, xp=True)
        enemy.gold_value = self.scaled_enemy_reward(enemy.gold_value, level_gap, xp=False)
        enemy.notes.append(f"Pseudo-scaled from level {original_level} to {target_level}.")

    def scaled_enemy_reward(self, base_value: int, level_gap: int, *, xp: bool) -> int:
        if base_value <= 0 or level_gap <= 0:
            return base_value
        per_level = 0.5 if xp else 0.35
        return max(base_value + 1, int(round(base_value * (1 + per_level * level_gap))))

    def ensure_minimum_encounter_enemies(self, encounter: Encounter, *, target_level: int, minimum: int) -> None:
        while len([enemy for enemy in encounter.enemies if "enemy" in enemy.tags and not enemy.dead]) < minimum:
            template = self.support_enemy_template_for_encounter(encounter.enemies, target_level=target_level)
            support = create_enemy(template)
            support.notes.append("Added by party-size encounter scaling.")
            encounter.enemies.append(support)

    def support_enemy_template_for_encounter(self, enemies: list[Character], *, target_level: int) -> str:
        living = [enemy for enemy in enemies if "enemy" in enemy.tags and not enemy.dead]
        tags = {tag for enemy in living for tag in enemy.tags}
        archetypes = {enemy.archetype for enemy in living}
        races = {enemy.race for enemy in living}

        if archetypes & {"caldra_voss", "choir_adept", "cult_lookout", "choir_executioner"}:
            return "cult_lookout"
        if "undead" in tags or "Undead" in races:
            return "lantern_fen_wisp" if target_level >= 3 else "skeletal_sentry"
        if "construct" in tags or "Construct" in races:
            return "animated_armor"
        if "plant" in tags or "Plant" in races:
            return "briar_twig"
        if "ooze" in tags or "Ooze" in races:
            return "ochre_slime"
        if "beast" in tags or "Beast" in races:
            return "stirge_swarm" if target_level >= 3 else "wolf"
        if "aberration" in tags or "Aberration" in races:
            return "blacklake_pincerling" if target_level >= 4 else "nothic"
        if "monstrosity" in tags or "Monstrosity" in races:
            if target_level >= 4:
                return "carrion_lash_crawler"
            return "rust_shell_scuttler"
        if "giant" in tags or "Giant" in races:
            return "goblin_skirmisher"
        if "Orc" in races:
            return "orc_raider"
        if "Bugbear" in races:
            return "bugbear_reaver"
        if "Kobold" in races:
            return "cinder_kobold"
        if "Goblin" in races:
            return "goblin_skirmisher"
        if "humanoid" in tags or races & {"Human", "Humanoid", "Hobgoblin"}:
            if archetypes & {"gutter_zealot", "ember_channeler"}:
                return "gutter_zealot"
            if target_level >= 3 and archetypes & {"expedition_reaver", "starblighted_miner"}:
                return "expedition_reaver"
            return "bandit_archer"
        return "bandit"

    def resolve_encounter_victory(self, encounter: Encounter, enemies: list[Character]) -> str:
        assert self.state is not None
        total_xp = sum(enemy.xp_value for enemy in enemies)
        total_gold = sum(enemy.gold_value for enemy in enemies)
        if total_xp or total_gold:
            self.reward_party(xp=total_xp, gold=total_gold, reason=encounter.title)
        self.collect_loot(enemies, source=encounter.title)
        self.recover_after_battle()
        play_sound_effect = getattr(self, "play_sound_effect", None)
        if callable(play_sound_effect):
            play_sound_effect("fight_victory")
        self.say("The encounter is yours.")
        self.pause_for_combat_transition()
        maybe_run_post_combat_random_encounter = getattr(self, "maybe_run_post_combat_random_encounter", None)
        if callable(maybe_run_post_combat_random_encounter):
            maybe_run_post_combat_random_encounter(encounter)
        create_autosave = getattr(self, "create_autosave", None)
        if callable(create_autosave):
            label = getattr(encounter, "title", "") or getattr(self.state, "current_scene", "combat")
            create_autosave(label=label)
        return "victory"

    def marked_priority_target(self, heroes: list[Character]) -> Character | None:
        marked = [hero for hero in heroes if hero.is_conscious() and self.has_status(hero, "marked")]
        if not marked:
            return None
        return max(marked, key=lambda hero: (hero.attack_bonus(), hero.current_hp))

    def apply_companion_combat_openers(
        self,
        heroes: list[Character],
        enemies: list[Character],
        encounter: Encounter,
    ) -> None:
        if self.state is None:
            return
        kaelis = next(
            (
                hero
                for hero in heroes
                if hero.is_conscious() and hero.companion_id == "kaelis_starling" and hero.disposition >= 6
            ),
            None,
        )
        if kaelis is not None:
            self.say(f"{kaelis.name} opens with a Shadow Volley that keeps the whole company under cover for one decisive beat.")
            for hero in heroes:
                if hero.is_conscious():
                    self.apply_status(hero, "invisible", 1, source=f"{kaelis.name}'s Shadow Volley")
        tolan = next(
            (
                hero
                for hero in heroes
                if hero.is_conscious() and hero.companion_id == "tolan_ironshield" and hero.disposition >= 6
            ),
            None,
        )
        if tolan is not None:
            self.say(f"{tolan.name} plants his feet and calls Hold the Line before steel ever meets steel.")
            for hero in heroes:
                if hero.is_conscious():
                    self.apply_status(hero, "guarded", 2, source=f"{tolan.name}'s Hold the Line")

    def hero_turn(
        self,
        actor: Character,
        heroes: list[Character],
        enemies: list[Character],
        encounter: Encounter,
        dodging: set[str],
    ) -> str | None:
        return self.player_turn(actor, heroes, enemies, encounter, dodging)

    def player_turn(
        self,
        actor: Character,
        heroes: list[Character],
        enemies: list[Character],
        encounter: Encounter,
        dodging: set[str],
    ) -> str | None:
        turn_state = TurnState()
        while True:
            conscious_enemies = [enemy for enemy in enemies if enemy.is_conscious()]
            if not conscious_enemies:
                return None
            options = self.get_player_combat_options(actor, encounter, turn_state=turn_state, heroes=heroes)
            if options == ["End Turn"]:
                return None
            selected_option = self.choose_grouped_combat_option(
                self.turn_prompt(actor, turn_state),
                options,
                actor=actor,
                heroes=heroes,
                enemies=enemies,
            )
            action = self.choice_text(selected_option)
            if action == "End Turn":
                return None
            if action == "Use Action Surge":
                if self.activate_action_surge(actor, turn_state):
                    continue
                return None
            if action == "Attack with Divine Smite":
                target = self.choose_target(conscious_enemies, prompt="Choose a target for Divine Smite.", allow_back=True)
                if target is None:
                    continue
                self.perform_weapon_attack(actor, target, heroes, enemies, dodging, use_smite=True)
                turn_state.actions_remaining -= 1
                turn_state.attack_action_taken = True
                continue
            if action.startswith("Attack"):
                target = self.choose_target(conscious_enemies, prompt="Choose a target for your attack.", allow_back=True)
                if target is None:
                    continue
                self.perform_weapon_attack(actor, target, heroes, enemies, dodging)
                turn_state.actions_remaining -= 1
                turn_state.attack_action_taken = True
                continue
            if action == "Make Off-Hand Attack":
                target = self.choose_target(conscious_enemies, prompt="Choose a target for your off-hand attack.", allow_back=True)
                if target is None:
                    continue
                self.perform_offhand_attack(actor, target, heroes, enemies, dodging)
                turn_state.bonus_action_available = False
                continue
            if action == "Use Martial Arts":
                target = self.choose_target(conscious_enemies, prompt="Choose a target for Martial Arts.", allow_back=True)
                if target is None:
                    continue
                self.use_martial_arts(actor, target, heroes, enemies, dodging)
                turn_state.bonus_action_available = False
                continue
            if action == "Use Flurry of Blows":
                target = self.choose_target(conscious_enemies, prompt="Choose a target for Flurry of Blows.", allow_back=True)
                if target is None:
                    continue
                self.use_flurry_of_blows(actor, target, heroes, enemies, dodging)
                turn_state.bonus_action_available = False
                continue
            if action == "Use Patient Defense":
                if not actor.spend_resource("ki"):
                    self.say(f"{self.style_name(actor)} has no ki left for Patient Defense.")
                    return None
                dodging.add(actor.name)
                self.say(f"{self.style_name(actor)} spends 1 ki point and slips into Patient Defense.")
                turn_state.bonus_action_available = False
                continue
            if action == "Use Step of the Wind":
                if not actor.spend_resource("ki"):
                    self.say(f"{self.style_name(actor)} has no ki left for Step of the Wind.")
                    return None
                step_choice = self.choose(
                    "Step of the Wind lets you move on sudden breath and balance.",
                    [
                        self.action_option("Dash through the fight and set up a clean escape."),
                        self.action_option("Disengage and peel free of immediate pressure."),
                        "Back",
                    ],
                    allow_meta=False,
                    show_hud=False,
                )
                if step_choice == 3:
                    actor.resources["ki"] += 1
                    continue
                if step_choice == 1:
                    turn_state.free_flee = True
                    self.apply_status(actor, "emboldened", 1, source="Step of the Wind")
                    self.say(f"{self.style_name(actor)} bursts through the melee with impossible speed.")
                else:
                    turn_state.free_flee = True
                    self.say(f"{self.style_name(actor)} flows clear of the immediate crush.")
                turn_state.bonus_action_available = False
                continue
            if action == "Use Cunning Action":
                cunning_choice = self.choose(
                    "Choose a Cunning Action.",
                    [
                        self.skill_tag("STEALTH", self.action_option("Hide in the fight's blind spots.")),
                        self.action_option("Dash and line up a clean escape."),
                        self.action_option("Disengage and break away safely."),
                        "Back",
                    ],
                    allow_meta=False,
                    show_hud=False,
                )
                if cunning_choice == 4:
                    continue
                if cunning_choice == 1:
                    success = self.skill_check(actor, "Stealth", 12, context="to vanish back into the melee's blind spots")
                    if success:
                        self.apply_status(actor, "invisible", 2, source="Cunning Action")
                        self.say(f"{self.style_name(actor)} slips back out of the enemy's direct line.")
                    else:
                        self.say(f"{self.style_name(actor)} cannot quite disappear into the chaos.")
                elif cunning_choice == 2:
                    turn_state.free_flee = True
                    self.apply_status(actor, "emboldened", 1, source="Cunning Action: Dash")
                    self.say(f"{self.style_name(actor)} surges for open ground and can break away cleanly this turn.")
                else:
                    turn_state.free_flee = True
                    self.say(f"{self.style_name(actor)} disengages cleanly and can flee without needing another opening this turn.")
                turn_state.bonus_action_available = False
                continue
            if action == "Enter Rage":
                self.use_rage(actor)
                turn_state.bonus_action_available = False
                continue
            if action == "Use Second Wind":
                self.use_second_wind(actor)
                turn_state.bonus_action_available = False
                continue
            if action == "Use Bardic Inspiration":
                target = self.choose_ally(heroes, prompt="Choose an ally to inspire.", allow_back=True)
                if target is None:
                    continue
                self.use_bardic_inspiration(actor, target)
                turn_state.bonus_action_available = False
                continue
            if action == "Use Lay on Hands":
                target = self.choose_ally(heroes, prompt="Choose an ally to heal with Lay on Hands.", allow_back=True)
                if target is None:
                    continue
                self.use_lay_on_hands(actor, target)
                turn_state.actions_remaining -= 1
                continue
            if action == "Invoke Channel Divinity":
                target = self.choose_target(conscious_enemies, prompt="Choose a target for Channel Divinity.", allow_back=True)
                if target is None:
                    continue
                self.use_channel_divinity(actor, target)
                turn_state.actions_remaining -= 1
                continue
            if action == "Cast Sacred Flame":
                target = self.choose_target(conscious_enemies, prompt="Choose a target for Sacred Flame.", allow_back=True)
                if target is None:
                    continue
                self.cast_sacred_flame(actor, target)
                turn_state.actions_remaining -= 1
                continue
            if action == "Cast Cure Wounds":
                target = self.choose_ally(heroes, prompt="Choose an ally to heal with Cure Wounds.", allow_back=True)
                if target is None:
                    continue
                self.cast_cure_wounds(actor, target)
                turn_state.actions_remaining -= 1
                turn_state.non_cantrip_action_spell_cast = True
                continue
            if action == "Cast Healing Word":
                target = self.choose_ally(heroes, prompt="Choose an ally to heal with Healing Word.", allow_back=True)
                if target is None:
                    continue
                self.cast_healing_word(actor, target)
                turn_state.bonus_action_available = False
                turn_state.bonus_action_spell_cast = True
                continue
            if action == "Cast Produce Flame":
                target = self.choose_target(conscious_enemies, prompt="Choose a target for Produce Flame.", allow_back=True)
                if target is None:
                    continue
                self.cast_produce_flame(actor, target, dodging)
                turn_state.actions_remaining -= 1
                continue
            if action == "Cast Vicious Mockery":
                target = self.choose_target(conscious_enemies, prompt="Choose a target for Vicious Mockery.", allow_back=True)
                if target is None:
                    continue
                self.cast_vicious_mockery(actor, target)
                turn_state.actions_remaining -= 1
                continue
            if action == "Cast Fire Bolt":
                target = self.choose_target(conscious_enemies, prompt="Choose a target for Fire Bolt.", allow_back=True)
                if target is None:
                    continue
                self.cast_fire_bolt(actor, target, dodging)
                turn_state.actions_remaining -= 1
                continue
            if action == "Cast Eldritch Blast":
                target = self.choose_target(conscious_enemies, prompt="Choose a target for Eldritch Blast.", allow_back=True)
                if target is None:
                    continue
                self.cast_eldritch_blast(actor, target, dodging)
                turn_state.actions_remaining -= 1
                continue
            if action == "Cast Magic Missile":
                target = self.choose_target(conscious_enemies, prompt="Choose a target for Magic Missile.", allow_back=True)
                if target is None:
                    continue
                self.cast_magic_missile(actor, target)
                turn_state.actions_remaining -= 1
                turn_state.non_cantrip_action_spell_cast = True
                continue
            if action == "Help a Downed Ally":
                target = self.choose_ally(
                    [hero for hero in heroes if hero.current_hp == 0 and not hero.dead],
                    prompt="Choose a downed ally to haul back into the fight.",
                    allow_back=True,
                )
                if target is None:
                    continue
                self.help_downed_ally(actor, target)
                turn_state.actions_remaining -= 1
                continue
            if action == "Take the Dodge action":
                dodging.add(actor.name)
                self.say(
                    f"{self.style_name(actor)} focuses on defense. Attacks against them have disadvantage until their next turn."
                )
                turn_state.actions_remaining -= 1
                continue
            if action == "Drink a Healing Potion":
                if self.drink_healing_potion_in_combat(actor):
                    turn_state.bonus_action_available = False
                continue
            if action == "Use an Item":
                if not self.use_item_from_inventory(combat=True, actor=actor, heroes=heroes, allow_self_healing_potion=False):
                    continue
                turn_state.actions_remaining -= 1
                continue
            if action == "Attempt Parley":
                self.attempt_parley(actor, enemies, encounter.parley_dc)
                turn_state.actions_remaining -= 1
                continue
            if action == "Try to Flee":
                if self.blocks_movement(actor):
                    self.say(f"{self.style_name(actor)} cannot break away while {self.describe_blocking_condition(actor)} or held fast.")
                    turn_state.actions_remaining -= 1
                    continue
                if turn_state.free_flee:
                    self.apply_status(actor, "emboldened", 1, source="using a clean opening")
                    self.say("You use the ground you bought yourself and lead the party clear of the fight.")
                    self.pause_for_combat_transition()
                    return "fled"
                success = self.skill_check(actor, "Stealth", 13, context="to break from the fight")
                turn_state.actions_remaining -= 1
                if success:
                    self.apply_status(actor, "emboldened", 1, source="finding a clean escape lane")
                    self.say("You find an opening and lead the party out of the melee.")
                    self.pause_for_combat_transition()
                    return "fled"
                self.apply_status(actor, "reeling", 1, source="a failed retreat")
                self.say("The enemies close the gap before you can disengage cleanly.")
                continue

    def turn_prompt(self, actor: Character, turn_state: TurnState) -> str:
        bonus_text = "ready" if turn_state.bonus_action_available else "spent"
        return f"Your turn, {self.style_name(actor)}. Actions left: {turn_state.actions_remaining}. Bonus action: {bonus_text}."

    def combat_option_group(self, option: str) -> str:
        action = self.choice_text(option)
        if action in {
            "Use Martial Arts",
            "Use Flurry of Blows",
            "Use Patient Defense",
            "Use Step of the Wind",
            "Use Cunning Action",
            "Enter Rage",
            "Use Second Wind",
            "Use Bardic Inspiration",
            "Cast Healing Word",
            "Make Off-Hand Attack",
            "Drink a Healing Potion",
        }:
            return "Bonus Action"
        if action in {
            "Use Action Surge",
            "Help a Downed Ally",
            "Use an Item",
            "Attempt Parley",
            "Try to Flee",
            "Take the Dodge action",
            "End Turn",
        }:
            return "Tactical"
        return "Action"

    def build_grouped_combat_keyboard_menu(
        self,
        prompt: str,
        sections: list[tuple[str, list[tuple[int, str]]]],
        *,
        actor: Character | None,
        heroes: list[Character],
        enemies: list[Character],
        selected_index: int,
        typed_buffer: str,
        feedback: str | None,
        show_instructions: bool,
    ):
        hero_lines = [self.describe_combatant(hero) for hero in heroes if not hero.dead]
        enemy_lines = [self.describe_combatant(enemy) for enemy in enemies if not enemy.dead]
        action_items: list[object] = [self.rich_text(prompt, bold=True)]
        if show_instructions:
            action_items.append(
                self.rich_text(
                    "Arrows move. Enter confirms. Type a number or command. Esc clears.",
                    "white",
                    dim=True,
                )
            )
        action_items.append(self.rich_text("", dim=True))
        for section_index, (section, grouped_options) in enumerate(sections):
            action_items.append(self.rich_text(f"{section}:", "light_yellow", bold=True))
            option_table = Table.grid(expand=True, padding=(0, 0))
            option_table.add_column(width=2)
            option_table.add_column(width=3)
            option_table.add_column(ratio=1)
            for display_index, option in grouped_options:
                active = display_index - 1 == selected_index
                marker = self.rich_text("> ", "light_green", bold=True) if active else self.rich_text("  ", dim=True)
                number = self.rich_text(f"{display_index}.", "light_yellow" if active else "white", bold=active)
                label = self.rich_from_ansi(self.format_option_text(option))
                if Text is not None and isinstance(label, Text) and active:
                    label.stylize("bold")
                row_style = "on rgb(28,36,46)" if active else None
                option_table.add_row(marker, number, label, style=row_style)
            action_items.append(option_table)
            if section_index < len(sections) - 1:
                action_items.append(self.rich_text("", dim=True))

        input_line = self.rich_text(f"> {typed_buffer}_", "light_green", bold=True) if typed_buffer else self.rich_text("> ", "white")
        action_items.append(self.rich_text("", dim=True))
        action_items.append(input_line)
        if feedback:
            action_items.append(self.rich_text(feedback, "light_red"))

        party_panel = Panel(
            Group(*(self.rich_from_ansi(line) for line in (hero_lines or ["No one is still standing."]))),
            title=self.rich_text("Party", "light_aqua", bold=True),
            border_style=rich_style_name("light_aqua"),
            box=box.ROUNDED,
            padding=(0, 1),
        )
        action_panel_title = "Action Box" if actor is None else f"{actor.name}'s Turn"
        action_panel = Panel(
            Group(*action_items),
            title=self.rich_text(action_panel_title, "light_yellow", bold=True),
            border_style=rich_style_name("light_yellow"),
            box=box.ROUNDED,
            padding=(0, 1),
        )
        enemy_panel = Panel(
            Group(*(self.rich_from_ansi(line) for line in (enemy_lines or ["Enemies routed."]))),
            title=self.rich_text("Enemies", "light_red", bold=True),
            border_style=rich_style_name("light_red"),
            box=box.ROUNDED,
            padding=(0, 1),
        )
        return self.rich_panel_row_renderable([party_panel, action_panel, enemy_panel], ratios=[3, 4, 3], padding=(0, 1))

    def run_grouped_combat_keyboard_menu(
        self,
        prompt: str,
        options: list[str],
        sections: list[tuple[str, list[tuple[int, str]]]],
        *,
        actor: Character | None,
        heroes: list[Character],
        enemies: list[Character],
    ) -> str | None:
        if not self.keyboard_choice_menu_supported():
            return None
        if Console is None or Live is None or Panel is None or Group is None or Table is None or box is None:
            return None

        selected_index = 0
        typed_buffer = ""
        feedback: str | None = None
        console = Console(
            force_terminal=True,
            color_system="truecolor",
            legacy_windows=False,
            highlight=False,
            width=self.safe_rich_render_width(),
        )
        show_instructions = self.begin_keyboard_choice_session()

        while True:
            submitted_text: str | None = None
            renderable_factory = lambda: self.build_grouped_combat_keyboard_menu(
                prompt,
                sections,
                actor=actor,
                heroes=heroes,
                enemies=enemies,
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
                        self.safe_rich_render_width,
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
                                return options[value - 1]
                        typed_buffer += payload
                        feedback = None
                    elif action == "enter":
                        if typed_buffer.strip():
                            submitted_text = typed_buffer.strip()
                            typed_buffer = ""
                            show_instructions = False
                            break
                        return options[selected_index]
                    if hide_instructions_after_update:
                        show_instructions = False
                    live.update(renderable_factory(), refresh=True)

            if submitted_text is None:
                continue
            if submitted_text.isdigit():
                value = int(submitted_text)
                if 1 <= value <= len(options):
                    return options[value - 1]
            if self.handle_meta_command(submitted_text):
                feedback = None
                continue
            feedback = "Type a listed number, use the arrows, or enter a global command."

    def choose_grouped_combat_option(
        self,
        prompt: str,
        options: list[str],
        *,
        actor: Character | None = None,
        heroes: list[Character] | None = None,
        enemies: list[Character] | None = None,
    ) -> str:
        while True:
            self.output_fn("")
            indexed: dict[int, str] = {}
            sections: list[tuple[str, list[tuple[int, str]]]] = []
            section_lookup: dict[str, list[tuple[int, str]]] = {}
            for display_index, option in enumerate(options, start=1):
                section = self.combat_option_group(option)
                if section not in section_lookup:
                    section_lookup[section] = []
                    sections.append((section, section_lookup[section]))
                section_lookup[section].append((display_index, option))
                indexed[display_index] = option
            if heroes is not None and enemies is not None:
                selected_option = self.run_grouped_combat_keyboard_menu(
                    prompt,
                    options,
                    sections,
                    actor=actor,
                    heroes=heroes,
                    enemies=enemies,
                )
                if selected_option is not None:
                    return selected_option
            rendered_dashboard = False
            if self.rich_enabled() and heroes is not None and enemies is not None and Panel is not None and Group is not None and box is not None:
                hero_lines = [self.describe_combatant(hero) for hero in heroes if not hero.dead]
                enemy_lines = [self.describe_combatant(enemy) for enemy in enemies if not enemy.dead]
                action_lines = [self.rich_from_ansi(prompt), self.rich_text("", dim=True)]
                for section, grouped_options in sections:
                    action_lines.append(self.rich_text(f"{section}:", "light_yellow", bold=True))
                    for display_index, option in grouped_options:
                        action_lines.append(self.rich_from_ansi(f"  {display_index}. {self.format_option_text(option)}"))
                    action_lines.append(self.rich_text("", dim=True))
                party_panel = Panel(
                    Group(*(self.rich_from_ansi(line) for line in (hero_lines or ["No one is still standing."]))),
                    title=self.rich_text("Party", "light_aqua", bold=True),
                    border_style=rich_style_name("light_aqua"),
                    box=box.ROUNDED,
                    padding=(0, 1),
                )
                action_panel_title = "Action Box" if actor is None else f"{actor.name}'s Turn"
                action_panel = Panel(
                    Group(*action_lines[:-1]),
                    title=self.rich_text(action_panel_title, "light_yellow", bold=True),
                    border_style=rich_style_name("light_yellow"),
                    box=box.ROUNDED,
                    padding=(0, 1),
                )
                enemy_panel = Panel(
                    Group(*(self.rich_from_ansi(line) for line in (enemy_lines or ["Enemies routed."]))),
                    title=self.rich_text("Enemies", "light_red", bold=True),
                    border_style=rich_style_name("light_red"),
                    box=box.ROUNDED,
                    padding=(0, 1),
                )
                rendered_dashboard = self.emit_rich_panel_row(
                    [party_panel, action_panel, enemy_panel],
                    ratios=[3, 4, 3],
                    width=self.safe_rich_render_width(),
                )
            if not rendered_dashboard:
                self.say(prompt)
                previous_section = ""
                for display_index, option in enumerate(options, start=1):
                    section = self.combat_option_group(option)
                    if section != previous_section:
                        if previous_section:
                            self.output_fn("")
                        self.output_fn(self.style_text(f"{section}:", "light_yellow"))
                        previous_section = section
                    self.output_fn(f"  {display_index}. {self.format_option_text(option)}")
            self.output_fn("")
            raw = self.read_input("> ").strip()
            if self.handle_meta_command(raw):
                continue
            if raw.isdigit():
                value = int(raw)
                if value in indexed:
                    return indexed[value]
            self.say("Please enter a listed number.")

    def activate_action_surge(self, actor: Character, turn_state: TurnState) -> bool:
        if not actor.spend_resource("action_surge"):
            self.say(f"{self.style_name(actor)} has already spent Action Surge this rest.")
            return False
        turn_state.actions_remaining += 1
        self.say(f"{self.style_name(actor)} digs deep and surges into another action.")
        return True

    def can_make_off_hand_attack(self, actor: Character) -> bool:
        main_hand = self.equipped_weapon_item(actor)
        off_hand = self.equipped_off_hand_weapon_item(actor)
        if main_hand is None or main_hand.weapon is None or off_hand is None:
            return False
        if main_hand.weapon.hands_required >= 2 or off_hand.weapon.hands_required >= 2:
            return False
        if main_hand.weapon.ranged or off_hand.weapon.ranged:
            return False
        return "light" in (main_hand.properties or []) and "light" in (off_hand.properties or [])

    def has_action_item_option(self, actor: Character, heroes: list[Character]) -> bool:
        if self.state is None:
            return False
        for item_id, quantity in self.inventory_dict().items():
            if quantity <= 0 or not get_item(item_id).is_combat_usable():
                continue
            if item_id != "potion_healing":
                return True
            if any(hero is not actor and not hero.dead for hero in heroes):
                return True
        return False

    def companion_turn(
        self,
        actor: Character,
        heroes: list[Character],
        enemies: list[Character],
        encounter: Encounter,
        dodging: set[str],
    ) -> None:
        conscious_enemies = [enemy for enemy in enemies if enemy.is_conscious()]
        if not conscious_enemies:
            return
        if actor.class_name == "Fighter" and actor.resources.get("second_wind", 0) > 0 and actor.current_hp <= actor.max_hp // 2:
            self.use_second_wind(actor)
            return
        if actor.class_name == "Barbarian" and actor.resources.get("rage", 0) > 0 and not self.has_status(actor, "emboldened"):
            self.use_rage(actor)
            return
        if actor.class_name == "Bard" and actor.resources.get("bardic_inspiration", 0) > 0:
            target = min([ally for ally in heroes if ally.is_conscious()], key=lambda ally: ally.current_hp)
            if not self.has_status(target, "blessed"):
                self.use_bardic_inspiration(actor, target)
                return
        if actor.class_name == "Cleric" and has_spell_slots(actor):
            wounded = [ally for ally in heroes if not ally.dead and ally.current_hp < ally.max_hp]
            if wounded:
                target = min(wounded, key=lambda ally: ally.current_hp)
                if target.current_hp <= max(1, target.max_hp // 2):
                    self.cast_cure_wounds(actor, target)
                    return
        if actor.class_name == "Paladin":
            leaders = [enemy for enemy in conscious_enemies if "leader" in enemy.tags]
            if actor.resources.get("channel_divinity", 0) > 0 and leaders:
                self.use_channel_divinity(actor, leaders[0])
                return
            wounded = [ally for ally in heroes if ally.is_conscious() and ally.current_hp < max(1, ally.max_hp // 2)]
            if actor.resources.get("lay_on_hands", 0) > 0 and wounded:
                self.use_lay_on_hands(actor, min(wounded, key=lambda ally: ally.current_hp))
                return
        if actor.class_name == "Wizard":
            leaders = [enemy for enemy in conscious_enemies if "leader" in enemy.tags]
            if has_spell_slots(actor) and leaders:
                self.cast_magic_missile(actor, leaders[0])
                return
            self.cast_fire_bolt(actor, conscious_enemies[0], dodging)
            return
        if actor.class_name == "Bard":
            self.cast_vicious_mockery(actor, conscious_enemies[0])
            return
        if actor.class_name == "Cleric":
            self.cast_sacred_flame(actor, conscious_enemies[0])
            return
        if actor.class_name == "Warlock":
            self.cast_eldritch_blast(actor, conscious_enemies[0], dodging)
            return
        if actor.class_name == "Sorcerer":
            if has_spell_slots(actor):
                self.cast_magic_missile(actor, conscious_enemies[0])
                return
            self.cast_fire_bolt(actor, conscious_enemies[0], dodging)
            return
        if actor.class_name == "Monk":
            self.use_martial_arts(actor, conscious_enemies[0], heroes, enemies, dodging)
            return
        target = min(conscious_enemies, key=lambda enemy: enemy.current_hp)
        self.perform_weapon_attack(actor, target, heroes, enemies, dodging)

    def enemy_turn(
        self,
        actor: Character,
        heroes: list[Character],
        enemies: list[Character],
        encounter: Encounter,
        dodging: set[str],
    ) -> None:
        conscious_heroes = [hero for hero in heroes if hero.is_conscious()]
        if not conscious_heroes:
            return
        conscious_allies = [enemy for enemy in enemies if enemy.is_conscious() and enemy is not actor]
        marked_target = self.marked_priority_target(conscious_heroes)
        if not self.can_make_hostile_action(actor):
            self.say(f"{self.style_name(actor)} falters and cannot press a hostile attack while Charmed.")
            return
        if actor.archetype == "ash_brand_enforcer" and actor.resources.get("punishing_strike", 0) > 0:
            target = next(
                (
                    hero
                    for hero in conscious_heroes
                    if any(self.has_status(hero, status) for status in ("blessed", "emboldened", "invisible"))
                ),
                marked_target,
            )
            if target is not None:
                actor.resources["punishing_strike"] = 0
                self.say(f"{actor.name} lunges at {target.name}, aiming to turn their own momentum against them.")
                hit = self.perform_enemy_attack(actor, target, heroes, enemies, dodging)
                if hit and target.is_conscious():
                    extra = self.apply_damage(
                        target,
                        self.roll_with_display_bonus(
                            "1d6",
                            style="damage",
                            context_label=f"{actor.name}'s punishing strike",
                            outcome_kind="damage",
                        ).total,
                        damage_type="slashing",
                    )
                    self.say(f"{actor.name} drives the opening deeper for {self.style_damage(extra)} extra damage.")
                    self.announce_downed_target(target)
                    if self.has_status(target, "blessed"):
                        self.clear_status(target, "blessed")
                        self.say(f"{target.name}'s blessing gutters out under the hit.")
                return
        if actor.archetype == "brand_saboteur" and actor.resources.get("flash_ash", 0) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["flash_ash"] = 0
            self.say(f"{actor.name} cracks a palmful of flash ash across {target.name}'s face.")
            if not self.saving_throw(target, "CON", 11, context=f"against {actor.name}'s flash ash"):
                self.apply_status(target, "blinded", 1, source=f"{actor.name}'s flash ash")
            else:
                self.say(f"{target.name} coughs through the ash without losing sight of the fight.")
            return
        if (
            actor.archetype == "brand_saboteur"
            and actor.resources.get("retreat_step", 0) > 0
            and actor.current_hp <= max(1, actor.max_hp // 2)
        ):
            actor.resources["retreat_step"] = 0
            self.apply_status(actor, "emboldened", 1, source=f"{actor.name}'s retreat step")
            self.say(f"{actor.name} hooks a boot behind cover, shifts the line, and looks for a cleaner exit.")
            return
        if actor.archetype == "sereth_vane" and actor.resources.get("silver_pressure", 0) > 0:
            target = min(conscious_heroes, key=lambda hero: (hero.current_hp, hero.armor_class))
            actor.resources["silver_pressure"] = 0
            self.say(f"{actor.name} names the price of every life in the chamber until {target.name}'s footing starts to feel negotiable.")
            if not self.saving_throw(target, "WIS", 12, context=f"against {actor.name}'s silver pressure"):
                self.apply_status(target, "reeling", 2, source=f"{actor.name}'s silver pressure")
            else:
                self.say(f"{target.name} refuses to let Sereth turn arithmetic into fear.")
            return
        if actor.archetype == "sereth_vane" and actor.resources.get("command_relocate", 0) > 0 and conscious_allies:
            ally = min(conscious_allies, key=lambda candidate: (candidate.current_hp, candidate.armor_class))
            actor.resources["command_relocate"] = 0
            self.apply_status(ally, "emboldened", 1, source=f"{actor.name}'s relocation order")
            self.say(f"{actor.name} snaps two fingers and sends {ally.name} into a better angle before the line can close.")
            return
        if actor.archetype == "sereth_vane" and actor.resources.get("flash_ash", 0) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["flash_ash"] = 0
            self.say(f"{actor.name} crushes a glass ash capsule underfoot and kicks the burst toward {target.name}.")
            if not self.saving_throw(target, "CON", 12, context=f"against {actor.name}'s flash ash"):
                self.apply_status(target, "blinded", 1, source=f"{actor.name}'s flash ash")
            else:
                self.say(f"{target.name} turns aside before the ash takes their eyes.")
            return
        if actor.archetype == "ember_channeler" and actor.resources.get("ember_mark", 0) > 0 and marked_target is None:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["ember_mark"] = 0
            self.say(f"{actor.name} traces a burning sigil toward {target.name} and lets the whole enemy line see it.")
            if not self.saving_throw(target, "WIS", 12, context=f"against {actor.name}'s ember mark"):
                self.apply_status(target, "marked", 2, source=f"{actor.name}'s ember mark")
                if target.is_conscious():
                    self.apply_status(target, "reeling", 1, source=f"{actor.name}'s ember mark")
            else:
                self.say(f"{target.name} shakes off the worst of the ember sign before it can settle.")
            return
        if actor.archetype == "carrion_stalker" and actor.resources.get("shadow_hide", 0) > 0 and not self.has_status(actor, "invisible"):
            actor.resources["shadow_hide"] = 0
            self.apply_status(actor, "invisible", 1, source=f"{actor.name}'s shadow hide")
            self.say(f"{actor.name} melts back into the blind angles of the fight.")
            return
        if actor.archetype == "cult_lookout" and actor.resources.get("blind_dust", 0) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["blind_dust"] = 0
            self.say(f"{actor.name} snaps a pouch of bitter dust across {target.name}'s line of sight.")
            if not self.saving_throw(target, "DEX", 12, context=f"against {actor.name}'s blinding dust"):
                self.apply_status(target, "blinded", 1, source=f"{actor.name}'s blind dust")
                if target.is_conscious():
                    self.apply_status(target, "reeling", 1, source=f"{actor.name}'s blind dust")
            else:
                self.say(f"{target.name} turns away before the worst of the dust can settle in.")
            return
        if actor.archetype == "cult_lookout" and actor.resources.get("marked_shot", 0) > 0:
            target = min(conscious_heroes, key=lambda hero: (hero.current_hp, hero.armor_class))
            actor.resources["marked_shot"] = 0
            self.apply_status(actor, "emboldened", 1, source=f"{actor.name}'s marked shot")
            self.say(f"{actor.name} exhales, waits for one clean heartbeat, and looses a marked shot at {target.name}.")
            hit = self.perform_enemy_attack(actor, target, heroes, enemies, dodging)
            if hit and target.is_conscious():
                self.apply_status(target, "reeling", 1, source=f"{actor.name}'s marked shot")
            return
        if actor.archetype == "choir_adept" and actor.resources.get("hush_prayer", 0) > 0:
            actor.resources["hush_prayer"] = 0
            self.say(f"{actor.name} intones a hush-prayer that steadies the Quiet Choir line into brutal focus.")
            for ally in [actor, *conscious_allies]:
                self.apply_status(ally, "blessed", 2, source=f"{actor.name}'s hush-prayer")
            return
        if actor.archetype == "choir_adept" and actor.resources.get("discordant_word", 0) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["discordant_word"] = 0
            self.say(f"{actor.name} speaks one wrong note directly into {target.name}'s thoughts.")
            if not self.saving_throw(target, "WIS", 13, context=f"against {actor.name}'s discordant word"):
                actual = self.apply_damage(
                    target,
                    self.roll_with_display_bonus(
                        "2d6",
                        style="damage",
                        context_label=f"{actor.name}'s discordant word",
                        outcome_kind="damage",
                    ).total,
                    damage_type="psychic",
                )
                self.say(f"The word lands like a blade of static, dealing {self.style_damage(actual)} psychic damage to {self.style_name(target)}.")
                self.announce_downed_target(target)
                if target.is_conscious():
                    self.apply_status(target, "frightened", 1, source=f"{actor.name}'s discordant word")
                    self.apply_status(target, "reeling", 2, source=f"{actor.name}'s discordant word")
            else:
                self.say(f"{target.name} forces the whisper back into noise before it can take hold.")
            return
        if actor.archetype == "animated_armor" and actor.resources.get("lockstep_bash", 0) > 0:
            target = min(conscious_heroes, key=lambda hero: (hero.armor_class, hero.current_hp))
            actor.resources["lockstep_bash"] = 0
            self.say(f"{actor.name} advances in perfect mechanical rhythm and crashes forward with a lockstep bash.")
            hit = self.perform_enemy_attack(actor, target, heroes, enemies, dodging)
            if hit and target.is_conscious() and not self.saving_throw(target, "STR", 13, context=f"against {actor.name}'s lockstep bash"):
                self.apply_status(target, "prone", 1, source=f"{actor.name}'s lockstep bash")
            return
        if actor.archetype == "spectral_foreman" and actor.resources.get("hammer_order", 0) > 0 and conscious_allies:
            target_ally = max(conscious_allies, key=lambda ally: (ally.attack_bonus(), ally.current_hp))
            actor.resources["hammer_order"] = 0
            self.say(f"{actor.name} slams a phantom pick against stone and barks an old shift-order at {target_ally.name}.")
            self.apply_status(target_ally, "emboldened", 2, source=f"{actor.name}'s hammer order")
            self.apply_status(actor, "blessed", 1, source=f"{actor.name}'s hammer order")
            return
        if actor.archetype == "spectral_foreman" and actor.resources.get("dead_shift", 0) > 0:
            target = min(conscious_heroes, key=lambda hero: (hero.current_hp, hero.armor_class))
            actor.resources["dead_shift"] = 0
            self.say(f"{actor.name} calls the dead shift back to work, and the cold of old labor falls across {target.name}.")
            if not self.saving_throw(target, "CON", 13, context=f"against {actor.name}'s dead shift"):
                actual = self.apply_damage(
                    target,
                    self.roll_with_display_bonus(
                        "2d6",
                        style="damage",
                        context_label=f"{actor.name}'s dead shift",
                        outcome_kind="damage",
                    ).total,
                    damage_type="necrotic",
                )
                self.say(f"{target.name} is drained for {self.style_damage(actual)} necrotic damage.")
                self.announce_downed_target(target)
                if target.is_conscious():
                    self.apply_status(target, "exhaustion", 1, source=f"{actor.name}'s dead shift")
                    self.apply_status(target, "reeling", 1, source=f"{actor.name}'s dead shift")
            else:
                self.say(f"{target.name} keeps their footing against the graveyard rhythm of the command.")
            return
        if actor.archetype == "starblighted_miner" and actor.resources.get("whisper_glare", 0) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["whisper_glare"] = 0
            self.say(f"{actor.name}'s eyes catch the forge-light wrong, and a whispering glare fixes on {target.name}.")
            if not self.saving_throw(target, "WIS", 13, context=f"against {actor.name}'s whisper glare"):
                self.apply_status(target, "frightened", 1, source=f"{actor.name}'s whisper glare")
                self.apply_status(target, "reeling", 2, source=f"{actor.name}'s whisper glare")
            else:
                self.say(f"{target.name} tears their focus loose before the whisper can sound like their own thought.")
            return
        if actor.archetype == "caldra_voss" and actor.resources.get("shard_veil", 0) > 0 and actor.current_hp <= (actor.max_hp * 2) // 3:
            actor.resources["shard_veil"] = 0
            actor.grant_temp_hp(8)
            self.apply_status(actor, "invisible", 1, source=f"{actor.name}'s shard veil")
            self.apply_status(actor, "blessed", 1, source=f"{actor.name}'s shard veil")
            self.say(f"{actor.name} draws a shard veil across herself and slips sideways through the forge-light.")
            return
        if actor.archetype == "caldra_voss" and actor.resources.get("quiet_choir_rally", 0) > 0 and conscious_allies:
            actor.resources["quiet_choir_rally"] = 0
            self.say(f"{actor.name} lifts her voice and the Quiet Choir answers in one terrible, disciplined breath.")
            for ally in [actor, *conscious_allies]:
                ally.grant_temp_hp(6)
                self.apply_status(ally, "emboldened", 2, source=f"{actor.name}'s rally")
            return
        if actor.archetype == "caldra_voss" and actor.resources.get("obelisk_whisper", 0) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["obelisk_whisper"] = 0
            self.say(f"{actor.name} lets a shard-bent whisper through, aimed only at {target.name}.")
            if not self.saving_throw(target, "WIS", 14, context=f"against {actor.name}'s obelisk whisper"):
                actual = self.apply_damage(
                    target,
                    self.roll_with_display_bonus(
                        "2d8",
                        style="damage",
                        context_label=f"{actor.name}'s obelisk whisper",
                        outcome_kind="damage",
                    ).total,
                    damage_type="psychic",
                )
                self.say(f"The whisper bites deep for {self.style_damage(actual)} psychic damage.")
                self.announce_downed_target(target)
                if target.is_conscious():
                    self.apply_status(target, "frightened", 2, source=f"{actor.name}'s obelisk whisper")
                    self.apply_status(target, "reeling", 2, source=f"{actor.name}'s obelisk whisper")
            else:
                self.say(f"{target.name} hears the shape of the whisper without letting it settle inside.")
            return
        if actor.archetype == "caldra_voss" and actor.resources.get("echo_step", 0) > 0:
            if self.blocks_movement(actor) or self.has_status(actor, "reeling") or actor.current_hp <= actor.max_hp // 2:
                actor.resources["echo_step"] = 0
                for status in ("grappled", "restrained", "prone", "reeling"):
                    self.clear_status(actor, status)
                self.apply_status(actor, "invisible", 1, source=f"{actor.name}'s echo step")
                self.apply_status(actor, "emboldened", 1, source=f"{actor.name}'s echo step")
                self.say(f"{actor.name} blurs into reflected sound and reappears a heartbeat later with the line reset.")
                return
        if actor.archetype == "cinder_kobold" and actor.resources.get("cinder_pot", 0) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["cinder_pot"] = 0
            self.say(f"{actor.name} hurls a clay cinder pot that bursts across {target.name}'s face in hot ash.")
            if not self.saving_throw(target, "DEX", 11, context=f"against {actor.name}'s cinder pot"):
                self.apply_status(target, "blinded", 1, source=f"{actor.name}'s cinder pot")
                if target.is_conscious():
                    self.apply_status(target, "reeling", 1, source=f"{actor.name}'s cinder pot")
            else:
                self.say(f"{target.name} turns aside before the ash can blind them cleanly.")
            return
        if actor.archetype == "mireweb_spider" and actor.resources.get("venom_web", 0) > 0:
            target = min(conscious_heroes, key=lambda hero: (0 if self.has_status(hero, "restrained") else 1, hero.current_hp))
            actor.resources["venom_web"] = 0
            self.say(f"{actor.name} spits a slick sheet of mirewebbing toward {target.name}.")
            if not self.saving_throw(target, "DEX", 11, context=f"against {actor.name}'s mireweb"):
                self.apply_status(target, "restrained", 2, source=f"{actor.name}'s mireweb")
            else:
                self.say(f"{target.name} tears free before the webbing can set.")
            return
        if actor.archetype == "gutter_zealot" and actor.resources.get("blood_prayer", 0) > 0 and actor.current_hp <= actor.max_hp // 2:
            actor.resources["blood_prayer"] = 0
            actor.grant_temp_hp(4)
            self.apply_status(actor, "blessed", 2, source=f"{actor.name}'s blood prayer")
            self.say(f"{actor.name} smears blood across a broken sigil and steadies into fanatic focus.")
            return
        if actor.archetype == "lantern_fen_wisp" and actor.resources.get("lure_glow", 0) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["lure_glow"] = 0
            self.say(f"{actor.name}'s pale glow drifts close, trying to draw {target.name} one bad step off the safe line.")
            if not self.saving_throw(target, "WIS", 12, context=f"against {actor.name}'s lure glow"):
                self.apply_status(target, "charmed", 1, source=f"{actor.name}'s lure glow")
                if target.is_conscious():
                    self.apply_status(target, "reeling", 1, source=f"{actor.name}'s lure glow")
            else:
                self.say(f"{target.name} refuses the ghostlight's invitation.")
            return
        if actor.archetype == "lantern_fen_wisp" and actor.resources.get("vanish", 0) > 0 and actor.current_hp <= actor.max_hp // 2:
            actor.resources["vanish"] = 0
            self.apply_status(actor, "invisible", 1, source=f"{actor.name}'s vanish")
            self.say(f"{actor.name} gutters out and slips invisible across the dark.")
            return
        if actor.archetype == "acidmaw_burrower" and actor.resources.get("acid_spray", 0) > 0:
            target = min(conscious_heroes, key=lambda hero: (hero.current_hp, hero.armor_class))
            actor.resources["acid_spray"] = 0
            self.say(f"{actor.name} rears up and blasts acid across {target.name}.")
            if not self.saving_throw(target, "DEX", 12, context=f"against {actor.name}'s acid spray"):
                actual = self.apply_damage(
                    target,
                    self.roll_with_display_bonus(
                        "2d6",
                        style="damage",
                        context_label=f"{actor.name}'s acid spray",
                        outcome_kind="damage",
                    ).total,
                    damage_type="acid",
                )
                self.say(f"{target.name} takes {self.style_damage(actual)} acid damage from the spray.")
                self.announce_downed_target(target)
                if target.is_conscious():
                    self.apply_status(target, "acid", 2, source=f"{actor.name}'s acid spray")
            else:
                self.say(f"{target.name} dives clear of the worst of the spray.")
            return
        if actor.archetype == "ettervine_webherd" and actor.resources.get("reel_strand", 0) > 0:
            target = min(conscious_heroes, key=lambda hero: (0 if self.has_status(hero, "restrained") else 1, hero.current_hp))
            actor.resources["reel_strand"] = 0
            self.say(f"{actor.name} snaps a root-web strand around {target.name} and hauls hard.")
            if not self.saving_throw(target, "DEX", 13, context=f"against {actor.name}'s reeling strand"):
                if self.has_status(target, "restrained"):
                    self.apply_status(target, "grappled", 1, source=f"{actor.name}'s reeling strand")
                else:
                    self.apply_status(target, "restrained", 2, source=f"{actor.name}'s reeling strand")
            else:
                self.say(f"{target.name} slips the strand before it can lock down.")
            return
        if actor.archetype == "carrion_lash_crawler" and actor.resources.get("carrion_tentacles", 0) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["carrion_tentacles"] = 0
            self.say(f"{actor.name}'s feeder tendrils lash toward {target.name} with grave-cold numbness.")
            if not self.saving_throw(target, "CON", 13, context=f"against {actor.name}'s carrion tentacles"):
                was_poisoned = self.has_status(target, "poisoned")
                self.apply_status(target, "poisoned", 2, source=f"{actor.name}'s carrion tentacles")
                if was_poisoned and target.is_conscious():
                    self.apply_status(target, "paralyzed", 1, source=f"{actor.name}'s carrion tentacles")
            else:
                self.say(f"{target.name} shrugs off the first wave of paralysis.")
            return
        if actor.archetype == "cache_mimic" and actor.resources.get("adhesive_grab", 0) > 0 and not any(self.has_status(hero, "grappled") for hero in conscious_heroes):
            target = min(conscious_heroes, key=lambda hero: (hero.current_hp, hero.armor_class))
            actor.resources["adhesive_grab"] = 0
            self.say(f"{actor.name}'s false lid splits into grasping adhesive cords around {target.name}.")
            if not self.saving_throw(target, "STR", 13, context=f"against {actor.name}'s adhesive lash"):
                self.apply_status(target, "grappled", 2, source=f"{actor.name}'s adhesive lash")
            else:
                self.say(f"{target.name} tears free before the mimic can lock on.")
            return
        if actor.archetype == "stonegaze_skulker" and actor.resources.get("petrifying_gaze", 0) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["petrifying_gaze"] = 0
            self.say(f"{actor.name}'s milky eyes fix on {target.name} with a mineral hunger.")
            if not self.saving_throw(target, "CON", 13, context=f"against {actor.name}'s petrifying gaze"):
                if self.has_status(target, "restrained"):
                    self.apply_status(target, "petrified", 1, source=f"{actor.name}'s petrifying gaze")
                else:
                    self.apply_status(target, "restrained", 1, source=f"{actor.name}'s petrifying gaze")
            else:
                self.say(f"{target.name} breaks the gaze before their limbs can lock.")
            return
        if actor.archetype == "cliff_harpy" and actor.resources.get("luring_song", 0) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["luring_song"] = 0
            self.say(f"{actor.name}'s song cuts through the fight with the ache of a false memory.")
            if not self.saving_throw(target, "WIS", 13, context=f"against {actor.name}'s luring song"):
                self.apply_status(target, "charmed", 1, source=f"{actor.name}'s luring song")
                if target.is_conscious():
                    self.apply_status(target, "reeling", 1, source=f"{actor.name}'s luring song")
            else:
                self.say(f"{target.name} hears the beauty without trusting it.")
            return
        if actor.archetype == "whispermaw_blob":
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            if not self.saving_throw(target, "WIS", 13, context=f"against {actor.name}'s gibbering chorus"):
                self.apply_status(target, "reeling", 1, source=f"{actor.name}'s gibbering chorus")
            if actor.resources.get("blinding_spittle", 0) > 0:
                actor.resources["blinding_spittle"] = 0
                self.say(f"{actor.name} spits a sheet of shining mucus at {target.name}.")
                if not self.saving_throw(target, "DEX", 13, context=f"against {actor.name}'s blinding spittle"):
                    self.apply_status(target, "blinded", 1, source=f"{actor.name}'s blinding spittle")
                else:
                    self.say(f"{target.name} twists clear of the worst of the spittle.")
                return
        if actor.archetype == "blacklake_pincerling" and actor.resources.get("shock_spines", 0) > 0:
            target = next((hero for hero in conscious_heroes if self.has_status(hero, "grappled")), None)
            if target is not None:
                actor.resources["shock_spines"] = 0
                self.say(f"{actor.name}'s shell-spines flare and discharge into {target.name}.")
                if not self.saving_throw(target, "CON", 13, context=f"against {actor.name}'s shock spines"):
                    self.apply_status(target, "paralyzed", 1, source=f"{actor.name}'s shock spines")
                else:
                    self.say(f"{target.name} grits through the numbing pulse.")
                return
        if actor.archetype == "graveblade_wight" and actor.resources.get("sunken_command", 0) > 0 and conscious_allies:
            actor.resources["sunken_command"] = 0
            target_ally = max(conscious_allies, key=lambda ally: (ally.attack_bonus(), ally.current_hp))
            self.say(f"{actor.name} raises a dead captain's blade and snaps an old field order at {target_ally.name}.")
            self.apply_status(target_ally, "emboldened", 2, source=f"{actor.name}'s sunken command")
            return
        if actor.archetype == "graveblade_wight" and actor.resources.get("life_drain", 0) > 0:
            target = min(conscious_heroes, key=lambda hero: (hero.current_hp, hero.armor_class))
            actor.resources["life_drain"] = 0
            self.say(f"{actor.name}'s blade draws a grave-cold arc toward {target.name}.")
            if not self.saving_throw(target, "CON", 14, context=f"against {actor.name}'s life drain"):
                actual = self.apply_damage(
                    target,
                    self.roll_with_display_bonus(
                        "2d6",
                        style="damage",
                        context_label=f"{actor.name}'s life drain",
                        outcome_kind="damage",
                    ).total,
                    damage_type="necrotic",
                )
                self.say(f"{target.name} is drained for {self.style_damage(actual)} necrotic damage.")
                self.announce_downed_target(target)
                if target.is_conscious():
                    self.apply_status(target, "exhaustion", 1, source=f"{actor.name}'s life drain")
            else:
                self.say(f"{target.name} holds onto their breath and blood both.")
            return
        if actor.archetype == "cinderflame_skull" and actor.resources.get("fire_burst", 0) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["fire_burst"] = 0
            self.say(f"{actor.name} detonates a wheel of ember-fire around {target.name}.")
            if not self.saving_throw(target, "DEX", 14, context=f"against {actor.name}'s fire burst"):
                actual = self.apply_damage(
                    target,
                    self.roll_with_display_bonus(
                        "3d6",
                        style="damage",
                        context_label=f"{actor.name}'s fire burst",
                        outcome_kind="damage",
                    ).total,
                    damage_type="fire",
                )
                self.say(f"{target.name} takes {self.style_damage(actual)} fire damage from the burst.")
                self.announce_downed_target(target)
                if target.is_conscious():
                    self.apply_status(target, "burning", 2, source=f"{actor.name}'s fire burst")
            else:
                self.say(f"{target.name} slips through the burst with only scorched air at their back.")
            return
        if actor.archetype == "obelisk_eye":
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            ray = self.rng.choice(("terror", "blinding", "binding"))
            self.say(f"{actor.name} turns and a new shard-ray locks onto {target.name}.")
            if ray == "terror":
                if not self.saving_throw(target, "WIS", 14, context=f"against {actor.name}'s fear ray"):
                    self.apply_status(target, "frightened", 2, source=f"{actor.name}'s fear ray")
                else:
                    self.say(f"{target.name} refuses the ray's pressure.")
            elif ray == "blinding":
                if not self.saving_throw(target, "CON", 14, context=f"against {actor.name}'s blinding ray"):
                    self.apply_status(target, "blinded", 1, source=f"{actor.name}'s blinding ray")
                    if target.is_conscious():
                        self.apply_status(target, "reeling", 1, source=f"{actor.name}'s blinding ray")
                else:
                    self.say(f"{target.name} tears their vision back out of the shard-light.")
            else:
                if not self.saving_throw(target, "STR", 14, context=f"against {actor.name}'s binding ray"):
                    self.apply_status(target, "restrained", 1, source=f"{actor.name}'s binding ray")
                else:
                    self.say(f"{target.name} breaks the ray's grip before it hardens around them.")
            return
        if actor.archetype == "iron_prayer_horror" and actor.resources.get("shield_bash", 0) > 0:
            target = min(conscious_heroes, key=lambda hero: (hero.armor_class, hero.current_hp))
            actor.resources["shield_bash"] = 0
            self.say(f"{actor.name} marches through the line and slams a scripture-stamped shield into {target.name}.")
            hit = self.perform_enemy_attack(actor, target, heroes, enemies, dodging)
            if hit and target.is_conscious() and not self.saving_throw(target, "STR", 14, context=f"against {actor.name}'s shield bash"):
                self.apply_status(target, "prone", 1, source=f"{actor.name}'s shield bash")
                self.apply_status(target, "reeling", 1, source=f"{actor.name}'s shield bash")
            return
        if actor.archetype == "hookclaw_burrower" and actor.resources.get("shriek_pulse", 0) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["shriek_pulse"] = 0
            self.say(f"{actor.name} unleashes a shriek that bounces off every wall at once.")
            if not self.saving_throw(target, "CON", 14, context=f"against {actor.name}'s shriek pulse"):
                self.apply_status(target, "deafened", 2, source=f"{actor.name}'s shriek pulse")
            else:
                self.say(f"{target.name} keeps enough hearing to stay oriented.")
            return
        if actor.archetype == "thunderroot_mound" and actor.resources.get("engulf", 0) > 0:
            target = next((hero for hero in conscious_heroes if self.has_status(hero, "restrained")), None)
            if target is not None:
                actor.resources["engulf"] = 0
                self.say(f"{actor.name} heaves its mass over {target.name} and tries to bury them alive in roots and mud.")
                actual = self.apply_damage(
                    target,
                    self.roll_with_display_bonus(
                        "2d6",
                        style="damage",
                        context_label=f"{actor.name}'s engulf",
                        outcome_kind="damage",
                    ).total,
                    damage_type="bludgeoning",
                )
                self.say(f"{target.name} takes {self.style_damage(actual)} bludgeoning damage inside the crush.")
                self.announce_downed_target(target)
                if target.is_conscious():
                    self.apply_status(target, "grappled", 2, source=f"{actor.name}'s engulf")
                return
        if actor.archetype == "oathbroken_revenant" and actor.resources.get("vengeance_mark", 0) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["vengeance_mark"] = 0
            actor.bond_flags["marked_target"] = target.name
            self.say(f"{actor.name} points its ruined blade at {target.name} and names a debt that death did not cancel.")
            if not self.saving_throw(target, "WIS", 14, context=f"against {actor.name}'s vengeance mark"):
                self.apply_status(target, "reeling", 2, source=f"{actor.name}'s vengeance mark")
            else:
                self.say(f"{target.name} refuses to let the revenant's hatred define the fight.")
            return
        if actor.archetype == "choir_executioner" and actor.resources.get("hush_command", 0) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["hush_command"] = 0
            self.say(f"{actor.name} speaks one verdict, and the air around {target.name} goes murderously still.")
            if not self.saving_throw(target, "WIS", 15, context=f"against {actor.name}'s hush command"):
                self.apply_status(target, "incapacitated", 1, source=f"{actor.name}'s hush command")
            else:
                self.say(f"{target.name} forces movement back into their own limbs.")
            return
        if actor.archetype == "duskmire_matriarch" and actor.resources.get("brood_command", 0) > 0 and conscious_allies:
            actor.resources["brood_command"] = 0
            self.say(f"{actor.name} rattles the cavern with a brood-command that sends every lesser hunter lunging harder.")
            for ally in [actor, *conscious_allies]:
                self.apply_status(ally, "emboldened", 2, source=f"{actor.name}'s brood command")
            return
        if actor.archetype == "duskmire_matriarch" and actor.resources.get("shadow_web", 0) > 0:
            target = min(conscious_heroes, key=lambda hero: (hero.current_hp, hero.armor_class))
            actor.resources["shadow_web"] = 0
            self.say(f"{actor.name} hurls a shadow-thick web that blots out the light around {target.name}.")
            if not self.saving_throw(target, "DEX", 15, context=f"against {actor.name}'s shadow web"):
                self.apply_status(target, "restrained", 2, source=f"{actor.name}'s shadow web")
                if target.is_conscious():
                    self.apply_status(target, "blinded", 1, source=f"{actor.name}'s shadow web")
            else:
                self.say(f"{target.name} cuts free before the web can cocoon them.")
            return
        if actor.archetype == "stirge_swarm":
            attached_to = str(actor.bond_flags.get("attached_to", "")).strip()
            if attached_to:
                target = next((hero for hero in conscious_heroes if hero.name == attached_to), None)
                if target is not None:
                    actual = self.apply_damage(
                        target,
                        self.roll_with_display_bonus(
                            "1d4",
                            style="damage",
                            context_label=f"{actor.name}'s feeding swarm",
                            outcome_kind="damage",
                        ).total,
                        damage_type="piercing",
                    )
                    self.say(f"{actor.name} stays latched onto {target.name} and drains {self.style_damage(actual)} blood from the wound.")
                    self.announce_downed_target(target)
                    if target.is_conscious():
                        self.apply_status(target, "grappled", 2, source=f"{actor.name}'s feeding swarm")
                    else:
                        actor.bond_flags.pop("attached_to", None)
                    return
                actor.bond_flags.pop("attached_to", None)
        if actor.archetype == "vaelith_marr" and actor.resources.get("ritual_surge", 0) > 0:
            actor.resources["ritual_surge"] = 0
            actor.grant_temp_hp(8)
            self.apply_status(actor, "blessed", 2, source=f"{actor.name}'s grave ward")
            if conscious_allies:
                target_ally = max(conscious_allies, key=lambda ally: (ally.attack_bonus(), ally.current_hp))
                self.apply_status(target_ally, "emboldened", 2, source=f"{actor.name}'s grave ward")
            self.say(f"{actor.name} drags soot-black sigils through the air and hardens the line behind a grave ward.")
            return
        if actor.archetype == "vaelith_marr" and actor.resources.get("grave_fear", 1) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["grave_fear"] = 0
            if not self.saving_throw(target, "WIS", 13, context=f"against {actor.name}'s sepulchral chant"):
                self.apply_status(target, "frightened", 2, source=f"{actor.name}'s grave chant")
                self.apply_status(target, "reeling", 1, source=f"{actor.name}'s grave chant")
                self.say(f"{actor.name}'s whisper turns old burial-cold into a command that rattles {target.name} badly.")
                return
        if actor.archetype == "vaelith_marr" and actor.resources.get("ash_veil", 1) > 0:
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
            actor.resources["ash_veil"] = 0
            if not self.saving_throw(target, "CON", 13, context=f"against {actor.name}'s choking ash veil"):
                self.apply_status(target, "blinded", 1, source=f"{actor.name}'s ash veil")
                self.apply_status(target, "reeling", 1, source=f"{actor.name}'s ash veil")
                self.say(f"{actor.name} bursts a veil of hot grave-ash across {target.name}'s face.")
                return
        if actor.archetype == "gravecaller" and actor.resources.get("grave_fear", 1) > 0:
            target = min(conscious_heroes, key=lambda hero: hero.current_hp)
            actor.resources["grave_fear"] = 0
            if not self.saving_throw(target, "WIS", 12, context=f"against {actor.name}'s sepulchral chant"):
                self.apply_status(target, "frightened", 2, source=f"{actor.name}'s grave chant")
                self.say(f"{actor.name}'s whisper drags old burial-cold across {target.name}'s thoughts.")
                return
        if actor.archetype == "gravecaller" and actor.resources.get("ash_veil", 1) > 0:
            target = min(conscious_heroes, key=lambda hero: hero.current_hp)
            actor.resources["ash_veil"] = 0
            if not self.saving_throw(target, "CON", 12, context=f"against {actor.name}'s choking ash veil"):
                self.apply_status(target, "blinded", 1, source=f"{actor.name}'s ash veil")
                self.say(f"A veil of hot grave-ash bursts over {target.name}'s face.")
                return
        if actor.archetype == "orc_bloodchief" and actor.resources.get("war_cry", 1) > 0 and actor.current_hp <= actor.max_hp:
            actor.resources["war_cry"] = 0
            actor.grant_temp_hp(6)
            self.apply_status(actor, "emboldened", 2, source=f"{actor.name}'s war cry")
            self.say(f"{actor.name} hammers a fist to their chest and roars themselves into a killing fury.")
            return
        if actor.archetype == "nothic" and actor.resources.get("weird_insight", 1) > 0:
            target = min(conscious_heroes, key=lambda hero: hero.current_hp)
            actor.resources["weird_insight"] = 0
            if not self.saving_throw(target, "WIS", 12, context=f"against {actor.name}'s hungry stare"):
                self.apply_status(target, "reeling", 2, source=f"{actor.name}'s weird insight")
                self.say(f"{actor.name} speaks a private fear aloud, and {target.name} stumbles under the weight of being seen.")
                return
        if actor.archetype == "nothic" and actor.resources.get("rotting_gaze", 1) > 0:
            target = min(conscious_heroes, key=lambda hero: hero.current_hp)
            actor.resources["rotting_gaze"] = 0
            if not self.saving_throw(target, "CON", 12, context=f"against {actor.name}'s rotting gaze"):
                self.apply_status(target, "poisoned", 2, source=f"{actor.name}'s rotting gaze")
                self.say(f"{target.name} feels flesh and courage both go sick beneath {actor.name}'s stare.")
                return
        if actor.archetype == "varyn" and actor.resources.get("silver_tongue", 1) > 0:
            target = min(conscious_heroes, key=lambda hero: hero.current_hp)
            actor.resources["silver_tongue"] = 0
            if not self.saving_throw(target, "WIS", 12, context=f"against {actor.name}'s silver-tongued lure"):
                self.apply_status(target, "charmed", 1, source=actor.name)
                self.say(f"{actor.name}'s measured voice bends the moment around {target.name}.")
                return
        if actor.archetype == "varyn" and actor.resources.get("binding_hex", 1) > 0:
            target = min(conscious_heroes, key=lambda hero: hero.current_hp)
            actor.resources["binding_hex"] = 0
            if not self.saving_throw(target, "WIS", 12, context=f"against {actor.name}'s binding hex"):
                self.apply_status(target, "incapacitated", 1, source=f"{actor.name}'s binding hex")
                self.say(f"A ring of ash-sigils clamps around {target.name}'s thoughts and locks them in place.")
                return
        if actor.archetype == "varyn" and actor.resources.get("ashen_gaze", 1) > 0:
            target = min(conscious_heroes, key=lambda hero: hero.current_hp)
            actor.resources["ashen_gaze"] = 0
            if not self.saving_throw(target, "CON", 12, context=f"against {actor.name}'s ash-glass gaze"):
                self.apply_status(target, "petrified", 1, source=f"{actor.name}'s ash-glass gaze")
                return
        if actor.archetype == "bandit_archer" and actor.resources.get("snare_shot", 1) > 0:
            target = min(conscious_heroes, key=lambda hero: hero.current_hp)
            actor.resources["snare_shot"] = 0
            if not self.saving_throw(target, "DEX", 12, context=f"against {actor.name}'s weighted line"):
                self.apply_status(target, "restrained", 2, source=f"{actor.name}'s weighted line")
                self.say(f"{actor.name}'s weighted line tangles around {target.name} and holds them fast.")
                return
        if actor.archetype == "bandit_archer" and actor.resources.get("ash_shot", 1) > 0:
            target = min(conscious_heroes, key=lambda hero: hero.current_hp)
            actor.resources["ash_shot"] = 0
            if not self.saving_throw(target, "DEX", 12, context=f"against {actor.name}'s ash-blinding shot"):
                self.apply_status(target, "blinded", 1, source=f"{actor.name}'s ash shot")
                return
        if actor.archetype == "rukhar" and actor.resources.get("war_shout", 1) > 0:
            actor.resources["war_shout"] = 0
            target = min(conscious_heroes, key=lambda hero: hero.current_hp)
            if not self.saving_throw(target, "CON", 12, context=f"against {actor.name}'s iron-bell war shout"):
                self.apply_status(target, "deafened", 2, source=f"{actor.name}'s war shout")
                return
        if actor.archetype == "varyn" and actor.resources.get("rally", 1) > 0 and actor.current_hp <= actor.max_hp // 2:
            actor.resources["rally"] = 0
            actor.grant_temp_hp(6)
            self.apply_status(actor, "emboldened", 2, source="Varyn's rally")
            self.say(f"{actor.name} barks an order and hardens behind 6 temporary hit points.")
            return
        if actor.archetype == "grimlock_tunneler":
            target = min(
                conscious_heroes,
                key=lambda hero: (0 if self.has_status(hero, "reeling") else 1, hero.current_hp, hero.armor_class),
            )
        elif actor.archetype == "hookclaw_burrower":
            target = min(
                conscious_heroes,
                key=lambda hero: (0 if self.has_status(hero, "reeling") else 1, hero.current_hp, hero.armor_class),
            )
        elif actor.archetype == "ochre_slime":
            target = min(
                conscious_heroes,
                key=lambda hero: (0 if self.has_status(hero, "acid") else 1, hero.current_hp, hero.armor_class),
            )
        elif actor.archetype == "rust_shell_scuttler":
            target = min(
                conscious_heroes,
                key=lambda hero: (0 if self.has_status(hero, "acid") else 1, hero.current_hp, hero.armor_class),
            )
        elif actor.archetype == "animated_armor":
            target = min(conscious_heroes, key=lambda hero: (hero.armor_class, hero.current_hp))
        elif actor.archetype == "iron_prayer_horror":
            target = min(conscious_heroes, key=lambda hero: (hero.armor_class, hero.current_hp))
        elif actor.archetype == "thunderroot_mound":
            target = min(
                conscious_heroes,
                key=lambda hero: (0 if self.has_status(hero, "restrained") else 1, hero.current_hp, hero.armor_class),
            )
        elif actor.archetype == "oathbroken_revenant":
            marked = str(actor.bond_flags.get("marked_target", "")).strip()
            target = next((hero for hero in conscious_heroes if hero.name == marked), None)
            if target is None:
                target = min(conscious_heroes, key=lambda hero: hero.current_hp)
        elif actor.archetype == "ash_brand_enforcer":
            target = marked_target or max(
                conscious_heroes,
                key=lambda hero: (
                    1 if any(self.has_status(hero, status) for status in ("blessed", "emboldened", "invisible")) else 0,
                    hero.attack_bonus(),
                    hero.current_hp,
                ),
            )
        elif actor.archetype == "brand_saboteur":
            target = marked_target or min(
                conscious_heroes,
                key=lambda hero: (
                    0 if self.has_status(hero, "blinded") else 1,
                    hero.current_hp,
                    hero.armor_class,
                ),
            )
        elif actor.archetype == "sereth_vane":
            target = marked_target or min(
                conscious_heroes,
                key=lambda hero: (
                    0 if self.has_status(hero, "reeling") else 1,
                    hero.current_hp,
                    hero.armor_class,
                ),
            )
        elif actor.archetype == "ember_channeler":
            target = marked_target or max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
        elif actor.archetype == "carrion_stalker":
            target = marked_target or min(conscious_heroes, key=lambda hero: (hero.current_hp, hero.armor_class))
        elif actor.archetype == "whispermaw_blob":
            target = max(conscious_heroes, key=lambda hero: (hero.attack_bonus(), hero.current_hp))
        else:
            target = min(conscious_heroes, key=lambda hero: hero.current_hp)
        self.perform_enemy_attack(actor, target, heroes, enemies, dodging)

    def get_player_combat_options(
        self,
        actor: Character,
        encounter: Encounter,
        *,
        turn_state: TurnState | None = None,
        heroes: list[Character] | None = None,
    ) -> list[str]:
        turn_state = turn_state or TurnState()
        heroes = heroes or (self.state.party_members() if self.state is not None else [actor])
        options: list[str] = []
        if "action_surge" in actor.features and actor.resources.get("action_surge", 0) > 0:
            options.append("Use Action Surge")
        if turn_state.actions_remaining > 0:
            options.append(f"Attack with {actor.weapon.name}")
            if actor.class_name == "Paladin" and "divine_smite" in actor.features:
                options.append("Attack with Divine Smite")
            if actor.class_name == "Paladin" and actor.resources.get("lay_on_hands", 0) > 0:
                options.append("Use Lay on Hands")
            if actor.class_name == "Cleric":
                if actor.resources.get("channel_divinity", 0) > 0:
                    options.append("Invoke Channel Divinity")
                options.append("Cast Sacred Flame")
                if has_spell_slots(actor) and not turn_state.bonus_action_spell_cast:
                    options.append("Cast Cure Wounds")
            if actor.class_name == "Druid":
                options.append("Cast Produce Flame")
                if has_spell_slots(actor) and not turn_state.bonus_action_spell_cast:
                    options.append("Cast Cure Wounds")
            if actor.class_name == "Bard":
                options.append("Cast Vicious Mockery")
                if has_spell_slots(actor) and not turn_state.bonus_action_spell_cast:
                    options.append("Cast Cure Wounds")
            if actor.class_name == "Sorcerer":
                options.append("Cast Fire Bolt")
                if has_spell_slots(actor) and not turn_state.bonus_action_spell_cast:
                    options.append("Cast Magic Missile")
            if actor.class_name == "Warlock":
                options.append("Cast Eldritch Blast")
            if actor.class_name == "Wizard":
                options.append("Cast Fire Bolt")
                if has_spell_slots(actor) and not turn_state.bonus_action_spell_cast:
                    options.append("Cast Magic Missile")
            if any(hero.current_hp == 0 and not hero.dead for hero in heroes if hero is not actor):
                options.append(self.skill_tag("MEDICINE", "Help a Downed Ally"))
            if self.has_action_item_option(actor, heroes):
                options.append("Use an Item")
            if encounter.allow_parley:
                options.append(self.skill_tag("PERSUASION / INTIMIDATION", "Attempt Parley"))
            if encounter.allow_flee:
                options.append(self.skill_tag("STEALTH", "Try to Flee"))
            options.append("Take the Dodge action")
        if turn_state.bonus_action_available:
            if actor.class_name == "Monk" and turn_state.attack_action_taken:
                options.append("Use Martial Arts")
                if actor.resources.get("ki", 0) > 0:
                    options.append("Use Flurry of Blows")
            if actor.class_name == "Monk" and actor.resources.get("ki", 0) > 0:
                options.append("Use Patient Defense")
                options.append("Use Step of the Wind")
            if "cunning_action" in actor.features:
                options.append("Use Cunning Action")
            if actor.class_name == "Barbarian" and actor.resources.get("rage", 0) > 0 and not self.has_status(actor, "emboldened"):
                options.append("Enter Rage")
            if actor.class_name == "Bard" and actor.resources.get("bardic_inspiration", 0) > 0:
                options.append("Use Bardic Inspiration")
            if actor.class_name == "Fighter" and actor.resources.get("second_wind", 0) > 0:
                options.append("Use Second Wind")
            if actor.class_name in {"Bard", "Cleric", "Druid"} and has_spell_slots(actor) and not turn_state.non_cantrip_action_spell_cast:
                options.append("Cast Healing Word")
            if turn_state.attack_action_taken and self.can_make_off_hand_attack(actor):
                options.append("Make Off-Hand Attack")
            if self.inventory_dict().get("potion_healing", 0) > 0:
                options.append("Drink a Healing Potion")
        options.append("End Turn")
        return options

    def initiative_bonus(self, actor: Character) -> int:
        return (
            actor.equipment_bonuses.get("initiative", 0)
            + actor.gear_bonuses.get("initiative", 0)
            + actor.relationship_bonuses.get("initiative", 0)
        )

    def critical_threshold(self, actor: Character) -> int:
        return 19 if "improved_critical" in actor.features else 20

    def spell_attack_bonus(self, caster: Character, ability: str) -> int:
        return (
            caster.proficiency_bonus
            + caster.ability_mod(ability)
            + caster.equipment_bonuses.get("spell_attack", 0)
            + caster.relationship_bonuses.get("spell_attack", 0)
        )

    def spell_damage_bonus(self, caster: Character) -> int:
        return caster.equipment_bonuses.get("spell_damage", 0) + caster.relationship_bonuses.get("spell_damage", 0)

    def healing_bonus(self, caster: Character) -> int:
        return caster.equipment_bonuses.get("healing", 0) + caster.relationship_bonuses.get("healing", 0)

    def rogue_sneak_attack_dice(self, actor: Character) -> str:
        return "2d6" if actor.level >= 3 else "1d6"

    def choose_target(self, enemies: list[Character], *, prompt: str, allow_back: bool = False) -> Character | None:
        options = [self.describe_combatant(enemy) for enemy in enemies]
        if allow_back:
            options.append("Back")
        index = self.choose(prompt, options, allow_meta=False, show_hud=False)
        if allow_back and index == len(enemies) + 1:
            return None
        return enemies[index - 1]

    def choose_ally(self, allies: list[Character], *, prompt: str, allow_back: bool = False) -> Character | None:
        valid = [ally for ally in allies if not ally.dead]
        options = [self.describe_combatant(ally) for ally in valid]
        if allow_back:
            options.append("Back")
        index = self.choose(prompt, options, allow_meta=False, show_hud=False)
        if allow_back and index == len(valid) + 1:
            return None
        return valid[index - 1]
