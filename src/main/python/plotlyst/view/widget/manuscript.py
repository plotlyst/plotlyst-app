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
import datetime
from functools import partial
from typing import Optional, List

import nltk
import qtanim
from PyQt5 import QtGui
from PyQt5.QtCore import QUrl, pyqtSignal, QTimer, Qt, QTextBoundaryFinder, QObject, QEvent, QMargins
from PyQt5.QtGui import QFont, QTextDocument, QTextCharFormat, QColor, QTextBlock, QSyntaxHighlighter, QKeyEvent, \
    QMouseEvent, QResizeEvent
from PyQt5.QtMultimedia import QSoundEffect
from PyQt5.QtWidgets import QWidget, QTextEdit, QApplication, QSizePolicy
from nltk import WhitespaceTokenizer
from overrides import overrides
from qthandy import retain_when_hidden, opaque, btn_popup, transparent, clear_layout, vbox
from textstat import textstat

from src.main.python.plotlyst.common import RELAXED_WHITE_COLOR
from src.main.python.plotlyst.core.client import json_client
from src.main.python.plotlyst.core.domain import Novel, Scene, TextStatistics, DocumentStatistics
from src.main.python.plotlyst.core.sprint import TimerModel
from src.main.python.plotlyst.core.text import wc, sentence_count, clean_text
from src.main.python.plotlyst.env import app_env
from src.main.python.plotlyst.resources import resource_registry
from src.main.python.plotlyst.service.persistence import RepositoryPersistenceManager
from src.main.python.plotlyst.view.common import scroll_to_top, spin, \
    OpacityEventFilter, scrolled
from src.main.python.plotlyst.view.generated.distraction_free_manuscript_editor_ui import \
    Ui_DistractionFreeManuscriptEditor
from src.main.python.plotlyst.view.generated.manuscript_context_menu_widget_ui import Ui_ManuscriptContextMenuWidget
from src.main.python.plotlyst.view.generated.readability_widget_ui import Ui_ReadabilityWidget
from src.main.python.plotlyst.view.generated.sprint_widget_ui import Ui_SprintWidget
from src.main.python.plotlyst.view.generated.timer_setup_widget_ui import Ui_TimerSetupWidget
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.widget.display import WordsDisplay
from src.main.python.plotlyst.view.widget.input import TextEditBase, GrammarHighlighter, GrammarHighlightStyle


class TimerSetupWidget(QWidget, Ui_TimerSetupWidget):
    def __init__(self, parent=None):
        super(TimerSetupWidget, self).__init__(parent)
        self.setupUi(self)

    def value(self) -> int:
        return self.sbTimer.value() * 60


class SprintWidget(QWidget, Ui_SprintWidget):
    def __init__(self, parent=None):
        super(SprintWidget, self).__init__(parent)
        self.setupUi(self)
        self._model = None
        self._compact: bool = False
        self.setModel(TimerModel())

        self._toggleState(False)

        self.btnTimer.setIcon(IconRegistry.timer_icon())
        self.btnReset.setIcon(IconRegistry.restore_alert_icon('#9b2226'))
        self._timer_setup = TimerSetupWidget()
        btn_popup(self.btnTimer, self._timer_setup)

        self._timer_setup.btnStart.clicked.connect(self.start)
        self.btnPause.clicked.connect(self._pauseStartTimer)
        self.btnReset.clicked.connect(self._reset)

        self._effect: Optional[QSoundEffect] = None

    def model(self) -> TimerModel:
        return self._model

    def setModel(self, model: TimerModel):
        self._model = model
        self._model.valueChanged.connect(self._updateTimer)
        self._model.finished.connect(self._finished)
        self._toggleState(self._model.isActive())

    def setCompactMode(self, compact: bool):
        self._compact = compact
        self._toggleState(self.model().isActive())
        self.time.setStyleSheet(f'border: 0px; color: {RELAXED_WHITE_COLOR}; background-color: rgba(0,0,0,0);')

    def start(self):
        self._toggleState(True)
        self._model.start(self._timer_setup.value())
        self._updateTimer()
        self.btnTimer.menu().hide()

    def _toggleState(self, running: bool):
        self.time.setVisible(running)
        if running:
            self.btnPause.setChecked(True)
            self.btnPause.setIcon(IconRegistry.pause_icon())
        if self._compact:
            self.btnTimer.setHidden(running)
            retain_when_hidden(self.btnPause)
            retain_when_hidden(self.btnReset)
            self.btnPause.setHidden(True)
            self.btnReset.setHidden(True)
        else:
            self.btnPause.setVisible(running)
            self.btnReset.setVisible(running)

    def _updateTimer(self):
        mins, secs = self._model.remainingTime()
        time = datetime.time(minute=mins, second=secs)
        self.time.setTime(time)

    def _pauseStartTimer(self, played: bool):
        self.model().toggle()
        if played:
            self.btnPause.setIcon(IconRegistry.pause_icon())
        else:
            self.btnPause.setIcon(IconRegistry.play_icon())

    def _reset(self):
        self.model().stop()
        self._toggleState(False)

    def _finished(self):
        if self._effect is None:
            self._effect = QSoundEffect()
            self._effect.setSource(QUrl.fromLocalFile(resource_registry.cork))
            self._effect.setVolume(0.3)
        self._effect.play()


class ManuscriptContextMenuWidget(QWidget, Ui_ManuscriptContextMenuWidget):
    languageChanged = pyqtSignal(str)

    def __init__(self, novel: Novel, parent=None):
        super(ManuscriptContextMenuWidget, self).__init__(parent)
        self.setupUi(self)
        self.novel = novel

        self.wdgShutDown.setHidden(True)

        self.btnArabicIcon.setIcon(IconRegistry.from_name('mdi.abjad-arabic'))

        self.cbEnglish.clicked.connect(partial(self._changed, 'en-US'))
        self.cbEnglishBritish.clicked.connect(partial(self._changed, 'en-GB'))
        self.cbEnglishCanadian.clicked.connect(partial(self._changed, 'en-CA'))
        self.cbEnglishAustralian.clicked.connect(partial(self._changed, 'en-AU'))
        self.cbEnglishNewZealand.clicked.connect(partial(self._changed, 'en-NZ'))
        self.cbEnglishSouthAfrican.clicked.connect(partial(self._changed, 'en-ZA'))
        self.cbSpanish.clicked.connect(partial(self._changed, 'es'))
        self.cbPortugese.clicked.connect(partial(self._changed, 'pt-PT'))
        self.cbPortugeseBrazil.clicked.connect(partial(self._changed, 'pt-BR'))
        self.cbPortugeseAngola.clicked.connect(partial(self._changed, 'pt-AO'))
        self.cbPortugeseMozambique.clicked.connect(partial(self._changed, 'pt-MZ'))
        self.cbFrench.clicked.connect(partial(self._changed, 'fr'))
        self.cbGerman.clicked.connect(partial(self._changed, 'de-DE'))
        self.cbGermanAustrian.clicked.connect(partial(self._changed, 'de-AT'))
        self.cbGermanSwiss.clicked.connect(partial(self._changed, 'de-CH'))
        self.cbChinese.clicked.connect(partial(self._changed, 'zh-CN'))
        self.cbArabic.clicked.connect(partial(self._changed, 'ar'))
        self.cbDanish.clicked.connect(partial(self._changed, 'da-DK'))
        self.cbDutch.clicked.connect(partial(self._changed, 'nl'))
        self.cbDutchBelgian.clicked.connect(partial(self._changed, 'nl-BE'))
        self.cbGreek.clicked.connect(partial(self._changed, 'el-GR'))
        self.cbIrish.clicked.connect(partial(self._changed, 'ga-IE'))
        self.cbItalian.clicked.connect(partial(self._changed, 'it'))
        self.cbJapanese.clicked.connect(partial(self._changed, 'ja-JP'))
        self.cbNorwegian.clicked.connect(partial(self._changed, 'no'))
        self.cbPersian.clicked.connect(partial(self._changed, 'fa'))
        self.cbPolish.clicked.connect(partial(self._changed, 'pl-PL'))
        self.cbRomanian.clicked.connect(partial(self._changed, 'ro-RO'))
        self.cbRussian.clicked.connect(partial(self._changed, 'ru-RU'))
        self.cbSlovak.clicked.connect(partial(self._changed, 'sk-SK'))
        self.cbSlovenian.clicked.connect(partial(self._changed, 'sl-SI'))
        self.cbSwedish.clicked.connect(partial(self._changed, 'sv'))
        self.cbTagalog.clicked.connect(partial(self._changed, 'tl-PH'))
        self.cbUkrainian.clicked.connect(partial(self._changed, 'uk-UA'))

        self.lang: str = self.novel.lang_settings.lang

        if self.lang == 'es':
            self.cbSpanish.setChecked(True)
        elif self.lang == 'en-US':
            self.cbEnglish.setChecked(True)
        elif self.lang == 'en-GB':
            self.cbEnglishBritish.setChecked(True)
        elif self.lang == 'en-CA':
            self.cbEnglishCanadian.setChecked(True)
        elif self.lang == 'en-AU':
            self.cbEnglishAustralian.setChecked(True)
        elif self.lang == 'en-NZ':
            self.cbEnglishNewZealand.setChecked(True)
        elif self.lang == 'en-ZA':
            self.cbEnglishSouthAfrican.setChecked(True)
        elif self.lang == 'fr':
            self.cbFrench.setChecked(True)
        elif self.lang == 'de-DE':
            self.cbGerman.setChecked(True)
        elif self.lang == 'de-AT':
            self.cbGermanAustrian.setChecked(True)
        elif self.lang == 'de-CH':
            self.cbGermanSwiss.setChecked(True)
        elif self.lang == 'pt-PT':
            self.cbPortugese.setChecked(True)
        elif self.lang == 'pt-BR':
            self.cbPortugeseBrazil.setChecked(True)
        elif self.lang == 'pt-AO':
            self.cbPortugeseAngola.setChecked(True)
        elif self.lang == 'pt-MZ':
            self.cbPortugeseMozambique.setChecked(True)
        elif self.lang == 'zh-CN':
            self.cbChinese.setChecked(True)
        elif self.lang == 'ar':
            self.cbArabic.setChecked(True)
        elif self.lang == 'da-DK':
            self.cbDanish.setChecked(True)
        elif self.lang == 'nl':
            self.cbDutch.setChecked(True)
        elif self.lang == 'nl-BE':
            self.cbDutchBelgian.setChecked(True)
        elif self.lang == 'el-GR':
            self.cbGreek.setChecked(True)
        elif self.lang == 'ga-IE':
            self.cbIrish.setChecked(True)
        elif self.lang == 'it':
            self.cbItalian.setChecked(True)
        elif self.lang == 'ja-JP':
            self.cbJapanese.setChecked(True)
        elif self.lang == 'no':
            self.cbNorwegian.setChecked(True)
        elif self.lang == 'fa':
            self.cbPersian.setChecked(True)
        elif self.lang == 'pl-PL':
            self.cbPolish.setChecked(True)
        elif self.lang == 'ro-RO':
            self.cbRomanian.setChecked(True)
        elif self.lang == 'ru-RU':
            self.cbRussian.setChecked(True)
        elif self.lang == 'sk-SK':
            self.cbSlovak.setChecked(True)
        elif self.lang == 'sl-SI':
            self.cbSlovenian.setChecked(True)
        elif self.lang == 'sv':
            self.cbSwedish.setChecked(True)
        elif self.lang == 'tl-PH':
            self.cbTagalog.setChecked(True)
        elif self.lang == 'uk-UA':
            self.cbUkrainian.setChecked(True)

        self.btnShutDown.clicked.connect(self._languageChanged)

    @overrides
    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        pass

    def _changed(self, lang: str, checked: bool):
        if not checked:
            return
        self.lang = lang
        if self.wdgShutDown.isHidden():
            QTimer.singleShot(200, self._showShutdownOption)
        else:
            qtanim.glow(self.btnShutDown, loop=2)

    def _showShutdownOption(self):
        scroll_to_top(self.scrollArea)
        self.wdgShutDown.setVisible(True)
        qtanim.fade_in(self.lblShutdownHint, duration=150)
        qtanim.glow(self.btnShutDown, loop=3)

    def _languageChanged(self):
        self.btnShutDown.setText('Shutting down ...')
        self.lblShutdownHint.setHidden(True)
        spin(self.btnShutDown, color='white')
        qtanim.glow(self.btnShutDown, loop=15)

        self.languageChanged.emit(self.lang)


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


class NightModeHighlighter(QSyntaxHighlighter):
    def __init__(self, textedit: QTextEdit):
        super(NightModeHighlighter, self).__init__(textedit.document())

        self._nightFormat = QTextCharFormat()
        self._nightFormat.setForeground(QColor('#edf6f9'))

    @overrides
    def highlightBlock(self, text: str) -> None:
        self.setFormat(0, len(text), self._nightFormat)


class WordTagHighlighter(QSyntaxHighlighter):
    def __init__(self, textedit: QTextEdit):
        super(WordTagHighlighter, self).__init__(textedit.document())

        self._adverbFormat = QTextCharFormat()
        self._adverbFormat.setBackground(QColor('#0a9396'))
        self.tokenizer = WhitespaceTokenizer()

    @overrides
    def highlightBlock(self, text: str) -> None:
        span_generator = self.tokenizer.span_tokenize(text)
        spans = [x for x in span_generator]
        tokens = self.tokenizer.tokenize(text)
        tags = nltk.pos_tag(tokens)

        for i, pos_tag in enumerate(tags):
            if pos_tag[1] == 'RB':
                if len(spans) > i:
                    self.setFormat(spans[i][0], spans[i][1] - spans[i][0], self._adverbFormat)


class ManuscriptTextEdit(TextEditBase):
    def __init__(self, parent=None, topBorder: bool = False):
        super(ManuscriptTextEdit, self).__init__(parent)
        self.highlighter = GrammarHighlighter(self.document(), checkEnabled=False,
                                              highlightStyle=GrammarHighlightStyle.BACKGOUND)
        self._minHeight = 60
        self._topBorder = topBorder

        self._sentenceHighlighter: Optional[SentenceHighlighter] = None
        self._nightModeHighlighter: Optional[NightModeHighlighter] = None
        self._wordTagHighlighter: Optional[WordTagHighlighter] = None

        if app_env.is_mac():
            family = 'Palatino'
            self.setFontFamily(family)
            self.document().setDefaultFont(QFont(family, 16))

        self._setDefaultStyleSheet()
        self.textChanged.connect(self.resizeToContent)

    @overrides
    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        self.resizeToContent()

    @overrides
    def resizeEvent(self, event: QResizeEvent):
        super(ManuscriptTextEdit, self).resizeEvent(event)
        self.resizeToContent()

    def resizeToContent(self):
        margins: QMargins = self.viewportMargins()
        self.setMinimumHeight(
            max(self._minHeight, self.document().size().height()) + margins.top() + margins.bottom() + 5)

    def setGrammarCheckEnabled(self, enabled: bool):
        self.highlighter.setCheckEnabled(enabled)

    def checkGrammar(self):
        self.highlighter.rehighlight()

    def asyncCheckGrammer(self):
        self.highlighter.asyncRehighlight()

    def clearHighlights(self):
        if self._sentenceHighlighter is not None:
            self._sentenceHighlighter.deleteLater()
            self._sentenceHighlighter = None
        if self._nightModeHighlighter is not None:
            self._nightModeHighlighter.deleteLater()
            self._nightModeHighlighter = None
            self._setDefaultStyleSheet()
        if self._wordTagHighlighter is not None:
            self._wordTagHighlighter.deleteLater()
            self._wordTagHighlighter = None

    def setNightModeEnabled(self, enabled: bool):
        self.clearHighlights()
        if enabled:
            transparent(self)
            self._nightModeHighlighter = NightModeHighlighter(self)

    def setSentenceHighlighterEnabled(self, enabled: bool):
        self.clearHighlights()
        if enabled:
            self._sentenceHighlighter = SentenceHighlighter(self)

    def setWordTagHighlighterEnabled(self, enabled: bool):
        self.clearHighlights()
        if enabled:
            self._wordTagHighlighter = WordTagHighlighter(self)

    def _setDefaultStyleSheet(self):
        border = 2 if self._topBorder else 0
        self.setStyleSheet(
            f'QTextEdit {{border-top: {border}px dashed grey; background-color: {RELAXED_WHITE_COLOR};}}')


class ManuscriptTextEditor(QWidget):
    textChanged = pyqtSignal()
    selectionChanged = pyqtSignal(ManuscriptTextEdit)

    def __init__(self, parent=None):
        super(ManuscriptTextEditor, self).__init__(parent)
        vbox(self, 0, 0)
        self._scrollArea, self._scrollWidget = scrolled(self, frameless=True)
        self._scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        vbox(self._scrollWidget, 0, 0)

        self._editors: List[ManuscriptTextEdit] = []

        self.repo = RepositoryPersistenceManager.instance()

    def setGrammarCheckEnabled(self, enabled: bool):
        for editor in self._editors:
            editor.setGrammarCheckEnabled(enabled)

    def checkGrammar(self):
        for editor in self._editors:
            editor.checkGrammar()

    def asyncCheckGrammer(self):
        for editor in self._editors:
            editor.asyncCheckGrammer()

    def setScene(self, scene: Scene):
        self.clear()
        self._addScene(scene)

    def setChapterScenes(self, scenes: List[Scene]):
        self.clear()
        for i, scene in enumerate(scenes):
            self._addScene(scene, topBorder=i > 0)

    def clear(self):
        clear_layout(self._scrollWidget.layout())
        self._editors.clear()

    def _addScene(self, scene, topBorder: bool = False):
        if not scene.manuscript.loaded:
            json_client.load_document(app_env.novel, scene.manuscript)

        editor = ManuscriptTextEdit(self, topBorder=topBorder)
        editor.setText(scene.manuscript.content)
        editor.setFormat(130, textIndent=20)
        editor.setFontPointSize(16)
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        editor.resizeToContent()
        editor.textChanged.connect(partial(self._textChanged, scene, editor))
        editor.selectionChanged.connect(partial(self.selectionChanged.emit, editor))
        self._editors.append(editor)
        self._scrollWidget.layout().addWidget(editor)

    def documents(self) -> List[QTextDocument]:
        return [x.document() for x in self._editors]

    def statistics(self) -> TextStatistics:
        if self._editors:
            return self._editors[0].statistics()

    def setMargins(self, left: int, top: int, right: int, bottom: int):
        if not self._editors:
            return

        if len(self._editors) > 1:
            for editor in self._editors:
                editor.setViewportMargins(left, 0, right, 0)
            self._editors[0].setViewportMargins(left, top, right, 0)
            self._editors[-1].setViewportMargins(left, 0, right, bottom)
        else:
            self._editors[0].setViewportMargins(left, top, right, bottom)

    def setNightModeEnabled(self, enabled: bool):
        for editor in self._editors:
            editor.setNightModeEnabled(enabled)

    def setSentenceHighlighterEnabled(self, enabled: bool):
        for editor in self._editors:
            editor.setSentenceHighlighterEnabled(enabled)

    def setWordTagHighlighterEnabled(self, enabled: bool):
        for editor in self._editors:
            editor.setWordTagHighlighterEnabled(enabled)

    @overrides
    def setFocus(self):
        if self._editors:
            self._editors[0].setFocus()

    def setVerticalScrollBarPolicy(self, policy):
        self._scrollArea.setVerticalScrollBarPolicy(policy)

    def installEventFilterOnEditors(self, filter):
        for editor in self._editors:
            editor.installEventFilter(filter)

    def removeEventFilterFromEditors(self, filter):
        for editor in self._editors:
            editor.removeEventFilter(filter)

    def _textChanged(self, scene: Scene, editor: ManuscriptTextEdit):
        wc = editor.statistics().word_count
        doc = scene.manuscript
        if doc.statistics is None:
            doc.statistics = DocumentStatistics()

        if doc.statistics.wc != wc:
            doc.statistics.wc = wc
            self.repo.update_scene(scene)

        scene.manuscript.content = editor.toHtml()
        self.repo.update_doc(app_env.novel, scene.manuscript)

        self.textChanged.emit()


class ReadabilityWidget(QWidget, Ui_ReadabilityWidget):
    def __init__(self, parent=None):
        super(ReadabilityWidget, self).__init__(parent)
        self.setupUi(self)

        self.btnRefresh.setIcon(IconRegistry.from_name('ei.refresh', 'darkBlue'))
        self.btnRefresh.installEventFilter(OpacityEventFilter(parent=self.btnRefresh))
        retain_when_hidden(self.btnRefresh)
        self.btnRefresh.setHidden(True)
        self._docs: List[QTextDocument] = []
        self.btnRefresh.clicked.connect(lambda: self.checkTextDocuments(self._docs))

    def checkTextDocuments(self, docs: List[QTextDocument]):
        if not docs:
            return

        doc = docs[0]
        spin(self.btnResult)

        text = doc.toPlainText()
        cleaned_text = clean_text(text)
        score = textstat.flesch_reading_ease(cleaned_text)
        self.btnResult.setToolTip(f'Flesch–Kincaid readability score: {score}')

        if score >= 80:
            self.btnResult.setIcon(IconRegistry.from_name('mdi.alpha-a-circle-outline', color='#2d6a4f'))
            result_text = 'Very easy to read' if score >= 90 else 'Easy to read'
            self.lblResult.setText(f'<i style="color:#2d6a4f">{result_text}</i>')
        elif score >= 60:
            self.btnResult.setIcon(IconRegistry.from_name('mdi.alpha-b-circle-outline', color='#52b788'))
            result_text = 'Fairly easy to read. 7th grade' if score >= 70 else 'Fairly easy to read. 8-9th grade'
            self.lblResult.setText(f'<i style="color:#52b788">{result_text}</i>')
        elif score >= 50:
            self.btnResult.setIcon(IconRegistry.from_name('mdi.alpha-c-circle-outline', color='#f77f00'))
            self.lblResult.setText('<i style="color:#f77f00">Fairly difficult to read. 10-12th grade</i>')
        elif score >= 30:
            self.btnResult.setIcon(IconRegistry.from_name('mdi.alpha-d-circle-outline', color='#bd1f36'))
            self.lblResult.setText('<i style="color:#bd1f36">Difficult to read</i>')
        else:
            self.btnResult.setIcon(IconRegistry.from_name('mdi.alpha-e-circle-outline', color='#85182a'))
            self.lblResult.setText('<i style="color:#85182a">Very difficult to read</i>')

        sentences_count = 0
        for i in range(doc.blockCount()):
            block = doc.findBlockByNumber(i)
            block_text = block.text()
            if block_text:
                sentences_count += sentence_count(block_text)

        if not sentences_count:
            sentence_length = 0
        else:
            sentence_length = wc(text) / sentences_count
        self.lblAvgSentenceLength.setText("%.2f" % round(sentence_length, 1))

        self.btnRefresh.setHidden(True)

    def setTextDocumentsUpdated(self, docs: List[QTextDocument], updated: bool = True):
        if not docs:
            return
        self._docs.clear()
        self._docs.extend(docs)
        if updated:
            if not self.btnRefresh.isVisible():
                anim = qtanim.fade_in(self.btnRefresh)
                anim.finished.connect(lambda: opaque(self.btnRefresh, 0.4))
        else:
            if self.btnRefresh.isVisible():
                qtanim.fade_out(self.btnRefresh)


class DistractionFreeManuscriptEditor(QWidget, Ui_DistractionFreeManuscriptEditor):
    exitRequested = pyqtSignal()

    def __init__(self, parent=None):
        super(DistractionFreeManuscriptEditor, self).__init__(parent)
        self.setupUi(self)
        self.editor: Optional[ManuscriptTextEditor] = None
        self.lblWords: Optional[WordsDisplay] = None

        self.sliderDocWidth.valueChanged.connect(
            lambda x: self.wdgDistractionFreeEditor.layout().setContentsMargins(self.width() / 3 - x, 0,
                                                                                self.width() / 3 - x, 0))
        self.wdgSprint = SprintWidget(self)
        self.wdgSprint.setCompactMode(True)
        self.wdgHeader.layout().insertWidget(0, self.wdgSprint, alignment=Qt.AlignLeft)

        self.wdgDistractionFreeEditor.installEventFilter(self)
        self.wdgBottom.installEventFilter(self)
        self.btnReturn.setIcon(IconRegistry.from_name('mdi.arrow-collapse', 'white'))
        self.btnReturn.clicked.connect(self.exitRequested.emit)
        self.btnFocus.setIcon(IconRegistry.from_name('mdi.credit-card', color_on='darkBlue'))
        self.btnFocus.toggled.connect(self._toggle_manuscript_focus)
        self.btnTypewriterMode.setIcon(IconRegistry.from_name('mdi.typewriter', color_on='darkBlue'))
        self.btnTypewriterMode.toggled.connect(self._toggle_typewriter_mode)
        self.btnNightMode.setIcon(IconRegistry.from_name('mdi.weather-night', color_on='darkBlue'))
        self.btnNightMode.toggled.connect(self._toggle_manuscript_night_mode)
        self.btnWordCount.setIcon(IconRegistry.from_name('mdi6.counter', color_on='darkBlue'))
        self.btnWordCount.clicked.connect(self._wordCountClicked)

    def activate(self, editor: ManuscriptTextEditor, timer: Optional[TimerModel] = None):
        self.editor = editor
        self.editor.installEventFilterOnEditors(self)
        clear_layout(self.wdgDistractionFreeEditor.layout())
        if timer and timer.isActive():
            self.wdgSprint.setModel(timer)
            self.wdgSprint.setVisible(True)
        else:
            self.wdgSprint.setHidden(True)
        self.wdgDistractionFreeEditor.layout().addWidget(self.editor)
        self.editor.setFocus()
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.wdgBottom.setVisible(True)
        self.sliderDocWidth.setMaximum(self.width() / 3)
        if self.sliderDocWidth.value() <= 2:
            self.sliderDocWidth.setValue(self.sliderDocWidth.maximum() // 2)

        self._toggle_manuscript_focus(self.btnFocus.isChecked())
        self._toggle_manuscript_night_mode(self.btnNightMode.isChecked())
        self._toggle_typewriter_mode(self.btnTypewriterMode.isChecked())
        self._wordCountClicked(self.btnWordCount.isChecked())
        self.setMouseTracking(True)
        self.wdgDistractionFreeEditor.setMouseTracking(True)
        QTimer.singleShot(3000, self._autoHideBottomBar)

    def deactivate(self):
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.editor.removeEventFilterFromEditors(self)
        self.editor.setMargins(30, 30, 30, 30)
        self._toggle_manuscript_focus(False)
        self._toggle_manuscript_night_mode(False)
        self.editor = None
        self.setMouseTracking(False)
        self.wdgDistractionFreeEditor.setMouseTracking(False)

    def setWordDisplay(self, words: WordsDisplay):
        self.lblWords = words
        self.wdgHeader.layout().addWidget(self.lblWords, alignment=Qt.AlignRight)
        self.lblWords.setStyleSheet(f'color: {RELAXED_WHITE_COLOR}')
        self._wordCountClicked(self.btnWordCount.isChecked())

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.wdgBottom and event.type() == QEvent.Leave:
            self.wdgBottom.setHidden(True)
        if event.type() == QEvent.MouseMove and isinstance(event, QMouseEvent):
            if self.wdgBottom.isHidden() and event.pos().y() > self.height() - 15:
                self.wdgBottom.setVisible(True)
        return super().eventFilter(watched, event)

    @overrides
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            if self.editor is not None:
                self.exitRequested.emit()
        event.accept()

    @overrides
    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.wdgBottom.isHidden() and event.pos().y() > self.height() - 15:
            self.wdgBottom.setVisible(True)

    def _wordCountClicked(self, checked: bool):
        if self.lblWords:
            self.lblWords.setVisible(checked)

    def _toggle_manuscript_focus(self, toggled: bool):
        if toggled:
            if self.btnNightMode.isChecked():
                self.btnNightMode.setChecked(False)
        self.editor.setSentenceHighlighterEnabled(toggled)

    def _toggle_manuscript_night_mode(self, toggled: bool):
        if toggled:
            if self.btnFocus.isChecked():
                self.btnFocus.setChecked(False)
        self.editor.setNightModeEnabled(toggled)

    def _toggle_typewriter_mode(self, toggled: bool):
        if toggled:
            self.editor.setMargins(30, 30, 30, QApplication.desktop().height() // 2)
        else:
            self.editor.setMargins(30, 30, 30, 30)

    def _autoHideBottomBar(self):
        if not self.wdgBottom.underMouse():
            self.wdgBottom.setHidden(True)
