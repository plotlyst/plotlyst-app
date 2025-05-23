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
from enum import Enum
from functools import partial
from typing import List, Optional

from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QResizeEvent, QPaintEvent
from PyQt6.QtWidgets import QWidget, QTextEdit
from overrides import overrides
from qthandy import vbox, incr_font, incr_icon, spacer, hbox, margins
from qthandy.filter import OpacityEventFilter, VisibilityToggleEventFilter
from qtmenu import MenuWidget, GridMenuWidget

from plotlyst.core.domain import Plot, Novel, BackstoryEvent, Position, Character, PlotType, \
    RelationshipDynamicsElement, RelationshipDynamicsType, RelationshipDynamicsDataType, ConnectorType
from plotlyst.env import app_env
from plotlyst.view.common import push_btn, columns, action, shadow, frame
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.style.button import apply_button_palette_color
from plotlyst.view.widget.characters import CharacterSelectorButton
from plotlyst.view.widget.display import ConnectorWidget, icon_text
from plotlyst.view.widget.input import IconTextInputDialog
from plotlyst.view.widget.timeline import TimelineLinearWidget, TimelineTheme, AbstractTimelineCard, TimelineEntityRow


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
        self.setMaximumSize(210, 110)
        self.verticalScrollBar().setVisible(False)
        self.setText(self.element.target if target else self.element.source)
        self.setPlaceholderText(
            self.element.synopsis if self.element.synopsis else f"Define the {self.element.keyphrase.lower()} of this character")

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
        apply_button_palette_color(self._title, self._element.type_color)
        self._title.setIconSize(QSize(28, 28))
        incr_font(self._title)
        font = self._title.font()
        font.setFamily(app_env.serif_font())
        self._title.setFont(font)
        wdgHeader = frame()
        hbox(wdgHeader, 2, 0)
        wdgHeader.layout().addWidget(self._title, alignment=Qt.AlignmentFlag.AlignCenter)
        wdgHeader.setProperty('rounded-on-top', True)
        wdgHeader.setProperty('muted-bg', True)
        # wdgHeader.setStyleSheet(f'''
        #     QFrame {{
        #         background: {self._element.type_color};
        #         border: 1px solid {self._element.type_color};
        #         border-top-left-radius: 6px;
        #         border-top-right-radius: 6px;
        #         border-bottom-left-radius: 0px;
        #         border-bottom-right-radius: 0px;
        #     }}
        # ''')

        # translucent(wdgHeader, 0.7)

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
        self.installEventFilter(VisibilityToggleEventFilter(self.btnDrag, self))

        if self._element.rel_type == RelationshipDynamicsType.SEPARATE:
            self.setMinimumWidth(550)

    @overrides
    def resizeEvent(self, a0: QResizeEvent) -> None:
        self.btnDrag.setGeometry(self.width() - self.btnDrag.sizeHint().width(), 0,
                                 self.btnDrag.sizeHint().width(),
                                 self.btnDrag.sizeHint().height())

    def _showContextMenu(self):
        menu = MenuWidget()
        menu.addAction(action('Edit', IconRegistry.edit_icon(), slot=self._edit))
        menu.addSeparator()
        menu.addAction(action('Remove', IconRegistry.trash_can_icon(), slot=self._remove))
        menu.exec()

    def _edit(self):
        result = IconTextInputDialog.edit('Edit element', placeholder='Name',
                                          description="Edit the name and icon of this relationship element",
                                          value=self._element.keyphrase, icon=self._element.type_icon,
                                          color=self._element.type_color)
        if result is not None:
            self._element.keyphrase = result[0]
            self._element.type_icon = result[1]
            self._element.type_color = result[2]

            self._title.setText(self._element.keyphrase)
            self._title.setIcon(IconRegistry.from_name(self._element.type_icon, self._element.type_color))
            apply_button_palette_color(self._title, self._element.type_color)

            self.edited.emit()

    def _remove(self):
        self.deleteRequested.emit(self)

    def __initTextElement(self, target: bool = False) -> RelationshipDynamicsTextElement:
        wdg = RelationshipDynamicsTextElement(self._element, target=target)
        wdg.changed.connect(self.edited)

        return wdg


class RelationshipDynamicsSelectorTemplate(Enum):
    Origin = ('Origin', 'fa5s.archive', 'black', 'SEPARATE', 'BIDIRECTIONAL')
    Attitude = ('Attitude', 'mdi6.emoticon-neutral-outline', 'black', 'SEPARATE', 'BIDIRECTIONAL')
    Values = ('Values', 'fa5s.balance-scale', 'black', 'SEPARATE', 'BIDIRECTIONAL')
    Social_status = ('Social status', 'mdi.ladder', 'black', 'SEPARATE', 'BIDIRECTIONAL')
    Desire = ('Desire', 'ei.star-alt', '#e9c46a', 'SEPARATE', 'BIDIRECTIONAL')
    Conflict = (
        'Conflict', 'mdi.sword-cross', '#e57c04', 'SHARED', None, "What causes conflict between the characters?")
    Goal = ('Shared goal', 'mdi.target', 'darkBlue', 'SHARED', None, "What's the mutual goal of the characters?")
    Relationship_evolution = ('Relationship evolution', 'fa5s.people-arrows', 'black', 'SHARED', None,
                              "How does the relationship evolve between the characters?")

    def __new__(cls, display_name: str, icon: str, color: str, rel_type: str, connector_type: Optional[str],
                placeholder: str = ''):
        obj = object.__new__(cls)
        obj._value_ = display_name
        obj.display_name = display_name
        obj.icon = icon
        obj.color = color
        obj.rel_type = rel_type
        obj.connector_type = connector_type
        obj.placeholder = placeholder
        return obj

    def element(self) -> RelationshipDynamicsElement:
        el = RelationshipDynamicsElement(self.display_name, self.placeholder, type_icon=self.icon,
                                         type_color=self.color,
                                         data_type=RelationshipDynamicsDataType.TEXT)
        el.rel_type = RelationshipDynamicsType[self.rel_type]
        if self.connector_type:
            el.connector_type = ConnectorType[self.connector_type]
        return el


class RelationshipDynamicsSelector(GridMenuWidget):
    selected = pyqtSignal(RelationshipDynamicsSelectorTemplate)
    customIndividualSelected = pyqtSignal()
    customSharedSelected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, largeIcons=True)
        apply_white_menu(self)

        row = 0
        self.addSection("Individual elements that are contrasting between the two characters", row, 0, colSpan=5)
        row += 1
        self.addSeparator(row, 0, colSpan=5)

        row += 1
        self._addAction(RelationshipDynamicsSelectorTemplate.Attitude, row, 0)
        self._addAction(RelationshipDynamicsSelectorTemplate.Desire, row, 1)
        self._addAction(RelationshipDynamicsSelectorTemplate.Origin, row, 2)
        self._addAction(RelationshipDynamicsSelectorTemplate.Social_status, row, 3)

        self.addAction(action('Custom...', slot=self.customIndividualSelected), row, 4)

        row += 1
        self.addSection(
            "Elements that are shared between the characters, e.g., interpersonal conflict, shared goal, etc.",
            row, 0, colSpan=5)
        row += 1
        self.addSeparator(row, 0, colSpan=5)
        row += 1
        self._addAction(RelationshipDynamicsSelectorTemplate.Conflict, row, 0)
        self._addAction(RelationshipDynamicsSelectorTemplate.Goal, row, 1)
        self._addAction(RelationshipDynamicsSelectorTemplate.Relationship_evolution, row, 2, colSpan=2)

        self.addAction(action('Custom...', slot=self.customSharedSelected), row, 4)

    def _addAction(self, template: RelationshipDynamicsSelectorTemplate, row: int, col: int, colSpan: int = 1):
        self.addAction(action(template.display_name, IconRegistry.from_name(template.icon),
                              slot=partial(self.selected.emit, template), incr_font_=1), row, col, colSpan=colSpan)


class RelationshipDynamicsEditor(TimelineLinearWidget):
    def __init__(self, plot: Plot, parent=None):
        super().__init__(parent, centerOnly=True)
        self._plot = plot
        self._menu: Optional[RelationshipDynamicsSelector] = None

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
        self._menu = RelationshipDynamicsSelector()
        self._menu.selected.connect(lambda x: self._add(x, position, row))
        self._menu.customIndividualSelected.connect(
            partial(self._addCustom, RelationshipDynamicsType.SEPARATE, ConnectorType.BIDIRECTIONAL, position, row))
        self._menu.customSharedSelected.connect(
            partial(self._addCustom, RelationshipDynamicsType.SHARED, None, position, row))
        self._menu.exec()

    def _add(self, template: RelationshipDynamicsSelectorTemplate, position: Position,
             row: Optional[TimelineEntityRow] = None):
        element = template.element()
        element.position = position
        if row:
            self._insertElement(element, row)
        else:
            self._addElement(element)

        self._menu = None

    def _addCustom(self, type_: RelationshipDynamicsType, connectorType: Optional[ConnectorType], position: Position,
                   row: Optional[TimelineEntityRow] = None):
        result = IconTextInputDialog.edit('Edit custom element', placeholder='Name',
                                          description="Define a custom name for a relationship element, and optionally select an icon")
        if result is not None:
            element = RelationshipDynamicsElement(result[0], '',
                                                  type_icon=result[1] if result[1] else 'msc.debug-stackframe-dot',
                                                  type_color=result[2],
                                                  rel_type=type_, position=position,
                                                  data_type=RelationshipDynamicsDataType.TEXT,
                                                  connector_type=connectorType)

            if row:
                self._insertElement(element, row)
            else:
                self._addElement(element)


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
        self.setMaximumWidth(800)

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
