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
from abc import abstractmethod
from enum import Enum, auto
from typing import Optional, List

from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import QWidget, QFrame
from overrides import overrides
from qthandy import bold, vbox, hbox
from qthandy.filter import OpacityEventFilter

from plotlyst.common import PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import Novel
from plotlyst.event.core import EventListener, Event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import CharacterChangedEvent, SceneChangedEvent, SceneDeletedEvent, \
    CharacterDeletedEvent, NovelSyncEvent, StorylineCreatedEvent, StorylineRemovedEvent, NovelStoryStructureUpdated, \
    NovelScenesOrganizationToggleEvent
from plotlyst.view._view import AbstractNovelView
from plotlyst.view.common import link_buttons_to_pages, scrolled
from plotlyst.view.generated.reports_view_ui import Ui_ReportsView
from plotlyst.view.icons import IconRegistry
from plotlyst.view.report import AbstractReport
from plotlyst.view.report.character import CharacterReport
from plotlyst.view.report.manuscript import ManuscriptReport
from plotlyst.view.report.plot import ArcReport
from plotlyst.view.report.productivity import ProductivityReport
from plotlyst.view.report.scene import SceneReport


class ReportType(Enum):
    CHARACTERS = auto()
    SCENES = auto()
    ARC = auto()
    MANUSCRIPT = auto()


report_classes = {ReportType.CHARACTERS: CharacterReport}


class ReportPage(QWidget, EventListener):
    def __init__(self, novel: Novel, parent=None):
        super(ReportPage, self).__init__(parent)
        self._novel: Novel = novel
        self._report: Optional[AbstractReport] = None
        self._refreshNext: bool = False

        vbox(self)

        self._scrollarea, self._wdgCenter = scrolled(self, frameless=True)
        hbox(self._wdgCenter)
        if self._hasFrame():
            self._wdgFrame = QFrame()
            self._wdgCenter.layout().addWidget(self._wdgFrame)
            self._wdgFrame.setProperty('relaxed-white-bg', True)
            self._wdgFrame.setProperty('large-rounded', True)
            hbox(self._wdgFrame, 20, 0)
            self._wdgFrame.setMaximumWidth(1200)
        else:
            self._wdgCenter.setProperty('relaxed-white-bg', True)

        self._dispatcher = event_dispatchers.instance(self._novel)
        self._dispatcher.register(self, NovelSyncEvent)

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        if self._report is None:
            self._report = self._initReport()
            if self._hasFrame():
                self._wdgFrame.layout().addWidget(self._report)
            else:
                self._wdgCenter.layout().addWidget(self._report)
        elif self._refreshNext:
            self.refresh()
            self._refreshNext = False

    @overrides
    def event_received(self, event: Event):
        if self.isVisible():
            self.refresh()
        else:
            self._refreshNext = True

    def refresh(self):
        if self._report:
            self._report.refresh()

    def _hasFrame(self) -> bool:
        return False

    @abstractmethod
    def _initReport(self) -> AbstractReport:
        pass


class CharactersReportPage(ReportPage):

    def __init__(self, novel: Novel, parent=None):
        super(CharactersReportPage, self).__init__(novel, parent)
        self._dispatcher.register(self, CharacterChangedEvent, CharacterDeletedEvent)

    @overrides
    def _hasFrame(self) -> bool:
        return True

    @overrides
    def _initReport(self):
        return CharacterReport(self._novel)


class ScenesReportPage(ReportPage):
    def __init__(self, novel: Novel, parent=None):
        super(ScenesReportPage, self).__init__(novel, parent)
        self._dispatcher.register(self, SceneChangedEvent, SceneDeletedEvent, CharacterChangedEvent,
                                  CharacterDeletedEvent, NovelStoryStructureUpdated)

    @overrides
    def _hasFrame(self) -> bool:
        return True

    @overrides
    def _initReport(self):
        return SceneReport(self._novel)


class ArcReportPage(ReportPage):
    def __init__(self, novel: Novel, parent=None):
        super(ArcReportPage, self).__init__(novel, parent)
        self._dispatcher.register(self, StorylineCreatedEvent, StorylineRemovedEvent, SceneChangedEvent,
                                  SceneDeletedEvent, CharacterChangedEvent)

    @overrides
    def _initReport(self):
        return ArcReport(self._novel)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, StorylineRemovedEvent):
            if self._report:
                self._report.removeStoryline(event.storyline)
        else:
            super().event_received(event)


class ManuscriptReportPage(ReportPage):
    def __init__(self, novel: Novel, parent=None):
        super(ManuscriptReportPage, self).__init__(novel, parent)
        self._dispatcher.register(self, SceneChangedEvent, SceneDeletedEvent, NovelScenesOrganizationToggleEvent)
        self._wc_cache: List[int] = []

    @overrides
    def _initReport(self):
        return ManuscriptReport(self._novel)

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        if not self._refreshNext:
            prev_wc = []
            prev_wc.extend(self._wc_cache)
            self._cacheWordCounts()
            if prev_wc != self._wc_cache:
                self._refreshNext = True
        super(ManuscriptReportPage, self).showEvent(event)

    @overrides
    def refresh(self):
        super(ManuscriptReportPage, self).refresh()
        self._cacheWordCounts()

    def _cacheWordCounts(self):
        self._wc_cache.clear()
        for scene in self._novel.scenes:
            if scene.manuscript and scene.manuscript.statistics:
                self._wc_cache.append(scene.manuscript.statistics.wc)
            else:
                self._wc_cache.append(0)


class ProductivityReportPage(ReportPage):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(novel, parent)

    @overrides
    def _hasFrame(self) -> bool:
        return True

    @overrides
    def _initReport(self):
        return ProductivityReport(self._novel)


class ReportsView(AbstractNovelView):
    def __init__(self, novel: Novel):
        super().__init__(novel)
        self.ui = Ui_ReportsView()
        self.ui.setupUi(self.widget)

        bold(self.ui.lblTitle)

        self.ui.iconReports.setIcon(IconRegistry.reports_icon())
        self.ui.btnCharacters.setIcon(IconRegistry.character_icon())
        self.ui.btnScenes.setIcon(IconRegistry.scene_icon())
        self.ui.btnConflict.setIcon(IconRegistry.conflict_icon('black', color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnArc.setIcon(IconRegistry.rising_action_icon('black', color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnManuscript.setIcon(IconRegistry.manuscript_icon())
        self.ui.btnProductivity.setIcon(
            IconRegistry.from_name('mdi6.progress-star-four-points', color_on=PLOTLYST_SECONDARY_COLOR))

        self.ui.btnConflict.setHidden(True)

        for btn in self.ui.buttonGroup.buttons():
            btn.installEventFilter(OpacityEventFilter(btn, leaveOpacity=0.7, ignoreCheckedButton=True))
            btn.setProperty('transparent-circle-bg-on-hover', True)
            btn.setProperty('large', True)
            btn.setProperty('top-selector', True)

        self._page_characters = CharactersReportPage(self.novel)
        self.ui.stackedWidget.addWidget(self._page_characters)
        self._page_scenes = ScenesReportPage(self.novel)
        self.ui.stackedWidget.addWidget(self._page_scenes)
        # self._page_conflicts = ConflictsReportPage(self.novel)
        # self.ui.stackedWidget.addWidget(self._page_conflicts)
        self._page_arc = ArcReportPage(self.novel)
        self.ui.stackedWidget.addWidget(self._page_arc)
        self._page_manuscript = ManuscriptReportPage(self.novel)
        self.ui.stackedWidget.addWidget(self._page_manuscript)

        self._page_productivty = ProductivityReportPage(self.novel)
        self.ui.stackedWidget.addWidget(self._page_productivty)

        link_buttons_to_pages(self.ui.stackedWidget, [
            (self.ui.btnCharacters, self._page_characters),
            (self.ui.btnScenes, self._page_scenes),
            (self.ui.btnArc, self._page_arc),
            (self.ui.btnManuscript, self._page_manuscript),
            (self.ui.btnProductivity, self._page_productivty)
        ])

        self.ui.btnCharacters.setChecked(True)

    @overrides
    def refresh(self):
        pass
