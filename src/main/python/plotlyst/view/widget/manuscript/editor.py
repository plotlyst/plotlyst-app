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
import math
from functools import partial
from typing import Optional, List

from PyQt6 import QtGui
from PyQt6.QtCore import pyqtSignal, QTextBoundaryFinder, Qt, QSize, QTimer, QEvent, QPoint
from PyQt6.QtGui import QFont, QResizeEvent, QShowEvent, QTextCursor, QTextCharFormat, QSyntaxHighlighter, QColor, \
    QTextBlock, QFocusEvent, QTextDocumentFragment
from PyQt6.QtWidgets import QWidget, QApplication, QTextEdit, QLineEdit, QToolButton, QFrame, QPushButton, \
    QGraphicsColorizeEffect
from overrides import overrides
from qthandy import vbox, clear_layout, vspacer, margins, transparent, gc, hbox, italic, translucent, sp, spacer, \
    decr_font, retain_when_hidden, pointy
from qthandy.filter import OpacityEventFilter
from qttextedit import remove_font, TextBlockState, DashInsertionMode, AutoCapitalizationMode, EllipsisInsertionMode
from qttextedit.ops import Heading1Operation, Heading2Operation, Heading3Operation, InsertListOperation, \
    InsertNumberedListOperation, BoldOperation, ItalicOperation, UnderlineOperation, StrikethroughOperation, \
    AlignLeftOperation, AlignCenterOperation, AlignRightOperation

from plotlyst.common import RELAXED_WHITE_COLOR, DEFAULT_MANUSCRIPT_LINE_SPACE, DEFAULT_MANUSCRIPT_INDENT, \
    PLACEHOLDER_TEXT_COLOR, PLOTLYST_TERTIARY_COLOR
from plotlyst.core.client import json_client
from plotlyst.core.domain import DocumentProgress, Novel, Scene, TextStatistics, DocumentStatistics, FontSettings, \
    Chapter
from plotlyst.core.sprint import TimerModel
from plotlyst.env import app_env
from plotlyst.event.core import Event, EventListener
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import SceneDeletedEvent, SceneChangedEvent, ScenesOrganizationResetEvent
from plotlyst.resources import resource_registry
from plotlyst.service.manuscript import daily_progress, daily_overall_progress
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import tool_btn, fade_in, fade, frame, restyle
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.text import apply_text_color
from plotlyst.view.style.theme import BG_DARK_COLOR
from plotlyst.view.widget.display import WordsDisplay, DividerWidget, SeparatorLineWithShadow
from plotlyst.view.widget.input import BasePopupTextEditorToolbar, TextEditBase, GrammarHighlighter, \
    GrammarHighlightStyle
from plotlyst.view.widget.manuscript import SprintWidget
from plotlyst.view.widget.manuscript.find import ManuscriptFindWidget
from plotlyst.view.widget.manuscript.settings import ManuscriptEditorSettingsWidget


class DistFreeDisplayBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self, 4, 6)
        margins(self, left=15, right=15)
        self.setStyleSheet(f'QWidget {{background-color: {BG_DARK_COLOR};}}')
        sp(self).v_max()

        self.btnExitDistFreeMode = tool_btn(IconRegistry.from_name('mdi.arrow-collapse', RELAXED_WHITE_COLOR),
                                            transparent_=True, tooltip='Exit distraction-free mode')
        self.btnExitDistFreeMode.installEventFilter(OpacityEventFilter(self.btnExitDistFreeMode, leaveOpacity=0.8))
        retain_when_hidden(self.btnExitDistFreeMode)

        self.wdgSprint = SprintWidget(self)
        self.wdgSprint.setCompactMode(True)

        self.layout().addWidget(self.wdgSprint, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.btnExitDistFreeMode, alignment=Qt.AlignmentFlag.AlignRight)

    def activate(self, timer: Optional[TimerModel] = None):
        self.btnExitDistFreeMode.setVisible(True)
        if timer and timer.isActive():
            self.wdgSprint.setModel(timer)
            self.wdgSprint.setVisible(True)
        else:
            self.wdgSprint.setHidden(True)
        QTimer.singleShot(5000, self._hideItems)

    @overrides
    def enterEvent(self, event: QtGui.QEnterEvent) -> None:
        if not self.btnExitDistFreeMode.isVisible():
            fade_in(self.btnExitDistFreeMode)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        self.btnExitDistFreeMode.setHidden(True)

    def _hideItems(self):
        if not self.underMouse():
            self.btnExitDistFreeMode.setHidden(True)


class DistFreeControlsBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self, 4, 6)
        margins(self, left=15, right=15)
        self.setStyleSheet(f'QWidget {{background-color: {BG_DARK_COLOR};}}')
        sp(self).v_max()
        self.lblWords: Optional[WordsDisplay] = None

        self.btnFocus = self._initButton('mdi.credit-card', 'Highlight')
        self.btnTypewriterMode = self._initButton('mdi.format-align-top', 'Centered')
        self.btnTypewriterMode.setChecked(True)
        self.btnWordCount = self._initButton('mdi6.counter', 'Word count')
        self.btnWordCount.clicked.connect(self._wordCountClicked)

        self.layout().addWidget(self.btnFocus)
        self.layout().addWidget(self.btnTypewriterMode)
        self.layout().addWidget(self.btnWordCount)
        self.layout().addWidget(spacer())

    def activate(self):
        self.btnFocus.setVisible(True)
        self.btnTypewriterMode.setVisible(True)
        self.btnWordCount.setVisible(True)
        QTimer.singleShot(4000, self._hideItems)

    @overrides
    def enterEvent(self, event: QtGui.QEnterEvent) -> None:
        if not self.btnFocus.isVisible():
            fade_in(self.btnFocus)
            fade_in(self.btnTypewriterMode)
            fade_in(self.btnWordCount)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        self.btnFocus.setHidden(True)
        self.btnTypewriterMode.setHidden(True)
        self.btnWordCount.setHidden(True)

    def setWordDisplay(self, words: WordsDisplay):
        words.setNightModeEnabled(True)
        self.lblWords = words
        self.layout().addWidget(self.lblWords)
        self.lblWords.setVisible(self.btnWordCount.isChecked())

    def _hideItems(self):
        if not self.underMouse():
            self.btnFocus.setHidden(True)
            self.btnTypewriterMode.setHidden(True)
            self.btnWordCount.setHidden(True)

    def _wordCountClicked(self, checked: bool):
        if self.lblWords:
            fade(self.lblWords, checked)

    def _initButton(self, icon: str, text: str) -> QToolButton:
        btn = tool_btn(
            IconRegistry.from_name(icon, 'lightgrey', color_on=PLOTLYST_TERTIARY_COLOR), checkable=True,
            properties=[
                'base', 'dark-mode-toggle'
            ])
        btn.setIconSize(QSize(22, 22))
        decr_font(btn, 2)
        btn.setText(text)
        retain_when_hidden(btn)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        return btn


class SentenceHighlighter(QSyntaxHighlighter):
    DEFAULT_FOREGROUND_COLOR = '#dee2e6'

    def __init__(self, textedit: QTextEdit):
        super(SentenceHighlighter, self).__init__(textedit.document())
        self._editor = textedit
        self._sentenceEnabled: bool = False

        self._hidden_format = QTextCharFormat()
        self._hidden_format.setForeground(QColor(self.DEFAULT_FOREGROUND_COLOR))

        self._visible_format = QTextCharFormat()
        self._visible_format.setForeground(QColor(RELAXED_WHITE_COLOR))

        self._prevBlock: Optional[QTextBlock] = None
        self._editor.cursorPositionChanged.connect(self.rehighlight)

    def sentenceHighlightEnabled(self) -> bool:
        return self._sentenceEnabled

    def setSentenceHighlightEnabled(self, enabled: bool):
        self._sentenceEnabled = enabled
        self._hidden_format.setForeground(QColor('#38414A' if enabled else self.DEFAULT_FOREGROUND_COLOR))
        self.rehighlight()

    @overrides
    def highlightBlock(self, text: str) -> None:
        self.setFormat(0, len(text), self._hidden_format)
        if self._sentenceEnabled and self._editor.hasFocus() and self._editor.textCursor().block() == self.currentBlock():
            text = self._editor.textCursor().block().text()
            finder = QTextBoundaryFinder(QTextBoundaryFinder.BoundaryType.Sentence, text)
            pos = self._editor.textCursor().positionInBlock()
            boundary = finder.toNextBoundary()
            prev_boundary = 0
            while -1 < boundary < pos:
                prev_boundary = boundary
                boundary = finder.toNextBoundary()

            self.setFormat(prev_boundary, boundary - prev_boundary, self._visible_format)


class ManuscriptPopupTextEditorToolbar(BasePopupTextEditorToolbar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty('rounded', True)
        self.setProperty('relaxed-white-bg', True)
        margins(self, 5, 5, 5, 5)

        self.addTextEditorOperation(BoldOperation)
        self.addTextEditorOperation(ItalicOperation)
        self.addTextEditorOperation(UnderlineOperation)
        self.addTextEditorOperation(StrikethroughOperation)
        self.addSeparator()
        self.addTextEditorOperation(AlignLeftOperation)
        self.addTextEditorOperation(AlignCenterOperation)
        self.addTextEditorOperation(AlignRightOperation)
        self.addSeparator()
        self.addTextEditorOperation(InsertListOperation)
        self.addTextEditorOperation(InsertNumberedListOperation)


class SceneSeparator(QPushButton):
    def __init__(self, scene: Scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        transparent(self)
        pointy(self)
        italic(self)
        translucent(self)
        decr_font(self)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self.refresh()

    def refresh(self):
        self.setText(f'~{self.scene.title if self.scene.title else "Scene"}~')


class ManuscriptTextEdit(TextEditBase):
    sceneSeparatorClicked = pyqtSignal(Scene)

    def __init__(self, parent=None, readOnly: bool = False):
        super(ManuscriptTextEdit, self).__init__(parent)
        self._pasteAsOriginalEnabled = False
        self._resizedOnShow: bool = False
        self._menuIsShown = False
        self._minHeight = 40
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTabChangesFocus(True)
        self._scene: Optional[Scene] = None

        self.highlighter = GrammarHighlighter(self.document(), checkEnabled=False,
                                              highlightStyle=GrammarHighlightStyle.BACKGOUND)

        self._sentenceHighlighter: Optional[SentenceHighlighter] = None

        self.setReadOnly(readOnly)
        if not readOnly:
            toolbar = ManuscriptPopupTextEditorToolbar()
            toolbar.activate(self)
            self.setPopupWidget(toolbar)

        self._setDefaultStyleSheet()
        self.setCommandOperations([Heading1Operation, Heading2Operation, Heading3Operation, InsertListOperation,
                                   InsertNumberedListOperation])

        self.textChanged.connect(self.resizeToContent)

    @overrides
    def createEnhancedContextMenu(self, pos: QPoint):
        def show():
            self._menuIsShown = True

        def hide():
            self._menuIsShown = False

        menu = super().createEnhancedContextMenu(pos)
        menu.aboutToShow.connect(show)
        menu.aboutToHide.connect(hide)
        return menu

    @overrides
    def setFocus(self) -> None:
        super().setFocus()
        self.moveCursor(QTextCursor.MoveOperation.Start)

    @overrides
    def focusOutEvent(self, event: QFocusEvent):
        super().focusOutEvent(event)
        if self._sentenceHighlighter and self._sentenceHighlighter.sentenceHighlightEnabled():
            self._sentenceHighlighter.rehighlight()
        if self.textCursor().hasSelection() and not self._menuIsShown:
            cursor = self.textCursor()
            cursor.clearSelection()
            self.setTextCursor(cursor)

    @overrides
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        cursor: QTextCursor = self.textCursor()
        move_up = cursor.block().blockNumber() == 0 and event.key() == Qt.Key.Key_Up
        move_down = cursor.block().blockNumber() == self.document().blockCount() - 1 and event.key() == Qt.Key.Key_Down

        if move_up or move_down:
            parent = self.parentWidget()
            if parent:
                focus_chain = parent.findChildren(QTextEdit)
                if focus_chain:
                    if (self is focus_chain[0] and move_up) or (self is focus_chain[-1] and move_down):
                        super(ManuscriptTextEdit, self).keyPressEvent(event)
                        return

                    current_index = focus_chain.index(self)
                    next_textedit = (
                        focus_chain[current_index - 1] if move_up else focus_chain[current_index + 1]
                    )
                    if next_textedit:
                        next_textedit.setFocus()

                        next_cursor = next_textedit.textCursor()
                        if move_up:
                            next_cursor.movePosition(QTextCursor.MoveOperation.End)
                        else:
                            next_cursor.movePosition(QTextCursor.MoveOperation.Start)
                        next_textedit.setTextCursor(next_cursor)

                    return
        super(ManuscriptTextEdit, self).keyPressEvent(event)

    # @overrides
    # def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
    #     anchor = self.anchorAt(event.pos())
    #     if anchor and anchor.startswith(SceneSeparatorTextFormatPrefix):
    #         if QApplication.overrideCursor() is None:
    #             QApplication.setOverrideCursor(Qt.CursorShape.PointingHandCursor)
    #         synopsis = self._sceneTextObject.sceneSynopsis(anchor.replace(SceneSeparatorTextFormatPrefix, ''))
    #         self.setToolTip(synopsis)
    #         return
    #     else:
    #         QApplication.restoreOverrideCursor()
    #         self.setToolTip('')
    #     super(ManuscriptTextEdit, self).mouseMoveEvent(event)

    # @overrides
    # def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
    #     anchor = self.anchorAt(event.pos())
    #     if anchor and anchor.startswith(SceneSeparatorTextFormatPrefix):
    #         scene = self._sceneTextObject.scene(anchor.replace(SceneSeparatorTextFormatPrefix, ''))
    #         if scene:
    #             self.sceneSeparatorClicked.emit(scene)
    #         return
    #
    #     super(ManuscriptTextEdit, self).mouseReleaseEvent(event)

    def setGrammarCheckEnabled(self, enabled: bool):
        self.highlighter.setCheckEnabled(enabled)

    def checkGrammar(self):
        self.highlighter.rehighlight()

    def asyncCheckGrammar(self):
        self.highlighter.asyncRehighlight()

    def initSentenceHighlighter(self):
        transparent(self)
        self._sentenceHighlighter = SentenceHighlighter(self)

    def clearSentenceHighlighter(self):
        if self._sentenceHighlighter is not None:
            gc(self._sentenceHighlighter)
            self._sentenceHighlighter = None

        self._setDefaultStyleSheet()

    def setSentenceHighlighterEnabled(self, enabled: bool):
        self._sentenceHighlighter.setSentenceHighlightEnabled(enabled)

    def setHighlights(self, highlights: list):
        self.highlighter.setHighlights(highlights)

    def clearHighlights(self):
        self.highlighter.clearHighlights()

    def scene(self) -> Optional[Scene]:
        return self._scene

    def setScene(self, scene: Scene):
        # self._sceneTextObject.setScenes([scene])
        self._scene = scene
        self._addScene(scene)
        self.setUneditableBlocksEnabled(False)
        self.document().clearUndoRedoStacks()
        self.resizeToContent()

    # def setScenes(self, scenes: List[Scene]):
    #     def sceneCharFormat(scene: Scene) -> QTextCharFormat:
    #         sceneSepCharFormat = QTextCharFormat()
    #         sceneSepCharFormat.setObjectType(SceneSeparatorTextFormat)
    #         sceneSepCharFormat.setToolTip(scene.synopsis)
    #         sceneSepCharFormat.setAnchor(True)
    #         sceneSepCharFormat.setAnchorHref(f'{SceneSeparatorTextFormatPrefix}{scene.id}')
    #
    #         return sceneSepCharFormat
    #
    #     self.setUneditableBlocksEnabled(True)
    #     self._sceneTextObject.setScenes(scenes)
    #
    #     for i, scene in enumerate(scenes):
    #         self.textCursor().insertBlock(self._sceneSepBlockFormat)
    #         self.textCursor().insertText(f'{OBJECT_REPLACEMENT_CHARACTER}', sceneCharFormat(scene))
    #         self.textCursor().block().setUserState(TextBlockState.UNEDITABLE.value)
    #         self.insertNewBlock()
    #         self._addScene(scene)
    #
    #     self._deleteBlock(0, force=True)
    #
    #     self.document().clearUndoRedoStacks()
    #     self.resizeToContent()

    # def insertNewBlock(self):
    #     self.textCursor().insertBlock(self._defaultBlockFormat, QTextCharFormat())

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self._resizedOnShow:
            self.resizeToContent()
            self._resizedOnShow = True

    @overrides
    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        if self._resizedOnShow:
            self.resizeToContent()

    def resizeToContent(self):
        padding = self.contentsMargins().top() + self.contentsMargins().bottom() + 2 * self.document().documentMargin()
        size = self.document().size()
        self.setFixedHeight(max(self._minHeight, math.ceil(size.height() + padding)))

    def _addScene(self, scene: Scene):
        if not scene.manuscript.loaded:
            json_client.load_document(app_env.novel, scene.manuscript)

        first_scene_block = self.textCursor().block()
        self.textCursor().insertHtml(remove_font(scene.manuscript.content))
        if first_scene_block.userState() == TextBlockState.UNEDITABLE.value:
            first_scene_block.setUserState(-1)

    def _transparent(self):
        border = 0
        self.setStyleSheet(f'border-top: {border}px dashed {RELAXED_WHITE_COLOR}; background-color: rgba(0, 0, 0, 0);')

    def _setDefaultStyleSheet(self):
        self.setStyleSheet(
            f'ManuscriptTextEdit {{background-color: {RELAXED_WHITE_COLOR};}}')


class ManuscriptEditor(QWidget, EventListener):
    textChanged = pyqtSignal()
    selectionChanged = pyqtSignal()
    progressChanged = pyqtSignal(DocumentProgress)
    sceneTitleChanged = pyqtSignal(Scene)
    sceneSeparatorClicked = pyqtSignal(Scene)
    cursorPositionChanged = pyqtSignal(int, int, int, int)
    cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._novel: Optional[Novel] = None
        self._textedits: List[ManuscriptTextEdit] = []
        self._defaultMargins = 45
        self._minimumMargins = 10
        self._sceneLabels: List[SceneSeparator] = []
        self._scenes: List[Scene] = []
        self._scene: Optional[Scene] = None
        self._chapter: Optional[Chapter] = None
        self._font = self.defaultFont()
        self._lineSpace: int = DEFAULT_MANUSCRIPT_LINE_SPACE
        self._characterWidth: int = 40
        self._maxContentWidth = 0
        self._settings: Optional[ManuscriptEditorSettingsWidget] = None
        self._lockCursorMove: bool = False
        self._lockTextChanged: bool = False

        self._find: Optional[ManuscriptFindWidget] = None

        vbox(self, 0, 0)

        self.textTitle = QLineEdit()
        self.textTitle.setProperty('transparent', True)
        self.textTitle.setFrame(False)
        self.textTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        apply_text_color(self.textTitle, QColor(PLACEHOLDER_TEXT_COLOR))
        self.textTitle.textEdited.connect(self._titleEdited)
        self.textTitle.returnPressed.connect(self.setFocus)

        self.wdgTitle = QWidget()
        hbox(self.wdgTitle, 0, 0).addWidget(self.textTitle)
        margins(self.wdgTitle, bottom=5)

        self.divider = DividerWidget()
        self.divider.setResource(resource_registry.top_frame1)
        self.divider.setMinimumHeight(95)
        effect = QGraphicsColorizeEffect(self.divider)
        effect.setColor(QColor(PLACEHOLDER_TEXT_COLOR))
        self.divider.setGraphicsEffect(effect)

        self.wdgEditor = QWidget()
        vbox(self.wdgEditor, 0, 0)
        margins(self.wdgEditor, left=20, top=20, bottom=50, right=15)

        self.wdgFrame = frame()
        vbox(self.wdgFrame, 0, 0)
        margins(self.wdgFrame, left=self._defaultMargins, right=self._defaultMargins, top=25)
        self.wdgFrame.setProperty('relaxed-white-bg', True)
        self.wdgFrame.setProperty('large-rounded', True)

        self.wdgFrame.layout().addWidget(self.divider)
        line_ = SeparatorLineWithShadow()
        self.wdgFrame.layout().addWidget(self.wdgTitle)
        self.wdgFrame.layout().addWidget(line_)
        self.wdgFrame.layout().addWidget(self.wdgEditor)

        self.layout().addWidget(self.wdgFrame)

        self.repo = RepositoryPersistenceManager.instance()

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, SceneChangedEvent):
            if self._scene == event.scene:
                if self._novel.prefs.is_scenes_organization():
                    self.textTitle.setText(self._scene.title)
                else:
                    self.textTitle.setText(self._scene.title_or_index(self._novel))
            for sceneLbl in self._sceneLabels:
                if sceneLbl.scene == event.scene:
                    sceneLbl.refresh()
        elif isinstance(event, SceneDeletedEvent):
            if self._scene and self._scene == event.scene:
                self.clear()
                self.cleared.emit()
            elif self._scenes and event.scene in self._scenes:
                removedLbl = None
                for lbl in self._sceneLabels:
                    if lbl.scene == event.scene:
                        removedLbl = lbl
                        break
                removedTextedit = None
                for textedit in self._textedits:
                    if textedit.scene() == event.scene:
                        removedTextedit = textedit
                        break
                if removedLbl:
                    self._sceneLabels.remove(removedLbl)
                    gc(removedLbl)
                if removedTextedit:
                    self._textedits.remove(removedTextedit)
                    gc(removedTextedit)
                self._scenes.remove(event.scene)
                self.textChanged.emit()
        elif isinstance(event, ScenesOrganizationResetEvent):
            self.clear()
            self.cleared.emit()

    @overrides
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        if self._maxContentWidth > 0:
            self._resizeToCharacterWidth()

        if event.size().width() < 600:
            margins(self.wdgFrame, left=self._minimumMargins, right=self._minimumMargins)
        elif self.wdgFrame.layout().contentsMargins().left() == self._minimumMargins:
            margins(self.wdgFrame, left=self._defaultMargins, right=self._defaultMargins)

    def defaultFont(self) -> QFont:
        if app_env.is_linux():
            return QFont('Palatino', 16)
        elif app_env.is_mac():
            return QFont('Palatino', 18)
        elif app_env.is_windows():
            return QFont('Georgia', 18)
        else:
            font = QApplication.font()
            font.setPointSize(16)
            return font

    def setNovel(self, novel: Novel):
        self._novel = novel

        if app_env.platform() in self._novel.prefs.manuscript.font.keys():
            fontSettings = self._getFontSettings()
            if fontSettings.family:
                self._font.setFamily(fontSettings.family)
            if fontSettings.font_size:
                self._font.setPointSize(fontSettings.font_size)
            if fontSettings.text_width:
                self.setCharacterWidth(fontSettings.text_width)
            else:
                self.setCharacterWidth(60)
            if fontSettings.line_space:
                self.setLineSpace(100 + 25 * fontSettings.line_space)
        else:
            self.setCharacterWidth(60)

        title_font = self.textTitle.font()
        title_font.setBold(True)
        title_font.setPointSize(32)
        title_font.setFamily(self._font.family())
        self.textTitle.setFont(title_font)

        event_dispatchers.instance(self._novel).register(self, SceneDeletedEvent, SceneChangedEvent,
                                                         ScenesOrganizationResetEvent)

    def scene(self) -> Optional[Scene]:
        return self._scene

    def setScene(self, scene: Scene):
        self.clear()
        self._scene = scene

        if self._novel.prefs.is_scenes_organization():
            self.textTitle.setText(self._scene.title)
            self.textTitle.setPlaceholderText('Scene title')
        else:
            self.textTitle.setText(self._scene.title_or_index(self._novel))
            self.textTitle.setPlaceholderText('Chapter title')
        self.textTitle.setReadOnly(False)

        wdg = self._initTextEdit(scene)
        self.wdgEditor.layout().addWidget(wdg)
        self.wdgEditor.layout().addWidget(vspacer())
        wdg.setFocus()

        self.activateFind()

    def chapter(self) -> Optional[Chapter]:
        return self._chapter

    def setChapterScenes(self, chapter: Chapter, scenes: List[Scene]):
        self.clear()
        self._chapter = chapter
        self._scenes.extend(scenes)

        self.textTitle.setText(chapter.display_name().replace('Chapter ', ''))
        self.textTitle.setPlaceholderText('Chapter')
        self.textTitle.setReadOnly(True)

        for scene in scenes:
            wdg = self._initTextEdit(scene)
            wdg.setPlaceholderText('Write this scene...')

            sceneLbl = SceneSeparator(scene)
            sceneLbl.clicked.connect(partial(self.sceneSeparatorClicked.emit, scene))
            self._sceneLabels.append(sceneLbl)
            self.wdgEditor.layout().addWidget(sceneLbl, alignment=Qt.AlignmentFlag.AlignRight)
            self.wdgEditor.layout().addWidget(wdg)

        if self._sceneLabels:
            self._sceneLabels[0].setHidden(True)

        self.wdgEditor.layout().addWidget(vspacer())
        self._textedits[0].setFocus()

        self.activateFind()

    def manuscriptFont(self) -> QFont:
        return self._font

    def setManuscriptFontPointSize(self, value: int):
        self._font.setPointSize(value)
        self._setFontForTextEdits()

    def setManuscriptFontFamily(self, family: str):
        self._font.setFamily(family)
        self._setFontForTextEdits()

    def characterWidth(self) -> int:
        return self._characterWidth

    def setCharacterWidth(self, width: int):
        self._characterWidth = width
        metrics = QtGui.QFontMetricsF(self.font())
        self._maxContentWidth = metrics.boundingRect('M' * self._characterWidth).width()
        self._resizeToCharacterWidth()

    def lineSpace(self) -> int:
        return self._lineSpace

    def setLineSpace(self, value: int):
        self._lineSpace = value
        for textedit in self._textedits:
            textedit.setBlockFormat(value, textIndent=DEFAULT_MANUSCRIPT_INDENT)
            textedit.applyBlockFormat()

    def refresh(self):
        if self._scene:
            self.setScene(self._scene)
        elif len(self._textedits) > 1:
            scenes = []
            scenes.extend(self._scenes)
            self.setChapterScenes(self._chapter, scenes)

    def clear(self):
        self._textedits.clear()
        self._sceneLabels.clear()
        self._scenes.clear()
        self._scene = None
        self._chapter = None
        clear_layout(self.wdgEditor)

    @overrides
    def setFocus(self) -> None:
        if self._textedits:
            self._textedits[0].setFocus()
        else:
            super().setFocus()

    def attachFindWidget(self, find: ManuscriptFindWidget):
        self._find = find

    def activateFind(self):
        if not self._find.isActive():
            self.resetFind()
            return

        for textedit in self._textedits:
            matches = self._find.sceneMathes(textedit.scene())
            self._lockTextChanged = True
            textedit.setHighlights(matches)
            self._lockTextChanged = False

    def resetFind(self):
        for textedit in self._textedits:
            textedit.clearHighlights()

    def setNightMode(self, mode: bool):
        if mode:
            self.wdgFrame.setFrameShape(QFrame.Shape.NoFrame)
            self.wdgFrame.setProperty('relaxed-white-bg', False)
            self.wdgFrame.setProperty('large-rounded', False)
            restyle(self.wdgFrame)
        else:
            self.wdgFrame.setFrameShape(QFrame.Shape.StyledPanel)
            self.wdgFrame.setProperty('relaxed-white-bg', True)
            self.wdgFrame.setProperty('large-rounded', True)
            restyle(self.wdgFrame)
        for lbl in self._sceneLabels:
            if mode:
                lbl.setStyleSheet(f'color: {RELAXED_WHITE_COLOR}; border: 0px; background-color: rgba(0, 0, 0, 0);')
            else:
                transparent(lbl)
            lbl.setDisabled(mode)

    def attachSettingsWidget(self, settings: ManuscriptEditorSettingsWidget):
        self._settings = settings
        self._settings.smartTypingSettings.dashChanged.connect(self._dashInsertionChanged)
        self._settings.smartTypingSettings.capitalizationChanged.connect(self._capitalizationChanged)
        self._settings.smartTypingSettings.smartQuotesChanged.connect(self._smartQuotesChanged)
        self._settings.smartTypingSettings.periodChanged.connect(self._periodChanged)
        self._settings.smartTypingSettings.ellipsisChanged.connect(self._ellipsisChanged)

        self._settings.fontSettings.sizeSetting.attach(self)
        self._settings.fontSettings.widthSetting.attach(self)
        self._settings.fontSettings.fontSetting.attach(self)
        self._settings.fontSettings.spaceSetting.attach(self)

        self._settings.fontSettings.sizeSetting.sizeChanged.connect(self._fontSizeChanged)
        self._settings.fontSettings.widthSetting.widthChanged.connect(self._textWidthChanged)
        self._settings.fontSettings.fontSetting.fontSelected.connect(self._fontChanged)
        self._settings.fontSettings.spaceSetting.spaceChanged.connect(self._spaceChanged)

    def statistics(self) -> TextStatistics:
        overall_stats = TextStatistics(0)
        if self.hasScenes():
            for editor in self._textedits:
                overall_stats.word_count += editor.statistics().word_count

        return overall_stats

    def asyncCheckGrammar(self):
        for textedit in self._textedits:
            textedit.setGrammarCheckEnabled(True)
            textedit.asyncCheckGrammar()

    def resetGrammarChecking(self):
        for textedit in self._textedits:
            textedit.setGrammarCheckEnabled(False)
            textedit.checkGrammar()

    def initSentenceHighlighter(self):
        for textedit in self._textedits:
            textedit.initSentenceHighlighter()

    def setSentenceHighlighterEnabled(self, enabled: bool):
        for textedit in self._textedits:
            textedit.setSentenceHighlighterEnabled(enabled)

    def clearSentenceHighlighter(self):
        for textedit in self._textedits:
            textedit.clearSentenceHighlighter()

    def hasScenes(self) -> bool:
        return len(self._textedits) > 0

    def selection(self) -> Optional[QTextDocumentFragment]:
        for textedit in self._textedits:
            if textedit.textCursor().hasSelection():
                return textedit.textCursor().selection()

    def jumpTo(self, start: int, end: int):
        if self._textedits:
            textedit = self._textedits[0]
            cursor = textedit.textCursor()
            self._lockCursorMove = True
            cursor.setPosition(start)
            textedit.setTextCursor(cursor)
            self._lockCursorMove = False

            QTimer.singleShot(50, lambda: self._cursorPositionChanged(textedit, marginY=300))

    def _textChanged(self, textedit: ManuscriptTextEdit, scene: Scene):
        if self._lockTextChanged:
            return
        if scene.manuscript.statistics is None:
            scene.manuscript.statistics = DocumentStatistics()

        wc = textedit.statistics().word_count
        updated_progress = self._updateProgress(scene, wc, ignoreDiff=textedit.isTextBeingPasted())

        scene.manuscript.content = textedit.toHtml()
        self.repo.update_doc(self._novel, scene.manuscript)
        if updated_progress:
            self.repo.update_scene(scene)
            self.repo.update_novel(self._novel)

        self.textChanged.emit()

        if self._find.isActive():
            QTimer.singleShot(25, lambda: self._updateFind(scene))

    def _updateProgress(self, scene: Scene, wc: int, ignoreDiff: bool = False) -> bool:
        if scene.manuscript.statistics.wc == wc:
            return False

        diff = wc - scene.manuscript.statistics.wc
        if not ignoreDiff:
            progress: DocumentProgress = daily_progress(scene)
            overall_progress = daily_overall_progress(self._novel)
            if diff > 0:
                progress.added += diff
                overall_progress.added += diff
            else:
                progress.removed += abs(diff)
                overall_progress.removed += abs(diff)
            self.progressChanged.emit(overall_progress)
        scene.manuscript.statistics.wc = wc

        return True

    def _cursorPositionChanged(self, textedit: ManuscriptTextEdit, marginX: int = 50, marginY: int = 50):
        if self._lockCursorMove:
            return
        rect = textedit.cursorRect(textedit.textCursor())
        pos = QPoint(rect.x(), rect.y())
        parent_pos = textedit.mapToParent(pos)
        parent_pos = self.wdgEditor.mapToParent(parent_pos)

        self.cursorPositionChanged.emit(parent_pos.x(), parent_pos.y(), marginX, marginY)

    def _initTextEdit(self, scene: Scene) -> ManuscriptTextEdit:
        _textedit = ManuscriptTextEdit(readOnly=self._novel.is_readonly())
        _textedit.setFont(self._font)
        _textedit.setDashInsertionMode(self._novel.prefs.manuscript.dash)
        _textedit.setAutoCapitalizationMode(self._novel.prefs.manuscript.capitalization)
        _textedit.setSmartQuotesEnabled(self._novel.prefs.manuscript.smart_quotes)
        _textedit.setPeriodInsertionEnabled(self._novel.prefs.manuscript.period)
        _textedit.setEllipsisInsertionMode(self._novel.prefs.manuscript.ellipsis)
        transparent(_textedit)

        _textedit.setBlockFormat(self._lineSpace, textIndent=DEFAULT_MANUSCRIPT_INDENT)
        _textedit.setAutoFormatting(QTextEdit.AutoFormattingFlag.AutoNone)
        _textedit.selectionChanged.connect(self.selectionChanged)
        _textedit.setProperty('borderless', True)

        _textedit.setPlaceholderText('Begin writing your story...')
        _textedit.setSidebarEnabled(False)
        _textedit.setDocumentMargin(0)

        _textedit.setScene(scene)
        _textedit.applyBlockFormat()
        _textedit.textChanged.connect(partial(self._textChanged, _textedit, scene))
        _textedit.cursorPositionChanged.connect(partial(self._cursorPositionChanged, _textedit))
        self._textedits.append(_textedit)

        return _textedit

    def _setFontForTextEdits(self):
        for textedit in self._textedits:
            textedit.setFont(self._font)
            textedit.resizeToContent()

    def _getFontSettings(self) -> FontSettings:
        if app_env.platform() not in self._novel.prefs.manuscript.font.keys():
            self._novel.prefs.manuscript.font[app_env.platform()] = FontSettings()
        return self._novel.prefs.manuscript.font[app_env.platform()]

    def _resizeToCharacterWidth(self):
        if 0 < self._maxContentWidth < self.width():
            margin = self.width() - self._maxContentWidth
        else:
            margin = 0

        margin = int(margin // 2)
        margins(self, left=margin, right=margin)

    def _dashInsertionChanged(self, mode: DashInsertionMode):
        for textedit in self._textedits:
            textedit.setDashInsertionMode(mode)
        self._novel.prefs.manuscript.dash = mode
        self.repo.update_novel(self._novel)

    def _capitalizationChanged(self, mode: AutoCapitalizationMode):
        for textedit in self._textedits:
            textedit.setAutoCapitalizationMode(mode)
        self._novel.prefs.manuscript.capitalization = mode
        self.repo.update_novel(self._novel)

    def _smartQuotesChanged(self, enabled: bool):
        for textedit in self._textedits:
            textedit.setSmartQuotesEnabled(enabled)
        self._novel.prefs.manuscript.smart_quotes = enabled
        self.repo.update_novel(self._novel)

    def _periodChanged(self, enabled: bool):
        for textedit in self._textedits:
            textedit.setPeriodInsertionEnabled(enabled)
        self._novel.prefs.manuscript.period = enabled
        self.repo.update_novel(self._novel)

    def _ellipsisChanged(self, mode: EllipsisInsertionMode):
        for textedit in self._textedits:
            textedit.setEllipsisInsertionMode(mode)
        self._novel.prefs.manuscript.ellipsis = mode
        self.repo.update_novel(self._novel)

    def _fontSizeChanged(self, size: int):
        fontSettings = self._getFontSettings()
        fontSettings.font_size = size
        self.repo.update_novel(self._novel)

    def _textWidthChanged(self, width: int):
        fontSettings = self._getFontSettings()
        fontSettings.text_width = width
        self.repo.update_novel(self._novel)

    def _fontChanged(self, family: str):
        fontSettings = self._getFontSettings()
        fontSettings.family = family

        titleFont = self.textTitle.font()
        titleFont.setFamily(family)
        self.textTitle.setFont(titleFont)

        self.repo.update_novel(self._novel)

    def _spaceChanged(self, value: int):
        fontSettings = self._getFontSettings()
        fontSettings.line_space = value
        self.repo.update_novel(self._novel)

    def _titleEdited(self, title: str):
        if self._scene:
            self._scene.title = title
            self.sceneTitleChanged.emit(self._scene)

    def _updateFind(self, scene: Scene):
        matches = self._find.updateScene(scene)
        for textedit in self._textedits:
            if textedit.scene() == scene:
                self._lockTextChanged = True
                textedit.setHighlights(matches)
                self._lockTextChanged = False
                break
