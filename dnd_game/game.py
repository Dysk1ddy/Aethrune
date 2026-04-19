from __future__ import annotations

from .gameplay.base import GameBase, GameInterrupted
from .gameplay.camp import CampMixin
from .gameplay.combat_flow import CombatFlowMixin
from .gameplay.combat_resolution import CombatResolutionMixin
from .gameplay.companions import CompanionSystemMixin
from .gameplay.creation import CharacterCreationMixin
from .gameplay.creation_point_buy import PointBuyCreationMixin
from .gameplay.dialogue_inputs import DialogueInputMixin
from .gameplay.encounter import Encounter
from .gameplay.interaction_actions import InteractionActionsMixin
from .gameplay.inventory_core import InventoryCoreMixin
from .gameplay.inventory_management import InventoryManagementMixin
from .gameplay.io import GameIOMixin
from .gameplay.journal import JournalMixin
from .gameplay.map_system import MapSystemMixin
from .gameplay.music import MusicMixin
from .gameplay.progression import ProgressionMixin
from .gameplay.quests import QuestMixin
from .gameplay.random_encounters import RandomEncounterMixin
from .gameplay.sound_effects import SoundEffectsMixin
from .gameplay.status_effects import StatusEffectMixin
from .gameplay.story_act1_expanded import StoryAct1ExpandedMixin
from .gameplay.story_act2_scaffold import StoryAct2ScaffoldMixin
from .gameplay.story_act3_scaffold import StoryAct3ScaffoldMixin
from .gameplay.story_endgame import StoryEndgameMixin
from .gameplay.story_intro import StoryIntroMixin
from .gameplay.story_town_hub import StoryTownHubMixin
from .gameplay.story_town_services import StoryTownServicesMixin


class TextDnDGame(
    CampMixin,
    CompanionSystemMixin,
    DialogueInputMixin,
    InteractionActionsMixin,
    MapSystemMixin,
    StoryAct1ExpandedMixin,
    StoryAct2ScaffoldMixin,
    StoryAct3ScaffoldMixin,
    StoryEndgameMixin,
    StoryTownServicesMixin,
    StoryTownHubMixin,
    StoryIntroMixin,
    StatusEffectMixin,
    CombatResolutionMixin,
    RandomEncounterMixin,
    CombatFlowMixin,
    InventoryManagementMixin,
    InventoryCoreMixin,
    ProgressionMixin,
    PointBuyCreationMixin,
    CharacterCreationMixin,
    QuestMixin,
    JournalMixin,
    MusicMixin,
    SoundEffectsMixin,
    GameIOMixin,
    GameBase,
):
    """Primary game class composed from focused gameplay modules."""


__all__ = ["Encounter", "GameInterrupted", "TextDnDGame"]
