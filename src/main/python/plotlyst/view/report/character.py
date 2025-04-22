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
from typing import List

from PyQt6.QtCharts import QPolarChart, QCategoryAxis, QLineSeries, QAreaSeries
from PyQt6.QtCharts import QValueAxis
from PyQt6.QtGui import QPen, QColor
from overrides import overrides
from qthandy import hbox, vbox, margins, flow

from plotlyst.common import PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import Novel, Character
from plotlyst.view.common import icon_to_html_img
from plotlyst.view.generated.report.character_report_ui import Ui_CharacterReport
from plotlyst.view.icons import IconRegistry
from plotlyst.view.report import AbstractReport
from plotlyst.view.widget.chart import SupporterRoleChart, GenderCharacterChart, \
    PolarBaseChart, RoleChart
from plotlyst.view.widget.display import ChartView


class CharacterReport(AbstractReport, Ui_CharacterReport):
    largeSize: int = 400
    mediumSize: int = 350
    smallSize: int = 250

    def __init__(self, novel: Novel, parent=None):
        super(CharacterReport, self).__init__(novel, parent)

        self._chartRoles = RoleChart()
        self.chartViewRoles = self.__newChartView(self.mediumSize)
        self.chartViewRoles.setChart(self._chartRoles)

        self._chartSupporterRoles = SupporterRoleChart()
        self.chartViewSupporterRoles = self.__newChartView(self.mediumSize)
        self.chartViewSupporterRoles.setChart(self._chartSupporterRoles)
        hbox(self.wdgRoles, 0)
        margins(self.wdgRoles, left=15)
        self.wdgRoles.layout().addWidget(self.chartViewRoles)
        self.wdgRoles.layout().addWidget(self.chartViewSupporterRoles)

        self._chartGenderAll = GenderCharacterChart()
        self._chartGenderAll.setTitle('')
        self.chartViewGenderAll = self.__newChartView(self.largeSize)
        self.wdgGender.layout().insertWidget(0, self.chartViewGenderAll)
        self.chartViewGenderAll.setChart(self._chartGenderAll)

        flow(self.wdgGenderGroups, 0)

        self._chartGenderMajor = GenderCharacterChart()
        self._chartGenderMajor.setTitle(f'{icon_to_html_img(IconRegistry.major_character_icon())}Major')
        self._chartGenderMajor.setLabelsVisible(False)
        self.chartViewGenderMajor = self.__newChartView(self.smallSize)
        self.chartViewGenderMajor.setChart(self._chartGenderMajor)
        self.wdgGenderGroups.layout().addWidget(self.chartViewGenderMajor)

        self._chartGenderSecondary = GenderCharacterChart()
        self._chartGenderSecondary.setTitle(f'{icon_to_html_img(IconRegistry.secondary_character_icon())}Secondary')
        self._chartGenderSecondary.setLabelsVisible(False)
        self.chartViewGenderSecondary = self.__newChartView(self.smallSize)
        self.chartViewGenderSecondary.setChart(self._chartGenderSecondary)
        self.wdgGenderGroups.layout().addWidget(self.chartViewGenderSecondary)

        self._chartGenderMinor = GenderCharacterChart()
        self._chartGenderMinor.setTitle(f'{icon_to_html_img(IconRegistry.minor_character_icon())}Minor')
        self._chartGenderMinor.setLabelsVisible(False)
        self.chartViewGenderMinor = self.__newChartView(self.smallSize)
        self.chartViewGenderMinor.setChart(self._chartGenderMinor)
        self.wdgGenderGroups.layout().addWidget(self.chartViewGenderMinor)

        # self._chartEnneagram = EnneagramChart()
        # self.chartViewEnneagram = self.__newChartView(self.largeSize)
        # self.chartViewEnneagram.setChart(self._chartEnneagram)
        # self.wdgPersonality.layout().addWidget(self.chartViewEnneagram)

        self._chartAge = AgeChart()
        self.chartViewAge = self.__newChartView(self.mediumSize)
        vbox(self.wdgAge, 0, 0).addWidget(self.chartViewAge)
        self.chartViewAge.setChart(self._chartAge)

        self.refresh()

    @overrides
    def refresh(self):
        self._chartRoles.refresh(self.novel.characters)
        self._chartSupporterRoles.refresh(self.novel.characters)
        self._chartGenderAll.refresh(self.novel.characters)
        self._chartGenderMajor.refresh(self.novel.major_characters())
        self._chartGenderSecondary.refresh(self.novel.secondary_characters())
        self._chartGenderMinor.refresh(self.novel.minor_characters())
        # self._chartEnneagram.refresh(self.novel.characters)
        self._chartAge.refresh(self.novel.characters)

    def __newChartView(self, size: int):
        chart = ChartView()
        chart.setFixedSize(size, size)
        return chart


class AgeChart(PolarBaseChart):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rad_axis = QValueAxis()
        self._rad_axis.setLabelsVisible(False)
        self._angular_axis = QCategoryAxis()
        self._angular_axis.setRange(0, 90)
        for age in [3, 8, 12, 18, 30, 45, 65]:
            self._angular_axis.append(str(age), age)

    def refresh(self, characters: List[Character]):
        self.reset()

        self.addAxis(self._rad_axis, QPolarChart.PolarOrientation.PolarOrientationRadial)
        self.addAxis(self._angular_axis, QPolarChart.PolarOrientation.PolarOrientationAngular)

        pen = QPen()
        pen.setWidth(2)
        pen.setColor(QColor(PLOTLYST_SECONDARY_COLOR))

        upper_series = QLineSeries()
        upper_series.setPen(pen)
        lower_series = QLineSeries()
        lower_series.setPen(pen)

        ages = {}
        for char in characters:
            if not char.age:
                continue
            if char.age_infinite:
                continue
            age = 90 if char.age > 90 else char.age
            if age not in ages.keys():
                ages[age] = 1
            ages[age] = ages[age] + 1
        sorted_ages = sorted(ages.keys())
        if sorted_ages:
            upper_series.append(sorted_ages[0], 0)
            for age in sorted_ages:
                upper_series.append(age, ages[age])
                lower_series.append(age, 0)
            upper_series.append(sorted_ages[-1], 0)

        if ages:
            self._rad_axis.setRange(0, max(ages.values()))

        self.addSeries(upper_series)
        self.addSeries(lower_series)

        series = QAreaSeries(upper_series, lower_series)
        series.setColor(QColor(PLOTLYST_SECONDARY_COLOR))
        series.setPen(pen)

        self.addSeries(series)
        series.attachAxis(self._rad_axis)
        series.attachAxis(self._angular_axis)
