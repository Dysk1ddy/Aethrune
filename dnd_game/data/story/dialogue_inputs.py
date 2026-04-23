from __future__ import annotations


DIALOGUE_INPUTS: list[dict[str, object]] = [
    {
        "id": "dialogue_input_bryn_phandalin_arrival_insight",
        "topic_keys": ["phandalin_arrival_insight"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["bryn_underbough"],
        "priority": 92,
        "lines": [
            (
                "bryn_underbough",
                "Nobody here is relaxed. They are only deciding which fear gets to speak first.",
            )
        ],
    },
    {
        "id": "dialogue_input_elira_phandalin_arrival_insight",
        "topic_keys": ["phandalin_arrival_insight"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["elira_dawnmantle"],
        "priority": 90,
        "lines": [
            (
                "elira_dawnmantle",
                "Fear makes triage out of whole streets if you let it. Start with the wound everyone keeps looking away from.",
            )
        ],
    },
    {
        "id": "dialogue_input_rhogar_phandalin_arrival_persuasion",
        "topic_keys": ["phandalin_arrival_persuasion"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["rhogar_valeguard"],
        "priority": 88,
        "lines": [
            (
                "rhogar_valeguard",
                "Say Greywake sent help, then make the help visible. A banner without a shield is just cloth.",
            )
        ],
    },
    {
        "id": "dialogue_input_tolan_phandalin_arrival_persuasion",
        "topic_keys": ["phandalin_arrival_persuasion"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["tolan_ironshield"],
        "priority": 86,
        "lines": [
            (
                "tolan_ironshield",
                "Promises are cheaper than shutters. Let them see where you mean to stand.",
            )
        ],
    },
    {
        "id": "dialogue_input_kaelis_phandalin_arrival_investigation",
        "topic_keys": ["phandalin_arrival_investigation"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["kaelis_starling"],
        "priority": 88,
        "lines": [
            (
                "kaelis_starling",
                "Those barricades point inward as much as out. The town is already defending against itself.",
            )
        ],
    },
    {
        "id": "dialogue_input_bryn_phandalin_arrival_investigation",
        "topic_keys": ["phandalin_arrival_investigation"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["bryn_underbough"],
        "priority": 84,
        "lines": [
            (
                "bryn_underbough",
                "The tracks are not random. Someone taught wagons to avoid the same corners twice.",
            )
        ],
    },
    {
        "id": "dialogue_input_tolan_barthen_shortage",
        "topic_keys": ["barthen_shortage"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["tolan_ironshield"],
        "priority": 90,
        "lines": [
            (
                "tolan_ironshield",
                "Empty shelves are a siege by another name. Break the road pressure before folk start bargaining with hunger.",
            )
        ],
    },
    {
        "id": "dialogue_input_bryn_barthen_shortage",
        "topic_keys": ["barthen_shortage"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["bryn_underbough"],
        "priority": 86,
        "lines": [
            (
                "bryn_underbough",
                "Roads fail quietly first. A missed sack, a smaller supper, then everyone acts surprised when desperation learns to shout.",
            )
        ],
    },
    {
        "id": "dialogue_input_elira_barthen_shortage",
        "topic_keys": ["barthen_shortage"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["elira_dawnmantle"],
        "priority": 84,
        "lines": [
            (
                "elira_dawnmantle",
                "Bandages running thin means the next mercy has to choose. I hate choices like that.",
            )
        ],
    },
    {
        "id": "dialogue_input_kaelis_lionshield_trade",
        "topic_keys": ["lionshield_trade"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["kaelis_starling"],
        "priority": 90,
        "lines": [
            (
                "kaelis_starling",
                "Caravans changing route leave patterns. If the Brand knows which wagons hurt most, someone is feeding them more than rumor.",
            )
        ],
    },
    {
        "id": "dialogue_input_rhogar_lionshield_trade",
        "topic_keys": ["lionshield_trade"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["rhogar_valeguard"],
        "priority": 88,
        "lines": [
            (
                "rhogar_valeguard",
                "Trade is not just coin. It is whether a frightened family believes tomorrow has flour and nails in it.",
            )
        ],
    },
    {
        "id": "dialogue_input_tolan_lionshield_trade",
        "topic_keys": ["lionshield_trade"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["tolan_ironshield"],
        "priority": 84,
        "lines": [
            (
                "tolan_ironshield",
                "Guard prices rise when roads rot. That makes fear profitable. Someone always notices.",
            )
        ],
    },
    {
        "id": "dialogue_input_elira_steward_vow",
        "topic_keys": ["steward_vow"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["elira_dawnmantle"],
        "priority": 90,
        "lines": [
            (
                "elira_dawnmantle",
                "Then make the vow small enough to keep today and strong enough to repeat tomorrow.",
            )
        ],
    },
    {
        "id": "dialogue_input_rhogar_steward_vow",
        "topic_keys": ["steward_vow"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["rhogar_valeguard"],
        "priority": 88,
        "lines": [
            (
                "rhogar_valeguard",
                "Good. Let the words bind your feet before they decorate your mouth.",
            )
        ],
    },
    {
        "id": "dialogue_input_tolan_steward_blackwake_rescue",
        "topic_keys": ["steward_blackwake"],
        "scene_keys": ["phandalin_hub"],
        "requires_flag_values": {"blackwake_resolution": "rescue"},
        "requires_companions": ["tolan_ironshield"],
        "priority": 92,
        "lines": [
            (
                "tolan_ironshield",
                "People first was the right call. Living witnesses carry truth farther than any seal.",
            )
        ],
    },
    {
        "id": "dialogue_input_kaelis_steward_blackwake_evidence",
        "topic_keys": ["steward_blackwake"],
        "scene_keys": ["phandalin_hub"],
        "requires_flag_values": {"blackwake_resolution": "evidence"},
        "requires_companions": ["kaelis_starling"],
        "priority": 92,
        "lines": [
            (
                "kaelis_starling",
                "False seals explain too much. The road was not being preyed on; it was being administered.",
            )
        ],
    },
    {
        "id": "dialogue_input_bryn_steward_blackwake_sabotage",
        "topic_keys": ["steward_blackwake"],
        "scene_keys": ["phandalin_hub"],
        "requires_flag_values": {"blackwake_resolution": "sabotage"},
        "requires_companions": ["bryn_underbough"],
        "priority": 92,
        "lines": [
            (
                "bryn_underbough",
                "Burning the cache kicked a chair out from under their table. Nice. Now find who built the table.",
            )
        ],
    },
    {
        "id": "dialogue_input_kaelis_stonehill_recruit_bryn",
        "topic_keys": ["stonehill_recruit_bryn"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["kaelis_starling"],
        "priority": 90,
        "lines": [
            (
                "kaelis_starling",
                "She has counted every exit and still stayed in the room. That is not nothing.",
            )
        ],
    },
    {
        "id": "dialogue_input_elira_stonehill_recruit_bryn",
        "topic_keys": ["stonehill_recruit_bryn"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["elira_dawnmantle"],
        "priority": 88,
        "lines": [
            (
                "elira_dawnmantle",
                "She is afraid in the practical way. Respect that, and she may trust the risk.",
            )
        ],
    },
    {
        "id": "dialogue_input_tolan_stonehill_recruit_bryn_second",
        "topic_keys": ["stonehill_recruit_bryn_second"],
        "scene_keys": ["phandalin_hub"],
        "max_act": 1,
        "requires_companions": ["tolan_ironshield"],
        "priority": 90,
        "lines": [
            (
                "tolan_ironshield",
                "Listening is not soft. It is how you learn which line needs holding.",
            )
        ],
    },
    {
        "id": "dialogue_input_rhogar_claims_council_opening",
        "topic_keys": ["act2_claims_council_opening"],
        "scene_keys": ["act2_claims_council"],
        "min_act": 2,
        "requires_companions": ["rhogar_valeguard"],
        "priority": 98,
        "lines": [
            (
                "rhogar_valeguard",
                "If this room wants a claim, make it name who the claim protects.",
            )
        ],
    },
    {
        "id": "dialogue_input_tolan_claims_council_opening",
        "topic_keys": ["act2_claims_council_opening"],
        "scene_keys": ["act2_claims_council"],
        "min_act": 2,
        "requires_companions": ["tolan_ironshield"],
        "priority": 94,
        "lines": [
            (
                "tolan_ironshield",
                "Maps are useful. So are hands to carry the wounded when a map turns greedy.",
            )
        ],
    },
    {
        "id": "dialogue_input_bryn_claims_council_opening",
        "topic_keys": ["act2_claims_council_opening"],
        "scene_keys": ["act2_claims_council"],
        "min_act": 2,
        "requires_companions": ["bryn_underbough"],
        "priority": 92,
        "lines": [
            (
                "bryn_underbough",
                "Everyone here says route like it means road. Half of them mean ownership and the other half mean escape.",
            )
        ],
    },
    {
        "id": "dialogue_input_elira_claims_council_opening",
        "topic_keys": ["act2_claims_council_opening"],
        "scene_keys": ["act2_claims_council"],
        "min_act": 2,
        "requires_companions": ["elira_dawnmantle"],
        "priority": 90,
        "lines": [
            (
                "elira_dawnmantle",
                "The cave will not become safer because we call hunger opportunity.",
            )
        ],
    },
    {
        "id": "dialogue_input_bryn_sponsor_exchange",
        "topic_keys": ["act2_sponsor_exchange"],
        "scene_keys": ["act2_claims_council"],
        "min_act": 2,
        "requires_companions": ["bryn_underbough"],
        "priority": 94,
        "lines": [
            (
                "bryn_underbough",
                "Halia will move fast. Fast gets answers. Fast also forgets who got stepped over unless somebody keeps counting.",
            )
        ],
    },
    {
        "id": "dialogue_input_tolan_sponsor_lionshield",
        "topic_keys": ["act2_sponsor_lionshield"],
        "scene_keys": ["act2_claims_council"],
        "min_act": 2,
        "requires_companions": ["tolan_ironshield"],
        "priority": 94,
        "lines": [
            (
                "tolan_ironshield",
                "Linene thinks in pallets, watch shifts, and clean road time. Good. A route needs bones before it needs speeches.",
            )
        ],
    },
    {
        "id": "dialogue_input_elira_sponsor_wardens",
        "topic_keys": ["act2_sponsor_wardens"],
        "scene_keys": ["act2_claims_council"],
        "min_act": 2,
        "requires_companions": ["elira_dawnmantle"],
        "priority": 96,
        "lines": [
            (
                "elira_dawnmantle",
                "Caution is not fear when it keeps a name from becoming an item on a list.",
            )
        ],
    },
    {
        "id": "dialogue_input_rhogar_sponsor_wardens",
        "topic_keys": ["act2_sponsor_wardens"],
        "scene_keys": ["act2_claims_council"],
        "min_act": 2,
        "requires_companions": ["rhogar_valeguard"],
        "priority": 92,
        "lines": [
            (
                "rhogar_valeguard",
                "A warden plan asks everyone to move at the speed of the vulnerable. That is harder than charging.",
            )
        ],
    },
    {
        "id": "dialogue_input_elira_hub_agatha",
        "topic_keys": ["act2_hub_agatha"],
        "scene_keys": ["act2_expedition_hub"],
        "min_act": 2,
        "requires_companions": ["elira_dawnmantle"],
        "priority": 94,
        "lines": [
            (
                "elira_dawnmantle",
                "Agatha is not a shortcut. Go as if a grief is giving testimony, not as if a ghost owes you answers.",
            )
        ],
    },
    {
        "id": "dialogue_input_kaelis_hub_wood",
        "topic_keys": ["act2_hub_wood"],
        "scene_keys": ["act2_expedition_hub"],
        "min_act": 2,
        "requires_companions": ["kaelis_starling"],
        "priority": 94,
        "lines": [
            (
                "kaelis_starling",
                "A sabotaged survey still tells the truth if you read the cuts. Whoever edited the camp left fingerprints in the damage.",
            )
        ],
    },
    {
        "id": "dialogue_input_tolan_hub_stonehollow",
        "topic_keys": ["act2_hub_stonehollow"],
        "scene_keys": ["act2_expedition_hub"],
        "min_act": 2,
        "requires_companions": ["tolan_ironshield"],
        "priority": 94,
        "lines": [
            (
                "tolan_ironshield",
                "Dig sites collapse when everyone argues over depth and nobody watches the braces. Bring people out before bringing theories back.",
            )
        ],
    },
    {
        "id": "dialogue_input_bryn_hub_midpoint",
        "topic_keys": ["act2_hub_midpoint"],
        "scene_keys": ["act2_expedition_hub"],
        "min_act": 2,
        "requires_companions": ["bryn_underbough"],
        "priority": 94,
        "lines": [
            (
                "bryn_underbough",
                "If we let the last lead go dark, assume the dark learns our names. Pick the cost with open eyes.",
            )
        ],
    },
    {
        "id": "dialogue_input_nim_hub_broken_prospect",
        "topic_keys": ["act2_hub_broken_prospect"],
        "scene_keys": ["act2_expedition_hub"],
        "min_act": 2,
        "requires_companions": ["nim_ardentglass"],
        "priority": 94,
        "lines": [
            (
                "nim_ardentglass",
                "Broken Prospect may be cleaner, which means it will tempt everyone into calling clean the same thing as safe. It is not.",
            )
        ],
    },
    {
        "id": "dialogue_input_irielle_hub_south_adit",
        "topic_keys": ["act2_hub_south_adit"],
        "scene_keys": ["act2_expedition_hub"],
        "min_act": 2,
        "requires_companions": ["irielle_ashwake"],
        "priority": 96,
        "lines": [
            (
                "irielle_ashwake",
                "Prison lines teach silence as obedience. If you go there, break the lesson first.",
            )
        ],
    },
    {
        "id": "dialogue_input_nim_hub_outer",
        "topic_keys": ["act2_hub_outer"],
        "scene_keys": ["act2_expedition_hub"],
        "min_act": 2,
        "requires_companions": ["nim_ardentglass"],
        "priority": 92,
        "lines": [
            (
                "nim_ardentglass",
                "Old galleries lie by echo and angle. If the walls repeat you too clearly, trust the second answer less.",
            )
        ],
    },
    {
        "id": "dialogue_input_elira_hub_causeway",
        "topic_keys": ["act2_hub_causeway"],
        "scene_keys": ["act2_expedition_hub"],
        "min_act": 2,
        "requires_companions": ["elira_dawnmantle"],
        "priority": 92,
        "lines": [
            (
                "elira_dawnmantle",
                "A drowned shrine is still a shrine if someone refuses to let the water have the last word.",
            )
        ],
    },
    {
        "id": "dialogue_input_irielle_hub_forge",
        "topic_keys": ["act2_hub_forge"],
        "scene_keys": ["act2_expedition_hub"],
        "min_act": 2,
        "requires_companions": ["irielle_ashwake"],
        "priority": 98,
        "lines": [
            (
                "irielle_ashwake",
                "The Forge will sound like certainty. Certainty is the Choir's favorite mask.",
            )
        ],
    },
    {
        "id": "dialogue_input_elira_conyberry_entry",
        "topic_keys": ["act2_conyberry_entry"],
        "scene_keys": ["conyberry_agatha"],
        "min_act": 2,
        "requires_companions": ["elira_dawnmantle"],
        "priority": 94,
        "lines": [
            (
                "elira_dawnmantle",
                "Ask cleanly. The dead can tell when the living arrive already rehearsing what they want to hear.",
            )
        ],
    },
    {
        "id": "dialogue_input_rhogar_conyberry_entry",
        "topic_keys": ["act2_conyberry_entry"],
        "scene_keys": ["conyberry_agatha"],
        "min_act": 2,
        "requires_companions": ["rhogar_valeguard"],
        "priority": 90,
        "lines": [
            (
                "rhogar_valeguard",
                "A vow broken loudly can still be answered quietly. Give her room to speak before you ask her to forgive the living.",
            )
        ],
    },
    {
        "id": "dialogue_input_kaelis_wood_entry",
        "topic_keys": ["act2_wood_entry"],
        "scene_keys": ["neverwinter_wood_survey_camp"],
        "min_act": 2,
        "requires_companions": ["kaelis_starling"],
        "priority": 94,
        "lines": [
            (
                "kaelis_starling",
                "Cut posts, spoiled stores, low survey strings. Saboteurs love damage that looks like incompetence.",
            )
        ],
    },
    {
        "id": "dialogue_input_bryn_wood_entry_delayed",
        "topic_keys": ["act2_wood_entry"],
        "scene_keys": ["neverwinter_wood_survey_camp"],
        "min_act": 2,
        "requires_flag_values": {"act2_neglected_lead": "woodland_survey_cleared"},
        "requires_companions": ["bryn_underbough"],
        "priority": 98,
        "lines": [
            (
                "bryn_underbough",
                "Late work has a smell. Smoke, panic, and people trying to make yesterday look unavoidable.",
            )
        ],
    },
    {
        "id": "dialogue_input_tolan_stonehollow_entry",
        "topic_keys": ["act2_stonehollow_entry"],
        "scene_keys": ["stonehollow_dig"],
        "min_act": 2,
        "requires_companions": ["tolan_ironshield"],
        "priority": 94,
        "lines": [
            (
                "tolan_ironshield",
                "Brace first, blame later. If scholars are alive, the dig is a rescue before it is evidence.",
            )
        ],
    },
    {
        "id": "dialogue_input_nim_stonehollow_entry",
        "topic_keys": ["act2_stonehollow_entry"],
        "scene_keys": ["stonehollow_dig"],
        "min_act": 2,
        "requires_companions": ["nim_ardentglass"],
        "priority": 90,
        "lines": [
            (
                "nim_ardentglass",
                "The ward-lines are coughing in three different dialects. That is a technical term for 'please do not touch that beam.'",
            )
        ],
    },
    {
        "id": "dialogue_input_elira_midpoint_counsel",
        "topic_keys": ["act2_midpoint_counsel"],
        "scene_keys": ["act2_midpoint_convergence"],
        "min_act": 2,
        "requires_companions": ["elira_dawnmantle"],
        "priority": 98,
        "lines": [
            (
                "elira_dawnmantle",
                "If the shrine lane breaks, every argument in the hall becomes uglier by morning.",
            )
        ],
    },
    {
        "id": "dialogue_input_bryn_midpoint_counsel",
        "topic_keys": ["act2_midpoint_counsel"],
        "scene_keys": ["act2_midpoint_convergence"],
        "min_act": 2,
        "requires_companions": ["bryn_underbough"],
        "priority": 96,
        "lines": [
            (
                "bryn_underbough",
                "Sabotage wants you chasing noise. Find what gets quieter when the lamps go out.",
            )
        ],
    },
    {
        "id": "dialogue_input_rhogar_midpoint_counsel",
        "topic_keys": ["act2_midpoint_counsel"],
        "scene_keys": ["act2_midpoint_convergence"],
        "min_act": 2,
        "requires_companions": ["rhogar_valeguard"],
        "priority": 94,
        "lines": [
            (
                "rhogar_valeguard",
                "The center matters. When a town sees its own table hold, panic has fewer places to recruit.",
            )
        ],
    },
    {
        "id": "dialogue_input_elira_south_adit_entry",
        "topic_keys": ["act2_south_adit_entry"],
        "scene_keys": ["south_adit"],
        "min_act": 2,
        "requires_companions": ["elira_dawnmantle"],
        "priority": 96,
        "lines": [
            (
                "elira_dawnmantle",
                "We rescue weakest first. A prison line is built to punish compassion; all that means is we make compassion disciplined.",
            )
        ],
    },
    {
        "id": "dialogue_input_irielle_south_adit_entry",
        "topic_keys": ["act2_south_adit_entry"],
        "scene_keys": ["south_adit"],
        "min_act": 2,
        "requires_companions": ["irielle_ashwake"],
        "priority": 98,
        "lines": [
            (
                "irielle_ashwake",
                "That rhythm in the locks is not habit. It is conditioning.",
            )
        ],
    },
    {
        "id": "dialogue_input_nim_black_lake_entry",
        "topic_keys": ["act2_black_lake_entry"],
        "scene_keys": ["black_lake_causeway"],
        "min_act": 2,
        "requires_companions": ["nim_ardentglass"],
        "priority": 92,
        "lines": [
            (
                "nim_ardentglass",
                "Causeways are arguments with water. This one is losing and pretending it is fine.",
            )
        ],
    },
    {
        "id": "dialogue_input_elira_black_lake_entry",
        "topic_keys": ["act2_black_lake_entry"],
        "scene_keys": ["black_lake_causeway"],
        "min_act": 2,
        "requires_companions": ["elira_dawnmantle"],
        "priority": 90,
        "lines": [
            (
                "elira_dawnmantle",
                "That shrine drowned slowly. We have at least one answer to give it.",
            )
        ],
    },
    {
        "id": "dialogue_input_irielle_forge_entry",
        "topic_keys": ["act2_forge_entry"],
        "scene_keys": ["forge_of_spells"],
        "min_act": 2,
        "requires_companions": ["irielle_ashwake"],
        "priority": 100,
        "lines": [
            (
                "irielle_ashwake",
                "Do not let her speak uninterrupted. The Choir is weakest when certainty has to breathe between sentences.",
            )
        ],
    },
    {
        "id": "dialogue_input_nim_forge_entry",
        "topic_keys": ["act2_forge_entry"],
        "scene_keys": ["forge_of_spells"],
        "min_act": 2,
        "requires_companions": ["nim_ardentglass"],
        "priority": 96,
        "lines": [
            (
                "nim_ardentglass",
                "The Forge was made to shape possibility. Caldra is using it to narrow people down.",
            )
        ],
    },
    {
        "id": "dialogue_input_elira_forge_entry",
        "topic_keys": ["act2_forge_entry"],
        "scene_keys": ["forge_of_spells"],
        "min_act": 2,
        "requires_companions": ["elira_dawnmantle"],
        "priority": 94,
        "lines": [
            (
                "elira_dawnmantle",
                "If she calls suffering clarity, answer with every life she tried to reduce to a lesson.",
            )
        ],
    },
    {
        "id": "dialogue_input_rhogar_forge_entry",
        "topic_keys": ["act2_forge_entry"],
        "scene_keys": ["forge_of_spells"],
        "min_act": 2,
        "requires_companions": ["rhogar_valeguard"],
        "priority": 92,
        "lines": [
            (
                "rhogar_valeguard",
                "Then let the final answer be chosen, spoken, and stood behind.",
            )
        ],
    },
]
