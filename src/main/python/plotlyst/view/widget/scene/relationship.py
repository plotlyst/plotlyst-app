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
from qthandy import incr_font, incr_icon, vbox, vspacer, line, decr_font
from qthandy.filter import VisibilityToggleEventFilter
from qtmenu import MenuWidget

from plotlyst.core.domain import StoryElement, CharacterAgency, Novel
from plotlyst.env import app_env
from plotlyst.service.cache import entities_registry
from plotlyst.view.common import label, push_btn, tool_btn, columns, wrap, rows, ExclusiveOptionalButtonGroup, frame
from plotlyst.view.icons import IconRegistry, avatars
from plotlyst.view.style.base import transparent_menu
from plotlyst.view.widget.button import SelectorToggleButton
from plotlyst.view.widget.display import MenuOverlayEventFilter
from plotlyst.view.widget.input import RemovalButton


class _DimensionSelectorButton(SelectorToggleButton):
    def __init__(self, dimension: str, icon: str, parent=None):
        super().__init__(Qt.ToolButtonStyle.ToolButtonTextBesideIcon, minWidth=80, parent=parent)
        self.dimension = dimension
        self.iconName = icon
        self.setText(dimension)
        self.setIcon(IconRegistry.from_name(icon))


class _ModifierSelectorButton(SelectorToggleButton):
    def __init__(self, modifier: str, parent=None):
        super().__init__(Qt.ToolButtonStyle.ToolButtonTextBesideIcon, minWidth=60, parent=parent)
        self.modifier = modifier
        self.setText(modifier)
        decr_font(self)


class RelationshipChangeDimensionPopup(MenuWidget):
    def __init__(self, element: StoryElement, parent=None):
        super().__init__(parent)
        transparent_menu(self)

        self.wdgFrame = frame()
        vbox(self.wdgFrame, 10)
        self.wdgFrame.setProperty('white-bg', True)
        self.wdgFrame.setProperty('large-rounded', True)

        self.btnGroupDimensions = ExclusiveOptionalButtonGroup()
        self.btnGroupModifiers = ExclusiveOptionalButtonGroup()

        self.btnGroupDimensions.buttonClicked.connect(self._dimensionClicked)

        self.wdgBond = rows(0)
        self.wdgConflict = rows(0)
        self.wdgCooperation = rows(0)

        self.wdgEditor = columns(0, 8)
        self.wdgEditor.layout().addWidget(self.wdgBond)
        self.wdgEditor.layout().addWidget(self.wdgCooperation)
        self.wdgEditor.layout().addWidget(self.wdgConflict)

        self.wdgFrame.layout().addWidget(
            label(
                "Select in which dimension the relationship evolves—bond, cooperation, or conflict—or choose a more specific subtype within those categories",
                description=True, wordWrap=True))
        self.wdgFrame.layout().addWidget(self.wdgEditor)

        btn = self.__initDimension('Bond', self.wdgBond, 'fa5s.hand-holding-heart')
        incr_font(btn, 2)
        self.wdgBond.layout().addWidget(line())
        self.__initDimension('Love', self.wdgBond, 'fa5s.heart')
        self.__initDimension('Friendship', self.wdgBond, 'ei.asl')
        self.__initDimension('Family', self.wdgBond, 'ei.group-alt')

        self.wdgBond.layout().addWidget(vspacer())

        btn = self.__initDimension('Cooperation', self.wdgCooperation, 'fa5.handshake')
        incr_font(btn, 2)
        self.wdgCooperation.layout().addWidget(line())
        self.__initDimension('Trust', self.wdgCooperation, 'fa5s.user-shield')
        self.__initDimension('Alliance', self.wdgCooperation, 'fa5s.thumbs-up')
        self.__initDimension('Respect', self.wdgCooperation, 'ri.award-fill')
        self.__initDimension('Loyalty', self.wdgCooperation, 'ei.link')
        self.wdgCooperation.layout().addWidget(vspacer())

        btn = self.__initDimension('Conflict', self.wdgConflict, 'mdi.sword-cross')
        incr_font(btn, 2)
        self.wdgConflict.layout().addWidget(line())
        self.__initDimension('Rivalry', self.wdgConflict, 'mdi6.trophy-outline')
        self.__initDimension('Betrayal', self.wdgConflict, 'mdi6.knife')
        self.__initDimension('Jealousy', self.wdgConflict, 'mdi.eye-circle-outline')
        self.wdgConflict.layout().addWidget(vspacer())

        self.wdgFrame.layout().addWidget(
            wrap(label(
                "Optionally select a modifier to reflect how the relationship dynamic has shifted",
                description=True), margin_top=25), alignment=Qt.AlignmentFlag.AlignRight)

        self.wdgModifiers = columns(0)
        self.wdgFrame.layout().addWidget(self.wdgModifiers, alignment=Qt.AlignmentFlag.AlignRight)
        self.__initModifier('Building')
        self.__initModifier('Growing')
        self.__initModifier('Strengthened')
        self.__initModifier('Pressured')
        self.__initModifier('Peaked')
        self.__initModifier('Fading')
        self.__initModifier('Broken')

        self.addWidget(self.wdgFrame)

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

    def _dimensionClicked(self):
        checkedDim = self.btnGroupDimensions.checkedButton() is not None
        if not checkedDim:
            self.btnGroupModifiers.reset()

        for btn in self.btnGroupModifiers.buttons():
            btn.setEnabled(checkedDim)

    def __initDimension(self, name: str, parent: QWidget, icon: str = '') -> _DimensionSelectorButton:
        btn = _DimensionSelectorButton(name, icon)
        self.btnGroupDimensions.addButton(btn)

        parent.layout().addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return btn

    def __initModifier(self, modifier: str) -> _ModifierSelectorButton:
        btn = _ModifierSelectorButton(modifier)
        self.btnGroupModifiers.addButton(btn)
        self.wdgModifiers.layout().addWidget(btn)

        return btn


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

    def _dimensionChanged(self, btn: _DimensionSelectorButton):
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

    def _modifierChanged(self, btn: _ModifierSelectorButton):
        self._lblModifier.setVisible(btn.isChecked())
        if btn.isChecked():
            self._lblModifier.setText(f'[{btn.modifier}]')
            self.element.modifier = btn.modifier
        else:
            self._lblModifier.setText('')
            self.element.modifier = ''
