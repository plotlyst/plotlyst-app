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
import datetime
from functools import partial
from typing import Optional, Dict, Set

from PyQt6.QtCore import QEvent, QThreadPool, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QSizePolicy, QFrame
from overrides import overrides
from qthandy import clear_layout, hbox, spacer, margins, vbox, incr_font, retain_when_hidden, decr_icon, translucent, \
    decr_font, transparent, vspacer, italic
from qthandy.filter import VisibilityToggleEventFilter, OpacityEventFilter

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, PLOTLYST_MAIN_COLOR, RELAXED_WHITE_COLOR
from plotlyst.core.domain import Board, Task, TaskStatus
from plotlyst.core.template import SelectionItem
from plotlyst.env import app_env
from plotlyst.service.resource import JsonDownloadWorker, JsonDownloadResult
from plotlyst.view.common import push_btn, spin, shadow, tool_btn, open_url, ButtonPressResizeEventFilter
from plotlyst.view.generated.roadmap_view_ui import Ui_RoadmapView
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.style.button import apply_button_palette_color
from plotlyst.view.widget.input import AutoAdjustableTextEdit
from plotlyst.view.widget.task import BaseStatusColumnWidget
from plotlyst.view.widget.tree import TreeView, EyeToggleNode

tags_counter: Dict[str, int] = {}
versions_counter: Dict[str, int] = {}


class TagsTreeView(TreeView):
    toggled = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)

    def setTags(self, tags: Dict[str, SelectionItem]):
        self.clear()
        for k, v in tags.items():
            node = EyeToggleNode(f'{k.capitalize()} ({tags_counter.get(k, 0)})',
                                 IconRegistry.from_name(v.icon, color=v.icon_color))
            node.setToolTip(v.text)
            node.toggled.connect(partial(self.toggled.emit, k))
            self._centralWidget.layout().addWidget(node)

        self._centralWidget.layout().addWidget(vspacer())

    def clear(self):
        clear_layout(self._centralWidget)


class RoadmapTaskWidget(QFrame):

    def __init__(self, task: Task, tags: Dict[str, SelectionItem], parent=None):
        super().__init__(parent)
        self._task: Task = task

        self.setProperty('relaxed-white-bg', True)
        self.setProperty('rounded', True)

        vbox(self, margin=5)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.setMinimumHeight(75)
        shadow(self, 3)

        self._textTitle = AutoAdjustableTextEdit(self)
        self._textTitle.setPlaceholderText('New task')
        self._textTitle.setText(task.title)
        self.setToolTip(task.summary)
        transparent(self._textTitle)
        self._textTitle.setReadOnly(True)
        font = QFont(app_env.sans_serif_font())
        font.setWeight(QFont.Weight.Medium)
        self._textTitle.setFont(font)
        incr_font(self._textTitle)

        self._btnOpenInExternal = tool_btn(IconRegistry.from_name('fa5s.external-link-alt', 'grey'), transparent_=True,
                                           tooltip='Open in browser')
        self._btnOpenInExternal.clicked.connect(lambda: open_url(self._task.web_link))
        retain_when_hidden(self._btnOpenInExternal)
        decr_icon(self._btnOpenInExternal, 4)

        top_wdg = group(self._textTitle, spacer(), self._btnOpenInExternal, margin=0, spacing=1)
        self.layout().addWidget(top_wdg, alignment=Qt.AlignmentFlag.AlignTop)

        self._wdgBottom = QWidget()
        retain_when_hidden(self._wdgBottom)
        hbox(self._wdgBottom)

        for tag_name in self._task.tags:
            tag = tags.get(tag_name)
            if tag:
                btn = tool_btn(IconRegistry.from_name(tag.icon, tag.icon_color), transparent_=True, icon_resize=False,
                               pointy_=False, tooltip=tag.text)
                decr_icon(btn, 4)
                translucent(btn, 0.7)
                self._wdgBottom.layout().addWidget(btn)

        self._wdgBottom.layout().addWidget(spacer())
        if self._task.version == 'Plus':
            self._btnVersion = push_btn(text=self._task.version, properties=['transparent'],
                                        tooltip='Feature will be available in Plotlyst Plus', icon_resize=False,
                                        pointy_=False)
            self._btnVersion.setIcon(IconRegistry.from_name('mdi.certificate', color=PLOTLYST_MAIN_COLOR))
            apply_button_palette_color(self._btnVersion, PLOTLYST_MAIN_COLOR)
            decr_font(self._btnVersion)
            decr_icon(self._btnVersion, 2)
            self._wdgBottom.layout().addWidget(self._btnVersion)

        self.layout().addWidget(self._wdgBottom, alignment=Qt.AlignmentFlag.AlignBottom)

        self.installEventFilter(VisibilityToggleEventFilter(self._btnOpenInExternal, self))

    def task(self) -> Task:
        return self._task


class RoadmapStatusColumn(BaseStatusColumnWidget):

    def __init__(self, status: TaskStatus, parent=None):
        super().__init__(status, parent, collapseEnabled=False, headerAdditionEnabled=False)

    def addTask(self, task: Task, board: Board) -> RoadmapTaskWidget:
        wdg = RoadmapTaskWidget(task, board.tags, self)
        self._container.layout().insertWidget(self._container.layout().count() - 1, wdg,
                                              alignment=Qt.AlignmentFlag.AlignTop)

        self._header.updateTitle(self._container.layout().count() - 1)
        return wdg


class RoadmapBoardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self, spacing=20)
        self._statusColumns: Dict[str, RoadmapStatusColumn] = {}
        self._tasks: Dict[Task, RoadmapTaskWidget] = {}
        self._tagFilters: Set[str] = set()

    def setBoard(self, board: Board):
        clear_layout(self)
        self._statusColumns.clear()
        self._tasks.clear()
        self._tagFilters.clear()
        self._version: str = ''
        self._beta: bool = False

        for status in board.statuses:
            column = RoadmapStatusColumn(status)
            self.layout().addWidget(column)
            self._statusColumns[str(status.id)] = column

        for task in board.tasks:
            column = self._statusColumns.get(str(task.status_ref))
            wdg = column.addTask(task, board)
            self._tasks[task] = wdg
            for tag in task.tags:
                if tag not in tags_counter:
                    tags_counter[tag] = 0
                tags_counter[tag] += 1
            if task.beta:
                versions_counter['Beta'] += 1
            if task.version:
                versions_counter[task.version] += 1

        _spacer = spacer()
        _spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.layout().addWidget(_spacer)
        margins(self, left=20)

    def showAll(self):
        self._version = ''
        self._beta = False

        for task, wdg in self._tasks.items():
            wdg.setVisible(self._filter(task))

    def filterVersion(self, version: str):
        self._version = version
        self._beta = False

        for task, wdg in self._tasks.items():
            wdg.setVisible(self._filter(task))

    def filterBeta(self):
        self._version = ''
        self._beta = True

        for task, wdg in self._tasks.items():
            wdg.setVisible(self._filter(task))

    def filterTag(self, tag: str, filtered: bool):
        if filtered:
            self._tagFilters.add(tag)
        else:
            self._tagFilters.remove(tag)

        for task, wdg in self._tasks.items():
            wdg.setVisible(self._filter(task))

    def _filter(self, task: Task) -> bool:
        if self._version and task.version != self._version:
            return False
        if self._beta and not task.beta:
            return False

        return self._filteredByTags(task)

    def _filteredByTags(self, task: Task) -> bool:
        if not self._tagFilters:
            return True

        for tag in task.tags:
            if tag in self._tagFilters:
                return True
        return False


class RoadmapView(QWidget, Ui_RoadmapView):
    DOWNLOAD_THRESHOLD_SECONDS = 60 * 60 * 8  # 8 hours in seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.btnRoadmapIcon.setIcon(IconRegistry.from_name('fa5s.road'))
        self.btnPlus.setIcon(IconRegistry.from_name('mdi.certificate', color_on=PLOTLYST_SECONDARY_COLOR))
        self.btnVisitRoadmap.setIcon(IconRegistry.from_name('fa5s.external-link-alt'))
        self.btnVisitRoadmap.installEventFilter(ButtonPressResizeEventFilter(self.btnVisitRoadmap))
        self.btnVisitRoadmap.clicked.connect(lambda: open_url('https://plotlyst.featurebase.app/roadmap'))
        decr_icon(self.btnVisitRoadmap, 2)
        decr_font(self.btnVisitRoadmap)
        italic(self.btnVisitRoadmap)
        self.btnVisitRoadmap.installEventFilter(OpacityEventFilter(self.btnVisitRoadmap, enterOpacity=0.7))

        self.btnSubmitRequest.setIcon(IconRegistry.from_name('mdi.comment-text', RELAXED_WHITE_COLOR))
        self.btnSubmitRequest.installEventFilter(ButtonPressResizeEventFilter(self.btnSubmitRequest))
        self.btnSubmitRequest.clicked.connect(lambda: open_url('https://plotlyst.featurebase.app/'))

        self.splitter.setSizes([150, 550])

        self._last_fetched = None
        self._downloading = False
        self._board: Optional[Board] = None
        self._thread_pool = QThreadPool()

        self._roadmapWidget = RoadmapBoardWidget()
        self.scrollAreaWidgetContents.layout().addWidget(self._roadmapWidget)

        self._tagsTree = TagsTreeView()
        self.wdgCategoriesParent.layout().addWidget(self._tagsTree)
        self._tagsTree.toggled.connect(self._roadmapWidget.filterTag)

        self.btnAll.clicked.connect(self._roadmapWidget.showAll)
        self.btnFree.clicked.connect(lambda: self._roadmapWidget.filterVersion('Free'))
        self.btnPlus.clicked.connect(lambda: self._roadmapWidget.filterVersion('Plus'))
        self.btnBeta.clicked.connect(self._roadmapWidget.filterBeta)

        self.wdgLoading.setHidden(True)

    @overrides
    def showEvent(self, event: QEvent):
        super().showEvent(event)

        if self._downloading:
            return

        if self._last_fetched is None or (
                datetime.datetime.now() - self._last_fetched).total_seconds() > self.DOWNLOAD_THRESHOLD_SECONDS:
            self._handle_downloading_status(True)
            self._download_data()

    def _download_data(self):
        result = JsonDownloadResult()
        runnable = JsonDownloadWorker("https://raw.githubusercontent.com/plotlyst/feed/refs/heads/main/posts.json",
                                      result)
        result.finished.connect(self._handle_downloaded_data)
        result.failed.connect(self._handle_download_failure)
        self._thread_pool.start(runnable)

    def _handle_downloaded_data(self, data):
        self.btnAll.setChecked(True)
        tags_counter.clear()
        versions_counter.clear()
        versions_counter['Free'] = 0
        versions_counter['Plus'] = 0
        versions_counter['Beta'] = 0

        self._board = Board.from_dict(data)
        self._roadmapWidget.setBoard(self._board)
        self._tagsTree.setTags(self._board.tags)

        self.btnFree.setText(f'Free ({versions_counter.get("Free", 0)})')
        self.btnPlus.setText(f'Plus ({versions_counter.get("Plus", 0)})')
        self.btnBeta.setText(f'Beta ({versions_counter.get("Beta", 0)})')

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.lblLastUpdated.setText(f"Last updated: {now}")
        self._last_fetched = datetime.datetime.now()

        self._handle_downloading_status(False)

    def _handle_download_failure(self, status_code: int, message: str):
        if self._board is None:
            self.lblLastUpdated.setText("Failed to update data.")
        self._handle_downloading_status(False)

    def _handle_downloading_status(self, loading: bool):
        self._downloading = loading
        self.scrollAreaWidgetContents.setDisabled(loading)
        self.splitter.setHidden(loading)
        self.wdgTopSelectors.setHidden(loading)
        self.wdgLoading.setVisible(loading)
        if loading:
            btn = push_btn(transparent_=True)
            btn.setIconSize(QSize(128, 128))
            self.wdgLoading.layout().addWidget(btn,
                                               alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            spin(btn, PLOTLYST_SECONDARY_COLOR)
        else:
            clear_layout(self.wdgLoading)
