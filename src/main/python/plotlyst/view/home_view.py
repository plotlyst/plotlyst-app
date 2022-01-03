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
from typing import List, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFileDialog
from overrides import overrides

from src.main.python.plotlyst.core.client import client
from src.main.python.plotlyst.core.domain import Novel, NovelDescriptor
from src.main.python.plotlyst.core.scrivener import ScrivenerImporter
from src.main.python.plotlyst.event.core import emit_event
from src.main.python.plotlyst.events import NovelDeletedEvent, NovelUpdatedEvent
from src.main.python.plotlyst.view._view import AbstractView
from src.main.python.plotlyst.view.common import ask_confirmation
from src.main.python.plotlyst.view.dialog.novel import NovelEditionDialog
from src.main.python.plotlyst.view.generated.home_view_ui import Ui_HomeView
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.layout import FlowLayout
from src.main.python.plotlyst.view.widget.cards import NovelCard
from src.main.python.plotlyst.worker.persistence import flush_or_fail


class HomeView(AbstractView):
    loadNovel = pyqtSignal(NovelDescriptor)

    def __init__(self):
        super(HomeView, self).__init__()
        self.ui = Ui_HomeView()
        self.ui.setupUi(self.widget)
        self._layout = FlowLayout(spacing=9)
        self.ui.novels.setLayout(self._layout)
        self.novel_cards: List[NovelCard] = []
        self.selected_card: Optional[NovelCard] = None
        self.refresh()

        self.ui.btnActivate.setIcon(IconRegistry.book_icon(color='white', color_on='white'))
        self.ui.btnActivate.clicked.connect(lambda: self.loadNovel.emit(self.selected_card.novel))
        self.ui.btnAdd.setIcon(IconRegistry.plus_icon(color='white'))
        self.ui.btnAdd.clicked.connect(self._add_new_novel)
        self.ui.btnEdit.setIcon(IconRegistry.edit_icon())
        self.ui.btnEdit.clicked.connect(self._on_edit)
        self.ui.btnDelete.setIcon(IconRegistry.trash_can_icon(color='white'))
        self.ui.btnDelete.clicked.connect(self._on_delete)
        self.ui.btnDelete.setDisabled(True)
        self.ui.btnEdit.setDisabled(True)
        self.ui.btnActivate.setDisabled(True)

    @overrides
    def refresh(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item:
                item.widget().deleteLater()
        self.novel_cards.clear()
        self.ui.btnDelete.setDisabled(True)
        self.ui.btnEdit.setDisabled(True)
        self.ui.btnActivate.setDisabled(True)
        self.selected_card = None
        flush_or_fail()
        for novel in client.novels():
            card = NovelCard(novel)
            self._layout.addWidget(card)
            self.novel_cards.append(card)
            card.selected.connect(self._card_selected)
            card.doubleClicked.connect(self.ui.btnActivate.click)

    def import_from_scrivener(self):
        project = QFileDialog.getExistingDirectory(None, 'Choose a Scrivener project directory')
        if not project:
            return
        importer = ScrivenerImporter()
        novel: Novel = importer.import_project(project)
        self.repo.insert_novel(novel)
        for scene in novel.scenes:
            self.repo.insert_scene(novel, scene)
        self.refresh()

    def _add_new_novel(self):
        if self.selected_card:
            self.selected_card.clearSelection()
            self.ui.btnDelete.setDisabled(True)
            self.ui.btnEdit.setDisabled(True)
        title = NovelEditionDialog().display()
        if title:
            self.repo.insert_novel(Novel(title))
            self.refresh()

    def _on_edit(self):
        title = NovelEditionDialog().display(self.selected_card.novel)
        if title:
            self.selected_card.novel.title = title
            self.selected_card.refresh()
            self.repo.update_project_novel(self.selected_card.novel)
            emit_event(NovelUpdatedEvent(self, self.selected_card.novel))

    def _on_delete(self):
        if ask_confirmation(f'Are you sure you want to delete the novel "{self.selected_card.novel.title}"?'):
            novel = self.selected_card.novel
            self.repo.delete_novel(novel)
            emit_event(NovelDeletedEvent(self, novel))
            self.selected_card.deleteLater()
            self.selected_card = None
            self.ui.btnDelete.setDisabled(True)
            self.refresh()

    def _card_selected(self, card: NovelCard):
        if self.selected_card and self.selected_card is not card:
            self.selected_card.clearSelection()
        self.selected_card = card
        self.ui.btnDelete.setEnabled(True)
        self.ui.btnEdit.setEnabled(True)
        self.ui.btnActivate.setEnabled(True)
