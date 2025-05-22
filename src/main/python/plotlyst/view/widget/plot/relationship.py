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
from typing import List, Optional

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPaintEvent
from PyQt6.QtWidgets import QWidget
from overrides import overrides
from qthandy import vbox, incr_font, incr_icon, spacer, hbox, bold
from qthandy.filter import OpacityEventFilter, VisibilityToggleEventFilter
from qtmenu import MenuWidget

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import Plot, Novel, BackstoryEvent, Position, Character, PlotType, \
    RelationshipDynamicsElement, RelationshipDynamicsType, ConnectorType, RelationshipDynamicsDataType
from plotlyst.view.common import push_btn, columns, action, shadow
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.characters import CharacterSelectorButton
from plotlyst.view.widget.display import PopupDialog, ConnectorWidget
from plotlyst.view.widget.input import TextEditBubbleWidget
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


class RelationshipDynamicsTextElement(TextEditBubbleWidget):
    changed = pyqtSignal()

    def __init__(self, element: RelationshipDynamicsElement, parent=None, target: bool = False):
        super().__init__(parent)
        self.element = element
        self._target = target
        self._title.setText(self.element.keyphrase)
        bold(self._title, False)
        self._textedit.setText(self.element.target if target else self.element.source)
        if self.element.type_icon:
            self._title.setIcon(IconRegistry.from_name(self.element.type_icon, self.element.type_color))

        shadow(self._textedit)

    @overrides
    def _textChanged(self):
        if self._target:
            self.element.target = self._textedit.toPlainText()
        else:
            self.element.source = self._textedit.toPlainText()

        self.changed.emit()


class RelationshipDynamicsElementCard(AbstractTimelineCard):

    def __init__(self, element: RelationshipDynamicsElement, theme: TimelineTheme, parent=None):
        super().__init__(element, parent)
        self._element = element
        hbox(self)

        self.btnDrag.clicked.connect(self._showContextMenu)

        self._source = self.__initTextElement()
        if element.rel_type == RelationshipDynamicsType.SEPARATE:
            self.layout().addWidget(self._source)
            if element.connector_type:
                self.layout().addWidget(ConnectorWidget(direction=element.connector_type))
            self._target = self.__initTextElement(target=True)
            self.layout().addWidget(self._target)
        elif element.rel_type == RelationshipDynamicsType.SHARED:
            self.layout().addWidget(self._source, alignment=Qt.AlignmentFlag.AlignCenter)

        self.layout().addWidget(self.btnDrag)

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
        def addOrigin():
            element = RelationshipDynamicsElement('Origin', '', position=position,
                                                  rel_type=RelationshipDynamicsType.SEPARATE,
                                                  data_type=RelationshipDynamicsDataType.TEXT,
                                                  connector_type=ConnectorType.BIDIRECTIONAL)
            if row:
                self._insertElement(element, row)
            else:
                self._addElement(element)

        def addConflict():
            element = RelationshipDynamicsElement('Conflict', '', type_icon='mdi.sword-cross', type_color='#e57c04',
                                                  position=position,
                                                  rel_type=RelationshipDynamicsType.SHARED,
                                                  data_type=RelationshipDynamicsDataType.TEXT)
            if row:
                self._insertElement(element, row)
            else:
                self._addElement(element)

        menu = MenuWidget()
        menu.addAction(action('Origin', slot=addOrigin))
        menu.addAction(action('Conflict', slot=addConflict))
        menu.exec()


class RelationshipDynamicsWidget(QWidget):
    changed = pyqtSignal()
    characterChanged = pyqtSignal()

    def __init__(self, plot: Plot, novel: Novel, parent=None):
        super().__init__(parent)
        self._plot = plot
        self._novel = novel

        vbox(self)
        self.setMaximumWidth(700)

        self._sourceCharacterSelector = CharacterSelectorButton(self._novel, iconSize=48)
        self._sourceCharacterSelector.characterSelected.connect(self._sourceCharacterSelected)
        self._targetCharacterSelector = CharacterSelectorButton(self._novel, iconSize=48)
        self._targetCharacterSelector.characterSelected.connect(self._targetCharacterSelected)
        self._btnEdit = push_btn(IconRegistry.plus_icon('grey'), 'Add element', transparent_=True)
        self._btnEdit.installEventFilter(OpacityEventFilter(self._btnEdit, leaveOpacity=0.7))
        incr_font(self._btnEdit, 2)
        incr_icon(self._btnEdit, 4)
        self._btnEdit.clicked.connect(lambda: self.wdgEditor.add(Position.CENTER))

        self.wdgHeader = columns(spacing=55)
        self.wdgHeader.layout().addWidget(spacer())
        self.wdgHeader.layout().addWidget(self._sourceCharacterSelector)
        self.wdgHeader.layout().addWidget(self._btnEdit)
        self.wdgHeader.layout().addWidget(self._targetCharacterSelector)
        self.wdgHeader.layout().addWidget(spacer())

        self.wdgEditor = RelationshipDynamicsEditor(self._plot)
        self.wdgEditor.refresh()
        self.wdgEditor.changed.connect(self.changed)

        self.layout().addWidget(self.wdgHeader)
        self.layout().addWidget(self.wdgEditor)

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
        self.changed.emit()

    def _targetCharacterSelected(self, character: Character):
        self._plot.relationship.target_characters.clear()
        self._plot.relationship.target_characters.append(character.id)
        self.changed.emit()
