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
from PyQt6.QtCore import QModelIndex, QItemSelectionModel
from PyQt6.QtWidgets import QTreeView
from overrides import overrides


class ActionBasedTreeView(QTreeView):

    def __init__(self, parent=None):
        super(ActionBasedTreeView, self).__init__(parent)

    @overrides
    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        index = self.indexAt(event.pos())
        self.model().displayAction(index)
        super(ActionBasedTreeView, self).mouseMoveEvent(event)

    def select(self, index: QModelIndex):
        self.selectionModel().select(index, QItemSelectionModel.Select)
