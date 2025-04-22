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

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Any, Dict, Optional

from PyQt6.QtCore import Qt
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
    def __eq__(self, other: 'SelectionItem'):
        if isinstance(other, SelectionItem):
            return self.text == other.text
        return False

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
    DISPLAY_ICON = 11
    COMPLEX = 12
    BAR = 13

    def is_display(self) -> bool:
        return self.name.startswith('DISPLAY')


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
    required: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    exclusive: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    enabled: bool = field(default=True, metadata=config(exclude=exclude_if_true))
    custom: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    min_value: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    max_value: int = 2_147_483_647
    compact: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    show_label: bool = field(default=True, metadata=config(exclude=exclude_if_true))
    color: str = field(default='', metadata=config(exclude=exclude_if_empty))
    has_notes: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))

    @overrides
    def __eq__(self, other: 'TemplateField'):
        if isinstance(other, TemplateField):
            return self.id == other.id
        return False

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
                                                          icon_color='#40D1DE',
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
                                                          icon_color='#EABE20',
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

                                       SelectionItem('INFJ', icon='ph.tree-fill', icon_color='#E5BC53'),  # yellow
                                       SelectionItem('INTJ', icon='fa5s.drafting-compass', icon_color='#E5BC53'),
                                       SelectionItem('ENFP', icon='fa5.sun', icon_color='#E5BC53'),
                                       SelectionItem('ENTP', icon='fa5.lightbulb', icon_color='#E5BC53'),

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
love_style_field = TemplateField('Love styles', TemplateFieldType.LABELS,
                                 id=uuid.UUID('dc707786-c35d-46bd-9517-6b6704cd4a88'),
                                 selections=[
                                     SelectionItem('Activity', icon='fa5s.heart', icon_color='#5e548e',
                                                   meta={
                                                       'desc': "Togetherness, engagement, shared interests",
                                                       'emoji': ':artist_palette:',
                                                   }),
                                     SelectionItem('Appreciation', icon='fa5s.heart', icon_color='#ad2831',
                                                   meta={
                                                       'desc': "Praise, recognition, words of affirmation",
                                                       'emoji': ':glowing_star:',
                                                   }),
                                     SelectionItem('Emotional', icon='fa5s.heart', icon_color='#ff0054',
                                                   meta={
                                                       'desc': "Empathy, support, emotional connection",
                                                       'emoji': ':smiling_face_with_open_hands:',
                                                   }),
                                     SelectionItem('Financial', icon='fa5s.heart', icon_color='#fb8500',
                                                   meta={
                                                       'desc': "Generosity, financial gestures, thoughtful spending",
                                                       'emoji': ':money_with_wings:',
                                                   }),
                                     SelectionItem('Intellectual', icon='fa5s.heart', icon_color='#0077b6',
                                                   meta={
                                                       'desc': "Mental connection, respect, thoughtful conversations",
                                                       'emoji': ':brain:',
                                                   }),
                                     SelectionItem('Physical', icon='fa5s.heart', icon_color='#f4a261',
                                                   meta={
                                                       'desc': "Physical intimacy, sensual experience, touch",
                                                       'emoji': ':kiss:',
                                                   }),
                                     SelectionItem('Practical', icon='fa5s.heart', icon_color='#2a9d8f',
                                                   meta={
                                                       'desc': "Everyday help, consideration, practical gestures",
                                                       'emoji': ':hammer_and_wrench:',
                                                   })
                                 ], compact=True, show_label=False)
disc_field = TemplateField('Work styles', TemplateFieldType.TEXT_SELECTION,
                           id=uuid.UUID('84adc497-aa43-47eb-aeac-148248cc1eca'),
                           selections=[
                               SelectionItem('Influence', icon='fa5s.briefcase', icon_color='#588157',
                                             meta={
                                                 'desc': "People, networking, persuasion, communication",
                                                 'emoji': ':party_popper:',
                                             }),
                               SelectionItem('Support', icon='fa5s.briefcase', icon_color='#219ebc',
                                             meta={
                                                 'desc': "Harmony, patience, team player, acceptance",
                                                 'emoji': ':handshake:',
                                             }),
                               SelectionItem('Clarity', icon='fa5s.briefcase', icon_color='#e9c46a',
                                             meta={
                                                 'desc': "Detail-oriented, precision, analytical, systematic",
                                                 'emoji': ':face_with_monocle:',
                                             }),
                               SelectionItem('Drive', icon='fa5s.briefcase', icon_color='#e63946',
                                             meta={
                                                 'desc': "Ambition, leadership, results-driven, competitive",
                                                 'emoji': ':fire:',
                                             })
                           ], compact=True, show_label=False)
positive_traits = sorted([
    'Accessible', 'Active', 'Adaptive', 'Admirable', 'Adventurous', 'Affable', 'Affectionate', 'Agreeable', 'Alert',
    'Altruistic',
    'Ambitious', 'Amusing', 'Appreciative',
    'Approachable',
    'Articulate', 'Aspiring', 'Assertive', 'Attentive', 'Balanced', 'Benevolent', 'Brave', 'Bright', 'Broad-minded',
    'Calm', 'Capable',
    'Captivating', 'Careful',
    'Caring', 'Challenging', 'Charismatic', 'Charming', 'Cheerful', 'Chivalrous', 'Clever', 'Colorful', 'Committed',
    'Communicative',
    'Compassionate',
    'Confident', 'Considerate', 'Cooperative', 'Cordial', 'Courageous', 'Creative', 'Curious', 'Daring', 'Decent',
    'Decisive',
    'Dedicated', 'Devoted', 'Dignified', 'Diplomatic', 'Disciplined', 'Discreet', 'Driven', 'Dutiful', 'Dynamic',
    'Earnest', 'Easygoing',
    'Educated', 'Efficient', 'Elegant', 'Empathetic', 'Encouraging', 'Energetic', 'Enthusiastic', 'Expressive', 'Fair',
    'Faithful', 'Flexible', 'Focused', 'Forgiving', 'Friendly', 'Gallant', 'Generous', 'Gentle', 'Genuine', 'Gracious',
    'Grateful', 'Gregarious',
    'Hard-working', 'Healthy', 'Hearty', 'Helpful', 'Honest', 'Honorable', 'Hopeful', 'Humble', 'Humorous',
    'Idealistic',
    'Imaginative', 'Impressive', 'Incorruptible', 'Independent', 'Individualistic', 'Innovative', 'Insightful',
    'Inspiring',
    'Intelligent', 'Intuitive', 'Invulnerable', 'Just', 'Kind', 'Knowledgeable', 'Leaderly', 'Lively', 'Logical',
    'Lovable',
    'Loyal',
    'Mature', 'Methodical', 'Meticulous', 'Moderate', 'Modest', 'Neat', 'Objective', 'Observant', 'Open', 'Optimistic',
    'Orderly', 'Organized', 'Original', 'Passionate', 'Patient', 'Peaceful', 'Perceptive',
    'Persuasive', 'Playful', 'Popular', 'Powerful', 'Practical', 'Pragmatic', 'Precise', 'Principled', 'Proactive',
    'Protective',
    'Punctual',
    'Purposeful', 'Rational', 'Realistic', 'Reflective', 'Relaxed', 'Reliable', 'Resourceful', 'Respectful',
    'Responsible', 'Responsive', 'Romantic', 'Sane', 'Scholarly', 'Secure', 'Selfless', 'Self-aware', 'Self-critical',
    'Sensible',
    'Sensitive', 'Sentimental', 'Serious', 'Sharing', 'Sincere', 'Skillful', 'Sociable', 'Solid', 'Sophisticated',
    'Spontaneous', 'Straightforward',
    'Structured', 'Supportive', 'Sweet', 'Sympathetic', 'Systematic', 'Tactful', 'Thorough', 'Tolerant', 'Tough',
    'Truthful',
    'Trustworthy',
    'Understanding', 'Unselfish', 'Upright', 'Versatile', 'Vivacious', 'Warm', 'Wise', 'Witty', 'Youthful', 'Zany',
    'Zealous'
])

negative_traits = sorted([
    'Abrasive', 'Abrupt', 'Aimless', 'Aloof', 'Amoral', 'Angry', 'Anxious', 'Apathetic', 'Argumentative', 'Arrogant',
    'Artificial', 'Asocial', 'Belligerent', 'Bewildered', 'Bizarre', 'Bland', 'Blunt', 'Bossy', 'Brutal',
    'Calculating',
    'Callous',
    'Careless', 'Cautious', 'Charmless', 'Childish', 'Clumsy', 'Cold', 'Colorless', 'Compulsive', 'Confused',
    'Conventional', 'Confrontational', 'Cowardly', 'Crazy', 'Critical', 'Crude', 'Cruel', 'Cunning', 'Cynical',
    'Deceitful',
    'Demanding', 'Dependent', 'Desperate', 'Destructive', 'Devious', 'Difficult', 'Discouraging', 'Dishonest',
    'Disloyal', 'Disobedient', 'Disorderly', 'Disorganized', 'Disrespectful', 'Disruptive', 'Disturbing', 'Dull',
    'Egocentric', 'Envious', 'Erratic', 'Evasive', 'Extravagant', 'Extreme', 'Faithless', 'False', 'Fanatical',
    'Fearful', 'Fickle',
    'Flamboyant', 'Foolish', 'Forgetful', 'Fraudulent', 'Frightening', 'Frivolous', 'Gloomy', 'Greedy', 'Grim',
    'Grumpy', 'Gullible', 'Harsh',
    'Hateful', 'Hesitant', 'Hypocritical', 'Ignorant', 'Ill-mannered', 'Image-conscious', 'Impatient', 'Impractical',
    'Imprudent',
    'Impulsive', 'Inconsiderate', 'Incurious', 'Indecisive', 'Indulgent', 'Insecure', 'Insensitive', 'Insincere',
    'Insulting', 'Intolerant', 'Irrational', 'Irresponsible', 'Irritable', 'Isolated', 'Jealous', 'Judgmental',
    'Killjoy', 'Lazy',
    'Malicious', 'Manipulative', 'Mannered', 'Materialistic', 'Mean', 'Moody', 'Naive', 'Narcissistic', 'Narrow-minded',
    'Negative',
    'Neglectful',
    'Nihilistic', 'Obnoxious',
    'Obsessive', 'One-dimensional', 'Opinionated', 'Oppressed', 'Outrageous', 'Paranoid', 'Passive', 'Patronizing',
    'Perfectionist', 'Pessimistic', 'Petty', 'Petulant',
    'Pompous', 'Possessive', 'Prejudiced', 'Pretentious', 'Procrastinating', 'Quick-tempered', 'Quirky', 'Rash',
    'Reckless',
    'Regretful',
    'Repressed',
    'Resentful', 'Ridiculous', 'Rigid', 'Rude', 'Sadistic', 'Scheming', 'Scornful', 'Selfish', 'Self-centered',
    'Self-indulgent',
    'Shortsighted', 'Shameless', 'Shy', 'Silly', 'Single-minded', 'Sloppy', 'Slow', 'Sly', 'Small-thinking', 'Sneaky',
    'Strict',
    'Stubborn',
    'Stupid', 'Submissive', 'Superficial', 'Superstitious', 'Suspicious', 'Tactless', 'Tasteless', 'Temperamental',
    'Tense',
    'Thoughtless',
    'Timid', 'Transparent', 'Treacherous', 'Troublesome', 'Unconvincing', 'Uncooperative', 'Uncreative', 'Uncritical',
    'Undisciplined', 'Unfriendly', 'Ungrateful', 'Unhealthy', 'Unimaginative', 'Unimpressive', 'Unlovable',
    'Unrealistic', 'Unreliable', 'Unstable', 'Vain', 'Vengeful', 'Vulnerable', 'Weak', 'Withdrawn'
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


enneagram_choices: Dict[str, SelectionItem] = get_selection_values(enneagram_field)
mbti_choices: Dict[str, SelectionItem] = get_selection_values(mbti_field)
love_style_choices: Dict[str, SelectionItem] = get_selection_values(love_style_field)
work_style_choices: Dict[str, SelectionItem] = get_selection_values(disc_field)

summary_field = TemplateField('Summary', type=TemplateFieldType.SMALL_TEXT,
                              id=uuid.UUID('90112538-2eca-45e8-81b4-e3c331204e31'),
                              placeholder="Summarize your character's role in the story",
                              show_label=False)

desire_field = TemplateField('Desire', type=TemplateFieldType.SMALL_TEXT, emoji=':star-struck:',
                             placeholder='What does the character want?',
                             id=uuid.UUID('eb6626ea-4d07-4b8a-80f0-d92d2fe7f1c3'))

goal_field = TemplateField('External goal', type=TemplateFieldType.SMALL_TEXT, emoji=':bullseye:',
                           description="Tangible objectives pursued by the character",
                           placeholder="What tangible, external goal does the character want to accomplish?",
                           id=uuid.UUID('99526331-6f3b-429d-ad22-0a4a90ee9d77'), has_notes=True,
                           icon='mdi.target')
internal_goal_field = TemplateField('Internal goal', type=TemplateFieldType.SMALL_TEXT,
                                    emoji=':smiling_face_with_hearts:',
                                    description="Emotional or psychological desires and growth pursued by the character",
                                    placeholder="What emotional state does the character want to achieve?",
                                    id=uuid.UUID('090d2431-3ae7-4aa3-81b3-2737a8043db7'), has_notes=True,
                                    icon='ri.user-heart-line')
motivation_field = TemplateField('Motivation', type=TemplateFieldType.SMALL_TEXT, emoji=':right-facing_fist:',
                                 placeholder='What practical or situational reason drives the character to accomplish their goal?',
                                 id=uuid.UUID('5aa2c2e6-90a6-42b2-af7b-b4c82a56390e'), has_notes=True)
internal_motivation_field = TemplateField('Internal motivation', type=TemplateFieldType.SMALL_TEXT, emoji=':red_heart:',
                                          placeholder='What deeper, often subconscious, reason drives the character?',
                                          id=uuid.UUID('6388368e-6d52-4259-b1e2-1d9c1aa5c89d'), has_notes=True)
conflict_field = TemplateField('Conflict', type=TemplateFieldType.SMALL_TEXT, emoji=':crossed_swords:',
                               placeholder='What external force is stopping the character from their goal?',
                               id=uuid.UUID('c7e39f6d-4b94-4060-b3a6-d2604247ca80'), has_notes=True)
internal_conflict_field = TemplateField('Internal conflict', type=TemplateFieldType.SMALL_TEXT, emoji=':fearful_face:',
                                        placeholder='What emotional, mental, or psychological barriers hold back the character?',
                                        id=uuid.UUID('8dcf6ce1-6679-4100-b332-8898ee2a2e3c'), has_notes=True)
stakes_field = TemplateField('Stakes', type=TemplateFieldType.SMALL_TEXT, emoji=':skull:',
                             placeholder="What could the character lose in the physical world if they fail to reach their goal?",
                             id=uuid.UUID('15770e28-b801-44c4-a6e6-ddba33935bc4'), has_notes=True)
internal_stakes_field = TemplateField('Internal stakes', type=TemplateFieldType.SMALL_TEXT, emoji=':broken_heart:',
                                      placeholder="What could the character lose emotionally or psychologically?",
                                      id=uuid.UUID('95f58293-c77a-4ec7-9e1f-b2f38d123e8d'), has_notes=True)
methods_field = TemplateField('Methods', type=TemplateFieldType.SMALL_TEXT, emoji=':hammer_and_pick:',
                              placeholder="How does the character try to achieve their goals?",
                              id=uuid.UUID('40d50e34-8dbf-4491-8fa9-854f060be5ef'), has_notes=True)
weaknesses_field = TemplateField('Weakness', type=TemplateFieldType.SMALL_TEXT, emoji=':nauseated_face:',
                                 placeholder="What are the character's weaknesses in the story?",
                                 id=uuid.UUID('f2aa5655-88b2-41ae-a630-c7e56795a858'))
strength_field = TemplateField('Strength', type=TemplateFieldType.SMALL_TEXT, emoji=':smiling_face_with_sunglasses:',
                               placeholder="What are the character's strengths in the story?",
                               id=uuid.UUID('4bc4269d-9ce7-47cf-aa65-23e7f8b1a250'))
void_field = TemplateField('Void', type=TemplateFieldType.SMALL_TEXT, emoji=':new_moon:',
                           description="An emptiness or absence the character feels in their life that drives their actions",
                           placeholder='What deep emptiness or absence does the character feel in their life?',
                           id=uuid.UUID('de65f5b9-06fd-481e-a75a-f8dc2990717c'), icon='fa5s.circle')
psychological_need_field = TemplateField('Psychological need', type=TemplateFieldType.SMALL_TEXT, emoji=':old_key:',
                                         description="An often subconscious internal struggle the character must overcome to achieve personal growth",
                                         placeholder='What personal flaw must the character overcome to achieve emotional or psychological growth?',
                                         id=uuid.UUID('2adb45eb-5a6f-4958-82f1-f4ae65124322'), icon='ri.key-fill')
interpersonal_need_field = TemplateField('Interpersonal need', type=TemplateFieldType.SMALL_TEXT, emoji=':handshake:',
                                         description="The character's growth in how they relate to others and improve their relationships",
                                         placeholder='What changes must the character make build healthier connections with others?',
                                         id=uuid.UUID('a9b9b418-a4ab-479e-a0f4-155c663575f2'),
                                         icon='fa5s.handshake')

values_field = TemplateField('Values', type=TemplateFieldType.LABELS, emoji=':smiling_face_with_open_hands:',
                             id=uuid.UUID('47e2e30e-1708-414b-be79-3413063a798d'))

baggage_field = TemplateField('Baggage', type=TemplateFieldType.COMPLEX,
                              id=uuid.UUID('b3e591ba-ce55-43c2-a4b0-f35864693977'))
ghost_field = TemplateField('Ghost', type=TemplateFieldType.SMALL_TEXT, emoji=':ghost:',
                            description="Unresolved issues from the character's past",
                            placeholder="What internal conflicts or unresolved issues haunt them from the past?",
                            id=uuid.UUID("12a61aa5-ffc0-4309-9b65-c6f26ab5bcf5"),
                            icon='mdi6.ghost')
wound_field = TemplateField('Wound', type=TemplateFieldType.SMALL_TEXT, emoji=':broken_heart:',
                            description="Emotional trauma and wound",
                            placeholder='What past event harmed the character and left an emotional wound?',
                            id=uuid.UUID('587cace8-0326-4895-b51e-de1d92b9db1b'),
                            icon='fa5s.heart-broken')
fear_field = TemplateField('Fear', type=TemplateFieldType.SMALL_TEXT, emoji=':fearful_face:',
                           description="Deeply rooted anxieties or apprehensions",
                           placeholder='What does the character fear as a result of their past?',
                           id=uuid.UUID('9601abef-c568-4ef6-9ff9-8da2e62e0572'),
                           icon='ri.ghost-2-fill')
demon_field = TemplateField('Demon', type=TemplateFieldType.SMALL_TEXT, emoji=':angry_face_with_horns:',
                            description="Deeply seated negative traits, vices, internal conflict",
                            placeholder="What deep-seated traits, fears, vices, internal conflict plague the character?",
                            id=uuid.UUID('66f5424d-f631-481f-872e-cb3ac85f8ec0'),
                            icon='mdi.emoticon-devil')
misbelief_field = TemplateField('Misbelief', type=TemplateFieldType.SMALL_TEXT, emoji=':exploding_head:',
                                description="A false view the character developed about themselves or about the world",
                                id=uuid.UUID('32feaa23-acbf-4990-b99f-429747824a0b'),
                                placeholder='What false view did the character develop about themselves or the world?',
                                icon='mdi.head-question-outline')
baggage_source_field = TemplateField('Source', type=TemplateFieldType.SMALL_TEXT, emoji=':seedling:',
                                     placeholder="What's the origin, the root cause of the character's baggage?",
                                     id=uuid.UUID('936b7ab4-d72c-42af-a485-32e03c89da85'))
baggage_defense_mechanism_field = TemplateField('Defense mechanism', type=TemplateFieldType.SMALL_TEXT,
                                                emoji=':shield:',
                                                placeholder="Unconsciously, what defense did the character deploy to protect themselves?",
                                                id=uuid.UUID('72794fb2-fc52-4266-b8e9-957778ccebdc'))

baggage_trigger_field = TemplateField('Trigger', type=TemplateFieldType.SMALL_TEXT, emoji=':high_voltage:',
                                      placeholder="What could trigger and aggravate the character's baggage?",
                                      id=uuid.UUID('1a7b45ee-29d4-4e69-a177-0f8804a93b78'))
baggage_healing_field = TemplateField('Healing', type=TemplateFieldType.SMALL_TEXT, emoji=':syringe:',
                                      placeholder='How could the character heal their baggage?',
                                      id=uuid.UUID('13ccb707-07bc-4567-9ae0-93da65b7f6e7'))

baggage_relation_field = TemplateField('Impact on relationships', type=TemplateFieldType.SMALL_TEXT,
                                       emoji=':broken_heart:',
                                       placeholder="How does the baggage impact the character's relationships?",
                                       id=uuid.UUID('5072c423-b5ae-4ac2-a108-142edcb3ec2f'))
baggage_manifestation_field = TemplateField('Manifestation', type=TemplateFieldType.SMALL_TEXT,
                                            emoji=':eyes:',
                                            placeholder="How is the character's baggage expressed outwardly through behaviour, habits, or else?",
                                            id=uuid.UUID('21d5234c-ed5d-42ee-aac7-aa9030e7abf9'))
baggage_coping_field = TemplateField('Coping', type=TemplateFieldType.SMALL_TEXT, emoji=':downcast_face_with_sweat:',
                                     placeholder="How does the character try to cope with their baggage?",
                                     id=uuid.UUID('f4e5afaf-4a62-43ec-9714-301ad7c4feb2'))
baggage_deterioration_field = TemplateField('Deterioration', type=TemplateFieldType.SMALL_TEXT,
                                            placeholder="How could the baggage progressively become worse?",
                                            emoji=':smiling_face_with_horns:',
                                            id=uuid.UUID('d66d65bd-ddaf-40ba-be8e-fa7dcbaa313c'))

strengths_weaknesses_field = TemplateField('Strengths and weaknesses', type=TemplateFieldType.COMPLEX,
                                           id=uuid.UUID('9cf11007-c032-46f9-a550-e238cb807714'))
flaw_placeholder_field = TemplateField('Flaw', TemplateFieldType.TEXT, emoji=':angry_face_with_horns:',
                                       placeholder="Describe the flaw that the character has",
                                       id=uuid.UUID('9d65ec96-fb07-4997-b9d4-3b2b4155ee5d'),
                                       icon='mdi.virus')
flaw_relation_field = TemplateField('Impact on relationships', type=TemplateFieldType.SMALL_TEXT,
                                    emoji=':broken_heart:',
                                    placeholder="How does the flaw impact the character's relationships?",
                                    id=uuid.UUID('bad8336e-631a-4af4-a6dd-d0d4349def3f'))
flaw_manifestation_field = TemplateField('Manifestation', type=TemplateFieldType.SMALL_TEXT,
                                         emoji=':eyes:',
                                         placeholder="How is the flaw expressed outwardly through behaviour, habits, or else?",
                                         id=uuid.UUID('b23f9492-7c1d-4aee-adfa-417cc7584486'))
flaw_coping_field = TemplateField('Coping', type=TemplateFieldType.SMALL_TEXT, emoji=':downcast_face_with_sweat:',
                                  placeholder="How does the character try to cope with the flaw?",
                                  id=uuid.UUID('99de6162-186e-4fb4-bbb8-28a80c2220bf'))
flaw_triggers_field = TemplateField('Triggers', type=TemplateFieldType.SMALL_TEXT, emoji=':police_car_light:',
                                    placeholder="What situations can trigger the flaw to resurface or intensify?",
                                    id=uuid.UUID('afabeeb6-0cb0-465b-845c-76e3755e761a'))
flaw_goals_field = TemplateField('Impact on goals', type=TemplateFieldType.SMALL_TEXT, emoji=':bullseye:',
                                 placeholder="How does the flaw impact the character's goals?",
                                 id=uuid.UUID('eb0c550b-b531-4295-b5a0-e88a2d330c06'))
flaw_growth_field = TemplateField('Potential growth', type=TemplateFieldType.SMALL_TEXT,
                                  emoji=':smiling_face_with_halo:',
                                  placeholder="How could the character grow and overcome their flaw?",
                                  id=uuid.UUID('6862fa7b-f33c-4de8-834e-ae172f0c5a74'))
flaw_deterioration_field = TemplateField('Deterioration', type=TemplateFieldType.SMALL_TEXT,
                                         placeholder="How could the flaw progressively become worse?",
                                         emoji=':smiling_face_with_horns:',
                                         id=uuid.UUID('6988b841-1d0e-4df5-9a80-13113a77228c'))

flaws_field = TemplateField('Flaws', type=TemplateFieldType.COMPLEX,
                            id=uuid.UUID('561900fb-3061-4735-ac9f-d87571131392'))

positive_arc = TemplateField('Positive arc', type=TemplateFieldType.SMALL_TEXT, emoji=':smiling_face_with_halo:',
                             placeholder='How does the character change positively?',
                             id=uuid.UUID('d0feee5d-c40b-4615-9aa0-78a6071f8ce7'))
negative_arc = TemplateField('Negative arc', type=TemplateFieldType.SMALL_TEXT, emoji=':smiling_face_with_horns:',
                             placeholder='How does the character change negatively?',
                             id=uuid.UUID('fcd1d4b7-d431-4460-b480-56bc9226a29d'))

values_items = [SelectionItem('Altruism', icon='fa5s.hand-holding-heart'),
                SelectionItem('Authenticity', icon='mdi6.certificate'),
                SelectionItem('Adventure', icon='mdi6.snowboard'),
                SelectionItem('Authority', icon='ri.government-fill'),
                SelectionItem('Autonomy', icon='fa5s.fist-raised'),
                SelectionItem('Balance', icon='fa5s.balance-scale'),
                SelectionItem('Beauty', icon='mdi6.butterfly'), SelectionItem('Bravery', icon='mdi.sword'),
                SelectionItem('Compassion', icon='mdi6.hand-heart'),
                SelectionItem('Citizenship', icon='mdi.passport'), SelectionItem('Community', icon='ei.group-alt'),
                SelectionItem('Competency', icon='fa5s.user-cog'),
                SelectionItem('Contribution', icon='fa5s.hand-holding-usd'),
                SelectionItem('Creativity', icon='mdi.head-lightbulb-outline'),
                SelectionItem('Curiosity', icon='ei.question-sign'),
                SelectionItem('Dignity', icon='fa5.handshake'), SelectionItem('Equality', icon='ri.scales-fill'),
                SelectionItem('Faith', icon='fa5s.hands'),
                SelectionItem('Fame', icon='ei.star-alt'), SelectionItem('Family', icon='mdi6.human-male-female-child'),
                SelectionItem('Forgiveness', icon='fa5s.hand-peace'),
                SelectionItem('Friendships', icon='fa5s.user-friends'), SelectionItem('Fun', icon='fa5s.football-ball'),
                SelectionItem('Generosity', icon='fa5s.gift'),
                SelectionItem('Growth', icon='fa5s.seedling'),
                SelectionItem('Happiness', icon='mdi.emoticon-happy-outline'),
                SelectionItem('Harmony', icon='mdi6.yin-yang'),
                SelectionItem('Honesty', icon='mdi.mother-heart'),
                SelectionItem('Honour', icon='fa5s.award'), SelectionItem('Humor', icon='fa5.laugh-squint'),
                SelectionItem('Independence', icon='fa.chain-broken'),
                SelectionItem('Integrity', icon='mdi.shield-link-variant'), SelectionItem('Justice', icon='mdi.gavel'),
                SelectionItem('Kindness', icon='mdi.balloon'),
                SelectionItem('Knowledge', icon='fa5s.book'),
                SelectionItem('Leadership', icon='fa5b.font-awesome-flag'),
                SelectionItem('Learning', icon='mdi6.book-education-outline'),
                SelectionItem('Love', icon='fa5s.heart'), SelectionItem('Loyalty', icon='fa5s.dog'),
                SelectionItem('Nature', icon='mdi.tree'),
                SelectionItem('Openness', icon='mdi.lock-open-variant'),
                SelectionItem('Optimism', icon='mdi6.white-balance-sunny'), SelectionItem('Peace', icon='fa5s.dove'),
                SelectionItem('Pleasure', icon='mdi.cupcake'),
                SelectionItem('Popularity', icon='fa5s.thumbs-up'), SelectionItem('Recognition', icon='ri.award-fill'),
                SelectionItem('Religion', icon='fa5s.praying-hands'),
                SelectionItem('Reputation', icon='fa5s.star'), SelectionItem('Respect', icon='ph.handshake-bold'),
                SelectionItem('Responsibility', icon='fa5s.hand-holding-water'),
                SelectionItem('Security', icon='mdi.security'), SelectionItem('Service', icon='mdi.room-service'),
                SelectionItem('Spirituality', icon='mdi6.meditation'),
                SelectionItem('Stability', icon='fa.balance-scale'),
                SelectionItem('Success', icon='fa5s.money-bill'),
                SelectionItem('Sustainability', icon='fa5s.leaf'), SelectionItem('Status', icon='mdi6.crown-circle'),
                SelectionItem('Trustworthiness', icon='fa5s.stamp'),
                SelectionItem('Wealth', icon='fa5s.coins'), SelectionItem('Wisdom', icon='mdi.owl')]
values_field.selections.extend(values_items)

iq_field = TemplateField(name='IQ', type=TemplateFieldType.BAR,
                         id=uuid.UUID('a27f2534-9933-4fc9-a70b-0f4f4480d619'), emoji=':brain:',
                         min_value=0, max_value=100, placeholder='IQ', color='#0077b6')

eq_field = TemplateField(name='Emotional intelligence', type=TemplateFieldType.BAR,
                         id=uuid.UUID('b2452206-05af-44c9-8908-4d4ff1f669ba'), emoji=':handshake:',
                         min_value=0, max_value=100, placeholder='EQ', color='#2a9d8f')

rationalism_field = TemplateField(name='Rationalism', type=TemplateFieldType.BAR,
                                  id=uuid.UUID('90bf2da5-d2f1-426d-9b0e-6a25859851b6'), emoji=':face_with_monocle:',
                                  min_value=0, max_value=100, placeholder='Rationalism', color='#b7b7a4')

creativity_field = TemplateField(name='Creativity', type=TemplateFieldType.BAR,
                                 id=uuid.UUID('4ba586c3-1ad0-4fef-9a7a-bd11d90b268c'), emoji=':artist_palette:',
                                 min_value=0, max_value=100, placeholder='Creativity', color='#9f86c0')

willpower_field = TemplateField(name='Willpower', type=TemplateFieldType.BAR,
                                id=uuid.UUID('ea8fb07d-d9ad-4f49-b8d1-4d2ec29343b5'), emoji=':fire:',
                                min_value=0, max_value=100, placeholder='Willpower', color='#f6bd60')


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

    @overrides
    def __eq__(self, other: 'Role'):
        if isinstance(other, Role):
            return self.text == other.text
        return False

    @overrides
    def __hash__(self):
        return hash(self.text)


protagonist_role = Role('Protagonist', icon='fa5s.chess-king', icon_color='#00798c', importance=RoleImportance.MAJOR)
deuteragonist_role = Role('Deuteragonist', icon='mdi.atom-variant', icon_color='#820b8a',
                          importance=RoleImportance.MAJOR)
antagonist_role = Role('Antagonist', icon='mdi.guy-fawkes-mask', icon_color='#bc412b', importance=RoleImportance.MAJOR)
contagonist_role = Role('Contagonist', icon='mdi.biohazard', icon_color='#ea9010', can_be_promoted=True)
adversary_role = Role('Adversary', icon='fa5s.thumbs-down', icon_color='#9e1946')
guide_role = Role('Guide', icon='mdi.compass-rose', icon_color='#80ced7')
confidant_role = Role('Confidant', icon='fa5s.user-friends', icon_color='#304d6d')
sidekick_role = Role('Sidekick', icon='ei.asl', icon_color='#b0a990')
love_interest_role = Role('Love Interest', icon='ei.heart', icon_color='#d1495b', can_be_promoted=True)
supporter_role = Role('Supporter', icon='fa5s.thumbs-up', icon_color='#266dd3')
foil_role = Role('Foil', icon='fa5s.yin-yang', icon_color='#947eb0', can_be_promoted=True)
secondary_role = Role('Secondary', icon='fa5s.chess-knight', icon_color='#619b8a', can_be_promoted=True)
major_role = Role('Major', icon='fa5s.chess-rook', icon_color='#00798c', importance=RoleImportance.MAJOR)
henchmen_role = Role('Heckler', icon='mdi.shuriken', icon_color='#596475', importance=RoleImportance.MINOR)
tertiary_role = Role('Tertiary', icon='mdi.chess-pawn', icon_color='#886f68', importance=RoleImportance.MINOR)


def promote_role(role: Role):
    if not role.can_be_promoted:
        return

    if role == secondary_role:
        role.icon = deuteragonist_role.icon
        role.icon_color = deuteragonist_role.icon_color
    elif role == love_interest_role:
        role.icon = 'mdi.heart-multiple'
        role.icon_color = '#b22d3e'
    elif role == contagonist_role:
        role.icon = 'fa5s.biohazard'
    elif role == foil_role:
        role.icon = deuteragonist_role.icon
        role.icon_color = '#7D639F'


def demote_role(role: Role):
    if not role.can_be_promoted:
        return
    if role == secondary_role:
        role.icon = secondary_role.icon
        role.icon_color = secondary_role.icon_color
    elif role == love_interest_role:
        role.icon = love_interest_role.icon
        role.icon_color = love_interest_role.icon_color
    elif role == contagonist_role:
        role.icon = contagonist_role.icon
    elif role == foil_role:
        role.icon = foil_role.icon
        role.icon_color = foil_role.icon_color


class HAlignment(Enum):
    DEFAULT = 0
    LEFT = Qt.AlignmentFlag.AlignLeft
    RIGHT = Qt.AlignmentFlag.AlignRight
    CENTER = Qt.AlignmentFlag.AlignHCenter
    JUSTIFY = Qt.AlignmentFlag.AlignJustify


class VAlignment(Enum):
    TOP = Qt.AlignmentFlag.AlignTop
    BOTTOM = Qt.AlignmentFlag.AlignBottom
    CENTER = Qt.AlignmentFlag.AlignVCenter


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
    v_alignment: VAlignment = VAlignment.TOP
    margins: Optional[Margins] = None


@dataclass
class ProfileTemplate:
    title: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    elements: List[ProfileElement] = field(default_factory=list)
