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
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHeaderView
from overrides import overrides

from src.main.python.plotlyst.core.domain import Novel
from src.main.python.plotlyst.events import CharacterChangedEvent, SceneChangedEvent, SceneDeletedEvent
from src.main.python.plotlyst.model.scenes_model import ScenesTableModel
from src.main.python.plotlyst.view._view import AbstractNovelView
from src.main.python.plotlyst.view.delegates import ScenesViewDelegate
from src.main.python.plotlyst.view.generated.timeline_view_ui import Ui_TimelineView
from src.main.python.plotlyst.view.widget.timeline import TimelineWidget


class TimelineView(AbstractNovelView):
    colors = [Qt.GlobalColor.red, Qt.GlobalColor.blue, Qt.green, Qt.magenta, Qt.GlobalColor.darkBlue, Qt.darkGreen]

    def __init__(self, novel: Novel):
        super().__init__(novel, [CharacterChangedEvent, SceneChangedEvent, SceneDeletedEvent])
        self.ui = Ui_TimelineView()
        self.ui.setupUi(self.widget)

        self.model = ScenesTableModel(self.novel)
        self.ui.tblScenes.setModel(self.model)
        for col in range(self.model.columnCount()):
            self.ui.tblScenes.hideColumn(col)
        self.ui.tblScenes.showColumn(ScenesTableModel.ColTitle)
        self.ui.tblScenes.showColumn(ScenesTableModel.ColTime)
        self.ui.tblScenes.setColumnWidth(ScenesTableModel.ColTime, 40)
        self.ui.tblScenes.horizontalHeader().setSectionResizeMode(ScenesTableModel.ColTitle,
                                                                  QHeaderView.ResizeMode.Stretch)
        self._delegate = ScenesViewDelegate()

        self.timeline_widget = TimelineWidget(self.novel)
        self.ui.scrollAreaWidgetContents.layout().addWidget(self.timeline_widget)

        self.ui.tblScenes.setItemDelegate(self._delegate)

        self._delegate.commitData.connect(self.timeline_widget.update)

    @overrides
    def refresh(self):
        self.model.modelReset.emit()
