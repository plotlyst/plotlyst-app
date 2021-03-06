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
from functools import partial
from typing import Optional, Dict

from PyQt5.QtChart import QPieSeries
from PyQt5.QtGui import QColor, QCursor
from PyQt5.QtWidgets import QToolTip
from overrides import overrides

from src.main.python.plotlyst.common import CONFLICT_CHARACTER_COLOR, CONFLICT_NATURE_COLOR, CONFLICT_TECHNOLOGY_COLOR, \
    CONFLICT_SOCIETY_COLOR, CONFLICT_SUPERNATURAL_COLOR, CONFLICT_SELF_COLOR
from src.main.python.plotlyst.core.domain import Novel, Character, ConflictType
from src.main.python.plotlyst.view.common import icon_to_html_img
from src.main.python.plotlyst.view.generated.report.conflict_report_ui import Ui_ConflictReport
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.report import AbstractReport
from src.main.python.plotlyst.view.widget.chart import BaseChart, GenderCharacterChart, SupporterRoleChart, \
    EnneagramChart


class ConflictReport(AbstractReport, Ui_ConflictReport):

    def __init__(self, novel: Novel, parent=None):
        super(ConflictReport, self).__init__(novel, parent)
        self.wdgCharacterSelector.characterToggled.connect(self._characterChanged)
        self.chartType = ConflictTypeChart(self.novel)
        self.chartViewConflictTypes.setChart(self.chartType)
        self.chartGender = GenderCharacterChart()
        self.chartViewGender.setChart(self.chartGender)
        self.chartRole = SupporterRoleChart()
        self.chartViewRole.setChart(self.chartRole)
        self.chartEnneagram = EnneagramChart()
        self.chartViewEnneagram.setChart(self.chartEnneagram)

        self.character: Optional[Character] = None
        self.display()

    @overrides
    def display(self):
        self.wdgCharacterSelector.setCharacters(self.novel.agenda_characters(), checkAll=False)

    def _characterChanged(self, character: Character, toggled: bool):
        if not toggled:
            return
        self.character = character
        self.chartType.refresh(self.character)

        conflicting_characters = []
        for scene in self.novel.scenes:
            agenda = scene.agendas[0]
            for conflict in agenda.conflicts(self.novel):
                if conflict.character_id == character.id and conflict.type == ConflictType.CHARACTER:
                    char = conflict.conflicting_character(self.novel)
                    if char:
                        conflicting_characters.append(char)

        self.chartGender.refresh(conflicting_characters)
        self.chartRole.refresh(conflicting_characters)
        self.chartEnneagram.refresh(conflicting_characters)


class ConflictTypeChart(BaseChart):
    def __init__(self, novel: Novel, parent=None):
        super(ConflictTypeChart, self).__init__(parent)
        self.novel = novel
        self.legend().hide()
        self.setTitle('<b>Conflict types<b>')

    def refresh(self, character: Character):
        conflicts: Dict[ConflictType, int] = {}
        for type_ in ConflictType:
            conflicts[type_] = 0

        for scene in self.novel.scenes:
            agenda = scene.agendas[0]
            if agenda.character_id == character.id:
                for conflict in agenda.conflicts(self.novel):
                    conflicts[conflict.type] = conflicts[conflict.type] + 1
        series = QPieSeries()
        for k, v in conflicts.items():
            if v:
                slice_ = series.append(k.name, v)
                slice_.setLabelVisible()
                slice_.setLabel(icon_to_html_img(IconRegistry.conflict_type_icon(k), size=24))
                slice_.setLabelArmLengthFactor(0.2)
                slice_.setColor(QColor(self._colorForType(k)))
                slice_.hovered.connect(partial(self._hovered, k))

        if self.series():
            self.removeAllSeries()
        self.addSeries(series)

    def _hovered(self, conflictType: ConflictType, state: bool):
        if state:
            QToolTip.showText(QCursor.pos(),
                              f'<b style="color: {self._colorForType(conflictType)}">{conflictType.name.capitalize()}</b>')
        else:
            QToolTip.hideText()

    def _colorForType(self, conflictType: ConflictType) -> str:
        if conflictType == ConflictType.CHARACTER:
            return CONFLICT_CHARACTER_COLOR
        elif conflictType == ConflictType.NATURE:
            return CONFLICT_NATURE_COLOR
        elif conflictType == ConflictType.TECHNOLOGY:
            return CONFLICT_TECHNOLOGY_COLOR
        elif conflictType == ConflictType.SOCIETY:
            return CONFLICT_SOCIETY_COLOR
        elif conflictType == ConflictType.SUPERNATURAL:
            return CONFLICT_SUPERNATURAL_COLOR
        elif conflictType == ConflictType.SELF:
            return CONFLICT_SELF_COLOR
        raise ValueError(f'Unrecognized conflict type {conflictType}')
