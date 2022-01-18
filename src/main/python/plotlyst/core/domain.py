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
import uuid
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Any, Dict

from PyQt5.QtCore import Qt
from dataclasses_json import dataclass_json, Undefined
from overrides import overrides

from src.main.python.plotlyst.common import PIVOTAL_COLOR


@dataclass
class TemplateValue:
    id: uuid.UUID
    value: Any


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


@dataclass
class Character:
    name: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    avatar: Optional[Any] = None
    template_values: List[TemplateValue] = field(default_factory=list)
    backstory: List[BackstoryEvent] = field(default_factory=list)
    document: Optional['Document'] = None
    journals: List['Document'] = field(default_factory=list)

    def enneagram(self) -> Optional['SelectionItem']:
        for value in self.template_values:
            if value.id == enneagram_field.id:
                return _enneagram_choices.get(value.value)

    def mbti(self) -> Optional['SelectionItem']:
        for value in self.template_values:
            if value.id == mbti_field.id:
                return _mbti_choices.get(value.value)

    def role(self) -> Optional['SelectionItem']:
        for value in self.template_values:
            if value.id == role_field.id:
                item = _role_choices.get(value.value)
                if not item:
                    return None
                if item.text == 'Protagonist' and self.gender() == 1:
                    return SelectionItem(item.text, item.type, 'fa5s.chess-queen', item.icon_color)
                return item

    def goals(self) -> List[str]:
        for value in self.template_values:
            if value.id == goal_field.id:
                return value.value
        return []

    def gender(self) -> int:
        for value in self.template_values:
            if value.id == gender_field.id:
                return value.value[0] if value.value else -1
        return -1


class NpcCharacter(Character):
    pass


@dataclass
class Chapter:
    title: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def sid(self) -> str:
        return str(self.id)


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


@dataclass
class StoryBeat:
    text: str
    act: int
    ends_act: bool = False
    color_hexa: str = PIVOTAL_COLOR
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    icon: str = ''
    icon_color: str = 'black'
    percentage: int = 0
    enabled: bool = True

    @overrides
    def __hash__(self):
        return hash(str(id))


class SelectionItemType(Enum):
    CHOICE = 0
    SEPARATOR = 1


@dataclass
class SelectionItem:
    text: str
    type: SelectionItemType = SelectionItemType.CHOICE
    icon: str = ''
    icon_color: str = 'black'
    color_hexa: str = ''
    meta: Dict[str, Any] = field(default_factory=dict)

    @overrides
    def __hash__(self):
        return hash(self.text)


@dataclass
class SceneStage(SelectionItem):
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __hash__(self):
        return hash(str(id))


@dataclass
class DramaticQuestion(SelectionItem):
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __hash__(self):
        return hash(str(id))


class PlotType(Enum):
    Main = 'main'
    Internal = 'internal'
    Subplot = 'subplot'


class PlotValue(SelectionItem):
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    description: str = ''

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
    value: Optional[PlotValue] = None
    character_id: Optional[uuid.UUID] = None

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

    def __hash__(self):
        return hash(str(self.id))


@dataclass
class SceneGoal(SelectionItem):
    story_goal: Optional[SelectionItem] = None

    def __hash__(self):
        return hash(self.text)


@dataclass
class ScenePlotValue:
    plot: Plot
    value: int = 0


class SceneType(Enum):
    ACTION = 'action'
    REACTION = 'reaction'
    MIXED = ''


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


class SceneOutcome(Enum):
    DISASTER = 0
    RESOLUTION = 1
    TRADE_OFF = 2


@dataclass
class SceneStructureItem:
    type: SceneStructureItemType
    part: int = 1
    text: str = ''
    conflicts: List[Conflict] = field(default_factory=list)
    goals: List[SceneGoal] = field(default_factory=list)
    outcome: Optional[SceneOutcome] = None


@dataclass
class SceneStructureAgenda(CharacterBased):
    character_id: Optional[uuid.UUID] = None
    items: List[SceneStructureItem] = field(default_factory=list)
    beginning_emotion: int = NEUTRAL
    ending_emotion: int = NEUTRAL

    def __post_init__(self):
        self._character: Optional[Character] = None


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
    type: SceneType = SceneType.ACTION
    sequence: int = 0
    beginning: str = ''
    middle: str = ''
    end: str = ''
    pov: Optional[Character] = None
    characters: List[Character] = field(default_factory=list)
    agendas: List[SceneStructureAgenda] = field(default_factory=list)
    wip: bool = False
    plot_values: List[ScenePlotValue] = field(default_factory=list)
    day: int = 1
    chapter: Optional[Chapter] = None
    arcs: List[CharacterArc] = field(default_factory=list)
    builder_elements: List[SceneBuilderElement] = field(default_factory=list)
    stage: Optional[SceneStage] = None
    beats: List[SceneStoryBeat] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    goals: List[SceneGoal] = field(default_factory=list)
    comments: List[Comment] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
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

    def outcome_resolution(self) -> bool:
        return self.__is_outcome(SceneOutcome.RESOLUTION)

    def outcome_trade_off(self) -> bool:
        return self.__is_outcome(SceneOutcome.TRADE_OFF)

    def __is_outcome(self, expected) -> bool:
        if self.agendas:
            for item_ in reversed(self.agendas[0].items):
                if item_.outcome is not None:
                    return item_.outcome == expected

        return False


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
                                     beats=[StoryBeat(text='Exposition',
                                                      icon='fa5.image',
                                                      icon_color='#1ea896',
                                                      id=uuid.UUID('40365047-e7df-4543-8816-f9f8dcce12da'),
                                                      act=1, percentage=1),
                                            StoryBeat(text='Inciting Incident',
                                                      icon='mdi.bell-alert-outline',
                                                      icon_color='#a2ad59',
                                                      id=uuid.UUID('a0c2d94a-b53c-485e-a279-f2548bdb38ec'),
                                                      act=1, percentage=10),
                                            StoryBeat(text='Plot Point One',
                                                      icon='mdi.dice-1',
                                                      icon_color='#2a4494',
                                                      id=uuid.UUID('8d85c960-1c63-44d4-812d-545d3ba4d153'), act=1,
                                                      ends_act=True, percentage=20),
                                            StoryBeat(text='Rising Action',
                                                      icon='fa5s.chart-line',
                                                      icon_color='#08605f',
                                                      id=uuid.UUID('991354ea-2e8e-46f2-bd42-11fa56f73801'),
                                                      act=2, percentage=30),
                                            StoryBeat(text='Midpoint',
                                                      icon='mdi.middleware-outline',
                                                      icon_color='#bb0a21',
                                                      id=uuid.UUID('3f817e10-85d1-46af-91c6-70f1ad5c0542'),
                                                      act=2, percentage=50),
                                            StoryBeat(text='Dark Night of the Soul',
                                                      icon='mdi.weather-night',
                                                      icon_color='#494368',
                                                      id=uuid.UUID('4ded5006-c90a-4825-9de7-e16bf62017a3'), act=2,
                                                      ends_act=True, percentage=75),
                                            StoryBeat(text='Pre Climax',
                                                      icon='mdi.escalator-up',
                                                      icon_color='#f4b393',
                                                      id=uuid.UUID('17a85b2a-76fb-44ec-a367-bccf6cd5f8aa'),
                                                      act=3, percentage=80),
                                            StoryBeat(text='Climax',
                                                      icon='mdi.triangle-outline',
                                                      icon_color='#ce2d4f',
                                                      id=uuid.UUID('342eb27c-52ff-40c2-8c5e-cf563d4e38bc'),
                                                      act=3, percentage=90),
                                            StoryBeat(text='Denouement',
                                                      icon='fa5s.water',
                                                      icon_color='#7192be',
                                                      id=uuid.UUID('996695b1-8db6-4c68-8dc4-51bbfe720e8b'),
                                                      act=3, percentage=99),
                                            ])
weiland_10_beats = StoryStructure(title="Weiland's 10 Beats",
                                  id=uuid.UUID('57157873-3443-4832-9381-b33606f35fb2'),
                                  icon='mdi.dice-d10-outline',
                                  beats=[StoryBeat(text='Hook',
                                                   id=uuid.UUID('93394a0a-7fbc-4b94-bbfc-bb4b416c19f5'),
                                                   icon='mdi.hook',
                                                   icon_color='#829399',
                                                   act=1, percentage=1),
                                         StoryBeat(text='Inciting Event',
                                                   id=uuid.UUID('319bdd5a-9514-4fc7-9e26-1cc55bd22b8e'),
                                                   icon='mdi.bell-alert-outline',
                                                   icon_color='#a2ad59',
                                                   act=1, percentage=8),
                                         StoryBeat(text='Key Event',
                                                   id=uuid.UUID('c0b0c68e-012d-44ab-96bf-ad3da25331aa'),
                                                   icon='mdi.key',
                                                   act=1, percentage=16),
                                         StoryBeat(text='First Plot Point',
                                                   id=uuid.UUID('221c4fc7-bf67-430c-bd0b-8de856dc65bc'),
                                                   icon='mdi.dice-1',
                                                   icon_color='#2a4494',
                                                   act=1, ends_act=True, percentage=20),
                                         StoryBeat(text='First Pinch Point',
                                                   id=uuid.UUID('6f3caa23-eca8-4d24-906e-0ac697087109'),
                                                   icon='fa5s.thermometer-three-quarters',
                                                   icon_color='#b81365',
                                                   act=2, percentage=37),
                                         StoryBeat(text='Midpoint',
                                                   id=uuid.UUID('ecf0a27d-079a-4ffa-9ee3-0a5b068124f3'),
                                                   icon='mdi.middleware-outline',
                                                   icon_color='#2e86ab',
                                                   act=2, percentage=50),
                                         StoryBeat(text='Second Pinch Point',
                                                   id=uuid.UUID('584810ed-cb97-4e58-91e1-a9d080a1b380'),
                                                   icon='fa5s.biohazard',
                                                   icon_color='#cd533b',
                                                   act=2, percentage=62),
                                         StoryBeat(text='Third Plot Point',
                                                   id=uuid.UUID('7383dbc5-3616-4cb7-9cb0-685369ce53c9'),
                                                   icon='mdi.dice-3',
                                                   icon_color='#6a0136',
                                                   act=2, ends_act=True, percentage=75),
                                         StoryBeat(text='Climax',
                                                   id=uuid.UUID('cf2b7e41-a67b-4837-8196-9ec447e6ae36'),
                                                   icon='mdi.triangle-outline',
                                                   icon_color='#ce2d4f',
                                                   act=3, percentage=90),
                                         StoryBeat(text='Resolution',
                                                   id=uuid.UUID('752cd22c-870e-474d-919c-35f6c082bfa8'),
                                                   icon='fa5s.water',
                                                   icon_color='#7192be',
                                                   act=3, percentage=99),
                                         ])

save_the_cat = StoryStructure(title='Save the Cat',
                              id=uuid.UUID('1f1c4433-6afa-48e1-a8dc-f8fcb94bfede'),
                              icon='fa5s.cat',
                              beats=[StoryBeat(text='Opening Image',
                                               icon='fa5.image',
                                               icon_color='#1ea896',
                                               id=uuid.UUID('249bba52-98b8-4577-8b3c-94481f6bf622'),
                                               act=1, percentage=1),
                                     StoryBeat(text='Set-up',
                                               icon='mdi.toy-brick-outline',
                                               icon_color='#1d3958',
                                               id=uuid.UUID('7ce4345b-60eb-4cd6-98cc-7cce98028839'),
                                               act=1, percentage=3),
                                     StoryBeat(text='Theme Stated',
                                               icon='ei.idea-alt',
                                               icon_color='#f72585',
                                               id=uuid.UUID('1c8b0903-f169-48d5-bcec-3e842f360150'),
                                               act=1, percentage=5),
                                     StoryBeat(text='Catalyst',
                                               icon='fa5s.vial',
                                               icon_color='#822faf',
                                               id=uuid.UUID('cc3d8641-bcdf-402b-ba84-7ff59b2cc76a'),
                                               act=1, percentage=10),
                                     StoryBeat(text='Debate',
                                               icon='fa5s.map-signs',
                                               icon_color='#ba6f4d',
                                               id=uuid.UUID('0203696e-dc54-4a10-820a-bfdf392a82dc'),
                                               act=1, percentage=14),
                                     StoryBeat(text='Break into Two',
                                               icon='mdi6.clock-time-three-outline',
                                               icon_color='#283618',
                                               id=uuid.UUID('43eb267f-2840-437b-9eac-9e52d80eba2b'),
                                               act=1, ends_act=True, percentage=20),
                                     StoryBeat(text='B Story',
                                               icon='mdi.alpha-b-box',
                                               icon_color='#a6808c',
                                               id=uuid.UUID('64229c74-5513-4391-9b45-c54ad106c137'),
                                               act=2, percentage=25),
                                     StoryBeat(text='Fun and Games',
                                               icon='fa5s.gamepad',
                                               icon_color='#2c699a',
                                               id=uuid.UUID('490157f0-f255-4ab3-82f3-bc5cb22ce03b'),
                                               act=2, percentage=27),
                                     StoryBeat(text='Midpoint',
                                               icon='mdi.middleware-outline',
                                               icon_color='#2e86ab',
                                               id=uuid.UUID('af4fb4e9-f287-47b6-b219-be75af752622'),
                                               act=2, percentage=50),
                                     StoryBeat(text='Bad Guys Close In',
                                               icon='fa5s.biohazard',
                                               icon_color='#cd533b',
                                               id=uuid.UUID('2060c95f-dcdb-4074-a096-4b054f70d57a'),
                                               act=2, percentage=62),
                                     StoryBeat(text='All is Lost',
                                               icon='mdi.trophy-broken',
                                               icon_color='#e9c46a',
                                               id=uuid.UUID('2971ce1a-eb69-4ac1-9f2d-74407e6fac92'),
                                               act=2, percentage=70),
                                     StoryBeat(text='Dark Night of the Soul',
                                               icon='mdi.weather-night',
                                               icon_color='#494368',
                                               id=uuid.UUID('c0e89a87-224d-4b97-b4f5-a2ace08fdadb'),
                                               act=2, percentage=74),
                                     StoryBeat(text='Break into Three',
                                               icon='mdi.clock-time-nine-outline',
                                               icon_color='#e85d04',
                                               id=uuid.UUID('677f83ad-355a-47fb-8ff7-812997bdb23a'),
                                               act=2, ends_act=True, percentage=78),
                                     StoryBeat(text='Gather the Team',
                                               icon='ri.team-fill',
                                               icon_color='#489fb5',
                                               id=uuid.UUID('777d81b6-b427-4fc0-ba8d-01cde45eedde'),
                                               act=3, percentage=82),
                                     StoryBeat(text='Execute the Plan',
                                               icon='mdi.format-list-checks',
                                               icon_color='#55a630',
                                               id=uuid.UUID('b99012a6-8c41-43c8-845d-7595ce7140d9'),
                                               act=3, percentage=84),
                                     StoryBeat(text='High Tower Surprise',
                                               icon='mdi.lighthouse-on',
                                               icon_color='#586f7c',
                                               id=uuid.UUID('fe77f4f2-9064-4b06-8062-920635aa415c'),
                                               act=3, percentage=88),
                                     StoryBeat(text='Dig Deep Down',
                                               icon='mdi.shovel',
                                               icon_color='#b08968',
                                               id=uuid.UUID('a5c4d0aa-9811-4988-8611-3483b2499732'),
                                               act=3, percentage=92),
                                     StoryBeat(text='Execute a New Plan',
                                               icon='mdi.lightbulb-on',
                                               icon_color='#4361ee',
                                               id=uuid.UUID('13d535f6-6b3d-4211-ae44-e0fcf3970186'),
                                               act=3, percentage=95),
                                     StoryBeat(text='Final Image',
                                               icon='fa5s.water',
                                               icon_color='#7192be',
                                               id=uuid.UUID('12d5ec21-af96-4e51-9c26-06583d830d87'),
                                               act=3, percentage=99),
                                     ])

story_circle = StoryStructure(title="Story circle",
                              id=uuid.UUID('ede1a536-435c-4298-a43c-a931e353848b'),
                              icon='mdi.chart-arc',
                              beats=[StoryBeat(text='You',
                                               id=uuid.UUID('ef7e76fa-c67a-49b1-9b28-e222482d1524'),
                                               act=1, percentage=1),
                                     StoryBeat(text='Need',
                                               id=uuid.UUID('09503ff3-0d49-4c06-9189-45a2a236f5de'),
                                               act=1, ends_act=True, percentage=13),
                                     StoryBeat(text='Go',
                                               id=uuid.UUID('bcd6f1a4-07d1-48b9-a41c-2642e49bb83b'),
                                               act=2, ends_act=True, percentage=25),
                                     StoryBeat(text='Search',
                                               id=uuid.UUID('984f671a-d801-4e19-99de-291ae265b0e0'),
                                               act=3, ends_act=True, percentage=37),
                                     StoryBeat(text='Find',
                                               id=uuid.UUID('86b002da-ed4f-4139-b8ab-064e62787ddb'),
                                               act=4, ends_act=True, percentage=50),
                                     StoryBeat(text='Take',
                                               id=uuid.UUID('0bb73a18-2837-4b3d-a8c7-b11e007b215d'),
                                               act=5, ends_act=True, percentage=62),
                                     StoryBeat(text='Return',
                                               id=uuid.UUID('7b5a55f6-47ed-4564-b19c-75e91bde7ce4'),
                                               act=6, ends_act=True, percentage=75),
                                     StoryBeat(text='Change',
                                               id=uuid.UUID('5a41ee1f-6e17-404e-a773-a00309284afe'),
                                               act=7, ends_act=True, percentage=88),
                                     ])

default_story_structures = [three_act_structure, weiland_10_beats, save_the_cat, story_circle]


@dataclass
class NovelDescriptor:
    title: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)


class TemplateFieldType(Enum):
    TEXT = 0
    SMALL_TEXT = 1
    TEXT_SELECTION = 2
    BUTTON_SELECTION = 3
    NUMERIC = 4
    IMAGE = 5
    LABELS = 6


class SelectionType(Enum):
    SINGLE_LIST = 0
    CHECKBOX = 1
    CHECKED_BUTTON = 2
    TAGS = 3


@dataclass
class TemplateField:
    name: str
    type: TemplateFieldType
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    description: str = ''
    emoji: str = ''
    placeholder: str = ''
    selections: List[SelectionItem] = field(default_factory=list)
    highlighted: bool = False
    required: bool = False
    exclusive: bool = False
    custom: bool = False
    min_value: int = 0
    max_value = 2_147_483_647
    compact: bool = False
    frozen: bool = False
    show_label: bool = True


name_field = TemplateField(name='Name', type=TemplateFieldType.TEXT, emoji=':bust_in_silhouette:', placeholder='Name',
                           id=uuid.UUID('45525d2e-3ba7-40e4-b072-e367f96a6eb4'), required=True, highlighted=True,
                           frozen=True, compact=True, show_label=False)
avatar_field = TemplateField(name='Avatar', type=TemplateFieldType.IMAGE,
                             id=uuid.UUID('c3b5c7b5-6fd2-4ae1-959d-6fabd659cb3c'), required=True, highlighted=True,
                             frozen=True, compact=True, show_label=False)
age_field = TemplateField(name='Age', type=TemplateFieldType.NUMERIC,
                          id=uuid.UUID('7c8fccb8-9228-495a-8edd-3f991ebeed4b'), emoji=':birthday_cake:',
                          show_label=False, compact=True, placeholder='Age')
gender_field = TemplateField(name='Gender', type=TemplateFieldType.BUTTON_SELECTION,
                             id=uuid.UUID('dd5421f5-b332-4295-8020-e69c482a2ac5'),
                             selections=[SelectionItem('Male', icon='mdi.gender-male', icon_color='#067bc2'),
                                         SelectionItem('Female', icon='mdi.gender-female', icon_color='#832161')],
                             compact=True, show_label=False, exclusive=True)
enneagram_field = TemplateField(name='Enneagram', type=TemplateFieldType.TEXT_SELECTION,
                                id=uuid.UUID('be281490-c1b7-413c-b519-f780dbdafaeb'),
                                selections=[SelectionItem('Perfectionist', icon='mdi.numeric-1-circle',
                                                          icon_color='#1f487e',
                                                          meta={'positive': ['Rational', 'Principled', 'Objective',
                                                                             'Structured'],
                                                                'negative': ['Strict'],
                                                                'desire': 'Being good, balanced, have integrity',
                                                                'fear': 'Being incorrect, corrupt, evil'}),
                                            SelectionItem('Giver', icon='mdi.numeric-2-circle',
                                                          icon_color='#7ae7c7',
                                                          meta={'positive': ['Generous', 'Warm', 'Caring'],
                                                                'negative': ['Possessive'],
                                                                'desire': 'To be loved and appreciated',
                                                                'fear': 'Being unloved, unwanted'}
                                                          ),
                                            SelectionItem('Achiever', icon='mdi.numeric-3-circle',
                                                          icon_color='#297045',
                                                          meta={'positive': ['Pragmatic', 'Driven', 'Ambitious'],
                                                                'negative': ['Image-conscious'],
                                                                'desire': 'Be valuable and worthwhile',
                                                                'fear': 'Being worthless'}
                                                          ),
                                            SelectionItem('Individualist', icon='mdi.numeric-4-circle',
                                                          icon_color='#4d8b31',
                                                          meta={'positive': ['Self-aware', 'Sensitive', 'Expressive'],
                                                                'negative': ['Temperamental'],
                                                                'desire': 'Express their individuality',
                                                                'fear': 'Having no identity or significance'}
                                                          ),
                                            SelectionItem('Investigator', icon='mdi.numeric-5-circle',
                                                          icon_color='#ffc600',
                                                          meta={'positive': ['Perceptive', 'Curious', 'Innovative'],
                                                                'negative': ['Isolated'],
                                                                'desire': 'Be competent',
                                                                'fear': 'Being useless, incompetent'}
                                                          ),
                                            SelectionItem('Skeptic', icon='mdi.numeric-6-circle',
                                                          icon_color='#ff6b35',
                                                          meta={'positive': ['Committed', 'Responsible', 'Organized'],
                                                                'negative': ['Anxious'],
                                                                'desire': 'Have security and support',
                                                                'fear': 'Being vulnerable and unprepared'}
                                                          ),
                                            SelectionItem('Enthusiast', icon='mdi.numeric-7-circle',
                                                          icon_color='#ec0b43',
                                                          meta={'positive': ['Optimistic', 'Flexible', 'Practical',
                                                                             'Adventurous'],
                                                                'negative': ['Impulsive', 'Self-centered'],
                                                                'desire': 'Be stimulated, engaged, satisfied',
                                                                'fear': 'Being deprived'}
                                                          ),
                                            SelectionItem('Challenger', icon='mdi.numeric-8-circle',
                                                          icon_color='#4f0147',
                                                          meta={'positive': ['Decisive', 'Powerful', 'Assertive',
                                                                             'Independent'],
                                                                'negative': ['Confrontational'],
                                                                'desire': 'Be independent and in control',
                                                                'fear': 'Being vulnerable, controlled, harmed'}
                                                          ),
                                            SelectionItem('Peacemaker', icon='mdi.numeric-9-circle',
                                                          icon_color='#3a015c',
                                                          meta={'positive': ['Easygoing', 'Understanding', 'Patient',
                                                                             'Supportive'],
                                                                'negative': ['Lazy', 'Indecisive'],
                                                                'desire': 'Internal peace, harmony',
                                                                'fear': 'Loss, separation'}
                                                          )],
                                compact=True)
mbti_field = TemplateField(name='MBTI', type=TemplateFieldType.TEXT_SELECTION,
                           id=uuid.UUID('bc5408a4-c2bd-4370-b46b-95f20018af01'),
                           selections=[SelectionItem('ISTJ', icon='mdi.magnify', icon_color='#2a9d8f'),  # green
                                       SelectionItem('ISFJ', icon='mdi.fireplace', icon_color='#2a9d8f'),
                                       SelectionItem('ESTP', icon='ei.fire', icon_color='#2a9d8f'),
                                       SelectionItem('ESFP', icon='mdi.microphone-variant', icon_color='#2a9d8f'),

                                       SelectionItem('INFJ', icon='ph.tree-fill', icon_color='#e9c46a'),  # yellow
                                       SelectionItem('INTJ', icon='fa5s.drafting-compass', icon_color='#e9c46a'),
                                       SelectionItem('ENFP', icon='fa5.sun', icon_color='#e9c46a'),
                                       SelectionItem('ENTP', icon='fa5.lightbulb', icon_color='#e9c46a'),

                                       SelectionItem('ISTP', icon='fa5s.hammer', icon_color='#457b9d'),  # blue
                                       SelectionItem('INTP', icon='ei.puzzle', icon_color='#457b9d'),
                                       SelectionItem('ESTJ', icon='mdi.gavel', icon_color='#457b9d'),
                                       SelectionItem('ENTJ', icon='fa5.compass', icon_color='#457b9d'),

                                       SelectionItem('ISFP', icon='mdi6.violin', icon_color='#d00000'),  # red
                                       SelectionItem('INFP', icon='fa5s.cloud-sun', icon_color='#d00000'),
                                       SelectionItem('ESFJ', icon='mdi6.cupcake', icon_color='#d00000'),
                                       SelectionItem('ENFJ', icon='mdi6.flower', icon_color='#d00000'),
                                       ],
                           compact=True)

positive_traits = sorted(['Generous', 'Objective', 'Principled', 'Rational',
                          'Structured', 'Caring', 'Warm', 'Driven', 'Ambitious', 'Self-aware', 'Sensitive',
                          'Expressive', 'Perceptive', 'Curious', 'Innovative', 'Committed', 'Responsible', 'Organized',
                          'Optimistic', 'Flexible', 'Practical',
                          'Adventurous', 'Decisive', 'Powerful', 'Assertive', 'Pragmatic',
                          'Independent', 'Easygoing', 'Understanding', 'Patient',
                          'Supportive'])
negative_traits = sorted(
    ['Anxious', 'Confrontational', 'Indecisive', 'Strict', 'Possessive', 'Image-conscious', 'Temperamental',
     'Isolated', 'Impulsive', 'Self-centered', 'Lazy'])

traits_field = TemplateField(name='Traits', type=TemplateFieldType.LABELS,
                             id=uuid.UUID('76faae5f-b1e4-47f4-9e3f-ed8497f6c6d3'))
for trait in positive_traits:
    traits_field.selections.append(SelectionItem(trait, meta={'positive': True}))
for trait in negative_traits:
    traits_field.selections.append(SelectionItem(trait, meta={'positive': False}))


def get_selection_values(field: TemplateField) -> Dict[str, SelectionItem]:
    _choices = {}
    for item in field.selections:
        if item.type != SelectionItemType.CHOICE:
            continue
        _choices[item.text] = item
    return _choices


_enneagram_choices = get_selection_values(enneagram_field)
_mbti_choices = get_selection_values(mbti_field)

goal_field = TemplateField('Goals', type=TemplateFieldType.LABELS,
                           id=uuid.UUID('5e6bf763-6fa1-424a-b011-f5974290a32a'),
                           emoji=':bullseye:',
                           placeholder='Character goals throughout the story')
misbelief_field = TemplateField('Misbelief', type=TemplateFieldType.SMALL_TEXT,
                                id=uuid.UUID('32feaa23-acbf-4990-b99f-429747824a0b'),
                                placeholder='The misbelief/lie the character believes in')
fear_field = TemplateField('Fear', type=TemplateFieldType.SMALL_TEXT, emoji=':face_screaming_in_fear:',
                           placeholder='Fear (select Enneagram to autofill)',
                           id=uuid.UUID('d03e91bf-bc58-441a-ae81-a7764c4d7e25'), show_label=False)
desire_field = TemplateField('Desire', type=TemplateFieldType.SMALL_TEXT, emoji=':star-struck:',
                             placeholder='Desire (select Enneagram to autofill)',
                             id=uuid.UUID('92729dda-ec8c-4a61-9ed3-039c12c10ba8'), show_label=False)
role_field = TemplateField('Role', type=TemplateFieldType.TEXT_SELECTION, emoji=':chess_pawn:',
                           id=uuid.UUID('131b9de6-ac95-4db5-b9a1-33200100b676'),
                           selections=[SelectionItem('Protagonist', icon='fa5s.chess-king', icon_color='#00798c'),
                                       SelectionItem('', type=SelectionItemType.SEPARATOR),
                                       SelectionItem('Deuteragonist', icon='mdi.atom-variant', icon_color='#820b8a'),
                                       SelectionItem('', type=SelectionItemType.SEPARATOR),
                                       SelectionItem('Antagonist', icon='mdi.guy-fawkes-mask', icon_color='#bc412b'),
                                       SelectionItem('Contagonist', icon='mdi.biohazard', icon_color='#ea9010'),
                                       SelectionItem('Adversary', icon='fa5s.thumbs-down', icon_color='#9e1946'),
                                       SelectionItem('Henchmen', icon='mdi.shuriken', icon_color='#596475'),
                                       SelectionItem('', type=SelectionItemType.SEPARATOR),
                                       SelectionItem('Guide', icon='mdi.compass-rose', icon_color='#80ced7'),
                                       SelectionItem('Confidant', icon='fa5s.user-friends', icon_color='#304d6d'),
                                       SelectionItem('Sidekick', icon='ei.asl', icon_color='#b0a990'),
                                       SelectionItem('Love Interest', icon='ei.heart', icon_color='#d1495b'),
                                       SelectionItem('Supporter', icon='fa5s.thumbs-up', icon_color='#266dd3'),
                                       SelectionItem('', type=SelectionItemType.SEPARATOR),
                                       SelectionItem('Foil', icon='fa5s.yin-yang', icon_color='#947eb0'),
                                       SelectionItem('', type=SelectionItemType.SEPARATOR),
                                       SelectionItem('Secondary', icon='fa5s.chess-knight', icon_color='#619b8a'),
                                       SelectionItem('', type=SelectionItemType.SEPARATOR),
                                       SelectionItem('Tertiary', icon='mdi.chess-pawn', icon_color='#886f68'),
                                       ], compact=True)

_role_choices = {}
for item in role_field.selections:
    if item.type != SelectionItemType.CHOICE:
        continue
    _role_choices[item.text] = item


class HAlignment(Enum):
    DEFAULT = 0
    LEFT = Qt.AlignLeft
    RIGHT = Qt.AlignRight
    CENTER = Qt.AlignHCenter
    JUSTIFY = Qt.AlignJustify


class VAlignment(Enum):
    TOP = Qt.AlignTop
    BOTTOM = Qt.AlignBottom
    CENTER = Qt.AlignVCenter


@dataclass
class ProfileElement:
    field: TemplateField
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    h_alignment: HAlignment = HAlignment.DEFAULT
    v_alignment: VAlignment = VAlignment.CENTER


@dataclass
class ProfileTemplate:
    title: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    elements: List[ProfileElement] = field(default_factory=list)


def default_character_profiles() -> List[ProfileTemplate]:
    fields = [ProfileElement(name_field, 0, 0),
              ProfileElement(avatar_field, 0, 1, row_span=3, h_alignment=HAlignment.RIGHT),
              ProfileElement(gender_field, 1, 0, v_alignment=VAlignment.BOTTOM),
              ProfileElement(age_field, 2, 0, v_alignment=VAlignment.TOP),
              ProfileElement(role_field, 3, 0, v_alignment=VAlignment.BOTTOM),
              ProfileElement(goal_field, 4, 0, col_span=2, v_alignment=VAlignment.TOP),
              ProfileElement(enneagram_field, 5, 0),
              ProfileElement(mbti_field, 5, 1),
              ProfileElement(desire_field, 6, 0),
              ProfileElement(fear_field, 6, 1),
              ProfileElement(traits_field, 7, 0, col_span=2),
              ]
    return [ProfileTemplate(title='Default character template',
                            id=uuid.UUID('6e89c683-c132-469b-a75c-6712af7c339d'),
                            elements=fields)]


sight_field = TemplateField('Sight', type=TemplateFieldType.LABELS,
                            id=uuid.UUID('935e6595-27ae-426e-8b41-b315e9160ad9'),
                            emoji=':eyes:',
                            placeholder='Sight')

location_name_field = TemplateField(name='Name', type=TemplateFieldType.TEXT, emoji=':round_pushpin:',
                                    placeholder='Name',
                                    id=uuid.UUID('84f9bdee-c817-4caa-9e65-666cd0c4a546'), required=True,
                                    highlighted=True,
                                    frozen=True, show_label=False)

smell_field = TemplateField('Smell', type=TemplateFieldType.LABELS,
                            id=uuid.UUID('50245a33-599b-49c6-9746-094f12b4d667'),
                            emoji=':nose:',
                            placeholder='Smell')
noise_field = TemplateField('Noise', type=TemplateFieldType.LABELS,
                            id=uuid.UUID('76659d94-8753-4945-8d5c-e811189e3b49'),
                            emoji=':speaker_high_volume:',
                            placeholder='Noise')

animals_field = TemplateField('Animals', type=TemplateFieldType.LABELS,
                              id=uuid.UUID('3aa9cc09-312c-492a-bc19-6914bb1eeba6'),
                              emoji=':paw_prints:',
                              placeholder='Animals')
nature_field = TemplateField('Nature', type=TemplateFieldType.LABELS,
                             id=uuid.UUID('ab54bf84-1b69-4bb4-b1b4-c04ad2dd58b1'),
                             emoji=':shamrock:',
                             placeholder='Nature')


def default_location_profiles() -> List[ProfileTemplate]:
    fields = [ProfileElement(location_name_field, 0, 0, col_span=2, h_alignment=HAlignment.CENTER),
              ProfileElement(sight_field, 1, 0),
              ProfileElement(smell_field, 1, 1),
              ProfileElement(noise_field, 2, 0),
              ProfileElement(animals_field, 3, 0),
              ProfileElement(nature_field, 3, 1),
              ]
    return [ProfileTemplate(title='Default location template',
                            id=uuid.UUID('8a95aa51-a975-416e-83d4-e349b84565b1'),
                            elements=fields)]


@dataclass
class CausalityItem(SelectionItem):
    links: List['CausalityItem'] = field(default_factory=list)

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
class Document(CharacterBased):
    title: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    type: DocumentType = DocumentType.DOCUMENT
    children: List['Document'] = field(default_factory=list)
    character_id: Optional[uuid.UUID] = None
    scene_id: Optional[uuid.UUID] = None
    data_id: Optional[uuid.UUID] = None
    icon: str = ''
    icon_color: str = 'black'

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
    return [Document('Story structure', id=uuid.UUID('ec2a62d9-fc00-41dd-8a6c-b121156b6cf4')),
            Document('Characters', id=uuid.UUID('8fa16650-bed0-489b-baa1-d239e5198d47')),
            Document('Scenes', id=uuid.UUID('75a552f4-037d-4179-860f-dd8400a7545b')),
            Document('Worldbuilding', id=uuid.UUID('5faf7c16-f970-465d-bbcb-1bad56f3313c')),
            Document('Brainstorming', id=uuid.UUID('f6df3a87-7054-40d6-a4b0-ad9917003136'))]


def default_tags() -> List[SelectionItem]:
    return [SelectionItem('Flashback', icon='fa5s.backward', icon_color='white', color_hexa='#1b263b'),
            SelectionItem('Flashforward', icon='fa5s.forward', icon_color='white', color_hexa='#1b998b'),
            SelectionItem('Ticking clock', icon='mdi.clock-alert-outline', icon_color='#f7cb15'),
            SelectionItem('Foreshadowing', icon='mdi.crystal-ball', icon_color='#76bed0'),
            SelectionItem('Cliffhanger', icon='mdi.target-account', icon_color='#f7cb15'),
            SelectionItem('Backstory', icon='mdi.archive', icon_color='#9a6d38'),
            SelectionItem('Red herring', icon='fa5s.fish', icon_color='#d33f49')]


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
    scene_goals: List[SceneGoal] = field(default_factory=list)
    documents: List[Document] = field(default_factory=default_documents)
    tags: List[SelectionItem] = field(default_factory=default_tags)
    logline: str = ''
    synopsis: Optional['Document'] = None

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
        self.scene_goals.clear()
        self.scene_goals.extend(updated_novel.scene_goals)
        self.tags.clear()
        self.tags.extend(updated_novel.tags)

    def pov_characters(self) -> List[Character]:
        pov_ids = set()
        povs: List[Character] = []
        for scene in self.scenes:
            if scene.pov and str(scene.pov.id) not in pov_ids:
                povs.append(scene.pov)
                pov_ids.add(str(scene.pov.id))

        return povs

    @property
    def active_story_structure(self) -> StoryStructure:
        for structure in self.story_structures:
            if structure.active:
                return structure
        return self.story_structures[0]


@dataclass
class Task:
    message: str
    reference: Optional[Any] = None
