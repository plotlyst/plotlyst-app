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
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget
from qthandy import decr_font, vbox, incr_font, line, vspacer
from qtmenu import MenuWidget

from plotlyst.view.common import frame, ExclusiveOptionalButtonGroup, rows, columns, label, wrap
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import transparent_menu
from plotlyst.view.widget.button import SelectorToggleButton


class DimensionSelectorButton(SelectorToggleButton):
    def __init__(self, dimension: str, icon: str, parent=None):
        super().__init__(Qt.ToolButtonStyle.ToolButtonTextBesideIcon, minWidth=80, parent=parent)
        self.dimension = dimension
        self.iconName = icon
        self.setText(dimension)
        self.setIcon(IconRegistry.from_name(icon))


class ModifierSelectorButton(SelectorToggleButton):
    def __init__(self, modifier: str, parent=None):
        super().__init__(Qt.ToolButtonStyle.ToolButtonTextBesideIcon, minWidth=60, parent=parent)
        self.modifier = modifier
        self.setText(modifier)
        decr_font(self)


class AbstractRelationshipChangeDimensionPopup(MenuWidget):
    def __init__(self, parent=None):
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

    def _dimensionClicked(self):
        checkedDim = self.btnGroupDimensions.checkedButton() is not None
        if not checkedDim:
            self.btnGroupModifiers.reset()

        for btn in self.btnGroupModifiers.buttons():
            btn.setEnabled(checkedDim)

    def __initDimension(self, name: str, parent: QWidget, icon: str = '') -> DimensionSelectorButton:
        btn = DimensionSelectorButton(name, icon)
        self.btnGroupDimensions.addButton(btn)

        parent.layout().addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return btn

    def __initModifier(self, modifier: str) -> ModifierSelectorButton:
        btn = ModifierSelectorButton(modifier)
        self.btnGroupModifiers.addButton(btn)
        self.wdgModifiers.layout().addWidget(btn)

        return btn
