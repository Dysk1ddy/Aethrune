from __future__ import annotations

from ..content import create_bryn_underbough, create_tolan_ironshield
from ..data.story.public_terms import marks_label
from .constants import LEVEL_XP_THRESHOLDS


class StoryTownHubMixin:
    def describe_blackwake_phandalin_arrival(self) -> None:
        assert self.state is not None
        if self.state.flags.get("phandalin_blackwake_arrival_seen"):
            return
        self.state.flags["phandalin_blackwake_arrival_seen"] = True
        resolution = self.state.flags.get("blackwake_resolution")
        if resolution == "rescue":
            self.say(
                "Blackwake's rescued teamsters have already become road-talk by the time you reach Iron Hollow. "
                "A few townsfolk look at you less like hired steel and more like someone who might actually bring people home."
            )
        elif resolution == "evidence":
            self.say(
                "The copied seals and ledgers from Blackwake make Iron Hollow's route permits look less like paperwork and more like a battlefield. "
                "Merchants notice the proof before they trust the promise behind it."
            )
        elif resolution == "sabotage":
            self.say(
                "Rumor reaches Iron Hollow ahead of you: a riverside cache burned, and the Ashen Brand's northbound supply rhythm stumbled. "
                "The town does not know whether to call it rescue, warning, or war."
            )
        else:
            self.say(
                "The Blackwake crossing follows you into town as a rumor of smoke, false seals, and caravans disappearing before Iron Hollow ever saw them."
            )
        if self.state.flags.get("blackwake_sereth_fate") == "escaped":
            self.say("One road hand lowers their voice over Sereth Vane's name, as if saying it too clearly might invite him south.")

    def scene_phandalin_hub(self) -> None:
        assert self.state is not None
        self.banner("Iron Hollow")
        if not self.state.flags.get("phandalin_arrived"):
            self.say(
                "Iron Hollow rises from rocky foothills in a scatter of simple homes, muddy lanes, and broken "
                "stonework left behind by an older, larger town. There are no real walls, no proper garrison, "
                "and too many people keeping weapons close at hand.",
                typed=True,
            )
            self.state.flags["phandalin_arrived"] = True
            self.add_journal("You reached Iron Hollow, a resettled frontier town under pressure from the Ashen Brand.")
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
                    self.say("You catch the way fear keeps pulling the crowd's attention toward the old ruins whenever the gang is mentioned.")
                    self.add_clue("The crowd keeps glancing toward the old manor ruins whenever the Ashen Brand is named.")
                    self.reward_party(xp=10, reason="reading Iron Hollow's mood on arrival")
                else:
                    self.say("The town's fear is real, but too tangled and contradictory for one quick read to untangle.")
                self.run_dialogue_input("phandalin_arrival_insight")
            elif choice == 2:
                self.player_speaker("Let them know Greywake sent help.")
                success = self.skill_check(self.state.player, "Persuasion", 12, context="to steady the town's nerves")
                if success:
                    self.say("A few shoulders ease as your words cut through the panic and sound like a promise worth believing.")
                    self.reward_party(xp=10, gold=6, reason="reassuring Iron Hollow on arrival")
                    self.say("A grateful merchant presses a few coins into your hand for road expenses.")
                else:
                    self.say("Your words land, but suspicion clings harder than hope in a town this strained.")
                self.run_dialogue_input("phandalin_arrival_persuasion")
            else:
                self.player_action("Show me the tracks, barricades, and weak points first.")
                success = self.skill_check(self.state.player, "Investigation", 12, context="to assess the town's defenses")
                if success:
                    self.say("Fresh ruts, hurried repairs, and trampled lanes start to line up into a pattern you can actually use.")
                    self.add_clue("Fresh wagon ruts and bootprints suggest the gang watches the manor-side lanes closely.")
                    self.reward_party(xp=10, reason="surveying Iron Hollow's defenses")
                else:
                    self.say("Too many wagon ruts and bootprints overlap for a clean read before the trail goes cold.")
                self.run_dialogue_input("phandalin_arrival_investigation")
        elif self.state.flags.get("ashfall_watch_cleared") and not self.state.flags.get("phandalin_after_watch_seen"):
            self.say(
                "When you return from Ashfall Watch, Iron Hollow feels changed in all the small ways that matter. "
                "Doors open faster, wagon talk replaces funeral whispers, and more than one townsman studies the road "
                "east like it might finally belong to honest travelers again.",
                typed=True,
            )
            if self.state.player.level < 2:
                xp_to_level_two = max(0, LEVEL_XP_THRESHOLDS[2] - self.state.xp)
                if xp_to_level_two > 0:
                    self.reward_party(xp=xp_to_level_two, reason="regrouping after Ashfall Watch")
            self.state.flags["phandalin_after_watch_seen"] = True

        while True:
            if self.state.flags.get("ashfall_watch_cleared"):
                ready_text = self.action_option("Descend into Emberhall Cellars")
            else:
                ready_text = self.action_option("Ride for Ashfall Watch") if len(self.state.clues) >= 2 else self.action_option("Ride for Ashfall Watch (need 2 clues)")
            options: list[tuple[str, str]] = []
            if self.has_steward_interactions():
                options.append(("steward", self.action_option("Report to Steward Tessa Harrow")))
            options.append(("inn", self.action_option("Visit the Ashlamp Inn")))
            if self.has_shrine_interactions():
                options.append(("shrine", self.action_option("Stop by the Lantern Shrine")))
            options.extend(
                [
                    ("barthen", self.skill_tag("TRADE", self.action_option("Browse Hadrik's Provisions"))),
                    ("linene", self.skill_tag("TRADE", self.action_option("Call on Linene Ironward at the Ironbound trading post"))),
                    ("camp", self.action_option("Return to camp")),
                    ("rest", self.action_option("Take a short rest")),
                    ("ashfall", ready_text),
                ]
            )
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
            elif selection_key == "camp":
                self.open_camp_menu()
            elif selection_key == "rest":
                self.short_rest()
            else:
                if not self.state.flags.get("ashfall_watch_cleared") and len(self.state.clues) < 2:
                    self.say("You still need firmer leads before marching on the watchtower.")
                elif self.state.flags.get("ashfall_watch_cleared"):
                    self.state.current_scene = "emberhall_cellars"
                    return
                else:
                    self.state.current_scene = "ashfall_watch"
                    return

    def has_steward_interactions(self) -> bool:
        assert self.state is not None
        return bool(
            not self.state.flags.get("steward_seen")
            or self.quest_is_ready("secure_miners_road")
            or not self.state.flags.get("steward_pressure_asked")
            or not self.state.flags.get("steward_ruins_asked")
            or (self.state.flags.get("blackwake_completed") and not self.state.flags.get("steward_blackwake_asked"))
            or (not self.state.flags.get("steward_vow_made") and self.quest_status("secure_miners_road") == "active")
        )

    def visit_steward(self) -> None:
        assert self.state is not None
        self.banner("Steward's Hall")
        self.introduce_character("Tessa Harrow")
        if not self.state.flags.get("steward_seen"):
            self.say(
                "Tessa stands over a desk buried in route maps, supply notes, and half-dried ink. "
                "She looks like someone trying to hold a frontier town together with ledgers, stubbornness, and not "
                "nearly enough sleep.",
                typed=True,
            )
            self.state.flags["steward_seen"] = True
        while True:
            options: list[tuple[str, str]] = []
            if self.quest_is_ready("secure_miners_road"):
                options.append(("turn_in", self.action_option("Tell Tessa what happened at Ashfall Watch.")))
            if not self.state.flags.get("steward_pressure_asked"):
                options.append(("pressure", "\"Where is the Ashen Brand hurting you the most?\""))
            if not self.state.flags.get("steward_ruins_asked"):
                options.append(("ruins", "\"Tell me about the old ruins around town.\""))
            if self.state.flags.get("blackwake_completed") and not self.state.flags.get("steward_blackwake_asked"):
                options.append(("blackwake", self.action_option("Share what happened at Blackwake Crossing.")))
            if not self.state.flags.get("steward_vow_made") and self.quest_status("secure_miners_road") == "active":
                options.append(("vow", "\"I'll break their grip on Iron Hollow.\""))
            options.append(("leave", self.action_option("Leave Tessa to her work and move on.")))
            choice = self.scenario_choice("Choose what you say to Tessa.", [text for _, text in options])
            selection_key, _ = options[choice - 1]
            if selection_key == "turn_in":
                self.player_action("Ashfall Watch is broken. Your road can breathe again.")
                self.speaker(
                    "Tessa Harrow",
                    "Then the town gets one honest stretch of hope before the next problem starts knocking. That's more than we've had in months.",
                )
                self.turn_in_quest("secure_miners_road", giver="Steward Tessa Harrow")
            elif selection_key == "pressure":
                self.state.flags["steward_pressure_asked"] = True
                self.player_speaker("Where is the Ashen Brand hurting you the most?")
                self.speaker(
                    "Tessa Harrow",
                    "Miners and supply runners take the worst of it. Every crew that stays home means less ore, less pay, and one more family buying food like it's a luxury. "
                    "Survivors keep naming a ruined watchtower east of town and cellar routes beneath older stonework, and every retelling sounds less like rumor and more like logistics.",
                )
                self.add_clue("Steward Harrow ties the gang to Ashfall Watch and cellar routes under old ruins.")
                if self.grant_quest(
                    "secure_miners_road",
                    note="Tessa says the watchtower is throttling miners, couriers, and every road-dependent family in town.",
                ):
                    self.speaker(
                        "Tessa Harrow",
                        "Break that watchtower and you won't just win a fight. You'll give this town room to breathe.",
                    )
            elif selection_key == "ruins":
                self.state.flags["steward_ruins_asked"] = True
                self.player_speaker("Tell me about the old ruins around town.")
                self.speaker(
                    "Tessa Harrow",
                    "The old foundations are blessing and curse alike. We build against them because the stone is already here, but every buried wall and forgotten cellar gives brigands another place to vanish before decent folk even know to look.",
                )
            elif selection_key == "blackwake":
                self.state.flags["steward_blackwake_asked"] = True
                self.player_action("Share what happened at Blackwake Crossing.")
                resolution = self.state.flags.get("blackwake_resolution")
                if resolution == "evidence":
                    self.speaker(
                        "Tessa Harrow",
                        "False seals this close to Greywake changes every petition on my desk. Give me names and route marks, and I can make officials answer a harder question than 'why are you afraid?'",
                    )
                    self.add_clue("Tessa can use the Blackwake ledgers to argue that the Ashen Brand is corrupting route authority, not merely raiding wagons.")
                    self.reward_party(gold=8, reason="sharing Blackwake proof with Iron Hollow's steward")
                elif resolution == "rescue":
                    self.speaker(
                        "Tessa Harrow",
                        "Then some of those families may reach us alive. That matters here. Proof can travel later; people need the road under their feet first.",
                    )
                    self.add_journal("Tessa Harrow promised to watch for survivors and teamsters pulled out of Blackwake Crossing.")
                elif resolution == "sabotage":
                    self.speaker(
                        "Tessa Harrow",
                        "A burned cache buys us time even if it leaves me with fewer papers to wave in a magistrate's face. I'll take time. Time lets a town move grain, tools, and children.",
                    )
                    self.add_clue("Blackwake's destroyed cache may weaken Ashen Brand supply pressure south of Greywake.")
                else:
                    self.speaker(
                        "Tessa Harrow",
                        "That is too organized to dismiss as roadside theft. Blackwake tells me the rot starts before wagons ever reach our hills.",
                    )
                if self.state.flags.get("blackwake_sereth_fate") == "escaped":
                    self.speaker("Tessa Harrow", "And if Sereth Vane is still breathing, I want that name in every watchman's ear by sundown.")
                self.run_dialogue_input("steward_blackwake")
            elif selection_key == "vow":
                self.state.flags["steward_vow_made"] = True
                self.player_speaker("I'll break their grip on Iron Hollow.")
                self.speaker(
                    "Tessa Harrow",
                    "Then give me a result I can build a safer week on, and Iron Hollow will remember your name for the right reason.",
                )
                self.run_dialogue_input("steward_vow")
            else:
                self.player_action("You leave Tessa to her work and move on.")
                return

    def visit_stonehill_inn(self) -> None:
        assert self.state is not None
        play_music_for_context = getattr(self, "play_music_for_context", None)
        refresh_scene_music = getattr(self, "refresh_scene_music", None)
        if callable(play_music_for_context):
            play_music_for_context("inn", restart=True)
        try:
            self.banner("Ashlamp Inn")
            if not self.state.flags.get("inn_seen"):
                self.say(
                    "The inn smells of stew, wet wool, and the kind of caution that settles into a room after too many bad nights. "
                    "Bryn Underbough still watches the door over the rim of her mug, but tonight she is not the only fixed point in the room. "
                    "A hard-eyed innkeeper is reading the crowd like weather, a singer is coaxing truth out of bad ale, and one courier at the wall "
                    "table keeps a hand near a split lip like she does not trust anyone else to own the story of it.",
                    typed=True,
                )
                self.state.flags["inn_seen"] = True
            while True:
                self.refresh_quest_statuses(announce=False)
                options: list[tuple[str, str]] = []
                if not self.state.flags.get("inn_buy_drink_asked"):
                    options.append(("drink", "\"Mind if I buy you a drink and ask a few questions?\""))
                if not self.state.flags.get("inn_road_rumors_asked"):
                    options.append(("rumors", "\"Tell me what the roads are saying about the Ashen Brand.\""))
                if self.state.flags.get("blackwake_completed") and not self.state.flags.get("inn_blackwake_rumor_asked"):
                    options.append(("blackwake", "\"What are people saying about Blackwake Crossing?\""))
                if self.stonehill_has_mara_interactions():
                    if self.quest_is_ready("marked_keg_investigation"):
                        options.append(("mara", self.action_option("Tell Mara Ashlamp what you found about the marked keg.")))
                    else:
                        options.append(("mara", self.action_option("Talk to Mara Ashlamp, who is keeping half the room from a fight.")))
                if self.stonehill_has_jerek_interactions():
                    options.append(("jerek", self.action_option("Sit with Jerek Harl and hear what anger has left him.")))
                if self.quest_is_ready("songs_for_the_missing") and self.stonehill_has_sella_interactions():
                    options.append(("sella", self.action_option("Bring Sella Quill the three true details she asked for.")))
                elif self.stonehill_has_sella_interactions():
                    options.append(("sella", self.action_option("Listen to Sella Quill and the room she keeps half-honest.")))
                if self.stonehill_has_old_tam_interactions():
                    options.append(("tam", self.action_option("Hear Old Tam Veller out over his cooling cup.")))
                if self.quest_is_ready("quiet_table_sharp_knives") and self.stonehill_has_nera_interactions():
                    options.append(("nera", self.action_option("Report the quiet-table scheme to Nera Doss.")))
                elif self.stonehill_has_nera_interactions() and not self.state.flags.get("stonehill_nera_treated"):
                    options.append(("nera", self.quoted_option("MEDICINE", "Let me look at that split lip.")))
                elif self.stonehill_has_nera_interactions():
                    options.append(("nera", self.action_option("Check on Nera Doss at the wall table.")))
                if self.state.flags.get("stonehill_barfight_ready") and not self.state.flags.get("stonehill_barfight_resolved"):
                    options.append(("barfight", self.action_option("Step into the rising dispute before the whole room tips over.")))
                if self.state.flags.get("quest_reward_stonehill_quiet_room_access") and not self.state.flags.get("stonehill_quiet_room_scene_done"):
                    options.append(("quiet_room", self.action_option("Take Nera up on the offer of the upstairs quiet room.")))
                if not self.state.flags.get("inn_recruit_bryn_attempted") and not self.has_companion("Bryn Underbough"):
                    options.append(("recruit_bryn", self.quoted_option("PERSUASION", "Take a share of the contract and ride with me.")))
                elif (
                    not self.state.flags.get("inn_recruit_bryn_second_attempted")
                    and not self.has_companion("Bryn Underbough")
                ):
                    options.append(
                        (
                            "recruit_bryn_second",
                            self.quoted_option("INSIGHT", "You don't need luck. You need someone who listens. Tell me what you're waiting to hear."),
                        )
                    )
                if self.state.flags.get("tolan_waiting_at_inn") and not self.has_companion("Tolan Ironshield"):
                    options.append(("recruit_tolan", self.action_option("Wave Tolan over and ask him to gear up.")))
                options.append(("paid_rest", self.action_option("Rent beds for a long rest (10 marks per active party member).")))
                options.append(("leave", self.action_option("Leave the common room for now.")))
                choice = self.scenario_choice("The common room quiets for a moment as you enter.", [text for _, text in options])
                selection_key, _ = options[choice - 1]
                if selection_key == "drink":
                    self.state.flags["inn_buy_drink_asked"] = True
                    self.player_speaker("Mind if I buy you a drink and ask a few questions?")
                    self.speaker(
                        "Bryn Underbough",
                        "Depends. If your questions are useful, so are my answers. Bryn Underbough. I know the trail, I know who's lying, and I know the difference between a worried town and one that's about to make desperate mistakes.",
                    )
                elif selection_key == "rumors":
                    self.state.flags["inn_road_rumors_asked"] = True
                    self.player_speaker("Tell me what the roads are saying about the Ashen Brand.")
                    self.speaker(
                        "Bryn Underbough",
                        "That they rotate scouts between Iron Hollow and a hillfort called Ashfall Watch, and that the scouts always seem to know which wagons are worth hurting first. "
                        "If the gang has a spine, that's where it'll be. Break that, and the rest starts looking mortal.",
                    )
                    self.add_clue("Bryn confirms Ashfall Watch is the gang's field base.")
                elif selection_key == "blackwake":
                    self.state.flags["inn_blackwake_rumor_asked"] = True
                    self.player_speaker("What are people saying about Blackwake Crossing?")
                    resolution = self.state.flags.get("blackwake_resolution")
                    if resolution == "rescue":
                        self.speaker(
                            "Ashlamp Teamster",
                            "That some folk walked out of smoke who had no right surviving it. People remember that kind of help, even when they pretend they only care about freight.",
                        )
                    elif resolution == "evidence":
                        self.speaker(
                            "Ashlamp Teamster",
                            "That the stolen seals were real enough to fool honest clerks. If you've got proof, keep it dry and close. Paper scares cowards when steel can't reach them yet.",
                        )
                    elif resolution == "sabotage":
                        self.speaker(
                            "Ashlamp Teamster",
                            "That someone taught the Brand what a supply loss feels like. Makes the room nervous, that does, but not all nervous is bad.",
                        )
                    else:
                        self.speaker(
                            "Ashlamp Teamster",
                            "That Blackwake was never just a burned crossing. It was a door, and somebody mean was deciding who got through.",
                        )
                    if self.state.flags.get("blackwake_sereth_fate") == "escaped":
                        self.speaker("Ashlamp Teamster", "Also heard a name: Sereth Vane. Folk say he leaves clean desks and dirty roads behind him.")
                elif selection_key == "mara":
                    self.stonehill_talk_mara()
                elif selection_key == "jerek":
                    self.stonehill_talk_jerek()
                elif selection_key == "sella":
                    self.stonehill_talk_sella()
                elif selection_key == "tam":
                    self.stonehill_talk_old_tam()
                elif selection_key == "nera":
                    self.stonehill_talk_nera()
                elif selection_key == "barfight":
                    self.stonehill_resolve_barfight()
                elif selection_key == "quiet_room":
                    self.stonehill_use_quiet_room()
                elif selection_key == "recruit_bryn":
                    self.state.flags["inn_recruit_bryn_attempted"] = True
                    self.player_speaker("Take a share of the contract and ride with me.")
                    self.run_dialogue_input("stonehill_recruit_bryn")
                    success = self.skill_check(self.state.player, "Persuasion", 12, context="to convince Bryn the risk is worth it")
                    if success:
                        self.recruit_companion(create_bryn_underbough())
                        self.speaker(
                            "Bryn Underbough",
                            "Fair split, honest cause, and a chance to make bandits miserable before they make anyone else bury family? I'm in.",
                        )
                    else:
                        self.speaker("Bryn Underbough", "Not yet. You sound useful, but useful and lucky are not always the same thing.")
                elif selection_key == "recruit_bryn_second":
                    self.state.flags["inn_recruit_bryn_second_attempted"] = True
                    self.player_speaker("You don't need luck. You need someone who listens. Tell me what you're waiting to hear.")
                    self.run_dialogue_input("stonehill_recruit_bryn_second")
                    success = self.skill_check(self.state.player, "Insight", 12, context="to read Bryn's hesitation and answer it plainly")
                    if success:
                        self.recruit_companion(create_bryn_underbough())
                        self.speaker(
                            "Bryn Underbough",
                            "There it is. Most people hear a scout and think boots and arrows. You heard judgment. Fine. I'll lend you mine.",
                        )
                    else:
                        self.speaker(
                            "Bryn Underbough",
                            "Closer. But if I ride with you, I need to know you'll read a room before it turns into a graveyard. Ask me again after you've proven that.",
                        )
                elif selection_key == "recruit_tolan":
                    self.player_action("You wave Tolan over and ask him to gear up again.")
                    self.state.flags.pop("tolan_waiting_at_inn", None)
                    self.recruit_companion(create_tolan_ironshield())
                    self.speaker("Tolan Ironshield", "About time. I was getting tired of waiting on soup.")
                elif selection_key == "paid_rest":
                    self.player_action("Rent beds at the Ashlamp Inn for the company.")
                    self.paid_inn_long_rest("Ashlamp Inn")
                else:
                    self.player_action("You leave the common room for now.")
                    return
        finally:
            if callable(refresh_scene_music):
                refresh_scene_music()

    def stonehill_has_liars_blessing(self) -> bool:
        assert self.state is not None
        return self.has_story_skill_modifier(self.state.player, self.LIARS_BLESSING_MODIFIER_ID)

    def stonehill_adjust_town_fear(self, delta: int) -> None:
        adjust_metric = getattr(self, "act1_adjust_metric", None)
        if callable(adjust_metric):
            adjust_metric("act1_town_fear", delta)

    def stonehill_has_mara_interactions(self) -> bool:
        assert self.state is not None
        return bool(
            not self.state.flags.get("stonehill_mara_met")
            or self.quest_is_ready("marked_keg_investigation")
            or (not self.has_quest("marked_keg_investigation") and not self.quest_is_completed("marked_keg_investigation"))
            or (
                self.has_quest("marked_keg_investigation")
                and not self.quest_is_completed("marked_keg_investigation")
                and not self.state.flags.get("marked_keg_resolved")
            )
            or not self.state.flags.get("stonehill_mara_order_asked")
        )

    def stonehill_has_jerek_interactions(self) -> bool:
        assert self.state is not None
        return bool(
            not self.state.flags.get("stonehill_jerek_met")
            or self.quest_is_ready("find_dain_harl")
            or (not self.has_quest("find_dain_harl") and not self.quest_is_completed("find_dain_harl"))
            or (
                not self.state.flags.get("stonehill_jerek_route_marks_shared")
                and not self.state.flags.get("dain_harl_truth_found")
            )
            or not self.state.flags.get("stonehill_jerek_grievance_asked")
            or not self.state.flags.get("songs_for_missing_jerek_detail")
        )

    def stonehill_has_sella_interactions(self) -> bool:
        assert self.state is not None
        return bool(
            not self.state.flags.get("stonehill_sella_met")
            or self.quest_is_ready("songs_for_the_missing")
            or (not self.has_quest("songs_for_the_missing") and not self.quest_is_completed("songs_for_the_missing"))
            or (self.has_quest("songs_for_the_missing") and not self.quest_is_completed("songs_for_the_missing"))
            or not self.state.flags.get("stonehill_sella_room_asked")
            or not self.state.flags.get("stonehill_sella_performance_attempted")
            or (
                self.quest_is_completed("songs_for_the_missing")
                and self.quest_is_completed("find_dain_harl")
                and not self.state.flags.get("stonehill_sella_dain_memorial_done")
            )
        )

    def stonehill_has_old_tam_interactions(self) -> bool:
        assert self.state is not None
        return bool(
            not self.state.flags.get("stonehill_old_tam_met")
            or not self.state.flags.get("stonehill_old_tam_route_asked")
            or not self.state.flags.get("songs_for_missing_tam_detail")
        )

    def stonehill_has_nera_interactions(self) -> bool:
        assert self.state is not None
        return bool(
            not self.state.flags.get("stonehill_nera_met")
            or self.quest_is_ready("quiet_table_sharp_knives")
            or not self.state.flags.get("stonehill_nera_treated")
            or (not self.has_quest("quiet_table_sharp_knives") and not self.quest_is_completed("quiet_table_sharp_knives"))
            or (
                self.has_quest("quiet_table_sharp_knives")
                and not self.quest_is_completed("quiet_table_sharp_knives")
                and not self.state.flags.get("quiet_table_knives_resolved")
            )
        )

    def stonehill_talk_mara(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("stonehill_mara_met"):
            self.state.flags["stonehill_mara_met"] = True
            self.speaker(
                "Mara Ashlamp",
                "If you're here to save the town, good. If you're here to practice on it, finish your drink outside. I can carry trays or trouble on a bad night, but not both.",
            )
        while True:
            self.refresh_quest_statuses(announce=False)
            options: list[tuple[str, str]] = []
            if self.quest_is_ready("marked_keg_investigation"):
                options.append(("turn_in", self.action_option("Tell Mara who marked the keg and why.")))
            elif not self.has_quest("marked_keg_investigation") and not self.quest_is_completed("marked_keg_investigation"):
                options.append(("quest", "\"What has you watching the kegs instead of the door?\""))
            elif not self.state.flags.get("marked_keg_resolved"):
                options.append(("investigate", self.action_option("Read the room around Mara's marked keg.")))
            if not self.state.flags.get("stonehill_mara_order_asked"):
                options.append(("order", "\"How are you keeping this room from breaking?\""))
            options.append(("leave", self.action_option("Leave Mara to the floor and step back into the room.")))
            choice = self.scenario_choice("Choose what you say to Mara Ashlamp.", [text for _, text in options])
            selection_key, _ = options[choice - 1]
            if selection_key == "turn_in":
                self.player_action("Tell Mara who marked the keg and why.")
                self.turn_in_quest("marked_keg_investigation", giver="Mara Ashlamp")
            elif selection_key == "quest":
                self.player_speaker("What has you watching the kegs instead of the door?")
                self.speaker(
                    "Mara Ashlamp",
                    "Because one cask near the back wall is wearing fresh chalk no cellar hand will claim. Somebody wants this room louder, meaner, and easier to steer. Name that hand for me before the whole place starts pretending the first flying chair was inevitable.",
                )
                self.grant_quest(
                    "marked_keg_investigation",
                    note="Mara spotted a chalk-marked keg and wants the hand behind it named before the room turns fear into entertainment.",
                )
            elif selection_key == "investigate":
                self.stonehill_investigate_marked_keg()
            elif selection_key == "order":
                self.state.flags["stonehill_mara_order_asked"] = True
                self.player_speaker("How are you keeping this room from breaking?")
                self.speaker(
                    "Mara Ashlamp",
                    "By learning who came in grieving, who came in lying, and who came in hoping grief would do the lying for them. On nights like this the difference keeps more people alive than the stew.",
                )
            else:
                self.player_action("You leave Mara to the floor and step back into the common room.")
                return

    def stonehill_investigate_marked_keg(self) -> None:
        assert self.state is not None
        options: list[tuple[str, str]] = [
            (
                "investigation",
                self.skill_tag("INVESTIGATION", self.action_option("Examine the keg chalk, cellar dust, and tap line.")),
            ),
            (
                "insight",
                self.skill_tag("INSIGHT", self.action_option("Watch who cares too much whether the marked keg gets opened.")),
            ),
        ]
        if self.stonehill_has_liars_blessing():
            options.append(
                (
                    "blessing",
                    self.skill_tag(
                        "LIAR'S BLESSING",
                        self.action_option("Smile like you already know who marked the cask and let the guilty hand correct you."),
                    ),
                )
            )
        options.append(("leave", self.action_option("Leave the keg alone for the moment.")))
        choice = self.scenario_choice("How do you handle Mara's marked keg?", [text for _, text in options], allow_meta=False)
        selection_key, _ = options[choice - 1]
        if selection_key == "leave":
            self.player_action("Leave the keg alone for the moment.")
            return
        if selection_key == "investigation":
            self.player_action("Examine the keg chalk, cellar dust, and tap line.")
            success = self.skill_check(self.state.player, "Investigation", 12, context="to read the marked keg and the hands around it")
        elif selection_key == "insight":
            self.player_action("Watch who cares too much whether the marked keg gets opened.")
            success = self.skill_check(self.state.player, "Insight", 12, context="to catch the room's wrong kind of interest")
        else:
            self.player_action("Smile like you already know who marked the cask and let the guilty hand correct you.")
            success = True
        if success:
            self.state.flags["marked_keg_resolved"] = True
            self.state.flags["stonehill_barfight_ready"] = False
            self.state.flags["stonehill_marked_keg_named"] = True
            self.say(
                "The answer comes cleanly once you stop looking at the keg and start looking at the hands. "
                "One supposed drover still has brewery chalk in the seam of his thumb, and when Mara says his drink is on the house he flinches like a man who was paid to make a room worse, not stay in it."
            )
            self.add_clue("A chalk-marked keg at the Ashlamp was meant to turn common-room fear into a useful riot.")
            self.add_journal("You exposed the hand behind the Ashlamp's marked keg before the whole room could be steered by it.")
        else:
            self.state.flags["stonehill_barfight_ready"] = True
            self.say(
                "You take one heartbeat too long. A shouted accusation jumps tables, a bench scrapes hard enough to promise splinters, "
                "and whatever was meant to stay a nudge has started leaning toward a fight."
            )

    def stonehill_talk_jerek(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("stonehill_jerek_met"):
            self.state.flags["stonehill_jerek_met"] = True
            self.speaker(
                "Jerek Harl",
                "People keep saying raids like that softens anything. My brother had a name before he became another warning told over ale.",
            )
        while True:
            self.refresh_quest_statuses(announce=False)
            options: list[tuple[str, str]] = []
            if self.quest_is_ready("find_dain_harl"):
                options.append(("turn_in", self.action_option("Tell Jerek what you found of Dain Harl.")))
            elif not self.has_quest("find_dain_harl") and not self.quest_is_completed("find_dain_harl"):
                options.append(("quest", "\"If I go to Ashfall, what truth do you want carried back?\""))
            elif not self.state.flags.get("stonehill_jerek_route_marks_shared") and not self.state.flags.get("dain_harl_truth_found"):
                options.append(("marks", "\"Tell me what would let me know I found Dain, not just another dead road hand.\""))
            if not self.state.flags.get("stonehill_jerek_grievance_asked"):
                options.append(("grievance", "\"Who are you angry at, really?\""))
            if not self.state.flags.get("songs_for_missing_jerek_detail"):
                options.append(
                    (
                        "detail",
                        self.quoted_option("PERSUASION", "Tell me the missing man's name so the room stops calling him 'another crew'."),
                    )
                )
            options.append(("leave", self.action_option("Leave Jerek to his drink and his thoughts.")))
            choice = self.scenario_choice("Choose what you say to Jerek Harl.", [text for _, text in options])
            selection_key, _ = options[choice - 1]
            if selection_key == "turn_in":
                self.player_action("Tell Jerek what you found of Dain Harl.")
                if self.turn_in_quest("find_dain_harl", giver="Jerek Harl") and not self.state.flags.get("stonehill_jerek_closure_shared"):
                    self.state.flags["stonehill_jerek_closure_shared"] = True
                    self.speaker(
                        "Jerek Harl",
                        "He deserved better than that yard. But he died himself, not as their warning. That matters. Keep the knot. I would rather one road in this town remember him by helping the next traveler home.",
                    )
                    self.stonehill_adjust_town_fear(-1)
            elif selection_key == "quest":
                self.player_speaker("If I go to Ashfall, what truth do you want carried back?")
                self.speaker(
                    "Jerek Harl",
                    "Truth. If he's alive, bring him. If he's dead, bring me something firmer than rumor. Dain wore a blue scarf knotted through his wrist ring when he hauled. Said it kept the road from stealing it. That scarf's the only thing about him nobody else in this room could fake cleanly.",
                )
                self.grant_quest(
                    "find_dain_harl",
                    note="Jerek wants truth about Dain Harl, last seen on the east road before Ashfall Watch started swallowing whole crews.",
                )
                if self.state.flags.get("ashfall_blue_scarf_truth_found") and not self.state.flags.get("dain_harl_truth_found"):
                    self.player_speaker("Blue scarf on the wrist ring. I saw one at Ashfall.")
                    self.state.flags["dain_harl_truth_found"] = True
                    self.add_clue("The blue-scarfed road worker who died freeing prisoners at Ashfall was Dain Harl.")
                    self.add_journal("Jerek's description of Dain matches the blue-scarfed road worker you found at Ashfall Watch.")
                    self.refresh_quest_statuses(announce=False)
                    self.speaker(
                        "Jerek Harl",
                        "Then the road at least gave me this much: a shape to grieve instead of a hole. Come back when you've said it all the way through.",
                    )
            elif selection_key == "marks":
                self.state.flags["stonehill_jerek_route_marks_shared"] = True
                self.player_speaker("Tell me what would let me know I found Dain, not just another dead road hand.")
                self.speaker(
                    "Jerek Harl",
                    "Blue scarf through the wrist ring. Left-handed knot, always ugly. And if a lock needed forcing, he'd leave scrape marks low because he never trusted top hinges. Dain fixed roads like he expected strangers to be the ones needing them next.",
                )
                self.add_clue("Dain Harl wore a blue scarf through his wrist ring and left low scrape marks when he forced a lock.")
            elif selection_key == "grievance":
                self.state.flags["stonehill_jerek_grievance_asked"] = True
                self.player_speaker("Who are you angry at, really?")
                self.speaker(
                    "Jerek Harl",
                    "At the Brand. At the roads. At every man in this room who says wait for proof like proof cooks supper. But mostly at the part of me that still listens for Dain's boots outside before I remember what kind of year this is.",
                )
                self.add_clue("Jerek Harl says east-road crews started vanishing before Ashfall Watch felt like a rumor anyone could afford to ignore.")
            elif selection_key == "detail":
                self.player_speaker("Tell me the missing man's name so the room stops calling him 'another crew'.")
                success = self.skill_check(self.state.player, "Persuasion", 12, context="to get Jerek to speak plainly about the missing")
                if success:
                    self.state.flags["songs_for_missing_jerek_detail"] = True
                    self.speaker(
                        "Jerek Harl",
                        "Dain Harl. Blue scarf even in warm weather because our mother said his throat would be the death of him before any blade was. If your singer wants truth, there it is. Dain laughed too loud and still showed up for first light.",
                    )
                    self.add_journal("Jerek Harl finally named the missing man his grief has been circling: Dain Harl, blue scarf, first-light worker.")
                else:
                    self.speaker("Jerek Harl", "Not from a stranger. Ask me that after you've earned one honest silence in this room.")
            else:
                self.player_action("You leave Jerek to his drink and his thoughts.")
                return

    def stonehill_use_quiet_room(self) -> None:
        assert self.state is not None
        if self.state.flags.get("stonehill_quiet_room_scene_done"):
            self.say("The upstairs quiet room has already yielded the best truth it was going to.")
            return
        self.player_action("Take Nera up on the offer of the upstairs quiet room.")
        self.say(
            "Nera leads you upstairs to a narrow back room with shuttered windows, a washbasin, and one table already laid out with the quiet-table take: "
            "a folded payment note, a courier strip, and a blackened seal pressed hard enough to dent the wood beneath it."
        )
        self.speaker(
            "Nera Doss",
            "This is what your reward really buys: one room where nobody gets to edit the message while it is still wet.",
        )
        self.speaker(
            "Sella Quill",
            "Also one room where fear is not allowed to improvise. Read fast. By morning the downstairs version will already be worse.",
        )
        options: list[tuple[str, str]] = [
            (
                "investigation",
                self.skill_tag("INVESTIGATION", self.action_option("Lay the payment note beside the courier strip and find the real route hidden between them.")),
            ),
            (
                "insight",
                self.skill_tag("INSIGHT", self.action_option("Pick the lie out of the handoff and follow the correction instead.")),
            ),
            (
                "nera",
                self.action_option("Have Nera walk you through the courier habits and take the cleanest lead she can name."),
            ),
        ]
        if self.stonehill_has_liars_blessing():
            options.append(
                (
                    "blessing",
                    self.skill_tag(
                        "LIAR'S BLESSING",
                        self.action_option("Speak the false countersign aloud and wait for the packet to correct you."),
                    ),
                )
            )
        choice = self.scenario_choice("How do you work the quiet-room packet?", [text for _, text in options], allow_meta=False)
        selection_key, _ = options[choice - 1]
        reward_xp = 10
        if selection_key == "investigation":
            self.player_action("Lay the payment note beside the courier strip and find the real route hidden between them.")
            if self.skill_check(self.state.player, "Investigation", 12, context="to decode the stolen courier packet cleanly"):
                reward_xp = 15
                self.say("The marks line up fast once you stop reading them like words and start reading them like habits.")
            else:
                self.say("It takes longer than you would like, but Nera's corrections keep the packet from lying to you twice.")
        elif selection_key == "insight":
            self.player_action("Pick the lie out of the handoff and follow the correction instead.")
            if self.skill_check(self.state.player, "Insight", 12, context="to hear where the courier packet expects the wrong listener"):
                reward_xp = 15
                self.say("You catch the packet's frightened rhythm: one line was written to be found, the next to be believed by the wrong man.")
            else:
                self.say("You miss the cleanest tell at first, but Sella hears the panic in the wording and pushes you back onto the true line.")
        elif selection_key == "blessing":
            self.player_action("Speak the false countersign aloud and wait for the packet to correct you.")
            reward_xp = 15
            self.say("The lie lands exactly where it should. Nera smiles without warmth as the real handoff phrase practically underlines itself.")
        else:
            self.player_action("Have Nera walk you through the courier habits and take the cleanest lead she can name.")
            self.speaker(
                "Nera Doss",
                "Ashfall uses the countersign to keep relief lines from killing their own scouts, and Emberhall copies the same hand too carefully in the ledger room. Different roads, same bad clerk.",
            )
        self.state.flags["stonehill_quiet_room_scene_done"] = True
        self.state.flags["stonehill_quiet_room_intel_decoded"] = True
        self.add_clue("Nera's quiet-room packet reveals an Ashfall countersign and ties Emberhall's ledger chain to the same courier hand.")
        self.add_journal(
            "In a private room above the Ashlamp, you decoded the quiet-table packet. The stolen countersign should help wrong-foot Ashfall's command line, and the same courier hand should make Emberhall's ledgers easier to read."
        )
        self.reward_party(xp=reward_xp, reason="decoding the quiet-room packet above the Ashlamp")

    def stonehill_talk_sella(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("stonehill_sella_met"):
            self.state.flags["stonehill_sella_met"] = True
            self.speaker(
                "Sella Quill",
                "People tell the truth in songs by accident. That is why I stay through the second chorus and leave before the third promise.",
            )
        while True:
            self.refresh_quest_statuses(announce=False)
            options: list[tuple[str, str]] = []
            if self.quest_is_ready("songs_for_the_missing"):
                options.append(("turn_in", self.action_option("Bring Sella the three true details she asked for.")))
            elif not self.has_quest("songs_for_the_missing") and not self.quest_is_completed("songs_for_the_missing"):
                options.append(("quest", "\"Can a song do anything for the missing?\""))
            elif self.has_quest("songs_for_the_missing") and not self.quest_is_completed("songs_for_the_missing"):
                options.append(("reminder", "\"Who do you still need me to hear properly?\""))
            if not self.state.flags.get("stonehill_sella_room_asked"):
                options.append(("room", "\"What does this room sound like to you?\""))
            if not self.state.flags.get("stonehill_sella_performance_attempted"):
                options.append(("performance", self.quoted_option("PERFORMANCE", "Let me trade you a verse for a rumor.")))
            if (
                self.quest_is_completed("songs_for_the_missing")
                and self.quest_is_completed("find_dain_harl")
                and not self.state.flags.get("stonehill_sella_dain_memorial_done")
            ):
                options.append(("memorial", self.action_option("Tell Sella Jerek finally has Dain Harl's true ending.")))
            options.append(("leave", self.action_option("Leave Sella Quill to her listening.")))
            choice = self.scenario_choice("Choose what you say to Sella Quill.", [text for _, text in options])
            selection_key, _ = options[choice - 1]
            if selection_key == "turn_in":
                self.player_action("Bring Sella the three true details she asked for.")
                self.turn_in_quest("songs_for_the_missing", giver="Sella Quill")
            elif selection_key == "quest":
                self.player_speaker("Can a song do anything for the missing?")
                self.speaker(
                    "Sella Quill",
                    "Not for the dead. They are past needing help from my sort. But for the living? A true name keeps grief from being flattened into rumor. Bring me three details this room has not made cowardly yet, and I will give them back to Iron Hollow in a shape worth remembering.",
                )
                self.grant_quest(
                    "songs_for_the_missing",
                    note="Sella wants three true details from the Ashlamp's regulars so the missing stop being reduced to muttered counts and roadside warnings.",
                )
            elif selection_key == "reminder":
                missing: list[str] = []
                if not self.state.flags.get("songs_for_missing_jerek_detail"):
                    missing.append("Jerek Harl")
                if not self.state.flags.get("songs_for_missing_tam_detail"):
                    missing.append("Old Tam Veller")
                if not self.state.flags.get("songs_for_missing_nera_detail"):
                    missing.append("Nera Doss")
                self.player_speaker("Who do you still need me to hear properly?")
                if missing:
                    self.speaker(
                        "Sella Quill",
                        f"Still missing from the song: {', '.join(missing)}. Truth travels badly in a frightened room unless somebody carries it on purpose.",
                    )
                else:
                    self.speaker("Sella Quill", "You have all three. Now bring them back before the room turns them into furniture and weather.")
            elif selection_key == "room":
                self.state.flags["stonehill_sella_room_asked"] = True
                self.player_speaker("What does this room sound like to you?")
                self.speaker(
                    "Sella Quill",
                    "Like a town trying not to become the story told about it elsewhere. Also like one table in the corner is speaking too softly for honest fear. Soft voices in a frontier inn are either lovers or knives, and nobody over there looks romantic.",
                )
                self.add_clue("Sella Quill thinks one quiet Ashlamp table is speaking too softly for honest fear.")
            elif selection_key == "performance":
                self.state.flags["stonehill_sella_performance_attempted"] = True
                self.player_speaker("Let me trade you a verse for a rumor.")
                success = self.skill_check(self.state.player, "Performance", 12, context="to turn Sella's room into an ally instead of an audience")
                if success:
                    self.say(
                        "Your verse is not perfect, but it is alive enough to make the room choose listening over muttering for one valuable minute."
                    )
                    self.reward_party(xp=10, gold=4, reason="winning the Ashlamp's room for a verse")
                else:
                    self.say("The room gives you courtesy, not surrender. Even Sella's smile says that was worth trying once and only once.")
            elif selection_key == "memorial":
                self.state.flags["stonehill_sella_dain_memorial_done"] = True
                self.player_action("Tell Sella Jerek finally has Dain Harl's true ending.")
                self.speaker(
                    "Sella Quill",
                    "Then the song changes tonight. Rooms like this keep the missing only while nobody is brave enough to bring them back in one true shape.",
                )
                self.say(
                    "When Sella takes the room, the second chorus changes. Where the old version counted wagons and weather, the new one names Dain Harl, the blue scarf, and the road that still carried truth home."
                )
                self.add_journal(
                    "Sella changed her Ashlamp song after Dain Harl's fate was brought home, giving the room a verse that carried his name instead of another warning."
                )
                self.reward_party(xp=10, reason="hearing Sella change the song for Dain Harl")
            else:
                self.player_action("You leave Sella Quill to her listening.")
                return

    def stonehill_talk_old_tam(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("stonehill_old_tam_met"):
            self.state.flags["stonehill_old_tam_met"] = True
            self.speaker(
                "Old Tam Veller",
                "Young people think a ruin starts where the roof is missing. A ruin starts where folk stop agreeing on what the place was for.",
            )
        while True:
            options: list[tuple[str, str]] = []
            if not self.state.flags.get("stonehill_old_tam_route_asked"):
                options.append(("route", "\"What old road are you remembering tonight?\""))
            if not self.state.flags.get("songs_for_missing_tam_detail"):
                options.append(
                    (
                        "detail",
                        self.quoted_option("INSIGHT", "Stay with the part that still has a name in it."),
                    )
                )
            options.append(("leave", self.action_option("Leave Old Tam to his cooling cup.")))
            choice = self.scenario_choice("Choose what you say to Old Tam Veller.", [text for _, text in options])
            selection_key, _ = options[choice - 1]
            if selection_key == "route":
                self.state.flags["stonehill_old_tam_route_asked"] = True
                self.player_speaker("What old road are you remembering tonight?")
                self.speaker(
                    "Old Tam Veller",
                    "The manor-side crawl under the hill, mostly. Used to breathe warm at dusk like somebody had candles where no cellar should still be whole. Town pretends the old stone is dead until it starts helping the wrong people live in it.",
                )
                self.add_clue("Old Tam remembers warm dusk air from old cellar runs under the manor hill.")
            elif selection_key == "detail":
                self.player_speaker("Stay with the part that still has a name in it.")
                success = self.skill_check(self.state.player, "Insight", 12, context="to keep Old Tam on one true memory instead of six broken ones")
                if success:
                    self.state.flags["songs_for_missing_tam_detail"] = True
                    self.speaker(
                        "Old Tam Veller",
                        "Nell Fallow. Best ore nose I ever saw on two legs. Carried a bent lantern hook on her belt because she never trusted a tunnel that wanted both hands. There. That one still deserves more than 'lost crew'.",
                    )
                    self.add_journal("Old Tam gave you a true detail for Sella's song: Nell Fallow, bent lantern hook, best ore nose on the old road.")
                else:
                    self.speaker("Old Tam Veller", "Too quick. Memory's a bad mine. Rush it and you only bring loose stone up.")
            else:
                self.player_action("You leave Old Tam to his cooling cup.")
                return

    def stonehill_talk_nera(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("stonehill_nera_met"):
            self.state.flags["stonehill_nera_met"] = True
            self.speaker(
                "Nera Doss",
                "I fell, that is all. And if you believe that, you have not spent much time around men who want messages to arrive edited.",
            )
        while True:
            self.refresh_quest_statuses(announce=False)
            options: list[tuple[str, str]] = []
            if self.quest_is_ready("quiet_table_sharp_knives"):
                options.append(("turn_in", self.action_option("Tell Nera what the quiet table was really doing.")))
            elif not self.state.flags.get("stonehill_nera_treated"):
                options.append(("treat", self.quoted_option("MEDICINE", "Let me look at that split lip.")))
            if not self.has_quest("quiet_table_sharp_knives") and not self.quest_is_completed("quiet_table_sharp_knives"):
                options.append(("quest", "\"That was not a fall. Who wanted your message changed?\""))
            elif (
                self.has_quest("quiet_table_sharp_knives")
                and not self.quest_is_completed("quiet_table_sharp_knives")
                and not self.state.flags.get("quiet_table_knives_resolved")
            ):
                options.append(("shadow", self.action_option("Shadow the quiet table Nera pointed out.")))
            options.append(("leave", self.action_option("Leave Nera Doss to the wall table and the exits.")))
            choice = self.scenario_choice("Choose what you say to Nera Doss.", [text for _, text in options])
            selection_key, _ = options[choice - 1]
            if selection_key == "turn_in":
                self.player_action("Tell Nera what the quiet table was really doing.")
                self.turn_in_quest("quiet_table_sharp_knives", giver="Nera Doss")
            elif selection_key == "treat":
                self.player_speaker("Let me look at that split lip.")
                success = self.skill_check(self.state.player, "Medicine", 12, context="to clean Nera's split lip without turning her into a public patient")
                self.state.flags["stonehill_nera_treated"] = True
                if success:
                    self.state.flags["songs_for_missing_nera_detail"] = True
                    self.speaker(
                        "Nera Doss",
                        "Better. Thanks. If your singer is asking after the missing, tell her Pella Voss still ran messages with one bad knee and a laugh mean enough to shame rain itself. She got farther hurt than most men get healthy.",
                    )
                    elira = self.find_companion("Elira Dawnmantle")
                    if elira is not None:
                        self.adjust_companion_disposition(elira, 1, "you treated Nera without making a show of it")
                else:
                    self.speaker(
                        "Nera Doss",
                        "You tried gently, which already puts you ahead of the room. Leave it. I can still carry my own face.",
                    )
            elif selection_key == "quest":
                self.player_speaker("That was not a fall. Who wanted your message changed?")
                self.speaker(
                    "Nera Doss",
                    "A quiet table in the corner keeps paying for conversations to finish uglier than they start. They do not stab first. They tilt. They edit. They buy one wrong word and wait for the room to do the hard part. If you're useful, go hear what they think nobody else deserves to hear.",
                )
                self.grant_quest(
                    "quiet_table_sharp_knives",
                    note="Nera thinks one quiet Ashlamp table is buying arguments, editing messages, and steering the room toward useful violence.",
                )
            elif selection_key == "shadow":
                self.stonehill_shadow_quiet_table()
            else:
                self.player_action("You leave Nera Doss to the wall table and the exits.")
                return

    def stonehill_shadow_quiet_table(self) -> None:
        assert self.state is not None
        options: list[tuple[str, str]] = [
            (
                "stealth",
                self.skill_tag("STEALTH", self.action_option("Move around the beams and hear the quiet table cleanly.")),
            ),
            (
                "insight",
                self.skill_tag("INSIGHT", self.action_option("Read which speaker thinks they are safest in the lie.")),
            ),
            (
                "deception",
                self.skill_tag("DECEPTION", self.action_option("Pass by like hired help and let them mistake you for nobody worth remembering.")),
            ),
        ]
        if self.stonehill_has_liars_blessing():
            options.append(
                (
                    "blessing",
                    self.skill_tag(
                        "LIAR'S BLESSING",
                        self.action_option("Repeat the lie the quiet table expects to hear and wait for the correction."),
                    ),
                )
            )
        options.append(("leave", self.action_option("Leave the quiet table for another moment.")))
        choice = self.scenario_choice("How do you work the quiet table?", [text for _, text in options], allow_meta=False)
        selection_key, _ = options[choice - 1]
        if selection_key == "leave":
            self.player_action("Leave the quiet table for another moment.")
            return
        if selection_key == "stealth":
            self.player_action("Move around the beams and hear the quiet table cleanly.")
            success = self.skill_check(self.state.player, "Stealth", 12, context="to catch the table's real purpose before it changes shape")
        elif selection_key == "insight":
            self.player_action("Read which speaker thinks they are safest in the lie.")
            success = self.skill_check(self.state.player, "Insight", 12, context="to spot the paid mouth steering the table")
        elif selection_key == "deception":
            self.player_action("Pass by like hired help and let them mistake you for nobody worth remembering.")
            success = self.skill_check(self.state.player, "Deception", 13, context="to hear the quiet table without being clocked")
        else:
            self.player_action("Repeat the lie the quiet table expects to hear and wait for the correction.")
            success = True
        if success:
            self.state.flags["quiet_table_knives_resolved"] = True
            self.state.flags["stonehill_barfight_ready"] = False
            self.state.flags["stonehill_instigator_unmasked"] = True
            self.say(
                "The corner table folds once you get the rhythm of it. One man keeps buying outrage half a sentence at a time, "
                "nudging miners against mercenaries and couriers against witnesses. When you move on him, his partner bolts first, which tells the rest of the room exactly how honest they were not."
            )
            self.add_clue("A paid Ashen Brand mouth at the Ashlamp was trying to keep Iron Hollow divided and easy to read.")
            self.add_journal("You exposed the quiet-table scheme inside Ashlamp Inn before it could buy a worse night.")
            bryn = self.find_companion("Bryn Underbough")
            if bryn is not None:
                self.adjust_companion_disposition(bryn, 1, "you read the inn before it turned ugly")
        else:
            self.state.flags["stonehill_barfight_ready"] = True
            self.say(
                "One of them clocks the attention a moment before you close the angle. The quiet table goes loud on purpose, somebody shouts liar at the wrong man, "
                "and the whole common room starts sliding toward broken furniture."
            )

    def stonehill_resolve_barfight(self) -> None:
        assert self.state is not None
        options: list[tuple[str, str]] = [
            (
                "persuasion",
                self.skill_tag("PERSUASION", self.action_option("Pull the room back from the edge before the first chair flies.")),
            ),
            (
                "insight",
                self.skill_tag("INSIGHT", self.action_option("Name the real instigator and make the room turn the right way.")),
            ),
            (
                "intimidation",
                self.skill_tag("INTIMIDATION", self.action_option("Shut the whole room down with one harder threat.")),
            ),
            (
                "athletics",
                self.skill_tag("ATHLETICS", self.action_option("Catch the first bench, shove the two worst fools apart, and own the middle.")),
            ),
            (
                "performance",
                self.skill_tag("PERFORMANCE", self.action_option("Break the tension with a loud toast sharp enough to steal the room.")),
            ),
        ]
        if self.stonehill_has_liars_blessing():
            options.append(
                (
                    "blessing",
                    self.skill_tag(
                        "LIAR'S BLESSING",
                        self.action_option("Tell the liar exactly the lie he thinks nobody else heard."),
                    ),
                )
            )
        options.append(("fight", self.action_option("Join the fight and end it the hard way.")))
        choice = self.scenario_choice("How do you handle the Ashlamp barfight?", [text for _, text in options], allow_meta=False)
        selection_key, _ = options[choice - 1]
        if selection_key == "persuasion":
            self.player_action("Pull the room back from the edge before the first chair flies.")
            success = self.skill_check(self.state.player, "Persuasion", 13, context="to keep the Ashlamp's fear from finding a target")
        elif selection_key == "insight":
            self.player_action("Name the real instigator and make the room turn the right way.")
            success = self.skill_check(self.state.player, "Insight", 12, context="to expose the paid mouth in the room")
        elif selection_key == "intimidation":
            self.player_action("Shut the whole room down with one harder threat.")
            success = self.skill_check(self.state.player, "Intimidation", 13, context="to freeze the room in place")
        elif selection_key == "athletics":
            self.player_action("Catch the first bench, shove the two worst fools apart, and own the middle.")
            success = self.skill_check(self.state.player, "Athletics", 12, context="to break up the barfight before it spreads")
        elif selection_key == "performance":
            self.player_action("Break the tension with a loud toast sharp enough to steal the room.")
            success = self.skill_check(self.state.player, "Performance", 12, context="to turn the room before anger hardens")
        elif selection_key == "blessing":
            self.player_action("Tell the liar exactly the lie he thinks nobody else heard.")
            success = True
        else:
            self.player_action("Join the fight and end it the hard way.")
            success = False

        self.state.flags["stonehill_barfight_ready"] = False
        self.state.flags["stonehill_barfight_resolved"] = True
        self.state.flags["stonehill_barfight_seen"] = True

        if success:
            self.say(
                "The room turns all at once once the right pressure point is named. The loudest man in the common room is suddenly not the one holding it. "
                "A chalk nub, a folded payment note, and one badly timed protest hit the floor in the same breath, and Mara is already moving before the liar finishes deciding whether to run."
            )
            self.reward_party(xp=15, reason="keeping the Ashlamp's common room from breaking")
            self.stonehill_adjust_town_fear(-1)
            tolan = self.find_companion("Tolan Ironshield")
            if tolan is not None:
                self.adjust_companion_disposition(tolan, 1, "you kept order in the Ashlamp without making civilians pay for it")
        else:
            self.state.flags["stonehill_barfight_brawled"] = True
            self.say(
                "You hit the middle of it hard enough to end it, but the lesson arrives in bruises, spilled stew, and one cracked chair Mara silently adds to your moral bill. "
                "Even so, the paid mouth loses his note purse in the scramble, and with it the room's last excuse not to see what tonight was meant to become."
            )
            if self.state.gold > 0:
                fee = min(2, self.state.gold)
                self.state.gold -= fee
                self.say(f"Mara keeps {marks_label(fee)} aside for broken crockery and does not apologize for it.")
            self.reward_party(xp=10, reason="ending the Ashlamp barfight the hard way")

        if not self.state.flags.get("marked_keg_resolved"):
            self.state.flags["marked_keg_resolved"] = True
            self.add_journal("The Ashlamp barfight exposed the hand behind Mara's marked keg.")
        if self.has_quest("quiet_table_sharp_knives") or self.state.flags.get("stonehill_instigator_unmasked"):
            self.state.flags["quiet_table_knives_resolved"] = True
        self.add_clue("The Ashlamp barfight exposed a paid mouth trying to turn Iron Hollow's fear inward.")
