from __future__ import annotations

from ..content import create_enemy
from ..items import EQUIPMENT_SLOTS, LEGACY_ITEM_NAMES, starter_item_ids_for_character
from ..models import Character
from .encounter import Encounter


class StoryEndgameMixin:
    def scene_ashfall_watch(self) -> None:
        assert self.state is not None
        self.banner("Ashfall Watch")
        self.say(
            "The watchtower squats above the road like a broken tooth. Bandits move between old stone and fresh "
            "timbers while smoke from cookfires curls into the evening.",
            typed=True,
        )
        enemies = [create_enemy("bandit"), create_enemy("bandit_archer")]
        encounter_bonus = self.apply_scene_companion_support("ashfall_watch")
        choice = self.scenario_choice(
            "How do you get close?",
            [
                self.skill_tag("STEALTH", self.action_option("Scout the ruined wall for a quiet angle.")),
                self.quoted_option("DECEPTION", "Bluff your way in as late-arriving hired steel."),
                self.skill_tag("ATHLETICS", self.action_option("Storm the gate before dusk settles.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Scout the ruined wall for a quiet angle.")
            success = self.skill_check(self.state.player, "Stealth", 12, context="to reach the wall unseen")
            if success:
                enemies[1].current_hp = max(1, enemies[1].current_hp - 4)
                self.apply_status(enemies[1], "surprised", 1, source="your silent wall-climb")
                encounter_bonus = 2
                self.say("You ghost up the hill and catch the lookout flat-footed before steel is drawn.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="a bad foothold on loose stone")
                self.say("Loose gravel betrays you and the camp snaps alert.")
        elif choice == 2:
            self.player_speaker("Bluff your way in as late-arriving hired steel.")
            success = self.skill_check(self.state.player, "Deception", 13, context="to sell the lie")
            if success:
                enemies[0].current_hp = max(1, enemies[0].current_hp - 3)
                self.apply_status(enemies[0], "surprised", 1, source="your sudden betrayal")
                self.apply_status(enemies[1], "reeling", 1, source="the collapsing ruse")
                encounter_bonus = 1
                self.say("The ruse holds just long enough for your first strike to land in chaos.")
            else:
                self.apply_status(self.state.player, "surprised", 1, source="the sentry's barked alarm")
                self.say("The sentry doesn't buy it, and the bluff collapses into a shout for blades.")
        else:
            self.player_action("Storm the gate before dusk settles.")
            success = self.skill_check(self.state.player, "Athletics", 13, context="to break through the gate with momentum")
            if success:
                self.apply_status(self.state.player, "emboldened", 2, source="bursting through the gate")
                self.apply_status(enemies[0], "prone", 1, source="the shattered gate rush")
                encounter_bonus = 2
                self.say("The gate gives way under force, and the first bandit goes down in the splintered rush.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="hitting the gate wrong")
                self.say("The gate still gives, but the impact rattles you hard enough to cost the clean opening you wanted.")

        first_encounter = Encounter(
            title="Ashfall Watch Outskirts",
            description="Bandits scramble for weapons among stacked crates and broken stone.",
            enemies=enemies,
            allow_flee=True,
            allow_parley=True,
            parley_dc=13,
            hero_initiative_bonus=encounter_bonus,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter_wave(first_encounter)
        if outcome == "defeat":
            self.handle_defeat("Ashfall Watch remains in enemy hands.")
            return
        if outcome == "fled":
            self.state.current_scene = "phandalin_hub"
            self.say("You fall back to Iron Hollow to rethink the assault.")
            return

        self.say(
            "At the tower's heart, a hobgoblin in disciplined armor steps through the smoke. "
            "Rukhar Cinderfang studies you with the patience of a veteran who has already measured the dead."
        )
        boss_enemies = [create_enemy("rukhar"), create_enemy("bandit_archer", name="Ashen Brand Lookout")]
        if len(self.state.party_members()) >= 3:
            boss_enemies.append(create_enemy("bandit", name="Ashen Brand Enforcer"))
        bonus = 0
        choice = self.scenario_choice(
            "Rukhar taps the flat of his blade against his shield.",
            [
                self.quoted_option("INTIMIDATION", "Surrender in Iron Hollow's name."),
                self.action_option("Face Rukhar cleanly and keep his soldiers out of it."),
                self.action_option("Strike first and let steel do the talking."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Surrender in Iron Hollow's name.")
            success = self.skill_check(self.state.player, "Intimidation", 13, context="to break Rukhar's composure")
            if success:
                boss_enemies[0].current_hp -= 4
                self.apply_status(boss_enemies[0], "frightened", 1, source="your iron-edged demand")
                self.apply_status(boss_enemies[0], "reeling", 2, source="a cracked command posture")
                self.say("Rukhar's escort falters, and even the sergeant's mask cracks for a second.")
            else:
                self.apply_status(boss_enemies[0], "emboldened", 2, source="your failed demand")
                self.speaker("Rukhar Cinderfang", "Good. You came with a spine.")
        elif choice == 2:
            self.player_action("Face me cleanly and keep your soldiers out of it.")
            bonus = 1
            self.say("Rukhar respects the directness enough to meet you blade-first without stalling.")
        else:
            self.player_action("Steel first. Words later.")
            boss_enemies[0].current_hp -= 3
            bonus = 2
            self.say("Steel answers before words can, and your party crashes into the tower court.")

        boss_encounter = Encounter(
            title="Miniboss: Rukhar Cinderfang",
            description="The Ashen Brand sergeant rallies his last loyal fighters.",
            enemies=boss_enemies,
            allow_flee=True,
            allow_parley=True,
            parley_dc=14,
            hero_initiative_bonus=bonus,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter(boss_encounter)
        if outcome == "defeat":
            self.handle_defeat("Rukhar drives the party from the tower in blood and smoke.")
            return
        if outcome == "fled":
            self.state.current_scene = "phandalin_hub"
            self.say("You escape the watchtower and retreat to Iron Hollow to regroup.")
            return

        self.add_clue("Rukhar carried a cellar map tied to Emberhall beneath an old manor ruin.")
        self.add_journal("Ashfall Watch is broken, but the gang's captain is below Iron Hollow in Emberhall Cellars.")
        self.state.flags["ashfall_watch_cleared"] = True
        self.state.flags["emberhall_revealed"] = True
        refresh_quest_statuses = getattr(self, "refresh_quest_statuses", None)
        if callable(refresh_quest_statuses):
            refresh_quest_statuses(announce=False)
        self.say(
            "Among Rukhar's orders you find a map to Emberhall Cellars, a hidden chamber beneath one of Iron Hollow's "
            "older ruins. The Ashen Brand's true captain is waiting below the town, but now you have time to carry "
            "that news back through Iron Hollow before the final descent."
        )
        self.state.current_scene = "phandalin_hub"

    def scene_emberhall_cellars(self) -> None:
        assert self.state is not None
        self.banner("Emberhall Cellars")
        self.say(
            "Near midnight, you descend through cracked stone into a cellar complex older than the town above it. "
            "Lanternlight flickers across stolen crates, ash-marked banners, and a final knot of hard-eyed brigands.",
            typed=True,
        )
        enemies = [create_enemy("varyn"), create_enemy("bandit"), create_enemy("bandit_archer")]
        hero_bonus = self.apply_scene_companion_support("emberhall_cellars")
        choice = self.scenario_choice(
            "How do you open the final assault?",
            [
                self.skill_tag("STEALTH", self.action_option("Slip through the drainage tunnel.")),
                self.skill_tag("ATHLETICS", self.action_option("Kick in the main cellar door.")),
                self.quoted_option("PERSUASION", "Call for surrender before blood is spilled."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Slip through the drainage tunnel.")
            success = self.skill_check(self.state.player, "Stealth", 13, context="to reach the inner chamber quietly")
            if success:
                enemies[2].current_hp = max(1, enemies[2].current_hp - 5)
                self.apply_status(enemies[2], "surprised", 1, source="your tunnel approach")
                self.apply_status(enemies[1], "acid", 2, source="a burst cask in the tunnel spill")
                hero_bonus = 2
                self.say("You emerge behind a stack of crates and the first lookout never gets a clean shot.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="the shrieking tunnel grate")
                self.say("The tunnel grate shrieks loudly enough to wake the whole cellar.")
        elif choice == 2:
            self.player_action("Kick in the main cellar door.")
            success = self.skill_check(self.state.player, "Athletics", 13, context="to break the cellar door off its hinges")
            if success:
                self.apply_status(self.state.player, "emboldened", 2, source="blasting into the cellar")
                self.apply_status(enemies[1], "prone", 1, source="the crashing door")
                hero_bonus = 2
                self.say("The door explodes inward, crushing one brigand off balance before the room can set itself.")
            else:
                self.apply_status(self.state.player, "prone", 1, source="the collapsing door frame")
                self.say("The door gives badly and drags you off balance into the first exchange.")
        else:
            self.player_speaker("Call for surrender before blood is spilled.")
            success = self.skill_check(self.state.player, "Persuasion", 14, context="to shake the gang's resolve")
            if success:
                fleeing = enemies.pop()
                for enemy in enemies:
                    if enemy.is_conscious():
                        self.apply_status(enemy, "frightened", 1, source="watching one of their own bolt")
                self.say(f"{fleeing.name} bolts for the far stairs instead of dying for someone else's cut.")
            else:
                self.apply_status(enemies[0], "emboldened", 2, source="your mercy being rejected")
                self.speaker("Varyn Sable", "Too late for mercy now.")

        encounter = Encounter(
            title="Boss: Varyn Sable",
            description="The captain of the Ashen Brand stands between Iron Hollow and another season of fear.",
            enemies=enemies,
            allow_flee=True,
            allow_parley=True,
            parley_dc=15,
            hero_initiative_bonus=hero_bonus,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter(encounter)
        if outcome == "defeat":
            self.handle_defeat("The cellar banners remain standing above a fallen company.")
            return
        if outcome == "fled":
            self.state.current_scene = "phandalin_hub"
            self.say("You escape the cellars and return to the surface to recover.")
            return

        self.say(
            "Varyn falls, but not cleanly. Body, cloak, and blade hit the cellar stones while the route behind him folds the wrong way. "
            "The remaining brigands scatter, the Ashen Brand breaks around that absence, and the people above finally get a quiet night. "
            "Among the captain's ledgers are references to older powers stirring beneath the Vein of Glass, with whispers that tie back toward the Resonant Vaults."
        )
        self.state.flags["varyn_body_defeated_act1"] = True
        self.state.flags["varyn_route_displaced"] = True
        self.state.flags["act1_ashen_brand_broken"] = True
        if self.state.flags.get("emberhall_ledger_read") or self.state.flags.get("emberhall_archive_tip"):
            self.state.flags["emberhall_impossible_exit_seen"] = True
            self.say("The exits you decoded before the fight all account for themselves except one: a route that appears in the ledger only after Varyn is gone.")
        self.add_journal("You broke the Ashen Brand and secured Iron Hollow through the end of Act 1.")
        self.reward_party(xp=250, gold=80, reason="securing Iron Hollow at the end of Act I")
        self.state.completed_acts.append(1)
        self.state.current_scene = "act1_complete"
        self.save_game(slot_name=f"{self.state.player.name}_act1_complete")

    def recruit_companion(self, companion: Character) -> None:
        assert self.state is not None
        if self.has_companion(companion.name):
            return
        if not companion.equipment_slots:
            companion.equipment_slots = {slot: None for slot in EQUIPMENT_SLOTS}
            for slot, item_id in starter_item_ids_for_character(companion).items():
                companion.equipment_slots[slot] = item_id
                if item_id is not None:
                    self.state.inventory[item_id] = self.state.inventory.get(item_id, 0) + 1
        self.state.companions.append(companion)
        for legacy_name, quantity in list(companion.inventory.items()):
            item_id = LEGACY_ITEM_NAMES.get(legacy_name)
            if item_id is not None:
                self.state.inventory[item_id] = self.state.inventory.get(item_id, 0) + quantity
        companion.inventory.clear()
        self.sync_equipment(companion)
        self.add_journal(f"{companion.name} joined the party.")

    def has_companion(self, name: str) -> bool:
        assert self.state is not None
        return any(companion.name == name for companion in self.state.companions)
