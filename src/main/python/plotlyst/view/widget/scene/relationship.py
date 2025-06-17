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
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QResizeEvent, QIcon
from PyQt6.QtWidgets import QWidget
from overrides import overrides
from qthandy import incr_font, incr_icon, vbox
from qthandy.filter import VisibilityToggleEventFilter

from plotlyst.core.domain import StoryElement, CharacterAgency, Novel
from plotlyst.env import app_env
from plotlyst.service.cache import entities_registry
from plotlyst.view.common import label, push_btn, tool_btn
from plotlyst.view.icons import IconRegistry, avatars
from plotlyst.view.widget.display import MenuOverlayEventFilter
from plotlyst.view.widget.input import RemovalButton
from plotlyst.view.widget.relationship import AbstractRelationshipChangeDimensionPopup, DimensionSelectorButton, \
    ModifierSelectorButton


class RelationshipChangeDimensionPopup(AbstractRelationshipChangeDimensionPopup):
    def __init__(self, element: StoryElement, parent=None):
        super().__init__(parent)

        if element.dimension:
            for btn in self.btnGroupDimensions.buttons():
                if btn.text() == element.dimension:
                    btn.setChecked(True)
                    break
            if element.modifier:
                for btn in self.btnGroupModifiers.buttons():
                    if btn.text() == element.modifier:
                        btn.setChecked(True)
                        break
        else:
            for btn in self.btnGroupModifiers.buttons():
                btn.setEnabled(False)


class RelationshipChangeWidget(QWidget):
    removed = pyqtSignal()

    def __init__(self, element: StoryElement, agency: CharacterAgency, novel: Novel, parent=None):
        super().__init__(parent)
        self.element = element
        self.agency = agency
        self.novel = novel
        vbox(self, 0, 0)

        self._btnRemove = RemovalButton(self)
        self._btnRemove.clicked.connect(self.removed)
        self._btnRemove.setHidden(True)

        self._characterLbl = tool_btn(QIcon(), transparent_=True)
        incr_icon(self._characterLbl, 14)
        self._characterLbl.clicked.connect(self._edit)

        self._lblDimension = push_btn(transparent_=True)
        incr_font(self._lblDimension, 2)
        font = self._lblDimension.font()
        font.setFamily(app_env.serif_font())
        self._lblDimension.setFont(font)
        self._lblDimension.clicked.connect(self._edit)
        self._lblModifier = label('', description=True, decr_font_diff=1)

        self.layout().addWidget(self._characterLbl, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._lblDimension, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._lblModifier, alignment=Qt.AlignmentFlag.AlignCenter)

        if self.novel.tutorial:
            character = self.novel.find_character(element.ref)
        else:
            character = entities_registry.character(str(element.ref))
        if character:
            self._characterLbl.setIcon(avatars.avatar(character))

        if self.element.dimension:
            self._lblDimension.setText(self.element.dimension)
            self._lblDimension.setIcon(IconRegistry.from_name(self.element.icon))
            if self.element.modifier:
                self._lblModifier.setText(f'[{self.element.modifier}]')
            else:
                self._lblModifier.setHidden(True)
        else:
            self._lblDimension.setIcon(IconRegistry.edit_icon('grey'))
            self._lblModifier.setHidden(True)

        self.installEventFilter(VisibilityToggleEventFilter(self._btnRemove, self))

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        self._btnRemove.setGeometry(self.width() - self._btnRemove.sizeHint().width(), 2,
                                    self._btnRemove.sizeHint().width(), self._btnRemove.sizeHint().height())

    def _edit(self):
        self._menu = RelationshipChangeDimensionPopup(self.element)
        self._menu.btnGroupDimensions.buttonClicked.connect(self._dimensionChanged)
        self._menu.btnGroupModifiers.buttonClicked.connect(self._modifierChanged)
        self._menu.installEventFilter(MenuOverlayEventFilter(self._menu))
        self._menu.exec()

    def _dimensionChanged(self, btn: DimensionSelectorButton):
        if btn.isChecked():
            self._lblDimension.setText(btn.dimension)
            self._lblDimension.setIcon(IconRegistry.from_name(btn.iconName))
            self.element.dimension = btn.dimension
            self.element.icon = btn.iconName
        else:
            self._lblDimension.setText('')
            self._lblDimension.setIcon(IconRegistry.edit_icon('grey'))
            self._lblModifier.setText('')
            self._lblModifier.setVisible(False)
            self.element.modifier = ''
            self.element.dimension = ''
            self.element.icon = ''

    def _modifierChanged(self, btn: ModifierSelectorButton):
        self._lblModifier.setVisible(btn.isChecked())
        if btn.isChecked():
            self._lblModifier.setText(f'[{btn.modifier}]')
            self.element.modifier = btn.modifier
        else:
            self._lblModifier.setText('')
            self.element.modifier = ''
