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
import nltk
from PyQt5.QtChart import QChart, QBarSet, QBarSeries, QValueAxis
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QSizePolicy

from src.main.python.plotlyst.view.widget.display import Chart


class SentenceVarietyChartView(Chart):
    def __init__(self, parent=None):
        super(SentenceVarietyChartView, self).__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        # self.setFixedHeight(500)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        self.text: str = ''
        self.variety = []
        self.chart = QChart()
        self.xAxis = QValueAxis()
        self.yAxis = QValueAxis()
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.legend().setVisible(False)
        # self.chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.setChart(self.chart)

    def setText(self, text: str):
        self.text = text
        self.refresh()

    def refresh(self):
        self.chart.removeAllSeries()
        self.chart.removeAxis(self.xAxis)
        self.chart.removeAxis(self.yAxis)
        if not self.text:
            return

        self.variety.clear()
        sentences = nltk.text.sent_tokenize(self.text)
        for sent in sentences:
            self.variety.append(len(sent.split(' ')))

        self.chart.removeAllSeries()

        series = QBarSeries()
        for i, sent in enumerate(self.variety):
            bar_set = QBarSet('')
            bar_set.setColor(QColor('darkBlue'))
            bar_set.append(sent)
            series.append(bar_set)

        self.chart.createDefaultAxes()
        self.yAxis.setMin(0)
        self.yAxis.setMax(max(self.variety))
        # self.xAxis.setMin(1)
        # self.xAxis.setMax(len(self.variety))
        self.chart.addSeries(series)
        self.chart.addAxis(self.yAxis, Qt.AlignLeft)
        # series.attachAxis(self.xAxis)

        # self.chart.setMinimumWidth(len(self.variety) * 5)
        # self.setMinimumWidth(len(self.variety) * 5)
