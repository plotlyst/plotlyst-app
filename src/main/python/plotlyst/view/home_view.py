"""
Plotlyst
Copyright (C) 2021-2023  Zsolt Kovari

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

from PyQt6.QtCore import pyqtSignal, QSize, Qt
from PyQt6.QtGui import QPixmap
from overrides import overrides
from qthandy import ask_confirmation, clear_layout, flow, transparent, gc, incr_font, hbox

from src.main.python.plotlyst.core.client import client
from src.main.python.plotlyst.core.domain import NovelDescriptor, Event
from src.main.python.plotlyst.event.core import emit_event
from src.main.python.plotlyst.event.handler import event_dispatcher
from src.main.python.plotlyst.events import NovelDeletedEvent, NovelUpdatedEvent
from src.main.python.plotlyst.resources import resource_registry
from src.main.python.plotlyst.service.persistence import flush_or_fail
from src.main.python.plotlyst.view._view import AbstractView
from src.main.python.plotlyst.view.common import link_buttons_to_pages
from src.main.python.plotlyst.view.dialog.home import StoryCreationDialog
from src.main.python.plotlyst.view.generated.home_view_ui import Ui_HomeView
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.widget.cards import NovelCard
from src.main.python.plotlyst.view.widget.library import ShelvesTreeView


class HomeView(AbstractView):
    loadNovel = pyqtSignal(NovelDescriptor)

    def __init__(self):
        super(HomeView, self).__init__()
        self.ui = Ui_HomeView()
        self.ui.setupUi(self.widget)
        self._layout = flow(self.ui.novels, margin=5, spacing=9)
        self.novel_cards: List[NovelCard] = []
        # self.selected_card: Optional[NovelCard] = None
        self._selected_novel: Optional[NovelDescriptor] = None

        self.ui.lblBanner.setPixmap(QPixmap(resource_registry.banner))
        self.ui.btnTwitter.setIcon(IconRegistry.from_name('fa5b.twitter', 'white'))
        self.ui.btnInstagram.setIcon(IconRegistry.from_name('fa5b.instagram', 'white'))
        self.ui.btnFacebook.setIcon(IconRegistry.from_name('fa5b.facebook', 'white'))
        transparent(self.ui.btnTwitter)
        transparent(self.ui.btnInstagram)
        transparent(self.ui.btnFacebook)

        self.ui.btnLibrary.setIcon(IconRegistry.from_name('mdi.bookshelf', color_on='darkBlue'))
        self.ui.btnProgress.setIcon(IconRegistry.from_name('fa5s.chart-line'))
        self.ui.btnNotes.setIcon(IconRegistry.document_edition_icon())
        self.ui.btnRoadmap.setIcon(IconRegistry.from_name('fa5s.road'))

        self.ui.btnActivate.setIcon(IconRegistry.book_icon(color='white', color_on='white'))
        self.ui.btnActivate.clicked.connect(lambda: self.loadNovel.emit(self._selected_novel))
        self.ui.btnAdd.setIcon(IconRegistry.plus_icon(color='white'))
        self.ui.btnAddNewStoryMain.setIcon(IconRegistry.plus_icon(color='white'))
        self.ui.btnAdd.clicked.connect(self._add_new_novel)
        self.ui.btnAddNewStoryMain.clicked.connect(self._add_new_novel)

        transparent(self.ui.lineNovelTitle)
        self.ui.lineNovelTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        incr_font(self.ui.lineNovelTitle, 10)
        self.ui.lineNovelTitle.textEdited.connect(self._on_edit_title)
        self.ui.btnNovelSettings.setIcon(IconRegistry.dots_icon(vertical=True))

        self._shelvesTreeView = ShelvesTreeView()
        hbox(self.ui.wdgShelvesParent, 2, 3)
        self.ui.splitterLibrary.setSizes([100, 500])
        self.ui.wdgShelvesParent.layout().addWidget(self._shelvesTreeView)
        self._shelvesTreeView.novelSelected.connect(self._novel_selected)

        incr_font(self.ui.btnAddNewStoryMain, 8)
        self.ui.btnAddNewStoryMain.setIconSize(QSize(24, 24))
        # self.ui.btnDelete.setIcon(IconRegistry.trash_can_icon(color='white'))
        # self.ui.btnDelete.clicked.connect(self._on_delete)
        self.ui.btnActivate.setDisabled(True)

        link_buttons_to_pages(self.ui.stackedWidget,
                              [(self.ui.btnLibrary, self.ui.pageLibrary), (self.ui.btnProgress, self.ui.pageProgress),
                               (self.ui.btnNotes, self.ui.pageNotes), (self.ui.btnRoadmap, self.ui.pageRoadmap)])

        self.ui.btnLibrary.setChecked(True)

        self.refresh()

        self.ui.stackWdgNovels.setCurrentWidget(self.ui.pageEmpty)

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
        self._selected_novel = None
        self.ui.stackWdgNovels.setCurrentWidget(self.ui.pageEmpty)
        self._toggle_novel_buttons(False)
        # self.selected_card = None
        flush_or_fail()
        novels: List[NovelDescriptor] = client.novels()
        for novel in novels:
            card = NovelCard(novel)
            self._layout.addWidget(card)
            self.novel_cards.append(card)
            # card.selected.connect(self._card_selected)
            card.doubleClicked.connect(self.ui.btnActivate.click)

        self._shelvesTreeView.setNovels(novels)

    def _novel_selected(self, novel: NovelDescriptor):
        self._selected_novel = novel
        self._toggle_novel_buttons(True)

        self.ui.stackWdgNovels.setCurrentWidget(self.ui.pageNovelDisplay)

        self.ui.lineNovelTitle.setText(novel.title)

    def _add_new_novel(self):
        # if self.selected_card:
        #     self.selected_card.clearSelection()
        #     self._toggle_novel_buttons(False)
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

    def _on_edit_title(self, title: str):
        if title:
            self._selected_novel.title = title
            self.repo.update_project_novel(self._selected_novel)
            emit_event(NovelUpdatedEvent(self, self._selected_novel))

    # def _on_edit(self):
    #     title = NovelEditionDialog().display(self.selected_card.novel)
    #     if title:
    #         self.selected_card.novel.title = title
    #         self.selected_card.refresh()
    #         self.repo.update_project_novel(self.selected_card.novel)
    #         emit_event(NovelUpdatedEvent(self, self.selected_card.novel))

    def _on_delete(self):
        if ask_confirmation(f'Are you sure you want to delete the novel "{self.selected_card.novel.title}"?'):
            novel = self.selected_card.novel
            self.repo.delete_novel(novel)
            emit_event(NovelDeletedEvent(self, novel))
            gc(self.selected_card)
            self.selected_card = None
            # self.ui.btnDelete.setDisabled(True)
            self.refresh()

    # def _card_selected(self, card: NovelCard):
    #     if self.selected_card and self.selected_card is not card:
    #         self.selected_card.clearSelection()
    #     self.selected_card = card
    #     self._toggle_novel_buttons(True)

    def _toggle_novel_buttons(self, toggled: bool):
        # self.ui.btnDelete.setEnabled(toggled)
        # self.ui.btnEdit.setEnabled(toggled)
        self.ui.btnActivate.setEnabled(toggled)
