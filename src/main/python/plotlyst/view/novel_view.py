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

from PyQt5.QtCore import QObject, QEvent, Qt
from PyQt5.QtGui import QFont
from overrides import overrides
from qthandy import retain_when_hidden, transparent

from src.main.python.plotlyst.core.client import json_client
from src.main.python.plotlyst.core.domain import Novel, Document
from src.main.python.plotlyst.event.core import emit_event
from src.main.python.plotlyst.events import NovelUpdatedEvent, \
    SceneChangedEvent
from src.main.python.plotlyst.resources import resource_registry
from src.main.python.plotlyst.view._view import AbstractNovelView
from src.main.python.plotlyst.view.common import link_buttons_to_pages, OpacityEventFilter
from src.main.python.plotlyst.view.dialog.novel import NovelEditionDialog
from src.main.python.plotlyst.view.generated.novel_view_ui import Ui_NovelView
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.widget.novel import PlotEditor


class NovelView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel, [NovelUpdatedEvent, SceneChangedEvent])
        self.ui = Ui_NovelView()
        self.ui.setupUi(self.widget)

        self.ui.btnStructure.setIcon(IconRegistry.story_structure_icon(color='white'))
        self.ui.btnPlot.setIcon(IconRegistry.plot_icon(color='white'))
        self.ui.btnSynopsis.setIcon(IconRegistry.from_name('fa5s.scroll', 'white'))
        self.ui.btnTags.setIcon(IconRegistry.tags_icon('white'))

        self.ui.btnEditNovel.setIcon(IconRegistry.edit_icon(color_on='darkBlue'))
        self.ui.btnEditNovel.installEventFilter(OpacityEventFilter(parent=self.ui.btnEditNovel))
        self.ui.btnEditNovel.clicked.connect(self._edit_novel)
        retain_when_hidden(self.ui.btnEditNovel)
        self.ui.wdgTitle.installEventFilter(self)
        self.ui.btnEditNovel.setHidden(True)

        transparent(self.ui.textPremise.textEdit)
        self.ui.textPremise.textEdit.setPlaceholderText('Premise')
        self.ui.textPremise.textEdit.setFontFamily('Helvetica')
        self.ui.textPremise.textEdit.setFontPointSize(16)
        self.ui.textPremise.textEdit.setAlignment(Qt.AlignCenter)
        self.ui.textPremise.textEdit.setFontWeight(QFont.Bold)

        self.ui.lblTitle.setText(self.novel.title)
        self.ui.textPremise.textEdit.insertPlainText(self.novel.premise)
        self.ui.textPremise.textEdit.textChanged.connect(self._premise_changed)
        self._premise_changed()
        self.ui.textSynopsis.setGrammarCheckEnabled(True)
        self.ui.textPremise.setGrammarCheckEnabled(True)

        self.ui.textPremise.setToolbarVisible(False)
        self.ui.textPremise.setTitleVisible(False)
        self.ui.textSynopsis.setToolbarVisible(False)
        self.ui.textSynopsis.setTitleVisible(False)
        if self.novel.synopsis:
            json_client.load_document(self.novel, self.novel.synopsis)
            self.ui.textSynopsis.setText(self.novel.synopsis.content)
            self.ui.lblSynopsisWords.setWordCount(self.ui.textSynopsis.textEdit.statistics().word_count)
        self.ui.textSynopsis.textEdit.textChanged.connect(self._synopsis_changed)

        self.ui.wdgStructure.setNovel(self.novel)
        self.ui.wdgTitle.setFixedHeight(150)
        self.ui.wdgTitle.setStyleSheet(
            f'#wdgTitle {{border-image: url({resource_registry.frame1}) 0 0 0 0 stretch stretch;}}')

        self.plot_editor = PlotEditor(self.novel)
        self.ui.wdgPlotContainer.layout().addWidget(self.plot_editor)

        self.ui.wdgTagsContainer.setNovel(self.novel)

        link_buttons_to_pages(self.ui.stackedWidget, [(self.ui.btnStructure, self.ui.pageStructure),
                                                      (self.ui.btnPlot, self.ui.pagePlot),
                                                      (self.ui.btnSynopsis, self.ui.pageSynopsis),
                                                      (self.ui.btnTags, self.ui.pageTags)])
        self.ui.btnStructure.setChecked(True)

        for btn in self.ui.buttonGroup.buttons():
            btn.setStyleSheet('''
            QPushButton {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 #89c2d9);
                border: 2px solid #2c7da0;
                border-radius: 6px;
                color: white;
                padding: 2px;
                font: bold;
            }
            QPushButton:checked {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 #014f86);
                border: 2px solid #013a63;
            }
            ''')
            btn.installEventFilter(OpacityEventFilter(leaveOpacity=0.7, parent=btn, ignoreCheckedButton=True))

    @overrides
    def refresh(self):
        self.ui.lblTitle.setText(self.novel.title)

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Enter:
            self.ui.btnEditNovel.setVisible(True)
        elif event.type() == QEvent.Leave:
            self.ui.btnEditNovel.setHidden(True)

        return super(NovelView, self).eventFilter(watched, event)

    def _edit_novel(self):
        title = NovelEditionDialog().display(self.novel)
        if title:
            self.novel.title = title
            self.repo.update_project_novel(self.novel)
            self.ui.lblTitle.setText(self.novel.title)
            emit_event(NovelUpdatedEvent(self, self.novel))

    def _premise_changed(self):
        text = self.ui.textPremise.textEdit.toPlainText()
        if not text:
            self.ui.textPremise.textEdit.setFontWeight(QFont.Bold)
            self.ui.textPremise.textEdit.setStyleSheet(
                'border: 1px dashed darkBlue; border-radius: 6px; background-color: rgba(0, 0, 0, 0);')
        elif not self.novel.premise:
            transparent(self.ui.textPremise.textEdit)

        self.novel.premise = text
        self.ui.lblLoglineWords.calculateWordCount(self.novel.premise)
        self.repo.update_novel(self.novel)

    def _synopsis_changed(self):
        if self.novel.synopsis is None:
            self.novel.synopsis = Document('Synopsis')
            self.novel.synopsis.loaded = True
            self.repo.update_novel(self.novel)
        self.novel.synopsis.content = self.ui.textSynopsis.textEdit.toHtml()
        self.ui.lblSynopsisWords.setWordCount(self.ui.textSynopsis.textEdit.statistics().word_count)
        self.repo.update_doc(self.novel, self.novel.synopsis)
