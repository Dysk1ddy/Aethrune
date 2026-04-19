from __future__ import annotations

from ..data.story.companions import COMPANION_PROFILES
from ..data.story.dialogue_inputs import DIALOGUE_INPUTS


class DialogueInputMixin:
    def dialogue_input_sequence(self, value: object) -> tuple[object, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            return (value,)
        if isinstance(value, (list, tuple, set)):
            return tuple(value)
        return (value,)

    def dialogue_input_seen_flag(self, entry: dict[str, object]) -> str:
        return str(entry.get("seen_flag") or f"{entry['id']}_seen")

    def dialogue_active_companion_by_id(self, companion_id: str):
        assert self.state is not None
        for companion in self.state.companions:
            if companion.companion_id == companion_id and not companion.dead:
                return companion
        return None

    def dialogue_companion_name(self, companion_id: str) -> str:
        companion = self.dialogue_active_companion_by_id(companion_id)
        if companion is not None:
            return companion.name
        profile = COMPANION_PROFILES.get(companion_id, {})
        return str(profile.get("name", companion_id.replace("_", " ").title()))

    def dialogue_input_condition_is_available(self, entry: dict[str, object]) -> bool:
        assert self.state is not None

        if "act" in entry:
            allowed_acts = {int(act) for act in self.dialogue_input_sequence(entry.get("act"))}
            if self.state.current_act not in allowed_acts:
                return False
        if "min_act" in entry:
            try:
                if self.state.current_act < int(entry["min_act"]):
                    return False
            except (TypeError, ValueError):
                return False
        if "max_act" in entry:
            try:
                if self.state.current_act > int(entry["max_act"]):
                    return False
            except (TypeError, ValueError):
                return False

        required_flags = self.dialogue_input_sequence(entry.get("requires_flags", ()))
        if any(not self.state.flags.get(str(flag)) for flag in required_flags):
            return False

        any_flags = self.dialogue_input_sequence(entry.get("requires_any_flags", ()))
        if any_flags and not any(self.state.flags.get(str(flag)) for flag in any_flags):
            return False

        blocked_flags = self.dialogue_input_sequence(entry.get("blocked_flags", ()))
        if any(self.state.flags.get(str(flag)) for flag in blocked_flags):
            return False

        for flag, expected in dict(entry.get("requires_flag_values", {})).items():
            if self.state.flags.get(str(flag)) != expected:
                return False

        for flag, allowed_values in dict(entry.get("requires_any_flag_values", {})).items():
            values = self.dialogue_input_sequence(allowed_values)
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

        required_companions = self.dialogue_input_sequence(entry.get("requires_companions", ()))
        if any(self.dialogue_active_companion_by_id(str(companion_id)) is None for companion_id in required_companions):
            return False

        any_companions = self.dialogue_input_sequence(entry.get("requires_any_companions", ()))
        if any_companions and not any(self.dialogue_active_companion_by_id(str(companion_id)) is not None for companion_id in any_companions):
            return False

        blocked_companions = self.dialogue_input_sequence(entry.get("blocked_companions", ()))
        if any(self.dialogue_active_companion_by_id(str(companion_id)) is not None for companion_id in blocked_companions):
            return False

        for companion_id, minimum in dict(entry.get("relationship_min", {})).items():
            companion = self.dialogue_active_companion_by_id(str(companion_id))
            if companion is None or not self.relationship_threshold(companion, str(minimum)):
                return False

        return True

    def dialogue_input_entry_is_available(self, entry: dict[str, object], topic_key: str, scene_key: str | None) -> bool:
        assert self.state is not None
        topics = self.dialogue_input_sequence(entry.get("topic_keys", entry.get("triggers", ())))
        if topic_key not in {str(topic) for topic in topics}:
            return False
        scene_keys = self.dialogue_input_sequence(entry.get("scene_keys", ()))
        if scene_keys and scene_key not in {str(key) for key in scene_keys}:
            return False
        if bool(entry.get("once", True)) and self.state.flags.get(self.dialogue_input_seen_flag(entry)):
            return False
        return self.dialogue_input_condition_is_available(entry)

    def available_dialogue_inputs(self, topic_key: str, *, scene_key: str | None = None) -> list[dict[str, object]]:
        assert self.state is not None
        resolved_scene_key = scene_key if scene_key is not None else self.state.current_scene
        available = [
            entry
            for entry in DIALOGUE_INPUTS
            if self.dialogue_input_entry_is_available(entry, topic_key, resolved_scene_key)
        ]
        return sorted(available, key=lambda entry: (-int(entry.get("priority", 0)), str(entry.get("id", ""))))

    def run_dialogue_input(self, topic_key: str, *, scene_key: str | None = None, max_entries: int = 1) -> int:
        assert self.state is not None
        emitted = 0
        for entry in self.available_dialogue_inputs(topic_key, scene_key=scene_key):
            if emitted >= max_entries:
                break
            if self.emit_dialogue_input(entry):
                emitted += 1
        return emitted

    def emit_dialogue_input(self, entry: dict[str, object]) -> bool:
        assert self.state is not None
        any_line_emitted = False
        for raw_line in list(entry.get("lines", ())):
            if isinstance(raw_line, dict):
                if not self.dialogue_input_condition_is_available(raw_line):
                    continue
                speaker_id = str(raw_line.get("speaker", "")).strip()
                text = str(raw_line.get("text", "")).strip()
            elif isinstance(raw_line, (list, tuple)) and len(raw_line) >= 2:
                speaker_id = str(raw_line[0]).strip()
                text = str(raw_line[1]).strip()
            else:
                continue

            if not text:
                continue
            if speaker_id in COMPANION_PROFILES and self.dialogue_active_companion_by_id(speaker_id) is None:
                continue
            if speaker_id:
                speaker_name = self.dialogue_companion_name(speaker_id) if speaker_id in COMPANION_PROFILES else speaker_id
                self.speaker(speaker_name, text)
            else:
                self.say(text)
            any_line_emitted = True

        if not any_line_emitted:
            return False

        if bool(entry.get("once", True)):
            self.state.flags[self.dialogue_input_seen_flag(entry)] = True
        for companion_id in self.dialogue_input_sequence(entry.get("requires_companions", ())):
            companion = self.dialogue_active_companion_by_id(str(companion_id))
            if companion is None:
                continue
            seen = companion.bond_flags.setdefault("dialogue_inputs", [])
            if entry["id"] not in seen:
                seen.append(str(entry["id"]))
        self.apply_dialogue_input_effects(entry)
        return True

    def apply_dialogue_input_effects(self, entry: dict[str, object]) -> None:
        self.apply_dialogue_input_effect(entry)
        for effect in list(entry.get("effects", ())):
            if isinstance(effect, dict) and self.dialogue_input_condition_is_available(effect):
                self.apply_dialogue_input_effect(effect)

    def apply_dialogue_input_effect(self, effect: dict[str, object]) -> None:
        assert self.state is not None
        for flag in self.dialogue_input_sequence(effect.get("set_flags", ())):
            self.state.flags[str(flag)] = True
        for flag, delta in dict(effect.get("flag_increments", {})).items():
            current = self.state.flags.get(str(flag), 0)
            if isinstance(current, bool):
                current = int(current)
            try:
                updated = int(current or 0) + int(delta)
            except (TypeError, ValueError):
                updated = int(delta)
            self.state.flags[str(flag)] = updated
        for companion_id, delta in dict(effect.get("companion_deltas", {})).items():
            companion = self.dialogue_active_companion_by_id(str(companion_id))
            if companion is not None:
                self.adjust_companion_disposition(companion, int(delta), "their input mattered in the moment")
        for metric_key, delta in dict(effect.get("metric_deltas", {})).items():
            self.apply_dialogue_input_metric_delta(str(metric_key), int(delta))
        for status, duration in dict(effect.get("player_statuses", {})).items():
            self.apply_status(self.state.player, str(status), int(duration), source="companion input")
        for companion_id, lore_entry in dict(effect.get("companion_lore", {})).items():
            companion = self.dialogue_active_companion_by_id(str(companion_id))
            if companion is not None and lore_entry not in companion.lore:
                companion.lore.append(str(lore_entry))
        for clue in self.dialogue_input_sequence(effect.get("clues", ())):
            self.add_clue(str(clue))
        journal = str(effect.get("journal", "")).strip()
        if journal:
            self.add_journal(journal)

    def apply_dialogue_input_metric_delta(self, metric_key: str, delta: int) -> None:
        assert self.state is not None
        if metric_key.startswith("act2_") and callable(getattr(self, "act2_shift_metric", None)):
            self.act2_shift_metric(metric_key, delta, "companion input shaped the scene")
            return
        if metric_key.startswith("act1_") and callable(getattr(self, "act1_adjust_metric", None)):
            self.act1_adjust_metric(metric_key, delta)
            return
        current = self.state.flags.get(metric_key, 0)
        try:
            self.state.flags[metric_key] = int(current or 0) + delta
        except (TypeError, ValueError):
            self.state.flags[metric_key] = delta
