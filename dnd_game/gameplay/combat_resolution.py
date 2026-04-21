from __future__ import annotations

from contextlib import contextmanager

from ..dice import D20Outcome, roll, roll_d20
from ..items import ITEMS
from ..ui.colors import rich_style_name
from ..ui.rich_render import Group, Panel, box
from .difficulty_policy import ACT_DIFFICULTY_BANDS, clamp_dc_to_band
from .spell_slots import spend_spell_slot


class CombatResolutionMixin:
    @contextmanager
    def temporary_roll_display_bonus(self, bonus: int):
        with self.temporary_roll_animation_metadata(display_bonus=bonus):
            yield

    def roll_with_display_bonus(
        self,
        expression: str,
        *,
        bonus: int = 0,
        critical: bool = False,
        style: str | None = None,
        context_label: str | None = None,
        outcome_kind: str | None = None,
    ):
        return self.roll_with_animation_context(
            expression,
            bonus=bonus,
            critical=critical,
            style=style,
            context_label=context_label,
            outcome_kind=outcome_kind,
        )

    def equipped_weapon_item(self, actor):
        return ITEMS.get(actor.equipment_slots.get("main_hand", "")) if getattr(actor, "equipment_slots", None) else None

    def equipped_off_hand_weapon_item(self, actor):
        if not getattr(actor, "equipment_slots", None):
            return None
        item = ITEMS.get(actor.equipment_slots.get("off_hand", ""))
        if item is None or item.weapon is None:
            return None
        return item

    def break_invisibility_from_hostile_action(self, actor) -> None:
        if self.has_status(actor, "invisible"):
            self.clear_status(actor, "invisible")
            self.say(f"{self.style_name(actor)} gives away their position by striking.")

    def weapon_attack_ability_for(self, actor, weapon) -> str:
        if weapon.ability == "SPELL":
            return actor.spellcasting_ability or "INT"
        if weapon.ability == "DEX":
            return "DEX"
        if weapon.ability == "FINESSE" or weapon.finesse:
            return "DEX" if actor.ability_mod("DEX") >= actor.ability_mod("STR") else "STR"
        return weapon.ability

    def weapon_attack_bonus_for(self, actor, weapon) -> int:
        return (
            actor.ability_mod(self.weapon_attack_ability_for(actor, weapon))
            + actor.proficiency_bonus
            + weapon.to_hit_bonus
            + actor.equipment_bonuses.get("attack", 0)
            + actor.gear_bonuses.get("attack", 0)
            + actor.relationship_bonuses.get("attack", 0)
        )

    def weapon_damage_bonus_for(self, actor, weapon, *, include_ability_mod: bool = True) -> int:
        ability_mod = actor.ability_mod(self.weapon_attack_ability_for(actor, weapon))
        if not include_ability_mod:
            ability_mod = min(0, ability_mod)
        return (
            ability_mod
            + weapon.damage_bonus
            + actor.equipment_bonuses.get("damage", 0)
            + actor.gear_bonuses.get("damage", 0)
            + actor.relationship_bonuses.get("damage", 0)
        )

    def current_difficulty_act(self) -> int:
        if self.state is None:
            return 1
        return 2 if int(getattr(self.state, "current_act", 1)) >= 2 else 1

    def current_act1_room_role(self) -> str | None:
        dungeon_getter = getattr(self, "current_act1_dungeon", None)
        room_getter = getattr(self, "current_act1_room", None)
        if not callable(dungeon_getter) or not callable(room_getter):
            return None
        try:
            dungeon = dungeon_getter()
            if dungeon is None:
                return None
            room = room_getter(dungeon)
        except Exception:
            return None
        role = str(getattr(room, "role", "")).strip().lower()
        return role or None

    def is_recruitment_check(self, context: str) -> bool:
        lowered = context.lower()
        companion_markers = ("bryn", "nim", "irielle", "kaelis", "rhogar", "tolan")
        return "convince" in lowered and any(marker in lowered for marker in companion_markers)

    def in_boss_difficulty_scene(self) -> bool:
        if self.state is None:
            return False
        room_role = self.current_act1_room_role()
        if room_role == "boss":
            return True
        return self.state.current_scene in {"forge_of_spells"}

    def in_hostile_skill_scene(self) -> bool:
        if self.state is None:
            return False
        room_role = self.current_act1_room_role()
        if room_role is not None:
            return room_role in {"entrance", "combat", "event", "treasure", "boss"}
        return self.state.current_scene in {
            "background_prologue",
            "road_ambush",
            "neverwinter_wood_survey_camp",
            "stonehollow_dig",
            "act2_midpoint_convergence",
            "broken_prospect",
            "south_adit",
            "wave_echo_outer_galleries",
            "black_lake_causeway",
            "forge_of_spells",
        }

    def skill_check_category(self, context: str) -> str:
        if self.is_recruitment_check(context):
            return "recruitment"
        if self.in_boss_difficulty_scene():
            return "boss"
        if getattr(self, "_in_combat", False):
            return "combat"
        if getattr(self, "_random_encounter_active", False):
            return "random"
        if self.in_hostile_skill_scene():
            return "combat"
        return "regular"

    def effective_skill_dc(self, dc: int, *, context: str) -> int:
        if self.state is None:
            return dc
        act = self.current_difficulty_act()
        category = self.skill_check_category(context)
        minimum_tier, maximum_tier = ACT_DIFFICULTY_BANDS[act][category]
        return clamp_dc_to_band(dc, minimum_tier, maximum_tier)

    def ally_pressure_bonus(self, attacker, allies, *, ranged: bool) -> int:
        if not any(ally.is_conscious() and ally is not attacker for ally in allies):
            return 0
        # A light flanking-style bonus keeps the text combat closer to 5e's feel
        # without granting near-constant full advantage.
        return 1 if ranged else 2

    def has_damage_resistance(self, actor, damage_type: str) -> bool:
        if not damage_type:
            return False
        if actor.gear_bonuses.get(f"resist_{damage_type}", 0):
            return True
        return self.has_status(actor, f"resist_{damage_type}")

    def perform_weapon_attack(self, attacker, target, heroes, enemies, dodging, *, use_smite: bool = False) -> None:
        if not self.can_make_hostile_action(attacker):
            self.say(f"{self.style_name(attacker)} can't bring themselves to make a hostile move while Charmed.")
            return
        play_attack_sound_for = getattr(self, "play_attack_sound_for", None)
        if callable(play_attack_sound_for):
            play_attack_sound_for(attacker)
        weapon_item = self.equipped_weapon_item(attacker)
        try:
            advantage = self.attack_advantage_state(attacker, target, heroes, enemies, dodging, ranged=attacker.weapon.ranged)
            target_ac = self.effective_armor_class(target)
            total_modifier = (
                attacker.attack_bonus()
                + self.ally_pressure_bonus(attacker, heroes, ranged=attacker.weapon.ranged)
                + self.status_value(attacker, "attack_bonus")
                - self.status_value(attacker, "attack_penalty")
            )
            d20 = self.roll_check_d20(
                attacker,
                advantage,
                target_number=target_ac,
                target_label=f"AC {target_ac}",
                modifier=total_modifier,
                style="attack",
                outcome_kind="attack",
                context_label=f"{attacker.name} attacks {target.name}",
            )
            total = d20.kept + total_modifier
            if d20.kept == 1:
                self.say(f"{self.style_name(attacker)} misses {self.style_name(target)} outright.")
                return
            critical_hit = d20.kept >= self.critical_threshold(attacker)
            if critical_hit and target.gear_bonuses.get("crit_immunity", 0):
                critical_hit = False
                self.say(f"{self.style_name(target)}'s armor turns a critical hit into a normal one.")
            if not critical_hit and total < target_ac:
                self.say(f"{self.style_name(attacker)} attacks {self.style_name(target)} but misses AC {target_ac}.")
                return
            damage_roll = self.roll_with_display_bonus(
                attacker.weapon.damage,
                bonus=attacker.damage_bonus(),
                critical=critical_hit,
                style="damage",
                context_label=f"{attacker.name} weapon damage",
                outcome_kind="damage",
            )
            weapon_damage = damage_roll.total + attacker.damage_bonus()
            weapon_damage_type = weapon_item.damage_type if weapon_item is not None else ""
            if attacker.class_name == "Rogue" and advantage >= 0 and self.can_sneak_attack(attacker, heroes, target):
                sneak = self.roll_with_animation_context(
                    self.rogue_sneak_attack_dice(attacker),
                    critical=critical_hit,
                    style="damage",
                    context_label=f"{attacker.name} Sneak Attack",
                    outcome_kind="damage",
                )
                weapon_damage += sneak.total
                self.say(f"Sneak Attack adds {self.style_damage(sneak.total)} damage.")
            martial_bonus = None
            smite = None
            if use_smite and attacker.class_name == "Paladin":
                smite_slot_level = spend_spell_slot(attacker, minimum_level=1)
                if smite_slot_level is None:
                    self.say(f"{self.style_name(attacker)} reaches for divine wrath but has no spell slots left.")
                else:
                    smite = self.roll_with_animation_context(
                        f"{smite_slot_level + 1}d8",
                        critical=critical_hit,
                        style="damage",
                        context_label="Divine Smite",
                        outcome_kind="damage",
                    )
                    self.say(f"Divine Smite adds {self.style_damage(smite.total)} radiant damage.")
            if attacker.archetype == "rukhar" and any(enemy.is_conscious() and enemy is not attacker for enemy in enemies):
                martial_bonus = self.roll_with_animation_context(
                    "2d6",
                    style="damage",
                    context_label=f"{attacker.name} martial advantage",
                    outcome_kind="damage",
                )
                weapon_damage += martial_bonus.total
                self.say(f"{self.style_name(attacker)}'s martial advantage adds {self.style_damage(martial_bonus.total)} damage.")
            total_actual = self.apply_damage(target, max(1, weapon_damage), damage_type=weapon_damage_type)
            if smite is not None:
                total_actual += self.apply_damage(target, smite.total, damage_type="radiant")
            if weapon_item is not None and weapon_item.extra_damage_dice:
                extra = self.roll_with_animation_context(
                    weapon_item.extra_damage_dice,
                    critical=critical_hit,
                    style="damage",
                    context_label=f"{weapon_item.enchantment or weapon_item.name} bonus damage",
                    outcome_kind="damage",
                )
                extra_actual = self.apply_damage(target, extra.total, damage_type=weapon_item.extra_damage_type)
                total_actual += extra_actual
                self.say(
                    f"{weapon_item.enchantment or weapon_item.name} adds {self.style_damage(extra_actual)} "
                    f"{weapon_item.extra_damage_type or 'magic'} damage."
                )
            if critical_hit and weapon_item is not None and weapon_item.crit_extra_damage_dice:
                vicious = self.roll_with_animation_context(
                    weapon_item.crit_extra_damage_dice,
                    style="damage",
                    context_label=f"{weapon_item.enchantment or weapon_item.name} critical damage",
                    outcome_kind="damage",
                )
                vicious_actual = self.apply_damage(target, vicious.total, damage_type=weapon_damage_type)
                total_actual += vicious_actual
                self.say(f"{weapon_item.enchantment or weapon_item.name} tears in for {self.style_damage(vicious_actual)} extra critical damage.")
            self.say(f"{self.style_name(attacker)} hits {self.style_name(target)} for {self.style_damage(total_actual)} damage.")
            self.announce_downed_target(target)
            if attacker.archetype in {"rukhar", "varyn"}:
                self.apply_poison_on_hit(attacker, target)
            if attacker.weapon.ranged or "bow" in attacker.weapon.name.lower():
                return
            if d20.kept >= 18 and target.is_conscious():
                self.apply_status(target, "reeling", 1, source=attacker.name)
        finally:
            self.break_invisibility_from_hostile_action(attacker)

    def perform_enemy_attack(self, attacker, target, heroes, enemies, dodging) -> bool:
        play_attack_sound_for = getattr(self, "play_attack_sound_for", None)
        if callable(play_attack_sound_for):
            play_attack_sound_for(attacker)
        weapon_item = self.equipped_weapon_item(attacker)
        advantage = self.attack_advantage_state(attacker, target, heroes, enemies, dodging, ranged=attacker.weapon.ranged)
        target_ac = self.effective_armor_class(target)
        total_modifier = (
            attacker.attack_bonus()
            + self.ally_pressure_bonus(attacker, enemies, ranged=attacker.weapon.ranged)
            + self.status_value(attacker, "attack_bonus")
            - self.status_value(attacker, "attack_penalty")
        )
        d20 = self.roll_check_d20(
            attacker,
            advantage,
            target_number=target_ac,
            target_label=f"AC {target_ac}",
            modifier=total_modifier,
            style="attack",
            outcome_kind="attack",
            context_label=f"{attacker.name} attacks {target.name}",
        )
        total = d20.kept + total_modifier
        critical_hit = d20.kept == 20 and not target.gear_bonuses.get("crit_immunity", 0)
        if d20.kept == 1 or (not critical_hit and d20.kept != 20 and total < target_ac):
            self.say(f"{self.style_name(attacker)} fails to land a hit on {self.style_name(target)}.")
            return False
        if d20.kept == 20 and not critical_hit:
            self.say(f"{self.style_name(target)}'s armor blunts what would have been a critical strike.")
        damage_roll = self.roll_with_display_bonus(
            attacker.weapon.damage,
            bonus=attacker.damage_bonus(),
            critical=critical_hit,
            style="damage",
            context_label=f"{attacker.name} weapon damage",
            outcome_kind="damage",
        )
        damage = max(1, damage_roll.total + attacker.damage_bonus())
        if self.has_status(target, "marked"):
            damage += 2
            self.say(f"The ember mark on {target.name} flares and gives {attacker.name} a cleaner wound to drive into.")
        actual = self.apply_damage(target, damage, damage_type=weapon_item.damage_type if weapon_item is not None else "")
        self.say(f"{self.style_name(attacker)} hits {self.style_name(target)} for {self.style_damage(actual)} damage.")
        self.announce_downed_target(target)
        if attacker.archetype == "ashstone_percher" and attacker.resources.get("drop_strike", 0) > 0 and target.is_conscious():
            attacker.resources["drop_strike"] = 0
            extra = self.apply_damage(
                target,
                self.roll_with_display_bonus(
                    "1d4",
                    style="damage",
                    context_label=f"{attacker.name} drop strike",
                    outcome_kind="damage",
                ).total,
                damage_type="slashing",
            )
            self.say(f"{attacker.name} crashes down from above for {self.style_damage(extra)} extra slashing damage.")
            self.announce_downed_target(target)
        if attacker.archetype == "bugbear_reaver" and attacker.resources.get("surprise_attack", 0) > 0 and target.is_conscious():
            attacker.resources["surprise_attack"] = 0
            extra = self.apply_damage(
                target,
                self.roll_with_display_bonus(
                    "2d6",
                    critical=critical_hit,
                    style="damage",
                    context_label=f"{attacker.name} ambush damage",
                    outcome_kind="damage",
                ).total,
                damage_type="bludgeoning",
            )
            self.say(f"{attacker.name} turns the first clean opening into {self.style_damage(extra)} extra ambush damage.")
            self.announce_downed_target(target)
        if attacker.archetype in {"wolf", "worg"} and target.is_conscious():
            if not self.saving_throw(target, "STR", 11, context=f"against {attacker.name}'s mauling rush"):
                self.apply_status(target, "prone", 1, source=attacker.name)
        if attacker.archetype == "briar_twig" and target.is_conscious():
            if not self.saving_throw(target, "STR", 11, context=f"against {attacker.name}'s snagging thorns"):
                self.apply_status(target, "reeling", 2, source=f"{attacker.name}'s snagging thorns")
        if attacker.archetype == "carrion_stalker" and target.is_conscious():
            self.apply_status(target, "bleeding", 2, source=f"{attacker.name}'s serrated talons")
        if attacker.archetype == "bandit" and d20.kept >= 18 and target.is_conscious():
            if not self.saving_throw(target, "STR", 11, context=f"against {attacker.name}'s clinch"):
                self.apply_status(target, "grappled", 1, source=attacker.name)
        if attacker.archetype == "acidmaw_burrower" and target.is_conscious():
            if not self.saving_throw(target, "STR", 12, context=f"against {attacker.name}'s burrowing clamp"):
                self.apply_status(target, "grappled", 1, source=f"{attacker.name}'s burrowing clamp")
        if attacker.archetype == "rust_shell_scuttler" and target.is_conscious():
            if self.has_status(target, "acid"):
                extra = self.apply_damage(
                    target,
                    self.roll_with_display_bonus(
                        "1d4",
                        style="damage",
                        context_label=f"{attacker.name} acid bite",
                        outcome_kind="damage",
                    ).total,
                    damage_type="acid",
                )
                self.say(f"{attacker.name} worries an already-corroded weak point for {self.style_damage(extra)} extra acid damage.")
                self.announce_downed_target(target)
            self.apply_status(target, "acid", 2, source=f"{attacker.name}'s rust-bite")
        if attacker.archetype == "ogre_brute" and d20.kept >= 18 and target.is_conscious():
            if not self.saving_throw(target, "STR", 12, context=f"against {attacker.name}'s club smash"):
                self.apply_status(target, "prone", 1, source=attacker.name)
        if attacker.archetype == "nothic" and d20.kept >= 18 and target.is_conscious():
            if not self.saving_throw(target, "WIS", 12, context=f"against {attacker.name}'s invasive whisper"):
                self.apply_status(target, "frightened", 1, source=attacker.name)
        if attacker.archetype in {"rukhar", "varyn", "mireweb_spider", "ettervine_webherd", "duskmire_matriarch"}:
            self.apply_poison_on_hit(attacker, target)
        if attacker.archetype == "cache_mimic" and target.is_conscious():
            if attacker.resources.get("adhesive_grab", 0) > 0:
                attacker.resources["adhesive_grab"] = 0
            if not self.saving_throw(target, "STR", 13, context=f"against {attacker.name}'s adhesive bite"):
                self.apply_status(target, "grappled", 2, source=f"{attacker.name}'s adhesive bite")
        if attacker.archetype == "stonegaze_skulker" and target.is_conscious() and self.has_status(target, "restrained"):
            extra = self.apply_damage(
                target,
                self.roll_with_display_bonus(
                    "1d4",
                    style="damage",
                    context_label=f"{attacker.name} venom",
                    outcome_kind="damage",
                ).total,
                damage_type="poison",
            )
            self.say(f"{attacker.name}'s mineral venom bites deeper for {self.style_damage(extra)} poison damage.")
            self.announce_downed_target(target)
        if attacker.archetype == "grimlock_tunneler" and target.is_conscious():
            if self.has_status(target, "reeling") or d20.kept >= 18:
                if not self.saving_throw(target, "STR", 12, context=f"against {attacker.name}'s hooked drag"):
                    self.apply_status(target, "grappled", 2, source=f"{attacker.name}'s hooked drag")
        if attacker.archetype == "hookclaw_burrower" and target.is_conscious():
            if not self.saving_throw(target, "STR", 14, context=f"against {attacker.name}'s cave drag"):
                already_grappled = self.has_status(target, "grappled")
                self.apply_status(target, "grappled", 2, source=f"{attacker.name}'s cave drag")
                if already_grappled:
                    self.apply_status(target, "prone", 1, source=f"{attacker.name}'s cave drag")
        if attacker.archetype == "stirge_swarm" and target.is_conscious():
            attacker.bond_flags["attached_to"] = target.name
            self.apply_status(target, "grappled", 2, source=f"{attacker.name}'s feeding swarm")
            self.say(f"{attacker.name} latches onto {target.name} and begins feeding.")
        if attacker.archetype == "ochre_slime" and target.is_conscious():
            acid = self.apply_damage(
                target,
                self.roll_with_display_bonus(
                    "1d4",
                    style="damage",
                    context_label=f"{attacker.name} corrosive slime",
                    outcome_kind="damage",
                ).total,
                damage_type="acid",
            )
            self.say(f"{attacker.name}'s dripping pseudopod burns for an extra {self.style_damage(acid)} acid damage.")
            self.apply_status(target, "acid", 2, source=f"{attacker.name}'s corrosive slime")
            self.announce_downed_target(target)
        if attacker.archetype == "animated_armor" and target.is_conscious() and d20.kept >= 18:
            if not self.saving_throw(target, "STR", 13, context=f"against {attacker.name}'s driving slam"):
                self.apply_status(target, "prone", 1, source=f"{attacker.name}'s driving slam")
        if attacker.archetype == "cliff_harpy" and target.is_conscious() and attacker.resources.get("swoop", 0) > 0:
            attacker.resources["swoop"] = 0
            if not self.saving_throw(target, "STR", 12, context=f"against {attacker.name}'s swooping pass"):
                self.apply_status(target, "prone", 1, source=f"{attacker.name}'s swoop")
        if attacker.archetype == "whispermaw_blob" and target.is_conscious() and d20.kept >= 18:
            if not self.saving_throw(target, "STR", 13, context=f"against {attacker.name}'s warped bulk"):
                self.apply_status(target, "prone", 1, source=f"{attacker.name}'s warped bulk")
        if attacker.archetype == "blacklake_pincerling" and target.is_conscious():
            if not self.saving_throw(target, "STR", 13, context=f"against {attacker.name}'s pincer hold"):
                self.apply_status(target, "grappled", 2, source=f"{attacker.name}'s pincer hold")
        if attacker.archetype == "thunderroot_mound" and target.is_conscious():
            if not self.saving_throw(target, "STR", 14, context=f"against {attacker.name}'s grasping roots"):
                self.apply_status(target, "restrained", 2, source=f"{attacker.name}'s grasping roots")
        if attacker.archetype == "oathbroken_revenant" and target.is_conscious():
            if target.name == str(attacker.bond_flags.get("marked_target", "")):
                extra = self.apply_damage(
                    target,
                    self.roll_with_display_bonus(
                        "1d6",
                        style="damage",
                        context_label=f"{attacker.name}'s vendetta",
                        outcome_kind="damage",
                    ).total,
                    damage_type="necrotic",
                )
                self.say(f"{attacker.name}'s vendetta cuts deeper for {self.style_damage(extra)} necrotic damage.")
                self.announce_downed_target(target)
        if attacker.archetype == "choir_executioner" and target.is_conscious():
            if any(self.has_status(target, status) for status in ("frightened", "restrained", "incapacitated")):
                extra = self.apply_damage(
                    target,
                    self.roll_with_display_bonus(
                        "2d6",
                        style="damage",
                        context_label=f"{attacker.name}'s execution strike",
                        outcome_kind="damage",
                    ).total,
                    damage_type="slashing",
                )
                self.say(f"{attacker.name} turns the opening into {self.style_damage(extra)} extra execution damage.")
                self.announce_downed_target(target)
        if attacker.archetype == "lantern_fen_wisp" and target.is_conscious() and attacker.resources.get("vanish", 0) > 0 and attacker.current_hp <= attacker.max_hp // 2:
            attacker.resources["vanish"] = 0
            self.apply_status(attacker, "invisible", 1, source=f"{attacker.name}'s vanish")
        return True

    def cast_sacred_flame(self, caster, target) -> None:
        if not self.can_make_hostile_action(caster):
            self.say(f"{self.style_name(caster)} hesitates and cannot turn Sacred Flame on an enemy while Charmed.")
            return
        play_attack_sound_for = getattr(self, "play_attack_sound_for", None)
        if callable(play_attack_sound_for):
            play_attack_sound_for(caster)
        dc = 8 + caster.proficiency_bonus + caster.ability_mod("WIS")
        success = self.saving_throw(target, "DEX", dc, context="against Sacred Flame")
        if success:
            self.say(f"{self.style_name(target)} slips clear of the radiant burst.")
            return
        actual = self.apply_damage(
            target,
            self.roll_with_display_bonus(
                "1d8",
                bonus=self.spell_damage_bonus(caster),
                style="damage",
                context_label="Sacred Flame",
                outcome_kind="damage",
            ).total
            + self.spell_damage_bonus(caster),
        )
        self.say(f"Sacred Flame burns {self.style_name(target)} for {self.style_damage(actual)} radiant damage.")
        self.announce_downed_target(target)
        if target.is_conscious():
            self.apply_status(target, "reeling", 1, source="radiant force")

    def cast_cure_wounds(self, caster, target) -> None:
        slot_level = spend_spell_slot(caster, minimum_level=1)
        if slot_level is None:
            self.say(f"{self.style_name(caster)} is out of spell slots.")
            return
        ability = "CHA" if caster.class_name in {"Bard", "Paladin"} else "WIS"
        amount = self.roll_with_animation_context(
            f"{slot_level}d8",
            style="healing",
            context_label="Cure Wounds",
            outcome_kind="healing",
        ).total + caster.ability_mod(ability) + self.healing_bonus(caster)
        healed = target.heal(max(1, amount))
        play_heal_sound_for = getattr(self, "play_heal_sound_for", None)
        if healed > 0 and callable(play_heal_sound_for):
            play_heal_sound_for(caster)
        self.say(f"{self.style_name(caster)} restores {self.style_healing(healed)} hit points to {self.style_name(target)}.")

    def cast_healing_word(self, caster, target) -> None:
        slot_level = spend_spell_slot(caster, minimum_level=1)
        if slot_level is None:
            self.say(f"{self.style_name(caster)} is out of spell slots.")
            return
        ability = "CHA" if caster.class_name == "Bard" else "WIS"
        amount = self.roll_with_animation_context(
            f"{slot_level}d4",
            style="healing",
            context_label="Healing Word",
            outcome_kind="healing",
        ).total + caster.ability_mod(ability) + self.healing_bonus(caster)
        healed = target.heal(max(1, amount))
        play_heal_sound_for = getattr(self, "play_heal_sound_for", None)
        if healed > 0 and callable(play_heal_sound_for):
            play_heal_sound_for(caster)
        self.say(f"{self.style_name(caster)} calls out a quick healing word and restores {self.style_healing(healed)} hit points to {self.style_name(target)}.")

    def cast_fire_bolt(self, caster, target, dodging) -> None:
        if not self.can_make_hostile_action(caster):
            self.say(f"{self.style_name(caster)} cannot hurl Fire Bolt at an enemy while Charmed.")
            return
        play_attack_sound_for = getattr(self, "play_attack_sound_for", None)
        if callable(play_attack_sound_for):
            play_attack_sound_for(caster)
        try:
            attack_bonus = self.spell_attack_bonus(caster, "INT")
            advantage = self.attack_advantage_state(caster, target, self.state.party_members(), [target], dodging, ranged=True)
            target_ac = self.effective_armor_class(target)
            total_modifier = (
                attack_bonus
                + self.ally_pressure_bonus(caster, self.state.party_members(), ranged=True)
                + self.status_value(caster, "attack_bonus")
                - self.status_value(caster, "attack_penalty")
            )
            d20 = self.roll_check_d20(
                caster,
                advantage,
                target_number=target_ac,
                target_label=f"AC {target_ac}",
                modifier=total_modifier,
                style="attack",
                outcome_kind="attack",
                context_label=f"{caster.name} casts Fire Bolt",
            )
            total = d20.kept + total_modifier
            if d20.kept == 1 or (d20.kept != 20 and total < target_ac):
                self.say(f"{self.style_name(caster)}'s Fire Bolt misses {self.style_name(target)}.")
                return
            actual = self.apply_damage(
                target,
                self.roll_with_display_bonus(
                    "1d10",
                    bonus=self.spell_damage_bonus(caster),
                    critical=d20.kept == 20,
                    style="damage",
                    context_label="Fire Bolt damage",
                    outcome_kind="damage",
                ).total
                + self.spell_damage_bonus(caster),
            )
            self.say(f"Fire Bolt scorches {self.style_name(target)} for {self.style_damage(actual)} fire damage.")
            self.announce_downed_target(target)
            if target.is_conscious():
                self.apply_status(target, "burning", 2, source="Fire Bolt")
        finally:
            self.break_invisibility_from_hostile_action(caster)

    def cast_produce_flame(self, caster, target, dodging) -> None:
        if not self.can_make_hostile_action(caster):
            self.say(f"{self.style_name(caster)} cannot lash out with Produce Flame while Charmed.")
            return
        play_attack_sound_for = getattr(self, "play_attack_sound_for", None)
        if callable(play_attack_sound_for):
            play_attack_sound_for(caster)
        try:
            attack_bonus = self.spell_attack_bonus(caster, "WIS")
            advantage = self.attack_advantage_state(caster, target, self.state.party_members(), [target], dodging, ranged=True)
            target_ac = self.effective_armor_class(target)
            total_modifier = (
                attack_bonus
                + self.ally_pressure_bonus(caster, self.state.party_members(), ranged=True)
                + self.status_value(caster, "attack_bonus")
                - self.status_value(caster, "attack_penalty")
            )
            d20 = self.roll_check_d20(
                caster,
                advantage,
                target_number=target_ac,
                target_label=f"AC {target_ac}",
                modifier=total_modifier,
                style="attack",
                outcome_kind="attack",
                context_label=f"{caster.name} hurls Produce Flame",
            )
            total = d20.kept + total_modifier
            if d20.kept == 1 or (d20.kept != 20 and total < target_ac):
                self.say(f"{self.style_name(caster)}'s Produce Flame misses {self.style_name(target)}.")
                return
            actual = self.apply_damage(
                target,
                self.roll_with_display_bonus(
                    "1d8",
                    bonus=self.spell_damage_bonus(caster),
                    critical=d20.kept == 20,
                    style="damage",
                    context_label="Produce Flame damage",
                    outcome_kind="damage",
                ).total
                + self.spell_damage_bonus(caster),
            )
            self.say(f"Produce Flame sears {self.style_name(target)} for {self.style_damage(actual)} fire damage.")
            self.announce_downed_target(target)
            if target.is_conscious():
                self.apply_status(target, "burning", 2, source="Produce Flame")
        finally:
            self.break_invisibility_from_hostile_action(caster)

    def cast_magic_missile(self, caster, target) -> None:
        if not self.can_make_hostile_action(caster):
            self.say(f"{self.style_name(caster)} cannot direct Magic Missile at an enemy while Charmed.")
            return
        play_attack_sound_for = getattr(self, "play_attack_sound_for", None)
        if callable(play_attack_sound_for):
            play_attack_sound_for(caster)
        try:
            slot_level = spend_spell_slot(caster, minimum_level=1)
            if slot_level is None:
                self.say(f"{self.style_name(caster)} is out of spell slots.")
                return
            dart_count = slot_level + 2
            actual = self.apply_damage(
                target,
                self.roll_with_display_bonus(
                    f"{dart_count}d4+{dart_count}",
                    bonus=self.spell_damage_bonus(caster),
                    style="damage",
                    context_label="Magic Missile",
                    outcome_kind="damage",
                ).total
                + self.spell_damage_bonus(caster),
            )
            self.say(f"Magic Missile slams into {self.style_name(target)} for {self.style_damage(actual)} force damage.")
            self.announce_downed_target(target)
        finally:
            self.break_invisibility_from_hostile_action(caster)

    def cast_vicious_mockery(self, caster, target) -> None:
        if not self.can_make_hostile_action(caster):
            self.say(f"{self.style_name(caster)} cannot weaponize a cutting remark while Charmed.")
            return
        play_attack_sound_for = getattr(self, "play_attack_sound_for", None)
        if callable(play_attack_sound_for):
            play_attack_sound_for(caster)
        try:
            dc = 8 + caster.proficiency_bonus + caster.ability_mod("CHA")
            success = self.saving_throw(target, "WIS", dc, context="against Vicious Mockery")
            if success:
                self.say(f"{self.style_name(target)} bites back a wince and resists the mockery.")
                return
            actual = self.apply_damage(
                target,
                self.roll_with_display_bonus(
                    "1d6",
                    bonus=self.spell_damage_bonus(caster),
                    style="damage",
                    context_label="Vicious Mockery",
                    outcome_kind="damage",
                ).total
                + self.spell_damage_bonus(caster),
                damage_type="psychic",
            )
            self.say(f"{self.style_name(caster)}'s mockery rattles {self.style_name(target)} for {self.style_damage(actual)} psychic damage.")
            self.announce_downed_target(target)
            if target.is_conscious():
                self.apply_status(target, "reeling", 2, source="humiliating mockery")
        finally:
            self.break_invisibility_from_hostile_action(caster)

    def cast_eldritch_blast(self, caster, target, dodging) -> None:
        if not self.can_make_hostile_action(caster):
            self.say(f"{self.style_name(caster)} cannot level Eldritch Blast at an enemy while Charmed.")
            return
        play_attack_sound_for = getattr(self, "play_attack_sound_for", None)
        if callable(play_attack_sound_for):
            play_attack_sound_for(caster)
        try:
            attack_bonus = self.spell_attack_bonus(caster, "CHA")
            advantage = self.attack_advantage_state(caster, target, self.state.party_members(), [target], dodging, ranged=True)
            target_ac = self.effective_armor_class(target)
            total_modifier = (
                attack_bonus
                + self.ally_pressure_bonus(caster, self.state.party_members(), ranged=True)
                + self.status_value(caster, "attack_bonus")
                - self.status_value(caster, "attack_penalty")
            )
            d20 = self.roll_check_d20(
                caster,
                advantage,
                target_number=target_ac,
                target_label=f"AC {target_ac}",
                modifier=total_modifier,
                style="attack",
                outcome_kind="attack",
                context_label=f"{caster.name} casts Eldritch Blast",
            )
            total = d20.kept + total_modifier
            if d20.kept == 1 or (d20.kept != 20 and total < target_ac):
                self.say(f"{self.style_name(caster)}'s Eldritch Blast tears sparks from stone but misses {self.style_name(target)}.")
                return
            actual = self.apply_damage(
                target,
                self.roll_with_display_bonus(
                    "1d10",
                    bonus=self.spell_damage_bonus(caster),
                    critical=d20.kept == 20,
                    style="damage",
                    context_label="Eldritch Blast damage",
                    outcome_kind="damage",
                ).total
                + self.spell_damage_bonus(caster),
                damage_type="force",
            )
            self.say(f"Eldritch Blast hammers {self.style_name(target)} for {self.style_damage(actual)} force damage.")
            self.announce_downed_target(target)
            if target.is_conscious():
                self.apply_status(target, "reeling", 1, source="eldritch impact")
        finally:
            self.break_invisibility_from_hostile_action(caster)

    def use_rage(self, actor) -> None:
        if not actor.spend_resource("rage"):
            self.say(f"{self.style_name(actor)} has no rage left to draw on.")
            return
        actor.grant_temp_hp(4 + actor.level)
        self.apply_status(actor, "emboldened", 3, source="rage")
        self.say(f"{self.style_name(actor)} flies into a rage, taking {self.style_healing(actor.temp_hp)} temporary hit points with it.")

    def use_bardic_inspiration(self, actor, target) -> None:
        if not actor.spend_resource("bardic_inspiration"):
            self.say(f"{self.style_name(actor)} has no Bardic Inspiration left.")
            return
        self.apply_status(target, "blessed", 2, source=f"{actor.name}'s inspiration")
        self.say(f"{self.style_name(actor)} lifts {self.style_name(target)} with a sharp line and steadier rhythm.")

    def use_martial_arts(self, attacker, target, heroes, enemies, dodging) -> None:
        if not self.can_make_hostile_action(attacker):
            self.say(f"{self.style_name(attacker)} cannot lash out with a martial arts strike while Charmed.")
            return
        play_attack_sound_for = getattr(self, "play_attack_sound_for", None)
        if callable(play_attack_sound_for):
            play_attack_sound_for(attacker)
        try:
            advantage = self.attack_advantage_state(attacker, target, heroes, enemies, dodging, ranged=False)
            target_ac = self.effective_armor_class(target)
            total_modifier = (
                self.weapon_attack_bonus_for(attacker, attacker.weapon)
                + self.ally_pressure_bonus(attacker, heroes, ranged=False)
                + self.status_value(attacker, "attack_bonus")
                - self.status_value(attacker, "attack_penalty")
            )
            d20 = self.roll_check_d20(
                attacker,
                advantage,
                target_number=target_ac,
                target_label=f"AC {target_ac}",
                modifier=total_modifier,
                style="attack",
                outcome_kind="attack",
                context_label=f"{attacker.name} martial arts strike",
            )
            total = d20.kept + total_modifier
            critical_hit = d20.kept >= self.critical_threshold(attacker)
            if d20.kept == 1 or (not critical_hit and d20.kept != 20 and total < target_ac):
                self.say(f"{self.style_name(attacker)}'s martial arts strike misses {self.style_name(target)}.")
                return
            damage_roll = self.roll_with_display_bonus(
                "1d4",
                bonus=self.weapon_damage_bonus_for(attacker, attacker.weapon),
                critical=critical_hit,
                style="damage",
                context_label=f"{attacker.name} martial arts damage",
                outcome_kind="damage",
            )
            actual = self.apply_damage(
                target,
                max(1, damage_roll.total + self.weapon_damage_bonus_for(attacker, attacker.weapon)),
                damage_type="bludgeoning",
            )
            self.say(f"{self.style_name(attacker)} snaps in with a martial arts strike for {self.style_damage(actual)} damage.")
            if target.is_conscious():
                self.apply_status(target, "reeling", 1, source=attacker.name)
            self.announce_downed_target(target)
        finally:
            self.break_invisibility_from_hostile_action(attacker)

    def use_flurry_of_blows(self, attacker, target, heroes, enemies, dodging) -> None:
        if not attacker.spend_resource("ki"):
            self.say(f"{self.style_name(attacker)} has no ki left for Flurry of Blows.")
            return
        self.say(f"{self.style_name(attacker)} spends 1 ki point and flows into a flurry of strikes.")
        self.use_martial_arts(attacker, target, heroes, enemies, dodging)
        if target.is_conscious():
            self.use_martial_arts(attacker, target, heroes, enemies, dodging)

    def perform_offhand_attack(self, attacker, target, heroes, enemies, dodging) -> None:
        if not self.can_make_hostile_action(attacker):
            self.say(f"{self.style_name(attacker)} cannot lash out with an off-hand strike while Charmed.")
            return
        play_attack_sound_for = getattr(self, "play_attack_sound_for", None)
        if callable(play_attack_sound_for):
            play_attack_sound_for(attacker)
        off_hand_item = self.equipped_off_hand_weapon_item(attacker)
        if off_hand_item is None:
            self.say(f"{self.style_name(attacker)} has no off-hand weapon ready.")
            return
        weapon = off_hand_item.weapon
        try:
            advantage = self.attack_advantage_state(attacker, target, heroes, enemies, dodging, ranged=weapon.ranged)
            target_ac = self.effective_armor_class(target)
            total_modifier = (
                self.weapon_attack_bonus_for(attacker, weapon)
                + self.ally_pressure_bonus(attacker, heroes, ranged=weapon.ranged)
                + self.status_value(attacker, "attack_bonus")
                - self.status_value(attacker, "attack_penalty")
            )
            d20 = self.roll_check_d20(
                attacker,
                advantage,
                target_number=target_ac,
                target_label=f"AC {target_ac}",
                modifier=total_modifier,
                style="attack",
                outcome_kind="attack",
                context_label=f"{attacker.name} off-hand attack",
            )
            total = d20.kept + total_modifier
            critical_hit = d20.kept >= self.critical_threshold(attacker)
            if d20.kept == 1 or (not critical_hit and d20.kept != 20 and total < target_ac):
                self.say(f"{self.style_name(attacker)}'s off-hand attack misses {self.style_name(target)}.")
                return
            actual = self.apply_damage(
                target,
                max(
                    1,
                    self.roll_with_display_bonus(
                        weapon.damage,
                        bonus=self.weapon_damage_bonus_for(attacker, weapon, include_ability_mod=False),
                        critical=critical_hit,
                        style="damage",
                        context_label=f"{attacker.name} off-hand damage",
                        outcome_kind="damage",
                    ).total
                    + self.weapon_damage_bonus_for(attacker, weapon, include_ability_mod=False),
                ),
                damage_type=off_hand_item.damage_type,
            )
            self.say(f"{self.style_name(attacker)} strikes with {off_hand_item.name} for {self.style_damage(actual)} damage.")
            self.announce_downed_target(target)
        finally:
            self.break_invisibility_from_hostile_action(attacker)

    def use_second_wind(self, actor) -> None:
        if not actor.spend_resource("second_wind"):
            self.say(f"{self.style_name(actor)} has already used Second Wind.")
            return
        amount = self.roll_with_animation_context(
            "1d10",
            style="healing",
            context_label="Second Wind",
            outcome_kind="healing",
        ).total + actor.level
        healed = actor.heal(amount)
        play_heal_sound_for = getattr(self, "play_heal_sound_for", None)
        if healed > 0 and callable(play_heal_sound_for):
            play_heal_sound_for(actor)
        self.say(f"{self.style_name(actor)} steadies themselves and regains {self.style_healing(healed)} hit points.")

    def use_action_surge(self, actor, target, heroes, enemies, dodging) -> None:
        if not actor.spend_resource("action_surge"):
            self.say(f"{self.style_name(actor)} has already spent Action Surge this rest.")
            return
        self.say(f"{self.style_name(actor)} digs deep and surges into a second strike.")
        self.perform_weapon_attack(actor, target, heroes, enemies, dodging)

    def use_channel_divinity(self, actor, target) -> None:
        if not self.can_make_hostile_action(actor):
            self.say(f"{self.style_name(actor)} cannot invoke hostile divine judgment while Charmed.")
            return
        if not actor.spend_resource("channel_divinity"):
            self.say(f"{self.style_name(actor)} has no Channel Divinity remaining.")
            return
        play_attack_sound_for = getattr(self, "play_attack_sound_for", None)
        if callable(play_attack_sound_for):
            play_attack_sound_for(actor)
        actual = self.apply_damage(
            target,
            self.roll_with_display_bonus(
                "2d8",
                bonus=self.spell_damage_bonus(actor),
                style="damage",
                context_label="Channel Divinity",
                outcome_kind="damage",
            ).total
            + self.spell_damage_bonus(actor),
        )
        self.say(
            f"{self.style_name(actor)} invokes Channel Divinity and sears {self.style_name(target)} "
            f"for {self.style_damage(actual)} radiant damage."
        )
        self.announce_downed_target(target)
        if target.is_conscious():
            self.apply_status(target, "stunned", 1, source="divine judgment")

    def help_downed_ally(self, actor, target) -> None:
        success = self.skill_check(actor, "Medicine", 10, context=f"to haul {target.name} back into the fight")
        if success:
            target.current_hp = 1
            target.stable = False
            target.death_successes = 0
            target.death_failures = 0
            play_heal_sound_for = getattr(self, "play_heal_sound_for", None)
            if callable(play_heal_sound_for):
                play_heal_sound_for(actor)
            self.say(
                f"{self.style_name(actor)} gets {self.style_name(target)} back to their feet at "
                f"{self.style_healing(1)} hit point."
            )
            return
        target.stable = True
        target.death_successes = 0
        target.death_failures = 0
        self.say(f"{self.style_name(actor)} stabilizes {self.style_name(target)}, but they cannot stand yet.")

    def use_healing_potion(self, user, target) -> None:
        if not user.spend_item("Healing Potion"):
            self.say(f"{self.style_name(user)} fumbles for a potion that is no longer there.")
            return
        healed = target.heal(
            self.roll_with_animation_context(
                "2d4+2",
                style="healing",
                context_label="Healing Potion",
                outcome_kind="healing",
            ).total
        )
        play_heal_sound_for = getattr(self, "play_heal_sound_for", None)
        if healed > 0 and callable(play_heal_sound_for):
            play_heal_sound_for(user)
        self.say(
            f"{self.style_name(user)} uses a healing potion on {self.style_name(target)}, "
            f"restoring {self.style_healing(healed)} hit points."
        )

    def use_lay_on_hands(self, user, target) -> None:
        pool = user.resources.get("lay_on_hands", 0)
        if pool <= 0:
            self.say(f"{self.style_name(user)} has no Lay on Hands healing left.")
            return
        amount = min(pool, 5, target.max_hp - target.current_hp if not target.dead else 0)
        if amount <= 0:
            self.say(f"{self.style_name(target)} does not need healing right now.")
            return
        user.resources["lay_on_hands"] -= amount
        healed = target.heal(amount)
        play_heal_sound_for = getattr(self, "play_heal_sound_for", None)
        if healed > 0 and callable(play_heal_sound_for):
            play_heal_sound_for(user)
        self.say(
            f"{self.style_name(user)} channels divine power and restores {self.style_healing(healed)} "
            f"hit points to {self.style_name(target)}."
        )

    def attempt_parley(self, actor, enemies, dc: int) -> None:
        skill = "Persuasion" if actor.skill_bonus("Persuasion") >= actor.skill_bonus("Intimidation") else "Intimidation"
        success = self.skill_check(actor, skill, dc, context="to force a break in the enemy's morale")
        if not success:
            for enemy in enemies:
                if enemy.is_conscious():
                    self.apply_status(enemy, "emboldened", 1, source="defying the parley")
            self.say("The enemy line hardens instead of yielding.")
            return
        leader = next((enemy for enemy in enemies if enemy.is_conscious() and "leader" in enemy.tags), None)
        if leader is not None and leader.current_hp <= leader.max_hp // 2:
            for enemy in enemies:
                if enemy.is_conscious():
                    enemy.current_hp = 0
                    enemy.dead = True
            self.say("The leader's nerve breaks and the rest of the encounter collapses with it.")
            return
        weakest = min((enemy for enemy in enemies if enemy.is_conscious()), key=lambda enemy: enemy.current_hp)
        weakest.current_hp = 0
        weakest.dead = True
        for enemy in enemies:
            if enemy.is_conscious():
                self.apply_status(enemy, "frightened", 1, source="the collapsing line")
        self.say(f"{self.style_name(weakest)} decides this pay is not worth dying for and flees.")

    def attack_advantage_state(self, attacker, target, heroes, enemies, dodging, *, ranged: bool = False) -> int:
        state = 0
        if target.name in dodging:
            state -= 1
        if "pack_tactics" in getattr(attacker, "features", []) and any(enemy.is_conscious() and enemy is not attacker for enemy in enemies):
            state += 1
        state += self.d20_disadvantage_state(attacker, attack=True)
        if self.has_status(attacker, "prone"):
            state -= 1
        if self.has_status(attacker, "invisible"):
            state += 1
        if self.has_status(target, "blinded"):
            state += 1
        if self.has_status(target, "restrained") or self.has_status(target, "stunned") or self.has_status(target, "paralyzed"):
            state += 1
        if self.has_status(target, "invisible") and "blind_sense" not in getattr(attacker, "features", []):
            state -= 1
        if self.has_status(target, "prone"):
            state += -1 if ranged else 1
        if self.has_status(target, "petrified") or self.has_status(target, "unconscious"):
            state += 1
        return 1 if state > 0 else -1 if state < 0 else 0

    def can_sneak_attack(self, attacker, heroes, target) -> bool:
        return any(hero.is_conscious() and hero is not attacker for hero in heroes) and target.is_conscious()

    def apply_poison_on_hit(self, attacker, target) -> None:
        dc = 12
        damage_roll = "1d4"
        condition_duration = 2
        always_damage = False
        source_text = f"{attacker.name}'s strike"
        if attacker.archetype == "mireweb_spider":
            dc = 11
            condition_duration = 1
            always_damage = True
            source_text = f"{attacker.name}'s venom"
        elif attacker.archetype == "ettervine_webherd":
            dc = 12
            condition_duration = 2
            always_damage = True
            source_text = f"{attacker.name}'s hooked fangs"
        elif attacker.archetype == "duskmire_matriarch":
            dc = 15
            damage_roll = "1d6"
            condition_duration = 2
            source_text = f"{attacker.name}'s widow venom"
        was_poisoned = self.has_status(target, "poisoned")
        save_success = self.saving_throw(target, "CON", dc, context=f"against {attacker.name}'s poisoned strike", against_poison=True)
        if save_success and not always_damage:
            return
        actual = self.apply_damage(
            target,
            self.roll_with_animation_context(
                damage_roll,
                style="damage",
                context_label=f"{attacker.name} poison damage",
                outcome_kind="damage",
            ).total,
            damage_type="poison",
        )
        self.say(f"{self.style_name(target)} suffers {self.style_damage(actual)} poison damage.")
        if not save_success:
            self.apply_status(target, "poisoned", condition_duration, source=source_text)
        if attacker.archetype == "rukhar" and not save_success and not self.saving_throw(target, "CON", 12, context=f"against {attacker.name}'s numbing poison", against_poison=True):
            self.apply_status(target, "paralyzed", 1, source=f"{attacker.name}'s numbing poison")
        if attacker.archetype == "varyn" and not save_success and not self.saving_throw(target, "CON", 12, context=f"against {attacker.name}'s draining toxin", against_poison=True):
            self.apply_status(target, "exhaustion", 2, source=f"{attacker.name}'s draining toxin")
        if attacker.archetype == "duskmire_matriarch" and not save_success and was_poisoned:
            if not self.saving_throw(target, "CON", 15, context=f"against {attacker.name}'s follow-up venom", against_poison=True):
                self.apply_status(target, "paralyzed", 1, source=f"{attacker.name}'s widow venom")
        self.announce_downed_target(target)

    def apply_damage(self, target, amount: int, *, damage_type: str = "") -> int:
        if target.dead:
            return 0
        if self.god_mode_enabled() and self.is_party_member_actor(target):
            return 0
        previous_hp = target.current_hp
        damage = max(0, amount)
        if self.has_status(target, "petrified"):
            damage //= 2
        resisted = False
        if damage_type == "poison" and "dwarven_resilience" in target.features:
            resisted = True
        if damage_type == "fire" and "hellish_resistance" in target.features:
            resisted = True
        if self.has_damage_resistance(target, damage_type):
            resisted = True
        if resisted:
            damage //= 2
        if target.temp_hp > 0:
            absorbed = min(target.temp_hp, damage)
            target.temp_hp -= absorbed
            damage -= absorbed
        if damage <= 0:
            return 0
        if target.current_hp == 0 and "enemy" not in target.tags:
            target.death_failures += 1
            if target.death_failures >= 3:
                target.dead = True
                if self.is_player_actor(target):
                    self.clear_liars_blessing_on_player_death()
            return damage
        target.current_hp = max(0, target.current_hp - damage)
        if target.current_hp == 0:
            if "enemy" in target.tags:
                if target.archetype == "cinderflame_skull" and target.resources.get("rekindle", 0) > 0:
                    target.resources["rekindle"] = 0
                    target.current_hp = 10
                    target.dead = False
                    self.say(f"{self.style_name(target)} collapses into ash, then flares back together with 10 hit points.")
                    return damage
                if target.archetype == "oathbroken_revenant" and target.resources.get("relentless_return", 0) > 0:
                    if str(target.bond_flags.get("marked_target", "")).strip():
                        target.resources["relentless_return"] = 0
                        target.current_hp = 12
                        target.dead = False
                        self.say(f"{self.style_name(target)} drags itself back upright on unfinished hatred with 12 hit points.")
                        return damage
                target.dead = True
            else:
                target.stable = False
                target.death_successes = 0
                target.death_failures = 0
        if target.current_hp < previous_hp:
            self.animate_health_bar_loss(target, previous_hp, target.current_hp)
            damage_hook = getattr(self, "after_actor_damaged", None)
            if callable(damage_hook):
                damage_hook(target, previous_hp=previous_hp, damage=damage, damage_type=damage_type)
        return damage

    def announce_downed_target(self, target) -> None:
        if target.current_hp == 0 and not target.dead and "enemy" not in target.tags:
            self.say(f"{self.style_name(target)} falls unconscious and begins making death saves.")

    def recover_after_battle(self) -> None:
        assert self.state is not None
        recovered: list[str] = []
        for member in self.state.party_members():
            if member.dead:
                continue
            if member.current_hp == 0:
                member.current_hp = 1
                member.stable = False
                member.death_successes = 0
                member.death_failures = 0
                recovered.append(member.name)
        if recovered:
            self.say("Once the danger passes, the party drags " + ", ".join(recovered) + " back to consciousness at 1 hit point.")

    def resolve_death_save(self, actor) -> None:
        d20 = self.roll_check_d20(
            actor,
            0,
            target_number=10,
            target_label="DC 10",
            modifier=0,
            style="save",
            outcome_kind="save",
            context_label=f"{actor.name} death save",
        )
        if d20.kept == 1:
            actor.death_failures += 2
            self.say(f"{self.style_name(actor)} rolls a natural 1 on a death save and suffers two failures.")
        elif d20.kept == 20:
            actor.current_hp = 1
            actor.death_successes = 0
            actor.death_failures = 0
            self.say(f"{self.style_name(actor)} rolls a natural 20 and staggers back to {self.style_healing(1)} hit point.")
            return
        elif d20.kept >= 10:
            actor.death_successes += 1
            self.say(f"{self.style_name(actor)} succeeds on a death save.")
        else:
            actor.death_failures += 1
            self.say(f"{self.style_name(actor)} fails a death save.")
        if actor.death_successes >= 3:
            actor.stable = True
            actor.death_successes = 0
            actor.death_failures = 0
            self.say(f"{self.style_name(actor)} stabilizes at 0 hit points.")
        if actor.death_failures >= 3:
            actor.dead = True
            if self.is_player_actor(actor):
                self.clear_liars_blessing_on_player_death()

    def skill_check(self, actor, skill: str, dc: int, *, context: str) -> bool:
        dc = self.effective_skill_dc(dc, context=context)
        advantage = self.d20_disadvantage_state(actor, skill=skill, context=context)
        total_modifier = actor.skill_bonus(skill)
        d20 = self.roll_check_d20(
            actor,
            advantage,
            target_number=dc,
            target_label=f"DC {dc}",
            modifier=total_modifier,
            style="skill",
            outcome_kind="check",
            context_label=f"{actor.name} {skill} check",
        )
        total = d20.kept + total_modifier
        self.say(
            f"{self.style_name(actor)} makes a {self.style_skill_label(skill)} check {context}: {total} vs DC {dc}."
        )
        success = total >= dc
        play_sound_effect = getattr(self, "play_sound_effect", None)
        if callable(play_sound_effect):
            play_sound_effect("skill_success" if success else "skill_fail")
        if not success:
            self.say("")
        return success

    def saving_throw(self, actor, ability: str, dc: int, *, context: str, against_poison: bool = False) -> bool:
        if self.always_pass_dice_checks_enabled() and self.is_party_member_actor(actor):
            self.say(f"{self.style_name(actor)} automatically clears the {ability} save {context}.")
            return True
        if self.auto_fail_save(actor, ability):
            self.say(f"{self.style_name(actor)} automatically fails the {ability} save {context}.")
            return False
        advantage = 1 if against_poison and "dwarven_resilience" in actor.features else 0
        if self.has_status(actor, "restrained") and ability == "DEX":
            advantage -= 1
        exhaustion = max(0, int(actor.conditions.get("exhaustion", 0)))
        if exhaustion >= 3:
            advantage -= 1
        total_modifier = (
            actor.save_bonus(ability)
            + self.status_value(actor, "save_bonus")
            - self.status_value(actor, "save_penalty")
        )
        d20 = self.roll_check_d20(
            actor,
            advantage,
            target_number=dc,
            target_label=f"DC {dc}",
            modifier=total_modifier,
            style="save",
            outcome_kind="save",
            context_label=f"{actor.name} {ability} save",
        )
        total = d20.kept + total_modifier
        self.say(f"{self.style_name(actor)} makes a {ability} save {context}: {total} vs DC {dc}.")
        return total >= dc

    def roll_with_advantage(self, actor, advantage_state: int) -> D20Outcome:
        return roll_d20(self.rng, advantage_state=advantage_state, lucky="lucky" in actor.features)

    def roll_check_d20(
        self,
        actor,
        advantage_state: int,
        *,
        target_number: int | None = None,
        target_label: str | None = None,
        modifier: int = 0,
        context_label: str | None = None,
        style: str | None = None,
        outcome_kind: str | None = None,
    ) -> D20Outcome:
        if self.always_pass_dice_checks_enabled() and self.is_party_member_actor(actor):
            kept = 20
            if target_number is not None:
                kept = max(2, target_number - modifier)
            forced_rolls = [kept, kept] if advantage_state != 0 else [kept]
            return D20Outcome(kept=kept, rolls=forced_rolls, rerolls=[], advantage_state=advantage_state)
        with self.temporary_roll_animation_metadata(
            target_number=target_number,
            target_label=target_label,
            total_modifier=modifier,
            context_label=context_label,
            style=style,
            outcome_kind=outcome_kind,
        ):
            return self.roll_with_advantage(actor, advantage_state)

    def roll_initiative(self, heroes, enemies, *, hero_bonus: int = 0, enemy_bonus: int = 0) -> list:
        entries: list[dict[str, object]] = []
        with self.suspend_dice_roll_animation():
            for index, actor in enumerate(heroes):
                if actor.dead:
                    continue
                modifier = actor.ability_mod("DEX") + hero_bonus + self.initiative_bonus(actor)
                outcome = self.roll_check_d20(
                    actor,
                    0,
                    modifier=modifier,
                    context_label=f"{actor.name} rolls initiative",
                    style="initiative",
                    outcome_kind="initiative",
                )
                entries.append(
                    {
                        "actor": actor,
                        "outcome": outcome,
                        "modifier": modifier,
                        "total": outcome.kept + modifier,
                        "dex_mod": actor.ability_mod("DEX"),
                        "side_priority": 1,
                        "tie_index": -index,
                    }
                )
            for index, actor in enumerate(enemies):
                modifier = actor.ability_mod("DEX") + enemy_bonus + self.initiative_bonus(actor)
                outcome = self.roll_check_d20(
                    actor,
                    0,
                    modifier=modifier,
                    context_label=f"{actor.name} rolls initiative",
                    style="initiative",
                    outcome_kind="initiative",
                )
                entries.append(
                    {
                        "actor": actor,
                        "outcome": outcome,
                        "modifier": modifier,
                        "total": outcome.kept + modifier,
                        "dex_mod": actor.ability_mod("DEX"),
                        "side_priority": 0,
                        "tie_index": -index,
                    }
                )
        entries.sort(
            key=lambda entry: (entry["total"], entry["dex_mod"], entry["side_priority"], entry["tie_index"]),
            reverse=True,
        )
        self.animate_initiative_rolls(entries)
        return [entry["actor"] for entry in entries]

    def print_battlefield(self, heroes, enemies) -> None:
        hero_lines = [self.describe_combatant(hero) for hero in heroes if not hero.dead]
        enemy_lines = [self.describe_combatant(enemy) for enemy in enemies if not enemy.dead]
        if self.rich_enabled() and Panel is not None and Group is not None and box is not None:
            party_panel = Panel(
                Group(*(self.rich_from_ansi(line) for line in (hero_lines or ["No one is still standing."]))),
                title=self.rich_text("Party", "light_aqua", bold=True),
                border_style=rich_style_name("light_aqua"),
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
            if self.emit_rich_panel_row(
                [party_panel, enemy_panel],
                ratios=[1, 1],
                width=self.safe_rich_render_width(),
            ):
                return
        self.say("Party: " + " | ".join(hero_lines))
        self.say("Enemies: " + " | ".join(enemy_lines))

    def describe_combatant(self, creature) -> str:
        active_conditions = [self.status_name(name) for name, value in creature.conditions.items() if value != 0]
        conditions = f" ({', '.join(active_conditions)})" if active_conditions else ""
        temp = f", temp {creature.temp_hp}" if creature.temp_hp else ""
        if creature.dead:
            return f"{self.style_name(creature)}: {self.format_health_bar(0, creature.max_hp)} (dead){conditions}"
        if creature.current_hp == 0 and not creature.dead:
            return f"{self.style_name(creature)}: {self.format_health_bar(0, creature.max_hp)} (down){conditions}"
        return (
            f"{self.style_name(creature)}: {self.format_health_bar(creature.current_hp, creature.max_hp)}, "
            f"AC {self.effective_armor_class(creature)}{temp}{conditions}"
        )

    def handle_defeat(self, reason: str) -> None:
        play_sound_effect = getattr(self, "play_sound_effect", None)
        if callable(play_sound_effect):
            play_sound_effect("game_over")
        self.banner("Defeat")
        self.say(reason)
        choice = self.choose(
            "What do you want to do?",
            [
                "Return to the title screen",
                "Open Save Files",
            ],
            allow_meta=False,
        )
        if choice == 2:
            loaded = self.open_save_files_menu()
            if loaded:
                return
        self.state = None
