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
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Any, Dict, Optional

from PyQt5.QtCore import Qt
from dataclasses_json import config
from overrides import overrides


def exclude_if_empty(value):
    return not value


def exclude_if_true(value):
    return value is True


def exclude_if_false(value):
    return value is False


def exclude_if_black(value):
    return value == 'black'


class SelectionItemType(Enum):
    CHOICE = 0
    SEPARATOR = 1


def exclude_if_choice(value):
    return value == SelectionItemType.CHOICE


@dataclass
class SelectionItem:
    text: str
    type: SelectionItemType = field(default=SelectionItemType.CHOICE, metadata=config(exclude=exclude_if_choice))
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))
    icon_color: str = field(default='black', metadata=config(exclude=exclude_if_black))
    color_hexa: str = field(default='', metadata=config(exclude=exclude_if_empty))
    meta: Dict[str, Any] = field(default_factory=dict, metadata=config(exclude=exclude_if_empty))

    @overrides
    def __hash__(self):
        return hash(self.text)


class TemplateFieldType(Enum):
    TEXT = 0
    SMALL_TEXT = 1
    TEXT_SELECTION = 2
    BUTTON_SELECTION = 3
    NUMERIC = 4
    IMAGE = 5
    LABELS = 6
    DISPLAY_SUBTITLE = 7
    DISPLAY_LABEL = 8
    DISPLAY_LINE = 9
    DISPLAY_HEADER = 10


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
    description: str = field(default='', metadata=config(exclude=exclude_if_empty))
    emoji: str = field(default='', metadata=config(exclude=exclude_if_empty))
    placeholder: str = field(default='', metadata=config(exclude=exclude_if_empty))
    selections: List[SelectionItem] = field(default_factory=list)
    highlighted: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    required: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    exclusive: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    custom: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    min_value: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    max_value = 2_147_483_647
    compact: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    show_label: bool = field(default=True, metadata=config(exclude=exclude_if_true))

    @overrides
    def __hash__(self):
        return hash(str(self.id))


age_field = TemplateField(name='Age', type=TemplateFieldType.NUMERIC,
                          id=uuid.UUID('7c8fccb8-9228-495a-8edd-3f991ebeed4b'), emoji=':birthday_cake:',
                          show_label=False, compact=True, placeholder='Age')

enneagram_field = TemplateField(name='Enneagram', type=TemplateFieldType.TEXT_SELECTION,
                                id=uuid.UUID('be281490-c1b7-413c-b519-f780dbdafaeb'),
                                selections=[SelectionItem('Perfectionist', icon='mdi.numeric-1-circle',
                                                          icon_color='#1f487e',
                                                          meta={'positive': ['Rational', 'Principled', 'Objective',
                                                                             'Structured'],
                                                                'negative': ['Strict'],
                                                                'desire': 'Being good, balanced, have integrity',
                                                                'fear': 'Being incorrect, corrupt, evil',
                                                                'number': 1}),
                                            SelectionItem('Giver', icon='mdi.numeric-2-circle',
                                                          icon_color='#7ae7c7',
                                                          meta={'positive': ['Generous', 'Warm', 'Caring'],
                                                                'negative': ['Possessive'],
                                                                'desire': 'To be loved and appreciated',
                                                                'fear': 'Being unloved, unwanted',
                                                                'number': 2}
                                                          ),
                                            SelectionItem('Achiever', icon='mdi.numeric-3-circle',
                                                          icon_color='#297045',
                                                          meta={'positive': ['Pragmatic', 'Driven', 'Ambitious'],
                                                                'negative': ['Image-conscious'],
                                                                'desire': 'Be valuable and worthwhile',
                                                                'fear': 'Being worthless',
                                                                'number': 3}
                                                          ),
                                            SelectionItem('Individualist', icon='mdi.numeric-4-circle',
                                                          icon_color='#4d8b31',
                                                          meta={'positive': ['Self-aware', 'Sensitive', 'Expressive'],
                                                                'negative': ['Temperamental'],
                                                                'desire': 'Express their individuality',
                                                                'fear': 'Having no identity or significance',
                                                                'number': 4}
                                                          ),
                                            SelectionItem('Investigator', icon='mdi.numeric-5-circle',
                                                          icon_color='#ffc600',
                                                          meta={'positive': ['Perceptive', 'Curious', 'Innovative'],
                                                                'negative': ['Isolated'],
                                                                'desire': 'Be competent',
                                                                'fear': 'Being useless, incompetent',
                                                                'number': 5}
                                                          ),
                                            SelectionItem('Skeptic', icon='mdi.numeric-6-circle',
                                                          icon_color='#ff6b35',
                                                          meta={'positive': ['Committed', 'Responsible', 'Organized'],
                                                                'negative': ['Anxious'],
                                                                'desire': 'Have security and support',
                                                                'fear': 'Being vulnerable and unprepared',
                                                                'number': 6}
                                                          ),
                                            SelectionItem('Enthusiast', icon='mdi.numeric-7-circle',
                                                          icon_color='#ec0b43',
                                                          meta={'positive': ['Optimistic', 'Flexible', 'Practical',
                                                                             'Adventurous'],
                                                                'negative': ['Impulsive', 'Self-centered'],
                                                                'desire': 'Be stimulated, engaged, satisfied',
                                                                'fear': 'Being deprived',
                                                                'number': 7}
                                                          ),
                                            SelectionItem('Challenger', icon='mdi.numeric-8-circle',
                                                          icon_color='#4f0147',
                                                          meta={'positive': ['Decisive', 'Powerful', 'Assertive',
                                                                             'Independent'],
                                                                'negative': ['Confrontational'],
                                                                'desire': 'Be independent and in control',
                                                                'fear': 'Being vulnerable, controlled, harmed',
                                                                'number': 8}
                                                          ),
                                            SelectionItem('Peacemaker', icon='mdi.numeric-9-circle',
                                                          icon_color='#3a015c',
                                                          meta={'positive': ['Easygoing', 'Understanding', 'Patient',
                                                                             'Supportive'],
                                                                'negative': ['Lazy', 'Indecisive'],
                                                                'desire': 'Internal peace, harmony',
                                                                'fear': 'Loss, separation',
                                                                'number': 9}
                                                          )],
                                compact=True, show_label=False)
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
                           compact=True, show_label=False)
positive_traits = sorted([
    'Accessible', 'Active', 'Adaptive', 'Admirable', 'Adventurous', 'Agreeable', 'Alert', 'Ambitious', 'Appreciative',
    'Articulate', 'Aspiring', 'Assertive', 'Attentive', 'Balanced', 'Benevolent', 'Calm', 'Capable', 'Captivating',
    'Caring', 'Challenging', 'Charismatic', 'Charming', 'Cheerful', 'Clever', 'Colorful', 'Committed', 'Compassionate',
    'Confident', 'Considerate', 'Cooperative', 'Courageous', 'Creative', 'Curious', 'Daring', 'Decent', 'Decisive',
    'Dedicated', 'Dignified', 'Disciplined', 'Discreet', 'Driven', 'Dutiful', 'Dynamic', 'Earnest', 'Easygoing',
    'Educated', 'Efficient', 'Elegant', 'Empathetic', 'Encouraging', 'Energetic', 'Enthusiastic', 'Expressive', 'Fair',
    'Faithful', 'Flexible', 'Focused', 'Forgiving', 'Friendly', 'Gallant', 'Generous', 'Gentle', 'Genuine', 'Gracious',
    'Hard-working', 'Healthy', 'Hearty', 'Helpful', 'Honest', 'Honorable', 'Humble', 'Humorous', 'Idealistic',
    'Imaginative', 'Impressive', 'Incorruptible', 'Independent', 'Individualistic', 'Innovative', 'Insightful',
    'Intelligent', 'Intuitive', 'Invulnerable', 'Just', 'Kind', 'Knowledge', 'Leaderly', 'Logical', 'Lovable', 'Loyal',
    'Mature', 'Methodical', 'Maticulous', 'Moderate', 'Modest', 'Neat', 'Objective', 'Observant', 'Open', 'Optimistic',
    'Orderly', 'Organized', 'Original', 'Passionate', 'Patient', 'Peaceful', 'Perceptive', 'Perfectionist',
    'Persuasive', 'Playful', 'Popular', 'Powerful', 'Practical', 'Precise', 'Principled', 'Protective', 'Punctual',
    'Purposeful', 'Rational', 'Realistic', 'Reflective', 'Relaxed', 'Reliable', 'Resourceful', 'Respectful',
    'Responsible', 'Responsive', 'Romantic', 'Sane', 'Scholarly', 'Secure', 'Selfless', 'Self-aware', 'Self-critical',
    'Sensitive', 'Sentimental', 'Serious', 'Sharing', 'Skillful', 'Sociable', 'Solid', 'Sophisticated', 'Spontaneous',
    'Structured', 'Supportive', 'Sweet', 'Sympathetic', 'Systematic', 'Tolerant', 'Truthful', 'Trustworthy',
    'Understanding', 'Unselfish', 'Warm', 'Wise', 'Witty', 'Youthful', 'Zany'
])

negative_traits = sorted([
    'Abrasive', 'Abrupt', 'Aimless', 'Aloof', 'Amoral', 'Angry', 'Anxious', 'Apathetic', 'Argumentative', 'Arrogant',
    'Artificial', 'Asocial', 'Assertive', 'Bewildered', 'Bizarre', 'Bland', 'Blunt', 'Brutal', 'Calculating', 'Callous',
    'Careless', 'Cautious', 'Charmless', 'Childish', 'Clumsy', 'Cold', 'Colorless', 'Compulsive', 'Confused',
    'Conventional', 'Confrontational', 'Cowardly', 'Crazy', 'Critical', 'Crude', 'Cruel', 'Cynical', 'Deceitful',
    'Demanding', 'Dependent', 'Desperate', 'Destructive', 'Devious', 'Difficult', 'Discouraging', 'Dishonest',
    'Disloyal', 'Disobedient', 'Disorderly', 'Disorganized', 'Disrespectful', 'Disruptive', 'Disturbing', 'Dull',
    'Egocentric', 'Envious', 'Erratic', 'Extravagant', 'Extreme', 'Faithless', 'False', 'Fanatical', 'Fearful',
    'Flamboyant', 'Foolish', 'Forgetful', 'Fraudulent', 'Frightening', 'Frivolous', 'Gloomy', 'Greedy', 'Grim',
    'Hateful', 'Hesitant', 'Ignorant', 'Ill-mannered', 'Image-conscious', 'Impatient', 'Impractical', 'Imprudent',
    'Impulsive', 'Inconsiderate', 'Incurious', 'Indecisive', 'Indulgent', 'Insecure', 'Insensitive', 'Insincere',
    'Insulting', 'Intolerant', 'Irrational', 'Irresponsible', 'Irritable', 'Isolated', 'Jealous', 'Judgmental', 'Lazy',
    'Malicious', 'Mannered', 'Mean', 'Moody', 'Naive', 'Narcissistic', 'Narrow-minded', 'Negative', 'Neglectful',
    'Nihilistic', 'Obsessive', 'One-dimensional', 'Opinionated', 'Oppressed', 'Outrageous', 'Paranoid', 'Passive',
    'Pompous', 'Possessive', 'Prejudiced', 'Pretentious', 'Procrastinating', 'Quirky', 'Regretful', 'Repressed',
    'Resentful', 'Ridiculous', 'Rigid', 'Rude', 'Sadistic', 'Scheming', 'Scornful', 'Selfish', 'Self-centered',
    'Shortsighted', 'Shy', 'Silly', 'Single-minded', 'Sloppy', 'Slow', 'Sly', 'Small-thinking', 'Strict', 'Stupid',
    'Submissive', 'Superficial', 'Superstitious', 'Suspicious', 'Tasteless', 'Temperamental', 'Tense', 'Thoughtless',
    'Timid', 'Transparent', 'Treacherous', 'Troublesome', 'Unconvincing', 'Uncooperative', 'Uncreative', 'Uncritical',
    'Undisciplined', 'Unfriendly', 'Ungrateful', 'Unhealthy', 'Unimaginative', 'Unimpressive', 'Unlovable',
    'Unrealistic', 'Unreliable', 'Unstable', 'Vulnerable', 'Weak',
])

traits_field = TemplateField(name='Traits', type=TemplateFieldType.LABELS, emoji=':dna:',
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


enneagram_choices = get_selection_values(enneagram_field)
mbti_choices = get_selection_values(mbti_field)

summary_field = TemplateField('Summary', type=TemplateFieldType.SMALL_TEXT,
                              id=uuid.UUID('90112538-2eca-45e8-81b4-e3c331204e31'),
                              placeholder="Summarize your character's role in the story",
                              show_label=False)

misbelief_field = TemplateField('Misbelief', type=TemplateFieldType.SMALL_TEXT,
                                id=uuid.UUID('32feaa23-acbf-4990-b99f-429747824a0b'),
                                placeholder='The misbelief/lie the character believes in')

desire_field = TemplateField('Conscious desire', type=TemplateFieldType.SMALL_TEXT, emoji=':star-struck:',
                             placeholder='What does the character want in the story?',
                             id=uuid.UUID('eb6626ea-4d07-4b8a-80f0-d92d2fe7f1c3'))
need_field = TemplateField('Need', type=TemplateFieldType.SMALL_TEXT, emoji=':face_with_monocle:',
                           placeholder='What does the character actually need in the story?',
                           id=uuid.UUID('2adb45eb-5a6f-4958-82f1-f4ae65124322'))
weaknesses_field = TemplateField('Flaws and weaknesses', type=TemplateFieldType.SMALL_TEXT, emoji=':nauseated_face:',
                                 placeholder="What are the character's weaknesses or flaws in the story?",
                                 id=uuid.UUID('f2aa5655-88b2-41ae-a630-c7e56795a858'))
ghost_field = TemplateField('Ghost', type=TemplateFieldType.SMALL_TEXT, emoji=':ghost:',
                            placeholder="What's the character's ghost from their past than haunt them?",
                            id=uuid.UUID("12a61aa5-ffc0-4309-9b65-c6f26ab5bcf5"))
values_field = TemplateField('Values', type=TemplateFieldType.LABELS, emoji=':hugging_face:',
                             id=uuid.UUID('47e2e30e-1708-414b-be79-3413063a798d'))


class RoleImportance(Enum):
    MAJOR = 0
    SECONDARY = 1
    MINOR = 2


@dataclass
class Role(SelectionItem):
    can_be_promoted: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    promoted: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    importance: RoleImportance = RoleImportance.SECONDARY

    def is_major(self) -> bool:
        return self.importance == RoleImportance.MAJOR or self.promoted

    def is_secondary(self) -> bool:
        return self.importance == RoleImportance.SECONDARY and not self.promoted

    def is_minor(self) -> bool:
        return self.importance == RoleImportance.MINOR


protagonist_role = Role('Protagonist', icon='fa5s.chess-king', icon_color='#00798c', importance=RoleImportance.MAJOR)
deuteragonist_role = Role('Deuteragonist', icon='mdi.atom-variant', icon_color='#820b8a',
                          importance=RoleImportance.MAJOR)
antagonist_role = Role('Antagonist', icon='mdi.guy-fawkes-mask', icon_color='#bc412b', importance=RoleImportance.MAJOR)
contagonist_role = Role('Contagonist', icon='mdi.biohazard', icon_color='#ea9010')
adversary_role = Role('Adversary', icon='fa5s.thumbs-down', icon_color='#9e1946')
guide_role = Role('Guide', icon='mdi.compass-rose', icon_color='#80ced7')
confidant_role = Role('Confidant', icon='fa5s.user-friends', icon_color='#304d6d', can_be_promoted=True)
sidekick_role = Role('Sidekick', icon='ei.asl', icon_color='#b0a990', can_be_promoted=True)
love_interest_role = Role('Love Interest', icon='ei.heart', icon_color='#d1495b', can_be_promoted=True)
supporter_role = Role('Supporter', icon='fa5s.thumbs-up', icon_color='#266dd3')
foil_role = Role('Foil', icon='fa5s.yin-yang', icon_color='#947eb0', can_be_promoted=True)
secondary_role = Role('Secondary', icon='fa5s.chess-knight', icon_color='#619b8a', can_be_promoted=True)
henchmen_role = Role('Henchmen', icon='mdi.shuriken', icon_color='#596475', importance=RoleImportance.MINOR)
tertiary_role = Role('Tertiary', icon='mdi.chess-pawn', icon_color='#886f68', importance=RoleImportance.MINOR)


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
class Margins:
    left: int = 2
    top: int = 0
    right: int = 2
    bottom: int = 0


@dataclass
class ProfileElement:
    field: TemplateField
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    h_alignment: HAlignment = HAlignment.DEFAULT
    v_alignment: VAlignment = VAlignment.CENTER
    margins: Optional[Margins] = None


@dataclass
class ProfileTemplate:
    title: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    elements: List[ProfileElement] = field(default_factory=list)


def default_character_profiles() -> List[ProfileTemplate]:
    summary_title = TemplateField('Summary', type=TemplateFieldType.DISPLAY_HEADER, required=True)
    characterization_title = TemplateField('Personality', type=TemplateFieldType.DISPLAY_HEADER, required=True)
    story_title = TemplateField('Story attributes', type=TemplateFieldType.DISPLAY_HEADER)
    fields = [ProfileElement(summary_title, 0, 0, col_span=2),
              ProfileElement(summary_field, 1, 0, col_span=2, margins=Margins(left=15)),
              ProfileElement(characterization_title, 2, 0, col_span=2),
              ProfileElement(enneagram_field, 3, 0, col_span=2, margins=Margins(left=15)),
              ProfileElement(mbti_field, 4, 0, col_span=2, margins=Margins(left=15)),
              ProfileElement(traits_field, 5, 0, col_span=2, margins=Margins(left=15)),
              # ProfileElement(TemplateField('', type=TemplateFieldType.DISPLAY_LINE), 4, 0, col_span=2),
              ProfileElement(story_title, 6, 0, col_span=2),
              ProfileElement(desire_field, 7, 0, margins=Margins(left=15)),
              ProfileElement(need_field, 7, 1),
              ProfileElement(weaknesses_field, 8, 0, col_span=2, margins=Margins(left=15)),
              ProfileElement(ghost_field, 9, 0, col_span=2, margins=Margins(left=15)),
              ProfileElement(values_field, 10, 0, col_span=2, margins=Margins(left=15))
              ]
    return [ProfileTemplate(title='Default character template',
                            id=uuid.UUID('6e89c683-c132-469b-a75c-6712af7c339d'),
                            elements=fields)]


sight_field = TemplateField('Sight', type=TemplateFieldType.SMALL_TEXT,
                            id=uuid.UUID('935e6595-27ae-426e-8b41-b315e9160ad9'),
                            emoji=':eyes:',
                            placeholder='Sight')

location_name_field = TemplateField(name='Name', type=TemplateFieldType.TEXT, emoji=':round_pushpin:',
                                    placeholder='Name',
                                    id=uuid.UUID('84f9bdee-c817-4caa-9e65-666cd0c4a546'), required=True,
                                    highlighted=True, show_label=False)

smell_field = TemplateField('Smell', type=TemplateFieldType.SMALL_TEXT,
                            id=uuid.UUID('50245a33-599b-49c6-9746-094f12b4d667'),
                            emoji=':nose:',
                            placeholder='Smell')
noise_field = TemplateField('Noise', type=TemplateFieldType.SMALL_TEXT,
                            id=uuid.UUID('76659d94-8753-4945-8d5c-e811189e3b49'),
                            emoji=':speaker_high_volume:',
                            placeholder='Noise')

animals_field = TemplateField('Animals', type=TemplateFieldType.SMALL_TEXT,
                              id=uuid.UUID('3aa9cc09-312c-492a-bc19-6914bb1eeba6'),
                              emoji=':paw_prints:',
                              placeholder='Animals')
nature_field = TemplateField('Nature', type=TemplateFieldType.SMALL_TEXT,
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
