from __future__ import annotations

from ..dice import roll
from ..items import (
    choose_supply_items_to_consume,
    format_inventory_line,
    get_item,
    inventory_supply_points,
    roll_loot_for_enemy,
)


class InventoryCoreMixin:
    def inventory_dict(self) -> dict[str, int]:
        assert self.state is not None
        return self.state.inventory

    def current_supply_points(self) -> int:
        return inventory_supply_points(self.inventory_dict())

    def add_inventory_item(self, item_id: str, quantity: int = 1, *, source: str = "") -> int:
        if quantity <= 0:
            return 0
        item = get_item(item_id)
        self.inventory_dict()[item_id] = self.inventory_dict().get(item_id, 0) + quantity
        if source:
            self.say(f"You add {item.name} x{quantity} from {source}.")
        return quantity

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
        return sum(
            1
            for member in [self.state.player, *self.state.all_companions()]
            for equipped_item_id in member.equipment_slots.values()
            if equipped_item_id == item_id
        )

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
        if member.spellcasting_ability is not None and ("arcane_recovery" in member.features or "natural_recovery" in member.features):
            max_slots = member.max_resources.get("spell_slots", 0)
            current_slots = member.resources.get("spell_slots", 0)
            if max_slots > current_slots:
                member.resources["spell_slots"] = min(max_slots, current_slots + 1)

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
            heal_amount = max(1, roll(f"1d{member.hit_die}", self.rng).total + member.ability_mod("CON"))
            member.heal(heal_amount)
            self.restore_short_rest_resources(member)
        self.say(
            f"The party takes a short rest, spends bandages and breath, and steadies up. "
            f"Short rests remaining before a long rest: {self.state.short_rests_remaining}."
        )

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
        self.state.short_rests_remaining = 2
        consumed_text = ", ".join(f"{get_item(item_id).name} x{quantity}" for item_id, quantity in consumed.items())
        self.say(f"The party completes a long rest after using {consumed_text}.")

    def show_inventory(self) -> None:
        assert self.state is not None
        self.banner("Inventory")
        self.say(
            f"Supply points: {self.current_supply_points()} | Gold: {self.state.gold} gp"
        )
        if not self.state.inventory:
            self.say("The shared inventory is empty.")
            return
        for item_id in sorted(self.state.inventory, key=lambda key: get_item(key).name):
            available = self.available_inventory_count(item_id)
            equipped = self.count_equipped(item_id)
            suffix = f" | {available} free"
            if equipped:
                suffix += f", {equipped} equipped"
            self.output_fn(f"- {format_inventory_line(item_id, self.state.inventory[item_id])}{suffix}")

    def drink_healing_potion_in_combat(self, actor) -> bool:
        potion = get_item("potion_healing")
        if not self.remove_inventory_item("potion_healing"):
            self.say("There is no Potion of Healing left in the shared inventory.")
            return False
        healed = actor.heal(roll(potion.heal_dice, self.rng).total + potion.heal_bonus + actor.gear_bonuses.get("healing_received", 0))
        self.say(f"{self.style_name(actor)} downs a Potion of Healing and restores {self.style_healing(healed)} hit points.")
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
            self.say("You do not have a usable consumable or scroll ready.")
            return False
        item_ids.sort(key=lambda item_id: (get_item(item_id).rarity, get_item(item_id).name))
        choice = self.choose(
            "Choose an item to use.",
            [format_inventory_line(item_id, self.inventory_dict()[item_id]) for item_id in item_ids] + ["Back"],
            allow_meta=False,
        )
        if choice == len(item_ids) + 1:
            return False
        item = get_item(item_ids[choice - 1])
        target_pool = heroes if heroes is not None else self.state.party_members()
        valid_targets = [
            member
            for member in target_pool
            if not member.dead and (allow_self_healing_potion or item.item_id != "potion_healing" or actor is None or member is not actor)
        ]
        if not valid_targets:
            if combat and actor is not None and item.item_id == "potion_healing":
                self.say("Drinking a Potion of Healing yourself is a bonus action here. Use the bonus-action option instead.")
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
        if item.heal_dice is not None:
            heal_amount = roll(item.heal_dice, self.rng).total + item.heal_bonus + target.gear_bonuses.get("healing_received", 0)
            healed = target.heal(heal_amount)
            effects.append(f"restores {healed} hit points")
        if item.revive_hp and target.current_hp == 0 and not target.dead:
            target.current_hp = max(target.current_hp, item.revive_hp)
            target.stable = False
            target.death_successes = 0
            target.death_failures = 0
            effects.append(f"brings {target.name} back to {target.current_hp} HP")
        if item.temp_hp:
            gained = target.grant_temp_hp(item.temp_hp)
            effects.append(f"sets temporary hit points to {gained}")
        if item.spell_slot_restore and target.spellcasting_ability is not None:
            max_slots = target.max_resources.get("spell_slots", 0)
            if max_slots:
                previous = target.resources.get("spell_slots", 0)
                target.resources["spell_slots"] = min(max_slots, previous + item.spell_slot_restore)
                restored = target.resources["spell_slots"] - previous
                effects.append(f"restores {restored} spell slot{'s' if restored != 1 else ''}")
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
        user_name = self.style_name(actor) if combat and actor is not None else "The party"
        self.say(f"{user_name} uses {item.name} on {self.style_name(target)}; it " + ", ".join(effects) + ".")
        return True
