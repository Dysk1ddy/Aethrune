from __future__ import annotations

from ..data.story.public_terms import (
    ability_label,
    marks_label,
    resource_label,
    skill_option_label,
    target_guard_label,
)
from ..models import ABILITY_ORDER, SKILL_TO_ABILITY
from ..items import get_item
from ..ui.colors import rich_style_name, strip_ansi
from ..ui.rich_render import Columns, Group, Panel, Table, box
from .spell_slots import is_spell_slot_resource


class JournalMixin:
    def rich_ledger_enabled(self) -> bool:
        return (
            callable(getattr(self, "should_use_rich_ui", None))
            and self.should_use_rich_ui()
            and Columns is not None
            and Group is not None
            and Panel is not None
            and Table is not None
            and box is not None
        )

    def member_panel_border_color(self, member) -> str:
        if self.state is not None and member is self.state.player:
            return "light_yellow"
        if getattr(member, "companion_id", ""):
            return "light_aqua"
        return "light_green"

    def member_resource_summary(self, member) -> str:
        visible_resources = [
            name for name in sorted(member.max_resources)
            if not is_spell_slot_resource(name)
        ]
        if not visible_resources:
            return "None"
        return ", ".join(
            f"{resource_label(name).title()} {member.resources.get(name, 0)}/{member.max_resources.get(name, 0)}"
            for name in visible_resources
        )

    def member_summary_panel(self, member):
        relationship_line = None
        if getattr(member, "companion_id", ""):
            relationship_line = self.rich_from_ansi(
                f"Relationship: {self.relationship_label_for(member)} ({member.disposition})"
            )
        details = [
            self.rich_from_ansi(f"Level {member.level} {member.public_identity}"),
            self.rich_from_ansi(
                f"{self.character_health_summary(member)} | {target_guard_label(member.armor_class)} | Temp HP {member.temp_hp}"
            ),
        ]
        magic_bar = self.format_member_magic_bar(member)
        if magic_bar:
            details.append(self.rich_from_ansi(magic_bar))
        details.append(self.rich_from_ansi(f"Conditions: {self.character_condition_summary(member)}"))
        story_modifiers = self.story_skill_modifier_display_lines(member)
        if story_modifiers:
            details.append(self.rich_from_ansi("Story modifiers: " + "; ".join(story_modifiers)))
        if relationship_line is not None:
            details.append(relationship_line)
        color = self.member_panel_border_color(member)
        return Panel(
            Group(*details),
            title=self.rich_from_ansi(self.style_name(member)),
            border_style=rich_style_name(color),
            box=box.ROUNDED,
            padding=(0, 1),
        )

    def character_sheet_panel(self, title: str, color: str, content):
        return Panel(
            content,
            title=self.rich_text(title, color, bold=True),
            border_style=rich_style_name(color),
            box=box.ROUNDED,
            padding=(0, 1),
        )

    def character_sheet_grid(self, rows: list[tuple[object, object]]):
        grid = Table.grid(expand=True, padding=(0, 0))
        grid.add_column(ratio=1, vertical="top")
        grid.add_column(ratio=1, vertical="top")
        for left_panel, right_panel in rows:
            grid.add_row(left_panel, right_panel)
        return grid

    def character_sheet_render_width(self) -> int:
        safe_width_getter = getattr(self, "safe_rich_render_width", None)
        if callable(safe_width_getter):
            return min(98, safe_width_getter())
        return min(98, self.rich_console_width())

    def build_character_sheet_rich_renderable(self, member):
        header = Table.grid(expand=True, padding=(0, 1))
        header.add_column(style=f"bold {rich_style_name('light_yellow')}", width=14)
        header.add_column(ratio=1)
        header.add_row("People / Role", f"Level {member.level} {member.public_identity}")
        header.add_row("Background", member.background)
        header.add_row("Status", strip_ansi(self.character_health_summary(member)))
        header.add_row("Guard", str(member.armor_class))
        header.add_row("Training", f"+{member.proficiency_bonus}")
        if getattr(member, "companion_id", ""):
            header.add_row("Relationship", f"{self.relationship_label_for(member)} ({member.disposition})")

        abilities = Table(box=box.SIMPLE_HEAVY, expand=True, pad_edge=False)
        abilities.add_column("Ability", style=f"bold {rich_style_name('light_yellow')}")
        abilities.add_column("Score", justify="center")
        abilities.add_column("Mod", justify="center")
        for ability in ABILITY_ORDER:
            score = member.ability_scores[ability]
            abilities.add_row(ability_label(ability, include_code=True), str(score), f"{member.ability_mod(ability):+d}")

        combat = Table.grid(expand=True, padding=(0, 1))
        combat.add_column(style=f"bold {rich_style_name('light_red')}", width=12)
        combat.add_column(ratio=1)
        combat.add_row("Weapon", member.weapon.name)
        combat.add_row("Strike", f"+{member.attack_bonus()}")
        combat.add_row("Damage bonus", f"+{member.damage_bonus()}")
        combat.add_row("Hit die", f"d{member.hit_die}")
        combat.add_row("Temp HP", str(member.temp_hp))
        combat.add_row("Conditions", self.character_condition_summary(member))
        if member.spellcasting_ability is not None:
            spell_attack = self.spell_attack_bonus(member, member.spellcasting_ability)
            combat.add_row("Channeling", ability_label(member.spellcasting_ability, include_code=True))
            combat.add_row("Channel strike", f"+{spell_attack}")
            magic_bar = self.format_member_magic_bar(member)
            if magic_bar is not None:
                combat.add_row("Reserve", self.rich_from_ansi(magic_bar))

        saves = Table(box=box.SIMPLE_HEAVY, expand=True, pad_edge=False)
        saves.add_column("Resist", style=f"bold {rich_style_name('light_aqua')}")
        saves.add_column("Bonus", justify="center")
        for ability in ABILITY_ORDER:
            proficient = "*" if ability in member.saving_throw_proficiencies else ""
            saves.add_row(f"{ability_label(ability, include_code=True)}{proficient}", f"{member.save_bonus(ability):+d}")

        skills = Table(box=box.SIMPLE_HEAVY, expand=True, pad_edge=False)
        skills.add_column("Skill", style=f"bold {rich_style_name('light_green')}")
        skills.add_column("Bonus", justify="center")
        skills.add_column("Tags")
        for skill in sorted(SKILL_TO_ABILITY):
            markers = []
            if skill in member.skill_proficiencies:
                markers.append("trained")
            if skill in member.skill_expertise:
                markers.append("deep")
            skills.add_row(skill_option_label(skill), f"{member.skill_bonus(skill):+d}", ", ".join(markers) or "-")

        feature_lines = [
            self.rich_text(
                ", ".join(self.format_feature_name(feature) for feature in member.features) if member.features else "None",
                "light_yellow",
            ),
            self.rich_text(
                "Background / bonus training: "
                + (", ".join(member.bonus_proficiencies) if member.bonus_proficiencies else "None"),
                "light_green",
            ),
        ]
        resources_text = self.member_resource_summary(member)
        if resources_text != "None":
            feature_lines.append(self.rich_text(f"Resources: {resources_text}", "light_aqua"))

        story_modifier_lines = self.story_skill_modifier_display_lines(member)
        story_modifier_panel = None
        if story_modifier_lines:
            story_modifier_panel = self.character_sheet_panel(
                "Story Modifiers",
                "purple",
                Group(*(self.rich_text(line, "purple") for line in story_modifier_lines)),
            )

        equipment_lines = [
            self.rich_text(
                f"{self.equipment_slot_label(slot)}: {get_item(item_id).name if item_id is not None else 'Empty'}",
                "light_aqua",
            )
            for slot, item_id in member.equipment_slots.items()
        ]

        stats_grid = self.character_sheet_grid(
            [
                (
                    self.character_sheet_panel("Ability Scores", "light_yellow", abilities),
                    self.character_sheet_panel("Resist Checks", "light_aqua", saves),
                ),
                (
                    self.character_sheet_panel("Combat", "light_red", combat),
                    self.character_sheet_panel("Skills", "light_green", skills),
                ),
            ]
        )
        detail_grid = self.character_sheet_grid(
            [
                (
                    self.character_sheet_panel("Features & Training", "light_yellow", Group(*feature_lines)),
                    self.character_sheet_panel("Equipment", "light_aqua", Group(*equipment_lines)),
                ),
            ]
        )
        renderables = [
            self.character_sheet_panel(f"Character Sheet: {member.name}", "light_yellow", header),
            stats_grid,
        ]
        if story_modifier_panel is not None:
            renderables.append(story_modifier_panel)
        renderables.append(detail_grid)
        return Group(*renderables)

    def render_rich_journal_view(
        self,
        *,
        ready_quests,
        active_quests,
        completed_quests,
        story_notes: list[str],
    ) -> bool:
        if not self.rich_ledger_enabled():
            return False

        extra_snapshot_lines_getter = getattr(self, "journal_snapshot_lines", None)
        extra_snapshot_lines = extra_snapshot_lines_getter() if callable(extra_snapshot_lines_getter) else []
        snapshot = Table.grid(expand=True, padding=(0, 1))
        snapshot.add_column(style=f"bold {rich_style_name('light_yellow')}", width=12)
        snapshot.add_column(ratio=1)
        snapshot.add_row("Location", self.hud_location_label())
        snapshot.add_row("Objective", self.hud_objective_label())
        snapshot.add_row(
            "Quest load",
            f"{len(active_quests)} active | {len(ready_quests)} ready | {len(completed_quests)} completed",
        )
        snapshot.add_row("Leads", f"{len(self.state.clues)} clues | {len(story_notes)} journal notes")
        for index, line in enumerate(extra_snapshot_lines):
            snapshot.add_row("Act II" if index == 0 else "", line)

        def quest_panel(title: str, entries, color: str, *, include_summary: bool) :
            table = Table.grid(expand=True, padding=(0, 1))
            table.add_column(style=f"bold {rich_style_name(color)}", width=11)
            table.add_column(ratio=1)
            if not entries:
                table.add_row("Status", "Nothing logged.")
            else:
                for index, (definition, entry) in enumerate(entries):
                    table.add_row("Quest", definition.title)
                    if include_summary:
                        table.add_row("Summary", definition.summary)
                    table.add_row("Objective", definition.objective)
                    if title == "Ready To Turn In":
                        table.add_row("Turn in", definition.turn_in)
                    table.add_row("Rewards", self.quest_reward_summary(definition.quest_id))
                    if entry.notes:
                        note_label = "Latest" if title != "Completed" else "Final"
                        table.add_row(note_label, entry.notes[-1])
                    if index < len(entries) - 1:
                        table.add_row("", "")
            return Panel(
                table,
                title=self.rich_text(title, color, bold=True),
                border_style=rich_style_name(color),
                box=box.ROUNDED,
                padding=(0, 1),
            )

        clue_content = (
            Group(*(self.rich_text(f"{index}. {clue}", "light_aqua") for index, clue in enumerate(self.state.clues, start=1)))
            if self.state.clues
            else self.rich_text("No clues tracked yet.", "light_aqua", dim=True)
        )
        recent_notes = list(reversed(story_notes[-8:]))
        updates: list[object] = [
            self.rich_text(f"{index}. {entry}", "light_green")
            for index, entry in enumerate(recent_notes, start=1)
        ]
        older_note_count = max(0, len(story_notes) - len(recent_notes))
        if older_note_count:
            updates.append(self.rich_text(f"Older notes archived in this run: {older_note_count}", "light_yellow"))
        updates_content: object = Group(*updates) if updates else self.rich_text("No recent updates logged.", "light_green", dim=True)

        return self.emit_rich(
            Group(
                Panel(
                    snapshot,
                    title=self.rich_text("Campaign Snapshot", "light_yellow", bold=True),
                    border_style=rich_style_name("light_yellow"),
                    box=box.ROUNDED,
                    padding=(0, 1),
                ),
                Columns(
                    [
                        quest_panel("Ready To Turn In", ready_quests, "light_yellow", include_summary=False),
                        quest_panel("Active Quests", active_quests, "light_green", include_summary=True),
                        quest_panel("Completed", completed_quests, "light_aqua", include_summary=False),
                    ],
                    expand=True,
                    equal=True,
                ),
                Columns(
                    [
                        Panel(
                            clue_content,
                            title=self.rich_text("Clue Board", "light_aqua", bold=True),
                            border_style=rich_style_name("light_aqua"),
                            box=box.ROUNDED,
                            padding=(0, 1),
                        ),
                        Panel(
                            updates_content,
                            title=self.rich_text("Recent Updates", "light_green", bold=True),
                            border_style=rich_style_name("light_green"),
                            box=box.ROUNDED,
                            padding=(0, 1),
                        ),
                    ],
                    expand=True,
                    equal=True,
                ),
            ),
            width=max(108, self.rich_console_width()),
        )

    def add_clue(self, clue: str) -> None:
        assert self.state is not None
        if clue not in self.state.clues:
            self.state.clues.append(clue)
            self.add_journal(f"Clue: {clue}")

    def add_journal(self, entry: str) -> None:
        assert self.state is not None
        if entry not in self.state.journal:
            self.state.journal.append(entry)

    def story_journal_entries(self) -> list[str]:
        assert self.state is not None
        return [entry for entry in self.state.journal if not entry.startswith("Clue: ")]

    def show_journal(self) -> None:
        assert self.state is not None
        refresh_quest_statuses = getattr(self, "refresh_quest_statuses", None)
        if callable(refresh_quest_statuses):
            refresh_quest_statuses(announce=False)
        self.banner("Journal")
        ready_quests = getattr(self, "quest_entries_by_status", lambda status: [])("ready_to_turn_in")
        active_quests = getattr(self, "quest_entries_by_status", lambda status: [])("active")
        completed_quests = getattr(self, "quest_entries_by_status", lambda status: [])("completed")
        story_notes = self.story_journal_entries()
        extra_snapshot_lines_getter = getattr(self, "journal_snapshot_lines", None)
        extra_snapshot_lines = extra_snapshot_lines_getter() if callable(extra_snapshot_lines_getter) else []
        if not ready_quests and not active_quests and not completed_quests and not self.state.clues and not story_notes and not extra_snapshot_lines:
            self.say("Your journal is empty.")
            return
        if self.render_rich_journal_view(
            ready_quests=ready_quests,
            active_quests=active_quests,
            completed_quests=completed_quests,
            story_notes=story_notes,
        ):
            return
        self.say("Campaign Snapshot:")
        self.output_fn(f"- Location: {self.hud_location_label()}")
        self.output_fn(f"- Objective: {self.hud_objective_label()}")
        self.output_fn(
            f"- Quest load: {len(active_quests)} active, {len(ready_quests)} ready to turn in, {len(completed_quests)} completed"
        )
        self.output_fn(f"- Leads tracked: {len(self.state.clues)} clues, {len(story_notes)} journal notes")
        for line in extra_snapshot_lines:
            self.output_fn(f"- {line}")
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
            self.say("Clue Board:")
            for index, clue in enumerate(self.state.clues, start=1):
                self.output_fn(f"{index}. {clue}")
        if story_notes:
            recent_notes = list(reversed(story_notes[-8:]))
            self.say("Recent Updates:")
            for index, entry in enumerate(recent_notes, start=1):
                self.output_fn(f"{index}. {entry}")
            older_note_count = max(0, len(story_notes) - len(recent_notes))
            if older_note_count:
                self.output_fn(f"- Older notes archived in this run: {older_note_count}")

    def show_party(self) -> None:
        assert self.state is not None
        self.banner("Party")
        if self.rich_ledger_enabled():
            summary = Table.grid(expand=True, padding=(0, 1))
            summary.add_column(style=f"bold {rich_style_name('light_yellow')}", width=12)
            summary.add_column(ratio=1)
            summary.add_row("Progress", self.xp_progress_summary())
            summary.add_row("Marks", marks_label(self.state.gold))
            summary.add_row("Short rests", str(self.state.short_rests_remaining))
            summary.add_row(
                "Carry",
                f"{self.current_inventory_weight():.1f}/{self.carrying_capacity()} lb",
            )
            active_panels = [self.member_summary_panel(member) for member in self.state.party_members()]
            camp_content = (
                Group(*(self.rich_from_ansi(f"- {self.companion_status_line(companion)}") for companion in self.state.camp_companions))
                if self.state.camp_companions
                else self.rich_text("No one is waiting back at camp.", "light_aqua", dim=True)
            )
            if self.emit_rich(
                Group(
                    Panel(
                        summary,
                        title=self.rich_text("Company Ledger", "light_yellow", bold=True),
                        border_style=rich_style_name("light_yellow"),
                        box=box.ROUNDED,
                        padding=(0, 1),
                    ),
                    Panel(
                        Columns(active_panels, expand=True, equal=True),
                        title=self.rich_text("Active Party", "light_green", bold=True),
                        border_style=rich_style_name("light_green"),
                        box=box.ROUNDED,
                        padding=(0, 1),
                    ),
                    Panel(
                        camp_content,
                        title=self.rich_text("Camp Companions", "light_aqua", bold=True),
                        border_style=rich_style_name("light_aqua"),
                        box=box.ROUNDED,
                        padding=(0, 1),
                    ),
                ),
                width=max(108, self.rich_console_width()),
            ):
                return
        self.say(
            f"{self.xp_progress_summary()} | Marks: {marks_label(self.state.gold)} | "
            f"Short rests left: {self.state.short_rests_remaining} | "
            f"Carry weight: {self.current_inventory_weight():.1f}/{self.carrying_capacity()} lb"
        )
        self.say("Active party:")
        for member in self.state.party_members():
            conditions = self.character_condition_summary(member)
            temp_hp = f", temp {member.temp_hp}" if member.temp_hp else ""
            self.output_fn(
                f"- {member.name}: Level {member.level} {member.public_identity}, "
                f"{self.character_health_summary(member)}, {target_guard_label(member.armor_class)}{temp_hp}, "
                f"conditions [{conditions}]"
            )
            story_modifiers = self.story_skill_modifier_summary(member)
            if story_modifiers != "None":
                self.output_fn(f"  Story modifiers: {story_modifiers}")
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
            f"{member.name}: Level {member.level} {member.public_identity} | "
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
        if self.rich_ledger_enabled():
            if self.emit_rich(
                self.build_character_sheet_rich_renderable(member),
                width=self.character_sheet_render_width(),
            ):
                return
        self.say(
            f"Level {member.level} {member.public_identity} | Background: {member.background} | "
            f"Status: {self.character_health_summary(member)} | {target_guard_label(member.armor_class)} | "
            f"Training bonus +{member.proficiency_bonus}"
        )
        self.output_fn("")
        self.say("Ability Scores:")
        for ability in ABILITY_ORDER:
            score = member.ability_scores[ability]
            modifier = member.ability_mod(ability)
            self.output_fn(f"- {ability_label(ability, include_code=True)}: {score} ({modifier:+d})")
        self.output_fn("")
        self.say("Combat:")
        self.output_fn(f"- Weapon: {member.weapon.name} | strike +{member.attack_bonus()} | damage bonus +{member.damage_bonus()}")
        self.output_fn(f"- Hit die: d{member.hit_die} | Temp HP: {member.temp_hp} | Conditions: {self.character_condition_summary(member)}")
        if member.spellcasting_ability is not None:
            spell_attack = self.spell_attack_bonus(member, member.spellcasting_ability)
            spellcasting_line = f"- Channeling: {ability_label(member.spellcasting_ability, include_code=True)} | channel strike +{spell_attack}"
            magic_bar = self.format_member_magic_bar(member)
            if magic_bar is not None:
                spellcasting_line += f" | {magic_bar}"
            self.output_fn(spellcasting_line)
        story_modifiers = self.story_skill_modifier_display_lines(member)
        if story_modifiers:
            self.output_fn("")
            self.say("Story Modifiers:")
            for line in story_modifiers:
                self.output_fn(f"- {line}")
        self.output_fn("")
        self.say("Resist Checks:")
        for ability in ABILITY_ORDER:
            proficient = "*" if ability in member.saving_throw_proficiencies else ""
            self.output_fn(f"- {ability_label(ability, include_code=True)}{proficient}: {member.save_bonus(ability):+d}")
        self.output_fn("")
        self.say("Skills:")
        for skill in sorted(SKILL_TO_ABILITY):
            markers = []
            if skill in member.skill_proficiencies:
                markers.append("trained")
            if skill in member.skill_expertise:
                markers.append("deep")
            suffix = f" ({', '.join(markers)})" if markers else ""
            self.output_fn(f"- {skill_option_label(skill)}: {member.skill_bonus(skill):+d}{suffix}")
        self.output_fn("")
        self.say("Features & Training:")
        self.output_fn(
            f"- Features: {', '.join(self.format_feature_name(feature) for feature in member.features) if member.features else 'None'}"
        )
        self.output_fn(
            f"- Background / bonus training: {', '.join(member.bonus_proficiencies) if member.bonus_proficiencies else 'None'}"
        )
        resources_text = self.member_resource_summary(member)
        if resources_text != "None":
            self.output_fn(f"- Resources: {resources_text}")
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
