"""
Plotlyst
Copyright (C) 2021-2022  Zsolt Kovari

This file is part of Plotlyst.

Plotlyst is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Plotlyst is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
# flake8: noqa

import uuid
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Any, Dict

from dataclasses_json import dataclass_json, Undefined, config
from overrides import overrides

from src.main.python.plotlyst.core.template import SelectionItem, exclude_if_empty, exclude_if_black, enneagram_field, \
    mbti_field, ProfileTemplate, default_character_profiles, default_location_profiles, enneagram_choices, mbti_choices, \
    Role, \
    summary_field


@dataclass
class TemplateValue:
    id: uuid.UUID
    value: Any

    @overrides
    def __hash__(self):
        return hash(str(self.id))


@dataclass
class Event:
    keyphrase: str
    synopsis: str
    conflicts: List['Conflict'] = field(default_factory=list)
    emotion: int = 0


@dataclass
class Comment:
    text: str
    created_at: datetime = datetime.now()
    major: bool = False
    resolved: bool = False
    character: Optional['Character'] = None


class AgePeriod(Enum):
    BABY = 0
    CHILD = 1
    TEENAGER = 2
    ADULT = 3


class BackstoryEventType(Enum):
    Event = 'event'
    Birthday = 'birth'
    Education = 'education'
    Job = 'fa5s.briefcase'
    Love = 'love'
    Family = 'family'
    Home = 'home'
    Friendship = 'friendship'
    Fortune = 'fortune'
    Promotion = 'promotion'
    Award = 'award'
    Death = 'death'
    Violence = 'violence'
    Accident = 'accident'
    Crime = 'crime'
    Catastrophe = 'catastrophe'
    Loss = 'loss'
    Medical = 'medical'
    Injury = 'injury'
    Breakup = 'breakup'
    Farewell = 'farewell'
    Travel = 'travel'
    Game = 'game'
    Sport = 'sport'
    Gift = 'gift'


@dataclass
class BackstoryEvent(Event):
    type: BackstoryEventType = BackstoryEventType.Event
    type_icon: str = 'ri.calendar-event-fill'
    type_color: str = 'darkBlue'
    follow_up: bool = False


@dataclass
class CharacterGoal:
    goal_id: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    support: bool = True
    children: List['CharacterGoal'] = field(default_factory=list)

    def goal(self, novel: 'Novel') -> Optional['Goal']:
        for goal_ in novel.goals:
            if goal_.id == self.goal_id:
                return goal_


MALE = 'male'
FEMALE = 'female'
TRANSGENDER = 'transgender'
NON_BINARY = 'non-binary'
GENDERLESS = 'genderless'


@dataclass
class AvatarPreferences:
    use_image: bool = True
    use_initial: bool = False
    use_role: bool = False
    use_custom_icon: bool = False
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))
    icon_color: str = field(default='black', metadata=config(exclude=exclude_if_black))

    def allow_initial(self):
        self.__allow(initial=True)

    def allow_image(self):
        self.__allow(image=True)

    def allow_role(self):
        self.__allow(role=True)

    def allow_custom_icon(self):
        self.__allow(custom=True)

    def __allow(self, image: bool = False, initial: bool = False, role: bool = False, custom: bool = False):
        self.use_image = image
        self.use_initial = initial
        self.use_role = role
        self.use_custom_icon = custom


@dataclass
class CharacterPreferences:
    avatar: AvatarPreferences = AvatarPreferences()


@dataclass
class Character:
    name: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    gender: str = ''
    role: Optional[Role] = None
    age: Optional[int] = None
    occupation: Optional[str] = None
    avatar: Optional[Any] = None
    template_values: List[TemplateValue] = field(default_factory=list)
    backstory: List[BackstoryEvent] = field(default_factory=list)
    goals: List[CharacterGoal] = field(default_factory=list)
    document: Optional['Document'] = None
    journals: List['Document'] = field(default_factory=list)
    prefs: CharacterPreferences = CharacterPreferences()

    def enneagram(self) -> Optional[SelectionItem]:
        for value in self.template_values:
            if value.id == enneagram_field.id:
                return enneagram_choices.get(value.value)

    def mbti(self) -> Optional[SelectionItem]:
        for value in self.template_values:
            if value.id == mbti_field.id:
                return mbti_choices.get(value.value)

    def summary(self) -> str:
        for value in self.template_values:
            if value.id == summary_field.id:
                return value.value

        return ''

    def is_major(self):
        return self.role and self.role.is_major()

    def is_secondary(self):
        return self.role and self.role.is_secondary()

    def is_minor(self) -> bool:
        return self.role and self.role.is_minor()

    def flatten_goals(self) -> List[CharacterGoal]:
        all_goals = []
        self.__traverse_goals(all_goals, self.goals)
        return all_goals

    def __traverse_goals(self, all_goals: List[CharacterGoal], current_goals: List[CharacterGoal]):
        for goal in current_goals:
            all_goals.append(goal)
            self.__traverse_goals(all_goals, goal.children)

    @overrides
    def __hash__(self):
        return hash(str(self.id))


class NpcCharacter(Character):
    pass


@dataclass
class Chapter:
    title: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def sid(self) -> str:
        return str(self.id)

    def title_index(self, novel: 'Novel') -> str:
        return f'Chapter {novel.chapters.index(self) + 1}'


@dataclass
class CharacterArc:
    arc: int
    character: Character


VERY_UNHAPPY: int = -2
UNHAPPY: int = -1
NEUTRAL: int = 0
HAPPY: int = 1
VERY_HAPPY: int = 2


class SceneBuilderElementType(Enum):
    SPEECH = 'speech'
    ACTION_BEAT = 'action_beat'
    CHARACTER_ENTRY = 'character_entry'
    REACTION = 'reaction'
    SIGHT = 'sight'
    SOUND = 'sound'
    SMELL = 'smell'
    TASTE = 'taste'
    TOUCH = 'touch'
    FEELING = 'feeling'
    REFLEX = 'reflex'
    ACTION = 'action'
    MONOLOG = 'monolog'
    EMOTIONAL_CHANGE = 'emotional_change'
    GOAL = 'goal'
    DISASTER = 'disaster'
    RESOLUTION = 'resolution'
    DECISION = 'decision'
    ENDING = 'ending'


@dataclass
class SceneBuilderElement:
    type: SceneBuilderElementType
    text: str = ''
    children: List['SceneBuilderElement'] = field(default_factory=list)
    character: Optional[Character] = None
    has_suspense: bool = False
    has_tension: bool = False
    has_stakes: bool = False


class StoryBeatType(Enum):
    BEAT = 'beat'
    CONTAINER = 'container'


def exclude_if_beat(value):
    return value == StoryBeatType.BEAT


@dataclass
class StoryBeat:
    text: str
    act: int
    description: str = ''
    type: StoryBeatType = field(default=StoryBeatType.BEAT, metadata=config(exclude=exclude_if_beat))
    ends_act: bool = field(default=False, metadata=config(exclude=exclude_if_empty))
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    icon: str = ''
    icon_color: str = field(default='black', metadata=config(exclude=exclude_if_black))
    percentage: int = 0
    percentage_end: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    enabled: bool = True

    @overrides
    def __hash__(self):
        return hash(str(id))


@dataclass
class SceneStage(SelectionItem):
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    @overrides
    def __hash__(self):
        return hash(str(id))


@dataclass
class DramaticQuestion(SelectionItem):
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    @overrides
    def __hash__(self):
        return hash(str(id))


class PlotType(Enum):
    Main = 'main'
    Internal = 'internal'
    Subplot = 'subplot'


@dataclass
class PlotValue(SelectionItem):
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    negative: str = ''

    @overrides
    def __hash__(self):
        return hash(str(id))


class CharacterBased(ABC):
    def set_character(self, character: Optional[Character]):
        if character is None:
            self.character_id = None
            self._character = None
        else:
            self.character_id = character.id
            self._character = character

    def character(self, novel: 'Novel') -> Optional[Character]:
        if not self.character_id:
            return None
        if not self._character:
            for c in novel.characters:
                if c.id == self.character_id:
                    self._character = c
                    break

        return self._character


@dataclass
class Plot(SelectionItem, CharacterBased):
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    plot_type: PlotType = PlotType.Main
    values: List[PlotValue] = field(default_factory=list)
    character_id: Optional[uuid.UUID] = None
    question: str = ''

    def __post_init__(self):
        self._character: Optional[Character] = None

    @overrides
    def __hash__(self):
        return hash(str(id))


class ConflictType(Enum):
    CHARACTER = 0
    SOCIETY = 1
    NATURE = 2
    TECHNOLOGY = 3
    SUPERNATURAL = 4
    SELF = 5


@dataclass
class Conflict(SelectionItem, CharacterBased):
    type: ConflictType = ConflictType.CHARACTER
    character_id: Optional[uuid.UUID] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    conflicting_character_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        self._character: Optional[Character] = None
        self._conflicting_character: Optional[Character] = None

    def conflicting_character(self, novel: 'Novel') -> Optional[Character]:
        if not self.conflicting_character_id:
            return None
        if not self._conflicting_character:
            for c in novel.characters:
                if c.id == self.conflicting_character_id:
                    self._conflicting_character = c
                    break

        return self._conflicting_character

    @overrides
    def __hash__(self):
        return hash(str(self.id))


@dataclass
class Goal(SelectionItem):
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    description: str = ''

    @overrides
    def __hash__(self):
        return hash(str(self.id))


@dataclass
class ScenePlotValueCharge:
    plot_value_id: uuid.UUID
    charge: int

    def plot_value(self, plot: Plot) -> Optional[PlotValue]:
        for v in plot.values:
            if v.id == self.plot_value_id:
                return v


@dataclass
class ScenePlotReferenceData:
    comment: str = field(default='', metadata=config(exclude=exclude_if_empty))
    values: List[ScenePlotValueCharge] = field(default_factory=list)


@dataclass
class ScenePlotReference:
    plot: Plot
    data: ScenePlotReferenceData = ScenePlotReferenceData()


class SceneType(Enum):
    DEFAULT = ''
    ACTION = 'action'
    REACTION = 'reaction'


class SceneStructureItemType(Enum):
    GOAL = 0
    CONFLICT = 1
    OUTCOME = 2
    REACTION = 3
    DILEMMA = 4
    DECISION = 5
    BEAT = 6
    INCITING_INCIDENT = 7
    RISING_ACTION = 8
    CRISIS = 9
    TICKING_CLOCK = 10
    HOOK = 11
    EXPOSITION = 12


class SceneOutcome(Enum):
    DISASTER = 0
    RESOLUTION = 1
    TRADE_OFF = 2


@dataclass
class SceneStructureItem:
    type: SceneStructureItemType
    part: int = 1
    text: str = ''
    outcome: Optional[SceneOutcome] = None
    emotion: Optional[int] = None


@dataclass
class ConflictReference:
    conflict_id: uuid.UUID
    message: str = ''
    intensity: int = 1


@dataclass
class GoalReference:
    character_goal_id: uuid.UUID
    message: str = ''


@dataclass
class TagReference:
    tag_id: uuid.UUID
    message: str = ''


@dataclass
class SceneStructureAgenda(CharacterBased):
    character_id: Optional[uuid.UUID] = None
    items: List[SceneStructureItem] = field(default_factory=list)
    conflict_references: List[ConflictReference] = field(default_factory=list)
    goal_references: List[GoalReference] = field(default_factory=list)
    outcome: Optional[SceneOutcome] = None
    beginning_emotion: int = NEUTRAL
    ending_emotion: int = NEUTRAL

    def __post_init__(self):
        self._character: Optional[Character] = None

    def conflicts(self, novel: 'Novel') -> List[Conflict]:
        conflicts_ = []
        for id_ in [x.conflict_id for x in self.conflict_references]:
            for conflict in novel.conflicts:
                if conflict.id == id_:
                    conflicts_.append(conflict)

        return conflicts_

    def remove_conflict(self, conflict: Conflict):
        self.conflict_references = [x for x in self.conflict_references if x.conflict_id != conflict.id]

    def remove_goal(self, char_goal: CharacterGoal):
        self.goal_references = [x for x in self.goal_references if x.character_goal_id != char_goal.id]

    def goals(self, character: Character) -> List[CharacterGoal]:
        goals_ = character.flatten_goals()
        agenda_goal_ids = [x.character_goal_id for x in self.goal_references]
        return [x for x in goals_ if x.id in agenda_goal_ids]


@dataclass
class SceneStoryBeat:
    structure_id: uuid.UUID
    beat_id: uuid.UUID
    character_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        self._beat: Optional[StoryBeat] = None

    def beat(self, structure: 'StoryStructure') -> Optional[StoryBeat]:
        if not self._beat and self.structure_id == structure.id:
            for b in structure.beats:
                if b.id == self.beat_id and self.character_id == structure.character_id:
                    self._beat = b
                    break

        return self._beat

    @staticmethod
    def of(structure: 'StoryStructure', beat: StoryBeat) -> 'SceneStoryBeat':
        return SceneStoryBeat(structure.id, beat.id, structure.character_id)


@dataclass
class Scene:
    title: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    synopsis: str = ''
    type: SceneType = SceneType.DEFAULT
    pov: Optional[Character] = None
    characters: List[Character] = field(default_factory=list)
    agendas: List[SceneStructureAgenda] = field(default_factory=list)
    wip: bool = False
    plot_values: List[ScenePlotReference] = field(default_factory=list)
    day: int = 1
    chapter: Optional[Chapter] = None
    arcs: List[CharacterArc] = field(default_factory=list)
    builder_elements: List[SceneBuilderElement] = field(default_factory=list)
    stage: Optional[SceneStage] = None
    beats: List[SceneStoryBeat] = field(default_factory=list)
    comments: List[Comment] = field(default_factory=list)
    tag_references: List[TagReference] = field(default_factory=list)
    document: Optional['Document'] = None
    manuscript: Optional['Document'] = None

    def beat(self, novel: 'Novel') -> Optional[StoryBeat]:
        structure = novel.active_story_structure
        for b in self.beats:
            if b.structure_id == structure.id and b.character_id == structure.character_id:
                return b.beat(structure)

    def remove_beat(self, novel: 'Novel'):
        beat = self.beat(novel)
        if not beat:
            return
        beat_structure = None
        for b in self.beats:
            if b.beat_id == beat.id:
                beat_structure = b
                break
        if beat_structure:
            self.beats.remove(beat_structure)

    def pov_arc(self) -> int:
        for arc in self.arcs:
            if arc.character == self.pov:
                return arc.arc
        return NEUTRAL

    def plots(self) -> List[Plot]:
        return [x.plot for x in self.plot_values]

    def tags(self, novel: 'Novel') -> List['Tag']:
        tags_ = []
        for id_ in [x.tag_id for x in self.tag_references]:
            for tags_per_type in novel.tags.values():
                for tag in tags_per_type:
                    if tag.id == id_:
                        tags_.append(tag)

        return tags_

    def outcome_resolution(self) -> bool:
        return self.__is_outcome(SceneOutcome.RESOLUTION)

    def outcome_trade_off(self) -> bool:
        return self.__is_outcome(SceneOutcome.TRADE_OFF)

    def title_or_index(self, novel: 'Novel') -> str:
        return self.title if self.title else f'Scene {novel.scenes.index(self) + 1}'

    def __is_outcome(self, expected) -> bool:
        if self.agendas:
            for item_ in reversed(self.agendas[0].items):
                if item_.outcome is not None:
                    return item_.outcome == expected

        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


def default_stages() -> List[SceneStage]:
    return [SceneStage('Outlined'), SceneStage('1st Draft'),
            SceneStage('2nd Draft'), SceneStage('3rd Draft'), SceneStage('4th Draft'),
            SceneStage('Edited'), SceneStage('Proofread'), SceneStage('Final')]


@dataclass
class Location:
    name: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    children: List['Location'] = field(default_factory=list)
    icon: str = ''
    icon_color: str = 'black'
    template_values: List[TemplateValue] = field(default_factory=list)
    document: Optional['Document'] = None


@dataclass
class StoryStructure(CharacterBased):
    title: str
    icon: str = ''
    icon_color: str = 'black'
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    beats: List[StoryBeat] = field(default_factory=list)
    custom: bool = False
    active: bool = False
    character_id: Optional[uuid.UUID] = None

    def __post_init__(self):
        self._character: Optional[Character] = None

    def act_beats(self) -> List[StoryBeat]:
        return [x for x in self.beats if x.ends_act]


three_act_structure = StoryStructure(title='Three Act Structure',
                                     id=uuid.UUID('58013be5-1efb-4de4-9dd2-1433ce6edf90'),
                                     icon='mdi.numeric-3-circle-outline',
                                     icon_color='#ff7800',
                                     beats=[StoryBeat(text='Hook',
                                                      id=uuid.UUID('40365047-e7df-4543-8816-f9f8dcce12da'),
                                                      icon='mdi.hook',
                                                      icon_color='#829399',
                                                      description="Raises curiosity and hooks the reader's attention. May hint at what kind of story the reader can expect.",
                                                      act=1, percentage=1),
                                            StoryBeat(text='Inciting Incident',
                                                      icon='mdi.bell-alert-outline',
                                                      icon_color='#a2ad59',
                                                      description="The first event that truly changes the protagonist's status quo and thus establishes the story. Often an external conflict is involved that raises the stakes and sets the protagonist in a new direction.",
                                                      id=uuid.UUID('a0c2d94a-b53c-485e-a279-f2548bdb38ec'),
                                                      act=1, percentage=10),
                                            StoryBeat(text='First Plot Point',
                                                      icon='mdi.dice-1',
                                                      icon_color='#2a4494',
                                                      description="First 'Point of No Return' beat. It propels the protagonist into the central conflict. At this point for character-driven stories, the protagonist should be fully committed to react to the inciting incident.",
                                                      id=uuid.UUID('8d85c960-1c63-44d4-812d-545d3ba4d153'), act=1,
                                                      ends_act=True, percentage=20),
                                            StoryBeat(text='First Pinch Point',
                                                      id=uuid.UUID('af024374-12e6-44dc-80e6-28f2bc0e59ed'),
                                                      icon='fa5s.thermometer-three-quarters',
                                                      description='A reminder of the power of antagonistic forces.',
                                                      icon_color='#b81365',
                                                      act=2, percentage=35),
                                            StoryBeat(text='Midpoint',
                                                      icon='mdi.middleware-outline',
                                                      icon_color='#2e86ab',
                                                      description="Another Point of No Return beat that raises the stakes. Often includes a moment of truth beat which makes the protagonist become proactive from reactive.",
                                                      id=uuid.UUID('3f817e10-85d1-46af-91c6-70f1ad5c0542'),
                                                      act=2, percentage=50),
                                            StoryBeat(text='Second Pinch Point',
                                                      id=uuid.UUID('74087e28-b37a-4797-95bc-41d96f6a9393'),
                                                      icon='fa5s.biohazard',
                                                      description="A showcase of the full strength of antagonistic forces and a reminder of what's at stake.",
                                                      icon_color='#cd533b',
                                                      act=2, percentage=62),
                                            StoryBeat(text='Dark Moment',
                                                      icon='mdi.weather-night',
                                                      icon_color='#494368',
                                                      description="All-time low moment for the protagonist. They must feel worse than at the beginning of the story.",
                                                      id=uuid.UUID('4ded5006-c90a-4825-9de7-e16bf62017a3'), act=2,
                                                      percentage=75),
                                            StoryBeat(text='Second Plot Point',
                                                      id=uuid.UUID('95705e5e-a6b8-4abe-b2ea-426f2ae8d020'),
                                                      icon='mdi.dice-2',
                                                      description="Second 'Point of No Return' beat. The last piece of key information is provided that launches the protagonist towards the climax.",
                                                      icon_color='#6a0136',
                                                      act=2, ends_act=True, percentage=80),
                                            StoryBeat(text='Crisis',
                                                      icon='mdi.arrow-decision-outline',
                                                      icon_color='#ce2d4f',
                                                      description="The protagonist must decide between two equally bad or two irreconcilable good choices.",
                                                      id=uuid.UUID('466688f7-ebee-4d36-a655-83ff40e1c46d'),
                                                      act=3, percentage=95, enabled=False),
                                            StoryBeat(text='Climax',
                                                      icon='fa5s.chevron-up',
                                                      icon_color='#ce2d4f',
                                                      description="The highest point of tension. The final confrontation between the protagonist and the antagonist. The story's main dramatic question is resolved.",
                                                      id=uuid.UUID('342eb27c-52ff-40c2-8c5e-cf563d4e38bc'),
                                                      act=3, percentage=97),
                                            StoryBeat(text='Resolution',
                                                      icon='fa5s.water',
                                                      description="An 'after' snapshot to tie up loose ends and release tension.",
                                                      icon_color='#7192be',
                                                      id=uuid.UUID('996695b1-8db6-4c68-8dc4-51bbfe720e8b'),
                                                      act=3, percentage=99),
                                            ])

save_the_cat = StoryStructure(title='Save the Cat',
                              id=uuid.UUID('1f1c4433-6afa-48e1-a8dc-f8fcb94bfede'),
                              icon='fa5s.cat',
                              beats=[StoryBeat(text='Opening Image',
                                               icon='fa5.image',
                                               icon_color='#1ea896',
                                               description="Establishes the setting and introduces the protagonist. Bonus: hints at the main character's flaws and desires.",
                                               id=uuid.UUID('249bba52-98b8-4577-8b3c-94481f6bf622'),
                                               act=1, percentage=1),
                                     StoryBeat(text='Setup',
                                               type=StoryBeatType.CONTAINER,
                                               icon='mdi.toy-brick-outline',
                                               icon_color='#02bcd4',
                                               id=uuid.UUID('7ce4345b-60eb-4cd6-98cc-7cce98028839'),
                                               act=1, percentage=1, percentage_end=10),
                                     StoryBeat(text='Theme Stated',
                                               icon='ei.idea-alt',
                                               icon_color='#f72585',
                                               description="Hints at the lesson that the protagonist will learn by the end of the story. At this point they ignore it.",
                                               id=uuid.UUID('1c8b0903-f169-48d5-bcec-3e842f360150'),
                                               act=1, percentage=5),
                                     StoryBeat(text='Catalyst',
                                               icon='fa5s.vial',
                                               icon_color='#822faf',
                                               description="The first event that truly changes the protagonist's status quo. Often external conflict is involved that raises the stakes and sets the protagonist in a new direction.",
                                               id=uuid.UUID('cc3d8641-bcdf-402b-ba84-7ff59b2cc76a'),
                                               act=1, percentage=10),
                                     StoryBeat(text='Debate',
                                               type=StoryBeatType.CONTAINER,
                                               icon='fa5s.map-signs',
                                               icon_color='#ba6f4d',
                                               id=uuid.UUID('0203696e-dc54-4a10-820a-bfdf392a82dc'),
                                               act=1, percentage=10, percentage_end=20),
                                     StoryBeat(text='Break into Two',
                                               icon='mdi6.clock-time-three-outline',
                                               icon_color='#1bbc9c',
                                               description="Start of Act 2. The protagonist enters a new world, sometimes physically, by making a decision and addressing the Catalyst event.",
                                               id=uuid.UUID('43eb267f-2840-437b-9eac-9e52d80eba2b'),
                                               act=1, ends_act=True, percentage=20),
                                     StoryBeat(text='B Story',
                                               icon='mdi.alpha-b-box',
                                               icon_color='#a6808c',
                                               description="Introduction of a new character who represents the B Story, which is the thematic or spiritual story of the protagonist's journey.",
                                               id=uuid.UUID('64229c74-5513-4391-9b45-c54ad106c137'),
                                               act=2, percentage=22),
                                     StoryBeat(text='Fun and Games',
                                               type=StoryBeatType.CONTAINER,
                                               icon='fa5s.gamepad',
                                               icon_color='#2c699a',
                                               id=uuid.UUID('490157f0-f255-4ab3-82f3-bc5cb22ce03b'),
                                               act=2, percentage=20, percentage_end=50),
                                     StoryBeat(text='Midpoint',
                                               icon='mdi.middleware-outline',
                                               icon_color='#2e86ab',
                                               description="A false defeat or false victory moment that raises the stakes. Often Story A and Story B intersect. The protagonist turns to proactive from reactive.",
                                               id=uuid.UUID('af4fb4e9-f287-47b6-b219-be75af752622'),
                                               act=2, percentage=50),
                                     StoryBeat(text='Bad Guys Close In',
                                               type=StoryBeatType.CONTAINER,
                                               icon='fa5s.biohazard',
                                               icon_color='#cd533b',
                                               id=uuid.UUID('2060c95f-dcdb-4074-a096-4b054f70d57a'),
                                               act=2, percentage=50, percentage_end=75),
                                     StoryBeat(text='All is Lost',
                                               icon='mdi.trophy-broken',
                                               icon_color='#cd533b',
                                               description='All-time low moment for the protagonist. They must feel worse than at the beginning of the story.',
                                               id=uuid.UUID('2971ce1a-eb69-4ac1-9f2d-74407e6fac92'),
                                               act=2, percentage=75),
                                     StoryBeat(text='Return to the Familiar',
                                               icon='mdi.home-circle',
                                               icon_color='#8ecae6',
                                               description="While the protagonist wallows, they often retrieve to their normal world but their old environment doesn't feel the same anymore",
                                               id=uuid.UUID('aed2a29a-2d9d-4f5e-8539-73588b774101'),
                                               act=2, percentage=77, enabled=False),
                                     StoryBeat(text='Dark Night of the Soul',
                                               type=StoryBeatType.CONTAINER,
                                               icon='mdi.weather-night',
                                               icon_color='#494368',
                                               id=uuid.UUID('c0e89a87-224d-4b97-b4f5-a2ace08fdadb'),
                                               act=2, percentage=75, percentage_end=80),
                                     StoryBeat(text='Break into Three',
                                               icon='mdi.clock-time-nine-outline',
                                               icon_color='#e85d04',
                                               description='An a-ha moment for the protagonist. They realize that they have to change. They know how to fix their flaws and thus resolve the story.',
                                               id=uuid.UUID('677f83ad-355a-47fb-8ff7-812997bdb23a'),
                                               act=2, ends_act=True, percentage=80),
                                     StoryBeat(text='Finale',
                                               type=StoryBeatType.CONTAINER,
                                               icon='fa5s.flag-checkered',
                                               icon_color='#ff7800',
                                               id=uuid.UUID('10191cac-7786-4e85-9a36-75f99be22b92'),
                                               act=3, percentage=80, percentage_end=99),
                                     StoryBeat(text='Gather the Team',
                                               icon='ri.team-fill',
                                               icon_color='#489fb5',
                                               description='The protagonist might need to make some amends and gather allies.',
                                               id=uuid.UUID('777d81b6-b427-4fc0-ba8d-01cde45eedde'),
                                               act=3, percentage=84),
                                     StoryBeat(text='Execute the Plan',
                                               icon='mdi.format-list-checks',
                                               icon_color='#55a630',
                                               description='The protagonist executes the original plan.',
                                               id=uuid.UUID('b99012a6-8c41-43c8-845d-7595ce7140d9'),
                                               act=3, percentage=86),
                                     StoryBeat(text='High Tower Surprise',
                                               icon='mdi.lighthouse-on',
                                               icon_color='#586f7c',
                                               description='A sudden twist! The original plan did not work out.',
                                               id=uuid.UUID('fe77f4f2-9064-4b06-8062-920635aa415c'),
                                               act=3, percentage=88),
                                     StoryBeat(text='Dig Deep Down',
                                               icon='mdi.shovel',
                                               icon_color='#b08968',
                                               description='A new plan is necessary. The protegonist must find the truth and act accordingly.',
                                               id=uuid.UUID('a5c4d0aa-9811-4988-8611-3483b2499732'),
                                               act=3, percentage=90),
                                     StoryBeat(text='Execute a New Plan',
                                               icon='mdi.lightbulb-on',
                                               icon_color='#4361ee',
                                               description='Execute the new plan and likely resolve the conflict.',
                                               id=uuid.UUID('13d535f6-6b3d-4211-ae44-e0fcf3970186'),
                                               act=3, percentage=95),
                                     StoryBeat(text='Final Image',
                                               icon='fa5s.water',
                                               icon_color='#7192be',
                                               description="An 'after' snapshot of the protagonist to often contrast the opening image.",
                                               id=uuid.UUID('12d5ec21-af96-4e51-9c26-06583d830d87'),
                                               act=3, percentage=99),
                                     ])

default_story_structures = [three_act_structure,
                            save_the_cat]


@dataclass
class LanguageSettings:
    lang: str = 'en-US'


class ImportOriginType(Enum):
    SCRIVENER = 'scrivener'


@dataclass
class ImportOrigin:
    type: ImportOriginType
    source: str


@dataclass
class NovelDescriptor:
    title: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    lang_settings: LanguageSettings = LanguageSettings()
    import_origin: Optional[ImportOrigin] = None


@dataclass
class CausalityItem(SelectionItem):
    links: List['CausalityItem'] = field(default_factory=list)

    @overrides
    def __hash__(self):
        return hash(self.text)


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Causality:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    items: List['CausalityItem'] = field(default_factory=list)


class DocumentType(Enum):
    DOCUMENT = 0
    CHARACTER_BACKSTORY = 1
    CAUSE_AND_EFFECT = 2
    REVERSED_CAUSE_AND_EFFECT = 3
    SNOWFLAKE = 4
    CHARACTER_ARC = 5
    STORY_STRUCTURE = 6


@dataclass
class TextStatistics:
    word_count: int = -1


@dataclass
class DocumentStatistics:
    wc: int = 0


@dataclass
class Document(CharacterBased):
    title: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    type: DocumentType = DocumentType.DOCUMENT
    children: List['Document'] = field(default_factory=list)
    character_id: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))
    scene_id: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))
    data_id: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))
    icon_color: str = field(default='black', metadata=config(exclude=exclude_if_black))
    statistics: Optional[DocumentStatistics] = field(default=None, metadata=config(exclude=exclude_if_empty))

    @overrides
    def __hash__(self):
        return hash(str(self.id))

    def __post_init__(self):
        self.loaded: bool = False
        self.content: str = ''
        self.data: Any = None
        self._character: Optional[Character] = None
        self._scene: Optional[Scene] = None

    def scene(self, novel: 'Novel') -> Optional[Scene]:
        if not self.scene_id:
            return None
        if not self._scene:
            for s in novel.scenes:
                if s.id == self.scene_id:
                    self._scene = s
                    break

        return self._scene


def default_documents() -> List[Document]:
    return [Document('Story', id=uuid.UUID('ec2a62d9-fc00-41dd-8a6c-b121156b6cf4'), icon='fa5s.book-open'),
            Document('Characters', id=uuid.UUID('8fa16650-bed0-489b-baa1-d239e5198d47'), icon='fa5s.user'),
            Document('Scenes', id=uuid.UUID('75a552f4-037d-4179-860f-dd8400a7545b'), icon='mdi.movie-open'),
            Document('Locations', id=uuid.UUID('5faf7c16-f970-465d-bbcb-1bad56f3313c'), icon='fa5s.map-pin')]


@dataclass
class TagType(SelectionItem):
    description: str = ''

    @overrides
    def __hash__(self):
        return hash(self.text)


@dataclass
class Tag(SelectionItem):
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    tag_type: str = 'General'
    builtin: bool = False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


def default_general_tags() -> List[Tag]:
    return [
        Tag('Flashback', id=uuid.UUID('1daadfcf-dc6a-4b9d-b708-f9577cbb9e83'), icon='fa5s.backward', icon_color='white',
            color_hexa='#1b263b', builtin=True),
        Tag('Flashforward', id=uuid.UUID('a5db2d5f-099d-4d01-83e8-31c726f04100'), icon='fa5s.forward',
            icon_color='white',
            color_hexa='#1b998b', builtin=True),
        Tag('Ticking clock', id=uuid.UUID('88ab7b73-6934-4f63-8022-0b8732caa8bd'), icon='mdi.clock-alert-outline',
            icon_color='#f7cb15', builtin=True),
        Tag('Foreshadowing', id=uuid.UUID('2ba0c868-da0f-44fc-9142-fef0bfa6e1c6'), icon='mdi.crystal-ball',
            icon_color='#76bed0', builtin=True),
        Tag('Cliffhanger', id=uuid.UUID('51e0bcc5-396e-4602-b195-fc8efe985f13'), icon='mdi.target-account',
            icon_color='#f7cb15', builtin=True),
        Tag('Backstory', id=uuid.UUID('72d155da-df20-4b64-84d3-acfbbc7f87c7'), icon='mdi.archive', icon_color='#9a6d38',
            builtin=True),
        Tag('Red herring', id=uuid.UUID('96ff9491-cdd3-4c85-8086-ee47144828cb'), icon='fa5s.fish', icon_color='#d33f49',
            builtin=True)]


def default_tag_types() -> List[TagType]:
    return [
        TagType('General', icon='ei.tags', icon_color='#2a2a72',
                description='General tags that can be tracked for each scenes.'),
        TagType('Symbols', icon='fa5s.dove', icon_color='#5995ed',
                description='A symbol can be anything that represents something beyond their literal meaning.'),
        TagType('Motifs', icon='mdi6.glass-fragile', icon_color='#8ac6d0',
                description='A motif is a recurring object, sound, situation, phrase, or idea throughout the story.'
                            + ' A motif might remind the reader to the theme.'),
        TagType('Items', icon='mdi.ring', icon_color='#b6a6ca',
                description='Relevant items that reappear throughout the story.'
                            + ' They do not have symbolic meaning unlike Symbols or Motifs.'),
        TagType('Themes', icon='ei.idea-alt', icon_color='#f72585',
                description='The main ideas or lessons that the story explores.')
    ]


def default_tags() -> Dict[TagType, List[Tag]]:
    tags = {}
    types = default_tag_types()
    for t in types:
        if t.text == 'General':
            tags[t] = default_general_tags()
        else:
            tags[t] = []

    return tags


@dataclass
class DocsPreferences:
    grammar_check: bool = True


class NovelPanel(Enum):
    OUTLINE = 'outline'
    MANUSCRIPT = 'manuscript'
    REPORTS = 'reports'


class ScenesView(Enum):
    NOVEL = 'novel'
    CHARACTERS = 'characters'
    SCENES = 'scenes'
    LOCATIONS = 'locations'
    DOCS = 'docs'


@dataclass
class PanelPreferences:
    panel: NovelPanel = NovelPanel.OUTLINE
    scenes_view: Optional[ScenesView] = None


@dataclass
class NovelPreferences:
    active_stage_id: Optional[uuid.UUID] = None
    docs: DocsPreferences = DocsPreferences()
    panels: PanelPreferences = PanelPreferences()


@dataclass
class Novel(NovelDescriptor):
    story_structures: List[StoryStructure] = field(default_factory=list)
    characters: List[Character] = field(default_factory=list)
    scenes: List[Scene] = field(default_factory=list)
    locations: List[Location] = field(default_factory=list)
    plots: List[Plot] = field(default_factory=list)
    chapters: List[Chapter] = field(default_factory=list)
    stages: List[SceneStage] = field(default_factory=default_stages)
    character_profiles: List[ProfileTemplate] = field(default_factory=default_character_profiles)
    location_profiles: List[ProfileTemplate] = field(default_factory=default_location_profiles)
    conflicts: List[Conflict] = field(default_factory=list)
    goals: List[Goal] = field(default_factory=list)
    documents: List[Document] = field(default_factory=default_documents)
    tags: Dict[TagType, List[Tag]] = field(default_factory=default_tags)
    premise: str = ''
    synopsis: Optional['Document'] = None
    prefs: NovelPreferences = NovelPreferences()

    def update_from(self, updated_novel: 'Novel'):
        self.title = updated_novel.title
        self.scenes.clear()
        self.scenes.extend(updated_novel.scenes)
        self.characters.clear()
        self.characters.extend(updated_novel.characters)
        self.chapters.clear()
        self.chapters.extend(updated_novel.chapters)
        self.plots.clear()
        self.plots.extend(updated_novel.plots)
        self.stages.clear()
        self.stages.extend(updated_novel.stages)
        self.character_profiles.clear()
        self.character_profiles.extend(updated_novel.character_profiles)
        self.conflicts.clear()
        self.conflicts.extend(updated_novel.conflicts)
        self.goals.clear()
        self.goals.extend(updated_novel.goals)
        self.tags.clear()
        for k in updated_novel.tags:
            self.tags[k] = updated_novel.tags[k]

    def pov_characters(self) -> List[Character]:
        pov_ids = set()
        povs: List[Character] = []
        for scene in self.scenes:
            if scene.pov and str(scene.pov.id) not in pov_ids:
                povs.append(scene.pov)
                pov_ids.add(str(scene.pov.id))

        return povs

    def agenda_characters(self) -> List[Character]:
        char_ids = set()
        chars: List[Character] = []
        for scene in self.scenes:
            if scene.agendas and scene.agendas[0].character_id and str(scene.agendas[0].character_id) not in char_ids:
                character = scene.agendas[0].character(self)
                if character:
                    chars.append(character)
                    char_ids.add(str(scene.agendas[0].character_id))

        return chars

    def major_characters(self) -> List[Character]:
        return [x for x in self.characters if x.is_major()]

    def secondary_characters(self) -> List[Character]:
        return [x for x in self.characters if x.is_secondary()]

    def minor_characters(self) -> List[Character]:
        return [x for x in self.characters if x.is_minor()]

    @property
    def active_story_structure(self) -> StoryStructure:
        for structure in self.story_structures:
            if structure.active:
                return structure
        return self.story_structures[0]

    @property
    def active_stage(self) -> Optional[SceneStage]:
        if self.prefs.active_stage_id:
            for stage in self.stages:
                if stage.id == self.prefs.active_stage_id:
                    return stage

    def scenes_in_chapter(self, chapter: Chapter) -> List[Scene]:
        return [x for x in self.scenes if x.chapter is chapter]

    @staticmethod
    def new_scene(title: str = '') -> Scene:
        return Scene(title, agendas=[SceneStructureAgenda()])

    def insert_scene_after(self, scene: Scene, chapter: Optional[Chapter] = None) -> Scene:
        i = self.scenes.index(scene)
        day = scene.day

        new_scene = self.new_scene()
        new_scene.day = day
        if chapter:
            new_scene.chapter = chapter
        else:
            new_scene.chapter = scene.chapter
        self.scenes.insert(i + 1, new_scene)

        return new_scene

    @overrides
    def __hash__(self):
        return hash(str(self.id))
