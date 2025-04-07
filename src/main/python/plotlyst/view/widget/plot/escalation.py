"""
Plotlyst
Copyright (C) 2021-2025  Zsolt Kovari

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
from PyQt6.QtCore import pyqtSignal, QSize, Qt
from PyQt6.QtWidgets import QWidget, QFrame
from qthandy import vbox, flow, sp, incr_font, incr_icon, line, vspacer, margins

from plotlyst.common import LIGHTGREY_ACTIVE_COLOR
from plotlyst.core.domain import Plot, DynamicPlotPrincipleType, DynamicPlotPrincipleGroupType
from plotlyst.view.common import push_btn, rows, label
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.display import icon_text


class EscalationWidget(QFrame):
    def __init__(self, type_: DynamicPlotPrincipleType, parent=None):
        super().__init__(parent)
        vbox(self, 5)

        self.setProperty('large-rounded', True)
        self.setProperty('muted-bg', True)

        self.container = QWidget()
        flow(self.container, spacing=5)
        sp(self.container).v_max()

        wdg = rows()
        wdg.setFixedHeight(140)
        self.btnPlus = push_btn(IconRegistry.plus_icon(LIGHTGREY_ACTIVE_COLOR))
        self.btnPlus.setIconSize(QSize(36, 36))
        self.btnPlus.setStyleSheet(f'color: {LIGHTGREY_ACTIVE_COLOR}; border: 0px;')
        self.btnPlus.clicked.connect(self._plusClicked)
        wdg.layout().addWidget(self.btnPlus, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.container.layout().addWidget(wdg)

        header = icon_text(type_.icon(), type_.display_name(), icon_color=type_.color(), opacity=0.8)
        incr_font(header, 2)
        incr_icon(header, 2)
        self.layout().addWidget(header, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(line(color=type_.color()))
        self.layout().addWidget(self.container)

        sp(self).v_max()

    def _plusClicked(self):
        pass


class StorylineEscalationEditorWidget(QWidget):
    changed = pyqtSignal()

    def __init__(self, plot: Plot, parent=None):
        super().__init__(parent)
        self._plot = plot

        vbox(self, 5, 8)
        margins(self, left=25, right=25)

        self.wdgTurns = EscalationWidget(DynamicPlotPrincipleType.TURN)
        self.wdgTwists = EscalationWidget(DynamicPlotPrincipleType.TWIST)
        self.wdgDanger = EscalationWidget(DynamicPlotPrincipleType.DANGER)

        self.layout().addWidget(label(DynamicPlotPrincipleGroupType.ESCALATION.description(), description=True))
        self.layout().addWidget(self.wdgTurns)
        self.layout().addWidget(self.wdgTwists)
        self.layout().addWidget(self.wdgDanger)

        self.layout().addWidget(vspacer())
