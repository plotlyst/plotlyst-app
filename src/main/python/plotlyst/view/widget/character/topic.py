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
from functools import partial
from typing import Optional, Dict

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QWidget
from qthandy import vbox, vspacer
from qtmenu import MenuWidget, ActionTooltipDisplayMode

from plotlyst.core.domain import Character, Topic, TemplateValue, TopicType
from plotlyst.view.common import push_btn, scrolled, action
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.topic import TopicsEditor, topic_ids


class CharacterTopicGroupSelector(MenuWidget):
    topicGroupTriggered = pyqtSignal(TopicType)

    def __init__(self, character: Character, parent=None):
        super().__init__(parent)
        self._character = character
        self._actions: Dict[TopicType, QAction] = {}
        self.setTooltipDisplayMode(ActionTooltipDisplayMode.DISPLAY_UNDER)

        for topic_group in TopicType:
            if topic_group == TopicType.Worldbuilding:
                continue
            action_ = action(topic_group.name, icon=IconRegistry.from_name(topic_group.icon()),
                             tooltip=topic_group.description())
            self._actions[topic_group] = action_
            action_.triggered.connect(partial(self.topicGroupTriggered.emit, topic_group))
            self.addAction(action_)

    def updateTopic(self, topicType: TopicType, enabled: bool):
        self._actions[topicType].setEnabled(enabled)


class CharacterTopicsEditor(QWidget):
    def __init__(self, parent=None):
        super(CharacterTopicsEditor, self).__init__(parent)
        self._character: Optional[Character] = None
        self._menu: Optional[CharacterTopicGroupSelector] = None

        self.btnAdd = push_btn(IconRegistry.plus_icon('white'), 'Add category', properties=['base', 'positive'])

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
        self._menu = CharacterTopicGroupSelector(self._character, self.btnAdd)
        self._menu.topicGroupTriggered.connect(self._addTopicGroup)

        self._wdgTopics.clear()
        for value in character.topics:
            topic = topic_ids.get(str(value.id))
            if topic:
                topicType = TopicType(topic.type)
                self._wdgTopics.addTopic(topic, topicType, value)
                self._menu.updateTopic(topicType, False)

    def _addTopicGroup(self, topicType: TopicType):
        if self._character is None:
            return
        self._wdgTopics.addTopicGroup(topicType)

        self._menu.updateTopic(topicType, False)

    def _topicGroupRemoved(self, topicType: TopicType):
        self._menu.updateTopic(topicType, True)

    def _topicAdded(self, topic: Topic, value: TemplateValue):
        self._character.topics.append(value)

    def _topicRemoved(self, topic: Topic, value: TemplateValue):
        self._character.topics.remove(value)
