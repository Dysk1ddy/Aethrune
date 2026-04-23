from __future__ import annotations

from ..content import BACKGROUNDS, CLASSES, RACES, build_character
from ..data.story.public_terms import marks_label
from ..items import get_item
from ..data.story.camp_banter import CAMP_BANTERS
from ..data.story.companions import COMPANION_PROFILES
from ..ui.colors import rich_style_name
from ..ui.rich_render import Columns, Group, Panel, Table, box


class CampMixin:
    def camp_digest_lines(self) -> list[str]:
        getter = getattr(self, "act2_camp_digest_lines", None)
        if not callable(getter):
            return []
        return list(getter())

    def render_camp_overview(self) -> None:
        assert self.state is not None
        digest_lines = self.camp_digest_lines()
        if not (
            callable(getattr(self, "should_use_rich_ui", None))
            and self.should_use_rich_ui()
            and Columns is not None
            and Group is not None
            and Panel is not None
            and Table is not None
            and box is not None
        ):
            if digest_lines:
                self.say("Act II Digest:")
                for line in digest_lines:
                    self.output_fn(f"- {line}")
            return
        status = Table.grid(expand=True, padding=(0, 1))
        status.add_column(style=f"bold {rich_style_name('light_yellow')}", width=12)
        status.add_column(ratio=1)
        status.add_row("Marks", marks_label(self.state.gold))
        status.add_row("Short rests", str(self.state.short_rests_remaining))
        status.add_row(
            "Carry",
            f"{self.current_inventory_weight():.1f}/{self.carrying_capacity()} lb",
        )
        status.add_row("Active party", str(len(self.state.party_members())))
        status.add_row("Camp roster", str(len(self.state.camp_companions)))

        active_party = Group(
            *(
                self.rich_from_ansi(
                    f"{member.name}: {self.character_health_summary(member)} | Guard {member.armor_class} | "
                    f"{self.character_condition_summary(member)}"
                )
                for member in self.state.party_members()
            )
        )
        camp_roster = (
            Group(*(self.rich_from_ansi(self.companion_status_line(companion)) for companion in self.state.camp_companions))
            if self.state.camp_companions
            else self.rich_text("No companions are resting at camp right now.", "light_aqua", dim=True)
        )
        has_banter = bool(self.available_camp_banters())
        option_lines = [
            self.rich_text("1. Party and roster", "light_green"),
            self.rich_text("2. Supplies and equipment", "light_green"),
            self.rich_text("3. Rest and recovery", "light_green"),
            self.rich_text("4. Talk to a companion", "light_green"),
            self.rich_text("5. View journal", "light_green"),
            self.rich_text("6. Speak to the magic mirror", "light_green"),
            self.rich_text("7. Break camp", "light_green"),
        ]
        if has_banter:
            option_lines.append(self.rich_text("8. Listen around the campfire", "light_green"))
        options = Group(*option_lines)
        panels: list[object] = [
            Panel(
                status,
                title=self.rich_text("Camp Ledger", "light_yellow", bold=True),
                border_style=rich_style_name("light_yellow"),
                box=box.ROUNDED,
                padding=(0, 1),
            )
        ]
        if digest_lines:
            digest_content = Group(*(self.rich_from_ansi(line) for line in digest_lines))
            panels.append(
                Panel(
                    digest_content,
                    title=self.rich_text("Act II Digest", "light_aqua", bold=True),
                    border_style=rich_style_name("light_aqua"),
                    box=box.ROUNDED,
                    padding=(0, 1),
                )
            )
        panels.append(
            Columns(
                [
                    Panel(
                        active_party,
                        title=self.rich_text("Around The Fire", "light_green", bold=True),
                        border_style=rich_style_name("light_green"),
                        box=box.ROUNDED,
                        padding=(0, 1),
                    ),
                    Panel(
                        camp_roster,
                        title=self.rich_text("Camp Roster", "light_aqua", bold=True),
                        border_style=rich_style_name("light_aqua"),
                        box=box.ROUNDED,
                        padding=(0, 1),
                    ),
                    Panel(
                        options,
                        title=self.rich_text("Camp Actions", "light_red", bold=True),
                        border_style=rich_style_name("light_red"),
                        box=box.ROUNDED,
                        padding=(0, 1),
                    ),
                ],
                expand=True,
                equal=True,
            )
        )
        self.emit_rich(
            Group(*panels),
            width=max(108, self.rich_console_width()),
        )

    def open_camp_menu(self) -> None:
        play_music_for_context = getattr(self, "play_music_for_context", None)
        refresh_scene_music = getattr(self, "refresh_scene_music", None)
        if callable(play_music_for_context):
            play_music_for_context("camp", restart=True)
        try:
            self.banner("Camp")
            self.say(
                "Canvas, bedrolls, cookfire smoke, and the impossible magic mirror make camp the one place on the road "
                "where the party can breathe, reorganize, and speak honestly."
            )
            while True:
                self.render_camp_overview()
                options = [
                    "Party and roster",
                    "Supplies and equipment",
                    "Rest and recovery",
                    "Talk to a companion",
                    "View journal",
                    "Speak to the magic mirror (100 marks)",
                    "Break camp",
                ]
                if self.available_camp_banters():
                    options.append("Listen around the campfire")
                choice = self.choose(
                    "How do you spend this stop at camp?",
                    options,
                    allow_meta=False,
                )
                if choice == 1:
                    self.open_camp_party_menu()
                elif choice == 2:
                    self.open_camp_supplies_menu()
                elif choice == 3:
                    self.open_camp_recovery_menu()
                elif choice == 4:
                    self.talk_to_companion()
                elif choice == 5:
                    self.show_journal()
                elif choice == 6:
                    self.visit_magic_mirror()
                elif choice == 7:
                    self.say("The campfire is banked, straps are tightened, and the road calls again.")
                    return
                else:
                    self.listen_around_campfire()
        finally:
            if callable(refresh_scene_music):
                refresh_scene_music()

    def open_camp_party_menu(self) -> None:
        while True:
            choice = self.choose(
                "Choose a party task.",
                [
                    "Review the active party",
                    "Review the full roster",
                    "View character sheets",
                    "Manage the active party",
                    "Back",
                ],
                allow_meta=False,
            )
            if choice == 1:
                self.show_party()
            elif choice == 2:
                self.show_full_roster()
            elif choice == 3:
                self.show_character_sheets()
            elif choice == 4:
                self.manage_party_roster()
            else:
                return

    def open_camp_supplies_menu(self) -> None:
        while True:
            choice = self.choose(
                "Choose how the company handles supplies and gear.",
                [
                    "View all inventory",
                    "View inventory by category",
                    "Use a consumable or scroll",
                    "Manage inventory",
                    "Manage equipment",
                    "Back",
                ],
                allow_meta=False,
            )
            if choice == 1:
                self.show_inventory()
            elif choice == 2:
                self.review_inventory_by_filter()
            elif choice == 3:
                self.use_item_from_inventory()
            elif choice == 4:
                self.manage_inventory()
            elif choice == 5:
                self.manage_equipment()
            else:
                return

    def open_camp_recovery_menu(self) -> None:
        assert self.state is not None
        while True:
            dead_allies = self.dead_allies_in_company()
            revivify_ready = bool(dead_allies)
            revivify_name = get_item("scroll_revivify").name
            revivify_text = (
                f"Use {revivify_name} on a dead ally"
                if self.state.inventory.get("scroll_revivify", 0) > 0
                else f"Use {revivify_name} on a dead ally (need one)"
            )
            short_rest_text = "Take a short rest"
            if self.state.short_rests_remaining <= 0:
                short_rest_text = "Take a short rest (none remaining)"
            options = [short_rest_text, "Take a long rest"]
            if revivify_ready:
                options.append(revivify_text)
            options.append("Back")
            choice = self.choose("Choose how the party recovers tonight.", options, allow_meta=False)
            if choice == 1:
                self.short_rest()
            elif choice == 2:
                self.apply_scene_companion_support("camp_rest")
                self.long_rest()
            elif revivify_ready and choice == 3:
                self.use_scroll_of_revivify()
            else:
                return

    def dead_allies_in_company(self) -> list:
        assert self.state is not None
        return [companion for companion in self.state.all_companions() if companion.dead]

    def use_scroll_of_revivify(self) -> bool:
        assert self.state is not None
        item = get_item("scroll_revivify")
        dead_allies = self.dead_allies_in_company()
        if not dead_allies:
            self.say("No fallen ally in camp can be reached by revivify right now.")
            return False
        if self.state.inventory.get("scroll_revivify", 0) <= 0:
            self.say(f"You need {item.name} in the shared inventory before you can attempt the rite.")
            return False
        choice = self.choose(
            "Choose who you restore with the scroll.",
            [self.companion_status_line(companion) for companion in dead_allies] + ["Back"],
            allow_meta=False,
        )
        if choice == len(dead_allies) + 1:
            return False
        target = dead_allies[choice - 1]
        if not self.remove_inventory_item("scroll_revivify"):
            self.say("The scroll is no longer in the shared inventory.")
            return False
        target.dead = False
        target.current_hp = min(target.max_hp, max(1, item.revive_hp))
        target.stable = False
        target.death_successes = 0
        target.death_failures = 0
        target.temp_hp = 0
        target.conditions.clear()
        self.say(f"The scroll burns down in silver ash, and {target.name} returns to life at {target.current_hp} HP.")
        self.add_journal(f"{target.name} was restored to life at camp with {item.name}.")
        return True

    def show_full_roster(self) -> None:
        assert self.state is not None
        self.banner("Company Roster")
        if (
            callable(getattr(self, "should_use_rich_ui", None))
            and self.should_use_rich_ui()
            and Columns is not None
            and Group is not None
            and Panel is not None
            and box is not None
        ):
            active = [self.state.player, *self.state.companions]
            active_panel = Panel(
                Group(
                    *(
                        self.rich_from_ansi(
                            f"{member.name}: Level {member.level} {member.race} {member.class_name} | "
                            f"{self.character_health_summary(member)}"
                        )
                        for member in active
                    )
                ),
                title=self.rich_text("Active Party", "light_green", bold=True),
                border_style=rich_style_name("light_green"),
                box=box.ROUNDED,
                padding=(0, 1),
            )
            camp_panel = Panel(
                Group(*(self.rich_from_ansi(self.companion_status_line(companion)) for companion in self.state.camp_companions))
                if self.state.camp_companions
                else self.rich_text("No one is assigned to camp.", "light_aqua", dim=True),
                title=self.rich_text("Camp Companions", "light_aqua", bold=True),
                border_style=rich_style_name("light_aqua"),
                box=box.ROUNDED,
                padding=(0, 1),
            )
            if self.emit_rich(
                Group(
                    Panel(
                        self.rich_text(
                            f"Active party limit: {self.active_companion_limit() + 1} total, including you.",
                            "light_yellow",
                        ),
                        title=self.rich_text("Company Roster", "light_yellow", bold=True),
                        border_style=rich_style_name("light_yellow"),
                        box=box.ROUNDED,
                        padding=(0, 1),
                    ),
                    Columns([active_panel, camp_panel], expand=True, equal=True),
                ),
                width=max(108, self.rich_console_width()),
            ):
                return
        self.say(f"Active party limit: {self.active_companion_limit() + 1} total, including you.")
        self.output_fn(f"- {self.state.player.name}: Player character | Level {self.state.player.level}")
        for companion in self.state.all_companions():
            self.output_fn(f"- {self.companion_status_line(companion)}")

    def manage_party_roster(self) -> None:
        assert self.state is not None
        while True:
            options = ["Send an active companion to camp"]
            if self.state.camp_companions:
                options.append("Call a camp companion into the active party")
            options.append("Back")
            choice = self.choose("Manage who travels in the active party.", options, allow_meta=False)
            if choice == 1:
                active = list(self.state.companions)
                if not active:
                    self.say("No companions are currently in the active party.")
                    continue
                picked = self.choose_ally(active, prompt="Choose who returns to camp.")
                self.move_companion_to_camp(picked)
            elif len(options) == 3 and choice == 2:
                picked = self.choose_ally(self.state.camp_companions, prompt="Choose who joins the active party.")
                self.move_companion_to_party(picked)
            else:
                return

    def camp_topic_is_available(self, topic: dict[str, object]) -> bool:
        assert self.state is not None

        required_flags = topic.get("requires_flags", ())
        if isinstance(required_flags, str):
            required_flags = (required_flags,)
        if any(not self.state.flags.get(str(flag)) for flag in required_flags):
            return False

        blocked_flags = topic.get("blocked_flags", ())
        if isinstance(blocked_flags, str):
            blocked_flags = (blocked_flags,)
        if any(self.state.flags.get(str(flag)) for flag in blocked_flags):
            return False

        required_resolution = topic.get("requires_blackwake_resolution")
        if required_resolution and self.state.flags.get("blackwake_resolution") != required_resolution:
            return False

        return True

    def camp_banter_seen_flag(self, banter: dict[str, object]) -> str:
        return str(banter.get("seen_flag") or f"{banter['id']}_seen")

    def camp_companion_by_id(self, companion_id: str):
        assert self.state is not None
        for companion in self.state.all_companions():
            if companion.companion_id == companion_id and not companion.dead:
                return companion
        return None

    def camp_companion_name(self, companion_id: str) -> str:
        companion = self.camp_companion_by_id(companion_id)
        if companion is not None:
            return companion.name
        profile = COMPANION_PROFILES.get(companion_id, {})
        return str(profile.get("name", companion_id.replace("_", " ").title()))

    def camp_condition_is_available(self, entry: dict[str, object]) -> bool:
        assert self.state is not None

        required_flags = entry.get("requires_flags", ())
        if isinstance(required_flags, str):
            required_flags = (required_flags,)
        if any(not self.state.flags.get(str(flag)) for flag in required_flags):
            return False

        any_flags = entry.get("requires_any_flags", ())
        if isinstance(any_flags, str):
            any_flags = (any_flags,)
        if any_flags and not any(self.state.flags.get(str(flag)) for flag in any_flags):
            return False

        blocked_flags = entry.get("blocked_flags", ())
        if isinstance(blocked_flags, str):
            blocked_flags = (blocked_flags,)
        if any(self.state.flags.get(str(flag)) for flag in blocked_flags):
            return False

        for flag, expected in dict(entry.get("requires_flag_values", {})).items():
            if self.state.flags.get(str(flag)) != expected:
                return False

        for flag, allowed_values in dict(entry.get("requires_any_flag_values", {})).items():
            values = allowed_values if isinstance(allowed_values, (list, tuple, set)) else (allowed_values,)
            if self.state.flags.get(str(flag)) not in values:
                return False

        for flag, minimum in dict(entry.get("min_flags", {})).items():
            try:
                if int(self.state.flags.get(str(flag), 0) or 0) < int(minimum):
                    return False
            except (TypeError, ValueError):
                return False

        for flag, maximum in dict(entry.get("max_flags", {})).items():
            try:
                if int(self.state.flags.get(str(flag), 0) or 0) > int(maximum):
                    return False
            except (TypeError, ValueError):
                return False

        return True

    def camp_banter_is_available(self, banter: dict[str, object]) -> bool:
        assert self.state is not None
        if self.state.flags.get(self.camp_banter_seen_flag(banter)):
            return False
        if not self.camp_condition_is_available(banter):
            return False
        for companion_id in list(banter.get("participants", ())):
            if self.camp_companion_by_id(str(companion_id)) is None:
                return False
        return True

    def available_camp_banters(self) -> list[dict[str, object]]:
        available = [banter for banter in CAMP_BANTERS if self.camp_banter_is_available(banter)]
        return sorted(available, key=lambda banter: (-int(banter.get("priority", 0)), str(banter.get("id", ""))))

    def camp_banter_option_label(self, banter: dict[str, object]) -> str:
        participant_names = [self.camp_companion_name(str(companion_id)) for companion_id in banter.get("participants", ())]
        return f"{banter['title']} ({', '.join(participant_names)})"

    def listen_around_campfire(self) -> None:
        available = self.available_camp_banters()
        if not available:
            self.say("The campfire is companionable tonight, but no new conversation rises above the crackle.")
            return
        if len(available) == 1:
            self.run_camp_banter(available[0])
            return
        options = [self.camp_banter_option_label(banter) for banter in available]
        options.append("Back")
        choice = self.choose("Which campfire conversation do you follow?", options, allow_meta=False)
        if choice == len(options):
            return
        self.run_camp_banter(available[choice - 1])

    def run_camp_banter(self, banter: dict[str, object]) -> None:
        assert self.state is not None
        if not self.camp_banter_is_available(banter):
            self.say("That campfire conversation is not available right now.")
            return
        self.banner(str(banter["title"]))
        intro = str(banter.get("intro", "")).strip()
        if intro:
            self.say(intro)
        for line in list(banter.get("lines", ())):
            if isinstance(line, tuple):
                speaker_id, text = line
                self.speaker(self.camp_companion_name(str(speaker_id)), str(text))
                continue
            if not isinstance(line, dict) or not self.camp_condition_is_available(line):
                continue
            text = str(line.get("text", "")).strip()
            if not text:
                continue
            speaker_id = str(line.get("speaker", "")).strip()
            if speaker_id:
                self.speaker(self.camp_companion_name(speaker_id), text)
            else:
                self.say(text)
        seen_flag = self.camp_banter_seen_flag(banter)
        self.state.flags[seen_flag] = True
        for companion_id in list(banter.get("participants", ())):
            companion = self.camp_companion_by_id(str(companion_id))
            if companion is None:
                continue
            seen = companion.bond_flags.setdefault("camp_banters", [])
            if banter["id"] not in seen:
                seen.append(str(banter["id"]))
        self.apply_camp_banter_effects(banter)

    def apply_camp_banter_effects(self, banter: dict[str, object]) -> None:
        refresh_act3 = False
        for effect in list(banter.get("effects", ())):
            if not isinstance(effect, dict) or not self.camp_condition_is_available(effect):
                continue
            self.apply_camp_banter_effect(effect)
            if "act3_reveal_resistance_bonus" in dict(effect.get("flag_increments", {})):
                refresh_act3 = True
        if refresh_act3 and callable(getattr(self, "act3_refresh_post_reveal_state", None)):
            self.act3_refresh_post_reveal_state()

    def apply_camp_banter_effect(self, effect: dict[str, object]) -> None:
        assert self.state is not None
        for flag in list(effect.get("set_flags", ())):
            self.state.flags[str(flag)] = True
        for flag, delta in dict(effect.get("flag_increments", {})).items():
            current = self.state.flags.get(str(flag), 0)
            if isinstance(current, bool):
                current = int(current)
            try:
                updated = int(current or 0) + int(delta)
            except (TypeError, ValueError):
                updated = int(delta)
            if str(flag) in {"ninth_ledger_pressure", "act3_reveal_resistance_bonus"}:
                updated = max(0, min(5, updated))
            self.state.flags[str(flag)] = updated
            self.say(f"{self.camp_flag_label(str(flag))} is now {updated}.")
        for companion_id, delta in dict(effect.get("companion_deltas", {})).items():
            companion = self.camp_companion_by_id(str(companion_id))
            if companion is not None:
                self.adjust_companion_disposition(companion, int(delta), "campfire conversation")
        for metric_key, delta in dict(effect.get("metric_deltas", {})).items():
            self.apply_camp_banter_metric_delta(str(metric_key), int(delta))
        for status, duration in dict(effect.get("player_statuses", {})).items():
            self.apply_status(self.state.player, str(status), int(duration), source="campfire resolve")
        for companion_id, lore_entry in dict(effect.get("companion_lore", {})).items():
            companion = self.camp_companion_by_id(str(companion_id))
            if companion is not None and lore_entry not in companion.lore:
                companion.lore.append(str(lore_entry))
        for clue in list(effect.get("clues", ())):
            self.add_clue(str(clue))
        journal = str(effect.get("journal", "")).strip()
        if journal:
            self.add_journal(journal)

    def camp_flag_label(self, flag: str) -> str:
        labels = {
            "act3_companion_testimony_count": "Companion testimony",
            "act3_mercy_or_contradiction_count": "Mercy and contradiction",
            "act3_reveal_resistance_bonus": "Ledger resistance",
            "act2_bonus_whisper_pressure": "Act II bonus whisper pressure",
        }
        return labels.get(flag, flag.replace("_", " ").title())

    def apply_camp_banter_metric_delta(self, metric_key: str, delta: int) -> None:
        assert self.state is not None
        if not delta:
            return
        if metric_key.startswith("act2_") and callable(getattr(self, "act2_shift_metric", None)):
            self.act2_shift_metric(metric_key, delta, "campfire conversation")
            return
        if metric_key in getattr(self, "ACT1_METRIC_NAMES", {}):
            current = self.act1_metric_value(metric_key)
            updated = self.act1_adjust_metric(metric_key, delta)
            if updated == current:
                return
            direction = "rises" if updated > current else "falls"
            label = self.ACT1_METRIC_NAMES.get(metric_key, metric_key.replace("_", " ").title())
            metric_labels = getattr(self, "ACT1_METRIC_LABELS", {}).get(metric_key)
            if metric_labels:
                bounded = max(0, min(updated, len(metric_labels) - 1))
                self.say(f"{label} {direction} to {metric_labels[bounded]} (campfire conversation).")
            else:
                self.say(f"{label} {direction} to {updated} (campfire conversation).")

    def talk_to_companion(self) -> None:
        assert self.state is not None
        roster = self.state.all_companions()
        if not roster:
            self.say("No companions are with your wider company yet.")
            return
        companion = self.choose_ally(roster, prompt="Choose who you want to talk to at camp.")
        profile = COMPANION_PROFILES[companion.companion_id]
        self.banner(companion.name)
        self.say(profile["summary"])
        self.say(f"Relationship: {self.relationship_label_for(companion)} ({companion.disposition}).")
        if companion.disposition >= 6:
            self.speaker(companion.name, profile["great_dialogue"])
        if companion.disposition >= 9:
            self.speaker(companion.name, profile["exceptional_dialogue"])
        while True:
            talked_topics = set(companion.bond_flags.get("talked_topics", []))
            options: list[tuple[str, str]] = []
            available_topics = [
                topic for topic in profile["camp_topics"] if self.camp_topic_is_available(topic)
            ]
            for topic in available_topics:
                prefix = "" if topic["id"] not in talked_topics else "(Already discussed) "
                options.append((topic["id"], prefix + topic["prompt"]))
            options.append(("view", self.action_option("Ask how they see you now.")))
            options.append(("leave", self.action_option("Return to the campfire.")))
            choice = self.choose(f"What do you say to {companion.name}?", [text for _, text in options], allow_meta=False)
            topic_id, _ = options[choice - 1]
            if topic_id == "view":
                self.describe_companion_relationship(companion)
                continue
            if topic_id == "leave":
                return
            topic = next(entry for entry in available_topics if entry["id"] == topic_id)
            self.player_choice_output(topic["prompt"])
            self.speaker(companion.name, topic["response"])
            if topic_id not in talked_topics:
                companion.bond_flags.setdefault("talked_topics", []).append(topic_id)
                self.adjust_companion_disposition(companion, int(topic["delta"]), reason=f"talking with {companion.name}")
                if companion not in self.state.all_companions():
                    return
            else:
                self.say(f"{companion.name} has already shared most of what they mean to on that subject.")

    def describe_companion_relationship(self, companion) -> None:
        label = self.relationship_label_for(companion)
        if label == "Exceptional":
            self.say(f"{companion.name} trusts you completely and speaks as if your futures are tied together.")
        elif label == "Great":
            self.say(f"{companion.name} trusts your judgment and volunteers more than they hide.")
        elif label == "Good":
            self.say(f"{companion.name} is warming to you and increasingly willing to confide in you.")
        elif label == "Bad":
            self.say(f"{companion.name} is frustrated and keeping emotional distance.")
        elif label == "Terrible":
            self.say(f"{companion.name} has almost no trust left to give.")
        else:
            self.say(f"{companion.name} is still measuring you carefully.")

    def visit_magic_mirror(self) -> None:
        assert self.state is not None
        if self.state.gold < 100:
            self.say("The mirror's silver frame hums once, then falls quiet. You need 100 marks for a full respec.")
            return
        self.say(
            "The magic mirror shows not your reflection, but a dozen possible versions of the life you might have led."
        )
        if not self.confirm("Spend 100 marks to fully respec your character?"):
            return
        previous_level = self.state.player.level
        previous_name = self.state.player.name
        self.state.gold -= 100
        race = self.choose_named_option("Choose a race", RACES)
        class_name = self.choose_named_option("Choose a class", CLASSES)
        background = self.choose_named_option("Choose a background", BACKGROUNDS)
        base_scores = self.choose_ability_scores()
        class_skills = self.choose_class_skills(race, class_name, background)
        expertise: list[str] = []
        if class_name == "Rogue":
            expertise = self.choose_expertise(race, background, class_skills)
        rebuilt = build_character(
            name=previous_name,
            race=race,
            class_name=class_name,
            background=background,
            base_ability_scores=base_scores,
            class_skill_choices=class_skills,
            expertise_choices=expertise,
            inventory={},
        )
        rebuilt.inventory.clear()
        self.state.player = rebuilt
        self.ensure_state_integrity()
        for next_level in range(2, previous_level + 1):
            self.level_up_character(self.state.player, next_level)
        self.state.player.current_hp = self.state.player.max_hp
        self.add_journal(f"The camp mirror reshaped {previous_name}'s training and talents for 100 marks.")
        self.say(f"The mirror settles. {previous_name} steps away remade, still level {previous_level}.")
