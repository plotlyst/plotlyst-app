from typing import Optional, Dict

from PyQt6.QtCharts import QPieSeries, QPieSlice
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QToolTip
from overrides import overrides
from qthandy import vbox

from plotlyst.core.domain import Novel, Character
from plotlyst.core.text import html
from plotlyst.service.cache import acts_registry
from plotlyst.view.common import icon_to_html_img, columns, rows, wrap
from plotlyst.view.icons import avatars
from plotlyst.view.report import AbstractReport
from plotlyst.view.widget.chart import BaseChart, ActDistributionChart
from plotlyst.view.widget.display import ChartView
from plotlyst.view.widget.structure.selector import ActSelectorButtons


class SceneReport(AbstractReport):

    def __init__(self, novel: Novel, parent=None):
        super(SceneReport, self).__init__(novel, parent, setupUi=False)
        vbox(self)

        self.wdgDistributions = columns()
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

        self.layout().addWidget(self.wdgDistributions)

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
