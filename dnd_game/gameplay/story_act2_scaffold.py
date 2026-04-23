from __future__ import annotations

from ..content import create_enemy, create_irielle_ashwake, create_nim_ardentglass
from .encounter import Encounter


class StoryAct2ScaffoldMixin:
    ACT2_BRANCH_FLAGS = (
        "agatha_truth_secured",
        "stonehollow_dig_cleared",
        "woodland_survey_cleared",
    )
    ACT2_BRANCH_LABELS = {
        "agatha_truth_secured": "Hushfen and the Pale Circuit",
        "stonehollow_dig_cleared": "Stonehollow Dig",
        "woodland_survey_cleared": "Greywake survey line",
    }
    ACT2_METRIC_NAMES = {
        "act2_town_stability": "Town Stability",
        "act2_route_control": "Route Control",
        "act2_whisper_pressure": "Whisper Pressure",
    }
    ACT2_METRIC_LIMITS = {
        "act2_town_stability": 5,
        "act2_route_control": 5,
        "act2_whisper_pressure": 5,
    }
    ACT2_METRIC_LABELS = {
        "act2_town_stability": ("Fractured", "Shaken", "Strained", "Holding", "Steady", "United"),
        "act2_route_control": ("Lost", "Thin", "Contested", "Firm", "Dominant", "Commanding"),
        "act2_whisper_pressure": ("Quieted", "Faint", "Present", "Growing", "Severe", "Overwhelming"),
    }
    ACT2_SPONSOR_LABELS = {
        "exchange": "Halia Vey's Exchange bloc",
        "lionshield": "Linene Ironward's disciplined supply line",
        "wardens": "Elira Lanternward and Daran Orchard's cautious wardens",
        "council": "a divided but cooperative council",
    }
    ACT2_FORGE_SUBROUTES = (
        ("forge_choir_pit_silenced", "silenced the choir pit"),
        ("forge_pact_rhythm_found", "recovered the Meridian Compact anvil's rhythm"),
        ("forge_shard_channels_disrupted", "shattered the shard channels"),
    )
    ACT2_MILESTONE_GEAR_IDS = (
        "delver_lantern_hood_uncommon",
        "forgehand_gauntlets_uncommon",
        "choirward_amulet_uncommon",
    )
    ACT2_RARE_ROUTE_GEAR_IDS = (
        "sigil_anchor_ring_rare",
        "choirward_amulet_rare",
        "delver_lantern_hood_rare",
        "forgehand_gauntlets_rare",
        "studded_leather_rare",
        "breastplate_rare",
        "chain_mail_rare",
        "splint_armor_rare",
        "shield_rare",
    )

    def act2_pick_enemy(self, templates, *, name: str | None = None):
        return create_enemy(self.rng.choice(tuple(templates)), name=name)

    def act2_award_milestone_gear(self, reward_flag: str, item_id: str, *, source: str) -> None:
        assert self.state is not None
        if self.state.flags.get(reward_flag):
            return
        if self.add_inventory_item(item_id, source=source):
            self.state.flags[reward_flag] = item_id

    def act2_stonehollow_milestone_item(self) -> str:
        assert self.state is not None
        if self.state.flags.get("stonehollow_ward_path_read") or self.state.flags.get("stonehollow_notes_preserved"):
            return "delver_lantern_hood_uncommon"
        return "forgehand_gauntlets_uncommon"

    def act2_black_lake_milestone_item(self) -> str:
        assert self.state is not None
        if self.state.flags.get("black_lake_shrine_purified") or self.act2_metric_value("act2_whisper_pressure") >= 4:
            return "sigil_anchor_ring_rare"
        return "fireward_elixir"

    def act2_party_has_strong_route_gear(self) -> bool:
        assert self.state is not None
        inventory = self.inventory_dict()
        if any(inventory.get(item_id, 0) > 0 for item_id in self.ACT2_RARE_ROUTE_GEAR_IDS):
            return True
        milestone_count = sum(inventory.get(item_id, 0) for item_id in self.ACT2_MILESTONE_GEAR_IDS)
        equipped_ids: list[str] = []
        for member in self.state.party_members():
            equipped_ids.extend(item_id for item_id in member.equipment_slots.values() if item_id is not None)
        if any(item_id in self.ACT2_RARE_ROUTE_GEAR_IDS for item_id in equipped_ids):
            return True
        milestone_count += sum(1 for item_id in equipped_ids if item_id in self.ACT2_MILESTONE_GEAR_IDS)
        return milestone_count >= 3

    def act2_branch_progress(self) -> int:
        assert self.state is not None
        return sum(1 for flag in self.ACT2_BRANCH_FLAGS if self.state.flags.get(flag))

    def act2_unresolved_early_leads(self) -> list[str]:
        assert self.state is not None
        return [flag for flag in self.ACT2_BRANCH_FLAGS if not self.state.flags.get(flag)]

    def act2_named_companion(self, name: str):
        finder = getattr(self, "find_companion", None)
        if not callable(finder):
            return None
        companion = finder(name)
        if companion is None or companion.dead:
            return None
        return companion

    def act2_company_has(self, name: str) -> bool:
        return self.act2_named_companion(name) is not None

    def act2_metric_value(self, metric_key: str) -> int:
        assert self.state is not None
        if metric_key not in self.state.flags:
            self.act2_initialize_metrics()
        return int(self.state.flags.get(metric_key, 0))

    def act2_metric_label(self, metric_key: str) -> str:
        value = max(0, min(self.act2_metric_value(metric_key), self.ACT2_METRIC_LIMITS[metric_key]))
        return self.ACT2_METRIC_LABELS[metric_key][value]

    def act2_join_phrases(self, phrases: list[str]) -> str:
        if not phrases:
            return ""
        if len(phrases) == 1:
            return phrases[0]
        if len(phrases) == 2:
            return f"{phrases[0]} and {phrases[1]}"
        return f"{', '.join(phrases[:-1])}, and {phrases[-1]}"

    def act2_forge_cleared_subroutes(self) -> list[str]:
        assert self.state is not None
        return [label for flag_name, label in self.ACT2_FORGE_SUBROUTES if self.state.flags.get(flag_name)]

    def act3_forge_cleared_subroute_labels(self) -> list[str]:
        assert self.state is not None
        labels_by_flag = dict(self.ACT2_FORGE_SUBROUTES)
        stored = self.state.flags.get("act3_forge_subroutes_cleared", [])
        if not isinstance(stored, list):
            return []
        labels: list[str] = []
        for flag_name in stored:
            if isinstance(flag_name, str):
                labels.append(labels_by_flag.get(flag_name, flag_name.replace("_", " ")))
        return labels

    def act2_forge_route_summary_line(self) -> str | None:
        assert self.state is not None
        cleared = self.act2_forge_cleared_subroutes()
        if not cleared and not self.state.flags.get("forge_threshold_crossed") and not self.state.flags.get("caldra_defeated"):
            return None
        if len(cleared) == 3:
            line = f"Inside the Meridian Forge, you {self.act2_join_phrases(cleared)} before Caldra could stabilize any of them."
        elif len(cleared) == 2:
            line = f"Inside the Meridian Forge, you {self.act2_join_phrases(cleared)} before the final fight, but one live subroute stayed dangerous to the end."
        elif len(cleared) == 1:
            line = f"Inside the Meridian Forge, you only {cleared[0]} before confronting Caldra directly."
        elif self.state.flags.get("caldra_defeated"):
            line = "Caldra fell before the Meridian Forge's side routes were fully broken, which left the chamber dangerous right up to the end."
        else:
            line = "The Meridian Forge threshold is breached, but most of its side routes are still live."
        if self.state.flags.get("forge_lens_mapped") and not self.state.flags.get("caldra_defeated"):
            return f"{line} The resonance lens is already mapped from inside."
        if self.state.flags.get("forge_lens_mapped") and self.state.flags.get("caldra_defeated"):
            return f"{line} You also mapped the resonance lens from inside before the chamber broke."
        return line

    def act3_forge_handoff_line(self) -> str | None:
        assert self.state is not None
        route_state = str(self.state.flags.get("act3_forge_route_state", "")).strip()
        lens_state = str(self.state.flags.get("act3_forge_lens_state", "")).strip()
        cleared = self.act3_forge_cleared_subroute_labels()
        if not route_state and not lens_state and not cleared:
            return None
        if route_state == "mastered" and cleared:
            line = f"Act 3 inherits a Meridian Forge where you already {self.act2_join_phrases(cleared)}."
        elif route_state == "broken" and cleared:
            line = f"Act 3 inherits a Meridian Forge where you already {self.act2_join_phrases(cleared)}, but one forge line still escaped a clean ruin."
        elif route_state == "partial" and cleared:
            line = f"Act 3 only inherits one clean break in the Meridian Forge: you {cleared[0]}."
        else:
            line = "Act 3 inherits the Meridian Forge mostly as aftermath rather than as a fully read instrument."
        if lens_state == "mapped":
            return f"{line} The mapped resonance lens gives later scenes a reliable read on how Caldra held witness, ritual, and shard pressure together."
        if lens_state == "shattered_blind":
            return f"{line} The lens broke before it could be fully read, so later scenes have to work from fallout, rumor, and surviving echoes."
        return line

    def act2_sponsor_fallout_line(self) -> str:
        assert self.state is not None
        sponsor = str(self.state.flags.get("act2_sponsor", "council"))
        claims_state = str(self.state.flags.get("act3_claims_balance", "contested"))
        forge_state = str(self.state.flags.get("act3_forge_route_state", "direct"))
        lens_state = str(self.state.flags.get("act3_forge_lens_state", "shattered_blind"))
        if sponsor == "exchange":
            if claims_state == "secured":
                line = "Halia Vey's Exchange bloc comes out of the cave with the fastest ledgers and the ugliest leverage over what Resonant Vaults becomes next."
            elif claims_state == "contested":
                line = "Halia still has crews, cash, and hard proof in the field, but every claim she makes now has witnesses arguing the moral cost."
            else:
                line = "Exchange money is still moving, but the claims race has slipped so far that Halia's grip looks more like opportunism than governance."
            if lens_state == "mapped":
                return f"{line} Her people are already talking about the mapped lens lines like inventory."
            if forge_state in {"partial", "direct"}:
                return f"{line} That ambition is still aimed at a Meridian Forge nobody fully unraveled."
            return f"{line} Even the Exchange cannot pretend the place is safe to own cleanly."
        if sponsor == "lionshield":
            if claims_state == "secured":
                line = "Linene Ironward's supply line ends the act controlling the practical routes, which steadies caravans and turns Resonant Vaults into guarded infrastructure."
            elif claims_state == "contested":
                line = "Linene can keep people fed and moving, but not settle whose version of the route gets called legitimate."
            else:
                line = "Ironbound discipline keeps some wagons moving, but not enough to make the claims war feel governed."
            if lens_state == "mapped":
                return f"{line} She starts treating the mapped lens lanes like hazardous cargo corridors that must stay locked down."
            if forge_state in {"partial", "direct"}:
                return f"{line} That order still stops at a Meridian Forge whose internals were never fully tamed."
            return f"{line} It is stability under quarantine, not a clean victory."
        if sponsor == "wardens":
            if claims_state == "secured":
                line = "Elira Lanternward and Daran Orchard come out with the strongest moral authority over the deepest routework, even if profit has to wait behind burial, warding, and witness."
            elif claims_state == "contested":
                line = "The wardens are trusted by the people who saw the worst of the cave, but not obeyed by everyone still counting ore and salvage."
            else:
                line = "The wardens are still right about the danger, but the aftermath is too splintered to let caution rule cleanly."
            if lens_state == "mapped":
                return f"{line} The mapped lens gives them a real case for quarantine instead of sounding like superstition."
            if forge_state in {"partial", "direct"}:
                return f"{line} Their warnings only sharpen because some of the Meridian Forge still had to be left half-read."
            return f"{line} Their victory reads as containment first and ownership a distant second."
        if claims_state == "secured":
            line = "The council stays barely cooperative because no single bloc can claim the whole win without the others."
        elif claims_state == "contested":
            line = "The council remains a bargaining table, not a verdict. Everyone has part of the truth and none of them trust the rest with all of it."
        else:
            line = "The council is still meeting, but mostly to stop rival claims from turning into open theft and panic."
        if lens_state == "mapped":
            return f"{line} The mapped resonance lens keeps at least one argument anchored in something concrete."
        if forge_state in {"partial", "direct"}:
            return f"{line} None of them get to speak as if the Meridian Forge was ever fully understood."
        return f"{line} The Meridian Forge's damage keeps any one faction from sounding fully triumphant."

    def act2_companion_digest_line(self) -> str | None:
        assert self.state is not None
        notes: list[str] = []
        nim = self.find_companion("Nim Ardentglass")
        if nim is not None:
            if nim in self.state.companions:
                notes.append("Nim Ardentglass is with the active party keeping the route notes honest")
            else:
                notes.append("Nim Ardentglass is at camp turning Stonehollow's salvage into usable maps")
        irielle = self.find_companion("Irielle Ashwake")
        if irielle is not None:
            irielle_line = "Irielle Ashwake is with the active party"
            if irielle not in self.state.companions:
                irielle_line = "Irielle Ashwake is at camp"
            if self.state.flags.get("south_adit_counter_cadence_learned") or self.state.flags.get("irielle_counter_cadence"):
                irielle_line += " carrying the adit's counter-cadence"
            else:
                irielle_line += " as one of the clearest witnesses against the Choir"
            notes.append(irielle_line)
        if not notes:
            return None
        return f"Company state: {'; '.join(notes)}."

    def act2_shift_metric(self, metric_key: str, delta: int, reason: str) -> None:
        assert self.state is not None
        if not delta:
            return
        current = self.act2_metric_value(metric_key)
        limit = self.ACT2_METRIC_LIMITS[metric_key]
        updated = max(0, min(limit, current + delta))
        if updated == current:
            return
        self.state.flags[metric_key] = updated
        direction = "rises" if updated > current else "falls"
        self.say(
            f"{self.ACT2_METRIC_NAMES[metric_key]} {direction} to {self.act2_metric_label(metric_key)} ({reason})."
        )

    def act2_adjust_named_companion(self, name: str, delta: int, reason: str) -> None:
        companion = self.act2_named_companion(name)
        if companion is None:
            return
        self.adjust_companion_disposition(companion, delta, reason)

    def act2_initialize_metrics(self, *, force: bool = False) -> None:
        assert self.state is not None
        if self.state.flags.get("act2_metrics_initialized") and not force:
            return
        town = 2
        route = 2
        whisper = 2
        if self.state.flags.get("steward_vow_made"):
            town += 1
        if self.state.flags.get("phandalin_council_seen"):
            town += 1
        if self.state.flags.get("elira_helped"):
            town += 1
            whisper -= 1
        if self.state.flags.get("miners_exchange_dispute_resolved"):
            route += 1
        if self.state.flags.get("miners_exchange_ledgers_checked"):
            route += 1
        early_recruit = self.state.flags.get("early_companion_recruited")
        if early_recruit == "Kaelis Starling":
            route += 1
        elif early_recruit == "Rhogar Valeguard":
            town += 1
        if self.act2_company_has("Bryn Underbough"):
            route += 1
        if self.act2_company_has("Tolan Ironshield"):
            town += 1
        if self.act2_company_has("Kaelis Starling"):
            route += 1
        if self.act2_company_has("Elira Dawnmantle"):
            whisper -= 1
        if self.state.flags.get("quest_reward_blackwake_watch_backing"):
            town += 1
            route += 1
        if self.state.flags.get("quest_reward_miners_road_open"):
            town += 1
            route += 1
        if self.state.flags.get("quest_reward_barthen_resupply_credit"):
            town += 1
        if self.state.flags.get("quest_reward_lionshield_logistics"):
            route += 1
        if self.state.flags.get("quest_reward_gravequiet_contacts"):
            whisper -= 1
        if self.state.flags.get("quest_reward_edermath_scout_network"):
            route += 1
        if self.state.flags.get("act2_edermath_cache_routework"):
            route += 1
        if self.state.flags.get("quest_reward_bryn_underworld_favor"):
            route += 1
        if self.state.flags.get("quest_reward_elira_mercy_blessing"):
            town += 1
            whisper -= 1
        if self.state.flags.get("neverwinter_contract_house_political_callback"):
            route += 1
        self.state.flags["act2_town_stability"] = max(0, min(5, town))
        self.state.flags["act2_route_control"] = max(0, min(5, route))
        self.state.flags["act2_whisper_pressure"] = max(0, min(5, whisper))
        self.state.flags.setdefault("act2_sponsor", "council")
        self.state.flags.setdefault("act2_captive_outcome", "uncertain")
        self.state.flags["act2_metrics_initialized"] = True

    def act2_initialize_blackwake_callbacks(self) -> None:
        assert self.state is not None
        if self.state.flags.get("neverwinter_contract_house_political_callback"):
            self.state.flags["act2_neverwinter_witness_pressure_active"] = True
            if not self.state.flags.get("act2_neverwinter_witness_callback_recorded"):
                self.state.flags["act2_neverwinter_witness_callback_recorded"] = True
                self.add_journal(
                    "Greywake callback: Oren, Sabra, Vessa, and Garren kept pressure on the false-manifest circuit, giving Act 2's route claims a stronger city-side witness line."
                )
        if self.state.flags.get("blackwake_sereth_fate") != "escaped":
            return
        self.state.flags["act2_sereth_shadow_active"] = True
        if self.state.flags.get("act2_sereth_callback_recorded"):
            return
        self.state.flags["act2_sereth_callback_recorded"] = True
        self.add_journal(
            "Blackwake consequence: Sereth Vane escaped into Act 2's route war; false permits and quiet cargo claims may surface again around Resonant Vaults."
        )

    def act2_late_route_hub_recap(self) -> str | None:
        assert self.state is not None
        first_late_route = str(self.state.flags.get("act2_first_late_route", "")).strip()
        if first_late_route == "broken_prospect":
            if self.state.flags.get("south_adit_cleared") and self.state.flags.get("act2_captive_outcome") == "few_saved":
                return "Broken Prospect went first, and South Adit never recovered cleanly from that delay."
            if self.state.flags.get("south_adit_cleared"):
                return "Broken Prospect went first, and South Adit had to be reclaimed after the damage was already in motion."
            return "Broken Prospect went first. South Adit is still paying for that delay."
        if first_late_route == "south_adit":
            if self.state.flags.get("broken_prospect_cleared"):
                return "South Adit went first, and Broken Prospect had to be recovered after the claims race tightened."
            return "South Adit went first. Broken Prospect is still hardening around that choice."
        return None

    def act2_campaign_focus_lines(self) -> list[str]:
        assert self.state is not None
        lines: list[str] = []
        first_late_route = str(self.state.flags.get("act2_first_late_route", "")).strip()
        if first_late_route == "broken_prospect":
            if self.state.flags.get("south_adit_cleared") and self.state.flags.get("act2_captive_outcome") == "few_saved":
                lines.append("Late-route commitment: Broken Prospect first; South Adit only yielded partial rescues.")
            elif self.state.flags.get("south_adit_cleared"):
                lines.append("Late-route commitment: Broken Prospect first; South Adit was recovered after the delay.")
            else:
                lines.append("Late-route commitment: Broken Prospect first; South Adit remains under delay pressure.")
        elif first_late_route == "south_adit":
            if self.state.flags.get("broken_prospect_cleared"):
                lines.append("Late-route commitment: South Adit first; Broken Prospect was recovered after the route race hardened.")
            else:
                lines.append("Late-route commitment: South Adit first; Broken Prospect is still hardening.")

        rescue_parts: list[str] = []
        if self.state.flags.get("stonehollow_scholars_found"):
            if self.state.flags.get("nim_countermeasure_notes") or self.state.flags.get("stonehollow_notes_preserved"):
                rescue_parts.append("Stonehollow scholars escaped with usable survey testimony")
            else:
                rescue_parts.append("Stonehollow survivors were pulled out alive")
        captive_outcome = str(self.state.flags.get("act2_captive_outcome", "uncertain"))
        if captive_outcome == "many_saved":
            rescue_parts.append("South Adit yielded many survivors")
        elif captive_outcome == "few_saved":
            rescue_parts.append("South Adit only yielded partial rescues")
        elif captive_outcome == "captives_endangered":
            rescue_parts.append("South Adit's captives are still endangered")
        if self.state.flags.get("irielle_contact_made"):
            irielle = self.find_companion("Irielle Ashwake")
            if irielle is None:
                rescue_parts.append("Irielle Ashwake escaped the adit and reached the wider company")
            elif irielle in self.state.companions:
                rescue_parts.append("Irielle Ashwake is traveling with the active party")
            else:
                rescue_parts.append("Irielle Ashwake is sheltering at camp with the company")
        if rescue_parts:
            lines.append(f"Rescue summary: {'; '.join(rescue_parts)}.")

        route_parts: list[str] = []
        if self.state.flags.get("act2_edermath_cache_routework"):
            route_parts.append("Daran's old cache map preserves a quiet orchard-to-highland control line")
        if self.state.flags.get("nim_countermeasure_notes"):
            route_parts.append("Nim's Stonehollow countermeasure notes survived")
        if self.state.flags.get("prospect_markers_decoded") or self.state.flags.get("prospect_route_cache_read"):
            route_parts.append("Broken Prospect exposed the deeper Meridian Compact approach")
        if self.state.flags.get("wave_echo_outer_cleared"):
            route_parts.append("the outer galleries now hold as a real expedition line")
        elif self.state.flags.get("outer_survey_marks_read") or self.state.flags.get("outer_false_echo_named"):
            route_parts.append("the outer galleries are starting to read cleanly")
        if self.state.flags.get("black_lake_crossed"):
            route_parts.append("the Blackglass threshold is open")
        elif self.state.flags.get("black_lake_shrine_purified") or self.state.flags.get("black_lake_barracks_raided"):
            route_parts.append("the Blackglass crossing is being prepared from multiple angles")
        if self.state.flags.get("forge_lens_mapped") and not self.state.flags.get("caldra_defeated"):
            route_parts.append("the Meridian Forge's resonance lens has been mapped from inside")
        elif self.state.flags.get("forge_threshold_crossed") and not self.state.flags.get("caldra_defeated"):
            route_parts.append("the Meridian Forge threshold is under direct pressure")
        elif self.state.flags.get("caldra_defeated"):
            route_parts.append("the Meridian Forge lens has been broken")
        if route_parts:
            lines.append(f"Route intelligence: {'; '.join(route_parts)}.")
        if self.state.flags.get("act2_sereth_shadow_active"):
            lines.append(
                "Blackwake callback: Sereth Vane escaped the crossing and remains a live route-corruption thread around Resonant Vaults supply claims."
            )
        if self.state.flags.get("act2_neverwinter_witness_pressure_active"):
            lines.append(
                "Greywake politics: Oren, Sabra, Vessa, and Garren are backing a city-side witness line against false manifests and copied road authority."
            )
        forge_route_line = self.act2_forge_route_summary_line()
        if forge_route_line is not None:
            lines.append(f"Forge route: {forge_route_line}")

        if (
            self.state.flags.get("quiet_choir_identified")
            or self.state.flags.get("south_adit_witness_found")
            or self.state.flags.get("south_adit_counter_cadence_learned")
            or self.state.flags.get("black_lake_barracks_orders_taken")
        ):
            choir_parts: list[str] = []
            if self.state.flags.get("quiet_choir_identified") or self.state.flags.get("south_adit_witness_found"):
                choir_parts.append("captives have named the Quiet Choir's prison cadence")
            if self.state.flags.get("south_adit_counter_cadence_learned"):
                choir_parts.append("Irielle's augur notes carry a counter-cadence into the forge route")
            if self.state.flags.get("black_lake_barracks_orders_taken"):
                choir_parts.append("barracks orders confirm the Meridian Forge reserve plan")
            lines.append(f"Choir intelligence: {'; '.join(choir_parts)}.")

        return lines

    def journal_snapshot_lines(self) -> list[str]:
        if self.state is None or not self.state.flags.get("act2_started"):
            return []
        return self.act2_campaign_focus_lines()

    def act2_camp_digest_lines(self) -> list[str]:
        assert self.state is not None
        if not self.state.flags.get("act2_started"):
            return []
        lines = [
            f"Town {self.act2_metric_value('act2_town_stability')}/5 ({self.act2_metric_label('act2_town_stability')}) | "
            f"Route {self.act2_metric_value('act2_route_control')}/5 ({self.act2_metric_label('act2_route_control')}) | "
            f"Whisper {self.act2_metric_value('act2_whisper_pressure')}/5 ({self.act2_metric_label('act2_whisper_pressure')})"
        ]
        late_route_recap = self.act2_late_route_hub_recap()
        if late_route_recap is not None:
            lines.append(late_route_recap)
        companion_line = self.act2_companion_digest_line()
        if companion_line is not None:
            lines.append(companion_line)
        focus_lines = [line for line in self.act2_campaign_focus_lines() if not line.startswith("Late-route commitment:")]
        lines.extend(focus_lines[:3])
        return lines[:5]

    def act2_campaign_snapshot_lines(self) -> list[str]:
        assert self.state is not None
        lines = [
            f"- Town Stability: {self.act2_metric_label('act2_town_stability')} ({self.act2_metric_value('act2_town_stability')}/5)",
            f"- Route Control: {self.act2_metric_label('act2_route_control')} ({self.act2_metric_value('act2_route_control')}/5)",
            f"- Whisper Pressure: {self.act2_metric_label('act2_whisper_pressure')} ({self.act2_metric_value('act2_whisper_pressure')}/5)",
            f"- Expedition sponsor: {self.ACT2_SPONSOR_LABELS.get(str(self.state.flags.get('act2_sponsor', 'council')), 'a loose council')}",
        ]
        delayed_lead = str(self.state.flags.get("act2_neglected_lead", "")).strip()
        if delayed_lead and delayed_lead != "none":
            resolved = bool(self.state.flags.get(delayed_lead))
            status = "recovered late" if resolved else "still unresolved"
            lines.append(f"- Delayed lead: {self.ACT2_BRANCH_LABELS[delayed_lead]} ({status})")
        lines.extend(f"- {line}" for line in self.act2_campaign_focus_lines())
        return lines

    def show_act2_campaign_status(self, *, banner: bool = True) -> None:
        if banner:
            self.banner("Act II Pressures")
        self.say(
            "Act 2 now tracks how well Iron Hollow holds together, how much of the expedition map your side controls, and how loudly the mine's wrong music is leaking into the campaign."
        )
        for line in self.act2_campaign_snapshot_lines():
            self.output_fn(line)

    def act2_commit_to_midpoint(self) -> None:
        assert self.state is not None
        if self.state.flags.get("act2_midpoint_locked"):
            return
        unresolved = self.act2_unresolved_early_leads()
        if not unresolved:
            self.state.flags["act2_neglected_lead"] = "none"
            self.say(
                "Because you did not leave a lead behind, the town enters sabotage night bruised but unusually prepared."
            )
            self.act2_shift_metric(
                "act2_town_stability",
                1,
                "all three outer leads were accounted for before the Quiet Choir struck",
            )
            self.act2_shift_metric(
                "act2_route_control",
                1,
                "every major approach was at least understood before the town had to react",
            )
        else:
            neglected = unresolved[0]
            self.state.flags["act2_neglected_lead"] = neglected
            self.add_journal(
                f"The party let {self.ACT2_BRANCH_LABELS[neglected]} drift while Iron Hollow braced for sabotage. The consequences landed before the lead could be recovered."
            )
            if neglected == "agatha_truth_secured":
                self.state.flags["agatha_circuit_defiled"] = True
                self.say(
                    "Without the Pale Witness's warning in hand, the Quiet Choir gets another night to work unchallenged around Hushfen. The town walks into the midpoint with less truth than it needed."
                )
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    1,
                    "the Pale Circuit was left unanswered long enough for the Choir to stain it",
                )
                self.act2_shift_metric(
                    "act2_route_control",
                    -1,
                    "the southern adit remains rumor instead of confirmed routework",
                )
            elif neglected == "woodland_survey_cleared":
                self.state.flags["midpoint_infiltrator_seeded"] = True
                self.say(
                    "Because the woodland saboteurs stayed active, the Quiet Choir gets knives, smoke, and lookout marks inside the town's first serious meeting."
                )
                self.act2_shift_metric(
                    "act2_town_stability",
                    -1,
                    "the unbroken wood line fed panic straight into Iron Hollow",
                )
                self.act2_shift_metric(
                    "act2_route_control",
                    -1,
                    "survey crews kept losing time and stores to the same hidden hands",
                )
            else:
                self.state.flags["stonehollow_notes_lost"] = True
                self.say(
                    "Stonehollow being left for later means maps and testimony arrive late, incomplete, or not at all. People still push toward the cave, but they do it with worse numbers in their hands."
                )
                self.act2_shift_metric(
                    "act2_route_control",
                    -1,
                    "Stonehollow's cleanest survey notes were not secured in time",
                )
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    1,
                    "the deeper dig had longer to sit under bad resonance without interruption",
                )
        self.state.flags["act2_midpoint_locked"] = True

    def act2_mark_late_route_choice(self, route_key: str) -> None:
        assert self.state is not None
        if self.state.flags.get("act2_first_late_route"):
            return
        self.state.flags["act2_first_late_route"] = route_key
        if route_key == "broken_prospect":
            self.add_journal(
                "You chose to secure the approach before the prison line. The route improves, but everyone knows the captives are still below."
            )
            self.act2_shift_metric(
                "act2_route_control",
                1,
                "your side secured the prospect approach before rival claimants could plant themselves there",
            )
            self.state.flags["act2_captive_outcome"] = "captives_endangered"
        else:
            self.add_journal(
                "You went for the prisoners before the cleaner cave approach. More people may live, but the claims race hardens while you are below."
            )
            self.act2_shift_metric(
                "act2_town_stability",
                1,
                "word spreads that you chose living prisoners over mining rights",
            )
            self.act2_shift_metric(
                "act2_whisper_pressure",
                -1,
                "the South Adit line is broken before the Choir can finish all its work there",
            )

    def confirm_act2_late_route_priority(self, route_key: str) -> bool:
        assert self.state is not None
        if self.state.flags.get("act2_first_late_route"):
            return True
        if route_key == "broken_prospect":
            self.say(
                "Choosing Broken Prospect first commits the expedition to the cleaner cave approach. Route control improves, "
                "but South Adit's prisoners remain below while the Choir keeps sorting them."
            )
            options = [
                self.action_option("Commit to Broken Prospect first."),
                self.action_option("Back to the expedition table."),
            ]
        else:
            self.say(
                "Choosing South Adit first puts living prisoners ahead of the route race. More captives may survive, "
                "but Broken Prospect will have longer to harden with rivals, sentries, and bad claims."
            )
            options = [
                self.action_option("Commit to South Adit first."),
                self.action_option("Back to the expedition table."),
            ]
        choice = self.scenario_choice(
            "This first late-route choice will change the other route. Proceed?",
            options,
            allow_meta=False,
        )
        return choice == 1

    def act2_set_midpoint_pattern(self, pattern_key: str) -> None:
        assert self.state is not None
        pattern_flags = {
            "hall": "pattern_preserves_institutions",
            "shrine": "pattern_preserves_people",
            "infiltrator": "pattern_hunts_systems",
        }
        for flag_name in pattern_flags.values():
            self.state.flags[flag_name] = False
        selected_flag = pattern_flags.get(pattern_key)
        if selected_flag is not None:
            self.state.flags[selected_flag] = True

    def act2_refresh_secret_handoff_flags(self) -> None:
        assert self.state is not None
        whisper = self.act2_metric_value("act2_whisper_pressure")
        counter_cadence_known = any(
            bool(self.state.flags.get(flag_name))
            for flag_name in (
                "counter_cadence_known",
                "south_adit_counter_cadence_learned",
                "irielle_counter_cadence",
                "act3_choir_cadence_known",
            )
        )
        if counter_cadence_known:
            self.state.flags["counter_cadence_known"] = True

        carries_signal = any(
            bool(self.state.flags.get(flag_name))
            for flag_name in (
                "act3_shard_notes_carried",
                "nim_countermeasure_notes",
                "act3_choir_cadence_known",
                "irielle_counter_cadence",
            )
        )
        self.state.flags["act3_signal_carried"] = bool(whisper >= 4 or carries_signal)

        if self.state.flags.get("forge_lens_mapped"):
            self.state.flags["act3_lens_understood"] = True
            self.state.flags.pop("act3_lens_blinded", None)
        elif self.state.flags.get("caldra_defeated"):
            self.state.flags["act3_lens_blinded"] = True
            self.state.flags.pop("act3_lens_understood", None)
        else:
            self.state.flags.pop("act3_lens_understood", None)
            self.state.flags.pop("act3_lens_blinded", None)

    def act2_record_epilogue_flags(self) -> None:
        assert self.state is not None
        town = self.act2_metric_value("act2_town_stability")
        route = self.act2_metric_value("act2_route_control")
        whisper = self.act2_metric_value("act2_whisper_pressure")
        forge_cleared = [flag_name for flag_name, _ in self.ACT2_FORGE_SUBROUTES if self.state.flags.get(flag_name)]
        self.state.flags["act3_phandalin_state"] = "united" if town >= 4 else "holding" if town >= 2 else "fractured"
        self.state.flags["act3_claims_balance"] = "secured" if route >= 4 else "contested" if route >= 2 else "chaotic"
        self.state.flags["act3_whisper_state"] = "contained" if whisper <= 1 else "lingering" if whisper <= 3 else "carried_out"
        self.state.flags["act3_forge_subroutes_cleared"] = forge_cleared
        if len(forge_cleared) == 3:
            self.state.flags["act3_forge_route_state"] = "mastered"
        elif len(forge_cleared) == 2:
            self.state.flags["act3_forge_route_state"] = "broken"
        elif len(forge_cleared) == 1:
            self.state.flags["act3_forge_route_state"] = "partial"
        else:
            self.state.flags["act3_forge_route_state"] = "direct"
        self.state.flags["act3_forge_lens_state"] = "mapped" if self.state.flags.get("forge_lens_mapped") else "shattered_blind"
        self.act2_refresh_secret_handoff_flags()

    def scene_stonehollow_dig(self) -> None:
        assert self.state is not None
        delayed = self.state.flags.get("act2_neglected_lead") == "stonehollow_dig_cleared"
        if not self.has_quest("rescue_stonehollow_scholars"):
            self.grant_quest("rescue_stonehollow_scholars")
        self.banner("Stonehollow Dig")
        self.say(
            "Stonehollow is a half-legitimate dig site turned excavation wound. Survey strings hang through damp air, "
            "collapsed supports choke the lower lane, and someone has been using the trapped scholars as unwilling map readers.",
            typed=True,
        )
        if delayed:
            self.say(
                "Coming here late means the place has had longer to collapse inward on both bodies and evidence. The lower notes are not all going to be recoverable now."
            )
        self.run_dialogue_input("act2_stonehollow_entry")
        enemies = [create_enemy("echo_sapper"), create_enemy("grimlock_tunneler")]
        if delayed:
            enemies.append(self.act2_pick_enemy(("survey_chain_revenant", "spectral_foreman")))
        elif len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("blackglass_listener", "ochre_slime", "acidmaw_burrower")))
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("grimlock_tunneler", "echo_sapper", "blackglass_listener")))
        choice = self.scenario_choice(
            "How do you stabilize the dig long enough to get people out?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Read the support lines and pick the one section that can still hold.")),
                self.skill_tag("ATHLETICS", self.action_option("Muscle the blockage open before the lower lane fully goes.")),
                self.skill_tag("ARCANA", self.action_option("Follow the echoing wards and find the scholars before the monsters do.")),
            ],
            allow_meta=False,
        )
        hero_bonus = self.apply_scene_companion_support("stonehollow_dig")
        if choice == 1:
            self.player_action("Read the support lines and pick the one section that can still hold.")
            if self.skill_check(self.state.player, "Investigation", 13, context="to read the dig braces under pressure"):
                hero_bonus += 1
                self.apply_status(enemies[0], "reeling", 1, source="a planned collapse")
                self.state.flags["stonehollow_supports_stabilized"] = True
        elif choice == 2:
            self.player_action("Muscle the blockage open before the lower lane fully goes.")
            if self.skill_check(self.state.player, "Athletics", 13, context="to clear the blockage in time"):
                hero_bonus += 2
                self.state.flags["stonehollow_lane_forced"] = True
        else:
            self.player_action("Follow the echoing wards and find the scholars before the monsters do.")
            if self.skill_check(self.state.player, "Arcana", 13, context="to track the scholars through residual Meridian Compact warding"):
                hero_bonus += 2
                enemies[-1].current_hp = max(1, enemies[-1].current_hp - 3)
                self.state.flags["stonehollow_ward_path_read"] = True
        outcome = self.run_encounter(
            Encounter(
                title="Stonehollow Breakout",
                description="The trapped dig is full of things that want the scholars silenced before they can finish reading the cave.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Stonehollow seals over the party and the missing scholars stay lost below.")
            return
        if outcome == "fled":
            self.state.current_scene = "act2_expedition_hub"
            self.say("You retreat from the dig before the collapse can trap everyone together.")
            return
        if not self.find_companion("Nim Ardentglass"):
            self.speaker(
                "Nim Ardentglass",
                "If you're the reason I'm not dying under my own survey notes, I should probably stop pretending I can solve Resonant Vaults by myself."
            )
            recruit = self.scenario_choice(
                "Nim gathers his satchel and looks between you and the ruined lane.",
                [
                    self.quoted_option("RECRUIT", "Then walk with us and keep the maps honest."),
                    self.quoted_option("SAFE", "Get back to Iron Hollow and recover. We can talk there."),
                ],
                allow_meta=False,
            )
            self.recruit_companion(create_nim_ardentglass())
            nim = self.find_companion("Nim Ardentglass")
            if delayed and nim is not None:
                self.adjust_companion_disposition(
                    nim,
                    -1,
                    "you came for Stonehollow late, after some of the cleanest notes were already gone",
                )
            if recruit == 2 and nim is not None and nim in self.state.companions:
                self.move_companion_to_camp(nim)
                self.say("Nim agrees to return to camp and organize whatever survey truth can still be salvaged.")
        self.state.flags["stonehollow_dig_cleared"] = True
        self.reward_party(xp=45, gold=10, reason="clearing Stonehollow Dig")
        self.act2_award_milestone_gear(
            "act2_stonehollow_milestone_gear",
            self.act2_stonehollow_milestone_item(),
            source="Stonehollow's recovered survey locker",
        )
        if delayed:
            self.act2_shift_metric(
                "act2_route_control",
                1,
                "you salvage enough of Stonehollow's survey work to stop the route picture from staying crippled",
            )
        else:
            self.act2_shift_metric(
                "act2_route_control",
                2,
                "the Stonehollow survey line finally belongs to people who plan to bring it back out alive",
            )
            if self.state.flags.get("stonehollow_ward_path_read"):
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    -1,
                    "reading the Meridian Compact warding correctly keeps one more part of the cave from teaching through panic",
                )
        self.state.current_scene = "act2_expedition_hub"

    def scene_act2_midpoint_convergence(self) -> None:
        assert self.state is not None
        self.act2_commit_to_midpoint()
        self.banner("Sabotage Night")
        self.say(
            "With at least two routes clarified, the town finally tries to hold a real claims meeting. That is when the Quiet Choir moves openly. "
            "Lanterns go out, storehouses catch in the wrong places, and somebody inside Iron Hollow is trying to turn panic into cover for a deeper strike.",
            typed=True,
        )
        neglected = str(self.state.flags.get("act2_neglected_lead", "none"))
        enemies = [create_enemy("claimbinder_notary"), create_enemy("choir_cartographer")]
        if neglected == "woodland_survey_cleared":
            enemies.append(self.act2_pick_enemy(("false_map_skirmisher", "expedition_reaver", "memory_taker_adept")))
        elif neglected == "stonehollow_dig_cleared":
            enemies.append(self.act2_pick_enemy(("blackglass_listener", "memory_taker_adept")))
        elif len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("false_map_skirmisher", "memory_taker_adept", "cult_lookout")))
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "false_map_skirmisher", "expedition_reaver")))
        if neglected == "agatha_truth_secured":
            self.apply_status(
                self.state.player,
                "reeling",
                1,
                source="walking blind into the riot without the Pale Witness's full warning",
            )
        if self.state.flags.get("conyberry_chapel_relit") and not self.state.flags.get("conyberry_chapel_pressure_payoff_applied"):
            self.state.flags["conyberry_chapel_pressure_payoff_applied"] = True
            self.state.flags["conyberry_chapel_sabotage_payoff"] = True
            self.say(
                "Pilgrims from Hushfen arrive with lamp discipline instead of rumor. The first fires of sabotage still start, but fewer frightened people turn them into a chorus."
            )
            self.act2_shift_metric(
                "act2_whisper_pressure",
                -1,
                "the relit Chapel of Lamps teaches Iron Hollow's frightened lanes how to move without joining the Choir's panic",
            )
        self.run_dialogue_input("act2_midpoint_counsel", max_entries=2)
        choice = self.scenario_choice(
            "What do you protect first when the sabotage breaks wide open?",
            [
                self.quoted_option("PERSUASION", "Hold the claims hall together. If the council breaks tonight, the mine owns the aftermath."),
                self.skill_tag("MEDICINE", self.action_option("Get to the shrine lane and keep the wounded and terrified from becoming a stampede.")),
                self.skill_tag("PERCEPTION", self.action_option("Find the infiltrator cell and cut out the real strike team before they vanish again.")),
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.act2_set_midpoint_pattern("hall")
        elif choice == 2:
            self.act2_set_midpoint_pattern("shrine")
        else:
            self.act2_set_midpoint_pattern("infiltrator")
        hero_bonus = 0
        if choice == 1:
            self.player_speaker("Hold the claims hall together. If the council breaks tonight, the mine owns the aftermath.")
            if self.skill_check(self.state.player, "Persuasion", 14, context="to keep the claims meeting from shattering under pressure"):
                hero_bonus = 1
                self.state.flags["act2_midpoint_priority"] = "hall"
                if self.state.flags.get("act2_sponsor") == "lionshield":
                    hero_bonus += 1
        elif choice == 2:
            self.player_action("Get to the shrine lane and keep the wounded and terrified from becoming a stampede.")
            if self.skill_check(self.state.player, "Medicine", 14, context="to turn a panicked fireline into an evacuation instead"):
                hero_bonus = 2
                self.state.flags["act2_midpoint_priority"] = "shrine"
                if self.state.flags.get("elira_town_lantern"):
                    hero_bonus += 1
        else:
            self.player_action("Find the infiltrator cell and cut out the real strike team before they vanish again.")
            if self.skill_check(self.state.player, "Perception", 14, context="to see through the sabotage pattern"):
                hero_bonus = 2
                self.apply_status(enemies[1], "surprised", 1, source="your clean read of the trap")
                self.state.flags["act2_midpoint_priority"] = "infiltrator"
                if self.state.flags.get("bryn_false_ledgers_salted"):
                    hero_bonus += 1
        outcome = self.run_encounter(
            Encounter(
                title="Midpoint: Sabotage Night",
                description="The Quiet Choir's local strike team tries to turn Iron Hollow's first united plan into a riot and a fire.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=14,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Iron Hollow loses its nerve and the expedition fractures before it can truly begin.")
            return
        if outcome == "fled":
            self.state.current_scene = "act2_expedition_hub"
            self.say("You pull the party clear, but the sabotage still scars the town.")
            return
        self.state.flags["claims_meet_held"] = True
        self.state.flags["phandalin_sabotage_resolved"] = True
        if choice == 1:
            self.say(
                "You keep the hall from breaking. People still shout, still grieve, still accuse, but the town does not fully lose the shape of a plan."
            )
            self.act2_shift_metric(
                "act2_town_stability",
                1,
                "the council stayed visible enough that panic never became the only voice in town",
            )
            if self.state.flags.get("midpoint_infiltrator_seeded"):
                self.state.flags["act2_infiltrator_escaped"] = True
                self.say("Even so, someone still slips the smoke with a packet of copied route notes and a better story than the truth deserved.")
                self.act2_shift_metric(
                    "act2_route_control",
                    -1,
                    "the infiltrator cell escapes with useful route scraps while your attention is on the hall",
                )
            self.act2_adjust_named_companion("Rhogar Valeguard", 1, "you chose to hold the town's center under pressure")
        elif choice == 2:
            self.say(
                "You choose people over procedure. The claims table is a mess by dawn, but the shrine lane is full of survivors who know exactly why they are still alive."
            )
            self.act2_shift_metric(
                "act2_town_stability",
                2,
                "saving the vulnerable first keeps Iron Hollow from remembering the mine as a thing that immediately demanded sacrifices",
            )
            self.act2_shift_metric(
                "act2_whisper_pressure",
                -1,
                "the Choir's chaos fails to turn fear into the clean reverence it wanted",
            )
            if self.state.flags.get("act2_sponsor") == "exchange":
                self.act2_shift_metric(
                    "act2_route_control",
                    -1,
                    "Halia's bloc loses papers, people, and patience while you ignore the claims books for the wounded",
                )
            self.act2_adjust_named_companion("Elira Dawnmantle", 1, "you chose living people over the claims race")
        else:
            self.say(
                "You go for the knives in the dark instead of the lanterns in the square. The strike team breaks, but the town has to feel the fear while you are elsewhere."
            )
            self.state.flags["act2_infiltrator_caught"] = True
            self.act2_shift_metric(
                "act2_route_control",
                2,
                "cutting out the infiltrator cell protects the route map from being rewritten in secret",
            )
            if not self.state.flags.get("midpoint_infiltrator_seeded"):
                self.act2_shift_metric(
                    "act2_town_stability",
                    -1,
                    "people remember how alone the square felt while the strike team was being hunted",
                )
            self.act2_adjust_named_companion("Bryn Underbough", 1, "you trusted her instincts about hidden knives and bad paperwork")
        self.reward_party(xp=50, gold=15, reason="holding Iron Hollow together through sabotage night")
        self.state.current_scene = "act2_expedition_hub"

    def scene_broken_prospect(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("act2_first_late_route"):
            self.act2_mark_late_route_choice("broken_prospect")
        delayed = self.state.flags.get("act2_first_late_route") == "south_adit"
        self.banner("Broken Prospect")
        self.say(
            "Broken Prospect is a jagged approach above the Resonant Vaults: half collapsed survey cut, half old dwarfwork scar, and now one more place where history is trying to decide which footsteps matter.",
            typed=True,
        )
        if delayed:
            self.say(
                "Because you chose the prison line first, rival crews and cult sentries have had longer to root themselves into the prospect shelves."
            )
        enemies = [create_enemy("animated_armor"), create_enemy("spectral_foreman")]
        if delayed or self.act2_metric_value("act2_route_control") <= 2:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "iron_prayer_horror", "obelisk_eye")))
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "grimlock_tunneler", "starblighted_miner")))
        choice = self.scenario_choice(
            "How do you make first contact with the cave approach?",
            [
                self.skill_tag("HISTORY", self.action_option("Call the old survey marks before the echoes lie about distance.")),
                self.skill_tag("STEALTH", self.action_option("Use the broken prospect ledge and slip past the first sentries.")),
                self.skill_tag("RELIGION", self.action_option("Steady the line before the dead memory of this place gets teeth.")),
            ],
            allow_meta=False,
        )
        hero_bonus = 0
        if self.state.flags.get("nim_countermeasure_notes"):
            hero_bonus += 1
            self.say("Nim's preserved theorem notes let you predict which part of the prospect's echo is honest and which part is bait.")
        if choice == 1:
            self.player_action("Call the old survey marks before the echoes lie about distance.")
            if self.skill_check(self.state.player, "History", 14, context="to use the Meridian Compact survey marks correctly"):
                hero_bonus += 2
        elif choice == 2:
            self.player_action("Use the broken prospect ledge and slip past the first sentries.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to slip into Resonant Vaults cleanly"):
                hero_bonus += 2
                self.apply_status(enemies[0], "surprised", 1, source="your ledge approach")
        else:
            self.player_action("Steady the line before the dead memory of this place gets teeth.")
            if self.skill_check(self.state.player, "Religion", 14, context="to keep the haunted threshold from owning the pace"):
                hero_bonus += 1
                self.apply_status(self.state.player, "blessed", 2, source="meeting the cave with deliberate faith")
        outcome = self.run_encounter(
            Encounter(
                title="Broken Prospect",
                description="The first Resonant Vaults guardians still answer old duties, even now that new masters are twisting them.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Resonant Vaults' threshold throws the company back into the dark above.")
            return
        if outcome == "fled":
            self.state.current_scene = "act2_expedition_hub"
            self.say("You withdraw from the cave mouth before the threshold can swallow the approach.")
            return
        self.state.flags["wave_echo_reached"] = True
        self.state.flags["broken_prospect_cleared"] = True
        if not self.has_quest("free_wave_echo_captives"):
            self.grant_quest("free_wave_echo_captives")
        if not self.has_quest("sever_quiet_choir"):
            self.grant_quest("sever_quiet_choir")
        self.act2_shift_metric(
            "act2_route_control",
            1,
            "the prospect approach now belongs to your side instead of whoever would have claimed it with confidence and bad intent",
        )
        if self.state.flags.get("act2_captive_outcome") == "captives_endangered":
            self.say(
                "The route is cleaner now, but nobody in camp mistakes that clean line for a moral victory while the South Adit still holds prisoners."
            )
        self.state.current_scene = "act2_expedition_hub"

    def scene_south_adit(self) -> None:
        assert self.state is not None
        if not self.state.flags.get("act2_first_late_route"):
            self.act2_mark_late_route_choice("south_adit")
        delayed = self.state.flags.get("act2_first_late_route") == "broken_prospect"
        if not self.has_quest("free_wave_echo_captives"):
            self.grant_quest("free_wave_echo_captives")
        if not self.has_quest("sever_quiet_choir"):
            self.grant_quest("sever_quiet_choir")
        self.banner("South Adit")
        self.say(
            "The southern workings smell like old iron, cold water, and fear kept quiet too long. Cells have been built into the support chambers. "
            "The Quiet Choir has not just occupied Resonant Vaults. It has been sorting people here.",
            typed=True,
        )
        if delayed:
            self.say(
                "Broken Prospect going first bought your side a cleaner route, but the adit has had longer to become a place of missing names and emptied cells."
            )
        self.run_dialogue_input("act2_south_adit_entry")
        enemies = [create_enemy("starblighted_miner"), create_enemy("choir_adept")]
        if delayed:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "oathbroken_revenant")))
        elif len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "choir_executioner")))
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("cult_lookout", "grimlock_tunneler", "starblighted_miner")))
        choice = self.scenario_choice(
            "How do you crack the prison line?",
            [
                self.skill_tag("SLEIGHT OF HAND", self.action_option("Open the cells quietly and arm the captives before the wardens know.")),
                self.skill_tag("INTIMIDATION", self.action_option("Hit the wardens hard enough that the prisoners remember your side instead.")),
                self.skill_tag("MEDICINE", self.action_option("Go for the weakest captives first and keep the line from becoming a slaughter.")),
            ],
            allow_meta=False,
        )
        hero_bonus = self.apply_scene_companion_support("south_adit")
        if self.state.flags.get("elira_field_lantern"):
            hero_bonus += 1
            self.say("Elira's field lantern turns the adit's worst silence from sacred to merely ugly.")
        if choice == 1:
            self.player_action("Open the cells quietly and arm the captives before the wardens know.")
            if self.skill_check(self.state.player, "Sleight of Hand", 14, context="to free the first prisoners without raising the line"):
                hero_bonus += 2
                self.apply_status(enemies[1], "surprised", 1, source="the cells opening behind them")
        elif choice == 2:
            self.player_action("Hit the wardens hard enough that the prisoners remember your side instead.")
            if self.skill_check(self.state.player, "Intimidation", 14, context="to crack the adit's prison discipline"):
                hero_bonus += 1
        else:
            self.player_action("Go for the weakest captives first and keep the line from becoming a slaughter.")
            if self.skill_check(self.state.player, "Medicine", 14, context="to keep the rescue from turning into a panic crush"):
                hero_bonus += 1
                self.apply_status(self.state.player, "blessed", 1, source="saving the vulnerable first")
        outcome = self.run_encounter(
            Encounter(
                title="South Adit Wardens",
                description="The prison line beneath Resonant Vaults tries to bury witnesses before the truth can get out.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The South Adit stays a prison and the captives disappear back into the dark.")
            return
        if outcome == "fled":
            self.state.current_scene = "act2_expedition_hub"
            self.say("You fall back from the adit before the rescue turns fatal.")
            return
        self.state.flags["south_adit_cleared"] = True
        self.state.flags["wave_echo_reached"] = True
        self.state.flags["quiet_choir_identified"] = True
        if delayed:
            self.state.flags["act2_captive_outcome"] = "few_saved"
            self.say(
                "You still free people, but too many cells are already empty for the party to pretend this delay was clean."
            )
        else:
            self.state.flags["act2_captive_outcome"] = "many_saved"
            self.act2_shift_metric(
                "act2_town_stability",
                1,
                "the rescue reaches town as proof that this expedition still remembers the people trapped under it",
            )
        if not self.has_companion("Irielle Ashwake"):
            self.speaker(
                "Irielle Ashwake",
                "If you were trying to prove there was still a side worth escaping to, this was a convincing way to do it."
            )
            recruit = self.scenario_choice(
                "A shaken tiefling augur stands among the freed captives, eyes fixed on the deeper dark.",
                [
                    self.quoted_option("RECRUIT", "Then come with us and help end the Choir properly."),
                    self.quoted_option("SAFE", "Get topside and breathe real air first. We will speak in camp."),
                ],
                allow_meta=False,
            )
            self.recruit_companion(create_irielle_ashwake())
            self.state.flags["counter_cadence_known"] = True
            irielle = self.find_companion("Irielle Ashwake")
            if irielle is not None and delayed:
                self.adjust_companion_disposition(
                    irielle,
                    -1,
                    "too many captives were left below long enough to vanish before you reached the adit",
                )
            elif irielle is not None:
                self.adjust_companion_disposition(
                    irielle,
                    1,
                    "you chose the prison line before the cleaner route race",
                )
            if recruit == 2 and irielle is not None and irielle in self.state.companions:
                self.move_companion_to_camp(irielle)
                self.say("Irielle agrees to reach camp first and share what she knows once she can think without whispering walls around her.")
        self.reward_party(xp=60, gold=18, reason="freeing the South Adit prisoners")
        self.act2_award_milestone_gear(
            "act2_south_adit_milestone_gear",
            "choirward_amulet_uncommon",
            source="the South Adit prisoner cache",
        )
        self.state.current_scene = "act2_expedition_hub"

    def scene_wave_echo_outer_galleries(self) -> None:
        assert self.state is not None
        self.banner("Resonant Vault Outer Galleries")
        self.say(
            "The outer galleries keep the mine's old grandeur and none of its safety. Echoing rails, broken cranes, and ancient runoffs "
            "turn every line of advance into a place where one mistake could still matter more than courage.",
            typed=True,
        )
        enemies = [create_enemy("resonance_leech"), create_enemy("grimlock_tunneler")]
        if self.act2_metric_value("act2_whisper_pressure") >= 4:
            enemies.append(self.act2_pick_enemy(("forge_echo_stalker", "blackglass_listener", "hookclaw_burrower")))
        elif self.act2_metric_value("act2_route_control") <= 2 or len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("echo_sapper", "hookclaw_burrower", "carrion_lash_crawler")))
        if len(self.state.party_members()) >= 4:
            enemies.append(self.act2_pick_enemy(("resonance_leech", "grimlock_tunneler", "survey_chain_revenant")))
        choice = self.scenario_choice(
            "How do you carry the company through the outer galleries?",
            [
                self.skill_tag("INVESTIGATION", self.action_option("Follow the survey marks and keep the old mine from lying about its own shape.")),
                self.skill_tag("SURVIVAL", self.action_option("Take the side-runs the grimlocks trust and beat them to the angle.")),
                self.skill_tag("ATHLETICS", self.action_option("Reopen the haul rail and force the cave to answer a direct advance.")),
            ],
            allow_meta=False,
        )
        hero_bonus = self.apply_scene_companion_support("wave_echo_outer_galleries")
        if choice == 1:
            self.player_action("Follow the survey marks and keep the old mine from lying about its own shape.")
            if self.skill_check(self.state.player, "Investigation", 14, context="to keep the party on the real line through false echoes"):
                hero_bonus += 2
        elif choice == 2:
            self.player_action("Take the side-runs the grimlocks trust and beat them to the angle.")
            if self.skill_check(self.state.player, "Survival", 14, context="to move like something that actually belongs underground"):
                hero_bonus += 2
                self.apply_status(enemies[0], "surprised", 1, source="you reached their angle first")
        else:
            self.player_action("Reopen the haul rail and force the cave to answer a direct advance.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to turn the broken rail into a fighting line instead of a hazard"):
                hero_bonus += 1
                self.apply_status(self.state.player, "emboldened", 2, source="forcing the galleries to take your pace")
        outcome = self.run_encounter(
            Encounter(
                title="Outer Gallery Pressure",
                description="Resonant Vaults' outer defenses are now a mix of scavengers, predators, and bad old engineering.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The outer galleries close around the party before the deeper route can be stabilized.")
            return
        if outcome == "fled":
            self.state.current_scene = "act2_expedition_hub"
            self.say("You retreat from the outer galleries to reset the approach.")
            return
        self.state.flags["wave_echo_outer_cleared"] = True
        self.reward_party(xp=50, gold=12, reason="forcing the outer galleries open")
        self.act2_shift_metric(
            "act2_route_control",
            1,
            "the company now owns a real line through Resonant Vaults' outer galleries",
        )
        self.state.current_scene = "act2_expedition_hub"

    def scene_black_lake_causeway(self) -> None:
        assert self.state is not None
        self.banner("Blackglass Causeway")
        self.say(
            "The old black water cuts the cave in half beneath a narrow causeway of stone and broken dwarfwork. A drowned shrine leans off one side. A cult barracks squats on the other. "
            "This is the last clean threshold before the Meridian Forge, and the Quiet Choir knows it.",
            typed=True,
        )
        self.run_dialogue_input("act2_black_lake_entry", max_entries=2)
        high_pressure = self.act2_metric_value("act2_whisper_pressure") >= 4
        bad_route = self.act2_metric_value("act2_route_control") <= 2
        strong_gear = self.act2_party_has_strong_route_gear()
        full_party = len(self.state.party_members()) >= 4
        enemies = [create_enemy("blacklake_adjudicator"), create_enemy("pact_archive_warden")]
        if full_party or high_pressure:
            enemies.append(self.act2_pick_enemy(("obelisk_chorister", "blackglass_listener", "blacklake_pincerling", "survey_chain_revenant")))
        if full_party and (bad_route or high_pressure or strong_gear):
            enemies.append(self.act2_pick_enemy(("starblighted_miner", "blackglass_listener", "pact_archive_warden")))
        choice = self.scenario_choice(
            "What do you claim on the way across the lake?",
            [
                self.skill_tag("RELIGION", self.action_option("Reclaim the drowned shrine and force some older sanctity back into the crossing.")),
                self.skill_tag("STEALTH", self.action_option("Strip the cult barracks first and cut their messengers and reserves out from under them.")),
                self.skill_tag("ATHLETICS", self.action_option("Sabotage the causeway anchors and fight while the whole line trembles.")),
            ],
            allow_meta=False,
        )
        hero_bonus = 1
        if choice == 1:
            self.player_action("Reclaim the drowned shrine and force some older sanctity back into the crossing.")
            if self.skill_check(self.state.player, "Religion", 14, context="to wake the shrine before the Choir notices what you are doing"):
                hero_bonus += 1
                self.state.flags["black_lake_shrine_purified"] = True
                self.apply_status(self.state.player, "blessed", 2, source="the reclaimed shrine")
                self.act2_shift_metric(
                    "act2_whisper_pressure",
                    -1,
                    "the drowned shrine answers before the forge can drown it entirely in the Choir's rhythm",
                )
        elif choice == 2:
            self.player_action("Strip the cult barracks first and cut their messengers and reserves out from under them.")
            if self.skill_check(self.state.player, "Stealth", 14, context="to gut the barracks without losing the crossing"):
                hero_bonus += 2
                self.state.flags["black_lake_barracks_raided"] = True
                self.act2_shift_metric(
                    "act2_route_control",
                    1,
                    "you seize the last organized staging point before the Meridian Forge itself",
                )
        else:
            self.player_action("Sabotage the causeway anchors and fight while the whole line trembles.")
            if self.skill_check(self.state.player, "Athletics", 14, context="to break the line's stability without dropping your own company with it"):
                hero_bonus += 2
                self.state.flags["black_lake_causeway_shaken"] = True
                self.apply_status(enemies[0], "prone", 1, source="the causeway lurching under your sabotage")
        outcome = self.run_encounter(
            Encounter(
                title="Blackglass Causeway",
                description="Constructs, corrupted miners, and old command echoes try to stop the final approach.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=False,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("The causeway becomes a kill lane and the Meridian Forge remains out of reach.")
            return
        if outcome == "fled":
            self.state.current_scene = "act2_expedition_hub"
            self.say("You withdraw from the causeway before the line fully collapses around you.")
            return
        self.state.flags["black_lake_crossed"] = True
        self.reward_party(xp=55, gold=15, reason="crossing the Blackglass causeway")
        self.act2_award_milestone_gear(
            "act2_black_lake_milestone_gear",
            self.act2_black_lake_milestone_item(),
            source="the Blackglass reliquary",
        )
        self.state.current_scene = "act2_expedition_hub"

    def scene_forge_of_spells(self) -> None:
        assert self.state is not None
        self.banner("Meridian Forge")
        self.say(
            "The Meridian Forge is no longer just a lost wonder. The Quiet Choir has turned it into an instrument. "
            "Shards hum inside old channels, the air sounds wrong when it moves, and Sister Caldra Voss stands where ancient craft meets a much newer hunger.",
            typed=True,
        )
        high_pressure = self.act2_metric_value("act2_whisper_pressure") >= 4
        hard_route = self.act2_metric_value("act2_route_control") <= 2 or self.act2_party_has_strong_route_gear()
        full_party = len(self.state.party_members()) >= 4
        enemies = [create_enemy("caldra_voss"), create_enemy("obelisk_chorister")]
        if full_party:
            enemies.append(self.act2_pick_enemy(("forge_echo_stalker", "memory_taker_adept", "choir_executioner")))
        if self.state.flags.get("black_lake_barracks_raided") and full_party and (hard_route or high_pressure):
            enemies.append(self.act2_pick_enemy(("memory_taker_adept", "forge_echo_stalker")))
        elif not self.state.flags.get("black_lake_barracks_raided"):
            enemies.append(self.act2_pick_enemy(("memory_taker_adept", "choir_executioner", "starblighted_miner")))
        if high_pressure:
            enemies.append(self.act2_pick_enemy(("forge_echo_stalker", "obelisk_eye", "covenant_breaker_wight")))
        if self.state.flags.get("black_lake_shrine_purified"):
            self.apply_status(self.state.player, "blessed", 2, source="the reclaimed Blackglass shrine")
        self.speaker("Sister Caldra Voss", "The Forge does not create. It clarifies.")
        self.speaker("Sister Caldra Voss", "Every vow has an echo. Every echo has an owner.")
        self.speaker("Sister Caldra Voss", "The world is loud because it fears being counted.")
        self.run_dialogue_input("act2_forge_entry", max_entries=2)
        choice = self.scenario_choice(
            "How do you open the final confrontation?",
            [
                self.quoted_option("ARCANA", "Break her ritual tempo before she finishes tuning the forge."),
                self.quoted_option("PERSUASION", "You have seen enough of what the Choir calls revelation. Step away from the forge."),
                self.action_option("Hit the chamber hard and trust momentum before the whispers settle in."),
            ],
            allow_meta=False,
        )
        hero_bonus = self.apply_scene_companion_support("forge_of_spells")
        if self.state.flags.get("irielle_counter_cadence"):
            self.state.flags["counter_cadence_known"] = True
            hero_bonus += 1
            enemies[0].current_hp = max(1, enemies[0].current_hp - 4)
            self.say("Irielle's counter-cadence lands first and steals part of the forge's certainty before steel ever crosses it.")
        if choice == 1:
            dc = 15
            if self.state.flags.get("agatha_truth_clear"):
                dc -= 1
            if self.state.flags.get("nim_countermeasure_notes"):
                dc -= 1
            self.player_speaker("Break her ritual tempo before she finishes tuning the forge.")
            if self.skill_check(self.state.player, "Arcana", dc, context="to disrupt the forge-channel harmony"):
                hero_bonus += 2
                enemies[0].current_hp = max(1, enemies[0].current_hp - 6)
        elif choice == 2:
            dc = 15
            if self.state.flags.get("act2_captive_outcome") == "many_saved":
                dc -= 1
            if self.find_companion("Irielle Ashwake") is not None:
                dc -= 1
            self.player_speaker("You have seen enough of what the Choir calls revelation. Step away from the forge.")
            if self.skill_check(self.state.player, "Persuasion", dc, context="to force even a moment of doubt into Caldra's certainty"):
                hero_bonus += 1
                self.apply_status(enemies[1], "frightened", 1, source="hearing the certainty crack")
        else:
            self.player_action("Hit the chamber hard and trust momentum before the whispers settle in.")
            hero_bonus += 2
            self.apply_status(self.state.player, "emboldened", 2, source="storming the Meridian Forge")
            if self.state.flags.get("act2_sponsor") == "lionshield":
                hero_bonus += 1
        outcome = self.run_encounter(
            Encounter(
                title="Boss: Sister Caldra Voss",
                description="The Quiet Choir's cult agent makes the final stand at the Meridian Forge.",
                enemies=enemies,
                allow_flee=True,
                allow_parley=True,
                parley_dc=15,
                hero_initiative_bonus=hero_bonus,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.handle_defeat("Caldra holds the Meridian Forge and the mine's song bends further away from anything mortal should trust.")
            return
        if outcome == "fled":
            self.state.current_scene = "act2_expedition_hub"
            self.say("You tear yourself out of the forge chamber before the whole room can close around the party.")
            return
        self.state.flags["caldra_defeated"] = True
        self.add_clue("Caldra's notes describe the Meridian Forge as only a lens. Whatever the Quiet Choir truly serves is deeper, older, and not confined to the mine.")
        if self.act2_metric_value("act2_whisper_pressure") >= 4:
            self.add_clue(
                "Even broken, the Meridian Forge keeps trying to answer a call from farther down. The party is not leaving Resonant Vaults with clean silence."
            )
        self.reward_party(xp=120, gold=40, reason="breaking the Quiet Choir's Resonant Vaults cell")
        self.act2_record_epilogue_flags()
        self.state.current_scene = "act2_expedition_hub"

    def scene_act2_scaffold_complete(self) -> None:
        assert self.state is not None
        self.act2_record_epilogue_flags()
        self.banner("Act II Complete")
        town_state = self.state.flags.get("act3_phandalin_state", "holding")
        claims_state = self.state.flags.get("act3_claims_balance", "contested")
        whisper_state = self.state.flags.get("act3_whisper_state", "lingering")
        forge_state = str(self.state.flags.get("act3_forge_route_state", "direct"))
        captive_outcome = str(self.state.flags.get("act2_captive_outcome", "uncertain"))
        if town_state == "united":
            town_line = "Iron Hollow comes through the act bloodied but unmistakably more united than it began."
        elif town_state == "holding":
            town_line = "Iron Hollow survives, but in the careful, tired way frontier towns survive when everyone is counting what almost went worse."
        else:
            town_line = "Iron Hollow survives in pieces. The town still stands, but the act leaves strain that Act 3 can exploit."
        claims_line = self.act2_sponsor_fallout_line()
        if whisper_state == "contained":
            whisper_line = "You kept the mine's wrong music from spreading far past the cave."
        elif whisper_state == "lingering":
            whisper_line = "You stopped Caldra, but the song under Resonant Vaults is still following somebody home in fragments."
        else:
            whisper_line = "You won the act, but not cleanly. The mine's whisper-pressure leaves the cave with you, which is exactly what Act 3 wants."
        if captive_outcome == "many_saved":
            captive_line = "Word of the South Adit rescue becomes one of the few uncomplicated pieces of hope the act leaves behind."
        elif captive_outcome == "few_saved":
            captive_line = "The rescue still matters, but too many missing names follow the company back out of the adit."
        else:
            captive_line = "The prisoners were never the only stakes, but they proved who the party believed the cave was for."
        forge_line = self.act2_forge_route_summary_line()
        if forge_line is None:
            if forge_state == "mastered":
                forge_line = "You broke the Meridian Forge so thoroughly that even its side routes end the act sounding more like ruined craft than living doctrine."
            elif forge_state == "broken":
                forge_line = "You broke enough of the Meridian Forge's side routes that Act 3 inherits a damaged instrument instead of a clean weapon."
            elif forge_state == "partial":
                forge_line = "You hurt the Meridian Forge badly, but one surviving side route still shapes how dangerous its aftermath will be."
            else:
                forge_line = "You reached Caldra directly, which saved the act but left the Meridian Forge's side wounds less thoroughly explored."
        handoff_line = self.act3_forge_handoff_line()
        self.say(
            town_line,
            typed=True,
        )
        self.say(claims_line)
        self.say(whisper_line)
        self.say(captive_line)
        self.say(forge_line)
        if handoff_line is not None:
            self.say(handoff_line)
        if 2 not in self.state.completed_acts:
            self.state.completed_acts.append(2)
        self.state.current_act = 2
        saver = getattr(self, "save_game", None)
        if callable(saver):
            saver(slot_name=f"{self.state.player.name}_act2_complete")
        choice = self.choose(
            "What next?",
            [
                "Review the party",
                "Return to the title screen",
            ],
            allow_meta=False,
        )
        if choice == 1:
            self.show_party()
        self.state = None

