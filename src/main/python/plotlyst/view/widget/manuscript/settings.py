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

from PyQt6 import QtGui
from PyQt6.QtCore import pyqtSignal, QTimer, Qt, QSize
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QWidget, QFrame, QAbstractButton
from overrides import overrides
from qthandy import margins, vbox, decr_icon, pointy, vspacer, hbox, incr_font
from qtmenu import group
from qttextedit import DashInsertionMode
from qttextedit.api import AutoCapitalizationMode, EllipsisInsertionMode
from qttextedit.ops import FontSectionSettingWidget, FontSizeSectionSettingWidget, TextWidthSectionSettingWidget, \
    FontRadioButton, SliderSectionWidget
from qttextedit.util import EN_DASH, EM_DASH

from plotlyst.core.domain import Novel
from plotlyst.view.common import label, push_btn, \
    exclusive_buttons
from plotlyst.view.generated.manuscript_context_menu_widget_ui import Ui_ManuscriptContextMenuWidget
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.button import CollapseButton, SmallToggleButton
from plotlyst.view.widget.confirm import asked
from plotlyst.view.widget.display import IconText


class ManuscriptSpellcheckingSettingsWidget(QWidget, Ui_ManuscriptContextMenuWidget):
    languageChanged = pyqtSignal(str)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.novel = novel

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

    @overrides
    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        pass

    @overrides
    def sizeHint(self) -> QSize:
        return QSize(self.maximumWidth(), 500)

    def _changed(self, lang: str, checked: bool):
        if not checked:
            return
        self.lang = lang
        self._showShutdownOption()

    def _showShutdownOption(self):
        def confirm():
            if asked('To apply a new language, you have to close this novel.', 'Change language for spellcheck',
                     btnConfirmText='Shutdown now'):
                self.languageChanged.emit(self.lang)

        QTimer.singleShot(450, confirm)


class ManuscriptFontSettingWidget(FontSectionSettingWidget):

    @overrides
    def _activate(self):
        font_ = self._editor.manuscriptFont()
        for btn in self._btnGroupFonts.buttons():
            if btn.family() == font_.family():
                btn.setChecked(True)

    @overrides
    def _changeFont(self, btn: FontRadioButton, toggled):
        if toggled:
            self._editor.setManuscriptFontFamily(btn.family())


class LineSpaceSettingWidget(SliderSectionWidget):
    spaceChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__('Line Space', 0, 4, parent)

    @overrides
    def _activate(self):
        value = self._editor.lineSpace()
        value -= 100
        value //= 25
        self._slider.setValue(value)
        self._slider.valueChanged.connect(self._valueChanged)

    def _valueChanged(self, value: int):
        if self._editor is None:
            return
        self._editor.setLineSpace(100 + 25 * value)
        self.spaceChanged.emit(value)


class ManuscriptFontSizeSettingWidget(FontSizeSectionSettingWidget):

    @overrides
    def _activate(self):
        size = self._editor.manuscriptFont().pointSize()
        self._slider.setValue(size)
        self._slider.valueChanged.connect(self._valueChanged)

    @overrides
    def _valueChanged(self, value: int):
        if self._editor is None:
            return
        self._editor.setManuscriptFontPointSize(value)
        if self._editor.characterWidth():
            self._editor.setCharacterWidth(self._editor.characterWidth())

        self.sizeChanged.emit(value)


class ManuscriptTextSettingsWidget(QWidget):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        vbox(self)

        self.fontSetting = ManuscriptFontSettingWidget()
        self.sizeSetting = ManuscriptFontSizeSettingWidget()
        self.widthSetting = TextWidthSectionSettingWidget()
        self.spaceSetting = LineSpaceSettingWidget()

        self.layout().addWidget(self.fontSetting)
        self.layout().addWidget(self.sizeSetting)
        self.layout().addWidget(self.widthSetting)
        self.layout().addWidget(self.spaceSetting)


class ManuscriptSmartTypingSettingsWidget(QWidget):
    dashChanged = pyqtSignal(DashInsertionMode)
    capitalizationChanged = pyqtSignal(AutoCapitalizationMode)
    ellipsisChanged = pyqtSignal(EllipsisInsertionMode)
    smartQuotesChanged = pyqtSignal(bool)
    periodChanged = pyqtSignal(bool)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel
        vbox(self, spacing=1)

        self.smartQuotesSettings = self._addHeader('Smart quotes',
                                                   'Insert smart quotes when typing simple apostrophes and quotes')
        self.toggleSmartQuotes = self._addToggleSetting(self.smartQuotesSettings, icon='fa5s.quote-right')
        self.toggleSmartQuotes.setChecked(self.novel.prefs.manuscript.smart_quotes)
        self.toggleSmartQuotes.clicked.connect(self.smartQuotesChanged)

        self.wdgDashSettings = self._addHeader('Dash', 'Insert a dash automatically when typing double hyphens (--)')
        self.toggleEn = self._addToggleSetting(self.wdgDashSettings, f'En dash ({EN_DASH})')
        self.toggleEm = self._addToggleSetting(self.wdgDashSettings, f'Em dash ({EM_DASH})')
        self.btnGroupDash = exclusive_buttons(self.wdgDashSettings, self.toggleEn, self.toggleEm, optional=True)

        if self.novel.prefs.manuscript.dash == DashInsertionMode.INSERT_EN_DASH:
            self.toggleEn.setChecked(True)
        elif self.novel.prefs.manuscript.dash == DashInsertionMode.INSERT_EM_DASH:
            self.toggleEm.setChecked(True)
        self.btnGroupDash.buttonToggled.connect(self._dashToggled)

        self.wdgCapitalizationSettings = self._addHeader('Auto-capitalization',
                                                         'Auto-capitalize the first letter at paragraph or sentence level (experimental)')
        self.toggleParagraphCapital = self._addToggleSetting(self.wdgCapitalizationSettings, 'Paragraph')
        self.toggleSentenceCapital = self._addToggleSetting(self.wdgCapitalizationSettings, 'Sentence')
        self.btnGroupCapital = exclusive_buttons(self.wdgDashSettings, self.toggleParagraphCapital,
                                                 self.toggleSentenceCapital, optional=True)

        if self.novel.prefs.manuscript.capitalization == AutoCapitalizationMode.PARAGRAPH:
            self.toggleParagraphCapital.setChecked(True)
        elif self.novel.prefs.manuscript.capitalization == AutoCapitalizationMode.SENTENCE:
            self.toggleSentenceCapital.setChecked(True)
        self.btnGroupCapital.buttonToggled.connect(self._capitalizationToggled)

        self.ellipsisSettings = self._addHeader('Ellipsis',
                                                'Insert an ellipsis character when typing three consecutive periods')
        self.toggleEllipsis = self._addToggleSetting(self.ellipsisSettings, icon='fa5s.ellipsis-h')
        self.toggleEllipsis.setChecked(self.novel.prefs.manuscript.ellipsis == EllipsisInsertionMode.INSERT_ELLIPSIS)
        self.toggleEllipsis.clicked.connect(self._ellipsisToggled)

        self.periodSettings = self._addHeader('Period', 'Insert a period when typing two consecutive spaces')
        self.togglePeriod = self._addToggleSetting(self.periodSettings, icon='msc.debug-stackframe-dot')
        self.togglePeriod.setChecked(self.novel.prefs.manuscript.period)
        self.togglePeriod.clicked.connect(self.periodChanged)

        self.layout().addWidget(vspacer())

    def _addHeader(self, title: str, desc: str = '') -> QWidget:
        self.layout().addWidget(label(title, bold=True), alignment=Qt.AlignmentFlag.AlignLeft)
        wdgSettings = QWidget()
        vbox(wdgSettings, 0, 0)
        margins(wdgSettings, left=10)
        if desc:
            wdgSettings.layout().addWidget(label(desc, description=True, wordWrap=True, decr_font_diff=1),
                                           alignment=Qt.AlignmentFlag.AlignLeft)

        self.layout().addWidget(wdgSettings)
        return wdgSettings

    def _addToggleSetting(self, wdg: QWidget, text: str = '', icon: str = '') -> QAbstractButton:
        toggle = SmallToggleButton(translucent=False)
        lbl = IconText()
        lbl.setText(text)
        if icon:
            lbl.setIcon(IconRegistry.from_name(icon, 'grey'))
        wdg.layout().addWidget(group(lbl, toggle, spacing=0), alignment=Qt.AlignmentFlag.AlignRight)

        return toggle

    def _dashToggled(self):
        btn = self.btnGroupDash.checkedButton()
        if btn is None:
            self.dashChanged.emit(DashInsertionMode.NONE)
        elif btn is self.toggleEn:
            self.dashChanged.emit(DashInsertionMode.INSERT_EN_DASH)
        elif btn is self.toggleEm:
            self.dashChanged.emit(DashInsertionMode.INSERT_EM_DASH)

    def _capitalizationToggled(self):
        btn = self.btnGroupCapital.checkedButton()
        if btn is None:
            self.capitalizationChanged.emit(AutoCapitalizationMode.NONE)
        elif btn is self.toggleParagraphCapital:
            self.capitalizationChanged.emit(AutoCapitalizationMode.PARAGRAPH)
        elif btn is self.toggleSentenceCapital:
            self.capitalizationChanged.emit(AutoCapitalizationMode.SENTENCE)

    def _ellipsisToggled(self, toggled: bool):
        if toggled:
            self.ellipsisChanged.emit(EllipsisInsertionMode.INSERT_ELLIPSIS)
        else:
            self.ellipsisChanged.emit(EllipsisInsertionMode.NONE)


class EditorSettingsHeader(QFrame):
    def __init__(self, title: str, icon: str, widget: QWidget, parent=None):
        super().__init__(parent)
        self._widget = widget
        hbox(self, 0, 0)
        margins(self, 2, 5, 5, 5)
        self.setProperty('alt-bg', True)
        pointy(self)

        sectionTitle = push_btn(IconRegistry.from_name(icon), title, transparent_=True)
        incr_font(sectionTitle)
        self.btnCollapse = CollapseButton(checked=Qt.Edge.TopEdge)
        decr_icon(self.btnCollapse, 4)
        sectionTitle.clicked.connect(self.btnCollapse.click)

        self.layout().addWidget(sectionTitle, alignment=Qt.AlignmentFlag.AlignLeft)
        self._widget.setHidden(True)
        self.btnCollapse.toggled.connect(self._widget.setVisible)
        self.layout().addWidget(self.btnCollapse, alignment=Qt.AlignmentFlag.AlignRight)

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.btnCollapse.click()

    def setChecked(self, checked: bool = True):
        self.btnCollapse.setChecked(checked)
        self._widget.setVisible(checked)


class ManuscriptEditorSettingsWidget(QWidget):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        vbox(self)

        self.fontSettings = ManuscriptTextSettingsWidget(novel)
        self.smartTypingSettings = ManuscriptSmartTypingSettingsWidget(novel)
        self.langSelectionWidget = ManuscriptSpellcheckingSettingsWidget(novel)

        headerSettings = self._addSection('Editor settings', 'fa5s.font', self.fontSettings)
        headerSmart = self._addSection('Smart Typing', 'ri.double-quotes-r', self.smartTypingSettings)
        headerSpellcheck = self._addSection('Spellchecking', 'fa5s.spell-check', self.langSelectionWidget)
        exclusive_buttons(self, headerSettings.btnCollapse, headerSmart.btnCollapse, headerSpellcheck.btnCollapse,
                          optional=True)
        headerSettings.setChecked(True)
        self.layout().addWidget(vspacer())

    def _addSection(self, title: str, icon: str, widget: QWidget) -> EditorSettingsHeader:
        header = EditorSettingsHeader(title, icon, widget)

        self.layout().addWidget(header)
        self.layout().addWidget(widget)

        return header
