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
from typing import List

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPaintEvent
from PyQt6.QtWidgets import QWidget
from overrides import overrides
from qthandy import vbox, incr_font, incr_icon, spacer
from qthandy.filter import OpacityEventFilter

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import Plot, Novel, BackstoryEvent, Position
from plotlyst.view.common import push_btn, columns
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.characters import CharacterSelectorButton
from plotlyst.view.widget.display import PopupDialog
from plotlyst.view.widget.timeline import TimelineLinearWidget, BackstoryCard, TimelineTheme


class RelationshipDynamicsEditorPopup(PopupDialog):
    def __init__(self, plot: Plot, parent=None):
        super().__init__(parent)
        self.plot = plot

        self.btnClose = push_btn(IconRegistry.ok_icon(RELAXED_WHITE_COLOR), 'Apply', properties=['confirm', 'positive'])
        self.btnClose.clicked.connect(self.accept)

        self.frame.layout().addWidget(self.btnClose, alignment=Qt.AlignmentFlag.AlignRight)

    def display(self):
        self.exec()


class RelationshipDynamicsElement(BackstoryCard):
    def __init__(self, element: BackstoryEvent, theme: TimelineTheme, parent=None):
        super().__init__(element, theme, parent=parent)
        self.refresh()


class RelationshipDynamicsEditor(TimelineLinearWidget):
    def __init__(self, plot: Plot, parent=None):
        super().__init__(parent)
        self._plot = plot

    @overrides
    def events(self) -> List[BackstoryEvent]:
        return self._plot.relationship.elements

    @overrides
    def cardClass(self):
        return RelationshipDynamicsElement

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        pass


class RelationshipDynamicsWidget(QWidget):
    changed = pyqtSignal()

    def __init__(self, plot: Plot, novel: Novel, parent=None):
        super().__init__(parent)
        self._plot = plot
        self._novel = novel

        vbox(self)
        self.setMaximumWidth(600)

        self._sourceCharacterSelector = CharacterSelectorButton(self._novel, iconSize=48)
        self._targetCharacterSelector = CharacterSelectorButton(self._novel, iconSize=48)
        self._btnEdit = push_btn(IconRegistry.plus_icon('grey'), 'Add element', transparent_=True)
        self._btnEdit.installEventFilter(OpacityEventFilter(self._btnEdit, leaveOpacity=0.7))
        incr_font(self._btnEdit, 2)
        incr_icon(self._btnEdit, 4)
        self._btnEdit.clicked.connect(lambda: self.wdgEditor.add(Position.CENTER))

        self.wdgHeader = columns(spacing=50)
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
