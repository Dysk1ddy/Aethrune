from __future__ import annotations

from ..data.story.background_openings import BACKGROUND_STARTS, background_start_summary
from ..data.story.lore import BACKGROUND_LORE, CLASS_LORE, RACE_LORE
from ..content import (
    BACKGROUNDS,
    CLASSES,
    PRESET_CHARACTERS,
    RACES,
    STANDARD_ARRAY,
    build_character,
    build_preset_character,
    format_racial_bonuses,
)
from ..models import ABILITY_ORDER, Character, GameState


class CharacterCreationMixin:
    def start_new_game(self) -> None:
        play_music_for_context = getattr(self, "play_music_for_context", None)
        if callable(play_music_for_context):
            play_music_for_context("main_menu")
        self.banner("Character Creation")
        mode = self.choose(
            "Choose how you want to start.",
            [
                "Preset Character",
                "Custom Character",
            ],
            allow_meta=False,
        )
        if mode == 1:
            character = self.choose_preset_character()
        else:
            character = self.create_custom_character()
        self.preview_character(character)
        if not self.confirm("Begin the adventure with this character?"):
            self.say("Let's rebuild them from the start.")
            return self.start_new_game()

        self.begin_adventure(character)

    def create_custom_character(self) -> Character:
        name = self.ask_text("Name your adventurer")
        race = self.choose_named_option("Choose a race", RACES)
        class_name = self.choose_named_option("Choose a class", CLASSES)
        background = self.choose_named_option("Choose a background", BACKGROUNDS)
        base_scores = self.choose_ability_scores()
        class_skills = self.choose_class_skills(race, class_name, background)
        expertise: list[str] = []
        if class_name == "Rogue":
            expertise = self.choose_expertise(race, background, class_skills)
        character = build_character(
            name=name,
            race=race,
            class_name=class_name,
            background=background,
            base_ability_scores=base_scores,
            class_skill_choices=class_skills,
            expertise_choices=expertise,
            inventory={"Healing Potion": 1},
        )
        return character

    def choose_preset_character(self) -> Character:
        class_names = list(PRESET_CHARACTERS)
        while True:
            choice = self.choose("Choose a preset class.", class_names, allow_meta=False)
            selected_class = class_names[choice - 1]
            self.describe_preset_character(selected_class)
            if self.confirm("Lock that preset in?"):
                return build_preset_character(selected_class)

    def describe_preset_character(self, class_name: str) -> None:
        preset = PRESET_CHARACTERS[class_name]
        self.say(
            f"{class_name} preset selected: {preset['name']}, {preset['race']} {class_name} ({preset['background']})."
        )
        self.say(str(preset["description"]))
        abilities = ", ".join(
            f"{ability} {preset['base_ability_scores'][ability]}"
            for ability in ABILITY_ORDER
        )
        self.say(f"Preset abilities: {abilities}")
        self.say(f"Preset class skills: {', '.join(preset['class_skill_choices'])}")
        expertise = list(preset.get("expertise_choices", []))
        if expertise:
            self.say(f"Preset expertise: {', '.join(expertise)}")

    def begin_adventure(self, character: Character) -> None:
        self.state = GameState(
            player=character,
            current_act=1,
            current_scene="background_prologue",
            flags={"act1_started": True, "background_prologue_pending": character.background},
            clues=[],
            journal=[],
            completed_acts=[],
            xp=0,
            gold=20,
            inventory={
                "potion_healing": 2,
                "bread_round": 4,
                "travel_biscuits": 4,
                "dried_fish": 3,
                "goat_cheese": 2,
                "frontier_ale": 2,
                "root_vegetables": 2,
                "antitoxin_vial": 1,
            },
            short_rests_remaining=2,
        )
        self.state.player.inventory.clear()
        self.ensure_state_integrity()
        start_note = BACKGROUND_STARTS.get(character.background, {}).get("arrival_note", "")
        self.add_journal(start_note or f"Your {character.background.lower()} path pulls you toward Neverwinter and the road to Phandalin.")
        self.add_journal("Word reaches you that Mira Thann is quietly gathering capable hands in Neverwinter against a new bandit threat around Phandalin.")

    def choose_named_option(self, title: str, options: dict[str, dict[str, object]]) -> str:
        names = list(options)
        while True:
            if options is RACES or options is CLASSES or options is BACKGROUNDS:
                labels = list(names)
            else:
                labels = [f"{name}: {options[name]['description']}" for name in names]
            choice = self.choose(title, labels, allow_meta=False)
            selected = names[choice - 1]
            self.describe_selection(selected, options[selected], category=title)
            if self.confirm("Lock that in?"):
                return selected

    def describe_selection(self, name: str, details: dict[str, object], *, category: str) -> None:
        if category == "Choose a race":
            bonuses = format_racial_bonuses(name)
            skills = ", ".join(details["skills"]) if details["skills"] else "No racial skill proficiencies"
            features = ", ".join(details["features"]) if details["features"] else "No special racial features"
            self.say(f"{name} selected. Bonuses: {bonuses}. {details['description']}")
            self.say(f"Racial skills: {skills}. Features: {features}.")
            if name in RACE_LORE:
                self.say(RACE_LORE[name]["text"])
            return
        if category == "Choose a class":
            hit_die = details["hit_die"]
            saves = ", ".join(details["saving_throws"])
            self.say(f"{name} selected. {details['description']}")
            self.say(f"Hit die: d{hit_die}. Saving throw proficiencies: {saves}.")
            if name in CLASS_LORE:
                self.say(CLASS_LORE[name]["text"])
            return
        if category == "Choose a background":
            skills = ", ".join(details["skills"])
            proficiencies = ", ".join(details.get("proficiencies", [])) or "No extra proficiencies"
            notes = " | ".join(details["notes"])
            self.say(f"{name} selected. {details['description']}")
            self.say(f"Background skills: {skills}. Extra proficiencies: {proficiencies}.")
            self.say(f"Background perks: {notes}")
            if name in BACKGROUND_LORE:
                self.say(BACKGROUND_LORE[name]["text"])
            return
        self.say(f"{name} selected. {details['description']}")

    def choose_ability_scores(self) -> dict[str, int]:
        method = self.choose(
            "Choose how to assign your ability scores.",
            [
                "Standard array (15, 14, 13, 12, 10, 8)",
                "Point buy (27 points, scores from 8 to 15 before racial bonuses)",
            ],
            allow_meta=False,
        )
        if method == 1:
            remaining = list(STANDARD_ARRAY)
            scores: dict[str, int] = {}
            for ability in ABILITY_ORDER:
                index = self.choose(
                    f"Assign a value to {ability}. Remaining scores: {', '.join(str(value) for value in remaining)}",
                    [str(value) for value in remaining],
                    allow_meta=False,
                )
                scores[ability] = remaining.pop(index - 1)
            return scores

        return self.choose_point_buy_scores()

    def choose_class_skills(self, race: str, class_name: str, background: str) -> list[str]:
        available = list(CLASSES[class_name]["skill_choices"])
        already_known = set(BACKGROUNDS[background]["skills"]) | set(RACES[race]["skills"])
        pool = [skill for skill in available if skill not in already_known]
        if len(pool) < CLASSES[class_name]["skill_picks"]:
            pool = available
        chosen: list[str] = []
        for _ in range(CLASSES[class_name]["skill_picks"]):
            choice = self.choose(
                f"Pick a {class_name} skill proficiency.",
                [skill for skill in pool if skill not in chosen],
                allow_meta=False,
            )
            options = [skill for skill in pool if skill not in chosen]
            chosen.append(options[choice - 1])
        return chosen

    def choose_expertise(self, race: str, background: str, class_skills: list[str]) -> list[str]:
        base_skills = set(BACKGROUNDS[background]["skills"]) | set(RACES[race]["skills"]) | set(class_skills)
        pool = sorted(base_skills)
        chosen: list[str] = []
        for _ in range(2):
            choice = self.choose(
                "Choose a skill for rogue Expertise.",
                [skill for skill in pool if skill not in chosen],
                allow_meta=False,
            )
            options = [skill for skill in pool if skill not in chosen]
            chosen.append(options[choice - 1])
        return chosen

    def preview_character(self, character: Character) -> None:
        self.banner("Character Summary")
        self.say(
            f"{character.name}, {character.race} {character.class_name} ({character.background})\n"
            f"HP {character.current_hp}/{character.max_hp}, AC {character.armor_class}, weapon: {character.weapon.name}"
        )
        abilities = ", ".join(f"{ability} {character.ability_scores[ability]}" for ability in ABILITY_ORDER)
        self.say(f"Abilities: {abilities}")
        self.say(f"Skills: {', '.join(character.skill_proficiencies)}")
        if character.skill_expertise:
            self.say(f"Expertise: {', '.join(character.skill_expertise)}")
        if character.bonus_proficiencies:
            self.say(f"Background proficiencies: {', '.join(character.bonus_proficiencies)}")
        self.say(
            f"Features: {', '.join(self.format_feature_name(feature) for feature in character.features) if character.features else 'None'}"
        )
        self.say(f"Kit notes: {' | '.join(character.notes)}")
        self.say(f"Starting point: {background_start_summary(character.background)}")
