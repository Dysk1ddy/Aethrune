from __future__ import annotations

from ..models import ABILITY_ORDER, Character, SKILL_TO_ABILITY
from ..items import canonical_equipment_slot, equipment_slot_label, format_inventory_line, get_item, marks_label
from ..ui.colors import rich_style_name
from ..ui.rich_render import Columns, Group, Panel, Table, box


class InventoryManagementMixin:
    def render_trade_catalog(
        self,
        *,
        merchant_id: str,
        merchant_name: str,
        title: str,
        item_ids: list[str],
        quantity_lookup: dict[str, int],
        quantity_label: str,
        price_label: str,
        price_lookup: dict[str, int],
    ) -> bool:
        assert self.state is not None
        if not (self.rich_enabled() and Table is not None and Panel is not None and Columns is not None and Group is not None and box is not None):
            return False
        table = Table(box=box.SIMPLE_HEAVY, expand=True, show_lines=False)
        table.add_column("Item", ratio=2, overflow="fold")
        table.add_column("Rarity", no_wrap=True)
        table.add_column(quantity_label, justify="right", no_wrap=True)
        table.add_column(price_label, justify="right", no_wrap=True)
        table.add_column("Rules", ratio=4, overflow="fold")
        for item_id in item_ids:
            item = get_item(item_id)
            quantity = quantity_lookup[item_id]
            table.add_row(
                self.inventory_rich_item_name(item),
                self.inventory_rich_rarity(item),
                str(quantity),
                marks_label(price_lookup[item_id]),
                self.inventory_item_rules_summary(item),
            )
        negotiator = self.trade_negotiator()
        carry_room = max(0.0, self.carrying_capacity() - self.current_inventory_weight())
        sidebar = Panel(
            Group(
                self.rich_text(merchant_name, "light_aqua", bold=True),
                self.rich_text(f"Party gold: {self.state.gold}", "light_yellow"),
                self.rich_text(f"Carry room: {carry_room:.1f} lb", "white"),
                self.rich_text(
                    f"Negotiator: {negotiator.name} (Persuasion +{negotiator.skill_bonus('Persuasion')})",
                    "white",
                ),
                self.rich_text(f"Attitude: {self.get_merchant_attitude(merchant_id)}/100", "white"),
                self.rich_text(
                    f"Buy x{self.buy_price_multiplier(merchant_id):.2f} | Sell x{self.sell_price_multiplier(merchant_id):.2f}",
                    "white",
                ),
            ),
            title=self.rich_text("Trade Desk", "light_yellow", bold=True),
            border_style=rich_style_name("light_yellow"),
            box=box.ROUNDED,
            padding=(0, 1),
        )
        catalog = Panel(
            table,
            title=self.rich_text(title, "light_yellow", bold=True),
            border_style=rich_style_name("light_yellow"),
            box=box.ROUNDED,
            padding=(0, 1),
        )
        return self.emit_rich(Columns([catalog, sidebar], expand=True, equal=False), width=max(108, self.rich_console_width()))

    def choose_inventory_filter(self, *, allow_back: bool = True) -> str | None:
        filter_options = self.inventory_filter_options()
        options = [label for _, label in filter_options]
        if allow_back:
            options.append("Back")
        choice = self.choose("Choose which inventory category to review.", options, allow_meta=False)
        if allow_back and choice == len(filter_options) + 1:
            return None
        return filter_options[choice - 1][0]

    def review_inventory_by_filter(self) -> None:
        filter_key = self.choose_inventory_filter(allow_back=True)
        if filter_key is None:
            return
        self.show_inventory(filter_key=filter_key)

    def manage_inventory(self, *, merchant_id: str | None = None, merchant_name: str | None = None) -> None:
        assert self.state is not None
        while True:
            if merchant_id is not None and merchant_name is not None:
                self.say(self.merchant_trade_summary(merchant_id, merchant_name))
            options = ["View inventory", "View inventory by category"]
            if merchant_id is not None and merchant_name is not None:
                options.extend(
                    [
                        self.skill_tag("TRADE", f"Browse {merchant_name}'s wares"),
                        self.skill_tag("TRADE", f"Buy items from {merchant_name}"),
                    ]
                )
            options.extend(["Use a consumable or script", "Manage equipment", "Drop items"])
            if merchant_id is not None and merchant_name is not None:
                options.append(self.skill_tag("TRADE", f"Sell items to {merchant_name}"))
            options.append("Back")
            choice = self.choose(
                "Manage the party's shared inventory."
                if merchant_name is None
                else f"Manage the party's shared inventory while dealing with {merchant_name}.",
                options,
                allow_meta=False,
            )
            if choice == 1:
                self.show_inventory()
            elif choice == 2:
                self.review_inventory_by_filter()
            elif merchant_id is not None and merchant_name is not None and choice == 3:
                self.show_merchant_stock(merchant_id, merchant_name)
            elif merchant_id is not None and merchant_name is not None and choice == 4:
                self.buy_items(merchant_id, merchant_name)
            elif choice == (5 if merchant_id is not None and merchant_name is not None else 3):
                self.use_item_from_inventory()
            elif choice == (6 if merchant_id is not None and merchant_name is not None else 4):
                self.manage_equipment()
            elif choice == (7 if merchant_id is not None and merchant_name is not None else 5):
                self.drop_items()
            elif merchant_id is not None and merchant_name is not None and choice == 8:
                self.sell_items(merchant_id=merchant_id, merchant_name=merchant_name)
            else:
                return

    def show_merchant_stock(self, merchant_id: str, merchant_name: str) -> None:
        stock = self.get_merchant_stock(merchant_id)
        self.banner(f"{merchant_name}'s Wares")
        self.say(self.merchant_trade_summary(merchant_id, merchant_name))
        if not stock:
            self.say(f"{merchant_name} has nothing left on the shelf right now.")
            return
        item_ids = sorted(stock, key=lambda key: get_item(key).name)
        rendered = self.render_trade_catalog(
            merchant_id=merchant_id,
            merchant_name=merchant_name,
            title=f"{merchant_name}'s Wares",
            item_ids=item_ids,
            quantity_lookup={item_id: stock[item_id] for item_id in item_ids},
            quantity_label="Stock",
            price_label="Buy",
            price_lookup={item_id: self.merchant_buy_price(merchant_id, item_id) for item_id in item_ids},
        )
        if rendered:
            return
        for item_id in item_ids:
            self.output_fn(f"- {format_inventory_line(item_id, stock[item_id])} | buy {marks_label(self.merchant_buy_price(merchant_id, item_id))} each")

    def ask_quantity_or_back(self, prompt: str, maximum: int) -> int | None:
        while True:
            self.output_fn("")
            raw = self.read_input(f"{prompt} (1-{maximum}, or 'back'): ").strip().lower()
            if self.handle_meta_command(raw):
                continue
            if raw == "back":
                return None
            if raw.isdigit():
                value = int(raw)
                if 1 <= value <= maximum:
                    return value
            self.say("Enter a valid quantity or type 'back'.")

    def buy_items(self, merchant_id: str, merchant_name: str) -> None:
        assert self.state is not None
        stock = self.get_merchant_stock(merchant_id)
        item_ids = [item_id for item_id, quantity in stock.items() if quantity > 0]
        if not item_ids:
            self.say(f"{merchant_name} has nothing left to sell.")
            return
        item_ids.sort(key=lambda item_id: get_item(item_id).name)
        while True:
            self.say(self.merchant_trade_summary(merchant_id, merchant_name))
            self.render_trade_catalog(
                merchant_id=merchant_id,
                merchant_name=merchant_name,
                title=f"Buy from {merchant_name}",
                item_ids=item_ids,
                quantity_lookup={item_id: stock[item_id] for item_id in item_ids},
                quantity_label="Stock",
                price_label="Buy",
                price_lookup={item_id: self.merchant_buy_price(merchant_id, item_id) for item_id in item_ids},
            )
            choice = self.choose(
                f"Choose an item to buy from {merchant_name}.",
                [
                    f"{get_item(item_id).name} x{stock[item_id]} | buy {marks_label(self.merchant_buy_price(merchant_id, item_id))} each"
                    for item_id in item_ids
                ]
                + ["Back"],
                allow_meta=False,
                sticky_trailing_options=1,
            )
            if choice == len(item_ids) + 1:
                return
            item_id = item_ids[choice - 1]
            item = get_item(item_id)
            available = stock.get(item_id, 0)
            unit_price = self.merchant_buy_price(merchant_id, item_id)
            if available <= 0:
                self.say(f"{merchant_name} has run out of {item.name}.")
                return
            affordable = self.state.gold // max(1, unit_price)
            if item.weight > 0:
                capacity_left = max(0.0, self.carrying_capacity() - self.current_inventory_weight())
                carry_limit = int(capacity_left // item.weight)
            else:
                carry_limit = available
            maximum = min(available, affordable, carry_limit)
            if maximum <= 0:
                if affordable <= 0:
                    self.say(f"You cannot afford {item.name} right now.")
                else:
                    self.say(f"The party cannot carry any more {item.name} right now.")
                return
            quantity = maximum if maximum == 1 else self.ask_quantity_or_back(f"How many {item.name} do you want to buy?", maximum)
            if quantity is None:
                continue
            stock[item_id] -= quantity
            if stock[item_id] <= 0:
                stock.pop(item_id, None)
            total_price = unit_price * quantity
            self.state.gold -= total_price
            self.add_inventory_item(item_id, quantity=quantity, source=merchant_name)
            play_sound_effect = getattr(self, "play_sound_effect", None)
            if callable(play_sound_effect):
                play_sound_effect("buy_item")
            self.say(f"You buy {item.name} x{quantity} from {merchant_name} for {marks_label(total_price)}.")
            return

    def manage_equipment(self) -> None:
        assert self.state is not None
        while True:
            member = self.choose_company_member("Choose whose equipment you want to manage.", allow_back=True)
            if member is None:
                return
            while True:
                choice = self.choose(
                    f"Manage equipment for {member.name}.",
                    [self.equipment_slot_summary(member, slot) for slot in member.equipment_slots] + ["Back"],
                    allow_meta=False,
                )
                if choice == len(member.equipment_slots) + 1:
                    break
                slot = list(member.equipment_slots)[choice - 1]
                self.manage_equipment_slot(member, slot)

    def equipment_slot_summary(self, member, slot: str) -> str:
        item_id = member.equipment_slots.get(slot)
        item_text = get_item(item_id).name if item_id is not None else "Empty"
        return f"{equipment_slot_label(slot)}: {item_text}"

    def copy_member_for_preview(self, member: Character) -> Character:
        return Character.from_dict(member.to_dict())

    def preview_member_after_slot_change(self, member: Character, slot: str, item_id: str | None) -> Character:
        preview = self.copy_member_for_preview(member)
        preview.equipment_slots = dict(preview.equipment_slots)
        preview.equipment_slots[slot] = item_id
        self.sync_equipment(preview)
        return preview

    def format_delta(self, label: str, delta: int) -> str:
        color = "light_green" if delta > 0 else "light_red"
        return f"{label} {self.style_text(f'{delta:+d}', color)}"

    def equipment_comparison_summary(self, before: Character, after: Character) -> str:
        parts: list[str] = []
        core_stats = [
            ("Defense", after.armor_class - before.armor_class),
            ("strike", after.attack_bonus() - before.attack_bonus()),
            ("damage", after.damage_bonus() - before.damage_bonus()),
            ("initiative", self.initiative_bonus(after) - self.initiative_bonus(before)),
        ]
        for label, delta in core_stats:
            if delta:
                parts.append(self.format_delta(label, delta))
        if before.weapon.name != after.weapon.name:
            parts.append(f"weapon: {before.weapon.name} -> {after.weapon.name}")
        before_spell_ability = before.spellcasting_ability
        after_spell_ability = after.spellcasting_ability
        if before_spell_ability or after_spell_ability:
            before_spell_attack = self.spell_attack_bonus(before, before_spell_ability or after_spell_ability or "INT")
            after_spell_attack = self.spell_attack_bonus(after, after_spell_ability or before_spell_ability or "INT")
            spell_attack_delta = after_spell_attack - before_spell_attack
            if spell_attack_delta:
                parts.append(self.format_delta("channeling strike", spell_attack_delta))
            spell_damage_delta = self.spell_damage_bonus(after) - self.spell_damage_bonus(before)
            if spell_damage_delta:
                parts.append(self.format_delta("channeling damage", spell_damage_delta))
            healing_delta = self.healing_bonus(after) - self.healing_bonus(before)
            if healing_delta:
                parts.append(self.format_delta("healing", healing_delta))
        skill_deltas = [
            self.format_delta(skill, after.skill_bonus(skill) - before.skill_bonus(skill))
            for skill in sorted(SKILL_TO_ABILITY)
            if after.skill_bonus(skill) != before.skill_bonus(skill)
        ]
        if skill_deltas:
            parts.append("skills: " + ", ".join(skill_deltas))
        save_deltas = [
            self.format_delta(ability, after.save_bonus(ability) - before.save_bonus(ability))
            for ability in ABILITY_ORDER
            if after.save_bonus(ability) != before.save_bonus(ability)
        ]
        if save_deltas:
            parts.append("resist checks: " + ", ".join(save_deltas))
        before_resistances = {
            key.replace("resist_", "")
            for key, value in before.gear_bonuses.items()
            if key.startswith("resist_") and value
        }
        after_resistances = {
            key.replace("resist_", "")
            for key, value in after.gear_bonuses.items()
            if key.startswith("resist_") and value
        }
        gained_resistances = sorted(after_resistances - before_resistances)
        lost_resistances = sorted(before_resistances - after_resistances)
        if gained_resistances:
            parts.append("gains resist " + ", ".join(gained_resistances))
        if lost_resistances:
            parts.append("loses resist " + ", ".join(lost_resistances))
        if not before.gear_bonuses.get("stealth_advantage", 0) and after.gear_bonuses.get("stealth_advantage", 0):
            parts.append("gains edge on Stealth")
        elif before.gear_bonuses.get("stealth_advantage", 0) and not after.gear_bonuses.get("stealth_advantage", 0):
            parts.append("loses edge on Stealth")
        if not before.gear_bonuses.get("crit_immunity", 0) and after.gear_bonuses.get("crit_immunity", 0):
            parts.append("critical hits become normal hits")
        elif before.gear_bonuses.get("crit_immunity", 0) and not after.gear_bonuses.get("crit_immunity", 0):
            parts.append("loses critical-hit protection")
        if before.shield != after.shield:
            parts.append("shield ready" if after.shield else "shield removed")
        return "; ".join(parts) if parts else "No major stat change."

    def show_equipment_comparisons(self, member: Character, slot: str, current_item_id: str | None, candidates: list[str]) -> None:
        current_name = get_item(current_item_id).name if current_item_id is not None else "Empty"
        self.say(f"Current {equipment_slot_label(slot)}: {current_name}")
        base_state = self.preview_member_after_slot_change(member, slot, current_item_id)
        if current_item_id is not None:
            unequipped_state = self.preview_member_after_slot_change(member, slot, None)
            self.say(f"Unequip: {self.equipment_comparison_summary(base_state, unequipped_state)}")
        if not candidates:
            return
        self.say("Compare with current:")
        for item_id in candidates:
            preview_state = self.preview_member_after_slot_change(member, slot, item_id)
            self.say(f"- {get_item(item_id).name}: {self.equipment_comparison_summary(base_state, preview_state)}")

    def manage_equipment_slot(self, member, slot: str) -> bool:
        current_item_id = member.equipment_slots.get(slot)
        candidates = self.compatible_inventory_items_for_slot(member, slot)
        if current_item_id is None and not candidates:
            self.say(f"No unequipped inventory item fits {equipment_slot_label(slot)} for {member.name}.")
            return False
        self.show_equipment_comparisons(member, slot, current_item_id, candidates)
        options: list[str] = []
        if current_item_id is not None:
            options.append(f"Unequip {get_item(current_item_id).name}")
        options.extend(format_inventory_line(item_id, self.available_inventory_count(item_id)) for item_id in candidates)
        options.append("Back")
        choice = self.choose(
            f"What do you want to do with {equipment_slot_label(slot)} for {member.name}?",
            options,
            allow_meta=False,
        )
        if choice == len(options):
            return False
        if current_item_id is not None and choice == 1:
            member.equipment_slots[slot] = None
            self.sync_equipment(member)
            self.say(f"{member.name} clears {equipment_slot_label(slot)}.")
            return True
        item_offset = 1 if current_item_id is not None else 0
        return self.equip_item_to_slot(member, candidates[choice - 1 - item_offset], slot)

    def compatible_inventory_items_for_slot(self, member, slot: str) -> list[str]:
        item_ids: list[str] = []
        for item_id, quantity in self.inventory_dict().items():
            if quantity <= 0 or self.available_inventory_count(item_id) <= 0:
                continue
            item = get_item(item_id)
            if not item.is_equippable():
                continue
            if self.item_can_fit_slot(member, item, slot):
                item_ids.append(item_id)
        item_ids.sort(key=lambda item_id: (get_item(item_id).rarity, get_item(item_id).name))
        return item_ids

    def item_can_fit_slot(self, member, item, slot: str) -> bool:
        if slot == "main_hand":
            return item.weapon is not None
        if slot == "off_hand":
            return bool(item.shield_bonus) or (item.weapon is not None and item.weapon.hands_required == 1)
        if slot == "chest":
            return item.armor is not None
        if slot in {"ring_1", "ring_2"}:
            return item.item_type == "ring"
        return canonical_equipment_slot(item.slot) == slot

    def equip_item_to_slot(self, member, item_id: str, slot: str) -> bool:
        item = get_item(item_id)
        if not self.item_can_fit_slot(member, item, slot):
            self.say(f"{item.name} does not fit {equipment_slot_label(slot)}.")
            return False
        if slot == "off_hand":
            main_hand_id = member.equipment_slots.get("main_hand")
            if main_hand_id is not None:
                main_hand_item = get_item(main_hand_id)
                if main_hand_item.weapon is not None and main_hand_item.weapon.hands_required >= 2:
                    self.say(f"{member.name} cannot use an off-hand item while wielding a two-handed weapon.")
                    return False
            if item.weapon is not None and item.weapon.hands_required >= 2:
                self.say(f"{item.name} needs two hands and cannot be equipped off-hand.")
                return False
        if slot == "main_hand" and item.weapon is not None and item.weapon.hands_required >= 2:
            member.equipment_slots["off_hand"] = None
        member.equipment_slots[slot] = item.legacy_id or item.item_id
        self.sync_equipment(member)
        self.say(f"{member.name} equips {item.name} in {equipment_slot_label(slot)}.")
        return True

    def equip_from_inventory(self) -> None:
        self.manage_equipment()

    def unequip_gear(self) -> None:
        self.manage_equipment()

    def drop_items(self) -> None:
        assert self.state is not None
        item_ids = [item_id for item_id in self.inventory_dict() if self.available_inventory_count(item_id) > 0]
        if not item_ids:
            self.say("There are no unequipped items available to drop.")
            return
        item_ids.sort(key=lambda item_id: get_item(item_id).name)
        while True:
            choice = self.choose(
                "Choose an item to drop.",
                [format_inventory_line(item_id, self.available_inventory_count(item_id)) for item_id in item_ids] + ["Back"],
                allow_meta=False,
            )
            if choice == len(item_ids) + 1:
                return
            item_id = item_ids[choice - 1]
            if self.remove_inventory_item(item_id):
                self.say(f"You drop {get_item(item_id).name}.")
            return

    def sell_items(self, *, merchant_id: str | None = None, merchant_name: str | None = None) -> None:
        assert self.state is not None
        if merchant_name is None or merchant_id is None:
            self.say("You can only sell items when you are dealing with a merchant or trader.")
            return
        item_ids = [item_id for item_id in self.inventory_dict() if self.available_inventory_count(item_id) > 0]
        if not item_ids:
            self.say("There are no unequipped items available to sell.")
            return
        item_ids.sort(key=lambda item_id: get_item(item_id).name)
        while True:
            self.say(self.merchant_trade_summary(merchant_id, merchant_name))
            available_lookup = {item_id: self.available_inventory_count(item_id) for item_id in item_ids}
            self.render_trade_catalog(
                merchant_id=merchant_id,
                merchant_name=merchant_name,
                title=f"Sell to {merchant_name}",
                item_ids=item_ids,
                quantity_lookup=available_lookup,
                quantity_label="Owned",
                price_label="Sell",
                price_lookup={item_id: self.merchant_sell_price(merchant_id, item_id) for item_id in item_ids},
            )
            choice = self.choose(
                f"Choose an item to sell to {merchant_name}.",
                [
                    f"{get_item(item_id).name} x{self.available_inventory_count(item_id)} | sell {marks_label(self.merchant_sell_price(merchant_id, item_id))} each"
                    for item_id in item_ids
                ]
                + ["Back"],
                allow_meta=False,
                sticky_trailing_options=1,
            )
            if choice == len(item_ids) + 1:
                return
            item_id = item_ids[choice - 1]
            item = get_item(item_id)
            available = self.available_inventory_count(item_id)
            unit_price = self.merchant_sell_price(merchant_id, item_id)
            quantity = available if available == 1 else self.ask_quantity_or_back(f"How many {item.name} do you want to sell?", available)
            if quantity is None:
                continue
            if self.remove_inventory_item(item_id, quantity):
                total_price = unit_price * quantity
                self.state.gold += total_price
                stock = self.get_merchant_stock(merchant_id)
                stock[item_id] = stock.get(item_id, 0) + quantity
                play_sound_effect = getattr(self, "play_sound_effect", None)
                if callable(play_sound_effect):
                    play_sound_effect("sell_item")
                self.say(f"{merchant_name} buys {item.name} x{quantity} for {marks_label(total_price)}.")
            return

    def open_camp_menu(self) -> None:
        while True:
            choice = self.choose(
                "Review the party and camp supplies.",
                [
                    "View party",
                    "View journal",
                    "View inventory",
                    "Manage inventory",
                    "Back",
                ],
                allow_meta=False,
            )
            if choice == 1:
                self.show_party()
            elif choice == 2:
                self.show_journal()
            elif choice == 3:
                self.show_inventory()
            elif choice == 4:
                self.manage_inventory()
            else:
                return
