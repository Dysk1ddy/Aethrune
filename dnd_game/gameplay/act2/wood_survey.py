from __future__ import annotations

from ...content import create_enemy
from ..encounter import Encounter


class StoryAct2WoodSurveyMixin:
    WOOD_SURVEY_TRACK_LIMIT = 4
    WOOD_SURVEY_INTEGRITY_LABELS = ("Shredded", "Compromised", "Patchable", "Reliable", "Clean")
    WOOD_SURVEY_COVER_LABELS = ("Broken", "Thin", "Contested", "Shielded", "Sealed")

    def _wood_survey_delayed(self) -> bool:
        assert self.state is not None
        return self.state.flags.get("act2_neglected_lead") == "woodland_survey_cleared"

    def _wood_survey_track_value(self, flag_name: str, default: int) -> int:
        assert self.state is not None
        value = self.state.flags.get(flag_name, default)
        if isinstance(value, bool) or not isinstance(value, int):
            value = default
        return max(0, min(self.WOOD_SURVEY_TRACK_LIMIT, value))

    def _wood_survey_set_tracks(self, *, integrity: int | None = None, cover: int | None = None) -> None:
        assert self.state is not None
        if integrity is not None:
            self.state.flags["woodland_survey_integrity"] = max(0, min(self.WOOD_SURVEY_TRACK_LIMIT, integrity))
        if cover is not None:
            self.state.flags["woodland_sabotage_cover"] = max(0, min(self.WOOD_SURVEY_TRACK_LIMIT, cover))

    def _wood_survey_integrity(self) -> int:
        return self._wood_survey_track_value("woodland_survey_integrity", 2)

    def _wood_survey_cover(self) -> int:
        return self._wood_survey_track_value("woodland_sabotage_cover", 2)

    def _wood_survey_shift_integrity(self, delta: int) -> int:
        updated = self._wood_survey_integrity() + delta
        self._wood_survey_set_tracks(integrity=updated)
        return self._wood_survey_integrity()

    def _wood_survey_shift_cover(self, delta: int) -> int:
        updated = self._wood_survey_cover() + delta
        self._wood_survey_set_tracks(cover=updated)
        return self._wood_survey_cover()

    def _wood_survey_track_line(self) -> str:
        integrity = self._wood_survey_integrity()
        cover = self._wood_survey_cover()
        return (
            f"Survey Integrity: {self.WOOD_SURVEY_INTEGRITY_LABELS[integrity]} ({integrity}/4) | "
            f"Sabotage Cover: {self.WOOD_SURVEY_COVER_LABELS[cover]} ({cover}/4)"
        )

    def _wood_survey_show_tracks(self, reason: str | None = None) -> None:
        prefix = "Wood Survey Tracks"
        if reason:
            prefix = f"{prefix} - {reason}"
        self.say(f"{prefix}: {self._wood_survey_track_line()}")

    def scene_neverwinter_wood_survey_camp(self) -> None:
        assert self.state is not None
        delayed = self._wood_survey_delayed()
        if not self.has_quest("cut_woodland_saboteurs"):
            self.grant_quest("cut_woodland_saboteurs")

        starting_integrity = 1 if delayed else 2
        starting_cover = 3 if delayed else 2
        if self.state.flags.get("kaelis_hidden_trail"):
            starting_integrity += 1
            starting_cover -= 1
        self._wood_survey_set_tracks(integrity=starting_integrity, cover=starting_cover)

        self.banner("Greywake Survey Camp")
        self.say(
            "The camp is not destroyed so much as edited. Survey posts are cut low, stores are spoiled just enough to matter, "
            "and the raiders still close enough to smell the damage they made. This time the evidence is breathing: two wounded carriers, "
            "a shaking apprentice cartographer, and a guide who saw the false route markers go in before the knives came out.",
            typed=True,
        )
        if delayed:
            self.say(
                "Because you let this line wait until after sabotage night, the saboteurs are no longer just cutting posts. "
                "They are cleaning up living witnesses and burning the logistics that tied them to Iron Hollow's riot."
            )
        self._wood_survey_show_tracks("arrival")
        self.run_dialogue_input("act2_wood_entry")

        choice = self.scenario_choice(
            "How do you break the sabotage line?",
            [
                self.skill_tag("STEALTH", self.action_option("Circle the camp, cut the signal runner, and keep the witnesses alive.")),
                self.quoted_option("INTIMIDATION", "Drop your blades and explain who hired the false routework."),
                self.skill_tag("SURVIVAL", self.action_option("Read the cut survey lines and expose the hidden fallback trail.")),
            ],
            allow_meta=False,
        )
        hero_bonus = 0
        if self.state.flags.get("kaelis_hidden_trail"):
            hero_bonus += 1
            self.say("Kaelis's hidden trail turns the approach into something closer to a controlled cut than a blind entry.")

        if choice == 1:
            self.player_action("Circle the camp, cut the signal runner, and keep the witnesses alive.")
            if self.skill_check(self.state.player, "Stealth", 13, context="to get inside the raiders' outer watch before the witnesses are moved"):
                self.state.flags["woodland_spy_taken"] = True
                self.state.flags["woodland_witnesses_saved"] = True
                self._wood_survey_shift_cover(-2)
                self._wood_survey_shift_integrity(1)
                hero_bonus += 2
                self.say("The signal runner goes down with the warning still in his teeth, and the living witnesses stay alive enough to contradict the false map.")
            else:
                self._wood_survey_shift_cover(1)
                self.say("You reach the outer watch, but one runner vanishes into the brush with enough noise to thicken the cover story.")
        elif choice == 2:
            self.player_speaker("Drop your blades and explain who hired the false routework.")
            if self.skill_check(self.state.player, "Intimidation", 13, context="to crack the saboteurs before steel is drawn"):
                self.state.flags["woodland_ringleader_broken"] = True
                self.state.flags["woodland_logistics_named"] = True
                self._wood_survey_shift_cover(-2)
                hero_bonus += 1
                self.say("The ringleader flinches at the word hired. Names spill out as logistics first, ideology second: wagons, cover payments, dead drops, false route stakes.")
            else:
                self._wood_survey_shift_integrity(-1)
                self.say("The threat lands, but badly. The saboteurs start cutting packs loose and making the camp look like simple bandit work.")
        else:
            self.player_action("Read the cut survey lines and expose the hidden fallback trail.")
            if self.skill_check(self.state.player, "Survival", 13, context="to turn the damaged survey route against the saboteurs"):
                self.state.flags["woodland_fallback_trail_found"] = True
                self.state.flags["woodland_false_routework_exposed"] = True
                self._wood_survey_shift_integrity(2)
                self._wood_survey_shift_cover(-1)
                hero_bonus += 2
                self.say("The false routework is too neat where honest panic would be messy. You find the fallback trail by reading what the saboteurs overcorrected.")
            else:
                self._wood_survey_shift_integrity(-1)
                self.say("The damaged stakes tell a story, but not cleanly enough. You find the fight, not the whole lie behind it.")
        self._wood_survey_show_tracks("after your opening move")

        enemies = [create_enemy("expedition_reaver"), create_enemy("false_map_skirmisher")]
        if delayed:
            enemies.append(self.act2_pick_enemy(("claimbinder_notary", "choir_cartographer", "memory_taker_adept")))
        elif len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("claimbinder_notary", "cult_lookout")))
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "false_map_skirmisher", "expedition_reaver")))

        cover = self._wood_survey_cover()
        integrity = self._wood_survey_integrity()
        if cover >= 3:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "false_map_skirmisher"), name="Cover-Story Runner"))
            hero_bonus -= 1
            self.say("The sabotage cover is still strong enough to put another runner in motion before steel settles the question.")
        if integrity >= 3:
            hero_bonus += 1
            self.apply_status(enemies[0], "reeling", 1, source="your clean read of the false routework")
        if cover <= 1 and enemies:
            self.apply_status(enemies[0], "frightened", 1, source="their cover story collapsing in front of living witnesses")
        if self.state.flags.get("woodland_fallback_trail_found"):
            enemies[0].current_hp = max(1, enemies[0].current_hp - 4)

        outcome = self.run_encounter(
            Encounter(
                title="Woodland Saboteurs",
                description=(
                    "Rival expedition muscle and Quiet Choir lookouts try to keep living witnesses, logistics ledgers, "
                    "and false routework from becoming one clear story."
                ),
                enemies=enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=13,
                hero_initiative_bonus=hero_bonus,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The woodland sabotage line stays alive and the route back to Iron Hollow turns dangerous again.")
            return
        if outcome == "fled":
            self.state.current_scene = "act2_expedition_hub"
            self.say("You break contact and return to town with the wood still contested.")
            return

        self.state.flags["woodland_survey_cleared"] = True
        if self._wood_survey_integrity() >= 3:
            self.state.flags["woodland_survey_integrity_high"] = True
        if self._wood_survey_cover() <= 1:
            self.state.flags["woodland_sabotage_cover_broken"] = True
        if self.state.flags.get("woodland_witnesses_saved") or self._wood_survey_integrity() >= 3:
            self.state.flags["woodland_living_witnesses_secured"] = True

        self.reward_party(xp=40, gold=12, reason="securing the woodland survey route")
        if delayed:
            self.say(
                "You break the saboteur line at last, but not before admitting to yourself that this victory is corrective, not preventative. "
                "The living witnesses can still speak; they just speak from bruises now."
            )
            self.act2_shift_metric(
                "act2_route_control",
                1,
                "you finally stop the woodland cuts from feeding new bad information into the claims race",
            )
            if self.state.flags.get("woodland_living_witnesses_secured"):
                self.act2_shift_metric(
                    "act2_town_stability",
                    1,
                    "surviving woodland witnesses give Iron Hollow a human account instead of another rumor",
                )
        else:
            self.act2_shift_metric(
                "act2_route_control",
                2,
                "the survey line can finally breathe without being edited by hostile hands",
            )
            self.act2_shift_metric(
                "act2_town_stability",
                1,
                "stopping the woodland saboteurs keeps more fires and lies from reaching town",
            )
            if self.state.flags.get("woodland_sabotage_cover_broken"):
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    -1,
                    "the cover story breaks in front of living witnesses before the Choir can turn it into doctrine",
                )
        self._wood_survey_show_tracks("secured")
        self.state.current_scene = "act2_expedition_hub"
