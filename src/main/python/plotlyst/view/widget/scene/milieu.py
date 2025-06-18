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
from enum import Enum

import emoji
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QColor
from PyQt6.QtWidgets import QWidget, QGraphicsColorizeEffect
from overrides import overrides
from qthandy import vbox, sp, hbox, spacer, vline, pointy

from plotlyst.view.common import push_btn, frame, shadow, restyle
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.display import Emoji


class DayNightState(Enum):
    Idle = 0
    Day = 1
    Night = 2

    def next(self) -> 'DayNightState':
        if self == DayNightState.Idle:
            return DayNightState.Day
        elif self == DayNightState.Day:
            return DayNightState.Night
        else:
            return DayNightState.Idle


class DayNightSelector(Emoji):
    toggled = pyqtSignal(DayNightState)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = DayNightState.Idle
        pointy(self)
        self.setToolTip('Day-night selector')
        self.refresh()

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._state = self._state.next()
        self.refresh()
        self.toggled.emit(self._state)

    def refresh(self):
        if self._state == DayNightState.Idle:
            self.setText(emoji.emojize(':sun_with_face:'))
            effect = QGraphicsColorizeEffect(self)
            effect.setColor(QColor('grey'))
            self.setGraphicsEffect(effect)
        elif self._state == DayNightState.Day:
            self.setText(emoji.emojize(':sun_with_face:'))
            self.setGraphicsEffect(None)
        else:
            self.setText(emoji.emojize(':waxing_crescent_moon:'))
            self.setGraphicsEffect(None)


class SceneMilieuLinkWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self, 4, 0)

        self.btn = push_btn(IconRegistry.world_building_icon('grey', 'grey'), 'Milieu', transparent_=True)
        self.frame = frame()
        self.frame.setProperty('rounded', True)
        self.frame.setProperty('relaxed-white-bg', True)
        sp(self.frame).h_exp().v_max()

        self.emojiDay = DayNightSelector()
        self.emojiDay.toggled.connect(self._dayNightToggled)
        hbox(self.frame)
        self.frame.layout().addWidget(self.emojiDay)
        self.frame.layout().addWidget(vline())
        self.frame.layout().addWidget(spacer())

        self.layout().addWidget(self.btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.frame)

    def _dayNightToggled(self, state: DayNightState):
        if state == DayNightState.Day:
            muted_prop = False
            anim = True
        elif state == DayNightState.Night:
            muted_prop = True
            anim = False
        else:
            muted_prop = False
            anim = False

        self.frame.setProperty('night-bg', muted_prop)
        self.frame.setProperty('relaxed-white-bg', not muted_prop)
        restyle(self.frame)
        if anim:
            shadow(self.frame)
        else:
            self.frame.setGraphicsEffect(None)
