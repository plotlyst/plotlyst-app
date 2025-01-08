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
from typing import List

from PyQt6.QtCore import Qt, QTimer, QSize, QThreadPool
from PyQt6.QtWidgets import QSplitter, QWidget, QDialog
from overrides import overrides
from qthandy import sp, vbox, line, vspacer, hbox, clear_layout, transparent, margins

from plotlyst.common import RELAXED_WHITE_COLOR, PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import NovelDescriptor, StoryType, Novel, Location
from plotlyst.service.importer import NovelLoaderWorker, NovelLoadingResult
from plotlyst.view.common import push_btn, label, spin
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.display import PopupDialog
from plotlyst.view.widget.library import ShelvesTreeView
from plotlyst.view.widget.world.milieu import LocationsTreeView


class SeriesImportBase(PopupDialog):
    def __init__(self, series: NovelDescriptor, novels: List[NovelDescriptor], parent=None):
        super().__init__(parent)
        self._loadingResult = NovelLoadingResult()
        self._loadingResult.finished.connect(self._novelLoadingFinished)

        self.lblTitle = label('Import', h4=True)

        self.wdgSplitter = QSplitter()
        sp(self.wdgSplitter).v_exp()
        self.wdgSplitter.setChildrenCollapsible(False)
        self.wdgSplitter.setSizes([150, 450])

        self.wdgCenter = QWidget()
        vbox(self.wdgCenter)
        self.wdgLoading = QWidget()
        hbox(self.wdgLoading)
        self.wdgCenter.layout().addWidget(self.wdgLoading)
        sp(self.wdgLoading).v_exp().h_exp()
        self.wdgCenter.setMinimumSize(350, 400)

        self.treeView = ShelvesTreeView(readOnly=True)
        self.treeView.setMinimumWidth(250)
        self.treeView.novelSelected.connect(self._novelSelected)
        self.wdgSplitter.addWidget(self.treeView)
        self.wdgSplitter.addWidget(self.wdgCenter)

        items = [series]
        items.extend(novels)
        self.treeView.setNovels(items)

        self.btnConfirm = push_btn(icon=IconRegistry.from_name('mdi.application-import', RELAXED_WHITE_COLOR),
                                   text='Import',
                                   properties=['confirm', 'positive'])
        sp(self.btnConfirm).h_exp()
        self.btnConfirm.setEnabled(False)
        self.btnConfirm.clicked.connect(self.accept)
        self.btnCancel = push_btn(text='Cancel', properties=['confirm', 'cancel'])
        self.btnCancel.clicked.connect(self.reject)

        self.frame.layout().addWidget(self.lblTitle, alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame.layout().addWidget(line(color='lightgrey'))
        self.frame.layout().addWidget(self.wdgSplitter)
        self.wdgCenter.layout().addWidget(group(self.btnCancel, self.btnConfirm, margin_top=20),
                                          alignment=Qt.AlignmentFlag.AlignRight)

    def _novelSelected(self, novel: NovelDescriptor):
        if novel.story_type != StoryType.Novel:
            return

        self.wdgLoading.setVisible(True)
        btn = push_btn(transparent_=True)
        btn.setIconSize(QSize(128, 128))
        self.wdgLoading.layout().addWidget(btn,
                                           alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        spin(btn, PLOTLYST_SECONDARY_COLOR)
        QTimer.singleShot(25, lambda: self._fetchNovel(novel))

    def _fetchNovel(self, novel: NovelDescriptor):
        runnable = NovelLoaderWorker(novel.id, self._loadingResult)
        QThreadPool.globalInstance().start(runnable)

    def _novelLoadingFinished(self, novel: Novel):
        self.wdgLoading.setVisible(False)
        clear_layout(self.wdgLoading)
        self.btnConfirm.setEnabled(True)

        self._novelFetched(novel)

    def _novelFetched(self, novel: Novel):
        pass


class ImportCharacterPopup(SeriesImportBase):
    def __init__(self, series: NovelDescriptor, novels: List[NovelDescriptor], parent=None):
        super().__init__(series, novels, parent)
        self.lblTitle.setText('Import characters from series')
        self.btnConfirm.setText('Import characters')
        self.wdgCenter.layout().insertWidget(0, vspacer())

    def display(self):
        result = self.exec()

    @overrides
    def _novelFetched(self, novel: Novel):
        for character in novel.characters:
            self.wdgCenter.layout().addWidget(label(character.name))


class ImportLocationPopup(SeriesImportBase):
    def __init__(self, series: NovelDescriptor, novels: List[NovelDescriptor], parent=None):
        super().__init__(series, novels, parent)
        self.lblTitle.setText('Import locations from series')
        self.btnConfirm.setText('Import locations')

        self.locationsTree = LocationsTreeView()
        margins(self.locationsTree.centralWidget(), left=20, top=20)
        transparent(self.locationsTree)
        transparent(self.locationsTree.centralWidget())

        self.wdgCenter.layout().insertWidget(0, self.locationsTree)

    def display(self) -> List[Location]:
        result = self.exec()

        if result == QDialog.DialogCode.Accepted:
            return self.locationsTree.checkedLocations()

    @overrides
    def _novelFetched(self, novel: Novel):
        self.locationsTree.setNovel(novel, readOnly=True, checkable=True)
