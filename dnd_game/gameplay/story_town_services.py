from __future__ import annotations

from ..content import create_elira_dawnmantle


class StoryTownServicesMixin:
    def visit_shrine(self) -> None:
        assert self.state is not None
        self.banner("Shrine of Tymora")
        if self.has_companion("Elira Dawnmantle") and self.state.flags.get("elira_neverwinter_recruited"):
            if not self.state.flags.get("shrine_seen"):
                bell_echo = (
                    " A green road-ribbon hangs from the altar bell, bright as the promise Elira tied to the cracked luck bell "
                    "on the northern road."
                    if self.state.flags.get("wayside_luck_bell_promised")
                    else ""
                )
                self.say(
                    "Phandalin's little luck shrine is open, but Elira's field kit is not waiting beside the altar. "
                    "The acolytes are working from the triage notes she sent ahead from the northern road, and the wounded keep "
                    "pointing south toward the same ash-bitter blades."
                    + bell_echo,
                    typed=True,
                )
                self.state.flags["shrine_seen"] = True
                if not self.state.flags.get("shrine_raiders_asked"):
                    self.state.flags["shrine_raiders_asked"] = True
                    self.add_clue("Elira's notes confirm the Ashen Brand poison reached Phandalin from the Neverwinter road.")
            else:
                self.say("The shrine bells move in the wind while Elira stays with the company, where the next wound is likeliest to happen.")
            return
        if not self.state.flags.get("shrine_seen"):
            if self.state.flags.get("elira_phandalin_fallback_pending"):
                bell_echo = (
                    " A rain-stiff green road-ribbon from the cracked luck bell is tied beside her field kit."
                    if self.state.flags.get("wayside_luck_bell_seen")
                    else ""
                )
                self.say(
                    "A modest shrine stands open to the road, all wind bells, votive flame, and hurried footsteps. "
                    "Elira looks up from a miner's ash-dark wound with the tired recognition of someone who already met you where the road first started bleeding."
                    + bell_echo,
                    typed=True,
                )
            elif self.state.flags.get("neverwinter_elira_met"):
                bell_echo = (
                    " A green road-ribbon from the cracked luck bell has been knotted beside the votive flame."
                    if self.state.flags.get("wayside_luck_bell_seen")
                    else ""
                )
                self.say(
                    "A modest shrine stands open to the road, all wind bells, votive flame, and hurried footsteps. "
                    "Elira looks up from a miner's ash-dark wound and recognizes you from Neverwinter without letting her hands slow."
                    + bell_echo,
                    typed=True,
                )
            else:
                self.say(
                    "A modest shrine stands open to the road, all wind bells, votive flame, and hurried footsteps. "
                    "Sister Elira Dawnmantle is kneeling beside a miner whose wound has darkened with ash-stained poison, "
                    "working with the calm intensity of someone refusing to let panic set the pace.",
                    typed=True,
                )
            self.state.flags["shrine_seen"] = True
        while True:
            options: list[tuple[str, str]] = []
            if not self.state.flags.get("shrine_medicine_attempted"):
                options.append(("medicine", self.quoted_option("MEDICINE", "Let me examine the poisoned miner.")))
            if not self.state.flags.get("shrine_prayer_attempted"):
                options.append(("prayer", self.quoted_option("RELIGION", "I'll offer a prayer with you.")))
            if not self.state.flags.get("shrine_raiders_asked"):
                options.append(("raiders", "\"What have you learned about the raiders?\""))
            if not self.state.flags.get("shrine_recruit_attempted") and not self.has_companion("Elira Dawnmantle"):
                options.append(
                    (
                        "recruit",
                        "\"Come with me. Phandalin needs you in the field.\""
                        if self.state.flags.get("elira_helped") or self.state.flags.get("elira_phandalin_fallback_pending")
                        else self.quoted_option("PERSUASION", "Come with me. Phandalin needs you in the field."),
                    )
                )
            leave_text = (
                "Give Elira a moment to tend the shrine."
                if self.has_companion("Elira Dawnmantle")
                else "Step back and leave Elira to her work."
            )
            options.append(("leave", self.action_option(leave_text)))
            choice = self.scenario_choice("Choose what you say to Elira.", [text for _, text in options])
            selection_key, _ = options[choice - 1]
            if selection_key == "medicine":
                self.state.flags["shrine_medicine_attempted"] = True
                self.player_speaker("Let me examine the poisoned miner.")
                success = self.skill_check(self.state.player, "Medicine", 8, context="to stabilize the miner")
                if success:
                    self.state.flags["elira_helped"] = True
                    self.speaker("Elira Dawnmantle", "Good hands. You just bought this miner another sunrise.")
                    self.reward_party(xp=10, reason="helping Elira treat the poisoned miner")
                else:
                    self.speaker("Elira Dawnmantle", "You did what you could. Let me carry the rest from here.")
            elif selection_key == "prayer":
                self.state.flags["shrine_prayer_attempted"] = True
                self.player_speaker("I'll offer a prayer with you.")
                success = self.skill_check(self.state.player, "Religion", 8, context="to guide a steady prayer")
                if success:
                    self.state.flags["elira_helped"] = True
                    self.speaker("Elira Dawnmantle", "Luck still walks beside you. I can feel it.")
                    self.reward_party(xp=10, reason="praying with Elira")
                else:
                    self.speaker("Elira Dawnmantle", "Your heart is in the right place. Tymora honors that too.")
            elif selection_key == "raiders":
                self.state.flags["shrine_raiders_asked"] = True
                self.player_speaker("What have you learned about the raiders?")
                self.speaker(
                    "Elira Dawnmantle",
                    "Their blades carry an ash-bitter toxin, and they move through ruined stonework like trained soldiers, not frightened thieves. "
                    "Whoever shaped them taught discipline first and cruelty second, which is usually the more dangerous order.",
                )
                self.add_clue("Elira confirms the gang uses poison and disciplined tactics, not random violence.")
            elif selection_key == "recruit":
                self.state.flags["shrine_recruit_attempted"] = True
                self.player_speaker("Come with me. Phandalin needs you in the field.")
                if self.state.flags.get("elira_helped") or self.state.flags.get("elira_phandalin_fallback_pending"):
                    self.recruit_companion(create_elira_dawnmantle())
                    self.state.flags["elira_phandalin_recruited"] = True
                    self.state.flags.pop("elira_phandalin_fallback_pending", None)
                    self.speaker("Elira Dawnmantle", "Then I will walk with you. The road needs more than prayers.")
                else:
                    success = self.skill_check(self.state.player, "Persuasion", 8, context="to ask Elira into danger")
                    if success:
                        self.recruit_companion(create_elira_dawnmantle())
                        self.speaker("Elira Dawnmantle", "Very well. Faith that never leaves the shrine is only half alive.")
                    else:
                        self.speaker("Elira Dawnmantle", "I want to help, but I won't abandon this place lightly without trust.")
            else:
                if self.has_companion("Elira Dawnmantle"):
                    self.player_action("You give Elira a moment to tend the shrine before moving on.")
                else:
                    self.player_action("You leave Elira to her work for now.")
                return

    def visit_barthen_provisions(self) -> None:
        assert self.state is not None
        self.banner("Barthen's Provisions")
        if not self.state.flags.get("barthen_seen"):
            self.say(
                "The provision house smells of flour, lamp oil, leather straps, and worry worked into routine. "
                "Barthen is already halfway through an argument with a teamster about missing crates when he spots "
                "fresh adventurers with coin, road dust, and the posture of people likely to be asked for help.",
                typed=True,
            )
            self.state.flags["barthen_seen"] = True
        while True:
            options: list[tuple[str, str]] = []
            if self.quest_is_ready("restore_barthen_supplies"):
                options.append(("turn_in", self.action_option("Tell Barthen the watchtower road is open again.")))
            if not self.state.flags.get("barthen_shortage_asked"):
                options.append(("shortage", "\"What does Phandalin run short on first when the road turns bad?\""))
            options.append(("shop", self.skill_tag("TRADE", self.action_option("Check the shelves for provisions and trail gear."))))
            options.append(("leave", self.action_option("Leave the provision house.")))
            choice = self.scenario_choice("Barthen wipes his hands on an apron and nods toward the shelves.", [text for _, text in options])
            selection_key, _ = options[choice - 1]
            if selection_key == "turn_in":
                self.player_action("Ashfall Watch is broken. Wagons should have a chance again.")
                self.speaker(
                    "Barthen",
                    "Then I can stop deciding which family hears 'maybe tomorrow' when the bread runs thin. That's worth more than a strongbox to me.",
                )
                self.turn_in_quest("restore_barthen_supplies", giver="Barthen")
            elif selection_key == "shortage":
                self.state.flags["barthen_shortage_asked"] = True
                self.player_speaker("What does Phandalin run short on first when the road turns bad?")
                self.speaker(
                    "Barthen",
                    "Food that keeps, bandages, lamp oil, and anything light enough to move fast. Every raid turns simple bread into strategy, because sooner or later somebody's child asks why supper got smaller again.",
                )
                if self.grant_quest(
                    "restore_barthen_supplies",
                    note="Barthen says the raiders are turning everyday provisions into rationed hope.",
                ):
                    self.speaker(
                        "Barthen",
                        "Break the watchtower and you'll do more for this town than selling one more sack of flour ever could.",
                    )
                self.run_dialogue_input("barthen_shortage")
            elif selection_key == "shop":
                self.player_action("You start checking the shelves for food, salves, and travel goods.")
                self.manage_inventory(merchant_id="barthen_provisions", merchant_name="Barthen")
            else:
                self.player_action("You leave Barthen to his shelves and supply ledgers.")
                return

    def visit_trading_post(self) -> None:
        assert self.state is not None
        self.banner("Lionshield Coster")
        if not self.state.flags.get("trading_post_seen"):
            self.say(
                "Inside the timber-walled trading post, Linene Graywind keeps ledgers, blades, and road-worn pack goods "
                "in severe, deliberate order. Her eyes linger on every dented shield and bloodied satchel that comes "
                "through the door, as if each one is a report nobody bothered to write down.",
                typed=True,
            )
            self.state.flags["trading_post_seen"] = True
        while True:
            options: list[tuple[str, str]] = []
            if self.quest_is_ready("reopen_lionshield_trade"):
                options.append(("turn_in", self.action_option("Report that Ashfall Watch has been broken.")))
            if not self.state.flags.get("trading_post_trade_asked"):
                options.append(("trade", "\"How badly are the raiders strangling trade?\""))
            options.append(("shop", self.skill_tag("TRADE", self.action_option("Lay out the party's goods and talk prices."))))
            options.append(("leave", self.action_option("Leave the trading post.")))
            choice = self.scenario_choice("Linene looks up from the counter.", [text for _, text in options])
            selection_key, _ = options[choice - 1]
            if selection_key == "turn_in":
                self.player_action("Ashfall Watch won't be taxing honest caravans again.")
                self.speaker(
                    "Linene Graywind",
                    "Good. Fear is expensive, and I've had enough customers paying in it.",
                )
                self.turn_in_quest("reopen_lionshield_trade", giver="Linene Graywind")
            elif selection_key == "trade":
                self.state.flags["trading_post_trade_asked"] = True
                self.player_speaker("How badly are the raiders strangling trade?")
                self.speaker(
                    "Linene Graywind",
                    "Bad enough that every honest caravan is paying twice: once in coin, once in fear. Teamsters are taking longer routes, guards are naming higher prices, and every missing wagon teaches the next one to hesitate.",
                )
                self.add_clue("Linene confirms the gang's raids are choking Phandalin's trade through Ashfall Watch.")
                if self.grant_quest(
                    "reopen_lionshield_trade",
                    note="Linene says the town is paying for the raiders in coin, delay, and fear.",
                ):
                    self.speaker(
                        "Linene Graywind",
                        "Break Ashfall Watch and I'll know by the look of the next caravan that rolls through the gate.",
                    )
                self.run_dialogue_input("lionshield_trade")
            elif selection_key == "shop":
                self.player_action("You spread out the party's spare gear and start haggling with Linene.")
                self.manage_inventory(merchant_id="linene_graywind", merchant_name="Linene Graywind")
            else:
                self.player_action("You leave the trading post and step back into Phandalin's muddy lane.")
                return
