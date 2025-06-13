"""
Plotlyst
Copyright (C) 2021-2024  Zsolt Kovari

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
import copy
import uuid
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import List, Optional, Any, Dict

from PyQt6.QtCore import Qt
from dataclasses_json import dataclass_json, Undefined, config
from overrides import overrides
from qttextedit import DashInsertionMode
from qttextedit.api import AutoCapitalizationMode, EllipsisInsertionMode

from plotlyst.common import act_color, RED_COLOR, PLOTLYST_SECONDARY_COLOR
from plotlyst.core.template import SelectionItem, exclude_if_empty, exclude_if_black, enneagram_choices, \
    mbti_choices, Role, exclude_if_false, antagonist_role, exclude_if_true
from plotlyst.view.common import default_character_color


@dataclass
class TemplateValue:
    id: uuid.UUID
    value: Any
    ignored: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    notes: str = field(default='', metadata=config(exclude=exclude_if_empty))

    @overrides
    def __eq__(self, other: 'TemplateValue'):
        if isinstance(other, TemplateValue):
            return self.id == other.id and self.value == other.value
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


class LayoutType(Enum):
    HORIZONTAL = 0
    VERTICAL = 1
    FLOW = 2
    CURVED_FLOW = 3
    GRID = 4


@dataclass
class Event:
    keyphrase: str
    synopsis: str
    emotion: int = 5


@dataclass
class Comment:
    text: str
    created_at: datetime = datetime.now()
    major: bool = False
    resolved: bool = False
    character: Optional['Character'] = None


@dataclass
class ImageRef:
    extension: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __post_init__(self):
        self.loaded: bool = False
        self.data: Any = None

    @overrides
    def __eq__(self, other: 'ImageRef'):
        if isinstance(other, ImageRef):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


class TopicType(Enum):
    Physical = auto()
    Habits = auto()
    Skills = auto()
    Fears = auto()
    Background = auto()
    Hobbies = auto()
    Communication = auto()
    Beliefs = auto()
    Worldbuilding = auto()

    @property
    def text(self):
        return self.name

    def description(self) -> str:
        if self == TopicType.Physical:
            return 'Body type, clothing, hairstyle, etc.'
        elif self == TopicType.Habits:
            return 'Exercises, routines, bad habits, superstitions, daily rituals'
        elif self == TopicType.Skills:
            return 'Art and creativity, technical, leadership, communication, emotional intelligence'
        elif self == TopicType.Fears:
            return 'Fears, phobias, social anxiety, public speaking, etc.'
        elif self == TopicType.Background:
            return 'Cultural heritage, traditions, family, education, identity struggles, dreams'
        elif self == TopicType.Hobbies:
            return 'Sports, art, collecting, travel, leisure time'
        elif self == TopicType.Communication:
            return 'Conversation style, listening skills, networking, charisma'
        elif self == TopicType.Beliefs:
            return 'Religion, spirituality, ethics and morals, political beliefs'

    def icon(self) -> str:
        if self == TopicType.Physical:
            return 'mdi6.human-male-height-variant'
        elif self == TopicType.Habits:
            return 'mdi.smoking'
        elif self == TopicType.Skills:
            return 'fa5s.palette'
        elif self == TopicType.Fears:
            return 'ri.ghost-2-fill'
        elif self == TopicType.Background:
            return 'fa5s.passport'
        elif self == TopicType.Hobbies:
            return 'fa5s.book-reader'
        elif self == TopicType.Communication:
            return 'ph.chats-circle'
        elif self == TopicType.Beliefs:
            return 'fa5s.balance-scale'

    def display_name(self) -> str:
        if self == TopicType.Physical:
            return 'Physical Appearance'
        elif self == TopicType.Habits:
            return 'Habits and Routines'
        elif self == TopicType.Skills:
            return 'Skills and Talents'
        elif self == TopicType.Fears:
            return 'Fears and Phobias'
        elif self == TopicType.Background:
            return 'Background and Identity'
        elif self == TopicType.Hobbies:
            return 'Interests and Hobbies'
        elif self == TopicType.Communication:
            return 'Communication'
        elif self == TopicType.Beliefs:
            return 'Beliefs'

    def id(self) -> uuid.UUID:
        if self == TopicType.Physical:
            return uuid.UUID('d841dc6a-18b2-4aa1-a4bb-144d7a47a4b2')
        elif self == TopicType.Habits:
            return uuid.UUID('2cd853f0-76db-4c0f-9736-610ba56a3351')
        elif self == TopicType.Skills:
            return uuid.UUID('4998d508-dbb0-4a00-bb1b-94a4511393c1')
        elif self == TopicType.Fears:
            return uuid.UUID('53e0be5c-951a-43fc-8722-61797d1a0151')
        elif self == TopicType.Background:
            return uuid.UUID('0ede391c-8c73-4f76-9e73-12d80044ffbb')
        elif self == TopicType.Hobbies:
            return uuid.UUID('f9f8d9b9-f609-4fec-8ae6-7eb5cef55fc5')
        elif self == TopicType.Communication:
            return uuid.UUID('9020065e-9a6a-479f-bd44-d29dc10cf52d')
        elif self == TopicType.Beliefs:
            return uuid.UUID('ba23f272-eec5-44d1-8abd-f032d1ae414a')

    def topic(self) -> 'Topic':
        return Topic(self.display_name(), self, id=self.id(), icon=self.icon())


@dataclass
class Topic:
    text: str
    type: TopicType
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))
    icon_color: str = field(default='black', metadata=config(exclude=exclude_if_black))
    description: str = field(default='', metadata=config(exclude=exclude_if_empty))

    @overrides
    def __eq__(self, other: 'Topic'):
        if isinstance(other, Topic):
            return self.id == other.id and self.text == other.text
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


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


class Position(Enum):
    LEFT = 0
    RIGHT = 1
    CENTER = 2

    def toggle(self) -> 'Position':
        if self == Position.RIGHT:
            return Position.LEFT
        if self == Position.LEFT:
            return Position.RIGHT


@dataclass
class BackstoryEvent(Event):
    type: BackstoryEventType = BackstoryEventType.Event
    type_icon: str = 'ri.calendar-event-fill'
    type_color: str = 'darkBlue'
    position: Optional[Position] = None


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

    @overrides
    def __eq__(self, other: 'CharacterGoal'):
        if isinstance(other, CharacterGoal):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


@dataclass
class CharacterPlan:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    summary: str = ''
    external: bool = True
    goals: List[CharacterGoal] = field(default_factory=list)

    @overrides
    def __eq__(self, other: 'CharacterPlan'):
        if isinstance(other, CharacterPlan):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


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
class BigFiveFacet:
    name: str


@dataclass
class BigFiveDimension:
    name: str
    color: str = 'black'
    icon: str = ''
    facets: List[BigFiveFacet] = field(default_factory=list)

    @overrides
    def __eq__(self, other: 'BigFiveDimension'):
        if isinstance(other, BigFiveDimension):
            return self.name == other.name
        return False

    @overrides
    def __hash__(self):
        return hash(self.name)


agreeableness = BigFiveDimension('agreeableness', color='#8ecae6', icon='fa5s.thumbs-up',
                                 facets=[
                                     BigFiveFacet('trust'),
                                     BigFiveFacet('straightforwardness'),
                                     BigFiveFacet('altruism'),
                                     BigFiveFacet('compliance'),
                                     BigFiveFacet('modesty'),
                                     BigFiveFacet('tender-mindedness'),
                                 ])
neuroticism = BigFiveDimension('neuroticism', color='#e63946', icon='mdi6.head-flash',
                               facets=[
                                   BigFiveFacet('anxiety'),
                                   BigFiveFacet('depression'),
                                   BigFiveFacet('impulsiveness'),
                                   BigFiveFacet('hostility'),
                                   BigFiveFacet('vulnerability'),
                                   BigFiveFacet('self-consciousness'),
                               ])
extroversion = BigFiveDimension('extroversion', color='#a7c957', icon='fa5s.people-arrows',
                                facets=[
                                    BigFiveFacet('warmth'),
                                    BigFiveFacet('gregariousness'),
                                    BigFiveFacet('assertiveness'),
                                    BigFiveFacet('activity'),
                                    BigFiveFacet('excitement-seeking'),
                                    BigFiveFacet('positive emotions'),
                                ])
openness = BigFiveDimension('openness', color='#e9c46a', icon='mdi.head-lightbulb',
                            facets=[
                                BigFiveFacet('fantasy'),
                                BigFiveFacet('aesthetics'),
                                BigFiveFacet('feelings'),
                                BigFiveFacet('actions'),
                                BigFiveFacet('ideas'),
                                BigFiveFacet('values'),
                            ])
conscientiousness = BigFiveDimension('conscientiousness', color='#cdb4db', icon='mdi.head-cog-outline',
                                     facets=[
                                         BigFiveFacet('competence'),
                                         BigFiveFacet('order'),
                                         BigFiveFacet('dutifulness'),
                                         BigFiveFacet('achievement striving'),
                                         BigFiveFacet('self-discipline'),
                                         BigFiveFacet('deliberation'),
                                     ])


def default_big_five_values() -> Dict[str, List[int]]:
    return {
        agreeableness.name: [50, 50, 50, 50, 50, 50],
        neuroticism.name: [50, 50, 50, 50, 50, 50],
        extroversion.name: [50, 50, 50, 50, 50, 50],
        openness.name: [50, 50, 50, 50, 50, 50],
        conscientiousness.name: [50, 50, 50, 50, 50, 50]
    }


@dataclass
class CharacterPreferences:
    avatar: AvatarPreferences = field(default_factory=AvatarPreferences)
    settings: Dict[str, Any] = field(default_factory=dict)

    def toggled(self, setting: 'NovelSetting', default: bool = True) -> bool:
        return self.settings.get(setting.value, default)


class CharacterProfileSectionType(Enum):
    Summary = 'summary'
    Personality = 'personality'
    Philosophy = 'philosophy'
    Faculties = 'faculties'
    Flaws = 'flaws'
    Strengths = 'strengths and weaknesses'
    Baggage = 'baggage'
    Goals = 'goals'
    Lack = 'lack'

    # def description(self) -> str:
    #     if self == CharacterProfileSectionType.Summary:
    #         return "Summary of the character's role or personality"
    #     elif self == CharacterProfileSectionType.Personality:
    #         return "Personality traits and common personality types"
    #     elif self == CharacterProfileSectionType.Philosophy:
    #         return "The character's values"
    #     elif self == CharacterProfileSectionType.Strengths:
    #         return "The character's strengths and weaknesses"
    #     elif self == CharacterProfileSectionType.Faculties:
    #         return "IQ, emotional intelligence, rationality, willpower, creativity"
    #     elif self == CharacterProfileSectionType.Flaws:
    #         return "Character's flaws"
    #     elif self == CharacterProfileSectionType.Baggage:
    #         return "Character's ghosts, wounds, misbeliefs, demons, or fears"
    #     elif self == CharacterProfileSectionType.Goals:
    #         return "Goal, conflict, motivation, stakes, and methods"


class CharacterProfileFieldType(Enum):
    Text = 'text'
    Image = 'image'
    Labels = 'labels'
    Bar = 'bar'
    Field_Summary = 'summary'
    Field_Personality = 'personality'
    Field_Traits = 'traits'
    Field_Values = 'values'
    Field_Strengths = 'strengths'
    Field_Faculties_IQ = 'iq'
    Field_Faculties_EQ = 'eq'
    Field_Faculties_Rationalism = 'rationalism'
    Field_Faculties_Creativity = 'creativity'
    Field_Faculties_Willpower = 'willpower'
    Field_Flaws = 'flaws'
    Field_Baggage = 'baggage'
    Field_Goals = 'goals'
    Field_Lacks = 'lacks'


@dataclass
class CharacterProfileFieldReference:
    type: CharacterProfileFieldType
    ref: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))
    value: Optional[Any] = field(default=None, metadata=config(exclude=exclude_if_empty))


@dataclass
class CharacterProfileSectionReference:
    type: Optional[CharacterProfileSectionType] = field(default=None, metadata=config(exclude=exclude_if_empty))
    ref: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))
    fields: List[CharacterProfileFieldReference] = field(default_factory=list)
    enabled: bool = field(default=True, metadata=config(exclude=exclude_if_true))


def default_character_profile() -> List[CharacterProfileSectionReference]:
    return [
        CharacterProfileSectionReference(CharacterProfileSectionType.Summary, fields=[
            CharacterProfileFieldReference(CharacterProfileFieldType.Field_Summary)
        ]),
        CharacterProfileSectionReference(CharacterProfileSectionType.Personality, fields=[
            CharacterProfileFieldReference(CharacterProfileFieldType.Field_Personality),
            CharacterProfileFieldReference(CharacterProfileFieldType.Field_Traits),
        ]),
        CharacterProfileSectionReference(CharacterProfileSectionType.Philosophy, fields=[
            CharacterProfileFieldReference(CharacterProfileFieldType.Field_Values)
        ]),
        CharacterProfileSectionReference(CharacterProfileSectionType.Faculties, fields=[
            CharacterProfileFieldReference(CharacterProfileFieldType.Field_Faculties_IQ),
            CharacterProfileFieldReference(CharacterProfileFieldType.Field_Faculties_EQ),
            CharacterProfileFieldReference(CharacterProfileFieldType.Field_Faculties_Rationalism),
            CharacterProfileFieldReference(CharacterProfileFieldType.Field_Faculties_Willpower),
            CharacterProfileFieldReference(CharacterProfileFieldType.Field_Faculties_Creativity)
        ]),
        CharacterProfileSectionReference(CharacterProfileSectionType.Flaws),
        CharacterProfileSectionReference(CharacterProfileSectionType.Strengths, fields=[
            CharacterProfileFieldReference(CharacterProfileFieldType.Field_Strengths)
        ]),
        CharacterProfileSectionReference(CharacterProfileSectionType.Baggage),
        CharacterProfileSectionReference(CharacterProfileSectionType.Goals),
        CharacterProfileSectionReference(CharacterProfileSectionType.Lack)
    ]


class MultiAttributePrimaryType(Enum):
    External_goal = 'external_goal'
    Internal_goal = 'internal_goal'
    Ghost = 'ghost'
    Wound = 'wound'
    Demon = 'demon'
    Fear = 'fear'
    Misbelief = 'misbelief'
    Flaw = 'flaw'
    Void = 'void'
    Psychological_need = 'psychological_need'
    Interpersonal_need = 'interpersonal_need'


class MultiAttributeSecondaryType(Enum):
    External_motivation = 'external_motivation'
    Internal_motivation = 'internal_motivation'
    External_conflict = 'external_conflict'
    Internal_conflict = 'internal_conflict'
    External_stakes = 'external_stakes'
    Internal_stakes = 'internal_stakes'
    Methods = 'methods'

    Baggage_source = 'baggage_source'
    Baggage_manifestation = 'baggage_manifestation'
    Baggage_relation = 'baggage_relation'
    Baggage_coping = 'baggage_coping'
    Baggage_healing = 'baggage_healing'
    Baggage_deterioration = 'baggage_deterioration'
    Baggage_defense_mechanism = 'baggage_defense_mechanism'
    Baggage_trigger = 'baggage_trigger'

    Flaw_triggers = 'flaw_triggers'
    Flaw_coping = 'flaw_coping'
    Flaw_manifestation = 'flaw_manifestation'
    Flaw_relation = 'flaw_relation'
    Flaw_goals = 'flaw_goals'
    Flaw_growth = 'flaw_growth'
    Flaw_deterioration = 'flaw_deterioration'


@dataclass
class CharacterSecondaryAttribute:
    type: MultiAttributeSecondaryType
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    value: str = field(default='', metadata=config(exclude=exclude_if_empty))


@dataclass
class CharacterMultiAttribute:
    type: MultiAttributePrimaryType
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    value: str = field(default='', metadata=config(exclude=exclude_if_empty))
    attributes: Dict[str, CharacterSecondaryAttribute] = field(default_factory=dict,
                                                               metadata=config(exclude=exclude_if_empty))
    settings: Dict[str, Any] = field(default_factory=dict)
    label: str = field(default='', metadata=config(exclude=exclude_if_empty))

    def attribute(self, type_: MultiAttributeSecondaryType) -> Optional[CharacterSecondaryAttribute]:
        if self.settings.get(type_.value, False):
            return self.attributes.get(type_.value)


@dataclass
class StrengthWeaknessAttribute:
    name: str
    has_strength: bool = False
    has_weakness: bool = False
    strength: str = ''
    weakness: str = ''


@dataclass
class CharacterPersonalityAttribute:
    value: str = ''


@dataclass
class CharacterPersonality:
    enneagram: Optional[CharacterPersonalityAttribute] = None
    mbti: Optional[CharacterPersonalityAttribute] = None
    love: Optional[CharacterPersonalityAttribute] = None
    work: Optional[CharacterPersonalityAttribute] = None


class TopicElementType(Enum):
    Text = 0
    Icon = 1
    Image = 2


@dataclass
class TopicElementBlock:
    type: TopicElementType = field(default=TopicElementType.Text)
    text: str = field(default='', metadata=config(exclude=exclude_if_empty))


@dataclass
class TopicElement:
    id: uuid.UUID
    blocks: List[TopicElementBlock] = field(default_factory=list)


def character_codex_root() -> 'WorldBuildingEntity':
    root_main_section = WorldBuildingEntityElement(WorldBuildingEntityElementType.Main_Section)
    root_main_section.blocks.append(WorldBuildingEntityElement(WorldBuildingEntityElementType.Header))
    root_main_section.blocks.append(WorldBuildingEntityElement(WorldBuildingEntityElementType.Text))

    elements = []
    for topicType in [TopicType.Physical, TopicType.Background, TopicType.Habits, TopicType.Hobbies, TopicType.Skills,
                      TopicType.Communication, TopicType.Beliefs]:
        topic = topicType.topic()
        section = WorldBuildingEntityElement(WorldBuildingEntityElementType.Section, title=topic.text, ref=topic.id)
        section.blocks.append(
            WorldBuildingEntityElement(WorldBuildingEntityElementType.Header, title=topic.text, icon=topic.icon))
        section.blocks.append(WorldBuildingEntityElement(WorldBuildingEntityElementType.Text))

        elements.append(section)

    first_section = WorldBuildingEntityElement(WorldBuildingEntityElementType.Section)
    first_section.blocks.append(WorldBuildingEntityElement(WorldBuildingEntityElementType.Header, title='Profile'))
    first_section.blocks.append(WorldBuildingEntityElement(WorldBuildingEntityElementType.Text))

    child_el = WorldBuildingEntity('Secondary Topics', icon='mdi.card-account-details-star-outline', side_visible=False,
                                   elements=elements)

    return WorldBuildingEntity('Character Codex', icon='ri.typhoon-fill', bg_color='#40916c', side_visible=False,
                               elements=[root_main_section], children=[child_el])


@dataclass
class Character:
    name: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    gender: str = field(default='', metadata=config(exclude=exclude_if_empty))
    role: Optional[Role] = None
    age: Optional[int] = None
    age_infinite: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    occupation: Optional[str] = None
    avatar: Optional[Any] = None
    template_values: List[TemplateValue] = field(default_factory=list)
    disabled_template_headers: Dict[str, bool] = field(default_factory=dict)
    backstory: List[BackstoryEvent] = field(default_factory=list)
    plans: List[CharacterPlan] = field(default_factory=list)
    document: Optional['Document'] = None
    journals: List['Document'] = field(default_factory=list)
    prefs: CharacterPreferences = field(default_factory=CharacterPreferences)
    topics: List[TopicElement] = field(default_factory=list)
    big_five: Dict[str, List[int]] = field(default_factory=default_big_five_values)
    profile: List[CharacterProfileSectionReference] = field(default_factory=default_character_profile)
    summary: str = field(default='', metadata=config(exclude=exclude_if_empty))
    faculties: Dict[str, int] = field(default_factory=dict, metadata=config(exclude=exclude_if_empty))
    traits: List[str] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    values: List[str] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    gmc: List[CharacterMultiAttribute] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    lack: List[CharacterMultiAttribute] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    baggage: List[CharacterMultiAttribute] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    flaws: List[CharacterMultiAttribute] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    strengths: List[StrengthWeaknessAttribute] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    personality: CharacterPersonality = field(default_factory=CharacterPersonality)
    alias: str = field(default='', metadata=config(exclude=exclude_if_empty))
    origin_id: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))
    codex: 'WorldBuildingEntity' = field(default_factory=character_codex_root)

    def __post_init__(self):
        if self.prefs.avatar.icon_color == 'black':
            self.prefs.avatar.icon_color = default_character_color(self.id)

    def enneagram(self) -> Optional[SelectionItem]:
        if self.prefs.toggled(NovelSetting.Character_enneagram):
            if self.personality.enneagram:
                return enneagram_choices.get(self.personality.enneagram.value)
        # for value in self.template_values:
        #     if value.id == enneagram_field.id:
        #         return enneagram_choices.get(value.value)

    def mbti(self) -> Optional[SelectionItem]:
        if self.prefs.toggled(NovelSetting.Character_mbti):
            if self.personality.mbti:
                return mbti_choices.get(self.personality.mbti.value)
        # for value in self.template_values:
        #     if value.id == mbti_field.id:
        #         return mbti_choices.get(value.value)

    def displayed_name(self) -> str:
        return self.alias if self.alias else self.name

    def is_major(self):
        return self.role and self.role.is_major()

    def is_secondary(self):
        return self.role and self.role.is_secondary()

    def is_minor(self) -> bool:
        return self.role and self.role.is_minor()

    def flatten_goals(self) -> List[CharacterGoal]:
        all_goals = []
        for plan in self.plans:
            for goal in plan.goals:
                all_goals.append(goal)
                for subgoal in goal.children:
                    all_goals.append(subgoal)

        return all_goals

    @overrides
    def __eq__(self, other: 'Character'):
        if isinstance(other, Character):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


class PlaceholderCharacter(Character):

    def __post_init__(self):
        self.prefs.avatar.allow_image()


class ChapterType(Enum):
    Prologue = 0
    Epilogue = 1
    Interlude = 2


@dataclass
class Chapter:
    title: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    type: Optional[ChapterType] = field(default=None, metadata=config(exclude=exclude_if_empty))

    def sid(self) -> str:
        return str(self.id)

    def display_name(self) -> str:
        if self.type is None:
            return self.title
        else:
            return self.type.name

    @overrides
    def __eq__(self, other: 'Chapter'):
        if isinstance(other, Chapter):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


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


class StoryBeatType(Enum):
    BEAT = 'beat'
    CONTAINER = 'container'


def exclude_if_beat(value):
    return value == StoryBeatType.BEAT


@dataclass
class OutlineItem:
    text: str = ''


class PlotProgressionItemType(Enum):
    BEGINNING = 0
    MIDDLE = 1
    ENDING = 2
    EVENT = 3


@dataclass
class PlotProgressionItem(OutlineItem):
    type: PlotProgressionItemType = PlotProgressionItemType.EVENT


@dataclass
class StoryBeat(OutlineItem):
    act: int = 0
    percentage: float = 1.0
    description: str = ''
    type: StoryBeatType = field(default=StoryBeatType.BEAT, metadata=config(exclude=exclude_if_beat))
    ends_act: bool = field(default=False, metadata=config(exclude=exclude_if_empty))
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    icon: str = ''
    icon_color: str = field(default='black', metadata=config(exclude=exclude_if_black))
    percentage_end: float = field(default=0, metadata=config(exclude=exclude_if_empty))
    enabled: bool = True
    notes: str = field(default='', metadata=config(exclude=exclude_if_empty))
    custom: bool = False
    act_colorized: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    placeholder: str = field(default='', metadata=config(exclude=exclude_if_empty))
    seq: int = field(default=0, metadata=config(exclude=exclude_if_empty))

    @overrides
    def __eq__(self, other: 'StoryBeat'):
        if isinstance(other, StoryBeat):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


@dataclass
class SceneStage(SelectionItem):
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    @overrides
    def __eq__(self, other: 'SceneStage'):
        if isinstance(other, SceneStage):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


@dataclass
class DramaticQuestion(SelectionItem):
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    @overrides
    def __eq__(self, other: 'DramaticQuestion'):
        if isinstance(other, DramaticQuestion):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


class PlotType(Enum):
    Main = 'main'
    Internal = 'internal'
    Subplot = 'subplot'
    Relation = 'relation'
    Global = 'global'


@dataclass
class PlotValue(SelectionItem):
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    negative: str = ''

    @overrides
    def __eq__(self, other: 'PlotValue'):
        if isinstance(other, PlotValue):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


class PlotPrincipleType(Enum):
    GOAL = 0
    ANTAGONIST = 1
    CONFLICT = 2
    QUESTION = 8
    STAKES = 9
    THEME = 10
    POSITIVE_CHANGE = 11
    NEGATIVE_CHANGE = 12
    DESIRE = 13
    NEED = 14
    INTERNAL_CONFLICT = 15
    EXTERNAL_CONFLICT = 16
    FLAW = 17
    LINEAR_PROGRESSION = 18

    SKILL_SET = 19
    TICKING_CLOCK = 20
    WAR = 21
    WAR_MENTAL_EFFECT = 22
    MONSTER = 23
    CONFINED_SPACE = 24
    CRIME = 25
    SLEUTH = 26
    AUTHORITY = 27
    MACGUFFIN = 28
    SCHEME = 29
    CRIME_CLOCK = 30

    SELF_DISCOVERY = 31
    LOSS_OF_INNOCENCE = 32
    MATURITY = 33
    FIRST_LOVE = 34
    MENTOR = 35

    DYNAMIC_ELEMENTS = 36

    def display_name(self) -> str:
        if self == PlotPrincipleType.WAR_MENTAL_EFFECT:
            return 'Mental effect'
        elif self == PlotPrincipleType.CRIME_CLOCK:
            return 'Time pressure'
        elif self == PlotPrincipleType.MACGUFFIN:
            return 'MacGuffin'
        elif self == PlotPrincipleType.SELF_DISCOVERY:
            return 'Self-discovery'
        return self.name.lower().capitalize().replace('_', ' ')


@dataclass
class PlotPrinciple:
    type: PlotPrincipleType
    value: Any = None
    is_set: bool = False


class DynamicPlotPrincipleType(Enum):
    TWIST = 'twist'
    TURN = 'turn'
    DANGER = 'danger'
    WONDER = 'wonder'
    MONSTER = 'monster'
    ALLY = 'ally'
    ENEMY = 'enemy'
    NEUTRAL = 'neutral'
    SUSPECT = 'suspect'
    CREW_MEMBER = 'crew'

    DESCRIPTION = 'DESCRIPTION'
    MOTIVE = 'motive'
    CLUES = 'clues'
    RED_HERRING = 'red_herring'
    ALIBI = 'alibi'
    SECRETS = 'secrets'
    RED_FLAGS = 'red_flags'
    CRIMINAL_RECORD = 'criminal_record'
    EVIDENCE_AGAINST = 'evidence_against'
    EVIDENCE_IN_FAVOR = 'evidence_in_favor'
    BEHAVIOR_DURING_INVESTIGATION = 'behavior_during_investigation'

    SKILL_SET = 'skill_set'
    MOTIVATION = 'motivation'
    CONTRIBUTION = 'contribution'
    WEAK_LINK = 'weak_link'
    HIDDEN_AGENDA = 'hidden_agenda'
    NICKNAME = 'nickname'

    def display_name(self) -> str:
        return self.name.lower().capitalize().replace('_', ' ')

    def icon(self) -> str:
        if self == DynamicPlotPrincipleType.TWIST:
            return 'ph.shuffle-bold'
        elif self == DynamicPlotPrincipleType.TURN:
            return 'mdi.sign-direction'
        elif self == DynamicPlotPrincipleType.DANGER:
            return 'ei.fire'
        elif self == DynamicPlotPrincipleType.WONDER:
            return 'mdi.star-four-points-outline'
        elif self == DynamicPlotPrincipleType.MONSTER:
            return 'ri.ghost-2-fill'
        elif self == DynamicPlotPrincipleType.ALLY:
            return 'fa5s.thumbs-up'
        elif self == DynamicPlotPrincipleType.ENEMY:
            return 'fa5s.thumbs-down'
        elif self == DynamicPlotPrincipleType.NEUTRAL:
            return 'fa5.hand-rock'
        elif self == DynamicPlotPrincipleType.SUSPECT:
            return 'ri.criminal-fill'
        elif self == DynamicPlotPrincipleType.CREW_MEMBER:
            return 'mdi.robber'
        elif self == DynamicPlotPrincipleType.DESCRIPTION:
            return 'mdi6.human-male-height-variant'
        elif self == DynamicPlotPrincipleType.MOTIVE:
            return 'fa5s.fist-raised'
        elif self == DynamicPlotPrincipleType.CLUES:
            return 'mdi.fingerprint'
        elif self == DynamicPlotPrincipleType.RED_HERRING:
            return 'fa5s.fish'
        elif self == DynamicPlotPrincipleType.ALIBI:
            return 'fa5.calendar-check'
        elif self == DynamicPlotPrincipleType.SECRETS:
            return 'ei.lock-alt'
        elif self == DynamicPlotPrincipleType.RED_FLAGS:
            return 'fa5s.flag'
        elif self == DynamicPlotPrincipleType.CRIMINAL_RECORD:
            return 'fa5s.gavel'
        elif self == DynamicPlotPrincipleType.EVIDENCE_AGAINST:
            return 'ri.criminal-fill'
        elif self == DynamicPlotPrincipleType.EVIDENCE_IN_FAVOR:
            return 'fa5s.dove'
        elif self == DynamicPlotPrincipleType.BEHAVIOR_DURING_INVESTIGATION:
            return 'mdi.head-dots-horizontal-outline'

        elif self == DynamicPlotPrincipleType.SKILL_SET:
            return "fa5s.tools"
        elif self == DynamicPlotPrincipleType.MOTIVATION:
            return "fa5s.hand-holding-usd"
        elif self == DynamicPlotPrincipleType.CONTRIBUTION:
            return "ph.puzzle-piece"
        elif self == DynamicPlotPrincipleType.WEAK_LINK:
            return "mdi6.target-account"
        elif self == DynamicPlotPrincipleType.HIDDEN_AGENDA:
            return "fa5s.user-secret"
        elif self == DynamicPlotPrincipleType.NICKNAME:
            return "mdi.badge-account-outline"

    def color(self) -> str:
        if self == DynamicPlotPrincipleType.TWIST:
            return "#f20089"
        elif self == DynamicPlotPrincipleType.TURN:
            return "#8338ec"
        elif self == DynamicPlotPrincipleType.DANGER:
            return '#f4a261'
        elif self == DynamicPlotPrincipleType.WONDER:
            return "#40916c"
        elif self == DynamicPlotPrincipleType.MONSTER:
            return antagonist_role.icon_color
        elif self == DynamicPlotPrincipleType.ALLY:
            return '#266dd3'
        elif self == DynamicPlotPrincipleType.ENEMY:
            return '#9e1946'
        elif self == DynamicPlotPrincipleType.NEUTRAL:
            return 'grey'
        elif self == DynamicPlotPrincipleType.SUSPECT:
            return '#9e2a2b'
        elif self == DynamicPlotPrincipleType.CREW_MEMBER:
            return '#0077b6'

        elif self == DynamicPlotPrincipleType.RED_HERRING:
            return '#d33f49'
        elif self == DynamicPlotPrincipleType.RED_FLAGS:
            return '#9e1946'

        return 'black'

    def description(self) -> str:
        if self == DynamicPlotPrincipleType.TWIST:
            return "Brings an unexpected development of the story by defying readers expectations"
        elif self == DynamicPlotPrincipleType.TURN:
            return "Delivers a shift in the story's direction"
        elif self == DynamicPlotPrincipleType.DANGER:
            return "Moments of heightened danger, either physical or emotional"
        elif self == DynamicPlotPrincipleType.ALLY:
            return "A character forming alliance with the storyline's focal character"
        elif self == DynamicPlotPrincipleType.ENEMY:
            return "An adversary character who opposes the storyline's focal character"
        elif self == DynamicPlotPrincipleType.NEUTRAL:
            return "A character who remains neutral towards the storyline's focal character"

        elif self == DynamicPlotPrincipleType.DESCRIPTION:
            return "The suspect's physical appearance and distinguishing features"
        elif self == DynamicPlotPrincipleType.MOTIVE:
            return "The suspects underlying or speculated motivation to commit the crime"
        elif self == DynamicPlotPrincipleType.CLUES:
            return "Information or evidence that brings the suspect into the investigation"
        elif self == DynamicPlotPrincipleType.RED_HERRING:
            return "A misleading clue that diverts the investigation"
        elif self == DynamicPlotPrincipleType.ALIBI:
            return "Does the suspect have any alibi when the crime occurred?"
        elif self == DynamicPlotPrincipleType.SECRETS:
            return "Secrets from the suspect's life that may be relevant to the investigation"
        elif self == DynamicPlotPrincipleType.RED_FLAGS:
            return "Any behavior or sign that raises suspicion about the suspect"
        elif self == DynamicPlotPrincipleType.CRIMINAL_RECORD:
            return "Does the suspect have a criminal record?"
        elif self == DynamicPlotPrincipleType.EVIDENCE_AGAINST:
            return "Evidence that strongly suggests the suspect's involvement in the crime"
        elif self == DynamicPlotPrincipleType.EVIDENCE_IN_FAVOR:
            return "Any information that supports the suspect's innocence"
        elif self == DynamicPlotPrincipleType.BEHAVIOR_DURING_INVESTIGATION:
            return "How does the suspect behave during the investigation?"

        elif self == DynamicPlotPrincipleType.SKILL_SET:
            return "What's the member's unique skill set that can help the caper?"
        elif self == DynamicPlotPrincipleType.MOTIVATION:
            return "The member's unique motivation for participating"
        elif self == DynamicPlotPrincipleType.CONTRIBUTION:
            return "How does the member help the team?"
        elif self == DynamicPlotPrincipleType.WEAK_LINK:
            return "Is the member a weak link or a liability?"
        elif self == DynamicPlotPrincipleType.HIDDEN_AGENDA:
            return "Is there a hidden agenda of the member behind being part of the team?"
        elif self == DynamicPlotPrincipleType.NICKNAME:
            return "Any nicknames the member is referred to"

        return ""

    def placeholder(self) -> str:
        if self == DynamicPlotPrincipleType.TWIST:
            return "How the story develops unexpectedly by defying readers expectations"
        elif self == DynamicPlotPrincipleType.TURN:
            return "How does the story's direction shift?"
        elif self == DynamicPlotPrincipleType.DANGER:
            return "Moments of heightened danger, either physical or emotional"
        elif self == DynamicPlotPrincipleType.WONDER:
            return "Describe an element of wonder that make your fantastical world captivating"
        elif self == DynamicPlotPrincipleType.MONSTER:
            return "How the monster's power evolved or revealed continuously"
        elif self == DynamicPlotPrincipleType.ALLY:
            return "Describe who and how forms an alliance with the character"
        elif self == DynamicPlotPrincipleType.ENEMY:
            return "Describe who and how opposes the focal character"
        elif self == DynamicPlotPrincipleType.NEUTRAL:
            return "Describe who and why remains neutral towards the focal character"

        elif self == DynamicPlotPrincipleType.DESCRIPTION:
            return "Describe the suspect's physical appearance or any distinguishing features"
        elif self == DynamicPlotPrincipleType.MOTIVE:
            return "Describe the suspect's potential motivation to commit the crime"
        elif self == DynamicPlotPrincipleType.CLUES:
            return "Describe what clues raise suspicion about the suspect"
        elif self == DynamicPlotPrincipleType.RED_HERRING:
            return "What misleading clues distract the investigation and divert it into a wrong direction"
        elif self == DynamicPlotPrincipleType.ALIBI:
            return "Describe any potential alibi"
        elif self == DynamicPlotPrincipleType.SECRETS:
            return "Describe the secrets the suspect may have"
        elif self == DynamicPlotPrincipleType.RED_FLAGS:
            return "Describe any behavior or sign that raises suspicion about the suspect"
        elif self == DynamicPlotPrincipleType.CRIMINAL_RECORD:
            return "Describe the suspect's criminal record, if there's any"
        elif self == DynamicPlotPrincipleType.EVIDENCE_AGAINST:
            return "Describe any evidence that strongly suggests the suspect is guilty"
        elif self == DynamicPlotPrincipleType.EVIDENCE_IN_FAVOR:
            return "Describe any significant information that supports the suspect's innocence"
        elif self == DynamicPlotPrincipleType.BEHAVIOR_DURING_INVESTIGATION:
            return "Describe how the suspect behaves during the investigation"

        elif self == DynamicPlotPrincipleType.SKILL_SET:
            return "Describe the member's unique skill set that helps the scheme"
        elif self == DynamicPlotPrincipleType.MOTIVATION:
            return "Describe the member's motivation for being part of the heist"
        elif self == DynamicPlotPrincipleType.CONTRIBUTION:
            return "Describe how the member helps the scheme"
        elif self == DynamicPlotPrincipleType.WEAK_LINK:
            return "Describe how the member is considered a weak link"
        elif self == DynamicPlotPrincipleType.HIDDEN_AGENDA:
            return "Describe the member's hidden agenda behind participating in the scheme"
        elif self == DynamicPlotPrincipleType.NICKNAME:
            return "Describe member's nicknames, if there's any"

        return ""


@dataclass
class DynamicPlotPrinciple(OutlineItem):
    type: DynamicPlotPrincipleType = DynamicPlotPrincipleType.TWIST
    elements: List['DynamicPlotPrinciple'] = field(default_factory=list)
    character_id: str = ''
    node: Optional['Node'] = field(default=None, metadata=config(exclude=exclude_if_empty))


class DynamicPlotPrincipleGroupType(Enum):
    ESCALATION = 0
    ALLIES_AND_ENEMIES = 1
    SUSPECTS = 2
    ELEMENTS_OF_WONDER = 3
    EVOLUTION_OF_THE_MONSTER = 4
    CAST = 5
    TIMELINE = 6
    RELATIONSHIP = 7

    def display_name(self) -> str:
        return self.name.lower().capitalize().replace('_', ' ')

    def icon(self) -> str:
        if self == DynamicPlotPrincipleGroupType.ESCALATION:
            return 'ph.shuffle-bold'
        elif self == DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES:
            return 'fa5s.thumbs-up'
        elif self == DynamicPlotPrincipleGroupType.SUSPECTS:
            return 'ri.criminal-fill'
        elif self == DynamicPlotPrincipleGroupType.ELEMENTS_OF_WONDER:
            return 'ph.globe-stand-bold'
        elif self == DynamicPlotPrincipleGroupType.EVOLUTION_OF_THE_MONSTER:
            return 'ri.ghost-2-fill'
        elif self == DynamicPlotPrincipleGroupType.CAST:
            return 'mdi.robber'
        elif self == DynamicPlotPrincipleGroupType.TIMELINE:
            return 'mdi.timeline-text-outline'
        elif self == DynamicPlotPrincipleGroupType.RELATIONSHIP:
            return 'fa5s.people-arrows'

    def color(self) -> str:
        if self == DynamicPlotPrincipleGroupType.ESCALATION:
            return '#8338ec'
        elif self == DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES:
            return '#9e1946'
        elif self == DynamicPlotPrincipleGroupType.SUSPECTS:
            return '#9e2a2b'
        elif self == DynamicPlotPrincipleGroupType.ELEMENTS_OF_WONDER:
            return '#40916c'
        elif self == DynamicPlotPrincipleGroupType.EVOLUTION_OF_THE_MONSTER:
            return antagonist_role.icon_color
        elif self == DynamicPlotPrincipleGroupType.CAST:
            return '#0077b6'

        return 'black'

    def description(self) -> str:
        if self == DynamicPlotPrincipleGroupType.ESCALATION:
            return 'Narrative turns, unexpected twists, and dangerous moments that add intrigue and excitement to the storyline'
        elif self == DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES:
            return "Characters forming alliances and adversaries around the focal character"
        elif self == DynamicPlotPrincipleGroupType.SUSPECTS:
            return "Suspects, clues, red herrings that add depth to a mystery"
        elif self == DynamicPlotPrincipleGroupType.ELEMENTS_OF_WONDER:
            return "Elements of wonder and awe that make a fantastical world captivating"
        elif self == DynamicPlotPrincipleGroupType.EVOLUTION_OF_THE_MONSTER:
            return "The continuous evolution or revelation of the monster's power, unfolding dynamically throughout the narrative"
        elif self == DynamicPlotPrincipleGroupType.CAST:
            return "The ensemble of characters involved in a caper, each with unique skills and contributions"
        elif self == DynamicPlotPrincipleGroupType.TIMELINE:
            return "Most significant events related to this storyline"
        elif self == DynamicPlotPrincipleGroupType.RELATIONSHIP:
            return "A dynamic relationship and its evolution between two characters"


@dataclass
class DynamicPlotPrincipleGroup:
    type: DynamicPlotPrincipleGroupType
    principles: List[DynamicPlotPrinciple] = field(default_factory=list)


class PlotEventType(Enum):
    PROGRESS = 0
    SETBACK = 2
    CRISIS = 3
    COST = 4
    TOOL = 5


@dataclass
class PlotEvent:
    text: str
    type: PlotEventType


# must add to the subclass:
#    character_id: Optional[uuid.UUID] = None
#    def __post_init__(self):
#        self._character: Optional[Character] = None
class CharacterBased(ABC):
    def set_character(self, character: Optional[Character]):
        if character is None:
            self.reset_character()
        else:
            self.character_id = character.id
            self._character = character

    def reset_character(self):
        self.character_id = None
        self._character = None

    def character(self, novel: 'Novel') -> Optional[Character]:
        if not self.character_id:
            return None
        if not self._character:
            for c in novel.characters:
                if c.id == self.character_id:
                    self._character = c
                    break

        return self._character


class SceneBased(ABC):

    def set_scene(self, scene: Optional['Scene']):
        if scene is None:
            self.scene_id = None
        else:
            self.scene_id = scene.id

    def scene(self, novel: 'Novel') -> Optional['Scene']:
        if not self.scene_id:
            return None
        if not self._scene:
            for s in novel.scenes:
                if s.id == self.scene_id:
                    return s


def default_plot_value() -> PlotValue:
    return PlotValue('Progress', icon='fa5s.chart-line')


class StorylineLinkType(Enum):
    Connection = auto()
    Catalyst = auto()
    Impact = auto()
    Contrast = auto()
    Reflect_character = auto()
    Reflect_plot = auto()
    Reveal = auto()
    Resolve = auto()
    Compete = auto()

    def display_name(self) -> str:
        if self == StorylineLinkType.Reflect_character:
            return 'Reflect character'
        elif self == StorylineLinkType.Reflect_plot:
            return 'Reflect plot'

        return self.name

    def icon(self) -> str:
        if self == StorylineLinkType.Catalyst:
            return 'fa5s.vial'
        elif self == StorylineLinkType.Impact:
            return 'mdi.motion-outline'
        elif self == StorylineLinkType.Contrast:
            return 'ei.adjust'
        elif self == StorylineLinkType.Reflect_character:
            return 'msc.mirror'
        elif self == StorylineLinkType.Reflect_plot:
            return 'msc.mirror'
        elif self == StorylineLinkType.Resolve:
            return 'mdi.bullseye-arrow'
        # elif self == StorylineLinkType.Parallel:
        #     return 'fa5s.grip-lines'
        elif self == StorylineLinkType.Compete:
            return 'ph.arrows-in-line-horizontal'
        # elif self == StorylineLinkType.Complicate:
        #     return 'mdi.sword-cross'
        # elif self == StorylineLinkType.Converge:
        #     return 'ri.git-pull-request-fill'
        return 'fa5s.link'

    def desc(self) -> str:
        if self == StorylineLinkType.Catalyst:
            return 'A storyline triggers the events in an other storyline'
        elif self == StorylineLinkType.Impact:
            return 'A storyline impacts or influences the events in an other storyline'
        elif self == StorylineLinkType.Contrast:
            return 'The storylines contrast each other in any way, e.g.,theme, tone, or pacing'
        elif self == StorylineLinkType.Reflect_character:
            return "The relationship plot reflects the character's changes"
        elif self == StorylineLinkType.Reflect_plot:
            return "The relationship plot reflects larger plot themes of conflicts through character interactions"
        elif self == StorylineLinkType.Reveal:
            return "The character's changes reveal the true nature of a relationship plot"
        elif self == StorylineLinkType.Resolve:
            return "Only through the character's changes the plot can be resolved"
        elif self == StorylineLinkType.Compete:
            return 'Two storylines compete against each other, often for a common goal'
        return 'How does the storyline connect to the other one?'

    def placeholder(self) -> str:
        if self == StorylineLinkType.Catalyst:
            return ""
        elif self == StorylineLinkType.Impact:
            return ""
        elif self == StorylineLinkType.Contrast:
            return ""
        elif self == StorylineLinkType.Reflect_character:
            return ""
        elif self == StorylineLinkType.Reflect_plot:
            return ""
        elif self == StorylineLinkType.Resolve:
            return ""
        elif self == StorylineLinkType.Compete:
            return ""
        return 'How does the storyline connect to the other one?'


@dataclass
class StorylineLink:
    source_id: uuid.UUID
    target_id: uuid.UUID
    type: StorylineLinkType
    text: str = ''


class RelationshipDynamicsType(Enum):
    SEPARATE = 0
    SHARED = 1


class RelationshipDynamicsDataType(Enum):
    TEXT = 0
    RELATION = 1


class ConnectorType(Enum):
    LEFT_TO_RIGHT = 0
    RIGHT_TO_LEFT = 1
    BIDIRECTIONAL = 2


@dataclass
class RelationshipDynamicsElement(BackstoryEvent):
    source: str = field(default='', metadata=config(exclude=exclude_if_empty))
    target: str = field(default='', metadata=config(exclude=exclude_if_empty))
    rel_type: RelationshipDynamicsType = RelationshipDynamicsType.SEPARATE
    data_type: RelationshipDynamicsDataType = RelationshipDynamicsDataType.TEXT
    connector_type: Optional[ConnectorType] = None


@dataclass
class RelationshipDynamics:
    source_characters: List[uuid.UUID] = field(default_factory=list)
    target_characters: List[uuid.UUID] = field(default_factory=list)
    elements: List[RelationshipDynamicsElement] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))


@dataclass
class Plot(SelectionItem, CharacterBased):
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    plot_type: PlotType = PlotType.Main
    values: List[PlotValue] = field(default_factory=list)
    character_id: Optional[uuid.UUID] = None
    relation_character_id: Optional[uuid.UUID] = None
    question: str = ''
    principles: List[PlotPrinciple] = field(default_factory=list)
    dynamic_principles: List[DynamicPlotPrincipleGroup] = field(default_factory=list)
    has_progression: bool = False
    timeline: List[BackstoryEvent] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    has_relationship: bool = False
    relationship: Optional[RelationshipDynamics] = None
    has_escalation: bool = False
    escalation: Optional[DynamicPlotPrincipleGroup] = None
    has_allies: bool = False
    allies: Optional[DynamicPlotPrincipleGroup] = None
    has_suspects: bool = False
    suspects: Optional[DynamicPlotPrincipleGroup] = None
    has_cast: bool = False
    cast: Optional[DynamicPlotPrincipleGroup] = None
    has_villain: bool = False
    villain: List[BackstoryEvent] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    has_dynamic_principles: bool = True
    has_thematic_relevance: bool = False
    events: List[PlotEvent] = field(default_factory=list)
    default_value: PlotValue = field(default_factory=default_plot_value)
    default_value_enabled: bool = True
    progression: List[PlotProgressionItem] = field(default_factory=list)
    links: List[StorylineLink] = field(default_factory=list)

    def __post_init__(self):
        self._character: Optional[Character] = None
        self._relation_character: Optional[Character] = None

    def relation_character(self, novel: 'Novel') -> Optional[Character]:
        if not self.relation_character_id:
            return None
        if not self._relation_character:
            for c in novel.characters:
                if c.id == self.relation_character_id:
                    self._relation_character = c
                    break

        return self._relation_character

    def set_relation_character(self, character: Optional[Character]):
        if character is None:
            self.reset_character()
        else:
            self.relation_character_id = character.id
            self._relation_character = character

    def reset_relation_character(self):
        self.relation_character_id = None
        self._relation_character = None

    @overrides
    def __eq__(self, other: 'Plot'):
        if isinstance(other, Plot):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


class ConflictType(Enum):
    PERSONAL = 0
    COMMUNITY = 1
    MILIEU = 2
    GLOBAL = 3
    INTERNAL = 4

    def display_name(self) -> str:
        return self.name.lower().capitalize()

    def icon(self) -> str:
        if self == ConflictType.PERSONAL:
            return 'fa5s.user'
        elif self == ConflictType.COMMUNITY:
            return 'ei.group-alt'
        elif self == ConflictType.INTERNAL:
            return 'mdi.mirror'
        elif self == ConflictType.GLOBAL:
            return 'fa5s.globe'
        elif self == ConflictType.MILIEU:
            return 'mdi.globe-model'

    def color(self) -> str:
        if self == ConflictType.INTERNAL:
            return '#843b4d'
        if self == ConflictType.GLOBAL:
            return '#513E2B'
        if self == ConflictType.MILIEU:
            return '#787236'
        if self == ConflictType.COMMUNITY:
            return '#705089'
        return '#e57c04'

    def placeholder(self) -> str:
        if self == ConflictType.COMMUNITY:
            return "Conflict that affects a community the character is part of"
        if self == ConflictType.GLOBAL:
            return "Conflict that globally impacts a broader population"
        if self == ConflictType.INTERNAL:
            return "Character struggles with their own desires and beliefs"
        if self == ConflictType.MILIEU:
            return "Conflict against the environment or society"
        return "Conflict that personally affects the character"


class Tier(Enum):
    S = 's'
    A = 'a'
    B = 'b'
    C = 'c'
    D = 'd'

    def intensity(self) -> int:
        if self == Tier.D:
            return 1
        if self == Tier.C:
            return 2
        if self == Tier.B:
            return 3
        if self == Tier.A:
            return 4
        if self == Tier.S:
            return 5


@dataclass
class Conflict(SelectionItem):
    scope: ConflictType = ConflictType.PERSONAL
    character_id: Optional[uuid.UUID] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    desc: str = field(default='', metadata=config(exclude=exclude_if_empty))
    tier: Optional[Tier] = field(default=None, metadata=config(exclude=exclude_if_empty))

    @overrides
    def __eq__(self, other: 'Conflict'):
        if isinstance(other, Conflict):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))

    def display_icon(self) -> str:
        if self.scope == ConflictType.PERSONAL:
            return 'mdi.sword-cross'
        else:
            return self.scope.icon()

    def display_name(self) -> str:
        if self.text:
            return self.text
        elif self.scope == ConflictType.PERSONAL:
            return 'Conflict'
        else:
            return f'{self.scope.display_name()} conflict'

    def display_color(self) -> str:
        return self.scope.color()


@dataclass
class Goal(SelectionItem):
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    description: str = ''

    @overrides
    def __eq__(self, other: 'Goal'):
        if isinstance(other, Goal):
            return self.id == other.id
        return False

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
    charge: int = 0
    values: List[ScenePlotValueCharge] = field(default_factory=list)


@dataclass
class ScenePlotReference:
    plot: Plot
    data: ScenePlotReferenceData = field(default_factory=ScenePlotReferenceData)


class SceneStructureItemType(Enum):
    ACTION = 0
    CONFLICT = 1
    CLIMAX = 2
    REACTION = 3
    DILEMMA = 4
    DECISION = 5
    BEAT = 6
    INCITING_INCIDENT = 7
    RISING_ACTION = 8
    CHOICE = 9
    TICKING_CLOCK = 10
    HOOK = 11
    EXPOSITION = 12
    TURN = 13
    MYSTERY = 14
    REVELATION = 15
    SETUP = 16
    EMOTION = 17
    SUMMARY = 18
    PROGRESS = 19
    SETBACK = 20
    RESOLUTION = 21
    BUILDUP = 22
    DISTURBANCE = 23
    FALSE_VICTORY = 24


class SceneOutcome(Enum):
    DISASTER = 0
    RESOLUTION = 1
    TRADE_OFF = 2
    MOTION = 3

    @staticmethod
    def to_str(outcome: 'SceneOutcome') -> str:
        if outcome == SceneOutcome.TRADE_OFF:
            return 'Trade-off outcome'
        elif outcome == SceneOutcome.MOTION:
            return 'Set into motion'
        return outcome.name.lower().capitalize() + ' outcome'


@dataclass
class SceneStructureItem(OutlineItem):
    type: SceneStructureItemType = SceneStructureItemType.BEAT
    emotion: str = field(default='', metadata=config(exclude=exclude_if_empty))
    meta: Dict[str, Any] = field(default_factory=dict, metadata=config(exclude=exclude_if_empty))

    @property
    def outcome(self) -> Optional[SceneOutcome]:
        if 'outcome' in self.meta.keys():
            return SceneOutcome(self.meta['outcome'])

    @outcome.setter
    def outcome(self, value: SceneOutcome):
        self.meta['outcome'] = value.value


class Motivation(Enum):
    PHYSIOLOGICAL = 0
    SAFETY = 1
    BELONGING = 2
    ESTEEM = 3
    SELF_ACTUALIZATION = 4
    SELF_TRANSCENDENCE = 5

    def display_name(self) -> str:
        if self == Motivation.PHYSIOLOGICAL:
            return 'Physiological needs'
        elif self == Motivation.SAFETY:
            return 'Security and safety'
        elif self == Motivation.BELONGING:
            return 'Belonging and love'
        elif self == Motivation.ESTEEM:
            return 'Esteem and success'
        else:
            return self.name.lower().replace('_', '-').capitalize()

    def icon(self) -> str:
        if self == Motivation.PHYSIOLOGICAL:
            return 'mdi.water'
        elif self == Motivation.SAFETY:
            return 'mdi.shield-half-full'
        elif self == Motivation.BELONGING:
            return 'fa5s.hand-holding-heart'
        elif self == Motivation.ESTEEM:
            return 'fa5s.award'
        elif self == Motivation.SELF_ACTUALIZATION:
            return 'mdi.yoga'
        elif self == Motivation.SELF_TRANSCENDENCE:
            return 'mdi6.meditation'

    def color(self) -> str:
        if self == Motivation.PHYSIOLOGICAL:
            return '#023e8a'
        elif self == Motivation.SAFETY:
            return '#8900f2'
        elif self == Motivation.BELONGING:
            return '#d00000'
        elif self == Motivation.ESTEEM:
            return '#00b4d8'
        elif self == Motivation.SELF_ACTUALIZATION:
            return '#52b788'
        elif self == Motivation.SELF_TRANSCENDENCE:
            return '#c38e70'


@dataclass
class GoalReference:
    character_goal_id: uuid.UUID
    message: str = ''
    stakes: Dict[int, int] = field(default_factory=dict, metadata=config(exclude=exclude_if_empty))

    def goal(self, character: Character) -> CharacterGoal:
        for goal_ in character.flatten_goals():
            if goal_.id == self.character_goal_id:
                return goal_


@dataclass
class TagReference:
    tag_id: uuid.UUID
    message: str = ''


@dataclass
class CharacterAgencyChanges:
    initial: Optional['StoryElement'] = None
    transition: Optional['StoryElement'] = None
    final: Optional['StoryElement'] = None


@dataclass
class CharacterAgency:
    character_id: Optional[uuid.UUID] = None
    conflicts: List[Conflict] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    motivations: Dict[int, int] = field(default_factory=dict, metadata=config(exclude=exclude_if_empty))
    intensity: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    changes: List[CharacterAgencyChanges] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    elements: List['StoryElement'] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))


@dataclass
class SceneStoryBeat:
    structure_id: uuid.UUID
    beat_id: uuid.UUID
    character_id: Optional[uuid.UUID] = None

    def beat(self, structure: 'StoryStructure') -> Optional[StoryBeat]:
        if self.structure_id == structure.id and self.character_id == structure.character_id:
            return next((b for b in structure.beats if b.id == self.beat_id), None)

    @staticmethod
    def of(structure: 'StoryStructure', beat: StoryBeat) -> 'SceneStoryBeat':
        return SceneStoryBeat(structure.id, beat.id, structure.character_id)


class ReaderPosition(Enum):
    SUPERIOR = 0
    INFERIOR = 1


class InformationAcquisition(Enum):
    DISCOVERY = 0
    REVELATION = 1


@dataclass
class SceneDrive:
    worldbuilding: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    tension: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    new_information: Optional[InformationAcquisition] = field(default=None, metadata=config(exclude=exclude_if_empty))
    reader_position: Optional[ReaderPosition] = field(default=None, metadata=config(exclude=exclude_if_empty))
    deus_ex_machina: bool = field(default=False, metadata=config(exclude=exclude_if_false))


class ScenePurposeType(Enum):
    Story = 'story'
    Reaction = 'reaction'
    Character = 'character'
    Emotion = 'emotion'
    Setup = 'setup'
    Exposition = 'exposition'
    Other = 'other'


@dataclass
class ScenePurpose:
    type: ScenePurposeType
    display_name: str
    keywords: List[str] = field(default_factory=list)
    include: List[ScenePurposeType] = field(default_factory=list)
    help_include: str = ''
    pacing: str = ''


advance_story_scene_purpose = ScenePurpose(ScenePurposeType.Story, 'Drive',
                                           keywords=['motion', 'goal', 'conflict', 'narrative drive', 'advancing story',
                                                     'action', 'outcome', 'tension', 'revelation',
                                                     'mystery', 'catalyst', 'crisis', 'cause & effect'],
                                           include=[ScenePurposeType.Character, ScenePurposeType.Emotion,
                                                    ScenePurposeType.Setup],
                                           pacing='fast-medium')
reaction_story_scene_purpose = ScenePurpose(ScenePurposeType.Reaction, 'Aftermath',
                                            keywords=['reaction', 'reflection', 'dilemma', 'decision', 'introspection',
                                                      'analysis',
                                                      'new goal'],
                                            include=[ScenePurposeType.Character, ScenePurposeType.Emotion],
                                            pacing='medium-slow')
character_story_scene_purpose = ScenePurpose(ScenePurposeType.Character, 'Character insight',
                                             keywords=['characterization', 'introspection', 'backstory',
                                                       'internal conflict', 'relations', 'character change'],
                                             include=[ScenePurposeType.Emotion])
emotion_story_scene_purpose = ScenePurpose(ScenePurposeType.Emotion, 'Resonance',
                                           keywords=['mood', 'atmosphere', 'resonance', 'emotion', 'evocative tone',
                                                     'evocative imagery', 'ambience',
                                                     'thematic resonance'])
setup_story_scene_purpose = ScenePurpose(ScenePurposeType.Setup, 'Setup',
                                         keywords=['plant', 'foreshadowing', 'setup'])
exposition_story_scene_purpose = ScenePurpose(ScenePurposeType.Exposition, 'Exposition',
                                              keywords=['introduction', 'description', 'information', 'transition'])

scene_purposes: Dict[ScenePurposeType, ScenePurpose] = {
    ScenePurposeType.Story: advance_story_scene_purpose,
    ScenePurposeType.Reaction: reaction_story_scene_purpose,
    ScenePurposeType.Character: character_story_scene_purpose,
    ScenePurposeType.Emotion: emotion_story_scene_purpose,
    ScenePurposeType.Setup: setup_story_scene_purpose,
    ScenePurposeType.Exposition: exposition_story_scene_purpose,
}


class StoryElementType(Enum):
    Plot = 'plot'
    Character = 'character'
    Mystery = 'mystery'
    Revelation = 'revelation'
    Resonance = 'resonance'
    Reaction = 'reaction'
    Reflection = 'reflection'
    Repercussion = 'repercussion'
    Setup = 'setup'
    Information = 'information'
    Arc = 'arc'
    Outcome = 'outcome'
    Consequences = 'consequences'
    Character_state = 'character_state'
    Character_internal_state = 'character_internal_state'
    Character_state_change = 'character_state_change'
    Character_internal_state_change = 'character_internal_state_change'

    Connector = 'connector'
    H_line = 'h_line'
    V_line = 'v_line'

    Expectation = 'expectation'
    Realization = 'realization'
    Goal = 'goal'
    Motivation = 'motivation'
    Conflict = 'conflict'
    Internal_conflict = 'internal_conflict'
    Dilemma = 'dilemma'
    Choice = 'choice'
    Impact = 'impact'
    Responsibility = 'responsibility'
    Decision = 'decision'
    Emotion = 'emotion'
    Emotion_change = 'emotion_change'
    Relationship = 'relationship'
    Agency = 'agency'
    Initiative = 'initiative'
    Catalyst = 'catalyst'
    Action = 'action'
    Plan_change = 'plan_change'
    Collaboration = 'collaboration'
    Subtext = 'subtext'

    Event = 'event'
    Effect = 'effect'
    Delayed_effect = 'delayed_effect'
    Thematic_effect = 'thematic_effect'

    def displayed_name(self) -> str:
        if self == StoryElementType.Character_state:
            return 'External state'
        if self == StoryElementType.Character_internal_state:
            return 'Internal state'
        if self == StoryElementType.Character_state_change:
            return 'External change'
        if self == StoryElementType.Character_internal_state_change:
            return 'Internal change'
        return self.value.capitalize().replace('_', ' ')

    def icon(self) -> str:
        if self == StoryElementType.Goal:
            return 'mdi.target'
        elif self == StoryElementType.Conflict:
            return 'mdi.sword-cross'
        elif self == StoryElementType.Internal_conflict:
            return 'mdi.mirror'
        elif self == StoryElementType.Dilemma:
            return 'fa5s.map-signs'
        elif self == StoryElementType.Choice:
            return 'mdi.arrow-decision-outline'
        elif self == StoryElementType.Catalyst:
            return 'fa5s.vial'
        elif self == StoryElementType.Action:
            return 'mdi.run-fast'
        elif self == StoryElementType.Impact:
            return 'mdi.motion'
        elif self == StoryElementType.Outcome:
            return 'fa5s.bomb'
        elif self == StoryElementType.Character_state:
            return 'fa5s.user-circle'
        elif self == StoryElementType.Character_internal_state:
            return 'mdi6.head-dots-horizontal-outline'
        elif self == StoryElementType.Character_state_change:
            return 'ph.user-circle-gear-fill'
        elif self == StoryElementType.Character_internal_state_change:
            return 'mdi.head-flash-outline'
        elif self == StoryElementType.Expectation:
            return 'mdi.sign-direction'
        elif self == StoryElementType.Realization:
            return 'mdi.routes'
        elif self == StoryElementType.Decision:
            return 'fa5.lightbulb'
        elif self == StoryElementType.Motivation:
            return 'fa5s.fist-raised'
        elif self == StoryElementType.Emotion:
            return 'mdi.emoticon-neutral-outline'
        elif self == StoryElementType.Emotion_change:
            return 'mdi.emoticon-neutral-outline'
        elif self == StoryElementType.Relationship:
            return 'fa5s.people-arrows'

    def placeholder(self) -> str:
        if self == StoryElementType.Goal:
            return "What's the character's goal in this scene?"
        elif self == StoryElementType.Conflict:
            return "What kind of conflict does the character have to face?"
        elif self == StoryElementType.Internal_conflict:
            return "What internal struggles does the character have to face?"
        elif self == StoryElementType.Outcome:
            return "What's the scene's outcome for the character?"
        elif self == StoryElementType.Character_state:
            return "What's the character's external circumstances or situation?"
        elif self == StoryElementType.Character_internal_state:
            return "What's the character's internal state, mentally or psychologically?"
        elif self == StoryElementType.Character_state_change:
            return "How does the character's external circumstances change?"
        elif self == StoryElementType.Character_internal_state_change:
            return "How does the character's internal state change?"
        elif self == StoryElementType.Expectation:
            return "What does the character anticipate to happen?"
        elif self == StoryElementType.Realization:
            return "What did actually happen that upended expectations?"
        elif self == StoryElementType.Catalyst:
            return "What disrupts the character's life and forces them to act?"
        elif self == StoryElementType.Dilemma:
            return "What difficult choice does the character have to face?"
        elif self == StoryElementType.Choice:
            return "An impossible choice between two equally good or bad outcomes"
        elif self == StoryElementType.Action:
            return "What steps or decisions does the character make?"
        elif self == StoryElementType.Impact:
            return "What impact do the character’s actions have on the story?"
        elif self == StoryElementType.Decision:
            return "What decision does the character have to make?"
        elif self == StoryElementType.Motivation:
            return "How does the character's motivation change?"
        elif self == StoryElementType.Emotion:
            return "What's the character's emotional state?"
        elif self == StoryElementType.Emotion_change:
            return "How does the character's emotional state change?"
        elif self == StoryElementType.Relationship:
            return "How does the dynamic evolve among the characters?"

        return ''


@dataclass
class StoryElement:
    type: StoryElementType
    ref: Optional[uuid.UUID] = None
    text: str = ''
    value: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    row: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    col: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    arrows: Dict[int, int] = field(default_factory=dict, metadata=config(exclude=exclude_if_empty))
    elements: List['StoryElement'] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    dimension: str = field(default='', metadata=config(exclude=exclude_if_empty))
    modifier: str = field(default='', metadata=config(exclude=exclude_if_empty))
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))


@dataclass
class SceneReaderQuestion:
    id: uuid.UUID
    resolved: bool = False

    def sid(self) -> str:
        return str(self.id)


class ReaderInformationType(Enum):
    Story = 0
    Character = 1
    World = 2

    def color(self) -> str:
        if self == ReaderInformationType.Story:
            return '#C9A2D7'
        elif self == ReaderInformationType.Character:
            return '#73A9B6'
        elif self == ReaderInformationType.World:
            return '#70A88F'


@dataclass
class SceneReaderInformation:
    type: ReaderInformationType
    subtype: Optional[StoryElementType] = field(default=None, metadata=config(exclude=exclude_if_empty))
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    text: str = ''
    revelation: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    character_id: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))

    def sid(self) -> str:
        return str(self.id)

    @overrides
    def __eq__(self, other: 'SceneReaderInformation'):
        if isinstance(other, SceneReaderInformation):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


@dataclass
class SceneFunction:
    type: StoryElementType
    text: str = ''
    character_id: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))
    ref: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))


@dataclass
class SceneFunctions:
    primary: List[SceneFunction] = field(default_factory=list)
    secondary: List[SceneFunction] = field(default_factory=list)


@dataclass
class SceneMigration:
    migrated_functions: bool = True


@dataclass
class Scene:
    title: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    synopsis: str = ''
    pov: Optional[Character] = None
    characters: List[Character] = field(default_factory=list)
    agency: List[CharacterAgency] = field(default_factory=list)
    wip: bool = False
    plot_values: List[ScenePlotReference] = field(default_factory=list)
    day: int = 1
    chapter: Optional[Chapter] = None
    arcs: List[CharacterArc] = field(default_factory=list)
    stage: Optional[SceneStage] = None
    beats: List[SceneStoryBeat] = field(default_factory=list)
    comments: List[Comment] = field(default_factory=list)
    tag_references: List[TagReference] = field(default_factory=list)
    document: Optional['Document'] = None
    manuscript: Optional['Document'] = None
    drive: SceneDrive = field(default_factory=SceneDrive)
    purpose: Optional[ScenePurposeType] = None
    outcome: Optional[SceneOutcome] = None
    story_elements: List[StoryElement] = field(default_factory=list)
    structure: List[SceneStructureItem] = field(default_factory=list)
    questions: List[SceneReaderQuestion] = field(default_factory=list)
    info: List[SceneReaderInformation] = field(default_factory=list)
    progress: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    plot_pos_progress: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    plot_neg_progress: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    functions: SceneFunctions = field(default_factory=SceneFunctions)
    migration: SceneMigration = field(default_factory=SceneMigration)

    def beat(self, novel: 'Novel') -> Optional[StoryBeat]:
        structure = novel.active_story_structure
        for b in self.beats:
            if b.structure_id == structure.id and b.character_id == structure.character_id:
                return b.beat(structure)

    def link_beat(self, structure: 'StoryStructure', beat: StoryBeat):
        self.reset_structure(structure)
        self.beats.append(SceneStoryBeat.of(structure, beat))

    def reset_structure(self, structure: 'StoryStructure'):
        self.beats[:] = [x for x in self.beats if
                         x.structure_id != structure.id and x.character_id != structure.character_id]

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

    def outcome_motion(self) -> bool:
        return self.__is_outcome(SceneOutcome.MOTION)

    def title_or_index(self, novel: 'Novel') -> str:
        prefix = 'Scene' if novel.prefs.is_scenes_organization() else 'Chapter'
        return self.title if self.title else f'{prefix} {novel.scenes.index(self) + 1}'

    def link_plot(self, plot: Plot) -> ScenePlotReference:
        ref = ScenePlotReference(plot)
        self.plot_values.append(ref)
        function = SceneFunction(StoryElementType.Plot)
        function.ref = plot.id
        self.functions.primary.append(function)

        return ref

    def unlink_plot(self, plot: Plot):
        ref_to_be_removed = next((plot_v for plot_v in self.plot_values if plot_v.plot is plot),
                                 None)
        function_to_be_removed = next(
            (func for func in self.functions.primary if func.ref == plot.id), None)
        if ref_to_be_removed:
            self.plot_values.remove(ref_to_be_removed)
            self.calculate_plot_progress()
        if function_to_be_removed:
            self.functions.primary.remove(function_to_be_removed)

    def calculate_plot_progress(self):
        self.plot_pos_progress = 0
        self.plot_neg_progress = 0
        for ref in self.plot_values:
            if ref.data.charge:
                if ref.data.charge > 0:
                    self.plot_pos_progress = max(self.plot_pos_progress, ref.data.charge)
                else:
                    self.plot_neg_progress = min(self.plot_neg_progress, ref.data.charge)

    def update_purpose(self):
        self.purpose = ScenePurposeType.Other
        for i, function in enumerate(self.functions.primary):
            if i == 0 and function.type == StoryElementType.Resonance:
                self.purpose = ScenePurposeType.Emotion
            if function.type == StoryElementType.Plot:
                self.purpose = ScenePurposeType.Story
                break
            elif function.type in [StoryElementType.Reaction, StoryElementType.Reflection,
                                   StoryElementType.Repercussion]:
                self.purpose = ScenePurposeType.Reaction

        if self.purpose == ScenePurposeType.Other:
            for info in self.info:
                if info.subtype == StoryElementType.Setup:
                    self.purpose = ScenePurposeType.Setup
                    break
                if info.type == ReaderInformationType.Character:
                    self.purpose = ScenePurposeType.Character
                elif self.purpose == ScenePurposeType.Other:
                    self.purpose = ScenePurposeType.Exposition
        if self.purpose == ScenePurposeType.Other:
            self.purpose = ScenePurposeType.Story

    def __is_outcome(self, expected) -> bool:
        if self.outcome and self.outcome == expected:
            return True

        return False

    @overrides
    def __eq__(self, other: 'Scene'):
        if isinstance(other, Scene):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


def default_stages() -> List[SceneStage]:
    return [SceneStage('Outlined'), SceneStage('1st Draft'),
            SceneStage('Early Revision'), SceneStage('Mid-revision'), SceneStage('Late Revision'),
            SceneStage('Proofread'), SceneStage('Final')]


class GraphicsItemType(Enum):
    CHARACTER = 'character'
    STICKER = 'sticker'
    EVENT = 'event'
    TEXT = 'text'
    COMMENT = 'comment'
    SETUP = 'setup'
    NOTE = 'note'
    IMAGE = 'image'
    MAP_MARKER = 'map_marker'
    ICON = 'icon'
    MAP_AREA_SQUARE = 'map_area_square'
    MAP_AREA_CIRCLE = 'map_area_circle'
    MAP_AREA_CUSTOM = 'map_area_custom'

    def mimeType(self) -> str:
        return f'application/node-{self.value}'


NODE_SUBTYPE_GOAL = 'goal'
NODE_SUBTYPE_CONFLICT = 'conflict'
NODE_SUBTYPE_DISTURBANCE = 'disturbance'
NODE_SUBTYPE_BACKSTORY = 'backstory'
NODE_SUBTYPE_INTERNAL_CONFLICT = 'internal_conflict'
NODE_SUBTYPE_TURN = 'turn'
NODE_SUBTYPE_TWIST = 'twist'
NODE_SUBTYPE_DANGER = 'danger'
NODE_SUBTYPE_PROGRESS = 'progress'
NODE_SUBTYPE_SETBACK = 'setback'
NODE_SUBTYPE_REALIZATION = 'realization'
NODE_SUBTYPE_REACTION = 'reaction'
NODE_SUBTYPE_REFLECTION = 'reflection'
NODE_SUBTYPE_REPERCUSSION = 'repercussion'
NODE_SUBTYPE_RESONANCE = 'resonance'

NODE_SUBTYPE_QUESTION = 'question'
NODE_SUBTYPE_FORESHADOWING = 'foreshadowing'
NODE_SUBTYPE_TOOL = 'tool'
NODE_SUBTYPE_COST = 'cost'


class VariableType(Enum):
    Text = 0


@dataclass
class Variable:
    key: str
    type: VariableType
    value: Any
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    @overrides
    def __eq__(self, other: 'Variable'):
        if isinstance(other, Variable):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


class WorldBuildingEntityType(Enum):
    ARTICLE = 1
    SETTING = 2
    GROUP = 3
    ITEM = 4
    CONTAINER = 5


class WorldBuildingEntityElementType(Enum):
    Text = 0
    Header = 1
    Quote = 2
    Image = 3
    Separator = 4
    Timeline = 5
    Variables = 6
    Comments = 7
    Section = 8
    Highlight = 9
    Main_Section = 10
    Conceits = 11


@dataclass
class WorldBuildingEntityElement:
    type: WorldBuildingEntityElementType
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    title: str = field(default='', metadata=config(exclude=exclude_if_empty))
    text: str = field(default='', metadata=config(exclude=exclude_if_empty))
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))
    ref: Any = field(default=None, metadata=config(exclude=exclude_if_empty))
    events: List[BackstoryEvent] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    blocks: List['WorldBuildingEntityElement'] = field(default_factory=list,
                                                       metadata=config(exclude=exclude_if_empty))
    variables: List[Variable] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    image_ref: Optional[ImageRef] = field(default=None, metadata=config(exclude=exclude_if_empty))

    @overrides
    def __eq__(self, other: 'WorldBuildingEntityElement'):
        if isinstance(other, WorldBuildingEntityElement):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


@dataclass
class WorldBuildingEntity:
    name: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    children: List['WorldBuildingEntity'] = field(default_factory=list)
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))
    icon_color: str = field(default='', metadata=config(exclude=exclude_if_empty))
    emoji: str = field(default='', metadata=config(exclude=exclude_if_empty))
    bg_color: str = field(default='', metadata=config(exclude=exclude_if_empty))
    summary: str = field(default='', metadata=config(exclude=exclude_if_empty))
    type: WorldBuildingEntityType = WorldBuildingEntityType.ARTICLE
    elements: List[WorldBuildingEntityElement] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    side_elements: List[WorldBuildingEntityElement] = field(default_factory=list,
                                                            metadata=config(exclude=exclude_if_empty))
    side_visible: bool = field(default=True, metadata=config(exclude=exclude_if_true))
    ref: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))

    @overrides
    def __eq__(self, other: 'WorldBuildingEntity'):
        if isinstance(other, WorldBuildingEntity):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


class WorldConceitType(Enum):
    Geography = 'geography'
    Biology = 'biology'
    Magic = 'magic'
    Metaphysics = 'metaphysics'
    Technology = 'technology'
    Culture = 'culture'

    def icon(self) -> str:
        if self == WorldConceitType.Geography:
            return 'ph.globe-bold'
        elif self == WorldConceitType.Biology:
            return 'mdi.dna'
        elif self == WorldConceitType.Magic:
            return 'ei.magic'
        elif self == WorldConceitType.Metaphysics:
            return 'mdi.eye-circle-outline'
        elif self == WorldConceitType.Technology:
            return 'ei.cogs'
        elif self == WorldConceitType.Culture:
            return 'mdi.vector-circle'


@dataclass
class WorldConceit:
    name: str
    type: WorldConceitType
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    text: str = field(default='', metadata=config(exclude=exclude_if_empty))
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))
    icon_color: str = field(default='', metadata=config(exclude=exclude_if_empty))
    children: List['WorldConceit'] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))

    @overrides
    def __eq__(self, other: 'WorldConceit'):
        if isinstance(other, WorldConceit):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


def worldbuilding_root() -> WorldBuildingEntity:
    main_section = WorldBuildingEntityElement(WorldBuildingEntityElementType.Main_Section)
    main_section.blocks.append(WorldBuildingEntityElement(WorldBuildingEntityElementType.Header))
    main_section.blocks.append(WorldBuildingEntityElement(WorldBuildingEntityElementType.Text))
    return WorldBuildingEntity('My world', icon='mdi.globe-model', bg_color='#40916c',
                               elements=[main_section])


@dataclass
class GlossaryItem(SelectionItem):
    key: str = ''

    @overrides
    def __eq__(self, other: 'GlossaryItem'):
        if isinstance(other, GlossaryItem):
            return self.key == other.key
        return False

    @overrides
    def __hash__(self):
        return hash(self.key)


@dataclass
class Point:
    x: float
    y: float


@dataclass
class WorldBuildingMarker:
    x: float
    y: float
    type: GraphicsItemType = GraphicsItemType.MAP_MARKER
    name: str = ''
    description: str = ''
    color: str = '#ef233c'
    color_selected: str = '#A50C1E'
    icon: str = 'mdi.circle'
    size: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    height: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    width: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    ref: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))
    points: List[Point] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    opacity: int = field(default=0, metadata=config(exclude=exclude_if_empty))


@dataclass
class WorldBuildingMap:
    ref: Optional[ImageRef] = None
    title: str = ''
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    markers: List[WorldBuildingMarker] = field(default_factory=list)
    dominant_color: str = field(default='', metadata=config(exclude=exclude_if_empty))
    default: bool = field(default=False, metadata=config(exclude=exclude_if_false))


class LocationSensorType(Enum):
    SIGHT = 0
    LIGHT = 1
    SOUND = 2
    SMELL = 3
    TASTE = 4
    TEXTURE = 5
    TEMPERATURE = 6

    def display_name(self) -> str:
        return self.name.lower().capitalize()

    def description(self) -> str:
        if self == LocationSensorType.SIGHT:
            return 'What are the most significant visual details in this location?'
        elif self == LocationSensorType.SOUND:
            return 'What ambient or distinct sounds can be heard here?'
        elif self == LocationSensorType.SMELL:
            return 'What scents or odors define the atmosphere of this place?'
        elif self == LocationSensorType.TASTE:
            return 'Is there any taste in the air or through local cuisine?'
        elif self == LocationSensorType.TEXTURE:
            return 'What textures can be felt when interacting with surfaces here?'

    def icon(self) -> str:
        if self == LocationSensorType.SIGHT:
            return 'fa5.eye'
        elif self == LocationSensorType.SOUND:
            return 'fa5s.music'
        elif self == LocationSensorType.SMELL:
            return 'fa5s.air-freshener'
        elif self == LocationSensorType.TASTE:
            return 'mdi.food-drumstick'
        elif self == LocationSensorType.TEXTURE:
            return 'mdi.hand'

    def emoji(self) -> str:
        if self == LocationSensorType.SIGHT:
            return ':eyes:'
        elif self == LocationSensorType.SOUND:
            return ':musical_note:'
        elif self == LocationSensorType.SMELL:
            return ':nose:'
        elif self == LocationSensorType.TASTE:
            return ':tongue:'
        elif self == LocationSensorType.TEXTURE:
            return ':hand_with_fingers_splayed:'


@dataclass
class SensoryPerception:
    text: str = ''
    night_text: str = field(default='', metadata=config(exclude=exclude_if_empty))
    enabled: bool = field(default=False, metadata=config(exclude=exclude_if_false))


@dataclass
class SensoryDetail:
    night_mode: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    perceptions: Dict[str, SensoryPerception] = field(default_factory=dict,
                                                      metadata=config(exclude=exclude_if_empty))


@dataclass
class Location:
    name: str = ''
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    summary: str = field(default='', metadata=config(exclude=exclude_if_empty))
    children: List['Location'] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    sensory_detail: SensoryDetail = field(default_factory=SensoryDetail)
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))
    icon_color: str = field(default='', metadata=config(exclude=exclude_if_empty))
    origin_id: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))
    image_ref: Optional[ImageRef] = field(default=None, metadata=config(exclude=exclude_if_empty))

    @overrides
    def __eq__(self, other: 'Location'):
        if isinstance(other, Location):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


def default_maps() -> List[WorldBuildingMap]:
    return [WorldBuildingMap(default=True)]


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class WorldBuilding:
    root_entity: WorldBuildingEntity = field(default_factory=worldbuilding_root)
    glossary: Dict[str, GlossaryItem] = field(default_factory=dict)
    maps: List[WorldBuildingMap] = field(default_factory=default_maps)
    conceits: List[WorldConceit] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))


@dataclass
class TaskStatus(SelectionItem):
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    wip: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    resolves: bool = field(default=False, metadata=config(exclude=exclude_if_false))

    @overrides
    def __eq__(self, other: 'TaskStatus'):
        if isinstance(other, TaskStatus):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


tag_characterization = SelectionItem('Characterization', icon='fa5s.user', icon_color='darkBlue')
tag_worldbuilding = SelectionItem('Worldbuilding', icon='mdi.globe-model', icon_color='#2d6a4f')
tag_brainstorming = SelectionItem('Brainstorming', icon='fa5s.brain', icon_color='#FF5733')
tag_research = SelectionItem('Research', icon='mdi.library', icon_color='#0066CC')
tag_writing = SelectionItem('Writing', icon='mdi.typewriter', icon_color='#9933CC')
tag_plotting = SelectionItem('Plotting', icon='fa5s.theater-masks', icon_color='#FF6666')
tag_theme = SelectionItem('Theme', icon='mdi.butterfly-outline', icon_color='#9d4edd')
tag_outlining = SelectionItem('Outlining', icon='fa5s.list', icon_color='#99CC00')
tag_revision = SelectionItem('Revision', icon='mdi.clipboard-edit-outline', icon_color='#FF9933')
tag_drafting = SelectionItem('Drafting', icon='fa5s.dog', icon_color='#66CC33')
tag_editing = SelectionItem('Editing', icon='fa5s.cat', icon_color='#ff758f')
tag_collect_feedback = SelectionItem('Collect feedback', icon='msc.feedback', icon_color='#5e60ce')
tag_publishing = SelectionItem('Publishing', icon='fa5s.cloud-upload-alt', icon_color='#FF9900')
tag_marketing = SelectionItem('Marketing', icon='fa5s.bullhorn', icon_color='#FF3366')
tag_book_cover_design = SelectionItem('Book cover design', icon='fa5s.book', icon_color='#FF66CC')
tag_formatting = SelectionItem('Formatting', icon='mdi.format-pilcrow', icon_color='#006600')

_tags = [
    tag_characterization, tag_worldbuilding, tag_brainstorming, tag_research, tag_writing,
    tag_plotting, tag_theme, tag_outlining, tag_revision, tag_drafting, tag_editing,
    tag_collect_feedback, tag_publishing, tag_marketing, tag_book_cover_design, tag_formatting
]
task_tags: Dict[str, SelectionItem] = {}
for tag in _tags:
    task_tags[tag.text] = tag


@dataclass
class Task(CharacterBased):
    title: str
    status_ref: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    creation_date: Optional[datetime] = None
    resolved_date: Optional[datetime] = None
    summary: str = field(default='', metadata=config(exclude=exclude_if_empty))
    character_id: Optional[uuid.UUID] = None
    tags: List[str] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    web_link: str = field(default='', metadata=config(exclude=exclude_if_empty))
    version: str = field(default='', metadata=config(exclude=exclude_if_empty))
    beta: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))
    preview: str = field(default='', metadata=config(exclude=exclude_if_empty))

    def __post_init__(self):
        if self.creation_date is None:
            self.creation_date = datetime.now()
        self._character: Optional[Character] = None

    def creation_date_str(self):
        return self.creation_date.strftime("%Y-%m-%d %H:%M:%S")

    def resolved_date_str(self):
        return self.resolved_date.strftime("%Y-%m-%d %H:%M:%S") if self.resolved_date else ''

    def update_resolved_date(self):
        self.resolved_date = datetime.now()

    @overrides
    def __eq__(self, other: 'Task'):
        if isinstance(other, Task):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


def default_task_statues() -> List[TaskStatus]:
    return [TaskStatus('To Do', color_hexa='#0077b6'), TaskStatus('In Progress', color_hexa='#9f86c0', wip=True),
            TaskStatus('Done', color_hexa='#588157', resolves=True)]


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Board:
    tasks: List[Task] = field(default_factory=list)
    statuses: List[TaskStatus] = field(default_factory=default_task_statues)
    tags: Dict[str, SelectionItem] = field(default_factory=dict, metadata=config(exclude=exclude_if_empty))


class TemplateStoryStructureType(Enum):
    NONE = 0
    THREE_ACT = 1
    SPINE = 2
    TWISTS = 3
    FIVE_ACT = 4
    PACE = 5
    TENSION = 6
    TRANSFORMATION = 7
    CUSTOM = 8
    CORRUPTION = 9

    def description(self) -> str:
        if self == TemplateStoryStructureType.SPINE:
            return "A simple narrative framework created by Kenn Adams that consists a series of connected phrases, beginning with the status quo, followed by a disrupting event, and ending with resolution."


class StoryStructureDisplayType(Enum):
    Proportional_timeline = 'proportional_timeline'
    Sequential_timeline = 'sequential_timeline'


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
    acts_text: Dict[int, str] = field(default_factory=dict, metadata=config(exclude=exclude_if_empty))
    acts_icon: Dict[int, str] = field(default_factory=dict, metadata=config(exclude=exclude_if_empty))
    acts: int = 3
    display_type: StoryStructureDisplayType = field(default=StoryStructureDisplayType.Proportional_timeline)
    template_type: TemplateStoryStructureType = field(default=TemplateStoryStructureType.NONE)
    expected_acts: Optional[int] = field(default=None, metadata=config(exclude=exclude_if_empty))

    def __post_init__(self):
        self._character: Optional[Character] = None

    def act_beats(self) -> List[StoryBeat]:
        return [x for x in self.sorted_beats() if x.ends_act]

    def sorted_beats(self) -> List[StoryBeat]:
        return sorted(self.beats, key=lambda x: x.percentage)

    def increaseAct(self):
        self.acts += 1
        if self.acts == 1:
            self.acts = 2

    def decreaseAct(self):
        self.acts -= 1
        if self.acts == 1:
            self.acts = 0

    def update_acts(self):
        if self.acts == 0:
            for beat in self.beats:
                beat.act = 0
        else:
            act = 1
            for beat in self.sorted_beats():
                beat.act = act
                if beat.act_colorized:
                    beat.icon_color = act_color(act, self.acts)
                if beat.ends_act:
                    act += 1

    def normalize_beats(self):
        if not self.beats or self.display_type != StoryStructureDisplayType.Sequential_timeline:
            return

        percentage_per_beat = 99.0 / len(self.beats)
        for i, beat in enumerate(self.beats):
            beat.percentage = percentage_per_beat * (i + 1)


general_beat = StoryBeat(text='Beat',
                         id=uuid.UUID('3dc905df-1a9b-4e04-90f5-199ea908f2d5'),
                         icon='mdi.lightning-bolt-outline', icon_color='grey',
                         description="A pivotal moment or event that advances the plot or develops a character",
                         act=1, percentage=1)

hook_beat = StoryBeat(text='Hook',
                      id=uuid.UUID('40365047-e7df-4543-8816-f9f8dcce12da'),
                      icon='mdi.hook',
                      icon_color='#829399',
                      description="Raises curiosity and hooks the reader's attention. May hint at what kind of story the reader can expect.",
                      act=1, percentage=1)
motion_beat = StoryBeat(text='Motion',
                        id=uuid.UUID('f9120632-3e27-405e-b404-543f9c5b12ca'),
                        icon='mdi.motion-outline',
                        icon_color='#d4a373',
                        description='Sets the story in motion with enough intrigue to create narrative drive, without establishing the story yet.',
                        act=1, percentage=1)
disturbance_beat = StoryBeat(text='Disturbance',
                             id=uuid.UUID('a954f949-8be9-46d6-8ebf-f9f76f482944'),
                             icon='mdi.chemical-weapon',
                             icon_color='#e63946',
                             description="Disturbs the protagonist's life and sets the story in motion. It could act as the inciting incident.",
                             placeholder="Disturbs the protagonist's life and sets the story in motion.",
                             act=1, percentage=1)
characteristic_moment_beat = StoryBeat(text='Characteristic Moment',
                                       id=uuid.UUID('b50c32e4-1927-4633-b5a3-9765aeaee7ad'),
                                       icon='mdi6.human-scooter',
                                       icon_color='#457b9d',
                                       description="Introduces the protagonist, highlighting their personality, including possible flaws, goals, or weaknesses.",
                                       act=1, percentage=1)
normal_world_beat = StoryBeat(text='Normal World',
                              id=uuid.UUID('79ebc3b6-6b02-4d2d-8fdd-12274b8bb412'),
                              icon='fa5.image',
                              icon_color='#1ea896',
                              description="Establishes the setting alongside the protagonist before the first major event in the story would happen.",
                              act=1, percentage=1)

inciting_incident_beat = StoryBeat(text='Inciting Incident',
                                   icon='mdi.bell-alert-outline',
                                   icon_color='#a2ad59',
                                   description="An event that disrupts the protagonist's life and sets the story in motion. Often an external conflict is involved that sets the protagonist in a new direction.",
                                   placeholder="An event that disrupts the protagonist's life and sets the story in motion",
                                   id=uuid.UUID('a0c2d94a-b53c-485e-a279-f2548bdb38ec'),
                                   act=1, percentage=10)

synchronicity_beat = StoryBeat(text='Synchronicity',
                               icon='msc.sync',
                               icon_color='#0077b6',
                               description='A series of accidents or coincidences take on meaning, calling the protagonist to action as if guided by fate.',
                               placeholder="Unrelated, but meaningful coincidences call the protagonist to action as if guided by fate.",
                               id=uuid.UUID('e4351ee3-ed30-42c4-9c3a-2f6b690c8417'),
                               act=1, percentage=10)
trigger_beat = StoryBeat('Trigger',
                         icon='mdi.lightning-bolt-outline',
                         icon_color='#AD9C58',
                         description="An event that sets the story in motion and introduces a new situation or problem. Often followed by the 'Establish' beat to establish the story later.",
                         placeholder="An event that sets the story in motion and introduces a new situation or problem.",
                         id=uuid.UUID('f127f7db-5715-4d3b-90aa-c074181c765c'),
                         act=1, percentage=10
                         )
establish_beat = StoryBeat('Establish',
                           icon='fa5s.stamp',
                           icon_color='#AD7E58',
                           description='An event or character decision that establishes the story. Often preceded by the Trigger beat to set the story in motion first.',
                           placeholder='An event or character decision that establishes the story.',
                           id=uuid.UUID('c23a3e47-1161-4869-8104-c4874ab6f98b'),
                           act=1, percentage=17)

refusal_beat = StoryBeat(text='Refusal',
                         icon='mdi6.hand-back-left',
                         icon_color='#e5989b',
                         description='The protagonist hesitates or resists the inciting incident',
                         id=uuid.UUID('9fd9c53d-8e58-4099-b538-be60fb898531'),
                         act=1,
                         percentage=14)

turn_beat = StoryBeat(text='Turn',
                      id=uuid.UUID('31000162-4bed-49f2-9def-a70ba15ff378'),
                      icon='mdi.sign-direction',
                      icon_color='#8338ec',
                      description="Shifts the story's direction")

twist_beat = StoryBeat(text='Twist',
                       id=uuid.UUID('cd297072-07ea-487a-b884-c645673a73cb'),
                       icon='ph.shuffle-bold',
                       icon_color='#f20089',
                       description="Brings an unexpected development to the story by defying readers' expectations")

danger_beat = StoryBeat(text='Danger',
                        id=uuid.UUID('d87d76e1-b0b2-412d-b39b-84c622127915'),
                        icon='ei.fire',
                        icon_color='#f4a261',
                        description="Moments of heightened danger, either physical or emotional")
revelation_beat = StoryBeat(text='Revelation',
                            icon='fa5s.binoculars',
                            icon_color='#588157',
                            description="A moment where a key information is revealed or discovered",
                            id=uuid.UUID('36d8a7e9-db8d-4d87-a2d0-9170c86aa6c3'))

dark_moment = StoryBeat(text='Dark Moment',
                        icon='mdi.weather-night',
                        icon_color='#494368',
                        description="All-time low moment for the protagonist. They must feel worse than at the beginning of the story.",
                        id=uuid.UUID('4ded5006-c90a-4825-9de7-e16bf62017a3'), act=2,
                        percentage=75, enabled=False)

first_pinch_point_beat = StoryBeat(text='First Pinch Point',
                                   id=uuid.UUID('af024374-12e6-44dc-80e6-28f2bc0e59ed'),
                                   icon='fa5s.thermometer-three-quarters',
                                   description='A reminder of the power of antagonistic forces.',
                                   icon_color='#b81365',
                                   act=2, percentage=35)
second_pinch_point_beat = StoryBeat(text='Second Pinch Point',
                                    id=uuid.UUID('74087e28-b37a-4797-95bc-41d96f6a9393'),
                                    icon='fa5s.biohazard',
                                    description="A showcase of the full strength of antagonistic forces and a reminder of what's at stake.",
                                    icon_color='#cd533b',
                                    act=2, percentage=62)
plot_point = StoryBeat('Plot Point',
                       icon='mdi6.chevron-double-right',
                       description="It propels the story into a new stage, possibly into a new act.",
                       id=uuid.UUID('2adeeb15-ad30-4830-909b-1d8d41f3e9d6'),
                       ends_act=True, act_colorized=True)
plot_point_ponr = StoryBeat(text='Point of No Return',
                            icon='fa5s.door-closed',
                            description="It propels the story into a new stage through the character's irreversible decision. There's no going back now.",
                            placeholder="It propels the story into a new stage through the character's irreversible decision.",
                            id=uuid.UUID('6c1c36b8-c04a-41b9-9d2e-4f9d8f095355'),
                            ends_act=True, act_colorized=True)
plot_point_aha = StoryBeat(text='A-ha moment',
                           icon='fa5.lightbulb',
                           description="It propels the story into a new stage through the character's epiphany. They often have a realization about themselves or the plot.",
                           placeholder="It propels the story into a new stage through the character's epiphany.",
                           id=uuid.UUID('77e05b3c-27c3-42b2-bcbc-1f46dfc85d73'),
                           ends_act=True, act_colorized=True)
plot_point_rededication = StoryBeat(text='Re-dedication',
                                    icon='fa5s.heartbeat',
                                    description="It propels the story into a new stage when the character recommits to their goal or mission.",
                                    id=uuid.UUID('4468e497-77f7-4758-90f2-4601f16c7685'),
                                    ends_act=True, act_colorized=True)

first_plot_point = StoryBeat(text='First Plot Point',
                             icon='mdi6.chevron-double-right',
                             icon_color='#2a4494',
                             description="It propels the protagonist into the central conflict.",
                             id=uuid.UUID('8d85c960-1c63-44d4-812d-545d3ba4d153'), act=1,
                             ends_act=True, percentage=20)

first_plot_point_ponr = StoryBeat(text='First Plot Point',
                                  icon='fa5s.door-closed',
                                  icon_color='#2a4494',
                                  description="It propels the protagonist into the central conflict through the character's irreversible decision. There's no going back now.",
                                  placeholder="It propels the protagonist into the central conflict through the character's irreversible decision",
                                  id=uuid.UUID('d94e8ecd-c60d-4e7b-9817-47877ea1402f'), act=1,
                                  ends_act=True, percentage=20)

second_plot_point = StoryBeat(text='Second Plot Point',
                              id=uuid.UUID('95705e5e-a6b8-4abe-b2ea-426f2ae8d020'),
                              icon='mdi6.chevron-triple-right',
                              description="It propels the protagonist towards the climax to face the main conflict, often through a new twist, revelation, or turning point.",
                              placeholder="It propels the protagonist towards the climax to face the main conflict",
                              icon_color='#6a0136',
                              act=2, ends_act=True, percentage=80)

second_plot_point_aha = StoryBeat(text='A-ha moment',
                                  icon='fa5.lightbulb',
                                  icon_color='#6a0136',
                                  description="It propels the story into the climax through the character's epiphany. They often have a realization about themselves or the plot.",
                                  placeholder="It propels the story into the climax through the character's epiphany.",
                                  id=uuid.UUID('00ccb15d-9331-4f45-8ed7-ffc7b2e7bf90'),
                                  act=2, ends_act=True, percentage=80)

second_plot_point_hero_ordeal = StoryBeat(text='Ordeal',
                                          icon='mdi6.skull',
                                          description='The hero faces a decisive challenge and fails, having an all-time low moment, but only to be reborn later',
                                          id=uuid.UUID('57803320-e4e8-434e-9364-01de61d14773'),
                                          act=2, ends_act=True, percentage=75)

second_plot_point_hero_road_back = StoryBeat(text='The Road Back',
                                             icon='fa5s.route',
                                             icon_color='#0077b6',
                                             description='The hero returns to the ordinary world with a newfound understanding or power to face the main conflict',
                                             placeholder='The hero returns to the ordinary world with a newfound understanding or power',
                                             id=uuid.UUID('2f7b08de-04dc-401b-ba72-b30f8dbfe74f'),
                                             act=2, ends_act=True, percentage=75)

hero_reward = StoryBeat(text='Reward',
                        icon='mdi6.flask-round-bottom',
                        icon_color='#414833',
                        description='The hero achieves the goal of the journey and receives a reward',
                        id=uuid.UUID('6e14dba8-86ce-48c6-8324-5eda18d73ecc'),
                        act=2,
                        percentage=70)

hero_false_victory = StoryBeat(text='False victory',
                               icon='mdi.trophy-broken',
                               icon_color='#b5838d',
                               description="A moment when the hero appears to achieve their goal, only to face immediate setbacks",
                               id=uuid.UUID('115ed42c-0d83-4762-b5be-adf5c97429cd'),
                               act=2, percentage=70, enabled=False)

midpoint = StoryBeat(text='Midpoint',
                     icon='mdi.middleware-outline',
                     icon_color='#2e86ab',
                     description="Intensifies the conflict or raises the stakes by often involving a major revelation or turning point. It may shift the story into a different direction.",
                     placeholder="Intensifies the conflict or raises the stakes by often involving a major revelation or turning point",
                     id=uuid.UUID('3f817e10-85d1-46af-91c6-70f1ad5c0542'),
                     act=2, percentage=50)
midpoint_ponr = StoryBeat('Point of No Return',
                          icon='fa5s.door-closed',
                          icon_color='#028090',
                          description='An irreversible critical decision with significant consequences from which the protagonist has no way back.',
                          id=uuid.UUID('0630a2af-f687-4dfa-98f1-2c50a52b40cb'),
                          act=2, percentage=50)
midpoint_mirror = StoryBeat('Mirror Moment',
                            icon='mdi6.mirror-variant',
                            icon_color='#0096c7',
                            description="The protagonist's self-reflection, confronting their flaws or internal conflicts.",
                            id=uuid.UUID('94b58db9-e59f-412e-b284-b911908e443f'),
                            act=2, percentage=50
                            )
midpoint_proactive = StoryBeat('Reactive to Proactive Shift',
                               icon='mdi.account-convert',
                               icon_color='#219ebc',
                               description="The protagonist takes the initiative and takes control of the conflict instead of reacting to it.",
                               id=uuid.UUID('d7d1b457-353f-4259-92c2-0cc7da0e4b88'),
                               act=2, percentage=50
                               )
midpoint_false_victory = StoryBeat(text='False victory',
                                   icon='mdi.trophy-broken',
                                   icon_color='#b5838d',
                                   description="A moment when the protagonist appears to achieve their goal, only to face immediate setbacks",
                                   id=uuid.UUID('404883e9-d110-4e83-9c52-e37bb888632c'),
                                   act=2, percentage=50)
midpoint_re_dedication = StoryBeat(text='Re-dedication',
                                   icon='fa5s.heartbeat',
                                   icon_color=RED_COLOR,
                                   description="A moment when the protagonist renews their commitment to their goal or mission, often after facing significant setbacks or doubts.",
                                   placeholder="A moment when the protagonist renews their commitment to their goal or mission.",
                                   id=uuid.UUID('7b63be66-1c96-4332-af78-ffa62b79bbd4'),
                                   act=2, percentage=50)

midpoint_hero_ordeal = StoryBeat(text='Ordeal',
                                 icon='mdi6.skull',
                                 description='The hero faces a decisive challenge and fails, having an all-time low moment, but only to be reborn later',
                                 id=uuid.UUID('46cfccac-f5fe-463c-8f4b-5075b9b5e733'),
                                 act=2,
                                 percentage=50)

midpoint_hero_mirror = StoryBeat('Mirror Moment',
                                 icon='mdi6.mirror-variant',
                                 icon_color='#0096c7',
                                 description="The hero is confronted with their flaws or internal conflicts.",
                                 id=uuid.UUID('035809e2-7702-424d-bc9a-83c077f91782'),
                                 act=2, percentage=50)

crisis = StoryBeat(text='Crisis',
                   icon='mdi.arrow-decision-outline',
                   icon_color='#ce2d4f',
                   description="The protagonist must decide between two equally bad or two irreconcilable good choices.",
                   id=uuid.UUID('466688f7-ebee-4d36-a655-83ff40e1c46d'),
                   act=3, percentage=95)
climax_beat = StoryBeat(text='Climax',
                        icon='fa5s.chevron-up',
                        icon_color='#ce2d4f',
                        description="The highest point of tension. The final confrontation between the protagonist and the antagonist. The story's central conflict is resolved.",
                        placeholder="The final confrontation where the story's central conflict is resolved",
                        id=uuid.UUID('342eb27c-52ff-40c2-8c5e-cf563d4e38bc'),
                        act=3, percentage=97)
resolution_beat = StoryBeat(text='Resolution',
                            icon='fa5s.water',
                            icon_color='#7192be',
                            description="An 'after' snapshot to tie up loose ends and release tension. It may introduce us to the protagonist's new life.",
                            placeholder="An 'after' snapshot to tie up loose ends and release tension.",
                            id=uuid.UUID('996695b1-8db6-4c68-8dc4-51bbfe720e8b'),
                            act=3, percentage=99)

contrast_beat = StoryBeat('Contrast',
                          icon='ei.adjust',
                          icon_color='#7192be',
                          description="A moment that contrasts with the beginning of the story, showing how the character or their world has changed.",
                          placeholder="A moment that contrasts with the beginning of the story.",
                          id=uuid.UUID('be29edaf-58e1-47ec-99ab-0614fee5cd4d'),
                          act=3, percentage=99)
retrospection_beat = StoryBeat('Retrospection',
                               icon='mdi.magnify-scan',
                               icon_color='#7192be',
                               description="A moment where a character reflects on how the plot was resolved, providing insight to the reader after the fact.",
                               placeholder="A moment that reveals how the plot was resolved, providing insight after the fact",
                               id=uuid.UUID('7a8581bc-ef27-402a-8e57-539d79145d37'),
                               act=3, percentage=99)

first_plot_points = (first_plot_point, first_plot_point_ponr)
second_plot_points = (second_plot_point, second_plot_point_aha)
midpoints = (
    midpoint, midpoint_ponr, midpoint_mirror, midpoint_proactive, midpoint_false_victory, midpoint_re_dedication)


def copy_beat(beat: StoryBeat) -> StoryBeat:
    cloned_beat = copy.deepcopy(beat)
    cloned_beat.id = uuid.uuid4()
    cloned_beat.custom = True
    return cloned_beat


three_act_structure = StoryStructure(title='Three Act Structure',
                                     id=uuid.UUID('58013be5-1efb-4de4-9dd2-1433ce6edf90'),
                                     icon='mdi.numeric-3-circle-outline',
                                     icon_color='#ff7800',
                                     template_type=TemplateStoryStructureType.THREE_ACT,
                                     beats=[hook_beat,
                                            inciting_incident_beat,
                                            first_plot_point,
                                            first_pinch_point_beat,
                                            midpoint,
                                            second_pinch_point_beat,
                                            dark_moment,
                                            second_plot_point,
                                            crisis,
                                            climax_beat,
                                            resolution_beat,
                                            ])

five_act_structure = StoryStructure(title='Five Act Structure',
                                    id=uuid.UUID('9b5dcfca-e140-452f-ac42-67ebb9a3b301'),
                                    icon='mdi.numeric-5-box-outline',
                                    icon_color='#',
                                    template_type=TemplateStoryStructureType.FIVE_ACT,
                                    )

save_the_cat = StoryStructure(title='Save the Cat',
                              id=uuid.UUID('1f1c4433-6afa-48e1-a8dc-f8fcb94bfede'),
                              icon='fa5s.cat',
                              beats=[StoryBeat(text='Opening Image',
                                               icon='fa5.image',
                                               icon_color='#1ea896',
                                               description="Establishes the setting and introduces the protagonist. Bonus: hints at the main character's flaws and desires.",
                                               placeholder="Establishes the setting and introduces the protagonist",
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
                                               placeholder="Hints at the lesson that the protagonist will learn by the end of the story",
                                               id=uuid.UUID('1c8b0903-f169-48d5-bcec-3e842f360150'),
                                               act=1, percentage=5),
                                     StoryBeat(text='Catalyst',
                                               icon='fa5s.vial',
                                               icon_color='#822faf',
                                               description="The first event that truly changes the protagonist's status quo. Often external conflict is involved that raises the stakes and sets the protagonist in a new direction.",
                                               placeholder="The first event that truly changes the protagonist's status quo",
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
                                               placeholder="Start of Act 2. The protagonist enters a new world, sometimes physically",
                                               id=uuid.UUID('43eb267f-2840-437b-9eac-9e52d80eba2b'),
                                               act=1, ends_act=True, percentage=20),
                                     StoryBeat(text='B Story',
                                               icon='mdi.alpha-b-box',
                                               icon_color='#a6808c',
                                               description="Introduction of a new character who represents the B Story, which is the thematic or spiritual story of the protagonist's journey.",
                                               placeholder="Introduction of a new character who represents the B Story",
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
                                               placeholder="A false defeat or false victory moment that often raises the stakes",
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
                                               placeholder="An a-ha moment for the protagonist. They realize that they have to change",
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
                                               description='A new plan is necessary. The protagonist must find the truth and act accordingly.',
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

pace_turn_beat_one = StoryBeat(text='Turn',
                               id=uuid.UUID('15108852-1959-49ef-9c58-0ce55cb676ed'),
                               icon='mdi.sign-direction',
                               icon_color='#2a4494',
                               description="A shift in the story's direction",
                               percentage=25)

pace_turn_beat_two = StoryBeat(text='Turn',
                               id=uuid.UUID('98a8a1ce-43f5-4db7-80a6-ddba7fb17e05'),
                               icon='mdi.sign-direction',
                               icon_color='#6a0136',
                               description="A shift in the story's direction",
                               percentage=75)

pace_driven_structure = StoryStructure(title="Pace-driven",
                                       id=uuid.UUID('54f4e296-b281-4dc9-b3be-36a869ee48c3'),
                                       icon='mdi.lightning-bolt-outline',
                                       display_type=StoryStructureDisplayType.Sequential_timeline,
                                       template_type=TemplateStoryStructureType.PACE,
                                       acts=0,
                                       beats=[
                                           hook_beat,
                                           inciting_incident_beat,
                                           pace_turn_beat_one,
                                           midpoint,
                                           pace_turn_beat_two,
                                           climax_beat,
                                           resolution_beat
                                       ]
                                       )

tension_first_conflict = StoryBeat(text='First conflict',
                                   id=uuid.UUID('3610723f-c23e-47a0-9174-f328f6f8ebd6'),
                                   icon='mdi.sword-cross',
                                   icon_color='#f3a712',
                                   description="A complication that forces the character to react",
                                   percentage=25)

tension_second_conflict = StoryBeat(text='Second conflict',
                                    id=uuid.UUID('5f520c66-f3a5-4353-884f-cc6055b6952b'),
                                    icon='mdi.sword-cross',
                                    icon_color='#B88612',
                                    description="Tension tightens and the plot complicates",
                                    percentage=50)

tension_third_conflict = StoryBeat(text='Third conflict',
                                   id=uuid.UUID('a5172e05-4e08-4c2c-8346-7f05ff5573d3'),
                                   icon='mdi.sword-cross',
                                   icon_color='#CD533B',
                                   description="A major revelation, twist, or dark moment",
                                   percentage=75)

tension_driven_structure = StoryStructure(title="Tension",
                                          id=uuid.UUID('6b01f4e2-2116-4849-be88-85f519d2fbd4'),
                                          icon='fa5s.fire',
                                          display_type=StoryStructureDisplayType.Sequential_timeline,
                                          template_type=TemplateStoryStructureType.TENSION,
                                          acts=0,
                                          beats=[
                                              disturbance_beat,
                                              tension_first_conflict,
                                              tension_second_conflict,
                                              tension_third_conflict,
                                              climax_beat,
                                              resolution_beat
                                          ]
                                          )

transformation_need_beat = StoryBeat(text='Need',
                                     id=uuid.UUID('929de7eb-b7db-44bc-8e9f-7eed5616aadd'),
                                     icon='ri.key-fill',
                                     icon_color='#457b9d',
                                     description="The protagonist lacks something in their life even if they don't realize it",
                                     percentage=1)

transformation_aha_moment = StoryBeat(text='A-ha moment',
                                      icon='fa5.lightbulb',
                                      icon_color='#6a0136',
                                      description="A choice or realization that changes the protagonist",
                                      id=uuid.UUID('249d7977-2c8c-4c2f-b66a-1b9f329d8dd1'),
                                      percentage=80)

transformation_final_test = StoryBeat(text='Final test',
                                      id=uuid.UUID('7af98db6-c8e2-4929-b90b-b8321882ce6c'),
                                      icon='fa5s.chevron-up',
                                      icon_color='#ce2d4f',
                                      description="The protagonist has to prove their transformation through a final test",
                                      percentage=95)

transformation_driven_structure = StoryStructure(title="Transformation",
                                                 id=uuid.UUID('b9aa5a84-6c19-4ac3-8589-73523b1fa897'),
                                                 icon='mdi6.butterfly-outline',
                                                 display_type=StoryStructureDisplayType.Sequential_timeline,
                                                 template_type=TemplateStoryStructureType.TRANSFORMATION,
                                                 acts=0,
                                                 beats=[
                                                     transformation_need_beat,
                                                     inciting_incident_beat,
                                                     refusal_beat,
                                                     midpoint_mirror,
                                                     transformation_aha_moment,
                                                     transformation_final_test,
                                                     contrast_beat
                                                 ]
                                                 )

heros_journey = StoryStructure(title="Hero archetype",
                               id=uuid.UUID('d19e6f28-c6ed-4496-8f6b-064ab4306f17'),
                               icon='fa5s.mask',
                               beats=[
                                   StoryBeat(text='Flawed Hero',
                                             icon='mdi6.human-scooter',
                                             icon_color='#457b9d',
                                             placeholder='The hero is introduced alongside their lacks, flaws, or weaknesses',
                                             description='The hero is introduced alongside their lacks, flaws, or weaknesses that they have to resolve by the end of the story',
                                             id=uuid.UUID('99e3f76b-6bbe-44e8-8733-5c9334b3b2ec'),
                                             act=1,
                                             percentage=1),
                                   StoryBeat(text='Call to Adventure',
                                             icon='mdi.bell-alert-outline',
                                             icon_color='#a2ad59',
                                             description='The hero is presented with a challenge or opportunity to embark on a journey',
                                             id=uuid.UUID('e246082a-67ff-412b-9f07-7310339157a5'),
                                             act=1,
                                             percentage=10),
                                   StoryBeat(text='Refusal of the Call',
                                             icon='mdi6.hand-back-left',
                                             icon_color='#e5989b',
                                             description='The hero initially refuses the call to adventure',
                                             id=uuid.UUID('638ff0ec-e867-48a5-a606-54de7e39eeee'),
                                             act=1,
                                             percentage=12, enabled=False),
                                   StoryBeat(text='Meeting with the Mentor',
                                             icon='mdi.compass-rose',
                                             icon_color='#80ced7',
                                             description='The hero meets their mentor who will offer guidance or tools necessary to succeed with the journey',
                                             id=uuid.UUID('c3b899f2-c6c4-4306-98e7-359ab65851be'),
                                             act=1,
                                             percentage=18, enabled=False),
                                   StoryBeat(text='Crossing the First Threshold',
                                             icon='fa5s.torii-gate',
                                             icon_color='#a4161a',
                                             description='The hero leaves the ordinary world and embarks on the journey',
                                             id=uuid.UUID('f4e9b677-bfc2-443f-b4b3-0691e398b3d5'),
                                             act=1,
                                             ends_act=True,
                                             percentage=25),
                                   midpoint_hero_mirror,
                                   hero_false_victory,
                                   second_plot_point_hero_ordeal,
                                   StoryBeat(text='Resurrection',
                                             icon='fa5s.chevron-up',
                                             icon_color='#ce2d4f',
                                             description='The hero must overcome a final challenge that redeems and transforms them',
                                             id=uuid.UUID('7013dc29-ac7d-47df-893d-95211f15fd77'),
                                             act=3,
                                             percentage=90),
                                   StoryBeat(text='Resolution',
                                             icon='mdi6.flask-round-bottom-empty',
                                             icon_color='#023e8a',
                                             description='The hero returns to the ordinary world as a complete person who addressed their flaws',
                                             id=uuid.UUID('ca7da757-31fa-4ffb-902d-b7c391bb9bc3'),
                                             act=3,
                                             percentage=98)
                               ]
                               )

story_spine = StoryStructure(title="Story Spine",
                             id=uuid.UUID('38c22213-3f9b-4a51-ac87-b7a60a535e41'),
                             icon='mdi.chart-timeline-variant-shimmer',
                             display_type=StoryStructureDisplayType.Sequential_timeline,
                             template_type=TemplateStoryStructureType.SPINE,
                             acts=0,
                             beats=[
                                 StoryBeat(text='Once upon a time...',
                                           id=uuid.UUID('3c09104c-414a-4042-bf30-887c686473cd'),
                                           seq=1,
                                           icon_color='#457b9d',
                                           description="Introduces the world and key characters",
                                           percentage=1),
                                 StoryBeat(text='Every day...',
                                           id=uuid.UUID('23de963d-7655-4685-a9b7-bfccdad46404'),
                                           seq=2,
                                           icon_color='#457b9d',
                                           description="Depicts the characters' routine life and the status quo",
                                           percentage=5),
                                 StoryBeat(text='But, one day...',
                                           id=uuid.UUID('a8fdc9bc-72fc-425f-8a97-2c501724d6e3'),
                                           seq=3,
                                           icon_color='#a2ad59',
                                           description="An event disrupts the character's life",
                                           percentage=10),
                                 StoryBeat(text='Because of that...',
                                           id=uuid.UUID('18412ba6-2411-4e57-9997-fc63a9a6ab60'),
                                           seq=4,
                                           icon_color='#cd533b',
                                           description="The characters react to the disruption, leading to new events",
                                           percentage=25),
                                 StoryBeat(text='Because of that...',
                                           id=uuid.UUID('678c5f83-8fe6-4166-bb5e-df9715f24e74'),
                                           seq=5,
                                           icon_color='#cd533b',
                                           description="These events create further challenges and complications",
                                           percentage=50),
                                 StoryBeat(text='Because of that...',
                                           id=uuid.UUID('c3d3450e-9819-4f47-a683-1314358206fc'),
                                           seq=6,
                                           icon_color='#cd533b',
                                           description="The characters face increasing obstacles leading to a climax",
                                           percentage=75),
                                 StoryBeat(text='Until finally...',
                                           id=uuid.UUID('8c87b59f-e229-47ca-9734-c656d8e8e973'),
                                           seq=7,
                                           icon_color='#ce2d4f',
                                           description="Reaches the climax where the main conflict is addressed",
                                           percentage=90),
                                 StoryBeat(text='And ever since that day...',
                                           id=uuid.UUID('be8740a3-caec-4045-bc48-169f8a588ed3'),
                                           seq=8,
                                           icon_color='#7192be',
                                           description="Concludes with the resolution and the new status quo for the characters",
                                           percentage=99),
                             ]

                             )
corruption_spine = StoryStructure(title="Corruption",
                                  id=uuid.UUID('efd11bc7-91e4-48f8-a84b-eb8132168693'),
                                  icon='mdi.bottle-tonic-skull',
                                  display_type=StoryStructureDisplayType.Sequential_timeline,
                                  template_type=TemplateStoryStructureType.CORRUPTION,
                                  acts=0,
                                  beats=[
                                      StoryBeat(text='Once uncorrupted',
                                                id=uuid.UUID('8e54323d-28cf-4fd7-b8b4-58bfd4b6b924'),
                                                seq=1,
                                                icon_color='#457b9d',
                                                description="A morally intact character with an often unfulfilling life, untouched by corruption",
                                                percentage=1),
                                      StoryBeat(text='Yet they crave power',
                                                id=uuid.UUID('b8cb5f80-a9b2-4598-a189-d2c775d35417'),
                                                seq=2,
                                                icon_color='#a2ad59',
                                                description="",
                                                percentage=12),
                                      StoryBeat(text='They cross a line',
                                                id=uuid.UUID('54ff1ca5-76fb-4e10-8b37-5db714302510'),
                                                seq=3,
                                                icon_color='#E76F51',
                                                description="",
                                                percentage=25),
                                      StoryBeat(text='They silence their doubts',
                                                id=uuid.UUID('e789bf11-6c17-41b2-8bc5-82f672cc86f3'),
                                                seq=4,
                                                icon_color='#B56576',
                                                description="",
                                                percentage=35),
                                      StoryBeat(text='They cling to their gains',
                                                id=uuid.UUID('c9d543fc-1543-4176-a909-2af6ade7446d'),
                                                seq=5,
                                                icon_color='#6D597A',
                                                description="",
                                                percentage=50),
                                      StoryBeat(text='The truth breaks through',
                                                id=uuid.UUID('bcb718d1-7542-4f12-a614-c845ad9b87cd'),
                                                seq=6,
                                                icon_color='#4C3A51',
                                                description="",
                                                percentage=70),
                                      StoryBeat(text="They lose control",
                                                id=uuid.UUID('fcc7ae00-00a1-407f-b243-f0ed125d898a'),
                                                seq=7,
                                                icon_color='#3E1F47',
                                                description="",
                                                percentage=90),
                                      StoryBeat(text='They suffer the consequences',
                                                id=uuid.UUID('61d1dffd-d547-45f5-91a4-4bcc001b760a'),
                                                seq=8,
                                                icon_color='#1A1A1A',
                                                description="",
                                                percentage=98),
                                  ]

                                  )
twists_and_turns = StoryStructure(title='Twists and Turns',
                                  id=uuid.UUID('f905ba6b-0195-4ed7-932e-0b02e49cb1ae'),
                                  icon='ph.shuffle-bold',
                                  display_type=StoryStructureDisplayType.Sequential_timeline,
                                  template_type=TemplateStoryStructureType.TWISTS,
                                  acts=0)

default_story_structures = [three_act_structure, save_the_cat, heros_journey]


@dataclass
class LanguageSettings:
    lang: str = 'en-US'


class ImportOriginType(Enum):
    SCRIVENER = 'scrivener'


@dataclass
class ImportOrigin:
    type: ImportOriginType
    source: str
    source_id: Optional[uuid.UUID] = None
    sync: bool = False
    last_mod_time: int = 0


class StoryType(Enum):
    Novel = 0
    Series = 1


@dataclass
class NovelDescriptor:
    title: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    lang_settings: LanguageSettings = field(default_factory=LanguageSettings)
    import_origin: Optional[ImportOrigin] = None
    subtitle: str = field(default='', metadata=config(exclude=exclude_if_empty))
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))
    icon_color: str = field(default='black', metadata=config(exclude=exclude_if_black))
    tutorial: bool = False
    creation_date: Optional[datetime] = None
    story_type: StoryType = field(default=StoryType.Novel)
    short_synopsis: str = field(default='', metadata=config(exclude=exclude_if_empty))
    parent: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))
    sequence: int = field(default=0, metadata=config(exclude=exclude_if_empty))

    def __post_init__(self):
        if self.creation_date is None:
            self.creation_date = datetime.now()

    @overrides
    def __eq__(self, other: 'NovelDescriptor'):
        if isinstance(other, NovelDescriptor):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))

    def is_scrivener_sync(self) -> bool:
        if self.import_origin is None:
            return False
        return self.import_origin.type == ImportOriginType.SCRIVENER and self.import_origin.sync

    def is_readonly(self) -> bool:
        if self.import_origin is None:
            return False
        return self.import_origin.sync


@dataclass
class CausalityItem(SelectionItem):
    links: List['CausalityItem'] = field(default_factory=list)

    @overrides
    def __eq__(self, other: 'CausalityItem'):
        if isinstance(other, CausalityItem):
            return self.text == other.text
        return False

    @overrides
    def __hash__(self):
        return hash(self.text)


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Causality:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    items: List['CausalityItem'] = field(default_factory=list)


class MiceType(Enum):
    CHARACTER = 0
    INQUIRY = 1
    MILIEU = 2
    EVENT = 3


@dataclass
class MiceThread:
    type: MiceType
    text: str = ''
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    beginning_scene_id: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))
    ending_scene_id: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))

    def beginning_scene(self, novel: 'Novel') -> Optional['Scene']:
        if not self.beginning_scene_id:
            return None
        for s in novel.scenes:
            if s.id == self.beginning_scene_id:
                return s

    def ending_scene(self, novel: 'Novel') -> Optional['Scene']:
        if not self.ending_scene_id:
            return None
        for s in novel.scenes:
            if s.id == self.ending_scene_id:
                return s


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class MiceQuotient:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    threads: List[MiceThread] = field(default_factory=list)


@dataclass
class BoxParameters:
    lm: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    tm: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    rm: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    bm: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    width: int = field(default=0, metadata=config(exclude=exclude_if_empty))


@dataclass
class PremiseIdea:
    text: str
    selected: bool = True
    params: Optional[BoxParameters] = None


@dataclass
class PremiseQuestion:
    text: str
    selected: bool = field(default=True, metadata=config(exclude=exclude_if_true))
    visible: bool = field(default=True, metadata=config(exclude=exclude_if_true))
    children: List['PremiseQuestion'] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))


@dataclass
class Label:
    keyword: str

    @overrides
    def __eq__(self, other):
        if isinstance(other, Label):
            return self.keyword == other.keyword
        if isinstance(other, str):
            return self.keyword == other
        return False


@dataclass
class PremiseReview:
    premise: str


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class PremiseBuilder:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    ideas: List[PremiseIdea] = field(default_factory=list)
    questions: List[PremiseQuestion] = field(default_factory=list)
    current: str = field(default='', metadata=config(exclude=exclude_if_empty))
    keywords: List[Label] = field(default_factory=list)
    saved_premises: List[PremiseReview] = field(default_factory=list)


class DocumentType(Enum):
    DOCUMENT = 0
    CHARACTER_BACKSTORY = 1
    CAUSE_AND_EFFECT = 2
    REVERSED_CAUSE_AND_EFFECT = 3
    CHARACTER_ARC = 5
    STORY_STRUCTURE = 6
    MICE = 7
    PDF = 8
    PREMISE = 9
    MIND_MAP = 10


@dataclass
class TextStatistics:
    word_count: int = -1


@dataclass
class DocumentProgress:
    added: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    removed: int = field(default=0, metadata=config(exclude=exclude_if_empty))


@dataclass
class DocumentStatistics:
    wc: int = 0
    progress: Dict[str, DocumentProgress] = field(default_factory=dict, metadata=config(exclude=exclude_if_empty))


@dataclass
class Document(CharacterBased, SceneBased):
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
    file: str = field(default='', metadata=config(exclude=exclude_if_empty))
    diagram: Optional['Diagram'] = field(default=None, metadata=config(exclude=exclude_if_empty))

    def display_name(self) -> str:
        if self.title:
            return self.title
        return 'Untitled'

    @overrides
    def __eq__(self, other: 'Document'):
        if isinstance(other, Document):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))

    def __post_init__(self):
        self.loaded: bool = False
        self.content: str = ''
        self.data: Any = None
        self._character: Optional[Character] = None
        self._scene: Optional[Scene] = None


WELCOME_DOC_ID = uuid.UUID('ec2a62d9-fc00-41dd-8a6c-b121156b6cf4')


def default_documents() -> List[Document]:
    return [Document('Welcome!', id=WELCOME_DOC_ID, icon='ph.hand-waving-fill')]


@dataclass
class ProductivityType(SelectionItem):
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    enabled: bool = True

    @overrides
    def __eq__(self, other: 'ProductivityType'):
        if isinstance(other, ProductivityType):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


class SnapshotType(Enum):
    Productivity = ('Monthly Productivity', 'mdi6.progress-star-four-points')
    MonthlyWriting = ('Monthly Writing', 'mdi.calendar-month')
    DailyWriting = ('Daily Writing', 'mdi6.calendar-today')

    def __new__(cls, display_name: str, icon: str):
        obj = object.__new__(cls)
        obj._value_ = display_name
        obj.display_name = display_name
        obj.icon = icon
        return obj


def default_productivity_categories() -> List[ProductivityType]:
    return [
        ProductivityType('Writing', icon='fa5s.pen-fancy', icon_color=PLOTLYST_SECONDARY_COLOR),
        ProductivityType('Planning', icon='fa5s.theater-masks', icon_color='#895F6D'),
        ProductivityType('Research', icon='mdi.library', icon_color='#0066CC'),
        ProductivityType('Character', icon='fa5s.user', icon_color='#219ebc'),
        ProductivityType('Worldbuilding', icon='mdi.globe-model', icon_color='#40916c'),
        ProductivityType('Editing', icon='fa5s.highlighter', icon_color='#FF7171'),
    ]


@dataclass
class DailyProductivity:
    overall_days: int = 0
    categories: List[ProductivityType] = field(default_factory=default_productivity_categories)
    progress: Dict[str, str] = field(default_factory=dict,
                                     metadata=config(exclude=exclude_if_empty))


class ReaderQuestionType(Enum):
    General = 0
    Character_growth = 1
    Backstory = 2
    Internal_conflict = 3
    Relationship = 4
    Character_motivation = 5
    Conflict_resolution = 6
    Plot = 7
    Wonder = 8

    def display_name(self) -> str:
        return self.name.replace('_', ' ')

    def description(self) -> str:
        if self == ReaderQuestionType.General:
            return "Any mystery, secret, or dramatic question raised in the story"
        if self == ReaderQuestionType.Character_growth:
            return "Questions related to a character's growth and development"
        if self == ReaderQuestionType.Backstory:
            return "A mystery about a character's past"
        if self == ReaderQuestionType.Internal_conflict:
            return "Questions related to a character's internal turmoil and their resolution"
        if self == ReaderQuestionType.Relationship:
            return "Questions related to conflicting, dynamic or complex relationships"
        if self == ReaderQuestionType.Character_motivation:
            return "Questions related to a character's hidden motivation"
        if self == ReaderQuestionType.Conflict_resolution:
            return "Questions related to unresolved conflict"
        if self == ReaderQuestionType.Plot:
            return "Dramatic questions related to plot"
        if self == ReaderQuestionType.Wonder:
            return "Reader's intrigue related to the setting's sense of wonder (especially in fantasy and sci-fi)"

    def icon(self) -> str:
        if self == ReaderQuestionType.General:
            return "ei.question-sign"
        if self == ReaderQuestionType.Character_growth:
            return "ph.person-bold"
        if self == ReaderQuestionType.Backstory:
            return "mdi.archive-alert"
        if self == ReaderQuestionType.Internal_conflict:
            return "mdi6.mirror-variant"
        if self == ReaderQuestionType.Relationship:
            return "fa5s.people-arrows"
        if self == ReaderQuestionType.Character_motivation:
            return "fa5s.fist-raised"
        if self == ReaderQuestionType.Conflict_resolution:
            return "mdi.sword-cross"
        if self == ReaderQuestionType.Plot:
            return "mdi.drama-masks"
        if self == ReaderQuestionType.Wonder:
            return "mdi.globe-model"


@dataclass
class ReaderQuestion:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    text: str = ''
    type: ReaderQuestionType = ReaderQuestionType.General

    def sid(self) -> str:
        return str(self.id)

    @overrides
    def __eq__(self, other: 'ReaderQuestion'):
        if isinstance(other, ReaderQuestion):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


@dataclass
class TagType(SelectionItem):
    description: str = ''

    @overrides
    def __eq__(self, other: 'TagType'):
        if isinstance(other, TagType):
            return self.text == other.text
        return False

    @overrides
    def __hash__(self):
        return hash(self.text)


@dataclass
class Tag(SelectionItem):
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    tag_type: str = 'General'
    builtin: bool = False

    @overrides
    def __eq__(self, other: 'Tag'):
        if isinstance(other, Tag):
            return self.id == other.id
        return False

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
                description='General tags that can be tracked for each scene.'),
        TagType('Symbols', icon='fa5s.dove', icon_color='#5995ed',
                description='A symbol can be anything that represents something beyond their literal meaning.'),
        TagType('Motifs', icon='mdi6.glass-fragile', icon_color='#8ac6d0',
                description='A motif is a recurring object, sound, situation, phrase, or idea throughout the story'
                            + ' that empowers the theme.'),
        TagType('Items', icon='mdi.ring', icon_color='#b6a6ca',
                description='Relevant items that reappear throughout the story.'
                            + ' They do not have symbolic meaning unlike Symbols or Motifs.'),
        # TagType('Themes', icon='ei.idea-alt', icon_color='#f72585',
        #         description='The main ideas or lessons that the story explores.')
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
class Node(CharacterBased):
    x: float
    y: float
    type: GraphicsItemType
    subtype: str = field(default='', metadata=config(exclude=exclude_if_empty))
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    character_id: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))
    color: str = field(default='black', metadata=config(exclude=exclude_if_black))
    text: str = field(default='', metadata=config(exclude=exclude_if_empty))
    size: int = 12
    bold: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    italic: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    underline: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    width: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    height: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    image_ref: Optional[ImageRef] = field(default=None, metadata=config(exclude=exclude_if_empty))
    transparent: bool = field(default=False, metadata=config(exclude=exclude_if_false))

    def __post_init__(self):
        self._character: Optional[Character] = None

    @overrides
    def __eq__(self, other: 'Node'):
        if isinstance(other, Node):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


def to_node(x: float, y: float, type: GraphicsItemType, subtype: str = '', default_size: int = 12) -> Node:
    node = Node(x, y, type=type, subtype=subtype)
    if type == GraphicsItemType.EVENT or type == GraphicsItemType.TEXT:
        node.size = max(16, default_size)
        if subtype in [NODE_SUBTYPE_BACKSTORY, NODE_SUBTYPE_INTERNAL_CONFLICT]:
            node.size = max(14, default_size - 1)

    if type == GraphicsItemType.TEXT:
        node.transparent = True

    if subtype == NODE_SUBTYPE_GOAL:
        node.icon = 'mdi.target'
        node.color = 'darkBlue'
    elif subtype == NODE_SUBTYPE_CONFLICT:
        node.icon = 'mdi.sword-cross'
        node.color = '#f3a712'
    elif subtype == NODE_SUBTYPE_BACKSTORY:
        node.icon = 'fa5s.archive'
        node.color = '#9c6644'
    elif subtype == NODE_SUBTYPE_INTERNAL_CONFLICT:
        node.icon = 'mdi.mirror'
        node.color = '#94b0da'
    elif subtype == NODE_SUBTYPE_DISTURBANCE:
        node.icon = 'mdi.bell-alert-outline'
        node.color = '#a2ad59'
    elif subtype == NODE_SUBTYPE_TURN:
        node.icon = 'mdi.sign-direction'
        node.color = '#8338ec'
    elif subtype == NODE_SUBTYPE_TWIST:
        node.icon = 'ph.shuffle-bold'
        node.color = '#f20089'
    elif subtype == NODE_SUBTYPE_DANGER:
        node.icon = 'ei.fire'
        node.color = '#f48c06'
    elif subtype == NODE_SUBTYPE_PROGRESS:
        node.icon = 'mdi.chevron-double-up'
        node.color = '#40916c'
    elif subtype == NODE_SUBTYPE_SETBACK:
        node.icon = 'mdi.chevron-double-down'
        node.color = '#d00000'
    elif subtype == NODE_SUBTYPE_REALIZATION:
        node.icon = 'fa5.lightbulb'
        node.color = '#219ebc'
    elif subtype == NODE_SUBTYPE_REACTION:
        node.icon = 'fa5s.heartbeat'
        node.color = '#b81365'
    elif subtype == NODE_SUBTYPE_REFLECTION:
        node.icon = 'mdi.thought-bubble-outline'
        node.color = '#219ebc'
    elif subtype == NODE_SUBTYPE_REPERCUSSION:
        node.icon = 'fa5s.radiation'
        node.color = '#CD533B'
    elif subtype == NODE_SUBTYPE_RESONANCE:
        node.icon = 'mdi.butterfly-outline'
        node.color = '#9d4edd'

    elif subtype == NODE_SUBTYPE_QUESTION:
        node.icon = 'ei.question-sign'
    elif subtype == NODE_SUBTYPE_FORESHADOWING:
        node.icon = 'mdi6.crystal-ball'

    return node


@dataclass
class Connector:
    source_id: uuid.UUID
    target_id: uuid.UUID
    source_angle: float
    target_angle: float
    type: str = ''
    pen: Qt.PenStyle = Qt.PenStyle.SolidLine
    width: int = 1
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))
    color: str = field(default='', metadata=config(exclude=exclude_if_empty))
    text: str = field(default='', metadata=config(exclude=exclude_if_empty))
    cp_x: Optional[float] = None
    cp_y: Optional[float] = None
    start_arrow_enabled: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    end_arrow_enabled: bool = field(default=True, metadata=config(exclude=exclude_if_true))
    cp_controlled: Optional[bool] = None


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class DiagramData:
    nodes: List[Node] = field(default_factory=list)
    connectors: List[Connector] = field(default_factory=list)


@dataclass
class DiagramSettings:
    snap_to_grid: bool = field(default=False, metadata=config(exclude=exclude_if_false))


@dataclass
class Diagram:
    title: str = field(default='', metadata=config(exclude=exclude_if_empty))
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))
    icon_color: str = field(default='black', metadata=config(exclude=exclude_if_black))
    settings: DiagramSettings = field(default_factory=DiagramSettings)

    def __post_init__(self):
        self.loaded: bool = False
        self.data: Optional[DiagramData] = None

    @overrides
    def __eq__(self, other: 'Diagram'):
        if isinstance(other, Diagram):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))


def default_character_networks() -> List[Diagram]:
    return [Diagram('Character relations', id=uuid.UUID('bfd1f2d3-cb33-48a6-a09e-b4332c3d1ed1'))]


@dataclass
class Relation(SelectionItem):
    pass


@dataclass
class FontSettings:
    family: str = ''
    text_width: int = 0
    font_size: int = 0
    line_space: int = 2


@dataclass
class DocsPreferences:
    grammar_check: bool = False
    font: Dict[str, FontSettings] = field(default_factory=dict)


@dataclass
class ManuscriptPreferences:
    font: Dict[str, FontSettings] = field(default_factory=dict)
    dash: DashInsertionMode = DashInsertionMode.INSERT_EM_DASH
    capitalization: AutoCapitalizationMode = AutoCapitalizationMode.PARAGRAPH
    ellipsis: EllipsisInsertionMode = EllipsisInsertionMode.NONE
    smart_quotes: bool = True
    period: bool = True
    header_variant: int = 1


class NovelPanel(Enum):
    OUTLINE = 'outline'
    MANUSCRIPT = 'manuscript'
    REPORTS = 'reports'


class ScenesView(Enum):
    NOVEL = 'novel'
    CHARACTERS = 'characters'
    SCENES = 'scenes'
    WORLD_BUILDING = 'world_building'
    DOCS = 'docs'
    MANUSCRIPT = 'manuscript'
    BOARD = 'board'
    REPORTS = 'reports'
    FORMATTING = 'formatting'


@dataclass
class PanelPreferences:
    panel: NovelPanel = NovelPanel.OUTLINE
    scenes_view: Optional[ScenesView] = None
    scene_chapters_sidebar_toggled: bool = False


class CardSizeRatio(Enum):
    RATIO_2_3 = 0
    RATIO_3_4 = 1


class NovelSetting(Enum):
    Structure = 'structure'
    Storylines = 'storylines'
    Mindmap = 'mindmap'
    Characters = 'characters'
    Scenes = 'scenes'
    Track_emotion = 'track_emotion'
    Track_motivation = 'track_motivation'
    Track_conflict = 'track_conflict'
    Track_pov = 'pov'
    Documents = 'documents'
    Manuscript = 'manuscript'
    World_building = 'world_building'
    Management = 'management'
    Reports = 'reports'
    Formatting = 'formatting'
    SCENE_CARD_POV = 'scene_card_pov'
    SCENE_CARD_PURPOSE = 'scene_card_purpose'
    SCENE_CARD_PLOT_PROGRESS = 'scene_card_plot_progress'
    SCENE_CARD_STAGE = 'scene_card_stage'
    SCENE_CARD_MIDDLE = 'scene_card_middle_display'
    SCENE_CARD_WIDTH = 'scene_card_width'
    SCENE_TABLE_POV = 'scene_table_pov'
    SCENE_TABLE_PURPOSE = 'scene_table_purpose'
    SCENE_TABLE_CHARACTERS = 'scene_table_characters'
    SCENE_TABLE_STORYLINES = 'scene_table_storylines'
    SCENE_TABLE_PLOT_PROGRESS = 'scene_table_plot_progress'
    Character_enneagram = 'character_enneagram'
    Character_mbti = 'character_mbti'
    Character_love_style = 'character_love_style'
    Character_work_style = 'character_work_style'
    CHARACTER_TABLE_ROLE = 'character_table_role'
    CHARACTER_TABLE_AGE = 'character_table_age'
    CHARACTER_TABLE_GENDER = 'character_table_gender'
    CHARACTER_TABLE_OCCUPATION = 'character_table_occupation'
    CHARACTER_TABLE_ENNEAGRAM = 'character_table_enneagram'
    CHARACTER_TABLE_MBTI = 'character_table_mbti'
    Scenes_organization = 'scenes_organization'

    def scene_card_setting(self) -> bool:
        return self.name.startswith('SCENE_CARD')

    def scene_table_setting(self) -> bool:
        return self.name.startswith('SCENE_TABLE')


@dataclass
class NovelPreferences:
    active_stage_id: Optional[uuid.UUID] = None
    docs: DocsPreferences = field(default_factory=DocsPreferences)
    manuscript: ManuscriptPreferences = field(default_factory=ManuscriptPreferences)
    panels: PanelPreferences = field(default_factory=PanelPreferences)
    settings: Dict[str, Any] = field(default_factory=dict)

    def toggled(self, setting: NovelSetting, default: bool = True) -> bool:
        return self.settings.get(setting.value, default)

    def setting(self, setting: NovelSetting, default: Any) -> Any:
        return self.settings.get(setting.value, default)

    def is_scenes_organization(self) -> bool:
        return self.settings.get(NovelSetting.Scenes_organization.value, True)


@dataclass
class ManuscriptGoals:
    target_wc: int = 80000


MINDMAP_PREVIEW = 'mindmap'
NETWORK_PREVIEW = 'network'
BACKSTORY_PREVIEW = 'backstory'
STORY_GRID_PREVIEW = 'story_grid'
STORY_MAP_PREVIEW = 'story_map'
WORLD_BUILDING_PREVIEW = 'worldbuilding'


def default_locations() -> List[Location]:
    return [Location('New location')]


@dataclass
class NovelInfo:
    audience: str = ''
    style: str = ''
    genres: List[str] = field(default_factory=list)
    mood: List[str] = field(default_factory=list)
    type: str = ''
    has_spice: bool = False
    spice: int = 1


@dataclass
class Novel(NovelDescriptor):
    story_structures: List[StoryStructure] = field(default_factory=list)
    characters: List[Character] = field(default_factory=list)
    scenes: List[Scene] = field(default_factory=list)
    plots: List[Plot] = field(default_factory=list)
    chapters: List[Chapter] = field(default_factory=list)
    custom_chapters: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    stages: List[SceneStage] = field(default_factory=default_stages)
    character_topics: List[Topic] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    goals: List[Goal] = field(default_factory=list)
    documents: List[Document] = field(default_factory=default_documents)
    tags: Dict[TagType, List[Tag]] = field(default_factory=default_tags)
    premise: str = ''
    synopsis: Optional['Document'] = None
    prefs: NovelPreferences = field(default_factory=NovelPreferences)
    world: WorldBuilding = field(default_factory=WorldBuilding)
    locations: List[Location] = field(default_factory=default_locations)
    board: Board = field(default_factory=Board)
    manuscript_goals: ManuscriptGoals = field(default_factory=ManuscriptGoals)
    events_map: Diagram = field(default=None, metadata=config(exclude=exclude_if_empty))
    character_networks: List[Diagram] = field(default_factory=default_character_networks)
    manuscript_progress: Dict[str, DocumentProgress] = field(default_factory=dict,
                                                             metadata=config(exclude=exclude_if_empty))
    questions: Dict[str, ReaderQuestion] = field(default_factory=dict)
    productivity: DailyProductivity = field(default_factory=DailyProductivity)
    descriptors: NovelInfo = field(default_factory=NovelInfo)

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
            for agenda in scene.agency:
                if agenda.character_id and str(agenda.character_id) not in char_ids:
                    character: Character = agenda.character(self)
                    if character:
                        chars.append(character)
                        char_ids.add(str(character.id))

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
        return Scene(title)

    @staticmethod
    def new_novel(title: str = '') -> 'Novel':
        novel = Novel(title)
        copied_structure = copy.deepcopy(three_act_structure)
        # copied_structure.beats[0].enabled = False  # hook
        copied_structure.beats[3].enabled = False  # pinch 1
        copied_structure.beats[5].enabled = False  # pinch 2
        copied_structure.beats[8].enabled = False  # crisis
        novel.story_structures = [copied_structure]
        chapter = Chapter('Chapter 1')
        novel.chapters.append(chapter)

        scene = Novel.new_scene('My first scene')
        scene.chapter = chapter
        novel.scenes.append(scene)

        plot = Plot('Main plot', icon='fa5s.theater-masks', icon_color='#03396c')
        novel.plots.append(plot)

        return novel

    @staticmethod
    def new_series(title: str = '') -> 'Novel':
        return Novel(title, icon='ph.books', story_type=StoryType.Series)

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

    def update_chapter_titles(self):
        i = 1
        for chapter in self.chapters:
            if chapter.type is None:
                chapter.title = f'Chapter {i}'
                i += 1

    @overrides
    def __eq__(self, other: 'Novel'):
        if isinstance(other, Novel):
            return self.id == other.id
        return False

    @overrides
    def __hash__(self):
        return hash(str(self.id))
