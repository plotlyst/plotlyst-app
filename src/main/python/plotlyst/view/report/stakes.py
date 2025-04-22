"""
Plotlyst
Copyright (C) 2021-2024  Zsolt Kovari

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
from typing import Dict

from PyQt6.QtCharts import QLegend, QValueAxis, QSplineSeries
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QColor
from overrides import overrides

from plotlyst.core.domain import Novel, Character, Motivation
from plotlyst.core.text import html
from plotlyst.view.common import icon_to_html_img
from plotlyst.view.generated.report.stakes_report_ui import Ui_StakesReport
from plotlyst.view.icons import IconRegistry
from plotlyst.view.report import AbstractReport
from plotlyst.view.widget.chart import BaseChart


class StakesReport(AbstractReport, Ui_StakesReport):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(novel, parent)
        self.wdgCharacterSelector.characterToggled.connect(self._characterChanged)
        self.chartStakes = StakesChart(self.novel)
        self.chartViewStakes.setChart(self.chartStakes)

        self.display()

    @overrides
    def display(self):
        self.wdgCharacterSelector.setCharacters(self.novel.agenda_characters(), checkAll=False)

    def _characterChanged(self, character: Character, toggled: bool):
        if not toggled:
            return

        self.chartStakes.refresh(character)


class StakesChart(BaseChart):
    def __init__(self, novel: Novel, parent=None):
        super(StakesChart, self).__init__(parent)
        self.novel = novel
        self.legend().setMarkerShape(QLegend.MarkerShape.MarkerShapeCircle)
        self.legend().show()
        self.setTitle(html('Stakes').bold())

    def refresh(self, character: Character):
        self.reset()

        axisX = QValueAxis()
        axisX.setRange(0, len(self.novel.scenes))
        self.addAxis(axisX, Qt.AlignmentFlag.AlignBottom)
        axisX.setVisible(False)

        axisY = QValueAxis()
        axisY.setRange(0, 10)
        self.addAxis(axisY, Qt.AlignmentFlag.AlignLeft)
        axisY.setVisible(False)

        splines: Dict[int, QSplineSeries] = {}
        char_goals: Dict[str, Dict[int, int]] = {}

        for i, scene in enumerate(self.novel.scenes):
            for agenda in scene.agency:
                if agenda.character_id == character.id:
                    for goal_ref in scene.agency[0].goal_references:
                        stakes = goal_ref.stakes
                        if stakes.keys():
                            char_goals[str(goal_ref.character_goal_id)] = stakes
                        elif str(goal_ref.character_goal_id) in char_goals.keys():
                            stakes = char_goals[str(goal_ref.character_goal_id)]

                        for k, v in stakes.items():
                            if v == 0:
                                continue
                            self._spline(splines, k).append(i + 1, v)

        for series in splines.values():
            self.addSeries(series)
            series.attachAxis(axisX)
            series.attachAxis(axisY)

    def _spline(self, splines: Dict[int, QSplineSeries], stake: int):
        if stake in splines.keys():
            return splines[stake]

        series = QSplineSeries()
        splines[stake] = series

        if stake == Motivation.PHYSIOLOGICAL:
            text = 'Physiological'
            icon_name = 'mdi.water'
            color = '#023e8a'
        elif stake == Motivation.SAFETY:
            text = 'Security'
            icon_name = 'mdi.shield-half-full'
            color = '#8900f2'
        elif stake == Motivation.BELONGING:
            text = 'Belonging'
            icon_name = 'fa5s.hand-holding-heart'
            color = '#d00000'
        elif stake == Motivation.ESTEEM:
            text = 'Esteem'
            icon_name = 'fa5s.award'
            color = '#00b4d8'
        elif stake == Motivation.SELF_ACTUALIZATION:
            text = 'Self-actualization'
            icon_name = 'mdi.yoga'
            color = '#52b788'
        elif stake == Motivation.SELF_TRANSCENDENCE:
            text = 'Self-transcendence'
            icon_name = 'mdi6.meditation'
            color = '#c38e70'
        else:
            return series

        series.setName(icon_to_html_img(IconRegistry.from_name(icon_name, color)) + text)
        pen = QPen()
        pen.setColor(QColor(color))
        pen.setWidth(2)
        series.setPen(pen)

        return series
