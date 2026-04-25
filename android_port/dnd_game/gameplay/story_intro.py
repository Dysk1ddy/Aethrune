from __future__ import annotations

from ..data.story.background_openings import BACKGROUND_STARTS
from ..content import create_enemy, create_kaelis_starling, create_rhogar_valeguard, create_tolan_ironshield
from .encounter import Encounter


class StoryIntroMixin:
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
        self.state.flags.pop("background_prologue_pending", None)
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
                self.quoted_option("INTIMIDATION", "Lock the teamsters in line and make the thief choose fear over speed."),
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
            self.player_speaker("Lock the teamsters in line and make the thief choose fear over speed.")
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
        enemies = [create_enemy("goblin_skirmisher"), create_enemy("wolf")]
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
        enemies = [create_enemy("goblin_skirmisher")]
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

    def scene_neverwinter_briefing(self) -> None:
        assert self.state is not None
        self.banner("Act I: Ashes on the Triboar Trail")
        if not self.state.flags.get("briefing_seen"):
            self.say(
                "Warm mist drifts off the Neverwinter River as you enter the Jewel of the North. "
                "Even after the devastation tied to Mount Hotenow, craftsmen, traders, and laborers "
                "keep the city rebuilding itself with stubborn pride.",
                typed=True,
            )
            self.speaker(
                "Mira Thann",
                "Caravans bound for Phandalin have vanished, miners are being shaken down, and a new gang calling itself the Ashen Brand is using the frontier's old ruins for cover.",
            )
            self.state.flags["briefing_seen"] = True
        if not self.state.flags.get("early_companion_recruited"):
            self.offer_early_companion()

        while True:
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
            options.append(("leave", self.action_option("Take the writ and head for the High Road.")))
            choice = self.scenario_choice("Choose your response to Mira.", [text for _, text in options])
            selection_key, selection = options[choice - 1]
            if selection_key.startswith(("class:", "race:")):
                if self.handle_scene_identity_action("neverwinter_briefing", selection_key):
                    continue
            self.player_choice_output(selection)
            if selection_key == "neverwinter":
                self.state.flags["briefing_q_neverwinter"] = True
                self.speaker(
                    "Mira Thann",
                    "Neverwinter is bruised, not broken. Trade is flowing again, and Lord Neverember wants the road to Phandalin secure before fear spreads back north.",
                )
            elif selection_key == "phandalin":
                self.state.flags["briefing_q_phandalin"] = True
                self.speaker(
                    "Mira Thann",
                    "Phandalin is a resettled frontier town south of here. It was lost for centuries after monsters destroyed the old settlement, and the folk there still live like every roof beam matters.",
                )
            elif selection_key == "brand":
                self.state.flags["briefing_q_brand"] = True
                self.speaker(
                    "Mira Thann",
                    "Dangerous enough that witnesses keep mentioning goblin outriders, poisoned blades, and a hobgoblin sergeant running the field work from a hill watchtower east of town.",
                )
            elif selection_key == "prep":
                self.handle_neverwinter_prep()
            else:
                self.add_journal("Mira Thann sent you south with a writ for Phandalin's steward.")
                self.state.current_scene = "road_ambush"
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
            self.say("A temple acolyte presses an extra healing potion into your hands before you leave.")
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

    def scene_road_ambush(self) -> None:
        assert self.state is not None
        self.banner("High Road")
        self.say(
            "South of Neverwinter, smoke rises from a wrecked wagon just off the road. Goblin voices bark "
            "from the scrub while a chained ash wolf snaps at a wounded caravan guard trying to hold them back.",
            typed=True,
        )
        party_size = len(self.state.party_members())
        if party_size == 1:
            enemies = [create_enemy("goblin_skirmisher"), create_enemy("wolf")]
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
            enemies = [create_enemy("goblin_skirmisher"), create_enemy("wolf")]
            enemies[1].current_hp = enemies[1].max_hp = 7
            hero_bonus = 1
            self.say("The wounded guard buys your smaller company a narrow opening before the ambush can fully close.")
        else:
            enemies = [
                create_enemy("goblin_skirmisher"),
                create_enemy("goblin_skirmisher", name="Goblin Cutthroat"),
                create_enemy("wolf"),
            ]
            hero_bonus = 0
        hero_bonus += self.apply_scene_companion_support("road_ambush")
        if not self.state.flags.get("road_approach_chosen"):
            choice = self.scenario_choice(
                "How do you approach the ambush?",
                [
                    self.skill_tag("ATHLETICS", self.action_option("Charge in before the guard falls.")),
                    self.skill_tag("STEALTH", self.action_option("Flank through the brush.")),
                    self.quoted_option("INTIMIDATION", "Break their nerve with a warning shout."),
                ],
                allow_meta=False,
            )
            self.state.flags["road_approach_chosen"] = True
            if choice == 1:
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
            elif choice == 2:
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
                self.player_speaker("Break their nerve with a warning shout.")
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

        encounter = Encounter(
            title="Roadside Ambush",
            description="Goblin raiders and an ash wolf rush the ruined wagon.",
            enemies=enemies,
            allow_flee=True,
            allow_parley=True,
            parley_dc=12 if party_size <= 2 else 13,
            hero_initiative_bonus=hero_bonus,
        )
        outcome = self.run_encounter(encounter)
        if outcome == "defeat":
            self.handle_defeat("The High Road falls silent around the wreckage.")
            return
        if outcome == "fled":
            self.say("You circle wide, catch your breath, and try the road again.")
            return

        self.add_clue("A scorched badge on the goblins marks the Ashen Brand.")
        self.add_clue("The raiders were working with a hobgoblin sergeant tied to Ashfall Watch.")
        self.reward_party(xp=25, gold=15, reason="saving the caravan guard on the High Road")
        self.say(
            "Once the smoke settles, the wounded guard introduces himself as Tolan Ironshield, a caravan veteran "
            "who was escorting ore and temple supplies to Phandalin."
        )
        self.speaker("Tolan Ironshield", "I can still stand. Say the word and I walk with you, or I make for the inn.")
        options = [
            self.quoted_option("RECRUIT", "If you can stand, stand with us."),
            self.quoted_option("SAFE", "Get to the inn and recover. We'll talk there."),
        ]
        choice = self.scenario_choice("Tolan tightens the straps on his shield.", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            self.recruit_companion(create_tolan_ironshield())
        else:
            self.state.flags["tolan_waiting_at_inn"] = True
            self.add_journal("Tolan Ironshield is waiting at the Stonehill Inn if you need another shield arm.")
        self.state.current_scene = "phandalin_hub"
