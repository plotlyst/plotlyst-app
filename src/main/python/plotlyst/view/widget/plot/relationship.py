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
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget
from qthandy import vbox

from plotlyst.core.domain import Plot, Novel
from plotlyst.view.common import label


class RelationshipDynamicsWidget(QWidget):
    changed = pyqtSignal()

    def __init__(self, plot: Plot, novel: Novel, parent=None):
        super().__init__(parent)
        self._plot = plot
        self._novel = novel

        vbox(self)
        self.layout().addWidget(label('Test rel'))
