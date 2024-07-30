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
import math
from dataclasses import dataclass
from enum import Enum
from functools import partial
from typing import Optional, List

import qtanim
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, QObject, QEvent, QTimer, QPoint, QSize, pyqtSignal, QModelIndex, QItemSelectionModel
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QKeyEvent, QPaintEvent, QPainter, QBrush, QLinearGradient, \
    QColor, QSyntaxHighlighter, \
    QTextDocument, QTextBlockUserData, QIcon, QResizeEvent, QFocusEvent
from PyQt6.QtWidgets import QTextEdit, QFrame, QPushButton, QStylePainter, QStyleOptionButton, QStyle, QMenu, \
    QApplication, QToolButton, QLineEdit, QWidgetAction, QListView, QSpinBox, QWidget, QLabel, QDialog
from language_tool_python import LanguageTool
from overrides import overrides
from qthandy import transparent, hbox, margins, pointy, sp, line, flow, vbox, translucent, decr_icon, bold, incr_font, \
    decr_font, clear_layout
from qthandy.filter import DisabledClickEventFilter, OpacityEventFilter
from qtmenu import MenuWidget
from qttextedit import EnhancedTextEdit, RichTextEditor, DashInsertionMode, remove_font
from qttextedit.api import AutoCapitalizationMode

from plotlyst.common import IGNORE_CAPITALIZATION_PROPERTY, RELAXED_WHITE_COLOR, PLOTLYST_SECONDARY_COLOR, RED_COLOR
from plotlyst.core.domain import TextStatistics, Character, Label
from plotlyst.core.text import wc
from plotlyst.env import app_env
from plotlyst.event.core import EventListener, Event
from plotlyst.event.handler import global_event_dispatcher
from plotlyst.events import LanguageToolSet
from plotlyst.model.characters_model import CharactersTableModel
from plotlyst.model.common import proxy
from plotlyst.service.grammar import language_tool_proxy, dictionary
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import action, label, push_btn, tool_btn, insert_before, fade_out_and_gc
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import apply_color
from plotlyst.view.style.text import apply_texteditor_toolbar_style
from plotlyst.view.widget._toggle import AnimatedToggle
from plotlyst.view.widget.button import DotsMenuButton
from plotlyst.view.widget.display import PopupDialog
from plotlyst.view.widget.utility import IconSelectorDialog


class AutoAdjustableTextEdit(EnhancedTextEdit):
    resizedOnShow = pyqtSignal()

    def __init__(self, parent=None, height: int = 25):
        super(AutoAdjustableTextEdit, self).__init__(parent)
        self.textChanged.connect(self._resizeToContent)
        self._minHeight = height
        self._resizedOnShow: bool = False
        self.setAcceptRichText(False)
        self.setFixedHeight(self._minHeight)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTabChangesFocus(True)

        self.setDocumentMargin(0)
        self.setSidebarEnabled(False)
        self.setCommandsEnabled(False)

    @overrides
    def setText(self, text: str) -> None:
        self.setPlainText(text)

    @overrides
    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        if not self._resizedOnShow:
            self._resizeToContent()
            self._resizedOnShow = True
            self.resizedOnShow.emit()

    @overrides
    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if self._resizedOnShow:
            self._resizeToContent()

    def _resizeToContent(self):
        padding = self.contentsMargins().top() + self.contentsMargins().bottom() + 2 * self.document().documentMargin()
        size = self.document().size()
        self.setFixedHeight(max(self._minHeight, math.ceil(size.height() + padding)))


class AutoAdjustableLineEdit(QLineEdit):
    def __init__(self, parent=None, defaultWidth: int = 200):
        super(AutoAdjustableLineEdit, self).__init__(parent)
        self._padding = 10
        self._defaultWidth = defaultWidth + self._padding
        self._resizedOnShow: bool = False
        self.setFixedWidth(self._defaultWidth)
        self.textChanged.connect(self._resizeToContent)

    @overrides
    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        if not self._resizedOnShow:
            self._resizeToContent()
            self._resizedOnShow = True

    def _resizeToContent(self):
        text = self.text().strip()
        if not text:
            text = self.placeholderText().strip()
        if text:
            text_width = self.fontMetrics().boundingRect(text).width()
            width = max(text_width + self._padding, self._defaultWidth)
            self.setFixedWidth(width)
        else:
            self.setFixedWidth(self._defaultWidth)


class TextBlockData(QTextBlockUserData):
    def __init__(self):
        super(TextBlockData, self).__init__()
        self._misspellings = []
        self._wordCount: int = -1

    @property
    def misspellings(self):
        return self._misspellings

    @misspellings.setter
    def misspellings(self, value):
        self._misspellings.clear()
        self._misspellings.extend(value)

    @property
    def wordCount(self):
        return self._wordCount

    @wordCount.setter
    def wordCount(self, value):
        self._wordCount = value


class AbstractTextBlockHighlighter(QSyntaxHighlighter):
    def _currentblockData(self) -> TextBlockData:
        data = self.currentBlockUserData()
        if data is None or not isinstance(data, TextBlockData):
            data = TextBlockData()
            self.setCurrentBlockUserData(data)

        return data


class GrammarHighlightStyle(Enum):
    UNDERLINE = 1
    BACKGOUND = 2


# partially based on https://gist.github.com/ssokolow/0e69b9bd9ca442163164c8a9756aa15f
class GrammarHighlighter(AbstractTextBlockHighlighter, EventListener):

    def __init__(self, document: QTextDocument, checkEnabled: bool = True,
                 highlightStyle: GrammarHighlightStyle = GrammarHighlightStyle.UNDERLINE):
        super(GrammarHighlighter, self).__init__(document)
        self._checkEnabled: bool = checkEnabled

        self._misspelling_format = QTextCharFormat()
        self._misspelling_format.setUnderlineColor(QColor('#d90429'))
        if highlightStyle == GrammarHighlightStyle.BACKGOUND:
            self._misspelling_format.setBackground(QBrush(QColor('#fbe0dd')))
        self._misspelling_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)

        self._style_format = QTextCharFormat()
        self._style_format.setUnderlineColor(QColor('#5a189a'))
        if highlightStyle == GrammarHighlightStyle.BACKGOUND:
            self._style_format.setBackground(QBrush(QColor('#dec9e9')))
        self._style_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)

        self._grammar_format = QTextCharFormat()
        self._grammar_format.setUnderlineColor(QColor('#ffc300'))
        if highlightStyle == GrammarHighlightStyle.BACKGOUND:
            self._grammar_format.setBackground(QBrush(QColor('#fffae6')))
        self._grammar_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)

        self._formats_per_issue = {'misspelling': self._misspelling_format, 'style': self._style_format}

        self._language_tool: Optional[LanguageTool] = None
        if language_tool_proxy.is_set():
            self._language_tool = language_tool_proxy.tool

        self._currentAsyncBlock: int = 0
        self._asyncTimer = QTimer()
        self._asyncTimer.setInterval(20)
        self._asyncTimer.timeout.connect(self._highlightNextBlock)

        global_event_dispatcher.register(self, LanguageToolSet)

    def checkEnabled(self) -> bool:
        return self._checkEnabled

    def setCheckEnabled(self, enabled: bool):
        self._checkEnabled = enabled
        if not enabled:
            self._asyncTimer.stop()

    @overrides
    def setDocument(self, doc: Optional[QTextDocument]) -> None:
        self._asyncTimer.stop()
        super(GrammarHighlighter, self).setDocument(doc)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, LanguageToolSet):
            self._language_tool = language_tool_proxy.tool
            self.asyncRehighlight()

    @overrides
    def highlightBlock(self, text: str) -> None:
        data = self._currentblockData()
        if self._checkEnabled and self._language_tool:
            matches = self._language_tool.check(text)
            misspellings = []
            for m in matches:
                if dictionary.is_known_word(text[m.offset:m.offset + m.errorLength]):
                    continue
                self.setFormat(m.offset, m.errorLength,
                               self._formats_per_issue.get(m.ruleIssueType, self._grammar_format))
                misspellings.append((m.offset, m.errorLength, m.replacements, m.message, m.ruleIssueType))
            data.misspellings = misspellings
        else:
            data.misspellings.clear()

    def asyncRehighlight(self):
        if self._checkEnabled and self._language_tool:
            self._currentAsyncBlock = 0
            self._asyncTimer.start()

    def _highlightNextBlock(self):
        if self._currentAsyncBlock >= self.document().blockCount():
            return self._asyncTimer.stop()

        block = self.document().findBlockByNumber(self._currentAsyncBlock)
        self.rehighlightBlock(block)
        self._currentAsyncBlock += 1


class BlockStatistics(AbstractTextBlockHighlighter):

    @overrides
    def highlightBlock(self, text: str) -> None:
        data = self._currentblockData()
        data.wordCount = wc(text)


class CharacterContentAssistMenu(QMenu):
    characterSelected = pyqtSignal(Character)

    def __init__(self, parent=None):
        super(CharacterContentAssistMenu, self).__init__(parent)
        self.novel = app_env.novel
        self.lstCharacters = QListView(self)
        self.model = CharactersTableModel(self.novel)
        self._proxy = proxy(self.model)
        self.lstCharacters.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lstCharacters.clicked.connect(self._clicked)
        self.lstCharacters.setModel(self._proxy)

    def init(self, text: str = ''):
        action = QWidgetAction(self)

        action.setDefaultWidget(self.lstCharacters)
        self._proxy.setFilterRegularExpression(f'^{text}')
        if self._proxy.rowCount():
            self.lstCharacters.selectionModel().select(self._proxy.index(0, 0), QItemSelectionModel.Select)
        self.addAction(action)

    @overrides
    def popup(self, pos: QPoint) -> None:
        if self._proxy.rowCount() == 1:
            character = self._proxy.index(0, 0).data(CharactersTableModel.CharacterRole)
            self.characterSelected.emit(character)
        elif self._proxy.rowCount() > 1:
            super(CharacterContentAssistMenu, self).popup(pos)

    @overrides
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        super(CharacterContentAssistMenu, self).keyPressEvent(event)
        if event.key() == Qt.Key.Key_Return:
            indexes = self.lstCharacters.selectedIndexes()
            if indexes:
                self._clicked(indexes[0])

    def _clicked(self, index: QModelIndex):
        char = index.data(CharactersTableModel.CharacterRole)
        self.characterSelected.emit(char)


class GrammarPopup(QFrame):
    replacementRequested = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self._locked = False
        self.setProperty('rounded', True)
        self.setProperty('relaxed-white-bg', True)
        self.lblType = label(bold=True)
        self.wdgReplacements = QWidget()
        flow(self.wdgReplacements)
        self.btnClose = RemovalButton()
        self.lblMessage = label(description=True, wordWrap=True)
        self.lblMessage.setMinimumWidth(200)
        self.lblMessage.setMaximumWidth(300)
        decr_font(self.lblMessage)

        self.wdgTop = QWidget()
        hbox(self.wdgTop)
        self.wdgTop.layout().addWidget(self.lblType, alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgTop.layout().addWidget(self.btnClose, alignment=Qt.AlignmentFlag.AlignRight)

        vbox(self, 8)
        self.layout().addWidget(self.wdgTop)
        self.layout().addWidget(line())
        self.layout().addWidget(self.lblMessage)
        self.layout().addWidget(self.wdgReplacements)

    def init(self, replacements: List[str], msg: str, style: str):
        if style in ['misspelling']:
            apply_color(self.lblType, '#d90429')
        elif style == 'style':
            apply_color(self.lblType, '#5a189a')
        else:
            apply_color(self.lblType, '#ffc300')
        self.lblType.setText(style.capitalize())
        self.lblMessage.setText(msg)

        clear_layout(self.wdgReplacements)
        for i, replacement in enumerate(replacements):
            if i > 10:
                break
            self.wdgReplacements.layout().addWidget(self._button(replacement))

    def locked(self):
        return self._locked

    def lock(self):
        self._locked = True

    def unlock(self):
        self._locked = False

    def _button(self, replacement: str) -> QPushButton:
        btn = QPushButton(replacement, self)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty('lang-spellcheck-suggestion', True)
        btn.clicked.connect(lambda: self.replacementRequested.emit(replacement))

        return btn


@dataclass
class ReplacementInfo:
    cursor: QTextCursor
    start: int
    length: int


class TextEditBase(EnhancedTextEdit):

    def __init__(self, parent=None):
        super(TextEditBase, self).__init__(parent)
        self._blockStatistics = BlockStatistics(self.document())
        self.setDashInsertionMode(DashInsertionMode.INSERT_EM_DASH)
        self.setAutoCapitalizationMode(AutoCapitalizationMode.PARAGRAPH)

        self._wdgGrammarPopup: Optional[GrammarPopup] = None
        self._replacementInfo: Optional[ReplacementInfo] = None

    def statistics(self) -> TextStatistics:
        wc = 0
        for i in range(self.document().blockCount()):
            block = self.document().findBlockByNumber(i)
            data = block.userData()
            if isinstance(data, TextBlockData):
                wc += data.wordCount

        return TextStatistics(wc)

    # @overrides
    # def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
    #     super(TextEditBase, self).keyPressEvent(event)
    #     if event.key() == Qt.Key.Key_Space and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
    #         menu = CharacterContentAssistMenu(self)
    #         cursor = self.textCursor()
    #         cursor.select(QTextCursor.SelectionType.WordUnderCursor)
    #         menu.init(cursor.selectedText())
    #         menu.characterSelected.connect(self._insertCharacterName)
    #         menu.characterSelected.connect(menu.hide)
    #         rect = self.cursorRect(self.textCursor())
    #         self._popupMenu(menu, QPoint(rect.x(), rect.y()))

    @overrides
    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super(TextEditBase, self).mouseMoveEvent(event)
        cursor = self.cursorForPosition(event.pos())
        if cursor.atBlockStart() or cursor.atBlockEnd():
            QApplication.restoreOverrideCursor()
            return

        for start, length, replacements, msg, style in self._errors(cursor):
            if start <= cursor.positionInBlock() <= start + length:
                if QApplication.overrideCursor() is None:
                    QApplication.setOverrideCursor(Qt.CursorShape.PointingHandCursor)
                return
        QApplication.restoreOverrideCursor()

    @overrides
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        super(TextEditBase, self).mousePressEvent(event)
        QApplication.restoreOverrideCursor()
        cursor = self.cursorForPosition(event.pos())
        if cursor.atBlockStart() or cursor.atBlockEnd():
            QApplication.restoreOverrideCursor()
            return

        for start, length, replacements, msg, style in self._errors(cursor):
            if start <= cursor.positionInBlock() <= start + length:
                if self._wdgGrammarPopup is None:
                    self._wdgGrammarPopup = GrammarPopup(QApplication.activeWindow())
                    self._wdgGrammarPopup.replacementRequested.connect(self._replaceWord)
                    self._wdgGrammarPopup.btnClose.clicked.connect(self._wdgGrammarPopup.hide)

                self._replacementInfo = ReplacementInfo(cursor, start, length)
                self._wdgGrammarPopup.init(replacements, msg, style)
                self._popupWidget(self._wdgGrammarPopup, event.pos())

    @overrides
    def focusOutEvent(self, event: QFocusEvent):
        self._hidePopup(self._wdgGrammarPopup)

    def _popupWidget(self, wdg: GrammarPopup, pos: QPoint):
        ml = self.viewportMargins().left()
        tl = self.viewportMargins().top()
        global_pos: QPoint = self.mapToGlobal(pos) - QPoint(-ml,
                                                            wdg.sizeHint().height() + 40 - tl) - QApplication.activeWindow().pos()
        wdg.setGeometry(global_pos.x(), global_pos.y(), wdg.sizeHint().width(),
                        wdg.sizeHint().height())

        wdg.lock()
        qtanim.fade_in(wdg, teardown=wdg.unlock)

    @overrides
    def _cursorPositionChanged(self):
        self._hidePopup(self._wdgGrammarPopup)
        super()._cursorPositionChanged()

    def _hidePopup(self, wdg: GrammarPopup):
        if wdg and wdg.isVisible() and not wdg.locked():
            wdg.hide()

    def _errors(self, cursor: QTextCursor):
        data = cursor.block().userData()
        if data and isinstance(data, TextBlockData):
            return data.misspellings

        return []

    # def paintEvent(self, event: QtGui.QPaintEvent) -> None:
    #     super(_TextEditor, self).paintEvent(event)
    #     painter = QPainter(self.viewport())
    #     painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    #     painter.setPen(QPen(QColor('#02bcd4'), 20, Qt.PenStyle.SolidLine))
    #     painter.setBrush(QColor('#02bcd4'))
    #     # painter.begin()
    #     # painter.setPen(QPen(Qt.GlobalColor.black), 12, Qt.PenStyle.SolidLine)
    #     self.textCursor().position()
    #     rect = self.cursorRect(self.textCursor())
    #     painter.drawText(rect.x(), rect.y(), 'Painted text')
    #     # painter.drawLine(0, 0, self.width(), self.height())

    def _replaceWord(self, replacement: str):
        cursor = self._replacementInfo.cursor
        start = self._replacementInfo.start
        length = self._replacementInfo.length

        block_pos = cursor.block().position()
        cursor.setPosition(block_pos + start, QTextCursor.MoveMode.MoveAnchor)
        cursor.setPosition(block_pos + start + length, QTextCursor.MoveMode.KeepAnchor)
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(replacement)
        cursor.endEditBlock()
        QApplication.restoreOverrideCursor()

    def _insertCharacterName(self, character: Character):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.removeSelectedText()
        cursor.insertText(character.name)
        cursor.endEditBlock()


class TextEditorBase(RichTextEditor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._wdgFind.lineEditSearch().setProperty('rounded', True)
        self._wdgFind.lineEditSearch().setProperty('white-bg', True)
        self._wdgFind.lineEditReplace().setProperty('rounded', True)
        self._wdgFind.lineEditReplace().setProperty('white-bg', True)

        self._wdgFind.setProperty('relaxed-white-bg', True)


class DocumentTextEdit(TextEditBase):
    grammarCheckToggled = pyqtSignal(bool)

    @overrides
    def createEnhancedContextMenu(self, pos: QPoint) -> QMenu:
        menu = super(DocumentTextEdit, self).createEnhancedContextMenu(pos)

        menu.addSeparator()
        grammar_action = action('Grammar check', slot=self.grammarCheckToggled.emit, parent=menu, checkable=True)
        grammar_action.setChecked(app_env.novel.prefs.docs.grammar_check)
        menu.addAction(grammar_action)
        return menu


class CapitalizationEventFilter(QObject):

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if isinstance(event, QKeyEvent) and event.type() == QEvent.Type.KeyPress:
            if (event.text().isalpha() and (self._empty(watched) or self._selectedAll(
                    watched)) and not watched.property(IGNORE_CAPITALIZATION_PROPERTY)
                    and 'filter' not in watched.objectName().lower() and not self._readOnly(
                        watched)):
                inserted = self._insert(watched, event.text().upper())
                if inserted:
                    return True
        return super(CapitalizationEventFilter, self).eventFilter(watched, event)

    def _empty(self, widget) -> bool:
        if isinstance(widget, QLineEdit):
            return not widget.text()
        elif isinstance(widget, QTextEdit):
            return not widget.toPlainText()
        return False

    def _readOnly(self, widget) -> bool:
        if isinstance(widget, QLineEdit):
            return widget.isReadOnly()
        elif isinstance(widget, QTextEdit):
            return widget.isReadOnly()
        return False

    def _selectedAll(self, widget) -> bool:
        if isinstance(widget, QLineEdit):
            return widget.hasSelectedText() and widget.selectedText() == widget.text()
        elif isinstance(widget, QTextEdit):
            cursor = widget.textCursor()
            return cursor.hasSelection() and cursor.selectedText() == widget.toPlainText()
        return False

    def _insert(self, widget, text: str) -> bool:
        if isinstance(widget, QLineEdit):
            widget.insert(text)
            return True
        elif isinstance(widget, QTextEdit):
            widget.insertPlainText(text)
            return True
        return False


class DocumentTextEditor(TextEditorBase):
    titleChanged = pyqtSignal(str)
    iconChanged = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super(DocumentTextEditor, self).__init__(parent)
        self._titleVisible: bool = True

        self._btnIcon = tool_btn(QIcon(), transparent_=True)
        self._btnIcon.setIconSize(QSize(48, 48))
        self._btnIcon.installEventFilter(OpacityEventFilter(self._btnIcon, leaveOpacity=1.0, enterOpacity=0.8))
        self._btnIcon.clicked.connect(self._changeIcon)
        self._textTitle = QLineEdit()
        self._textTitle.setProperty('transparent', True)
        self._textTitle.setFrame(False)
        title_font = self._textTitle.font()
        title_font.setBold(True)
        title_font.setPointSize(40)
        self._textTitle.setFont(title_font)
        self._textTitle.returnPressed.connect(self.textEdit.setFocus)
        self._textTitle.textChanged.connect(self.titleChanged)

        apply_texteditor_toolbar_style(self.toolbar())

        self._wdgTitle = QWidget()
        hbox(self._wdgTitle, 0, 0)
        self._wdgTitle.layout().addWidget(self._btnIcon, alignment=Qt.AlignmentFlag.AlignCenter)
        self._wdgTitle.layout().addWidget(self._textTitle)
        self._wdgTitle.setProperty('relaxed-white-bg', True)
        margins(self._wdgTitle, top=20, bottom=5)
        self.setProperty('relaxed-white-bg', True)

        self.textEdit.setViewportMargins(5, 5, 5, 5)

        self.highlighter = self._initHighlighter()

        self.textEdit.setFont(QFont(app_env.sans_serif_font(), 16))
        self.textEdit.setProperty('transparent', True)
        self.textEdit.zoomIn(int(self.textEdit.font().pointSize() * 0.25))
        self.textEdit.setBlockFormat(lineSpacing=110, margin_bottom=10, margin_top=10)
        self.textEdit.setAutoFormatting(QTextEdit.AutoFormattingFlag.AutoAll)
        self.textEdit.setPlaceholderText("Begin writing, or press '/' for commands...")

        self.setWidthPercentage(90)

        self.layout().insertWidget(1, self._wdgTitle)

        self._textedit.verticalScrollBar().valueChanged.connect(self._scrolled)

    @property
    def textTitle(self):
        return self._textTitle

    @overrides
    def _initTextEdit(self) -> EnhancedTextEdit:
        def grammarCheckToggled(toggled: bool):
            app_env.novel.prefs.docs.grammar_check = toggled
            RepositoryPersistenceManager.instance().update_novel(app_env.novel)

            self.setGrammarCheckEnabled(toggled)
            if toggled:
                self.asyncCheckGrammar()
            else:
                self.checkGrammar()

        textedit = DocumentTextEdit(self)
        textedit.grammarCheckToggled.connect(grammarCheckToggled)
        return textedit

    @overrides
    def _resize(self):
        super(DocumentTextEditor, self)._resize()
        margins(self._wdgTitle, left=self.textEdit.viewportMargins().left())

    def _initHighlighter(self) -> GrammarHighlighter:
        return GrammarHighlighter(self.textEdit.document(), checkEnabled=False)

    def setText(self, content: str, title: str = '', icon: Optional[QIcon] = None, title_read_only: bool = False):
        self.textEdit.setHtml(remove_font(content))
        self.textEdit.setFocus()
        self._textTitle.setText(title)
        self._textTitle.setReadOnly(title_read_only)
        self.setTitleIcon(icon)
        self._textTitle.setVisible(self._titleVisible)

    def setTitleIcon(self, icon: Optional[QIcon] = None):
        self._btnIcon.setVisible(icon is not None)
        if icon:
            self._btnIcon.setIcon(icon)

    def setTitle(self, title: str):
        self._textTitle.setText(title)

    def setPlaceholderText(self, text: str):
        self.textEdit.setPlaceholderText(text)

    def setTitleVisible(self, visible: bool):
        self._titleVisible = visible
        self._wdgTitle.setVisible(visible)

    def setToolbarVisible(self, visible: bool):
        self.toolbar().setVisible(visible)

    def setMargins(self, left: int, top: int, right: int, bottom: int):
        self.textEdit.setViewportMargins(left, top, right, bottom)

    def setGrammarCheckEnabled(self, enabled: bool):
        self.highlighter.setCheckEnabled(enabled)

    def checkGrammar(self):
        self.highlighter.rehighlight()

    def asyncCheckGrammar(self):
        self.highlighter.asyncRehighlight()

    def clear(self):
        self.textEdit.clear()
        self._textTitle.clear()

    def statistics(self) -> TextStatistics:
        return self.textEdit.statistics()

    def _scrolled(self, value: int):
        if value > self._wdgTitle.height():
            self._wdgTitle.setHidden(True)
        elif self._titleVisible:
            self._wdgTitle.setVisible(True)

    def _changeIcon(self):
        if self._textTitle.isReadOnly():
            return
        result = IconSelectorDialog.popup()
        if result:
            name = result[0]
            color = result[1].name()
            self.iconChanged.emit(name, color)
            self._btnIcon.setIcon(IconRegistry.from_name(name, color))


class TextHighlighterAnimation:
    def __init__(self, text_edit, color: QColor, duration=300, interval=10):
        self.text_edit = text_edit
        self.color = color
        self.duration = duration
        self.interval = interval
        self.total_steps = self.duration // self.interval
        self.current_step = 0
        self.start_pos = 0
        self.end_pos = 0
        self.direction = 1
        self.step_alpha = 255 / self.total_steps
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_highlight_color)

    def start_highlight(self, start_pos: int, end_pos: int):
        self.current_step = 0
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.direction = 1
        self.timer.start(self.interval)

    def update_highlight_color(self):
        if self.current_step > self.total_steps * 2:
            self.timer.stop()
            return

        if self.current_step > self.total_steps:
            alpha = int((2 * self.total_steps - self.current_step) * self.step_alpha)
        else:
            alpha = int(self.current_step * self.step_alpha)

        cursor = self.text_edit.textCursor()
        cursor.setPosition(self.start_pos)
        cursor.setPosition(self.end_pos, QTextCursor.MoveMode.KeepAnchor)

        format = QTextCharFormat()
        format.setBackground(QColor(self.color.red(), self.color.green(), self.color.blue(), alpha))
        cursor.setCharFormat(format)

        self.current_step += 1


class RotatedButtonOrientation(Enum):
    VerticalTopToBottom = 0
    VerticalBottomToTop = 1


class RotatedButton(QPushButton):
    def __init__(self, parent=None):
        super(RotatedButton, self).__init__(parent)
        self._orientation = RotatedButtonOrientation.VerticalTopToBottom

    def setOrientation(self, orientation: RotatedButtonOrientation):
        self._orientation = orientation
        self.update()

    @overrides
    def paintEvent(self, event: QPaintEvent):
        if app_env.test_env():
            super(RotatedButton, self).paintEvent(event)
            return
        painter = QStylePainter(self)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        if self._orientation == RotatedButtonOrientation.VerticalTopToBottom:
            painter.rotate(90)
            painter.translate(0, -1 * self.width())
        else:
            painter.rotate(-90)
            painter.translate(-1 * self.height(), 0)
        option.rect = option.rect.transposed()
        painter.drawControl(QStyle.ControlElement.CE_PushButton, option)

        painter.end()

    @overrides
    def sizeHint(self):
        size = super(RotatedButton, self).sizeHint()
        size.transpose()
        return size


class Toggle(AnimatedToggle):
    def __init__(self, parent=None):
        super(Toggle, self).__init__(parent=parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(50)


class _PowerBar(QFrame):
    def __init__(self, steps: int = 10, startColor: str = 'red', endColor: str = 'green', parent=None):
        super(_PowerBar, self).__init__(parent)
        self.steps = steps
        self.startColor = startColor
        self.endColor = endColor
        self.value: int = 0

    @overrides
    def sizeHint(self) -> QSize:
        return QSize(10 * self.steps, 30)

    @overrides
    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.white)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(self.startColor))
        gradient.setColorAt(1, QColor(self.endColor))
        brush = QBrush(gradient)
        painter.setBrush(brush)

        painter.fillRect(0, 0, self.value * 10, self.height(), brush)

        painter.end()

    def increase(self):
        if self.value < self.steps:
            self.value += 1
            self.update()

    def decrease(self):
        if self.value > 0:
            self.value -= 1
            self.update()


class PowerBar(QFrame):
    MINUS_COLOR_IDLE: str = '#c75146'
    MINUS_COLOR_ACTIVE: str = '#ad2e24'
    PLUS_COLOR_IDLE: str = '#52b788'
    PLUS_COLOR_ACTIVE: str = '#81171b'

    def __init__(self, parent=None):
        super(PowerBar, self).__init__(parent)

        self.setFrameStyle(QFrame.Shape.Box)
        hbox(self, 0)
        self.btnMinus = QToolButton()
        self.btnMinus.setIcon(IconRegistry.minus_icon(self.MINUS_COLOR_IDLE))
        self.btnPlus = QToolButton()
        self.btnPlus.setIcon(IconRegistry.plus_circle_icon(self.PLUS_COLOR_IDLE))
        self._styleButton(self.btnMinus)
        self._styleButton(self.btnPlus)
        self.btnMinus.clicked.connect(self.decrease)
        self.btnPlus.clicked.connect(self.increase)

        self._bar = _PowerBar(startColor='#e1ecf7', endColor='#2ec4b6')
        self.layout().addWidget(self.btnMinus)
        self.layout().addWidget(self._bar)
        self.layout().addWidget(self.btnPlus)

    def _styleButton(self, button: QToolButton):
        transparent(button)
        button.installEventFilter(self)
        button.setIconSize(QSize(14, 14))
        button.setCursor(Qt.CursorShape.PointingHandCursor)

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if isinstance(watched, QToolButton):
            if event.type() == QEvent.Type.Enter:
                watched.setIconSize(QSize(16, 16))
            elif event.type() == QEvent.Type.Leave:
                watched.setIconSize(QSize(14, 14))

        return super(PowerBar, self).eventFilter(watched, event)

    def value(self) -> int:
        return self._bar.value

    def decrease(self):
        self.btnMinus.setIcon(IconRegistry.minus_icon(self.MINUS_COLOR_ACTIVE))
        QTimer.singleShot(100, lambda: self.btnMinus.setIcon(IconRegistry.minus_icon(self.MINUS_COLOR_IDLE)))
        self._bar.decrease()

    def increase(self):
        self.btnPlus.setIcon(IconRegistry.plus_circle_icon(self.PLUS_COLOR_ACTIVE))
        QTimer.singleShot(100, lambda: self.btnPlus.setIcon(IconRegistry.plus_circle_icon(self.PLUS_COLOR_IDLE)))
        self._bar.increase()


class RemovalButton(QToolButton):
    def __init__(self, parent=None, colorOff: str = 'grey', colorOn=RED_COLOR, colorHover='black'):
        super(RemovalButton, self).__init__(parent)
        self._colorOff = colorOff
        self._colorHover = colorHover
        self.setIcon(IconRegistry.close_icon(self._colorOff))
        pointy(self)
        self.installEventFilter(self)
        self.setIconSize(QSize(12, 12))
        transparent(self)

        self.pressed.connect(lambda: self.setIcon(IconRegistry.close_icon(colorOn)))
        self.released.connect(lambda: self.setIcon(IconRegistry.close_icon(colorOff)))

    @overrides
    def eventFilter(self, watched: 'QObject', event: 'QEvent') -> bool:
        if event.type() == QEvent.Type.Enter:
            self.setIcon(IconRegistry.close_icon(self._colorHover))
        elif event.type() == QEvent.Type.Leave:
            self.setIcon(IconRegistry.close_icon(self._colorOff))
        return super(RemovalButton, self).eventFilter(watched, event)


class ButtonsOnlySpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineEdit().setVisible(False)
        self.setFixedWidth(18)
        self.setFrame(False)


class FontSizeSpinBox(QWidget):
    DEFAULT_VALUE: int = 2
    fontChanged = pyqtSignal(int)

    def __init__(self, font_size_prefix: str = "Font Size:"):
        super().__init__()
        self._font_sizes = [8, 10, 12, 13, 14, 16, 18, 20, 24, 28, 32, 48, 64]

        self._label = QLabel(font_size_prefix, self)
        self._font_size_spinner = ButtonsOnlySpinBox(self)
        self._font_size_spinner.setRange(0, len(self._font_sizes) - 1)
        self._font_size_spinner.setValue(self.DEFAULT_VALUE)
        self._font_size_spinner.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)  # Show only up/down buttons
        self._font_size_spinner.valueChanged.connect(self._updateFontSize)

        hbox(self)
        self.layout().addWidget(self._label)
        self.layout().addWidget(self._font_size_spinner)

        self._updateFontSize()

    def setValue(self, value: int):
        try:
            index = self._font_sizes.index(value)
            self._font_size_spinner.setValue(index)
        except ValueError:
            self._font_size_spinner.setValue(self.DEFAULT_VALUE)

    def _updateFontSize(self):
        selected_index = self._font_size_spinner.value()
        font_size = self._font_sizes[selected_index]

        self._label.setText(f"{font_size} pt")

        self.fontChanged.emit(font_size)


class TextInputDialog(PopupDialog):
    def __init__(self, title: str, placeholder: str, value: str = '', parent=None):
        super().__init__(parent)

        self.title = label(title, h4=True)
        sp(self.title).v_max()
        self.wdgTitle = QWidget()
        hbox(self.wdgTitle, spacing=5)
        self.wdgTitle.layout().addWidget(self.title, alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgTitle.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)

        self.lineKey = QLineEdit()
        self.lineKey.setProperty('white-bg', True)
        self.lineKey.setProperty('rounded', True)
        self.lineKey.setPlaceholderText(placeholder)
        self.lineKey.setText(value)
        self.lineKey.textChanged.connect(self._textChanged)

        self.btnConfirm = push_btn(text='Confirm', properties=['base', 'positive'])
        self.btnConfirm.setShortcut(Qt.Key.Key_Return)
        sp(self.btnConfirm).h_exp()
        self.btnConfirm.clicked.connect(self.accept)
        self.btnConfirm.setDisabled(True)
        self.btnConfirm.installEventFilter(
            DisabledClickEventFilter(self.btnConfirm, lambda: qtanim.shake(self.lineKey)))
        self.lineKey.editingFinished.connect(self.btnConfirm.click)

        self.frame.layout().addWidget(self.wdgTitle)
        self.frame.layout().addWidget(self.lineKey)
        self.frame.layout().addWidget(self.btnConfirm)

    def display(self) -> Optional[str]:
        result = self.exec()

        if result == QDialog.DialogCode.Accepted:
            return self.lineKey.text()

        return None

    @classmethod
    def edit(cls, title: str = 'Edit text', placeholder: str = 'Edit text', value: str = ''):
        return cls.popup(title, placeholder, value)

    def _textChanged(self, key: str):
        self.btnConfirm.setEnabled(len(key) > 0)


class TextAreaInputDialog(PopupDialog):

    def __init__(self, title: str, placeholder: str, description: str, value: str = '', parent=None):
        super().__init__(parent)

        self.title = label(title, h4=True)
        sp(self.title).v_max()
        self.wdgTitle = QWidget()
        hbox(self.wdgTitle, spacing=5)
        self.wdgTitle.layout().addWidget(self.title, alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgTitle.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)

        self.lblDesc = label(description, description=True, wordWrap=True)
        sp(self.lblDesc).v_max()

        self.textEdit = QTextEdit()
        self.textEdit.setProperty('white-bg', True)
        self.textEdit.setProperty('rounded', True)
        self.setMaximumWidth(300)
        self.textEdit.setFixedSize(250, 60)
        self.textEdit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit.setPlaceholderText(placeholder)
        self.textEdit.setText(value)
        self.textEdit.textChanged.connect(self._textChanged)
        self.textEdit.installEventFilter(self)

        self.btnConfirm = push_btn(text='Confirm', properties=['base', 'positive'])
        self.btnConfirm.setFixedWidth(250)
        self.btnConfirm.setShortcut(Qt.Key.Key_Return)
        sp(self.btnConfirm).h_exp()
        self.btnConfirm.clicked.connect(self.accept)
        self.btnConfirm.setDisabled(True)
        self.btnConfirm.installEventFilter(
            DisabledClickEventFilter(self.btnConfirm, lambda: qtanim.shake(self.textEdit)))

        self.frame.layout().addWidget(self.wdgTitle)
        self.frame.layout().addWidget(line())
        self.frame.layout().addWidget(self.lblDesc)
        self.frame.layout().addWidget(self.textEdit, alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame.layout().addWidget(self.btnConfirm, alignment=Qt.AlignmentFlag.AlignCenter)

    def display(self) -> Optional[str]:
        result = self.exec()

        if result == QDialog.DialogCode.Accepted:
            return self.textEdit.toPlainText()

        return None

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Return:
            QTimer.singleShot(10, self.btnConfirm.click)
            return True
        return super().eventFilter(watched, event)

    @classmethod
    def edit(cls, title: str = 'Edit text', placeholder: str = 'Edit text', description: str = 'Edit text',
             value: str = ''):
        return cls.popup(title, placeholder, description, value)

    def _textChanged(self):
        self.btnConfirm.setEnabled(len(self.textEdit.toPlainText()) > 0)


class LabelWidget(QFrame):
    edited = pyqtSignal()
    removed = pyqtSignal()
    clicked = pyqtSignal()

    def __init__(self, label_: Label, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName('parentFrame')
        self._label = label_
        self.lblWidget = label(label_.keyword)
        self.lblWidget.setObjectName('labelText')
        self.setStyleSheet(f'''
            #parentFrame {{
                background-color: {PLOTLYST_SECONDARY_COLOR};
                border-radius: 16px;
            }}
            #labelText {{
                color: {RELAXED_WHITE_COLOR};
                font-family: Serif;
            }}''')

        self.btnMenu = DotsMenuButton()
        decr_icon(self.btnMenu, 2)
        hbox(self, 5)
        margins(self, left=7)
        self.layout().addWidget(self.lblWidget)
        self.layout().addWidget(self.btnMenu)
        self.btnMenu.setHidden(True)
        menu = MenuWidget(self.btnMenu)
        menu.addAction(action('Edit', IconRegistry.edit_icon(), self._edit))
        menu.addAction(action('Remove', IconRegistry.trash_can_icon(), self.removed))

        pointy(self)
        self.btnMenu.setCursor(Qt.CursorShape.ArrowCursor)

    def label(self) -> Label:
        return self._label

    def text(self):
        return self.lblWidget.text()

    @overrides
    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        translucent(self, 0.7)

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.setGraphicsEffect(None)
        self.clicked.emit()

    @overrides
    def enterEvent(self, event: QtGui.QEnterEvent) -> None:
        qtanim.fade_in(self.btnMenu)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        self.btnMenu.setHidden(True)

    def _edit(self):
        new_text = TextInputDialog.edit('Edit label', value=self.lblWidget.text())
        if new_text:
            self._label.keyword = new_text
            self.lblWidget.setText(new_text)
            self.edited.emit()


class LabelsEditor(QFrame):
    labelAdded = pyqtSignal(Label)
    labelEdited = pyqtSignal(Label)
    labelClicked = pyqtSignal(Label)
    labelRemoved = pyqtSignal(Label)

    def __init__(self, title: str = '', parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName('parentFrame')
        self.wdgHeader = QWidget()
        self.wdgHeader.setObjectName('labelsHeader')
        self.wdgContainer = QWidget()
        vbox(self, 0)
        self.layout().addWidget(self.wdgHeader)
        self.layout().addWidget(line())
        self.layout().addWidget(self.wdgContainer)

        self.setStyleSheet(f'''
            #parentFrame {{
                border-radius: 12px;
                border: 1px solid lightgrey;
            }}
            #labelsHeader {{
                background: {PLOTLYST_SECONDARY_COLOR};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px hidden lightgrey;
            }}
            #labelsTitle {{
                color: {RELAXED_WHITE_COLOR};
            }}
            #labelPlaceholder {{
                font-family: Serif;
            }}
        ''')

        hbox(self.wdgHeader, 0, 0)
        margins(self.wdgHeader, top=3, bottom=3)
        flow(self.wdgContainer, margin=10, spacing=6)

        self.lblTitle = label(title, bold=True)
        self.lblTitle.setObjectName('labelsTitle')
        self.wdgHeader.layout().addWidget(self.lblTitle, alignment=Qt.AlignmentFlag.AlignCenter)
        if not title:
            self.lblTitle.setHidden(True)

        self.linePlaceholder = QLineEdit()
        self.linePlaceholder.setObjectName('labelPlaceholder')
        self.linePlaceholder.setProperty('transparent', True)
        self.linePlaceholder.setProperty(IGNORE_CAPITALIZATION_PROPERTY, True)
        self.linePlaceholder.setPlaceholderText('Edit')
        self.linePlaceholder.installEventFilter(self)
        self.linePlaceholder.editingFinished.connect(self._editingFinished)

        self.btnAdd = tool_btn(IconRegistry.plus_icon(PLOTLYST_SECONDARY_COLOR), transparent_=True)
        self.btnAdd.installEventFilter(OpacityEventFilter(self.btnAdd, leaveOpacity=0.7))
        self.btnAdd.clicked.connect(self._startEditing)
        self.wdgContainer.layout().addWidget(self.linePlaceholder)
        self.linePlaceholder.setHidden(True)
        self.wdgContainer.layout().addWidget(self.btnAdd)

        sp(self).v_max()

    @overrides
    def eventFilter(self, watched: 'QObject', event: 'QEvent') -> bool:
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self._cancelEditing()
        elif event.type() == QEvent.Type.FocusOut:
            if not watched.text():
                self._cancelEditing()

        return super().eventFilter(watched, event)

    def addLabel(self, label: Label):
        lblWidget = LabelWidget(label)
        lblWidget.edited.connect(partial(self.labelEdited.emit, label))
        lblWidget.clicked.connect(partial(self.labelClicked.emit, label))
        lblWidget.removed.connect(partial(self._remove, lblWidget))
        insert_before(self.wdgContainer, lblWidget, self.linePlaceholder)

    def _startEditing(self):
        self.linePlaceholder.clear()
        self.btnAdd.setHidden(True)
        self.linePlaceholder.setVisible(True)
        self.linePlaceholder.setFocus()

    def _cancelEditing(self):
        self.linePlaceholder.clear()
        self._editingFinished()

    def _editingFinished(self):
        if self.linePlaceholder.text():
            label = Label(self.linePlaceholder.text())
            self.addLabel(label)
            self.labelAdded.emit(label)
        self.linePlaceholder.setHidden(True)
        self.btnAdd.setVisible(True)

    def _remove(self, lblWdg: LabelWidget):
        label = lblWdg.label()
        fade_out_and_gc(self.wdgContainer, lblWdg)
        self.labelRemoved.emit(label)


class TextEditBubbleWidget(QFrame):
    removed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._removalEnabled: bool = False

        vbox(self)
        self._title = QPushButton()
        transparent(self._title)
        bold(self._title)
        self._title.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._textedit = QTextEdit(self)
        self._textedit.setProperty('white-bg', True)
        self._textedit.setProperty('rounded', True)
        self._textedit.setTabChangesFocus(True)
        if app_env.is_mac():
            incr_font(self._textedit)
        self._textedit.setMinimumSize(175, 100)
        self._textedit.setMaximumSize(190, 120)
        self._textedit.verticalScrollBar().setVisible(False)

        self._textedit.textChanged.connect(self._textChanged)

        self.layout().addWidget(self._title, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._textedit)

        self._btnRemove = RemovalButton(self)
        self._btnRemove.setHidden(True)
        self._btnRemove.clicked.connect(self.removed)

        sp(self).v_max()

    @overrides
    def enterEvent(self, event: QtGui.QEnterEvent) -> None:
        if self._removalEnabled:
            self._btnRemove.setVisible(True)
            self._btnRemove.raise_()

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        self._btnRemove.setHidden(True)

    @overrides
    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self._btnRemove.setGeometry(self.width() - 20, 5, 20, 20)

    def _textChanged(self):
        pass
