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

from typing import Optional

from PyQt5.QtCore import QModelIndex, QTextBoundaryFinder, Qt
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QTextBlock, QColor
from PyQt5.QtWidgets import QHeaderView, QTextEdit
from overrides import overrides

from src.main.python.plotlyst.core.client import json_client
from src.main.python.plotlyst.core.domain import Novel, Document
from src.main.python.plotlyst.event.core import emit_event, emit_critical
from src.main.python.plotlyst.events import NovelUpdatedEvent, SceneChangedEvent, OpenDistractionFreeMode
from src.main.python.plotlyst.model.chapters_model import ChaptersTreeModel, SceneNode, ChapterNode
from src.main.python.plotlyst.view._view import AbstractNovelView
from src.main.python.plotlyst.view.common import set_opacity
from src.main.python.plotlyst.view.generated.manuscript_view_ui import Ui_ManuscriptView
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.report.manuscript import SentenceVarietyChartView
from src.main.python.plotlyst.view.widget.input import GrammarHighlighter
from src.main.python.plotlyst.worker.grammar import language_tool_proxy


class ManuscriptView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel, [NovelUpdatedEvent, SceneChangedEvent])
        self.ui = Ui_ManuscriptView()
        self.ui.setupUi(self.widget)
        self._current_doc: Optional[Document] = None
        self.highlighter = GrammarHighlighter(self.ui.textEdit.textEditor.document(), checkEnabled=False)
        self.ui.splitter.setSizes([100, 500])
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageEmpty)

        self.ui.textEdit.setTitleVisible(False)
        self.ui.textEdit.setToolbarVisible(False)
        self.ui.wdgSentences.setHidden(True)

        self.ui.btnDistractionFree.setIcon(IconRegistry.from_name('fa5s.expand-alt'))
        self.ui.btnSpellCheckIcon.setIcon(IconRegistry.from_name('fa5s.spell-check'))
        self.ui.btnAnalysis.setIcon(IconRegistry.from_name('mdi.google-analytics', color_on='darkBlue'))
        self.ui.cbSpellCheck.toggled.connect(self._spellcheck_toggled)
        self.ui.cbSpellCheck.clicked.connect(self._spellcheck_clicked)
        self._spellcheck_toggled(self.ui.btnSpellCheckIcon.isChecked())

        self.chartSentences = SentenceVarietyChartView()
        self.ui.wdgSentences.layout().addWidget(self.chartSentences)

        self.chaptersModel = ChaptersTreeModel(self.novel)
        self.ui.treeChapters.setModel(self.chaptersModel)
        self.ui.treeChapters.expandAll()
        self.chaptersModel.modelReset.connect(self.ui.treeChapters.expandAll)
        self.ui.treeChapters.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.ui.treeChapters.setColumnWidth(ChaptersTreeModel.ColPlus, 24)
        self.ui.treeChapters.clicked.connect(self._edit)

        self.ui.textEdit.setPasteAsPlainText(True)
        self.ui.textEdit.textEditor.textChanged.connect(self._save)
        self.ui.btnDistractionFree.clicked.connect(
            lambda: emit_event(OpenDistractionFreeMode(self, self.ui.textEdit, self.ui.wdgSprint.model())))

    @overrides
    def refresh(self):
        self.chaptersModel.modelReset.emit()

    def restore_editor(self, editor: QTextEdit):
        self.ui.pageText.layout().insertWidget(2, editor)

    def _edit(self, index: QModelIndex):
        def set_statistics():
            self.ui.lblWordCount.setText(f'<html><b>{self.ui.textEdit.statistics().word_count}</b> words')
            self.chartSentences.setText(self.ui.textEdit.textEditor.toPlainText())

        node = index.data(ChaptersTreeModel.NodeRole)
        if isinstance(node, SceneNode):
            if not node.scene.manuscript:
                node.scene.manuscript = Document('', scene_id=node.scene.id)
                self.repo.update_scene(node.scene)
            self._current_doc = node.scene.manuscript

            if not self._current_doc.loaded:
                json_client.load_document(self.novel, self._current_doc)

            self.ui.stackedWidget.setCurrentWidget(self.ui.pageText)
            self.highlighter.setCheckEnabled(False)
            self.ui.textEdit.setText(self._current_doc.content, self._current_doc.title)
            self.chartSentences.setText(self.ui.textEdit.textEditor.toPlainText())

            self.ui.textEdit.setMargins(30, 30, 30, 30)
            self.ui.textEdit.setFormat(130)
            self.ui.textEdit.setFontPointSize(16)
            set_statistics()
            self.ui.textEdit.textEditor.textChanged.connect(set_statistics)

            if self.ui.cbSpellCheck.isChecked():
                self.highlighter.setCheckEnabled(True)
                self.highlighter.asyncRehighlight()

        elif isinstance(node, ChapterNode):
            self.ui.stackedWidget.setCurrentWidget(self.ui.pageEmpty)

    def _save(self):
        if not self._current_doc:
            return
        self._current_doc.content = self.ui.textEdit.textEditor.toHtml()
        json_client.save_document(self.novel, self._current_doc)

    def _spellcheck_toggled(self, toggled: bool):
        set_opacity(self.ui.btnSpellCheckIcon, 1 if toggled else 0.4)

    def _spellcheck_clicked(self, checked: bool):
        if checked:
            if language_tool_proxy.is_failed():
                self.ui.cbSpellCheck.setChecked(False)
                emit_critical(language_tool_proxy.error)
            else:
                self.highlighter.setCheckEnabled(True)
                self.highlighter.asyncRehighlight()
        elif self.highlighter:
            self.highlighter.setCheckEnabled(False)
            self.highlighter.rehighlight()


class SentenceHighlighter(QSyntaxHighlighter):

    def __init__(self, textedit: QTextEdit):
        super(SentenceHighlighter, self).__init__(textedit.document())
        self._editor = textedit

        self._hidden_format = QTextCharFormat()
        self._hidden_format.setForeground(QColor('#dee2e6'))

        self._visible_format = QTextCharFormat()
        self._visible_format.setForeground(Qt.black)

        self._prevBlock: Optional[QTextBlock] = None
        self._editor.cursorPositionChanged.connect(self.rehighlight)

    @overrides
    def highlightBlock(self, text: str) -> None:
        self.setFormat(0, len(text), self._hidden_format)
        if self._editor.textCursor().block() == self.currentBlock():
            text = self._editor.textCursor().block().text()
            finder = QTextBoundaryFinder(QTextBoundaryFinder.Sentence, text)
            pos = self._editor.textCursor().positionInBlock()
            boundary = finder.toNextBoundary()
            prev_boundary = 0
            while -1 < boundary < pos:
                prev_boundary = boundary
                boundary = finder.toNextBoundary()

            self.setFormat(prev_boundary, boundary - prev_boundary, self._visible_format)
