from __future__ import annotations


class StoryAct2ConyberryMixin:
    def _conyberry_active_companion(self, name: str):
        assert self.state is not None
        companion = self.find_companion(name)
        if companion is None or companion not in self.state.companions:
            return None
        return companion

    def _conyberry_circuit_strain(self) -> int:
        assert self.state is not None
        value = self.state.flags.get("conyberry_circuit_strain", 0)
        return int(value) if isinstance(value, int) and not isinstance(value, bool) else 0

    def _conyberry_shift_circuit_strain(self, delta: int) -> int:
        assert self.state is not None
        current = self._conyberry_circuit_strain()
        updated = max(0, current + delta)
        self.state.flags["conyberry_circuit_strain"] = updated
        return updated

    def _conyberry_hushed_pilgrim_road(self, *, delayed: bool) -> None:
        assert self.state is not None
        self.say(
            "The road to Hushfen is all blown grass, old stone, and the feeling that too many footsteps ended here without ever becoming history. "
            "Ahead, a knot of pilgrims, peddlers, and hired carriers stands in the road like people who are ashamed of how frightened they already are.",
            typed=True,
        )
        if delayed:
            self.say(
                "The knot in the road is smaller than it should be. Someone already left rather than be seen here, and the ones who remained have had longer to teach each other the wrong version."
            )
        elira = self._conyberry_active_companion("Elira Dawnmantle")
        bryn = self._conyberry_active_companion("Bryn Underbough")
        if elira is not None:
            self.speaker(
                "Elira Lanternward",
                "Panic spreads faster when someone respectable pretends it is caution. Start with the frightened. The rest will follow what the room becomes.",
            )
        if bryn is not None:
            self.speaker(
                "Bryn Underbough",
                "Watch which one keeps correcting their own story. That is never just fear. That is someone testing which version sounds safest.",
            )
        choice = self.scenario_choice(
            "How do you answer the frightened road before the circuit answers it for you?",
            [
                self.skill_tag("PERSUASION", self.action_option("Steady the whole group openly and name the road as still belonging to the living.")),
                self.skill_tag("INSIGHT", self.action_option("Pull one witness aside and extract the cleanest version before fear edits it again.")),
                self.skill_tag("SURVIVAL", self.action_option("Follow the one story that changed in the telling and track the wrongness first.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Steady the whole group openly and name the road as still belonging to the living.")
            if bryn is not None:
                self.speaker(
                    "Bryn Underbough",
                    "Fair. Just remember half the room will tell the cleanest lie they can once they calm down enough to choose one.",
                )
            if self.skill_check(self.state.player, "Persuasion", 13, context="to steady the frightened road into Hushfen"):
                self.state.flags["conyberry_pilgrims_steadied"] = True
                self._conyberry_shift_circuit_strain(-1)
                self.reward_party(xp=10, reason="steadying the road into Hushfen")
                self.say("The fear does not vanish. It just stops performing for itself long enough to let the truth breathe.")
            else:
                self._conyberry_shift_circuit_strain(1)
                self.say("The road calms only by degrees. Too many people still sound like they are trying out safer lies.")
        elif choice == 2:
            self.player_action("Pull one witness aside and extract the cleanest version before fear edits it again.")
            if elira is not None:
                self.speaker(
                    "Elira Lanternward",
                    "Take the clearest witness if you must. Just do not teach the others that only precise fear is worth answering.",
                )
            if bryn is not None:
                self.speaker(
                    "Bryn Underbough",
                    "Good. The truth is usually in the person trying hardest not to sound like they own any.",
                )
            if self.skill_check(self.state.player, "Insight", 13, context="to isolate the clean witness on the Hushfen road"):
                self.state.flags["conyberry_clean_witness_taken"] = True
                self.say("One pilgrim stops revising themselves long enough to tell you where the hush in the road first turned deliberate.")
            else:
                self._conyberry_shift_circuit_strain(1)
                self.say("You still get names and fragments, but none of them come out of the same mouth cleanly twice.")
        else:
            self.player_action("Follow the one story that changed in the telling and track the wrongness first.")
            if elira is not None:
                self.speaker(
                    "Elira Lanternward",
                    "Then do it quickly. I will not have the road think we stepped around the living to get to the mystery.",
                )
            if self.skill_check(self.state.player, "Survival", 13, context="to track the wrongness moving through Hushfen's road"):
                self.state.flags["conyberry_whisper_track_named"] = True
                self.add_clue("Hushfen's silence has been handled, not merely suffered. Something practical has been teaching the road where to sound wrong.")
                self.say("The wrongness has a route to it. That is worse and more useful than a haunting would have been.")
            else:
                self._conyberry_shift_circuit_strain(1)
                self.say("The trail blurs into too many frightened corrections, and the road feels more watched for your attention.")

    def _conyberry_waymarker_cairn(self) -> None:
        assert self.state is not None
        self.say(
            "A broken waymarker cairn still points nowhere useful, but somebody has touched it recently. Old devotional scratches sit beside newer handling marks, "
            "as if practical hands wanted the road to keep looking abandoned while still being readable to the right people."
        )
        bryn = self._conyberry_active_companion("Bryn Underbough")
        if bryn is not None:
            self.speaker(
                "Bryn Underbough",
                "Old stone, new handling marks. Somebody wants this road to stay abandoned in public and usable in private.",
            )
        choice = self.scenario_choice(
            "How do you read the waymarker cairn before the circuit closes around it?",
            [
                self.skill_tag("RELIGION", self.action_option("Read it as a warded waymarker and follow the chapel line first.")),
                self.skill_tag("HISTORY", self.action_option("Read it as funerary routework and take the grave ring first.")),
                self.skill_tag("INVESTIGATION", self.action_option("Read it as a disguised trail correction and follow the tampered line first.")),
            ],
            allow_meta=False,
        )
        first_site = "chapel" if choice == 1 else "grave" if choice == 2 else "sigil"
        self.state.flags["conyberry_first_site"] = first_site
        if choice == 1:
            self.player_action("Read it as a warded waymarker and follow the chapel line first.")
            if self.skill_check(self.state.player, "Religion", 13, context="to read Hushfen's warded waymarker correctly"):
                self.state.flags["conyberry_cairn_ward_read"] = True
                self.say("The cairn stops being abandoned stone and becomes a wounded instruction to keep the lamps in mind.")
            else:
                self._conyberry_shift_circuit_strain(1)
                self.say("The warding logic is still there, but it reaches you through abrasion rather than clarity.")
        elif choice == 2:
            self.player_action("Read it as funerary routework and take the grave ring first.")
            if self.skill_check(self.state.player, "History", 13, context="to read Hushfen's grave-route order"):
                self.state.flags["conyberry_cairn_grave_read"] = True
                self.say("The route becomes less mystical and more deliberate. The dead here were organized, not abandoned at random.")
            else:
                self._conyberry_shift_circuit_strain(1)
                self.say("You still find the grave line, but not before the road makes you work for the difference between memory and concealment.")
        else:
            self.player_action("Read it as a disguised trail correction and follow the tampered line first.")
            if self.skill_check(self.state.player, "Investigation", 13, context="to read the tampered Hushfen trail logic"):
                self.state.flags["conyberry_cairn_trail_read"] = True
                self.say("The false neglect has a pattern to it. Someone wanted the practical route hidden inside the pious ruin of the place.")
            else:
                self._conyberry_shift_circuit_strain(1)
                self.say("The trail still yields, but only after enough hesitation to tell the circuit you are being read back.")

    def _conyberry_chapel_of_lamps(self) -> None:
        assert self.state is not None
        self.state.flags["conyberry_chapel_seen"] = True
        self.say(
            "The chapel is hardly bigger than a roadside shelter: lamp niches, a basin, and a wall hammered with the sort of practical prayer people write "
            "when they know strangers live or die by unseen maintenance."
        )
        elira = self._conyberry_active_companion("Elira Dawnmantle")
        if elira is not None:
            self.speaker(
                "Elira Lanternward",
                "This is not ornamental faith. This is maintenance made holy because strangers depended on it.",
            )
        choice = self.scenario_choice(
            "How do you answer the Chapel of Lamps?",
            [
                self.skill_tag("RELIGION", self.action_option("Relight the chapel and wake one clean ward.")),
                self.skill_tag("SURVIVAL", self.action_option("Take the basin lantern and field wards into the circuit.")),
                self.skill_tag("INVESTIGATION", self.action_option("Seal the chapel and leave it untouched by further hands.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Relight the chapel and wake one clean ward.")
            if self.skill_check(self.state.player, "Religion", 13, context="to relight Hushfen's chapel cleanly"):
                self.state.flags["conyberry_chapel_relit"] = True
                self._conyberry_shift_circuit_strain(-1)
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    -1,
                    "the Chapel of Lamps remembers service as discipline instead of fear",
                )
                self.say("One lamp catches cleanly, and the whole roadside feels less eager to imitate the wrong quiet.")
            else:
                self._conyberry_shift_circuit_strain(1)
                self.say("The wick catches only badly. The chapel does not reject you, but it does not trust the hurry in your hands either.")
        elif choice == 2:
            self.player_action("Take the basin lantern and field wards into the circuit.")
            if self.skill_check(self.state.player, "Survival", 13, context="to take Hushfen's field lantern without stripping it thoughtlessly"):
                self.state.flags["conyberry_field_lantern_taken"] = True
                if elira is not None:
                    self.state.flags["elira_field_lantern"] = True
                    self.speaker(
                        "Elira Lanternward",
                        "If we carry it, we carry it as responsibility, not salvage.",
                    )
                self.say("The basin lantern comes free with less protest than you feared, as if the chapel would rather be carried carefully than admired badly.")
            else:
                self._conyberry_shift_circuit_strain(1)
                self.say("You get the lantern, but not without making the room sound more handled than served.")
        else:
            self.player_action("Seal the chapel and leave it untouched by further hands.")
            if self.skill_check(self.state.player, "Investigation", 13, context="to quarantine the damaged chapel without worsening it"):
                self.state.flags["conyberry_chapel_quarantined"] = True
                self.say("You leave the chapel dark but protected, refusing to make a wounded sacred place perform usefulness for you.")
            else:
                self._conyberry_shift_circuit_strain(1)
                self.say("The seal holds, but only after reminding the room that your caution is still another kind of intrusion.")

    def _conyberry_grave_ring(self) -> None:
        assert self.state is not None
        self.state.flags["conyberry_grave_seen"] = True
        self.say(
            "The grave ring is not dramatic. That is what makes it worse. Low stones, weather-soft names, and a circle that still feels organized "
            "enough to shame anyone trying to treat it like scenery."
        )
        elira = self._conyberry_active_companion("Elira Dawnmantle")
        bryn = self._conyberry_active_companion("Bryn Underbough")
        if elira is not None:
            self.speaker(
                "Elira Lanternward",
                "Say the names if you can. The dead should not have to compete with our urgency to stay real.",
            )
        choice = self.scenario_choice(
            "How do you read the Grave Ring?",
            [
                self.skill_tag("HISTORY", self.action_option("Read the markers historically and learn how the dead were organized here.")),
                self.skill_tag("RELIGION", self.action_option("Name the dead aloud and stabilize the ring as memory instead of puzzle.")),
                self.skill_tag("INVESTIGATION", self.action_option("Search for later claimant marks and hidden handling scars.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Read the markers historically and learn how the dead were organized here.")
            if self.skill_check(self.state.player, "History", 13, context="to read the grave ring as Meridian Compact route memory"):
                self.state.flags["conyberry_grave_history_read"] = True
                self.say("The dead here were not simply buried. They were placed under a discipline the living were expected to remember.")
            else:
                self._conyberry_shift_circuit_strain(1)
                self.say("The pattern still emerges, but only as a grief you are reading from too far away.")
        elif choice == 2:
            self.player_action("Name the dead aloud and stabilize the ring as memory instead of puzzle.")
            if self.skill_check(self.state.player, "Religion", 13, context="to name the dead cleanly enough for the ring to settle"):
                self.state.flags["conyberry_dead_named"] = True
                self._conyberry_shift_circuit_strain(-1)
                self.say("The ring does not become warm. It becomes less defensive, which is the closer thing to kindness a place like this still has.")
            else:
                self._conyberry_shift_circuit_strain(1)
                self.say("You speak the names with more urgency than steadiness, and the ring keeps some of its hurt to itself.")
        else:
            self.player_action("Search for later claimant marks and hidden handling scars.")
            if self.skill_check(self.state.player, "Investigation", 13, context="to find the living claim marks hiding in the grave ring"):
                self.state.flags["conyberry_claim_marks_found"] = True
                self.state.flags["agatha_claim_cover_suspected"] = True
                self.add_clue("Someone in the modern claims race has been using Hushfen's dead ground as cover for practical business and hidden handling marks.")
                if bryn is not None:
                    self.speaker(
                        "Bryn Underbough",
                        "That is not cult handwriting. That is claimant handwriting wearing cult weather.",
                    )
                if elira is not None:
                    self.speaker(
                        "Elira Lanternward",
                        "Then the living have already tried to use grief as cover. That is a smaller sin than murder and closer to the same shape than people admit.",
                    )
            else:
                self._conyberry_shift_circuit_strain(1)
                self.say("You find scratches and wear, but not enough to prove whether the living here were hiding business or only surviving fear badly.")

    def _conyberry_defiled_sigil(self, *, delayed: bool) -> None:
        assert self.state is not None
        self.state.flags["conyberry_sigil_seen"] = True
        self.say(
            "Silver nails, chalk geometry, and a wrong neatness sit over older marks like somebody tried to teach a roadside ward to serve a new master without changing its posture."
        )
        if delayed:
            self.say(
                "The sigil has had longer to settle into the place. It no longer reads like a fresh violation so much as an order that expected to keep standing."
            )
        elira = self._conyberry_active_companion("Elira Dawnmantle")
        bryn = self._conyberry_active_companion("Bryn Underbough")
        if elira is not None:
            self.speaker(
                "Elira Lanternward",
                "Look at the neatness of it. Somebody wanted the ward to keep the posture of service while answering the wrong will.",
            )
        if bryn is not None:
            self.speaker(
                "Bryn Underbough",
                "The clever part is not the sigil. It is making the damage look like nobody practical could have been involved.",
            )
        choice = self.scenario_choice(
            "What do you do with the defiled sigil?",
            [
                self.skill_tag("RELIGION", self.action_option("Break the sigil cleanly and push the wrong mark out.")),
                self.skill_tag("ARCANA", self.action_option("Copy the pattern before breaking it.")),
                self.skill_tag("STEALTH", self.action_option("Leave it live long enough to bait a watcher.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_action("Break the sigil cleanly and push the wrong mark out.")
            if self.skill_check(self.state.player, "Religion", 13, context="to break the Choir's sigil without teaching it a second lesson"):
                self.state.flags["conyberry_sigil_broken"] = True
                self._conyberry_shift_circuit_strain(-1)
                if elira is not None:
                    self.speaker(
                        "Elira Lanternward",
                        "Better broken than obedient to the wrong voice.",
                    )
                self.say("The sigil fails with a sound closer to a breath leaving than a curse breaking.")
            else:
                self._conyberry_shift_circuit_strain(1)
                self.say("The sigil comes apart, but not cleanly. The road keeps some of the bruise.")
        elif choice == 2:
            self.player_action("Copy the pattern before breaking it.")
            if self.skill_check(self.state.player, "Arcana", 13, context="to copy the defiled ward pattern before it collapses"):
                self.state.flags["conyberry_sigil_copied"] = True
                self._conyberry_shift_circuit_strain(1)
                if elira is not None:
                    self.speaker(
                        "Elira Lanternward",
                        "Be careful. There is a kind of understanding that always pretends it can stay clean.",
                    )
                self.add_clue("The Quiet Choir has been teaching older roadside wards to keep the posture of service while answering the wrong will.")
                self.say("The copied pattern is useful in exactly the way that should make you distrust wanting it.")
            else:
                self._conyberry_shift_circuit_strain(1)
                self.say("You catch only fragments of the pattern before it tears under your attention.")
        else:
            self.player_action("Leave it live long enough to bait a watcher.")
            if self.skill_check(self.state.player, "Stealth", 13, context="to bait the sigil's watcher without letting them own the angle"):
                self.state.flags["conyberry_watcher_baited"] = True
                self.state.flags["conyberry_watcher_seen"] = True
                if bryn is not None:
                    self.speaker(
                        "Bryn Underbough",
                        "Good. Dead wards do not file reports. Living hands do.",
                    )
                self.say("A living shape withdraws from the far scrub once it realizes the sigil has started watching back the wrong people.")
            else:
                self._conyberry_shift_circuit_strain(1)
                self.say("The watcher, if there was one, leaves you only the feeling of having been counted and dismissed.")

    def _conyberry_visit_branch_site(self, site: str, *, delayed: bool) -> None:
        if site == "grave":
            self._conyberry_grave_ring()
        elif site == "sigil":
            self._conyberry_defiled_sigil(delayed=delayed)
        else:
            self._conyberry_chapel_of_lamps()

    def _conyberry_first_branch_site(self, *, delayed: bool) -> None:
        assert self.state is not None
        first_site = str(self.state.flags.get("conyberry_first_site", "chapel"))
        self._conyberry_visit_branch_site(first_site, delayed=delayed)

    def _conyberry_second_branch_site(self, *, delayed: bool) -> None:
        assert self.state is not None
        site_options: list[tuple[str, str]] = []
        if not self.state.flags.get("conyberry_chapel_seen"):
            site_options.append(("chapel", self.skill_tag("RELIGION", self.action_option("Return the Chapel of Lamps to the circuit before the Pale Witness bears the whole warning."))))
        if not self.state.flags.get("conyberry_grave_seen"):
            site_options.append(("grave", self.skill_tag("HISTORY", self.action_option("Read the Grave Ring so the warning does not travel without its dead."))))
        if not self.state.flags.get("conyberry_sigil_seen"):
            site_options.append(("sigil", self.skill_tag("ARCANA", self.action_option("Answer the defiled sigil before it keeps teaching the road the wrong lesson."))))
        if not site_options:
            return
        self.say(
            "The circuit does not release you after one answer. Another part of Hushfen pulls at the road, asking whether you want warning with roots or only warning with speed."
        )
        choice = self.scenario_choice(
            "Which second part of the circuit do you answer before the Pale Witness speaks?",
            [text for _, text in site_options],
            allow_meta=False,
        )
        site, _ = site_options[choice - 1]
        self.state.flags["conyberry_second_site"] = site
        self._conyberry_visit_branch_site(site, delayed=delayed)
        self.state.flags["conyberry_two_sites_answered"] = True

    def _conyberry_exit_warning_choice(self, *, success: bool, delayed: bool) -> None:
        assert self.state is not None
        if self.state.flags.get("conyberry_warning_exit_choice"):
            return
        if success:
            self.say(
                "The Pale Witness's warning leaves the circuit with you, but Hushfen still asks what kind of burden truth becomes once the living start carrying it."
            )
        else:
            self.say(
                "Even broken, the warning has enough shape to harm or help depending on who gets to hold it first."
            )
        choice = self.scenario_choice(
            "How do you carry the Pale Witness's warning out of Hushfen?",
            [
                self.quoted_option("PERSUASION", "Share it publicly. Fear travels anyway; truth should not arrive gagged."),
                self.quoted_option("INSIGHT", "Restrict it to trusted hands until the town can act instead of merely panic."),
                self.quoted_option("ARCANA", "Bind the warning into a controlled circuit and keep one dangerous edge for later leverage."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("Share it publicly. Fear travels anyway; truth should not arrive gagged.")
            self.state.flags["conyberry_warning_exit_choice"] = "public"
            self.state.flags["agatha_warning_shared_publicly"] = True
            self.state.flags["agatha_public_warning_known"] = True
            self.act2_shift_metric(
                "act2_town_stability",
                1,
                "the Pale Witness's warning travels openly enough that rumors have less room to pretend they are strategy",
            )
            self.speaker("Pale Witness", "Then let it travel honestly, even if honesty makes cowards of half the room for a while.")
            elira = self._conyberry_active_companion("Elira Dawnmantle")
            if elira is not None:
                self.speaker("Elira Lanternward", "Good. Fear travels easily enough. Truth should not arrive gagged.")
        elif choice == 2:
            self.player_speaker("Restrict it to trusted hands until the town can act instead of merely panic.")
            self.state.flags["conyberry_warning_exit_choice"] = "trusted"
            self.state.flags["agatha_warning_restricted"] = True
            self.act2_shift_metric(
                "act2_route_control",
                1,
                "trusted hands carry the Pale Witness's warning as actionable route discipline instead of a rumor every claimant can bend",
            )
            self.speaker("Pale Witness", "Control is the oldest temptation of anyone who survives hearing too much.")
            bryn = self._conyberry_active_companion("Bryn Underbough")
            if bryn is not None:
                self.speaker(
                    "Bryn Underbough",
                    "That is not dishonorable. It is only dishonorable if we start pretending control and stewardship are the same thing.",
                )
        else:
            self.player_speaker("Bind the warning into a controlled circuit and keep one dangerous edge for later leverage.")
            self.state.flags["conyberry_warning_exit_choice"] = "bound"
            self.state.flags["agatha_warning_bound"] = True
            self.state.flags["agatha_bound_leverage"] = True
            self.act2_shift_metric(
                "act2_route_control",
                1,
                "binding the Pale Witness's warning preserves one dangerous edge for later use against the Choir's own route logic",
            )
            if delayed or not success:
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    1,
                    "binding a bruised warning keeps part of Hushfen's wound active instead of letting it settle",
                )
            self.speaker(
                "Pale Witness",
                "Better bound than cheaply spent. Better shared than hoarded. You are learning why the living kept failing this place.",
            )

    def scene_conyberry_agatha(self) -> None:
        assert self.state is not None
        delayed = self.state.flags.get("act2_neglected_lead") == "agatha_truth_secured"
        if "conyberry_circuit_strain" not in self.state.flags:
            self.state.flags["conyberry_circuit_strain"] = 1 if delayed else 0
        self.banner("Hushfen and the Pale Circuit")
        self._conyberry_hushed_pilgrim_road(delayed=delayed)
        self._conyberry_waymarker_cairn()
        self._conyberry_first_branch_site(delayed=delayed)
        self._conyberry_second_branch_site(delayed=delayed)
        self.say("Beyond the last roadside turn, the air stops feeling abandoned and starts feeling expectant.")
        self.say("The Pale Witness does not rise like a monster out of a tale. She arrives like a grief the air was already carrying.")
        self.speaker("Pale Witness", "You are late enough to be dangerous and early enough to matter.")
        self.speaker("Pale Witness", "The living always arrive wanting warning clean enough to carry and terrible enough to obey.")
        if delayed and self.state.flags.get("agatha_circuit_defiled"):
            self.say(
                "Silver nails and chalk sigils at the edge of the circuit tell you the Quiet Choir reached here first. Whatever warning Pale Witness gives now will come through damage."
            )
            self.speaker("Pale Witness", "They touched the circuit before you did. That is why I sound smaller than the truth.")
        if self.state.flags.get("conyberry_pilgrims_steadied"):
            self.speaker(
                "Pale Witness",
                "At least you did not begin by teaching the frightened that fear must earn eloquence before it deserves mercy.",
            )
        if self.state.flags.get("conyberry_dead_named"):
            self.speaker("Pale Witness", "At least you did not begin by forgetting whose road this still is.")
        if self.state.flags.get("conyberry_chapel_relit"):
            self.speaker("Pale Witness", "Someone still remembered the lamps were for service, not display.")
        if self.state.flags.get("conyberry_sigil_copied"):
            self.speaker("Pale Witness", "You brought me theft with your reverence and expect me to separate the two.")
        strain = self._conyberry_circuit_strain()
        if strain >= 2 and not delayed:
            self.speaker("Pale Witness", "You made the circuit wait like a claimant at a locked office and still expect witness from it.")
            self.say("The circuit is still holding, but not cleanly. The truth here already sounds like it had to cross damage to reach you.")
        dc = 14
        if self.act2_company_has("Elira Dawnmantle"):
            dc -= 1
            self.say("Elira's presence keeps the approach from sounding like another living theft of the dead.")
        if self.state.flags.get("conyberry_pilgrims_steadied"):
            dc -= 1
        if self.state.flags.get("conyberry_dead_named") or self.state.flags.get("conyberry_chapel_relit"):
            dc -= 1
        if self.state.flags.get("conyberry_sigil_copied"):
            dc += 1
        self.run_dialogue_input("act2_conyberry_entry")
        choice = self.scenario_choice(
            "How do you approach the Pale Witness's truth?",
            [
                self.quoted_option("PERSUASION", "We are not here to plunder your dead. We need the warning only you still remember."),
                self.quoted_option("RELIGION", "Tell me what vow was broken here, and what the living are about to repeat."),
                self.quoted_option("ARCANA", "If the cave's old song is changing, describe the change exactly."),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.player_speaker("We are not here to plunder your dead. We need the warning only you still remember.")
            success = self.skill_check(self.state.player, "Persuasion", dc, context="to keep Pale Witness listening instead of lashing out")
        elif choice == 2:
            self.player_speaker("Tell me what vow was broken here, and what the living are about to repeat.")
            success = self.skill_check(self.state.player, "Religion", dc, context="to name the old wrong cleanly enough for the dead")
        else:
            self.player_speaker("If the cave's old song is changing, describe the change exactly.")
            success = self.skill_check(self.state.player, "Arcana", dc, context="to understand Pale Witness's warning about the cave's altered resonance")
        if success and not delayed and strain <= 1:
            self.say(
                "The Pale Witness gives you a clean, terrible truth: Resonant Vaults' old song is being tuned into something quieter and hungrier, and a southern adit once used for labor now carries the cult's cleanest path."
            )
            self.add_clue(
                "The Pale Witness confirms the Quiet Choir is using a southern service adit to reach deeper workings beneath the Resonant Vaults."
            )
            self.state.flags["agatha_truth_clear"] = True
            if choice == 1:
                self.state.flags["agatha_public_warning_known"] = True
            elif choice == 2:
                self.state.flags["agatha_pact_restraint_known"] = True
            self.reward_party(xp=60, reason="earning the Pale Witness's full warning")
            self.act2_shift_metric(
                "act2_whisper_pressure",
                -1,
                "the Pale Witness's warning gives the company a truer picture of what the mine is doing",
            )
            if choice == 3:
                self.state.flags["agatha_public_warning_known"] = True
                self.act2_shift_metric(
                    "act2_route_control",
                    1,
                    "you translate the Pale Witness's warning into usable route logic instead of just dread",
                )
        elif success:
            self.say(
                "The Pale Witness still answers, but the warning reaches you through bruised magic: the southern adit is real, the Meridian Forge is being used as a listening lens, "
                "and whatever touched her circuit has already made the truth harder to hold cleanly."
            )
            self.add_clue(
                "Even damaged, the Pale Witness confirms the southern adit matters and the Meridian Forge is being tuned into something that listens back."
            )
            self.state.flags["agatha_truth_clear"] = False
            if choice == 1:
                self.state.flags["agatha_public_warning_known"] = True
            elif choice == 2:
                self.state.flags["agatha_pact_restraint_known"] = True
            self.reward_party(xp=45, reason="salvaging the Pale Witness's delayed warning")
        else:
            self.say(
                "The Pale Witness's scream never quite becomes violence, but the answer she leaves you is broken and cold: a warning about a 'quiet choir' and a road that should have stayed collapsed."
            )
            if not delayed:
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    1,
                    "the company leaves Hushfen with fear and fragments instead of a clean warning",
                )
        self._conyberry_exit_warning_choice(success=success, delayed=delayed)
        self.state.flags["agatha_truth_secured"] = True
        self.state.current_scene = "act2_expedition_hub"


