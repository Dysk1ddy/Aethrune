from __future__ import annotations

from ..data.story.background_openings import BACKGROUND_STARTS
from ..content import (
    create_elira_dawnmantle,
    create_enemy,
    create_kaelis_starling,
    create_rhogar_valeguard,
    create_tolan_ironshield,
)
from .encounter import Encounter


class StoryIntroMixin:
    def intro_pick_enemy(self, templates, *, name: str | None = None):
        return create_enemy(self.rng.choice(tuple(templates)), name=name)

    def scene_background_prologue(self) -> None:
        assert self.state is not None
        background = self.state.player.background
        handlers = {
            "Soldier": self.prologue_soldier,
            "Acolyte": self.prologue_acolyte,
            "Criminal": self.prologue_criminal,
            "Sage": self.prologue_sage,
            "Outlander": self.prologue_outlander,
            "Charlatan": self.prologue_charlatan,
            "Guild Artisan": self.prologue_guild_artisan,
            "Hermit": self.prologue_hermit,
        }
        handlers.get(background, self.prologue_default)()

    def background_prologue_header(self, background: str) -> None:
        entry = BACKGROUND_STARTS.get(background, {})
        self.banner(f"{background} Prologue: {entry.get('title', 'Opening')}")
        self.say(
            f"Starting point: {entry.get('summary', 'You begin close to Neverwinter, with the frontier already pulling at your day.')}",
            typed=True,
        )

    def finish_background_prologue(self, background: str, closing_text: str, *, clue: str = "", journal_note: str = "") -> None:
        assert self.state is not None
        if clue:
            self.add_clue(clue)
        self.say(closing_text)
        self.add_journal(
            journal_note
            or f"Your {background.lower()} prologue ends with the trail leading toward Mira Thann's private briefing in Neverwinter."
        )
        self.state.flags["background_prologue_completed"] = background
        self.state.flags["system_profile_seeded"] = True
        self.state.flags.pop("background_prologue_pending", None)
        self.state.current_scene = "wayside_luck_shrine"

    def wayside_elira_first_read(self) -> None:
        assert self.state is not None
        player = self.state.player
        background = player.background
        class_name = player.class_name
        if background == "Acolyte" or class_name in {"Cleric", "Paladin"}:
            self.state.flags["elira_first_read"] = "faith_action"
            self.speaker(
                "Elira Dawnmantle",
                "If your faith can move your hands, I need both. If it only names the pain, pray after.",
            )
        elif background == "Soldier" or class_name == "Fighter":
            self.state.flags["elira_first_read"] = "triage_competence"
            self.speaker(
                "Elira Dawnmantle",
                "You have seen triage before. Good. Then you know the first rule: choose fast and keep breathing.",
            )
        elif background in {"Criminal", "Charlatan"} or class_name == "Rogue":
            self.state.flags["elira_first_read"] = "unwatched_mercy"
            self.speaker(
                "Elira Dawnmantle",
                "No one important is watching this shrine. That makes what you do next more honest, not less.",
            )
        elif background == "Sage" or class_name == "Wizard":
            self.state.flags["elira_first_read"] = "knowledge_vs_saving"
            self.speaker(
                "Elira Dawnmantle",
                "Name the poison if you can, but do not mistake knowing it for saving him.",
            )
        else:
            self.state.flags["elira_first_read"] = "steady_hands"
            self.speaker("Elira Dawnmantle", "If you can keep your hands steady, I can use them.")

    def wayside_set_elira_trust(self, route: str, trust: str) -> None:
        assert self.state is not None
        self.state.flags["wayside_aid_route"] = route
        self.state.flags["elira_initial_trust_reason"] = trust

    def wayside_apply_elira_trust(self) -> None:
        assert self.state is not None
        elira = self.find_companion("Elira Dawnmantle")
        if elira is None:
            return
        trust = self.state.flags.get("elira_initial_trust_reason")
        if trust == "warm_trust":
            self.adjust_companion_disposition(elira, 1, "you helped the wounded before asking anything of her")
            self.speaker("Elira Dawnmantle", "You helped before I had to ask twice. I remember that.")
        elif trust == "spiritual_kinship":
            self.adjust_companion_disposition(elira, 1, "your prayer made room for action")
            self.speaker("Elira Dawnmantle", "You know prayer has to leave the mouth eventually. Good.")
        elif trust == "wary_respect":
            self.adjust_companion_disposition(elira, 1, "you read danger in the road before it announced itself")
            self.speaker("Elira Dawnmantle", "You read the road sharply. Keep that edge pointed at the people hurting it.")
        elif trust == "reserved_kindness":
            self.speaker(
                "Elira Dawnmantle",
                "You kept moving when the shrine needed hands. I can still walk beside you, but trust will need work.",
            )

    def scene_wayside_luck_shrine(self) -> None:
        assert self.state is not None
        if self.state.flags.get("wayside_luck_shrine_seen"):
            self.state.current_scene = "greywake_triage_yard"
            return
        self.state.flags["wayside_luck_shrine_seen"] = True
        self.state.flags["wayside_luck_bell_seen"] = True
        self.state.flags["elira_first_contact"] = True
        self.state.flags["neverwinter_elira_met"] = True
        self.banner("Wayside Luck Shrine")
        self.say(
            "The first bells of Neverwinter are still only a rumor when you find the shrine: a lucky-road marker under a black oak, "
            "a cracked luck bell hanging from green road-ribbons stiff with rain. A young priestess has turned the altar into a triage board.",
            typed=True,
        )
        self.wayside_elira_first_read()
        self.speaker("Elira Dawnmantle", "If you are here to pray, kneel. If you are here to help, wash your hands first.")
        choice = self.scenario_choice(
            "How do you help at the roadside shrine?",
            [
                self.skill_tag("MEDICINE", self.action_option("Stabilize the poisoned drover with Elira.")),
                self.skill_tag("RELIGION", self.action_option("Lead Tymora's road-prayer so Elira can keep working.")),
                self.skill_tag("INVESTIGATION", self.action_option("Inspect the harness marks and false authority signs.")),
                self.action_option("Keep the shrine moving and save your strength for the road."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Stabilize the poisoned drover with Elira.")
            self.wayside_set_elira_trust("wounded", "warm_trust")
            if self.skill_check(self.state.player, "Medicine", 8, context="to slow the ash-bitter poison at the wayside shrine"):
                self.state.flags["elira_helped"] = True
                self.state.flags["wayside_drover_stabilized"] = True
                self.add_clue("Elira identifies an ash-bitter poison reaching victims before the road even enters Neverwinter.")
                self.reward_party(xp=10, reason="helping Elira stabilize a poisoned drover")
                self.say("The gray edge of the wound stops spreading, and Elira gives you one small nod before reaching for clean thread.")
            else:
                self.say("The poison keeps moving, but your pressure and clean bandage buy Elira enough time to save the drover.")
        elif choice == 2:
            self.player_action("Lead Tymora's road-prayer so Elira can keep working.")
            self.wayside_set_elira_trust("prayer", "spiritual_kinship")
            if self.skill_check(self.state.player, "Religion", 8, context="to steady the wayside shrine and caravan"):
                self.state.flags["elira_helped"] = True
                self.state.flags["wayside_prayer_steadied"] = True
                self.reward_party(xp=10, reason="steadying the Wayside Luck Shrine")
                self.say("The prayer quiets the panic without softening the danger, which may be Tymora's cleanest kind of luck.")
            else:
                self.say("The words land unevenly, but the caravan still leaves with steadier hands and one less argument.")
            self.add_inventory_item("blessed_salve", source="Elira's wayside shrine satchel")
        elif choice == 3:
            self.player_action("Inspect the harness marks and false authority signs.")
            if self.skill_check(self.state.player, "Investigation", 8, context="to connect poison, harness marks, and forged authority at the wayside shrine"):
                self.wayside_set_elira_trust("road_marks", "wary_respect")
                self.state.flags["elira_helped"] = True
                self.state.flags["wayside_false_road_marks_found"] = True
                self.state.flags["blackwake_millers_ford_lead"] = True
                self.add_clue("Harness marks near the wayside shrine match false roadwarden inspections close to Neverwinter.")
                self.reward_party(xp=10, reason="reading the poisoned road evidence")
                self.say("The harness cuts are too neat for panic. Someone with copied authority pulled this wagon out of line.")
            else:
                self.wayside_set_elira_trust("road_marks_uncertain", "reserved_kindness")
                self.say("You catch the pattern too late to name it cleanly, but the false inspection cuts stay in your mind.")
        else:
            self.player_action("Keep the shrine moving and save your strength for the road.")
            self.wayside_set_elira_trust("none", "reserved_kindness")
            self.add_inventory_item("potion_healing", source="Elira's road charity basket")
            self.say("Elira presses a healing draught into your hands anyway. Luck, apparently, dislikes going unused.")

        if not self.has_companion("Elira Dawnmantle"):
            options = [
                self.quoted_option("RECRUIT", "Come with me. The next wound will be on the road, not at this shrine."),
                self.quoted_option("SAFE", "Stay with them. I will carry your warning to Neverwinter."),
            ]
            recruit_choice = self.scenario_choice("Elira wipes her hands clean and looks toward the city road.", options, allow_meta=False)
            self.player_choice_output(options[recruit_choice - 1])
            self.state.flags["elira_wayside_recruit_attempted"] = True
            if recruit_choice == 1:
                if self.state.flags.get("elira_helped") or self.skill_check(
                    self.state.player,
                    "Persuasion",
                    8,
                    context="to convince Elira the road needs her before Neverwinter",
                ):
                    self.recruit_companion(create_elira_dawnmantle())
                    self.state.flags["elira_pre_neverwinter_recruited"] = True
                    self.state.flags["elira_neverwinter_recruited"] = True
                    self.state.flags["elira_first_companion"] = True
                    self.wayside_apply_elira_trust()
                    self.speaker("Elira Dawnmantle", "Then I walk now. Tymora can keep a shrine; people need hands.")
                    self.state.flags["wayside_luck_bell_promised"] = True
                    self.say(
                        "Elira ties the cracked luck bell once with a green road-ribbon, not as a prayer, "
                        "but as a promise that someone will come back to repair it."
                    )
                else:
                    self.state.flags["elira_wayside_recruit_failed"] = True
                    self.state.flags["elira_phandalin_fallback_pending"] = True
                    self.speaker("Elira Dawnmantle", "Not yet. I will not leave people bleeding because the road might need me more loudly.")
            else:
                self.state.flags["elira_phandalin_fallback_pending"] = True
                self.speaker("Elira Dawnmantle", "Then I will move the wounded toward the city and trust you to keep the road alive.")
        self.state.current_scene = "greywake_triage_yard"

    def scene_greywake_triage_yard(self) -> None:
        assert self.state is not None
        if self.state.flags.get("greywake_triage_yard_seen"):
            self.state.current_scene = "greywake_road_breakout"
            return
        self.state.flags["greywake_triage_yard_seen"] = True
        self.state.flags["greywake_outcome_sorting_seen"] = True
        self.banner("Greywake Triage Yard")
        self.say(
            "Greywake Yard is where Neverwinter pretends the road can be made orderly before it enters the city. Today the ropes sag, "
            "the clerks are pale, and one intake board has already sorted wagons into treat, hold, and lost before anyone has crossed "
            "the gate. One manifest lists three wounded travelers by name before the wagons carrying them arrive.",
            typed=True,
        )
        self.add_clue("Greywake's intake board sorted travelers into outcomes before their wagons reached the yard.")
        if self.has_companion("Elira Dawnmantle"):
            self.speaker("Elira Dawnmantle", "That ledger is not reporting wounds. It is assigning endings.")
        elif self.state.flags.get("elira_first_contact"):
            self.speaker(
                "Elira Dawnmantle",
                "I kept the shrine breathing. Now someone has taught the road to decide who survives before it sees them.",
            )
        choice = self.scenario_choice(
            "How do you stabilize Greywake Yard?",
            [
                self.skill_tag("INSIGHT", self.action_option("Challenge the outcome-marked manifest before the clerk can bury it.")),
                self.skill_tag("MEDICINE", self.action_option("Match the prewritten triage tags against the wounded with Elira.")),
                self.skill_tag("PERSUASION", self.action_option("Make the clerks read the outcome marks aloud before panic swallows them.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Challenge the outcome-marked manifest before the clerk can bury it.")
            if self.skill_check(self.state.player, "Insight", 9, context="to challenge the outcome-marked Greywake manifest"):
                self.state.flags["greywake_manifest_preserved"] = True
                self.state.flags["greywake_outcome_manifest_read"] = True
                self.state.flags["greywake_mira_evidence_kind"] = "marked_manifest"
                self.state.flags["system_profile_seeded"] = True
                self.state.flags["varyn_route_pattern_seen"] = True
                self.add_clue(
                    "The Greywake manifest pre-sorted travelers by expected wound, delay, and loss before their wagons arrived."
                )
                self.say(
                    "The clerk stops arguing when you name the outcome column: TREAT, HOLD, LOST. The wagon curtain opens, "
                    "and the first wound matches the ink."
                )
            else:
                self.state.flags["greywake_mira_evidence_kind"] = "unverified_outcome_board"
                self.say("The manifest is wrong in exactly the way fear makes hard to prove. The outcome marks keep the yard volatile.")
        elif choice == 2:
            self.player_action("Match the prewritten triage tags against the wounded with Elira.")
            if self.skill_check(self.state.player, "Medicine", 9, context="to stabilize the Greywake wounded line"):
                self.state.flags["greywake_wounded_stabilized"] = True
                self.state.flags["greywake_outcome_tags_matched_wounds"] = True
                self.state.flags["greywake_mira_evidence_kind"] = "matched_triage_tags"
                self.state.flags["system_profile_seeded"] = True
                self.state.flags["elira_helped"] = True
                self.add_clue("Greywake triage tags matched injury categories written before the victims arrived.")
                self.reward_party(xp=10, reason="stabilizing Greywake's wounded line")
                self.say(
                    "The wounded line starts moving like triage instead of panic, but the tags trouble Elira more than the blood: "
                    "three injuries were labeled before the victims reached the rope."
                )
            else:
                self.state.flags["greywake_mira_evidence_kind"] = "unverified_outcome_board"
                self.say("Elira prevents the worst of it, but the line never fully becomes calm, and the prewritten tags keep circulating.")
        else:
            self.player_action("Make the clerks read the outcome marks aloud before panic swallows them.")
            if self.skill_check(self.state.player, "Persuasion", 9, context="to steady Greywake Yard before the attack"):
                self.state.flags["greywake_yard_steadied"] = True
                self.state.flags["greywake_sorting_publicly_exposed"] = True
                self.state.flags["greywake_mira_evidence_kind"] = "yard_witnesses"
                self.state.flags["system_profile_seeded"] = True
                self.add_clue("Greywake witnesses heard clerks read outcome marks for travelers who had not arrived yet.")
                self.reward_party(xp=10, reason="steadying Greywake Yard")
                self.say(
                    "Teamsters become stretcher hands, pilgrims become lookouts, and the clerks say the quiet part aloud: "
                    "the manifest is dividing people into outcomes, not arrivals."
                )
            else:
                self.state.flags["greywake_mira_evidence_kind"] = "unverified_outcome_board"
                self.say("The crowd listens for a breath, then the wrong shout from the road pulls the fear loose again.")

        if not self.has_companion("Elira Dawnmantle"):
            self.speaker(
                "Elira Dawnmantle",
                "This is not a ledger mistake. If I stay, I treat what someone already decided. If I walk with you, maybe we reach the hand moving the marks.",
            )
            options = [
                self.quoted_option("RECRUIT", "Then walk with me now. We stop the wound before it reaches the shrine."),
                self.quoted_option("SAFE", "Stay. If the road brings me back alive, I will find you again."),
            ]
            recruit_choice = self.scenario_choice(
                "A clerk bell rings from the east rope while Elira closes her field kit with one hand.",
                options,
                allow_meta=False,
            )
            self.player_choice_output(options[recruit_choice - 1])
            self.state.flags["elira_greywake_recruit_attempted"] = True
            if recruit_choice == 1:
                dc = 6 if self.state.flags.get("elira_helped") or self.state.flags.get("greywake_wounded_stabilized") else 8
                if self.skill_check(self.state.player, "Persuasion", dc, context="to convince Elira to join before Greywake breaks"):
                    self.recruit_companion(create_elira_dawnmantle())
                    self.state.flags["elira_greywake_recruited"] = True
                    self.state.flags["elira_neverwinter_recruited"] = True
                    self.state.flags["elira_first_companion"] = True
                    self.speaker("Elira Dawnmantle", "Then I stop waiting for the next wound to be carried to me.")
                else:
                    self.state.flags["elira_greywake_recruit_failed"] = True
                    self.state.flags["elira_phandalin_fallback_pending"] = True
                    self.speaker("Elira Dawnmantle", "Not yet. If Tymora is kind, you will find me in Phandalin before the next prayer turns into triage.")
            else:
                self.state.flags["elira_phandalin_fallback_pending"] = True
                self.speaker("Elira Dawnmantle", "Then I will keep this line breathing and follow the wounded south.")
        self.state.flags["greywake_attack_imminent"] = True
        self.say(
            "The east-rope clerk tries to fold the marked manifest under his coat. A roadwarden badge flashes too cleanly at the gate, "
            "and the first arrow cuts the quarantine line before anyone can pretend this is only paperwork."
        )
        self.state.current_scene = "greywake_road_breakout"

    def scene_greywake_road_breakout(self) -> None:
        assert self.state is not None
        self.banner("Greywake Road Breakout")
        self.say(
            "The attack comes under clerk bells and wagon shouts. Ashen Brand cutters hit the triage yard with blades out, "
            "not to hold ground, but to steal the outcome-marked manifest and leave no witness calm enough to describe how the road "
            "was pre-sorted before it bled.",
            typed=True,
        )
        enemies = [create_enemy("bandit"), create_enemy("bandit_archer")]
        if self.act1_party_size() >= 3:
            enemies.append(self.intro_pick_enemy(("goblin_skirmisher", "brand_saboteur")))
        else:
            enemies[0].current_hp = min(enemies[0].current_hp, 8)
            enemies[0].max_hp = enemies[0].current_hp
        hero_bonus = 0
        if self.state.flags.get("greywake_yard_steadied"):
            hero_bonus += 1
        if self.has_companion("Elira Dawnmantle"):
            self.apply_status(self.state.player, "blessed", 1, source="Elira's field prayer at Greywake")
            self.say("Elira's prayer lands fast and practical, the kind meant to keep a pulse under pressure.")
        elif self.state.flags.get("elira_first_contact"):
            self.say("Elira stays with the wounded line, making the yard harder to turn into a slaughter while you face the blades.")

        choice = self.scenario_choice(
            "What do you protect first when Greywake breaks?",
            [
                self.skill_tag("MEDICINE", self.action_option("Guard the wounded line before the cutters can turn it into leverage.")),
                self.skill_tag("INVESTIGATION", self.action_option("Seize the manifest runner before the proof disappears.")),
                self.skill_tag("INTIMIDATION", self.action_option("Break the attackers' nerve loudly enough for the yard to hear.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Guard the wounded line before the cutters can turn it into leverage.")
            if self.skill_check(self.state.player, "Medicine", 10, context="to keep Greywake's wounded alive under attack"):
                self.state.flags["greywake_wounded_line_guarded"] = True
                hero_bonus += 1
                elira = self.find_companion("Elira Dawnmantle")
                if elira is not None:
                    self.adjust_companion_disposition(elira, 1, "you protected the wounded before chasing proof")
                self.say("The wounded line folds behind cover instead of into panic, and the cutters lose their ugliest leverage.")
        elif choice == 2:
            self.player_action("Seize the manifest runner before the proof disappears.")
            if self.skill_check(self.state.player, "Investigation", 10, context="to preserve the impossible Greywake manifest under attack"):
                self.state.flags["greywake_manifest_preserved"] = True
                self.state.flags["system_profile_seeded"] = True
                self.state.flags["varyn_route_pattern_seen"] = True
                hero_bonus += 1
                self.add_clue("The Greywake manifest listed wounded travelers before they arrived, as if someone was sorting losses ahead of the road.")
                self.say("The runner drops the manifest into mud instead of flame, and the impossible names stay readable.")
        else:
            self.player_action("Break the attackers' nerve loudly enough for the yard to hear.")
            if self.skill_check(self.state.player, "Intimidation", 10, context="to break the Greywake cutters' nerve"):
                hero_bonus += 2
                self.apply_status(enemies[0], "frightened", 1, source="your public challenge")
                self.say("The first cutter looks back toward the road instead of forward toward the wounded. The yard hears fear change sides.")

        outcome = self.run_encounter(
            Encounter(
                title="Greywake Road Breakout",
                description="Ashen Brand cutters try to erase proof and witnesses at Neverwinter's outer triage yard.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=12,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Greywake Yard falls into screaming paperwork and blood, and Neverwinter receives rumor instead of proof.")
            return
        if outcome == "fled":
            self.state.flags["greywake_manifest_destroyed"] = True
            self.state.flags["greywake_mira_evidence_kind"] = "burned_manifest_corner"
            self.state.flags["elira_phandalin_fallback_pending"] = not self.has_companion("Elira Dawnmantle")
            self.add_clue("A burned Greywake manifest corner still shows an outcome mark beside a traveler's name.")
            self.say("You break clear of Greywake before the yard can become a trap, but the manifest burns behind you.")
            self.state.current_scene = "neverwinter_briefing"
            return
        self.state.flags["greywake_breakout_resolved"] = True
        if self.state.flags.get("greywake_manifest_preserved"):
            self.state.flags["greywake_mira_evidence_kind"] = "marked_manifest"
        elif not self.state.flags.get("greywake_mira_evidence_kind"):
            self.state.flags["greywake_mira_evidence_kind"] = "yard_witnesses"
        if not self.has_companion("Elira Dawnmantle"):
            self.state.flags["elira_phandalin_fallback_pending"] = True
        self.reward_party(xp=25, gold=8, reason="holding Greywake Yard before the Neverwinter briefing")
        self.add_journal("You held Greywake Yard long enough to carry its outcome-marked manifest pressure into Mira Thann's briefing.")
        self.state.current_scene = "neverwinter_briefing"

    def resolve_background_encounter(
        self,
        *,
        title: str,
        description: str,
        enemies,
        hero_bonus: int = 0,
        parley_dc: int = 12,
    ) -> bool:
        encounter = Encounter(
            title=title,
            description=description,
            enemies=enemies,
            allow_flee=False,
            allow_parley=True,
            parley_dc=parley_dc,
            hero_initiative_bonus=hero_bonus,
            allow_post_combat_random_encounter=False,
        )
        outcome = self.run_encounter(encounter)
        if outcome == "defeat":
            self.handle_defeat("The opening turns against you before the wider road south can even begin.")
            return False
        return True

    def prologue_default(self) -> None:
        assert self.state is not None
        background = self.state.player.background
        self.background_prologue_header(background)
        self.say(
            "You arrive in Neverwinter carrying the instincts of your old life, and before the day is out someone points you toward "
            "Mira Thann, who is buying competence more quietly than most officers buy noise.",
            typed=True,
        )
        self.finish_background_prologue(
            background,
            "By dusk, those loose directions become a destination: a discreet briefing in Neverwinter about the road to Phandalin.",
        )

    def prologue_soldier(self) -> None:
        assert self.state is not None
        self.background_prologue_header("Soldier")
        self.say(
            "The day begins in shouted counts and buckled straps. A courier from the south arrives bloodied and furious, "
            "and an Ashen Brand runner tries to cut through the mustering yard with dispatches that were never meant to leave it.",
            typed=True,
        )
        choice = self.scenario_choice(
            "How do you respond?",
            [
                self.skill_tag("ATHLETICS", self.action_option("Hit the gate hard before the runner clears the yard.")),
                self.skill_tag("INSIGHT", self.action_option("Read the panic and pick the real escape lane.")),
                self.skill_tag("INTIMIDATION", self.action_option("Lock the teamsters in line and make the thief choose fear over speed.")),
            ],
            allow_meta=False,
        )
        enemies = [create_enemy("bandit", name="Ashen Brand Runner")]
        enemies[0].current_hp = enemies[0].max_hp = 8
        hero_bonus = 0
        if choice == 1:
            self.player_action("Hit the gate hard before the runner clears the yard.")
            if self.skill_check(self.state.player, "Athletics", 11, context="to catch the runner before the lane opens"):
                self.apply_status(self.state.player, "emboldened", 2, source="drilled momentum")
                hero_bonus = 2
                self.say("You turn the breakout into a stand-up fight on your own timing.")
            else:
                self.apply_status(self.state.player, "reeling", 1, source="a rushed impact")
                self.say("You still get there first, but not as cleanly as you wanted.")
        elif choice == 2:
            self.player_action("Read the panic and pick the real escape lane.")
            if self.skill_check(self.state.player, "Insight", 11, context="to identify the true breakout line"):
                enemies[0].current_hp = 5
                hero_bonus = 1
                self.say("You ignore the decoy panic and ruin the runner's best chance to disappear.")
            else:
                self.say("You find the pattern a half-second late and have to recover with steel instead of foresight.")
        else:
            self.player_action("Lock the teamsters in line and make the thief choose fear over speed.")
            if self.skill_check(self.state.player, "Intimidation", 11, context="to bark order into a breaking yard"):
                self.apply_status(enemies[0], "frightened", 2, source="your command voice")
                self.say("The yard remembers discipline before it remembers fear.")
            else:
                self.say("The teamsters move, but panic still keeps the lane ugly.")
        if not self.resolve_background_encounter(
            title="South Barracks Breakout",
            description="An Ashen Brand runner tries to cut through the barracks yard with stolen dispatches.",
            enemies=enemies,
            hero_bonus=hero_bonus,
        ):
            return
        self.reward_party(xp=15, gold=6, reason="holding the barracks line")
        self.finish_background_prologue(
            "Soldier",
            "The recovered dispatch names Mira Thann as the officer quietly gathering capable hands for a harder answer than routine patrols can offer.",
            clue="A stolen dispatch confirms the attacks around Phandalin are organized enough to rattle Neverwinter's quartermasters.",
        )

    def prologue_acolyte(self) -> None:
        assert self.state is not None
        self.background_prologue_header("Acolyte")
        self.say(
            "At the hospice, the road arrives as wounds first and explanation later. A pilgrim wagon limps in with poison in one teamster's veins, "
            "char on the axle wood, and survivors too shaken to tell their story cleanly.",
            typed=True,
        )
        choice = self.scenario_choice(
            "What do you do first?",
            [
                self.skill_tag("MEDICINE", self.action_option("Stabilize the poisoned teamster before the details vanish with them.")),
                self.skill_tag("RELIGION", self.action_option("Lead the room in a sharp, steady prayer instead of letting fear set the pace.")),
                self.skill_tag("NATURE", self.action_option("Read the toxin, claw marks, and scent trail outside the hospice gate.")),
            ],
            allow_meta=False,
        )
        enemies = [create_enemy("wolf")]
        enemies[0].current_hp = enemies[0].max_hp = 8
        if choice == 1:
            self.player_action("Stabilize the poisoned teamster before the details vanish with them.")
            if self.skill_check(self.state.player, "Medicine", 11, context="to keep the poison from closing the throat"):
                self.add_inventory_item("blessed_salve", source="the hospice stores")
                self.say("You buy the patient enough breath to confirm ash-bitter poison and disciplined raiders.")
            else:
                self.say("You keep them alive, but only scraps of the story come back with the breath.")
        elif choice == 2:
            self.player_action("Lead the room in a sharp, steady prayer instead of letting fear set the pace.")
            if self.skill_check(self.state.player, "Religion", 11, context="to turn ritual into usable calm"):
                self.apply_status(self.state.player, "blessed", 3, source="a centered prayer")
                self.say("The prayer leaves you moving through panic with cleaner purpose.")
            else:
                self.say("The words help, but only after fear has already had its first say.")
        else:
            self.player_action("Read the toxin, claw marks, and scent trail outside the hospice gate.")
            if self.skill_check(self.state.player, "Nature", 11, context="to identify what the raiders drove ahead of them"):
                self.apply_status(enemies[0], "reeling", 1, source="tracking its weak angle")
                self.say("The spoor tells you exactly how the beast will circle back.")
            else:
                self.say("The signs are muddied by too many feet, but danger is still moving your way.")
        if not self.resolve_background_encounter(
            title="Hospice Gate",
            description="An ash wolf bolts back toward the hospice, trying to finish the panic the raiders started.",
            enemies=enemies,
        ):
            return
        self.reward_party(xp=15, reason="protecting the hospice gate")
        self.finish_background_prologue(
            "Acolyte",
            "When the worst passes, a temple contact quietly points you toward Mira Thann, who is trying to treat the road south as more than an accounting problem.",
            clue="Survivors from the south speak of poison, disciplined raiders, and attacks designed to terrorize as much as steal.",
        )

    def prologue_criminal(self) -> None:
        assert self.state is not None
        self.background_prologue_header("Criminal")
        self.say(
            "The Blacklake job is supposed to be simple: a fence, a courier, and a satchel full of stolen wagon seals. "
            "Instead, an Ashen Brand collector arrives early and starts talking like everyone in the room already belongs to someone.",
            typed=True,
        )
        choice = self.scenario_choice(
            "How do you play the room?",
            [
                self.skill_tag("DECEPTION", self.action_option("Pose as the collector's actual buyer and turn the meeting sideways.")),
                self.skill_tag("STEALTH", self.action_option("Slip above the warehouse floor and take the satchel before anyone notices.")),
                self.skill_tag("SLEIGHT OF HAND", self.action_option("Lift the ledger and leave the silver where it lies.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Pose as the collector's actual buyer and turn the meeting sideways.")
            if self.skill_check(self.state.player, "Deception", 12, context="to make two criminals distrust each other instead of you"):
                self.reward_party(xp=30, gold=12, reason="turning a dockside deal inside out")
                self.finish_background_prologue(
                    "Criminal",
                    "You walk out with the satchel and one useful name: Mira Thann, the officer quietly tracing where those forged seals keep ending up.",
                    clue="A stolen dockside ledger ties forged caravan seals to Phandalin-bound cargo.",
                )
                return
            self.say("The lie nearly lands, but not cleanly enough to stop steel from coming out.")
        elif choice == 2:
            self.player_action("Slip above the warehouse floor and take the satchel before anyone notices.")
            if self.skill_check(self.state.player, "Stealth", 12, context="to cross the beams without warning the floor below"):
                self.reward_party(xp=30, gold=8, reason="ghosting through the warehouse rafters")
                self.finish_background_prologue(
                    "Criminal",
                    "You vanish into the fog with exactly the sort of evidence Mira Thann has been paying quiet coin to find.",
                    clue="The satchel holds seals meant to mark southbound cargo as safe for Ashen Brand middlemen.",
                )
                return
            self.say("A creaking beam turns the theft into a chase.")
        else:
            self.player_action("Lift the ledger and leave the silver where it lies.")
            if self.skill_check(self.state.player, "Sleight of Hand", 12, context="to steal the real value out from under armed men"):
                self.reward_party(xp=30, gold=10, reason="lifting the ledger out of a live exchange")
                self.finish_background_prologue(
                    "Criminal",
                    "The ledger puts you on the same trail Mira Thann has been following from the lawful side of the city, which is inconvenient but useful.",
                    clue="The ledger shows stolen ore and false caravan papers moving through Blacklake before reaching the road south.",
                )
                return
            self.say("Your fingers are quick, but not quick enough to keep the room from erupting.")
        enemies = [create_enemy("bandit", name="Ashen Brand Collector")]
        enemies[0].current_hp = enemies[0].max_hp = 9
        if not self.resolve_background_encounter(
            title="Blacklake Warehouse",
            description="An Ashen Brand collector finally decides the room would be safer if you stopped breathing.",
            enemies=enemies,
            parley_dc=13,
        ):
            return
        self.reward_party(xp=10, gold=6, reason="surviving the Blacklake warehouse fight")
        self.finish_background_prologue(
            "Criminal",
            "Among the spilled papers is the one name worth following next: Mira Thann, who has begun asking the same questions from a safer side of the law.",
            clue="Blacklake smugglers are laundering forged wagon seals tied to Phandalin cargo.",
        )

    def prologue_sage(self) -> None:
        assert self.state is not None
        self.background_prologue_header("Sage")
        self.say(
            "In the archive, old surveys of Phandalin and cellar plans beneath ruined manors stop looking academic once someone starts stealing only the pages that matter. "
            "A nervous scrivener insists the missing folios vanished just before dawn.",
            typed=True,
        )
        choice = self.scenario_choice(
            "How do you respond?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Follow the corrections, dust, and shelf gaps instead of the panic.")),
                self.skill_tag("ARCANA", self.action_option("Decode the sigils and shorthand in the margins before the thief can profit from them.")),
                self.skill_tag("HISTORY", self.action_option("Reconstruct which ruin-map would matter most to an organized gang.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Follow the corrections, dust, and shelf gaps instead of the panic.")
            success = self.skill_check(self.state.player, "Investigation", 11, context="to catch the thief's route through the archive")
        elif choice == 2:
            self.player_action("Decode the sigils and shorthand in the margins before the thief can profit from them.")
            success = self.skill_check(self.state.player, "Arcana", 11, context="to read the hidden notation in the copied plans")
        else:
            self.player_action("Reconstruct which ruin-map would matter most to an organized gang.")
            success = self.skill_check(self.state.player, "History", 11, context="to identify the ruin line the theft was really after")
        if success:
            self.add_inventory_item("focus_ink", source="a grateful archive keeper")
            self.reward_party(xp=30, reason="untangling the archive theft")
            self.finish_background_prologue(
                "Sage",
                "The archivist sends you straight to Mira Thann, who needs someone able to connect raiders, ruin plans, and frontier logistics into one coherent problem.",
                clue="Archive notes point to old cellar routes beneath manor-side stonework in and around Phandalin.",
            )
            return
        self.say("You solve enough of the pattern to know the theft matters, but not fast enough to stop the getaway cleanly.")
        enemies = [create_enemy("bandit_archer", name="Archive Cutout")]
        enemies[0].current_hp = enemies[0].max_hp = 7
        if not self.resolve_background_encounter(
            title="Archive Stair",
            description="A hired cutout bolts for the service stair with copied ruin plans under one arm.",
            enemies=enemies,
        ):
            return
        self.reward_party(xp=10, reason="recovering the copied plans")
        self.finish_background_prologue(
            "Sage",
            "The copied folios are damaged but readable, and the one official in Neverwinter who will care immediately is Mira Thann.",
            clue="Someone is stealing exactly the plans that would make hidden cellar routes under frontier ruins usable.",
        )

    def prologue_outlander(self) -> None:
        assert self.state is not None
        self.background_prologue_header("Outlander")
        self.say(
            "The camp wakes to the wrong kind of quiet. No birds, fresh spoor, and a cooking fire kicked apart in the dark tell you raiders tested the trail line before sunrise and may still be circling back.",
            typed=True,
        )
        choice = self.scenario_choice(
            "What do you trust first?",
            [
                self.skill_tag("SURVIVAL", self.action_option("Set your ground where the tracks say they will come through.")),
                self.skill_tag("PERCEPTION", self.action_option("Climb high, count movement, and refuse to be surprised.")),
                self.skill_tag("STEALTH", self.action_option("Ghost into the brush and strike from the line they think is empty.")),
            ],
            allow_meta=False,
        )
        enemies = [
            self.intro_pick_enemy(("goblin_skirmisher", "cinder_kobold")),
            self.intro_pick_enemy(("wolf", "mireweb_spider")),
        ]
        enemies[0].current_hp = enemies[0].max_hp = 5
        enemies[1].current_hp = enemies[1].max_hp = 7
        hero_bonus = 0
        if choice == 1:
            self.player_action("Set your ground where the tracks say they will come through.")
            if self.skill_check(self.state.player, "Survival", 11, context="to build the fight on your chosen ground"):
                hero_bonus = 2
                self.say("When they come, they come exactly where your instincts said they would.")
            else:
                self.say("The pattern is there, but not cleanly enough to fully own the opening.")
        elif choice == 2:
            self.player_action("Climb high, count movement, and refuse to be surprised.")
            if self.skill_check(self.state.player, "Perception", 11, context="to catch the circling wolf before it closes"):
                self.apply_status(enemies[1], "surprised", 1, source="your high-ground warning")
                self.say("You spot the wolf's angle early and force the whole approach into the open.")
            else:
                self.say("You see enough to know the danger is real, but not enough to own every angle.")
        else:
            self.player_action("Ghost into the brush and strike from the line they think is empty.")
            if self.skill_check(self.state.player, "Stealth", 11, context="to disappear from the camp's expected defense line"):
                enemies[0].current_hp = 3
                hero_bonus = 1
                self.say("Your first strike lands before the goblin can decide whether this camp is prey or trap.")
            else:
                self.say("The brush hides you until the last second, and then everyone finds everyone at once.")
        if not self.resolve_background_encounter(
            title="Camp at First Light",
            description="A goblin outrider and ash wolf press into camp to test whether the road guides are easy prey.",
            enemies=enemies,
            hero_bonus=hero_bonus,
        ):
            return
        self.reward_party(xp=15, gold=5, reason="breaking the dawn raid")
        self.finish_background_prologue(
            "Outlander",
            "Among the raiders' gear is a scrap pointing toward Phandalin, and before noon a road warden tells you Mira Thann has been trying to get ahead of exactly this pattern.",
            clue="The raiders are probing camps north of Phandalin, not just hitting wagons once they reach the frontier town itself.",
        )

    def prologue_charlatan(self) -> None:
        assert self.state is not None
        self.background_prologue_header("Charlatan")
        self.say(
            "The market loves a polished lie until someone more dangerous than a customer decides your talent is useful. "
            "An Ashen Brand fixer corners you between stalls and offers a choice between quiet employment and louder regret.",
            typed=True,
        )
        choice = self.scenario_choice(
            "How do you answer?",
            [
                self.skill_tag("DECEPTION", self.action_option("Convince the fixer you already work for someone richer and harder to cross.")),
                self.skill_tag("PERFORMANCE", self.action_option("Turn the exchange into a public spectacle the fixer cannot control.")),
                self.skill_tag("INSIGHT", self.action_option("Read what the fixer is really protecting and press there first.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Convince the fixer you already work for someone richer and harder to cross.")
            success = self.skill_check(self.state.player, "Deception", 12, context="to sell a lie dangerous enough to earn caution")
        elif choice == 2:
            self.player_action("Turn the exchange into a public spectacle the fixer cannot control.")
            success = self.skill_check(self.state.player, "Performance", 12, context="to weaponize the crowd's attention")
        else:
            self.player_action("Read what the fixer is really protecting and press there first.")
            success = self.skill_check(self.state.player, "Insight", 12, context="to find the pressure point in the fixer's confidence")
        if success:
            self.reward_party(xp=30, gold=10, reason="turning the market scene your way")
            self.finish_background_prologue(
                "Charlatan",
                "Once the fixer peels off, a watching clerk quietly suggests you share that information with Mira Thann before somebody deadlier turns it into policy.",
                clue="The fixer lets slip that the Ashen Brand is paying well for forged southbound papers and quiet buyers.",
            )
            return
        self.say("The read is close, but not close enough, and the fixer reaches for steel rather than pride.")
        enemies = [create_enemy("bandit", name="Ashen Brand Fixer")]
        enemies[0].current_hp = enemies[0].max_hp = 8
        if not self.resolve_background_encounter(
            title="Market Corner",
            description="The fixer decides a crowded market is still quiet enough for one quick killing blow.",
            enemies=enemies,
        ):
            return
        self.reward_party(xp=10, gold=6, reason="surviving the market confrontation")
        self.finish_background_prologue(
            "Charlatan",
            "The fixer's purse and papers both point toward the same next stop: Mira Thann's private recruiting effort in Neverwinter.",
            clue="Forged identities and caravan papers are part of how the Ashen Brand keeps its trade side alive.",
        )

    def prologue_guild_artisan(self) -> None:
        assert self.state is not None
        self.background_prologue_header("Guild Artisan")
        self.say(
            "The counting-house is a battlefield disguised as a ledger. Too many southbound crates are arriving light, too many teamsters are revising weights after the fact, "
            "and somebody expects the fraud to drown in ordinary confusion.",
            typed=True,
        )
        choice = self.scenario_choice(
            "What do you do first?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Audit the manifests until the missing route shows its shape.")),
                self.skill_tag("PERSUASION", self.action_option("Settle the room and get the teamsters talking plainly.")),
                self.skill_tag("ATHLETICS", self.action_option("Cut off the crate-haulers trying to leave before questions start.")),
            ],
            allow_meta=False,
        )
        enemies = [create_enemy("bandit_archer", name="Ashen Brand Teamster")]
        enemies[0].current_hp = enemies[0].max_hp = 8
        if choice == 1:
            self.player_action("Audit the manifests until the missing route shows its shape.")
            if self.skill_check(self.state.player, "Investigation", 11, context="to catch where the numbers stop being honest"):
                self.add_inventory_item("camp_stew_jar", source="a grateful warehouse master")
                self.reward_party(xp=30, gold=8, reason="breaking the warehouse fraud pattern")
                self.finish_background_prologue(
                    "Guild Artisan",
                    "The master factor sends you to Mira Thann before the next caravan leaves, because somebody needs to fix the road rather than merely price the loss.",
                    clue="Manipulated manifests keep bending southbound cargo toward the same vulnerable approach to Phandalin.",
                )
                return
            self.say("You find the fraud, but not before one culprit tries to bolt with the evidence.")
        elif choice == 2:
            self.player_action("Settle the room and get the teamsters talking plainly.")
            if self.skill_check(self.state.player, "Persuasion", 11, context="to turn a shouting match into usable testimony"):
                self.reward_party(xp=30, gold=6, reason="untangling the teamsters' testimony")
                self.finish_background_prologue(
                    "Guild Artisan",
                    "With the testimony in hand, you are pointed toward Mira Thann, who needs someone that understands how trade panic becomes a weapon.",
                    clue="Multiple teamsters name the same hill watch and the same fear of being singled out on the road to Phandalin.",
                )
                return
            self.say("You settle part of the room, but one liar still decides leaving is safer than talking.")
        else:
            self.player_action("Cut off the crate-haulers trying to leave before questions start.")
            if self.skill_check(self.state.player, "Athletics", 11, context="to block the runaway teamster before the lane opens"):
                self.apply_status(enemies[0], "reeling", 1, source="your shoulder-check")
                self.say("You stop the escape hard enough that the culprit has to fight or talk in the yard.")
            else:
                self.say("You get there only just, and now the lane turns violent instead of orderly.")
        if not self.resolve_background_encounter(
            title="Counting-House Yard",
            description="A compromised teamster tries to flee the warehouse row with altered manifests and a bow at their back.",
            enemies=enemies,
        ):
            return
        self.reward_party(xp=10, gold=4, reason="stopping the warehouse runner")
        self.finish_background_prologue(
            "Guild Artisan",
            "The recovered manifests are enough to interest Mira Thann immediately, because the missing goods are no longer abstract numbers once they start mapping a campaign.",
            clue="Trade sabotage around Neverwinter is being shaped to soften the routes feeding Phandalin.",
        )

    def prologue_hermit(self) -> None:
        assert self.state is not None
        self.background_prologue_header("Hermit")
        self.say(
            "The shrine keeps a quieter watch than any city tower. Before sunrise, a feverish courier collapses near the offerings stone, and the signs around them—drag marks, ash scent, and broken brush—say they were pushed hard for a reason."
        )
        choice = self.scenario_choice(
            "What do you trust first?",
            [
                self.skill_tag("MEDICINE", self.action_option("Stabilize the courier before whatever hunted them closes the distance.")),
                self.skill_tag("NATURE", self.action_option("Read the spoor and choose where the pursuit will break cover.")),
                self.skill_tag("RELIGION", self.action_option("Treat the courier's warning as omen and pattern, not nonsense.")),
            ],
            allow_meta=False,
        )
        enemies = [self.intro_pick_enemy(("goblin_skirmisher", "cinder_kobold"))]
        enemies[0].current_hp = enemies[0].max_hp = 5
        if choice == 1:
            self.player_action("Stabilize the courier before whatever hunted them closes the distance.")
            if self.skill_check(self.state.player, "Medicine", 11, context="to keep the courier conscious long enough to speak clearly"):
                self.add_inventory_item("moonmint_drops", source="the shrine stores")
                self.say("You buy the courier enough clarity to name the watchtower haunting the road south.")
            else:
                self.say("You save their life, but not their full account of the chase.")
        elif choice == 2:
            self.player_action("Read the spoor and choose where the pursuit will break cover.")
            if self.skill_check(self.state.player, "Nature", 11, context="to read the hunter's angle before it becomes an attack"):
                self.apply_status(enemies[0], "surprised", 1, source="your omen-read ground")
                self.say("The trail gives away the pursuer's confidence, and that lets you meet it where it is weakest.")
            else:
                self.say("The signs are real but half-scrubbed, and the pursuer still gets close before you pin them down.")
        else:
            self.player_action("Treat the courier's warning as omen and pattern, not nonsense.")
            if self.skill_check(self.state.player, "Religion", 11, context="to hear meaning inside the courier's fractured warning"):
                self.apply_status(self.state.player, "blessed", 2, source="a hard-won omen")
                self.say("The warning stops sounding random and starts sounding directional.")
            else:
                self.say("The omen stays clouded, and the answer arrives on a blade instead of in words.")
        if not self.resolve_background_encounter(
            title="Wayside Pursuit",
            description="A goblin outrider follows the courier to the shrine, hoping the quiet place will make the finish easier.",
            enemies=enemies,
        ):
            return
        self.reward_party(xp=15, reason="protecting the courier at the shrine")
        self.finish_background_prologue(
            "Hermit",
            "Once the courier is safe enough to hand off, the one name they insist you hear next is Mira Thann's. Whatever stalks the road south has moved beyond omen into open work.",
            clue="A hunted courier names Ashfall Watch as a key pressure point on the road toward Phandalin.",
        )

    def handle_greywake_mira_reaction(self) -> None:
        assert self.state is not None
        if self.state.flags.get("greywake_mira_reacted"):
            return
        if not (
            self.state.flags.get("greywake_breakout_resolved")
            or self.state.flags.get("greywake_manifest_destroyed")
            or self.state.flags.get("greywake_outcome_sorting_seen")
        ):
            return
        evidence_kind = self.state.flags.get("greywake_mira_evidence_kind", "yard_witnesses")
        self.state.flags["greywake_mira_reacted"] = True
        if self.has_companion("Elira Dawnmantle") and (
            self.state.flags.get("elira_pre_neverwinter_recruited") or self.state.flags.get("elira_greywake_recruited")
        ):
            self.speaker(
                "Mira Thann",
                "You found Dawnmantle before I could send anyone for her. Good. That means the road is already worse than my reports.",
            )
        if evidence_kind == "marked_manifest" or self.state.flags.get("greywake_manifest_preserved"):
            self.speaker(
                "Mira Thann",
                "This is not a forged report. This is a schedule.",
            )
            self.add_clue("Mira identifies Greywake's outcome-marked manifest as proof someone is pre-sorting road casualties.")
        elif evidence_kind == "burned_manifest_corner" or self.state.flags.get("greywake_manifest_destroyed"):
            self.speaker(
                "Mira Thann",
                "Then we work from witnesses. Less clean, but sometimes harder to kill.",
            )
            self.add_clue("Mira keeps Greywake witness testimony alive after the outcome-marked manifest burns.")
        elif evidence_kind == "matched_triage_tags":
            self.speaker(
                "Mira Thann",
                "Matching triage tags before the wagons arrived is enough. Someone is not merely attacking the road; they are deciding what the road will produce.",
            )
            self.add_clue("Mira treats the matched Greywake triage tags as proof of pre-sorted road outcomes.")
        else:
            self.speaker(
                "Mira Thann",
                "A yard full of witnesses heard outcome marks read for wagons still on the road. That is not panic. That is a system showing its teeth.",
            )
            self.add_clue("Mira accepts the Greywake witnesses as evidence that someone is pre-sorting road outcomes.")
        if self.state.flags.get("greywake_wounded_line_guarded") or self.state.flags.get("greywake_wounded_stabilized"):
            self.speaker(
                "Mira Thann",
                "People will talk because they lived long enough to be angry.",
            )
            self.add_clue("Greywake survivors can testify because the wounded line lived through the attack.")
        self.add_journal("Mira Thann treated Greywake's outcome marks as concrete proof that the Ashen Brand is coordinating losses, not merely causing them.")

    def mira_dialogue_stage(self) -> str:
        assert self.state is not None
        flags = self.state.flags
        if flags.get("varyn_body_defeated_act1") or flags.get("act1_victory_tier"):
            return "post_act1_return"
        if flags.get("tresendar_cleared") or flags.get("emberhall_revealed"):
            return "late_act1_return"
        if flags.get("ashfall_watch_cleared"):
            return "post_ashfall_return"
        if flags.get("old_owl_well_cleared") or flags.get("wyvern_tor_cleared"):
            return "mid_act1_return"
        if flags.get("phandalin_arrived"):
            return "phandalin_return"
        if flags.get("blackwake_completed") and flags.get("blackwake_return_destination") == "neverwinter":
            return "blackwake_return"
        return "initial_briefing"

    def mira_city_beneficiary_question_available(self) -> bool:
        assert self.state is not None
        return bool(
            self.state.flags.get("neverwinter_private_room_intel")
            or self.state.flags.get("neverwinter_contract_house_political_callback")
            or self.has_quest("false_manifest_circuit")
            or self.quest_is_completed("false_manifest_circuit")
        )

    def mira_need_question_available(self) -> bool:
        assert self.state is not None
        return bool(
            self.state.flags.get("greywake_manifest_preserved")
            or self.state.flags.get("blackwake_completed")
            or self.state.flags.get("elira_pre_neverwinter_recruited")
            or self.state.flags.get("elira_greywake_recruited")
            or self.has_companion("Elira Dawnmantle")
        )

    def mira_initial_question_options(self) -> list[tuple[str, str]]:
        assert self.state is not None
        options: list[tuple[str, str]] = []
        if not self.state.flags.get("briefing_q_neverwinter"):
            options.append(("neverwinter", "\"How is Neverwinter holding together these days?\""))
        if not self.state.flags.get("briefing_q_phandalin"):
            options.append(("phandalin", "\"Tell me what matters most about Phandalin before I ride.\""))
        if not self.state.flags.get("briefing_q_brand"):
            options.append(("brand", "\"How dangerous is this Ashen Brand, really?\""))
        options.extend(self.scene_identity_options("neverwinter_briefing"))
        if not self.state.flags.get("neverwinter_preparation_done"):
            options.append(("prep", self.action_option("Make one more stop in Neverwinter before riding out.")))
        options.append(("inn", self.action_option("Stop by Oren Vale's contract house.")))
        options.append(("leave", self.action_option("Take the writ and head for the High Road.")))
        if self.state.flags.get("greywake_outcome_sorting_seen") and not self.state.flags.get("mira_q_greywake_initial"):
            options.append(("greywake", "\"What do you make of Greywake?\""))
        if (
            (self.state.flags.get("elira_first_contact") or self.has_companion("Elira Dawnmantle"))
            and not self.state.flags.get("mira_q_elira_initial")
        ):
            options.append(("elira", "\"You know Elira Dawnmantle?\""))
        if self.mira_city_beneficiary_question_available() and not self.state.flags.get("mira_q_city_initial"):
            options.append(("city", "\"Who inside the city benefits from this?\""))
        if self.mira_need_question_available() and not self.state.flags.get("mira_q_need_initial"):
            options.append(("need", "\"What do you need from me before I leave?\""))
        return options

    def mira_return_question_options(self, stage: str) -> list[tuple[str, str]]:
        assert self.state is not None
        options: list[tuple[str, str]] = []
        flags = self.state.flags
        if flags.get("blackwake_completed") and not flags.get("mira_q_blackwake_return"):
            options.append(("blackwake_return", "\"Blackwake was worse than a side road.\""))
        if flags.get("phandalin_arrived") and not flags.get("mira_q_phandalin_return"):
            options.append(("phandalin_return", "\"Phandalin is worse than your reports.\""))
        if (
            (flags.get("old_owl_well_cleared") or flags.get("wyvern_tor_cleared"))
            and not flags.get("mira_q_route_sites_return")
        ):
            options.append(("route_sites_return", "\"The outer sites are not random.\""))
        if flags.get("ashfall_watch_cleared") and not flags.get("mira_q_ashfall_return"):
            options.append(("ashfall_return", "\"Ashfall Watch is broken.\""))
        if (flags.get("tresendar_cleared") or flags.get("emberhall_revealed")) and not flags.get("mira_q_cellars_return"):
            options.append(("cellars_return", "\"The manor is not just a ruin.\""))
        if (flags.get("varyn_body_defeated_act1") or flags.get("act1_victory_tier")) and not flags.get("mira_q_act1_after_report"):
            options.append(("act1_after_report", "\"Varyn is beaten.\""))
        if self.mira_city_beneficiary_question_available() and not flags.get("mira_q_city_return"):
            options.append(("city_return", "\"Who inside the city benefits from what we found?\""))
        leave_text = "Return to Phandalin." if flags.get("phandalin_arrived") else "Take the road south."
        options.append(("return_leave", self.action_option(leave_text)))
        return options

    def mira_describe_return_stage_once(self, stage: str) -> None:
        assert self.state is not None
        if stage == "initial_briefing":
            return
        flag = f"mira_return_intro_{stage}"
        if self.state.flags.get(flag):
            return
        self.state.flags[flag] = True
        if stage == "blackwake_return":
            self.say(
                "Mira listens without interrupting. That is worse than impatience. By the time you finish, "
                "she has moved two pins on the map and crossed out one tidy assumption.",
                typed=True,
            )
        elif stage == "phandalin_return":
            self.say(
                "Mira's room has changed while you were south. The old Neverwinter map is still there, but Phandalin now sits "
                "under three pins, two witness strings, and a charcoal note that says: town pressure is not collateral.",
                typed=True,
            )
        elif stage == "mid_act1_return":
            self.say(
                "Mira has cleared more table space for the frontier sites. Old Owl Well, Wyvern Tor, and Cinderfall sit in a rough triangle "
                "around Phandalin like someone was teaching the road where to flinch.",
                typed=True,
            )
        elif stage == "post_ashfall_return":
            self.say(
                "Ashfall Watch is marked in black wax now. Mira has not crossed it off. She has circled what it used to command.",
                typed=True,
            )
        elif stage == "late_act1_return":
            self.say(
                "The map on Mira's wall has moved inward from roads to foundations. Tresendar Manor sits at the center of the newest strings, "
                "as if the road was only the first layer of the wound.",
                typed=True,
            )
        else:
            self.say(
                "Mira hears the final report with the stillness of someone separating victory from explanation. "
                "Phandalin is safer. The route marks are not quiet.",
                typed=True,
            )

    def mira_handle_neverwinter_question(self, *, return_context: bool = False) -> None:
        assert self.state is not None
        if return_context:
            self.state.flags["mira_q_neverwinter_return"] = True
        else:
            self.state.flags["briefing_q_neverwinter"] = True
        self.speaker(
            "Mira Thann",
            "Neverwinter is bruised, not broken. That is the line Lord Neverember prefers, and to be fair, it is not entirely a lie.",
        )
        self.speaker(
            "Mira Thann",
            "The city rebuilds faster than fear can settle. New stone goes up over old ash. Traders come back because profit has a stronger stomach than memory. But roads are how a city proves it is more than walls. If the road to Phandalin fails, every merchant in Neverwinter learns that the frontier can still reach north and take what it wants.",
        )
        if self.state.flags.get("greywake_manifest_preserved"):
            self.speaker("Mira Thann", "And now I have a schedule pretending to be a manifest. That makes this a city problem, not a frontier inconvenience.")
        resolution = self.state.flags.get("blackwake_resolution")
        if self.state.flags.get("blackwake_completed") and resolution == "evidence":
            self.speaker("Mira Thann", "Blackwake proves the rot can stand within sight of Neverwinter's smoke and still call itself road business. I can move on that. Quietly, first. Loudly, if they make me.")
        elif self.state.flags.get("blackwake_completed") and resolution == "rescue":
            self.speaker("Mira Thann", "The rescued teamsters are already changing the story. A city can ignore missing cargo longer than it can ignore people walking home with names, scars, and witnesses.")
        elif self.state.flags.get("blackwake_completed") and resolution == "sabotage":
            self.speaker("Mira Thann", "A burned cache is less useful in court, but useful on the road. Sometimes stopping the next attack matters more than proving the last one.")
        self.speaker(
            "Mira Thann",
            "Because soldiers make a road look occupied, not understood. If I send a column south, the Brand scatters, Phandalin panics, and the person shaping the route learns exactly which pressure made us flinch.",
        )
        self.speaker(
            "Mira Thann",
            "I need capable hands that can move faster than permission and report back before the official version hardens around the wrong lie.",
        )

    def mira_handle_phandalin_question(self, *, return_context: bool = False) -> None:
        assert self.state is not None
        if return_context:
            self.state.flags["mira_q_phandalin_return"] = True
        else:
            self.state.flags["briefing_q_phandalin"] = True
        self.speaker(
            "Mira Thann",
            "Phandalin is a town built by people who know ruins do not stay ruins if someone is stubborn enough. That makes them brave, practical, and terribly vulnerable to anyone who can make tomorrow's bread look less certain than today's fear.",
        )
        self.speaker(
            "Mira Thann",
            "The miners matter. The provisioners matter. The shrine matters more than it admits, because the wounded go there before they go to law. If the Ashen Brand can make those people distrust one another, Phandalin becomes easier to hold without ever being conquered.",
        )
        if self.state.flags.get("steward_vow_made"):
            self.speaker("Mira Thann", "Tessa Harrow will remember a vow. Be careful with that. Frontier towns live on promises, but they also keep score.")
        if self.state.flags.get("phandalin_arrived") and self.state.flags.get("steward_seen"):
            self.speaker("Mira Thann", "Now you have seen Tessa's room. That town is not waiting for rescue. It is arguing over how much of itself it can spend to survive.")
        if self.state.flags.get("stonehill_instigator_unmasked"):
            self.speaker("Mira Thann", "The paid mouth at Stonehill tells me the Brand is attacking the room before the road. That is cheaper than killing a caravan and usually cleaner.")
        elif self.state.flags.get("stonehill_barfight_resolved"):
            self.speaker("Mira Thann", "A brawl in the Stonehill sounds small until you remember that panic is logistics too. A town that cannot share a room cannot hold a gate.")
        self.speaker(
            "Mira Thann",
            "Trust slowly. Tessa Harrow will try to hold the town together even if it costs her sleep and friends. Barthen will know what is missing before the law knows what was stolen. Linene Graywind will notice which weapons arrive late. Elira, if she is there, will tell you who is hurt before she tells you who is guilty.",
        )
        self.speaker("Mira Thann", "And listen at the Stonehill. Inns lie constantly, but they lie in public. That makes the useful ones easier to catch.")

    def mira_handle_brand_question(self, *, return_context: bool = False) -> None:
        assert self.state is not None
        if return_context:
            self.state.flags["mira_q_brand_return"] = True
        else:
            self.state.flags["briefing_q_brand"] = True
        self.speaker("Mira Thann", "Dangerous enough to stop calling them raiders.")
        self.speaker(
            "Mira Thann",
            "Raiders take what is loose. The Ashen Brand is deciding what becomes loose. They pressure miners, bend caravan routes, poison witnesses, and use old ruins like a clerk uses shelves. Someone taught them that fear moves goods as well as horses do.",
        )
        if self.state.flags.get("wayside_false_road_marks_found"):
            self.speaker("Mira Thann", "Those false road marks you found near the shrine matter. The Brand is not only ambushing wagons. It is borrowing the shape of authority long enough to make honest people obey the wrong command.")
        if self.state.flags.get("greywake_outcome_sorting_seen"):
            self.speaker("Mira Thann", "Greywake makes the danger uglier. Someone is not merely predicting losses. They are preparing the road to accept those losses as normal.")
        if self.state.flags.get("old_owl_notes_found") or self.state.flags.get("varyn_filter_logic_seen"):
            self.speaker("Mira Thann", "Old Owl Well adds a filter to the pattern. They are not only choosing targets. They are sorting which kinds of fear travel best.")
        if self.state.flags.get("wyvern_beast_stampede") or self.state.flags.get("varyn_detour_logic_seen"):
            self.speaker("Mira Thann", "Wyvern Tor shows the other hand: force the road to detour, then punish the detour until the detour feels inevitable.")
        if self.state.flags.get("cinderfall_relay_destroyed"):
            self.speaker("Mira Thann", "Cinderfall was a relay, not a camp. That means messages, timing, and fallback orders. You did not just burn a nest. You cut a nerve.")
        self.speaker(
            "Mira Thann",
            "The field name I have is Rukhar Cinderfang, a hobgoblin with enough discipline to make cruelty useful. But Greywake, Blackwake, and the false manifests point above him.",
        )
        self.speaker("Mira Thann", "Do not chase the grand name too early. Find the hand close enough to hurt people today. The larger hand will reach for what it loses.")
        if self.state.flags.get("varyn_route_pattern_seen"):
            self.speaker("Mira Thann", "You have already seen the route pattern. Keep that in mind. Whoever commands this does not think in camps. They think in paths.")

    def mira_handle_greywake_question(self) -> None:
        assert self.state is not None
        self.state.flags["mira_q_greywake_initial"] = True
        self.speaker("Mira Thann", "Greywake is the moment the mask slipped.")
        self.speaker(
            "Mira Thann",
            "A false manifest says somebody lied. An outcome manifest says somebody expected obedience from the future. Treat. Hold. Lost. Those are not clerical mistakes. Those are orders wearing ink.",
        )
        if self.state.flags.get("greywake_manifest_preserved"):
            self.speaker("Mira Thann", "With the manifest intact, I can push quietly at three offices before anyone knows which desk is shaking.")
        if self.state.flags.get("greywake_manifest_destroyed"):
            self.speaker("Mira Thann", "With the manifest gone, I use witnesses. Messier, yes. But a witness can answer a question a page cannot: who looked relieved when the proof burned?")
        if self.state.flags.get("greywake_wounded_line_guarded") or self.state.flags.get("greywake_wounded_stabilized"):
            self.speaker("Mira Thann", "Protecting the wounded line did more than save lives. It preserved memory under pressure.")
        if self.state.flags.get("greywake_yard_steadied"):
            self.speaker("Mira Thann", "Steadying the yard gave me public witnesses. Public witnesses are dangerous to the guilty because they are harder to buy one at a time.")
        self.speaker("Mira Thann", "Yes. Greywake was close to the city because the system is safest to test near the place that trusts paperwork most. Phandalin is where that system becomes hunger, missing tools, and frightened miners.")

    def mira_handle_elira_question(self) -> None:
        assert self.state is not None
        self.state.flags["mira_q_elira_initial"] = True
        if self.has_companion("Elira Dawnmantle"):
            self.speaker(
                "Mira Thann",
                "I know of her. Tymora's clergy tend to look harmless right up until they become the only reason a road still has witnesses.",
            )
            self.speaker(
                "Elira Dawnmantle",
                "Harmless is what people call you when they have never watched you choose who gets the last clean bandage. I prefer useful.",
            )
            self.speaker(
                "Mira Thann",
                "If Dawnmantle chose to walk with you, she saw the same thing I see: the wounded are not aftermath anymore. They are evidence someone keeps trying to erase.",
            )
            self.speaker(
                "Elira Dawnmantle",
                "The wounded are people first. If their pain becomes proof, it is because someone tried to bury them with it.",
            )
        elif self.state.flags.get("elira_phandalin_fallback_pending"):
            self.speaker(
                "Mira Thann",
                "Then she will move with the wounded. If the road lets her reach Phandalin, find her at the shrine. If the road does not, remember that delay has a body count.",
            )
        else:
            self.speaker("Mira Thann", "I know of her. Field clergy like Dawnmantle often become the road's memory before anyone official arrives.")
        trust = self.state.flags.get("elira_initial_trust_reason")
        if trust == "warm_trust":
            self.speaker("Mira Thann", "She trusts hands before speeches. You gave her hands.")
        elif trust == "spiritual_kinship":
            self.speaker("Mira Thann", "Faith that keeps people alive is useful. Faith that only decorates fear is not. Dawnmantle knows the difference.")
        elif trust == "wary_respect":
            self.speaker("Mira Thann", "Wary respect from a field healer is worth more than praise from a comfortable officer.")
        elif trust == "reserved_kindness":
            self.speaker("Mira Thann", "She is kind, but do not confuse that for easy trust. People who work triage learn the cost of every delay.")
        if self.state.flags.get("elira_phandalin_recruited"):
            self.speaker("Mira Thann", "So she waited until the town itself became the patient. That sounds like Dawnmantle. Do not waste what it cost her to leave.")
        if self.has_companion("Elira Dawnmantle"):
            self.speaker(
                "Elira Dawnmantle",
                "Trust me with breath, blood, and bad odds. Do not trust me to bless a lie because it would make the room easier to stand in.",
            )
        self.speaker("Mira Thann", "With a life, yes. With an easy lie, no. That is usually the better arrangement.")

    def mira_handle_city_question(self, *, return_context: bool = False) -> None:
        assert self.state is not None
        self.state.flags["mira_q_city_return" if return_context else "mira_q_city_initial"] = True
        self.speaker("Mira Thann", "Benefit is the wrong first question. Start with who can make the wrong paper look normal.")
        self.speaker(
            "Mira Thann",
            "A wagon master can lose a crate. A corrupt clerk can lose a road. The Ashen Brand needs blades, yes, but blades do not explain why honest teamsters keep obeying bad instructions.",
        )
        if self.quest_is_completed("false_manifest_circuit"):
            self.speaker(
                "Mira Thann",
                "Oren's room, Sabra's manifest, Vessa's buyer phrase, and Garren's roadwarden cadence give me four corners of the same table. Now I can press without guessing where the legs are.",
            )
        if self.state.flags.get("neverwinter_contract_house_blackwake_reported"):
            self.speaker("Mira Thann", "Your Blackwake report gave those witnesses teeth. Before that, they were useful rumors. Now they are pressure.")
        self.speaker("Mira Thann", "I am asking you to bring back facts so clean that the officials expose themselves trying to explain them away.")

    def mira_handle_need_question(self) -> None:
        assert self.state is not None
        self.state.flags["mira_q_need_initial"] = True
        self.speaker(
            "Mira Thann",
            "Three things. Keep the writ visible when it protects civilians. Hide it when it would make you predictable. And do not mistake the loudest threat for the hand that profits from it.",
        )
        self.speaker(
            "Mira Thann",
            "When you reach Phandalin, listen before you promise. A town under pressure will ask for certainty it cannot afford. Give them useful truth instead.",
        )
        if self.state.flags.get("greywake_manifest_preserved"):
            self.speaker("Mira Thann", "Also: keep that schedule close. Anyone who recognizes it too quickly is more useful than they meant to be.")
        if self.state.flags.get("blackwake_completed"):
            self.speaker("Mira Thann", "And if Blackwake follows you south, do not let people call it a side matter. It is the road showing you its teeth early.")
        if self.has_companion("Elira Dawnmantle") and not self.state.flags.get("early_companion_recruited"):
            self.speaker("Mira Thann", "You already have Dawnmantle. I can still assign a scout or shield if you have room, but I will not pretend a roster matters more than the road's own choices.")

    def mira_handle_blackwake_return_question(self) -> None:
        assert self.state is not None
        self.state.flags["mira_q_blackwake_return"] = True
        resolution = self.state.flags.get("blackwake_resolution")
        if resolution == "evidence":
            self.speaker("Mira Thann", "Copied seals, route marks, payment categories. Good. Ugly, but good.")
            self.speaker("Mira Thann", "Evidence lets me hurt the people who thought distance would protect them. Blackwake is close enough to Neverwinter that someone will have to explain why they never smelled the smoke.")
        elif resolution == "rescue":
            self.speaker("Mira Thann", "Survivors first was the right call if you wanted truth with a pulse.")
            self.speaker("Mira Thann", "The ledgers can be replaced. A teamster who saw the handoff can ruin three liars before breakfast.")
        elif resolution == "sabotage":
            self.speaker("Mira Thann", "You broke their rhythm. That buys lives even if it leaves me fewer names.")
            self.speaker("Mira Thann", "I can work with ashes, but ashes do not testify. Next time, if the choice allows it, bring me one living mouth from the other side.")
        else:
            self.speaker("Mira Thann", "Blackwake is too close to the city to dismiss as frontier noise.")
        if self.state.flags.get("blackwake_sereth_fate") == "escaped":
            self.speaker("Mira Thann", "Sereth Vane escaping means the road still has a clever coward in it. Clever cowards are dangerous because they learn.")
        if self.state.flags.get("neverwinter_private_room_intel"):
            self.speaker("Mira Thann", "Oren and Sabra can make this hurt in the city. Vessa will charge us for honesty. Garren will pretend he is not relieved to finally be useful. I can use all of that.")
        self.speaker("Mira Thann", "Go south. Phandalin needs the next answer before Neverwinter finishes arguing over the first.")

    def mira_handle_phandalin_return_question(self) -> None:
        assert self.state is not None
        self.state.flags["mira_q_phandalin_return"] = True
        if self.state.flags.get("steward_seen"):
            self.speaker("Mira Thann", "Tessa Harrow usually sounds tired in writing. If she looked tired in person, assume the town is closer to breaking than she wants Neverwinter to know.")
        if self.state.flags.get("steward_vow_made"):
            self.speaker("Mira Thann", "You made her a vow. Good. Now make it useful. Vows do not feed towns or open roads unless someone turns them into work.")
        resolution = self.state.flags.get("blackwake_resolution")
        if resolution == "rescue":
            self.speaker("Mira Thann", "Rescued teamsters reaching Phandalin changes the town's posture. People fear less stupidly when they know survival has precedent.")
        elif resolution == "evidence":
            self.speaker("Mira Thann", "The Blackwake ledgers will make the merchants angrier than the bodies did. I do not admire that, but I can use it.")
        elif resolution == "sabotage":
            self.speaker("Mira Thann", "The sabotage bought time. Time is only mercy if you spend it before the enemy does.")
        self.speaker(
            "Mira Thann",
            "Not enough. A few writs, a little coin, pressure on the legal offices, and names whispered into the right ears. If I send soldiers now, Neverwinter gets to feel helpful while Phandalin becomes a symbol.",
        )
        self.speaker("Mira Thann", "I would rather it remains a town.")

    def mira_handle_route_sites_return_question(self) -> None:
        assert self.state is not None
        self.state.flags["mira_q_route_sites_return"] = True
        old_owl = self.state.flags.get("old_owl_well_cleared")
        wyvern = self.state.flags.get("wyvern_tor_cleared")
        if old_owl and wyvern:
            self.speaker("Mira Thann", "Old Owl Well and Wyvern Tor are two jaws of the same trap. One teaches fear to linger. The other teaches traffic to move where the Brand wants it.")
        elif old_owl:
            self.speaker("Mira Thann", "Old Owl Well first. Then the Brand is willing to mix old dead things with new logistics. That is either desperation or doctrine. I dislike both.")
        elif wyvern:
            self.speaker("Mira Thann", "Wyvern Tor first. Hill pressure, beast panic, and forced detours. That is a road commander's language.")
        if self.state.flags.get("old_owl_notes_found"):
            self.speaker("Mira Thann", "Those notes matter. They read people as categories, not enemies. That matches Greywake too closely for comfort.")
        if self.state.flags.get("wyvern_beast_stampede"):
            self.speaker("Mira Thann", "A stampede is useful because nobody asks who ordered an animal to panic. Remember that.")
        if self.state.flags.get("hidden_route_unlocked") or self.state.flags.get("cinderfall_ruins_cleared"):
            self.speaker("Mira Thann", "Cinderfall was the missing hinge. Routes do not bend by themselves. Something was relaying the pressure.")
        self.speaker("Mira Thann", "If Phandalin can breathe, cut the relay and the watch becomes less certain. If Phandalin is bleeding now, hit the watch before careful work becomes an elegant excuse.")

    def mira_handle_ashfall_return_question(self) -> None:
        assert self.state is not None
        self.state.flags["mira_q_ashfall_return"] = True
        self.speaker("Mira Thann", "Then the Brand has lost its field spine.")
        self.speaker("Mira Thann", "Do not celebrate too long. A broken spine can still leave teeth behind, and whoever built this operation will start deciding what to abandon.")
        if self.state.flags.get("act1_survivors_saved", 0) >= 2 or self.state.flags.get("greywake_wounded_line_guarded"):
            self.speaker("Mira Thann", "Prisoners who walk home carry better maps than anything you can draw. Let them talk before fear edits them.")
        if self.state.flags.get("cinderfall_relay_destroyed"):
            self.speaker("Mira Thann", "With Cinderfall cut and Ashfall broken, their timing should start to fray. Watch for the mistake they make when orders arrive late.")
        if self.state.flags.get("elira_faith_under_ash_resolved"):
            self.speaker("Mira Thann", "Dawnmantle's mercy will complicate your report. Good. Clean reports usually mean someone left people out.")
        self.speaker("Mira Thann", "Now they stop pretending the road is the battlefield. They will pull inward, toward the places under Phandalin where fear has walls.")

    def mira_handle_cellars_return_question(self) -> None:
        assert self.state is not None
        self.state.flags["mira_q_cellars_return"] = True
        self.speaker("Mira Thann", "No. It is a mouth.")
        self.speaker(
            "Mira Thann",
            "Old stone gives criminals privacy. Older stone gives worse things patience. If the Brand used Tresendar as more than shelter, then Phandalin has been standing over part of the answer since the beginning.",
        )
        route = self.state.flags.get("tresendar_nothic_route")
        if route == "kill":
            self.speaker("Mira Thann", "You killed the thing in the dark. That is sometimes the only clean sentence a report gets.")
        elif route == "trade":
            self.speaker("Mira Thann", "You traded with it. I will not scold you until I know whether the price follows you home.")
        elif route == "deceive":
            self.speaker("Mira Thann", "You lied to a thing built to eat truths. Brave, foolish, or useful. I will decide after you survive the consequences.")
        if self.state.flags.get("tresendar_nothic_wave_echo_lore"):
            self.speaker("Mira Thann", "Wave Echo again. That name keeps appearing where ordinary banditry should have run out of imagination.")
        self.speaker("Mira Thann", "Officially? No. Unofficially? You are already the intervention.")

    def mira_handle_act1_after_report_question(self) -> None:
        assert self.state is not None
        self.state.flags["mira_q_act1_after_report"] = True
        if self.state.flags.get("varyn_route_displaced"):
            self.speaker("Mira Thann", "Beaten, yes. Finished, I am less sure.")
            self.speaker("Mira Thann", "Bodies are usually persuasive. Routes that fold wrong are not usually interested in persuasion.")
        tier = self.state.flags.get("act1_victory_tier")
        if tier == "clean_victory":
            self.speaker("Mira Thann", "Phandalin will get to call this a victory without choking on the word. That is rare. Let them have it.")
        elif tier == "costly_victory":
            self.speaker("Mira Thann", "The road is open, but nobody south of here will mistake open for healed. Costly victories still count. They also send invoices.")
        elif tier == "fractured_victory":
            self.speaker("Mira Thann", "You won. I believe that. I also believe Phandalin will spend months learning what the word cost.")
        if self.state.flags.get("emberhall_impossible_exit_seen"):
            self.speaker("Mira Thann", "Tell me again about the exit that should not have worked. Slowly. That may be the first honest sentence in this whole affair.")
        self.speaker("Mira Thann", "Publicly, we praise brave locals, condemn organized banditry, and send repair money late enough to insult everyone.")
        self.speaker("Mira Thann", "Privately, I start tracking every route that behaved like it had a memory. The next enemy may not call itself the Ashen Brand. It may not need to.")

    def mira_handle_question(self, selection_key: str, stage: str) -> bool:
        if selection_key == "neverwinter":
            self.mira_handle_neverwinter_question()
            return True
        if selection_key == "phandalin":
            self.mira_handle_phandalin_question()
            return True
        if selection_key == "brand":
            self.mira_handle_brand_question()
            return True
        if selection_key == "greywake":
            self.mira_handle_greywake_question()
            return True
        if selection_key == "elira":
            self.mira_handle_elira_question()
            return True
        if selection_key == "city":
            self.mira_handle_city_question()
            return True
        if selection_key == "need":
            self.mira_handle_need_question()
            return True
        if selection_key == "blackwake_return":
            self.mira_handle_blackwake_return_question()
            return True
        if selection_key == "phandalin_return":
            self.mira_handle_phandalin_return_question()
            return True
        if selection_key == "route_sites_return":
            self.mira_handle_route_sites_return_question()
            return True
        if selection_key == "ashfall_return":
            self.mira_handle_ashfall_return_question()
            return True
        if selection_key == "cellars_return":
            self.mira_handle_cellars_return_question()
            return True
        if selection_key == "act1_after_report":
            self.mira_handle_act1_after_report_question()
            return True
        if selection_key == "city_return":
            self.mira_handle_city_question(return_context=True)
            return True
        return False

    def mira_leave_return_briefing(self) -> None:
        assert self.state is not None
        if self.state.flags.get("phandalin_arrived"):
            self.return_to_phandalin("You leave Mira's counting room and take the long road back to Phandalin's unfinished arguments.")
            return
        self.handle_neverwinter_departure_fork()

    def scene_neverwinter_briefing(self) -> None:
        assert self.state is not None
        self.banner("Act I: Ashes on the Triboar Trail")
        stage = self.mira_dialogue_stage()
        if not self.state.flags.get("briefing_seen"):
            self.say(
                "Warm mist drifts off the Neverwinter River as you enter the Jewel of the North. Even after the devastation tied to "
                "Mount Hotenow, craftsmen, traders, and laborers keep the city rebuilding itself with stubborn pride. Mira has borrowed "
                "a counting room above the river warehouses, though nothing in it is being counted honestly anymore.",
                typed=True,
            )
            self.speaker(
                "Mira Thann",
                "Caravans bound for Phandalin have vanished, miners are being shaken down, and a new gang calling itself the Ashen Brand is using the frontier's old ruins for cover. That was the simple version before you walked in.",
            )
            self.state.flags["briefing_seen"] = True
        else:
            self.mira_describe_return_stage_once(stage)
        self.handle_greywake_mira_reaction()

        while True:
            stage = self.mira_dialogue_stage()
            options = (
                self.mira_initial_question_options()
                if stage == "initial_briefing"
                else self.mira_return_question_options(stage)
            )
            choice = self.scenario_choice("Choose your response to Mira.", [text for _, text in options])
            selection_key, selection = options[choice - 1]
            if selection_key.startswith(("class:", "race:")):
                if self.handle_scene_identity_action("neverwinter_briefing", selection_key):
                    continue
            self.player_choice_output(selection)
            if self.mira_handle_question(selection_key, stage):
                continue
            if selection_key == "prep":
                self.handle_neverwinter_prep()
            elif selection_key == "inn":
                self.visit_neverwinter_contract_house()
            elif selection_key == "return_leave":
                self.mira_leave_return_briefing()
                return
            else:
                self.handle_neverwinter_departure_fork()
                return

    def handle_neverwinter_prep(self) -> None:
        assert self.state is not None
        choice = self.scenario_choice(
            "Pick one last preparation before you leave Neverwinter.",
            [
                self.quoted_option("INVESTIGATION", "Let me review the missing caravan ledgers."),
                self.quoted_option("RELIGION", "I want a blessing and road-prayer before I leave."),
                self.quoted_option("PERSUASION", "Point me to the teamsters and dockhands. Rumors travel fast."),
                self.action_option("Skip the detour and ride now."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            success = self.skill_check(self.state.player, "Investigation", 12, context="to piece together the caravan trail")
            if success:
                self.state.flags["system_profile_seeded"] = True
                self.state.flags["varyn_route_pattern_seen"] = True
                self.say("The ledger gaps stop looking random and start forming a route pattern with one ugly choke point in common.")
                self.add_clue("Caravan ledgers point to repeated disappearances near the old switchback east of Phandalin.")
                self.reward_party(xp=15, gold=8, reason="reviewing caravan ledgers")
            else:
                self.say("The ledgers are too incomplete and hastily corrected to yield more than suspicion.")
        elif choice == 2:
            success = self.skill_check(self.state.player, "Religion", 12, context="to center yourself with a road prayer")
            self.add_inventory_item("potion_healing", source="the Neverwinter temple")
            if success:
                self.say("The prayer settles over you cleanly, and for a moment the road ahead feels chosen rather than feared.")
                self.reward_party(xp=10, reason="seeking a blessing before the road")
            else:
                self.say("The words do not quite settle, but the ritual still steadies your breathing before departure.")
            self.say("A temple acolyte presses an extra healing draught into your hands before you leave.")
        elif choice == 3:
            success = self.skill_check(self.state.player, "Persuasion", 12, context="to loosen anxious tongues on the docks")
            if success:
                self.say("Once one dockhand starts talking, the rest fill in the gaps with the kind of details only workers notice.")
                self.add_clue("Dockside rumors say the Ashen Brand sells stolen ore through quiet middlemen.")
                self.reward_party(xp=15, gold=12, reason="working the rumor mill")
            else:
                self.say("The dockworkers stay guarded, but a few half-finished warnings still leave you with something useful to carry south.")
                self.reward_party(gold=4, reason="working the rumor mill")
        else:
            self.say("You keep your focus on the road ahead.")
        self.state.flags["neverwinter_preparation_done"] = True

    def visit_neverwinter_contract_house(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("neverwinter_contract_house_seen"):
            self.state.flags["neverwinter_contract_house_seen"] = True
            self.banner("Oren Vale's Contract House")
            self.say(
                "Half inn, half contracting room, the house sits off the river road where teamsters, wardens, and quiet fixers can all pretend they are only here for stew. "
                "No one raises their voice unless they mean to buy the room with it.",
                typed=True,
            )
            self.speaker(
                "Oren Vale",
                "If Mira sent you, then you are either early, in trouble, or smart enough to know those can all look the same from across a table.",
            )
        while True:
            self.refresh_quest_statuses(announce=False)
            if self.state.flags.get("neverwinter_ash_in_the_ale_ready"):
                self.neverwinter_resolve_ash_in_the_ale()
                continue
            options: list[tuple[str, str]] = []
            if self.state.flags.get("quest_reward_neverwinter_private_room_access") and not self.state.flags.get("neverwinter_private_room_scene_done"):
                options.append(("private_room", self.action_option("Take Oren's offer and use the upstairs private room.")))
            options.extend(
                [
                    ("oren", "\"Oren Vale looks like he already priced this conversation.\""),
                    ("sabra", "\"Let me see the ledgers Sabra Kestrel keeps glaring at.\""),
                    ("vessa", "\"Sit in on Vessa Marr's card table.\""),
                    ("garren", "\"Ask Garren Flint how false roadwarden seals keep getting obeyed.\""),
                    ("rest", self.action_option("Rent beds upstairs (10 gp per active party member).")),
                    ("leave", self.action_option("Leave the contract house and return to Mira's rooms.")),
                ]
            )
            choice = self.scenario_choice(
                "The contract house room keeps three conversations going at once.",
                [text for _, text in options],
                allow_meta=False,
            )
            selection_key, _ = options[choice - 1]
            if selection_key == "private_room":
                self.neverwinter_use_private_room()
            elif selection_key == "oren":
                self.neverwinter_talk_oren()
            elif selection_key == "sabra":
                self.neverwinter_talk_sabra()
            elif selection_key == "vessa":
                self.neverwinter_talk_vessa()
            elif selection_key == "garren":
                self.neverwinter_talk_garren()
            elif selection_key == "rest":
                self.paid_inn_long_rest("Oren Vale's contract house")
            else:
                self.player_action("You leave the contract house and head back toward Mira's borrowed briefing rooms.")
                return

    def neverwinter_talk_oren(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("neverwinter_oren_met"):
            self.state.flags["neverwinter_oren_met"] = True
            self.speaker(
                "Oren Vale",
                "I do not mind dangerous people. I mind loud ones. Dangerous and quiet can still finish a meal.",
            )
        while True:
            self.refresh_quest_statuses(announce=False)
            options: list[tuple[str, str]] = []
            if self.has_quest("false_manifest_circuit") and not self.state.flags.get("false_manifest_oren_detail"):
                options.append(
                    (
                        "detail",
                        self.skill_tag(
                            "INSIGHT",
                            self.action_option("Ask which room booking was written by someone expecting never to be checked."),
                        ),
                    )
                )
            if not self.state.flags.get("neverwinter_oren_room_asked"):
                options.append(("room", "\"What kind of business hides in a room like this?\""))
            if not self.state.flags.get("neverwinter_oren_mira_asked"):
                options.append(("mira", "\"What does Mira actually buy from you besides quiet tables?\""))
            if self.state.flags.get("quest_reward_neverwinter_private_room_access") and not self.state.flags.get("neverwinter_private_room_scene_done"):
                options.append(("access", self.action_option("Ask whether the upstairs room is ready.")))
            options.append(("leave", self.action_option("Leave Oren to his careful hospitality.")))
            choice = self.scenario_choice("Choose what you say to Oren Vale.", [text for _, text in options], allow_meta=False)
            selection_key, _ = options[choice - 1]
            if selection_key == "detail":
                self.player_action("Ask which room booking was written by someone expecting never to be checked.")
                if self.skill_check(self.state.player, "Insight", 12, context="to hear which contract-house booking line belongs to a practiced liar"):
                    self.state.flags["false_manifest_oren_detail"] = True
                    self.add_clue("Oren remembers one false booking line that paid cash, used no baggage, and referenced a river-cut pickup the room should not have known.")
                    self.speaker(
                        "Oren Vale",
                        "Room Seven. No luggage, paid too neatly, and asked after a wagon that had not yet officially gone missing. That is not a guest. That is a correction waiting to happen.",
                    )
                else:
                    self.speaker("Oren Vale", "Closer. The lie is in the confidence, not the handwriting.")
            elif selection_key == "room":
                self.state.flags["neverwinter_oren_room_asked"] = True
                self.player_speaker("What kind of business hides in a room like this?")
                self.speaker(
                    "Oren Vale",
                    "Mostly the sort that wants a witness without wanting a crowd. Contracts, reconciliations, and people deciding whether a bad truth is cheaper than a useful lie.",
                )
            elif selection_key == "mira":
                self.state.flags["neverwinter_oren_mira_asked"] = True
                self.player_speaker("What does Mira actually buy from you besides quiet tables?")
                self.speaker(
                    "Oren Vale",
                    "A place where frightened professionals can tell the truth before they remember who signs their wages. Cities are held together by beams, coin, and one room like this per district.",
                )
            elif selection_key == "access":
                self.player_action("Ask whether the upstairs room is ready.")
                self.speaker(
                    "Oren Vale",
                    "You bought enough truth to merit better walls. Use the back room before somebody poorer in judgment realizes what Sabra just learned.",
                )
                self.neverwinter_use_private_room()
                return
            else:
                self.player_action("You leave Oren to his careful hospitality.")
                return

    def neverwinter_talk_sabra(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("neverwinter_sabra_met"):
            self.state.flags["neverwinter_sabra_met"] = True
            self.speaker(
                "Sabra Kestrel",
                "Missing cargo would bother me less if it stayed missing honestly. These ledgers are being corrected by someone who expects not to be checked.",
            )
        while True:
            self.refresh_quest_statuses(announce=False)
            options: list[tuple[str, str]] = []
            if self.quest_is_ready("false_manifest_circuit"):
                options.append(("turn_in", self.action_option("Bring Sabra the contract-house lies you untangled.")))
            elif not self.has_quest("false_manifest_circuit") and not self.quest_is_completed("false_manifest_circuit"):
                options.append(("quest", "\"Which ledger line is wrong enough to matter before I ride?\""))
            else:
                options.append(("reminder", "\"Whose detail are you still missing from the manifest line?\""))
            if not self.state.flags.get("neverwinter_sabra_fear_asked"):
                options.append(("fear", "\"Which caravan frightens you most?\""))
            options.append(("leave", self.action_option("Leave Sabra to her ledgers and ink stains.")))
            choice = self.scenario_choice("Choose what you say to Sabra Kestrel.", [text for _, text in options], allow_meta=False)
            selection_key, _ = options[choice - 1]
            if selection_key == "turn_in":
                self.player_action("Bring Sabra the contract-house lies you untangled.")
                if self.turn_in_quest("false_manifest_circuit", giver="Sabra Kestrel"):
                    self.speaker(
                        "Oren Vale",
                        "Upstairs room. Back stair. Take the cleaner bottle with you, not the brighter one.",
                    )
            elif selection_key == "quest":
                self.player_speaker("Which ledger line is wrong enough to matter before I ride?")
                self.speaker(
                    "Sabra Kestrel",
                    "Three different liars corrected the same caravan in three different directions: one at the rail, one at the cards, and one in the road cadence. Bring me those three truths and I can name the false manifest circuit before it reaches the south road.",
                )
                self.grant_quest(
                    "false_manifest_circuit",
                    note="Sabra wants the contract house's three cleanest tells cross-checked before the forged manifest line reaches the High Road.",
                )
            elif selection_key == "reminder":
                missing: list[str] = []
                if not self.state.flags.get("false_manifest_oren_detail"):
                    missing.append("Oren")
                if not self.state.flags.get("false_manifest_vessa_detail"):
                    missing.append("Vessa")
                if not self.state.flags.get("false_manifest_garren_detail"):
                    missing.append("Garren")
                self.player_speaker("Whose detail are you still missing from the manifest line?")
                if missing:
                    self.speaker(
                        "Sabra Kestrel",
                        f"Oren, Vessa, and Garren are each holding one clean piece of the lie. Still missing: {', '.join(missing)}.",
                    )
                else:
                    self.speaker(
                        "Sabra Kestrel",
                        "That is the whole shape of it, then. Bring it back before the room talks itself into forgetting how obvious it now feels.",
                    )
            elif selection_key == "fear":
                self.state.flags["neverwinter_sabra_fear_asked"] = True
                self.player_speaker("Which caravan frightens you most?")
                self.speaker(
                    "Sabra Kestrel",
                    "The one marked as delayed before it even left the river cut. Real danger misses schedules. Only people with paper confidence prewrite loss that neatly.",
                )
                self.add_clue("Sabra has a Neverwinter manifest showing one caravan marked delayed before departure, which means somebody north of the High Road is prewriting losses.")
            else:
                self.player_action("You leave Sabra to her ledgers and ink stains.")
                return

    def neverwinter_talk_vessa(self) -> None:
        assert self.state is not None
        has_blessing = self.has_story_skill_modifier(self.state.player, self.LIARS_BLESSING_MODIFIER_ID)
        if not self.state.flags.get("neverwinter_vessa_met"):
            self.state.flags["neverwinter_vessa_met"] = True
            self.speaker(
                "Vessa Marr",
                "Everyone lies at cards. The interesting part is what they choose not to lie about.",
            )
        while True:
            self.refresh_quest_statuses(announce=False)
            options: list[tuple[str, str]] = []
            if self.has_quest("false_manifest_circuit") and not self.state.flags.get("false_manifest_vessa_detail"):
                options.append(
                    (
                        "detail",
                        self.skill_tag(
                            "INSIGHT",
                            self.action_option("Watch which seal-color makes Vessa stop joking for half a breath."),
                        ),
                    )
                )
            if not self.state.flags.get("neverwinter_vessa_cards_played"):
                options.append(("cards", self.quoted_option("SLEIGHT OF HAND", "Sit for one hand and make the table show its tells.")))
            if has_blessing and not self.state.flags.get("neverwinter_smuggler_phrase_known"):
                options.append(
                    (
                        "blessing",
                        self.skill_tag(
                            "LIAR'S BLESSING",
                            self.action_option("Name the false buyer Vessa is expecting and let the table correct you."),
                        ),
                    )
                )
            if not self.state.flags.get("neverwinter_vessa_smoke_asked"):
                options.append(("smoke", "\"What does the river-cut smoke mean to the people who profit from it?\""))
            options.append(("leave", self.action_option("Leave Vessa Marr to the cards and the marks.")))
            choice = self.scenario_choice("Choose what you say to Vessa Marr.", [text for _, text in options], allow_meta=False)
            selection_key, _ = options[choice - 1]
            if selection_key == "detail":
                self.player_action("Watch which seal-color makes Vessa stop joking for half a breath.")
                if self.skill_check(self.state.player, "Insight", 12, context="to catch Vessa's one honest reaction at the card table"):
                    self.state.flags["false_manifest_vessa_detail"] = True
                    self.state.flags["blackwake_millers_ford_lead"] = True
                    self.speaker(
                        "Vessa Marr",
                        "Blue wax on a river manifest means the cargo never plans to meet a real roadwarden. That color is for men who only want the look of authority long enough to wave a wagon sideways.",
                    )
                else:
                    self.speaker("Vessa Marr", "Pretty read. Wrong heartbeat.")
            elif selection_key == "cards":
                self.state.flags["neverwinter_vessa_cards_played"] = True
                self.player_speaker("Sit for one hand and make the table show its tells.")
                if self.skill_check(self.state.player, "Sleight of Hand", 12, context="to stay ahead of Vessa's card table without becoming the room's punchline"):
                    self.state.flags["neverwinter_smuggler_phrase_known"] = True
                    self.reward_party(xp=10, gold=8, reason="surviving Vessa Marr's card table")
                    self.speaker(
                        "Vessa Marr",
                        "Not bad. Since you earned it: if somebody says the load is 'rain-marked,' they mean it already belongs to a forged inspection line.",
                    )
                else:
                    self.say("A loaded cup hits the wall before the hand is even fully called. Too many bruised egos decide they would rather be righteous than lucky.")
                    self.state.flags["neverwinter_ash_in_the_ale_ready"] = True
                    return
            elif selection_key == "blessing":
                self.player_action("Name the false buyer Vessa is expecting and let the table correct you.")
                self.state.flags["neverwinter_smuggler_phrase_known"] = True
                self.reward_party(xp=10, gold=4, reason="turning Liar's Blessing into a card-table passphrase")
                self.speaker(
                    "Vessa Marr",
                    "Rain-marked? Gods, no. That phrase would get you robbed in three districts. The real buyers ask whether the load is blue before they ask whether it is legal.",
                )
            elif selection_key == "smoke":
                self.state.flags["neverwinter_vessa_smoke_asked"] = True
                self.state.flags["blackwake_millers_ford_lead"] = True
                self.player_speaker("What does the river-cut smoke mean to the people who profit from it?")
                self.speaker(
                    "Vessa Marr",
                    "That somebody north of Miller's Ford got impatient. Smoke there means papers burned before witnesses could read them, which means the survivors will be worth more than the cargo for a day or two.",
                )
            else:
                self.player_action("You leave Vessa Marr to the cards and the marks.")
                return

    def neverwinter_talk_garren(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("neverwinter_garren_met"):
            self.state.flags["neverwinter_garren_met"] = True
            self.speaker(
                "Garren Flint",
                "A fake seal only works if honest people are already tired enough to obey it.",
            )
        while True:
            self.refresh_quest_statuses(announce=False)
            options: list[tuple[str, str]] = []
            if self.has_quest("false_manifest_circuit") and not self.state.flags.get("false_manifest_garren_detail"):
                options.append(
                    (
                        "detail",
                        self.skill_tag(
                            "PERSUASION",
                            self.action_option("Ask what a real roadwarden would never write on an honest stop order."),
                        ),
                    )
                )
            if not self.state.flags.get("neverwinter_garren_route_asked"):
                options.append(("route", "\"How are the false seals getting traction at all?\""))
            if not self.state.flags.get("neverwinter_garren_pressed"):
                options.append(("pressure", self.quoted_option("INTIMIDATION", "Stop protecting whoever taught the Brand your cadence.")))
            options.append(("leave", self.action_option("Leave Garren Flint to his cooling temper.")))
            choice = self.scenario_choice("Choose what you say to Garren Flint.", [text for _, text in options], allow_meta=False)
            selection_key, _ = options[choice - 1]
            if selection_key == "detail":
                self.player_action("Ask what a real roadwarden would never write on an honest stop order.")
                if self.skill_check(self.state.player, "Persuasion", 12, context="to get Garren to share the wrong cadence in the false orders"):
                    self.state.flags["false_manifest_garren_detail"] = True
                    self.state.flags["road_patrol_writ"] = True
                    self.speaker(
                        "Garren Flint",
                        "No one who ever stood a freezing checkpoint says 'detain pending courtesy review.' That is clerk language wearing a guard's boots. If you see it, the paper is poison.",
                    )
                else:
                    self.speaker("Garren Flint", "Ask me cleaner when the room sounds less thirsty for a spectacle.")
            elif selection_key == "route":
                self.state.flags["neverwinter_garren_route_asked"] = True
                self.state.flags["blackwake_gallows_copse_lead"] = True
                self.player_speaker("How are the false seals getting traction at all?")
                self.speaker(
                    "Garren Flint",
                    "Because the real road has been tired for months. Too many hungry hands, not enough clean patrols, and one copied seal is all panic needs before it starts obeying the wrong man.",
                )
            elif selection_key == "pressure":
                self.state.flags["neverwinter_garren_pressed"] = True
                self.player_speaker("Stop protecting whoever taught the Brand your cadence.")
                if self.skill_check(self.state.player, "Intimidation", 12, context="to force the truth past Garren's pride without breaking the room"):
                    self.state.flags["blackwake_gallows_copse_lead"] = True
                    self.speaker(
                        "Garren Flint",
                        "Gallows Copse. That is where I would look if I were trying to copy a patrol line without meeting the patrol itself. There. I have said enough in public for one week.",
                    )
                else:
                    self.say("A chair scrapes back too hard. One teamster thinks Garren has been accused of the thing he merely failed to stop, and the room starts choosing sides faster than sense can keep up.")
                    self.state.flags["neverwinter_ash_in_the_ale_ready"] = True
                    return
            else:
                self.player_action("You leave Garren Flint to his cooling temper.")
                return

    def neverwinter_resolve_ash_in_the_ale(self) -> None:
        assert self.state is not None
        self.state.flags["neverwinter_ash_in_the_ale_ready"] = False
        self.banner("Ash In The Ale")
        self.say(
            "A cup bursts against the wall hard enough to silence three nearby tables. One teamster is on his feet, another swears the cards or the road-talk were rigged, and the whole room has started deciding whose embarrassment deserves help.",
            typed=True,
        )
        choice = self.scenario_choice(
            "The contract house tilts toward a fight. What do you do?",
            [
                self.skill_tag("PERSUASION", self.action_option("Make them sit before pride turns into blood.")),
                self.skill_tag("INSIGHT", self.action_option("Name the real liar before the loudest fool gets to define the room.")),
                self.skill_tag("SLEIGHT OF HAND", self.action_option("Make the loaded cup and marked die disappear at the same time.")),
                self.skill_tag("INTIMIDATION", self.action_option("Freeze the room with one promise nobody wants tested.")),
                self.skill_tag("ATHLETICS", self.action_option("Step between them and catch the first shove cleanly.")),
                self.action_option("Let the room settle itself."),
            ],
            allow_meta=False,
        )
        success = False
        if choice == 1:
            self.player_action("Make them sit before pride turns into blood.")
            success = self.skill_check(self.state.player, "Persuasion", 12, context="to stop the contract-house fight before the room takes a side")
        elif choice == 2:
            self.player_action("Name the real liar before the loudest fool gets to define the room.")
            success = self.skill_check(self.state.player, "Insight", 12, context="to call out the actual liar in the contract-house flare-up")
        elif choice == 3:
            self.player_action("Make the loaded cup and marked die disappear at the same time.")
            success = self.skill_check(self.state.player, "Sleight of Hand", 12, context="to remove the room's excuse for violence before anyone notices your hand")
        elif choice == 4:
            self.player_action("Freeze the room with one promise nobody wants tested.")
            success = self.skill_check(self.state.player, "Intimidation", 12, context="to cow the contract-house room back into its chairs")
        elif choice == 5:
            self.player_action("Step between them and catch the first shove cleanly.")
            success = self.skill_check(self.state.player, "Athletics", 12, context="to absorb the first tavern shove and own the space after it")
        else:
            self.player_action("Let the room settle itself.")
        self.state.flags["neverwinter_ash_in_the_ale_resolved"] = True
        if success:
            self.state.flags["neverwinter_oren_trust"] = int(self.state.flags.get("neverwinter_oren_trust", 0)) + 1
            self.state.flags["blackwake_neverwinter_rumor"] = True
            self.reward_party(xp=15, gold=6, reason="settling the contract-house flare-up before it became a brawl")
            self.speaker(
                "Oren Vale",
                "Useful. A room that trusts you after a near-fight will tell you more truth than a polite one ever does.",
            )
            self.say("The noise ebbs. Somebody laughs from pure relief, and the contract house goes back to pretending it is only an inn.")
        else:
            self.apply_status(self.state.player, "reeling", 1, source="the contract-house brawl")
            self.say("The room resolves itself with scraped knuckles, overturned cups, and one hard shove that reminds you why Oren charges for quiet.")

    def neverwinter_use_private_room(self) -> None:
        assert self.state is not None
        self.banner("Upstairs Contract Room")
        self.say(
            "Upstairs, Oren closes the door on the common room and Sabra spreads corrected manifests beside a guest register that was never meant to leave the desk. Politics gets smaller in rooms like this, but never cleaner.",
            typed=True,
        )
        has_blessing = self.has_story_skill_modifier(self.state.player, self.LIARS_BLESSING_MODIFIER_ID)
        options: list[tuple[str, str]] = [
            (
                "investigation",
                self.skill_tag(
                    "INVESTIGATION",
                    self.action_option("Lay the corrected manifests over the room register and follow the one hand that lies the same way in both."),
                ),
            ),
            (
                "insight",
                self.skill_tag(
                    "INSIGHT",
                    self.action_option("Read which missing caravan line Sabra keeps watching when she thinks nobody sees."),
                ),
            ),
            (
                "persuasion",
                self.skill_tag(
                    "PERSUASION",
                    self.action_option("Get Oren to name which patron buys privacy and never uses the same need twice."),
                ),
            ),
        ]
        if has_blessing:
            options.append(
                (
                    "blessing",
                    self.skill_tag(
                        "LIAR'S BLESSING",
                        self.action_option("Offer the wrong contract phrase and wait for the room to correct you."),
                    ),
                )
            )
        choice = self.scenario_choice("How do you read the upstairs contract room?", [text for _, text in options], allow_meta=False)
        selection_key, _ = options[choice - 1]
        reward_xp = 10
        if selection_key == "investigation":
            self.player_action("Lay the corrected manifests over the room register and follow the one hand that lies the same way in both.")
            if self.skill_check(self.state.player, "Investigation", 12, context="to line up Sabra's manifests with Oren's quiet-room register"):
                reward_xp = 15
                self.state.flags["blackwake_millers_ford_lead"] = True
                self.state.flags["road_patrol_writ"] = True
                self.say("The same clerkly hesitation appears in both ledgers: one hand writing authority it has never personally carried.")
            else:
                self.say("The overlap is real, but the room gives up only the broad shape of it before the details blur together.")
        elif selection_key == "insight":
            self.player_action("Read which missing caravan line Sabra keeps watching when she thinks nobody sees.")
            if self.skill_check(self.state.player, "Insight", 12, context="to read Sabra's fear past the ledger ink"):
                reward_xp = 15
                self.state.flags["blackwake_neverwinter_rumor"] = True
                self.say("Sabra never watches the most expensive cargo line. She watches the one that disappeared before it was supposed to exist on paper at all.")
            else:
                self.say("You catch the fear, if not the neatest explanation behind it.")
        elif selection_key == "persuasion":
            self.player_action("Get Oren to name which patron buys privacy and never uses the same need twice.")
            if self.skill_check(self.state.player, "Persuasion", 12, context="to get Oren to share the upstairs-room pattern plainly"):
                reward_xp = 15
                self.state.flags["blackwake_gallows_copse_lead"] = True
                self.say("Oren finally admits the same buyer rents different needs under different names and always asks which patrol line is short-handed this week.")
            else:
                self.say("Oren gives you half a truth and the kind of look that says the rest has to be earned somewhere else.")
        else:
            self.player_action("Offer the wrong contract phrase and wait for the room to correct you.")
            reward_xp = 15
            self.state.flags["blackwake_millers_ford_lead"] = True
            self.state.flags["road_patrol_writ"] = True
            self.say("The lie lands exactly badly enough. Sabra flinches, Oren corrects you on instinct, and the real manifest chain all but writes itself into the silence.")
        self.state.flags["neverwinter_private_room_scene_done"] = True
        self.state.flags["neverwinter_private_room_intel"] = True
        self.add_clue("Oren and Sabra's upstairs room confirms that copied manifests, false room bookings, and fake roadwarden cadence are all part of one Neverwinter-side correction line feeding the frontier.")
        self.add_journal(
            "In Oren Vale's upstairs room, you tied Sabra's altered manifests to the same contract-house habits feeding false road authority toward the High Road."
        )
        self.reward_party(xp=reward_xp, reason="working the private room above Oren Vale's contract house")

    def handle_neverwinter_tymora_shrine(self) -> None:
        assert self.state is not None
        if self.state.flags.get("greywake_breakout_resolved"):
            self.state.flags["neverwinter_tymora_shrine_seen"] = True
            return
        if self.state.flags.get("neverwinter_tymora_shrine_seen"):
            return
        self.state.flags["neverwinter_tymora_shrine_seen"] = True
        self.state.flags["neverwinter_elira_met"] = True
        self.banner("South Gate Shrine of Tymora")
        self.say(
            "Mira's writ takes you through Neverwinter's southern gate, where a temporary Tymoran shrine has been lashed "
            "to a rebuilt watch alcove. A priestess is treating a drover whose arm has gone gray around an ash-bitter cut, "
            "while Helm's Hold pilgrims and Phandalin teamsters wait in a nervous half-circle.",
            typed=True,
        )
        self.speaker(
            "Elira Dawnmantle",
            "If the road is teaching its wounds this close to the city, then Phandalin will be seeing worse by nightfall.",
        )
        choice = self.scenario_choice(
            "How do you help at the shrine before the road takes you south?",
            [
                self.skill_tag("MEDICINE", self.action_option("Stabilize the poisoned drover with Elira.")),
                self.skill_tag("RELIGION", self.action_option("Lead Tymora's road-prayer for the waiting caravan.")),
                self.skill_tag("INVESTIGATION", self.action_option("Study the ash toxin and the false road marks on the harness.")),
                self.action_option("Keep the shrine moving and save your strength for the road."),
            ],
            allow_meta=False,
        )
        helped_elira = False
        if choice == 1:
            self.player_action("Stabilize the poisoned drover with Elira.")
            helped_elira = self.skill_check(self.state.player, "Medicine", 8, context="to slow the ash-bitter poison")
            if helped_elira:
                self.state.flags["elira_helped"] = True
                self.state.flags["neverwinter_elira_helped"] = True
                self.state.flags["road_poison_pattern_known"] = True
                self.add_clue("Elira identifies an ash-bitter poison reaching victims before Phandalin.")
                self.reward_party(xp=10, reason="helping Elira stabilize a poisoned drover")
                self.say("The gray edge of the wound stops spreading, and Elira gives you a small, approving nod.")
            else:
                self.say("The poison keeps moving, but your pressure and clean bandage buy Elira enough time to save the drover.")
        elif choice == 2:
            self.player_action("Lead Tymora's road-prayer for the waiting caravan.")
            helped_elira = self.skill_check(self.state.player, "Religion", 8, context="to steady the shrine and caravan")
            self.add_inventory_item("blessed_salve", source="Elira's shrine satchel")
            if helped_elira:
                self.state.flags["elira_helped"] = True
                self.state.flags["neverwinter_elira_blessing"] = True
                self.reward_party(xp=10, reason="steadying the South Gate shrine")
                self.say("The prayer quiets the panic without softening the danger, which may be Tymora's cleanest kind of luck.")
            else:
                self.say("The words land unevenly, but the caravan still leaves with steadier hands and one less argument.")
        elif choice == 3:
            self.player_action("Study the ash toxin and the false road marks on the harness.")
            helped_elira = self.skill_check(self.state.player, "Investigation", 8, context="to connect poison, harness marks, and forged authority")
            if helped_elira:
                self.state.flags["elira_helped"] = True
                self.state.flags["neverwinter_false_road_marks_found"] = True
                self.state.flags["blackwake_millers_ford_lead"] = True
                self.add_clue("Harness marks at Neverwinter's gate match false roadwarden inspections near Miller's Ford.")
                self.reward_party(xp=10, reason="reading the poisoned road evidence")
                self.say("The harness cuts are too neat for panic. Someone with copied authority pulled this wagon out of line.")
            else:
                self.say("You catch the pattern too late to name it cleanly, but the false inspection cuts stay in your mind.")
        else:
            self.player_action("Keep the shrine moving and save your strength for the road.")
            self.add_inventory_item("potion_healing", source="Elira's road charity basket")
            self.say("Elira presses a healing draught into your hands anyway. Luck, apparently, dislikes going unused.")

        if self.has_companion("Elira Dawnmantle"):
            return
        options = [
            self.quoted_option("RECRUIT", "Walk with us. The road needs a field priest more than a waiting shrine."),
            self.quoted_option("SAFE", "Finish your work here. If Phandalin still needs you, we will find you there."),
        ]
        recruit_choice = self.scenario_choice("Elira looks from the shrine to the south road.", options, allow_meta=False)
        self.player_choice_output(options[recruit_choice - 1])
        if recruit_choice == 1:
            if self.state.flags.get("elira_helped") or self.skill_check(
                self.state.player,
                "Persuasion",
                8,
                context="to convince Elira the field needs her now",
            ):
                self.recruit_companion(create_elira_dawnmantle())
                self.state.flags["elira_neverwinter_recruited"] = True
                self.state.flags["shrine_recruit_attempted"] = True
                self.speaker("Elira Dawnmantle", "Then I walk now. Tymora can keep a shrine; people need hands.")
            else:
                self.state.flags["neverwinter_elira_recruit_failed"] = True
                self.speaker("Elira Dawnmantle", "Not yet. Earn the road's trust, and ask me again in Phandalin.")
        else:
            self.state.flags["elira_neverwinter_available_in_phandalin"] = True
            self.speaker("Elira Dawnmantle", "Then I will finish here and follow the wounded south. We may meet again before the day is done.")

    def handle_neverwinter_high_road_milehouse(self) -> None:
        assert self.state is not None
        if self.state.flags.get("neverwinter_high_road_milehouse_seen"):
            return
        self.state.flags["neverwinter_high_road_milehouse_seen"] = True
        self.banner("High Road Milehouse")
        self.say(
            "Past the last Neverwinter stones, the High Road narrows around a shuttered milehouse used by Helm's Hold pilgrims, "
            "Lord Neverember's roadwardens, and Phandalin-bound wagons. Fresh ash has been rubbed into the milemark, trying to "
            "turn a lawful stop into a frightened detour.",
            typed=True,
        )
        enemies = [create_enemy("brand_saboteur")]
        if self.act1_party_size() >= 3:
            enemies.append(create_enemy("bandit"))
        else:
            enemies[0].current_hp = enemies[0].max_hp = 7
        hero_bonus = 0
        choice = self.scenario_choice(
            "Which path do you secure from the milehouse?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Inspect the false roadwarden writs before anyone moves on.")),
                self.skill_tag("SURVIVAL", self.action_option("Scout the Neverwinter Wood verge for the ambush line.")),
                self.skill_tag("PERSUASION", self.action_option("Organize the Helm's Hold pilgrims and refugee wagons into one guarded column.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Inspect the false roadwarden writs before anyone moves on.")
            if self.skill_check(self.state.player, "Investigation", 12, context="to expose forged roadwarden authority"):
                self.state.flags["neverwinter_false_writs_spotted"] = True
                self.state.flags["blackwake_millers_ford_lead"] = True
                self.state.flags["road_patrol_writ"] = True
                enemies[0].current_hp = max(1, enemies[0].current_hp - 3)
                hero_bonus += 1
                self.add_clue("False roadwarden writs near Neverwinter point toward forged authority before Phandalin.")
                self.say("The writ seal copies Lord Neverember's road mark closely enough to fool scared teamsters, but not a calm look.")
        elif choice == 2:
            self.player_action("Scout the Neverwinter Wood verge for the ambush line.")
            if self.skill_check(self.state.player, "Survival", 12, context="to read the woodline before the Brand springs it"):
                self.state.flags["neverwinter_woodline_path"] = True
                self.state.flags["road_ambush_scouted"] = True
                self.apply_status(enemies[0], "surprised", 1, source="your woodline scout")
                hero_bonus += 1
                self.say("The ash line hides badly under pine needles. You find the waiting knife before it finds the wagon.")
        else:
            self.player_action("Organize the Helm's Hold pilgrims and refugee wagons into one guarded column.")
            if self.skill_check(self.state.player, "Persuasion", 12, context="to turn frightened travelers into an orderly column"):
                self.state.flags["neverwinter_pilgrims_guarded"] = True
                self.state.flags["blackwake_gallows_copse_lead"] = True
                hero_bonus += 1
                elira = self.find_companion("Elira Dawnmantle")
                if elira is not None:
                    self.adjust_companion_disposition(elira, 1, "you protected pilgrims before chasing the faster lead")
                self.say("The column tightens around the weakest carts, and a pilgrim points out where two wagons were taken south alive.")

        outcome = self.run_encounter(
            Encounter(
                title="High Road Milehouse Intercept",
                description="Ashen Brand cutters try to turn forged authority and pilgrim fear into another missing wagon.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=12,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The milehouse falls quiet, and the road south learns fear before your name.")
            return
        if outcome == "fled":
            self.state.flags["neverwinter_milehouse_bypassed"] = True
            self.say("You break away from the milehouse before the false roadwardens can pin the company in place.")
            return
        self.state.flags["neverwinter_milehouse_secured"] = True
        self.reward_party(xp=20, gold=5, reason="securing the High Road milehouse")
        self.add_journal("You secured a Neverwinter-side milehouse and chose how the road south would open.")

    def handle_neverwinter_signal_cairn(self) -> None:
        assert self.state is not None
        if self.state.flags.get("neverwinter_signal_cairn_seen"):
            return
        self.state.flags["neverwinter_signal_cairn_seen"] = True
        self.banner("Neverwinter Wood Signal Cairn")
        self.say(
            "A little farther south, the road bends past an old signal cairn on the Neverwinter Wood side of the ditch. "
            "Its stones are older than the new roadwarden paint, and someone has packed the top with green pine, lamp oil, "
            "and a strip of ash-black cloth waiting for a match.",
            typed=True,
        )
        enemies = [self.intro_pick_enemy(("goblin_skirmisher", "cinder_kobold"))]
        if self.act1_party_size() >= 3:
            enemies.append(create_enemy("bandit_archer"))
        else:
            enemies[0].current_hp = enemies[0].max_hp = 6
        hero_bonus = 0
        choice = self.scenario_choice(
            "How do you handle the signal cairn?",
            [
                self.skill_tag("STEALTH", self.action_option("Take the firekeeper quietly before the signal rises.")),
                self.skill_tag("SURVIVAL", self.action_option("Spoil the fuel and read where the watchers came from.")),
                self.skill_tag("ARCANA", self.action_option("Check the ash-cloth for a magical or alchemical trigger.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Take the firekeeper quietly before the signal rises.")
            if self.skill_check(self.state.player, "Stealth", 12, context="to silence the signal watcher"):
                self.state.flags["road_reinforcement_signal_cut"] = True
                self.apply_status(enemies[0], "surprised", 1, source="your quiet approach")
                hero_bonus += 1
                self.say("The watcher turns too late, flint still in hand, and the signal never becomes more than intent.")
        elif choice == 2:
            self.player_action("Spoil the fuel and read where the watchers came from.")
            if self.skill_check(self.state.player, "Survival", 12, context="to spoil the cairn and follow the sign-cut trail"):
                self.state.flags["road_reinforcement_signal_cut"] = True
                self.state.flags["road_second_wave_trail_read"] = True
                hero_bonus += 1
                self.add_clue("A signal cairn south of Neverwinter was meant to call a harder Ashen Brand wave onto the High Road.")
                self.say("The fuel goes wet and useless, and the footprints point toward a second ambush pocket farther south.")
        else:
            self.player_action("Check the ash-cloth for a magical or alchemical trigger.")
            if self.skill_check(self.state.player, "Arcana", 12, context="to disarm the ash-cloth flash trigger"):
                self.state.flags["road_reinforcement_signal_cut"] = True
                self.state.flags["road_ash_signal_understood"] = True
                enemies[0].current_hp = max(1, enemies[0].current_hp - 2)
                hero_bonus += 1
                self.say("The cloth is treated to flare high and dirty. You pinch the trigger out before the Brand can paint the sky.")

        outcome = self.run_encounter(
            Encounter(
                title="Neverwinter Wood Signal Cairn",
                description="A hidden firekeeper tries to warn the High Road ambush before you can stop the signal.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=12,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The signal fire climbs over the trees, and the High Road closes around you before Phandalin ever sees your face.")
            return
        if outcome == "fled":
            self.state.flags["neverwinter_signal_cairn_bypassed"] = True
            self.say("You leave the cairn burning low behind you, knowing someone farther south may have seen enough.")
            return
        self.state.flags["neverwinter_signal_cairn_cleared"] = True
        self.reward_party(xp=15, gold=4, reason="silencing the Neverwinter Wood signal cairn")
        self.add_journal("You found and broke a signal cairn meant to harden the High Road ambush.")

    def handle_neverwinter_departure_fork(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("early_companion_recruited"):
            self.offer_early_companion()
        self.handle_neverwinter_tymora_shrine()
        if self.state is None or self.state.current_scene != "neverwinter_briefing":
            return
        self.handle_neverwinter_high_road_milehouse()
        if self.state is None or self.state.current_scene != "neverwinter_briefing":
            return
        self.handle_neverwinter_signal_cairn()
        if self.state is None or self.state.current_scene != "neverwinter_briefing":
            return
        self.add_journal("Mira Thann sent you south with a writ for Phandalin's steward.")

        while True:
            self.banner("Leaving Neverwinter")
            self.say(
                "The south road opens beyond the last city stones, but smoke smears the river cut to the east. "
                "A panicked wagon team hammers past with a charred toll seal hanging from the harness.",
                typed=True,
            )
            choice = self.scenario_choice(
                "Which route do you take?",
                [
                    self.action_option("Take the direct south road toward Phandalin."),
                    self.action_option("Investigate the smoke and caravan panic near the river cut."),
                    self.skill_tag("BACKTRACK", self.action_option("Circle back long enough to gather one more rumor in Neverwinter.")),
                ],
                allow_meta=False,
            )
            if choice == 1:
                self.player_action("Take the direct south road toward Phandalin.")
                self.travel_to_act1_node("high_road_ambush")
                return
            if choice == 2:
                self.player_action("Investigate the smoke and caravan panic near the river cut.")
                self.state.flags["blackwake_started"] = True
                self.state.flags["blackwake_return_destination"] = "undecided"
                self.grant_quest(
                    "trace_blackwake_cell",
                    note="Smoke outside Neverwinter points toward Blackwake Crossing before the wider High Road opens.",
                )
                self.add_journal("You turned off toward Blackwake Crossing to trace smoke, forged toll seals, and missing caravans.")
                self.travel_to_act1_node("blackwake_crossing")
                return

            self.player_action("Circle back long enough to gather one more rumor in Neverwinter.")
            if not self.state.flags.get("blackwake_neverwinter_rumor"):
                self.state.flags["blackwake_neverwinter_rumor"] = True
                self.add_clue(
                    "A Neverwinter drover says forged river-cut inspections are bleeding southbound caravans before they ever reach the High Road."
                )
                self.say(
                    "A drover near the north gate swears the missing wagons were waved aside by men carrying good-looking papers and bad patience."
                )
            else:
                self.say("The rumor loop has gone thin. The smoke east of the road is still the only fresh lead.")
            self.state.current_scene = "neverwinter_briefing"
            return

    def offer_early_companion(self) -> None:
        assert self.state is not None
        if self.state.flags.get("early_companion_recruited"):
            self.say("Mira has already assigned someone to your company for the ride south.")
            return
        self.speaker(
            "Mira Thann",
            "You are not riding into this alone. Choose the road-shield you want beside you: Kaelis for eyes in the brush, or Rhogar for a sworn lineholder.",
        )
        options = [
            self.action_option("Send Kaelis Starling, a ranger scout, with me."),
            self.action_option("Rhogar Valeguard, a paladin caravan-guard, sounds right for this road."),
        ]
        choice = self.scenario_choice(
            "Mira glances across the tavern and taps two names on the contract roster.",
            options,
            allow_meta=False,
        )
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            self.recruit_companion(create_kaelis_starling())
            self.state.flags["early_companion_recruited"] = "Kaelis Starling"
            self.say("Kaelis checks the fletching on an arrow, nods once, and agrees to ride with you.")
        else:
            self.recruit_companion(create_rhogar_valeguard())
            self.state.flags["early_companion_recruited"] = "Rhogar Valeguard"
            self.say("Rhogar lifts his shield, swears to see the road cleared, and joins your company.")

    def liars_circle_branch_available(self) -> bool:
        assert self.state is not None
        if not self.state.flags.get("liars_circle_branch_available"):
            return False
        return not (
            self.state.flags.get("liars_circle_locked")
            or self.state.flags.get("liars_circle_solved")
            or self.state.flags.get("liars_circle_failed")
        )

    def discover_liars_circle_branch(self) -> None:
        assert self.state is not None
        if self.state.flags.get("liars_circle_branch_discovered"):
            return
        self.state.flags["liars_circle_branch_discovered"] = True
        self.state.flags["liars_circle_branch_available"] = True
        self.say(
            "Past the broken ambush wagon, a deer track slips west into thorn and old stone. Four weathered shapes wait there "
            "in a clearing just far enough from the road to feel deliberate."
        )
        self.add_clue("A side trail near the High Road ambush leads to a circle of four talking statues.")
        self.add_journal("A wilderness side trail from the High Road leads to a statue puzzle called Liar's Circle.")

    def high_road_tollstones_branch_available(self) -> bool:
        assert self.state is not None
        return bool(self.state.flags.get("high_road_tollstones_branch_available")) and not bool(
            self.state.flags.get("high_road_tollstones_resolved")
        )

    def high_road_false_checkpoint_available(self) -> bool:
        assert self.state is not None
        return bool(self.state.flags.get("high_road_false_checkpoint_available")) and not bool(
            self.state.flags.get("high_road_false_checkpoint_resolved")
        )

    def has_false_checkpoint_contract_proof(self) -> bool:
        assert self.state is not None
        if self.state.flags.get("neverwinter_private_room_intel") or self.state.flags.get(
            "quest_reward_neverwinter_private_room_access"
        ):
            return True
        return bool(
            self.has_quest("false_manifest_circuit")
            and self.state.flags.get("false_manifest_oren_detail")
            and self.state.flags.get("false_manifest_garren_detail")
        )

    def discover_high_road_tollstones_branch(self) -> None:
        assert self.state is not None
        if self.state.flags.get("high_road_tollstones_branch_discovered"):
            return
        self.state.flags["high_road_tollstones_branch_discovered"] = True
        self.state.flags["high_road_tollstones_branch_available"] = True
        self.say(
            "Beyond the wagon wreck, a second mark catches your eye: fresh black paint on a broken roadwarden milemarker, "
            "laid too neatly to be weather or accident."
        )
        self.add_clue("A broken High Road milemarker still carries fresh false-roadwarden paint.")
        self.add_journal("A broken milemarker near the High Road ambush points to another false toll operation.")

    def discover_high_road_false_checkpoint_branch(self) -> None:
        assert self.state is not None
        if self.state.flags.get("high_road_false_checkpoint_discovered"):
            return
        self.state.flags["high_road_false_checkpoint_discovered"] = True
        self.state.flags["high_road_false_checkpoint_available"] = True
        self.say(
            "A little farther south, fresh bootlines and a canvas shade mark an improvised roadwarden checkpoint. "
            "The men under it stand too straight around borrowed authority and too loose around real danger."
        )
        self.add_clue("Fake roadwardens have set a High Road checkpoint demanding papers from southbound travelers.")
        self.add_journal("A false roadwarden checkpoint waits on the High Road south of the ambush site.")

    def discover_high_road_side_branches(self) -> None:
        self.discover_liars_circle_branch()
        self.discover_high_road_tollstones_branch()
        self.discover_high_road_false_checkpoint_branch()

    def scene_high_road_liars_circle(self) -> None:
        assert self.state is not None
        self.banner("Liar's Circle")
        self.state.flags["liars_circle_seen"] = True
        self.say(
            "The trail opens into a small clearing where four stone statues stand in a ring: Knight, Priest, Thief, and King. "
            "Their carved eyes point inward, as if the answer has been standing between them for years.",
            typed=True,
        )
        self.say('A cracked plaque reads: "Exactly one of us speaks the truth. The others always lie."')
        if self.state.flags.get("liars_circle_locked"):
            self.say("The statues are locked in their chosen silence now. Whatever judgment they made will not be remade today.")
            self.travel_to_act1_node(
                "phandalin_hub",
                transition_text="You return to the High Road and continue toward Phandalin.",
            )
            return

        statue_lines = {
            "knight": ("Knight", "If the Priest is lying, then the King is telling the truth."),
            "priest": ("Priest", "Exactly one of the Knight or the King is telling the truth."),
            "thief": ("Thief", "Exactly one of the Priest or I is telling the truth."),
            "king": ("King", "The Priest is lying if and only if I am telling the truth."),
        }
        inspect_options = [
            ("knight", self.action_option("Inspect the Knight statue.")),
            ("priest", self.action_option("Inspect the Priest statue.")),
            ("thief", self.action_option("Inspect the Thief statue.")),
            ("king", self.action_option("Inspect the King statue.")),
            ("answer", self.skill_tag("LOGIC", self.action_option("Name the only truthful statue."))),
            ("leave", self.action_option("Leave the circle unresolved.")),
        ]
        while True:
            choice = self.scenario_choice(
                "What do you do in Liar's Circle?",
                [text for _, text in inspect_options],
                allow_meta=False,
            )
            selection_key, selection_text = inspect_options[choice - 1]
            if selection_key in statue_lines:
                self.player_choice_output(selection_text)
                speaker_name, line = statue_lines[selection_key]
                self.speaker(speaker_name, line)
                self.state.flags[f"liars_circle_inspected_{selection_key}"] = True
                continue
            if selection_key == "answer":
                self.player_choice_output(selection_text)
                answer_options = [
                    ("knight", self.quoted_option("KNIGHT", "The Knight tells the truth.")),
                    ("priest", self.quoted_option("PRIEST", "The Priest tells the truth.")),
                    ("thief", self.quoted_option("THIEF", "The Thief tells the truth.")),
                    ("king", self.quoted_option("KING", "The King tells the truth.")),
                    ("back", self.action_option("Step back and keep thinking.")),
                ]
                answer_choice = self.scenario_choice(
                    "Which statue is the only truthful one?",
                    [text for _, text in answer_options],
                    allow_meta=False,
                )
                answer_key, answer_text = answer_options[answer_choice - 1]
                if answer_key == "back":
                    self.player_choice_output(answer_text)
                    continue
                self.resolve_liars_circle_answer(answer_key, answer_text)
                break
            self.player_choice_output(selection_text)
            self.say("You leave the four statues arguing with the wind and follow the trail back to the High Road.")
            break

        self.travel_to_act1_node(
            "phandalin_hub",
            transition_text="You return to the High Road and continue toward Phandalin.",
        )

    def resolve_liars_circle_answer(self, answer_key: str, answer_text: str) -> None:
        assert self.state is not None
        self.player_choice_output(answer_text)
        self.state.flags["liars_circle_locked"] = True
        self.state.flags["liars_circle_branch_available"] = False
        self.state.flags["liars_circle_answer"] = answer_key
        if answer_key == "thief":
            self.state.flags["liars_circle_solved"] = True
            self.speaker("Thief", "Finally. Someone heard the shape of the lie instead of the polish on the crown.")
            self.say("The Thief statue bows with a scrape of old stone, and the circle exhales like a held secret.")
            self.apply_liars_blessing()
            return
        self.state.flags["liars_circle_failed"] = True
        self.speaker("King", "A confident answer is still an answer.")
        self.say("The ring snaps shut with a sound like a lock turning under your tongue.")
        self.apply_liars_curse()

    def scene_high_road_false_checkpoint(self) -> None:
        assert self.state is not None
        self.banner("False Roadwarden Checkpoint")
        self.state.flags["high_road_false_checkpoint_seen"] = True
        self.say(
            "A canvas shade hangs over the road where no lawful checkpoint should be. Three men in borrowed roadwarden colors demand papers, "
            "one hand on a ledger and the other near a whistle meant for somebody hidden in the brush.",
            typed=True,
        )
        if self.state.flags.get("high_road_false_checkpoint_resolved"):
            self.say("The false checkpoint has already folded. Only wheel ruts, cut rope, and a discarded paper seal remain.")
            self.travel_to_act1_node(
                "phandalin_hub",
                transition_text="You leave the false checkpoint behind and continue toward Phandalin.",
            )
            return

        options: list[tuple[str, str]] = []
        if self.has_false_checkpoint_contract_proof():
            options.append(
                (
                    "proof",
                    self.skill_tag(
                        "CONTRACT HOUSE PROOF",
                        self.action_option("Use Oren, Sabra, and Garren's evidence to break the checkpoint's authority."),
                    ),
                )
            )
        options.extend(
            [
                ("deception", self.skill_tag("DECEPTION", self.action_option("Present yourself as the inspector they were expecting."))),
                ("insight", self.skill_tag("INSIGHT", self.action_option("Name the one phrase no real roadwarden would use."))),
                ("persuasion", self.skill_tag("PERSUASION", self.action_option("Convince the checkpoint hands they are holding poison, not power."))),
                ("intimidation", self.skill_tag("INTIMIDATION", self.action_option("Make the copied seals feel more dangerous to carry than to abandon."))),
                ("comply", self.action_option("Show harmless papers, pay the nuisance fee, and keep moving.")),
            ]
        )
        choice = self.scenario_choice("The fake roadwardens demand your papers. What do you do?", [text for _, text in options], allow_meta=False)
        selection_key, selection_text = options[choice - 1]
        self.player_choice_output(selection_text)
        if selection_key == "proof":
            self.say(
                "Oren's room line, Sabra's corrected manifest, and Garren's forbidden cadence land like three nails through the same false seal. "
                "The ledger man shuts the book before his own hands can betray him."
            )
            self.resolve_high_road_false_checkpoint(success=True, method="proof")
        elif selection_key == "deception":
            success = self.skill_check(self.state.player, "Deception", 13, context="to impersonate the inspector the fake checkpoint expected")
            self.resolve_high_road_false_checkpoint(success=success, method="deception")
        elif selection_key == "insight":
            success = self.skill_check(self.state.player, "Insight", 12, context="to expose the false roadwarden cadence in their demand")
            self.resolve_high_road_false_checkpoint(success=success, method="insight")
        elif selection_key == "persuasion":
            success = self.skill_check(self.state.player, "Persuasion", 13, context="to talk the checkpoint hands out of copied authority")
            self.resolve_high_road_false_checkpoint(success=success, method="persuasion")
        elif selection_key == "intimidation":
            success = self.skill_check(self.state.player, "Intimidation", 13, context="to make the false checkpoint abandon its papers")
            self.resolve_high_road_false_checkpoint(success=success, method="intimidation")
        else:
            self.resolve_high_road_false_checkpoint(success=False, method="compliance")

        self.travel_to_act1_node(
            "phandalin_hub",
            transition_text="You leave the false checkpoint behind and follow the High Road south.",
        )

    def resolve_high_road_false_checkpoint(self, *, success: bool, method: str) -> None:
        assert self.state is not None
        self.state.flags["high_road_false_checkpoint_resolved"] = True
        self.state.flags["high_road_false_checkpoint_available"] = False
        self.state.flags["high_road_false_checkpoint_resolution"] = method if success else "paid_fee"
        if not success:
            fee = min(6, self.state.gold)
            if fee:
                self.state.gold -= fee
            self.state.flags["high_road_false_checkpoint_fee_paid"] = True
            self.apply_status(self.state.player, "reeling", 1, source="a humiliating false checkpoint delay")
            self.say(
                f"The checkpoint fails to find real leverage, but it wastes your time and extracts {fee} gp before waving you through with clerkly contempt."
            )
            self.add_journal("You passed the false roadwarden checkpoint by paying its nuisance fee instead of exposing it.")
            return

        self.state.flags["high_road_false_checkpoint_exposed"] = True
        self.state.flags["blackwake_false_checkpoint_exposed"] = True
        self.state.flags["blackwake_millers_ford_lead"] = True
        self.state.flags["road_patrol_writ"] = True
        self.state.flags["system_profile_seeded"] = True
        self.state.flags["varyn_route_pattern_seen"] = True
        self.add_clue("A High Road false checkpoint uses the same roadwarden cadence tied to Miller's Ford and copied Neverwinter authority.")
        if method == "proof":
            self.state.flags["high_road_false_checkpoint_contract_proof_used"] = True
            self.state.flags["neverwinter_contract_house_checkpoint_pressure"] = True
            self.state.flags["blackwake_gallows_copse_lead"] = True
            self.say(
                "One fake warden bolts; another leaves the ledger behind. The names in it point toward Miller's Ford, Gallows Copse, and the same correction line Sabra feared."
            )
            self.reward_party(xp=30, gold=14, reason="using contract-house proof to collapse a false High Road checkpoint")
            self.add_journal("Oren, Sabra, and Garren's evidence broke a false High Road checkpoint before Blackwake could frame the proof as rumor.")
        elif method == "deception":
            self.say("Your false authority outranks theirs just long enough to make the ledger open and the checkpoint fold around its own panic.")
            self.reward_party(xp=20, gold=10, reason="deceiving the false High Road checkpoint")
            self.add_journal("You bluffed the false roadwarden checkpoint into exposing its Miller's Ford lead.")
        elif method == "insight":
            self.say("You repeat their own wrong phrase back at them and name why no real roadwarden would say it. The borrowed uniforms suddenly look much too large.")
            self.reward_party(xp=20, gold=8, reason="reading the false High Road checkpoint's bad cadence")
            self.add_journal("You exposed the false roadwarden checkpoint by reading its wrong patrol cadence.")
        elif method == "persuasion":
            self.state.flags["high_road_false_checkpoint_hands_spared"] = True
            self.say("The checkpoint hands choose distance over loyalty. One leaves the ledger on the road and tells you which ford the papers came from.")
            self.reward_party(xp=20, gold=6, reason="talking down the false High Road checkpoint")
            self.add_journal("You persuaded the false checkpoint hands to abandon their forged road authority.")
        else:
            self.say("The copied seals hit the dirt before your threat finishes. Nobody there wants to be the last fool holding treason in daylight.")
            self.reward_party(xp=20, gold=8, reason="intimidating the false High Road checkpoint into retreat")
            self.add_journal("You intimidated the false roadwarden checkpoint into dropping its copied seals.")

    def scene_high_road_false_tollstones(self) -> None:
        assert self.state is not None
        self.banner("False Tollstones")
        self.state.flags["high_road_tollstones_seen"] = True
        self.say(
            "The broken milemarker stands beside a narrow service path, its old roadwarden notches painted over with "
            "Ashen Brand ash-black lines. Two nervous spotters wait in the scrub with a ledger, a lockbox, and the wrong kind of confidence.",
            typed=True,
        )
        if self.state.flags.get("high_road_tollstones_resolved"):
            self.say("The false toll is already broken. Only trampled brush and a scraped-clean milemarker remain.")
            self.travel_to_act1_node(
                "phandalin_hub",
                transition_text="You leave the milemarker behind and follow the High Road south.",
            )
            return

        has_blessing = self.has_story_skill_modifier(self.state.player, self.LIARS_BLESSING_MODIFIER_ID)
        if has_blessing:
            self.say("Liar's Blessing warms behind your teeth. The false paint almost seems to arrange itself into a passphrase.")

        options: list[tuple[str, str]] = []
        if has_blessing:
            options.append(
                (
                    "blessing",
                    self.skill_tag(
                        "LIAR'S BLESSING",
                        self.action_option("Speak the lie the false tollkeepers expect to hear."),
                    ),
                )
            )
        options.extend(
            [
                ("deception", self.skill_tag("DECEPTION", self.action_option("Bluff as an Ashen Brand courier."))),
                ("persuasion", self.skill_tag("PERSUASION", self.action_option("Offer the spotters a cleaner way out."))),
                ("leave", self.action_option("Leave the milemarker and stay on the main road.")),
            ]
        )
        choice = self.scenario_choice("How do you handle the false toll?", [text for _, text in options], allow_meta=False)
        selection_key, selection_text = options[choice - 1]
        if selection_key == "leave":
            self.player_choice_output(selection_text)
            self.say("You mark the painted stone for later and keep the party moving before the spotters find their nerve.")
            self.travel_to_act1_node(
                "phandalin_hub",
                transition_text="You leave the milemarker behind and follow the High Road south.",
            )
            return

        self.player_choice_output(selection_text)
        if selection_key == "blessing":
            self.say(
                "You give them a courier's lie with a thief-statue's perfect angle. The ledger opens before either spotter realizes "
                "they never asked for proof."
            )
            self.resolve_high_road_tollstones(success=True, method="blessing")
        elif selection_key == "deception":
            dc = 12 if has_blessing else 14
            success = self.skill_check(
                self.state.player,
                "Deception",
                dc,
                context="to pass as a courier collecting the false toll ledger",
            )
            self.resolve_high_road_tollstones(success=success, method="deception")
        else:
            dc = 11 if has_blessing else 13
            success = self.skill_check(
                self.state.player,
                "Persuasion",
                dc,
                context="to convince the spotters that running now is wiser than dying loyal",
            )
            self.resolve_high_road_tollstones(success=success, method="persuasion")

        self.travel_to_act1_node(
            "phandalin_hub",
            transition_text="You leave the milemarker behind and follow the High Road south.",
        )

    def resolve_high_road_tollstones(self, *, success: bool, method: str) -> None:
        assert self.state is not None
        self.state.flags["high_road_tollstones_resolved"] = True
        self.state.flags["high_road_tollstones_branch_available"] = False
        self.state.flags["high_road_tollstones_resolution"] = method if success else "failed"
        if not success:
            self.state.flags["high_road_tollstones_spotters_scattered"] = True
            self.apply_status(self.state.player, "reeling", 1, source="a false toll scramble")
            self.say("The spotters panic, scatter the ledger leaves into the brush, and leave you with only smoke, bootprints, and a foul mood.")
            self.add_journal("The false toll at the broken milemarker scattered before you could secure its ledger.")
            return

        self.state.flags["high_road_tollstones_ledger_taken"] = True
        self.state.flags["system_profile_seeded"] = True
        self.state.flags["varyn_route_pattern_seen"] = True
        self.add_inventory_item("antitoxin_vial", 1, source="the false toll lockbox")
        if method == "blessing":
            self.state.flags["high_road_tollstones_blessing_used"] = True
            self.state.flags["high_road_tollstones_passphrase_known"] = True
            self.say(
                "The lockbox yields a vial of antitoxin, a neat stack of toll coins, and a passphrase keyed to Ashen Brand patrols farther south."
            )
            self.add_clue("Liar's Blessing exposed an Ashen Brand passphrase from the false tollstone ledger.")
            self.reward_party(xp=25, gold=16, reason="turning Liar's Blessing against the false tollstones")
            self.add_journal("Liar's Blessing cracked the false tollstone operation and revealed an Ashen Brand passphrase.")
        elif method == "persuasion":
            self.state.flags["high_road_tollstones_contact_spared"] = True
            self.say("One spotter drops the ledger and runs. The other leaves the lockbox behind after whispering where the next Brand patrol listens.")
            self.add_clue("A frightened tollstone spotter named a southern Ashen Brand listening post.")
            self.reward_party(xp=20, gold=10, reason="breaking the false tollstones without bloodshed")
            self.add_journal("You talked the false tollstone spotters into abandoning their post.")
        else:
            self.say("Your bluff opens the ledger long enough to lift the lockbox and copy the next patrol mark before the spotters bolt.")
            self.add_clue("The false tollstone ledger names a southern Ashen Brand patrol mark.")
            self.reward_party(xp=20, gold=12, reason="bluffing through the false tollstones")
            self.add_journal("You bluffed through the false tollstone post and took its ledger mark.")

    def scene_road_ambush(self) -> None:
        assert self.state is not None
        self._sync_map_state_with_scene(force_node_id="high_road_ambush")
        self.banner("High Road")
        if self.state.flags.get("road_ambush_cleared") or self.state.flags.get("phandalin_arrived"):
            if self.state.flags.get("road_ambush_cleared"):
                self.discover_high_road_side_branches()
            self.render_act1_overworld_map(force=True)
            self.say(
                "The ambush site has gone quiet: ash-dark wagon ribs, old hoof churn, and the track south toward Phandalin "
                "all sit under a wind that knows the worst of this fight already passed."
            )
            options: list[tuple[str, str]] = [
                ("south", self.action_option("Follow the High Road back to Phandalin.")),
            ]
            backtrack_node = self.peek_act1_overworld_backtrack_node()
            if backtrack_node is not None:
                options.append(("backtrack", self.skill_tag("BACKTRACK", self.action_option(f"Backtrack to {backtrack_node.title}"))))
            if self.liars_circle_branch_available():
                options.append(
                    (
                        "liars_circle",
                        self.skill_tag("PUZZLE", self.action_option("Follow the overgrown statue trail into the wilderness.")),
                    )
                )
            if self.high_road_tollstones_branch_available():
                options.append(
                    (
                        "tollstones",
                        self.skill_tag("PARLEY", self.action_option("Investigate the broken roadwarden milemarker.")),
                    )
                )
            if self.high_road_false_checkpoint_available():
                options.append(
                    (
                        "checkpoint",
                        self.skill_tag("SOCIAL", self.action_option("Challenge the false roadwarden checkpoint.")),
                    )
                )
            choice = self.scenario_choice("Where do you go from the High Road?", [text for _, text in options], allow_meta=False)
            selection_key, _ = options[choice - 1]
            if selection_key == "backtrack":
                if not self.backtrack_act1_overworld_node():
                    self.say("There is no familiar road behind you to backtrack right now.")
                    return
                return
            if selection_key == "liars_circle":
                self.player_action("Follow the overgrown statue trail into the wilderness.")
                self.travel_to_act1_node(
                    "liars_circle",
                    transition_text="You follow the thorn track away from the road until four old statues come into view.",
                )
                return
            if selection_key == "tollstones":
                self.player_action("Investigate the broken roadwarden milemarker.")
                self.travel_to_act1_node(
                    "false_tollstones",
                    transition_text="You follow the paint-scarred markers to a broken roadwarden stone and a waiting false toll.",
                )
                return
            if selection_key == "checkpoint":
                self.player_action("Challenge the false roadwarden checkpoint.")
                self.travel_to_act1_node(
                    "false_checkpoint",
                    transition_text="You follow fresh bootlines to a canvas shade and men wearing borrowed roadwarden authority.",
                )
                return
            self.travel_to_act1_node(
                "phandalin_hub",
                transition_text="You turn south again, letting the familiar road carry you back to Phandalin's lanterns.",
            )
            return
        self.say(
            "South of Neverwinter, smoke rises from a wrecked wagon just off the road. Goblin voices bark "
            "from the scrub while a chained ash wolf snaps at a wounded caravan guard trying to hold them back.",
            typed=True,
        )
        if (
            self.state.flags.get("blackwake_sereth_fate") == "escaped"
            and not self.state.flags.get("blackwake_sereth_road_note_seen")
        ):
            self.state.flags["blackwake_sereth_road_note_seen"] = True
            self.say(
                "A waxy scrap pinned inside the wagon bed bears a careful S.V. mark and one fresh instruction: "
                "move the useful cargo south before the crossing story spreads."
            )
            self.add_clue("A High Road note suggests Sereth Vane survived Blackwake and is still moving useful cargo south.")
            self.add_journal("Sereth Vane's initials surfaced on a High Road note after Blackwake.")
        if not self.state.flags.get("road_ambush_wave_one_cleared"):
            party_size = len(self.state.party_members())
            if party_size == 1:
                enemies = [
                    self.intro_pick_enemy(("goblin_skirmisher", "cinder_kobold")),
                    self.intro_pick_enemy(("wolf", "mireweb_spider")),
                ]
                enemies[0].current_hp = enemies[0].max_hp = 5
                enemies[1].current_hp = enemies[1].max_hp = 5
                hero_bonus = 2
                self.state.player.temp_hp = max(self.state.player.temp_hp, 6)
                self.apply_status(self.state.player, "blessed", 1, source="the guard's desperate cover")
                self.say(
                    "The wounded guard has already bloodied both threats and buys you a cleaner lane to enter the fight. "
                    "You begin with 6 temporary hit points and a brief surge of confidence."
                )
            elif party_size == 2:
                enemies = [
                    self.intro_pick_enemy(("goblin_skirmisher", "cinder_kobold")),
                    self.intro_pick_enemy(("wolf", "mireweb_spider")),
                ]
                enemies[1].current_hp = enemies[1].max_hp = 7
                hero_bonus = 1
                self.say("The wounded guard buys your smaller company a narrow opening before the ambush can fully close.")
            else:
                enemies = [
                    self.intro_pick_enemy(("goblin_skirmisher", "cinder_kobold")),
                    self.intro_pick_enemy(("goblin_skirmisher", "cinder_kobold", "briar_twig")),
                    self.intro_pick_enemy(("wolf", "mireweb_spider")),
                ]
                hero_bonus = 0
            hero_bonus += self.apply_scene_companion_support("road_ambush")
            parley_dc = 12 if party_size <= 2 else 13
            if self.state.flags.get("road_ambush_scouted") and enemies:
                hero_bonus += 1
                self.apply_status(enemies[0], "surprised", 1, source="the milehouse woodline scout")
                self.say("Because you read the woodline at the milehouse, the ambush starts with one raider looking the wrong way.")
            if self.state.flags.get("road_patrol_writ") and enemies:
                enemies[-1].current_hp = max(1, enemies[-1].current_hp - 2)
                parley_dc = max(10, parley_dc - 1)
                self.say("The exposed roadwarden writ makes the raiders hesitate before committing to another false seizure.")
            if self.state.flags.get("neverwinter_pilgrims_guarded"):
                hero_bonus += 1
                self.say("The Helm's Hold column keeps its nerve behind you, leaving fewer panicked bodies for the raiders to exploit.")
            if not self.state.flags.get("road_approach_chosen"):
                approach_options = [
                    ("athletics", self.skill_tag("ATHLETICS", self.action_option("Charge in before the guard falls."))),
                    ("stealth", self.skill_tag("STEALTH", self.action_option("Flank through the brush."))),
                    ("intimidation", self.skill_tag("INTIMIDATION", self.action_option("Break their nerve with a warning shout."))),
                ]
                backtrack_node = self.peek_act1_overworld_backtrack_node()
                if backtrack_node is not None:
                    approach_options.append(
                        (
                            "backtrack",
                            self.skill_tag(
                                "BACKTRACK",
                                self.action_option("Backtrack toward Neverwinter and reconsider the river smoke."),
                            ),
                        )
                    )
                choice = self.scenario_choice(
                    "How do you approach the ambush?",
                    [text for _, text in approach_options],
                    allow_meta=False,
                )
                selection_key, _ = approach_options[choice - 1]
                if selection_key == "backtrack":
                    if not self.backtrack_act1_overworld_node():
                        self.say("There is no familiar road behind you to backtrack right now.")
                    return
                self.state.flags["road_approach_chosen"] = True
                if selection_key == "athletics":
                    self.player_action("Charge in before the guard falls.")
                    success = self.skill_check(self.state.player, "Athletics", 12, context="to hit the ambush line like a battering ram")
                    if success:
                        self.apply_status(self.state.player, "emboldened", 2, source="a crashing opening charge")
                        if enemies:
                            self.apply_status(enemies[0], "prone", 1, source="your shoulder-first impact")
                        self.say("You smash into the raiders hard enough to break their shape before the melee is even set.")
                        hero_bonus += 2
                    else:
                        self.apply_status(self.state.player, "reeling", 1, source="an overextended charge")
                        self.say("You still hit the fight fast, but the first impact jars you off balance instead of breaking the line.")
                elif selection_key == "stealth":
                    self.player_action("Flank through the brush.")
                    success = self.skill_check(self.state.player, "Stealth", 12, context="to slip through the brush")
                    if success:
                        enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
                        self.apply_status(enemies[0], "surprised", 1, source="your hidden approach")
                        hero_bonus += 2
                        self.say("You strike from cover before the goblins fully understand what hit them.")
                    else:
                        self.apply_status(self.state.player, "reeling", 1, source="getting caught in the open")
                        self.say("A snapped branch gives you away, and the goblins whirl toward you.")
                else:
                    self.player_action("Break their nerve with a warning shout.")
                    success = self.skill_check(self.state.player, "Intimidation", 12, context="to rattle the raiders")
                    if success:
                        enemies[-1].current_hp = max(1, enemies[-1].current_hp - 3)
                        self.apply_status(enemies[-1], "frightened", 2, source="your warning roar")
                        self.say("The wolf hesitates just long enough for the guard to pull free and draw breath.")
                    else:
                        for enemy in enemies:
                            if enemy.is_conscious():
                                self.apply_status(enemy, "emboldened", 1, source="seeing the bluff fail")
                        self.say("The goblins only cackle harder and close in.")

            outcome = self.run_encounter(
                Encounter(
                    title="Roadside Ambush: First Wave",
                    description="Roadside raiders and a hunting beast rush the ruined wagon.",
                    enemies=enemies,
                    allow_flee=True,
                    allow_parley=True,
                    parley_dc=parley_dc,
                    hero_initiative_bonus=hero_bonus,
                    allow_post_combat_random_encounter=False,
                )
            )
            if outcome == "defeat":
                self.handle_defeat("The High Road falls silent around the wreckage.")
                return
            if outcome == "fled":
                self.say("You circle wide, catch your breath, and try the road again.")
                return

            self.state.flags["road_ambush_wave_one_cleared"] = True
            self.add_clue("A scorched badge on the first High Road raiders marks the Ashen Brand.")
            self.reward_party(xp=15, gold=8, reason="breaking the first High Road wave")
            self.say(
                "Once the first rush breaks, the wounded guard introduces himself as Tolan Ironshield, a caravan veteran "
                "who was escorting ore and temple supplies to Phandalin."
            )
            self.speaker("Tolan Ironshield", "That was only the hook. I can still stand for the hammer blow if you'll have me.")
            options = [
                self.quoted_option("RECRUIT", "If you can stand, stand with us."),
                self.quoted_option("SAFE", "Get to the inn and recover. We'll talk there."),
            ]
            choice = self.scenario_choice("Tolan tightens the straps on his shield.", options, allow_meta=False)
            self.player_choice_output(options[choice - 1])
            if choice == 1:
                self.recruit_companion(create_tolan_ironshield())
                self.speaker(
                    "Tolan Ironshield",
                    "Good. Give me a minute to cinch the shield and I'll see you all the way to Phandalin.",
                )
            else:
                self.state.flags["tolan_waiting_at_inn"] = True
                self.add_journal("Tolan Ironshield is waiting at the Stonehill Inn if you need another shield arm.")
        else:
            self.say("The first ambush wave is already broken, but the road ahead still carries signal calls and running feet.")

        if self.state is None:
            return
        if not self.state.flags.get("road_ambush_wave_two_cleared"):
            self.say(
                "A horn coughs from the pines before the wagon dust can settle. The second wave comes in tighter: "
                "not scavengers this time, but the crew meant to punish anyone who survived the first rush.",
                typed=True,
            )
            party_size = len(self.state.party_members())
            if party_size <= 2:
                enemies = [create_enemy("bandit"), self.intro_pick_enemy(("goblin_skirmisher", "cinder_kobold"))]
                enemies[0].current_hp = min(enemies[0].current_hp, 9)
                enemies[0].max_hp = min(enemies[0].max_hp, 9)
                hero_bonus = 1
            elif party_size == 3:
                enemies = [create_enemy("ash_brand_enforcer"), self.intro_pick_enemy(("goblin_skirmisher", "cinder_kobold"))]
                hero_bonus = 0
            else:
                enemies = [
                    create_enemy("ash_brand_enforcer"),
                    create_enemy("bandit_archer"),
                    self.intro_pick_enemy(("cinder_kobold", "goblin_skirmisher", "wolf")),
                ]
                hero_bonus = 0
            if self.state.flags.get("road_reinforcement_signal_cut"):
                hero_bonus += 1
                if enemies:
                    self.apply_status(enemies[0], "reeling", 1, source="the broken signal cairn")
                self.say("Because the signal cairn went dark, the second wave arrives angry instead of coordinated.")
            if self.state.flags.get("road_second_wave_trail_read") and enemies:
                self.apply_status(enemies[-1], "surprised", 1, source="your read on the second-wave trail")
                self.say("You already read this approach at the cairn; the trailing raider walks straight into your angle.")

            outcome = self.run_encounter(
                Encounter(
                    title="High Road Second Wave",
                    description="A harder Ashen Brand reserve crew hits the wagon wreck after Tolan has a chance to join the line.",
                    enemies=enemies,
                    allow_flee=True,
                    allow_parley=True,
                    parley_dc=13 if party_size <= 2 else 14,
                    hero_initiative_bonus=hero_bonus,
                    allow_post_combat_random_encounter=False,
                )
            )
            if outcome == "defeat":
                self.handle_defeat("The second High Road wave breaks the caravan line before Phandalin can be warned.")
                return
            if outcome == "fled":
                self.say("You fall back from the second wave and will need to retake the road before Phandalin is safe.")
                return

            self.state.flags["road_ambush_wave_two_cleared"] = True
            self.add_clue("The harder High Road reserve was working under a hobgoblin sergeant tied to Ashfall Watch.")
            self.reward_party(xp=20, gold=7, reason="breaking the High Road reserve wave")

        self.state.flags["road_ambush_cleared"] = True
        self.discover_high_road_side_branches()
        self.travel_to_act1_node("phandalin_hub")
