from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random
import re

from ...models import Armor, Character, Weapon
from ...ui.colors import colorize, rarity_color


RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary"]
RARITY_TITLES = {
    "common": "Common",
    "uncommon": "Uncommon",
    "rare": "Rare",
    "epic": "Epic",
    "legendary": "Legendary",
}


@dataclass(slots=True)
class Item:
    item_id: str
    name: str
    category: str
    item_type: str
    rarity: str
    description: str
    source: str
    weight: float
    value: int
    slot: str | None = None
    properties: list[str] | None = None
    supply_points: int = 0
    heal_dice: str | None = None
    heal_bonus: int = 0
    revive_hp: int = 0
    revive_dead: bool = False
    temp_hp: int = 0
    spell_slot_restore: int = 0
    cure_poison: bool = False
    clear_conditions: list[str] | None = None
    apply_conditions: dict[str, int] | None = None
    skill_bonuses: dict[str, int] | None = None
    save_bonuses: dict[str, int] | None = None
    ac_bonus: int = 0
    shield_bonus: int = 0
    attack_bonus: int = 0
    damage_bonus: int = 0
    initiative_bonus: int = 0
    spell_attack_bonus: int = 0
    spell_damage_bonus: int = 0
    healing_bonus: int = 0
    damage_type: str = ""
    versatile_damage: str | None = None
    range_text: str | None = None
    enchantment: str | None = None
    extra_damage_dice: str | None = None
    extra_damage_type: str = ""
    crit_extra_damage_dice: str | None = None
    damage_resistances: list[str] | None = None
    crit_immunity: bool = False
    stealth_advantage: bool = False
    notes: list[str] | None = None
    weapon: Weapon | None = None
    armor: Armor | None = None

    @property
    def rarity_title(self) -> str:
        return RARITY_TITLES[self.rarity]

    def is_consumable(self) -> bool:
        return self.category in {"consumable", "scroll", "supply"}

    def is_equippable(self) -> bool:
        return self.slot is not None or self.weapon is not None or self.armor is not None

    def is_combat_usable(self) -> bool:
        return self.is_consumable() and (
            self.heal_dice is not None
            or (self.revive_hp > 0 and not self.revive_dead)
            or self.temp_hp > 0
            or self.spell_slot_restore > 0
            or self.cure_poison
            or bool(self.clear_conditions)
            or bool(self.apply_conditions)
        )

    def supply_label(self) -> str:
        return f"{self.supply_points} supply" if self.supply_points else "no supply value"


@dataclass(slots=True)
class LootEntry:
    item_id: str
    chance: float
    minimum: int = 1
    maximum: int = 1


RARITY_WEAPON_BONUS = {
    "common": (0, 0),
    "uncommon": (1, 0),
    "rare": (1, 1),
    "epic": (2, 1),
    "legendary": (2, 2),
}
RARITY_ARMOR_BONUS = {
    "common": 0,
    "uncommon": 1,
    "rare": 1,
    "epic": 2,
    "legendary": 3,
}
RARITY_PREFIX = {
    "common": "Roadworn",
    "uncommon": "Ash-Kissed",
    "rare": "Starforged",
    "epic": "Kingshard",
    "legendary": "Mythwake",
}
RARITY_SOURCE = {
    "common": "General stores, starter kits, goblin packs, roadside scavengers, and ordinary frontier trade.",
    "uncommon": "Trusted traders, veteran scouts, shrine caches, and better-provisioned raider lieutenants.",
    "rare": "Hidden manor vaults, named enemy stashes, defended strongholds, and expensive specialist merchants.",
    "epic": "Deep relic chambers, late-act boss hoards, and secrets guarded by major story threats.",
    "legendary": "Mythic relic sites, endgame bosses, and unique Forgotten Realms wonders almost never seen in trade.",
}
RARITY_VALUE_MULTIPLIERS = {
    "common": 0.6,
    "uncommon": 1.25,
    "rare": 3.0,
    "epic": 4.0,
    "legendary": 5.0,
}


WEAPON_BASES = [
    {
        "slug": "longsword",
        "name": "Longsword",
        "damage": "1d8",
        "versatile_damage": "1d10",
        "damage_type": "slashing",
        "ability": "STR",
        "weapon_type": "longsword",
        "weight": 3.0,
        "value": 15,
        "description": "A balanced blade favored by soldiers and caravan guards.",
        "properties": ["versatile"],
    },
    {
        "slug": "shortsword",
        "name": "Shortsword",
        "damage": "1d6",
        "damage_type": "piercing",
        "ability": "FINESSE",
        "weapon_type": "shortsword",
        "weight": 2.0,
        "value": 10,
        "description": "A quick sidearm built for speed in tight quarters.",
        "finesse": True,
        "properties": ["finesse", "light"],
    },
    {
        "slug": "rapier",
        "name": "Rapier",
        "damage": "1d8",
        "damage_type": "piercing",
        "ability": "FINESSE",
        "weapon_type": "rapier",
        "weight": 2.0,
        "value": 25,
        "description": "A slender dueling blade that rewards precision.",
        "finesse": True,
        "properties": ["finesse"],
    },
    {
        "slug": "greatsword",
        "name": "Greatsword",
        "damage": "2d6",
        "damage_type": "slashing",
        "ability": "STR",
        "weapon_type": "greatsword",
        "weight": 6.0,
        "value": 15,
        "description": "A heavy two-handed sword for decisive strikes.",
        "hands_required": 2,
        "properties": ["heavy", "two-handed"],
    },
    {
        "slug": "warhammer",
        "name": "Warhammer",
        "damage": "1d8",
        "versatile_damage": "1d10",
        "damage_type": "bludgeoning",
        "ability": "STR",
        "weapon_type": "warhammer",
        "weight": 2.0,
        "value": 15,
        "description": "A dense hammer built to break armor and bone.",
        "properties": ["versatile"],
    },
    {
        "slug": "battleaxe",
        "name": "Battleaxe",
        "damage": "1d8",
        "versatile_damage": "1d10",
        "damage_type": "slashing",
        "ability": "STR",
        "weapon_type": "battleaxe",
        "weight": 4.0,
        "value": 10,
        "description": "A broad axe with a brutal chopping edge.",
        "properties": ["versatile"],
    },
    {
        "slug": "spear",
        "name": "Spear",
        "damage": "1d6",
        "versatile_damage": "1d8",
        "damage_type": "piercing",
        "range_text": "20/60",
        "ability": "STR",
        "weapon_type": "spear",
        "weight": 3.0,
        "value": 1,
        "description": "A simple hunting and war spear common along the frontier.",
        "properties": ["thrown", "versatile"],
    },
    {
        "slug": "mace",
        "name": "Mace",
        "damage": "1d6",
        "damage_type": "bludgeoning",
        "ability": "STR",
        "weapon_type": "mace",
        "weight": 4.0,
        "value": 5,
        "description": "A simple blunt weapon used by guards and priests alike.",
    },
    {
        "slug": "quarterstaff",
        "name": "Quarterstaff",
        "damage": "1d6",
        "versatile_damage": "1d8",
        "damage_type": "bludgeoning",
        "ability": "STR",
        "weapon_type": "quarterstaff",
        "weight": 4.0,
        "value": 2,
        "description": "A traveling staff that doubles as a practical weapon.",
        "properties": ["versatile"],
    },
    {
        "slug": "dagger",
        "name": "Dagger",
        "damage": "1d4",
        "damage_type": "piercing",
        "range_text": "20/60",
        "ability": "FINESSE",
        "weapon_type": "dagger",
        "weight": 1.0,
        "value": 2,
        "description": "A knife-sized blade easy to hide or throw.",
        "finesse": True,
        "properties": ["light", "thrown"],
    },
    {
        "slug": "shortbow",
        "name": "Shortbow",
        "damage": "1d6",
        "damage_type": "piercing",
        "range_text": "80/320",
        "ability": "DEX",
        "weapon_type": "shortbow",
        "weight": 2.0,
        "value": 25,
        "description": "A flexible bow used by scouts, hunters, and raiders.",
        "ranged": True,
        "hands_required": 2,
        "properties": ["ammunition", "two-handed"],
    },
    {
        "slug": "longbow",
        "name": "Longbow",
        "damage": "1d8",
        "damage_type": "piercing",
        "range_text": "150/600",
        "ability": "DEX",
        "weapon_type": "longbow",
        "weight": 2.0,
        "value": 50,
        "description": "A tall war bow that hits hard at range.",
        "ranged": True,
        "to_hit_bonus": 1,
        "hands_required": 2,
        "properties": ["ammunition", "heavy", "two-handed"],
    },
]

ARMOR_BASES = [
    {
        "slug": "traveler_clothes",
        "name": "Traveler Clothes",
        "base_ac": 10,
        "armor_type": "clothing",
        "dex_cap": None,
        "heavy": False,
        "weight": 4.0,
        "value": 1,
        "description": "Layered clothes and a padded coat with no real armor plates.",
    },
    {
        "slug": "padded_armor",
        "name": "Padded Armor",
        "base_ac": 11,
        "armor_type": "light",
        "dex_cap": None,
        "heavy": False,
        "weight": 8.0,
        "value": 5,
        "description": "Quilted layers that protect better than plain clothes.",
    },
    {
        "slug": "leather_armor",
        "name": "Leather Armor",
        "base_ac": 11,
        "armor_type": "light",
        "dex_cap": None,
        "heavy": False,
        "weight": 10.0,
        "value": 10,
        "description": "Tough boiled leather worn by scouts and rogues.",
    },
    {
        "slug": "studded_leather",
        "name": "Studded Leather",
        "base_ac": 12,
        "armor_type": "light",
        "dex_cap": None,
        "heavy": False,
        "weight": 13.0,
        "value": 45,
        "description": "Leather reinforced with rivets and hidden plates.",
    },
    {
        "slug": "chain_shirt",
        "name": "Chain Shirt",
        "base_ac": 13,
        "armor_type": "medium",
        "dex_cap": 2,
        "heavy": False,
        "weight": 20.0,
        "value": 50,
        "description": "Close-fitting mail that balances defense and mobility.",
    },
    {
        "slug": "scale_mail",
        "name": "Scale Mail",
        "base_ac": 14,
        "armor_type": "medium",
        "dex_cap": 2,
        "heavy": False,
        "stealth_disadvantage": True,
        "weight": 45.0,
        "value": 50,
        "description": "Linked metal scales that turn glancing blows well.",
    },
    {
        "slug": "breastplate",
        "name": "Breastplate",
        "base_ac": 14,
        "armor_type": "medium",
        "dex_cap": 2,
        "heavy": False,
        "weight": 20.0,
        "value": 400,
        "description": "A polished cuirass that protects without slowing the wearer much.",
    },
    {
        "slug": "chain_mail",
        "name": "Chain Mail",
        "base_ac": 16,
        "armor_type": "heavy",
        "dex_cap": 0,
        "heavy": True,
        "stealth_disadvantage": True,
        "weight": 55.0,
        "value": 75,
        "description": "Heavy linked armor standard among trained soldiers.",
    },
    {
        "slug": "splint_armor",
        "name": "Splint Armor",
        "base_ac": 17,
        "armor_type": "heavy",
        "dex_cap": 0,
        "heavy": True,
        "stealth_disadvantage": True,
        "weight": 60.0,
        "value": 200,
        "description": "Metal strips over leather that offer stout protection.",
    },
]

SHIELD_BASES = [
    {
        "slug": "shield",
        "name": "Shield",
        "slot": "off_hand",
        "item_type": "shield",
        "weight": 6.0,
        "value": 10,
        "description": "A standard shield that adds 2 to Armor Class when your other hand is free.",
        "shield_bonus": 2,
        "properties": ["shield"],
    }
]

GEAR_BASES = [
    {"slug": "traveler_hood", "name": "Traveler's Hood", "slot": "head", "item_type": "helmet", "weight": 1.0, "value": 5, "description": "A practical hood and cap for road dust.", "skill_bonuses": {"Perception": 1}, "rarities": {"common", "uncommon"}},
    {"slug": "iron_cap", "name": "Iron Cap", "slot": "head", "item_type": "helmet", "weight": 2.0, "value": 12, "description": "A metal cap favored by caravan guards.", "ac_bonus": 1, "rarities": {"common", "uncommon", "rare"}},
    {"slug": "delver_lantern_hood", "name": "Delver Lantern Hood", "slot": "head", "item_type": "helmet", "weight": 1.2, "value": 18, "description": "A miner's hood stitched around a shuttered crystal lantern and polished brow mirror.", "skill_bonuses": {"Investigation": 1, "Perception": 1}, "rarities": {"uncommon", "rare"}, "source": "Wave Echo side chambers, expedition quartermasters, and recovered survey caches."},
    {"slug": "wayfarer_boots", "name": "Wayfarer Boots", "slot": "boots", "item_type": "boots", "weight": 2.0, "value": 8, "description": "Boots made for trail miles and rocky ground.", "skill_bonuses": {"Survival": 1}, "rarities": {"common", "uncommon"}},
    {"slug": "silent_step_boots", "name": "Silent Step Boots", "slot": "boots", "item_type": "boots", "weight": 2.0, "value": 18, "description": "Soft-soled boots stitched for scouts and burglars.", "skill_bonuses": {"Stealth": 1}, "rarities": {"uncommon", "rare", "epic"}},
    {"slug": "echostep_boots", "name": "Echostep Boots", "slot": "boots", "item_type": "boots", "weight": 2.0, "value": 22, "description": "Soft boots wrapped in resonant thread that help the wearer place each step with uncanny care.", "skill_bonuses": {"Acrobatics": 1}, "rarities": {"uncommon", "rare"}, "source": "Conyberry ruins, pact survey lockers, and stealth-minded expedition spoils."},
    {"slug": "work_gloves", "name": "Work Gloves", "slot": "gloves", "item_type": "gloves", "weight": 1.0, "value": 4, "description": "Tough gloves that help with climbing and hauling.", "skill_bonuses": {"Athletics": 1}, "rarities": {"common", "uncommon"}},
    {"slug": "scribe_gloves", "name": "Scribe Gloves", "slot": "gloves", "item_type": "gloves", "weight": 0.5, "value": 10, "description": "Fine gloves marked with ink-proof sigils.", "skill_bonuses": {"Arcana": 1, "Investigation": 1}, "rarities": {"uncommon", "rare"}},
    {"slug": "forgehand_gauntlets", "name": "Forgehand Gauntlets", "slot": "gloves", "item_type": "gloves", "weight": 2.0, "value": 20, "description": "Rune-etched work gauntlets built for hauling ore, bracing shields, and striking through sparks.", "skill_bonuses": {"Athletics": 1}, "rarities": {"uncommon", "rare"}, "source": "Collapsed smithies, dwarven work camps, and Wave Echo tool vaults."},
    {"slug": "reinforced_breeches", "name": "Reinforced Cloak", "slot": "cape", "item_type": "cloak", "weight": 2.0, "value": 7, "description": "A travel cloak with patchwork reinforcement stitched into the lining.", "ac_bonus": 1, "rarities": {"common", "uncommon"}},
    {"slug": "trail_leggings", "name": "Trail Mantle", "slot": "cape", "item_type": "cloak", "weight": 1.5, "value": 9, "description": "A flexible mantle cut to stay out of the way on rough roads.", "skill_bonuses": {"Acrobatics": 1}, "rarities": {"common", "uncommon"}},
    {"slug": "copper_ring", "name": "Copper Ring", "slot": "ring", "item_type": "ring", "weight": 0.1, "value": 6, "description": "A cheap ring carried for luck or sentiment.", "skill_bonuses": {"Persuasion": 1}, "rarities": {"common", "uncommon"}},
    {"slug": "watcher_ring", "name": "Watcher's Ring", "slot": "ring", "item_type": "ring", "weight": 0.1, "value": 20, "description": "A ring etched with tiny all-seeing eyes.", "skill_bonuses": {"Insight": 1, "Perception": 1}, "rarities": {"uncommon", "rare", "epic"}},
    {"slug": "sigil_anchor_ring", "name": "Sigil Anchor Ring", "slot": "ring", "item_type": "ring", "weight": 0.1, "value": 32, "description": "A narrow band inscribed with counter-sigils meant to keep strange influences from taking easy root.", "skill_bonuses": {"Arcana": 1}, "save_bonuses": {"WIS_save": 1}, "rarities": {"rare", "epic"}, "source": "Cult reliquaries, black-lake shrines, and the deepest Phandelver vaults."},
    {"slug": "amber_amulet", "name": "Amber Amulet", "slot": "neck", "item_type": "amulet", "weight": 0.2, "value": 15, "description": "A warm amber charm worn for steady nerves.", "save_bonuses": {"WIS_save": 1}, "rarities": {"uncommon", "rare"}},
    {"slug": "soldiers_amulet", "name": "Soldier's Amulet", "slot": "neck", "item_type": "amulet", "weight": 0.2, "value": 12, "description": "A campaign token often worn by veterans.", "save_bonuses": {"CON_save": 1}, "rarities": {"common", "uncommon", "rare"}},
    {"slug": "choirward_amulet", "name": "Choirward Amulet", "slot": "neck", "item_type": "amulet", "weight": 0.2, "value": 28, "description": "A hammered silver charm engraved with a broken circle, worn by those who expect whispered magic to answer back.", "save_bonuses": {"WIS_save": 1}, "rarities": {"uncommon", "rare"}, "source": "Shrines to Dumathoin, rescued prisoners, and caches hidden from the Quiet Choir."},
]

WEAPON_RARITY_AVAILABILITY = {
    "common": {base["slug"] for base in WEAPON_BASES},
    "uncommon": {base["slug"] for base in WEAPON_BASES},
    "rare": {"longsword", "rapier", "greatsword", "warhammer", "battleaxe", "longbow", "shortbow"},
    "epic": {"longsword", "greatsword", "longbow"},
    "legendary": {"longsword"},
}

ARMOR_RARITY_AVAILABILITY = {
    "common": {base["slug"] for base in ARMOR_BASES},
    "uncommon": {"leather_armor", "studded_leather", "chain_shirt", "scale_mail", "breastplate", "chain_mail"},
    "rare": {"studded_leather", "breastplate", "chain_mail", "splint_armor"},
    "epic": {"breastplate", "splint_armor"},
    "legendary": {"splint_armor"},
}

TRINKET_RARITY_COUNTS = {
    "common": 80,
    "uncommon": 32,
    "rare": 16,
    "epic": 4,
    "legendary": 2,
}

SUPPLY_ITEMS = [
    ("bread_round", "Bread Round", "A dense travel loaf baked to last several days.", 0.5, 2, 1, "Common pantry food sold in Neverwinter and Phandalin."),
    ("miners_ration_tin", "Miner's Ration Tin", "A square tin packed with hard cheese, smoked mushrooms, and dense black bread for a long shift underground.", 0.9, 6, 3, "Wave Echo expedition wagons, dwarven waystations, and reclaimed survey packs."),
    ("mushroom_broth_flask", "Mushroom Broth Flask", "A stoppered flask of salty mushroom broth that stays warm longer than it should.", 0.8, 5, 2, "Conyberry kitchens, miner camps, and late-night watchfires."),
    ("dried_fish", "Dried Fish", "Salted river fish wrapped for road use.", 0.5, 3, 2, "Fishing stalls, caravan stores, and goblin satchels."),
    ("goat_cheese", "Goat Cheese", "Sharp frontier cheese that keeps well in cloth.", 0.5, 4, 2, "Farmsteads, inn kitchens, and pack saddles."),
    ("smoked_ham", "Smoked Ham Slice", "A rich cured cut that can sustain a full meal.", 1.0, 6, 3, "Inn stores, bandit camps, and merchant wagons."),
    ("camp_stew_jar", "Camp Stew Jar", "A sealed clay jar of thick traveling stew.", 1.5, 8, 4, "Stonehill Inn kitchens and quartermaster stores."),
    ("frontier_ale", "Frontier Ale", "Cheap ale in a sealed skin for the road.", 1.0, 3, 1, "Taverns, patrol wagons, and idle bandit crates."),
    ("red_wine", "Red Wine", "A bottle of decent red meant for officers or merchants.", 1.0, 8, 2, "Steward gifts, manor cellars, and noble stores."),
    ("dried_apple", "Dried Apple Pouch", "Sweet dried fruit easy to ration out in camp.", 0.5, 3, 1, "General stores and shrine pantries."),
    ("nut_mix", "Roasted Nut Mix", "A cloth pouch of roasted nuts and herbs.", 0.3, 3, 1, "Scouts, hunters, and roadside traders."),
    ("salt_pork", "Salt Pork", "A greasy but dependable protein for campfire meals.", 1.0, 5, 3, "Caravan barrels and military stores."),
    ("berry_tart", "Berry Tart", "A fragile but morale-boosting sweet wrapped in wax cloth.", 0.4, 4, 1, "Stonehill Inn and festival vendors."),
    ("travel_biscuits", "Travel Biscuits", "Hard biscuits made for soldiers and explorers.", 0.5, 2, 1, "Quartermaster kits and supply sacks."),
    ("mushroom_skewer", "Mushroom Skewer", "Charred mushrooms brushed with herb oil.", 0.4, 4, 1, "Shrine gardens, campfires, and druid caches."),
    ("spiced_sausage", "Spiced Sausage", "A cured sausage with enough salt to keep for days.", 0.7, 5, 2, "Hunter camps, taverns, and bandit stores."),
    ("honey_cake", "Honey Cake", "A compact sweet cake with surprisingly good shelf life.", 0.4, 5, 1, "Temple kitchens and holiday markets."),
    ("root_vegetables", "Root Vegetable Bundle", "A tied bundle of onions, carrots, and turnips.", 1.2, 4, 2, "Farm plots and kitchen cellars."),
    ("black_tea", "Black Tea Tin", "A small tin of bitter black tea leaves.", 0.2, 6, 1, "Merchant caravans and refined provisions."),
    ("herbal_tea", "Herbal Tea Satchel", "Calming herbs brewed to steady nerves at camp.", 0.2, 5, 1, "Shrines, apothecaries, and ranger packs."),
    ("river_clams", "River Clam Basket", "Fresh clams packed in damp reeds.", 1.5, 7, 2, "Fishers and riverbank stalls."),
    ("spirit_bottle", "Strong Spirit Bottle", "Clear grain spirit used for drink, trade, and sterilizing wounds.", 1.0, 7, 2, "Bandit stores, surgeons, and caravan packs."),
]

CONSUMABLE_ITEMS = [
    {
        "item_id": "potion_healing",
        "name": "Potion of Healing",
        "rarity": "common",
        "description": "A red tonic matching the official Potion of Healing profile.",
        "source": "Starter kits, shrine aid packs, goblin satchels, and common loot drops.",
        "weight": 0.5,
        "value": 15,
        "heal_dice": "2d4",
        "heal_bonus": 2,
        "notes": ["Official baseline: regains 2d4 + 2 hit points."],
    },
    {
        "item_id": "greater_healing_draught",
        "name": "Greater Healing Draught",
        "rarity": "uncommon",
        "description": "A frontier draught built on the official Greater Healing potion numbers.",
        "source": "Ashfall Watch stores, shrine caches, and uncommon treasure rolls.",
        "weight": 0.5,
        "value": 38,
        "heal_dice": "4d4",
        "heal_bonus": 4,
        "notes": ["Official baseline: regains 4d4 + 4 hit points."],
    },
    {
        "item_id": "delvers_amber",
        "name": "Delver's Amber",
        "rarity": "uncommon",
        "description": "A honey-thick tonic brewed to steady breath and nerve in collapsing tunnels.",
        "source": "Stonehollow survey stores, dwarven quartermasters, and careful expedition caches.",
        "weight": 0.4,
        "value": 34,
        "temp_hp": 6,
        "notes": ["Grants 6 temporary hit points and calms panic before a hard descent."],
    },
    {
        "item_id": "resonance_tonic",
        "name": "Resonance Tonic",
        "rarity": "uncommon",
        "description": "A mineral tonic that sharpens focus when the air starts humming with old magic.",
        "source": "Agatha's bargaining cache, pact research chests, and Wave Echo side vaults.",
        "weight": 0.3,
        "value": 30,
        "spell_slot_restore": 1,
        "notes": ["Restores 4 MP and helps shake off rattled footing in this adaptation."],
    },
    {
        "item_id": "superior_healing_elixir",
        "name": "Superior Healing Elixir",
        "rarity": "rare",
        "description": "A luminous elixir modeled on the official Superior Healing potion.",
        "source": "Hidden vaults, elite captains, and rare merchant caravans.",
        "weight": 0.5,
        "value": 350,
        "heal_dice": "8d4",
        "heal_bonus": 8,
        "notes": ["Official baseline: regains 8d4 + 8 hit points."],
    },
    {
        "item_id": "supreme_healing_phial",
        "name": "Supreme Healing Phial",
        "rarity": "epic",
        "description": "A jewel-red phial based on the official Supreme Healing potion.",
        "source": "Late-act relic caches, dragon hoards, and near-mythic alchemical vaults.",
        "weight": 0.5,
        "value": 900,
        "heal_dice": "10d4",
        "heal_bonus": 20,
        "notes": ["Official baseline: regains 10d4 + 20 hit points."],
    },
    {
        "item_id": "phoenix_salts",
        "name": "Phoenix Salts",
        "rarity": "epic",
        "description": "Smoldering salts that can drag a fallen ally back to fighting shape.",
        "source": "Secret relic hoards and later-act treasure tables.",
        "weight": 0.3,
        "value": 700,
        "revive_hp": 5,
        "notes": ["Game adaptation: revives a downed ally at 5 HP."],
    },
    {
        "item_id": "warding_tonic",
        "name": "Warding Tonic",
        "rarity": "common",
        "description": "A simple tonic that grants temporary durability before a fight.",
        "source": "General stores, caravan alchemists, and common bandit loot.",
        "weight": 0.4,
        "value": 10,
        "temp_hp": 4,
        "notes": ["Grants 4 temporary hit points."],
    },
    {
        "item_id": "potion_heroism",
        "name": "Potion of Heroism",
        "rarity": "rare",
        "description": "An adaptation of the official Potion of Heroism for this faster combat system.",
        "source": "Temple vaults, champion kits, and rare divine caches.",
        "weight": 0.4,
        "value": 220,
        "temp_hp": 10,
        "notes": ["Official inspiration: grants temporary hit points and a bless-like combat edge."],
    },
    {
        "item_id": "forge_blessing_elixir",
        "name": "Forge-Blessing Elixir",
        "rarity": "rare",
        "description": "A copper-bright elixir distilled from soot-black herbs and lingering forge magic.",
        "source": "Wave Echo reliquaries, forge galleries, and named cult lieutenants.",
        "weight": 0.4,
        "value": 95,
        "temp_hp": 8,
        "notes": ["Grants 8 temporary hit points and a brief surge of courage in this adaptation."],
    },
    {
        "item_id": "thoughtward_draught",
        "name": "Thoughtward Draught",
        "rarity": "rare",
        "description": "A bitter blue draught prepared by hunters of cursed lore to push back invasive whispers.",
        "source": "Cult-breaking kits, hidden shrine lockers, and black-lake escape satchels.",
        "weight": 0.3,
        "value": 82,
        "temp_hp": 4,
        "notes": ["Clears mental pressure and leaves behind 4 temporary hit points."],
    },
    {
        "item_id": "blessed_salve",
        "name": "Blessed Salve",
        "rarity": "uncommon",
        "description": "A holy salve inspired by restorative ointments such as Keoghtom's Ointment.",
        "source": "Shrine donations, acolyte satchels, and priestly reward caches.",
        "weight": 0.2,
        "value": 24,
        "heal_dice": "1d8",
        "heal_bonus": 2,
        "cure_poison": True,
        "notes": ["Heals 1d8 + 2 and cures poison in this adaptation."],
    },
    {
        "item_id": "antitoxin_vial",
        "name": "Antitoxin Vial",
        "rarity": "common",
        "description": "A bitter counteragent modeled after official antitoxin utility.",
        "source": "Apothecaries, shrine stores, and caravan medicine kits.",
        "weight": 0.2,
        "value": 14,
        "cure_poison": True,
        "notes": ["Cures poison now and grants short-term resistance to poison in combat."],
    },
    {
        "item_id": "focus_ink",
        "name": "Focus Ink",
        "rarity": "uncommon",
        "description": "Arcane ink and herbs steeped to restore a flicker of spellcasting stamina.",
        "source": "Wizard caches, rare scribes, and magical loot tables.",
        "weight": 0.2,
        "value": 26,
        "spell_slot_restore": 1,
        "notes": ["Restores 4 MP."],
    },
    {
        "item_id": "moonmint_drops",
        "name": "Moonmint Drops",
        "rarity": "common",
        "description": "A tin of sharp mint lozenges that settle the body after a rough fight.",
        "source": "Inn kitchens, halfling traders, and common loot sacks.",
        "weight": 0.1,
        "value": 8,
        "heal_dice": "1d4",
        "heal_bonus": 1,
        "notes": ["Restores 1d4 + 1 hit points and clears fear or hearing shock."],
    },
    {
        "item_id": "giantfire_balm",
        "name": "Giantfire Balm",
        "rarity": "rare",
        "description": "Hot resin balm that surges warmth and vigor through battered limbs.",
        "source": "Rare alchemist shelves, Emberhall stores, and later-act finds.",
        "weight": 0.4,
        "value": 240,
        "temp_hp": 10,
        "notes": ["Grants 10 temporary hit points and shakes off control effects."],
    },
    {
        "item_id": "fireward_elixir",
        "name": "Fireward Elixir",
        "rarity": "uncommon",
        "description": "A resistance draught inspired by official Potions of Resistance.",
        "source": "Shrine braziers, dragon-hunter packs, and uncommon magical stores.",
        "weight": 0.3,
        "value": 34,
        "notes": ["Grants fire resistance for several rounds."],
    },
    {
        "item_id": "dust_of_disappearance",
        "name": "Dust of Disappearance",
        "rarity": "rare",
        "description": "A pinch of gray dust based on the official Dust of Disappearance.",
        "source": "Wizard vaults, covert operatives, and hidden manor stores.",
        "weight": 0.1,
        "value": 180,
        "notes": ["Makes the target invisible for a short span."],
    },
]


def rarity_value(base_value: int, rarity: str) -> int:
    return max(1, int(base_value * RARITY_VALUE_MULTIPLIERS[rarity] + 0.5))


SCROLL_EFFECTS = [
    ("scroll_mending_word", "Scroll of Mending Word", "common", "A simple healing prayer written for quick use.", "Shrines, hedge mages, and healer caches.", "1d6", 2, 0, 0, False),
    ("scroll_lesser_restoration", "Scroll of Lesser Restoration", "uncommon", "A clean restorative script that breaks poison and weakness.", "Shrine archives and rare support caches.", None, 0, 0, 0, True),
    ("scroll_revivify", "Scroll of Revivify", "uncommon", "A tightly warded resurrection script for camp rites after a fresh battlefield death.", "Rarely stocked by frontier traders and occasionally recovered from hard-fought battles.", None, 0, 0, 0, False),
    ("scroll_arcane_refresh", "Scroll of Arcane Refresh", "rare", "An elegant sigil-chain that restores a surge of MP.", "Wizard satchels, hidden libraries, and rare arcane drops.", None, 0, 0, 1, False),
    ("scroll_echo_step", "Scroll of Echo Step", "rare", "A delicate step-script that blurs the reader between falling dust and reflected sound.", "Wave Echo script tubes, hidden survey lockers, and expert scout caches.", None, 0, 0, 0, False),
    ("scroll_quell_the_deep", "Scroll of Quell the Deep", "rare", "A warding litany copied by priests and delvers who learned that some caverns answer back.", "Temple satchels, ruined chapels, and counter-cult ward caches.", "2d6", 2, 0, 0, False),
    ("scroll_forge_shelter", "Scroll of Forge Shelter", "rare", "A layered sigil-sheet that kindles a protective halo like banked coals around the reader.", "Forge of Spells annexes, dwarven vault doors, and late-act expedition rewards.", None, 0, 8, 0, False),
    ("scroll_guardian_light", "Scroll of Guardian Light", "uncommon", "A radiant seal that wraps the reader in a protective glow.", "Temple vaults, priestly gifts, and divine loot pools.", None, 0, 6, 0, False),
    ("scroll_ember_ward", "Scroll of Ember Ward", "rare", "An ashen ward-scroll that leaves shimmering protection in its wake.", "Ashfall Watch stores and hidden Emberhall shelves.", None, 0, 8, 0, False),
    ("scroll_surge_of_life", "Scroll of Surge of Life", "epic", "A difficult script that can haul a fallen ally back with a gasp.", "Later-act relic troves and named boss caches.", None, 0, 0, 0, False),
    ("scroll_clarity", "Scroll of Clarity", "common", "A script of calm focus and measured breathing.", "Libraries, sages, and reward satchels.", "1d4", 1, 0, 0, False),
    ("scroll_battle_psalm", "Scroll of Battle Psalm", "uncommon", "A hymn-scroll that hardens the spirit before battle.", "Temple vaults, marshal chapels, and divine support caches.", None, 0, 4, 0, False),
    ("scroll_starlit_rest", "Scroll of Starlit Rest", "rare", "A rare scroll of restful sigils used by experienced camp leaders.", "Secret ranger caches and rare restful rewards.", "2d6", 3, 0, 0, False),
    ("scroll_resurgent_flame", "Scroll of Resurgent Flame", "epic", "A blazing script said to rekindle nearly spent life.", "Future acts and mythic relic bundles.", None, 0, 12, 0, False),
]

UNIQUE_REWARD_ITEMS = [
    {
        "item_id": "miras_blackwake_seal",
        "name": "Mira's Blackwake Seal",
        "item_type": "ring",
        "rarity": "uncommon",
        "description": "A dark steel signet stamped with Neverwinter watch authority and a private route cipher.",
        "source": "Quest reward from Embers Before the Road.",
        "weight": 0.1,
        "value": 80,
        "slot": "ring_1",
        "properties": ["ring", "quest_reward"],
        "skill_bonuses": {"Investigation": 1, "Persuasion": 1},
        "initiative_bonus": 1,
        "notes": ["Marks the party as trusted enough to cite Mira's Blackwake proof in later negotiations."],
    },
    {
        "item_id": "roadwarden_cloak",
        "name": "Roadwarden Cloak",
        "item_type": "cloak",
        "rarity": "uncommon",
        "description": "A weather-treated frontier cloak bearing Tessa Harrow's field stitch inside the hem.",
        "source": "Quest reward from Stop the Watchtower Raids.",
        "weight": 1.4,
        "value": 90,
        "slot": "cape",
        "properties": ["cloak", "quest_reward"],
        "skill_bonuses": {"Survival": 1},
        "ac_bonus": 1,
        "notes": ["A practical badge of road service that helps the wearer travel and keep their guard up."],
    },
    {
        "item_id": "barthen_resupply_token",
        "name": "Barthen's Resupply Token",
        "item_type": "ring",
        "rarity": "uncommon",
        "description": "A brass trade token on a leather loop, good for a knowing nod at honest provision counters.",
        "source": "Quest reward from Keep the Shelves Full.",
        "weight": 0.1,
        "value": 65,
        "slot": "ring_1",
        "properties": ["ring", "quest_reward"],
        "skill_bonuses": {"Persuasion": 1},
        "save_bonuses": {"CON_save": 1},
        "notes": ["A reminder that full shelves can matter as much as full quivers."],
    },
    {
        "item_id": "lionshield_quartermaster_badge",
        "name": "Lionshield Quartermaster Badge",
        "item_type": "ring",
        "rarity": "uncommon",
        "description": "A clipped steel badge used by Lionshield factors to identify reliable caravan hands.",
        "source": "Quest reward from Reopen the Trade Lane.",
        "weight": 0.1,
        "value": 75,
        "slot": "ring_1",
        "properties": ["ring", "quest_reward"],
        "skill_bonuses": {"Investigation": 1, "Persuasion": 1},
        "initiative_bonus": 1,
        "notes": ["Linene's mark makes later logistics arguments easier to win."],
    },
    {
        "item_id": "gravequiet_amulet",
        "name": "Gravequiet Amulet",
        "item_type": "amulet",
        "rarity": "uncommon",
        "description": "A dull silver charm etched with a closed eye and old warding numerals.",
        "source": "Quest reward from Silence Old Owl Well.",
        "weight": 0.2,
        "value": 95,
        "slot": "neck",
        "properties": ["amulet", "quest_reward"],
        "skill_bonuses": {"Religion": 1},
        "save_bonuses": {"WIS_save": 1},
        "healing_bonus": 1,
        "notes": ["Made for crews who learned that some graves dislike being robbed."],
    },
    {
        "item_id": "edermath_scout_buckle",
        "name": "Edermath Scout Buckle",
        "item_type": "boots",
        "rarity": "uncommon",
        "description": "A battered boot-buckle from an old adventuring harness, polished back to use.",
        "source": "Quest reward from Break the Wyvern Tor Raiders.",
        "weight": 0.3,
        "value": 85,
        "slot": "boots",
        "properties": ["boots", "quest_reward"],
        "skill_bonuses": {"Perception": 1, "Survival": 1},
        "initiative_bonus": 1,
        "notes": ["Daran gives it only to people he trusts to read dangerous ground before it reads them."],
    },
    {
        "item_id": "edermath_cache_compass",
        "name": "Edermath Cache Compass",
        "item_type": "amulet",
        "rarity": "uncommon",
        "description": "A palm-sized trail compass in a dented brass case, its needle steadier near old field marks than ordinary north.",
        "source": "Recovered from Daran Edermath's old adventurer's cache.",
        "weight": 0.2,
        "value": 100,
        "slot": "neck",
        "properties": ["amulet", "unique", "quest_reward"],
        "skill_bonuses": {"Stealth": 1, "Survival": 1},
        "initiative_bonus": 1,
        "notes": ["Its scratched backplate marks a quiet orchard-to-highland route Daran no longer trusts to memory alone."],
    },
    {
        "item_id": "bryns_cache_keyring",
        "name": "Bryn's Cache Keyring",
        "item_type": "ring",
        "rarity": "uncommon",
        "description": "A ring of old cache tags and tiny picks, each filed down until it looks harmless.",
        "source": "Quest reward from Loose Ends.",
        "weight": 0.1,
        "value": 70,
        "slot": "ring_1",
        "properties": ["ring", "quest_reward"],
        "skill_bonuses": {"Sleight of Hand": 1, "Stealth": 1},
        "initiative_bonus": 1,
        "notes": ["Bryn's old routes are closed, but the habits that kept them alive are still useful."],
    },
    {
        "item_id": "dawnmantle_mercy_charm",
        "name": "Dawnmantle Mercy Charm",
        "item_type": "amulet",
        "rarity": "uncommon",
        "description": "A small dawnburst charm wrapped in field bandage thread and quiet Tymoran prayer knots.",
        "source": "Quest reward from Faith Under Ash.",
        "weight": 0.2,
        "value": 85,
        "slot": "neck",
        "properties": ["amulet", "quest_reward"],
        "skill_bonuses": {"Medicine": 1},
        "save_bonuses": {"WIS_save": 1},
        "healing_bonus": 1,
        "notes": ["Elira's answer to hard justice: carry mercy where it can still change the next choice."],
    },
    {
        "item_id": "innkeeper_credit_token",
        "name": "Innkeeper Credit Token",
        "item_type": "ring",
        "rarity": "uncommon",
        "description": "A brass room token stamped by Mara Stonehill after one night the common room did not break.",
        "source": "Quest reward from The Marked Keg.",
        "weight": 0.1,
        "value": 72,
        "slot": "ring_1",
        "properties": ["ring", "quest_reward"],
        "skill_bonuses": {"Insight": 1, "Persuasion": 1},
        "save_bonuses": {"CON_save": 1},
        "notes": ["Stonehill's staff recognizes it as proof the wearer helped keep panic from turning into business."],
    },
    {
        "item_id": "sella_ballad_token",
        "name": "Sella's Ballad Token",
        "item_type": "amulet",
        "rarity": "uncommon",
        "description": "A singer's token wrapped in blue thread, given to people who carried truth back before rumor could flatten it.",
        "source": "Quest reward from Songs for the Missing.",
        "weight": 0.2,
        "value": 78,
        "slot": "neck",
        "properties": ["amulet", "quest_reward"],
        "skill_bonuses": {"Insight": 1, "Performance": 1},
        "initiative_bonus": 1,
        "notes": ["Sella's token favors the moment when a room is about to listen, if someone brave enough speaks first."],
    },
    {
        "item_id": "blackseal_taster_pin",
        "name": "Blackseal Taster Pin",
        "item_type": "ring",
        "rarity": "uncommon",
        "description": "A small dark pin once used by couriers to test whether a message room felt honest enough to survive.",
        "source": "Quest reward from Quiet Table, Sharp Knives.",
        "weight": 0.1,
        "value": 84,
        "slot": "ring_1",
        "properties": ["ring", "quest_reward"],
        "skill_bonuses": {"Deception": 1, "Perception": 1},
        "initiative_bonus": 1,
        "notes": ["Nera says the pin is for people who can hear the knife before it leaves the whisper."],
    },
    {
        "item_id": "harl_road_knot",
        "name": "Harl Road-Knot",
        "item_type": "amulet",
        "rarity": "uncommon",
        "description": "A strip of Dain Harl's blue scarf rebound into a tight courier's knot and set on a simple neck cord.",
        "source": "Quest reward from Bring Back Dain's Name.",
        "weight": 0.2,
        "value": 82,
        "slot": "neck",
        "properties": ["amulet", "quest_reward"],
        "skill_bonuses": {"Insight": 1, "Survival": 1},
        "save_bonuses": {"CON_save": 1},
        "notes": ["Jerek says the knot is for people who bring truth back before the road can grind it flat."],
    },
    {
        "item_id": "kestrel_ledger_clasp",
        "name": "Kestrel Ledger Clasp",
        "item_type": "ring",
        "rarity": "uncommon",
        "description": "A brass page-clasp cut with river-route notches and Sabra's precise habit of never wasting a mark.",
        "source": "Quest reward from False Manifest Circuit.",
        "weight": 0.1,
        "value": 86,
        "slot": "ring_1",
        "properties": ["ring", "quest_reward"],
        "skill_bonuses": {"Investigation": 1, "Perception": 1},
        "initiative_bonus": 1,
        "notes": ["Sabra only gives the clasp to people who notice corrections before the road has to pay for them."],
    },
    {
        "item_id": "pact_waymap_case",
        "name": "Pact Waymap Case",
        "item_type": "helmet",
        "rarity": "rare",
        "description": "A brow-slung map case with crystal tabs that align old Phandelver survey marks.",
        "source": "Quest reward from Recover the Pact Waymap.",
        "weight": 0.8,
        "value": 180,
        "slot": "head",
        "properties": ["helmet", "quest_reward"],
        "skill_bonuses": {"Investigation": 2, "Survival": 1},
        "initiative_bonus": 1,
        "notes": ["The case turns recovered route fragments into usable marching decisions."],
    },
    {
        "item_id": "agathas_truth_lantern",
        "name": "Agatha's Truth Lantern",
        "item_type": "helmet",
        "rarity": "rare",
        "description": "A shuttered spirit-lantern that burns cold when a story is being bent around a corpse.",
        "source": "Quest reward from Ask the Banshee What Was Buried.",
        "weight": 1.0,
        "value": 165,
        "slot": "head",
        "properties": ["helmet", "quest_reward"],
        "skill_bonuses": {"Insight": 2},
        "save_bonuses": {"WIS_save": 1},
        "notes": ["It does not reveal every lie, but it makes buried truth harder to ignore."],
    },
    {
        "item_id": "stonehollow_survey_lantern",
        "name": "Stonehollow Survey Lantern",
        "item_type": "helmet",
        "rarity": "uncommon",
        "description": "A compact survey lamp repaired from Stonehollow field gear and marked with scholar initials.",
        "source": "Quest reward from Bring Back the Survey Team.",
        "weight": 1.1,
        "value": 105,
        "slot": "head",
        "properties": ["helmet", "quest_reward"],
        "skill_bonuses": {"Investigation": 1, "Perception": 1},
        "initiative_bonus": 1,
        "notes": ["A rescued team's work keeps helping long after the rescue is over."],
    },
    {
        "item_id": "woodland_wayfinder_boots",
        "name": "Woodland Wayfinder Boots",
        "item_type": "boots",
        "rarity": "rare",
        "description": "Soft green-black boots stitched with route marks from Daran's oldest woodland charts.",
        "source": "Quest reward from Break the Woodland Saboteurs.",
        "weight": 2.0,
        "value": 155,
        "slot": "boots",
        "properties": ["boots", "quest_reward"],
        "skill_bonuses": {"Stealth": 1, "Survival": 2},
        "initiative_bonus": 1,
        "notes": ["They favor careful feet, clean approaches, and paths that stay found."],
    },
    {
        "item_id": "claims_accord_brooch",
        "name": "Claims Accord Brooch",
        "item_type": "ring",
        "rarity": "rare",
        "description": "A silver-and-iron accord brooch stamped after the claims meeting survived its worst night.",
        "source": "Quest reward from Hold the Claims Meeting Together.",
        "weight": 0.1,
        "value": 170,
        "slot": "ring_1",
        "properties": ["ring", "quest_reward"],
        "skill_bonuses": {"Insight": 1, "Persuasion": 2},
        "notes": ["Proof that the wearer helped keep Phandalin arguing in words instead of blades."],
    },
    {
        "item_id": "freed_captive_prayer_beads",
        "name": "Freed-Captive Prayer Beads",
        "item_type": "amulet",
        "rarity": "rare",
        "description": "A string of mismatched beads, each tied on by someone who made it out of the South Adit alive.",
        "source": "Quest reward from Free the South Adit Prisoners.",
        "weight": 0.2,
        "value": 160,
        "slot": "neck",
        "properties": ["amulet", "quest_reward"],
        "skill_bonuses": {"Medicine": 1},
        "save_bonuses": {"WIS_save": 1},
        "healing_bonus": 2,
        "notes": ["The beads steady the hand that has to help someone else stand back up."],
    },
    {
        "item_id": "forgeheart_cinder",
        "name": "Forgeheart Cinder",
        "item_type": "ring",
        "rarity": "epic",
        "description": "A heatless ember sealed in dark glass, bright only when old forge magic pushes back.",
        "source": "Quest reward from Sever the Quiet Choir.",
        "weight": 0.1,
        "value": 320,
        "slot": "ring_1",
        "properties": ["ring", "quest_reward"],
        "skill_bonuses": {"Arcana": 2},
        "save_bonuses": {"WIS_save": 1},
        "initiative_bonus": 1,
        "spell_attack_bonus": 1,
        "damage_resistances": ["psychic"],
        "notes": ["A dangerous little victory: the Choir's pressure can still be felt, but now it has something to strike against."],
    },
]

TRINKET_PREFIXES = ["Ashen", "Silver", "Old", "Stone", "Moon", "Sun", "Gloom", "Star", "Iron", "River"]
TRINKET_SUFFIXES = ["Token", "Seal", "Charm", "Icon", "Brooch", "Compass", "Cog", "Medallion"]
TRINKET_THEMES = [
    ("scout", "Useful to scouts and pathfinders."),
    ("priest", "Favored by priests and shrine keepers."),
    ("soldier", "Carried by veterans, guards, and mercenaries."),
    ("bandit", "Common in raider packs and hidden caches."),
]

ARMOR_RESISTANCE_TYPES = {
    "studded_leather": "poison",
    "breastplate": "lightning",
    "chain_mail": "cold",
    "splint_armor": "fire",
}


def merge_notes(*chunks: object) -> list[str] | None:
    notes: list[str] = []
    for chunk in chunks:
        if not chunk:
            continue
        if isinstance(chunk, str):
            notes.append(chunk)
            continue
        notes.extend(str(entry) for entry in chunk if entry)
    return notes or None


def format_bonus_map(bonuses: dict[str, int] | None, *, suffix: str = "") -> list[str]:
    if not bonuses:
        return []
    return [f"{name.replace('_', ' ')} +{value}{suffix}".replace(" save", " save") for name, value in bonuses.items()]


def weapon_enchantment_for(base: dict[str, object], rarity: str) -> dict[str, object]:
    if rarity == "common":
        return {}
    if rarity == "uncommon":
        return {
            "enchantment": "Warning",
            "initiative_bonus": 1,
            "notes": [
                "Inspired by official weapons of warning, this weapon grants +1 initiative while equipped.",
            ],
        }
    if rarity == "rare":
        return {
            "enchantment": "Vicious",
            "crit_extra_damage_dice": "2d6",
            "notes": [
                "Inspired by vicious weapons, a critical hit deals an extra 2d6 damage.",
            ],
        }
    if rarity == "epic":
        if bool(base.get("ranged", False)):
            return {
                "enchantment": "Seeking String",
                "extra_damage_dice": "1d8",
                "extra_damage_type": "force",
                "initiative_bonus": 1,
                "notes": [
                    "Inspired by high-tier magical bows such as Oathbow, each hit adds 1d8 force damage.",
                ],
            }
        return {
            "enchantment": "Flame Tongue",
            "extra_damage_dice": "2d6",
            "extra_damage_type": "fire",
            "notes": [
                "Inspired by Flame Tongue, each hit adds 2d6 fire damage.",
            ],
        }
    return {
        "enchantment": "Holy Avenger",
        "extra_damage_dice": "2d6",
        "extra_damage_type": "radiant",
        "crit_extra_damage_dice": "2d8",
        "initiative_bonus": 2,
        "notes": [
            "Inspired by Holy Avenger, each hit adds 2d6 radiant damage and critical hits add another 2d8 radiant.",
        ],
    }


def armor_enchantment_for(base: dict[str, object], rarity: str) -> dict[str, object]:
    if rarity == "common":
        return {}
    if rarity == "uncommon":
        if bool(base.get("stealth_disadvantage", False)):
            return {
                "enchantment": "Mithral Weave",
                "stealth_disadvantage": False,
                "notes": [
                    "Inspired by mithral armor, this suit ignores its normal Stealth disadvantage.",
                ],
            }
        return {
            "enchantment": "Tempered Links",
            "notes": [
                "The magical fittings echo the reliability of official +1 armor.",
            ],
        }
    if rarity == "rare":
        return {
            "enchantment": "Adamantine Ward",
            "crit_immunity": True,
            "notes": [
                "Inspired by adamantine armor, critical hits against you become normal hits.",
            ],
        }
    resistance = ARMOR_RESISTANCE_TYPES.get(str(base["slug"]), "fire")
    if rarity == "epic":
        return {
            "enchantment": f"{resistance.title()} Resistance",
            "damage_resistances": [resistance],
            "notes": [
                f"Inspired by armor of resistance, you resist {resistance} damage while wearing it.",
            ],
        }
    return {
        "enchantment": "Dragonguard Panoply",
        "damage_resistances": [resistance],
        "crit_immunity": True,
        "save_bonuses": {"CON_save": 1},
        "notes": [
            f"Legendary plating grants {resistance} resistance, +1 Constitution saves, and turns critical hits into normal hits.",
        ],
    }


def shield_enchantment_for(rarity: str) -> dict[str, object]:
    if rarity == "common":
        return {}
    if rarity == "uncommon":
        return {
            "enchantment": "Sentinel",
            "initiative_bonus": 1,
            "skill_bonuses": {"Perception": 1},
            "notes": [
                "Inspired by Sentinel Shield, the bearer gains +1 initiative and +1 Perception.",
            ],
        }
    return {
        "enchantment": "Arrow-Catching",
        "initiative_bonus": 1,
        "save_bonuses": {"DEX_save": 1},
        "notes": [
            "Inspired by Arrow-Catching Shield, the bearer gains +1 initiative and +1 Dexterity saves.",
        ],
    }


def gear_enchantment_for(base: dict[str, object], rarity: str) -> dict[str, object]:
    slug = str(base["slug"])
    if slug == "delver_lantern_hood" and rarity == "rare":
        return {
            "enchantment": "Lantern Eye",
            "initiative_bonus": 1,
            "notes": [
                "Built from Phandelver survey gear, the hood's mirrored lamp catches danger a heartbeat early.",
            ],
        }
    if slug == "echostep_boots" and rarity == "rare":
        return {
            "enchantment": "Surestep",
            "initiative_bonus": 1,
            "notes": [
                "These boots were tuned for unstable caverns and help the wearer move before panic turns to a cave-in.",
            ],
        }
    if slug == "forgehand_gauntlets" and rarity == "rare":
        return {
            "enchantment": "Stonegrip",
            "save_bonuses": {"STR_save": 1},
            "notes": [
                "Runes along the knuckles help the wearer brace against shock, weight, and sudden violent force.",
            ],
        }
    if slug == "silent_step_boots":
        return {
            "enchantment": "Elvenkind",
            "stealth_advantage": True,
            "notes": [
                "Inspired by Boots of Elvenkind, these grant advantage on Stealth checks.",
            ],
        }
    if slug == "sigil_anchor_ring":
        bonus = 1 if rarity == "rare" else 2
        return {
            "enchantment": "Mind Anchor",
            "initiative_bonus": bonus,
            "notes": [
                "Etched to resist invasive whisper-magic, this ring helps the wearer act before alien pressure can settle in.",
            ],
        }
    if slug == "watcher_ring":
        bonus = 1 if rarity == "uncommon" else 2 if rarity == "epic" else 1
        return {
            "enchantment": "Protection",
            "initiative_bonus": bonus,
            "save_bonuses": {"WIS_save": 1} if rarity in {"rare", "epic"} else None,
            "notes": [
                "Inspired by rings of protection and warning, this ring sharpens reactions and watchfulness.",
            ],
        }
    if slug == "amber_amulet" and rarity == "rare":
        return {
            "enchantment": "Wound Closure",
            "healing_bonus": 2,
            "notes": [
                "Inspired by Periapt of Wound Closure, healing effects on the wearer restore 2 extra HP in this adaptation.",
            ],
        }
    if slug == "choirward_amulet" and rarity == "rare":
        return {
            "enchantment": "Quiet Mercy",
            "save_bonuses": {"CHA_save": 1},
            "notes": [
                "Designed by priests who expected hostile whispers, this amulet helps the wearer keep both voice and will their own.",
            ],
        }
    return {}


def normalize_item_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def build_weapon_item(base: dict[str, object], rarity: str) -> Item:
    to_hit_bonus, damage_bonus = RARITY_WEAPON_BONUS[rarity]
    magic = weapon_enchantment_for(base, rarity)
    weapon = Weapon(
        name=f"{RARITY_PREFIX[rarity]} {base['name']}",
        damage=base["damage"],
        ability=base["ability"],
        weapon_type=str(base.get("weapon_type", base["slug"])),
        to_hit_bonus=to_hit_bonus + int(base.get("to_hit_bonus", 0)),
        damage_bonus=damage_bonus,
        finesse=bool(base.get("finesse", False)),
        ranged=bool(base.get("ranged", False)),
        hands_required=int(base.get("hands_required", 1)),
        properties=list(base.get("properties", [])),
    )
    name = weapon.name
    return Item(
        item_id=f"{base['slug']}_{rarity}",
        name=name,
        category="weapon",
        item_type=str(base.get("weapon_type", base["slug"])),
        rarity=rarity,
        description=f"{base['description']} Its {RARITY_TITLES[rarity].lower()} craftsmanship improves its battlefield edge.",
        source=str(base.get("source", RARITY_SOURCE[rarity])),
        weight=float(base["weight"]),
        value=rarity_value(int(base["value"]), rarity),
        slot="main_hand",
        properties=list(base.get("properties", [])),
        damage_type=str(base.get("damage_type", "")),
        versatile_damage=base.get("versatile_damage"),
        range_text=base.get("range_text"),
        enchantment=magic.get("enchantment"),
        extra_damage_dice=magic.get("extra_damage_dice"),
        extra_damage_type=str(magic.get("extra_damage_type", "")),
        crit_extra_damage_dice=magic.get("crit_extra_damage_dice"),
        initiative_bonus=int(magic.get("initiative_bonus", 0)),
        notes=merge_notes(magic.get("notes")),
        weapon=weapon,
    )


def build_armor_item(base: dict[str, object], rarity: str) -> Item:
    armor_bonus = RARITY_ARMOR_BONUS[rarity]
    magic = armor_enchantment_for(base, rarity)
    armor = Armor(
        name=f"{RARITY_PREFIX[rarity]} {base['name']}",
        base_ac=int(base["base_ac"]) + armor_bonus,
        armor_type=str(base.get("armor_type", "light")),
        dex_cap=base["dex_cap"],
        heavy=bool(base["heavy"]),
        stealth_disadvantage=bool(magic.get("stealth_disadvantage", base.get("stealth_disadvantage", False))),
    )
    return Item(
        item_id=f"{base['slug']}_{rarity}",
        name=armor.name,
        category="armor",
        item_type=str(base.get("armor_type", "light")),
        rarity=rarity,
        description=f"{base['description']} Its {RARITY_TITLES[rarity].lower()} finish offers stronger protection.",
        source=RARITY_SOURCE[rarity],
        weight=float(base["weight"]),
        value=rarity_value(int(base["value"]), rarity),
        slot="chest",
        properties=["armor", str(base.get("armor_type", "light"))],
        enchantment=magic.get("enchantment"),
        save_bonuses=dict(magic.get("save_bonuses") or {}) or None,
        damage_resistances=list(magic.get("damage_resistances", [])) or None,
        crit_immunity=bool(magic.get("crit_immunity", False)),
        notes=merge_notes(magic.get("notes")),
        armor=armor,
    )


def build_shield_item(base: dict[str, object], rarity: str) -> Item:
    ac_bonus = 0 if rarity == "common" else 1 if rarity in {"uncommon", "rare"} else 2 if rarity == "epic" else 3
    magic = shield_enchantment_for(rarity)
    return Item(
        item_id=f"{base['slug']}_{rarity}",
        name=f"{RARITY_PREFIX[rarity]} {base['name']}",
        category="equipment",
        item_type=str(base["item_type"]),
        rarity=rarity,
        description=f"{base['description']} This {RARITY_TITLES[rarity].lower()} version is built to last.",
        source=RARITY_SOURCE[rarity],
        weight=float(base["weight"]),
        value=rarity_value(int(base["value"]), rarity),
        slot=str(base["slot"]),
        properties=list(base.get("properties", [])),
        shield_bonus=int(base["shield_bonus"]) + ac_bonus,
        enchantment=magic.get("enchantment"),
        initiative_bonus=int(magic.get("initiative_bonus", 0)),
        skill_bonuses=dict(magic.get("skill_bonuses") or {}) or None,
        save_bonuses=dict(magic.get("save_bonuses") or {}) or None,
        notes=merge_notes(magic.get("notes")),
    )


def build_gear_item(base: dict[str, object], rarity: str) -> Item:
    skill_bonuses = dict(base.get("skill_bonuses", {}))
    save_bonuses = dict(base.get("save_bonuses", {}))
    ac_bonus = int(base.get("ac_bonus", 0))
    rarity_scale = RARITY_ORDER.index(rarity)
    magic = gear_enchantment_for(base, rarity)
    if rarity_scale >= 2 and skill_bonuses:
        first_key = next(iter(skill_bonuses))
        skill_bonuses[first_key] += 1
    if rarity_scale >= 3 and save_bonuses:
        first_key = next(iter(save_bonuses))
        save_bonuses[first_key] += 1
    if rarity_scale >= 4:
        ac_bonus += 1
    for key, bonus in dict(magic.get("skill_bonuses") or {}).items():
        skill_bonuses[key] = skill_bonuses.get(key, 0) + bonus
    for key, bonus in dict(magic.get("save_bonuses") or {}).items():
        save_bonuses[key] = save_bonuses.get(key, 0) + bonus
    return Item(
        item_id=f"{base['slug']}_{rarity}",
        name=f"{RARITY_PREFIX[rarity]} {base['name']}",
        category="equipment",
        item_type=str(base["item_type"]),
        rarity=rarity,
        description=f"{base['description']} Frontier rumor says this {RARITY_TITLES[rarity].lower()} piece was hard won.",
        source=str(base.get("source", RARITY_SOURCE[rarity])),
        weight=float(base["weight"]),
        value=rarity_value(int(base["value"]), rarity),
        slot="ring_1" if base["slot"] == "ring" else str(base["slot"]),
        properties=[str(base["item_type"]), str(base["slot"])],
        skill_bonuses=skill_bonuses or None,
        save_bonuses=save_bonuses or None,
        ac_bonus=ac_bonus,
        initiative_bonus=int(magic.get("initiative_bonus", 0)),
        healing_bonus=int(magic.get("healing_bonus", 0)),
        enchantment=magic.get("enchantment"),
        stealth_advantage=bool(magic.get("stealth_advantage", False)),
        notes=merge_notes(magic.get("notes")),
    )


def build_supply_items() -> list[Item]:
    items: list[Item] = []
    for item_id, name, description, weight, value, supply_points, source in SUPPLY_ITEMS:
        items.append(
            Item(
                item_id=item_id,
                name=name,
                category="supply",
                item_type="provisions",
                rarity="common",
                description=description,
                source=source,
                weight=weight,
                value=value,
                supply_points=supply_points,
            )
        )
    return items


def build_consumables() -> list[Item]:
    items: list[Item] = []
    for data in CONSUMABLE_ITEMS:
        payload = dict(data)
        payload["item_type"] = "potion"
        payload["properties"] = ["consumable", payload["rarity"]]
        items.append(Item(category="consumable", **payload))
    for item_id, name, rarity, description, source, heal_dice, heal_bonus, temp_hp, spell_slot_restore, cure_poison in SCROLL_EFFECTS:
        revive_dead = item_id == "scroll_revivify"
        revive_hp = 5 if item_id == "scroll_surge_of_life" else 1 if revive_dead else 0
        value = 200 if item_id == "scroll_revivify" else rarity_value(25, rarity)
        items.append(
            Item(
                item_id=item_id,
                name=name,
                category="scroll",
                item_type="scroll",
                rarity=rarity,
                description=description,
                source=source or RARITY_SOURCE[rarity],
                weight=0.1,
                value=value,
                properties=["scroll", rarity],
                heal_dice=heal_dice,
                heal_bonus=heal_bonus,
                revive_dead=revive_dead,
                temp_hp=temp_hp,
                spell_slot_restore=spell_slot_restore,
                cure_poison=cure_poison,
                revive_hp=revive_hp,
            )
        )
    effect_overrides = {
        "blessed_salve": {"clear_conditions": ["poisoned", "blinded"]},
        "antitoxin_vial": {"clear_conditions": ["poisoned"], "apply_conditions": {"resist_poison": 5}},
        "moonmint_drops": {"clear_conditions": ["deafened", "frightened"]},
        "delvers_amber": {"clear_conditions": ["frightened"]},
        "resonance_tonic": {"clear_conditions": ["reeling"]},
        "potion_heroism": {"apply_conditions": {"blessed": 3}},
        "forge_blessing_elixir": {"apply_conditions": {"blessed": 3}},
        "thoughtward_draught": {"clear_conditions": ["charmed", "frightened"]},
        "fireward_elixir": {"apply_conditions": {"resist_fire": 5}},
        "dust_of_disappearance": {"apply_conditions": {"invisible": 3}},
        "scroll_lesser_restoration": {"clear_conditions": ["blinded", "deafened", "paralyzed", "poisoned"]},
        "scroll_clarity": {"clear_conditions": ["charmed", "frightened", "deafened"]},
        "scroll_echo_step": {"clear_conditions": ["restrained"], "apply_conditions": {"invisible": 2}},
        "scroll_quell_the_deep": {"clear_conditions": ["charmed", "frightened", "incapacitated"]},
        "scroll_forge_shelter": {"apply_conditions": {"blessed": 2}},
        "scroll_guardian_light": {"apply_conditions": {"blessed": 3}},
        "scroll_ember_ward": {"apply_conditions": {"invisible": 2}},
        "scroll_surge_of_life": {"clear_conditions": ["incapacitated", "stunned"]},
        "scroll_battle_psalm": {"apply_conditions": {"blessed": 3}, "clear_conditions": ["frightened"]},
        "scroll_resurgent_flame": {"clear_conditions": ["exhaustion", "petrified", "paralyzed"]},
        "giantfire_balm": {"clear_conditions": ["reeling", "prone", "grappled", "restrained"]},
    }
    for item in items:
        overrides = effect_overrides.get(item.item_id)
        if overrides is None:
            continue
        item.clear_conditions = list(overrides.get("clear_conditions", [])) or None
        item.apply_conditions = dict(overrides.get("apply_conditions", {})) or None
    return items


def build_unique_reward_items() -> list[Item]:
    items: list[Item] = []
    for data in UNIQUE_REWARD_ITEMS:
        payload = dict(data)
        items.append(Item(category="equipment", **payload))
    return items


def build_trinkets() -> list[Item]:
    items: list[Item] = []
    combinations = [(prefix, suffix) for prefix in TRINKET_PREFIXES for suffix in TRINKET_SUFFIXES]
    for rarity in RARITY_ORDER:
        count = TRINKET_RARITY_COUNTS[rarity]
        for index, (prefix, suffix) in enumerate(combinations[:count]):
            theme_name, theme_description = TRINKET_THEMES[index % len(TRINKET_THEMES)]
            name = f"{prefix} {suffix}"
            items.append(
                Item(
                    item_id=f"trinket_{normalize_item_id(name)}_{rarity}",
                    name=f"{name} ({RARITY_TITLES[rarity]})",
                    category="trinket",
                    item_type="trinket",
                    rarity=rarity,
                    description=f"{theme_description} This {RARITY_TITLES[rarity].lower()} trinket is more valuable than practical.",
                    source=RARITY_SOURCE[rarity].replace("relic", f"{theme_name} relic"),
                    weight=0.2,
                    value=rarity_value(8, rarity),
                    properties=["trinket"],
                )
            )
    return items


def build_catalog() -> dict[str, Item]:
    items: list[Item] = []
    for base in WEAPON_BASES:
        for rarity in RARITY_ORDER:
            if base["slug"] not in WEAPON_RARITY_AVAILABILITY[rarity]:
                continue
            items.append(build_weapon_item(base, rarity))
    for base in ARMOR_BASES:
        for rarity in RARITY_ORDER:
            if base["slug"] not in ARMOR_RARITY_AVAILABILITY[rarity]:
                continue
            items.append(build_armor_item(base, rarity))
    for base in SHIELD_BASES:
        for rarity in ("common", "uncommon", "rare"):
            items.append(build_shield_item(base, rarity))
    for base in GEAR_BASES:
        for rarity in RARITY_ORDER:
            if rarity not in base["rarities"]:
                continue
            items.append(build_gear_item(base, rarity))
    items.extend(build_supply_items())
    items.extend(build_consumables())
    items.extend(build_unique_reward_items())
    items.extend(build_trinkets())
    return {item.item_id: item for item in items}


ITEMS = build_catalog()

MERCHANT_STOCKS = {
    "linene_graywind": {
        "longsword_common": 2,
        "battleaxe_common": 2,
        "warhammer_common": 2,
        "shortsword_common": 2,
        "rapier_common": 1,
        "dagger_common": 4,
        "shortbow_common": 2,
        "longbow_common": 1,
        "shield_common": 2,
        "padded_armor_common": 2,
        "leather_armor_common": 2,
        "studded_leather_common": 1,
        "chain_shirt_common": 1,
        "scale_mail_common": 1,
        "iron_cap_common": 2,
        "traveler_hood_common": 2,
        "work_gloves_common": 2,
        "wayfarer_boots_common": 2,
        "reinforced_breeches_common": 2,
        "soldiers_amulet_common": 1,
        "potion_healing": 4,
        "warding_tonic": 3,
        "antitoxin_vial": 3,
        "fireward_elixir": 1,
        "travel_biscuits": 6,
        "frontier_ale": 4,
    },
    "barthen_provisions": {
        "bread_round": 10,
        "dried_fish": 8,
        "goat_cheese": 6,
        "smoked_ham": 4,
        "camp_stew_jar": 3,
        "frontier_ale": 8,
        "red_wine": 3,
        "dried_apple": 6,
        "nut_mix": 6,
        "travel_biscuits": 10,
        "mushroom_skewer": 5,
        "spiced_sausage": 6,
        "honey_cake": 4,
        "root_vegetables": 6,
        "black_tea": 4,
        "herbal_tea": 4,
        "river_clams": 2,
        "spirit_bottle": 2,
        "potion_healing": 3,
        "warding_tonic": 2,
        "antitoxin_vial": 2,
        "moonmint_drops": 4,
        "fireward_elixir": 1,
        "traveler_clothes_common": 2,
        "quarterstaff_common": 2,
        "dagger_common": 4,
    },
}

RARE_MERCHANT_OFFERS = {
    "linene_graywind": [("scroll_revivify", 1, 0.15)],
    "barthen_provisions": [("scroll_revivify", 1, 0.10)],
}

LOOT_TABLES = {
    "goblin": [
        LootEntry("potion_healing", 0.35),
        LootEntry("scroll_revivify", 0.01),
        LootEntry("bread_round", 0.45),
        LootEntry("dagger_common", 0.2),
        LootEntry("leather_armor_common", 0.15),
    ],
    "wolf": [
        LootEntry("dried_fish", 0.4),
        LootEntry("travel_biscuits", 0.25),
    ],
    "worg": [
        LootEntry("smoked_ham", 0.45),
        LootEntry("travel_biscuits", 0.35),
        LootEntry("spiced_sausage", 0.25),
    ],
    "bandit": [
        LootEntry("potion_healing", 0.4),
        LootEntry("scroll_revivify", 0.02),
        LootEntry("frontier_ale", 0.5),
        LootEntry("shortsword_common", 0.2),
        LootEntry("leather_armor_common", 0.25),
        LootEntry("antitoxin_vial", 0.15),
    ],
    "bandit_archer": [
        LootEntry("moonmint_drops", 0.35),
        LootEntry("shortbow_common", 0.25),
        LootEntry("nut_mix", 0.4),
    ],
    "brand_saboteur": [
        LootEntry("antitoxin_vial", 0.25),
        LootEntry("travel_biscuits", 0.35),
        LootEntry("dagger_common", 0.2),
    ],
    "skeletal_sentry": [
        LootEntry("blessed_salve", 0.18),
        LootEntry("mace_common", 0.14),
        LootEntry("soldiers_amulet_common", 0.06),
    ],
    "orc_raider": [
        LootEntry("potion_healing", 0.3),
        LootEntry("battleaxe_common", 0.25),
        LootEntry("shield_common", 0.15),
        LootEntry("salt_pork", 0.45),
        LootEntry("travel_biscuits", 0.35),
    ],
    "orc_bloodchief": [
        LootEntry("greater_healing_draught", 0.6),
        LootEntry("battleaxe_uncommon", 0.3),
        LootEntry("scale_mail_uncommon", 0.18),
        LootEntry("potion_heroism", 0.25),
        LootEntry("spiced_sausage", 1.0, 2, 3),
    ],
    "ogre_brute": [
        LootEntry("camp_stew_jar", 0.5),
        LootEntry("bread_round", 1.0, 1, 3),
        LootEntry("warhammer_common", 0.18),
    ],
    "gravecaller": [
        LootEntry("scroll_clarity", 0.45),
        LootEntry("scroll_lesser_restoration", 0.3),
        LootEntry("amber_amulet_uncommon", 0.18),
        LootEntry("blessed_salve", 0.35),
        LootEntry("black_tea", 0.6),
    ],
    "nothic": [
        LootEntry("watcher_ring_uncommon", 0.18),
        LootEntry("amber_amulet_uncommon", 0.18),
        LootEntry("scroll_arcane_refresh", 0.25),
        LootEntry("red_wine", 0.8),
    ],
    "rukhar": [
        LootEntry("greater_healing_draught", 0.8),
        LootEntry("scroll_revivify", 0.05),
        LootEntry("warhammer_uncommon", 0.35),
        LootEntry("chain_shirt_uncommon", 0.25),
        LootEntry("fireward_elixir", 0.25),
        LootEntry("scroll_guardian_light", 0.35),
        LootEntry("smoked_ham", 1.0, 2, 3),
    ],
    "sereth_vane": [
        LootEntry("potion_healing", 0.65),
        LootEntry("scroll_clarity", 0.35),
        LootEntry("shortsword_uncommon", 0.25),
        LootEntry("red_wine", 0.8),
    ],
    "varyn": [
        LootEntry("superior_healing_elixir", 0.8),
        LootEntry("scroll_revivify", 0.05),
        LootEntry("rapier_rare", 0.35),
        LootEntry("studded_leather_rare", 0.25),
        LootEntry("dust_of_disappearance", 0.2),
        LootEntry("scroll_arcane_refresh", 0.35),
        LootEntry("camp_stew_jar", 1.0, 2, 4),
    ],
    "cult_lookout": [
        LootEntry("potion_healing", 0.25),
        LootEntry("moonmint_drops", 0.35),
        LootEntry("shortbow_uncommon", 0.12),
        LootEntry("leather_armor_uncommon", 0.12),
        LootEntry("dagger_uncommon", 0.08),
        LootEntry("dust_of_disappearance", 0.04),
        LootEntry("travel_biscuits", 0.6, 1, 2),
    ],
    "choir_adept": [
        LootEntry("resonance_tonic", 0.22),
        LootEntry("thoughtward_draught", 0.08),
        LootEntry("choirward_amulet_uncommon", 0.09),
        LootEntry("dagger_uncommon", 0.12),
        LootEntry("scroll_clarity", 0.3),
        LootEntry("scroll_lesser_restoration", 0.18),
        LootEntry("herbal_tea", 0.7, 1, 2),
    ],
    "expedition_reaver": [
        LootEntry("delvers_amber", 0.18),
        LootEntry("battleaxe_uncommon", 0.1),
        LootEntry("shortsword_uncommon", 0.12),
        LootEntry("leather_armor_uncommon", 0.16),
        LootEntry("forgehand_gauntlets_uncommon", 0.07),
        LootEntry("miners_ration_tin", 0.75, 1, 2),
    ],
    "grimlock_tunneler": [
        LootEntry("delvers_amber", 0.12),
        LootEntry("potion_healing", 0.18),
        LootEntry("dagger_common", 0.16),
        LootEntry("leather_armor_common", 0.08),
        LootEntry("mushroom_broth_flask", 0.55, 1, 2),
    ],
    "starblighted_miner": [
        LootEntry("resonance_tonic", 0.16),
        LootEntry("thoughtward_draught", 0.06),
        LootEntry("warhammer_uncommon", 0.12),
        LootEntry("delver_lantern_hood_uncommon", 0.08),
        LootEntry("miners_ration_tin", 0.85, 1, 2),
        LootEntry("mushroom_broth_flask", 0.45),
    ],
    "animated_armor": [
        LootEntry("shield_uncommon", 0.12),
        LootEntry("chain_mail_uncommon", 0.09),
        LootEntry("forgehand_gauntlets_uncommon", 0.1),
        LootEntry("fireward_elixir", 0.14),
        LootEntry("scroll_guardian_light", 0.16),
    ],
    "spectral_foreman": [
        LootEntry("greater_healing_draught", 0.35),
        LootEntry("warhammer_uncommon", 0.22),
        LootEntry("chain_mail_uncommon", 0.14),
        LootEntry("delver_lantern_hood_uncommon", 0.16),
        LootEntry("scroll_guardian_light", 0.22),
        LootEntry("resonance_tonic", 0.2),
    ],
    "blacklake_pincerling": [
        LootEntry("fireward_elixir", 0.2),
        LootEntry("antitoxin_vial", 0.25),
        LootEntry("thoughtward_draught", 0.08),
        LootEntry("sigil_anchor_ring_rare", 0.05),
        LootEntry("studded_leather_uncommon", 0.08),
        LootEntry("mushroom_broth_flask", 0.5),
    ],
    "caldra_voss": [
        LootEntry("superior_healing_elixir", 0.85),
        LootEntry("scroll_revivify", 0.08),
        LootEntry("sigil_anchor_ring_rare", 0.35),
        LootEntry("choirward_amulet_rare", 0.22),
        LootEntry("rapier_rare", 0.18),
        LootEntry("thoughtward_draught", 0.35),
        LootEntry("scroll_ember_ward", 0.28),
        LootEntry("resonance_tonic", 0.5, 1, 2),
    ],
}


LEGACY_ITEM_NAMES = {
    "Healing Potion": "potion_healing",
}

EQUIPMENT_SLOTS = [
    "head",
    "ring_1",
    "ring_2",
    "neck",
    "chest",
    "gloves",
    "boots",
    "main_hand",
    "off_hand",
    "cape",
]

LEGACY_EQUIPMENT_SLOT_ALIASES = {
    "helmet": "head",
    "amulet": "neck",
    "pants": "cape",
}

EQUIPMENT_SLOT_LABELS = {
    "head": "Head",
    "ring_1": "Ring 1",
    "ring_2": "Ring 2",
    "neck": "Neck",
    "chest": "Chest",
    "gloves": "Gloves",
    "boots": "Boots",
    "main_hand": "Main Hand",
    "off_hand": "Off Hand",
    "cape": "Cape",
}


def canonical_equipment_slot(slot: str | None) -> str | None:
    if slot is None:
        return None
    return LEGACY_EQUIPMENT_SLOT_ALIASES.get(slot, slot)


def equipment_slot_label(slot: str) -> str:
    canonical = canonical_equipment_slot(slot) or slot
    return EQUIPMENT_SLOT_LABELS.get(canonical, canonical.replace("_", " ").title())

STARTER_WEAPON_IDS = {
    "Greatsword": "greatsword_common",
    "Longsword": "longsword_common",
    "Rapier": "rapier_common",
    "Mace": "mace_common",
    "Quarterstaff": "quarterstaff_common",
    "Longbow": "longbow_common",
    "Shortsword": "shortsword_common",
}

STARTER_ARMOR_IDS = {
    "Leather Armor": "leather_armor_common",
    "Studded Leather": "studded_leather_common",
    "Scale Mail": "scale_mail_common",
    "Chain Mail": "chain_mail_common",
    "Chain Shirt": "chain_shirt_common",
}


def get_item(item_id: str) -> Item:
    return ITEMS[item_id]


def initial_merchant_stock(merchant_id: str, *, rng: random.Random | None = None) -> dict[str, int]:
    stock = dict(MERCHANT_STOCKS.get(merchant_id, {}))
    if rng is not None:
        for item_id, quantity, chance in RARE_MERCHANT_OFFERS.get(merchant_id, []):
            if rng.random() <= chance:
                stock[item_id] = stock.get(item_id, 0) + quantity
    return stock


def inventory_weight(inventory: dict[str, int]) -> float:
    return sum(ITEMS[item_id].weight * quantity for item_id, quantity in inventory.items() if item_id in ITEMS for quantity in [quantity])


def inventory_supply_points(inventory: dict[str, int]) -> int:
    return sum(ITEMS[item_id].supply_points * quantity for item_id, quantity in inventory.items() if item_id in ITEMS)


def party_carry_capacity(party: list[Character]) -> int:
    return sum(member.ability_scores["STR"] * 15 for member in party if not member.dead)


def roll_loot_for_enemy(enemy: Character, rng: random.Random) -> dict[str, int]:
    drops: dict[str, int] = {}
    for entry in LOOT_TABLES.get(enemy.archetype, []):
        if rng.random() <= entry.chance:
            quantity = rng.randint(entry.minimum, entry.maximum)
            drops[entry.item_id] = drops.get(entry.item_id, 0) + quantity
    return drops


def ability_label_for_weapon(item: Item) -> str:
    if item.weapon is None:
        return ""
    if item.weapon.ability == "FINESSE" or item.weapon.finesse:
        return "Str or Dex"
    if item.weapon.ability == "SPELL":
        return "Spellcasting ability"
    return item.weapon.ability.title()


def item_rules_text(item: Item) -> str:
    rules: list[str] = []
    if item.weapon is not None:
        damage_text = f"{item.weapon.damage} {item.damage_type}".strip()
        if item.versatile_damage:
            damage_text += f" (versatile {item.versatile_damage})"
        if item.range_text:
            damage_text += f", range {item.range_text}"
        rules.append(damage_text)
        rules.append(f"attack stat {ability_label_for_weapon(item)}")
        if item.weapon.to_hit_bonus or item.weapon.damage_bonus:
            rules.append(f"magic +{item.weapon.to_hit_bonus} hit / +{item.weapon.damage_bonus} damage")
    if item.armor is not None:
        armor_bits = [f"AC {item.armor.base_ac}"]
        if item.armor.dex_cap is None and item.item_type != "clothing":
            armor_bits.append("full Dex")
        elif item.armor.dex_cap is not None:
            armor_bits.append(f"Dex cap +{item.armor.dex_cap}")
        if item.armor.stealth_disadvantage:
            armor_bits.append("Stealth disadvantage")
        rules.append(", ".join(armor_bits))
    if item.shield_bonus:
        rules.append(f"+{item.shield_bonus} AC")
    if item.ac_bonus:
        rules.append(f"AC +{item.ac_bonus}")
    if item.heal_dice is not None:
        rules.append(f"heals {item.heal_dice}+{item.heal_bonus}")
    if item.revive_hp:
        if item.revive_dead:
            rules.append(f"resurrects a dead ally at {item.revive_hp} HP when used at camp")
        else:
            rules.append(f"revives at {item.revive_hp} HP")
    if item.temp_hp:
        rules.append(f"{item.temp_hp} temp HP")
    if item.spell_slot_restore:
        rules.append(f"restores {item.spell_slot_restore * 4} MP")
    if item.skill_bonuses:
        rules.append("skills " + ", ".join(f"{name} +{value}" for name, value in item.skill_bonuses.items()))
    if item.save_bonuses:
        rules.append("saves " + ", ".join(f"{name.replace('_', ' ')} +{value}" for name, value in item.save_bonuses.items()))
    if item.attack_bonus:
        rules.append(f"attack +{item.attack_bonus}")
    if item.damage_bonus:
        rules.append(f"damage +{item.damage_bonus}")
    if item.initiative_bonus:
        rules.append(f"initiative +{item.initiative_bonus}")
    if item.spell_attack_bonus:
        rules.append(f"spell attack +{item.spell_attack_bonus}")
    if item.spell_damage_bonus:
        rules.append(f"spell damage +{item.spell_damage_bonus}")
    if item.healing_bonus:
        rules.append(f"received healing +{item.healing_bonus}")
    if item.enchantment:
        rules.append(f"enchantment {item.enchantment}")
    if item.extra_damage_dice:
        rules.append(f"+{item.extra_damage_dice} {item.extra_damage_type} on hit".strip())
    if item.crit_extra_damage_dice:
        rules.append(f"+{item.crit_extra_damage_dice} on crit")
    if item.damage_resistances:
        rules.append("resist " + ", ".join(item.damage_resistances))
    if item.crit_immunity:
        rules.append("critical hits become normal hits")
    if item.stealth_advantage:
        rules.append("advantage on Stealth")
    if item.clear_conditions:
        rules.append("clears " + ", ".join(condition.replace("_", " ") for condition in item.clear_conditions))
    if item.apply_conditions:
        applied = ", ".join(f"{condition.replace('_', ' ')} {duration}r" for condition, duration in item.apply_conditions.items())
        rules.append("applies " + applied)
    if item.notes:
        rules.extend(item.notes)
    return "; ".join(rules)


def format_inventory_line(item_id: str, quantity: int) -> str:
    item = ITEMS[item_id]
    total_weight = item.weight * quantity
    item_name = colorize(item.name, rarity_color(item.rarity))
    rarity_title = colorize(item.rarity_title, rarity_color(item.rarity))
    rules = item_rules_text(item)
    return (
        f"{item_name} x{quantity} [{rarity_title}] "
        f"({item.category}/{item.item_type}, {total_weight:.1f} lb, {item.supply_label()}, {item.value} gp each) "
        + (f"- {rules}" if rules else "")
    ).strip()


def choose_supply_items_to_consume(inventory: dict[str, int], required_points: int) -> tuple[dict[str, int], int]:
    candidates: list[tuple[float, int, str]] = []
    for item_id, quantity in inventory.items():
        item = ITEMS.get(item_id)
        if item is None or item.supply_points <= 0 or quantity <= 0:
            continue
        efficiency = item.value / max(1, item.supply_points)
        candidates.append((efficiency, -item.supply_points, item_id))
    candidates.sort()

    consumed: dict[str, int] = {}
    remaining = required_points
    for _, _, item_id in candidates:
        item = ITEMS[item_id]
        while inventory.get(item_id, 0) > consumed.get(item_id, 0) and remaining > 0:
            consumed[item_id] = consumed.get(item_id, 0) + 1
            remaining -= item.supply_points
            if remaining <= 0:
                return consumed, 0
    return consumed, max(0, remaining)


def write_item_catalog(destination: Path) -> None:
    lines = [
        "# Item Catalog",
        "",
        f"Total items: {len(ITEMS)}",
        "",
        "Each entry lists rarity, category, combat rules, weight, supply value, and where it is obtained.",
        "",
    ]
    for rarity in RARITY_ORDER:
        lines.append(f"## {RARITY_TITLES[rarity]}")
        lines.append("")
        rarity_items = [item for item in ITEMS.values() if item.rarity == rarity]
        rarity_items.sort(key=lambda item: (item.category, item.name))
        for item in rarity_items:
            rules = item_rules_text(item) or "No special combat rules."
            lines.append(
                f"- **{item.name}** (`{item.item_id}`) [{item.category}] "
                f"{item.weight:.1f} lb, {item.supply_label()}, {item.value} gp, type `{item.item_type}`. "
                f"{item.description} Rules: {rules}. Obtain from: {item.source}"
            )
        lines.append("")
    destination.write_text("\n".join(lines), encoding="utf-8")


def starter_item_ids_for_character(character: Character) -> dict[str, str]:
    slots = {slot: None for slot in EQUIPMENT_SLOTS}
    slots["main_hand"] = STARTER_WEAPON_IDS.get(character.weapon.name)
    slots["chest"] = STARTER_ARMOR_IDS.get(character.armor.name) if character.armor is not None else None
    if character.shield:
        slots["off_hand"] = "shield_common"
    return slots
