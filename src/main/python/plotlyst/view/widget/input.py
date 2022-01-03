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
from builtins import getattr
from enum import Enum
from functools import partial

import fbs_runtime.platform
from PyQt6 import QtGui
from PyQt6.QtCore import Qt, QObject, QEvent, QTimer, QPoint, QSize
from PyQt6.QtGui import QKeySequence, QFont, QTextCursor, QTextBlockFormat, QTextCharFormat, QTextFormat, \
    QKeyEvent, QPaintEvent, QTextListFormat, QPainter, QBrush, QLinearGradient, QColor, QAction, QActionGroup
from PyQt6.QtWidgets import QTextEdit, QFrame, QPushButton, QStylePainter, QStyleOptionButton, QStyle, QToolBar, \
    QComboBox, QMenu, QVBoxLayout, QApplication, QToolButton, QHBoxLayout, QLabel
from overrides import overrides

from src.main.python.plotlyst.common import truncate_string
from src.main.python.plotlyst.view.common import line
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.widget._toggle import AnimatedToggle


class AutoAdjustableTextEdit(QTextEdit):
    def __init__(self, parent=None, height: int = 25):
        super(AutoAdjustableTextEdit, self).__init__(parent)
        self.textChanged.connect(self._resizeToContent)
        self._minHeight = height
        self.setAcceptRichText(False)
        self.setMaximumHeight(self._minHeight)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    @overrides
    def setText(self, text: str) -> None:
        self.setPlainText(text)

    @overrides
    def setPlainText(self, text: str) -> None:
        super(AutoAdjustableTextEdit, self).setPlainText(text)
        QTimer.singleShot(50, self._resizeToContent)

    def _resizeToContent(self):
        size = self.document().size()
        self.setMaximumHeight(max(self._minHeight, size.height()))


class _TextEditor(QTextEdit):
    @overrides
    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super(_TextEditor, self).mouseMoveEvent(event)
        cursor = self.cursorForPosition(event.pos())
        if cursor.atBlockStart() or cursor.atBlockEnd():
            QApplication.restoreOverrideCursor()
            return
        data = cursor.block().userData()
        errors = getattr(data, 'misspelled', [])
        for start, length, replacements in errors:
            if start <= cursor.positionInBlock() <= start + length:
                if QApplication.overrideCursor() is None:
                    QApplication.setOverrideCursor(Qt.CursorShape.PointingHandCursor)
                return
        QApplication.restoreOverrideCursor()

    @overrides
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        super(_TextEditor, self).mousePressEvent(event)
        QApplication.restoreOverrideCursor()
        cursor = self.cursorForPosition(event.pos())
        if cursor.atBlockStart() or cursor.atBlockEnd():
            QApplication.restoreOverrideCursor()
            return
        data = cursor.block().userData()
        errors = getattr(data, 'misspelled', [])
        for start, length, replacements in errors:
            if start <= cursor.positionInBlock() <= start + length:
                menu = QMenu(self)
                for i, repl in enumerate(replacements):
                    if i > 4:
                        break
                    menu.addAction(truncate_string(repl), partial(self._replaceWord, cursor, repl, start, length))
                menu.popup(self.mapToGlobal(event.pos()))

    # def paintEvent(self, event: QtGui.QPaintEvent) -> None:
    #     super(_TextEditor, self).paintEvent(event)
    #     painter = QPainter(self.viewport())
    #     painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    #     painter.setPen(QPen(QColor('#02bcd4'), 20, Qt.SolidLine))
    #     painter.setBrush(QColor('#02bcd4'))
    #     # painter.begin()
    #     # painter.setPen(QPen(Qt.GlobalColor.black), 12, Qt.SolidLine)
    #     self.textCursor().position()
    #     rect = self.cursorRect(self.textCursor())
    #     painter.drawText(rect.x(), rect.y(), 'Painted text')
    #     # painter.drawLine(0, 0, self.width(), self.height())

    def _replaceWord(self, cursor: QTextCursor, replacement: str, start: int, length: int):
        block_pos = cursor.block().position()
        cursor.setPosition(block_pos + start, QTextCursor.MoveMode.MoveAnchor)
        cursor.setPosition(block_pos + start + length, QTextCursor.MoveMode.KeepAnchor)
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(replacement)
        cursor.endEditBlock()
        QApplication.restoreOverrideCursor()


class RichTextEditor(QFrame):
    def __init__(self, parent=None):
        super(RichTextEditor, self).__init__(parent)

        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(2, 2, 2, 2)

        self.toolbar = QToolBar()
        self.toolbar.setStyleSheet('.QToolBar {background-color: rgb(255, 255, 255);}')
        self.toolbar.layout().setSpacing(5)
        self.textTitle = AutoAdjustableTextEdit(height=50)
        self.textTitle.setStyleSheet('border: 0px;')

        self.textEditor = _TextEditor()
        self.textEditor.setMouseTracking(True)

        self.textEditor.cursorPositionChanged.connect(self._updateFormat)
        self.textEditor.setViewportMargins(5, 5, 5, 5)

        if fbs_runtime.platform.is_linux():
            family = 'Noto Sans Mono'
        elif fbs_runtime.platform.is_mac():
            family = 'Palatino'
        else:
            family = 'Helvetica'
        self.textEditor.setStyleSheet(f'QTextEdit {{background: white; border: 0px; font: {family}}}')
        self.textEditor.setFontFamily(family)

        self._lblPlaceholder = QLabel(self.textEditor)
        font = QFont(family)
        font.setItalic(True)
        self._lblPlaceholder.setFont(font)
        self._lblPlaceholder.setStyleSheet('color: #118ab2;')

        self.setMouseTracking(True)
        self.textEditor.installEventFilter(self)
        self.textEditor.setMouseTracking(True)
        self.textEditor.setTabStopDistance(
            QtGui.QFontMetricsF(self.textEditor.font()).horizontalAdvance(' ') * 4)
        self.setMargins(3, 3, 3, 3)

        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.textTitle)
        self.layout().addWidget(self.textEditor)

        self.cbHeading = QComboBox()
        self.cbHeading.setStyleSheet('''
        QComboBox {
            border: 0px;
            padding: 1px 1px 1px 3px;
        }
        ''')

        self.cbHeading.addItem('Normal')
        self.cbHeading.addItem(IconRegistry.heading_1_icon(), '')
        self.cbHeading.addItem(IconRegistry.heading_2_icon(), '')
        self.cbHeading.addItem(IconRegistry.heading_3_icon(), '')
        self.cbHeading.setCurrentText('Normal')
        self.cbHeading.currentIndexChanged.connect(self._setHeading)

        self.actionBold = QAction(IconRegistry.from_name('fa5s.bold'), '')
        self.actionBold.triggered.connect(
            lambda x: self.textEditor.setFontWeight(QFont.Weight.Bold if x else QFont.Weight.Normal))
        self.actionBold.setCheckable(True)
        self.actionBold.setShortcut(QKeySequence.StandardKey.Bold)

        self.actionItalic = QAction(IconRegistry.from_name('fa5s.italic'), '')
        self.actionItalic.triggered.connect(self.textEditor.setFontItalic)
        self.actionItalic.setCheckable(True)
        self.actionItalic.setShortcut(QKeySequence.StandardKey.Italic)

        self.actionUnderline = QAction(IconRegistry.from_name('fa5s.underline'), '')
        self.actionUnderline.triggered.connect(self.textEditor.setFontUnderline)
        self.actionUnderline.setCheckable(True)
        self.actionUnderline.setShortcut(QKeySequence.StandardKey.Underline)

        self.actionAlignLeft = QAction(IconRegistry.from_name('fa5s.align-left'), '')
        self.actionAlignLeft.triggered.connect(lambda: self.textEditor.setAlignment(Qt.AlignmentFlag.AlignLeft))
        self.actionAlignLeft.setCheckable(True)
        self.actionAlignLeft.setChecked(True)
        self.actionAlignCenter = QAction(IconRegistry.from_name('fa5s.align-center'), '')
        self.actionAlignCenter.triggered.connect(lambda: self.textEditor.setAlignment(Qt.AlignmentFlag.AlignCenter))
        self.actionAlignCenter.setCheckable(True)
        self.actionAlignRight = QAction(IconRegistry.from_name('fa5s.align-right'), '')
        self.actionAlignRight.triggered.connect(lambda: self.textEditor.setAlignment(Qt.AlignmentFlag.AlignRight))
        self.actionAlignRight.setCheckable(True)

        self.actionInsertList = QAction(IconRegistry.from_name('fa5s.list'), '')
        self.actionInsertList.triggered.connect(
            lambda: self.textEditor.textCursor().insertList(QTextListFormat.Style.ListDisc))
        self.actionInsertNumberedList = QAction(IconRegistry.from_name('fa5s.list-ol'), '')
        self.actionInsertNumberedList.triggered.connect(
            lambda: self.textEditor.textCursor().insertList(QTextListFormat.Style.ListDecimal))

        self.actionGroupAlignment = QActionGroup(self.toolbar)
        self.actionGroupAlignment.addAction(self.actionAlignLeft)
        self.actionGroupAlignment.addAction(self.actionAlignCenter)
        self.actionGroupAlignment.addAction(self.actionAlignRight)

        self.toolbar.addWidget(self.cbHeading)
        self.toolbar.addAction(self.actionBold)
        self.toolbar.addAction(self.actionItalic)
        self.toolbar.addAction(self.actionUnderline)
        self.toolbar.addWidget(line(vertical=True))
        self.toolbar.addAction(self.actionAlignLeft)
        self.toolbar.addAction(self.actionAlignCenter)
        self.toolbar.addAction(self.actionAlignRight)
        self.toolbar.addWidget(line(vertical=True))
        self.toolbar.addAction(self.actionInsertList)
        self.toolbar.addAction(self.actionInsertNumberedList)

    def setText(self, content: str, title: str = '', title_read_only: bool = False):
        self.textEditor.setHtml(content)
        self.textEditor.setFocus()
        self.textTitle.setHtml(f'''
                            <style>
                                h1 {{text-align: center;}}
                                </style>
                            <h1>{title}</h1>''')
        self.textTitle.setReadOnly(title_read_only)

    def setTitleVisible(self, visible: bool):
        self.textTitle.setVisible(visible)

    def setToolbarVisible(self, visible: bool):
        self.toolbar.setVisible(visible)

    def setMargins(self, left: int, top: int, right: int, bottom: int):
        self.textEditor.setViewportMargins(left, top, right, bottom)

    def setFormat(self, lineSpacing: int = 100, textIndent: int = 20):
        blockFmt = QTextBlockFormat()
        blockFmt.setTextIndent(textIndent)
        blockFmt.setLineHeight(lineSpacing, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)

        cursor = self.textEditor.textCursor()
        cursor.clearSelection()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.mergeBlockFormat(blockFmt)

    def setFontPointSize(self, size: int):
        self.textEditor.textCursor().select(QTextCursor.SelectionType.Document)
        self.textEditor.setFontPointSize(size)
        font = self._lblPlaceholder.font()
        font.setPointSize(size)
        self._lblPlaceholder.setFont(font)
        self.textEditor.textCursor().clearSelection()

    def clear(self):
        self.textEditor.clear()
        self.textTitle.clear()

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if isinstance(event, QKeyEvent):
            # if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key_Return:
            #     if self._lblPlaceholder.isVisible():
            #         self.textEditor.textCursor().insertText(self._lblPlaceholder.text())
            #         self._lblPlaceholder.hide()
            #         return True
            # elif event.type() == QEvent.Type.KeyPress and self._lblPlaceholder.isVisible():
            #     self._lblPlaceholder.hide()

            cursor = self.textEditor.textCursor()
            if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Tab:
                _list = cursor.block().textList()
                if _list and _list.count() > 1:
                    cursor.beginEditBlock()
                    block = cursor.block()
                    _list.remove(block)
                    _list.format().setIndent(_list.format().indent() + 1)
                    cursor.insertList(_list.format())

                    cursor.endEditBlock()
                    return True
            if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Return:
                level = cursor.blockFormat().headingLevel()
                if level > 0:  # heading
                    cursor.insertBlock()
                    self.cbHeading.setCurrentIndex(0)
                    self._setHeading()
                    return True
            if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Slash:
                if self.textEditor.textCursor().atBlockStart():
                    self._showCommands()

            if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Space:
                cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)
                if cursor.selectedText() == ' ':
                    self.textEditor.textCursor().deletePreviousChar()
                    self.textEditor.textCursor().insertText('.')
            elif event.type() == QEvent.Type.KeyPress and event.text().isalpha() and self._atSentenceStart(cursor):
                self.textEditor.textCursor().insertText(event.text().upper())
                return True
            elif event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_QuoteDbl:
                self.textEditor.textCursor().insertText(event.text())
                cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter)
                self.textEditor.setTextCursor(cursor)
            # elif event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key_Tab:
            #     self._lblPlaceholder.setText(' said ')
            #     self._lblPlaceholder.show()
            #     rect = self.textEditor.cursorRect(cursor)
            #     self._lblPlaceholder.move(rect.x() + self.textEditor.viewportMargins().left(),
            #                               rect.y() + self.textEditor.viewportMargins().top())

        return super(RichTextEditor, self).eventFilter(watched, event)

    def _atSentenceStart(self, cursor: QTextCursor) -> bool:
        if cursor.atBlockStart():
            return True

        cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)
        if cursor.selectedText() == '.':
            return True
        if cursor.atBlockStart() and cursor.selectedText() == '"':
            return True
        if cursor.positionInBlock() == 1:
            return False
        elif cursor.selectedText() == ' ' or cursor.selectedText() == '"':
            cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)
            if cursor.selectedText().startswith('.'):
                return True

        return False

    def _updateFormat(self):
        self.actionBold.setChecked(self.textEditor.fontWeight() == QFont.Weight.Bold)
        self.actionItalic.setChecked(self.textEditor.fontItalic())
        self.actionUnderline.setChecked(self.textEditor.fontUnderline())

        self.actionAlignLeft.setChecked(self.textEditor.alignment() == Qt.AlignmentFlag.AlignLeft)
        self.actionAlignCenter.setChecked(self.textEditor.alignment() == Qt.AlignmentFlag.AlignCenter)
        self.actionAlignRight.setChecked(self.textEditor.alignment() == Qt.AlignmentFlag.AlignRight)

        self.cbHeading.blockSignals(True)
        cursor = self.textEditor.textCursor()
        level = cursor.blockFormat().headingLevel()
        self.cbHeading.setCurrentIndex(level)
        self.cbHeading.blockSignals(False)

    def _setHeading(self):
        cursor: QTextCursor = self.textEditor.textCursor()
        cursor.beginEditBlock()

        blockFormat: QTextBlockFormat = cursor.blockFormat()
        blockFormat.setObjectIndex(-1)
        headingLevel = self.cbHeading.currentIndex()
        blockFormat.setHeadingLevel(headingLevel)
        cursor.setBlockFormat(blockFormat)
        sizeAdjustment = 5 - headingLevel if headingLevel else 0

        charFormat = QTextCharFormat()
        charFormat.setFontWeight(QFont.Weight.Bold if headingLevel else QFont.Weight.Normal)
        charFormat.setProperty(QTextFormat.Property.FontSizeAdjustment, sizeAdjustment)
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        cursor.mergeCharFormat(charFormat)
        self.textEditor.mergeCurrentCharFormat(charFormat)

        cursor.endEditBlock()

    def _showCommands(self):
        def trigger(func):
            self.textEditor.textCursor().deletePreviousChar()
            func()

        rect = self.textEditor.cursorRect(self.textEditor.textCursor())

        menu = QMenu(self.textEditor)
        menu.addAction(IconRegistry.heading_1_icon(), '', partial(trigger, lambda: self.cbHeading.setCurrentIndex(1)))
        menu.addAction(IconRegistry.heading_2_icon(), '', partial(trigger, lambda: self.cbHeading.setCurrentIndex(2)))

        menu.popup(self.textEditor.viewport().mapToGlobal(QPoint(rect.x(), rect.y())))


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
    pass


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
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(3)
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
        button.setStyleSheet('border: 0px;')
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
