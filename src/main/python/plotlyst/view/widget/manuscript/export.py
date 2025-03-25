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
from qthandy import vbox, busy, margins, decr_icon, decr_font

from plotlyst.common import RELAXED_WHITE_COLOR, IGNORE_CAPITALIZATION_PROPERTY
from plotlyst.core.domain import Novel
from plotlyst.event.core import EventListener, Event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import NovelScenesOrganizationToggleEvent
from plotlyst.service.manuscript import export_manuscript_to_docx
from plotlyst.view.common import push_btn, exclusive_buttons, label, fade, frame, wrap
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.button import SmallToggleButton
from plotlyst.view.widget.input import DecoratedLineEdit
from plotlyst.view.widget.settings import Forms


class ManuscriptExportWidget(QWidget, EventListener):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        vbox(self, 5, spacing=15)

        self.toggleTitlePage = SmallToggleButton()
        self.toggleTitlePage.setChecked(True)
        self.layout().addWidget(group(label('Title page', bold=True), self.toggleTitlePage, margin=0, spacing=0),
                                alignment=Qt.AlignmentFlag.AlignLeft)

        self.nameFrame = frame()
        self.nameFrame.setProperty('rounded', True)
        self.nameFrame.setProperty('bg', True)
        vbox(self.nameFrame, 4)
        margins(self.nameFrame, left=10)
        self.lineName = DecoratedLineEdit(autoAdjustable=False)
        self.lineName.lineEdit.setPlaceholderText("Author's name")
        self.lineName.setIcon(IconRegistry.from_name('mdi.account'))
        decr_icon(self.lineName.icon, 4)
        decr_font(self.lineName.lineEdit)
        self.nameFrame.layout().addWidget(self.lineName)
        self.layout().addWidget(wrap(self.nameFrame, margin_left=10), alignment=Qt.AlignmentFlag.AlignLeft)

        self.emailFrame = frame()
        self.emailFrame.setProperty('rounded', True)
        self.emailFrame.setProperty('bg', True)
        vbox(self.emailFrame, 4)
        self.lineEmail = DecoratedLineEdit(autoAdjustable=False)
        self.lineEmail.lineEdit.setPlaceholderText('Email')
        self.lineEmail.lineEdit.setProperty(IGNORE_CAPITALIZATION_PROPERTY, True)
        self.lineEmail.setIcon(IconRegistry.from_name('fa5s.at'))
        decr_icon(self.lineEmail.icon, 4)
        decr_font(self.lineEmail.lineEdit)
        self.emailFrame.layout().addWidget(self.lineEmail)
        self.layout().addWidget(wrap(self.emailFrame, margin_left=10), alignment=Qt.AlignmentFlag.AlignLeft)

        self.toggleTitlePage.toggled.connect(self._titlePageToggled)

        self.chapterForms = Forms('Chapter titles')
        self.chapterSceneTitle = self.chapterForms.addSetting("First scene's title")
        self.chapterScenePov = self.chapterForms.addSetting("POV's name")
        self.chapterForms.setRowVisible(0, self._novel.prefs.is_scenes_organization())
        exclusive_buttons(self, self.chapterSceneTitle, self.chapterScenePov, optional=True)

        self._btnExport = push_btn(IconRegistry.from_name('mdi.file-word-outline', RELAXED_WHITE_COLOR),
                                   'Export to docx',
                                   properties=['confirm', 'positive'])
        self._btnExport.clicked.connect(self._export)

        self.layout().addWidget(self.chapterForms)
        self.layout().addWidget(self._btnExport, alignment=Qt.AlignmentFlag.AlignCenter)

        event_dispatchers.instance(self._novel).register(self, NovelScenesOrganizationToggleEvent)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, NovelScenesOrganizationToggleEvent):
            self.chapterForms.setRowVisible(0, self._novel.prefs.is_scenes_organization())

    def _titlePageToggled(self, toggled: bool):
        fade(self.nameFrame, toggled)
        fade(self.emailFrame, toggled)

    @busy
    def _export(self, _):
        export_manuscript_to_docx(self._novel, sceneTitle=self.chapterSceneTitle.isChecked(),
                                  povTitle=self.chapterScenePov.isChecked(), titlePage=self.toggleTitlePage.isChecked(),
                                  author=self.lineName.lineEdit.text(), email=self.lineEmail.lineEdit.text())
