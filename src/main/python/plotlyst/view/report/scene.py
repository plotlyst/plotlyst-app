from typing import Optional, Dict

from PyQt6.QtCharts import QPieSeries, QPieSlice
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QToolTip, QWidget, QPushButton, QFrame, QTextEdit
from overrides import overrides
from qthandy import vbox, hbox, sp, translucent, flow, clear_layout, incr_icon

from plotlyst.common import PLACEHOLDER_TEXT_COLOR
from plotlyst.core.domain import Novel, Character, Tier, Conflict, ConflictType
from plotlyst.core.text import html
from plotlyst.env import app_env
from plotlyst.service.cache import acts_registry, entities_registry
from plotlyst.view.common import icon_to_html_img, columns, rows, wrap, label
from plotlyst.view.icons import avatars, IconRegistry
from plotlyst.view.report import AbstractReport
from plotlyst.view.widget.chart import BaseChart, ActDistributionChart
from plotlyst.view.widget.display import PremiumOverlayWidget, IconText
from plotlyst.view.widget.structure.selector import ActSelectorButtons


class SceneReport(AbstractReport):

    def __init__(self, novel: Novel, parent=None):
        super(SceneReport, self).__init__(novel, parent, setupUi=False)
        vbox(self)

        self.wdgDistributions = columns()
        self.wdgPov = rows(0, 0)
        self.chartViewPovDistribution = self._newChartView(self.largeSize)
        self._povChart = PovDistributionChart()
        self.chartViewPovDistribution.setChart(self._povChart)
        self.actSelector = ActSelectorButtons(novel)
        self.wdgPov.layout().addWidget(self.actSelector, alignment=Qt.AlignmentFlag.AlignCenter)
        self.wdgPov.layout().addWidget(self.chartViewPovDistribution)
        self.actSelector.actToggled.connect(self._povChart.toggleAct)

        self.chartViewActDistribution = self._newChartView(self.largeSize)
        self._actChart = ActDistributionChart()
        self.chartViewActDistribution.setChart(self._actChart)

        self.wdgDistributions.layout().addWidget(wrap(self.chartViewActDistribution, margin_top=35))
        self.wdgDistributions.layout().addWidget(self.wdgPov)

        self.conflictDisplay = ConflictSTierDisplay()

        self.layout().addWidget(self.wdgDistributions)
        self.layout().addWidget(label("Conflict tier list", h2=True), alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.conflictDisplay)

        if not app_env.profile().get('scene-functions', False):
            PremiumOverlayWidget(self.conflictDisplay, 'Conflict reports',
                                 icon='mdi.sword-cross',
                                 alt_link='https://plotlyst.com/docs/scenes/')

        self.refresh()

    @overrides
    def refresh(self):
        self._povChart.refresh(self.novel)
        self._actChart.refresh(self.novel)
        self.conflictDisplay.refresh(self.novel)


class PovDistributionChart(BaseChart):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.createDefaultAxes()
        self.setTitle(html("POV Distribution").bold())
        self._novel: Optional[Novel] = None

        self.pov_number: Dict[Character, int] = {}
        self._acts_filter: Dict[int, bool] = {}

    def toggleAct(self, act: int, toggled: bool):
        self._acts_filter[act] = toggled
        self.refresh(self._novel)

    def refresh(self, novel: Novel):
        self._novel = novel
        for k in self.pov_number.keys():
            self.pov_number[k] = 0

        for scene in novel.scenes:
            if not self._acts_filter.get(acts_registry.act(scene), True):
                continue
            if scene.pov and scene.pov not in self.pov_number.keys():
                self.pov_number[scene.pov] = 0
            if scene.pov:
                self.pov_number[scene.pov] += 1

        series = QPieSeries()
        series.setHoleSize(0.45)
        series.hovered.connect(self._hovered)
        for k, v in self.pov_number.items():
            if v:
                slice = series.append(k.name, v)
                slice.setLabel(icon_to_html_img(avatars.avatar(k)))
                slice.setLabelVisible()

        self.removeAllSeries()
        self.addSeries(series)

    def _hovered(self, slice: QPieSlice, state: bool):
        if state:
            QToolTip.showText(QCursor.pos(), slice.label() + " {:.1f}%".format(100 * slice.percentage()))
        else:
            QToolTip.hideText()


class TierConflictReferenceWidget(QFrame):
    def __init__(self, conflict: Conflict, parent=None):
        super().__init__(parent)
        self.conflict = conflict

        vbox(self, 5)
        self.setMinimumSize(145, 105)
        self.setProperty('large-rounded', True)
        self.setProperty('relaxed-white-bg', True)

        self._lblConflict = IconText()
        font = self._lblConflict.font()
        font.setFamily(app_env.serif_font())
        self._lblConflict.setFont(font)
        self._lblConflict.setText(self.conflict.text if self.conflict.text else self.conflict.scope.display_name())
        if self.conflict.scope != ConflictType.PERSONAL:
            self._lblConflict.setStyleSheet(f'color: {self.conflict.scope.color()}; border: 0px;')

        if self.conflict.character_id:
            character = entities_registry.character(str(self.conflict.character_id))
            if character:
                self._lblConflict.setIcon(avatars.avatar(character))
            incr_icon(self._lblConflict, 6)
        elif self.conflict.scope != ConflictType.PERSONAL:
            self._lblConflict.setIcon(IconRegistry.from_name(self.conflict.scope.icon(), self.conflict.scope.color()))

        self._textedit = QTextEdit(self)
        self._textedit.setTabChangesFocus(True)
        self._textedit.verticalScrollBar().setVisible(False)
        self._textedit.setStyleSheet(
            f'color: {PLACEHOLDER_TEXT_COLOR}; border: 0px; padding: 0px; background-color: rgba(0, 0, 0, 0);')
        self._textedit.setMaximumSize(165, 85)
        self._textedit.setReadOnly(True)
        self._textedit.setText(self.conflict.desc if self.conflict.desc else self.conflict.scope.placeholder())

        self.layout().addWidget(self._lblConflict, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._textedit)


class STierRow(QWidget):
    def __init__(self, tier: Tier, parent=None):
        super().__init__(parent)
        self.tier = tier
        hbox(self, 0, 8)

        self.lbl = QPushButton()
        self.lbl.setIconSize(QSize(55, 55))
        self.lbl.setMinimumHeight(125)
        sp(self.lbl).h_max().v_exp()
        border_top_left = 6 if self.tier == Tier.S else 0
        border_bottom_left = 6 if self.tier == Tier.D else 0
        self.lbl.setStyleSheet(f'''
                    QPushButton {{
                        background: {self.tier.color()};
                        border: 1px solid lightgrey;
                        padding-left: 15px;
                        padding-right: 15px;
                        border-top-left-radius: {border_top_left}px;
                        border-bottom-left-radius: {border_bottom_left}px;
                    }}
                ''')
        if 1 < self.tier.intensity() < 3:
            translucent(self.lbl, 0.40 * self.tier.intensity())

        self.lbl.setIcon(
            IconRegistry.from_name(f'mdi6.alpha-{self.tier.value}', scale=1.4))

        self.container = QWidget()
        flow(self.container, 4, 8)
        sp(self.container).h_exp().v_max()

        self.layout().addWidget(self.lbl, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.container)

    def clear(self):
        clear_layout(self.container)

    def addConflict(self, conflict: Conflict):
        wdg = TierConflictReferenceWidget(conflict)
        self.container.layout().addWidget(wdg)


class ConflictSTierDisplay(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self, 0, 0)
        self.setProperty('dark-bg', True)
        self.setProperty('large-rounded', True)

        self._tiers: Dict[Tier, STierRow] = {}

        self.__initTierWidget(Tier.S)
        self.__initTierWidget(Tier.A)
        self.__initTierWidget(Tier.B)
        self.__initTierWidget(Tier.C)
        self.__initTierWidget(Tier.D)

    def refresh(self, novel: Novel):
        for wdg in self._tiers.values():
            wdg.clear()

        for scene in novel.scenes:
            for agency in scene.agency:
                for conflict in agency.conflicts:
                    if conflict.tier:
                        self._tiers[conflict.tier].addConflict(conflict)

    def __initTierWidget(self, tier: Tier):
        wdg = STierRow(tier)
        self._tiers[tier] = wdg
        self.layout().addWidget(wdg)
