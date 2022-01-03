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
from typing import Any, List

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from overrides import overrides

from src.main.python.plotlyst.core.domain import Task, Scene, Character
from src.main.python.plotlyst.view.icons import IconRegistry


class TasksTableModel(QAbstractTableModel):
    ColType = 0
    ColRef = 1
    ColMessage = 2

    def __init__(self, tasks: List[Task], parent=None):
        super().__init__(parent)
        self.tasks = tasks

    @overrides
    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self.tasks)

    @overrides
    def columnCount(self, parent: QModelIndex = None) -> int:
        return 3

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return

        if index.column() == self.ColRef:
            if self.tasks[index.row()].reference:
                if isinstance(self.tasks[index.row()].reference, Scene):
                    if role == Qt.ItemDataRole.DisplayRole:
                        return self.tasks[index.row()].reference.title
                    if role == Qt.ItemDataRole.DecorationRole:
                        return IconRegistry.scene_icon()
                if isinstance(self.tasks[index.row()].reference, Character):
                    if role == Qt.ItemDataRole.DisplayRole:
                        return self.tasks[index.row()].reference.name
                    if role == Qt.ItemDataRole.DecorationRole:
                        return IconRegistry.character_icon()
        if index.column() == self.ColMessage:
            if role == Qt.ItemDataRole.DisplayRole:
                return self.tasks[index.row()].message
