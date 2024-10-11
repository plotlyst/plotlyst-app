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
from typing import Optional, Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget
from qthandy import vbox, vspacer

from plotlyst.core.domain import Character, Topic, TemplateValue, TopicType
from plotlyst.view.common import push_btn, scrolled
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.topic import TopicsEditor, TopicSelectionDialog

topics: Dict[TopicType, List[Topic]] = {
    TopicType.Physical: [
        Topic('Clothing', TopicType.Physical, uuid.UUID('4572a00f-9039-43a1-8eb9-8abd39fbec32'), 'fa5s.tshirt',
              description='Usual clothing style, favourite accessories, etc.'),
        Topic('Marks or scars', TopicType.Physical, uuid.UUID('088ae5e0-99f8-4308-9d77-3daa624ca7a3'),
              'mdi.bandage',
              description='Any distinguishable marks or scars'),
        Topic('Hairstyle', TopicType.Physical, uuid.UUID('88225a8f-76c7-42ba-9abc-cc2041581c6e'),
              'mdi.hair-dryer-outline',
              description='The hairstyle of the character'),
        Topic('Facial features', TopicType.Physical, uuid.UUID('fbc31cca-6722-490b-b5f8-fbc995f33c0c'),
              'mdi.face-recognition',
              description="Describe the character's facial structure or any peculiar features"),
        Topic('Eyes and gaze', TopicType.Physical, uuid.UUID('683537ee-4b5a-4fae-9cea-65ffd2aa7e17'),
              'ph.smiley-x-eyes',
              description="Describe the color of their eyes and how often they avert or hold eye contact"),
        Topic('Tattoos', TopicType.Physical, uuid.UUID('5c39da51-41c3-4363-9d74-7a7f92fb9d18'),
              'ri.ink-bottle-line',
              description="Describe any tattoos or piercings that character has"),
        Topic('Height and build', TopicType.Physical, uuid.UUID('22fdba94-aed2-45f4-bf9b-4452d0b69d16'),
              'mdi6.human-male-height-variant',
              description="Height, weight, and body type (slim, athletic, obese, etc.)"),
        Topic('Grooming style', TopicType.Physical, uuid.UUID('8a546a2b-24c1-4224-b6dd-53e284fb8d90'),
              'mdi.mustache',
              description="Facial hair, hygiene, skincare"),
        Topic('Gait', TopicType.Physical, uuid.UUID('24622007-1db5-4927-b813-f915612df528'),
              'fa5s.walking',
              description="How does the character walk?"),
    ],
    TopicType.Habits: [
        Topic('Fitness', TopicType.Habits, uuid.UUID('0e3e6e19-b284-4f7d-85ef-ce2ba047743c'),
              'mdi.dumbbell', description="How fit is the character?"),
        Topic('Dietary habits', TopicType.Habits, uuid.UUID('923a808b-ddac-4b78-82b8-5b4f27451130'),
              'mdi.food',
              description="What does the character eat? Any preferences or restrictions?"),
        Topic('Working habits', TopicType.Habits, uuid.UUID('f95e380b-1c52-4884-a710-a5b26dd8e3fd'),
              'mdi.desk-lamp',
              description="How does the character approach working hours or studies?"),
        Topic('Superstitions', TopicType.Habits, uuid.UUID('21c638b4-a62c-4520-b827-233cfa3d693d'),
              'fa5s.cat',
              description="Describe any known superstitions"),
        Topic('Morning routines', TopicType.Habits, uuid.UUID('a8071d76-2f6e-4ae6-bcb1-e69a6a6658cf'),
              'ph.sun',
              description="Does the character follow a specific morning routine?"),
        Topic('Evening routines', TopicType.Habits, uuid.UUID('91dd8a0c-0fa6-4cf1-a076-a6d8447711fa'),
              'mdi6.weather-night-partly-cloudy',
              description="Does the character follow a specific evening routine?"),
        Topic('Daily rituals', TopicType.Habits, uuid.UUID('a3334c82-4991-48d5-8607-1dd6a2501d5f'),
              'fa5.calendar-alt',
              description="Any known daily rituals the character follow"),
        Topic('Bad or toxic habits', TopicType.Habits, uuid.UUID('ed55fb8c-4f1a-42b0-a8cc-a4383f4302e2'),
              'mdi.smoking',
              description="Describe any bad or toxic habits that character may have"),
    ],
    TopicType.Skills: [
        Topic('Art and creativity', TopicType.Skills, uuid.UUID('18087847-18c7-420e-a683-90144e73385b'),
              'fa5s.palette',
              description="Describes the character's proficiency and interest in art"),
        Topic('Technical skills', TopicType.Skills, uuid.UUID('5d591970-224d-4507-89f7-759a40c84463'),
              'fa5s.wrench',
              description="Does the character handle technical areas?"),
        Topic('Linguistic abilities', TopicType.Skills, uuid.UUID('124cad31-b431-41fa-bfdb-4a13923cf2e3'),
              'ph.speaker-simple-high-light',
              description="How well the character communicates?"),
        Topic('Musical talents', TopicType.Skills, uuid.UUID('c7a6e418-04b7-4828-84da-297df0c4031e'),
              'fa5s.music',
              description="Can the character play any instrument?"),
        Topic('Leadership qualities', TopicType.Skills, uuid.UUID('eb28ddae-c68a-440e-b188-a5e7cc67bb5e'),
              'mdi.podium-gold',
              description="Can the character lead, guide, or inspire others?"),
        Topic('Emotional intelligence', TopicType.Skills, uuid.UUID('163000d6-29d0-4f39-be91-35c1da594617'),
              'mdi.head-heart-outline',
              description="Can the character understand, manage, and navigate their own and others' emotions?"),
        Topic('Analytical thinking', TopicType.Skills, uuid.UUID('addae2f5-2da4-4f2b-9856-390ad8516d54'),
              'mdi.head-cog-outline',
              description="Can the character analyze information, solve problems, and think critically?"),
        Topic('Adaptability', TopicType.Skills, uuid.UUID('c0972d75-cdd5-4006-9943-5ec0c4102d9d'),
              'mdi.head-sync-outline',
              description="Can the character adapt to new situations?"),
        Topic('Public speaking', TopicType.Skills, uuid.UUID('228fa06d-1e50-4ecf-922c-9b8623e08ef1'),
              'ph.megaphone-fill',
              description="How well can the character speak publicly?"),
        Topic('Athleticism', TopicType.Skills, uuid.UUID('43eb10df-2022-4d7b-b734-05b7fc836127'),
              'mdi.weight-lifter',
              description="Any proficiency in sports or any physical activities?"),
    ],
    TopicType.Fears: [
        Topic('Social', TopicType.Fears, uuid.UUID('8bda952a-cc7a-49f3-8cad-49d1d8194c3a'),
              'ri.ghost-2-fill',
              description="Fears related to social interactions and situations"),
        Topic('Environmental', TopicType.Fears, uuid.UUID('03efeb54-fc9d-4446-bdf4-714b3166986f'),
              'ri.ghost-2-fill',
              description="Fears related to the environment, e.g., heights, darkness, confined spaces"),
        Topic('Performance', TopicType.Fears, uuid.UUID('280ea481-e444-401e-ac01-4f063b009571'),
              'ri.ghost-2-fill',
              description="Fear of failure, criticism, not meeting expectations"),
        Topic('Commitment', TopicType.Fears, uuid.UUID('b4edee5e-455b-4ceb-96b8-055073d6db51'),
              'ri.ghost-2-fill',
              description="Fear of long-term commitment and obligations, e.g., relationships or responsibilities"),
        Topic('Health and safety', TopicType.Fears, uuid.UUID('38bef5cb-a728-4830-a683-593fe0d25f68'),
              'ri.ghost-2-fill',
              description="Fears related to personal health and safety"),
        Topic('Change and uncertainty', TopicType.Fears, uuid.UUID('448303eb-42ce-411a-8f8e-525fdeee4719'),
              'ri.ghost-2-fill',
              description="Fears related to change, unpredictability, and the unknown"),
        Topic('Existential', TopicType.Fears, uuid.UUID('b7fda0c7-08cc-458e-abf5-5d052be71733'),
              'ri.ghost-2-fill',
              description="Fears related to existential questions and concerns about life and death, e.g., meaninglessness or mortality"),
        Topic('Relationship', TopicType.Fears, uuid.UUID('b06e599f-6457-4af3-a5f2-27f0888e8f29'),
              'ri.ghost-2-fill',
              description="Fear of betrayal, intimacy, heartbreak and disappointments, or being unloved"),
        Topic('Isolation and abandonment', TopicType.Fears, uuid.UUID('051dcd55-7e32-4028-9580-823f2ffd5bd7'),
              'ri.ghost-2-fill',
              description="Fears related to loneliness, isolation, or being abandoned"),
        Topic('Technology and future', TopicType.Fears, uuid.UUID('90fad66c-a12d-4fcd-867f-18bef98f1db1'),
              'ri.ghost-2-fill',
              description="Fear of technology, AI and their impact, e.g., obsolescence"),
        Topic('Phobias', TopicType.Fears, uuid.UUID('fc1695c0-2155-4b5b-b8dd-d9961c8b7e5d'),
              'ri.ghost-2-fill',
              description="Specific phobias: spiders, snakes, flying, enclosed spaces, etc."),
    ],
    TopicType.Background: [
        Topic('Cultural heritage', TopicType.Background,
              uuid.UUID('0304fca3-47b0-4c50-a502-27a4da6a095f'),
              'mdi.balloon',
              description="Cultural traditions, customs, and values"),
        Topic('Family dynamics', TopicType.Background,
              uuid.UUID('d917bad2-6153-42d0-8327-a0026b9c642e'),
              'mdi6.human-male-female-child',
              description="The character's family background and relationships"),
        Topic('Education', TopicType.Background, uuid.UUID('6742e431-e0bd-42b9-8363-118f5dab92af'),
              'fa5s.graduation-cap',
              description="The character's educational level and background"),
        Topic('Citizenship', TopicType.Background, uuid.UUID('ef29e2c5-84ba-4978-88cb-b05bb5b6bc82'),
              'fa5s.passport',
              description="The character's nationality"),
        Topic('Hometown', TopicType.Background, uuid.UUID('689b429f-0ff7-4a0d-917c-8a8a0b127892'),
              'ei.home-alt',
              description="The character's hometown and how it mau have influenced their identity, values, or perspectives"),
        Topic('Unique life experiences', TopicType.Background, uuid.UUID('b450d336-375d-4011-80a2-4f84add2cad0'),
              'fa5s.map-signs',
              description="Any exceptional life experience that sets the character apart from others"),
        Topic('Personal aspirations', TopicType.Background,
              uuid.UUID('5d0f0b1e-2fc0-4400-a7ee-b76adafa96c2'),
              'mdi6.thought-bubble-outline',
              description="The character's goals, dreams, and aspirations for the future."),
        Topic('Socioeconomic background', TopicType.Background, uuid.UUID('f95af7a4-aa38-4842-be87-b0dc722615cb'),
              'fa5s.hand-holding-usd',
              description="Includes the character's income, education, employment and social background"),
        Topic('Identity or self-discovery', TopicType.Background,
              uuid.UUID('4d67143c-20cf-43c6-b28f-def85fc760b9'),
              'mdi6.mirror',
              description="Involves any internal conflicts or periods of self-discovery related to the character's identity"),
        Topic('Childhood memories', TopicType.Background,
              uuid.UUID('1da54d78-3ac1-4ae6-8360-fb1a11b1166d'),
              'fa5s.child',
              description="Any influential figures or memories from the character's past"),
    ],
    TopicType.Hobbies: [
        Topic('Art', TopicType.Hobbies, uuid.UUID('72a0249e-3040-4ff0-93e7-88a83cdcad39'),
              'mdi.palette',
              description="Does the character engage in any artistic hobbies? E.g., painting, drawing, writing, etc."),
        Topic('Sports', TopicType.Hobbies, uuid.UUID('10ed740a-71dd-4982-9f21-29937f8a5948'),
              'ri.football-line',
              description="Does the character play any sport? Individually or in a group?"),
        Topic('Music', TopicType.Hobbies, uuid.UUID('3df7ddfd-e9a7-4bb8-a492-86be079ce7bc'),
              'fa5s.music',
              description="Musical preferences. Can the character play any instrument?"),
        Topic('Reading', TopicType.Hobbies, uuid.UUID('b514a9fa-ee3d-40de-a73f-38cfc8b9e8ae'),
              'fa5s.book-reader',
              description="The character's reading habits and favourite genres or authors"),
        Topic('Travel', TopicType.Hobbies, uuid.UUID('0d11a1b5-75e1-4d1b-a0c1-6c6f16dc8fd4'),
              'mdi.airplane',
              description="Does the character like to travel and broaden their horizon?"),
        Topic('Cuisine', TopicType.Hobbies, uuid.UUID('63b5c7f1-b221-40e0-b554-946387e47c63'),
              'mdi.food-turkey',
              description="Food preferences and cooking skills"),
        Topic('Games', TopicType.Hobbies, uuid.UUID('c3e68522-a318-4011-8737-3325f3facdd5'),
              'fa5s.gamepad',
              description="What does the character like to play?"),
        Topic('Collecting', TopicType.Hobbies, uuid.UUID('3b9fd229-1c53-48de-b1d0-7eb039d1e48d'),
              'mdi.postage-stamp',
              description="Any unique collecting habits? E.g., stamps, coins, vintage items"),
        Topic('Volunteer work', TopicType.Hobbies, uuid.UUID('e501d9db-d6e8-47a2-8f3d-8867d69e5e85'),
              'mdi6.hand-front-right',
              description="Does the character partake in volunteering?"),
        Topic('Leisure time', TopicType.Hobbies, uuid.UUID('e6ea2ee5-f0d8-4742-9568-ad3ab4c50db8'),
              'mdi.netflix',
              description="What does the character like to do in their leisure time?"),
        Topic('Outdoor activities', TopicType.Hobbies, uuid.UUID('4b9a4258-fa0a-49d5-ae1d-b7c259d305b7'),
              'mdi.nature-people',
              description="Any outdoor activities the character would pursue? Walking, hiking, sitting on a bench?"),
    ],
    TopicType.Communication: [
        Topic('Listening skills', TopicType.Communication, uuid.UUID('74144d63-01dd-496d-935e-6287fc627358'),
              'fa5s.assistive-listening-systems',
              description="Is the character a good listener? Or do they always have to interrupt?"),
        Topic('Sense of humor', TopicType.Communication, uuid.UUID('c6f2a50d-abe1-4904-aa78-38990541b976'),
              'fa5.laugh-beam',
              description="What is the character's general sense of humor?"),
        Topic('Conversational style', TopicType.Communication, uuid.UUID('955f8960-e3e1-4233-9a2d-9037df883c5a'),
              'ph.chats-circle',
              description="E.g., formal, informal, adaptive, assertive, expressive"),
        Topic('Conflict resolution', TopicType.Communication, uuid.UUID('600a8f6a-2ddf-4188-8989-9c23552e8c9f'),
              'mdi6.shield-sword-outline',
              description="How does the character approach conflicts and arguments?"),
        Topic('Leadership', TopicType.Communication, uuid.UUID('8f318195-7e26-4b4b-bf62-5eebf87479e2'),
              'fa5s.flag',
              description="Can the character lead, guide, and influence other people?"),
        Topic('Charisma', TopicType.Communication, uuid.UUID('1c112a93-f27c-4e6b-97a4-452903514c09'),
              'ri.user-star-line',
              description="Is there a charm or attractiveness or engaging presence about the character that inspires others?"),
        Topic('Networking', TopicType.Communication, uuid.UUID('58c019ea-cce0-4f72-a822-b30566601dfd'),
              'ph.share-network-bold',
              description="Does the character have connections, an inner circle, to leverage for professional and personal growth?"),
        Topic('Collaboration', TopicType.Communication, uuid.UUID('f6f9d6f8-4746-44bd-9595-922e92203679'),
              'ph.handshake-bold',
              description="Can the character easily communicate and work with others?"),
        Topic('Public speaking', TopicType.Communication, uuid.UUID('b8800918-62e3-45ff-a0e6-1c86a9ed8941'),
              'fa5s.microphone-alt',
              description="Is the character comfortable with addressing a large audience?"),
    ],
    TopicType.Beliefs: [
        Topic('Religion', TopicType.Beliefs, uuid.UUID('2a228fff-8919-4f8b-800c-0a4c876611c4'),
              'fa5s.hands',
              description="Includes the character's faith, doctrines, beliefs, or practices, adherence to a particular religion shared by a community"),
        Topic('Spirituality', TopicType.Beliefs, uuid.UUID('09e1d944-150e-423f-8586-0f0a69a6593d'),
              'mdi6.meditation',
              description="Includes the character's connection to a greater existence, including peace and purpose"),
        Topic('Political ideologies', TopicType.Beliefs, uuid.UUID('3171c907-f1f2-40e8-8fdd-ce81606951ca'),
              'ei.group-alt',
              description="Includes the character's beliefs and opinions regarding governance, society, and political issues"),
        Topic('Ethics and moral code', TopicType.Beliefs, uuid.UUID('53db2a10-8651-4424-bffb-364e91b90f58'),
              'fa5s.balance-scale',
              description="Principles or rules that govern the character's sense of right and wrong"),
    ],
}

topic_ids = {}
for topics_per_group in topics.values():
    for topic in topics_per_group:
        topic_ids[str(topic.id)] = topic


class CharacterTopicSelectionDialog(TopicSelectionDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._title.setText('Common character topics')

        for topicType in [TopicType.Physical, TopicType.Habits, TopicType.Skills, TopicType.Fears, TopicType.Background,
                          TopicType.Hobbies, TopicType.Communication, TopicType.Beliefs]:
            self._addSection(topicType, topics[topicType])

        self._wdgCenter.layout().addWidget(vspacer())
        self.frame.layout().addWidget(group(self.btnCancel, self.btnSelect), alignment=Qt.AlignmentFlag.AlignRight)


class CharacterTopicsEditor(QWidget):
    def __init__(self, parent=None):
        super(CharacterTopicsEditor, self).__init__(parent)
        self._character: Optional[Character] = None

        self.btnAdd = push_btn(IconRegistry.plus_icon('white'), 'Add topics', properties=['base', 'positive'])
        self.btnAdd.clicked.connect(self._selectTopics)

        self._wdgTopics = TopicsEditor(self)
        vbox(self, 0, 0)
        self.layout().addWidget(self.btnAdd, alignment=Qt.AlignmentFlag.AlignLeft)
        self._scrollarea, self._wdgCenter = scrolled(self, frameless=True)
        self._wdgCenter.setProperty('relaxed-white-bg', True)
        vbox(self._wdgCenter)
        self._wdgCenter.layout().addWidget(self._wdgTopics)
        self._wdgCenter.layout().addWidget(vspacer())
        self._wdgTopics.topicGroupRemoved.connect(self._topicGroupRemoved)
        self._wdgTopics.topicAdded.connect(self._topicAdded)
        self._wdgTopics.topicRemoved.connect(self._topicRemoved)

    def setCharacter(self, character: Character):
        self._character = character

        self._wdgTopics.clear()
        for element in character.topics:
            topic = topic_ids.get(str(element.id))
            if topic:
                topicType = TopicType(topic.type)
                self._wdgTopics.addTopic(topic, topicType, element)
                self._menu.updateTopic(topicType, False)

    def _addTopicGroup(self, topicType: TopicType):
        if self._character is None:
            return
        self._wdgTopics.addTopicGroup(topicType)

    def _topicGroupRemoved(self, topicType: TopicType):
        self._menu.updateTopic(topicType, True)

    def _topicAdded(self, topic: Topic, value: TemplateValue):
        self._character.topics.append(value)

    def _topicRemoved(self, topic: Topic, value: TemplateValue):
        self._character.topics.remove(value)

    def _selectTopics(self):
        topics = CharacterTopicSelectionDialog.popup()
        if topics:
            for topic in topics:
                print(topic.text)
                # self._addNewSection(topic)
