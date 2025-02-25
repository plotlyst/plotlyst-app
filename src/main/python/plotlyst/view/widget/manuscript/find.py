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
import re

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QShowEvent, QTextDocument, QTextCursor, QSyntaxHighlighter, QTextCharFormat, QColor, \
    QMouseEvent, QTextBlockUserData, QTextBlockFormat
from PyQt6.QtWidgets import QWidget, QTextBrowser
from overrides import overrides
from qthandy import incr_font, vbox, busy, transparent

from plotlyst.common import PLOTLYST_TERTIARY_COLOR, PLOTLYST_SECONDARY_COLOR
from plotlyst.core.client import json_client
from plotlyst.core.domain import Novel
from plotlyst.view.common import DelayedSignalSlotConnector, label
from plotlyst.view.widget.input import SearchField


class SearchHighlighter(QSyntaxHighlighter):
    def __init__(self, document, parent=None):
        super().__init__(document)
        self.parent = parent
        self.highlighted_block = None
        self.format = QTextCharFormat()
        self.format.setForeground(QColor(PLOTLYST_SECONDARY_COLOR))
        self.format.setFontUnderline(True)
        self.format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.DotLine)
        self.format.setUnderlineColor(QColor(PLOTLYST_SECONDARY_COLOR))

    @overrides
    def highlightBlock(self, text):
        if self.parent.hovered_paragraph is None:
            return

        block = self.parent.hovered_paragraph
        if self.currentBlock() == block:
            self.setFormat(0, len(text), self.format)


class SearchBlockUserData(QTextBlockUserData):
    def __init__(self, result):
        super().__init__()
        self.result = result


class SearchResultsTextEdit(QTextBrowser):
    matchClicked = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        transparent(self)
        self.setMouseTracking(True)
        self.hovered_paragraph = None
        self.hovered_cursor = None

        self.highlighter = SearchHighlighter(self.document(), self)

    @overrides
    def mouseMoveEvent(self, event: QMouseEvent):
        cursor = self.cursorForPosition(event.pos())
        self.hovered_cursor = cursor
        block = cursor.block()

        if block != self.hovered_paragraph and not block.blockFormat().headingLevel():
            self.hovered_paragraph = block
            self.highlighter.rehighlight()

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        cursor = self.cursorForPosition(event.pos())
        block = cursor.block()
        self.matchClicked.emit(block.userData().result)


class ManuscriptFindWidget(QWidget):
    CONTEXT_SIZE: int = 30

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel
        vbox(self)

        self.search = SearchField()
        incr_font(self.search.lineSearch)
        DelayedSignalSlotConnector(self.search.lineSearch.textEdited, self._search, delay=500, parent=self)

        self.lblResults = label('', bold=True)

        self.wdgResults = SearchResultsTextEdit()
        font = self.wdgResults.font()
        font.setPointSize(11)
        self.wdgResults.setFont(font)

        self._headingBlockFormat = QTextBlockFormat()
        self._headingBlockFormat.setHeadingLevel(3)
        self._headingBlockFormat.setTopMargin(10)
        self._headingBlockFormat.setBottomMargin(10)

        self._textBlockFormat = QTextBlockFormat()
        self._textBlockFormat.setTopMargin(3)
        self._textBlockFormat.setBottomMargin(3)
        self._textBlockFormat.setLeftMargin(10)

        self.layout().addWidget(self.search, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.lblResults, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.wdgResults)

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.search.lineSearch.setFocus()

    @busy
    def _search(self, term: str):
        self.wdgResults.clear()
        if not term or term == ' ' or (len(term) == 1 and not re.match(r'[\d\W]', term)):
            self.lblResults.clear()
            return

        json_client.load_manuscript(self.novel)
        results = []

        resultCursor = QTextCursor(self.wdgResults.document())
        for scene in self.novel.scenes:
            if not scene.manuscript:
                continue
            doc = QTextDocument()
            doc.setHtml(scene.manuscript.content)
            raw_text = doc.toPlainText()

            cursor = QTextCursor(doc)
            scene_matches = []
            while not cursor.isNull() and not cursor.atEnd():
                cursor = doc.find(term, cursor)
                if cursor.isNull():
                    break

                start = cursor.selectionStart()
                end = cursor.selectionEnd()

                before_start = raw_text.rfind(" ", 0, start - self.CONTEXT_SIZE) + 1
                after_end = raw_text.find(" ", end + self.CONTEXT_SIZE)
                if after_end == -1:
                    after_end = len(raw_text)

                before = raw_text[before_start:start]
                after = raw_text[end:after_end]
                match_text = raw_text[start:end]

                formatted_match = f'{before}<span style="background-color: {PLOTLYST_TERTIARY_COLOR}; color: black; padding: 2px;">{match_text}</span>{after}'

                result = {
                    "scene": scene,
                    "start": start,
                    "end": end,
                    "context": formatted_match
                }
                scene_matches.append(result)

            if scene_matches:
                results.extend(scene_matches)

                resultCursor.insertBlock(self._headingBlockFormat)
                resultCursor.insertHtml(f'<h3>{scene.title_or_index(self.novel)}</h3>')
                for result in scene_matches:
                    resultCursor.insertBlock(self._textBlockFormat)
                    resultCursor.insertHtml(result['context'])
                    resultCursor.block().setUserData(SearchBlockUserData(result))

        self.lblResults.setText(f'{len(results)} results')
