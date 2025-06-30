from typing import Optional, Dict

from PyQt6.QtCharts import QPieSeries, QPieSlice
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QToolTip, QWidget, QPushButton, QFrame
from overrides import overrides
from qthandy import vbox, hbox, sp, translucent

from plotlyst.core.domain import Novel, Character, Tier
from plotlyst.core.text import html
from plotlyst.env import app_env
from plotlyst.service.cache import acts_registry
from plotlyst.view.common import icon_to_html_img, columns, rows, wrap, label
from plotlyst.view.icons import avatars, IconRegistry
from plotlyst.view.report import AbstractReport
from plotlyst.view.widget.chart import BaseChart, ActDistributionChart
from plotlyst.view.widget.display import ChartView, PremiumOverlayWidget
from plotlyst.view.widget.structure.selector import ActSelectorButtons


class SceneReport(AbstractReport):

    def __init__(self, novel: Novel, parent=None):
        super(SceneReport, self).__init__(novel, parent, setupUi=False)
        vbox(self)

        self.wdgDistributions = columns()
        self.wdgDistributions.setMinimumHeight(550)
        self.wdgPov = rows(0, 0)
        self.chartViewPovDistribution = ChartView()
        self._povChart = PovDistributionChart()
        self.chartViewPovDistribution.setChart(self._povChart)
        self.actSelector = ActSelectorButtons(novel)
        self.wdgPov.layout().addWidget(self.actSelector, alignment=Qt.AlignmentFlag.AlignCenter)
        self.wdgPov.layout().addWidget(self.chartViewPovDistribution)
        self.actSelector.actToggled.connect(self._povChart.toggleAct)

        self.chartViewActDistribution = ChartView()
        self._actChart = ActDistributionChart()
        self.chartViewActDistribution.setChart(self._actChart)

        self.wdgDistributions.layout().addWidget(wrap(self.chartViewActDistribution, margin_top=35))
        self.wdgDistributions.layout().addWidget(self.wdgPov)

        self.conflictDisplay = ConflictSTierDisplay()

        self.layout().addWidget(self.wdgDistributions)
        self.layout().addWidget(label("Conflict tier list", h3=True), alignment=Qt.AlignmentFlag.AlignCenter)
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


class STierRow(QWidget):
    def __init__(self, tier: Tier, parent=None):
        super().__init__(parent)
        self.tier = tier
        hbox(self, 0, 0)

        self.lbl = QPushButton()
        self.lbl.setIconSize(QSize(55, 55))
        sp(self.lbl).h_max()
        self.lbl.setStyleSheet(f'''
                    QPushButton {{
                        background: {self.tier.color()};
                        border: 1px solid lightgrey;
                        padding: 15px;
                        padding-top: 25px;
                        padding-bottom: 25px;
                        border-top-left-radius: 6px;
                        border-bottom-left-radius: 6px;
                    }}
                ''')
        if self.tier.intensity() < 4:
            translucent(self, 0.25 * self.tier.intensity())

        self.lbl.setIcon(
            IconRegistry.from_name(f'mdi6.alpha-{self.tier.value}', scale=1.4))

        self.layout().addWidget(self.lbl, alignment=Qt.AlignmentFlag.AlignLeft)


class ConflictSTierDisplay(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self, 0, 0)
        self.setProperty('muted-bg', True)
        self.setProperty('large-rounded', True)

        self.__initTierWidget(Tier.S)
        self.__initTierWidget(Tier.A)
        self.__initTierWidget(Tier.B)
        self.__initTierWidget(Tier.C)
        self.__initTierWidget(Tier.D)

    def __initTierWidget(self, tier: Tier):
        wdg = STierRow(tier)
        self.layout().addWidget(wdg)
