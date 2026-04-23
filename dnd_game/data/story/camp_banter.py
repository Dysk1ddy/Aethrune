from __future__ import annotations


CAMP_BANTERS: list[dict[str, object]] = [
    {
        "id": "camp_banter_elira_tolan_greywake",
        "title": "The Wounded Line",
        "participants": ["elira_dawnmantle", "tolan_ironshield"],
        "requires_flags": ["greywake_triage_yard_seen"],
        "requires_any_flags": ["greywake_wounded_stabilized", "greywake_wounded_line_guarded", "greywake_manifest_preserved"],
        "priority": 100,
        "intro": "Elira cleans a needle by the fire while Tolan studies the road as if it might try the same trick twice.",
        "lines": [
            ("tolan_ironshield", "That yard was not panic. Panic leaves a mess. That was a clerk with a knife."),
            ("elira_dawnmantle", "A clerk, a captain, or someone who taught both of them to think the same way."),
            ("tolan_ironshield", "You triaged like a shield wall. Worst bleeding first, then breathing, then anyone still shouting."),
            ("elira_dawnmantle", "And you talk about mercy like a barricade."),
            ("tolan_ironshield", "Aye. Sometimes it is."),
            {
                "speaker": "elira_dawnmantle",
                "text": "They will remember who stood between them and the road.",
                "requires_any_flags": ["greywake_wounded_stabilized", "greywake_wounded_line_guarded"],
            },
            {
                "speaker": "tolan_ironshield",
                "text": "Good. Let the enemy learn that witnesses can have armor too.",
                "requires_any_flags": ["greywake_wounded_stabilized", "greywake_wounded_line_guarded"],
            },
            {
                "speaker": "tolan_ironshield",
                "text": "That manifest was no casualty list. It was the fight before the fight.",
                "requires_flags": ["greywake_manifest_preserved"],
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "Names sorted into outcomes. The Lantern hates a loaded die.",
                "requires_flags": ["greywake_manifest_preserved"],
            },
            {
                "speaker": "tolan_ironshield",
                "text": "Paper burns. People who lived can still point.",
                "requires_flags": ["greywake_manifest_destroyed"],
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "Then we keep them alive long enough to be believed.",
                "requires_flags": ["greywake_manifest_destroyed"],
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "Faith did not make the work lighter. It only made looking away impossible.",
                "requires_flag_values": {"elira_initial_trust_reason": "spiritual_kinship"},
            },
            {
                "speaker": "tolan_ironshield",
                "text": "That is a better prayer than most hymns.",
                "requires_flag_values": {"elira_initial_trust_reason": "spiritual_kinship"},
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_greywake_testimony_threaded", "system_profile_seeded"],
                "companion_deltas": {"elira_dawnmantle": 1, "tolan_ironshield": 1},
                "journal": "At camp, Elira and Tolan reframed Greywake as a witness problem: the enemy is sorting outcomes, but living witnesses can fight that sorting.",
                "clues": [
                    "Elira and Tolan agree Greywake was a pre-sorted outcome system, not ordinary panic or battlefield accident."
                ],
                "companion_lore": {
                    "elira_dawnmantle": "At Greywake, Elira began treating witness protection as a sacred duty rather than only field medicine.",
                    "tolan_ironshield": "Tolan reads Greywake as battlefield triage turned into enemy administration, which makes living witnesses a kind of shield line.",
                },
                "player_statuses": {"blessed": 1},
            },
            {
                "requires_flags": ["greywake_manifest_preserved"],
                "set_flags": ["camp_greywake_manifest_read_as_schedule"],
                "journal": "The preserved Greywake manifest now anchors the party's understanding of the Ashen Brand as a scheduling system.",
            },
            {
                "requires_any_flags": ["greywake_wounded_stabilized", "greywake_wounded_line_guarded"],
                "metric_deltas": {"act1_town_fear": -1},
                "journal": "Greywake's protected wounded become a steadier witness line instead of only survivors.",
            },
        ],
    },
    {
        "id": "camp_banter_elira_rhogar_faith_action",
        "title": "Small Promises",
        "participants": ["elira_dawnmantle", "rhogar_valeguard"],
        "requires_any_flags": ["wayside_luck_shrine_seen", "greywake_triage_yard_seen", "road_ambush_cleared"],
        "priority": 94,
        "intro": "Rhogar watches Elira turn a frayed road-ribbon between her fingers, careful not to pull it apart.",
        "lines": [
            ("rhogar_valeguard", "You tied the shrine bell as if it could hear you."),
            ("elira_dawnmantle", "No. I tied it because we could."),
            ("rhogar_valeguard", "A promise, then."),
            ("elira_dawnmantle", "A small one. Small promises are harder to excuse."),
            ("rhogar_valeguard", "An oath begins the same way. Not with thunder. With a hand placed where it cannot easily be withdrawn."),
            {
                "speaker": "elira_dawnmantle",
                "text": "Some people need longer to find the wounded thing in front of them.",
                "requires_flag_values": {"elira_initial_trust_reason": "reserved_kindness"},
            },
            {
                "speaker": "rhogar_valeguard",
                "text": "Then we stand where they must look.",
                "requires_flag_values": {"elira_initial_trust_reason": "reserved_kindness"},
            },
            {
                "speaker": "rhogar_valeguard",
                "text": "They did not ask whether the road deserved saving. They saved who lay on it.",
                "requires_flag_values": {"elira_initial_trust_reason": "warm_trust"},
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "That is the only sermon I trust at first reading.",
                "requires_flag_values": {"elira_initial_trust_reason": "warm_trust"},
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_faith_oath_anchor"],
                "companion_deltas": {"elira_dawnmantle": 1, "rhogar_valeguard": 1},
                "journal": "Elira and Rhogar found common ground: faith and oath both matter only when they become action.",
                "player_statuses": {"blessed": 1},
            }
        ],
    },
    {
        "id": "camp_banter_bryn_kaelis_road_angles",
        "title": "Exits and Chimneys",
        "participants": ["bryn_underbough", "kaelis_starling"],
        "requires_any_flags": ["road_ambush_cleared", "blackwake_completed"],
        "priority": 90,
        "intro": "Bryn and Kaelis compare the day's tracks with the seriousness of people pretending they are not enjoying it.",
        "lines": [
            ("bryn_underbough", "You count exits before you count faces."),
            ("kaelis_starling", "Faces lie slower than exits close."),
            ("bryn_underbough", "That is horribly wise. I hate it."),
            ("kaelis_starling", "You counted the cookfire smoke."),
            ("bryn_underbough", "Cookfires tell the truth. People put lies in their mouths, not their chimneys."),
            {
                "speaker": "kaelis_starling",
                "text": "At Blackwake, the lie was in the uniforms.",
                "requires_flag_values": {"blackwake_resolution": "evidence"},
            },
            {
                "speaker": "bryn_underbough",
                "text": "Uniforms are just costumes with better buttons.",
                "requires_flag_values": {"blackwake_resolution": "evidence"},
            },
            {
                "speaker": "bryn_underbough",
                "text": "Their checkpoint folded fast once the quiet bits stopped working.",
                "requires_flag_values": {"blackwake_resolution": "sabotage"},
            },
            {
                "speaker": "kaelis_starling",
                "text": "Most systems look brave until one hinge is gone.",
                "requires_flag_values": {"blackwake_resolution": "sabotage"},
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_route_angles_read"],
                "companion_deltas": {"bryn_underbough": 1, "kaelis_starling": 1},
                "journal": "Bryn and Kaelis turned the road's ambush logic into practical camp intelligence.",
                "player_statuses": {"invisible": 1},
            },
            {
                "requires_flags": ["blackwake_completed"],
                "metric_deltas": {"act1_ashen_strength": -1},
                "clues": ["Bryn and Kaelis can now explain Blackwake as route control disguised as road authority."],
            },
        ],
    },
    {
        "id": "camp_banter_tolan_rhogar_line_and_oath",
        "title": "Line and Oath",
        "participants": ["tolan_ironshield", "rhogar_valeguard"],
        "requires_any_flags": ["road_ambush_cleared", "ashfall_watch_cleared"],
        "priority": 86,
        "intro": "Tolan sets his shield near the fire. Rhogar notices the angle before anyone else does.",
        "lines": [
            ("tolan_ironshield", "An oath is a fine thing until arrows start asking questions."),
            ("rhogar_valeguard", "Then the oath answers by where you stand."),
            ("tolan_ironshield", "Spoken like someone who has not had to move a wagon with two wheels and three cowards."),
            ("rhogar_valeguard", "Spoken like someone whose discipline has become faith without admitting it."),
            ("tolan_ironshield", "Careful. I am allergic to compliments."),
            {
                "speaker": "rhogar_valeguard",
                "text": "The prisoners lived because the line bent.",
                "requires_flags": ["ashfall_prisoners_freed"],
            },
            {
                "speaker": "tolan_ironshield",
                "text": "A line that never bends is just a wall waiting to crack.",
                "requires_flags": ["ashfall_prisoners_freed"],
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_line_oath_drill"],
                "companion_deltas": {"tolan_ironshield": 1, "rhogar_valeguard": 1},
                "journal": "Tolan and Rhogar turned shield discipline and oath-duty into a shared defensive drill.",
                "player_statuses": {"guarded": 1},
            }
        ],
    },
    {
        "id": "camp_banter_bryn_elira_quiet_mercy",
        "title": "Quiet Mercy",
        "participants": ["bryn_underbough", "elira_dawnmantle"],
        "requires_any_flags": [
            "stonehill_nera_treated",
            "greywake_wounded_stabilized",
            "greywake_wounded_line_guarded",
            "songs_for_missing_nera_detail",
        ],
        "priority": 82,
        "intro": "Bryn tries to sharpen a knife where Elira cannot see the tremor in her hand. Elira sees anyway.",
        "lines": [
            ("elira_dawnmantle", "You dislike being seen doing kind things."),
            ("bryn_underbough", "Wild accusation. Hurtful. Accurate, but hurtful."),
            ("elira_dawnmantle", "Why?"),
            ("bryn_underbough", "Because if people see it, they start deciding what it means."),
            ("elira_dawnmantle", "It can mean someone was helped."),
            ("bryn_underbough", "That is the dangerous version."),
            {
                "speaker": "elira_dawnmantle",
                "text": "Nera breathed easier after you left.",
                "requires_flags": ["stonehill_nera_treated"],
            },
            {
                "speaker": "bryn_underbough",
                "text": "Then let that be the whole song.",
                "requires_flags": ["stonehill_nera_treated"],
            },
            {
                "speaker": "bryn_underbough",
                "text": "Greywake was different. Too many eyes to be sneaky.",
                "requires_any_flags": ["greywake_wounded_stabilized", "greywake_wounded_line_guarded"],
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "And still you helped.",
                "requires_any_flags": ["greywake_wounded_stabilized", "greywake_wounded_line_guarded"],
            },
            {
                "speaker": "bryn_underbough",
                "text": "Do not make it sound noble. I panicked in a useful direction.",
                "requires_any_flags": ["greywake_wounded_stabilized", "greywake_wounded_line_guarded"],
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_quiet_mercy_named"],
                "companion_deltas": {"bryn_underbough": 1, "elira_dawnmantle": 1},
                "journal": "Bryn and Elira named quiet mercy as a kind of courage, not a lesser version of open heroics.",
            },
            {
                "requires_flags": ["stonehill_nera_treated"],
                "metric_deltas": {"act1_town_fear": -1},
            },
        ],
    },
    {
        "id": "camp_banter_bryn_rhogar_public_truth",
        "title": "Public Truth",
        "participants": ["bryn_underbough", "rhogar_valeguard"],
        "requires_any_flags": ["cinderfall_ruins_cleared", "bryn_loose_ends_resolved"],
        "priority": 78,
        "intro": "The Cinderfall maps sit between Bryn and Rhogar like a third person with terrible manners.",
        "lines": [
            ("rhogar_valeguard", "A hidden truth can protect the guilty."),
            ("bryn_underbough", "A shouted truth can get the powerless killed."),
            ("rhogar_valeguard", "Then choose the place and hour, but do not bury it forever."),
            ("bryn_underbough", "Forever is expensive. I usually rent silence by the week."),
            {
                "speaker": "rhogar_valeguard",
                "text": "The town deserved to know who sold its roads.",
                "requires_flag_values": {"act1_companion_conflict_side": "rhogar"},
            },
            {
                "speaker": "bryn_underbough",
                "text": "Aye. I just hope the town knows where to aim its anger.",
                "requires_flag_values": {"act1_companion_conflict_side": "rhogar"},
            },
            {
                "speaker": "bryn_underbough",
                "text": "Some names stayed quiet because quiet kept people breathing.",
                "requires_flag_values": {"act1_companion_conflict_side": "bryn"},
            },
            {
                "speaker": "rhogar_valeguard",
                "text": "Then the burden remains with us until quiet is no longer mercy.",
                "requires_flag_values": {"act1_companion_conflict_side": "bryn"},
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_public_truth_tension_named"],
                "journal": "Bryn and Rhogar clarified their disagreement: truth has to protect people, but silence cannot become ownership.",
                "clues": ["The Cinderfall route list can still affect who trusts the party's warnings later."],
            },
            {
                "requires_flag_values": {"act1_companion_conflict_side": "bryn"},
                "companion_deltas": {"bryn_underbough": 1},
                "metric_deltas": {"act1_town_fear": -1},
            },
            {
                "requires_flag_values": {"act1_companion_conflict_side": "rhogar"},
                "companion_deltas": {"rhogar_valeguard": 1},
                "metric_deltas": {"act1_town_fear": -1},
            },
        ],
    },
    {
        "id": "camp_banter_kaelis_tolan_timing",
        "title": "Half A Breath",
        "participants": ["kaelis_starling", "tolan_ironshield"],
        "requires_flags": ["road_ambush_cleared"],
        "priority": 76,
        "intro": "Kaelis times Tolan's shield drills by the crackle of the fire, then pretends he was not counting.",
        "lines": [
            ("kaelis_starling", "You step half a breath before the hit."),
            ("tolan_ironshield", "You vanish half a breath before anyone knows there is a hit."),
            ("kaelis_starling", "Both are timing."),
            ("tolan_ironshield", "Both are rude to whoever planned the ambush."),
            ("kaelis_starling", "Good."),
            {
                "speaker": "tolan_ironshield",
                "text": "Clean work on the ridge.",
                "requires_flags": ["road_ambush_scouted"],
            },
            {
                "speaker": "kaelis_starling",
                "text": "Clean means the wounded list stayed short.",
                "requires_flags": ["road_ambush_scouted"],
            },
            {
                "speaker": "kaelis_starling",
                "text": "I read the trees late.",
                "blocked_flags": ["road_ambush_scouted"],
            },
            {
                "speaker": "tolan_ironshield",
                "text": "Then read the next ones angry, not ashamed.",
                "blocked_flags": ["road_ambush_scouted"],
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_timing_drill"],
                "companion_deltas": {"kaelis_starling": 1, "tolan_ironshield": 1},
                "journal": "Kaelis and Tolan worked out a shared timing drill for ambushes.",
                "player_statuses": {"emboldened": 1},
            }
        ],
    },
    {
        "id": "camp_banter_elira_kaelis_silence",
        "title": "What Silence Means",
        "participants": ["elira_dawnmantle", "kaelis_starling"],
        "requires_any_flags": ["old_owl_well_cleared", "greywake_triage_yard_seen", "agatha_truth_secured"],
        "priority": 74,
        "intro": "The camp goes quiet enough for Kaelis to notice. Elira notices him noticing.",
        "lines": [
            ("elira_dawnmantle", "You listen like silence might confess."),
            ("kaelis_starling", "Sometimes it does."),
            ("elira_dawnmantle", "And when it does not?"),
            ("kaelis_starling", "Then it is waiting."),
            ("elira_dawnmantle", "I used to think silence was where faith rested. Now I think it is where fear hides its shoes."),
            {
                "speaker": "kaelis_starling",
                "text": "Blackglass Well was too quiet after the fight.",
                "requires_flags": ["old_owl_well_cleared"],
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "Some places do not become peaceful just because they stop screaming.",
                "requires_flags": ["old_owl_well_cleared"],
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_silence_read"],
                "companion_deltas": {"elira_dawnmantle": 1, "kaelis_starling": 1},
                "journal": "Elira and Kaelis began treating silence as evidence instead of comfort.",
            },
            {
                "requires_flags": ["agatha_truth_secured"],
                "metric_deltas": {"act2_whisper_pressure": -1},
            },
        ],
    },
    {
        "id": "camp_banter_tolan_bryn_stonehill_order",
        "title": "Bad Wheels",
        "participants": ["tolan_ironshield", "bryn_underbough"],
        "requires_any_flags": ["phandalin_council_seen", "marked_keg_resolved"],
        "priority": 72,
        "intro": "Tolan watches the road back toward town. Bryn watches the people watching it.",
        "lines": [
            ("tolan_ironshield", "A room full of frightened folk can turn faster than a bad wheel."),
            ("bryn_underbough", "Bad wheels squeak first. Frightened folk smile."),
            ("tolan_ironshield", "You watch smiles?"),
            ("bryn_underbough", "I watch who stops smiling when coin gets mentioned."),
            {
                "speaker": "tolan_ironshield",
                "text": "Public answer steadied them.",
                "requires_flags": ["stonehill_marked_keg_named"],
            },
            {
                "speaker": "bryn_underbough",
                "text": "Public answers also make public enemies.",
                "requires_flags": ["stonehill_marked_keg_named"],
            },
            {
                "speaker": "bryn_underbough",
                "text": "Quiet fix, fewer broken cups.",
                "requires_flags": ["marked_keg_resolved"],
                "blocked_flags": ["stonehill_marked_keg_named"],
            },
            {
                "speaker": "tolan_ironshield",
                "text": "And fewer lessons learned.",
                "requires_flags": ["marked_keg_resolved"],
                "blocked_flags": ["stonehill_marked_keg_named"],
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_stonehill_order_read"],
                "companion_deltas": {"tolan_ironshield": 1, "bryn_underbough": 1},
                "journal": "Tolan and Bryn compared Ashlamp's public order to the quieter fear that feeds riots.",
            },
            {
                "requires_flags": ["stonehill_marked_keg_named"],
                "metric_deltas": {"act1_town_fear": -1},
            },
        ],
    },
    {
        "id": "camp_banter_elira_rhogar_faith_under_ash",
        "title": "Judgment Leaves An Echo",
        "participants": ["elira_dawnmantle", "rhogar_valeguard"],
        "requires_flags": ["elira_faith_under_ash_resolved"],
        "priority": 70,
        "intro": "Elira says little until Rhogar sets his cup down and gives the silence somewhere honorable to stand.",
        "lines": [
            {
                "speaker": "rhogar_valeguard",
                "text": "Mercy is not softness. Not when given where anger has a claim.",
                "requires_flags": ["elira_mercy_blessing"],
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "I am not sure it was mercy. It may have been fear of becoming certain.",
                "requires_flags": ["elira_mercy_blessing"],
            },
            {
                "speaker": "rhogar_valeguard",
                "text": "Certainty has killed more prisoners than rage.",
                "requires_flags": ["elira_mercy_blessing"],
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "Then I will call doubt a guardrail and keep walking.",
                "requires_flags": ["elira_mercy_blessing"],
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "I keep hearing the bell from the shrine.",
                "requires_flags": ["elira_hard_verdict"],
            },
            {
                "speaker": "rhogar_valeguard",
                "text": "Because judgment leaves an echo.",
                "requires_flags": ["elira_hard_verdict"],
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "I thought a hard choice would feel cleaner.",
                "requires_flags": ["elira_hard_verdict"],
            },
            {
                "speaker": "rhogar_valeguard",
                "text": "Clean is not the same as just.",
                "requires_flags": ["elira_hard_verdict"],
            },
        ],
        "effects": [
            {
                "requires_flags": ["elira_mercy_blessing"],
                "set_flags": ["camp_faith_under_ash_mercy_processed"],
                "companion_deltas": {"elira_dawnmantle": 1, "rhogar_valeguard": 1},
                "player_statuses": {"blessed": 1},
                "journal": "Elira and Rhogar turned the Ashfall mercy choice into a shared defense against cruel certainty.",
            },
            {
                "requires_flags": ["elira_hard_verdict"],
                "set_flags": ["camp_faith_under_ash_verdict_processed"],
                "companion_deltas": {"rhogar_valeguard": 1},
                "flag_increments": {"act2_bonus_whisper_pressure": 1},
                "journal": "Elira and Rhogar named the cost of hard judgment under Ashfall; the choice will travel into later spiritual pressure.",
            },
        ],
    },
    {
        "id": "camp_banter_tolan_rhogar_ashfall",
        "title": "A Fort Pretending",
        "participants": ["tolan_ironshield", "rhogar_valeguard"],
        "requires_flags": ["ashfall_watch_cleared"],
        "priority": 68,
        "intro": "Ashfall's soot still clings to straps and buckles. Tolan and Rhogar speak as if scraping it off requires words.",
        "lines": [
            ("tolan_ironshield", "Ashfall was built like a threat pretending to be a fort."),
            ("rhogar_valeguard", "Then it fell like a fort pretending to be an oath."),
            ("tolan_ironshield", "That sounded clever. I am deciding whether to resent it."),
            ("rhogar_valeguard", "Take your time."),
            {
                "speaker": "tolan_ironshield",
                "text": "The prisoner line held.",
                "requires_flags": ["ashfall_prisoners_freed"],
            },
            {
                "speaker": "rhogar_valeguard",
                "text": "Because we treated it as the gate.",
                "requires_flags": ["ashfall_prisoners_freed"],
            },
            {
                "speaker": "rhogar_valeguard",
                "text": "We broke their command and still lost people.",
                "blocked_flags": ["ashfall_prisoners_freed"],
            },
            {
                "speaker": "tolan_ironshield",
                "text": "A victory can be true and still make you sick.",
                "blocked_flags": ["ashfall_prisoners_freed"],
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_ashfall_line_accounted"],
                "companion_deltas": {"tolan_ironshield": 1, "rhogar_valeguard": 1},
                "journal": "Tolan and Rhogar processed Ashfall as both a tactical victory and a moral ledger.",
                "player_statuses": {"guarded": 1},
            },
            {
                "requires_flags": ["ashfall_prisoners_freed"],
                "metric_deltas": {"act1_town_fear": -1},
            },
        ],
    },
    {
        "id": "camp_banter_bryn_kaelis_tresendar_eye",
        "title": "Secrets With Teeth",
        "participants": ["bryn_underbough", "kaelis_starling"],
        "requires_flags": ["tresendar_nothic_route"],
        "priority": 66,
        "intro": "Nobody says Cistern Eye first. Bryn loses the contest by making a face too obvious to ignore.",
        "lines": [
            ("bryn_underbough", "I prefer secrets with pockets."),
            ("kaelis_starling", "That thing had teeth where a secret should keep its door."),
            ("bryn_underbough", "Thank you for making my complaint worse."),
            ("kaelis_starling", "You are welcome."),
            {
                "speaker": "kaelis_starling",
                "text": "It learned something from us.",
                "requires_flag_values": {"tresendar_nothic_route": "bargain"},
            },
            {
                "speaker": "bryn_underbough",
                "text": "Everything does. The question is whether it paid.",
                "requires_flag_values": {"tresendar_nothic_route": "bargain"},
            },
            {
                "speaker": "bryn_underbough",
                "text": "Dead horrors tell fewer stories.",
                "requires_flag_values": {"tresendar_nothic_route": "kill"},
            },
            {
                "speaker": "kaelis_starling",
                "text": "Fewer is not none.",
                "requires_flag_values": {"tresendar_nothic_route": "kill"},
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_cistern_eye_warning"],
                "companion_deltas": {"bryn_underbough": 1, "kaelis_starling": 1},
                "journal": "Bryn and Kaelis marked the Cistern Eye as lingering truth-pressure, not just a dead or bargained monster.",
                "clues": ["The Cistern Eye's truths may keep echoing even after Duskmere Manor is cleared."],
            },
            {
                "requires_any_flag_values": {"tresendar_nothic_route": ["bargain", "trade"]},
                "flag_increments": {"act2_bonus_whisper_pressure": 1},
            },
        ],
    },
    {
        "id": "camp_banter_elira_tolan_after_varyn",
        "title": "The Bell After Varyn",
        "participants": ["elira_dawnmantle", "tolan_ironshield"],
        "requires_flags": ["varyn_body_defeated_act1"],
        "priority": 64,
        "intro": "After Varyn, the campfire burns lower than usual. Elira keeps glancing toward the road north.",
        "lines": [
            {
                "speaker": "tolan_ironshield",
                "text": "Town is bruised, not broken.",
                "requires_flag_values": {"act1_victory_tier": "clean_victory"},
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "And the bell can still be repaired.",
                "requires_flag_values": {"act1_victory_tier": "clean_victory"},
            },
            {
                "speaker": "tolan_ironshield",
                "text": "We won with our teeth clenched.",
                "requires_flag_values": {"act1_victory_tier": "costly_victory"},
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "Then we unclench them carefully. People mistake relief for healing.",
                "requires_flag_values": {"act1_victory_tier": "costly_victory"},
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "The road is open, but people look at it like a wound.",
                "requires_flag_values": {"act1_victory_tier": "fractured_victory"},
            },
            {
                "speaker": "tolan_ironshield",
                "text": "A wound can close wrong.",
                "requires_flag_values": {"act1_victory_tier": "fractured_victory"},
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "Then we do not pretend the scar is the cure.",
                "requires_flag_values": {"act1_victory_tier": "fractured_victory"},
            },
            ("tolan_ironshield", "You really mean to go back for that shrine."),
            ("elira_dawnmantle", "Yes. Promises get smaller if you leave them untended."),
        ],
        "effects": [
            {
                "set_flags": ["camp_varyn_victory_processed"],
                "companion_deltas": {"elira_dawnmantle": 1, "tolan_ironshield": 1},
                "journal": "Elira and Tolan tied Varyn's defeat back to the cracked luck bell and the obligation to repair what the road survived.",
            },
            {
                "requires_flag_values": {"act1_victory_tier": "clean_victory"},
                "flag_increments": {"act3_mercy_or_contradiction_count": 1},
            },
        ],
    },
    {
        "id": "camp_banter_nim_kaelis_maps_lie",
        "title": "Polite Suspicion",
        "participants": ["nim_ardentglass", "kaelis_starling"],
        "requires_any_flags": ["stonehollow_dig_cleared", "woodland_survey_cleared"],
        "priority": 62,
        "intro": "Nim spreads three maps by the fire. Kaelis immediately turns one upside down and improves it.",
        "lines": [
            ("nim_ardentglass", "A map lies when it is old, proud, copied badly, or paid for by a fool."),
            ("kaelis_starling", "A trail lies when someone wants you alive until the wrong bend."),
            ("nim_ardentglass", "So both our professions are mainly polite suspicion."),
            ("kaelis_starling", "Mine is not polite."),
            {
                "speaker": "nim_ardentglass",
                "text": "Stonehollow sat under bad math too long.",
                "requires_flag_values": {"act2_neglected_lead": "stonehollow_dig_cleared"},
            },
            {
                "speaker": "kaelis_starling",
                "text": "Then we stop trusting any line that wants to be finished for us.",
                "requires_flag_values": {"act2_neglected_lead": "stonehollow_dig_cleared"},
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_act2_map_suspicion"],
                "companion_deltas": {"nim_ardentglass": 1, "kaelis_starling": 1},
                "metric_deltas": {"act2_route_control": 1},
                "journal": "Nim and Kaelis compared map lies with trail lies, improving the party's route discipline.",
            }
        ],
    },
    {
        "id": "camp_banter_nim_bryn_false_ledgers",
        "title": "Bad Ledgers",
        "participants": ["nim_ardentglass", "bryn_underbough"],
        "requires_any_flags": ["miners_exchange_ledgers_checked", "bryn_false_ledgers_salted", "bryn_false_ledgers_exposed", "bryn_loose_ends_resolved"],
        "priority": 60,
        "intro": "Nim is annotating a ledger. Bryn is watching the margins more than the numbers.",
        "lines": [
            ("nim_ardentglass", "Bad ledgers have personalities."),
            ("bryn_underbough", "Good ledgers do too. Smug ones."),
            ("nim_ardentglass", "This one leaves room in the margins for a number it refuses to name."),
            ("bryn_underbough", "That is not accounting. That is bait."),
            {
                "speaker": "nim_ardentglass",
                "text": "There is a missing column in too many records.",
                "blocked_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "bryn_underbough",
                "text": "A column for what?",
                "blocked_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "nim_ardentglass",
                "text": "For what the record wants next.",
                "blocked_flags": ["malzurath_revealed"],
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_missing_ledger_column_noticed"],
                "companion_deltas": {"nim_ardentglass": 1, "bryn_underbough": 1},
                "metric_deltas": {"act2_route_control": 1},
                "clues": ["Nim and Bryn notice a recurring missing ledger column that behaves less like accounting and more like bait."],
                "journal": "Nim and Bryn made the campaign's ledger motif concrete without yet naming the hidden author behind it.",
                "companion_lore": {
                    "nim_ardentglass": "Nim has begun tracking the campaign's impossible ledgers as records that want future entries, not only records of the past.",
                    "bryn_underbough": "Bryn recognizes the missing ledger column as bait because it behaves like a smuggler's trap with better handwriting.",
                },
            }
        ],
    },
    {
        "id": "camp_banter_irielle_elira_after_adit",
        "title": "Someone Else's Voice",
        "participants": ["irielle_ashwake", "elira_dawnmantle"],
        "requires_flags": ["south_adit_cleared"],
        "priority": 58,
        "intro": "Irielle sits close enough to the fire to prove the cold is outside her. Elira lets her choose the first words.",
        "lines": [
            ("irielle_ashwake", "Do your prayers ever answer in someone else's voice?"),
            ("elira_dawnmantle", "No."),
            ("irielle_ashwake", "Good."),
            ("elira_dawnmantle", "Not because silence is proof of safety. Because a prayer should leave you more yourself, not less."),
            ("irielle_ashwake", "The Choir called that loneliness."),
            ("elira_dawnmantle", "The Choir lied."),
            {
                "speaker": "irielle_ashwake",
                "text": "You came before the voices learned everyone's names.",
                "requires_flag_values": {"act2_captive_outcome": "many_saved"},
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "Then we were lucky.",
                "requires_flag_values": {"act2_captive_outcome": "many_saved"},
            },
            {
                "speaker": "irielle_ashwake",
                "text": "No. Luck is when the door opens. Someone still has to walk through.",
                "requires_flag_values": {"act2_captive_outcome": "many_saved"},
            },
            {
                "speaker": "irielle_ashwake",
                "text": "You came late.",
                "requires_flag_values": {"act2_captive_outcome": "few_saved"},
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "Yes.",
                "requires_flag_values": {"act2_captive_outcome": "few_saved"},
            },
            {
                "speaker": "irielle_ashwake",
                "text": "Say it again.",
                "requires_flag_values": {"act2_captive_outcome": "few_saved"},
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "We came late.",
                "requires_flag_values": {"act2_captive_outcome": "few_saved"},
            },
            {
                "speaker": "irielle_ashwake",
                "text": "Good. Now it cannot grow teeth in the dark.",
                "requires_flag_values": {"act2_captive_outcome": "few_saved"},
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_adit_compassion_anchor"],
                "companion_deltas": {"irielle_ashwake": 1, "elira_dawnmantle": 1},
                "metric_deltas": {"act2_whisper_pressure": -1},
                "journal": "Irielle and Elira built a language for resisting the Choir: prayer and silence must leave a person more themselves, not less.",
            },
            {
                "requires_flag_values": {"act2_captive_outcome": "many_saved"},
                "flag_increments": {"act3_mercy_or_contradiction_count": 1},
            },
        ],
    },
    {
        "id": "camp_banter_irielle_nim_dangerous_theorem",
        "title": "A Blade Without A Handle",
        "participants": ["irielle_ashwake", "nim_ardentglass"],
        "requires_any_flags": ["forge_lens_mapped", "nim_countermeasure_notes", "nim_notes_burned"],
        "priority": 56,
        "intro": "Nim has a page open. Irielle has already decided whether she hates it.",
        "lines": [
            ("nim_ardentglass", "A dangerous theorem is not evil. It is a blade without a handle."),
            ("irielle_ashwake", "The Choir says the same thing before handing someone the sharp end."),
            ("nim_ardentglass", "That is a fair objection and a devastating image."),
            ("irielle_ashwake", "Do not admire it."),
            ("nim_ardentglass", "Too late, but I will behave."),
            {
                "speaker": "irielle_ashwake",
                "text": "You kept the pages.",
                "requires_flags": ["nim_countermeasure_notes"],
            },
            {
                "speaker": "nim_ardentglass",
                "text": "I kept responsibility for them.",
                "requires_flags": ["nim_countermeasure_notes"],
            },
            {
                "speaker": "irielle_ashwake",
                "text": "Pages do not care who feels responsible.",
                "requires_flags": ["nim_countermeasure_notes"],
            },
            {
                "speaker": "nim_ardentglass",
                "text": "I can still feel where the missing proof should sit.",
                "requires_flags": ["nim_notes_burned"],
            },
            {
                "speaker": "irielle_ashwake",
                "text": "Good. Let it ache. An ache is better than an altar.",
                "requires_flags": ["nim_notes_burned"],
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_dangerous_theorem_debated"],
                "journal": "Nim and Irielle debated whether dangerous knowledge can be kept without becoming an altar.",
            },
            {
                "requires_flags": ["nim_countermeasure_notes"],
                "companion_deltas": {"nim_ardentglass": 1, "irielle_ashwake": -1},
                "metric_deltas": {"act2_route_control": 1},
            },
            {
                "requires_flags": ["nim_notes_burned"],
                "companion_deltas": {"irielle_ashwake": 1},
                "metric_deltas": {"act2_whisper_pressure": -1},
            },
        ],
    },
    {
        "id": "camp_banter_irielle_rhogar_chosen_certainty",
        "title": "Chosen Certainty",
        "participants": ["irielle_ashwake", "rhogar_valeguard"],
        "requires_flags": ["south_adit_cleared"],
        "priority": 54,
        "intro": "Irielle watches Rhogar polish a blade with the wary focus of someone deciding whether certainty is safe.",
        "lines": [
            ("irielle_ashwake", "You sound certain when you speak."),
            ("rhogar_valeguard", "I try to sound accountable."),
            ("irielle_ashwake", "The Choir was certain."),
            ("rhogar_valeguard", "The Choir demanded surrender. An oath demands return."),
            ("irielle_ashwake", "Return to what?"),
            ("rhogar_valeguard", "The person who must answer for what the oath has done."),
            {
                "speaker": "irielle_ashwake",
                "text": "Certainty is louder when the whispers are near.",
                "min_flags": {"act2_whisper_pressure": 4},
            },
            {
                "speaker": "rhogar_valeguard",
                "text": "Then I will speak less and stand better.",
                "min_flags": {"act2_whisper_pressure": 4},
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_chosen_certainty_named"],
                "companion_deltas": {"irielle_ashwake": 1, "rhogar_valeguard": 1},
                "journal": "Irielle and Rhogar distinguished chosen oath from imposed certainty.",
                "player_statuses": {"blessed": 1},
            },
            {
                "min_flags": {"act2_whisper_pressure": 4},
                "metric_deltas": {"act2_whisper_pressure": -1},
            },
        ],
    },
    {
        "id": "camp_banter_nim_tolan_shield_map",
        "title": "Make Here Matter",
        "participants": ["nim_ardentglass", "tolan_ironshield"],
        "requires_any_flags": ["broken_prospect_cleared", "wave_echo_outer_cleared"],
        "priority": 52,
        "intro": "Nim sketches a route. Tolan immediately puts a cup on the most dangerous part of it.",
        "lines": [
            ("nim_ardentglass", "A shield is a map with one instruction."),
            ("tolan_ironshield", "Stand here?"),
            ("nim_ardentglass", "More precisely, make here matter."),
            ("tolan_ironshield", "I have heard worse from officers."),
            ("nim_ardentglass", "That is either praise or an indictment of officers."),
            ("tolan_ironshield", "Both, lad."),
            {
                "speaker": "tolan_ironshield",
                "text": "We saved the route and paid in faces.",
                "requires_flag_values": {"act2_first_late_route": "broken_prospect"},
            },
            {
                "speaker": "nim_ardentglass",
                "text": "A map that costs people is not finished.",
                "requires_flag_values": {"act2_first_late_route": "broken_prospect"},
            },
            {
                "speaker": "nim_ardentglass",
                "text": "We saved the captives and let the route harden.",
                "requires_flag_values": {"act2_first_late_route": "south_adit"},
            },
            {
                "speaker": "tolan_ironshield",
                "text": "Then the route gets a shield next.",
                "requires_flag_values": {"act2_first_late_route": "south_adit"},
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_shield_map_doctrine"],
                "companion_deltas": {"nim_ardentglass": 1, "tolan_ironshield": 1},
                "journal": "Nim and Tolan turned maps and shield work into one doctrine: make the dangerous place matter on your terms.",
            },
            {
                "requires_flag_values": {"act2_first_late_route": "broken_prospect"},
                "metric_deltas": {"act2_route_control": 1},
            },
            {
                "requires_flag_values": {"act2_first_late_route": "south_adit"},
                "metric_deltas": {"act2_town_stability": 1},
            },
        ],
    },
    {
        "id": "camp_banter_bryn_elira_route_displacement",
        "title": "Roads With Intentions",
        "participants": ["bryn_underbough", "elira_dawnmantle"],
        "requires_flags": ["act3_started", "varyn_route_displaced"],
        "priority": 48,
        "intro": "Bryn will not put the map too close to the fire. Elira does not ask why.",
        "lines": [
            {
                "speaker": "bryn_underbough",
                "text": "I hate a door that remembers where you meant to go.",
                "blocked_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "Roads should not have intentions.",
                "blocked_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "bryn_underbough",
                "text": "Exactly. Roads should be dirt with aspirations.",
                "blocked_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "And yet this one feels disappointed when we choose.",
                "blocked_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "bryn_underbough",
                "text": "Do not say that near the map.",
                "blocked_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "Varyn sorted roads. Malzurath sorts meaning.",
                "requires_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "bryn_underbough",
                "text": "I miss when our villains had normal hobbies.",
                "requires_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "elira_dawnmantle",
                "text": "He made cruelty look like administration.",
                "requires_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "bryn_underbough",
                "text": "Then we make mercy look like sabotage.",
                "requires_flags": ["malzurath_revealed"],
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_route_displacement_named"],
                "companion_deltas": {"bryn_underbough": 1, "elira_dawnmantle": 1},
                "journal": "Bryn and Elira named the road displacement as intentional without exposing the secret architect before the reveal.",
            },
            {
                "requires_flags": ["malzurath_revealed"],
                "flag_increments": {"act3_companion_testimony_count": 1, "act3_mercy_or_contradiction_count": 1},
                "clues": ["Bryn and Elira can testify that mercy itself has become a way to contradict Malzurath's sorting logic."],
            },
        ],
    },
    {
        "id": "camp_banter_nim_irielle_ninth_ledger",
        "title": "The Ninth Column",
        "participants": ["nim_ardentglass", "irielle_ashwake"],
        "requires_any_flags": ["act3_ninth_ledger_opened", "act3_ninth_column_seen", "malzurath_revealed"],
        "priority": 46,
        "intro": "Nim has stopped calling the extra mark a notation. Irielle has stopped letting him stare at it alone.",
        "lines": [
            {
                "speaker": "nim_ardentglass",
                "text": "The ninth column is not a sum. It is an appetite.",
                "blocked_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "irielle_ashwake",
                "text": "Do not give it a body before we know where it keeps its mouth.",
                "blocked_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "nim_ardentglass",
                "text": "That may be the most academically useful threat I have ever received.",
                "blocked_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "irielle_ashwake",
                "text": "It was advice.",
                "blocked_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "nim_ardentglass",
                "text": "Malzurath did not forge a ledger to describe reality. He forged one to make reality behave.",
                "requires_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "irielle_ashwake",
                "text": "The Choir listened for him without knowing whose ear they were feeding.",
                "requires_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "nim_ardentglass",
                "text": "Varyn's routes, Caldra's resonance, the copied claims, the missing column...",
                "requires_flags": ["malzurath_revealed"],
            },
            {
                "speaker": "irielle_ashwake",
                "text": "All practice for being filed.",
                "requires_flags": ["malzurath_revealed"],
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_ninth_column_theory"],
                "companion_deltas": {"nim_ardentglass": 1, "irielle_ashwake": 1},
                "journal": "Nim and Irielle advanced the ninth-column theory while preserving the reveal boundary if Malzurath is not yet known.",
                "companion_lore": {
                    "nim_ardentglass": "Nim's ninth-column theory becomes his way of understanding the Ledger as an appetite disguised as notation.",
                    "irielle_ashwake": "Irielle treats every attempt to give the ninth column a shape as dangerous until the party knows whose mouth it serves.",
                },
            },
            {
                "requires_flags": ["malzurath_revealed"],
                "flag_increments": {"act3_companion_testimony_count": 1, "act3_reveal_resistance_bonus": 1},
                "clues": ["Nim and Irielle can testify that the Quiet Choir and Varyn were both feeding Malzurath's Ledger logic."],
            },
        ],
    },
    {
        "id": "camp_banter_tolan_rhogar_recorded_routes",
        "title": "The Hand That Holds The Pen",
        "participants": ["tolan_ironshield", "rhogar_valeguard"],
        "requires_flags": ["malzurath_revealed"],
        "priority": 44,
        "intro": "Tolan and Rhogar sit shoulder to shoulder, both studying a threat neither can simply stand in front of.",
        "lines": [
            ("tolan_ironshield", "I can fight a tyrant. I can fight a dragon. I dislike fighting bookkeeping."),
            ("rhogar_valeguard", "Then we fight the hand that holds the pen."),
            ("tolan_ironshield", "And if the page already has us?"),
            ("rhogar_valeguard", "A record is not an oath."),
            ("tolan_ironshield", "Good. Because I did not sign."),
            {
                "speaker": "rhogar_valeguard",
                "text": "He will count the people we saved as proof we can be steered.",
                "requires_flag_values": {"act1_victory_tier": "clean_victory"},
            },
            {
                "speaker": "tolan_ironshield",
                "text": "Then he has mistaken survivors for sheep.",
                "requires_flag_values": {"act1_victory_tier": "clean_victory"},
            },
            {
                "speaker": "tolan_ironshield",
                "text": "He will count every loss.",
                "requires_flag_values": {"act1_victory_tier": "fractured_victory"},
            },
            {
                "speaker": "rhogar_valeguard",
                "text": "So will we. But not for the same reason.",
                "requires_flag_values": {"act1_victory_tier": "fractured_victory"},
            },
        ],
        "effects": [
            {
                "set_flags": ["camp_recorded_routes_defied"],
                "companion_deltas": {"tolan_ironshield": 1, "rhogar_valeguard": 1},
                "flag_increments": {"act3_companion_testimony_count": 1},
                "journal": "Tolan and Rhogar rejected Malzurath's premise that recorded action can replace chosen duty.",
                "player_statuses": {"guarded": 1},
            }
        ],
    },
    {
        "id": "camp_banter_full_party_before_secret_act4_nim_irielle",
        "title": "The Shape Of The Ending",
        "participants": ["nim_ardentglass", "irielle_ashwake", "elira_dawnmantle", "bryn_underbough"],
        "requires_flags": ["malzurath_revealed", "act3_ninth_ledger_opened"],
        "priority": 40,
        "intro": "The campfire gutters low enough that everyone can see the blank places on the map.",
        "lines": [
            ("nim_ardentglass", "The ledger does not end at the villain's defeat."),
            ("irielle_ashwake", "It wants the shape of the ending."),
            ("elira_dawnmantle", "Then we deny it certainty."),
            ("bryn_underbough", "I can steal certainty."),
            ("nim_ardentglass", "Can you?"),
            ("bryn_underbough", "No, but it sounded braver than panic creatively."),
        ],
        "effects": [
            {
                "set_flags": ["camp_secret_act4_margin_seeded"],
                "flag_increments": {"act3_companion_testimony_count": 2, "act3_mercy_or_contradiction_count": 1},
                "journal": "The party began to suspect the Ledger wants to own not only events, but the shape of the ending itself.",
                "clues": ["A secret path may depend on companions contradicting the Ledger's preferred ending together."],
            }
        ],
    },
]
