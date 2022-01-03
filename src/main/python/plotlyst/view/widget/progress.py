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
from typing import List

from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QPieSlice
from PyQt6.QtCore import Qt, QMargins
from PyQt6.QtGui import QPainter, QColor, QFont

from src.main.python.plotlyst.core.domain import Novel, SceneStage


class ProgressChartView(QChartView):
    def __init__(self, value: int, max: int, title_prefix: str = 'Progress', color=Qt.GlobalColor.darkBlue,
                 parent=None):
        super(ProgressChartView, self).__init__(parent)
        self.chart = QChart()
        self.chart.legend().hide()
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.chart.setMargins(QMargins(0, 1, 0, 1))
        font = QFont()
        font.setBold(True)
        self.chart.setTitleFont(font)
        self._title_prefix = title_prefix
        self._color = color

        self.setChart(self.chart)
        self.setMaximumHeight(200)
        self.setMaximumWidth(250)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.refresh(value, max)

    def refresh(self, value: int, max: int):
        self.chart.removeAllSeries()
        series = QPieSeries()
        series.setHoleSize(0.45)
        percentage_slice = QPieSlice('Progress', value)
        percentage_slice.setColor(QColor(self._color))
        empty_slice = QPieSlice('', max - value)
        empty_slice.setColor(Qt.GlobalColor.white)
        series.append(percentage_slice)
        series.append(empty_slice)
        self.chart.setTitle(self._title_prefix + " {:.1f}%".format(100 * percentage_slice.percentage()))

        self.chart.addSeries(series)


class SceneStageProgressCharts:

    def __init__(self, novel: Novel):
        self.novel = novel
        self._chartviews: List[ProgressChartView] = []
        self._stage = self.novel.stages[1]  # first draft
        self._stage_index = 1
        self._act_colors = {1: '#02bcd4', 2: '#1bbc9c', 3: '#ff7800'}

    def charts(self) -> List[ProgressChartView]:
        return self._chartviews

    def stage(self) -> SceneStage:
        return self._stage

    def setStage(self, stage: SceneStage):
        self._stage = stage
        self._stage_index = self.novel.stages.index(self._stage)
        self.refresh()

    def refresh(self):
        in_act_1 = True
        in_act_2 = False
        in_act_3 = False
        act1: List[bool] = []
        act2: List[bool] = []
        act3: List[bool] = []

        for scene in self.novel.scenes:
            if scene.beat and scene.beat.act == 1 and scene.beat.ends_act:
                in_act_2 = True
                in_act_1 = False
            elif scene.beat and scene.beat.act == 2 and scene.beat.ends_act:
                in_act_3 = True
                in_act_2 = False
            if scene.stage and self.novel.stages.index(scene.stage) >= self._stage_index:
                match = True
            else:
                match = False
            if in_act_1:
                act1.append(match)
            elif in_act_2:
                act2.append(match)
            elif in_act_3:
                act3.append(match)

        values = []
        match_in_act1 = len([x for x in act1 if x])
        match_in_act2 = len([x for x in act2 if x])
        match_in_act3 = len([x for x in act3 if x])

        values.append((match_in_act1 + match_in_act2 + match_in_act3, len(self.novel.scenes)))

        if act1:
            values.append((match_in_act1, len(act1)))
        else:
            values.append((0, 1))
        if act2:
            values.append((match_in_act2, len(act2)))
        else:
            values.append((0, 1))
        if act3:
            values.append((match_in_act3, len(act3)))
        else:
            values.append((0, 1))

        if not self._chartviews:
            overall = ProgressChartView(values[0][0], values[0][1], 'Overall:')
            self._chartviews.append(overall)

            for i in range(1, 4):
                act = ProgressChartView(values[i][0], values[i][1], f'Act {i}:',
                                        color=self._act_colors.get(i, Qt.GlobalColor.darkBlue))
                self._chartviews.append(act)
        else:
            for i, v in enumerate(values):
                self._chartviews[i].refresh(v[0], v[1])
