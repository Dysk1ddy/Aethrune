from __future__ import annotations

from .schema import QuestDefinition, QuestReward


ACT_2_QUESTS: dict[str, QuestDefinition] = {
    "recover_pact_waymap": QuestDefinition(
        quest_id="recover_pact_waymap",
        title="Recover the Compact Waymap",
        giver="Halia Vey",
        location="Delvers' Exchange",
        summary=(
            "Halia wants an old Meridian Compact survey route recovered before rival claimants, mercenary diggers, "
            "or worse walk away with the only clear route into the deeper workings."
        ),
        objective="Secure the Meridian Compact waymap fragments and bring the findings back to the Delvers' Exchange.",
        turn_in="Return to Halia Vey at the Delvers' Exchange.",
        completion_flags=("agatha_truth_secured", "wave_echo_reached"),
        reward=QuestReward(
            xp=140,
            gold=75,
            items={"pact_waymap_case": 1, "resonance_tonic": 2},
            flags={"quest_reward_pact_routes_mastered": True},
            act2_metrics={"act2_route_control": 1},
        ),
        accepted_text=(
            "Halia speaks of maps the way soldiers speak of walls: whoever controls the route controls the argument "
            "that follows."
        ),
        ready_text="The Meridian Compact waymap can finally be pieced together. Halia Vey should see what route survived.",
        turn_in_text=(
            "Halia studies the recovered route in absolute silence, then smiles like someone who has just seen the "
            "shape of next season's leverage."
        ),
    ),
    "seek_agathas_truth": QuestDefinition(
        quest_id="seek_agathas_truth",
        title="Ask the Pale Witness What Was Buried",
        giver="Elira Lanternward",
        location="Hushfen Road",
        summary=(
            "Elira believes the dead around Hushfen still remember what greed and fear tried to hide from the living."
        ),
        objective="Reach the Pale Circuit, learn what was buried, and return with a cleaner truth.",
        turn_in="Return to Elira Lanternward once the Hushfen lead is settled.",
        completion_flags=("agatha_truth_secured",),
        reward=QuestReward(
            xp=130,
            gold=40,
            items={"agathas_truth_lantern": 1, "scroll_quell_the_deep": 1},
            flags={"quest_reward_agathas_clear_truth": True},
            act2_metrics={"act2_whisper_pressure": -1},
        ),
        accepted_text=(
            "Elira does not call it safe. She only says that grief often keeps straighter records than the living do."
        ),
        ready_text="Hushfen's dead have given up what they know. Elira Lanternward should hear it clearly.",
        turn_in_text=(
            "Elira listens without interrupting, then bows her head once as if accepting testimony from both the living "
            "and the lost."
        ),
    ),
    "rescue_stonehollow_scholars": QuestDefinition(
        quest_id="rescue_stonehollow_scholars",
        title="Bring Back the Survey Team",
        giver="Linene Ironward",
        location="Stonehollow Dig",
        summary=(
            "Linene hired specialists to read the dig cleanly. Now they are missing, and every missing scholar means "
            "someone else gets to write the first version of the truth."
        ),
        objective="Find the missing Stonehollow survey team and bring back whoever still lives.",
        turn_in="Return to Linene Ironward after Stonehollow is resolved.",
        completion_flags=("stonehollow_dig_cleared",),
        reward=QuestReward(
            xp=140,
            gold=70,
            items={"stonehollow_survey_lantern": 1, "miners_ration_tin": 4},
            flags={"quest_reward_stonehollow_scholars_saved": True},
            merchant_attitudes={"linene_graywind": 10},
            act2_metrics={"act2_town_stability": 1, "act2_route_control": 1},
        ),
        accepted_text=(
            "Linene's request sounds like logistics, but the steel under it is plain enough: she wants her people home."
        ),
        ready_text="Stonehollow's missing survey team has been accounted for. Linene Ironward should hear how bad the dig became.",
        turn_in_text=(
            "Linene absorbs the report the way a quartermaster absorbs casualty numbers: without flinching until the room "
            "is finally empty."
        ),
    ),
    "cut_woodland_saboteurs": QuestDefinition(
        quest_id="cut_woodland_saboteurs",
        title="Break the Woodland Saboteurs",
        giver="Daran Orchard",
        location="Greywake Survey Line",
        summary=(
            "Daran believes someone along the survey line is cutting stakes, stealing provisions, and making sure every "
            "honest expedition starts half-blind."
        ),
        objective="Track the woodland saboteurs, break their line, and return with proof the route is breathing again.",
        turn_in="Return to Daran Orchard once the survey camp route is secured.",
        completion_flags=("woodland_survey_cleared",),
        reward=QuestReward(
            xp=140,
            gold=65,
            items={"woodland_wayfinder_boots": 1, "delvers_amber": 2},
            flags={"quest_reward_woodland_route_charts": True},
            act2_metrics={"act2_route_control": 1},
        ),
        accepted_text=(
            "Daran frames it as fieldcraft, not heroics. A route only exists if scouts can live long enough to chart it."
        ),
        ready_text="The woodland sabotage line is broken. Daran Orchard should know the route is no longer fighting for someone else.",
        turn_in_text=(
            "Daran nods like a man hearing that a bowstring he distrusted has finally been cut."
        ),
    ),
    "hold_the_claims_meet": QuestDefinition(
        quest_id="hold_the_claims_meet",
        title="Hold the Claims Meeting Together",
        giver="Linene Ironward",
        location="Iron Hollow",
        summary=(
            "Iron Hollow needs a claims meeting that ends with a plan instead of knives, bribes, or a panic-driven scramble."
        ),
        objective="See the claims meeting through the sabotage night and keep the expedition from splintering.",
        turn_in="Report back to Linene Ironward once the town stops shaking itself apart.",
        completion_flags=("claims_meet_held", "phandalin_sabotage_resolved"),
        reward=QuestReward(
            xp=120,
            gold=75,
            items={"claims_accord_brooch": 1},
            flags={"quest_reward_claims_accord": True},
            merchant_attitudes={"linene_graywind": 10},
            act2_metrics={"act2_town_stability": 2},
        ),
        accepted_text=(
            "Linene is blunt: if the town tears itself apart over claims before the mine is even reached, everyone loses."
        ),
        ready_text="The claims meeting held and the sabotage did not finish the job. Linene should hear how close it came.",
        turn_in_text=(
            "Linene exhales through her nose and immediately starts talking about what order can still be salvaged."
        ),
    ),
    "free_wave_echo_captives": QuestDefinition(
        quest_id="free_wave_echo_captives",
        title="Free the South Adit Prisoners",
        giver="Elira Lanternward",
        location="South Adit",
        summary=(
            "The deeper cells are being used for prisoners, labor, and whatever the Quiet Choir cannot yet do to people in public."
        ),
        objective="Open the South Adit cells, free the prisoners, and get the survivors back aboveground.",
        turn_in="Return to Elira Lanternward after the captives are clear of the adit.",
        completion_flags=("south_adit_cleared",),
        reward=QuestReward(
            xp=160,
            gold=80,
            items={"freed_captive_prayer_beads": 1, "scroll_echo_step": 1, "scroll_lesser_restoration": 1},
            flags={"quest_reward_south_adit_survivor_network": True},
            act2_metrics={"act2_town_stability": 1, "act2_whisper_pressure": -1},
        ),
        accepted_text=(
            "Elira's voice goes colder than usual when she realizes the mine has turned into a prison."
        ),
        ready_text="The South Adit captives are free. Elira Lanternward should know who made it out.",
        turn_in_text=(
            "Elira receives the names of the living with more visible relief than any coin reward could equal."
        ),
    ),
    "sever_quiet_choir": QuestDefinition(
        quest_id="sever_quiet_choir",
        title="Sever the Quiet Choir",
        giver="Iron Hollow Council",
        location="Resonant Vaults",
        summary=(
            "The expedition race is only surface noise now. A cult beneath the cave is using the mine's old magic to study "
            "something that should never have been found."
        ),
        objective="Identify the Quiet Choir's leader, break the cult cell, and cut their hold on the mine.",
        turn_in="There is no formal turn-in beyond surviving and bringing the truth back out.",
        completion_flags=("caldra_defeated",),
        reward=QuestReward(
            xp=250,
            gold=150,
            items={"forgeheart_cinder": 1, "forge_blessing_elixir": 2, "scroll_forge_shelter": 1},
            flags={"quest_reward_quiet_choir_broken": True},
            act2_metrics={"act2_town_stability": 1, "act2_route_control": 1, "act2_whisper_pressure": -2},
        ),
        accepted_text=(
            "By the time the Quiet Choir has a name, nobody in Iron Hollow mistakes this for an ordinary mining dispute anymore."
        ),
        ready_text="The Quiet Choir's leader has fallen. The people above should hear what kind of threat was really under them.",
        turn_in_text=(
            "The report lands on the table like a weight nobody in the room was ready to carry, but at least now it has a name."
        ),
    ),
}

