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
from functools import partial
from typing import Optional

import qtanim
from PyQt6 import QtGui
from PyQt6.QtCharts import QChart
from PyQt6.QtCore import pyqtSignal, QTimer, Qt, QRect, QDate, QPoint, QVariantAnimation, \
    QEasingCurve
from PyQt6.QtGui import QTextDocument, QColor, QTextFormat, QPainter, QTextOption, \
    QShowEvent, QIcon
from PyQt6.QtWidgets import QWidget, QCalendarWidget, QTableView, \
    QPushButton, QToolButton, QWidgetItem, QGraphicsColorizeEffect, QGraphicsTextItem, QHeaderView
from overrides import overrides
from qthandy import retain_when_hidden, translucent, margins, vbox, bold, vline, decr_font, \
    underline, transparent, italic, decr_icon, pointy, hbox
from qthandy.filter import OpacityEventFilter
from qtmenu import group
from qttextedit import TextBlockState
from textstat import textstat

from plotlyst.common import RELAXED_WHITE_COLOR, PLOTLYST_SECONDARY_COLOR, PLOTLYST_MAIN_COLOR, LIGHTGREY_ACTIVE_COLOR
from plotlyst.core.domain import Novel, DocumentProgress, SnapshotType
from plotlyst.core.text import wc, sentence_count, clean_text
from plotlyst.env import app_env
from plotlyst.service.manuscript import find_daily_overall_progress
from plotlyst.view.common import spin, ButtonPressResizeEventFilter, label, push_btn, \
    tool_btn
from plotlyst.view.generated.manuscript_lang_setting_ui import Ui_ManuscriptLangSettingWidget
from plotlyst.view.generated.readability_widget_ui import Ui_ReadabilityWidget
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.button import apply_button_palette_color
from plotlyst.view.widget.button import SnapshotButton
from plotlyst.view.widget.display import WordsDisplay, IconText, Emoji, ChartView
from plotlyst.view.widget.progress import ProgressChart


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
        vbox(self, spacing=0)

        self.btnSnapshot = SnapshotButton(self._novel, SnapshotType.Writing)

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

        self.layout().addWidget(self.btnSnapshot, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(group(self.btnDay, self.btnJumpToToday, margin=0))
        self.layout().addWidget(group(self.lblAdded, vline(), self.lblRemoved, margin=0, spacing=0),
                                alignment=Qt.AlignmentFlag.AlignRight)
        lbl = label('Added | Removed', description=True, decr_font_diff=2)
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
        self.lblAdded.setText(f'+{progress.added:,}')
        self.lblRemoved.setText(f'-{progress.removed:,}')


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

        self._initControlButton(item.widget().layout().itemAt(0), 'ei.circle-arrow-left')
        self._initDateButton(item.widget().layout().itemAt(2))
        self._initDateButton(item.widget().layout().itemAt(4))
        self._initControlButton(item.widget().layout().itemAt(6), 'ei.circle-arrow-right')

        widget = self.layout().itemAt(1).widget()
        if isinstance(widget, QTableView):
            widget.setStyleSheet(f'''
            QTableView {{
                selection-background-color: {RELAXED_WHITE_COLOR};
            }}
            QTableView::item:selected {{
                background: {RELAXED_WHITE_COLOR};
                color: black;
            }}
            ''')
            widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            widget.horizontalHeader().setMinimumSectionSize(20)
            widget.horizontalHeader().setDefaultSectionSize(25)

            widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            widget.verticalHeader().setMinimumSectionSize(20)
            widget.verticalHeader().setDefaultSectionSize(30)

        today = QDate.currentDate()
        self.setMaximumDate(today)

        self.setMaximumHeight(220)

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
                rad = min(rect.width(), rect.height()) // 2 - 1
                painter.drawEllipse(rect.center() + QPoint(1, 1), rad, rad)

            if date > self.maximumDate():
                painter.setPen(QColor(LIGHTGREY_ACTIVE_COLOR))
            else:
                painter.setPen(QColor('black'))
            painter.drawText(rect.toRectF(), str(date.day()), option)

    def _initControlButton(self, btnItem: QWidgetItem, icon: str):
        if btnItem and btnItem.widget() and isinstance(btnItem.widget(), QToolButton):
            btn = btnItem.widget()
            transparent(btn)
            pointy(btn)
            btn.setIcon(IconRegistry.from_name(icon, RELAXED_WHITE_COLOR))

    def _initDateButton(self, item: QWidgetItem):
        if item and item.widget() and isinstance(item.widget(), QToolButton):
            btn = item.widget()
            btn.setStyleSheet(f'''
                QToolButton {{
                    color: {RELAXED_WHITE_COLOR};
                    border: 0px;
                    background-color: rgba(0, 0, 0, 0);
                }}
                QToolButton:hover {{
                    background-color: {LIGHTGREY_ACTIVE_COLOR};
                }}
            ''')


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
