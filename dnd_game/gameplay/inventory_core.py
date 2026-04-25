from __future__ import annotations

from ..dice import roll
from ..items import (
    canonicalize_item_mapping,
    choose_supply_items_to_consume,
    format_inventory_line,
    get_item,
    inventory_supply_points,
    inventory_weight,
    item_rules_text,
    item_type_label,
    marks_label,
    party_carry_capacity,
    roll_loot_for_enemy,
)
from .magic_points import (
    restore_all_magic_points,
    restore_half_magic_points,
    restore_magic_points,
    spell_slot_restore_units_to_mp,
)
from .spell_slots import restore_all_spell_slots, restore_spell_slots
from ..ui.colors import rarity_color, rich_style_name
from ..ui.rich_render import Panel, RICH_AVAILABLE, Table, Text, box


class InventoryCoreMixin:
    INVENTORY_FILTER_DEFINITIONS = (
        ("all", "All Items"),
        ("consumables", "Consumables"),
        ("scrolls", "Scripts"),
        ("supplies", "Supplies"),
        ("weapons", "Weapons"),
        ("armor", "Armor and Shields"),
        ("accessories", "Accessories"),
        ("other", "Other Gear"),
    )

    def inventory_dict(self) -> dict[str, int]:
        assert self.state is not None
        self.state.inventory = canonicalize_item_mapping(self.state.inventory)
        return self.state.inventory

    def carrying_capacity(self) -> int:
        assert self.state is not None
        return party_carry_capacity(self.state.party_members())

    def current_inventory_weight(self) -> float:
        return inventory_weight(self.inventory_dict())

    def current_supply_points(self) -> int:
        return inventory_supply_points(self.inventory_dict())

    def inventory_filter_label(self, filter_key: str) -> str:
        for key, label in self.INVENTORY_FILTER_DEFINITIONS:
            if key == filter_key:
                return label
        return "All Items"

    def inventory_filter_options(self) -> list[tuple[str, str]]:
        return list(self.INVENTORY_FILTER_DEFINITIONS)

    def item_matches_inventory_filter(self, item, filter_key: str) -> bool:
        if filter_key == "all":
            return True
        if filter_key == "consumables":
            return item.category == "consumable"
        if filter_key == "scrolls":
            return item.category == "scroll"
        if filter_key == "supplies":
            return item.category == "supply"
        if filter_key == "weapons":
            return item.weapon is not None
        if filter_key == "armor":
            return item.armor is not None or item.item_type == "shield"
        if filter_key == "accessories":
            return item.is_equippable() and item.weapon is None and item.armor is None and item.item_type != "shield"
        if filter_key == "other":
            return not (
                item.category in {"consumable", "scroll", "supply"}
                or item.weapon is not None
                or item.armor is not None
                or item.item_type == "shield"
                or (item.is_equippable() and item.weapon is None and item.armor is None and item.item_type != "shield")
            )
        return True

    def inventory_item_ids_for_filter(self, filter_key: str) -> list[str]:
        item_ids = [
            item_id
            for item_id in self.inventory_dict()
            if self.item_matches_inventory_filter(get_item(item_id), filter_key)
        ]
        item_ids.sort(key=lambda key: get_item(key).name)
        return item_ids

    def inventory_item_kind_label(self, item) -> str:
        if item.weapon is not None:
            return "Weapon"
        if item.armor is not None:
            return "Armor"
        if item.item_type == "shield":
            return "Shield"
        if item.category == "consumable":
            return "Consumable"
        if item.category == "scroll":
            return "Script"
        if item.category == "supply":
            return "Supply"
        return item_type_label(item.item_type).title()

    def inventory_item_rules_summary(self, item) -> str:
        return item_rules_text(item) or item.description

    def inventory_rich_item_name(self, item):
        label = item.name
        color = rarity_color(item.rarity)
        if not (RICH_AVAILABLE and Text is not None):
            return label
        return Text(label, style=f"bold {rich_style_name(color)}")

    def inventory_rich_rarity(self, item):
        color = rarity_color(item.rarity)
        if not (RICH_AVAILABLE and Text is not None):
            return item.rarity_title
        return Text(item.rarity_title, style=f"bold {rich_style_name(color)}")

    def render_inventory_table(
        self,
        *,
        title: str,
        item_ids: list[str],
        quantity_lookup: dict[str, int],
        show_free_count: bool = True,
    ) -> bool:
        if not (self.rich_enabled() and Table is not None and Panel is not None and box is not None):
            return False
        table = Table(box=box.SIMPLE_HEAVY, expand=True, show_lines=False)
        table.add_column("Item", ratio=2, overflow="fold")
        table.add_column("Rarity", no_wrap=True)
        table.add_column("Qty", justify="right", no_wrap=True)
        if show_free_count:
            table.add_column("Free", justify="right", no_wrap=True)
        table.add_column("Wt", justify="right", no_wrap=True)
        table.add_column("Value", justify="right", no_wrap=True)
        table.add_column("Rules", ratio=4, overflow="fold")
        for item_id in item_ids:
            item = get_item(item_id)
            quantity = quantity_lookup[item_id]
            row = [
                self.inventory_rich_item_name(item),
                self.inventory_rich_rarity(item),
                str(quantity),
            ]
            if show_free_count:
                row.append(str(self.available_inventory_count(item_id)))
            row.extend(
                [
                    f"{item.weight * quantity:.1f} lb",
                    marks_label(item.value),
                    self.inventory_item_rules_summary(item),
                ]
            )
            table.add_row(*row)
        return self.emit_rich(
            Panel(
                table,
                title=self.rich_text(title, "light_yellow", bold=True),
                border_style=rich_style_name("light_yellow"),
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )

    def add_inventory_item(self, item_id: str, quantity: int = 1, *, source: str = "") -> int:
        if quantity <= 0:
            return 0
        item = get_item(item_id)
        added = 0
        while added < quantity and self.current_inventory_weight() + item.weight <= self.carrying_capacity():
            self.inventory_dict()[item_id] = self.inventory_dict().get(item_id, 0) + 1
            added += 1
        if added and source:
            self.say(f"You add {item.name} x{added} from {source}.")
        if added < quantity:
            self.say(f"You leave {item.name} behind because the party is at carrying capacity.")
        return added

    def remove_inventory_item(self, item_id: str, quantity: int = 1) -> bool:
        current = self.inventory_dict().get(item_id, 0)
        if current < quantity:
            return False
        remaining = current - quantity
        if remaining > 0:
            self.inventory_dict()[item_id] = remaining
        else:
            self.inventory_dict().pop(item_id, None)
        return True

    def count_equipped(self, item_id: str) -> int:
        assert self.state is not None
        target_id = get_item(item_id).item_id
        count = 0
        for member in [self.state.player, *self.state.all_companions()]:
            for equipped_item_id in member.equipment_slots.values():
                if equipped_item_id is None:
                    continue
                try:
                    equipped_id = get_item(equipped_item_id).item_id
                except KeyError:
                    continue
                if equipped_id == target_id:
                    count += 1
        return count

    def available_inventory_count(self, item_id: str) -> int:
        return max(0, self.inventory_dict().get(item_id, 0) - self.count_equipped(item_id))

    def collect_loot(self, enemies, *, source: str) -> None:
        loot_totals: dict[str, int] = {}
        for enemy in enemies:
            for item_id, quantity in roll_loot_for_enemy(enemy, self.rng).items():
                loot_totals[item_id] = loot_totals.get(item_id, 0) + quantity
        if not loot_totals:
            return
        self.banner("Loot")
        for item_id, quantity in sorted(loot_totals.items()):
            added = self.add_inventory_item(item_id, quantity, source=source)
            if added:
                self.add_journal(f"Looted {get_item(item_id).name} x{added} from {source}.")
                self.pause_for_loot_reveal()

    def restore_short_rest_resources(self, member) -> None:
        if "second_wind" in member.max_resources:
            member.resources["second_wind"] = member.max_resources["second_wind"]
        if "action_surge" in member.max_resources:
            member.resources["action_surge"] = member.max_resources["action_surge"]
        if "channel_divinity" in member.max_resources:
            member.resources["channel_divinity"] = member.max_resources["channel_divinity"]
        if "ki" in member.max_resources:
            member.resources["ki"] = member.max_resources["ki"]
        if member.class_name == "Warlock":
            restore_all_spell_slots(member)
            restore_all_magic_points(member)
        else:
            restore_half_magic_points(member)
        if member.spellcasting_ability is not None and ("arcane_recovery" in member.features or "natural_recovery" in member.features):
            restore_spell_slots(member, 1)

    def short_rest(self) -> None:
        assert self.state is not None
        if self.state.short_rests_remaining <= 0:
            self.say("You have already used your two free short rests since the last long rest.")
            return
        self.state.short_rests_remaining -= 1
        for member in self.state.party_members():
            if member.dead:
                continue
            if member.current_hp == 0:
                member.current_hp = 1
                member.stable = False
                member.death_successes = 0
                member.death_failures = 0
            heal_amount = max(1, (member.max_hp + 1) // 2)
            member.heal(heal_amount)
            self.restore_short_rest_resources(member)
        self.say(
            f"The party takes a short rest, spends bandages and breath, and steadies up. "
            f"Short rests remaining before a long rest: {self.state.short_rests_remaining}."
        )

    def complete_long_rest_recovery(self) -> None:
        assert self.state is not None
        for member in [self.state.player, *self.state.all_companions()]:
            if member.dead:
                member.temp_hp = 0
                continue
            persistent_conditions = {
                name: duration
                for name, duration in member.conditions.items()
                if duration < 0 or not bool(self.status_definition(name).get("combat_only", True))
            }
            member.reset_for_rest()
            member.conditions.update(persistent_conditions)
            if member.conditions.get("exhaustion", 0) > 0:
                member.conditions["exhaustion"] -= 1
                if member.conditions["exhaustion"] <= 0:
                    member.conditions.pop("exhaustion", None)
        clear_liars_curse_after_long_rest = getattr(self, "clear_liars_curse_after_long_rest", None)
        if callable(clear_liars_curse_after_long_rest):
            clear_liars_curse_after_long_rest()
        self.state.short_rests_remaining = 2

    def long_rest(self) -> None:
        assert self.state is not None
        required_points = 12
        consumed, missing = choose_supply_items_to_consume(self.inventory_dict(), required_points)
        if missing > 0:
            self.say(
                f"You need {required_points} supply points to long rest, but the party only has "
                f"{required_points - missing} available."
            )
            return
        for item_id, quantity in consumed.items():
            self.remove_inventory_item(item_id, quantity)
        self.complete_long_rest_recovery()
        consumed_text = ", ".join(f"{get_item(item_id).name} x{quantity}" for item_id, quantity in consumed.items())
        self.say(f"The party completes a long rest after using {consumed_text}.")

    def paid_inn_long_rest_cost(self) -> int:
        assert self.state is not None
        return 10 * max(1, len(self.state.party_members()))

    def paid_inn_long_rest(self, inn_name: str) -> bool:
        assert self.state is not None
        party_members = self.state.party_members()
        party_size = max(1, len(party_members))
        cost = self.paid_inn_long_rest_cost()
        member_text = "member" if party_size == 1 else "members"
        if self.state.gold < cost:
            self.say(
                f"A long rest at {inn_name} costs {marks_label(cost)} for {party_size} active party {member_text}, "
                f"but the party only has {marks_label(self.state.gold)}."
            )
            return False
        resting_members = [member for member in party_members if not member.dead]
        resting_names = ", ".join(member.name for member in resting_members) if resting_members else "no living active party members"
        dead_members = [member.name for member in party_members if member.dead]
        self.say(f"A long rest at {inn_name} will cost {marks_label(cost)} total for {party_size} active party {member_text}.")
        self.say(f"Will long rest: {resting_names}.")
        if dead_members:
            self.say(f"Will not be restored by resting: {', '.join(dead_members)} (dead).")
        if not self.confirm(f"Spend {marks_label(cost)} at {inn_name} and long rest this company?"):
            self.say("You keep your gold and do not rent beds.")
            return False
        self.state.gold -= cost
        self.complete_long_rest_recovery()
        self.say(f"The party pays {marks_label(cost)} for beds at {inn_name} and completes a long rest without using camp supplies.")
        self.add_journal(f"Paid {marks_label(cost)} for a long rest at {inn_name}.")
        return True

    def show_inventory(self, *, filter_key: str = "all") -> None:
        assert self.state is not None
        self.banner("Inventory")
        self.say(
            f"View: {self.inventory_filter_label(filter_key)} | "
            f"Weight: {self.current_inventory_weight():.1f}/{self.carrying_capacity()} lb | "
            f"Supply points: {self.current_supply_points()} | Gold: {self.state.gold}"
        )
        if not self.state.inventory:
            self.say("The shared inventory is empty.")
            return
        item_ids = self.inventory_item_ids_for_filter(filter_key)
        if not item_ids:
            self.say(f"No items match the {self.inventory_filter_label(filter_key).lower()} filter right now.")
            return
        preview_items = ", ".join(f"{get_item(item_id).name} x{self.state.inventory[item_id]}" for item_id in item_ids[:4])
        if len(item_ids) > 4:
            preview_items += ", ..."
        if self.rich_enabled():
            self.say(f"On hand: {preview_items}")
        rendered = self.render_inventory_table(
            title="Shared Inventory",
            item_ids=item_ids,
            quantity_lookup={item_id: self.state.inventory[item_id] for item_id in item_ids},
        )
        if rendered:
            return
        for item_id in item_ids:
            available = self.available_inventory_count(item_id)
            equipped = self.count_equipped(item_id)
            suffix = f" | {available} free"
            if equipped:
                suffix += f", {equipped} equipped"
            self.output_fn(f"- {format_inventory_line(item_id, self.state.inventory[item_id])}{suffix}")

    def drink_healing_potion_in_combat(self, actor) -> bool:
        potion = get_item("potion_healing")
        if not self.remove_inventory_item("potion_healing"):
            self.say(f"There is no {potion.name} left in the shared inventory.")
            return False
        healed = actor.heal(
            self.roll_with_animation_context(
                potion.heal_dice,
                style="healing",
                context_label=f"{actor.name} drinks {potion.name}",
                outcome_kind="healing",
            ).total
            + potion.heal_bonus
            + actor.gear_bonuses.get("healing_received", 0)
        )
        play_heal_sound_for = getattr(self, "play_heal_sound_for", None)
        if healed > 0 and callable(play_heal_sound_for):
            play_heal_sound_for(actor)
        self.say(f"{self.style_name(actor)} downs {potion.name} and restores {self.style_healing(healed)} hit points.")
        return True

    def use_item_from_inventory(
        self,
        *,
        combat: bool = False,
        actor=None,
        heroes=None,
        allow_self_healing_potion: bool = True,
    ) -> bool:
        assert self.state is not None
        item_ids = [
            item_id
            for item_id, quantity in self.inventory_dict().items()
            if quantity > 0 and get_item(item_id).is_combat_usable()
        ]
        if not item_ids:
            self.say("You do not have a usable consumable or script ready.")
            return False
        item_ids.sort(key=lambda item_id: (get_item(item_id).rarity, get_item(item_id).name))
        choice = self.choose(
            "Choose an item to use.",
            [format_inventory_line(item_id, self.inventory_dict()[item_id]) for item_id in item_ids] + ["Back"],
            allow_meta=False,
            show_hud=not combat,
        )
        if choice == len(item_ids) + 1:
            return False
        item = get_item(item_ids[choice - 1])
        target_pool = heroes if heroes is not None else self.state.party_members()
        valid_targets = [
            member
            for member in target_pool
            if not member.dead and (allow_self_healing_potion or item.legacy_id != "potion_healing" or actor is None or member is not actor)
        ]
        if not valid_targets:
            if combat and actor is not None and item.legacy_id == "potion_healing":
                self.say(f"Drinking {item.name} yourself is a bonus action here. Use the bonus-action option instead.")
            else:
                self.say(f"There is no valid target for {item.name} right now.")
            return False
        target = valid_targets[0]
        if len(valid_targets) > 1:
            target = self.choose_ally(valid_targets, prompt=f"Choose who receives {item.name}.", allow_back=combat)
            if target is None:
                return False
        if not self.remove_inventory_item(item.item_id):
            self.say(f"{item.name} is no longer in the shared inventory.")
            return False

        effects: list[str] = []
        triggered_healing = False
        if item.heal_dice is not None:
            heal_amount = (
                self.roll_with_animation_context(
                    item.heal_dice,
                    style="healing",
                    context_label=f"{item.name} for {target.name}",
                    outcome_kind="healing",
                ).total
                + item.heal_bonus
                + target.gear_bonuses.get("healing_received", 0)
            )
            healed = target.heal(heal_amount)
            effects.append(f"restores {healed} hit points")
            triggered_healing = triggered_healing or healed > 0
        if item.revive_hp and target.current_hp == 0 and not target.dead:
            target.current_hp = max(target.current_hp, item.revive_hp)
            target.stable = False
            target.death_successes = 0
            target.death_failures = 0
            effects.append(f"brings {target.name} back to {target.current_hp} HP")
            triggered_healing = True
        if item.temp_hp:
            gained = target.grant_temp_hp(item.temp_hp)
            effects.append(f"sets temporary hit points to {gained}")
        if item.spell_slot_restore and target.spellcasting_ability is not None:
            restored_mp = restore_magic_points(target, spell_slot_restore_units_to_mp(item.spell_slot_restore))
            if restored_mp:
                effects.append(f"restores {restored_mp} MP")
        if item.cure_poison and "poisoned" in target.conditions:
            target.conditions.pop("poisoned", None)
            effects.append("cures poison")
        if item.clear_conditions:
            cleared: list[str] = []
            for condition in item.clear_conditions:
                if condition == "exhaustion":
                    current = max(0, int(target.conditions.get("exhaustion", 0)))
                    if current > 0:
                        target.conditions["exhaustion"] = current - 1
                        if target.conditions["exhaustion"] <= 0:
                            target.conditions.pop("exhaustion", None)
                        cleared.append("Exhaustion")
                    continue
                if condition in target.conditions or (condition == "unconscious" and target.current_hp == 0):
                    self.clear_status(target, condition)
                    cleared.append(self.status_name(condition))
            if cleared:
                effects.append("clears " + ", ".join(cleared))
        if item.apply_conditions:
            applied: list[str] = []
            for condition, duration in item.apply_conditions.items():
                self.apply_status(target, condition, int(duration), source=item.name)
                applied.append(self.status_name(condition))
            if applied:
                effects.append("applies " + ", ".join(applied))
        if not effects:
            effects.append("has no immediate effect")
        play_heal_sound_for = getattr(self, "play_heal_sound_for", None)
        if triggered_healing and callable(play_heal_sound_for):
            play_heal_sound_for(actor if combat and actor is not None else target)
        user_name = self.style_name(actor) if combat and actor is not None else "The party"
        self.say(f"{user_name} uses {item.name} on {self.style_name(target)}; it " + ", ".join(effects) + ".")
        return True
