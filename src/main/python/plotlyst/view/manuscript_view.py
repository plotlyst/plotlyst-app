"""
Plotlyst
Copyright (C) 2021  Zsolt Kovari

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

from typing import Optional

from PyQt5.QtCore import QModelIndex
from PyQt5.QtWidgets import QHeaderView, QTextEdit
from overrides import overrides

from src.main.python.plotlyst.core.client import json_client
from src.main.python.plotlyst.core.domain import Novel, Document
from src.main.python.plotlyst.event.core import emit_event
from src.main.python.plotlyst.events import NovelUpdatedEvent, SceneChangedEvent, OpenDistractionFreeMode
from src.main.python.plotlyst.model.chapters_model import ChaptersTreeModel, SceneNode, ChapterNode
from src.main.python.plotlyst.view._view import AbstractNovelView
from src.main.python.plotlyst.view.generated.manuscript_view_ui import Ui_ManuscriptView
from src.main.python.plotlyst.view.icons import IconRegistry


class ManuscriptView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel, [NovelUpdatedEvent, SceneChangedEvent])
        self.ui = Ui_ManuscriptView()
        self.ui.setupUi(self.widget)
        self._current_doc: Optional[Document] = None
        self.ui.splitter.setSizes([100, 500])
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageEmpty)

        self.ui.textEdit.setTitleVisible(False)
        self.ui.textEdit.setToolbarVisible(False)

        self.ui.btnDistractionFree.setIcon(IconRegistry.from_name('fa5s.external-link-alt'))
        # self.ui.btnTimer.setIcon(IconRegistry.timer_icon())
        # menu = QMenu(self.ui.btnTimer)
        # action = QWidgetAction(menu)
        # self._timer_setup = TimerSetupWidget()
        # action.setDefaultWidget(self._timer_setup)
        # menu.addAction(action)
        # self.ui.btnTimer.setMenu(menu)

        self.chaptersModel = ChaptersTreeModel(self.novel)
        self.ui.treeChapters.setModel(self.chaptersModel)
        self.ui.treeChapters.expandAll()
        self.chaptersModel.modelReset.connect(self.ui.treeChapters.expandAll)
        self.ui.treeChapters.setColumnWidth(1, 20)
        self.ui.treeChapters.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.ui.treeChapters.clicked.connect(self._edit)

        self.ui.textEdit.textEditor.textChanged.connect(self._save)
        self.ui.btnDistractionFree.clicked.connect(lambda: emit_event(OpenDistractionFreeMode(self, self.ui.textEdit)))

    @overrides
    def refresh(self):
        self.chaptersModel.modelReset.emit()

    def restore_editor(self, editor: QTextEdit):
        self.ui.pageText.layout().addWidget(editor)

    def _edit(self, index: QModelIndex):
        node = index.data(ChaptersTreeModel.NodeRole)
        if isinstance(node, SceneNode):
            if not node.scene.manuscript:
                node.scene.manuscript = Document('', scene_id=node.scene.id)
                self.repo.update_scene(node.scene)
            self._current_doc = node.scene.manuscript

            if not self._current_doc.loaded:
                json_client.load_document(self.novel, self._current_doc)

            self.ui.stackedWidget.setCurrentWidget(self.ui.pageText)
            self.ui.textEdit.setText(self._current_doc.content, self._current_doc.title)
            self.ui.textEdit.setMargins(30, 30, 30, 30)
            self.ui.textEdit.setFormat(130)
            self.ui.textEdit.textEditor.selectAll()
            self.ui.textEdit.textEditor.setFontPointSize(16)
        elif isinstance(node, ChapterNode):
            self.ui.stackedWidget.setCurrentWidget(self.ui.pageEmpty)

    def _save(self):
        if not self._current_doc:
            return
        self._current_doc.content = self.ui.textEdit.textEditor.toHtml()
        json_client.save_document(self.novel, self._current_doc)
