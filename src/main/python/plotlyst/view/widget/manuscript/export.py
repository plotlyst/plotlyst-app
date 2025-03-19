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
from overrides import overrides
from qthandy import vbox, busy

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import Novel
from plotlyst.event.core import EventListener, Event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import NovelScenesOrganizationToggleEvent
from plotlyst.service.manuscript import export_manuscript_to_docx
from plotlyst.view.common import push_btn, exclusive_buttons
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.settings import Forms


class ManuscriptExportWidget(QWidget, EventListener):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        vbox(self, 5, spacing=15)

        self.chapterForms = Forms('Chapter titles')
        self.chapterSceneTitle = self.chapterForms.addSetting("First scene's title")
        self.chapterScenePov = self.chapterForms.addSetting("POV's name")
        self.chapterForms.setRowVisible(0, self._novel.prefs.is_scenes_organization())
        exclusive_buttons(self, self.chapterSceneTitle, self.chapterScenePov, optional=True)

        self._btnExport = push_btn(IconRegistry.from_name('mdi.file-word-outline', RELAXED_WHITE_COLOR),
                                   'Export to docx',
                                   properties=['base', 'positive'])
        self._btnExport.clicked.connect(self._export)

        self.layout().addWidget(self.chapterForms)
        self.layout().addWidget(self._btnExport, alignment=Qt.AlignmentFlag.AlignCenter)

        event_dispatchers.instance(self._novel).register(self, NovelScenesOrganizationToggleEvent)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, NovelScenesOrganizationToggleEvent):
            self.chapterForms.setRowVisible(0, self._novel.prefs.is_scenes_organization())

    @busy
    def _export(self):
        export_manuscript_to_docx(self._novel, sceneTitle=self.chapterSceneTitle.isChecked(),
                                  povTitle=self.chapterScenePov.isChecked())
