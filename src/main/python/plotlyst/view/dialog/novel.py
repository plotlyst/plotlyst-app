"""
Plotlyst
Copyright (C) 2021-2023  Zsolt Kovari

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
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QDialog, QPushButton, QDialogButtonBox, QApplication
from overrides import overrides
from qthandy import flow, decr_font, decr_icon, pointy
from qthandy.filter import DisabledClickEventFilter, OpacityEventFilter

from src.main.python.plotlyst.common import PLOTLYST_SECONDARY_COLOR
from src.main.python.plotlyst.core.domain import NovelDescriptor, PlotValue, Novel
from src.main.python.plotlyst.core.help import plot_value_help
from src.main.python.plotlyst.view.common import link_editor_to_btn, ButtonPressResizeEventFilter, set_tab_icon
from src.main.python.plotlyst.view.dialog.utility import IconSelectorDialog
from src.main.python.plotlyst.view.generated.novel_creation_dialog_ui import Ui_NovelCreationDialog
from src.main.python.plotlyst.view.generated.plot_value_editor_dialog_ui import Ui_PlotValueEditorDialog
from src.main.python.plotlyst.view.generated.synopsis_editor_dialog_ui import Ui_SynopsisEditorDialog
from src.main.python.plotlyst.view.icons import IconRegistry


class NovelEditionDialog(QDialog, Ui_NovelCreationDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

    def display(self, novel: Optional[NovelDescriptor] = None) -> Optional[str]:
        if novel:
            self.lineTitle.setText(novel.title)
        result = self.exec()
        if result == QDialog.DialogCode.Rejected:
            return None
        return self.lineTitle.text()


DEFAULT_VALUE_ICON = 'fa5s.chevron-circle-down'


class _TemplatePlotValueButton(QPushButton):
    def __init__(self, value: PlotValue, parent=None):
        super(_TemplatePlotValueButton, self).__init__(parent)
        self.setText(value.text)
        if value.negative:
            self.setToolTip(f'{value.text} vs. {value.negative}')
        else:
            self.setToolTip(value.text)
        if value.icon:
            self.setIcon(IconRegistry.from_name(value.icon, value.icon_color))
        else:
            self.setIcon(IconRegistry.from_name(DEFAULT_VALUE_ICON, value.icon_color))

        decr_font(self)
        decr_icon(self)

        self.setStyleSheet(f'''
            QPushButton {{
                border: 2px solid {value.icon_color};
                border-radius: 12px;
                padding: 4px;
            }}
            QPushButton:pressed {{
                border: 3px solid {value.icon_color};
            }}
        ''')
        self.installEventFilter(OpacityEventFilter(self, leaveOpacity=0.6))
        self.installEventFilter(ButtonPressResizeEventFilter(self))
        pointy(self)


love_value = PlotValue('Love', negative='Hate', icon='ei.heart', icon_color='#d1495b')
life_value = PlotValue('Life', negative='Death', icon='mdi.pulse', icon_color='#ef233c')
truth_value = PlotValue('Truth', negative='Lie', icon='mdi.scale-balance', icon_color='#5390d9')
wealth_value = PlotValue('Wealth', negative='Poverty', icon='fa5s.hand-holding-usd', icon_color='#e9c46a')
justice_value = PlotValue('Justice', negative='Injustice', icon='fa5s.gavel', icon_color='#a68a64')
maturity_value = PlotValue('Maturity', negative='Immaturity', icon='fa5s.seedling', icon_color='#95d5b2')
esteem_value = PlotValue('Esteem', negative='Disrespect', icon='mdi.account-star', icon_color='#f72585')
morality_value = PlotValue('Morality', negative='Immorality', icon='ph.scales-bold', icon_color='#560bad')
loyalty_value = PlotValue('Loyalty', negative='Betrayal', icon='fa5.handshake', icon_color='#5390d9')
empathy_value = PlotValue('Empathy', icon_color='#FFB6C1')
survival_value = PlotValue('Survival', icon_color='#F4A460')
power_value = PlotValue('Power', icon_color='#FF0000')
freedom_value = PlotValue('Freedom', icon_color='#023e8a')
unity_value = PlotValue('Unity', icon_color='#52b69a')

popular_plot_value_templates = [
    love_value,
    life_value,
    truth_value,
    survival_value,
    wealth_value,
    justice_value,
    maturity_value,
    esteem_value,
    morality_value,
    loyalty_value,
    freedom_value
]
foundational_plot_value_templates = [
    love_value,
    life_value,
    truth_value,
    survival_value,
    power_value,
    PlotValue('Victory', icon_color='#ffbe0b'),
    freedom_value

]
societal_plot_value_templates = [
    justice_value,
    unity_value,
    wealth_value,
    PlotValue('Poverty', icon_color='#8B4513'),
    PlotValue('Prejudice', icon_color='#800000'),
    PlotValue('Ethics', icon_color='#008000'),
    PlotValue('Tradition', icon_color='#A0522D'),
    PlotValue('Tolerance', icon_color='#FFD700'),
    PlotValue('Diversity', icon_color='#800080'),
    PlotValue('Innovation', icon_color='#5e548e'),
    PlotValue('Education', icon_color='#008080'),
]
relational_plot_value_templates = [
    love_value,
    PlotValue('Trust', icon_color='#34a0a4'),
    PlotValue('Friendship', icon_color='#457b9d'),
    PlotValue('Cooperation', icon_color='#32CD32'),
    PlotValue('Communication', icon_color='#000080'),
    power_value,
    unity_value,
    loyalty_value,
    PlotValue('Responsibility', icon_color='#FF4500'),
    PlotValue('Respect', icon_color='#FFFF00'),
    empathy_value,
    PlotValue('Duty', icon_color='#696969'),
    PlotValue('Forgiveness', icon_color='#FF1493')
]

personal_plot_value_templates = [
    PlotValue('Honor', negative='Dishonor', icon='fa5s.award', icon_color='#40916c'),
    PlotValue('Success', icon_color='#FFD700'),
    PlotValue('Kindness', icon_color='#FFC0CB'),
    PlotValue('Goodness', icon_color='#FF69B4'),
    morality_value,
    maturity_value,
    esteem_value,

    PlotValue('Meaning', icon_color='#8A2BE2'),
    PlotValue('Self-respect', icon_color='#B0C4DE'),
    PlotValue('Courage', icon_color='#ca6702'),
    PlotValue('Resilience', icon_color='#2E8B57'),
    PlotValue('Independence', icon_color='#20B2AA'),
    empathy_value,
    PlotValue('Compassion', icon_color='#FF4500'),
    PlotValue('Patience', icon_color='#FFA500'),
    PlotValue('Wisdom', icon_color='#000080'),
    PlotValue('Gratitude', icon_color='#DAA520'),
    PlotValue('Humility', icon_color='#a9def9'),
    PlotValue('Integrity', icon_color='#000000'),
    PlotValue('Perseverance', icon_color='#800000'),
]


class PlotValueEditorDialog(QDialog, Ui_PlotValueEditorDialog):
    def __init__(self, parent=None):
        super(PlotValueEditorDialog, self).__init__(parent)
        self.setupUi(self)

        self._value: Optional[PlotValue] = None

        self.subtitle.setHint(plot_value_help)

        decr_icon(self.btnIcon, 2)
        self.btnIcon.clicked.connect(self._changeIcon)

        for tab in [self.tabPopular, self.tabFoundational, self.tabSocietal, self.tabPersonal,
                    self.tabRelational]:
            flow(tab, margin=15, spacing=6)

        set_tab_icon(self.tabWidget, self.tabPopular,
                     IconRegistry.from_name('fa5s.star', color_on=PLOTLYST_SECONDARY_COLOR))
        set_tab_icon(self.tabWidget, self.tabFoundational,
                     IconRegistry.from_name('fa5s.cube', color_on=PLOTLYST_SECONDARY_COLOR))
        set_tab_icon(self.tabWidget, self.tabSocietal,
                     IconRegistry.from_name('mdi.account-group', color_on=PLOTLYST_SECONDARY_COLOR))
        set_tab_icon(self.tabWidget, self.tabPersonal,
                     IconRegistry.from_name('mdi.head-heart-outline', color_on=PLOTLYST_SECONDARY_COLOR))
        set_tab_icon(self.tabWidget, self.tabRelational,
                     IconRegistry.from_name('fa5s.people-arrows', color_on=PLOTLYST_SECONDARY_COLOR))

        for pair in [(self.tabPopular, popular_plot_value_templates),
                     (self.tabFoundational, foundational_plot_value_templates),
                     (self.tabSocietal, societal_plot_value_templates),
                     (self.tabPersonal, personal_plot_value_templates),
                     (self.tabRelational, relational_plot_value_templates)]:
            tab, values = pair
            for value in values:
                btn = _TemplatePlotValueButton(value)
                tab.layout().addWidget(btn)
                btn.clicked.connect(partial(self._fillTemplate, value))

        btnOk = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        btnOk.setEnabled(False)
        btnOk.installEventFilter(DisabledClickEventFilter(btnOk, lambda: qtanim.shake(self.linePositive)))
        link_editor_to_btn(self.linePositive, btnOk)

    def display(self, reference: Optional[PlotValue] = None) -> Optional[PlotValue]:
        self._value = PlotValue('', icon=DEFAULT_VALUE_ICON, icon_color='grey')
        if reference:
            self._fillTemplate(reference)
            self.linePositive.setFocus()
        else:
            self.btnIcon.setIcon(IconRegistry.from_name(self._value.icon, self._value.icon_color))

        result = self.exec()
        if result == QDialog.DialogCode.Accepted:
            self._value.text = self.linePositive.text()
            return self._value

    def _fillTemplate(self, value: PlotValue):
        self.linePositive.setText(value.text)
        if value.icon:
            icon = value.icon
        else:
            icon = DEFAULT_VALUE_ICON

        self.btnIcon.setIcon(IconRegistry.from_name(icon, value.icon_color))
        self._value.icon = icon
        self._value.icon_color = value.icon_color
        self.btnIcon.setBorderColor(self._value.icon_color)

        if self.isVisible():
            glow_color = QColor(value.icon_color)
            qtanim.glow(self.linePositive, color=glow_color)
            qtanim.glow(self.btnIcon, color=glow_color)

    def _changeIcon(self):
        result = IconSelectorDialog().display()
        if result:
            self._value.icon = result[0]
            self._value.icon_color = result[1].name()
            self.btnIcon.setIcon(IconRegistry.from_name(self._value.icon, self._value.icon_color))
            self.btnIcon.setBorderColor(self._value.icon_color)


class SynopsisEditorDialog(QDialog, Ui_SynopsisEditorDialog):
    def __init__(self, novel: Novel, parent=None):
        super(SynopsisEditorDialog, self).__init__(parent)
        self.setupUi(self)
        self._novel = novel

        self.textSynopsis.setPlaceholderText("Write down your story's main events")
        self.textSynopsis.setMargins(0, 10, 0, 10)
        self.textSynopsis.setGrammarCheckEnabled(False)

        self.textSynopsis.setToolbarVisible(False)
        self.textSynopsis.setTitleVisible(False)

        self.textSynopsis.setText(novel.synopsis.content)

    def synopsis(self) -> str:
        return self.textSynopsis.textEdit.toHtml()

    @overrides
    def show(self) -> None:
        screen = QApplication.screenAt(self.pos())
        if screen:
            self.resize(screen.size().width(), screen.size().height())
        else:
            self.resize(600, 500)
        super().show()

    # @staticmethod
    # def display(novel: Novel) -> str:
    #     dialog = SynopsisEditorDialog()
    #     dialog.textSynopsis.setText(novel.synopsis.content)
    #
    #     screen = QApplication.screenAt(dialog.pos())
    #     if screen:
    #         dialog.resize(screen.size().width(), screen.size().height())
    #     else:
    #         dialog.resize(600, 500)
    #
    #     dialog.show()
    #
    #     return dialog.textSynopsis.textEdit.toHtml()
