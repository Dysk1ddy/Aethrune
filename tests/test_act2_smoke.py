from __future__ import annotations

import random
import unittest

import pytest

from dnd_game.content import (
    build_character,
    create_bryn_underbough,
    create_irielle_ashwake,
    create_nim_ardentglass,
    create_rhogar_valeguard,
    create_tolan_ironshield,
)
from dnd_game.drafts.map_system import ACT2_ENEMY_DRIVEN_MAP
from dnd_game.game import Encounter, TextDnDGame
from dnd_game.models import GameState
from dnd_game.ui.colors import strip_ansi


pytestmark = pytest.mark.smoke


def make_act2_player():
    return build_character(
        name="Vale",
        race="Human",
        class_name="Fighter",
        background="Soldier",
        base_ability_scores={"STR": 15, "DEX": 14, "CON": 13, "INT": 8, "WIS": 12, "CHA": 10},
        class_skill_choices=["Athletics", "Survival"],
    )


class Act2SmokeTests(unittest.TestCase):
    """Fast, high-signal Act 2 route-flow checks for daily content iteration."""

    def plain_output(self, lines: list[str]) -> str:
        return strip_ansi("\n".join(lines))

    def option_index_containing(self, options: list[str], needle: str) -> int:
        plain_options = [strip_ansi(option) for option in options]
        for index, option in enumerate(plain_options, start=1):
            if needle in option:
                return index
        raise AssertionError(f"Could not find option containing {needle!r} in {plain_options!r}")

    def make_game(
        self,
        *,
        seed: int,
        current_scene: str,
        flags: dict[str, object] | None = None,
        companions: list | None = None,
        output_lines: list[str] | None = None,
    ) -> TextDnDGame:
        output_fn = (output_lines.append if output_lines is not None else (lambda _: None))
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=output_fn, rng=random.Random(seed))
        game.state = GameState(
            player=make_act2_player(),
            companions=list(companions or []),
            current_act=2,
            current_scene=current_scene,
            flags=dict(flags or {}),
        )
        return game

    def make_route_game(
        self,
        *,
        seed: int,
        current_scene: str,
        flags: dict[str, object],
        companions: list | None = None,
        output_lines: list[str] | None = None,
    ) -> tuple[TextDnDGame, list[Encounter]]:
        encounters: list[Encounter] = []
        game = self.make_game(
            seed=seed,
            current_scene=current_scene,
            flags=flags,
            companions=companions,
            output_lines=output_lines,
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]
        return game, encounters

    def test_act2_start_smoke_lands_in_claims_council(self) -> None:
        game = TextDnDGame(input_fn=lambda _: "1", output_fn=lambda _: None, rng=random.Random(94001))
        game.state = GameState(
            player=make_act2_player(),
            current_scene="act1_complete",
            flags={"blackwake_completed": True},
        )

        game.start_act2_scaffold()

        assert game.state is not None
        self.assertEqual(game.state.current_act, 2)
        self.assertEqual(game.state.current_scene, "act2_claims_council")
        self.assertTrue(game.state.flags["act2_started"])
        self.assertTrue(game.state.flags["act2_scaffold_enabled"])

    def test_act2_claims_council_smoke_reaches_hub_with_sponsor(self) -> None:
        log: list[str] = []
        answers = iter(["1", "1"])
        game = TextDnDGame(input_fn=lambda _: next(answers), output_fn=log.append, rng=random.Random(94002))
        game.state = GameState(
            player=make_act2_player(),
            companions=[create_rhogar_valeguard(), create_tolan_ironshield(), create_bryn_underbough()],
            current_act=2,
            current_scene="act2_claims_council",
            flags={"act2_started": True, "act2_town_stability": 3, "act2_route_control": 3, "act2_whisper_pressure": 2},
        )
        game.skill_check = lambda actor, skill, dc, context: False  # type: ignore[method-assign]

        game.scene_act2_claims_council()

        assert game.state is not None
        rendered = self.plain_output(log)
        self.assertIn("If this room wants a claim, make it name who the claim protects.", rendered)
        self.assertEqual(game.state.flags["act2_sponsor"], "exchange")
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")

    def test_act2_route_map_smoke_unlocks_sabotage_after_two_early_leads(self) -> None:
        log: list[str] = []
        game = self.make_game(
            seed=94003,
            current_scene="act2_expedition_hub",
            output_lines=log,
            flags={
                "act2_started": True,
                "agatha_truth_secured": True,
                "woodland_survey_cleared": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )

        game.render_act2_overworld_map(force=True)

        rendered = self.plain_output(log)
        self.assertIn("Trigger sabotage night", rendered)
        self.assertIn("Sabotage Night", rendered)

    def test_neverwinter_wood_smoke_breaks_cover_with_survey_integrity_track(self) -> None:
        log: list[str] = []
        game, encounters = self.make_route_game(
            seed=940031,
            current_scene="neverwinter_wood_survey_camp",
            output_lines=log,
            flags={
                "act2_started": True,
                "act2_town_stability": 3,
                "act2_route_control": 2,
                "act2_whisper_pressure": 2,
            },
        )

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "How do you break the sabotage line?":
                return self.option_index_containing(options, "keep the witnesses alive")
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_neverwinter_wood_survey_camp()

        assert game.state is not None
        rendered = self.plain_output(log)
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["woodland_survey_cleared"])
        self.assertTrue(game.state.flags["woodland_living_witnesses_secured"])
        self.assertTrue(game.state.flags["woodland_sabotage_cover_broken"])
        self.assertEqual(game.state.flags["woodland_survey_integrity"], 3)
        self.assertEqual(game.state.flags["woodland_sabotage_cover"], 0)
        self.assertIn("Survey Integrity", rendered)
        self.assertIn("Sabotage Cover", rendered)
        self.assertEqual([encounter.title for encounter in encounters], ["Woodland Saboteurs"])
        self.assertTrue(encounters[0].allow_post_combat_random_encounter)

    def test_neverwinter_wood_delayed_route_salvages_living_witnesses_without_blocking_progress(self) -> None:
        log: list[str] = []
        game, encounters = self.make_route_game(
            seed=940032,
            current_scene="neverwinter_wood_survey_camp",
            output_lines=log,
            flags={
                "act2_started": True,
                "iron_hollow_sabotage_resolved": True,
                "act2_neglected_lead": "woodland_survey_cleared",
                "act2_town_stability": 2,
                "act2_route_control": 2,
                "act2_whisper_pressure": 3,
            },
        )

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "How do you break the sabotage line?":
                return self.option_index_containing(options, "hidden fallback trail")
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_neverwinter_wood_survey_camp()

        assert game.state is not None
        rendered = self.plain_output(log)
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["woodland_survey_cleared"])
        self.assertTrue(game.state.flags["woodland_false_routework_exposed"])
        self.assertTrue(game.state.flags["woodland_living_witnesses_secured"])
        self.assertEqual(game.state.flags["woodland_survey_integrity"], 3)
        self.assertEqual(game.state.flags["woodland_sabotage_cover"], 2)
        self.assertEqual(game.state.flags["act2_route_control"], 3)
        self.assertEqual(game.state.flags["act2_town_stability"], 3)
        self.assertIn("corrective, not preventative", rendered)
        self.assertGreaterEqual(len(encounters[0].enemies), 3)

    def test_stonehollow_dig_smoke_route_reaches_hub(self) -> None:
        game, encounters = self.make_route_game(
            seed=94004,
            current_scene="stonehollow_dig",
            flags={
                "act2_started": True,
                "act2_town_stability": 3,
                "act2_route_control": 2,
                "act2_whisper_pressure": 2,
            },
        )

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "What do you do from Slime Cut?":
                return self.option_index_containing(options, "Scholar Pocket")
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_stonehollow_dig()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["stonehollow_dig_cleared"])
        self.assertTrue(game.state.flags["stonehollow_scholars_found"])
        self.assertEqual([encounter.title for encounter in encounters], ["Stonehollow Slime Cut", "Stonehollow Breakout"])

    def test_stonehollow_delayed_route_salvages_scholars_without_blocking_progress(self) -> None:
        log: list[str] = []
        game, encounters = self.make_route_game(
            seed=940042,
            current_scene="stonehollow_dig",
            output_lines=log,
            flags={
                "act2_started": True,
                "iron_hollow_sabotage_resolved": True,
                "act2_neglected_lead": "stonehollow_dig_cleared",
                "act2_town_stability": 2,
                "act2_route_control": 2,
                "act2_whisper_pressure": 3,
            },
        )

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "What do you do from Slime Cut?":
                return self.option_index_containing(options, "Scholar Pocket")
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_stonehollow_dig()

        assert game.state is not None
        rendered = self.plain_output(log)
        nim = game.find_companion("Nim Ardentglass")
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["stonehollow_dig_cleared"])
        self.assertTrue(game.state.flags["stonehollow_scholars_found"])
        self.assertEqual(game.state.flags["act2_route_control"], 3)
        self.assertIn("Coming here late means", rendered)
        self.assertIsNotNone(nim)
        self.assertEqual(nim.disposition, -1)
        self.assertEqual([encounter.title for encounter in encounters], ["Stonehollow Slime Cut", "Stonehollow Breakout"])
        self.assertGreaterEqual(len(encounters[-1].enemies), 2)

    def test_glasswater_intake_smoke_route_reaches_hub(self) -> None:
        game, encounters = self.make_route_game(
            seed=940041,
            current_scene="glasswater_intake",
            flags={
                "act2_started": True,
                "agatha_truth_secured": True,
                "act2_town_stability": 3,
                "act2_route_control": 2,
                "act2_whisper_pressure": 2,
            },
        )

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "What do you do from Gatehouse Winch?":
                return self.option_index_containing(options, "Valve Hall")
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_glasswater_intake()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["glasswater_intake_cleared"])
        self.assertTrue(game.state.flags["glasswater_headgate_purged"])
        self.assertEqual(game.state.inventory.get("thoughtward_draught"), 1)
        self.assertEqual(game.state.inventory.get("scroll_clarity"), 1)
        self.assertEqual(
            [encounter.title for encounter in encounters],
            ["Glasswater Intake Yard", "Glasswater Valve Hall", "Glasswater Filter Beds", "Brother Merik Sorn"],
        )

    def test_siltlock_counting_house_smoke_route_reaches_hub_and_sets_payoffs(self) -> None:
        game, encounters = self.make_route_game(
            seed=940043,
            current_scene="siltlock_counting_house",
            flags={
                "act2_started": True,
                "agatha_truth_secured": True,
                "act2_sponsor": "exchange",
                "act2_town_stability": 3,
                "act2_route_control": 2,
                "act2_whisper_pressure": 2,
            },
        )

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "What do you do from Public Counter?":
                return self.option_index_containing(options, "Permit Stacks")
            if prompt == "What do you do from Permit Stacks?":
                return self.option_index_containing(options, "Back Till Cage")
            if prompt == "What do you do from Back Till Cage?":
                return self.option_index_containing(options, "Sluice Bell Alcove")
            if prompt == "What do you do from Sluice Bell Alcove?":
                return self.option_index_containing(options, "Auditor's Stair")
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_siltlock_counting_house()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["siltlock_counting_house_cleared"])
        self.assertTrue(game.state.flags["glasswater_permit_fraud_exposed"])
        self.assertTrue(game.state.flags["sabotage_supply_watch_warned"])
        self.assertTrue(game.state.flags["act2_sponsor_pressure_named"])
        self.assertEqual([encounter.title for encounter in encounters], ["Siltlock Auditor's Stair"])

    def test_conyberry_agatha_smoke_route_reaches_hub_with_clean_warning(self) -> None:
        game = self.make_game(
            seed=940042,
            current_scene="conyberry_agatha",
            flags={
                "act2_started": True,
                "act2_town_stability": 3,
                "act2_route_control": 2,
                "act2_whisper_pressure": 2,
            },
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "How do you answer the frightened road before the circuit answers it for you?":
                return self.option_index_containing(options, "Steady the whole group")
            if prompt == "How do you read the waymarker cairn before the circuit closes around it?":
                return self.option_index_containing(options, "chapel line first")
            if prompt == "How do you answer the Chapel of Lamps?":
                return self.option_index_containing(options, "Relight the chapel")
            if prompt == "Which second part of the circuit do you answer before the Pale Witness speaks?":
                return self.option_index_containing(options, "Grave Ring")
            if prompt == "How do you read the Grave Ring?":
                return self.option_index_containing(options, "Name the dead aloud")
            if prompt == "How do you approach the Pale Witness's truth?":
                return self.option_index_containing(options, "We are not here to plunder your dead")
            if prompt == "How do you carry the Pale Witness's warning out of Hushfen?":
                return self.option_index_containing(options, "Share it publicly")
            raise AssertionError(f"Unexpected prompt: {prompt!r}")

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_conyberry_agatha()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["conyberry_pilgrims_steadied"])
        self.assertTrue(game.state.flags["conyberry_cairn_ward_read"])
        self.assertTrue(game.state.flags["conyberry_chapel_relit"])
        self.assertTrue(game.state.flags["conyberry_dead_named"])
        self.assertEqual(game.state.flags["conyberry_second_site"], "grave")
        self.assertEqual(game.state.flags["conyberry_warning_exit_choice"], "public")
        self.assertTrue(game.state.flags["agatha_truth_secured"])
        self.assertTrue(game.state.flags["agatha_truth_clear"])

    def test_conyberry_agatha_delayed_smoke_route_reaches_hub_with_bruised_warning(self) -> None:
        game = self.make_game(
            seed=940043,
            current_scene="conyberry_agatha",
            flags={
                "act2_started": True,
                "iron_hollow_sabotage_resolved": True,
                "act2_neglected_lead": "agatha_truth_secured",
                "agatha_circuit_defiled": True,
                "act2_town_stability": 3,
                "act2_route_control": 2,
                "act2_whisper_pressure": 2,
            },
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "How do you answer the frightened road before the circuit answers it for you?":
                return self.option_index_containing(options, "Follow the one story")
            if prompt == "How do you read the waymarker cairn before the circuit closes around it?":
                return self.option_index_containing(options, "tampered line first")
            if prompt == "What do you do with the defiled sigil?":
                return self.option_index_containing(options, "Break the sigil")
            if prompt == "Which second part of the circuit do you answer before the Pale Witness speaks?":
                return self.option_index_containing(options, "Chapel of Lamps")
            if prompt == "How do you answer the Chapel of Lamps?":
                return self.option_index_containing(options, "Relight the chapel")
            if prompt == "How do you approach the Pale Witness's truth?":
                return self.option_index_containing(options, "what vow was broken")
            if prompt == "How do you carry the Pale Witness's warning out of Hushfen?":
                return self.option_index_containing(options, "Bind the warning")
            raise AssertionError(f"Unexpected prompt: {prompt!r}")

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_conyberry_agatha()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["agatha_truth_secured"])
        self.assertFalse(game.state.flags["agatha_truth_clear"])
        self.assertTrue(game.state.flags["agatha_warning_bound"])
        self.assertEqual(game.state.flags["conyberry_second_site"], "chapel")

    def test_conyberry_route_consequences_smoke_carries_from_sabotage_to_black_lake(self) -> None:
        log: list[str] = []
        encounters: list[Encounter] = []
        game = self.make_game(
            seed=940044,
            current_scene="conyberry_agatha",
            output_lines=log,
            flags={
                "act2_started": True,
                "woodland_survey_cleared": True,
                "stonehollow_dig_cleared": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 3,
            },
        )
        game.skill_check = lambda actor, skill, dc, context: True  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: encounters.append(encounter) or "victory"  # type: ignore[method-assign]

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "How do you answer the frightened road before the circuit answers it for you?":
                return self.option_index_containing(options, "Steady the whole group")
            if prompt == "How do you read the waymarker cairn before the circuit closes around it?":
                return self.option_index_containing(options, "chapel line first")
            if prompt == "How do you answer the Chapel of Lamps?":
                return self.option_index_containing(options, "Relight the chapel")
            if prompt == "Which second part of the circuit do you answer before the Pale Witness speaks?":
                return self.option_index_containing(options, "Grave Ring")
            if prompt == "How do you read the Grave Ring?":
                return self.option_index_containing(options, "Name the dead aloud")
            if prompt == "How do you approach the Pale Witness's truth?":
                return self.option_index_containing(options, "We are not here to plunder your dead")
            if prompt == "How do you carry the Pale Witness's warning out of Hushfen?":
                return self.option_index_containing(options, "Share it publicly")
            if prompt == "What do you protect first when the sabotage breaks wide open?":
                return self.option_index_containing(options, "shrine lane")
            if prompt == "What do you read first on the crossing?":
                return self.option_index_containing(options, "Test the anchor pull")
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_conyberry_agatha()
        game.state.current_scene = "act2_midpoint_convergence"
        game.scene_act2_midpoint_convergence()
        game.state.flags["wave_echo_outer_cleared"] = True
        game.state.current_scene = "black_lake_causeway"
        dungeon = ACT2_ENEMY_DRIVEN_MAP.dungeons["black_lake_crossing"]
        game._black_lake_causeway_lip(dungeon, dungeon.rooms["causeway_lip"])

        assert game.state is not None
        rendered = self.plain_output(log)
        self.assertTrue(game.state.flags["conyberry_chapel_relit"])
        self.assertTrue(game.state.flags["conyberry_chapel_sabotage_payoff"])
        self.assertTrue(game.state.flags["black_lake_conyberry_lamp_guidance"])
        self.assertTrue(game.state.flags["black_lake_shrine_route_marked"])
        self.assertTrue(game.state.flags["conyberry_chapel_pressure_payoff_applied"])
        self.assertNotIn("black_lake_conyberry_pressure_payoff", game.state.flags)
        self.assertEqual(game.state.flags["act2_whisper_pressure"], 0)
        self.assertEqual(encounters[0].title, "Midpoint: Sabotage Night")
        self.assertIn("Pilgrims from Hushfen arrive with lamp discipline", rendered)
        self.assertIn("The lamp discipline you restored at Hushfen catches at the Blackglass shrine", rendered)

    def test_midpoint_convergence_smoke_records_pattern_and_returns_to_hub(self) -> None:
        game = self.make_game(
            seed=94005,
            current_scene="act2_midpoint_convergence",
            flags={
                "act2_started": True,
                "agatha_truth_secured": True,
                "stonehollow_dig_cleared": True,
                "woodland_survey_cleared": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )
        game.scenario_choice = lambda prompt, options, **kwargs: 2  # type: ignore[method-assign]
        game.skill_check = lambda actor, skill, dc, context: False  # type: ignore[method-assign]
        game.run_encounter = lambda encounter: "victory"  # type: ignore[method-assign]

        game.scene_act2_midpoint_convergence()

        assert game.state is not None
        self.assertTrue(game.state.flags["pattern_preserves_people"])
        self.assertTrue(game.state.flags["iron_hollow_sabotage_resolved"])
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")

    def test_act2_hub_smoke_warns_before_first_late_route_choice(self) -> None:
        log: list[str] = []
        confirmations = 0
        game = self.make_game(
            seed=94006,
            current_scene="act2_expedition_hub",
            output_lines=log,
            flags={
                "act2_started": True,
                "agatha_truth_secured": True,
                "woodland_survey_cleared": True,
                "stonehollow_dig_cleared": True,
                "iron_hollow_sabotage_resolved": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            nonlocal confirmations
            plain_options = [strip_ansi(option) for option in options]
            if prompt == "Where do you push next?":
                return self.option_index_containing(options, "Broken Prospect")
            if prompt == "This first late-route choice will change the other route. Proceed?":
                confirmations += 1
                return 2 if confirmations == 1 else 1
            raise AssertionError(f"Unexpected prompt: {prompt!r}")

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_act2_expedition_hub()

        assert game.state is not None
        rendered = self.plain_output(log)
        self.assertEqual(confirmations, 2)
        self.assertIn("Choosing Broken Prospect first commits the expedition to the cleaner cave approach", rendered)
        self.assertEqual(game.state.current_scene, "broken_prospect")
        self.assertNotIn("act2_first_late_route", game.state.flags)

    def test_south_adit_smoke_route_reaches_hub_and_recruits_irielle(self) -> None:
        log: list[str] = []
        game, encounters = self.make_route_game(
            seed=94007,
            current_scene="south_adit",
            output_lines=log,
            flags={
                "act2_started": True,
                "iron_hollow_sabotage_resolved": True,
                "act2_first_late_route": "broken_prospect",
                "act2_captive_outcome": "captives_endangered",
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "What do you do from South Adit Mouth?":
                return self.option_index_containing(options, "Silent Cells")
            if prompt == "What do you do from Silent Cells?":
                return self.option_index_containing(options, "Augur Cell")
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_south_adit()

        assert game.state is not None
        rendered = self.plain_output(log)
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["south_adit_cleared"])
        self.assertTrue(game.state.flags["counter_cadence_known"])
        self.assertEqual(game.state.flags["south_adit_irielle_plan"], "break")
        self.assertIn("Prison Cadence: Suppressed (1/5).", rendered)
        self.assertIn("Prison Cadence: Broken (0/5).", rendered)
        self.assertIsNotNone(game.find_companion("Irielle Ashwake"))
        self.assertEqual([encounter.title for encounter in encounters], ["South Adit Wardens"])

    def test_broken_prospect_smoke_route_reaches_hub(self) -> None:
        game, encounters = self.make_route_game(
            seed=94008,
            current_scene="broken_prospect",
            flags={
                "act2_started": True,
                "iron_hollow_sabotage_resolved": True,
                "south_adit_cleared": True,
                "act2_first_late_route": "south_adit",
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "What do you do from Broken Shelf?":
                return self.option_index_containing(options, "Rival Survey Shelf")
            if prompt == "What do you do from Rival Survey Shelf?":
                return self.option_index_containing(options, "Sealed Approach")
            if prompt == "What do you do from Sealed Approach?":
                return self.option_index_containing(options, "Dead Foreman's Shift")
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_broken_prospect()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["broken_prospect_cleared"])
        self.assertTrue(game.state.flags["wave_echo_reached"])
        self.assertEqual([encounter.title for encounter in encounters], ["Broken Prospect Rival Shelf", "Broken Prospect"])

    def test_wave_echo_outer_smoke_route_reaches_hub(self) -> None:
        game, encounters = self.make_route_game(
            seed=94009,
            current_scene="wave_echo_outer_galleries",
            flags={
                "act2_started": True,
                "broken_prospect_cleared": True,
                "south_adit_cleared": True,
                "wave_echo_reached": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "What do you do from Rail Junction?":
                return self.option_index_containing(options, "Slime Sluice")
            if prompt == "What do you do from Slime Sluice?":
                return self.option_index_containing(options, "False Echo Loop")
            if prompt == "What do you do from False Echo Loop?":
                return self.option_index_containing(options, "Deep Haul Gate")
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_wave_echo_outer_galleries()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["wave_echo_outer_cleared"])
        self.assertEqual([encounter.title for encounter in encounters], ["Resonant Vaults Slime Sluice", "Outer Gallery Pressure"])

    def test_black_lake_smoke_route_reaches_hub(self) -> None:
        game, encounters = self.make_route_game(
            seed=94010,
            current_scene="black_lake_causeway",
            flags={
                "act2_started": True,
                "wave_echo_outer_cleared": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "What do you do from Causeway Lip?":
                return self.option_index_containing(options, "Choir Barracks")
            if prompt == "What do you do from Choir Barracks?":
                return self.option_index_containing(options, "Blackwater Edge")
            if prompt == "What do you do from Blackwater Edge?":
                return self.option_index_containing(options, "Far Landing")
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_black_lake_causeway()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["black_lake_crossed"])
        self.assertTrue(game.state.flags["black_lake_barracks_raided"])
        self.assertEqual(
            [encounter.title for encounter in encounters],
            ["Blackglass Barracks", "Blackglass Waterline", "Blackglass Causeway"],
        )

    def test_blackglass_relay_smoke_route_reaches_hub_and_sets_forge_payoffs(self) -> None:
        game, encounters = self.make_route_game(
            seed=94012,
            current_scene="blackglass_relay_house",
            flags={
                "act2_started": True,
                "black_lake_crossed": True,
                "black_lake_barracks_orders_taken": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "What do you do from Relay Gate?":
                return self.option_index_containing(options, "Cable Sump")
            if prompt == "What do you do from Cable Sump?":
                return self.option_index_containing(options, "Keeper Ledger")
            if prompt == "What do you do from Keeper Ledger?":
                return self.option_index_containing(options, "Null-Bell Walk")
            if prompt == "What do you do from Null-Bell Walk?":
                return self.option_index_containing(options, "Counterweight Crown")
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_blackglass_relay_house()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["blackglass_relay_house_cleared"])
        self.assertTrue(game.state.flags["forge_signal_grounded"])
        self.assertTrue(game.state.flags["forge_reserve_timing_known"])
        self.assertTrue(game.state.flags["blackglass_relay_bell_tuned"])
        self.assertTrue(game.state.flags["blackglass_relay_cables_cleared"])
        self.assertEqual(
            [encounter.title for encounter in encounters],
            ["Blackglass Relay Cable Sump", "Blackglass Relay Crown"],
        )

    def test_forge_smoke_route_reaches_hub_and_records_handoff_flags(self) -> None:
        game, encounters = self.make_route_game(
            seed=94011,
            current_scene="forge_of_spells",
            companions=[create_nim_ardentglass(), create_irielle_ashwake()],
            output_lines=[],
            flags={
                "act2_started": True,
                "black_lake_crossed": True,
                "black_lake_shrine_purified": True,
                "black_lake_barracks_raided": True,
                "black_lake_barracks_orders_taken": True,
                "black_lake_causeway_shaken": True,
                "nim_countermeasure_notes": True,
                "south_adit_counter_cadence_learned": True,
                "act2_town_stability": 3,
                "act2_route_control": 3,
                "act2_whisper_pressure": 2,
            },
        )

        def fake_scenario_choice(prompt: str, options: list[str], **kwargs) -> int:
            if prompt == "What do you do from Forge Threshold?":
                return self.option_index_containing(options, "Shard Channels")
            if prompt == "What do you do from Shard Channels?":
                return self.option_index_containing(options, "Resonance Lens")
            if prompt == "What do you do from Resonance Lens?":
                return self.option_index_containing(options, "Caldra's Dais")
            return 1

        game.scenario_choice = fake_scenario_choice  # type: ignore[method-assign]
        game.scene_forge_of_spells()

        assert game.state is not None
        self.assertEqual(game.state.current_scene, "act2_expedition_hub")
        self.assertTrue(game.state.flags["caldra_defeated"])
        self.assertTrue(game.state.flags["act3_signal_carried"])
        self.assertTrue(game.state.flags["act3_lens_understood"])
        self.assertEqual(
            [encounter.title for encounter in encounters],
            ["Forge Shard Channels", "Boss: Sister Caldra Voss"],
        )
