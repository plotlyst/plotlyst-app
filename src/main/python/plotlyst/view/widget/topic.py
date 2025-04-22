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
from typing import Dict, List, Union

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import QWidget, QTextEdit, QGridLayout, QDialog
from qthandy import vbox, bold, line, margins, spacer, grid, hbox, clear_layout, flow, transparent, vspacer, sp
from qthandy.filter import VisibilityToggleEventFilter

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import Topic, TopicType, TopicElement, TopicElementBlock
from plotlyst.view.common import push_btn, fade_out_and_gc, label, \
    scrolled
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.button import CollapseButton, SelectorToggleButton
from plotlyst.view.widget.display import PopupDialog
from plotlyst.view.widget.input import AutoAdjustableTextEdit, RemovalButton, SearchField


class TopicSelectorButton(SelectorToggleButton):
    def __init__(self, topic: Topic, group: bool = False):
        button_style = Qt.ToolButtonStyle.ToolButtonTextBesideIcon if group else Qt.ToolButtonStyle.ToolButtonTextUnderIcon
        super().__init__(button_style)
        self.topic = topic

        self.setText(topic.text)
        self.setIcon(IconRegistry.from_name(topic.icon))
        self.setToolTip(topic.description)


class TopicGroupSelector(QWidget):
    def __init__(self, header: Union[Topic, TopicType], parent=None):
        super().__init__(parent)
        self._header = header
        if isinstance(header, Topic):
            self.headerTopicBtn = TopicSelectorButton(header, group=True)
            self._headerName = header.text
        elif isinstance(header, TopicType):
            self._headerName = header.display_name()
            self.headerTopicBtn = push_btn(icon=IconRegistry.from_name(header.icon()), text=self._headerName,
                                           pointy_=False, icon_resize=False, tooltip=header.description(),
                                           transparent_=True)

        vbox(self, 2, 0)
        margins(self, top=5)
        self._topics: Dict[str, TopicSelectorButton] = {}

        self.container = QWidget()
        flow(self.container)
        margins(self.container, left=10)

        self.layout().addWidget(self.headerTopicBtn, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(line(color='lightgrey'))
        self.layout().addWidget(self.container)

    def addTopic(self, btn: TopicSelectorButton):
        self.container.layout().addWidget(btn)
        self._topics[btn.topic.text] = btn

    def filter(self, term: str):
        if term:
            if term in self._headerName:
                # qtanim.glow(self.header, color=QColor(PLOTLYST_SECONDARY_COLOR), teardown=lambda: self.header.setGraphicsEffect(None))
                self._setVisibleAll(True)
                return

            visibleSection = False
            for topic in self._topics.keys():
                visibleTopic = term in topic
                self._topics[topic].setVisible(visibleTopic)
                if visibleTopic:
                    visibleSection = True

            self.setVisible(visibleSection)
        else:
            self._setVisibleAll(True)

    def _setVisibleAll(self, visible: bool):
        for _, btn in self._topics.items():
            btn.setVisible(visible)
        self.setVisible(True)


# if not term:
#     for _, btn in self._topics.items():
#         btn.setVisible(True)
#     return
#
# for topic in self._topics.keys():
#     self._topics[topic].setVisible(term in topic)


class TopicSelectionDialog(PopupDialog):
    DEFAULT_SELECT_BTN_TEXT: str = 'Select topics'

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selectedTopics = []

        self.frame.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)
        self._title = label('Common topics', h4=True)
        self.frame.layout().addWidget(self._title, alignment=Qt.AlignmentFlag.AlignCenter)
        self.search = SearchField()
        self.search.lineSearch.textEdited.connect(self._search)
        self.frame.layout().addWidget(self.search, alignment=Qt.AlignmentFlag.AlignLeft)
        self._scrollarea, self._wdgCenter = scrolled(self.frame, frameless=True, h_on=False)
        self._scrollarea.setProperty('transparent', True)
        transparent(self._wdgCenter)
        vbox(self._wdgCenter, 10)
        self.setMinimumWidth(550)

        self._sections: Dict[str, TopicGroupSelector] = {}

        self.btnSelect = push_btn(IconRegistry.ok_icon(RELAXED_WHITE_COLOR), self.DEFAULT_SELECT_BTN_TEXT,
                                  properties=['positive', 'confirm'])
        self.btnSelect.setDisabled(True)
        self.btnSelect.clicked.connect(self.accept)
        self.btnCancel = push_btn(text='Cancel', properties=['confirm', 'cancel'])
        self.btnCancel.clicked.connect(self.reject)

    def display(self) -> List[Topic]:
        self.search.lineSearch.setFocus()
        result = self.exec()
        if result == QDialog.DialogCode.Accepted:
            return self._selectedTopics

        return []

    def _addSection(self, header: Union[Topic, TopicType], topics: List[Topic]):
        wdg = TopicGroupSelector(header)
        wdg.headerTopicBtn.toggled.connect(partial(self._toggled, header))
        self._sections[header.text] = wdg
        self._wdgCenter.layout().addWidget(wdg)

        for topic in topics:
            btn = TopicSelectorButton(topic)
            # self._topics[topic.text] = btn
            btn.toggled.connect(partial(self._toggled, topic))
            wdg.addTopic(btn)

        self._wdgCenter.layout().addWidget(wdg)

    def _toggled(self, topic: Topic, checked: bool):
        if checked:
            self._selectedTopics.append(topic)
        else:
            self._selectedTopics.remove(topic)

        self.btnSelect.setEnabled(len(self._selectedTopics) > 0)
        if self._selectedTopics:
            self.btnSelect.setText(f'{self.DEFAULT_SELECT_BTN_TEXT} ({len(self._selectedTopics)})')
        else:
            self.btnSelect.setText(self.DEFAULT_SELECT_BTN_TEXT)

    def _search(self, term: str):
        for wdg in self._sections.values():
            wdg.filter(term)


class TopicGroupWidget(QWidget):
    topicRemoved = pyqtSignal(Topic, TopicElement)

    def __init__(self, topicType: TopicType, parent=None):
        super().__init__(parent)
        self._type = topicType
        vbox(self)

        self.btnHeader = CollapseButton(Qt.Edge.BottomEdge, Qt.Edge.RightEdge)
        self.btnHeader.setIconSize(QSize(16, 16))
        self.btnHeader.setText(self._type.display_name())
        self.btnHeader.setToolTip(self._type.description())
        bold(self.btnHeader)
        self._topicWidgets: Dict[Topic, TopicWidget] = {}

        self.wdgHeader = QWidget()
        hbox(self.wdgHeader)
        self.wdgHeader.layout().addWidget(self.btnHeader, alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgTopics = QWidget()
        vbox(self.wdgTopics)
        sp(self.wdgTopics).v_max()
        self.btnHeader.toggled.connect(self.wdgTopics.setHidden)

        self.layout().addWidget(self.wdgHeader)
        self.layout().addWidget(line())
        self.layout().addWidget(self.wdgTopics)

    def addTopic(self, topic: Topic, element: TopicElement) -> 'TopicWidget':
        wdg = TopicWidget(topic, element)
        wdg.removalRequested.connect(partial(self._removeTopic, topic))
        self._topicWidgets[topic] = wdg
        self.wdgTopics.layout().addWidget(wdg)

        return wdg

    def _removeTopic(self, topic: Topic):
        wdg = self._topicWidgets.pop(topic)
        self.topicRemoved.emit(topic, wdg.element())
        fade_out_and_gc(self.wdgTopics, wdg)


class TopicTextBlockWidget(QWidget):
    def __init__(self, topic: Topic, block: TopicElementBlock, parent=None):
        super().__init__(parent)
        vbox(self)
        self._block: TopicElementBlock = block
        self.textEdit = AutoAdjustableTextEdit(height=60)
        self.textEdit.setProperty('transparent', True)
        self.textEdit.setAutoFormatting(QTextEdit.AutoFormattingFlag.AutoAll)
        self.textEdit.setTabChangesFocus(True)
        self.textEdit.setPlaceholderText(topic.description)
        self.textEdit.setMarkdown(block.text)

        self.textEdit.textChanged.connect(self._textChanged)

        self.layout().addWidget(self.textEdit)

    def _textChanged(self):
        self._block.text = self.textEdit.toMarkdown()


class TopicWidget(QWidget):
    removalRequested = pyqtSignal()

    def __init__(self, topic: Topic, element: TopicElement, parent=None):
        super(TopicWidget, self).__init__(parent)

        self._topic = topic
        self._element = element

        self.btnHeader = push_btn(IconRegistry.from_name(topic.icon, topic.icon_color), topic.text,
                                  tooltip=topic.description, transparent_=True, pointy_=False, icon_resize=False)

        self._btnRemoval = RemovalButton()
        self._btnRemoval.clicked.connect(self.removalRequested)

        self._top = group(self.btnHeader, spacer(), self._btnRemoval, margin=0, spacing=1)
        margins(self._top, left=20)
        layout_ = vbox(self)
        layout_.addWidget(self._top)
        self._top.installEventFilter(VisibilityToggleEventFilter(self._btnRemoval, self._top))

        for block in element.blocks:
            wdg = TopicTextBlockWidget(topic, block)
            margins(wdg, left=20)
            layout_.addWidget(wdg)

    def element(self) -> TopicElement:
        return self._element


class TopicsEditor(QWidget):
    topicRemoved = pyqtSignal(Topic, TopicElement)

    def __init__(self, parent=None):
        super(TopicsEditor, self).__init__(parent)
        self._gridLayout: QGridLayout = grid(self)
        self._gridLayout.addWidget(vspacer(), 25, 0, 1, 1)

        self._topicGroups: Dict[TopicType, TopicGroupWidget] = {}

    def addTopicGroup(self, topicType: TopicType):
        wdg = TopicGroupWidget(topicType)
        wdg.topicRemoved.connect(self.topicRemoved)
        self._topicGroups[topicType] = wdg

        self._gridLayout.addWidget(wdg, topicType.value, 0)

    def addTopic(self, topic: Topic, element: TopicElement):
        if topic.type not in self._topicGroups:
            self.addTopicGroup(topic.type)

        self._topicGroups[topic.type].addTopic(topic, element)

    def clear(self):
        self._topicGroups.clear()
        clear_layout(self)
