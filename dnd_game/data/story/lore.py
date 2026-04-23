from __future__ import annotations

"""Aethrune lore codex entries used by the title-screen reference menu.

The public codex now presents Roads That Remember as an original Aethrune
campaign. Internal character-option keys still mirror the current mechanics so
existing saves, tests, and creation flow remain stable during the retcon.
"""

from collections.abc import Mapping

from ...models import SKILL_TO_ABILITY
from .character_options.backgrounds import BACKGROUNDS
from .character_options.classes import CLASSES, CLASS_LEVEL_PROGRESSION
from .character_options.races import RACES
from .public_terms import (
    ABILITY_PUBLIC_LABELS,
    CLASS_PUBLIC_LABELS,
    RACE_PUBLIC_LABELS,
    SKILL_PUBLIC_LABELS,
    rules_text,
)


LoreEntry = dict[str, str]
LoreSection = Mapping[str, LoreEntry]


LORE_INTRO = (
    "This codex introduces Aethrune, the original setting for Roads That Remember. "
    "It focuses on Greywake, the Emberway, Iron Hollow, the Resonant Vaults, and "
    "the Meridian systems still shaping the world after their builders are gone. "
    "The underlying combat and character math still uses an SRD-derived d20 chassis, "
    "but the public story language now favors Aethrune terms such as channeling, "
    "relics, draughts, scripts, Guard, edge, strain, and resist checks."
)


LOCATION_LORE: dict[str, LoreEntry] = {
    "Aethrune": {
        "menu": "A broken world where old roads, records, and buried systems still answer.",
        "text": (
            "Aethrune is a world rebuilt on top of a dead infrastructure empire. The Meridian Accord once "
            "bound cities, routes, waterworks, signal towers, vaults, and ledgers into a single living system. "
            "When that order collapsed, people survived by scavenging its roads, sheltering under its ruins, "
            "and arguing over what its records still mean.\n\n"
            "That history matters because the world is not empty wilderness. A broken road can still remember "
            "where travelers are meant to go. A sealed gate can still recognize old authority. A village ledger "
            "can become a weapon if the right faction learns how to read it."
        ),
    },
    "Shatterbelt Frontier": {
        "menu": "The Act I borderland where trade, fear, and old roadwork collide.",
        "text": (
            "The Shatterbelt Frontier is the rough belt between Greywake's city reach and the settlements that "
            "depend on the Emberway. It is practical country: milehouses, supply camps, shrine-lanterns, quarry "
            "tracks, farms, drainage cuts, ruined towers, and old Accord stone half-buried under newer work.\n\n"
            "The frontier is tense because nobody fully controls it. Greywake wants order, Iron Hollow wants "
            "breathing room, the Ashen Brand wants routes it can tax by fear, and older Meridian machinery waits "
            "below all of them with its own cold logic."
        ),
    },
    "Greywake": {
        "menu": "A salt-gray harbor city trying to govern roads it can no longer fully secure.",
        "text": (
            "Greywake is the campaign's opening city: a harbor of wet stone, ash-stained warehouses, emergency "
            "triage yards, and officials who know every road failure becomes a city problem eventually. Its power "
            "comes from shipping, paperwork, and the stubborn belief that a route can be saved if enough people "
            "are willing to stand in the rain and do the work.\n\n"
            "In Act I, Greywake is not a shining capital. It is a pressured city with too many wounded travelers, "
            "too many missing wagons, and too many factions trying to decide whether the Emberway is still worth "
            "defending."
        ),
    },
    "Emberway": {
        "menu": "The old road artery whose milestones, shrines, and tollmarks still shape Act I.",
        "text": (
            "The Emberway is more than a trade road. It is an Accord-era route laid across older survey lines, "
            "reinforced with milemarkers, culverts, watchpoints, signal stones, and shrine-lanterns. Travelers use "
            "it because the alternatives are slower and meaner, but every wagon that moves along it also enters a "
            "contest over who gets to define safe passage.\n\n"
            "When the Ashen Brand starts forging authority along the Emberway, the threat is not just violence. "
            "False papers, fake checkpoints, controlled rumors, and staged rescues can make a road obey the wrong "
            "masters long before anyone admits the route has fallen."
        ),
    },
    "Iron Hollow": {
        "menu": "A frontier hub built around claims, supply ledgers, and stubborn local survival.",
        "text": (
            "Iron Hollow is the Act I hub: a hard-working settlement with mine claims, supply posts, inn rooms, "
            "orchard walls, council arguments, and a population tired of being treated as someone else's margin "
            "note. The town survives because people keep showing up for one another even when the road fails them.\n\n"
            "That makes Iron Hollow the heart of grounded heroics. Reopening the Emberway means food arrives, "
            "tools move, wounded people get medicine, and families stop making every plan around fear."
        ),
    },
    "Lantern Shrine Network": {
        "menu": "Wayside refuges where road faith, first aid, and rumor all meet.",
        "text": (
            "The Lantern Shrine Network grew around small waystations that keep lamps burning for travelers. Some "
            "are staffed by faithful caretakers, some by volunteers, and some by whoever survived long enough to "
            "light the wick again.\n\n"
            "In story terms, a lantern shrine is never only holy ground. It is a field hospital, message drop, "
            "weather shelter, witness stand, and moral test. Who gets treated first? Which report gets believed? "
            "Which names are spoken aloud when the road starts taking people?"
        ),
    },
    "Blackglass Well": {
        "menu": "A cracked waterwork where old salvage, grave dust, and route history surface.",
        "text": (
            "Blackglass Well is an Accord-era waterwork whose dark lining still holds heat and memory. Salvagers "
            "come for copper, pumps, old seals, and anything a hungry market will buy. The trouble is that some "
            "systems were buried for reasons better than forgetfulness.\n\n"
            "The site gives Act I a different flavor of danger: not raiders on the road, but people profiting from "
            "the frontier's dead infrastructure before anyone understands what they have reopened."
        ),
    },
    "Red Mesa Hold": {
        "menu": "A raider stronghold on broken red stone above the trade cuts.",
        "text": (
            "Red Mesa Hold overlooks dry cuts and supply approaches where a disciplined raiding band can make "
            "itself feel larger than it is. Its danger is logistical as much as martial: one fortified height can "
            "shape which wagons move, which scouts vanish, and which town leaders start bargaining with fear.\n\n"
            "The hold also shows how old Accord routes can be repurposed. A place built to watch the land can "
            "become a fist around it."
        ),
    },
    "Cinderfall Ruins": {
        "menu": "A scorched relay ruin that hints at older signal logic beneath Act I.",
        "text": (
            "Cinderfall Ruins mark one of the frontier's half-understood signal scars. Burned stone, fused brackets, "
            "and relay fragments suggest the Meridian Accord once moved instructions through the region faster than "
            "horses could carry them.\n\n"
            "For the current story, Cinderfall is a hinge between ordinary bandit pressure and the stranger question "
            "underneath it: what happens when people learn to imitate a system the world forgot how to question?"
        ),
    },
    "Duskmere Manor": {
        "menu": "A buried estate whose cellars turn local extortion into an older secret.",
        "text": (
            "Duskmere Manor is the renamed Act I manor site: a broken estate over sealed rooms, smuggling paths, "
            "and old stone that never quite stopped listening. It looks like a gang hideout from the surface, which "
            "is exactly why it works so well as one.\n\n"
            "Below the rot and bravado, the manor points toward the campaign's deeper pattern. People think they are "
            "using ruins as cover. The ruins may be using them as evidence."
        ),
    },
    "Vein of Glass": {
        "menu": "The Act II region where claims, echoes, and old water-control systems converge.",
        "text": (
            "The Vein of Glass is a fractured region of mineral seams, flooded cuts, reflective stone, broken "
            "prospects, and old intake works. It draws miners, reclaimers, claim lawyers, scavengers, and zealots "
            "because every exposed layer seems to promise proof of something valuable.\n\n"
            "Act II turns the campaign from road control toward memory control. The question is no longer only who "
            "owns the route. It is who gets to define what the buried world was trying to say."
        ),
    },
    "Resonant Vaults": {
        "menu": "The deep ruin complex beneath Act II, where record and reality begin to blur.",
        "text": (
            "The Resonant Vaults are the Act II deep site: a network of galleries, flooded crossings, tuned chambers, "
            "and command spaces where Meridian systems still answer patterns, titles, and lies. The vaults do not "
            "feel dead. They feel paused.\n\n"
            "The Quiet Choir wants the Vaults because a system that remembers authority can be taught to obey a new "
            "voice. The player reaches them after seeing what route control did above ground, which makes the deeper "
            "threat easier to understand and harder to dismiss."
        ),
    },
    "Meridian Forge": {
        "menu": "The Act II convergence point where old infrastructure can be repaired or weaponized.",
        "text": (
            "The Meridian Forge is not just a workshop. It is a control chamber for making broken systems agree with "
            "one another again. In merciful hands, it could stabilize routes, waterworks, and signal relays. In the "
            "wrong hands, it could make oppression look like restored order.\n\n"
            "That is why the Forge matters to the long arc of Roads That Remember. It forces the story to ask whether "
            "a broken world should be repaired exactly as it was, or whether survival requires refusing some of the "
            "old system's permissions."
        ),
    },
}


CLASS_LORE: dict[str, LoreEntry] = {
    "Barbarian": {
        "label": "Barbarian",
        "menu": "Front-line survivors who turn pressure into momentum.",
        "text": (
            "In Aethrune, the Barbarian is the person who reaches the breach first and refuses to let it widen. "
            "Their fury is not mindless anger; it is a practiced survival state built from pain tolerance, field "
            "instinct, and the hard knowledge that hesitation can kill a whole caravan.\n\n"
            "Barbarians fit the Shatterbelt as convoy breakers, tunnel guardians, militia shock troops, or people "
            "who learned to survive when the road stopped being fair."
        ),
    },
    "Bard": {
        "label": "Bard",
        "menu": "Voice, rhythm, and social timing turned into battlefield force.",
        "text": (
            "Bards understand that Aethrune is built from patterns: songs, signals, ledgers, rumors, prayers, "
            "and names repeated until people obey them. A Bard can read a room, bend morale, expose a lie, and "
            "make a crowd remember courage at exactly the right second.\n\n"
            "The current class fantasy is a field performer, signal-reader, "
            "and morale architect who can turn attention itself into a tool."
        ),
    },
    "Cleric": {
        "label": "Cleric",
        "menu": "Lantern faith and disciplined channeling made practical.",
        "text": (
            "Clerics carry faith into places where faith has to do work: triage yards, flooded claims, frightened "
            "milehouses, and rooms where nobody wants to say how many names are missing. Their power is framed as "
            "lantern discipline, oath, doctrine, and practiced channeling rather than borrowed setting theology.\n\n"
            "A Cleric in Roads That Remember can be healer, witness, judge, exorcist, or road-priest. The common "
            "thread is responsibility under pressure."
        ),
    },
    "Druid": {
        "label": "Druid",
        "menu": "Land-sense, weathercraft, and living systems in one tradition.",
        "text": (
            "Druids know that Aethrune's wilderness is not separate from its ruins. Roots break culverts, water "
            "finds old channels, beasts nest in signal towers, and the land remembers every system that tried to "
            "discipline it.\n\n"
            "They make excellent frontier protagonists because they can tell when a road is merely damaged and when "
            "the world around it is rejecting the lie someone built into it."
        ),
    },
    "Fighter": {
        "label": "Fighter",
        "menu": "Disciplined arms, armor, and judgment without theatrics.",
        "text": (
            "Fighters are professional fighters in the broadest sense: caravan guards, militia captains, duelists, "
            "retired soldiers, bodyguards, and people who know where to stand when everyone else starts panicking.\n\n"
            "A Fighter is valuable in Aethrune because most crises are practical before they are dramatic. Hold the "
            "door. Keep the line. Choose the right target. Get everyone home."
        ),
    },
    "Monk": {
        "label": "Monk",
        "menu": "Body, breath, and attention trained until motion becomes answer.",
        "text": (
            "Monks come from orders, schools, shrine paths, and hard private disciplines that teach the body to "
            "become a reliable instrument. Their calm is not softness. It is compression.\n\n"
            "On the frontier, a Monk brings control into places ruled by mud, fear, crowd noise, and bad footing. "
            "That makes restraint feel dangerous in the best possible way."
        ),
    },
    "Paladin": {
        "label": "Paladin",
        "menu": "Sworn conviction made visible in shield, voice, and light.",
        "text": (
            "Paladins are people whose promises have become load-bearing structures. They walk into corruption, "
            "extortion, and despair carrying an oath that does not bend just because the road got expensive.\n\n"
            "They are not defined by a borrowed pantheon. They are defined by what they have sworn to protect when "
            "the old systems offer easier answers."
        ),
    },
    "Ranger": {
        "label": "Ranger",
        "menu": "Trackers, scouts, and route-keepers who know what roads hide.",
        "text": (
            "Rangers read the world before it explains itself. A wrong silence, a bent weed, a fresh wheel cut, "
            "a frightened horse, or a missing lantern tells them what a witness might not know how to say.\n\n"
            "The Emberway needs Rangers because maps are too clean. Roads are lived things, and somebody has to "
            "notice when the route starts lying."
        ),
    },
    "Rogue": {
        "label": "Rogue",
        "menu": "Precision, nerve, and side-door thinking under pressure.",
        "text": (
            "Rogues survive by seeing openings other people miss. Locks, false papers, quiet steps, coded marks, "
            "crowd flow, and bad assumptions are all part of their toolkit.\n\n"
            "In Aethrune, that makes them more than thieves. A Rogue is often the only person who can move through "
            "a controlled route without becoming part of the control."
        ),
    },
    "Sorcerer": {
        "label": "Sorcerer",
        "menu": "Innate channeling shaped by unstable power in the blood or body.",
        "text": (
            "Sorcerers carry power that arrived before permission. Some inherit it from exposure to energy cores, "
            "signal accidents, lineage scars, or a moment when the world pushed too much force through one life.\n\n"
            "Their story question is control: not whether power exists, but what it costs to make that power answer "
            "without burning the person who carries it."
        ),
    },
    "Warlock": {
        "label": "Warlock",
        "menu": "Borrowed force, dangerous bargains, and obligations with teeth.",
        "text": (
            "Warlocks are channelers whose power comes through a bargain, imprint, patron system, hidden voice, or "
            "other obligation that does not vanish when combat ends. In Aethrune, the old world left many things "
            "capable of answering desire.\n\n"
            "That makes Warlocks compelling because every useful gift raises a second question: who else heard the "
            "promise being made?"
        ),
    },
    "Wizard": {
        "label": "Wizard",
        "menu": "Studied channeling, pattern logic, and field scholarship.",
        "text": (
            "Wizards treat power as something that can be notated, tested, corrected, and improved. They read ruin "
            "marks, copy channel patterns, compare field journals, and turn old symbols into present leverage.\n\n"
            "A Wizard belongs naturally in the Resonant Vaults arc because the world keeps leaving instructions, "
            "and not all instructions deserve obedience."
        ),
    },
}


RACE_LORE: dict[str, LoreEntry] = {
    "Human": {
        "label": "Human",
        "menu": "Adaptable rebuilders who became the backbone of the post-Accord world.",
        "text": (
            "Humans are Aethrune's most numerous and varied people. During the Meridian Accord they were workers, "
            "traders, soldiers, clerks, couriers, and citizens. After the collapse, they became the survivors most "
            "likely to rebuild a town from whatever still stood.\n\n"
            "Human characters fit almost any path because adaptation is their inheritance."
        ),
    },
    "Dwarf": {
        "label": "Dwarf",
        "menu": "Deep infrastructure keepers shaped by stone, craft, and endurance.",
        "text": (
            "Dwarves maintained tunnels, foundations, load-bearing works, and deep systems under the old Accord. "
            "When surface authority failed, many endured below and emerged into a world that had become less reliable "
            "than the stone they trusted.\n\n"
            "They value craft because a bad join can kill generations later."
        ),
    },
    "Elf": {
        "label": "Elf",
        "menu": "Long-memory observers who carry fragments others forgot.",
        "text": (
            "Elves were archivists, continuity keepers, observers, and record minds within the old systems. "
            "They saw pieces of the collapse coming, but not enough to stop it cleanly.\n\n"
            "In play, an Elf character can make memory feel active rather than ornamental: a burden, a warning, "
            "and sometimes a weapon."
        ),
    },
    "Halfling": {
        "label": "Halfling",
        "menu": "Quick couriers and small-route survivors who thrive when systems fail.",
        "text": (
            "Halflings were messengers, small traders, and route improvisers even before the collapse. When big "
            "systems failed, they adapted faster than anyone who had depended on official permissions.\n\n"
            "Their courage is practical: keep moving, keep laughing when possible, and never let a giant institution "
            "convince you it is the whole world."
        ),
    },
    "Dragonborn": {
        "label": "Forged",
        "menu": "Forged survivors marked by ancient systems and visible power.",
        "text": (
            "Forged are living remnants of catastrophic fusion between flesh, authority, and old machinery. Some "
            "show metallic growth, strange heat, luminous eyes, or bodies that seem half-designed by a failed system.\n\n"
            "They are often feared because they make the Meridian past impossible to treat as safely dead."
        ),
    },
    "Gnome": {
        "label": "Unrecorded",
        "menu": "Unrecorded people whose presence resists easy categorization.",
        "text": (
            "Unrecorded people are rare and difficult to categorize. Old Accord records either missed them, erased them, or "
            "failed to hold them in a stable way. That absence has become part of their identity.\n\n"
            "An Unrecorded character suits curious, inventive, evasive, or pattern-breaking roles: someone the ledger cannot "
            "quite pin down."
        ),
    },
    "Half-Elf": {
        "label": "Elven Variant",
        "menu": "Pattern-sensitive observers partly out of sync with ordinary perception.",
        "text": (
            "Elven Variants emerged from elven lines exposed to unstable signal systems. They notice discontinuities, "
            "echoes, and false alignments others miss, but perception can become lonely when nobody else trusts the "
            "same evidence.\n\n"
            "They are excellent characters for reading the world's quiet wrongness before it becomes loud."
        ),
    },
    "Half-Orc": {
        "label": "Orc-Blooded",
        "menu": "Borderline inheritors of Orukh endurance and mixed-world pressure.",
        "text": (
            "Orc-Blooded people often move between communities that expect them to prove what should not need "
            "proving: loyalty, restraint, usefulness, or belonging. Many respond by becoming impossible to ignore.\n\n"
            "Their stories fit Aethrune's borderlands well because the Shatterbelt itself is built from mixed claims "
            "and disputed authority."
        ),
    },
    "Tiefling": {
        "label": "Fire-Blooded",
        "menu": "Fire-blooded people shaped by inner heat, restraint, and volatile inheritance.",
        "text": (
            "Fire-Blooded people descend from populations changed by proximity to old energy cores. Their bodies may show "
            "warm skin tones, emberlike eyes, or veins that glow under stress.\n\n"
            "Fire-Blooded culture values control because power that leaks at the wrong moment can become someone else's "
            "excuse to fear you."
        ),
    },
    "Goliath": {
        "label": "Riverfolk",
        "menu": "River and coast-adapted people who prize motion over rigidity.",
        "text": (
            "Riverfolk are tied to water-control systems, flood channels, rivers, and coastal change. Their cultures "
            "often prefer flexible agreements over rigid institutions because water has taught them that survival is "
            "movement with memory.\n\n"
            "A Riverfolk adventurer brings that flow into every hard place the party enters."
        ),
    },
    "Orc": {
        "label": "Orukh",
        "menu": "Powerful fringe survivors who learned not to depend on central systems.",
        "text": (
            "The Orukh lived at the edges of Accord benefit and often survived without trusting central promises. "
            "When the collapse came, that independence became preparation.\n\n"
            "Orukh characters carry strength, community loyalty, and suspicion of any authority that demands obedience "
            "before earning trust."
        ),
    },
}


BACKGROUND_LORE: dict[str, LoreEntry] = {
    "Soldier": {
        "label": "Route Veteran",
        "menu": "A guard, patrol hand, or militia survivor shaped by hard marches.",
        "text": (
            "Route Veterans know how quickly a checkpoint becomes a grave marker when command fails. They understand "
            "formations, ration math, frightened recruits, and the difference between bravery and simply having no "
            "safe place to retreat."
        ),
    },
    "Acolyte": {
        "label": "Lantern Acolyte",
        "menu": "A shrine-tender, field medic, or doctrine keeper from the road faiths.",
        "text": (
            "Lantern Acolytes keep lamps burning where travel turns dangerous. Their work is practical devotion: "
            "washing wounds, recording names, settling panic, and deciding what mercy requires when supplies run thin."
        ),
    },
    "Criminal": {
        "label": "Veil Broker",
        "menu": "A smuggler, lock hand, or papers-forger who knows hidden routes.",
        "text": (
            "Veil Brokers understand the underside of Aethrune's roads. False seals, quiet doors, smuggled food, "
            "coded favors, and borrowed identities can be crimes, survival tools, or both depending on who writes the law."
        ),
    },
    "Sage": {
        "label": "Accord Scholar",
        "menu": "A reader of old systems, failed ledgers, and dangerous precedent.",
        "text": (
            "Accord Scholars study ruins because old decisions still have teeth. They know that a treaty, relay note, "
            "or maintenance log can explain why a modern town is bleeding."
        ),
    },
    "Outlander": {
        "label": "Trail-Wise",
        "menu": "A camp survivor who trusts weather, tracks, and lived distance.",
        "text": (
            "Trail-Wise characters know the land outside official maps. They read firepits, river height, animal panic, "
            "and the human habit of pretending a bad road is safe because the alternative is expensive."
        ),
    },
    "Charlatan": {
        "label": "Maskwright",
        "menu": "A fraud, performer, or confidence reader who knows how belief moves.",
        "text": (
            "Maskwrights understand that identity is often a performance other people agree to believe. On the Emberway, "
            "that makes them useful against forged authority and dangerous when they decide to forge back."
        ),
    },
    "Guild Artisan": {
        "label": "Guildwright",
        "menu": "A craftsperson trained in prices, materials, supply, and reputation.",
        "text": (
            "Guildwrights know the practical machinery of town life: who supplies nails, who can repair a hinge, who "
            "owes whom, and why a missing wagon can break more than one household."
        ),
    },
    "Hermit": {
        "label": "Quiet Witness",
        "menu": "A secluded seeker who learned to notice signs before crowds do.",
        "text": (
            "Quiet Witnesses step away from noise long enough to hear pattern. Some study herbs, some omens, some old "
            "doctrine, and some merely know what people sound like when they are about to lie to themselves."
        ),
    },
}


ABILITY_LORE: dict[str, LoreEntry] = {
    "STR": {
        "label": "Strength",
        "menu": "Raw force, lifting, breaking, climbing, and close-quarters pressure.",
        "text": "Strength measures the ability to move weight, force doors, grapple, haul gear, and turn physical mass into action.",
    },
    "DEX": {
        "label": "Agility",
        "menu": "Speed, finesse, balance, stealth, and quick hands.",
        "text": "Agility covers initiative, careful movement, ranged aim, quiet steps, and the hand precision needed for delicate work.",
    },
    "CON": {
        "label": "Endurance",
        "menu": "Stamina, pain tolerance, poison resistance, and staying upright.",
        "text": "Endurance decides how much punishment, sickness, hunger, panic, and exhaustion a character can survive before breaking.",
    },
    "INT": {
        "label": "Intelligence",
        "menu": "Study, pattern recognition, memory, and system reasoning.",
        "text": "Intelligence helps decode Accord records, read old machinery, connect clues, and understand what a ruin was designed to do.",
    },
    "WIS": {
        "label": "Wisdom",
        "menu": "Perception, instinct, medicine, wayfinding, and reading the moment.",
        "text": "Wisdom is the sense that catches tracks, lies, infection, danger, weather, and the emotional shape of a room.",
    },
    "CHA": {
        "label": "Charisma",
        "menu": "Force of personality, social pressure, command, and performance.",
        "text": "Charisma is the ability to make people listen, believe, flinch, rally, confess, or follow when the outcome is uncertain.",
    },
}


SKILL_LORE: dict[str, LoreEntry] = {
    "Acrobatics": {"menu": "Balance, tumbling, slips, falls, and unstable footing.", "text": "Acrobatics keeps a character moving when roofs sag, bridges tilt, and a fight spills across broken ground."},
    "Animal Handling": {"menu": "Working with mounts, hounds, livestock, and frightened beasts.", "text": "Animal Handling reads the panic and trust of living creatures, especially on roads where horses often know trouble first."},
    "Arcana": {"label": "System Lore", "menu": "Knowledge of channeling, relics, old signals, and unstable forces.", "text": "System Lore explains Meridian machinery, channel patterns, relic behavior, and the difference between a miracle and a malfunction."},
    "Athletics": {"menu": "Climbing, swimming, jumping, grappling, and hard exertion.", "text": "Athletics is the body's answer when the route collapses, the gate sticks, or somebody has to hold a line by force."},
    "Deception": {"menu": "Lies, masks, forged confidence, and controlled misdirection.", "text": "Deception matters because Aethrune's factions often win by making false authority look official long enough to matter."},
    "History": {"menu": "Old records, battles, settlements, treaties, and ruins.", "text": "History turns names and buried stone into context, especially when the Meridian past keeps repeating through modern choices."},
    "Insight": {"label": "Reading", "menu": "Understanding motive, fear, pressure, and concealed intent.", "text": "Reading catches the moment when a witness edits the truth, a leader hides panic, or a negotiator smiles too late."},
    "Intimidation": {"menu": "Threat, command presence, and controlled menace.", "text": "Intimidation is the art of making consequences visible before anyone has to bleed for them."},
    "Investigation": {"menu": "Searching scenes, testing claims, and connecting evidence.", "text": "Investigation follows scratches, ledgers, footprints, missing objects, false seals, and the quiet math of what does not fit."},
    "Medicine": {"menu": "Triage, disease, wounds, fatigue, and field care.", "text": "Medicine keeps people alive when the shrine is full, the rain will not stop, and the next wagon is already overdue."},
    "Nature": {"menu": "Weather, terrain, plants, beasts, and living patterns.", "text": "Nature explains how the land reacts when roads, mines, and waterworks push too hard against it."},
    "Perception": {"menu": "Noticing threats, details, movement, sound, and ambush signs.", "text": "Perception is the skill of catching danger before it becomes a headline in someone else's ledger."},
    "Performance": {"menu": "Voice, rhythm, storytelling, public timing, and staged emotion.", "text": "Performance can rally survivors, distract a room, sell a false role, or make a truth memorable enough to travel."},
    "Persuasion": {"menu": "Honest pressure, negotiation, appeals, and earned trust.", "text": "Persuasion moves people without hiding the ask, which makes it precious in towns tired of being manipulated."},
    "Religion": {"label": "Doctrine", "menu": "Shrine law, ritual practice, oaths, cults, and sacred obligations.", "text": "Doctrine covers Lantern rites, funeral names, oath language, forbidden symbols, and the difference between faith and control."},
    "Sleight of Hand": {"label": "Handwork", "menu": "Quick fingers, hidden objects, small mechanisms, and misdirection.", "text": "Handwork handles palms, pins, seals, pockets, and the tiny movements that decide whether a plan survives contact."},
    "Stealth": {"menu": "Quiet movement, concealment, shadowing, and not being where eyes expect.", "text": "Stealth lets a character move through controlled roads, occupied ruins, and frightened towns without becoming another report."},
    "Survival": {"label": "Wayfinding", "menu": "Tracking, foraging, route sense, weather reading, and camp judgment.", "text": "Wayfinding keeps a party alive when maps are wrong, food is thin, and the road ahead has started lying."},
}


FEATURE_LORE: dict[str, LoreEntry] = {
    "rage": {"label": "Battle Surge", "menu": "A Barbarian's focused state of pressure and pain tolerance.", "text": "Battle Surge turns fear and injury into forward motion, hardening the body while the Barbarian forces the fight to answer them."},
    "unarmored_defense_barbarian": {"label": "Scar Guard", "menu": "Defense from instinct, endurance, and refusal to yield.", "text": "Scar Guard represents survival reflexes so practiced that armor is no longer the only way to stay standing."},
    "bard_spellcasting": {"label": "Bard Channeling", "menu": "Patterned voice and rhythm that shape reality.", "text": "Bard Channeling uses tone, cadence, memory, and attention as tools for support and disruption."},
    "bardic_inspiration": {"label": "Rally Note", "menu": "A timed word or phrase that helps an ally exceed themselves.", "text": "A Rally Note gives someone the exact push they need before doubt can settle into their hands."},
    "cleric_spellcasting": {"label": "Cleric Channeling", "menu": "Disciplined faith turned into healing, protection, and judgment.", "text": "Cleric Channeling frames power as service under pressure: mend the wounded, steady the frightened, and push back the dark."},
    "druid_spellcasting": {"label": "Druid Channeling", "menu": "Living systems, weather, and land-sense shaped into force.", "text": "Druid Channeling listens to the land's older intelligence and answers with growth, flame, water, and endurance."},
    "second_wind": {"label": "Second Breath", "menu": "A Fighter's practiced recovery in the middle of danger.", "text": "Second Breath is the moment training takes over and a wounded fighter finds enough air for one more push."},
    "martial_arts": {"label": "Close Form", "menu": "Disciplined strikes built from posture and timing.", "text": "Close Form turns movement into offense without needing heavy arms or armor to define the fighter."},
    "unarmored_defense_monk": {"label": "Empty-Hand Guard", "menu": "Defense through balance, breath, and disciplined motion.", "text": "Empty-Hand Guard keeps a Monk alive by making stillness, angle, and timing do the work of a shield."},
    "lay_on_hands": {"label": "Oath Mend", "menu": "A Paladin's sworn reserve of restorative force.", "text": "Oath Mend is care made immediate: a promise to protect translated through steady hands."},
    "divine_smite": {"label": "Vowstrike", "menu": "A close strike charged by conviction.", "text": "Vowstrike spends inner reserve to make a weapon blow carry the weight of an oath."},
    "natural_explorer": {"label": "Route Sense", "menu": "A Ranger's practiced edge in wild and broken routes.", "text": "Route Sense means terrain is never just scenery; it is evidence, warning, and opportunity."},
    "sneak_attack": {"label": "Veilstrike", "menu": "Precision damage when an opening appears.", "text": "Veilstrike rewards the Rogue for choosing the exact moment when defense becomes assumption."},
    "expertise": {"label": "Deep Practice", "menu": "A skill refined past ordinary competence.", "text": "Deep Practice marks the difference between knowing a trick and building a life around it."},
    "sorcerer_spellcasting": {"label": "Sorcerer Channeling", "menu": "Innate power shaped by instinct and control.", "text": "Sorcerer Channeling is volatile force made useful before it burns through the person carrying it."},
    "warlock_spellcasting": {"label": "Warlock Channeling", "menu": "Power drawn through bargain, imprint, or obligation.", "text": "Warlock Channeling is useful because something answered; it is dangerous because something may still be listening."},
    "wizard_spellcasting": {"label": "Wizard Channeling", "menu": "Studied patterns, notation, and repeatable power.", "text": "Wizard Channeling turns field notes and old symbols into controlled effects."},
    "arcane_recovery": {"label": "Pattern Recovery", "menu": "A Wizard's ability to restore channeling focus through review.", "text": "Pattern Recovery represents the scholar's habit of fixing the mind by returning to first principles."},
    "darkvision": {"label": "Lowlight Sight", "menu": "Eyes adapted to dim routes, tunnels, and old chambers.", "text": "Lowlight Sight marks people whose bodies learned to treat darkness as information rather than absence."},
    "dwarven_resilience": {"label": "Dwarven Resilience", "menu": "Deep-born resistance to poison, fatigue, and bad air.", "text": "Dwarven Resilience comes from generations shaped by tunnels, minerals, pressure, and stubborn survival."},
    "keen_senses": {"label": "Keen Senses", "menu": "Long-trained perception and memory working together.", "text": "Keen Senses catch small details because the mind has learned to wait for them."},
    "fey_ancestry": {"label": "Signal Distance", "menu": "A mind that resists easy influence and false resonance.", "text": "Signal Distance makes outside pressure slide off because the self is tuned to an older, steadier rhythm."},
    "lucky": {"label": "Halfling Luck", "menu": "A small survivor's talent for disaster missing by inches.", "text": "Halfling Luck is not destiny. It is readiness, motion, and a lifetime of refusing to be where danger expected."},
    "brave": {"label": "Small Courage", "menu": "Fear acknowledged, then stepped through anyway.", "text": "Small Courage suits Halflings because they know fear well enough not to worship it."},
    "draconic_presence": {"label": "Forged Presence", "menu": "A Forged aura of visible power and old-system weight.", "text": "Forged Presence makes authority physical, whether the Forged character wants that attention or not."},
    "gnome_cunning": {"label": "Unrecorded Cunning", "menu": "A mind hard for old systems to categorize or corner.", "text": "Unrecorded Cunning lets an Unrecorded character slip through assumptions built by ledgers, categories, and tidy answers."},
    "relentless_endurance": {"label": "Orcish Grit", "menu": "The refusal to fall when collapse seems reasonable.", "text": "Orcish Grit is survival as an argument: the world says enough, and the body says not yet."},
    "menacing": {"label": "Hard Stare", "menu": "Charisma sharpened by a life of being tested.", "text": "Hard Stare makes a warning land before steel has to."},
    "hellish_resistance": {"label": "Fire-Blooded Resistance", "menu": "Fire-Blooded heat tolerance and inner fire control.", "text": "Fire-Blooded Resistance lets Fire-Blooded people survive heat, surge, and stress that would break a colder body."},
    "stone_endurance": {"label": "Riverfolk Endurance", "menu": "Riverfolk toughness shaped by pressure and motion.", "text": "Riverfolk Endurance absorbs impact the way water and stone share a lesson: bend, brace, continue."},
    "adrenaline_rush": {"label": "Orc Rush", "menu": "A sudden burst of forward survival.", "text": "Orc Rush closes distance before hesitation can become a cage."},
}


APPENDIX_A_ENTRIES: dict[str, LoreEntry] = {
    "Appendix A: Blinded": {"menu": "A creature cannot rely on sight.", "text": "Blinded means visual information is gone or unreliable. In Aethrune terms, the character suffers strain on sight-based actions and gives enemies edge when sight would protect them."},
    "Appendix A: Charmed / Swayed": {"menu": "Influence clouds judgment toward the source.", "text": "Swayed characters are socially or supernaturally tilted toward a source and cannot treat that source as a clear enemy until the effect breaks."},
    "Appendix A: Deafened": {"menu": "A creature cannot rely on hearing.", "text": "Deafened blocks sound cues, spoken warnings, and signal rhythms. It matters in ruins where sound often arrives before danger does."},
    "Appendix A: Frightened / Shaken": {"menu": "Fear interferes with direct action.", "text": "Shaken characters struggle while the source of fear dominates the scene. In public language, this usually appears as strain on direct pressure against the fear."},
    "Appendix A: Grappled": {"menu": "Movement is physically pinned or controlled.", "text": "Grappled means someone or something has locked down movement. Escape usually calls for Strength or Agility under pressure."},
    "Appendix A: Incapacitated": {"menu": "A creature cannot take meaningful actions.", "text": "Incapacitated is a severe state where the character cannot act normally, whether from shock, pain, binding, or overwhelming force."},
    "Appendix A: Invisible / Veiled": {"menu": "A creature cannot be seen without special help.", "text": "Veiled targets are hidden from ordinary sight. Attacks against them suffer strain unless another sense or clue reveals the right angle."},
    "Appendix A: Paralyzed / Locked": {"menu": "A creature is held rigid and cannot move.", "text": "Locked characters cannot move or speak effectively. Close-range danger becomes much worse because defense has collapsed."},
    "Appendix A: Petrified": {"menu": "A creature is transformed into inert matter.", "text": "Petrified is rare and terrifying: the body becomes rigid matter, suspending ordinary action until the effect is reversed."},
    "Appendix A: Poisoned": {"menu": "Toxin or sickness weakens action.", "text": "Poisoned characters act under strain as the body fights venom, illness, bad air, or contaminated relic residue."},
    "Appendix A: Prone": {"menu": "A creature is down on the ground.", "text": "Prone means footing has failed. Standing costs time, close enemies gain openings, and distant attacks become less certain."},
    "Appendix A: Restrained": {"menu": "Movement is limited by bindings, rubble, or force.", "text": "Restrained characters can still think and struggle, but their movement is limited enough that enemies can exploit the position."},
    "Appendix A: Stunned / Disrupted": {"menu": "A creature loses the thread of action.", "text": "Disrupted means shock, impact, or signal interference has broken the character's ability to act for a moment."},
    "Appendix A: Unconscious": {"menu": "A creature is down, unaware, and unable to act.", "text": "Unconscious characters cannot defend themselves, speak, move, or choose actions until restored or stabilized."},
}


APPENDIX_LORE: dict[str, LoreEntry] = {
    "Appendix A: Conditions": {
        "menu": "Aethrune-facing names for major combat states.",
        "text": (
            "Contents:\n"
            + "\n".join(f"- {name.removeprefix('Appendix A: ')}" for name in APPENDIX_A_ENTRIES)
            + "\n\nThese entries keep the combat chassis readable while moving the public vocabulary toward Aethrune terms."
        ),
    },
    **APPENDIX_A_ENTRIES,
    "Appendix B: Lantern Faith": {
        "menu": "Road shrines, witness lamps, field mercy, and practical doctrine.",
        "text": (
            "The Lantern Faith is not a single centralized church. It is a family of road practices built around lamps, "
            "names, triage, funeral memory, safe passage, and the belief that people deserve to be witnessed when systems fail."
        ),
    },
    "Appendix B: Shrine-Lanterns": {
        "menu": "Small lights that mark refuge, warning, and obligation.",
        "text": "Shrine-lanterns are practical sacred objects: part signal, part promise, part emergency sign that someone still accepts responsibility here.",
    },
    "Appendix B: Oaths": {
        "menu": "Public promises treated as load-bearing social structures.",
        "text": "In Aethrune, an oath matters because institutions are unreliable. A sworn person becomes a structure others may lean on, for good or harm.",
    },
    "Appendix B: Funeral Names": {
        "menu": "The practice of recording the dead so routes cannot erase them.",
        "text": "Lantern caretakers record names after ambushes, floods, cave-ins, and failed crossings. A name kept properly is a small refusal of disappearance.",
    },
    "Appendix B: False Doctrine": {
        "menu": "When faith language becomes a tool of control.",
        "text": "The Quiet Choir often imitates comfort, confession, and order. The danger is not belief itself, but belief turned into obedience without consent.",
    },
    "Appendix C: Factions Overview": {
        "menu": "The major powers competing over roads, records, claims, and truth.",
        "text": (
            "Aethrune's factions are defined by what they think should control the future: force, testimony, trade, repair, faith, or hidden authority. "
            "Most are not pure villains or pure heroes, but each becomes dangerous when its answer is the only answer allowed."
        ),
    },
    "Appendix C: Ashen Brand": {
        "menu": "Route extortion, forged authority, and profitable fear.",
        "text": "The Ashen Brand wins by making travelers believe the road already belongs to them. Their tools include raids, fake checkpoints, stolen papers, and selective mercy.",
    },
    "Appendix C: Quiet Choir": {
        "menu": "Signal control, whispered doctrine, and obedience disguised as peace.",
        "text": "The Quiet Choir wants old systems to answer a new voice. They prefer alignment over argument and call that silence harmony.",
    },
    "Appendix C: Free Operators": {
        "menu": "Independent drivers, scouts, couriers, and troubleshooters.",
        "text": "Free Operators keep routes alive without waiting for permission. Some are heroic, some are opportunists, and most know exactly what a delayed wagon costs.",
    },
    "Appendix C: Meridian Reclaimers": {
        "menu": "Scholars and salvage crews trying to repair what can be trusted.",
        "text": "Meridian Reclaimers believe broken infrastructure can be studied, stabilized, and reused. Their best members are careful; their worst confuse usefulness with innocence.",
    },
    "Appendix C: Iron Hollow Council": {
        "menu": "Local leadership balancing fear, claims, trade, and survival.",
        "text": "The Iron Hollow Council is less grand than necessary. It has to decide which crisis gets labor, guards, marks, and public trust before the next wagon fails to arrive.",
    },
    "Appendix C: Ironbound Guild": {
        "menu": "Supply, tools, claims, and the hard politics of repair.",
        "text": "The Ironbound Guild controls practical goods and skilled labor. That makes it essential in a crisis and tempting to anyone who wants leverage over the town.",
    },
    "Appendix C: Delvers' Exchange": {
        "menu": "Claim records, salvage reports, and dangerous information.",
        "text": "The Delvers' Exchange handles claims and discoveries. Its ledgers can settle disputes, start them, or reveal that someone has been mining the wrong truth.",
    },
    "Appendix D: Aethrune Cosmology": {
        "menu": "How the world treats echoes, channels, relics, and system memory.",
        "text": "Aethrune does not need distant named planes to feel strange. Its wonder comes from resonance, buried command logic, living memory, and old systems that still shape the present.",
    },
    "Appendix D: The Near World": {
        "menu": "The lived surface of roads, towns, ruins, rivers, and weather.",
        "text": "The Near World is ordinary life under extraordinary inheritance: markets, milehouses, shrines, flood channels, farms, towers, and the people trying to keep them working.",
    },
    "Appendix D: Resonance": {
        "menu": "Patterned force that lets channeling, signals, and old records matter.",
        "text": "Resonance is the setting's connective logic. Words, symbols, routes, tones, and titles can matter because the world still contains systems built to answer them.",
    },
    "Appendix D: Meridian Depths": {
        "menu": "The old lower systems where infrastructure becomes mythic.",
        "text": "The Meridian Depths are not one place but a category of buried spaces: vaults, drains, control rooms, sealed galleries, and machine-lit dark below the known map.",
    },
    "Appendix D: Echo Pockets": {
        "menu": "Localized spaces where memory, route, and cause behave strangely.",
        "text": "Echo pockets are small unstable zones where old events seem to repeat, answer, or resist being contradicted. Some are hazards; some are evidence.",
    },
    "Appendix D: Signal Paths": {
        "menu": "Old routes for command, warning, and coordination.",
        "text": "Signal paths once moved instructions across the Accord. Broken signal paths can still carry influence, especially when someone learns which phrases wake them.",
    },
    "Appendix E: SRD-Derived Mechanics": {
        "menu": "A plain-language note on the current rules chassis.",
        "text": (
            "Roads That Remember currently keeps an SRD-derived d20 math base for character creation, checks, combat timing, conditions, and equipment. "
            "The public presentation is being rethemed in phases so the story, setting, factions, and terminology belong to Aethrune."
        ),
    },
    "Appendix E: Public Vocabulary": {
        "menu": "A quick bridge from old mechanics language to Aethrune language.",
        "text": (
            "Preferred public terms include Guard, strike check, resist check, edge, strain, channeling, draught, script, relic, and marks. "
            "Some internals still use legacy keys until the rules-presentation phase adds display-name adapters across combat, inventory, and saves."
        ),
    },
}


PLANNED_ACTS_LORE = {
    "Act Roadmap": {
        "menu": "How the Aethrune campaign arc is structured inside the game.",
        "text": (
            "Act I follows Greywake, the Emberway, Iron Hollow, and the Ashen Brand's attempt to turn route fear into rule. "
            "Act II descends into the Vein of Glass and the Resonant Vaults, where the Quiet Choir tries to teach old systems a new voice. "
            "Act III points toward the Meridian Depths and the question of whether a broken world should be restored, rewritten, or refused."
        ),
    }
}


TITLE_LORE_SECTIONS: tuple[tuple[str, LoreSection], ...] = (
    ("World & Locations", LOCATION_LORE),
    ("Classes", CLASS_LORE),
    ("Peoples", RACE_LORE),
    ("Backgrounds", BACKGROUND_LORE),
    ("Core Abilities", ABILITY_LORE),
    ("Skills", SKILL_LORE),
    ("Features & Abilities", FEATURE_LORE),
    ("Appendices", APPENDIX_LORE),
)


ABILITY_LABELS = {
    "STR": "Strength",
    "DEX": "Dexterity",
    "CON": "Constitution",
    "INT": "Intelligence",
    "WIS": "Wisdom",
    "CHA": "Charisma",
}


CLASS_PRIMARY_STATS = {
    "Barbarian": ["STR", "CON"],
    "Bard": ["CHA", "DEX"],
    "Cleric": ["WIS", "CON"],
    "Druid": ["WIS", "CON"],
    "Fighter": ["STR", "CON"],
    "Monk": ["DEX", "WIS"],
    "Paladin": ["STR", "CHA"],
    "Ranger": ["DEX", "WIS"],
    "Rogue": ["DEX", "WIS"],
    "Sorcerer": ["CHA", "CON"],
    "Warlock": ["CHA", "CON"],
    "Wizard": ["INT", "DEX"],
}


ABILITY_GAMEPLAY_NOTES = {
    "STR": "Used for melee force, Athletics, carrying capacity, and physical contests.",
    "DEX": "Used for initiative, stealth, finesse or ranged accuracy, and many reflex-based resist checks.",
    "CON": "Adds to hit points and helps endure poison, fatigue, and punishment.",
    "INT": "Used for learned knowledge, investigation, and Wizard channeling.",
    "WIS": "Used for perception, intuition, wayfinding, medicine, and Cleric or Druid channeling.",
    "CHA": "Used for social pressure, presence, deception, and Bard, Sorcerer, Paladin, or Warlock channeling.",
}


def public_class_label(class_name: str) -> str:
    return CLASS_PUBLIC_LABELS.get(class_name, class_name)


def public_race_label(race_name: str) -> str:
    return RACE_PUBLIC_LABELS.get(race_name, race_name)


def ability_label(code: str) -> str:
    base = ABILITY_LABELS.get(code, code)
    public = ABILITY_PUBLIC_LABELS.get(code)
    return f"{public} ({base})" if public and public != base else base


def format_bonus_list(bonuses: Mapping[str, int]) -> str:
    return ", ".join(f"{ability_label(ability)} +{value}" for ability, value in bonuses.items())


def format_feature_label(feature_id: str) -> str:
    if feature_id in FEATURE_LORE and FEATURE_LORE[feature_id].get("label"):
        return FEATURE_LORE[feature_id]["label"]
    label = feature_id.replace("_barbarian", "").replace("_monk", "")
    return label.replace("_", " ").title()


def format_feature_entry(feature_id: str, index: int) -> str:
    description = FEATURE_LORE.get(feature_id, {}).get("text", "No description recorded yet.")
    return f"{index}. {format_feature_label(feature_id)}: {description}"


def format_weapon_summary(class_name: str) -> str:
    weapon = CLASSES[class_name]["weapon"]
    attack_stat = weapon.ability
    if attack_stat == "FINESSE":
        attack_stat = "Strength or Agility"
    elif attack_stat == "SPELL":
        attack_stat = "channeling ability"
    else:
        attack_stat = ability_label(attack_stat)
    tags: list[str] = []
    if weapon.ranged:
        tags.append("ranged")
    if weapon.finesse:
        tags.append("finesse")
    if weapon.properties:
        tags.extend(weapon.properties)
    extras = f"; properties: {', '.join(tags)}" if tags else ""
    return f"{weapon.name} dealing {weapon.damage} using {attack_stat}{extras}."


def format_armor_summary(class_name: str) -> str:
    armor = CLASSES[class_name]["armor"]
    shield = "shield included" if CLASSES[class_name]["shield"] else "no shield"
    if armor is None:
        return f"Starts unarmored with {shield}."
    armor_bits = [f"{armor.name} (base Guard {armor.base_ac})", shield]
    if armor.heavy:
        armor_bits.append("heavy shell")
    elif armor.dex_cap is None:
        armor_bits.append("full Agility modifier applies")
    else:
        armor_bits.append(f"Agility bonus capped at +{armor.dex_cap}")
    return ". ".join([armor_bits[0], ", ".join(armor_bits[1:])]) + "."


def format_resource_summary(resources: Mapping[str, int]) -> str:
    if not resources:
        return "No tracked class resources at level 1."
    return ", ".join(f"{name.replace('_', ' ')} {amount}" for name, amount in resources.items())


def format_class_manual(class_name: str) -> str:
    details = CLASSES[class_name]
    public_name = public_class_label(class_name)
    lines = [
        "Gameplay Manual",
        f"Public role: {public_name}",
        f"Main stats: {', '.join(ability_label(stat) for stat in CLASS_PRIMARY_STATS.get(class_name, [])) or 'Flexible'}",
        f"Hit die: d{details['hit_die']}",
        f"Resist proficiencies: {', '.join(ability_label(save) for save in details['saving_throws'])}",
        f"Skill picks: choose {details['skill_picks']} from {', '.join(details['skill_choices'])}",
        f"Starting weapon: {format_weapon_summary(class_name)}",
        f"Guard profile: {format_armor_summary(class_name)}",
        (
            f"Channeling: uses {ability_label(details['spellcasting_ability'])}; "
            f"starting resources {format_resource_summary(details['resources'])}."
            if details["spellcasting_ability"]
            else f"Channeling: none at level 1. Starting resources: {format_resource_summary(details['resources'])}."
        ),
        "Starting abilities:",
    ]
    lines.extend(format_feature_entry(feature_id, index) for index, feature_id in enumerate(details["features"], start=1))
    progression = CLASS_LEVEL_PROGRESSION.get(class_name, {})
    if progression:
        lines.append("Early progression in this game:")
        for level in sorted(progression):
            features = progression[level]["features"]
            feature_text = "; ".join(f"{rules_text(name)}: {rules_text(description)}" for name, description in features)
            lines.append(f"- Level {level}: {feature_text}")
    return "\n".join(lines)


def format_race_manual(race_name: str) -> str:
    details = RACES[race_name]
    lines = [
        "Gameplay Manual",
        f"Public people: {public_race_label(race_name)}",
        f"Ability bonuses: {format_bonus_list(details['bonuses'])}",
        f"Automatic people skills: {', '.join(details['skills']) if details['skills'] else 'None'}",
        "People traits:",
    ]
    if details["features"]:
        lines.extend(format_feature_entry(feature_id, index) for index, feature_id in enumerate(details["features"], start=1))
    else:
        lines.append("1. No extra traits beyond the listed ability increases.")
    return "\n".join(lines)


def format_background_manual(background_name: str) -> str:
    details = BACKGROUNDS[background_name]
    bonuses = details.get("equipment_bonuses", {})
    bonus_text = ", ".join(f"{key} +{value}" for key, value in bonuses.items()) if bonuses else "None"
    return "\n".join(
        [
            "Gameplay Manual",
            f"Background skills: {', '.join(details['skills'])}",
            f"Extra proficiencies: {', '.join(details.get('proficiencies', [])) or 'None'}",
            f"Game-specific passive bonuses: {bonus_text}",
            "Background perks:",
            *[f"- {note}" for note in details.get("notes", [])],
        ]
    )


def format_ability_manual(ability_code: str) -> str:
    linked_skills = sorted(skill for skill, ability in SKILL_TO_ABILITY.items() if ability == ability_code)
    matching_classes = sorted(
        public_class_label(class_name)
        for class_name, stats in CLASS_PRIMARY_STATS.items()
        if ability_code in stats
    )
    return "\n".join(
        [
            "Gameplay Manual",
            f"Public name: {ability_label(ability_code)}",
            f"Linked skills: {', '.join(linked_skills) if linked_skills else 'None'}",
            f"Common main stat for: {', '.join(matching_classes) if matching_classes else 'No class listed as primary'}",
            f"Gameplay role: {ABILITY_GAMEPLAY_NOTES.get(ability_code, 'No note recorded yet.')}",
        ]
    )


def format_skill_manual(skill_name: str) -> str:
    linked_ability = SKILL_TO_ABILITY[skill_name]
    class_sources = sorted(public_class_label(class_name) for class_name, details in CLASSES.items() if skill_name in details["skill_choices"])
    race_sources = sorted(public_race_label(race_name) for race_name, details in RACES.items() if skill_name in details["skills"])
    background_sources = sorted(BACKGROUND_LORE.get(name, {}).get("label", name) for name, details in BACKGROUNDS.items() if skill_name in details["skills"])
    return "\n".join(
        [
            "Gameplay Manual",
            f"Governing ability: {ability_label(linked_ability)}",
            f"Class access: {', '.join(class_sources) if class_sources else 'No class grants selection access'}",
            f"Automatic people access: {', '.join(race_sources) if race_sources else 'None'}",
            f"Automatic background access: {', '.join(background_sources) if background_sources else 'None'}",
            f"Gameplay role: {SKILL_LORE[skill_name]['text']}",
        ]
    )


def format_feature_manual(feature_name: str) -> str:
    class_sources = sorted(public_class_label(class_name) for class_name, details in CLASSES.items() if feature_name in details["features"])
    race_sources = sorted(public_race_label(race_name) for race_name, details in RACES.items() if feature_name in details["features"])
    return "\n".join(
        [
            "Gameplay Manual",
            f"Used by classes: {', '.join(class_sources) if class_sources else 'None at level 1'}",
            f"Used by peoples: {', '.join(race_sources) if race_sources else 'None'}",
            f"Gameplay role: {FEATURE_LORE[feature_name]['text']}",
        ]
    )


def manual_text_for_entry(section_title: str, entry_name: str) -> str:
    if section_title == "Classes" and entry_name in CLASSES:
        return format_class_manual(entry_name)
    if section_title in {"Races", "Peoples"} and entry_name in RACES:
        return format_race_manual(entry_name)
    if section_title == "Backgrounds" and entry_name in BACKGROUNDS:
        return format_background_manual(entry_name)
    if section_title == "Core Abilities" and entry_name in ABILITY_LABELS:
        return format_ability_manual(entry_name)
    if section_title == "Skills" and entry_name in SKILL_TO_ABILITY:
        return format_skill_manual(entry_name)
    if section_title == "Features & Abilities" and entry_name in FEATURE_LORE:
        return format_feature_manual(entry_name)
    return ""
