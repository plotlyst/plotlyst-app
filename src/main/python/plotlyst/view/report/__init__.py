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
from abc import abstractmethod

from PyQt6.QtWidgets import QWidget

from plotlyst.core.domain import Novel
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.widget.display import ChartView


class AbstractReport(QWidget):
    largeSize: int = 400
    mediumSize: int = 350
    smallSize: int = 250

    def __init__(self, novel: Novel, parent=None, setupUi: bool = True):
        super(AbstractReport, self).__init__(parent)
        self.novel = novel
        if setupUi:
            self.setupUi(self)

        self.repo = RepositoryPersistenceManager.instance()

    @abstractmethod
    def refresh(self):
        pass

    def _newChartView(self, size: int):
        chart = ChartView()
        chart.setFixedSize(size, size)
        return chart
