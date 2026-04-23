from __future__ import annotations

from ..content import create_enemy
from ..data.story.public_terms import marks_label
from .encounter import Encounter


POST_COMBAT_RANDOM_ENCOUNTER_CHANCE = 0.65
ACT_1_POST_COMBAT_RANDOM_ENCOUNTERS: tuple[tuple[str, str, str], ...] = (
    ("locked_chest_under_ferns", "Locked Chest Under the Ferns", "random_encounter_locked_chest_under_ferns"),
    ("abandoned_cottage", "Abandoned Cottage", "random_encounter_abandoned_cottage"),
    ("bandit_toll_line", "Bandit Toll Line", "random_encounter_bandit_toll_line"),
    ("wounded_messenger", "Wounded Messenger", "random_encounter_wounded_messenger"),
    ("messenger_returns_with_reward", "Messenger Returns", "random_encounter_messenger_returns_with_reward"),
    ("hunter_snare", "Hunter's Snare", "random_encounter_hunter_snare"),
    ("lone_wolf", "Lone Wolf at the Kill", "random_encounter_lone_wolf"),
    ("smuggler_cookfire", "Smuggler Cookfire", "random_encounter_smuggler_cookfire"),
    ("smuggler_revenge_squad", "Smuggler Revenge Squad", "random_encounter_smuggler_revenge_squad"),
    ("shrine_of_tymora", "Shrine of Tymora", "random_encounter_shrine_of_tymora"),
    ("half_sunk_satchel", "Half-Sunk Satchel", "random_encounter_half_sunk_satchel"),
    ("ruined_wayhouse", "Ruined Wayhouse", "random_encounter_ruined_wayhouse"),
    ("scavenger_cart", "Scavenger Cart", "random_encounter_scavenger_cart"),
    ("loose_flagstones", "Loose Flagstones", "random_encounter_loose_flagstones"),
    ("frightened_draft_horse", "Frightened Draft Horse", "random_encounter_frightened_draft_horse"),
    ("rain_barrel_cache", "Rain Barrel Cache", "random_encounter_rain_barrel_cache"),
    ("watchfire_embers", "Watchfire Embers", "random_encounter_watchfire_embers"),
    ("broken_milestone", "Broken Milestone", "random_encounter_broken_milestone"),
)
ACT_2_POST_COMBAT_RANDOM_ENCOUNTERS: tuple[tuple[str, str, str], ...] = (
    ("echoing_supply_cache", "Echoing Supply Cache", "random_encounter_act2_scaffold"),
    ("whispering_lantern", "Whispering Lantern", "random_encounter_act2_scaffold"),
    ("collapsed_ore_sled", "Collapsed Ore Sled", "random_encounter_act2_scaffold"),
    ("silent_prayer_wall", "Silent Prayer Wall", "random_encounter_act2_scaffold"),
    ("flooded_tool_chest", "Flooded Tool Chest", "random_encounter_act2_scaffold"),
    ("surveyor_ghostlight", "Surveyor Ghostlight", "random_encounter_act2_scaffold"),
    ("stolen_claim_markers", "Stolen Claim Markers", "random_encounter_act2_scaffold"),
    ("blackwater_drifter", "Blackwater Drifter", "random_encounter_act2_scaffold"),
    ("chain_drag_tunnel", "Chain-Drag Tunnel", "random_encounter_act2_scaffold"),
    ("mushroom_bloom_hall", "Mushroom Bloom Hall", "random_encounter_act2_scaffold"),
    ("shattered_foreman_bell", "Shattered Foreman Bell", "random_encounter_act2_scaffold"),
    ("hidden_prisoner_note", "Hidden Prisoner Note", "random_encounter_act2_scaffold"),
    ("obsidian_shard_outcrop", "Obsidian Shard Outcrop", "random_encounter_act2_scaffold"),
    ("broken_lift_cradle", "Broken Lift Cradle", "random_encounter_act2_scaffold"),
    ("hushed_campfire", "Hushed Campfire", "random_encounter_act2_scaffold"),
    ("false_route_beacon", "False-Route Beacon", "random_encounter_act2_scaffold"),
    ("choir_map_ambush", "Choir Map Ambush", "random_encounter_act2_scaffold"),
    ("resonance_bleed_pool", "Resonance Bleed Pool", "random_encounter_act2_scaffold"),
    ("black_lake_verdict", "Black Lake Verdict", "random_encounter_act2_scaffold"),
    ("forge_heatshadow", "Forge Heatshadow", "random_encounter_act2_scaffold"),
)
ACT_3_POST_COMBAT_RANDOM_ENCOUNTERS: tuple[tuple[str, str, str], ...] = ()

POST_COMBAT_RANDOM_ENCOUNTERS = ACT_1_POST_COMBAT_RANDOM_ENCOUNTERS


class RandomEncounterMixin:
    def post_combat_random_encounter_entries(self) -> tuple[tuple[str, str, str], ...]:
        if self.state is None:
            return ACT_1_POST_COMBAT_RANDOM_ENCOUNTERS
        if self.state.current_act >= 3:
            return ACT_3_POST_COMBAT_RANDOM_ENCOUNTERS
        if self.state.current_act == 2:
            return ACT_2_POST_COMBAT_RANDOM_ENCOUNTERS
        return ACT_1_POST_COMBAT_RANDOM_ENCOUNTERS

    def post_combat_random_encounter_ids(self) -> list[str]:
        return [encounter_id for encounter_id, _, _ in self.post_combat_random_encounter_entries()]

    def random_encounter_intro(self, text: str) -> None:
        self.say(text, typed=True)

    def random_encounter_unlocked(self, encounter_id: str) -> bool:
        if self.state is None:
            return True
        if encounter_id == "messenger_returns_with_reward":
            return bool(self.state.flags.get("saved_wounded_messenger")) and not bool(self.state.flags.get("messenger_return_paid"))
        if encounter_id == "smuggler_revenge_squad":
            return bool(self.state.flags.get("smuggler_revenge_pending")) and not bool(self.state.flags.get("smuggler_revenge_resolved"))
        if encounter_id == "resonance_bleed_pool":
            return bool(self.state.flags.get("stonehollow_dig_cleared") or self.state.flags.get("wave_echo_reached"))
        if encounter_id == "black_lake_verdict":
            return bool(self.state.flags.get("wave_echo_outer_cleared") or self.state.flags.get("black_lake_crossed"))
        if encounter_id == "forge_heatshadow":
            return bool(self.state.flags.get("black_lake_crossed"))
        return True

    def weighted_post_combat_random_encounter_pool(self) -> list[tuple[str, str, str]]:
        entries = list(self.post_combat_random_encounter_entries())
        if self.state is None:
            return entries
        seen = set(self.state.flags.get("random_encounters_seen", []))
        weighted: list[tuple[str, str, str]] = []
        for encounter in entries:
            encounter_id = encounter[0]
            if not self.random_encounter_unlocked(encounter_id):
                continue
            weight = 1 if encounter_id in seen else 10
            weighted.extend([encounter] * weight)
        return weighted

    def maybe_run_post_combat_random_encounter(self, source_encounter: Encounter) -> None:
        if self.state is None or not getattr(source_encounter, "allow_post_combat_random_encounter", True):
            return
        if self.rng.random() > POST_COMBAT_RANDOM_ENCOUNTER_CHANCE:
            return
        pool = self.weighted_post_combat_random_encounter_pool()
        if not pool:
            return
        encounter_id, _, _ = self.rng.choice(pool)
        self.run_named_post_combat_random_encounter(encounter_id)

    def run_named_post_combat_random_encounter(self, encounter_id: str) -> None:
        if self.state is None:
            return
        all_entries = (
            *ACT_1_POST_COMBAT_RANDOM_ENCOUNTERS,
            *ACT_2_POST_COMBAT_RANDOM_ENCOUNTERS,
            *ACT_3_POST_COMBAT_RANDOM_ENCOUNTERS,
        )
        for current_id, title, handler_name in all_entries:
            if current_id != encounter_id:
                continue
            seen = self.state.flags.setdefault("random_encounters_seen", [])
            if encounter_id not in seen:
                seen.append(encounter_id)
            play_music_for_context = getattr(self, "play_music_for_context", None)
            refresh_scene_music = getattr(self, "refresh_scene_music", None)
            if callable(play_music_for_context):
                play_music_for_context("random_encounter", restart=True)
            try:
                self._random_encounter_active = True
                self.banner(f"After the Battle: {title}")
                if handler_name == "random_encounter_act2_scaffold":
                    self.random_encounter_act2_scaffold(encounter_id)
                else:
                    getattr(self, handler_name)()
            finally:
                self._random_encounter_active = False
                if callable(refresh_scene_music):
                    refresh_scene_music()
            return
        raise ValueError(f"Unknown post-combat random encounter '{encounter_id}'.")

    def grant_random_encounter_rewards(
        self,
        *,
        reason: str,
        gold: int = 0,
        items: dict[str, int] | None = None,
    ) -> None:
        assert self.state is not None
        if gold > 0:
            self.state.gold += gold
            self.say(f"You secure {marks_label(gold)} from {reason}.")
            self.pause_for_loot_reveal()
        for item_id, quantity in (items or {}).items():
            added = self.add_inventory_item(item_id, quantity, source=reason)
            if added or quantity:
                self.pause_for_loot_reveal()

    def suffer_random_encounter_damage(self, target, amount: int, *, damage_type: str = "", source: str = "") -> int:
        if target.dead or target.current_hp <= 1:
            if source:
                self.say(source)
            return 0
        actual = min(max(1, amount), target.current_hp - 1)
        target.current_hp -= actual
        prefix = f"{source} " if source else ""
        typed = f" {damage_type}" if damage_type else ""
        self.say(f"{prefix}{self.style_name(target)} takes {self.style_damage(actual)}{typed} damage.")
        return actual

    def random_bandit_pair(self) -> list:
        assert self.state is not None
        enemies = [create_enemy("bandit")]
        if len(self.state.party_members()) >= 3:
            enemies.append(create_enemy("bandit_archer"))
        return enemies

    def random_goblin_pair(self) -> list:
        assert self.state is not None
        enemies = [create_enemy("goblin_skirmisher")]
        if len(self.state.party_members()) >= 3:
            enemies.append(create_enemy("goblin_skirmisher", name="Goblin Scavenger"))
        return enemies

    def resolve_random_encounter_fight(
        self,
        *,
        title: str,
        description: str,
        enemies: list,
        allow_parley: bool = True,
        parley_dc: int = 13,
        setback_text: str = "",
        flee_text: str = "",
    ) -> str:
        assert self.state is not None
        outcome = self.run_encounter(
            Encounter(
                title=title,
                description=description,
                enemies=enemies,
                allow_flee=True,
                allow_parley=allow_parley,
                parley_dc=parley_dc,
                allow_post_combat_random_encounter=False,
            )
        )
        if outcome == "defeat":
            self.recover_after_battle()
            gold_loss = min(self.state.gold, self.rng.randint(2, 8))
            if gold_loss > 0:
                self.state.gold -= gold_loss
                self.say(
                    setback_text
                    or f"The side skirmish leaves the party bloodied, and the victors strip away {marks_label(gold_loss)} before scattering."
                )
            else:
                self.say(setback_text or "The side skirmish leaves the party bloodied, but the attackers vanish before they can do worse.")
        elif outcome == "fled":
            self.say(flee_text or "You break away before the surprise clash can turn uglier.")
        return outcome

    def random_encounter_act2_scaffold(self, encounter_id: str) -> None:
        assert self.state is not None
        if encounter_id == "false_route_beacon":
            self.random_encounter_intro(
                "A route beacon ahead glows too cleanly for a cave this wet, and the claim ribbons tied around it point three different directions at once."
            )
            enemies = [create_enemy("false_map_skirmisher")]
            if len(self.state.party_members()) >= 4 or int(self.state.flags.get("act2_route_control", 2)) <= 2:
                enemies.append(create_enemy("claimbinder_notary"))
            else:
                enemies.append(create_enemy("expedition_reaver"))
            outcome = self.resolve_random_encounter_fight(
                title="False-Route Beacon",
                description="A sabotage team tries to turn the next route correction into a killing lane.",
                enemies=enemies,
                parley_dc=14,
                setback_text="The beacon team cuts the route sign, steals a little coin, and leaves the company following the wrong map for an ugly half hour.",
                flee_text="You back off before the false-route team can drag the whole fight onto their prepared line.",
            )
            if outcome == "victory":
                self.grant_random_encounter_rewards(
                    reason="the false-route beacon",
                    gold=6,
                    items={"delvers_amber": 1},
                )
            return
        if encounter_id == "choir_map_ambush":
            self.random_encounter_intro(
                "Pinned under a shard spike, you find half-burned survey sheets that only make sense once the ambushers waiting for you decide the reading is over."
            )
            enemies = [create_enemy("choir_cartographer")]
            if len(self.state.party_members()) >= 4:
                enemies.append(create_enemy("memory_taker_adept"))
            else:
                enemies.append(create_enemy("cult_lookout"))
            if int(self.state.flags.get("act2_whisper_pressure", 2)) >= 4 and len(self.state.party_members()) >= 4:
                enemies.append(create_enemy("blackglass_listener"))
            outcome = self.resolve_random_encounter_fight(
                title="Choir Map Ambush",
                description="A Quiet Choir route cell tries to kill witnesses before the real map can be read.",
                enemies=enemies,
                parley_dc=15,
                flee_text="You slip out before the cartographer can finish turning the whole branch into a prepared crossfire.",
            )
            if outcome == "victory":
                self.grant_random_encounter_rewards(
                    reason="the choir map satchel",
                    items={"scroll_clarity": 1},
                )
            return
        if encounter_id == "resonance_bleed_pool":
            self.random_encounter_intro(
                "A still pool ahead hums with the kind of wrong calm that means something in it has already heard you and is deciding what that means."
            )
            enemies = [create_enemy("blackglass_listener")]
            if len(self.state.party_members()) >= 4 or int(self.state.flags.get("act2_whisper_pressure", 2)) >= 4:
                enemies.append(create_enemy("resonance_leech"))
            outcome = self.resolve_random_encounter_fight(
                title="Resonance Bleed Pool",
                description="A living resonance pocket and the thing feeding on it lash out before the company can pass cleanly.",
                enemies=enemies,
                allow_parley=False,
                flee_text="You give the pool a wider berth and refuse to become one more rhythm it gets to remember.",
            )
            if outcome == "victory":
                self.grant_random_encounter_rewards(
                    reason="the resonance bleed",
                    items={"thoughtward_draught": 1, "resonance_tonic": 1},
                )
            return
        if encounter_id == "black_lake_verdict":
            self.random_encounter_intro(
                "At a narrow threshold above black water, old script wakes across the stone just long enough for a guardian shape to decide whether you count as permitted."
            )
            enemies = [create_enemy("pact_archive_warden")]
            if self.state.flags.get("black_lake_crossed") or int(self.state.flags.get("act2_whisper_pressure", 2)) >= 4:
                enemies.append(create_enemy("blacklake_adjudicator"))
            elif len(self.state.party_members()) >= 4:
                enemies.append(create_enemy("starblighted_miner"))
            outcome = self.resolve_random_encounter_fight(
                title="Black Lake Verdict",
                description="Threshold guardians try to deny you access by force and old authority both.",
                enemies=enemies,
                allow_parley=False,
                flee_text="You retreat from the threshold before the verdict can land cleanly.",
            )
            if outcome == "victory":
                self.grant_random_encounter_rewards(
                    reason="the threshold reliquary",
                    items={"scroll_guardian_light": 1, "fireward_elixir": 1},
                )
            return
        if encounter_id == "forge_heatshadow":
            self.random_encounter_intro(
                "Forge-light crawls along the wall ahead without any visible fire feeding it, and the moving shadow inside that glow suddenly decides it prefers flesh to stone."
            )
            enemies = [create_enemy("forge_echo_stalker")]
            if len(self.state.party_members()) >= 4:
                enemies.append(create_enemy("memory_taker_adept"))
            elif int(self.state.flags.get("act2_whisper_pressure", 2)) >= 4:
                enemies.append(create_enemy("blackglass_listener"))
            outcome = self.resolve_random_encounter_fight(
                title="Forge Heatshadow",
                description="A forge-born hunter and a trailing Choir cutter try to finish an already tired company.",
                enemies=enemies,
                allow_parley=False,
                flee_text="You break sight with the heatshadow before it can choose a better angle.",
            )
            if outcome == "victory":
                self.grant_random_encounter_rewards(
                    reason="the heatshadow kill site",
                    items={"resonance_tonic": 1},
                )
            return
        details = {
            "echoing_supply_cache": {
                "intro": "A supply cache wedged behind broken timbers answers every footstep with the wrong echo, as if the stone behind it is deeper than the wall allows.",
                "prompt": "How do you handle the cache?",
                "skill": "Investigation",
                "dc": 13,
                "context": "to tell a real cache from a planted lure in Wave Echo's broken wall",
                "success": "You find the true seam, pull the cache loose cleanly, and leave the false panel where it can mislead the next scavenger instead of you.",
                "reason": "the echoing cache",
                "gold": 7,
                "items": {"miners_ration_tin": 1},
                "salvage_text": "You grab the obvious bundle and move before the echoes can start sounding like footsteps again.",
                "salvage_items": {"mushroom_broth_flask": 1},
                "leave": "You leave the hidden cache in the wall and keep the cave's patience from turning into a trap.",
            },
            "whispering_lantern": {
                "intro": "A dead miner's lantern still burns with pale fuel beside the track, and the little hiss inside it almost sounds like someone trying not to speak aloud.",
                "prompt": "What do you do with the lantern?",
                "skill": "Arcana",
                "dc": 13,
                "context": "to tell whether the whispering lantern is warded, cursed, or simply wrong",
                "success": "You bleed off the bad resonance and recover the useful alchemical core without letting the whispering rhythm settle in your head.",
                "reason": "the whispering lantern",
                "items": {"thoughtward_draught": 1},
                "salvage_text": "You hood the lantern, take what fuel you can, and refuse to listen long enough for the sound to become a voice.",
                "salvage_gold": 5,
                "leave": "You leave the lantern where it burns and let the mine keep one more secret to itself.",
            },
            "collapsed_ore_sled": {
                "intro": "An ore sled lies half-crushed beneath a cave-in, with fresh tool marks showing someone started to dig it out and then left in a hurry.",
                "prompt": "How do you approach the sled?",
                "skill": "Athletics",
                "dc": 13,
                "context": "to clear the collapsed ore sled without bringing the rest of the debris down with it",
                "success": "You shift the load just enough to free the salvageable locker and pull it clear before the rubble remembers gravity.",
                "reason": "the collapsed ore sled",
                "gold": 8,
                "items": {"miners_ration_tin": 1},
                "salvage_text": "You pry loose one intact satchel and take the small win rather than challenge the whole collapse.",
                "salvage_items": {"mushroom_broth_flask": 1},
                "leave": "You give the buried sled a respectful distance and keep moving.",
            },
            "silent_prayer_wall": {
                "intro": "A side chamber wall is cut with old dwarven prayer marks, but every name on it has been scraped smooth except one unfinished rune near the floor.",
                "prompt": "How do you deal with the prayer wall?",
                "skill": "Religion",
                "dc": 13,
                "context": "to read the damaged prayer wall without disturbing whatever still clings to it",
                "success": "You recognize a ward for steadfast minds, restore enough of the pattern to wake it, and feel the chamber's pressure ease instead of mount.",
                "reason": "the silent prayer wall",
                "items": {"delvers_amber": 1},
                "salvage_text": "You recover a tucked votive packet from the base of the wall and leave the scraped names undisturbed.",
                "salvage_gold": 4,
                "leave": "You back away from the prayer wall without trying to claim anything from it.",
            },
            "flooded_tool_chest": {
                "intro": "A tool chest rocks in black runoff water beside a sidecut, opening and closing by a finger-width whenever the cave's distant tremor rolls through.",
                "prompt": "How do you handle the flooded chest?",
                "skill": "Sleight of Hand",
                "dc": 13,
                "context": "to free the flooded tool chest without ruining the dry packet tucked inside it",
                "success": "You catch the rhythm, pull the chest open on the quiet pulse, and rescue a dry bundle of useful delving stock.",
                "reason": "the flooded tool chest",
                "items": {"resonance_tonic": 1},
                "salvage_text": "You take the easiest dry tool wrap and leave the heavier chest to the water.",
                "salvage_gold": 5,
                "leave": "You leave the waterlogged chest to the runoff and spare yourself a worse slip.",
            },
            "surveyor_ghostlight": {
                "intro": "A pale light bobs down an unused survey branch, stopping every few paces like a guide who expects to be followed and resents being doubted.",
                "prompt": "Do you follow the ghostlight?",
                "skill": "History",
                "dc": 14,
                "context": "to tell whether the surveyor ghostlight is following an authentic Pact route marker sequence",
                "success": "The pattern matches old survey logic closely enough that you recover a hidden marker packet instead of getting led into a deadfall.",
                "reason": "the surveyor's ghostlight",
                "gold": 6,
                "items": {"resonance_tonic": 1},
                "salvage_text": "You refuse the deeper pull, but recover a dropped survey token near the branch mouth.",
                "salvage_gold": 4,
                "leave": "You let the light drift deeper without you and keep the main route under your own control.",
            },
            "stolen_claim_markers": {
                "intro": "A bundle of fresh claim stakes has been jammed behind a support beam, all marked with different guild symbols as if someone wanted every future dispute to start angry.",
                "prompt": "What do you do with the claim stakes?",
                "skill": "Survival",
                "dc": 13,
                "context": "to read who cached the stolen claim markers and what route they intended to poison with them",
                "success": "You sort the false trail from the real one, pocket the markers, and deny the next crew a manufactured feud.",
                "reason": "the stolen claim markers",
                "gold": 9,
                "items": {"miners_ration_tin": 1},
                "salvage_text": "You grab the markers and move on before anyone sees you standing over them.",
                "salvage_gold": 6,
                "leave": "You leave the rigged markers where they are and deny yourself the extra complication.",
            },
            "blackwater_drifter": {
                "intro": "Something wrapped in oilcloth drifts at the edge of the black water, snagged for now against a bent rail where one stronger ripple would take it out of reach.",
                "prompt": "How do you deal with the drifting bundle?",
                "skill": "Perception",
                "dc": 13,
                "context": "to time the blackwater drift and recover the bundle before it slides free",
                "success": "You catch the best moment, hook the oilcloth cleanly, and drag in a still-dry packet from the water's edge.",
                "reason": "the blackwater drifter",
                "items": {"mushroom_broth_flask": 1, "delvers_amber": 1},
                "salvage_text": "You snag only the outer wrap and accept the smaller salvage before the current changes.",
                "salvage_gold": 4,
                "leave": "You let the bundle drift away rather than lean too far over the black water.",
            },
            "chain_drag_tunnel": {
                "intro": "From a side tunnel comes the slow scrape of chain over stone, steady as breath and just distant enough that you cannot tell whether it is approaching or circling.",
                "prompt": "How do you answer the chain noise?",
                "skill": "Perception",
                "dc": 14,
                "context": "to judge the chain-drag tunnel by sound before the source reaches you",
                "success": "You catch the rhythm early enough to find the abandoned satchel without ever stepping into the thing's real patrol path.",
                "reason": "the chain-drag tunnel",
                "gold": 8,
                "items": {"thoughtward_draught": 1},
                "salvage_text": "You take the near satchel and leave before the scrape comes any closer.",
                "salvage_gold": 5,
                "leave": "You give the tunnel its distance and keep your line instead of your curiosity.",
            },
            "mushroom_bloom_hall": {
                "intro": "A collapsed side hall has become a bloom field of pale cave mushrooms growing over helmets, tools, and one very old ration satchel.",
                "prompt": "How do you move through the bloom hall?",
                "skill": "Nature",
                "dc": 13,
                "context": "to identify which mushrooms feed and which ones only want a lung to borrow",
                "success": "You sort the safe growth from the choking spores and harvest a clean bundle fit for the road.",
                "reason": "the bloom hall",
                "items": {"mushroom_broth_flask": 1, "miners_ration_tin": 1},
                "salvage_text": "You take the old satchel and ignore the rest before the spores can decide you belong to them too.",
                "salvage_gold": 3,
                "leave": "You leave the bloom hall untouched and keep breathing easy.",
            },
            "shattered_foreman_bell": {
                "intro": "A foreman's handbell lies cracked beside the track, and every time the cave answers itself the broken bronze gives back a note that does not belong to this mine anymore.",
                "prompt": "What do you do with the broken bell?",
                "skill": "History",
                "dc": 13,
                "context": "to remember what a Pact foreman's bell once signaled before the echoes were altered",
                "success": "You read the bell's old meaning correctly and find the foreman's emergency packet still hidden in the inspection niche nearby.",
                "reason": "the shattered foreman bell",
                "items": {"delvers_amber": 1, "resonance_tonic": 1},
                "salvage_text": "You take the bell's chain and hidden key-splint without trying to wake the note inside it again.",
                "salvage_gold": 5,
                "leave": "You leave the broken bell on the stone and refuse to ring the cave back.",
            },
            "hidden_prisoner_note": {
                "intro": "A folded scrap has been wedged into a support seam at shoulder height, hidden the way a prisoner hides hope: small, deliberate, and close enough to touch only if you know to look.",
                "prompt": "How do you handle the note?",
                "skill": "Investigation",
                "dc": 12,
                "context": "to spot whether the hidden note is a warning, a lure, or both",
                "success": "The note is real, and it points cleanly toward a safer route past a watched sidecut and a name the Quiet Choir did not expect anyone outside the cells to know.",
                "reason": "the hidden prisoner note",
                "gold": 4,
                "items": {"thoughtward_draught": 1},
                "clue": "A hidden prisoner note confirms the Choir rotated captives through the South Adit long before the wider expedition realized people were disappearing below.",
                "salvage_text": "You pocket the note and move, trusting the warning more than the handwriting.",
                "salvage_gold": 2,
                "leave": "You leave the note where it is, unwilling to risk a planted trap.",
            },
            "obsidian_shard_outcrop": {
                "intro": "An outcrop of dark glassy stone hums around a fist-sized shard lodged in the center, and the air nearby tastes like a storm trying to think.",
                "prompt": "How do you approach the shard?",
                "skill": "Arcana",
                "dc": 14,
                "context": "to bleed the dangerous charge out of the obsidian shard without carrying the wrong part of it with you",
                "success": "You ground the resonance safely and pocket only the stable residue the Choir failed to extract cleanly.",
                "reason": "the obsidian outcrop",
                "items": {"thoughtward_draught": 1, "resonance_tonic": 1},
                "salvage_text": "You chip off the calmest edge of the residue and leave the main shard seated where it was.",
                "salvage_gold": 6,
                "leave": "You leave the shard alone and refuse to become one more mind it gets to test.",
            },
            "broken_lift_cradle": {
                "intro": "A lift cradle hangs crooked over a shaft lip, one chain snapped and the cargo net below still holding a scatter of old field packs just out of comfortable reach.",
                "prompt": "How do you deal with the broken lift?",
                "skill": "Athletics",
                "dc": 13,
                "context": "to steady the broken lift cradle long enough to recover the hanging field packs",
                "success": "You brace the cradle, strip the useful packs free, and get clear before the second chain remembers it should not be trusted.",
                "reason": "the broken lift cradle",
                "gold": 8,
                "items": {"miners_ration_tin": 1, "mushroom_broth_flask": 1},
                "salvage_text": "You hook one field pack free and decide that tempting the rest would be greed, not need.",
                "salvage_gold": 5,
                "leave": "You leave the hanging packs to gravity and keep the party on solid ground.",
            },
            "hushed_campfire": {
                "intro": "A campfire has been smothered recently enough that the stones are still warm, but every bedroll around it has been rolled too neatly, like a crew that meant to come back and did not get the chance.",
                "prompt": "How do you investigate the camp?",
                "skill": "Insight",
                "dc": 13,
                "context": "to tell whether the hushed campfire was abandoned in fear, discipline, or ritual",
                "success": "You read the missing body-language in the camp and recover the hidden trail pouch before whatever scared the crew comes back around its circuit.",
                "reason": "the hushed campfire",
                "gold": 7,
                "items": {"delvers_amber": 1},
                "salvage_text": "You strip the nearest bedroll stash and move before the wrong owners return.",
                "salvage_gold": 4,
                "leave": "You leave the camp exactly as you found it and deny the darkness another sound to follow.",
            },
        }
        detail = details[encounter_id]
        self.random_encounter_intro(detail["intro"])
        options = [
            self.skill_tag(detail["skill"].upper(), self.action_option("Read the scene carefully and take only what is safe.")),
            self.action_option("Take the obvious salvage and move on."),
            self.action_option("Leave it alone and keep the route moving."),
        ]
        choice = self.scenario_choice(detail["prompt"], options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            if self.skill_check(self.state.player, detail["skill"], detail["dc"], context=detail["context"]):
                self.say(detail["success"])
                if detail.get("clue"):
                    self.add_clue(detail["clue"])
                self.grant_random_encounter_rewards(
                    reason=detail["reason"],
                    gold=int(detail.get("gold", 0)),
                    items=dict(detail.get("items", {})),
                )
            else:
                self.say("The cave never quite punishes you outright, but it makes clear this was not the moment to press deeper.")
        elif choice == 2:
            self.say(detail["salvage_text"])
            self.grant_random_encounter_rewards(
                reason=detail["reason"],
                gold=int(detail.get("salvage_gold", 0)),
                items=dict(detail.get("salvage_items", {})),
            )
        else:
            self.say(detail["leave"])

    def random_encounter_locked_chest_under_ferns(self) -> None:
        assert self.state is not None
        self.random_encounter_intro(
            "Fern fronds hide a traveler's chest tucked beneath a fallen marker stone, its lock still intact and its hinges only half-rusted."
        )
        options = [
            self.skill_tag("INVESTIGATION", self.action_option("Check the latch and seams for a hidden catch.")),
            self.skill_tag("SLEIGHT OF HAND", self.action_option("Work the lock open carefully.")),
            self.skill_tag("ATHLETICS", self.action_option("Wrench the lid open by force.")),
        ]
        choice = self.scenario_choice("How do you handle the chest?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            if self.skill_check(self.state.player, "Investigation", 12, context="to spot the trap before touching the chest"):
                self.grant_random_encounter_rewards(reason="the fern-hidden chest", gold=self.rng.randint(8, 14), items={"bread_round": 1})
            else:
                self.suffer_random_encounter_damage(
                    self.state.player,
                    2,
                    damage_type="poison",
                    source="A spring needle pricks your hand before you can pull back.",
                )
        elif choice == 2:
            if self.skill_check(self.state.player, "Sleight of Hand", 15, context="to pick the travel lock quietly"):
                self.grant_random_encounter_rewards(
                    reason="the fern-hidden chest",
                    gold=self.rng.randint(10, 16),
                    items={"potion_healing": 1},
                )
            else:
                self.say("The tumblers click loud enough to rouse armed scavengers from the brush.")
                self.resolve_random_encounter_fight(
                    title="Chest Scavengers",
                    description="Bandits rush the chest the moment they hear the failed lockpick.",
                    enemies=self.random_bandit_pair(),
                    parley_dc=12,
                )
        else:
            if self.skill_check(self.state.player, "Athletics", 13, context="to break the warped lid open cleanly"):
                self.grant_random_encounter_rewards(reason="the broken chest", gold=self.rng.randint(6, 12), items={"goat_cheese": 1})
            else:
                self.suffer_random_encounter_damage(
                    self.state.player,
                    3,
                    source="The chest splinters apart and a jagged hinge snaps across your knuckles.",
                )

    def random_encounter_abandoned_cottage(self) -> None:
        assert self.state is not None
        special_survivor = bool(self.state.flags.get("bryn_cache_found")) and not bool(
            self.state.flags.get("abandoned_cottage_survivor_met")
        )
        self.random_encounter_intro(
            "A soot-stained cottage slumps beside the trail, with one shutter hanging open and a cellar door that looks newer than the walls around it."
        )
        options = [
            self.skill_tag("PERCEPTION", self.action_option("Scout the windows and chimney before going near.")),
            self.quoted_option("PERSUASION", "Anyone inside can keep their roof if they answer plainly."),
            self.action_option("Shoulder the cellar door open and clear the place fast."),
        ]
        choice = self.scenario_choice("What do you do with the cottage?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            if self.skill_check(self.state.player, "Perception", 12, context="to read the cottage from the yard"):
                self.grant_random_encounter_rewards(reason="the cottage rafters", gold=4, items={"camp_stew_jar": 1, "bread_round": 1})
                if special_survivor:
                    self.state.flags["abandoned_cottage_survivor_met"] = True
                    self.say("A soot-streaked cellar holdout only crawls out after the yard settles. They whisper one useful thing before fleeing: Varyn's people call the deeper route under town Emberhall.")
                    self.add_clue("A terrified holdout in the cottage names Emberhall as the Ashen Brand's deeper cellar route under Phandalin.")
            else:
                self.say("A loose shutter bangs open, and the squatters inside answer with drawn steel.")
                self.resolve_random_encounter_fight(
                    title="Cottage Squatters",
                    description="Desperate scavengers rush out of the abandoned cottage with knives already in hand.",
                    enemies=self.random_goblin_pair(),
                )
        elif choice == 2:
            if self.skill_check(self.state.player, "Persuasion", 11, context="to promise safe passage to whoever is hiding inside"):
                self.grant_random_encounter_rewards(reason="the cottage table", gold=6, items={"goat_cheese": 1})
                if special_survivor:
                    self.state.flags["abandoned_cottage_survivor_met"] = True
                    self.say("Your offer pulls a hidden survivor out of the cellar. Between panicked breaths they mention Emberhall and the black-ink ledgers moving beneath town.")
                    self.add_clue("A hidden cottage survivor ties Emberhall to the Ashen Brand's cellar ledgers beneath town.")
            else:
                self.say("The reply is a crossbow quarrel through the boards.")
                self.resolve_random_encounter_fight(
                    title="Panicked Holdouts",
                    description="A pair of frightened holdouts decide to shoot their way free.",
                    enemies=[create_enemy("bandit_archer")],
                    parley_dc=11,
                )
        else:
            self.resolve_random_encounter_fight(
                title="Cellar Door Rush",
                description="Your hard entry startles goblin scavengers into a frantic knife fight.",
                enemies=self.random_goblin_pair(),
                parley_dc=12,
            )

    def random_encounter_bandit_toll_line(self) -> None:
        assert self.state is not None
        self.random_encounter_intro(
            "A rope strung across the road is tied to a rough sign promising 'safe passage' for a handful of coin, while voices wait just out of sight."
        )
        options = [
            self.action_option("Cut the rope and move on before the hidden collectors close in."),
            self.skill_tag("STEALTH", self.action_option("Slip around the line through the brush.")),
            self.quoted_option("INTIMIDATION", "Come out now or lose the hand that tied this rope."),
        ]
        choice = self.scenario_choice("How do you answer the toll line?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            self.say("You cut the rope and keep moving before the would-be collectors can gather their courage.")
        elif choice == 2:
            if self.skill_check(self.state.player, "Stealth", 12, context="to skirt the toll line unseen"):
                self.grant_random_encounter_rewards(reason="the brush by the toll line", gold=5)
            else:
                self.say("A hidden bell twitches on the rope and the collectors come running.")
                self.resolve_random_encounter_fight(
                    title="Road Toll Collectors",
                    description="Bandits burst from the brush to defend their roadside racket.",
                    enemies=self.random_bandit_pair(),
                )
        else:
            if self.skill_check(self.state.player, "Intimidation", 13, context="to break the nerve of the hidden collectors"):
                self.grant_random_encounter_rewards(reason="the abandoned toll pouch", gold=self.rng.randint(5, 10))
            else:
                self.resolve_random_encounter_fight(
                    title="Toll Line Standoff",
                    description="The bluff fails, and the hidden collectors decide to rush you.",
                    enemies=self.random_bandit_pair(),
                )

    def random_encounter_wounded_messenger(self) -> None:
        assert self.state is not None
        self.random_encounter_intro(
            "A messenger in torn livery lies behind a milepost with a split satchel, trying to hold one boot against a bleeding leg."
        )
        options = [
            self.skill_tag("MEDICINE", self.action_option("Bind the wound before asking questions.")),
            self.skill_tag("INVESTIGATION", self.action_option("Search the scattered satchel for whatever mattered enough to attack for.")),
            self.action_option("Leave the messenger with water and keep moving."),
        ]
        choice = self.scenario_choice("How do you deal with the messenger?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            if self.skill_check(self.state.player, "Medicine", 11, context="to stop the bleeding in time"):
                self.grant_random_encounter_rewards(reason="the grateful messenger", gold=9, items={"bread_round": 1})
                self.add_clue("A roadside messenger mentioned more Ashen Brand scouts probing side trails around Phandalin.")
                self.state.flags["saved_wounded_messenger"] = True
            else:
                self.say("You slow the bleeding, but the messenger can only rasp thanks before passing out.")
        elif choice == 2:
            if self.skill_check(self.state.player, "Investigation", 12, context="to gather the useful papers before the wind takes them"):
                self.grant_random_encounter_rewards(reason="the torn satchel", gold=7, items={"scroll_clarity": 1})
            else:
                self.say("You find little that still matters and lose time in the reeds.")
        else:
            self.say("You leave water within reach and let the road take the rest of the choice from you.")

    def random_encounter_messenger_returns_with_reward(self) -> None:
        assert self.state is not None
        self.random_encounter_intro(
            "The wounded messenger finds you on the road two battles later, walking stiffly but upright with a fresh bandage and a sealed runner's tube held out in both hands."
        )
        options = [
            self.quoted_option("PERSUASION", "What did you learn once you made it back alive?"),
            self.action_option("Take the reward and tell the messenger to keep breathing."),
            self.action_option("Refuse the coin and tell them to spend it in Phandalin instead."),
        ]
        choice = self.scenario_choice("How do you answer the messenger's return?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        self.state.flags["messenger_return_paid"] = True
        if choice == 1:
            if self.skill_check(self.state.player, "Persuasion", 12, context="to settle the messenger enough for the useful details"):
                self.grant_random_encounter_rewards(reason="the messenger's return", gold=8, items={"potion_healing": 1})
                self.add_clue("The recovered messenger confirms the Ashen Brand has been leaning on more side roads than the town realized.")
            else:
                self.grant_random_encounter_rewards(reason="the messenger's return", gold=5)
        elif choice == 2:
            self.grant_random_encounter_rewards(reason="the messenger's return", gold=7, items={"bread_round": 1})
        else:
            self.say("The messenger keeps the coin and promises it will land where Phandalin actually bleeds.")
            adjust_metric = getattr(self, "act1_adjust_metric", None)
            if callable(adjust_metric):
                adjust_metric("act1_town_fear", -1)

    def random_encounter_hunter_snare(self) -> None:
        assert self.state is not None
        self.random_encounter_intro(
            "A taut line glints between alder roots beside the road, with a snare knot drawn tight enough to catch a careless traveler by the ankle."
        )
        options = [
            self.skill_tag("PERCEPTION", self.action_option("Trace the snare and find the hidden anchor point.")),
            self.skill_tag("SURVIVAL", self.action_option("Follow the trapper's line back to wherever they stored their catch.")),
            self.action_option("Cut the snare and leave the setup ruined behind you."),
        ]
        choice = self.scenario_choice("What do you do with the snare?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            if self.skill_check(self.state.player, "Perception", 12, context="to read the snare before it snaps"):
                self.grant_random_encounter_rewards(reason="the trapper's blind", gold=5, items={"goat_cheese": 1, "bread_round": 1})
            else:
                self.suffer_random_encounter_damage(
                    self.state.player,
                    2,
                    source="The line lashes your wrist when the knot lets go.",
                )
        elif choice == 2:
            if self.skill_check(self.state.player, "Survival", 12, context="to follow the hidden drag marks through the brush"):
                self.grant_random_encounter_rewards(reason="the trapper's blind", gold=6, items={"potion_healing": 1})
            else:
                self.say("The trail circles you right into the trapper's lookout.")
                self.resolve_random_encounter_fight(
                    title="Snare-Line Ambushers",
                    description="Bandit hunters rise from the brush when you follow their line too boldly.",
                    enemies=[create_enemy("bandit_archer"), create_enemy("bandit")],
                    parley_dc=12,
                )
        else:
            self.say("The cord parts and the trap goes slack, leaving the road one danger lighter.")

    def random_encounter_lone_wolf(self) -> None:
        assert self.state is not None
        self.random_encounter_intro(
            "A lean ash-gray wolf crouches over a fresh carcass just off the trail, yellow eyes fixed on you while a torn purse glints beside the body."
        )
        options = [
            self.action_option("Back away and give the animal its ground."),
            self.skill_tag("SURVIVAL", self.action_option("Read the wolf's posture and edge toward the purse.")),
            self.skill_tag("INTIMIDATION", self.action_option("Drive the wolf off with noise and steel.")),
        ]
        choice = self.scenario_choice("How do you deal with the wolf?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            self.say("You leave the kill to the wolf and keep the road instead of tempting the wrong hunger.")
        elif choice == 2:
            if self.skill_check(self.state.player, "Survival", 12, context="to move inside the wolf's comfort without triggering a rush"):
                self.grant_random_encounter_rewards(reason="the purse beside the carcass", gold=self.rng.randint(6, 11))
            else:
                self.resolve_random_encounter_fight(
                    title="Wolf on the Trail",
                    description="The wolf decides you're too close to its kill and lunges.",
                    enemies=[create_enemy("wolf")],
                    allow_parley=False,
                    parley_dc=99,
                )
        else:
            if self.skill_check(self.state.player, "Intimidation", 12, context="to break the wolf's nerve with a hard shout"):
                self.grant_random_encounter_rewards(reason="the purse beside the carcass", gold=self.rng.randint(7, 12))
            else:
                self.resolve_random_encounter_fight(
                    title="Cornered Wolf",
                    description="Your threat only convinces the wolf to charge before you can press the edge.",
                    enemies=[create_enemy("wolf")],
                    allow_parley=False,
                    parley_dc=99,
                )

    def random_encounter_smuggler_cookfire(self) -> None:
        assert self.state is not None
        bryn_cache_live = self.has_quest("bryn_loose_ends") and not bool(self.state.flags.get("bryn_cache_found"))
        self.random_encounter_intro(
            "A narrow plume of smoke rises from a hidden cookfire ahead, where half-packed bundles sit under a tarp and someone has been careful not to camp on the road itself."
        )
        if bryn_cache_live:
            self.say("Bryn goes very still for half a second. The tarp knots and ash marks are old smuggler shorthand she recognizes immediately.")
        options = [
            self.skill_tag("STEALTH", self.action_option("Circle wide and lift what you can before the campers notice.")),
            self.quoted_option("DECEPTION", "Riders are coming from Neverwinter. Run while you still can."),
            self.action_option("Leave the hidden camp alone."),
        ]
        choice = self.scenario_choice("How do you approach the hidden fire?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        camp_disrupted = False
        cache_recovered = False
        if choice == 1:
            camp_disrupted = True
            if self.skill_check(self.state.player, "Stealth", 12, context="to reach the tarp without a snapped twig giving you away"):
                self.grant_random_encounter_rewards(reason="the smuggler tarp", gold=4, items={"potion_healing": 1})
                cache_recovered = True
            else:
                outcome = self.resolve_random_encounter_fight(
                    title="Smuggler Camp",
                    description="The hidden campers catch you in the act and come up armed.",
                    enemies=self.random_bandit_pair(),
                )
                cache_recovered = outcome == "victory"
        elif choice == 2:
            camp_disrupted = True
            if self.skill_check(self.state.player, "Deception", 12, context="to sell the story of riders on the road"):
                self.grant_random_encounter_rewards(reason="the abandoned cookfire", gold=7, items={"bread_round": 1})
                cache_recovered = True
            else:
                outcome = self.resolve_random_encounter_fight(
                    title="Smuggler Panic",
                    description="The campers spot the lie, snatch up their weapons, and rush the tree line.",
                    enemies=self.random_bandit_pair(),
                )
                cache_recovered = outcome == "victory"
        else:
            self.say("You let the hidden camp keep its secrets and deny the road one more reason to bleed tonight.")
        if camp_disrupted:
            self.state.flags["smuggler_revenge_pending"] = True
        if bryn_cache_live and cache_recovered:
            self.state.flags["bryn_cache_found"] = True
            self.say("Among the abandoned bundles is a smoke-wrapped ledger case Bryn knows instantly. One old cache just stopped being theoretical.")

    def random_encounter_smuggler_revenge_squad(self) -> None:
        assert self.state is not None
        self.state.flags["smuggler_revenge_resolved"] = True
        self.state.flags["smuggler_revenge_pending"] = False
        self.random_encounter_intro(
            "The retaliation comes on a stretch of brush road where the birds have already gone quiet. Smuggler lookouts and Ashen Brand muscle are waiting where they expect the score to settle."
        )
        enemies = [create_enemy("ash_brand_enforcer"), create_enemy("bandit_archer")]
        if len(self.state.party_members()) >= 3:
            enemies.append(create_enemy("ember_channeler"))
        options = [
            self.skill_tag("STEALTH", self.action_option("Spot the ambush first and break their line before it closes.")),
            self.quoted_option("INTIMIDATION", "Walk out and tell them exactly how badly this is about to go."),
            self.action_option("Meet the revenge squad head on."),
        ]
        choice = self.scenario_choice("How do you answer the revenge squad?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            if self.skill_check(self.state.player, "Stealth", 13, context="to catch the ambush line before it catches you"):
                self.grant_random_encounter_rewards(reason="the broken revenge line", gold=8, items={"scroll_clarity": 1})
            else:
                self.resolve_random_encounter_fight(
                    title="Smuggler Revenge Squad",
                    description="The hidden reprisals cell springs the trap with Ashen Brand backing behind it.",
                    enemies=enemies,
                )
        elif choice == 2:
            if self.skill_check(self.state.player, "Intimidation", 13, context="to break the revenge squad's nerve before the charge"):
                self.grant_random_encounter_rewards(reason="the shaken revenge squad", gold=9)
            else:
                self.resolve_random_encounter_fight(
                    title="Smuggler Revenge Squad",
                    description="The threatened smugglers decide they have come too far to turn back now.",
                    enemies=enemies,
                )
        else:
            outcome = self.resolve_random_encounter_fight(
                title="Smuggler Revenge Squad",
                description="Steel answers old grudges in the brush road dark.",
                enemies=enemies,
            )
            if outcome == "victory":
                self.grant_random_encounter_rewards(reason="the revenge squad", gold=6)

    def random_encounter_shrine_of_tymora(self) -> None:
        assert self.state is not None
        self.random_encounter_intro(
            "A weathered roadside shrine to Tymora leans beneath a white-streaked oak, its tiny offering bowl still dry despite the last night's rain."
        )
        options = [
            self.skill_tag("RELIGION", self.action_option("Set the shrine right and offer a quick frontier prayer.")),
            self.action_option("Leave a single coin and move on."),
            self.skill_tag("ATHLETICS", self.action_option("Pry up the stones around the shrine base.")),
        ]
        choice = self.scenario_choice("How do you treat the shrine?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            if self.skill_check(self.state.player, "Religion", 11, context="to settle the shrine the way a proper caretaker would"):
                self.grant_random_encounter_rewards(reason="the shrine's hidden niche", items={"potion_healing": 1})
            else:
                self.say("The prayer steadies the moment, but the shrine yields nothing except silence.")
        elif choice == 2:
            if self.state.gold > 0:
                self.state.gold -= 1
                self.say("You leave 1 mark in the bowl and take the quiet blessing of moving on with a clean conscience.")
            else:
                self.say("You reach for a coin you do not have and settle for a respectful nod instead.")
        else:
            if self.skill_check(self.state.player, "Athletics", 13, context="to heave up the old base stones without collapse"):
                self.grant_random_encounter_rewards(reason="the shrine base", gold=6)
            else:
                self.suffer_random_encounter_damage(
                    self.state.player,
                    2,
                    source="A loosened stone crushes down onto your boot before you can clear away.",
                )

    def random_encounter_half_sunk_satchel(self) -> None:
        assert self.state is not None
        self.random_encounter_intro(
            "At a muddy roadside ditch, a leather satchel is trapped beneath a sheet of runoff water while silver buckles flash below the surface."
        )
        options = [
            self.skill_tag("SURVIVAL", self.action_option("Read the current and pin the satchel before it slips downstream.")),
            self.skill_tag("ATHLETICS", self.action_option("Reach in and yank it free in one pull.")),
            self.action_option("Let the ditch keep it and stay dry."),
        ]
        choice = self.scenario_choice("What do you do with the satchel?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            if self.skill_check(self.state.player, "Survival", 11, context="to work with the current instead of against it"):
                self.grant_random_encounter_rewards(reason="the waterlogged satchel", gold=self.rng.randint(8, 13), items={"scroll_clarity": 1})
            else:
                self.say("The satchel slips deeper into the culvert before you can pin it.")
        elif choice == 2:
            if self.skill_check(self.state.player, "Athletics", 12, context="to haul the satchel out before the bank gives way"):
                self.grant_random_encounter_rewards(reason="the waterlogged satchel", gold=self.rng.randint(6, 10), items={"bread_round": 1})
            else:
                self.suffer_random_encounter_damage(
                    self.state.player,
                    2,
                    source="The bank collapses and sends you hard onto the stones.",
                )
        else:
            self.say("You leave the satchel to the ditch and keep the road under your feet.")

    def random_encounter_ruined_wayhouse(self) -> None:
        assert self.state is not None
        self.random_encounter_intro(
            "The shell of an old wayhouse stands with its roof gone and its front room open to the sky, but the cellar trapdoor has fresh scrape marks around it."
        )
        options = [
            self.skill_tag("PERCEPTION", self.action_option("Study the upper windows and the cellar lip before committing.")),
            self.quoted_option("PERSUASION", "Come out and we can all leave with less blood on the floor."),
            self.action_option("Drop through the trapdoor and take the space by force."),
        ]
        choice = self.scenario_choice("How do you approach the wayhouse?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            if self.skill_check(self.state.player, "Perception", 12, context="to catch the cellar glint before it catches you"):
                self.grant_random_encounter_rewards(reason="the wayhouse stash", gold=5, items={"goat_cheese": 1, "camp_stew_jar": 1})
            else:
                self.resolve_random_encounter_fight(
                    title="Wayhouse Scavengers",
                    description="Goblin scavengers rush the ladder the moment you show yourself at the opening.",
                    enemies=self.random_goblin_pair(),
                    parley_dc=11,
                )
        elif choice == 2:
            if self.skill_check(self.state.player, "Persuasion", 12, context="to convince the cellar squatters to trade space for safety"):
                self.grant_random_encounter_rewards(reason="the cellar handoff", gold=6, items={"bread_round": 1})
            else:
                self.resolve_random_encounter_fight(
                    title="Wayhouse Holdouts",
                    description="The hidden squatters answer your offer with a hard charge up the stairs.",
                    enemies=self.random_goblin_pair(),
                    parley_dc=11,
                )
        else:
            self.resolve_random_encounter_fight(
                title="Trapdoor Drop",
                description="You drop into the cellar before the hidden squatters can bolt, and the scramble turns violent fast.",
                enemies=self.random_goblin_pair(),
                parley_dc=11,
            )

    def random_encounter_scavenger_cart(self) -> None:
        assert self.state is not None
        self.random_encounter_intro(
            "A broken handcart sits canted in the ditch with sacks spilling grain and one axle pin still jammed half through the wheel."
        )
        options = [
            self.skill_tag("ATHLETICS", self.action_option("Set the cart upright and see what was worth dragging.")),
            self.skill_tag("INVESTIGATION", self.action_option("Check the sacks and hidden panels before touching the axle.")),
            self.action_option("Keep walking before whoever lost it comes back."),
        ]
        choice = self.scenario_choice("How do you deal with the cart?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            if self.skill_check(self.state.player, "Athletics", 12, context="to right the cart without dumping the last salvageable sack"):
                self.grant_random_encounter_rewards(reason="the salvaged cart", gold=4, items={"bread_round": 2})
            else:
                self.suffer_random_encounter_damage(
                    self.state.player,
                    2,
                    source="The axle pin tears free and clips your shoulder on the way down.",
                )
        elif choice == 2:
            if self.skill_check(self.state.player, "Investigation", 12, context="to find the hidden compartment before the obvious grain sacks distract you"):
                self.grant_random_encounter_rewards(reason="the cart's false bottom", gold=8, items={"goat_cheese": 1})
            else:
                self.say("You linger too long and hear returning footsteps in the scrub.")
                self.resolve_random_encounter_fight(
                    title="Returning Scavengers",
                    description="A pair of scavengers comes running back to reclaim the broken cart.",
                    enemies=[create_enemy("bandit"), create_enemy("bandit_archer")],
                    parley_dc=12,
                )
        else:
            self.say("You leave the cart where it lies and keep your pace instead of your curiosity.")

    def random_encounter_loose_flagstones(self) -> None:
        assert self.state is not None
        self.random_encounter_intro(
            "A patch of old flagstones peeks through the roadside mud, one slab sitting slightly higher than the rest as if something underneath has started to push back."
        )
        options = [
            self.skill_tag("INVESTIGATION", self.action_option("Test the seams and look for a deliberate cache.")),
            self.skill_tag("SLEIGHT OF HAND", self.action_option("Lift the edge carefully with a blade and cloth.")),
            self.action_option("Stamp the stones flat and deny anyone else the hiding place."),
        ]
        choice = self.scenario_choice("How do you handle the stones?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            if self.skill_check(self.state.player, "Investigation", 12, context="to tell cachework from ordinary road ruin"):
                self.grant_random_encounter_rewards(reason="the flagstone cache", gold=9, items={"scroll_mending_word": 1})
            else:
                self.say("The pattern still looks wrong, but you cannot make it yield before the light shifts.")
        elif choice == 2:
            if self.skill_check(self.state.player, "Sleight of Hand", 12, context="to lift the stone without tipping the hidden vial beneath it"):
                self.grant_random_encounter_rewards(reason="the flagstone cache", gold=6, items={"potion_healing": 1})
            else:
                self.suffer_random_encounter_damage(
                    self.state.player,
                    2,
                    damage_type="poison",
                    source="A brittle vial shatters under the stone and splashes your hand.",
                )
        else:
            self.say("You grind the raised stone back into the road and move on without learning what it once protected.")

    def random_encounter_frightened_draft_horse(self) -> None:
        assert self.state is not None
        self.random_encounter_intro(
            "A lathered draft horse stands tangled in a snapped trace line beside the road, ears pinned back while a pack roll hangs half loose from its saddle."
        )
        options = [
            self.skill_tag("ANIMAL HANDLING", self.action_option("Quiet the horse and free the line carefully.")),
            self.skill_tag("SLEIGHT OF HAND", self.action_option("Work the pack roll loose without spooking the animal further.")),
            self.skill_tag("INTIMIDATION", self.action_option("Drive off whatever is lurking nearby before it bolts again.")),
        ]
        choice = self.scenario_choice("How do you handle the horse?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            if self.skill_check(self.state.player, "Animal Handling", 12, context="to settle the horse and work the line free"):
                self.grant_random_encounter_rewards(reason="the grateful beast's gear", gold=5, items={"bread_round": 1, "goat_cheese": 1})
            else:
                self.say("The horse tears free and leaves only mud and a few loose oats behind.")
        elif choice == 2:
            if self.skill_check(self.state.player, "Sleight of Hand", 12, context="to free the pack roll before the horse jerks away"):
                self.grant_random_encounter_rewards(reason="the loosened pack roll", gold=6, items={"camp_stew_jar": 1})
            else:
                self.suffer_random_encounter_damage(
                    self.state.player,
                    2,
                    source="The horse jerks sideways and the rolling pack catches you across the ribs.",
                )
        else:
            if self.skill_check(self.state.player, "Intimidation", 12, context="to blast the brush with enough force to scare off the watcher"):
                self.grant_random_encounter_rewards(reason="the dropped watcher pouch", gold=7)
            else:
                self.resolve_random_encounter_fight(
                    title="Brush Stalker",
                    description="A hungry ash wolf bursts from the brush instead of retreating from the shout.",
                    enemies=[create_enemy("wolf")],
                    allow_parley=False,
                    parley_dc=99,
                )

    def random_encounter_rain_barrel_cache(self) -> None:
        assert self.state is not None
        self.random_encounter_intro(
            "Behind a split rail fence, a rain barrel has been weighted down with stones, and the hollow clunk beneath the water says someone hid more than water inside it."
        )
        options = [
            self.skill_tag("INVESTIGATION", self.action_option("Probe the barrel bottom and find the false floor.")),
            self.skill_tag("ATHLETICS", self.action_option("Tip the whole barrel over and collect whatever drops out.")),
            self.action_option("Leave the barrel and let the owner keep their hiding spot."),
        ]
        choice = self.scenario_choice("What do you do with the barrel?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            if self.skill_check(self.state.player, "Investigation", 11, context="to feel out the false floor without dunking the goods"):
                self.grant_random_encounter_rewards(reason="the rain barrel cache", gold=7, items={"scroll_guardian_light": 1})
            else:
                self.say("Your fingers find the seam too late and the little cache shifts deeper into the muck.")
        elif choice == 2:
            if self.skill_check(self.state.player, "Athletics", 12, context="to heave the barrel over before the fence gives out"):
                self.grant_random_encounter_rewards(reason="the rain barrel cache", gold=6, items={"potion_healing": 1})
            else:
                self.suffer_random_encounter_damage(
                    self.state.player,
                    2,
                    source="The barrel bursts against the fence and slams muddy boards into your shin.",
                )
        else:
            self.say("You let the fence, barrel, and secret beneath it keep their peace.")

    def random_encounter_watchfire_embers(self) -> None:
        assert self.state is not None
        self.random_encounter_intro(
            "A watchfire has only just gone to embers beside the trail, with two bedroll hollows still warm and bootprints leading into the dark."
        )
        options = [
            self.skill_tag("PERCEPTION", self.action_option("Read the campsite before touching anything.")),
            self.skill_tag("STEALTH", self.action_option("Follow the freshest bootprints just far enough to find the stash.")),
            self.action_option("Kick dirt over the embers and deny the campers their return point."),
        ]
        choice = self.scenario_choice("How do you handle the cold camp?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            if self.skill_check(self.state.player, "Perception", 12, context="to judge whether the campers left in panic or on purpose"):
                self.grant_random_encounter_rewards(reason="the abandoned watchfire", gold=5, items={"bread_round": 1, "goat_cheese": 1})
            else:
                self.say("The clues stay muddy and the camp yields little beyond smoke scent.")
        elif choice == 2:
            if self.skill_check(self.state.player, "Stealth", 12, context="to track the bootprints without brushing the hidden sentry line"):
                self.grant_random_encounter_rewards(reason="the hidden bedroll stash", gold=8, items={"scroll_ember_ward": 1})
            else:
                self.resolve_random_encounter_fight(
                    title="Returning Campers",
                    description="The owners of the warm camp catch you on their back trail and come in fast.",
                    enemies=self.random_bandit_pair(),
                )
        else:
            self.say("The last glow dies under your boot, and the road keeps its next secret a little longer.")

    def random_encounter_broken_milestone(self) -> None:
        assert self.state is not None
        self.random_encounter_intro(
            "A shattered milestone lies in chunks across the roadside, and fresh pry marks show someone recently checked whether anything had ever been hidden inside it."
        )
        options = [
            self.skill_tag("HISTORY", self.action_option("Study the carving and look for the original mason's trick.")),
            self.skill_tag("ATHLETICS", self.action_option("Split the largest chunk and see if the smugglers missed anything.")),
            self.action_option("Roll the stone off the road and leave it at that."),
        ]
        choice = self.scenario_choice("How do you deal with the broken stone?", options, allow_meta=False)
        self.player_choice_output(options[choice - 1])
        if choice == 1:
            if self.skill_check(self.state.player, "History", 11, context="to recall how old road markers sometimes hid courier niches"):
                self.grant_random_encounter_rewards(reason="the milestone niche", gold=7, items={"scroll_battle_psalm": 1})
            else:
                self.say("You remember enough old roadcraft to know there was a trick here once, but not enough to reclaim it.")
        elif choice == 2:
            if self.skill_check(self.state.player, "Athletics", 12, context="to crack the stone along an old seam"):
                self.grant_random_encounter_rewards(reason="the milestone niche", gold=9)
            else:
                self.say("The stone cracks louder than expected, and scavengers answer the noise.")
                self.resolve_random_encounter_fight(
                    title="Milestone Scavengers",
                    description="Bandits rush in, convinced the broken stone is covering someone else's hidden cut.",
                    enemies=self.random_bandit_pair(),
                )
        else:
            self.say("You clear the road and leave the old marker's secrets where they fell.")
