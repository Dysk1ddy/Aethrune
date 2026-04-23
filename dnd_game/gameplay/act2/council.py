from __future__ import annotations


class StoryAct2CouncilMixin:
    def start_act2_scaffold(self) -> None:
        assert self.state is not None
        self.state.current_act = 2
        self.state.flags["act2_started"] = True
        self.state.flags["act2_scaffold_enabled"] = True
        self.act2_initialize_metrics()
        self.act2_initialize_blackwake_callbacks()
        self.state.current_scene = "act2_claims_council"
        self.add_journal(
            "Act 2 begins with a claims war around the Resonant Vaults, a town trying to stay intact, and a cult using the mine's old song as a listening tool."
        )

    def scene_act1_complete(self) -> None:
        assert self.state is not None
        while True:
            self.banner("Act I Complete")
            self.say(
                "Iron Hollow survives Act I, but the victory only tears the lid off a deeper problem. Act 2 now tracks town stability, route control, sponsor politics, "
                "companion side decisions, and how much of the Quiet Choir's whisper-pressure you let leak into the region.",
                typed=True,
            )
            choice = self.choose(
                "What next?",
                [
                    "Continue into the Act II scaffold",
                    "Review the party",
                    "Return to the title screen",
                ],
                allow_meta=False,
            )
            if choice == 1:
                self.start_act2_scaffold()
                return
            if choice == 2:
                self.show_party()
                continue
            self.state = None
            return

    def scene_act2_claims_council(self) -> None:
        assert self.state is not None
        self.banner("Iron Hollow Claims Council")
        self.say(
            "A night after Varyn falls, Ashlamp Inn turns into a claims chamber. Mud-stained maps cover tables meant for ale, miners and merchants try to sound rational "
            "about a mine they have not yet entered, and every survivor from Act 1 understands that what comes next will decide whether Iron Hollow grows, hardens, or tears itself apart.",
            typed=True,
        )
        self.show_act2_campaign_status(banner=False)
        self.speaker(
            "Halia Vey",
            "Routes decide ownership. Ownership decides which story gets believed.",
        )
        self.speaker(
            "Linene Ironward",
            "Routes decide whether people come home at all. Start there."
        )
        self.speaker(
            "Elira Lanternward",
            "If the dead are already trying to warn us, greed is not the only thing bidding on this cave."
        )
        if self.act2_company_has("Bryn Underbough"):
            self.speaker(
                "Bryn Underbough",
                "Every room with ledgers and lanterns ends up being about exits eventually. Best decide whose you trust."
            )
        self.run_dialogue_input("act2_claims_council_opening", max_entries=2)
        if self.state.flags.get("quest_reward_jerek_road_knot"):
            self.speaker(
                "Linene Ironward",
                "Jerek's been showing people that blue road-knot. Folk remember who brought one hard truth home instead of letting the road swallow it. Use that while this room is still listening.",
            )
        if self.state.flags.get("stonehill_quiet_room_intel_decoded"):
            self.speaker(
                "Halia Vey",
                "Nera's courier packet was real enough to matter. If clerkwork and message chains were shaping Ashfall and Emberhall, assume the mine's routes are being edited the same way.",
            )
        if self.state.flags.get("act2_neverwinter_witness_pressure_active"):
            self.speaker(
                "Linene Ironward",
                "Greywake sent a witness packet from Oren Vale's house. Sabra's manifests, Vessa's buyer phrase, and Garren's roadwarden line all agree: any claim built on copied authority gets read twice.",
            )
        if not self.has_quest("recover_pact_waymap"):
            self.grant_quest("recover_pact_waymap")
        if not self.has_quest("seek_agathas_truth"):
            self.grant_quest("seek_agathas_truth")
        if not self.has_quest("hold_the_claims_meet"):
            self.grant_quest("hold_the_claims_meet")
        sponsor_choice = self.scenario_choice(
            "Who do you let set the expedition's first rhythm?",
            [
                self.quoted_option("INVESTIGATION", "Halia gets first claim on the routework. Fast maps matter more than soft hands."),
                self.quoted_option("PERSUASION", "Linene's supply discipline sets the pace. If we move, we move cleanly."),
                self.quoted_option("RELIGION", "Elira and Daran keep the expedition cautious. We do not feed this place more lives than we must."),
            ],
            allow_meta=False,
        )
        if sponsor_choice == 1:
            self.player_speaker("Halia gets first claim on the routework. Fast maps matter more than soft hands.")
            self.state.flags["act2_sponsor"] = "exchange"
            self.act2_shift_metric(
                "act2_route_control",
                1,
                "Halia's money and survey crews move faster than most moral arguments",
            )
            self.act2_shift_metric(
                "act2_whisper_pressure",
                1,
                "more bodies and greed hit the route before anyone knows what the cave is doing back",
            )
            if self.state.flags.get("miners_exchange_dispute_resolved"):
                self.act2_shift_metric(
                    "act2_route_control",
                    1,
                    "Halia already trusts your judgment after Act 1's guild dispute",
                )
        elif sponsor_choice == 2:
            self.player_speaker("Linene's supply discipline sets the pace. If we move, we move cleanly.")
            self.state.flags["act2_sponsor"] = "lionshield"
            self.act2_shift_metric(
                "act2_town_stability",
                1,
                "Linene's quartermaster logic gives Iron Hollow something firmer than rumors to stand on",
            )
            self.act2_shift_metric(
                "act2_route_control",
                1,
                "organized supply lines keep the approach from dissolving into freelancing",
            )
            if self.state.flags.get("early_companion_recruited") == "Rhogar Valeguard":
                self.act2_shift_metric(
                    "act2_town_stability",
                    1,
                    "Rhogar's earlier presence already taught the town to respect disciplined guardwork",
                )
        else:
            self.player_speaker("Elira and Daran keep the expedition cautious. We do not feed this place more lives than we must.")
            self.state.flags["act2_sponsor"] = "wardens"
            self.act2_shift_metric(
                "act2_town_stability",
                1,
                "people hear that someone is still prioritizing their lives over the cave's profits",
            )
            self.act2_shift_metric(
                "act2_whisper_pressure",
                -1,
                "fewer reckless crews run straight into the mine's stranger influence",
            )
            if self.state.flags.get("elira_helped"):
                self.act2_shift_metric(
                    "act2_town_stability",
                    1,
                    "Elira's standing in town lets the cautious plan sound like confidence instead of fear",
                )
        self.run_dialogue_input(f"act2_sponsor_{self.state.flags['act2_sponsor']}")
        read_choice = self.scenario_choice(
            "Before the first teams leave, what do you insist on reading clearly?",
            [
                self.quoted_option("INSIGHT", "Tell me whose argument is really serving the cave instead of the town."),
                self.quoted_option("INVESTIGATION", "Lay out every surviving route fragment. I want the old Meridian Compact logic, not the rumors."),
                self.quoted_option("PERSUASION", "If you all want this town to survive the mine, stop speaking like rivals for one night."),
            ],
            allow_meta=False,
        )
        if read_choice == 1:
            self.player_speaker("Tell me whose argument is really serving the cave instead of the town.")
            if self.skill_check(self.state.player, "Insight", 13, context="to read the hidden pressure in the claims room"):
                self.add_clue(
                    "Somebody keeps steering attention away from the southern workings and toward routes that generate noise instead of answers."
                )
                self.reward_party(xp=20, reason="reading the claims room cleanly")
        elif read_choice == 2:
            self.player_speaker("Lay out every surviving route fragment. I want the old Meridian Compact logic, not the rumors.")
            if self.skill_check(self.state.player, "Investigation", 13, context="to reconstruct the surviving Meridian Compact route logic"):
                self.add_clue(
                    "Old Meridian Compact roads converged through Hushfen, Stonehollow, and a southern service adit linked to the Resonant Vaults."
                )
                self.reward_party(xp=25, reason="reassembling the Meridian Compact route fragments")
                self.act2_shift_metric(
                    "act2_route_control",
                    1,
                    "you forced the council to work from real survey logic instead of expedient guesswork",
                )
        else:
            self.player_speaker("If you all want this town to survive the mine, stop speaking like rivals for one night.")
            if self.skill_check(self.state.player, "Persuasion", 13, context="to keep the claims council from hardening too early"):
                self.reward_party(xp=20, gold=10, reason="holding the first claims council together")
                self.act2_shift_metric(
                    "act2_town_stability",
                    1,
                    "you made the first council sound like a town making policy instead of a feeding frenzy",
                )
        self.state.flags["phandelver_claims_council_seen"] = True
        self.state.current_scene = "act2_expedition_hub"

    def scene_act2_expedition_hub(self) -> None:
        assert self.state is not None
        self.banner("Act II Expedition Hub")
        self.say(
            "Iron Hollow is still your base, but it now feels like a frontier port built around a wound in the world. Every trip changes the town's nerve, the race for Resonant Vaults, "
            "and how much of the Choir's wrong music gets out into open air.",
            typed=True,
        )
        for line in self.act2_campaign_snapshot_lines():
            self.output_fn(line)
        late_route_recap = self.act2_late_route_hub_recap()
        if late_route_recap is not None:
            self.say(late_route_recap)
        while True:
            options: list[tuple[str, str]] = []
            if not self.state.flags.get("agatha_truth_secured"):
                label = "Follow Elira's Hushfen lead and seek the Pale Witness's truth."
                if self.state.flags.get("phandalin_sabotage_resolved"):
                    label = "Recover Hushfen late and see what delaying the Pale Witness's warning cost."
                options.append(("agatha", self.action_option(label)))
            if not self.state.flags.get("woodland_survey_cleared"):
                label = "Break the sabotage line at Greywake Survey Camp."
                if self.state.flags.get("phandalin_sabotage_resolved"):
                    label = "Recover the Greywake survey line late after the saboteurs already bit into town."
                options.append(("wood", self.action_option(label)))
            if not self.state.flags.get("stonehollow_dig_cleared"):
                label = "Enter Stonehollow Dig and recover the missing survey team."
                if self.state.flags.get("phandalin_sabotage_resolved"):
                    label = "Return to Stonehollow late and salvage whatever survey truth still survived."
                options.append(("stonehollow", self.action_option(label)))
            if self.act2_branch_progress() >= 1 and not self.state.flags.get("glasswater_intake_cleared"):
                label = "Inspect the Glasswater Intake before the fouled water turns into a cleaner lie."
                if self.state.flags.get("phandalin_sabotage_resolved"):
                    label = "Recover Glasswater Intake late and see what the fouled water already cost."
                options.append(("glasswater", self.action_option(label)))
            if self.act2_branch_progress() >= 2 and not self.state.flags.get("phandalin_sabotage_resolved"):
                unresolved = self.act2_unresolved_early_leads()
                if unresolved:
                    label = f"Advance to sabotage night now and let {self.ACT2_BRANCH_LABELS[unresolved[0]]} go dark for a while."
                else:
                    label = "Advance to sabotage night with all three early leads secured."
                options.append(("midpoint", self.action_option(label)))
            if self.state.flags.get("phandalin_sabotage_resolved") and not self.state.flags.get("broken_prospect_cleared"):
                if not self.state.flags.get("act2_first_late_route"):
                    label = "Take the Broken Prospect route first and secure the cleaner cave approach."
                elif self.state.flags.get("act2_first_late_route") == "south_adit":
                    label = "Recover Broken Prospect after choosing the prison line first."
                else:
                    label = "Return to Broken Prospect."
                options.append(("broken_prospect", self.action_option(label)))
            if self.state.flags.get("phandalin_sabotage_resolved") and not self.state.flags.get("south_adit_cleared"):
                if not self.state.flags.get("act2_first_late_route"):
                    label = "Take the South Adit first and put the prisoners ahead of the route race."
                elif self.state.flags.get("act2_first_late_route") == "broken_prospect":
                    label = "Push into South Adit before the remaining captives vanish entirely."
                else:
                    label = "Return to South Adit."
                options.append(("south_adit", self.action_option(label)))
            if (
                self.state.flags.get("broken_prospect_cleared")
                and self.state.flags.get("south_adit_cleared")
                and not self.state.flags.get("wave_echo_outer_cleared")
            ):
                options.append(("outer", self.action_option("Advance through Resonant Vaults' outer galleries.")))
            if self.state.flags.get("wave_echo_outer_cleared") and not self.state.flags.get("black_lake_crossed"):
                options.append(("causeway", self.action_option("Cross the Blackglass causeway.")))
            if self.state.flags.get("black_lake_crossed") and not self.state.flags.get("caldra_defeated"):
                options.append(("forge", self.action_option("Confront the Quiet Choir at the Meridian Forge.")))
            if self.state.flags.get("caldra_defeated"):
                options.append(("complete", self.action_option("Close out Act II and record what happened beneath the cave.")))
            backtrack_node = self.peek_act2_overworld_backtrack_node()
            if backtrack_node is not None:
                options.append(("backtrack", self.skill_tag("BACKTRACK", self.action_option(f"Backtrack to {backtrack_node.title}"))))
            options.extend(
                [
                    ("status", self.action_option("Review the expedition pressures and current consequences.")),
                    ("turn_in", self.action_option("Report completed quests to their original givers.")),
                    ("camp", self.action_option("Return to camp and manage the wider company.")),
                    ("sidetrack", self.action_option("Follow a companion's Act 2 thread.")),
                    ("inn", self.action_option("Rest at Ashlamp Inn (10 marks per active party member).")),
                    ("rest", self.action_option("Take a short rest.")),
                    ("party", self.action_option("Review the current party.")),
                ]
            )
            choice = self.scenario_choice("Where do you push next?", [text for _, text in options], allow_meta=False)
            selection_key, _ = options[choice - 1]
            if selection_key == "agatha":
                self.run_dialogue_input("act2_hub_agatha")
                self.travel_to_act2_node("conyberry_agatha")
                return
            if selection_key == "wood":
                self.run_dialogue_input("act2_hub_wood")
                self.travel_to_act2_node("neverwinter_wood_survey_camp")
                return
            if selection_key == "stonehollow":
                self.run_dialogue_input("act2_hub_stonehollow")
                self.travel_to_act2_node("stonehollow_dig")
                return
            if selection_key == "glasswater":
                self.say("The Glasswater report has stopped sounding like rumor. If the annex is still live, it is teaching more than water to flow wrong.")
                self.travel_to_act2_node("glasswater_intake")
                return
            if selection_key == "midpoint":
                self.run_dialogue_input("act2_hub_midpoint")
                self.travel_to_act2_node("act2_midpoint_convergence")
                return
            if selection_key == "broken_prospect":
                if not self.confirm_act2_late_route_priority("broken_prospect"):
                    continue
                self.run_dialogue_input("act2_hub_broken_prospect")
                self.travel_to_act2_node("broken_prospect")
                return
            if selection_key == "south_adit":
                if not self.confirm_act2_late_route_priority("south_adit"):
                    continue
                self.run_dialogue_input("act2_hub_south_adit")
                self.travel_to_act2_node("south_adit")
                return
            if selection_key == "outer":
                self.run_dialogue_input("act2_hub_outer")
                self.travel_to_act2_node("wave_echo_outer_galleries")
                return
            if selection_key == "causeway":
                self.run_dialogue_input("act2_hub_causeway")
                self.travel_to_act2_node("black_lake_causeway")
                return
            if selection_key == "forge":
                self.run_dialogue_input("act2_hub_forge")
                self.travel_to_act2_node("forge_of_spells")
                return
            if selection_key == "complete":
                self.travel_to_act2_node("act2_scaffold_complete")
                return
            if selection_key == "backtrack":
                if not self.backtrack_act2_overworld_node():
                    self.say("There is no familiar expedition route to backtrack right now.")
                    continue
                return
            if selection_key == "status":
                self.show_act2_campaign_status()
                continue
            if selection_key == "turn_in":
                self.run_act2_council_turnins()
                continue
            if selection_key == "camp":
                self.open_camp_menu()
                continue
            if selection_key == "sidetrack":
                self.run_act2_companion_sidetrack()
                continue
            if selection_key == "inn":
                self.paid_inn_long_rest("Ashlamp Inn")
                continue
            if selection_key == "rest":
                self.short_rest()
                continue
            self.show_party()

    def act2_turn_in_dialogue(self, quest_id: str) -> None:
        if quest_id == "recover_pact_waymap":
            self.speaker(
                "Halia Vey",
                "Now that is a route worth arguing over. Good. A claim with a real map behind it survives longer than a claim with only shouting.",
            )
        elif quest_id == "seek_agathas_truth":
            self.speaker(
                "Elira Lanternward",
                "Then Hushfen's dead were not left speaking into the dark. Tell me the warning cleanly, and I will make sure it is carried gently.",
            )
            if self.state is not None and self.state.flags.get("agatha_claim_cover_suspected"):
                sponsor = str(self.state.flags.get("act2_sponsor", "council"))
                if sponsor == "exchange":
                    self.speaker(
                        "Halia Vey",
                        "Claim marks on dead ground are not piety. They are bookkeeping with incense on it. Give me the hand that wrote them and I can make half this room stop smiling.",
                    )
                    if not self.state.flags.get("agatha_claim_cover_council_reaction_recorded"):
                        self.act2_shift_metric(
                            "act2_route_control",
                            1,
                            "Halia turns Hushfen's hidden claim marks into leverage against rival route papers",
                        )
                elif sponsor == "lionshield":
                    self.speaker(
                        "Linene Ironward",
                        "If someone used graves as cover for route claims, I want names on my desk before another crew leaves with a false map and a brave speech.",
                    )
                    if not self.state.flags.get("agatha_claim_cover_council_reaction_recorded"):
                        self.act2_shift_metric(
                            "act2_town_stability",
                            1,
                            "Linene uses Hushfen's claim-cover proof to slow reckless crews before bad papers become dead miners",
                        )
                else:
                    self.speaker(
                        "Town Council",
                        "Then the Hushfen warning is not only spiritual. It is evidence. The next claim read in this room gets read against the dead as well as the ledgers.",
                    )
                    if not self.state.flags.get("agatha_claim_cover_council_reaction_recorded"):
                        self.act2_shift_metric(
                            "act2_whisper_pressure",
                            -1,
                            "naming Hushfen's claim-cover trick keeps the Choir from hiding practical corruption inside sacred dread",
                        )
                self.state.flags["agatha_claim_cover_council_reaction_recorded"] = True
        elif quest_id == "rescue_stonehollow_scholars":
            self.speaker(
                "Linene Ironward",
                "Names first. Then injuries. Then what they brought back. I can replace tools, but I will not file people under losses before I have to.",
            )
        elif quest_id == "cut_woodland_saboteurs":
            self.speaker(
                "Daran Orchard",
                "A broken sabotage line means scouts can breathe again. Not relax. Never relax. But breathe, and sometimes that is the difference.",
            )
        elif quest_id == "hold_the_claims_meet":
            self.speaker(
                "Linene Ironward",
                "The meeting held because someone kept the room pointed at tomorrow instead of old grudges. I will take that kind of order wherever I can get it.",
            )
        elif quest_id == "free_wave_echo_captives":
            self.speaker(
                "Elira Lanternward",
                "Give me every name you can remember. The rescued deserve more than being counted as proof that we did the correct thing.",
            )
        elif quest_id == "sever_quiet_choir":
            self.speaker(
                "Town Council",
                "Then Resonant Vaults was never only a claim dispute. Put the truth on the table, all of it, and let the town decide with open eyes.",
            )

    def run_act2_council_turnins(self) -> None:
        assert self.state is not None
        self.refresh_quest_statuses(announce=False)
        ready_quest_ids = [
            "recover_pact_waymap",
            "seek_agathas_truth",
            "rescue_stonehollow_scholars",
            "cut_woodland_saboteurs",
            "hold_the_claims_meet",
            "free_wave_echo_captives",
            "sever_quiet_choir",
        ]
        ready_quests = [
            self.get_quest_definition(quest_id)
            for quest_id in ready_quest_ids
            if self.quest_is_ready(quest_id)
        ]
        if not ready_quests:
            self.say("Nobody at the council table has a fresh report to close out just yet.")
            return
        options = [
            self.action_option(f"Report to {definition.giver}: {definition.title}.")
            for definition in ready_quests
        ]
        options.append(self.action_option("Hold the reports for now."))
        choice = self.scenario_choice("Who do you report to?", options, allow_meta=False)
        if choice == len(options):
            self.player_action("Hold the reports for now.")
            return
        definition = ready_quests[choice - 1]
        self.player_action(f"Report {definition.title} to {definition.giver}.")
        self.act2_turn_in_dialogue(definition.quest_id)
        self.turn_in_quest(definition.quest_id, giver=definition.giver)

    def run_act2_companion_sidetrack(self) -> None:
        assert self.state is not None
        companions = [member for member in self.state.all_companions() if not member.dead]
        if not companions:
            self.say("Nobody in camp is ready to open up right now.")
            return
        options = [f"{companion.name}: hear where the road is pressing on them." for companion in companions]
        options.append("Back")
        choice = self.choose("Whose thread do you spend time with?", options, allow_meta=False)
        if choice == len(options):
            return
        companion = companions[choice - 1]
        flag = f"{companion.companion_id or companion.name.lower().replace(' ', '_')}_act2_sidetrack_seen"
        if self.state.flags.get(flag):
            self.say(f"You already saw the decisive Act 2 turn in {companion.name}'s thread.")
            return
        if companion.companion_id == "bryn_underbough":
            self.say(
                "Bryn spreads copied claim ledgers across a crate and quietly names three figures who used to fence bad information for smugglers. "
                "She can salt the numbers quietly or drag the whole scheme into lantern light."
            )
            sidetrack = self.scenario_choice(
                "How do you let Bryn handle the false ledgers?",
                [
                    self.skill_tag("STEALTH", self.action_option("Let her quietly poison the false books with bad distances and dead routes.")),
                    self.quoted_option("PERSUASION", "Expose the whole trick publicly and make the town watch who flinches."),
                ],
                allow_meta=False,
            )
            if sidetrack == 1:
                self.player_action("Let her quietly poison the false books with bad distances and dead routes.")
                self.state.flags["bryn_false_ledgers_salted"] = True
                self.act2_shift_metric(
                    "act2_route_control",
                    1,
                    "Bryn quietly ruined the credibility of several bad route copies before rivals could use them",
                )
            else:
                self.player_speaker("Expose the whole trick publicly and make the town watch who flinches.")
                self.state.flags["bryn_false_ledgers_exposed"] = True
                self.act2_shift_metric(
                    "act2_town_stability",
                    1,
                    "the town sees the claims game for what it is and trusts the council a little more for naming it",
                )
                if self.state.flags.get("act2_sponsor") == "exchange":
                    self.act2_shift_metric(
                        "act2_route_control",
                        -1,
                        "publicly embarrassing the Exchange bloc makes Halia's side less eager to share clean routework",
                    )
        elif companion.companion_id == "elira_dawnmantle":
            self.say(
                "Elira has rebuilt a miners' lantern with shrine silver, Lantern-faith script, and wick ash from the vigil after Ashfall Watch. "
                "She can carry it into the field as a ward, or leave it in Iron Hollow so the town itself feels steadier."
            )
            sidetrack = self.scenario_choice(
                "Where should Elira place the lantern's weight?",
                [
                    self.quoted_option("RELIGION", "Carry it with us. We will need a cleaner light below."),
                    self.quoted_option("PERSUASION", "Leave it in town. Iron Hollow needs to feel held together when we are away."),
                ],
                allow_meta=False,
            )
            if sidetrack == 1:
                self.player_speaker("Carry it with us. We will need a cleaner light below.")
                self.state.flags["elira_field_lantern"] = True
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    -1,
                    "Elira turns a camp relic into a working ward against the Quiet Choir's cadence",
                )
            else:
                self.player_speaker("Leave it in town. Iron Hollow needs to feel held together when we are away.")
                self.state.flags["elira_town_lantern"] = True
                self.act2_shift_metric(
                    "act2_town_stability",
                    1,
                    "Elira's lantern becomes a visible promise that the town is still being thought about first",
                )
        elif companion.companion_id == "kaelis_starling":
            self.say(
                "Kaelis walks you through old ranger cuts around Greywake Survey Camp. One hidden trail could make the expedition faster. "
                "Burning it would deny the same edge to everyone else."
            )
            sidetrack = self.scenario_choice(
                "What do you ask Kaelis to do with the hidden trail?",
                [
                    self.skill_tag("SURVIVAL", self.action_option("Keep the trail alive for us and a few people we trust.")),
                    self.action_option("Collapse the approach and make sure nobody gets to use it cleanly again."),
                ],
                allow_meta=False,
            )
            if sidetrack == 1:
                self.player_action("Keep the trail alive for us and a few people we trust.")
                self.state.flags["kaelis_hidden_trail"] = True
                self.act2_shift_metric(
                    "act2_route_control",
                    1,
                    "Kaelis preserves a ranger-grade bypass that only your side really understands",
                )
            else:
                self.player_action("Collapse the approach and make sure nobody gets to use it cleanly again.")
                self.state.flags["kaelis_trail_burned"] = True
                self.act2_shift_metric(
                    "act2_town_stability",
                    1,
                    "denying the hidden trail makes surprise approaches into town and camp much harder",
                )
                self.act2_shift_metric(
                    "act2_route_control",
                    -1,
                    "you give up a fast path of your own to keep everyone else from enjoying it",
                )
        elif companion.companion_id == "rhogar_valeguard":
            self.say(
                "Rhogar asks the question like a confession: once the mine opens, should his oath sit with the town above or the holy threshold below? "
                "He cannot stand in both places with the same body."
            )
            sidetrack = self.scenario_choice(
                "Where do you ask Rhogar to place his oath?",
                [
                    self.quoted_option("PERSUASION", "Stand for the town first. The living have to survive the route before relics matter."),
                    self.quoted_option("RELIGION", "Hold the old threshold. If the mine's sanctity breaks again, the town suffers anyway."),
                ],
                allow_meta=False,
            )
            if sidetrack == 1:
                self.player_speaker("Stand for the town first. The living have to survive the route before relics matter.")
                self.state.flags["rhogar_square_oath"] = True
                self.act2_shift_metric(
                    "act2_town_stability",
                    1,
                    "Rhogar's vow becomes a public thing people can lean on",
                )
            else:
                self.player_speaker("Hold the old threshold. If the mine's sanctity breaks again, the town suffers anyway.")
                self.state.flags["rhogar_threshold_oath"] = True
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    -1,
                    "Rhogar's oathwork hardens one of the mine's older sacred seams against the Choir",
                )
        elif companion.companion_id == "tolan_ironshield":
            self.say(
                "Tolan finds a wagon hidden under a tarp near the claims stores. Half the load is usable brace-iron. Half is ore the cave has already started to wrongen. "
                "He wants your call before anyone pretends those are the same problem."
            )
            sidetrack = self.scenario_choice(
                "What do you ask Tolan to do with the find?",
                [
                    self.action_option("Strip the brace-iron and haul every practical piece into the expedition stockpile."),
                    self.action_option("Dump the tainted ore into a sealed shaft and let profit go to keep the company cleaner."),
                ],
                allow_meta=False,
            )
            if sidetrack == 1:
                self.player_action("Strip the brace-iron and haul every practical piece into the expedition stockpile.")
                self.state.flags["tolan_salvaged_braces"] = True
                self.act2_shift_metric(
                    "act2_route_control",
                    1,
                    "Tolan turns a bad wagon into usable structure before the cave can claim it",
                )
            else:
                self.player_action("Dump the tainted ore into a sealed shaft and let profit go to keep the company cleaner.")
                self.state.flags["tolan_buried_tainted_ore"] = True
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    -1,
                    "you choose not to circulate stone that already sounds wrong in the hands",
                )
                self.act2_shift_metric(
                    "act2_town_stability",
                    1,
                    "Tolan spreads the story that you threw profit away rather than gamble with cursed ore",
                )
        elif companion.companion_id == "nim_ardentglass":
            self.say(
                "Nim finally shows you the worst of his mentor's missing theorem: one set of notes might let you answer the Meridian Forge with a counter-pattern, "
                "but only if he preserves pages he is no longer sure are safe to carry."
            )
            sidetrack = self.scenario_choice(
                "What do you tell Nim to do with the theorem fragments?",
                [
                    self.quoted_option("ARCANA", "Preserve them. We may need every dangerous word before this ends."),
                    self.action_option("Burn the corrupted pages and keep only what can still be trusted by daylight."),
                ],
                allow_meta=False,
            )
            if sidetrack == 1:
                self.player_speaker("Preserve them. We may need every dangerous word before this ends.")
                self.state.flags["nim_countermeasure_notes"] = True
                self.state.flags["act3_shard_notes_carried"] = True
                self.act2_shift_metric(
                    "act2_route_control",
                    1,
                    "Nim keeps the one body of notes that might let you answer the forge in its own language",
                )
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    1,
                    "keeping the theorem means carrying more of the mine's wrong logic with you",
                )
            else:
                self.player_action("Burn the corrupted pages and keep only what can still be trusted by daylight.")
                self.state.flags["nim_notes_burned"] = True
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    -1,
                    "Nim gives up certainty to stop the cave from teaching through his satchel",
                )
        elif companion.companion_id == "irielle_ashwake":
            self.say(
                "Irielle can teach you the Quiet Choir's counter-cadence, but doing so means carrying part of the cult's pattern in your own memory. "
                "She can also bury it and trust silence instead."
            )
            sidetrack = self.scenario_choice(
                "How do you ask Irielle to handle the counter-cadence?",
                [
                    self.quoted_option("ARCANA", "Teach it to us. We use what they built against them."),
                    self.quoted_option("WISDOM", "Bury it. We end this without carrying their song any farther than we must."),
                ],
                allow_meta=False,
            )
            if sidetrack == 1:
                self.player_speaker("Teach it to us. We use what they built against them.")
                self.state.flags["irielle_counter_cadence"] = True
                self.state.flags["act3_choir_cadence_known"] = True
                self.state.flags["counter_cadence_known"] = True
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    1,
                    "the company now carries a usable fragment of the Choir's own pattern",
                )
            else:
                self.player_speaker("Bury it. We end this without carrying their song any farther than we must.")
                self.state.flags["irielle_silence_oath"] = True
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    -1,
                    "Irielle refuses to let the counter-cadence become a new kind of contamination",
                )
        else:
            self.say(f"{companion.name} lets more of their Act 2 burden show than usual.")
        self.adjust_companion_disposition(companion, 1, f"you invested in {companion.name}'s Act 2 thread")
        self.state.flags[flag] = True


