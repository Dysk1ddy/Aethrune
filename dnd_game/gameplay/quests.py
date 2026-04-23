from __future__ import annotations

from ..data.quests import QUESTS, QUEST_ORDER, QuestDefinition, QuestLogEntry
from ..data.story.public_terms import marks_label
from ..items import get_item
from ..ui.colors import rich_style_name
from ..ui.rich_render import Panel, Table, box


class QuestMixin:
    def render_new_quest_panel(self, definition: QuestDefinition) -> bool:
        if not (
            callable(getattr(self, "should_use_rich_ui", None))
            and self.should_use_rich_ui()
            and Panel is not None
            and Table is not None
            and box is not None
        ):
            return False
        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(style=f"bold {rich_style_name('light_yellow')}", width=11)
        table.add_column(ratio=1)
        table.add_row("Quest", definition.title)
        table.add_row("Giver", definition.giver)
        table.add_row("Location", definition.location)
        table.add_row("Objective", definition.objective)
        table.add_row("Turn in", definition.turn_in)
        table.add_row("Rewards", self.quest_reward_summary(definition.quest_id))
        if definition.accepted_text:
            table.add_row("Brief", definition.accepted_text)
        return self.emit_rich(
            Panel(
                table,
                title=self.rich_text("Quest Added", "light_yellow", bold=True),
                border_style=rich_style_name("light_yellow"),
                box=box.DOUBLE,
                padding=(0, 1),
            ),
            width=max(100, self.rich_console_width()),
        )

    def ensure_quest_log(self) -> None:
        if self.state is None:
            return
        self.state.quests = dict(self.state.quests)
        self.refresh_quest_statuses(announce=False)

    def get_quest_definition(self, quest_id: str) -> QuestDefinition:
        return QUESTS[quest_id]

    def get_quest_entry(self, quest_id: str) -> QuestLogEntry | None:
        assert self.state is not None
        return self.state.quests.get(quest_id)

    def has_quest(self, quest_id: str) -> bool:
        return self.get_quest_entry(quest_id) is not None

    def quest_status(self, quest_id: str) -> str | None:
        entry = self.get_quest_entry(quest_id)
        if entry is None:
            return None
        return entry.status

    def quest_is_ready(self, quest_id: str) -> bool:
        return self.quest_status(quest_id) == "ready_to_turn_in"

    def quest_is_completed(self, quest_id: str) -> bool:
        return self.quest_status(quest_id) == "completed"

    def append_quest_note(self, quest_id: str, note: str) -> None:
        if not note:
            return
        entry = self.get_quest_entry(quest_id)
        if entry is not None and note not in entry.notes:
            entry.notes.append(note)

    def quest_objective_met(self, quest_id: str) -> bool:
        assert self.state is not None
        definition = self.get_quest_definition(quest_id)
        return all(bool(self.state.flags.get(flag)) for flag in definition.completion_flags)

    def refresh_quest_statuses(self, *, announce: bool = True) -> None:
        assert self.state is not None
        for quest_id in QUEST_ORDER:
            entry = self.state.quests.get(quest_id)
            if entry is None or entry.status == "completed":
                continue
            definition = self.get_quest_definition(quest_id)
            should_be_ready = self.quest_objective_met(quest_id)
            if should_be_ready and entry.status != "ready_to_turn_in":
                entry.status = "ready_to_turn_in"
                self.append_quest_note(quest_id, definition.ready_text)
                self.add_journal(f"Quest updated: {definition.title} is ready to turn in.")
                if announce:
                    self.say(f"Quest updated: {definition.title}.")
                    self.say(definition.ready_text)
            elif not should_be_ready and entry.status == "ready_to_turn_in":
                entry.status = "active"

    def quest_reward_summary(self, quest_id: str) -> str:
        definition = self.get_quest_definition(quest_id)
        parts: list[str] = []
        if definition.reward.xp:
            parts.append(f"{definition.reward.xp} XP")
        if definition.reward.gold:
            parts.append(marks_label(definition.reward.gold))
        for item_id, quantity in definition.reward.items.items():
            parts.append(f"{get_item(item_id).name} x{quantity}")
        if definition.reward.flags:
            parts.append("story unlocks")
        if definition.reward.merchant_attitudes:
            parts.append("better trade terms")
        if definition.reward.act2_metrics:
            parts.append("campaign momentum")
        return ", ".join(parts) if parts else "No listed reward."

    def quest_reward_flag_label(self, flag: str) -> str:
        cleaned = flag
        for prefix in ("quest_reward_", "act2_", "act3_"):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :]
                break
        return cleaned.replace("_", " ").title()

    def apply_quest_unlock_rewards(self, definition: QuestDefinition) -> None:
        assert self.state is not None
        reward = definition.reward
        unlock_labels: list[str] = []
        for flag, value in reward.flags.items():
            self.state.flags[flag] = value
            unlock_labels.append(self.quest_reward_flag_label(flag))
        if unlock_labels:
            unlock_line = ", ".join(unlock_labels)
            self.say(f"Story reward unlocked: {unlock_line}.")
            self.add_journal(f"Story reward from {definition.title}: {unlock_line}.")

        for merchant_id, amount in reward.merchant_attitudes.items():
            self.adjust_merchant_attitude(merchant_id, amount, reason=f"{definition.giver}'s gratitude")

        shift_metric = getattr(self, "act2_shift_metric", None)
        metric_names = getattr(self, "ACT2_METRIC_NAMES", {})
        for metric_key, delta in reward.act2_metrics.items():
            if callable(shift_metric) and metric_key in metric_names:
                shift_metric(metric_key, delta, f"{definition.title} turned in")
                continue
            current = int(self.state.flags.get(metric_key, 0) or 0)
            self.state.flags[metric_key] = current + delta

    def quest_entries_by_status(self, status: str) -> list[tuple[QuestDefinition, QuestLogEntry]]:
        assert self.state is not None
        entries: list[tuple[QuestDefinition, QuestLogEntry]] = []
        for quest_id in QUEST_ORDER:
            entry = self.state.quests.get(quest_id)
            if entry is None or entry.status != status:
                continue
            entries.append((self.get_quest_definition(quest_id), entry))
        return entries

    def grant_quest(self, quest_id: str, *, note: str = "") -> bool:
        assert self.state is not None
        existing = self.state.quests.get(quest_id)
        if existing is not None:
            self.append_quest_note(quest_id, note)
            return False
        definition = self.get_quest_definition(quest_id)
        self.state.quests[quest_id] = QuestLogEntry(quest_id=quest_id)
        self.append_quest_note(quest_id, definition.accepted_text)
        self.append_quest_note(quest_id, note)
        self.add_journal(f"Quest accepted: {definition.title}.")
        if not self.render_new_quest_panel(definition):
            self.banner(f"Quest Added: {definition.title}")
            self.say(definition.accepted_text)
            self.say(f"Objective: {definition.objective}")
            self.say(f"Rewards: {self.quest_reward_summary(quest_id)}.")
        self.refresh_quest_statuses(announce=False)
        return True

    def turn_in_quest(self, quest_id: str, *, giver: str) -> bool:
        assert self.state is not None
        self.refresh_quest_statuses(announce=False)
        entry = self.state.quests.get(quest_id)
        if entry is None or entry.status != "ready_to_turn_in":
            return False
        definition = self.get_quest_definition(quest_id)
        if giver != definition.giver:
            self.say(f"{definition.title} has to be turned in to {definition.giver}.")
            return False
        entry.status = "completed"
        self.append_quest_note(quest_id, definition.turn_in_text)
        self.add_journal(f"Quest completed: {definition.title}.")
        self.say(definition.turn_in_text)
        if definition.reward.xp or definition.reward.gold:
            self.reward_party(xp=definition.reward.xp, gold=definition.reward.gold, reason=definition.title)
        if definition.reward.items:
            received_parts: list[str] = []
            for item_id, quantity in definition.reward.items.items():
                added = self.add_inventory_item(item_id, quantity, source=definition.giver)
                if added:
                    received_parts.append(f"{get_item(item_id).name} x{added}")
            if received_parts:
                reward_line = ", ".join(received_parts)
                self.say(f"Additional quest reward: {reward_line}.")
                self.add_journal(f"Quest reward from {definition.title}: {reward_line}.")
        self.apply_quest_unlock_rewards(definition)
        return True
