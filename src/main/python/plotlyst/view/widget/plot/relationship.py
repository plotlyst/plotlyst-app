"""
Plotlyst
Copyright (C) 2021-2025  Zsolt Kovari

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
from enum import Enum, auto
from functools import partial
from typing import List, Optional

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPaintEvent
from PyQt6.QtWidgets import QWidget, QTextEdit
from overrides import overrides
from qthandy import vbox, incr_font, incr_icon, spacer, hbox, margins
from qthandy.filter import OpacityEventFilter, VisibilityToggleEventFilter
from qtmenu import MenuWidget, GridMenuWidget

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import Plot, Novel, BackstoryEvent, Position, Character, PlotType, \
    RelationshipDynamicsElement, RelationshipDynamicsType, RelationshipDynamicsDataType, ConnectorType
from plotlyst.env import app_env
from plotlyst.view.common import push_btn, columns, action, shadow, frame
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.characters import CharacterSelectorButton
from plotlyst.view.widget.display import PopupDialog, ConnectorWidget, icon_text
from plotlyst.view.widget.timeline import TimelineLinearWidget, TimelineTheme, AbstractTimelineCard, TimelineEntityRow


class RelationshipDynamicsEditorPopup(PopupDialog):
    def __init__(self, plot: Plot, parent=None):
        super().__init__(parent)
        self.plot = plot

        self.btnClose = push_btn(IconRegistry.ok_icon(RELAXED_WHITE_COLOR), 'Apply', properties=['confirm', 'positive'])
        self.btnClose.clicked.connect(self.accept)

        self.frame.layout().addWidget(self.btnClose, alignment=Qt.AlignmentFlag.AlignRight)

    def display(self):
        self.exec()


class RelationshipDynamicsTextElement(QTextEdit):
    changed = pyqtSignal()

    def __init__(self, element: RelationshipDynamicsElement, parent=None, target: bool = False):
        super().__init__(parent)
        self.element = element
        self._target = target
        self.setProperty('white-bg', True)
        self.setProperty('rounded-on-bottom', True)

        self.setTabChangesFocus(True)
        if app_env.is_mac():
            incr_font(self)
        self.setMinimumSize(175, 90)
        self.setMaximumSize(190, 110)
        self.verticalScrollBar().setVisible(False)
        self.setText(self.element.target if target else self.element.source)

        self.textChanged.connect(self._textChanged)

        shadow(self)

    def _textChanged(self):
        if self._target:
            self.element.target = self.toPlainText()
        else:
            self.element.source = self.toPlainText()

        self.changed.emit()


class RelationshipDynamicsElementCard(AbstractTimelineCard):

    def __init__(self, element: RelationshipDynamicsElement, _: TimelineTheme, parent=None):
        super().__init__(element, parent)
        self._element = element

        vbox(self, 0, 0)
        self.btnDrag.clicked.connect(self._showContextMenu)

        self._source = self.__initTextElement()
        self._title = icon_text(self._element.type_icon, self._element.keyphrase, self._element.type_color)
        incr_font(self._title)
        font = self._title.font()
        font.setFamily(app_env.serif_font())
        self._title.setFont(font)
        wdgHeader = frame()
        hbox(wdgHeader, 2, 0)
        wdgHeader.layout().addWidget(self._title, alignment=Qt.AlignmentFlag.AlignCenter)
        wdgHeader.setProperty('rounded-on-top', True)
        wdgHeader.setProperty('muted-bg', True)

        wdgEditor = columns(3, 3)
        margins(wdgEditor, top=0)

        if element.rel_type == RelationshipDynamicsType.SEPARATE:
            wdgEditor.layout().addWidget(self._source)
            if element.connector_type:
                wdgEditor.layout().addWidget(ConnectorWidget(direction=element.connector_type))
            self._target = self.__initTextElement(target=True)
            wdgEditor.layout().addWidget(self._target)

        elif element.rel_type == RelationshipDynamicsType.SHARED:
            wdgEditor.layout().addWidget(self._source, alignment=Qt.AlignmentFlag.AlignCenter)

        self.layout().addWidget(wdgHeader)
        self.layout().addWidget(wdgEditor)

        self.btnDrag.setParent(self)
        self.btnDrag.setGeometry(self.sizeHint().width() - self.btnDrag.sizeHint().width(), 0,
                                 self.btnDrag.sizeHint().width(),
                                 self.btnDrag.sizeHint().height())

        self.installEventFilter(VisibilityToggleEventFilter(self.btnDrag, self))

    def _showContextMenu(self):
        menu = MenuWidget()
        menu.addAction(action('Remove', IconRegistry.trash_can_icon(), slot=self._remove))
        menu.exec()

    def _remove(self):
        self.deleteRequested.emit(self)

    def __initTextElement(self, target: bool = False) -> RelationshipDynamicsTextElement:
        wdg = RelationshipDynamicsTextElement(self._element, target=target)
        wdg.changed.connect(self.edited)

        return wdg


class RelationshipDynamicsSelectorTemplate(Enum):
    Origin = auto()
    Attitude = auto()
    Values = auto()
    Social_status = auto()
    Desire = auto()
    Conflict = auto()
    Goal = auto()
    Relationship_evolution = auto()

    def display_name(self) -> str:
        return self.name.capitalize().replace('_', ' ')

    def icon(self) -> str:
        if self == RelationshipDynamicsSelectorTemplate.Conflict:
            return 'mdi.sword-cross'
        return 'ri.calendar-event-fill'

    def color(self) -> str:
        if self == RelationshipDynamicsSelectorTemplate.Conflict:
            return '#e57c04'
        return 'black'

    def placeholder(self) -> str:
        pass

    def element(self) -> RelationshipDynamicsElement:
        el = RelationshipDynamicsElement(self.display_name(), '', type_icon=self.icon(), type_color=self.color(),
                                         data_type=RelationshipDynamicsDataType.TEXT)
        if self in [RelationshipDynamicsSelectorTemplate.Conflict, RelationshipDynamicsSelectorTemplate.Goal]:
            el.rel_type = RelationshipDynamicsType.SHARED
        else:
            el.rel_type = RelationshipDynamicsType.SEPARATE
            el.connector_type = ConnectorType.BIDIRECTIONAL

        return el


class RelationshipDynamicsSelector(GridMenuWidget):
    selected = pyqtSignal(RelationshipDynamicsSelectorTemplate)

    def __init__(self, parent=None):
        super().__init__(parent)

        row = 0
        self.addSection("Individual elements that are contrasting between the two characters", row, 0, colSpan=5)
        row += 1
        self.addSeparator(row, 0, colSpan=5)

        row += 1
        self._addAction(RelationshipDynamicsSelectorTemplate.Attitude, row, 0)
        self._addAction(RelationshipDynamicsSelectorTemplate.Desire, row, 1)
        self._addAction(RelationshipDynamicsSelectorTemplate.Origin, row, 2)
        self._addAction(RelationshipDynamicsSelectorTemplate.Social_status, row, 3)

        row += 1
        self.addSection(
            "Mutual elements that are shared between the characters, e.g. interpersonal conflict, shared, goal, etc.",
            row, 0, colSpan=5)
        row += 1
        self.addSeparator(row, 0, colSpan=5)
        row += 1
        self._addAction(RelationshipDynamicsSelectorTemplate.Conflict, row, 0)
        self._addAction(RelationshipDynamicsSelectorTemplate.Goal, row, 1)
        self._addAction(RelationshipDynamicsSelectorTemplate.Relationship_evolution, row, 2, colSpan=2)

    def _addAction(self, template: RelationshipDynamicsSelectorTemplate, row: int, col: int, colSpan: int = 1):
        self.addAction(action(template.display_name(), IconRegistry.from_name(template.icon()),
                              slot=partial(self.selected.emit, template)), row, col, colSpan=colSpan)


class RelationshipDynamicsEditor(TimelineLinearWidget):
    def __init__(self, plot: Plot, parent=None):
        super().__init__(parent, centerOnly=True)
        self._plot = plot

    @overrides
    def events(self) -> List[BackstoryEvent]:
        return self._plot.relationship.elements

    @overrides
    def cardClass(self):
        return RelationshipDynamicsElementCard

    @overrides
    def domainClass(self):
        return RelationshipDynamicsElement

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        pass

    @overrides
    def add(self, position: Position = Position.CENTER):
        self._displayMenu(position)

    @overrides
    def _insert(self, event: TimelineEntityRow, position: Position):
        self._displayMenu(position, event)

    def _displayMenu(self, position: Position, row: Optional[TimelineEntityRow] = None):
        def add(template: RelationshipDynamicsSelectorTemplate):
            element = template.element()
            element.position = position
            if row:
                self._insertElement(element, row)
            else:
                self._addElement(element)

        menu = RelationshipDynamicsSelector()
        menu.selected.connect(add)
        menu.exec()


class RelationshipDynamicsHeader(QWidget):
    characterChanged = pyqtSignal()

    def __init__(self, plot: Plot, novel: Novel, parent=None):
        super().__init__(parent)
        self._plot = plot
        self._novel = novel

        self.setMaximumWidth(700)

        self._sourceCharacterSelector = CharacterSelectorButton(self._novel, iconSize=48)
        self._sourceCharacterSelector.characterSelected.connect(self._sourceCharacterSelected)
        self._targetCharacterSelector = CharacterSelectorButton(self._novel, iconSize=48)
        self._targetCharacterSelector.characterSelected.connect(self._targetCharacterSelected)
        self.btnEdit = push_btn(IconRegistry.plus_icon('grey'), 'Add element', transparent_=True)
        self.btnEdit.installEventFilter(OpacityEventFilter(self.btnEdit, leaveOpacity=0.7))
        incr_font(self.btnEdit, 2)
        incr_icon(self.btnEdit, 4)

        hbox(self, 0, 55)
        self.layout().addWidget(spacer())
        self.layout().addWidget(self._sourceCharacterSelector)
        self.layout().addWidget(self.btnEdit, alignment=Qt.AlignmentFlag.AlignBottom)
        self.layout().addWidget(self._targetCharacterSelector)
        self.layout().addWidget(spacer())

        if self._plot.relationship.source_characters:
            self._sourceCharacterSelector.setCharacterById(self._plot.relationship.source_characters[0])
        if self._plot.relationship.target_characters:
            self._targetCharacterSelector.setCharacterById(self._plot.relationship.target_characters[0])

    def _sourceCharacterSelected(self, character: Character):
        self._plot.relationship.source_characters.clear()
        self._plot.relationship.source_characters.append(character.id)

        if self._plot.plot_type == PlotType.Relation:
            self._plot.set_character(character)

        self.characterChanged.emit()

    def _targetCharacterSelected(self, character: Character):
        self._plot.relationship.target_characters.clear()
        self._plot.relationship.target_characters.append(character.id)
        self.characterChanged.emit()


class RelationshipDynamicsWidget(QWidget):
    changed = pyqtSignal()
    characterChanged = pyqtSignal()

    def __init__(self, plot: Plot, novel: Novel, parent=None):
        super().__init__(parent)
        self._plot = plot
        self._novel = novel

        vbox(self)
        self.setMaximumWidth(700)

        self.wdgEditor = RelationshipDynamicsEditor(self._plot)
        self.wdgEditor.refresh()
        self.wdgEditor.changed.connect(self.changed)

        if self._plot.plot_type != PlotType.Relation:
            self.wdgRelationsHeader = RelationshipDynamicsHeader(self._plot, novel)
            self.wdgRelationsHeader.characterChanged.connect(self.changed)
            self.wdgRelationsHeader.characterChanged.connect(self.characterChanged)
            self.wdgRelationsHeader.btnEdit.clicked.connect(lambda: self.wdgEditor.add(Position.CENTER))
            self.layout().addWidget(self.wdgRelationsHeader, alignment=Qt.AlignmentFlag.AlignCenter)

        self.layout().addWidget(self.wdgEditor)
