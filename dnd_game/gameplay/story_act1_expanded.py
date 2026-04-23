from __future__ import annotations

from ..content import create_enemy
from .encounter import Encounter
from .constants import LEVEL_XP_THRESHOLDS


class StoryAct1ExpandedMixin:
    def act1_pick_enemy(self, templates, *, name: str | None = None):
        return create_enemy(self.rng.choice(tuple(templates)), name=name)

    def act1_party_size(self) -> int:
        assert self.state is not None
        return max(1, len([member for member in self.state.party_members() if not member.dead]))

    def act1_side_paths_cleared(self) -> bool:
        assert self.state is not None
        return bool(
            self.state.flags.get("old_owl_well_cleared") and self.state.flags.get("wyvern_tor_cleared")
        )

    def can_visit_old_owl_well(self) -> bool:
        assert self.state is not None
        return bool(self.has_quest("silence_old_owl_well") or self.state.flags.get("miners_exchange_lead"))

    def can_visit_wyvern_tor(self) -> bool:
        assert self.state is not None
        return bool(self.has_quest("break_wyvern_tor_raiders") or self.state.flags.get("edermath_orchard_lead"))

    def has_edermath_orchard_interactions(self) -> bool:
        assert self.state is not None
        return bool(
            not self.state.flags.get("edermath_orchard_seen")
            or self.quest_is_ready("break_wyvern_tor_raiders")
            or not self.state.flags.get("edermath_orchard_blight_checked")
            or not self.state.flags.get("edermath_orchard_wyvern_tor_asked")
            or not self.state.flags.get("edermath_orchard_training_done")
            or not self.state.flags.get("edermath_old_cache_recovered")
        )

    def has_miners_exchange_interactions(self) -> bool:
        assert self.state is not None
        return bool(
            not self.state.flags.get("miners_exchange_seen")
            or self.quest_is_ready("silence_old_owl_well")
            or not self.state.flags.get("miners_exchange_missing_crews_asked")
            or not self.state.flags.get("miners_exchange_ledgers_checked")
            or not self.state.flags.get("miners_exchange_dispute_resolved")
        )

    def wyvern_tor_recommended_level(self) -> int:
        return 3

    def should_warn_for_wyvern_tor(self) -> bool:
        assert self.state is not None
        return self.state.player.level < self.wyvern_tor_recommended_level()

    def confirm_wyvern_tor_departure(self) -> bool:
        if not self.should_warn_for_wyvern_tor():
            return True
        recommended_level = self.wyvern_tor_recommended_level()
        self.say(
            f"Red Mesa Hold is balanced as a level {recommended_level} route for a full four-person party. "
            "You can push it early, but the ridge will hit much harder than Blackglass Well."
        )
        choice = self.scenario_choice(
            "Do you still ride for Red Mesa Hold?",
            [
                self.action_option("Ride for Red Mesa Hold anyway."),
                self.action_option(f"Wait and come back at level {recommended_level}."),
            ],
            allow_meta=False,
        )
        return choice == 1

    def run_phandalin_council_event(self) -> None:
        assert self.state is not None
        if self.state.flags.get("phandalin_council_seen") or not self.act1_side_paths_cleared():
            return
        self.banner("Ashlamp War-Room")
        self.say(
            "By evening, the Ashlamp Inn has half-turned into a frontier war room. Tessa Harrow, Halia Vey, "
            "Hadrik, Linene Ironward, and Daran Orchard crowd around a beer-stained map while rain taps at the shutters. "
            "For the first time since your arrival, Iron Hollow sounds less afraid than focused.",
            typed=True,
        )
        self.speaker(
            "Tessa Harrow",
            "You brought back enough truth to stop guessing. Ashfall Watch is the hinge. Break it and the whole line stops bending around the Ashen Brand.",
        )
        choice = self.scenario_choice(
            "How do you help shape the plan?",
            [
                self.quoted_option("INVESTIGATION", "Show me the routes again. I want the exact pressure point."),
                self.quoted_option("PERSUASION", "If the town is going to hold, they need to hear that we can actually win this."),
                self.quoted_option("INSIGHT", "Rukhar is disciplined. Tell me what he is protecting, not what he is saying."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Show me the routes again. I want the exact pressure point.")
            success = self.skill_check(
                self.state.player,
                "Investigation",
                13,
                context="to identify the cleanest way to break Ashfall's road network",
            )
            if success:
                self.say(
                    "You line up courier times, smoke markers, and ridge tracks into one clear answer: cut Ashfall's signal basin early and the tower loses its reach."
                )
                self.add_clue("Ashfall Watch relies on a signal basin and ridge runners; blinding that line buys the assault room to breathe.")
                self.reward_party(xp=20, reason="mapping Ashfall Watch's pressure points")
            else:
                self.say("The routes make sense, but not cleanly enough to turn the whole table quiet.")
        elif choice == 2:
            self.player_speaker("If the town is going to hold, they need to hear that we can actually win this.")
            success = self.skill_check(
                self.state.player,
                "Persuasion",
                13,
                context="to turn anxious civilians into a steadier rear line",
            )
            if success:
                self.say(
                    "The room stops sounding like a list of shortages and starts sounding like a town choosing to stand behind a plan."
                )
                self.add_inventory_item("potion_heroism", source="a relieved council table")
                self.reward_party(xp=20, gold=8, reason="steadying Iron Hollow before the Ashfall march")
            else:
                self.say("They listen, but fear still sits in the room like another body at the table.")
        else:
            self.player_speaker("Rukhar is disciplined. Tell me what he is protecting, not what he is saying.")
            success = self.skill_check(
                self.state.player,
                "Insight",
                13,
                context="to read the shape of Rukhar's command habits from witness reports",
            )
            if success:
                self.say(
                    "The pattern is obvious once you hear it: prisoners and orders matter more to Rukhar than plunder, which means the lower barracks and map room are the real nerve center."
                )
                self.add_clue("Rukhar protects his prisoners, orders, and lower barracks more fiercely than his outer walls.")
                self.reward_party(xp=20, reason="reading Rukhar through secondhand testimony")
            else:
                self.say("Rukhar stays frustratingly hard to pin down even in other people's stories.")
        self.add_journal(
            "A council at Ashlamp Inn confirms Ashfall Watch is the next major target once Iron Hollow's two outer threats are broken."
        )
        self.state.flags["phandalin_council_seen"] = True

    def run_after_watch_gathering(self) -> None:
        assert self.state is not None
        if self.state.flags.get("phandalin_after_watch_seen") or not self.state.flags.get("ashfall_watch_cleared"):
            return
        if self.state.player.level < 2:
            xp_to_level_two = max(0, LEVEL_XP_THRESHOLDS[2] - self.state.xp)
            if xp_to_level_two > 0:
                self.reward_party(xp=xp_to_level_two, reason="regrouping after Ashfall Watch")
        self.banner("Lantern Vigil")
        self.say(
            "When you ride back from Ashfall Watch, Iron Hollow meets you with lanterns, not cheers. Too many people are counting the faces that returned. "
            "Outside the Ashlamp Inn, the town gathers in the road while rescued teamsters and miners trade fractured testimony about old cellars beneath the Duskmere ruins.",
            typed=True,
        )
        self.speaker(
            "Halia Vey",
            "Rukhar was moving ledgers, captives, and coin through the manor hill. Whatever sits under Duskmere is where the Ashen Brand keeps the part of itself that thinks.",
        )
        choice = self.scenario_choice(
            "What do you do in the middle of the vigil?",
            [
                self.quoted_option("MEDICINE", "Bring me the wounded witness. If they saw the tunnels, I can keep them talking."),
                self.quoted_option("RELIGION", "Let the vigil breathe. People remember more clearly when grief is not wrestling them to the ground."),
                self.quoted_option("INVESTIGATION", "Show me the soot-marked ledger scraps from Ashfall. I want the trail beneath the trail."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Bring me the wounded witness. If they saw the tunnels, I can keep them talking.")
            success = self.skill_check(
                self.state.player,
                "Medicine",
                13,
                context="to stabilize a rescued teamster long enough to get a clear account",
            )
            if success:
                self.say("The witness gives you a clean memory of a cistern stair beneath the old manor hill and a door opened by soot-black keys.")
                self.add_clue("A rescued teamster saw a hidden cistern stair beneath Duskmere Manor.")
                self.reward_party(xp=20, reason="stabilizing a rescued witness during the vigil")
            else:
                self.say("You keep them from slipping under again, but their memory comes back in scattered shards.")
        elif choice == 2:
            self.player_speaker("Let the vigil breathe. People remember more clearly when grief is not wrestling them to the ground.")
            success = self.skill_check(
                self.state.player,
                "Religion",
                13,
                context="to guide the crowd through mourning without letting panic retake the night",
            )
            if success:
                self.say("The prayers do not erase grief, but they give the town enough stillness for the important details to surface.")
                self.add_inventory_item("scroll_clarity", source="Elira's shrine stores")
                self.reward_party(xp=20, reason="holding the lantern vigil together")
            else:
                self.say("The prayers help, but the night stays raw and hard-edged.")
        else:
            self.player_speaker("Show me the soot-marked ledger scraps from Ashfall. I want the trail beneath the trail.")
            success = self.skill_check(
                self.state.player,
                "Investigation",
                13,
                context="to trace Ashfall's paper trail into Iron Hollow's buried foundations",
            )
            if success:
                self.say(
                    "Under the ash and rain damage, you find repeated references to 'manor intake' and 'Emberhall reserve,' with Duskmere clearly serving as the handoff."
                )
                self.add_clue("Rukhar's ledgers show Duskmere Manor as the handoff point to Emberhall deeper below town.")
                self.reward_party(xp=20, reason="decoding Rukhar's ledgers")
            else:
                self.say("You salvage enough to confirm the manor matters, but not enough to fully map the chain below it.")
        self.state.flags["phandalin_after_watch_seen"] = True
        self.state.flags["tresendar_revealed"] = True
        self.add_journal("The lantern vigil turns up a new lead: the Ashen Brand is still moving through hidden cellars beneath Duskmere Manor.")

    def scene_phandalin_hub(self) -> None:
        assert self.state is not None
        self.banner("Iron Hollow")
        if not self.state.flags.get("phandalin_arrived"):
            self.say(
                "Iron Hollow rises from rocky foothills in a scatter of rebuilt homes, old stone scars, orchard walls, wagon sheds, and lantern-lit mud lanes. "
                "There are no proper walls, no garrison worth the name, and too many decent people living one bad week away from disaster.",
                typed=True,
            )
            self.state.flags["phandalin_arrived"] = True
            self.add_journal("You reached Iron Hollow, a hard-bitten frontier town under growing Ashen Brand pressure.")
            if self.state.flags.get("blackwake_completed"):
                self.describe_blackwake_phandalin_arrival()
            choice = self.scenario_choice(
                "How do you enter town?",
                [
                    self.quoted_option("INSIGHT", "I want to read the mood of the town before I speak."),
                    self.quoted_option("PERSUASION", "Let them know Greywake sent help."),
                    self.skill_tag("INVESTIGATION", self.action_option("Survey the tracks, barricades, and weak points first.")),
                ]
                + [text for _, text in self.scene_identity_options("phandalin_arrival")],
                allow_meta=False,
            )
            identity_options = self.scene_identity_options("phandalin_arrival")
            if choice > 3:
                selection_key, _ = identity_options[choice - 4]
                if self.handle_scene_identity_action("phandalin_arrival", selection_key):
                    return self.scene_phandalin_hub()
            elif choice == 1:
                self.player_speaker("I want to read the mood of the town before I speak.")
                success = self.skill_check(self.state.player, "Insight", 12, context="to gauge the town's fear")
                if success:
                    self.say(
                        "You catch the way fear keeps pulling the crowd's attention toward manor-side ruins, the east road, and a handful of people everybody seems to quietly trust."
                    )
                    self.add_clue("Iron Hollow's fear points in three directions: the east road, the old manor hill, and the few locals still holding the place together.")
                    self.reward_party(xp=10, reason="reading Iron Hollow's mood on arrival")
                else:
                    self.say("The town's fear is real, but too tangled to untangle in one glance.")
            elif choice == 2:
                self.player_speaker("Let them know Greywake sent help.")
                success = self.skill_check(self.state.player, "Persuasion", 12, context="to steady the town's nerves")
                if success:
                    self.say("A few shoulders ease as your words sound more like a promise than a performance.")
                    self.reward_party(xp=10, gold=6, reason="reassuring Iron Hollow on arrival")
                else:
                    self.say("People listen, but frontier caution clings harder than hope.")
            else:
                self.player_action("Show me the tracks, barricades, and weak points first.")
                success = self.skill_check(self.state.player, "Investigation", 12, context="to assess the town's defenses")
                if success:
                    self.say("Fresh wagon ruts, anxious repairs, and redirected lanes give you a usable picture of how fear is reshaping the town.")
                    self.add_clue("Recent wagon ruts suggest the Ashen Brand watches both the east road and the manor-side lanes.")
                    self.reward_party(xp=10, reason="surveying Iron Hollow's defenses")
                else:
                    self.say("There are too many overlapping tracks and half-finished repairs for a quick clean read.")

        self.run_phandalin_council_event()
        self.run_after_watch_gathering()

        while True:
            options: list[tuple[str, str]] = []
            if self.has_steward_interactions():
                options.append(("steward", self.action_option("Report to Steward Tessa Harrow")))
            options.append(("inn", self.action_option("Visit the Ashlamp Inn")))
            if self.has_shrine_interactions():
                options.append(("shrine", self.action_option("Stop by the Lantern shrine")))
            options.extend(
                [
                    ("barthen", self.skill_tag("TRADE", self.action_option("Browse Hadrik's Provisions"))),
                    ("linene", self.skill_tag("TRADE", self.action_option("Call on Linene Ironward at the Ironbound trading post"))),
                ]
            )
            if self.has_edermath_orchard_interactions():
                options.append(("orchard", self.action_option("Walk the old walls of Orchard Wall")))
            if self.has_miners_exchange_interactions():
                options.append(("exchange", self.action_option("Step into the Delvers' Exchange")))
            options.extend(
                [
                    ("camp", self.action_option("Return to camp")),
                    ("rest", self.action_option("Take a short rest")),
                ]
            )
            if not self.state.flags.get("old_owl_well_cleared"):
                label = self.action_option("Investigate Blackglass Well")
                if not self.can_visit_old_owl_well():
                    label = self.action_option("Investigate Blackglass Well (need a lead)")
                options.append(("old_owl", label))
            if not self.state.flags.get("wyvern_tor_cleared"):
                label = self.action_option("Hunt the raiders at Red Mesa Hold")
                if not self.can_visit_wyvern_tor():
                    label = self.action_option("Hunt the raiders at Red Mesa Hold (need a lead)")
                options.append(("wyvern", label))
            if not self.state.flags.get("ashfall_watch_cleared"):
                label = self.action_option("Ride for Ashfall Watch")
                if not self.act1_side_paths_cleared():
                    label = self.action_option("Ride for Ashfall Watch (clear Blackglass Well and Red Mesa Hold first)")
                options.append(("ashfall", label))
            elif not self.state.flags.get("tresendar_cleared"):
                label = self.action_option("Descend beneath Duskmere Manor")
                if not self.state.flags.get("tresendar_revealed"):
                    label = self.action_option("Descend beneath Duskmere Manor (wait for a firmer lead)")
                options.append(("tresendar", label))
            else:
                options.append(("emberhall", self.action_option("Descend into Emberhall Cellars")))

            choice = self.scenario_choice("Where do you go next?", [text for _, text in options])
            selection_key, _ = options[choice - 1]
            if selection_key == "steward":
                self.visit_steward()
            elif selection_key == "inn":
                self.visit_stonehill_inn()
            elif selection_key == "shrine":
                self.visit_shrine()
            elif selection_key == "barthen":
                self.visit_barthen_provisions()
            elif selection_key == "linene":
                self.visit_trading_post()
            elif selection_key == "orchard":
                self.visit_edermath_orchard()
            elif selection_key == "exchange":
                self.visit_miners_exchange()
            elif selection_key == "camp":
                self.open_camp_menu()
            elif selection_key == "rest":
                self.short_rest()
            elif selection_key == "old_owl":
                if not self.can_visit_old_owl_well():
                    self.say("You need a firmer lead on the well before marching the party into empty scrub.")
                    continue
                self.state.current_scene = "old_owl_well"
                return
            elif selection_key == "wyvern":
                if not self.can_visit_wyvern_tor():
                    self.say("You still need somebody to point you toward the tor and the raiders haunting it.")
                    continue
                self.state.current_scene = "wyvern_tor"
                return
            elif selection_key == "ashfall":
                if not self.act1_side_paths_cleared():
                    self.say("Ashfall Watch is still too dangerous to take cleanly without dealing with the outer threats first.")
                    continue
                self.state.current_scene = "ashfall_watch"
                return
            elif selection_key == "tresendar":
                if not self.state.flags.get("tresendar_revealed"):
                    self.say("You need a firmer lead before committing to the buried manor routes.")
                    continue
                self.state.current_scene = "tresendar_manor"
                return
            else:
                self.state.current_scene = "emberhall_cellars"
                return

    def visit_edermath_orchard(self) -> None:
        assert self.state is not None
        self.banner("Orchard Wall")
        if not self.state.flags.get("edermath_orchard_seen"):
            self.say(
                "Low stone walls shelter a battered orchard on the edge of town. Daran Orchard moves between the trees with a veteran's economy, trimming dead wood one moment and testing an old sword edge the next. "
                "The place feels less like a farm than a retired watchpost pretending to be one.",
                typed=True,
            )
            self.state.flags["edermath_orchard_seen"] = True
        while True:
            options: list[tuple[str, str]] = []
            if self.quest_is_ready("break_wyvern_tor_raiders"):
                options.append(("turn_in", self.action_option("Tell Daran what happened at Red Mesa Hold.")))
            if not self.state.flags.get("edermath_orchard_blight_checked"):
                options.append(
                    (
                        "blight",
                        self.quoted_option("NATURE", "Something is wrong with these trees. Let me see what the ash is doing."),
                    )
                )
            if not self.state.flags.get("edermath_orchard_wyvern_tor_asked"):
                options.append(("tor", "\"You look like someone who knows the hills. What is happening at Red Mesa Hold?\""))
            if not self.state.flags.get("edermath_orchard_training_done"):
                options.append(
                    (
                        "training",
                        self.quoted_option("ATHLETICS", "If you still drill, put me through a frontier warm-up."),
                    )
                )
            if not self.state.flags.get("edermath_old_cache_recovered"):
                options.append(
                    (
                        "cache",
                        self.quoted_option("STEALTH", "If your old cache is still buried, we can reach it quietly."),
                    )
                )
            options.append(("leave", self.action_option("Leave the orchard and head back toward town.")))
            choice = self.scenario_choice("Daran wipes orchard dust from his hands and waits.", [text for _, text in options])
            selection_key, _ = options[choice - 1]
            if selection_key == "turn_in":
                self.player_action("Red Mesa Hold is broken. The raiders there will not trouble Iron Hollow again.")
                self.speaker(
                    "Daran Orchard",
                    "Good. Some victories feel loud. The best kind just make a road safe enough that ordinary people stop talking about it.",
                )
                self.turn_in_quest("break_wyvern_tor_raiders", giver="Daran Orchard")
            elif selection_key == "blight":
                self.state.flags["edermath_orchard_blight_checked"] = True
                self.player_speaker("Something is wrong with these trees. Let me see what the ash is doing.")
                success = self.skill_check(
                    self.state.player,
                    "Nature",
                    12,
                    context="to tell normal orchard trouble from raider-caused blight",
                )
                if success:
                    self.say(
                        "The damage is not natural. Somebody deliberately salted the roots with ash and bad runoff to pressure Daran into leaving the wall and his vantage."
                    )
                    self.add_clue("The raiders are sabotaging orchard roots and farm walls to blind trusted lookouts around Iron Hollow.")
                    self.add_inventory_item("moonmint_drops", source="Daran's herb shelf")
                    self.reward_party(xp=10, reason="reading the orchard blight")
                else:
                    self.say("You can tell the ash was placed there, but not enough more than that to make the answer feel complete.")
            elif selection_key == "tor":
                self.state.flags["edermath_orchard_wyvern_tor_asked"] = True
                self.state.flags["edermath_orchard_lead"] = True
                self.player_speaker("You look like someone who knows the hills. What is happening at Red Mesa Hold?")
                self.speaker(
                    "Daran Orchard",
                    "Orcs, a worg pack, and a blood-chief with enough sense to use the old stone folds. They hit goat herders, road scouts, and anyone trying to move quietly east. "
                    "Clear the tor and you close one of the town's ugliest leaks.",
                )
                self.add_clue("Daran Orchard confirms organized raiders and worgs are working out of Red Mesa Hold.")
                if self.grant_quest(
                    "break_wyvern_tor_raiders",
                    note="Daran says Red Mesa Hold is the high-ground threat stalking scouts, herders, and anyone trying to move east unseen.",
                ):
                    self.speaker(
                        "Daran Orchard",
                        "Do the town a favor and do it thoroughly. Half-cleared hills only teach raiders to come back meaner.",
                    )
            elif selection_key == "training":
                self.state.flags["edermath_orchard_training_done"] = True
                self.player_speaker("If you still drill, put me through a frontier warm-up.")
                success = self.skill_check(
                    self.state.player,
                    "Athletics",
                    12,
                    context="to keep up with a retired adventurer's practical drill circuit",
                )
                if success:
                    self.say(
                        "Daran makes you work the wall, the ladder, and the loose-stone turn at speed until your breathing stops being decorative."
                    )
                    self.reward_party(xp=10, reason="drilling with Daran Orchard")
                    self.add_inventory_item("travel_biscuits", 2, source="Daran's field satchel")
                else:
                    self.speaker(
                        "Daran Orchard",
                        "Not bad. Frontier fighting is mostly staying useful after the first ugly surprise.",
                    )
            elif selection_key == "cache":
                self.run_edermath_old_cache_scene()
            else:
                self.player_action("You leave the orchard and head back toward the busier lanes.")
                return

    def run_edermath_old_cache_scene(self) -> None:
        assert self.state is not None
        self.banner("Orchard Wall: Old Adventurer's Cache")
        self.player_speaker("If your old cache is still buried, we can reach it quietly.")
        if self.state.flags.get("wyvern_tor_cleared"):
            self.speaker(
                "Daran Orchard",
                "After Red Mesa Hold, I believe you can follow ugly ground without flattering it. That helps. The map is still half-wrong because I drew it half-drunk and thirty years too confident. The other half is worse: somebody has been watching the orchard walls.",
            )
            self.say(
                "Daran adds a fresh correction from the tor fight: any watcher patient enough to hold this line will favor the low ditch, not the obvious gap in the wall."
            )
        else:
            self.speaker(
                "Daran Orchard",
                "Maybe. The map is half-wrong because I drew it half-drunk and thirty years too confident. The other half is worse: somebody has been watching the orchard walls.",
            )
        self.say(
            "Daran marks three old apple trees, a split stone, and a ditch that no longer exists. The true path is the negative space between them: low through root-shadow, then still beside the broken wall."
        )
        success = self.skill_check(
            self.state.player,
            "Stealth",
            12,
            context="to reach Daran's buried adventuring cache without alerting the orchard watchers",
        )
        if success:
            self.say(
                "You move when the wind worries the branches and freeze when a watcher turns. By the time the spade bites earth, nobody outside the orchard knows you were there."
            )
            self.state.flags["edermath_old_cache_quiet"] = True
            self.grant_edermath_old_cache_rewards(quiet=True)
            return

        self.say(
            "A loose stone clicks underfoot. The watching shape beyond the wall answers with a low whistle, and two Ashen Brand scouts come over the orchard edge with knives already out."
        )
        enemies = [create_enemy("brand_saboteur"), create_enemy("bandit_archer")]
        if self.act1_party_size() >= 3:
            enemies.append(create_enemy("bandit"))
        encounter = Encounter(
            "Orchard Wall Watchers",
            "Ashen Brand scouts caught watching Daran's old cache route turn a failed stealth approach into a close orchard fight.",
            enemies,
            allow_flee=True,
            allow_parley=False,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter(encounter)
        if outcome == "victory":
            self.say(
                "Daran wipes one blade clean, then points with the other to a root knot the watchers never understood. The cache comes up dented, dry, and still useful."
            )
            self.state.flags["edermath_old_cache_watchers_defeated"] = True
            self.grant_edermath_old_cache_rewards(quiet=False)
        else:
            self.say("The watchers keep enough of the orchard line to force you off the cache for now.")

    def grant_edermath_old_cache_rewards(self, *, quiet: bool) -> None:
        assert self.state is not None
        if self.state.flags.get("edermath_old_cache_recovered"):
            return
        self.state.flags["edermath_old_cache_recovered"] = True
        self.state.flags["edermath_old_cache_trust"] = True
        self.state.flags["act2_edermath_cache_routework"] = True
        self.add_inventory_item("edermath_cache_compass", source="Daran Orchard's old adventurer's cache")
        self.reward_party(xp=35, gold=12, reason="recovering Daran Orchard's old adventurer's cache")
        self.add_clue(
            "Daran's old cache map preserves a quiet orchard-to-highland route that can help control Act 2 approaches."
        )
        if quiet:
            self.speaker(
                "Daran Orchard",
                "Clean work. After Red Mesa Hold, I hoped you knew patience as well as pressure. Now I know it."
                if self.state.flags.get("wyvern_tor_cleared")
                else "Clean work. Old routes reward patience more often than courage. Remember that when everyone else starts calling haste a plan.",
            )
            self.add_journal(
                "You recovered Daran Orchard's old adventuring cache without alerting the orchard watchers, earning his trust and a route-control hook for Act 2."
            )
        else:
            self.speaker(
                "Daran Orchard",
                "Red Mesa Hold taught you to finish hard ground. This was messier than I hoped, but you finished it again, and now we know exactly who wanted that cache watched."
                if self.state.flags.get("wyvern_tor_cleared")
                else "Messier than I hoped. Still, you finished it, and now we know exactly who wanted that cache watched.",
            )
            self.add_journal(
                "You recovered Daran Orchard's old adventuring cache after fighting the orchard watchers, earning his trust and a route-control hook for Act 2."
            )

    def visit_miners_exchange(self) -> None:
        assert self.state is not None
        self.banner("Delvers' Exchange")
        if not self.state.flags.get("miners_exchange_seen"):
            self.say(
                "The Delvers' Exchange smells of wet stone, chalk dust, lamp oil, and bad news delivered in practical voices. Halia Vey runs the counter with polished calm, "
                "sorting claim tags and grievance slips while half the room tries not to look as worried as it is.",
                typed=True,
            )
            self.state.flags["miners_exchange_seen"] = True
        while True:
            options: list[tuple[str, str]] = []
            if self.quest_is_ready("silence_old_owl_well"):
                options.append(("turn_in", self.action_option("Tell Halia the threat at Blackglass Well has been dealt with.")))
            if not self.state.flags.get("miners_exchange_missing_crews_asked"):
                options.append(("missing", "\"Which crews are missing, and where did they vanish?\""))
            if not self.state.flags.get("miners_exchange_ledgers_checked"):
                options.append(
                    (
                        "ledgers",
                        self.quoted_option("INVESTIGATION", "Let me look at the tally books. Somebody is getting paid for this chaos."),
                    )
                )
            if not self.state.flags.get("miners_exchange_dispute_resolved"):
                options.append(
                    (
                        "dispute",
                        self.quoted_option("PERSUASION", "You two can stop shouting. Tell me what happened, and one of you gets to be right."),
                    )
                )
            options.append(("leave", self.action_option("Leave the exchange and step back into town.")))
            choice = self.scenario_choice("Halia closes one ledger with a fingertip and gives you her attention.", [text for _, text in options])
            selection_key, _ = options[choice - 1]
            if selection_key == "turn_in":
                self.player_action("Blackglass Well is silent. Whatever was digging there will not trouble your crews again.")
                self.speaker(
                    "Halia Vey",
                    "Excellent. Quiet roads make honest ore much easier to turn into coin.",
                )
                self.turn_in_quest("silence_old_owl_well", giver="Halia Vey")
            elif selection_key == "missing":
                self.state.flags["miners_exchange_missing_crews_asked"] = True
                self.state.flags["miners_exchange_lead"] = True
                self.player_speaker("Which crews are missing, and where did they vanish?")
                self.speaker(
                    "Halia Vey",
                    "Scouts east of town, grave-salvage teams who got too close to old stones, and one fool prospector who thought Blackglass Well was abandoned. It is not. "
                    "People go there and either disappear or come back talking about corpse-light and hired steel.",
                )
                self.add_clue("Halia Vey ties missing crews and salvage thefts to Blackglass Well.")
                if self.grant_quest(
                    "silence_old_owl_well",
                    note="Halia says Blackglass Well has become a grave-salvage site protected by both hired blades and something worse.",
                ):
                    self.speaker(
                        "Halia Vey",
                        "Bring me proof the well is quiet and I'll make it worth your time. Preferably the kind of proof that stays dead.",
                    )
            elif selection_key == "ledgers":
                self.state.flags["miners_exchange_ledgers_checked"] = True
                self.player_speaker("Let me look at the tally books. Somebody is getting paid for this chaos.")
                success = self.skill_check(
                    self.state.player,
                    "Investigation",
                    12,
                    context="to catch hidden patterns in the Delvers' Exchange ledgers",
                )
                if success:
                    self.say(
                        "The numbers show purchase spikes in shovels, grave-hooks, and lamp oil timed to raids elsewhere. Somebody has been feeding Blackglass Well from inside a broader supply web."
                    )
                    self.add_clue("Exchange ledgers show Blackglass Well being supplied as part of the Ashen Brand's wider logistics chain.")
                    self.reward_party(xp=10, reason="reading the exchange ledgers")
                else:
                    self.say("The books are too cleaned-up to expose the whole scheme, but not enough to feel honest.")
            elif selection_key == "dispute":
                self.state.flags["miners_exchange_dispute_resolved"] = True
                self.player_speaker("You two can stop shouting. Tell me what happened, and one of you gets to be right.")
                success = self.skill_check(
                    self.state.player,
                    "Persuasion",
                    12,
                    context="to cut through a bitter claim dispute without letting it become a brawl",
                )
                if success:
                    self.say(
                        "You pull the truth out of both miners before pride can ruin it, and Halia watches closely enough to remember the favor."
                    )
                    self.reward_party(xp=10, gold=8, reason="settling a claim dispute at the exchange")
                else:
                    self.speaker(
                        "Halia Vey",
                        "Worth trying. Next time I may just charge admission and let them tire themselves out.",
                    )
            else:
                self.player_action("You leave the exchange and return to the muddy lane outside.")
                return

    def scene_old_owl_well(self) -> None:
        assert self.state is not None
        self.banner("Blackglass Well")
        if not self.state.flags.get("old_owl_well_seen"):
            self.say(
                "The old watchtower rises from the scrub like a cracked finger of Netherese stone. Dig lines, corpse-salt circles, and half-collapsed tents surround the well itself, "
                "and every gust of wind seems to carry up dust that should have stayed buried.",
                typed=True,
            )
            self.state.flags["old_owl_well_seen"] = True
        party_size = self.act1_party_size()
        enemies = [create_enemy("skeletal_sentry"), create_enemy("bandit", name="Ashen Brand Fixer")]
        if party_size >= 3:
            enemies.append(self.act1_pick_enemy(("skeletal_sentry", "rust_shell_scuttler", "ashstone_percher", "briar_twig")))
        hero_bonus = self.apply_scene_companion_support("old_owl_well")
        choice = self.scenario_choice(
            "How do you work the edge of the site?",
            [
                self.skill_tag("STEALTH", self.action_option("Move along the broken irrigation trench and get inside the ring quietly.")),
                self.quoted_option("ARCANA", "Those sigils matter. Let me read what kind of wrongness is powering them."),
                self.quoted_option("DECEPTION", "Call out as hired salvage come to collect the next cart of bones."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Move along the broken irrigation trench and get inside the ring quietly.")
            success = self.skill_check(self.state.player, "Stealth", 13, context="to slip into the dig site unseen")
            if success:
                self.apply_status(enemies[0], "surprised", 1, source="your trench approach")
                enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
                hero_bonus += 2
                self.say("You are inside the ward-ring before the first skull-lantern turns your way.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="loose stone and a snapped old bucket chain")
                self.say("A snapped chain and shower of stone give the site plenty of warning.")
        elif choice == 2:
            self.player_speaker("Those sigils matter. Let me read what kind of wrongness is powering them.")
            success = self.skill_check(self.state.player, "Arcana", 13, context="to read the ward sigils before they flare")
            if success:
                self.apply_status(self.state.player, "resist_poison", 3, source="ward-script countermeasures")
                if len(enemies) > 1:
                    self.apply_status(enemies[1], "reeling", 2, source="your disruption of the ritual ring")
                hero_bonus += 1
                self.say("You spoil the smooth flow of the ritual enough to leave the defenders moving through their own half-broken pattern.")
            else:
                self.say("The symbols are older and uglier than you wanted them to be, and the answer comes back as a pulse of cold air instead of clarity.")
        else:
            self.player_speaker("Hired salvage. Open the line before the carts start backing up.")
            success = self.skill_check(self.state.player, "Deception", 13, context="to bluff your way into the dig perimeter")
            if success:
                if len(enemies) > 1:
                    enemies[1].current_hp = max(1, enemies[1].current_hp - 3)
                    self.apply_status(enemies[1], "surprised", 1, source="your sudden betrayal")
                hero_bonus += 1
                self.say("The bluff holds just long enough for your first strike to turn the whole ring inside out.")
            else:
                self.apply_status(self.state.player, "surprised", 1, source="a suspicious foreman's shout")
                self.say("The closest hireling narrows their eyes, then starts yelling for the dead to rise.")

        first_encounter = Encounter(
            title="Blackglass Well Dig Ring",
            description="Bone-haulers and animated sentries close around the well mouth.",
            enemies=enemies,
            allow_flee=True,
            allow_parley=False,
            hero_initiative_bonus=hero_bonus,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter(first_encounter)
        if outcome == "defeat":
            self.handle_defeat("The dead keep their watch at Blackglass Well.")
            return
        if outcome == "fled":
            self.state.current_scene = "phandalin_hub"
            self.say("You fall back from the well before the site can swallow the whole party.")
            return

        self.say(
            "With the outer ring broken, you find a prospector lashed near a salt cart and a page of soot-black notes describing shipments onward to Ashfall and the manor hill."
        )
        choice = self.scenario_choice(
            "What do you do in the short lull?",
            [
                self.quoted_option("MEDICINE", "Cut the prospector free and keep them steady long enough to speak."),
                self.quoted_option("INVESTIGATION", "Read the notes and sketch the route chain before the wind ruins them."),
                self.action_option("Kick the salt cart into the ritual trench and foul the whole site."),
            ],
            allow_meta=False,
        )
        boss_bonus = 0
        if choice == 1:
            self.player_speaker("Cut the prospector free and keep them steady long enough to speak.")
            success = self.skill_check(
                self.state.player,
                "Medicine",
                12,
                context="to stabilize the prospector before shock takes their memory with it",
            )
            if success:
                self.say("The prospector gasps out one useful truth before passing out: the gravecaller answers to Ashfall's coin and the manor's keys.")
                self.add_clue("A rescued prospector says the gravecaller at Blackglass Well was being paid through Ashfall Watch for work tied to the manor hill.")
                boss_bonus += 1
                self.reward_party(xp=10, reason="saving the prospector at Blackglass Well")
            else:
                self.say("You save the prospector's life, but not a clean version of what they saw.")
        elif choice == 2:
            self.player_speaker("Read the notes and sketch the route chain before the wind ruins them.")
            success = self.skill_check(
                self.state.player,
                "Investigation",
                12,
                context="to preserve the gravecaller notes before they scatter",
            )
            if success:
                self.say("The page names Ashfall Watch as the collection point and mentions a soot-key transfer beneath the old manor hill.")
                self.add_clue("The Blackglass Well notes point to Ashfall Watch as the collection point for salvage moved toward the manor hill.")
                boss_bonus += 1
                self.reward_party(xp=10, reason="securing the Blackglass Well route notes")
            else:
                self.say("You save fragments, but the ugliest details go spinning away with the dust.")
        else:
            self.player_action("Kick the salt cart into the ritual trench and foul the whole site.")
            self.say("White salt and grave ash spill through the sigil cuts, forcing the inner ring to stutter and flare.")
            boss_bonus += 2

        self.say(
            "A hooded gravecaller rises from the well mouth itself, one hand blackened to the wrist by ritual soot. Their voice is calm in the way only committed fools and true fanatics manage."
        )
        self.speaker(
            "Vaelith Marr",
            "You are late. The dead were almost ready to remember who owned this land before your little town learned to squat on it.",
        )
        boss_enemies = [create_enemy("vaelith_marr")]
        if party_size >= 2:
            boss_enemies.append(create_enemy("carrion_lash_crawler"))
        if party_size >= 4:
            boss_enemies.append(self.act1_pick_enemy(("skeletal_sentry", "graveblade_wight", "lantern_fen_wisp")))
        choice = self.scenario_choice(
            "How do you answer the gravecaller?",
            [
                self.quoted_option("RELIGION", "These dead are not yours to command. Let them go."),
                self.quoted_option("INTIMIDATION", "You are finished here. Step away from the well and survive it."),
                self.action_option("Rush the ritual line before another corpse can stand."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("These dead are not yours to command. Let them go.")
            success = self.skill_check(self.state.player, "Religion", 13, context="to break the gravecaller's hold on the risen dead")
            if success:
                if len(boss_enemies) > 1:
                    self.apply_status(boss_enemies[1], "frightened", 2, source="your command over the dead")
                self.apply_status(boss_enemies[0], "reeling", 1, source="a broken ritual cadence")
                self.say("For one sharp moment the dead hesitate as if something older than Vaelith has finally been heard.")
            else:
                self.say("The words are right. The gravecaller simply believes the wrong thing harder.")
        elif choice == 2:
            self.player_speaker("You are finished here. Step away from the well and survive it.")
            success = self.skill_check(self.state.player, "Intimidation", 13, context="to crack the gravecaller's composure")
            if success:
                boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 4)
                self.apply_status(boss_enemies[0], "frightened", 1, source="your iron-edged demand")
                self.say("Vaelith gives ground almost without meaning to, and the dead feel the break in confidence.")
            else:
                self.apply_status(boss_enemies[0], "emboldened", 2, source="your failed threat")
                self.speaker("Vaelith Marr", "You speak like the living have ever held a thing permanently.")
        else:
            self.player_action("Rush the ritual line before another corpse can stand.")
            boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 3)
            boss_bonus += 2
            self.say("You break the distance fast enough to make the first exchange happen inside Vaelith's own ward-ring.")

        boss_encounter = Encounter(
            title="Miniboss: Vaelith Marr",
            description="The gravecaller of Blackglass Well fights from the lip of the buried dark.",
            enemies=boss_enemies,
            allow_flee=True,
            allow_parley=False,
            hero_initiative_bonus=boss_bonus,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter(boss_encounter)
        if outcome == "defeat":
            self.handle_defeat("The well's corpse-lights burn on above the fallen party.")
            return
        if outcome == "fled":
            self.state.current_scene = "phandalin_hub"
            self.say("You break contact and retreat to Iron Hollow with the well still active behind you.")
            return

        self.state.flags["old_owl_well_cleared"] = True
        self.add_clue("Blackglass Well is cleared, and its notes tie grave-salvage, Ashfall Watch, and the manor hill into one supply chain.")
        self.add_journal("You silenced Blackglass Well and broke one of the Ashen Brand's outer operations.")
        refresh_quest_statuses = getattr(self, "refresh_quest_statuses", None)
        if callable(refresh_quest_statuses):
            refresh_quest_statuses(announce=False)
        self.add_inventory_item("scroll_lesser_restoration", source="Vaelith's ritual satchel")
        self.state.current_scene = "phandalin_hub"

    def scene_wyvern_tor(self) -> None:
        assert self.state is not None
        self.banner("Red Mesa Hold")
        if not self.state.flags.get("wyvern_tor_seen"):
            self.say(
                "Red Mesa Hold looms out of the hills in broken shelves of wind-cut stone. Goat paths, old watch cairns, and smoke-stained hollows twist around the ridge, "
                "and something large has been pacing the high ground long enough to turn the dust into habitual scars.",
                typed=True,
            )
            self.state.flags["wyvern_tor_seen"] = True
        party_size = self.act1_party_size()
        enemies = [create_enemy("orc_raider"), create_enemy("worg")]
        if party_size >= 3:
            enemies.append(self.act1_pick_enemy(("orc_raider", "bugbear_reaver", "acidmaw_burrower", "cliff_harpy")))
        hero_bonus = self.apply_scene_companion_support("wyvern_tor")
        choice = self.scenario_choice(
            "How do you take the tor?",
            [
                self.skill_tag("SURVIVAL", self.action_option("Use the goat path and the wind shadow to reach the upper shelf.")),
                self.skill_tag("STEALTH", self.action_option("Shadow the smoke line and hit the pickets first.")),
                self.quoted_option("NATURE", "The worg pack is the key. Let me read where it expects prey to run."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Use the goat path and the wind shadow to reach the upper shelf.")
            success = self.skill_check(self.state.player, "Survival", 13, context="to take the hidden path up Red Mesa Hold")
            if success:
                self.apply_status(enemies[0], "surprised", 1, source="your high approach")
                hero_bonus += 2
                self.say("You come out above the outer camp instead of below it, which changes the whole feel of the fight.")
            else:
                self.say("The path is real, but not as forgiving as the goats make it look.")
        elif choice == 2:
            self.player_action("Shadow the smoke line and hit the pickets first.")
            success = self.skill_check(self.state.player, "Stealth", 13, context="to get onto the shelf before the pickets spot you")
            if success:
                enemies[-1].current_hp = max(1, enemies[-1].current_hp - 4)
                self.apply_status(enemies[-1], "reeling", 1, source="your opening strike")
                hero_bonus += 1
                self.say("The closest lookout goes down hard enough that the alarm comes late and ugly.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="gravel underfoot")
                self.say("Loose scree gives you away and the shelf erupts into motion.")
        else:
            self.player_speaker("The worg pack is the key. Let me read where it expects prey to run.")
            success = self.skill_check(self.state.player, "Nature", 13, context="to predict the worg's line of attack")
            if success:
                self.apply_status(enemies[1], "frightened", 1, source="your perfect read of its momentum")
                hero_bonus += 1
                self.say("You move before the beast commits, which steals its best rush cleanly away.")
            else:
                self.say("You read enough to know the worg is clever, not enough to stop it from choosing the angle first.")

        first_encounter = Encounter(
            title="Red Mesa Hold Shelf Fight",
            description="Orc raiders and a hunting worg defend the tor's outer shelf.",
            enemies=enemies,
            allow_flee=True,
            allow_parley=False,
            hero_initiative_bonus=hero_bonus,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter(first_encounter)
        if outcome == "defeat":
            self.handle_defeat("Red Mesa Hold keeps the high ground and the road below it.")
            return
        if outcome == "fled":
            self.state.current_scene = "phandalin_hub"
            self.say("You break away from the tor and retreat before the shelf turns into a killing bowl.")
            return

        self.say(
            "Beyond the outer shelf you find butcher hooks, stolen tack, and a terrified drover bound near a cairn shrine to Tempus that the raiders have half-defaced."
        )
        boss_bonus = 0
        choice = self.scenario_choice(
            "What do you handle before the chief reaches you?",
            [
                self.quoted_option("MEDICINE", "Get the drover breathing right and find out how many are still above us."),
                self.quoted_option("RELIGION", "Set the cairn shrine right. I want the chief fighting under a bad sign."),
                self.action_option("Cut the pack tethers and send the remaining beasts into the upper camp."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Get the drover breathing right and find out how many are still above us.")
            success = self.skill_check(
                self.state.player,
                "Medicine",
                12,
                context="to steady the captured drover before shock takes over",
            )
            if success:
                self.say("The drover coughs out one clean answer: a blood-chief named Brughor, one ogre, and enough ego to think the hill already belongs to him.")
                self.add_clue("A captured drover confirms Brughor holds Red Mesa Hold with an ogre and a small disciplined raiding party.")
                boss_bonus += 1
                self.reward_party(xp=10, reason="saving the captured drover at Red Mesa Hold")
            else:
                self.say("The drover lives, but the useful details come back in broken pieces.")
        elif choice == 2:
            self.player_speaker("Set the cairn shrine right. I want the chief fighting under a bad sign.")
            success = self.skill_check(
                self.state.player,
                "Religion",
                12,
                context="to restore the cairn shrine enough to unsettle the raiders",
            )
            if success:
                self.apply_status(self.state.player, "blessed", 2, source="the restored cairn shrine")
                boss_bonus += 1
                self.say("You set the cairn stones true again, and the hill stops feeling entirely like theirs.")
            else:
                self.say("You do what you can with the broken shrine, but the best of the omen slips through your fingers.")
        else:
            self.player_action("Cut the pack tethers and send the remaining beasts into the upper camp.")
            self.say("Goats and half-starved pack animals scatter uphill in a chaos of bells and hooves, dragging the upper camp's attention sideways.")
            boss_bonus += 2

        self.say(
            "A broad-shouldered orc in scavenged scale laughs once as he comes down from the upper shelf, great axe low in one hand and old blood drying on his bracers. "
            "An ogre lumbers after him, dragging a club over stone."
        )
        self.speaker(
            "Brughor Skullcleaver",
            "Good. I was getting tired of prey that ran downhill.",
        )
        boss_enemies = [create_enemy("orc_bloodchief", name="Brughor Skullcleaver")]
        if party_size >= 2:
            boss_enemies.append(self.act1_pick_enemy(("ogre_brute", "ettervine_webherd")))
        if party_size >= 4:
            boss_enemies.append(self.act1_pick_enemy(("orc_raider", "bugbear_reaver")))
        choice = self.scenario_choice(
            "How do you answer the blood-chief?",
            [
                self.quoted_option("INTIMIDATION", "You picked the wrong town to stalk."),
                self.quoted_option("ATHLETICS", "Then come down the rest of the way and see how long you stand."),
                self.action_option("Hit the chief before the ogre can settle into the fight."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("You picked the wrong town to stalk.")
            success = self.skill_check(self.state.player, "Intimidation", 13, context="to meet Brughor's violence with greater certainty")
            if success:
                boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 4)
                self.apply_status(boss_enemies[0], "frightened", 1, source="your refusal to yield ground")
                self.say("Brughor's grin slips for a heartbeat, and the hill feels smaller around him.")
            else:
                self.apply_status(boss_enemies[0], "emboldened", 2, source="your challenge feeding his pride")
                self.speaker("Brughor Skullcleaver", "Better. Fearless prey usually swings harder.")
        elif choice == 2:
            self.player_speaker("Then come down the rest of the way and see how long you stand.")
            success = self.skill_check(self.state.player, "Athletics", 13, context="to own the footing and force the chief into your timing")
            if success:
                self.apply_status(self.state.player, "emboldened", 2, source="holding the shelf against Brughor's rush")
                boss_bonus += 1
                self.say("You take the rock shelf like a shield line, and Brughor has to meet you on terms he did not choose.")
            else:
                self.say("The footing is uglier than your confidence suggested, and the chief sees it.")
        else:
            self.player_action("Hit the chief before the ogre can settle into the fight.")
            boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 3)
            boss_bonus += 2
            self.say("You crash into the upper shelf before the whole enemy line can come together cleanly.")

        boss_encounter = Encounter(
            title="Miniboss: Brughor Skullcleaver",
            description="The blood-chief of Red Mesa Hold makes his stand on the broken high shelf.",
            enemies=boss_enemies,
            allow_flee=True,
            allow_parley=False,
            hero_initiative_bonus=boss_bonus,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter(boss_encounter)
        if outcome == "defeat":
            self.handle_defeat("Brughor leaves the hill red and the road below it empty.")
            return
        if outcome == "fled":
            self.state.current_scene = "phandalin_hub"
            self.say("You pull clear of the upper shelf and retreat to Iron Hollow to regroup.")
            return

        self.state.flags["wyvern_tor_cleared"] = True
        self.add_clue("Red Mesa Hold is cleared, and its raiders were coordinating with Ashfall Watch rather than acting alone.")
        self.add_journal("You broke the raiders at Red Mesa Hold and stripped another outer shield away from the Ashen Brand.")
        refresh_quest_statuses = getattr(self, "refresh_quest_statuses", None)
        if callable(refresh_quest_statuses):
            refresh_quest_statuses(announce=False)
        self.add_inventory_item("greater_healing_draught", source="Brughor's travel chest")
        self.state.current_scene = "phandalin_hub"

    def scene_ashfall_watch(self) -> None:
        assert self.state is not None
        self.banner("Ashfall Watch")
        self.say(
            "Ashfall Watch crouches over the road in layered ruin and fresh timber: a snapped tower, palisade repairs, prisoner cages, and a signal basin built to spit smoke across the hills. "
            "It is no longer just a raider den. It is a frontier choke point built on fear and scheduling.",
            typed=True,
        )
        party_size = self.act1_party_size()
        enemies = [create_enemy("bandit"), create_enemy("bandit_archer")]
        if party_size >= 3:
            enemies.append(self.act1_pick_enemy(("worg", "gutter_zealot", "rust_shell_scuttler")))
        hero_bonus = self.apply_scene_companion_support("ashfall_watch")
        choice = self.scenario_choice(
            "How do you open the assault?",
            [
                self.skill_tag("STEALTH", self.action_option("Slip up the ruin side and cut the outer line quietly.")),
                self.quoted_option("DECEPTION", "Late relief from the tor. Open up before the ridge goes black."),
                self.skill_tag("ATHLETICS", self.action_option("Hit the wagon gate before the watch can settle.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Slip up the ruin side and cut the outer line quietly.")
            success = self.skill_check(self.state.player, "Stealth", 13, context="to reach the outer ruin unseen")
            if success:
                self.apply_status(enemies[1], "surprised", 1, source="your silent wall-climb")
                enemies[1].current_hp = max(1, enemies[1].current_hp - 4)
                hero_bonus += 2
                self.say("You are inside the outer ruin before the first lookout can call the line.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="slipping on loose stone")
                self.say("Loose stone skips down the wall and the alarm comes early.")
        elif choice == 2:
            self.player_speaker("Late relief from the tor. Open up before the ridge goes black.")
            success = self.skill_check(self.state.player, "Deception", 13, context="to sell a field report at the gate")
            if success:
                self.apply_status(enemies[0], "surprised", 1, source="your sudden betrayal")
                enemies[0].current_hp = max(1, enemies[0].current_hp - 3)
                hero_bonus += 1
                self.say("The lie holds exactly long enough to put the first defender down badly.")
            else:
                self.apply_status(self.state.player, "surprised", 1, source="the sentry's barked alarm")
                self.say("The sentry does not buy it, and now the whole gate is shouting.")
        else:
            self.player_action("Hit the wagon gate before the watch can settle.")
            success = self.skill_check(self.state.player, "Athletics", 13, context="to burst through the wagon gate with momentum")
            if success:
                self.apply_status(self.state.player, "emboldened", 2, source="blasting through the gate")
                self.apply_status(enemies[0], "prone", 1, source="the splintered rush")
                hero_bonus += 2
                self.say("The gate gives under force and the outer line loses shape immediately.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="hitting the gate wrong")
                self.say("The gate still gives, but the impact costs you the clean opening.")

        first_encounter = Encounter(
            title="Ashfall Gate",
            description="Outer sentries scramble between ruined stone, cages, and signal braziers.",
            enemies=enemies,
            allow_flee=True,
            allow_parley=True,
            parley_dc=13,
            hero_initiative_bonus=hero_bonus,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter(first_encounter)
        if outcome == "defeat":
            self.handle_defeat("Ashfall Watch remains in enemy hands.")
            return
        if outcome == "fled":
            self.state.current_scene = "phandalin_hub"
            self.say("You fall back to Iron Hollow to rethink the assault.")
            return

        self.say(
            "With the gate broken, you reach a prisoner yard, the tower's smoke basin, and a half-charred order board marked with Rukhar's hand."
        )
        second_bonus = 0
        choice = self.scenario_choice(
            "What do you handle before the inner barracks can form up?",
            [
                self.skill_tag("STEALTH", self.action_option("Snuff the signal basin before anyone can call the ridge.")),
                self.skill_tag("ATHLETICS", self.action_option("Break the prisoner cage and arm whoever can still stand.")),
                self.quoted_option("INVESTIGATION", "Read the order board. If Rukhar thinks in patterns, I want them now."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Snuff the signal basin before anyone can call the ridge.")
            success = self.skill_check(self.state.player, "Stealth", 12, context="to kill the signal basin without drawing the whole court")
            if success:
                second_bonus += 2
                self.say("You smother the basin under wet tarp and grit. No help is coming from the ridge in time to matter.")
            else:
                self.say("You kill the signal late and loud, but late still counts for something.")
                second_bonus += 1
        elif choice == 2:
            self.player_action("Break the prisoner cage and arm whoever can still stand.")
            success = self.skill_check(self.state.player, "Athletics", 12, context="to break the cage open fast enough to matter")
            if success:
                self.apply_status(self.state.player, "emboldened", 1, source="freed prisoners roaring for revenge")
                second_bonus += 2
                self.reward_party(xp=15, reason="freeing Ashfall's prisoners under fire")
                self.say("A few freed prisoners grab dropped clubs and stones, throwing the barracks response into chaos.")
            else:
                self.say("You free them, but not cleanly enough to keep the barracks from organizing.")
        else:
            self.player_speaker("Read the order board. If Rukhar thinks in patterns, I want them now.")
            success = self.skill_check(
                self.state.player,
                "Investigation",
                12,
                context="to read Rukhar's order board in the middle of the assault",
            )
            if success:
                self.add_clue("Rukhar rotates his strongest fighters through the lower barracks before taking the courtyard himself.")
                second_bonus += 1
                self.reward_party(xp=15, reason="reading Rukhar's order board under pressure")
                self.say("You catch enough of the rotation to know exactly which door the inner response will use.")
            else:
                self.say("You get fragments, but not the whole shape of his defense.")

        second_enemies = [create_enemy("bandit"), create_enemy("bandit_archer", name="Ashen Brand Barracks Archer")]
        if party_size >= 2:
            second_enemies.append(self.act1_pick_enemy(("bandit", "orc_raider", "gutter_zealot", "ashstone_percher")))
        if party_size >= 4:
            second_enemies.append(self.act1_pick_enemy(("orc_raider", "rust_shell_scuttler", "bugbear_reaver")))
        second_encounter = Encounter(
            title="Ashfall Lower Barracks",
            description="Veterans and hired blades spill out of the lower barracks in a hard organized rush.",
            enemies=second_enemies,
            allow_flee=True,
            allow_parley=True,
            parley_dc=14,
            hero_initiative_bonus=second_bonus,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter(second_encounter)
        if outcome == "defeat":
            self.handle_defeat("Ashfall's lower barracks break the party in the smoke.")
            return
        if outcome == "fled":
            self.state.current_scene = "phandalin_hub"
            self.say("You drag the party clear of the lower yard and retreat before the courtyard can close on you.")
            return

        self.say(
            "At the tower court's heart, a disciplined hobgoblin in darkened mail steps through the smoke with the calm of a soldier who has already sorted the dead from the living."
        )
        self.speaker(
            "Rukhar Cinderfang",
            "You have cost my employers time, coin, and useful subordinates. I will not pretend that leaves us room for civility.",
        )
        boss_enemies = [create_enemy("rukhar")]
        if party_size >= 2:
            boss_enemies.append(self.act1_pick_enemy(("bandit", "gutter_zealot", "bugbear_reaver")))
        if party_size >= 4:
            boss_enemies.append(self.act1_pick_enemy(("orc_raider", "rust_shell_scuttler")))
        boss_bonus = 0
        choice = self.scenario_choice(
            "Rukhar raises his blade and waits to see how you answer.",
            [
                self.quoted_option("INTIMIDATION", "Surrender the yard in Iron Hollow's name."),
                self.quoted_option("PERSUASION", "Your paymaster is already losing. Walk away with the people who still can."),
                self.action_option("Strike before he can settle the shield line."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Surrender the yard in Iron Hollow's name.")
            success = self.skill_check(self.state.player, "Intimidation", 13, context="to crack Rukhar's command posture")
            if success:
                boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 4)
                self.apply_status(boss_enemies[0], "frightened", 1, source="your iron-edged demand")
                self.say("Rukhar's line tightens too hard, which is its own kind of weakness.")
            else:
                self.apply_status(boss_enemies[0], "emboldened", 2, source="your failed demand")
                self.speaker("Rukhar Cinderfang", "Good. You arrived with a spine.")
        elif choice == 2:
            self.player_speaker("Your paymaster is already losing. Walk away with the people who still can.")
            success = self.skill_check(self.state.player, "Persuasion", 13, context="to separate Rukhar from the men still taking his orders")
            if success:
                fleeing = boss_enemies.pop() if len(boss_enemies) > 1 else None
                if fleeing is not None:
                    self.say(f"{fleeing.name} looks at the smoke, looks at Rukhar, and decides not to die for bookkeeping.")
                self.apply_status(boss_enemies[0], "reeling", 1, source="his line cracking around him")
            else:
                self.say("Rukhar's discipline holds harder than your mercy can pry apart.")
        else:
            self.player_action("Strike before he can settle the shield line.")
            boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 3)
            boss_bonus += 2
            self.say("Steel answers before speeches can, and the final fight begins in motion.")

        boss_encounter = Encounter(
            title="Miniboss: Rukhar Cinderfang",
            description="The Ashfall sergeant rallies the last disciplined core of the Ashen Brand field force.",
            enemies=boss_enemies,
            allow_flee=True,
            allow_parley=True,
            parley_dc=14,
            hero_initiative_bonus=boss_bonus,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter(boss_encounter)
        if outcome == "defeat":
            self.handle_defeat("Rukhar drives the party from the tower in blood and smoke.")
            return
        if outcome == "fled":
            self.state.current_scene = "phandalin_hub"
            self.say("You escape the watchtower and retreat to Iron Hollow to regroup.")
            return

        self.state.flags["ashfall_watch_cleared"] = True
        self.add_clue("Rukhar carried a soot-black key stamped with the Duskmere crest and orders to move captives beneath the manor hill.")
        self.add_journal("Ashfall Watch is broken, but the Ashen Brand's cellar routes beneath Iron Hollow are still active.")
        refresh_quest_statuses = getattr(self, "refresh_quest_statuses", None)
        if callable(refresh_quest_statuses):
            refresh_quest_statuses(announce=False)
        self.say(
            "Among Rukhar's orders you find a blackened key bearing the Duskmere crest, prisoner transfer notes, and references to a deeper reserve called Emberhall. "
            "The field base is broken, but the gang's thinking parts are still below town."
        )
        self.state.current_scene = "phandalin_hub"

    def scene_tresendar_manor(self) -> None:
        assert self.state is not None
        self.banner("Duskmere Manor")
        self.say(
            "The ruined manor crouches over Iron Hollow like a memory that never learned to stay buried. Beneath the broken shell, a hidden stair drops into wet stone, cistern corridors, and ash-marked cellars where the Ashen Brand keeps its quieter work.",
            typed=True,
        )
        party_size = self.act1_party_size()
        enemies = [create_enemy("bandit", name="Ashen Brand Collector"), create_enemy("bandit_archer", name="Archive Cutout")]
        if party_size >= 3:
            enemies.append(self.act1_pick_enemy(("skeletal_sentry", "mireweb_spider", "cache_mimic", "ashstone_percher")))
        hero_bonus = self.apply_scene_companion_support("tresendar_manor")
        choice = self.scenario_choice(
            "How do you enter the buried manor?",
            [
                self.quoted_option("INVESTIGATION", "There is a hidden stair here somewhere. Let me find the one they trust."),
                self.skill_tag("STEALTH", self.action_option("Slip through the collapsed chapel side and into the cellars.")),
                self.skill_tag("ATHLETICS", self.action_option("Rip the old cistern grate open and take the straight drop.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("There is a hidden stair here somewhere. Let me find the one they trust.")
            success = self.skill_check(
                self.state.player,
                "Investigation",
                13,
                context="to find the concealed manor intake route",
            )
            if success:
                self.apply_status(enemies[0], "surprised", 1, source="your hidden entry")
                hero_bonus += 2
                self.say("You find the concealed stair and enter on the defenders' blind side.")
            else:
                self.say("You find the route, just not before the noise of the search carries below.")
        elif choice == 2:
            self.player_action("Slip through the collapsed chapel side and into the cellars.")
            success = self.skill_check(self.state.player, "Stealth", 13, context="to cross the broken chapel without warning the cellars")
            if success:
                enemies[1].current_hp = max(1, enemies[1].current_hp - 4)
                self.apply_status(enemies[1], "reeling", 1, source="your chapel-side opening")
                hero_bonus += 1
                self.say("You come through the chapel rubble already moving and the first lookout never gets set.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="a falling stone saint-head")
                self.say("A broken stone saint tumbles and announces you to the lower rooms.")
        else:
            self.player_action("Rip the old cistern grate open and take the straight drop.")
            success = self.skill_check(self.state.player, "Athletics", 13, context="to force the old grate without losing balance on the drop")
            if success:
                self.apply_status(self.state.player, "emboldened", 2, source="a brutal manor breach")
                self.apply_status(enemies[0], "prone", 1, source="the crashing grate and falling iron")
                hero_bonus += 1
                self.say("The grate comes free in a crash of iron and you land already driving the fight.")
            else:
                self.apply_status(self.state.player, "prone", 1, source="a bad landing through the cistern grate")
                self.say("The grate gives, but the landing is uglier than planned.")

        first_encounter = Encounter(
            title="Duskmere Cellars",
            description="Collectors, cutouts, and buried sentries hold the intake route beneath the manor.",
            enemies=enemies,
            allow_flee=True,
            allow_parley=True,
            parley_dc=13,
            hero_initiative_bonus=hero_bonus,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter(first_encounter)
        if outcome == "defeat":
            self.handle_defeat("The buried manor swallows the party beneath Iron Hollow.")
            return
        if outcome == "fled":
            self.state.current_scene = "phandalin_hub"
            self.say("You pull back from the manor tunnels before the whole cellar network can close around you.")
            return

        self.say(
            "Beyond the intake cellars lies a cracked cistern where something with a single reflective eye is moving through the dark as if it has been fed on secrets instead of meat."
        )
        second_bonus = 0
        choice = self.scenario_choice(
            "How do you handle the thing in the cistern before it fully commits?",
            [
                self.quoted_option("INSIGHT", "It is testing us. Let me read what it wants before it strikes."),
                self.quoted_option("ARCANA", "That is no simple cellar monster. I want its pattern before it gets mine."),
                self.action_option("Throw a ration sack into the dark and charge while it turns."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("It is testing us. Let me read what it wants before it strikes.")
            success = self.skill_check(
                self.state.player,
                "Insight",
                13,
                context="to read the cistern horror's attention before it breaks cover",
            )
            if success:
                second_bonus += 1
                self.say("The creature wants secrets and weakness first, flesh second. Knowing that lets you meet its gaze without offering either too freely.")
            else:
                self.say("You catch hunger, curiosity, and malice all at once, which is not the same as understanding.")
        elif choice == 2:
            self.player_speaker("That is no simple cellar monster. I want its pattern before it gets mine.")
            success = self.skill_check(
                self.state.player,
                "Arcana",
                13,
                context="to identify the cistern horror before it opens the fight",
            )
            if success:
                self.apply_status(self.state.player, "blessed", 1, source="naming the cistern horror correctly")
                second_bonus += 1
                self.say("Putting the creature into words steals some of the fear it was trying to weaponize.")
            else:
                self.say("Naming the horror correctly does not stop it from grinning at you out of the dark.")
        else:
            self.player_action("Throw a ration sack into the dark and charge while it turns.")
            second_bonus += 2
            self.say("The sack hits water, the yellow eye turns, and you use the half-second it gives you.")

        second_enemies = [create_enemy("nothic", name="Cistern Eye")]
        if party_size >= 3:
            second_enemies.append(self.act1_pick_enemy(("skeletal_sentry", "stonegaze_skulker", "whispermaw_blob", "lantern_fen_wisp")))
        enemy_bonus = 0
        route_shell = getattr(self, "_tresendar_nothic_route_shell", None)
        if callable(route_shell):
            route_bonus, enemy_bonus = route_shell(second_enemies[0])
            second_bonus += route_bonus
        second_encounter = Encounter(
            title="The Cistern Eye",
            description="A warped cellar horror rises from the dark water below Duskmere Manor.",
            enemies=second_enemies,
            allow_flee=True,
            allow_parley=False,
            hero_initiative_bonus=second_bonus,
            enemy_initiative_bonus=enemy_bonus,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter(second_encounter)
        if outcome == "defeat":
            self.handle_defeat("The cistern horror keeps its secrets and your bodies with them.")
            return
        if outcome == "fled":
            self.state.current_scene = "phandalin_hub"
            self.say("You retreat from the cistern dark before the manor can claim the rest of the night.")
            return

        self.state.flags["tresendar_cleared"] = True
        self.state.flags["emberhall_revealed"] = True
        self.add_clue("Duskmere Manor was the Ashen Brand's intake route; Varyn's remaining core has withdrawn into Emberhall below.")
        self.add_journal("You cleared the buried Duskmere route and confirmed Varyn has fallen back to Emberhall for the final stand.")
        self.add_inventory_item("scroll_arcane_refresh", source="a sealed coffer in the cistern alcove")
        self.state.current_scene = "phandalin_hub"

    def scene_emberhall_cellars(self) -> None:
        assert self.state is not None
        self.banner("Emberhall Cellars")
        self.say(
            "Near midnight, you descend into Emberhall: old stone vaults, stolen crates, poison tables, ash-marked banners, and the last disciplined knot of the Ashen Brand. "
            "This is not a hideout anymore. It is an answer the gang built under the town while decent people slept overhead.",
            typed=True,
        )
        party_size = self.act1_party_size()
        enemies = [create_enemy("bandit", name="Ashen Brand Fixer"), create_enemy("bandit_archer", name="Cellar Sniper")]
        if party_size >= 3:
            enemies.append(self.act1_pick_enemy(("bandit", "gutter_zealot", "cache_mimic", "cinderflame_skull")))
        hero_bonus = self.apply_scene_companion_support("emberhall_cellars")
        choice = self.scenario_choice(
            "How do you break the final approach open?",
            [
                self.skill_tag("STEALTH", self.action_option("Slip through the drainage run and hit the antechamber from behind.")),
                self.skill_tag("ATHLETICS", self.action_option("Kick in the main cellar door and force the issue immediately.")),
                self.quoted_option("PERSUASION", "Call for surrender before the last of them decides to die for Varyn."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Slip through the drainage run and hit the antechamber from behind.")
            success = self.skill_check(self.state.player, "Stealth", 13, context="to reach the antechamber quietly")
            if success:
                enemies[1].current_hp = max(1, enemies[1].current_hp - 5)
                self.apply_status(enemies[1], "surprised", 1, source="your tunnel approach")
                hero_bonus += 2
                self.say("You come out behind stacked crates and the first lookout never finds a clean line.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="a shrieking drainage grate")
                self.say("The grate screams and the last defenders know exactly where you are.")
        elif choice == 2:
            self.player_action("Kick in the main cellar door and force the issue immediately.")
            success = self.skill_check(self.state.player, "Athletics", 13, context="to blast the cellar door off its hinges")
            if success:
                self.apply_status(self.state.player, "emboldened", 2, source="blasting into Emberhall")
                self.apply_status(enemies[0], "prone", 1, source="the crashing cellar door")
                hero_bonus += 2
                self.say("The door explodes inward and the antechamber never really gets to become a line.")
            else:
                self.apply_status(self.state.player, "prone", 1, source="a collapsing door frame")
                self.say("The door gives badly and drags you down with it.")
        else:
            self.player_speaker("Call for surrender before the last of them decides to die for Varyn.")
            success = self.skill_check(self.state.player, "Persuasion", 14, context="to shake the final defenders before steel is fully drawn")
            if success:
                fleeing = enemies.pop()
                self.say(f"{fleeing.name} bolts for the far stair instead of dying for someone else's cut.")
                hero_bonus += 1
            else:
                self.say("The room tightens instead of yielding, and the last defenders settle in behind Varyn's certainty.")

        first_encounter = Encounter(
            title="Emberhall Antechamber",
            description="The gang's last disciplined guard line forms among poison tables and stolen crates.",
            enemies=enemies,
            allow_flee=True,
            allow_parley=True,
            parley_dc=14,
            hero_initiative_bonus=hero_bonus,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter(first_encounter)
        if outcome == "defeat":
            self.handle_defeat("Emberhall's last guard line leaves the cellars to the Ashen Brand.")
            return
        if outcome == "fled":
            self.state.current_scene = "phandalin_hub"
            self.say("You retreat to the surface before the last chamber can close around you.")
            return

        self.say(
            "Beyond the antechamber, a chained clerk, a table full of ledgers, and a stack of poison vials sit outside the final hall. Varyn is close enough now that every choice feels like part of the last blow."
        )
        boss_bonus = 0
        choice = self.scenario_choice(
            "What do you do in the final lull?",
            [
                self.quoted_option("MEDICINE", "The chained clerk is fading. Get them talking before the poison finishes the job."),
                self.quoted_option("INVESTIGATION", "Give me the ledgers. I want the shape of Varyn's exits and lies."),
                self.action_option("Smash the poison table and flood the hall with glass, fumes, and noise."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("The chained clerk is fading. Get them talking before the poison finishes the job.")
            success = self.skill_check(
                self.state.player,
                "Medicine",
                13,
                context="to keep the poisoned clerk alive long enough for a final warning",
            )
            if success:
                self.say("The clerk rasps out one useful warning: Varyn keeps a reserve vial for the first enemy who lands a real hit.")
                self.add_inventory_item("antitoxin_vial", source="the chained clerk's hidden pocket")
                self.reward_party(xp=15, reason="saving the chained clerk in Emberhall")
                boss_bonus += 1
            else:
                self.say("You save what life you can, but the warning dies in fragments.")
        elif choice == 2:
            self.player_speaker("Give me the ledgers. I want the shape of Varyn's exits and lies.")
            success = self.skill_check(
                self.state.player,
                "Investigation",
                13,
                context="to decode Varyn's fallback routes before the last fight",
            )
            if success:
                self.say("You map the hall fast enough to know where Varyn intended to break line and reposition.")
                boss_bonus += 1
                self.reward_party(xp=15, reason="decoding Varyn's fallback plan")
            else:
                self.say("You get the broad shape of the chamber, but not every escape seam.")
        else:
            self.player_action("Smash the poison table and flood the hall with glass, fumes, and noise.")
            boss_bonus += 2
            self.say("Glass and reeking poison spread across the hall entrance, forcing the final fight to start amid chaos you chose.")

        boss_enemies = [create_enemy("varyn"), create_enemy("bandit", name="Ashen Brand Enforcer"), create_enemy("bandit_archer")]
        boss_enemies[0].max_hp += 8
        boss_enemies[0].current_hp += 8
        if party_size >= 4:
            boss_enemies.append(self.act1_pick_enemy(("bandit", "cinderflame_skull", "whispermaw_blob")))
        choice = self.scenario_choice(
            "Varyn Sable waits in the last chamber with ash banners at their back.",
            [
                self.quoted_option("PERSUASION", "It is over. Walk up the stairs alive, or do not walk them at all."),
                self.quoted_option("INTIMIDATION", "You are out of road, out of men, and out of time."),
                self.action_option("No more speeches. End this now."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("It is over. Walk up the stairs alive, or do not walk them at all.")
            success = self.skill_check(self.state.player, "Persuasion", 15, context="to make Varyn feel the walls finally closing in")
            if success:
                fleeing = boss_enemies.pop()
                self.say(f"{fleeing.name} breaks for the stairs before the first strike lands.")
                boss_bonus += 1
            else:
                self.speaker("Varyn Sable", "If it were over, you would not still be trying to talk me out of surviving it.")
        elif choice == 2:
            self.player_speaker("You are out of road, out of men, and out of time.")
            success = self.skill_check(self.state.player, "Intimidation", 15, context="to crack the captain's final composure")
            if success:
                boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 5)
                self.apply_status(boss_enemies[0], "reeling", 2, source="your certainty finally landing")
                self.say("For the first time, Varyn looks less amused than calculating.")
            else:
                self.apply_status(boss_enemies[0], "emboldened", 2, source="defying your threat")
                self.speaker("Varyn Sable", "That is what people say right before they become examples.")
        else:
            self.player_action("No more speeches. End this now.")
            boss_enemies[0].current_hp = max(1, boss_enemies[0].current_hp - 3)
            boss_bonus += 2
            self.say("Steel and spell-fire answer before Varyn can turn the room into a conversation again.")

        encounter = Encounter(
            title="Boss: Varyn Sable",
            description="The captain of the Ashen Brand makes the final stand beneath Iron Hollow.",
            enemies=boss_enemies,
            allow_flee=True,
            allow_parley=True,
            parley_dc=15,
            hero_initiative_bonus=boss_bonus,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter(encounter)
        if outcome == "defeat":
            self.handle_defeat("The cellar banners remain standing above a fallen company.")
            return
        if outcome == "fled":
            self.state.current_scene = "phandalin_hub"
            self.say("You escape the cellars and return to the surface to recover.")
            return

        self.say(
            "Varyn falls, but not cleanly. Body, cloak, and blade hit the cellar stones while the route behind him folds the wrong way. "
            "The remaining brigands scatter, the Ashen Brand breaks around that absence, and the pressure that has bent every road into Iron Hollow finally snaps. "
            "Among the captain's ledgers are references to older powers stirring beneath the Shatterbelt highlands, with whispers pointing toward deeper ruins, buried wealth, and unfinished business near Resonant Vaults."
        )
        self.state.flags["varyn_body_defeated_act1"] = True
        self.state.flags["varyn_route_displaced"] = True
        self.state.flags["act1_ashen_brand_broken"] = True
        if self.state.flags.get("emberhall_ledger_read") or self.state.flags.get("emberhall_archive_tip"):
            self.state.flags["emberhall_impossible_exit_seen"] = True
            self.say("The exits you decoded before the fight all account for themselves except one: a route that appears in the ledger only after Varyn is gone.")
        self.add_journal("You broke the Ashen Brand and secured Iron Hollow through the end of Act 1.")
        self.reward_party(xp=250, gold=80, reason="securing Iron Hollow at the end of Act I")
        if 1 not in self.state.completed_acts:
            self.state.completed_acts.append(1)
        self.state.current_scene = "act1_complete"
        self.save_game(slot_name=f"{self.state.player.name}_act1_complete")
