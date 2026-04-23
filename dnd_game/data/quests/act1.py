from __future__ import annotations

from .schema import QuestDefinition, QuestReward


ACT_1_QUESTS: dict[str, QuestDefinition] = {
    "trace_blackwake_cell": QuestDefinition(
        quest_id="trace_blackwake_cell",
        title="Embers Before the Road",
        giver="Mira Thann",
        location="Blackwake Crossing",
        summary=(
            "Smoke near the river cut points to burned toll records, forged route authority, and an Ashen Brand supply cell operating closer to Greywake than expected."
        ),
        objective="Investigate Blackwake Crossing, uncover the cache behind the forged papers, and decide what survives the floodgate chamber.",
        turn_in="Report the Blackwake outcome to Mira in Greywake or carry the proof south toward Iron Hollow.",
        completion_flags=("blackwake_completed",),
        reward=QuestReward(
            xp=90,
            gold=35,
            items={"miras_blackwake_seal": 1, "scroll_ember_ward": 1},
            flags={"quest_reward_blackwake_watch_backing": True},
        ),
        accepted_text=(
            "The road to Iron Hollow can wait long enough to answer one ugly question: why are caravans vanishing before they even reach the wider Emberway?"
        ),
        ready_text="The Blackwake cell has been resolved. The crossing's prisoners, ledgers, and cache damage will shape what the road hears next.",
        turn_in_text=(
            "Mira reads the Blackwake account without interrupting. By the end, the Ashen Brand is no longer a distant frontier gang on her board. It is a supply network with city-side shadows."
        ),
    ),
    "secure_miners_road": QuestDefinition(
        quest_id="secure_miners_road",
        title="Stop the Watchtower Raids",
        giver="Steward Tessa Harrow",
        location="Steward's Hall",
        summary=(
            "Tessa Harrow needs Ashfall Watch broken so miners, messengers, and supply runners can take "
            "the east road without vanishing into smoke and ambush."
        ),
        objective="Break the Ashen Brand's hold on Ashfall Watch, then return to Tessa Harrow.",
        turn_in="Return to Tessa Harrow in Steward's Hall.",
        completion_flags=("ashfall_watch_cleared",),
        reward=QuestReward(
            xp=100,
            gold=50,
            items={"roadwarden_cloak": 1, "travel_biscuits": 4},
            flags={"quest_reward_miners_road_open": True},
        ),
        accepted_text=(
            "Tessa does not dress it up as heroics. She needs the watchtower raiders stopped before a frightened "
            "town begins starving by caution alone."
        ),
        ready_text="Ashfall Watch has fallen. Tessa Harrow should hear that the east road can breathe again.",
        turn_in_text=(
            "Relief finally reaches Tessa's face in full. For the first time all day, she speaks like someone "
            "who believes tomorrow's wagons might actually arrive."
        ),
    ),
    "restore_barthen_supplies": QuestDefinition(
        quest_id="restore_barthen_supplies",
        title="Keep the Shelves Full",
        giver="Hadrik",
        location="Hadrik's Provisions",
        summary="Hadrik wants the raiders at Ashfall Watch driven off before Iron Hollow's simplest needs become luxuries.",
        objective="Clear Ashfall Watch and report back to Hadrik once the road is safer.",
        turn_in="Return to Hadrik's Provisions.",
        completion_flags=("ashfall_watch_cleared",),
        reward=QuestReward(
            xp=75,
            gold=35,
            items={"barthen_resupply_token": 1, "bread_round": 4, "camp_stew_jar": 2},
            flags={"quest_reward_barthen_resupply_credit": True},
            merchant_attitudes={"barthen_provisions": 20},
        ),
        accepted_text=(
            "Hadrik's request is practical to the point of pain: make the road safe enough that flour, bandages, "
            "and lamp oil stop feeling rarer than courage."
        ),
        ready_text="With Ashfall Watch broken, Hadrik can finally start planning for steady wagons again.",
        turn_in_text=(
            "Hadrik laughs once under his breath, more tired than cheerful, then immediately starts talking about "
            "what full shelves will mean for families who have been rationing every meal."
        ),
    ),
    "reopen_lionshield_trade": QuestDefinition(
        quest_id="reopen_lionshield_trade",
        title="Reopen the Trade Lane",
        giver="Linene Ironward",
        location="Ironbound Trading Post",
        summary=(
            "Linene needs proof that the Ashen Brand's chokehold is weakening so honest trade can move without paying "
            "for fear on both ends."
        ),
        objective="Break Ashfall Watch and return to Linene Ironward with the news.",
        turn_in="Return to Linene Ironward at the Ironbound trading post.",
        completion_flags=("ashfall_watch_cleared",),
        reward=QuestReward(
            xp=85,
            gold=45,
            items={"lionshield_quartermaster_badge": 1, "potion_healing": 2, "antitoxin_vial": 2},
            flags={"quest_reward_lionshield_logistics": True},
            merchant_attitudes={"linene_graywind": 20},
        ),
        accepted_text=(
            "Linene frames it in ledgers and steel, but the meaning is simple enough: if the watchtower stands, "
            "every honest caravan keeps bleeding coin to men with ash on their badges."
        ),
        ready_text="Ashfall Watch is down. Linene Ironward should know the trade lane finally has room to recover.",
        turn_in_text=(
            "Linene studies the soot on your gear, nods once, and starts reordering tomorrow in her head before you "
            "finish speaking."
        ),
    ),
    "marked_keg_investigation": QuestDefinition(
        quest_id="marked_keg_investigation",
        title="The Marked Keg",
        giver="Mara Ashlamp",
        location="Ashlamp Inn",
        summary=(
            "Mara Ashlamp spotted a chalk-marked keg and wants the hand behind it named before the Ashlamp's common room "
            "turns fear into entertainment for the wrong people."
        ),
        objective="Identify who marked the keg at Ashlamp Inn and report back to Mara Ashlamp.",
        turn_in="Return to Mara Ashlamp in the Ashlamp Inn common room.",
        completion_flags=("marked_keg_resolved",),
        reward=QuestReward(
            xp=70,
            gold=24,
            items={"innkeeper_credit_token": 1},
            flags={"quest_reward_stonehill_common_room_welcome": True},
        ),
        accepted_text=(
            "Mara does not ask for heroics. She asks for judgment fast enough to catch the liar before the first chair "
            "starts pretending it flew on its own."
        ),
        ready_text="You know who marked the keg. Mara Ashlamp is waiting for the name and the reason.",
        turn_in_text=(
            "Mara hears you out without wasting a blink. By the time you finish, the culprit is no longer a rumor in the "
            "room but a problem with a face, a motive, and no more cover."
        ),
    ),
    "songs_for_the_missing": QuestDefinition(
        quest_id="songs_for_the_missing",
        title="Songs for the Missing",
        giver="Sella Quill",
        location="Ashlamp Inn",
        summary=(
            "Sella Quill wants three true details from the Ashlamp's frightened regulars so the missing stop shrinking into "
            "numbers, warnings, and muttered road talk."
        ),
        objective="Bring Sella Quill three true details worth carrying into song.",
        turn_in="Return to Sella Quill in the Ashlamp Inn common room.",
        completion_flags=(
            "songs_for_missing_jerek_detail",
            "songs_for_missing_tam_detail",
            "songs_for_missing_nera_detail",
        ),
        reward=QuestReward(
            xp=65,
            gold=18,
            items={"sella_ballad_token": 1},
            flags={"quest_reward_sella_names_carried": True},
        ),
        accepted_text=(
            "Sella is not asking for gossip. She wants the kind of detail that can keep grief from flattening into habit "
            "once a frontier town gets tired enough to forget names."
        ),
        ready_text="You have gathered three true details for Sella Quill. The song is waiting on you now.",
        turn_in_text=(
            "Sella takes the three details like live coals and turns them carefully, already hearing where each one will "
            "land in the room. By the end, the missing sound less like statistics and more like neighbors whose absence still matters."
        ),
    ),
    "quiet_table_sharp_knives": QuestDefinition(
        quest_id="quiet_table_sharp_knives",
        title="Quiet Table, Sharp Knives",
        giver="Nera Doss",
        location="Ashlamp Inn",
        summary=(
            "Nera Doss thinks one quiet Ashlamp table is buying arguments, editing messages, and steering the common room "
            "toward useful violence for the Ashen Brand."
        ),
        objective="Expose the quiet-table scheme in Ashlamp Inn and report back to Nera Doss.",
        turn_in="Return to Nera Doss in the Ashlamp Inn common room.",
        completion_flags=("quiet_table_knives_resolved",),
        reward=QuestReward(
            xp=80,
            gold=28,
            items={"blackseal_taster_pin": 1},
            flags={"quest_reward_stonehill_quiet_room_access": True},
        ),
        accepted_text=(
            "Nera has no patience for melodrama. She has seen what one bought lie can do to a frightened room, and she would "
            "prefer the Ashlamp not become another message delivered in bruises."
        ),
        ready_text="The quiet-table scheme has been broken open. Nera Doss is waiting to hear exactly how.",
        turn_in_text=(
            "Nera listens with the stillness of a courier checking every word for weight. When you finish, she nods once like "
            "someone finally got her message to the right address without letting half the road write on it first."
        ),
    ),
    "find_dain_harl": QuestDefinition(
        quest_id="find_dain_harl",
        title="Bring Back Dain's Name",
        giver="Jerek Harl",
        location="Ashlamp Inn",
        summary=(
            "Jerek Harl wants truth about his brother Dain, one of the east-road workers swallowed by the crews taken toward Ashfall Watch."
        ),
        objective="Search Ashfall Watch for Dain Harl or proof of his fate, then return to Jerek Harl.",
        turn_in="Return to Jerek Harl in the Ashlamp Inn common room.",
        completion_flags=("dain_harl_truth_found",),
        reward=QuestReward(
            xp=85,
            gold=26,
            items={"harl_road_knot": 1},
            flags={"quest_reward_jerek_road_knot": True},
        ),
        accepted_text=(
            "Jerek is not asking for hope. He is asking for truth tough enough to survive the road home, whether that truth walks on its own feet or comes back in your hands."
        ),
        ready_text="You know what happened to Dain Harl at Ashfall Watch. Jerek is waiting for the truth, not rumor.",
        turn_in_text=(
            "Jerek listens without interrupting, like a man finally letting grief choose one shape instead of all of them at once. When you finish, the room goes quieter around him, but less lost."
        ),
    ),
    "false_manifest_circuit": QuestDefinition(
        quest_id="false_manifest_circuit",
        title="False Manifest Circuit",
        giver="Sabra Kestrel",
        location="Oren Vale's Contract House",
        summary=(
            "Sabra Kestrel has found one Greywake manifest corrected by three different liars. She wants the room's cleanest tells named before the forged line reaches the Emberway."
        ),
        objective="Cross-check Oren, Vessa, and Garren's truths about the forged manifest line, then return to Sabra Kestrel.",
        turn_in="Return to Sabra Kestrel at Oren Vale's contract house in Greywake.",
        completion_flags=("false_manifest_oren_detail", "false_manifest_vessa_detail", "false_manifest_garren_detail"),
        reward=QuestReward(
            xp=75,
            gold=24,
            items={"kestrel_ledger_clasp": 1},
            flags={"quest_reward_neverwinter_private_room_access": True},
        ),
        accepted_text=(
            "Sabra is not asking you to stop the whole network tonight. She just wants one clean manifest lie pinned to the wall before it can keep pretending it is routine paperwork."
        ),
        ready_text="You have the three details Sabra needed. The false manifest line can be named now, if you bring it back to her before the room changes its story.",
        turn_in_text=(
            "Sabra lines your three details together, exhales once, and finally lets herself call the thing by its proper shape: a forged manifest circuit feeding false road authority south."
        ),
    ),
    "silence_old_owl_well": QuestDefinition(
        quest_id="silence_old_owl_well",
        title="Silence Blackglass Well",
        giver="Halia Vey",
        location="Delvers' Exchange",
        summary=(
            "Halia Vey wants the grave-salvage operation at Blackglass Well destroyed before more prospectors and exchange crews vanish into its dig lines."
        ),
        objective="Break the operation at Blackglass Well and return to Halia Vey.",
        turn_in="Return to Halia Vey at the Delvers' Exchange.",
        completion_flags=("old_owl_well_cleared",),
        reward=QuestReward(
            xp=100,
            gold=45,
            items={"gravequiet_amulet": 1, "scroll_clarity": 1, "blessed_salve": 1},
            flags={"quest_reward_gravequiet_contacts": True},
        ),
        accepted_text=(
            "Halia phrases it like a ledger problem, but the meaning is simple enough: Blackglass Well is swallowing people, and every day it stays active makes the town smaller."
        ),
        ready_text="Blackglass Well is quiet. Halia Vey should hear the grave-salvage line has been broken.",
        turn_in_text=(
            "Halia's expression barely changes, but the room around her seems to unclench all the same. Even polished pragmatism has room for relief when missing crews stop becoming permanent."
        ),
    ),
    "break_wyvern_tor_raiders": QuestDefinition(
        quest_id="break_wyvern_tor_raiders",
        title="Break the Red Mesa Raiders",
        giver="Daran Orchard",
        location="Orchard Wall",
        summary=(
            "Daran Orchard wants the raiders at Red Mesa Hold scattered before they keep turning the eastern hills into hunting ground for scouts, drovers, and herders."
        ),
        objective="Clear Red Mesa Hold and report back to Daran Orchard.",
        turn_in="Return to Daran Orchard at the Orchard Wall.",
        completion_flags=("wyvern_tor_cleared",),
        reward=QuestReward(
            xp=100,
            gold=40,
            items={"edermath_scout_buckle": 1, "greater_healing_draught": 1},
            flags={"quest_reward_edermath_scout_network": True},
        ),
        accepted_text=(
            "Daran does not romanticize the work. Red Mesa Hold is a practical threat on practical roads, and he would prefer the town's scouts stop dying to prove it."
        ),
        ready_text="Red Mesa Hold is clear. Daran Orchard should know the high-ground raiders are gone.",
        turn_in_text=(
            "Daran nods once, the kind of nod old soldiers reserve for work done cleanly. The hills will still be dangerous tomorrow, but at least now they will be honestly dangerous."
        ),
    ),
    "bryn_loose_ends": QuestDefinition(
        quest_id="bryn_loose_ends",
        title="Loose Ends",
        giver="Bryn Underbough",
        location="The road and whatever old cache still remembers her",
        summary=(
            "Bryn suspects one of her abandoned smuggler caches has been folded into the Ashen Brand's side traffic. She wants the ledger inside found and judged before someone else profits from it."
        ),
        objective="Track down Bryn's old cache trail and decide what to do with the ledger inside it.",
        turn_in="Resolve the ledger question with Bryn once the cache is found.",
        completion_flags=("bryn_loose_ends_resolved",),
        reward=QuestReward(
            xp=80,
            gold=25,
            items={"bryns_cache_keyring": 1, "dust_of_disappearance": 1},
            flags={"quest_reward_bryn_underworld_favor": True},
        ),
        accepted_text=(
            "Bryn admits this one quietly: there is an old cache she never meant anyone worth saving to find. If the Brand reached it first, she wants your help ending the story cleanly."
        ),
        ready_text="Bryn's cache has been found. She needs your call on whether the ledger burns or gets sold.",
        turn_in_text=(
            "Bryn takes your answer without pretending it costs nothing. Whatever route that ledger once kept alive ends here, one way or another."
        ),
    ),
    "elira_faith_under_ash": QuestDefinition(
        quest_id="elira_faith_under_ash",
        title="Faith Under Ash",
        giver="Elira Lanternward",
        location="Wherever mercy has to stand under pressure",
        summary=(
            "Elira wants to see what kind of justice survives once the Ashen Brand is beaten badly enough to beg. She is asking about you as much as about them."
        ),
        objective="Face a captive servant of the Ashen Brand and decide whether mercy or fear carries the day.",
        turn_in="Make the call when Elira asks for it in the field.",
        completion_flags=("elira_faith_under_ash_resolved",),
        reward=QuestReward(
            xp=80,
            gold=20,
            items={"dawnmantle_mercy_charm": 1, "blessed_salve": 1},
            flags={"quest_reward_elira_mercy_blessing": True},
        ),
        accepted_text=(
            "Elira says it gently, which somehow makes it harder: anyone can sound righteous before the blood is close. What matters is the answer you choose after."
        ),
        ready_text="Elira's question has reached the point where a real answer is needed, not another good intention.",
        turn_in_text=(
            "Elira does not praise or condemn you cheaply. She simply carries your answer forward, which is heavier in its own way than either reaction would have been."
        ),
    ),
}
