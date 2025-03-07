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

from PyQt6.QtCore import QEvent, QThreadPool, QSize, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QPushButton
from overrides import overrides
from qthandy import clear_layout, vbox, incr_font, decr_icon, decr_font, vspacer, italic, bold, margins, incr_icon, \
    line, spacer, translucent
from qthandy.filter import OpacityEventFilter

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, RELAXED_WHITE_COLOR
from plotlyst.core.domain import Board, Task, TaskStatus
from plotlyst.env import app_env
from plotlyst.service.resource import JsonDownloadWorker, JsonDownloadResult
from plotlyst.view.common import push_btn, spin, tool_btn, open_url, ButtonPressResizeEventFilter, \
    ExclusiveOptionalButtonGroup, label
from plotlyst.view.generated.roadmap_view_ui import Ui_RoadmapView
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.display import IconText, Icon

tags_counter: Dict[str, int] = {}
versions_counter: Dict[str, int] = {}


class TaskWidget(QWidget):
    def __init__(self, task: Task, status: TaskStatus, parent=None, appendLine: bool = True):
        super().__init__(parent)
        self.task = task
        self.status = status
        vbox(self, 5, spacing=3)

        self.lblStatus = label(self.status.text)
        font = self.lblStatus.font()
        font.setCapitalization(QFont.Capitalization.SmallCaps)
        font.setFamily(app_env.serif_font())
        self.lblStatus.setFont(font)
        self.lblStatus.setStyleSheet(f'''
            color: {self.status.color_hexa};
        ''')

        self.iconPlus = Icon()
        self.iconPlus.setToolTip('Plotlyst Plus feature')
        self.iconPlus.setIcon(IconRegistry.from_name('mdi.certificate', PLOTLYST_SECONDARY_COLOR))
        translucent(self.iconPlus, 0.5)
        self.iconPlus.setVisible(self.task.version == 'Plus')

        self.lblName = IconText()
        incr_font(self.lblName, 4)
        self.lblName.setText(self.task.title)
        if self.task.icon:
            self.lblName.setIcon(IconRegistry.from_name(self.task.icon))
        self.lblDescription = label(self.task.summary, description=True, wordWrap=True)
        self.lblDescription.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        incr_font(self.lblDescription)

        self._btnOpenInExternal = tool_btn(IconRegistry.from_name('fa5s.external-link-alt', 'grey'), transparent_=True,
                                           tooltip='Open in browser')
        decr_icon(self._btnOpenInExternal, 4)
        self._btnOpenInExternal.clicked.connect(lambda: open_url(self.task.web_link))

        self.layout().addWidget(self.lblStatus, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(group(self.lblName, self._btnOpenInExternal, spacer(), self.iconPlus))
        self.layout().addWidget(self.lblDescription)
        if appendLine:
            self.layout().addWidget(line())


def tag_filter_btn(tag: str, icon: str, color: str = 'black') -> QPushButton:
    tagBtn = push_btn(IconRegistry.from_name(icon, color),
                      f'{tag.capitalize()} ({tags_counter.get(tag, 0)})', transparent_=True, checkable=True)
    incr_font(tagBtn)
    incr_icon(tagBtn, 2)
    tagBtn.toggled.connect(partial(bold, tagBtn))
    tagBtn.installEventFilter(OpacityEventFilter(tagBtn, leaveOpacity=0.8, ignoreCheckedButton=True))
    return tagBtn


class RoadmapBoardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self, spacing=10)
        self._tasks: Dict[Task, TaskWidget] = {}
        self._tagFilters: Set[str] = set()
        self._version: str = ''
        self._status: str = ''

    def setBoard(self, board: Board):
        clear_layout(self)
        self._tasks.clear()
        self._tagFilters.clear()
        self._version = ''
        self._status = ''

        btnSubmitRequest = push_btn(IconRegistry.from_name('mdi.comment-text', RELAXED_WHITE_COLOR),
                                    text='Request a new feature',
                                    properties=['positive', 'confirm'])
        btnSubmitRequest.clicked.connect(lambda: open_url('https://plotlyst.featurebase.app/'))
        self.layout().addWidget(btnSubmitRequest, alignment=Qt.AlignmentFlag.AlignRight)

        statuses = {}
        for status in board.statuses:
            statuses[str(status.id)] = status

        tags_counter['Planned'] = 0
        tags_counter['Completed'] = 0

        for i, task in enumerate(board.tasks):
            status = statuses[str(task.status_ref)]
            wdg = TaskWidget(task, status, appendLine=i < len(board.tasks) - 1)
            self._tasks[task] = wdg
            self.layout().addWidget(wdg)

            tags_counter[status.text] += 1

            for tag in task.tags:
                if tag not in tags_counter:
                    tags_counter[tag] = 0
                tags_counter[tag] += 1

            if task.version:
                versions_counter[task.version] += 1

        self.layout().addWidget(vspacer())

    def showAll(self):
        self._version = ''

        for task, wdg in self._tasks.items():
            wdg.setVisible(self._filter(task))

    def filterVersion(self, version: str):
        self._version = version

        for task, wdg in self._tasks.items():
            wdg.setVisible(self._filter(task))

    def filterStatus(self, status: str, toggled: bool):
        self._status = status if toggled else ''

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
        if self._status and self._tasks[task].status.text != self._status:
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

        self.btnPlus.setIcon(IconRegistry.from_name('mdi.certificate', color_on=PLOTLYST_SECONDARY_COLOR))
        self.btnVisitRoadmap.setIcon(IconRegistry.from_name('fa5s.external-link-alt'))
        self.btnVisitRoadmap.installEventFilter(ButtonPressResizeEventFilter(self.btnVisitRoadmap))
        self.btnVisitRoadmap.clicked.connect(lambda: open_url('https://plotlyst.featurebase.app/roadmap'))
        decr_icon(self.btnVisitRoadmap, 2)
        decr_font(self.btnVisitRoadmap)
        decr_font(self.lblLastUpdated)
        italic(self.btnVisitRoadmap)
        self.btnVisitRoadmap.installEventFilter(OpacityEventFilter(self.btnVisitRoadmap, enterOpacity=0.7))
        self.lblDesc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        incr_font(self.lblDesc)

        self.splitter.setSizes([150, 550])

        self._last_fetched = None
        self._downloading = False
        self._board: Optional[Board] = None
        self._thread_pool = QThreadPool()

        self._roadmapWidget = RoadmapBoardWidget()
        self.scrollAreaWidgetContents.layout().addWidget(self._roadmapWidget)

        incr_font(self.btnAll)
        incr_font(self.btnFree)
        incr_font(self.btnPlus)

        self.btnAll.clicked.connect(self._roadmapWidget.showAll)
        self.btnFree.clicked.connect(lambda: self._roadmapWidget.filterVersion('Free'))
        self.btnPlus.clicked.connect(lambda: self._roadmapWidget.filterVersion('Plus'))

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
        runnable = JsonDownloadWorker("https://raw.githubusercontent.com/plotlyst/feed/refs/heads/main/plus.json",
                                      result)
        result.finished.connect(self._handle_downloaded_data)
        result.failed.connect(self._handle_download_failure)
        self._thread_pool.start(runnable)

    def _handle_downloaded_data(self, data):
        self.btnAll.setChecked(True)
        tags_counter.clear()
        versions_counter.clear()
        clear_layout(self.wdgCategoriesParent)
        versions_counter['Free'] = 0
        versions_counter['Plus'] = 0
        versions_counter['Beta'] = 0

        self._board: Board = Board.from_dict(data)
        self._roadmapWidget.setBoard(self._board)

        btnGroup = ExclusiveOptionalButtonGroup(self)
        tagCompleted = tag_filter_btn('Completed', 'fa5s.check', '#40916c')
        tagPlanned = tag_filter_btn('Planned', 'fa5.calendar-alt', '#0077b6')
        tagCompleted.clicked.connect(partial(self._roadmapWidget.filterStatus, 'Completed'))
        tagPlanned.clicked.connect(partial(self._roadmapWidget.filterStatus, 'Planned'))
        btnGroup.addButton(tagCompleted)
        btnGroup.addButton(tagPlanned)
        self.wdgCategoriesParent.layout().addWidget(label('State', description=True))
        wdgStates = QWidget()
        vbox(wdgStates)
        margins(wdgStates, left=10, bottom=30)
        wdgStates.layout().addWidget(tagCompleted, alignment=Qt.AlignmentFlag.AlignLeft)
        wdgStates.layout().addWidget(tagPlanned, alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgCategoriesParent.layout().addWidget(wdgStates)

        self.wdgCategoriesParent.layout().addWidget(label('Type', description=True))
        wdgTypes = QWidget()
        vbox(wdgTypes)
        margins(wdgTypes, left=10)
        self.wdgCategoriesParent.layout().addWidget(wdgTypes)

        btnGroup = ExclusiveOptionalButtonGroup(self)
        for tag, item in self._board.tags.items():
            tagBtn = tag_filter_btn(tag, item.icon)
            btnGroup.addButton(tagBtn)
            tagBtn.toggled.connect(partial(self._roadmapWidget.filterTag, tag))
            wdgTypes.layout().addWidget(tagBtn, alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgCategoriesParent.layout().addWidget(vspacer())

        self.btnFree.setText(f'Free ({versions_counter.get("Free", 0)})')
        self.btnPlus.setText(f'Plus ({versions_counter.get("Plus", 0)})')

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
