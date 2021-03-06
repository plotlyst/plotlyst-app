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

from PyQt5.QtCore import pyqtSignal
from overrides import overrides
from qthandy import ask_confirmation, clear_layout, flow

from src.main.python.plotlyst.core.client import client
from src.main.python.plotlyst.core.domain import NovelDescriptor, Event
from src.main.python.plotlyst.event.core import emit_event
from src.main.python.plotlyst.event.handler import event_dispatcher
from src.main.python.plotlyst.events import NovelDeletedEvent, NovelUpdatedEvent
from src.main.python.plotlyst.service.persistence import flush_or_fail
from src.main.python.plotlyst.view._view import AbstractView
from src.main.python.plotlyst.view.dialog.home import StoryCreationDialog
from src.main.python.plotlyst.view.dialog.novel import NovelEditionDialog
from src.main.python.plotlyst.view.generated.home_view_ui import Ui_HomeView
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.widget.cards import NovelCard


class HomeView(AbstractView):
    loadNovel = pyqtSignal(NovelDescriptor)

    def __init__(self):
        super(HomeView, self).__init__()
        self.ui = Ui_HomeView()
        self.ui.setupUi(self.widget)
        self._layout = flow(self.ui.novels, margin=5, spacing=9)
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

        event_dispatcher.register(self, NovelUpdatedEvent)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, NovelUpdatedEvent):
            for card in self.novel_cards:
                if card.novel.id == event.novel.id:
                    card.novel.title = event.novel.title
                    card.refresh()
        else:
            super(HomeView, self).event_received(event)

    @overrides
    def refresh(self):
        clear_layout(self._layout)
        self.novel_cards.clear()
        self._toggle_novel_buttons(False)
        self.selected_card = None
        flush_or_fail()
        for novel in client.novels():
            card = NovelCard(novel)
            self._layout.addWidget(card)
            self.novel_cards.append(card)
            card.selected.connect(self._card_selected)
            card.doubleClicked.connect(self.ui.btnActivate.click)

    def _add_new_novel(self):
        if self.selected_card:
            self.selected_card.clearSelection()
            self._toggle_novel_buttons(False)
        novel = StoryCreationDialog(self.widget).display()
        if novel:
            self.repo.insert_novel(novel)
            for character in novel.characters:
                self.repo.insert_character(novel, character)
            for scene in novel.scenes:
                self.repo.insert_scene(novel, scene)
                if scene.manuscript:
                    self.repo.update_doc(novel, scene.manuscript)
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
        self._toggle_novel_buttons(True)

    def _toggle_novel_buttons(self, toggled: bool):
        self.ui.btnDelete.setEnabled(toggled)
        self.ui.btnEdit.setEnabled(toggled)
        self.ui.btnActivate.setEnabled(toggled)
