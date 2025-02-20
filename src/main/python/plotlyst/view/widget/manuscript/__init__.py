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
import datetime
from functools import partial
from typing import Optional, List

import qtanim
from PyQt6 import QtGui
from PyQt6.QtCharts import QChart
from PyQt6.QtCore import QUrl, pyqtSignal, QTimer, Qt, QRect, QDate, QPoint, QVariantAnimation, \
    QEasingCurve
from PyQt6.QtGui import QTextDocument, QColor, QTextFormat, QPainter, QTextOption, \
    QShowEvent, QIcon
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import QWidget, QLineEdit, QCalendarWidget, QTableView, \
    QPushButton, QToolButton, QWidgetItem, QGraphicsColorizeEffect, QGraphicsTextItem
from overrides import overrides
from qthandy import retain_when_hidden, translucent, margins, vbox, bold, vline, decr_font, \
    underline, transparent, italic, decr_icon, pointy, hbox
from qthandy.filter import OpacityEventFilter
from qtmenu import MenuWidget, group
from qttextedit import TextBlockState
from textstat import textstat

from plotlyst.common import RELAXED_WHITE_COLOR, PLOTLYST_SECONDARY_COLOR, PLOTLYST_MAIN_COLOR
from plotlyst.core.domain import Novel, Scene, DocumentProgress
from plotlyst.core.sprint import TimerModel
from plotlyst.core.text import wc, sentence_count, clean_text
from plotlyst.env import app_env
from plotlyst.resources import resource_registry
from plotlyst.service.manuscript import find_daily_overall_progress
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import spin, ButtonPressResizeEventFilter, label, push_btn, \
    tool_btn
from plotlyst.view.generated.manuscript_lang_setting_ui import Ui_ManuscriptLangSettingWidget
from plotlyst.view.generated.readability_widget_ui import Ui_ReadabilityWidget
from plotlyst.view.generated.sprint_widget_ui import Ui_SprintWidget
from plotlyst.view.generated.timer_setup_widget_ui import Ui_TimerSetupWidget
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.button import apply_button_palette_color
from plotlyst.view.widget.display import WordsDisplay, IconText, Emoji, ChartView
from plotlyst.view.widget.input import TextEditorBase
from plotlyst.view.widget.progress import ProgressChart


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
        transparent(self.time)
        transparent(self.btnPause)
        transparent(self.btnReset)

        self.btnTimer.setIcon(IconRegistry.timer_icon())
        self.btnPause.installEventFilter(OpacityEventFilter(self.btnPause, leaveOpacity=0.7))
        self.btnPause.installEventFilter(ButtonPressResizeEventFilter(self.btnPause))
        self.btnReset.setIcon(IconRegistry.restore_alert_icon('#ED6868'))
        self.btnReset.installEventFilter(OpacityEventFilter(self.btnReset, leaveOpacity=0.7))
        self.btnReset.installEventFilter(ButtonPressResizeEventFilter(self.btnReset))

        self._timer_setup = TimerSetupWidget()
        self._menu = MenuWidget(self.btnTimer)
        self._menu.addWidget(self._timer_setup)

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
        self._menu.close()

    def _toggleState(self, running: bool):
        self.time.setVisible(running)
        if running:
            self.btnPause.setChecked(True)
            self.btnPause.setIcon(IconRegistry.pause_icon(color='grey'))
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
            self.btnPause.setIcon(IconRegistry.pause_icon(color='grey'))
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


class ManuscriptLanguageSettingWidget(QWidget, Ui_ManuscriptLangSettingWidget):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.novel = novel

        self.btnArabicIcon.setIcon(IconRegistry.from_name('mdi.abjad-arabic'))

        self.cbEnglish.clicked.connect(partial(self._changed, 'en-US'))
        self.cbEnglish.setChecked(True)
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

    def _changed(self, lang: str, checked: bool):
        if not checked:
            return
        self.novel.lang_settings.lang = lang


# class NightModeHighlighter(QSyntaxHighlighter):
#     def __init__(self, textedit: QTextEdit):
#         super().__init__(textedit.document())
#
#         self._nightFormat = QTextCharFormat()
#         self._nightFormat.setForeground(QColor(RELAXED_WHITE_COLOR))
#
#     @overrides
#     def highlightBlock(self, text: str) -> None:
#         self.setFormat(0, len(text), self._nightFormat)


# class WordTagHighlighter(QSyntaxHighlighter):
#     def __init__(self, textedit: QTextEdit):
#         super().__init__(textedit.document())
#
#         self._adverbFormat = QTextCharFormat()
#         self._adverbFormat.setBackground(QColor('#0a9396'))
#         self.tokenizer = WhitespaceTokenizer()
#
#     @overrides
#     def highlightBlock(self, text: str) -> None:
#         span_generator = self.tokenizer.span_tokenize(text)
#         spans = [x for x in span_generator]
#         tokens = self.tokenizer.tokenize(text)
#         tags = nltk.pos_tag(tokens)
#
#         for i, pos_tag in enumerate(tags):
#             if pos_tag[1] == 'RB':
#                 if len(spans) > i:
#                     self.setFormat(spans[i][0], spans[i][1] - spans[i][0], self._adverbFormat)


SceneSeparatorTextFormat = QTextFormat.FormatType.UserFormat + 9999
SceneSeparatorTextFormatPrefix = 'scene:/'


# class SceneSeparatorTextObject(QObject, QTextObjectInterface):
#     def __init__(self, textedit: ManuscriptTextEdit):
#         super(SceneSeparatorTextObject, self).__init__(textedit)
#         self._textedit = textedit
#         self._scenes: Dict[str, Scene] = {}
#
#     def setScenes(self, scenes: List[Scene]):
#         self._scenes.clear()
#         for scene in scenes:
#             self._scenes[str(scene.id)] = scene
#
#     def sceneTitle(self, id_str: str) -> str:
#         if id_str in self._scenes.keys():
#             return self._scenes[id_str].title or 'Scene'
#         else:
#             return 'Scene'
#
#     def sceneSynopsis(self, id_str: str) -> str:
#         if id_str in self._scenes.keys():
#             return self._scenes[id_str].synopsis
#         else:
#             return ''
#
#     def scene(self, id_str: str) -> Optional[Scene]:
#         return self._scenes.get(id_str)
#
#     @overrides
#     def intrinsicSize(self, doc: QTextDocument, posInDocument: int, format_: QTextFormat) -> QSizeF:
#         metrics = QFontMetrics(self._textedit.font())
#         return QSizeF(350, metrics.boundingRect('W').height())
#
#     @overrides
#     def drawObject(self, painter: QPainter, rect: QRectF, doc: QTextDocument, posInDocument: int,
#                    format_: QTextFormat) -> None:
#         match = doc.find(OBJECT_REPLACEMENT_CHARACTER, posInDocument)
#         if match:
#             anchor = match.charFormat().anchorHref()
#             if anchor:
#                 painter.setPen(Qt.GlobalColor.lightGray)
#                 scene_id = anchor.replace(SceneSeparatorTextFormatPrefix, "")
#                 painter.drawText(rect, f'~{self.sceneTitle(scene_id)}~')


class ManuscriptTextEditor(TextEditorBase):
    textChanged = pyqtSignal()
    selectionChanged = pyqtSignal()
    sceneTitleChanged = pyqtSignal(Scene)
    progressChanged = pyqtSignal(DocumentProgress)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._novel: Optional[Novel] = None
        self._scenes: List[Scene] = []

        self._textTitle = QLineEdit()
        self._textTitle.setProperty('transparent', True)
        self._textTitle.setFrame(False)
        self._textTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = self._textedit.font()
        title_font.setBold(True)
        title_font.setPointSize(32)
        self._textTitle.setFont(title_font)
        self._textTitle.returnPressed.connect(self.textEdit.setFocus)
        self._textTitle.textEdited.connect(self._titleChanged)
        self._wdgTitle = group(self._textTitle, margin=0, spacing=0)
        self._wdgTitle.setProperty('relaxed-white-bg', True)
        margins(self._wdgTitle, left=20)

        self.layout().insertWidget(1, self._wdgTitle, alignment=Qt.AlignmentFlag.AlignTop)

        self.repo = RepositoryPersistenceManager.instance()

    def refresh(self):
        if len(self._scenes) == 1:
            self.setScene(self._scenes[0])
        elif len(self._scenes) > 1:
            self.setScenes(self._scenes, self._textTitle.text())

    def setViewportMargins(self, left: int, top: int, right: int, bottom: int):
        self.textEdit.setViewportMargins(left, top, right, bottom)

    def setMargins(self, left: int, top: int, right: int, bottom: int):
        self.textEdit.setViewportMargins(left, top, right, bottom)


class ReadabilityWidget(QWidget, Ui_ReadabilityWidget):
    def __init__(self, parent=None):
        super(ReadabilityWidget, self).__init__(parent)
        self.setupUi(self)

        self.btnRefresh.setIcon(IconRegistry.refresh_icon())
        self.btnRefresh.installEventFilter(OpacityEventFilter(parent=self.btnRefresh))
        self.btnRefresh.installEventFilter(ButtonPressResizeEventFilter(self.btnRefresh))
        retain_when_hidden(self.btnRefresh)
        self.btnRefresh.setHidden(True)
        self._updatedDoc: Optional[QTextDocument] = None
        self.btnRefresh.clicked.connect(lambda: self.checkTextDocument(self._updatedDoc))

    def checkTextDocument(self, doc: QTextDocument):
        text = doc.toPlainText()
        cleaned_text = clean_text(text)
        word_count = wc(text)
        spin(self.btnResult)
        if word_count < 30:
            msg = 'Text is too short for calculating readability score'
            self.btnResult.setToolTip(msg)
            self.btnResult.setIcon(IconRegistry.from_name('ei.question'))
            self.lblResult.setText(f'<i style="color:grey">{msg}</i>')
        else:
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
            if block.userState() == TextBlockState.UNEDITABLE.value:
                continue
            block_text = block.text()
            if block_text:
                sentences_count += sentence_count(block_text)

        if not sentences_count:
            sentence_length = 0
        else:
            sentence_length = word_count / sentences_count
        self.lblAvgSentenceLength.setText("%.2f" % round(sentence_length, 1))

        self.btnRefresh.setHidden(True)

    def setTextDocumentUpdated(self, doc: QTextDocument, updated: bool = True):
        self._updatedDoc = doc
        if updated:
            if not self.btnRefresh.isVisible():
                anim = qtanim.fade_in(self.btnRefresh)
                if not app_env.test_env():
                    anim.finished.connect(lambda: translucent(self.btnRefresh, 0.4))
        else:
            if self.btnRefresh.isVisible():
                qtanim.fade_out(self.btnRefresh)


class ManuscriptProgressChart(ProgressChart):
    def __init__(self, novel: Novel, parent=None):
        self.novel = novel
        super().__init__(maxValue=self.novel.manuscript_goals.target_wc,
                         color=PLOTLYST_SECONDARY_COLOR,
                         titleColor=PLOTLYST_SECONDARY_COLOR,
                         emptySliceColor=RELAXED_WHITE_COLOR, parent=parent)

        self.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.setAnimationDuration(700)
        self.setAnimationEasingCurve(QEasingCurve.Type.InQuad)

        self._holeSize = 0.6
        self._titleVisible = False


class ManuscriptProgressWidget(QWidget):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel
        vbox(self)

        self._wordCount: int = 0

        self.wdgGoalTitle = QWidget()
        hbox(self.wdgGoalTitle, 0)

        self.emojiGoal = Emoji(emoji='bullseye')
        effect = QGraphicsColorizeEffect()
        effect.setColor(QColor(PLOTLYST_MAIN_COLOR))
        self.emojiGoal.setGraphicsEffect(effect)
        self.lblGoal = WordsDisplay()
        tooltip = 'Manuscript word count target'
        self.emojiGoal.setToolTip(tooltip)
        self.lblGoal.setToolTip(tooltip)
        self.btnEditGoal = tool_btn(IconRegistry.edit_icon('grey'), transparent_=True,
                                    tooltip="Edit manuscript word count goal")
        decr_icon(self.btnEditGoal, 2)

        self.chartProgress = ManuscriptProgressChart(self.novel)
        self.chartProgressView = ChartView()
        self.chartProgressView.setMaximumSize(200, 200)
        self.chartProgressView.setChart(self.chartProgress)
        self.chartProgressView.scale(1.05, 1.05)
        self.percentageItem = QGraphicsTextItem()
        font = self.percentageItem.font()
        font.setBold(True)
        font.setPointSize(16)
        self.percentageItem.setFont(font)
        self.percentageItem.setDefaultTextColor(QColor(PLOTLYST_SECONDARY_COLOR))
        self.percentageItem.setTextWidth(200)
        text_option = QTextOption()
        text_option.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.percentageItem.document().setDefaultTextOption(text_option)
        self.counterAnimation = QVariantAnimation()
        self.counterAnimation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.counterAnimation.setDuration(500)
        self.counterAnimation.valueChanged.connect(self._updatePercentageText)
        self.counterAnimation.finished.connect(self._counterAnimationFinished)
        self._animation_started = False

        scene = self.chartProgressView.scene()
        scene.addItem(self.percentageItem)

        self.percentageItem.setPos(0,
                                   self.chartProgressView.chart().plotArea().center().y() - self.percentageItem.boundingRect().height() / 2)

        self.wdgGoalTitle.layout().addWidget(self.emojiGoal)
        self.wdgGoalTitle.layout().addWidget(self.lblGoal)
        self.wdgGoalTitle.layout().addWidget(self.btnEditGoal)

        self.layout().addWidget(self.wdgGoalTitle, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.chartProgressView)

    def setMaxValue(self, value: int):
        self.lblGoal.setWordCount(value)
        self.chartProgress.setMaxValue(value)
        self.chartProgress.setValue(self._wordCount)
        self._refresh()

    def setValue(self, value: int):
        self._wordCount = value
        self.chartProgress.setValue(value)
        self._refresh()

    @overrides
    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        if not self._animation_started:
            self.counterAnimation.setStartValue(0)
            self.counterAnimation.setEndValue(self.chartProgress.percentage())
            QTimer.singleShot(200, self.counterAnimation.start)
            self.percentageItem.setPlainText('')
            self._animation_started = True

    def _refresh(self):
        self.chartProgress.refresh()

        if self.isVisible():
            self.percentageItem.setPlainText(f'{self.chartProgress.percentage()}%')

    def _updatePercentageText(self, value: int):
        self.percentageItem.setPlainText(f"{value}%")

    def _counterAnimationFinished(self):
        self._animation_started = False


def date_to_str(date: QDate) -> str:
    return date.toString(Qt.DateFormat.ISODate)


class ManuscriptDailyProgress(QWidget):
    jumpToToday = pyqtSignal()

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        vbox(self)

        self.btnDay = IconText()
        self.btnDay.setText('Today')
        self.btnDay.setIcon(IconRegistry.from_name('mdi.calendar-month-outline'))

        self.btnJumpToToday = push_btn(IconRegistry.from_name('fa5s.arrow-right'), 'Jump to today', transparent_=True)
        retain_when_hidden(self.btnJumpToToday)
        italic(self.btnJumpToToday)
        self.btnJumpToToday.installEventFilter(OpacityEventFilter(self.btnJumpToToday, enterOpacity=0.7))
        decr_icon(self.btnJumpToToday, 3)
        decr_font(self.btnJumpToToday, 3)
        self.btnJumpToToday.clicked.connect(self.jumpToToday)

        self.lblAdded = label('', color=PLOTLYST_SECONDARY_COLOR, h3=True)
        self.lblRemoved = label('', color='grey', h3=True)

        self.layout().addWidget(group(self.btnDay, self.btnJumpToToday))
        self.layout().addWidget(group(self.lblAdded, vline(), self.lblRemoved), alignment=Qt.AlignmentFlag.AlignRight)
        lbl = label('Added/Removed', description=True)
        decr_font(lbl)
        self.layout().addWidget(lbl, alignment=Qt.AlignmentFlag.AlignRight)

    def refresh(self):
        self.setDate(QDate.currentDate())

    def setDate(self, date: QDate):
        date_str = date_to_str(date)
        if date == QDate.currentDate():
            self.btnDay.setText('Today')
            self.btnJumpToToday.setHidden(True)
        else:
            self.btnDay.setText(date_str[5:].replace('-', '/'))
            self.btnJumpToToday.setVisible(True)

        progress = find_daily_overall_progress(self._novel, date_str)
        if progress:
            self.setProgress(progress)
        else:
            self.lblAdded.setText('+')
            self.lblRemoved.setText('-')

    def setProgress(self, progress: DocumentProgress):
        self.lblAdded.setText(f'+{progress.added}')
        self.lblRemoved.setText(f'-{progress.removed}')


class ManuscriptProgressCalendar(QCalendarWidget):
    dayChanged = pyqtSignal(QDate)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel

        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.NoHorizontalHeader)
        self.setNavigationBarVisible(True)
        self.setSelectionMode(QCalendarWidget.SelectionMode.SingleSelection)
        self.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        item = self.layout().itemAt(0)
        item.widget().setStyleSheet(f'.QWidget {{background-color: {PLOTLYST_SECONDARY_COLOR};}}')

        self._initButton(item.widget().layout().itemAt(0), 'ei.circle-arrow-left')
        self._initButton(item.widget().layout().itemAt(6), 'ei.circle-arrow-right')

        widget = self.layout().itemAt(1).widget()
        if isinstance(widget, QTableView):
            widget.setStyleSheet(f'''
            QTableView {{
                selection-background-color: {RELAXED_WHITE_COLOR};
            }}
            ''')
            widget.horizontalHeader().setMinimumSectionSize(20)
            widget.verticalHeader().setMinimumSectionSize(20)

        today = QDate.currentDate()
        self.setMaximumDate(today)

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        if QDate.currentDate() != self.maximumDate():
            self.setMaximumDate(QDate.currentDate())
            self.showToday()
        super().showEvent(event)

    @overrides
    def showToday(self) -> None:
        super().showToday()
        self.setSelectedDate(QDate.currentDate())
        self.dayChanged.emit(self.maximumDate())

    @overrides
    def paintCell(self, painter: QtGui.QPainter, rect: QRect, date: QDate) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if date.month() == self.monthShown():
            option = QTextOption()
            option.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bold(painter, date == self.selectedDate())
            underline(painter, date == self.selectedDate())

            progress = find_daily_overall_progress(self._novel, date_to_str(date))
            if progress:
                painter.setPen(QColor('#BB90CE'))
                if progress.added + progress.removed >= 1500:
                    painter.setBrush(QColor('#C8A4D7'))
                elif progress.added + progress.removed >= 450:
                    painter.setBrush(QColor('#EDE1F2'))
                else:
                    painter.setBrush(QColor(RELAXED_WHITE_COLOR))
                rad = rect.width() // 2 - 1
                painter.drawEllipse(rect.center() + QPoint(1, 1), rad, rad)

            if date > self.maximumDate():
                painter.setPen(QColor('grey'))
            else:
                painter.setPen(QColor('black'))
            painter.drawText(rect.toRectF(), str(date.day()), option)

    def _initButton(self, btnItem: QWidgetItem, icon: str):
        if btnItem and btnItem.widget() and isinstance(btnItem.widget(), QToolButton):
            btn = btnItem.widget()
            transparent(btn)
            pointy(btn)
            btn.setIcon(IconRegistry.from_name(icon, RELAXED_WHITE_COLOR))


class ManuscriptProgressCalendarLegend(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        vbox(self)
        margins(self, left=15)

        self.layout().addWidget(self._legend(IconRegistry.from_name('fa5.square', color='#BB90CE'), '1+ words'),
                                alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self._legend(IconRegistry.from_name('fa5s.square', color='#EDE1F2'), '450+ words'),
                                alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self._legend(IconRegistry.from_name('fa5s.square', color='#C8A4D7'), '1500+ words'),
                                alignment=Qt.AlignmentFlag.AlignLeft)

    def _legend(self, icon: QIcon, text: str) -> QPushButton:
        legend = IconText()
        apply_button_palette_color(legend, 'grey')
        legend.setIcon(icon)
        legend.setText(text)

        return legend
