"""
Plotlyst
Copyright (C) 2021-2024  Zsolt Kovari

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

from PyQt6.QtCore import pyqtSignal, QSize, Qt, QEvent, QObject
from PyQt6.QtGui import QPixmap, QColor
from overrides import overrides
from qthandy import busy, vspacer, margins, pointy, retain_when_hidden
from qthandy.filter import OpacityEventFilter
from qtmenu import MenuWidget

from plotlyst.common import NAV_BAR_BUTTON_DEFAULT_COLOR, \
    NAV_BAR_BUTTON_CHECKED_COLOR, RELAXED_WHITE_COLOR, DEFAULT_PREMIUM_LINK
from plotlyst.core.client import client
from plotlyst.core.domain import NovelDescriptor, StoryType, Novel, WELCOME_DOC_ID
from plotlyst.core.help import home_page_welcome_text, WELCOME_DOC_CONTENT
from plotlyst.env import app_env
from plotlyst.event.core import emit_global_event, Event
from plotlyst.event.handler import global_event_dispatcher
from plotlyst.events import NovelDeletedEvent, NovelUpdatedEvent
from plotlyst.resources import resource_registry
from plotlyst.service.cache import entities_registry
from plotlyst.service.persistence import flush_or_fail
from plotlyst.service.tour import TourService
from plotlyst.view._view import AbstractView
from plotlyst.view.common import link_buttons_to_pages, ButtonPressResizeEventFilter, action, \
    TooltipPositionEventFilter, open_url, push_btn, wrap
from plotlyst.view.generated.home_view_ui import Ui_HomeView
from plotlyst.view.icons import IconRegistry
from plotlyst.view.roadmap_view import RoadmapView
from plotlyst.view.style.button import apply_button_palette_color
from plotlyst.view.widget.confirm import confirmed
from plotlyst.view.widget.kb.browser import KnowledgeBaseWidget
from plotlyst.view.widget.library import ShelvesTreeView, StoryCreationDialog, NovelDisplayCard, SeriesDisplayCard, \
    NovelSelectorPopup
from plotlyst.view.widget.patron import PlotlystPlusWidget
from plotlyst.view.widget.tour.core import LibraryTourEvent, NewStoryButtonTourEvent, \
    NewStoryDialogOpenTourEvent, TutorialNovelSelectTourEvent, NovelDisplayTourEvent, tutorial_novel, \
    NovelOpenButtonTourEvent, TutorialNovelCloseTourEvent
from plotlyst.view.widget.tree import TreeSettings


class HomeView(AbstractView):
    loadNovel = pyqtSignal(NovelDescriptor)

    def __init__(self):
        super(HomeView, self).__init__(
            [LibraryTourEvent, NewStoryButtonTourEvent, NewStoryDialogOpenTourEvent, TutorialNovelSelectTourEvent,
             NovelDisplayTourEvent, NovelOpenButtonTourEvent, TutorialNovelCloseTourEvent])
        self.ui = Ui_HomeView()
        self.ui.setupUi(self.widget)
        self._selected_novel: Optional[NovelDescriptor] = None
        self._novels: List[NovelDescriptor] = []
        self._tour_service = TourService.instance()

        self.ui.lblBanner.setPixmap(
            QPixmap(resource_registry.banner).scaled(180, 60, Qt.AspectRatioMode.KeepAspectRatio,
                                                     Qt.TransformationMode.SmoothTransformation))
        self.ui.btnPurchase.setIcon(IconRegistry.from_name('ei.shopping-cart', RELAXED_WHITE_COLOR))
        self.ui.btnJoinDiscord.setIcon(IconRegistry.from_name('fa5b.discord', RELAXED_WHITE_COLOR))
        self.ui.btnTwitter.setIcon(IconRegistry.from_name('fa5b.twitter', RELAXED_WHITE_COLOR))
        self.ui.btnInstagram.setIcon(IconRegistry.from_name('fa5b.instagram', RELAXED_WHITE_COLOR))
        self.ui.btnThreads.setIcon(IconRegistry.from_name('mdi.at', RELAXED_WHITE_COLOR))
        self.ui.btnPatreon.setIcon(IconRegistry.from_name('fa5b.patreon', RELAXED_WHITE_COLOR))
        self.ui.btnFacebook.setIcon(IconRegistry.from_name('fa5b.facebook', RELAXED_WHITE_COLOR))
        self.ui.btnYoutube.setIcon(IconRegistry.from_name('fa5b.youtube', RELAXED_WHITE_COLOR))
        self.ui.btnPinterest.setIcon(IconRegistry.from_name('fa5b.pinterest', RELAXED_WHITE_COLOR))
        self.ui.btnPurchase.installEventFilter(OpacityEventFilter(self.ui.btnPurchase, leaveOpacity=0.8))
        self.ui.btnJoinDiscord.installEventFilter(OpacityEventFilter(self.ui.btnJoinDiscord, leaveOpacity=0.8))
        self.ui.btnTwitter.installEventFilter(OpacityEventFilter(self.ui.btnTwitter, leaveOpacity=0.8))
        self.ui.btnInstagram.installEventFilter(OpacityEventFilter(self.ui.btnInstagram, leaveOpacity=0.8))
        self.ui.btnThreads.installEventFilter(OpacityEventFilter(self.ui.btnThreads, leaveOpacity=0.8))
        self.ui.btnPatreon.installEventFilter(OpacityEventFilter(self.ui.btnPatreon, leaveOpacity=0.8))
        self.ui.btnFacebook.installEventFilter(OpacityEventFilter(self.ui.btnFacebook, leaveOpacity=0.8))
        self.ui.btnYoutube.installEventFilter(OpacityEventFilter(self.ui.btnYoutube, leaveOpacity=0.8))
        self.ui.btnPinterest.installEventFilter(OpacityEventFilter(self.ui.btnPinterest, leaveOpacity=0.8))
        self.ui.btnPurchase.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnPurchase))
        self.ui.btnJoinDiscord.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnJoinDiscord))
        self.ui.btnTwitter.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnTwitter))
        self.ui.btnInstagram.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnInstagram))
        self.ui.btnThreads.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnThreads))
        self.ui.btnPatreon.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnPatreon))
        self.ui.btnFacebook.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnFacebook))
        self.ui.btnYoutube.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnYoutube))
        self.ui.btnPinterest.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnPinterest))
        self.ui.btnJoinDiscord.clicked.connect(lambda: open_url('https://discord.com/invite/9HZWnvNzM6'))
        self.ui.btnPurchase.clicked.connect(lambda: open_url(DEFAULT_PREMIUM_LINK))
        self.ui.btnTwitter.clicked.connect(lambda: open_url('https://twitter.com/plotlyst'))
        self.ui.btnInstagram.clicked.connect(lambda: open_url('https://www.instagram.com/plotlyst'))
        self.ui.btnThreads.clicked.connect(lambda: open_url('https://threads.net/@plotlyst'))
        self.ui.btnPatreon.clicked.connect(lambda: open_url('https://patreon.com/user?u=24283978'))
        self.ui.btnFacebook.clicked.connect(
            lambda: open_url('https://www.facebook.com/people/Plotlyst/61557773998679/'))
        self.ui.btnYoutube.clicked.connect(lambda: open_url('https://www.youtube.com/@Plotlyst'))
        self.ui.btnPinterest.clicked.connect(lambda: open_url('https://pinterest.com/Plotlyst'))

        self.ui.btnPurchase.setVisible(app_env.profile().get('license_type', 'FREE') == 'FREE')
        retain_when_hidden(self.ui.btnPurchase)

        self.ui.btnYoutube.setHidden(True)
        self.ui.btnPinterest.setHidden(True)

        self.ui.btnPurchase.setStyleSheet(f'color: {RELAXED_WHITE_COLOR}; border: 1px hidden black;')
        apply_button_palette_color(self.ui.btnJoinDiscord, RELAXED_WHITE_COLOR)
        pointy(self.ui.lblBanner)
        self.ui.lblBanner.installEventFilter(OpacityEventFilter(self.ui.lblBanner, leaveOpacity=1.0, enterOpacity=0.8))
        self.ui.lblBanner.installEventFilter(self)

        self.ui.btnLibrary.setIcon(
            IconRegistry.from_name('mdi.bookshelf', NAV_BAR_BUTTON_DEFAULT_COLOR, NAV_BAR_BUTTON_CHECKED_COLOR))
        self.ui.btnRoadmap.setIcon(
            IconRegistry.from_name('fa5s.road', NAV_BAR_BUTTON_DEFAULT_COLOR, NAV_BAR_BUTTON_CHECKED_COLOR))
        self.ui.btnPatrons.setIcon(
            IconRegistry.from_name('fa5b.patreon', NAV_BAR_BUTTON_DEFAULT_COLOR, NAV_BAR_BUTTON_CHECKED_COLOR))
        self.ui.btnKnowledgeBase.setIcon(
            IconRegistry.from_name('fa5s.graduation-cap', NAV_BAR_BUTTON_DEFAULT_COLOR, NAV_BAR_BUTTON_CHECKED_COLOR))

        for btn in self.ui.buttonGroup.buttons():
            btn.installEventFilter(OpacityEventFilter(btn, leaveOpacity=0.7, ignoreCheckedButton=True))
            btn.installEventFilter(TooltipPositionEventFilter(btn))

        self.ui.lblWelcomeMain.setText(home_page_welcome_text)

        self.ui.btnFirstStory.setIcon(IconRegistry.book_icon())
        self.ui.btnFirstStory.installEventFilter(OpacityEventFilter(self.ui.btnFirstStory, leaveOpacity=0.7))
        self.ui.btnFirstStory.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnFirstStory))

        self.novelDisplayCard = NovelDisplayCard()
        self.ui.pageNovelDisplay.layout().addWidget(self.novelDisplayCard)
        self.ui.pageNovelDisplay.layout().addWidget(vspacer())
        self.novelDisplayCard.btnActivate.clicked.connect(lambda: self.loadNovel.emit(self._selected_novel))
        self.novelDisplayCard.lineNovelTitle.textEdited.connect(self._title_edited)
        self.novelDisplayCard.lineSubtitle.textEdited.connect(self._subtitle_edited)
        self.novelDisplayCard.textSynopsis.textChanged.connect(self._short_synopsis_edited)
        self.novelDisplayCard.iconSelector.iconSelected.connect(self._icon_changed)

        self.seriesDisplayCard = SeriesDisplayCard()
        self.ui.scrollAreaSeries.layout().addWidget(self.seriesDisplayCard)
        self.ui.scrollAreaSeries.layout().addWidget(vspacer())
        self.seriesDisplayCard.lineNovelTitle.textEdited.connect(self._title_edited)
        self.seriesDisplayCard.iconSelector.iconSelected.connect(self._icon_changed)
        self.seriesDisplayCard.attachNovel.connect(self._attach_novel_to_series)
        self.seriesDisplayCard.detachNovel.connect(self._detach_novel_from_series)
        self.seriesDisplayCard.orderChanged.connect(self._series_novels_order_changed)
        self.seriesDisplayCard.openNovel.connect(self.loadNovel)

        self.ui.btnAddNewStoryMain.setIcon(IconRegistry.plus_icon(color='white'))
        self.ui.btnAddNewStoryMain.clicked.connect(self._add_new_novel)
        self.ui.btnAddNewStoryMain.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnAddNewStoryMain))

        menu = MenuWidget(self.novelDisplayCard.btnNovelSettings)
        menu.addAction(action('Delete', IconRegistry.trash_can_icon(), lambda: self._on_delete()))

        self._btnAddNew = push_btn(IconRegistry.plus_icon(RELAXED_WHITE_COLOR), tooltip='Add a new story',
                                   properties=['base', 'positive'])
        self._btnAddNew.clicked.connect(self._add_new_novel)
        self._shelvesTreeView = ShelvesTreeView(settings=TreeSettings(font_incr=2))
        margins(self._shelvesTreeView.centralWidget(), bottom=45)
        self.ui.splitterLibrary.setSizes([150, 500])
        self.ui.wdgShelvesParent.layout().addWidget(wrap(self._btnAddNew, margin_left=10, margin_top=10),
                                                    alignment=Qt.AlignmentFlag.AlignLeft)
        self.ui.wdgShelvesParent.layout().addWidget(self._shelvesTreeView)
        self._shelvesTreeView.novelSelected.connect(self._novel_selected)
        self._shelvesTreeView.novelChanged.connect(self._novel_changed_in_tree)
        self._shelvesTreeView.novelsShelveSelected.connect(self.reset)
        self._shelvesTreeView.newNovelRequested.connect(self._add_new_novel)
        self._shelvesTreeView.novelDeletionRequested.connect(self._on_delete)
        self._shelvesTreeView.novelOpenRequested.connect(self.loadNovel)
        self.seriesDisplayCard.displayNovel.connect(self._shelvesTreeView.selectNovel)
        self.novelDisplayCard.displaySeries.connect(self._shelvesTreeView.selectNovel)

        self.ui.btnAddNewStoryMain.setIconSize(QSize(24, 24))

        link_buttons_to_pages(self.ui.stackedWidget,
                              [(self.ui.btnLibrary, self.ui.pageLibrary),
                               (self.ui.btnRoadmap, self.ui.pageRoadmap),
                               (self.ui.btnPatrons, self.ui.pagePatrons),
                               (self.ui.btnKnowledgeBase, self.ui.pageKnowledgeBase),
                               ])

        self._roadmapView = RoadmapView()
        self.ui.pageRoadmap.layout().addWidget(self._roadmapView)

        self._knowledgeBase = KnowledgeBaseWidget()
        self.ui.pageKnowledgeBase.layout().addWidget(self._knowledgeBase)

        self._plotlystPlus = PlotlystPlusWidget()
        self.ui.pagePatrons.layout().addWidget(self._plotlystPlus)

        self.ui.btnLibrary.setChecked(True)
        self.ui.stackWdgNovels.setCurrentWidget(self.ui.pageEmpty)

        self._novels = client.novels()
        self.refresh()

        global_event_dispatcher.register(self, NovelUpdatedEvent)

    def novels(self) -> List[NovelDescriptor]:
        return self._novels

    def shelves(self) -> ShelvesTreeView:
        return self._shelvesTreeView

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonRelease:
            open_url('https://www.plotlyst.com')
        return super().eventFilter(watched, event)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, NovelUpdatedEvent):
            for novel in self._novels:
                if novel.id == event.novel.id:
                    novel.title = event.novel.title
            if self._selected_novel and self._selected_novel.id == event.novel.id:
                self.novelDisplayCard.lineNovelTitle.setText(self._selected_novel.title)
            self.refresh()
        elif isinstance(event, LibraryTourEvent):
            self._tour_service.addWidget(self.ui.btnLibrary, event)
        elif isinstance(event, NewStoryButtonTourEvent):
            self.ui.stackWdgNovels.setCurrentWidget(self.ui.pageEmpty)
            self._tour_service.addWidget(self.ui.btnAddNewStoryMain, event)
        elif isinstance(event, TutorialNovelSelectTourEvent):
            self._novel_selected(tutorial_novel)
            self._tour_service.next()
        elif isinstance(event, NovelDisplayTourEvent):
            self._tour_service.addWidget(self.ui.pageNovelDisplay, event)
        elif isinstance(event, NovelOpenButtonTourEvent):
            self._tour_service.addWidget(self.novelDisplayCard.btnActivate, event)
        elif isinstance(event, TutorialNovelCloseTourEvent):
            self.ui.stackWdgNovels.setCurrentWidget(self.ui.pageEmpty)
        else:
            super(HomeView, self).event_received(event)

    def reset(self):
        self._selected_novel = None
        self.ui.stackWdgNovels.setCurrentWidget(self.ui.pageEmpty)
        self._shelvesTreeView.clearSelection()

    @overrides
    def refresh(self):
        self._shelvesTreeView.setNovels(self._novels)

        series = [x for x in self._novels if x.story_type == StoryType.Series]
        entities_registry.set_series(series)

    def showKnowledgeBase(self):
        self.ui.btnKnowledgeBase.setChecked(True)

    def showRoadmap(self):
        self.ui.btnRoadmap.setChecked(True)

    def selectSeries(self, series: NovelDescriptor):
        self._shelvesTreeView.selectNovel(series)

    def selectNovel(self, novel: NovelDescriptor):
        for novel_desc in self._novels:
            if novel_desc.id == novel.id:
                self._shelvesTreeView.selectNovel(novel_desc)
                break

    def seriesNovels(self, series: NovelDescriptor) -> List[NovelDescriptor]:
        return self._shelvesTreeView.childrenNovels(series)

    def _novel_selected(self, novel: NovelDescriptor):
        self._selected_novel = None

        if novel.story_type == StoryType.Novel:
            self.ui.stackWdgNovels.setCurrentWidget(self.ui.pageNovelDisplay)
            self.novelDisplayCard.setNovel(novel)
            self._selected_novel = novel
        elif novel.story_type == StoryType.Series:
            self.ui.stackWdgNovels.setCurrentWidget(self.ui.pageSeriesDisplay)
            self.seriesDisplayCard.setNovel(novel)
            self.seriesDisplayCard.setChildren(self._shelvesTreeView.childrenNovels(novel))

        self._selected_novel = novel

    def _add_new_novel(self):
        @busy
        def flush():
            flush_or_fail()

        novel: Optional[Novel] = StoryCreationDialog.popup()
        if novel:
            if not novel.prefs.is_scenes_organization():
                for scene in novel.scenes:
                    scene.chapter = None
                    scene.title = ''
                novel.chapters.clear()

            self.repo.insert_novel(novel)
            self._novels.append(novel)
            flush()
            for character in novel.characters:
                self.repo.insert_character(novel, character)
            for scene in novel.scenes:
                self.repo.insert_scene(novel, scene)
                if scene.manuscript:
                    self.repo.update_doc(novel, scene.manuscript)

            for doc in novel.documents:
                if doc.id == WELCOME_DOC_ID:
                    doc.content = WELCOME_DOC_CONTENT
                    self.repo.update_doc(novel, doc)

            flush()

            self.refresh()
            self._shelvesTreeView.selectNovel(novel)
            if len(self._novels) == 1 and self._novels[0].story_type == StoryType.Novel:
                self.loadNovel.emit(novel)

    def _title_edited(self, title: str):
        if title:
            self._selected_novel.title = title
            self._shelvesTreeView.updateNovel(self._selected_novel)
            self.repo.update_project_novel(self._selected_novel)
            emit_global_event(NovelUpdatedEvent(self, self._selected_novel))

    def _subtitle_edited(self, subtitle: str):
        self._selected_novel.subtitle = subtitle
        self.repo.update_project_novel(self._selected_novel)
        emit_global_event(NovelUpdatedEvent(self, self._selected_novel))

    def _short_synopsis_edited(self):
        if self._selected_novel:
            self._selected_novel.short_synopsis = self.novelDisplayCard.textSynopsis.toPlainText()
            self.repo.update_project_novel(self._selected_novel)

    def _icon_changed(self, icon: str, color: QColor):
        self._selected_novel.icon = icon
        self._selected_novel.icon_color = color.name()
        self._shelvesTreeView.updateNovel(self._selected_novel)
        self.repo.update_project_novel(self._selected_novel)

        emit_global_event(NovelUpdatedEvent(self, self._selected_novel))

    def _novel_changed_in_tree(self, novel: NovelDescriptor):
        if self._selected_novel and self._selected_novel.id == novel.id:
            self.novelDisplayCard.lineNovelTitle.setText(self._selected_novel.title)
            if novel.icon:
                self.novelDisplayCard.iconSelector.selectIcon(novel.icon, novel.icon_color)
            else:
                self.novelDisplayCard.iconSelector.reset()
        self.repo.update_project_novel(novel)

        emit_global_event(NovelUpdatedEvent(self, self._selected_novel))

    def _on_delete(self, novel: Optional[NovelDescriptor] = None):
        if novel is None:
            novel = self._selected_novel
        if novel.story_type == StoryType.Series:
            title = f'Are you sure you want to delete the series "{novel.title}"?'
            msg = "<html>The attached novels <b>won't</b> be deleted."
        else:
            title = f'Are you sure you want to delete the novel "{novel.title}"?'
            msg = '<html><ul><li>This action cannot be undone.</li><li>All characters and scenes will be lost.</li>'

        if confirmed(msg, title):
            if novel.story_type == StoryType.Series:
                series_novels = self._shelvesTreeView.childrenNovels(novel)
                for sn in series_novels:
                    sn.parent = None
                    sn.sequence = 0
                    self.repo.update_project_novel(sn)
                    emit_global_event(NovelUpdatedEvent(self, sn))

            self.repo.delete_novel(novel)
            self._novels.remove(novel)
            emit_global_event(NovelDeletedEvent(self, novel))
            if self._selected_novel and novel.id == self._selected_novel.id:
                self.reset()
            self.refresh()

            if self._selected_novel:
                self._shelvesTreeView.selectNovel(self._selected_novel)

    def _attach_novel_to_series(self):
        if self._selected_novel and self._selected_novel.story_type == StoryType.Series:
            novel = NovelSelectorPopup.popup(self._novels)
            if novel and novel.parent != self._selected_novel.id:
                novel.parent = self._selected_novel.id
                novel.sequence = self.seriesDisplayCard.novelCount()
                self.repo.update_project_novel(novel)
                self.refresh()
                self._shelvesTreeView.selectNovel(self._selected_novel)

                emit_global_event(NovelUpdatedEvent(self, novel))

    @busy
    def _detach_novel_from_series(self, novel: NovelDescriptor):
        novel.parent = None
        novel.sequence = 0
        self.repo.update_project_novel(novel)
        self.refresh()
        self._shelvesTreeView.selectNovel(self._selected_novel)

        emit_global_event(NovelUpdatedEvent(self, novel))

    def _series_novels_order_changed(self, novels: List[NovelDescriptor]):
        for novel in novels:
            self.repo.update_project_novel(novel)
        self.refresh()
