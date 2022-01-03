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
from typing import List

from PyQt6 import QtGui
from PyQt6.QtWidgets import QWidget
from overrides import overrides

from src.main.python.plotlyst.core.domain import Novel, Task
from src.main.python.plotlyst.model.tasks_model import TasksTableModel
from src.main.python.plotlyst.view.generated.tasks_widget_ui import Ui_TasksWidget


class TasksWidget(QWidget, Ui_TasksWidget):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.novel = novel

        self.tasks: List[Task] = []
        self.model = TasksTableModel(self.tasks)
        self.tblTasks.setModel(self.model)
        self.tblTasks.setColumnWidth(TasksTableModel.ColType, 30)
        self.tblTasks.setColumnWidth(TasksTableModel.ColRef, 200)

        self.updateTasks()

    @overrides
    def showEvent(self, event: QtGui.QShowEvent) -> None:
        self.updateTasks()

    def updateTasks(self):
        self.tasks.clear()
        if not self.novel:
            return

        for scene in self.novel.scenes:
            if scene.wip:
                continue
            if not scene.pov:
                self.tasks.append(Task('POV is missing', reference=scene))
            if not scene.title or scene.title == 'Untitled':
                self.tasks.append(Task('Title is not specified', reference=scene))
            if not scene.beginning:
                self.tasks.append(Task('Beginning event is missing', reference=scene))
            if not scene.middle:
                self.tasks.append(Task('Middle event is missing', reference=scene))
            if not scene.end:
                self.tasks.append(Task('End event is missing', reference=scene))

        self.model.modelReset.emit()
