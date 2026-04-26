from __future__ import annotations

from ..models import ABILITY_ORDER, SKILL_TO_ABILITY
from ..items import get_item


class JournalMixin:
    def add_clue(self, clue: str) -> None:
        assert self.state is not None
        if clue not in self.state.clues:
            self.state.clues.append(clue)
            self.add_journal(f"Clue: {clue}")

    def add_journal(self, entry: str) -> None:
        assert self.state is not None
        if entry not in self.state.journal:
            self.state.journal.append(entry)

    def show_journal(self) -> None:
        assert self.state is not None
        refresh_quest_statuses = getattr(self, "refresh_quest_statuses", None)
        if callable(refresh_quest_statuses):
            refresh_quest_statuses(announce=False)
        self.banner("Journal")
        ready_quests = getattr(self, "quest_entries_by_status", lambda status: [])("ready_to_turn_in")
        active_quests = getattr(self, "quest_entries_by_status", lambda status: [])("active")
        completed_quests = getattr(self, "quest_entries_by_status", lambda status: [])("completed")
        if not ready_quests and not active_quests and not completed_quests and not self.state.clues and not self.state.journal:
            self.say("Your journal is empty.")
            return
        if ready_quests:
            self.say("Ready to Turn In:")
            for definition, entry in ready_quests:
                self.output_fn(f"- {definition.title} ({definition.giver})")
                self.output_fn(f"  Objective: {definition.objective}")
                self.output_fn(f"  Turn in: {definition.turn_in}")
                self.output_fn(f"  Rewards: {self.quest_reward_summary(definition.quest_id)}")
                if entry.notes:
                    self.output_fn(f"  Latest note: {entry.notes[-1]}")
        if active_quests:
            self.say("Active Quests:")
            for definition, entry in active_quests:
                self.output_fn(f"- {definition.title} ({definition.giver})")
                self.output_fn(f"  Summary: {definition.summary}")
                self.output_fn(f"  Objective: {definition.objective}")
                self.output_fn(f"  Rewards: {self.quest_reward_summary(definition.quest_id)}")
                if entry.notes:
                    self.output_fn(f"  Latest note: {entry.notes[-1]}")
        if completed_quests:
            self.say("Completed Quests:")
            for definition, entry in completed_quests:
                self.output_fn(f"- {definition.title}")
                if entry.notes:
                    self.output_fn(f"  Final note: {entry.notes[-1]}")
        if self.state.clues:
            self.say("Clues:")
            for index, clue in enumerate(self.state.clues, start=1):
                self.output_fn(f"{index}. {clue}")
        if self.state.journal:
            self.say("Notes:")
            for index, entry in enumerate(self.state.journal, start=1):
                self.output_fn(f"{index}. {entry}")

    def show_party(self) -> None:
        assert self.state is not None
        self.banner("Party")
        self.say(
            f"{self.xp_progress_summary()} | Gold: {self.state.gold} gp | "
            f"Short rests left: {self.state.short_rests_remaining} | "
            f"Supply points: {self.current_supply_points()}"
        )
        self.say("Active party:")
        for member in self.state.party_members():
            conditions = self.character_condition_summary(member)
            temp_hp = f", temp {member.temp_hp}" if member.temp_hp else ""
            self.output_fn(
                f"- {member.name}: Level {member.level} {member.race} {member.class_name}, "
                f"{self.character_health_summary(member)}, Defense {member.armor_class}{temp_hp}, "
                f"conditions [{conditions}]"
            )
            if getattr(member, "companion_id", ""):
                self.output_fn(f"  Relationship: {self.relationship_label_for(member)} ({member.disposition})")
        if self.state.camp_companions:
            self.say("Camp companions:")
            for companion in self.state.camp_companions:
                self.output_fn(f"- {self.companion_status_line(companion)}")

    def character_health_summary(self, member) -> str:
        return f"{self.format_health_bar(member.current_hp, member.max_hp)}{self.health_status_suffix(member.current_hp, dead=member.dead)}"

    def character_condition_summary(self, member) -> str:
        active = [self.status_name(name) for name, value in member.conditions.items() if value != 0]
        return ", ".join(active) if active else "none"

    def company_members(self) -> list:
        assert self.state is not None
        return [self.state.player, *self.state.all_companions()]

    def company_member_label(self, member) -> str:
        if self.state is not None and member is self.state.player:
            location = "Player"
        elif self.state is not None and member in self.state.companions:
            location = "Active"
        else:
            location = "Camp"
        return (
            f"{member.name}: Level {member.level} {member.race} {member.class_name} | "
            f"{self.character_health_summary(member)} | {location}"
        )

    def choose_company_member(self, prompt: str, *, allow_back: bool = False):
        roster = self.company_members()
        options = [self.company_member_label(member) for member in roster]
        if allow_back:
            options.append("Back")
        choice = self.choose(prompt, options, allow_meta=False)
        if allow_back and choice == len(roster) + 1:
            return None
        return roster[choice - 1]

    def show_character_sheets(self) -> None:
        while True:
            member = self.choose_company_member("Choose whose character sheet you want to inspect.", allow_back=True)
            if member is None:
                return
            self.show_character_sheet(member)
            if self.choose("What next?", ["View another sheet", "Back"], allow_meta=False) == 2:
                return

    def show_character_sheet(self, member) -> None:
        self.banner(f"Character Sheet: {member.name}")
        self.say(
            f"Level {member.level} {member.race} {member.class_name} | Background: {member.background} | "
            f"Status: {self.character_health_summary(member)} | Defense {member.armor_class} | "
            f"Proficiency bonus +{member.proficiency_bonus}"
        )
        self.output_fn("")
        self.say("Ability Scores:")
        for ability in ABILITY_ORDER:
            score = member.ability_scores[ability]
            modifier = member.ability_mod(ability)
            self.output_fn(f"- {ability}: {score} ({modifier:+d})")
        self.output_fn("")
        self.say("Combat:")
        self.output_fn(f"- Weapon: {member.weapon.name} | attack +{member.attack_bonus()} | damage bonus +{member.damage_bonus()}")
        self.output_fn(f"- Hit die: d{member.hit_die} | Temp HP: {member.temp_hp} | Conditions: {self.character_condition_summary(member)}")
        if member.spellcasting_ability is not None:
            spell_attack = self.spell_attack_bonus(member, member.spellcasting_ability)
            self.output_fn(
                f"- Spellcasting: {member.spellcasting_ability} | spell attack +{spell_attack} | "
                f"spell slots {member.resources.get('spell_slots', 0)}/{member.max_resources.get('spell_slots', 0)}"
            )
        self.output_fn("")
        self.say("Saving Throws:")
        for ability in ABILITY_ORDER:
            proficient = "*" if ability in member.saving_throw_proficiencies else ""
            self.output_fn(f"- {ability}{proficient}: {member.save_bonus(ability):+d}")
        self.output_fn("")
        self.say("Skills:")
        for skill in sorted(SKILL_TO_ABILITY):
            markers = []
            if skill in member.skill_proficiencies:
                markers.append("prof")
            if skill in member.skill_expertise:
                markers.append("expertise")
            suffix = f" ({', '.join(markers)})" if markers else ""
            self.output_fn(f"- {skill}: {member.skill_bonus(skill):+d}{suffix}")
        self.output_fn("")
        self.say("Features & Proficiencies:")
        self.output_fn(
            f"- Features: {', '.join(self.format_feature_name(feature) for feature in member.features) if member.features else 'None'}"
        )
        self.output_fn(
            f"- Background / bonus proficiencies: {', '.join(member.bonus_proficiencies) if member.bonus_proficiencies else 'None'}"
        )
        if member.resources or member.max_resources:
            self.output_fn(
                "- Resources: "
                + (
                    ", ".join(
                        f"{name.replace('_', ' ')} {member.resources.get(name, 0)}/{member.max_resources.get(name, 0)}"
                        for name in sorted(member.max_resources)
                    )
                    if member.max_resources
                    else "None"
                )
            )
        self.output_fn("")
        self.say("Equipment:")
        for slot, item_id in member.equipment_slots.items():
            item_name = get_item(item_id).name if item_id is not None else "Empty"
            self.output_fn(f"- {self.equipment_slot_label(slot)}: {item_name}")
        if getattr(member, "companion_id", ""):
            self.output_fn(f"- Relationship: {self.relationship_label_for(member)} ({member.disposition})")

    def equipment_slot_label(self, slot: str) -> str:
        from ..items import equipment_slot_label

        return equipment_slot_label(slot)
