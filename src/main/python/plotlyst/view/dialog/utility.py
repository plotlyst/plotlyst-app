"""
Plotlyst
Copyright (C) 2021-2022  Zsolt Kovari

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

from PyQt6 import QtGui
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QDialog, QHBoxLayout
from overrides import overrides

from src.main.python.plotlyst.view.widget.utility import IconSelectorWidget


class IconSelectorDialog(QDialog):

    def __init__(self, parent=None):
        super(IconSelectorDialog, self).__init__(parent)
        self.setWindowTitle('Select icon')

        self.resize(500, 500)
        self.setLayout(QHBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(1, 1, 1, 1)

        self._icon = ''
        self._color = None
        self.selector = IconSelectorWidget(self)
        self.selector.iconSelected.connect(self._icon_selected)

        self.layout().addWidget(self.selector)

    def display(self):
        result = self.exec()
        if result == QDialog.Accepted and self._icon:
            return self._icon, self._color

    @overrides
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self.selector.lstIcons.model().modelReset.emit()
        self.selector.lstIcons.update()

    def _icon_selected(self, icon_alias: str, color: QColor):
        self._icon = icon_alias
        self._color = color

        self.accept()
