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
from typing import List, Dict

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QShowEvent, QTextDocument, QTextCursor, QSyntaxHighlighter, QTextCharFormat, QColor, \
    QMouseEvent, QTextBlockUserData, QTextBlockFormat
from PyQt6.QtWidgets import QWidget, QTextBrowser
from overrides import overrides
from qthandy import vbox, busy, transparent, decr_icon, decr_font, margins

from plotlyst.common import PLOTLYST_TERTIARY_COLOR, PLOTLYST_SECONDARY_COLOR, RELAXED_WHITE_COLOR
from plotlyst.core.client import json_client
from plotlyst.core.domain import Novel, Scene
from plotlyst.core.text import wc
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import DelayedSignalSlotConnector, push_btn, label
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.button import SelectorToggleButton
from plotlyst.view.widget.confirm import asked
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


class SearchSceneHeaderUserData(QTextBlockUserData):
    def __init__(self, scene: Scene):
        super().__init__()
        self.scene = scene


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
        if isinstance(block.userData(), SearchBlockUserData):
            self.matchClicked.emit(block.userData().result)


class ManuscriptFindWidget(QWidget):
    CONTEXT_SIZE: int = 30
    matched = pyqtSignal()
    reset = pyqtSignal()
    replaced = pyqtSignal()

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel
        vbox(self, 1, spacing=2)
        margins(self, top=0)
        self._term: str = ''
        self._results: Dict[Scene, list] = {}

        self.search = SearchField(ignoreCapitalization=True)
        decr_icon(self.search.lineSearch)
        DelayedSignalSlotConnector(self.search.lineSearch.textEdited, self._search, delay=500, parent=self)

        self.btnCase = SelectorToggleButton(Qt.ToolButtonStyle.ToolButtonIconOnly, minWidth=40, animated=False)
        self.btnCase.setIcon(IconRegistry.from_name('msc.case-sensitive', 'grey', 'black'))
        self.btnCase.setToolTip('Toggle case sensitivity')
        decr_icon(self.btnCase, 4)
        self.btnCase.clicked.connect(self._settingChanged)

        self.btnWord = SelectorToggleButton(Qt.ToolButtonStyle.ToolButtonIconOnly, minWidth=40, animated=False)
        self.btnWord.setIcon(IconRegistry.from_name('msc.whole-word', 'grey', 'black'))
        self.btnWord.setToolTip('Match whole word only')
        decr_icon(self.btnWord, 4)
        self.btnWord.clicked.connect(self._settingChanged)

        self.replace = SearchField(ignoreCapitalization=True)
        decr_font(self.replace.lineSearch)
        self.replace.lineSearch.setPlaceholderText('Replace with...')
        self.replace.btnIcon.setIcon(IconRegistry.from_name('mdi.find-replace'))

        self.btnReplace = push_btn(IconRegistry.from_name('mdi.find-replace', RELAXED_WHITE_COLOR), 'Replace all',
                                   properties=['base', 'positive'])
        self.btnReplace.setDisabled(True)
        self.btnReplace.clicked.connect(self._replace)

        if self.novel.is_readonly():
            self.replace.setHidden(True)
            self.btnReplace.setHidden(True)

        self.lblResults = label('', bold=True)

        self.wdgResults = SearchResultsTextEdit()
        font = self.wdgResults.font()
        font.setPointSize(11)
        self.wdgResults.setFont(font)

        self._headingBlockFormat = QTextBlockFormat()
        self._headingBlockFormat.setHeadingLevel(4)
        self._headingBlockFormat.setTopMargin(5)
        self._headingBlockFormat.setBottomMargin(5)

        self._textBlockFormat = QTextBlockFormat()
        self._textBlockFormat.setTopMargin(2)
        self._textBlockFormat.setBottomMargin(2)
        self._textBlockFormat.setLeftMargin(10)

        self.layout().addWidget(self.search, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(group(self.btnCase, self.btnWord, margin_left=20), alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.replace, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.btnReplace, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.lblResults, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.wdgResults)

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.search.lineSearch.setFocus()

    def isActive(self) -> bool:
        return len(self._results) > 0

    def deactivate(self):
        self.search.lineSearch.clear()
        self.replace.lineSearch.clear()
        self._term = ''
        self.btnReplace.setDisabled(True)
        self.lblResults.clear()
        self.wdgResults.clear()
        self._results.clear()

    def sceneMathes(self, scene: Scene) -> List[dict]:
        return self._results.get(scene, [])

    @busy
    def updateScene(self, scene: Scene) -> List:
        scene_matches = self._searchForScene(scene)
        self._results[scene] = scene_matches

        doc = self.wdgResults.document()
        block = doc.begin()

        scene_heading_block = None
        while block.isValid():
            block_data = block.userData()
            next_block = block.next()

            if isinstance(block_data, SearchSceneHeaderUserData):
                print(f'header {block_data.scene.title}')
                if block_data.scene == scene:
                    scene_heading_block = block
                elif scene_heading_block:  # already found
                    print('break early')
                    break

            if isinstance(block_data, SearchBlockUserData) and block_data.result['scene'] == scene:
                cursor = QTextCursor(block)
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                cursor.beginEditBlock()
                cursor.removeSelectedText()
                if block.isValid():
                    cursor.deleteChar()
                cursor.endEditBlock()

            block = next_block

        if scene_heading_block:
            resultCursor = QTextCursor(scene_heading_block)
            resultCursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            for result in scene_matches:
                resultCursor.insertBlock(self._textBlockFormat)
                resultCursor.insertHtml(result['context'])
                resultCursor.block().setUserData(SearchBlockUserData(result))

        self._updateResultsLabel()
        return scene_matches

    def _settingChanged(self):
        self._search(self._term)

    @busy
    def _search(self, term: str):
        self._term = term
        self.wdgResults.clear()
        self._results.clear()
        if not term or term == ' ' or (len(term) == 1 and not re.match(r'[\d\W]', term)):
            self.lblResults.clear()
            self.btnReplace.setDisabled(True)
            self.reset.emit()
            return

        json_client.load_manuscript(self.novel)

        count = 0
        resultCursor = QTextCursor(self.wdgResults.document())
        for scene in self.novel.scenes:
            scene_matches = self._searchForScene(scene)
            if scene_matches:
                count += len(scene_matches)
                self._results[scene] = scene_matches

                resultCursor.insertBlock(self._headingBlockFormat)
                resultCursor.insertHtml(f'<h4>{scene.title_or_index(self.novel)}</h4>')
                resultCursor.block().setUserData(SearchSceneHeaderUserData(scene))
                for result in scene_matches:
                    resultCursor.insertBlock(self._textBlockFormat)
                    resultCursor.insertHtml(result['context'])
                    resultCursor.block().setUserData(SearchBlockUserData(result))

        self.lblResults.setText(f'{count} results')
        self.btnReplace.setEnabled(count > 0)
        self.matched.emit()

    def _searchForScene(self, scene: Scene) -> List:
        self._results.pop(scene, None)
        if not scene.manuscript:
            return []
        doc = QTextDocument()
        doc.setHtml(scene.manuscript.content)
        raw_text = doc.toPlainText()

        flags = None
        if self.btnCase.isChecked():
            flags = QTextDocument.FindFlag.FindCaseSensitively
        if self.btnWord.isChecked():
            flags = flags | QTextDocument.FindFlag.FindWholeWords if flags else QTextDocument.FindFlag.FindWholeWords

        cursor = QTextCursor(doc)
        scene_matches = []
        while not cursor.isNull() and not cursor.atEnd():
            if flags:
                cursor = doc.find(self._term, cursor, options=flags)
            else:
                cursor = doc.find(self._term, cursor)
            if cursor.isNull():
                break

            start = cursor.selectionStart()
            end = cursor.selectionEnd()

            before_start = raw_text.rfind(" ", 0, start - self.CONTEXT_SIZE)
            before_start = 0 if before_start == -1 else before_start + 1
            after_end = raw_text.find(" ", end + self.CONTEXT_SIZE)
            after_end = len(raw_text) if after_end == -1 else after_end

            before = raw_text[before_start:start]
            after = raw_text[end:after_end]
            match_text = raw_text[start:end]

            formatted_match = f'{before}<span style="background-color: {PLOTLYST_TERTIARY_COLOR}; color: black; padding: 2px;">{match_text}</span>{after}'

            result = {
                "scene": scene,
                "start": start,
                "end": end,
                "block": cursor.blockNumber(),
                "pos_in_block": (cursor.positionInBlock() - len(match_text), cursor.positionInBlock()),
                "context": formatted_match
            }
            scene_matches.append(result)

        return scene_matches

    def _updateResultsLabel(self):
        count = 0
        for result in self._results.values():
            count += len(result)
        self.lblResults.setText(f'{count} results')

    def _replace(self):
        count = 0
        for result in self._results.values():
            count += len(result)
        if asked(
                f"Are you sure you want to replace all {count} occurrences with '<b>{self.replace.lineSearch.text()}</b>'?",
                'Replace all'):
            self._replaceResults(self._results)

    @busy
    def _replaceResults(self, results: Dict[Scene, list]):
        if not results:
            return
        replace_text = self.replace.lineSearch.text()

        repo = RepositoryPersistenceManager.instance()

        for scene, matches in results.items():
            if not matches:
                continue

            doc = QTextDocument()
            doc.setHtml(scene.manuscript.content)
            cursor = QTextCursor(doc)

            for result in sorted(matches, key=lambda res: res["start"], reverse=True):
                start, end = result["start"], result["end"]

                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
                cursor.insertText(replace_text)

            scene.manuscript.content = doc.toHtml()
            scene.manuscript.statistics.wc = wc(doc.toPlainText())
            repo.update_doc(self.novel, scene.manuscript)

        self.replaced.emit()
        self._search(self._term)
