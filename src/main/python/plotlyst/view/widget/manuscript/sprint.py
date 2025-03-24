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

import datetime
from typing import Optional, List

import qtanim
from PyQt6.QtCore import QUrl, QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import QWidget, QFrame, QTimeEdit, QDateTimeEdit, QAbstractSpinBox
from qthandy import retain_when_hidden, transparent, vbox, incr_font, hbox
from qthandy.filter import OpacityEventFilter, DisabledClickEventFilter
from qtmenu import MenuWidget

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.resources import resource_registry
from plotlyst.view.common import push_btn, ButtonIconSwitchEventFilter, frame, tool_btn
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.style.base import transparent_menu
from plotlyst.view.widget.display import MenuOverlayEventFilter, icon_text
from plotlyst.view.widget.input import DecoratedSpinBox, Toggle


class TimerModel(QObject):
    DefaultValue: int = 60 * 5

    valueChanged = pyqtSignal()
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super(TimerModel, self).__init__(parent)
        self.value: int = 0
        self._times: List[int] = []
        self._currentIndex: int = 0

        self._timer = QTimer()
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    def start(self, session: int, cycles: int = 1, breakTime: int = 300):
        if session == 3600:
            session -= 1
        self._times.append(session)
        for i in range(cycles - 1):
            self._times.append(breakTime)
            self._times.append(session)

        self._currentIndex = 0
        self.value = self._times[self._currentIndex]
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self.value = self.DefaultValue

    def next(self):
        self.value = 0
        self._tick()

    def remainingTime(self):
        minutes = self.value // 60
        seconds = self.value % 60
        return minutes, seconds

    def isActive(self) -> bool:
        return self._timer.isActive()

    def toggle(self):
        if self._timer.isActive():
            self._timer.stop()
        else:
            self._timer.start()

    def _tick(self):
        if self.value == 0:
            self._timer.stop()
            self.finished.emit()
        else:
            self.value -= 1
            self.valueChanged.emit()


class TimerSetupWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self, 15, 8)

        self.setProperty('bg', True)
        self.setProperty('large-rounded', True)

        self.sbTimer = DecoratedSpinBox(icon=IconRegistry.from_name('mdi.timer'))
        self.sbTimer.setPrefix('Session (minutes):')
        self.sbTimer.setMinimum(1)
        self.sbTimer.setMaximum(60)
        self.sbTimer.setValue(25)
        incr_font(self.sbTimer.spinBox, 3)

        self.toggleCycle = Toggle()

        self.frameCycle = frame()
        vbox(self.frameCycle, 5)
        self.frameCycle.setProperty('muted-bg', True)
        self.frameCycle.setProperty('large-rounded', True)

        self.sbCycles = DecoratedSpinBox(icon=IconRegistry.from_name('ph.repeat-fill'))
        self.sbCycles.installEventFilter(
            DisabledClickEventFilter(self.sbCycles, lambda: qtanim.shake(self.toggleCycle)))
        self.sbCycles.setPrefix('Cycles:')
        self.sbCycles.setMinimum(1)
        self.sbCycles.setMaximum(10)
        self.sbCycles.setValue(4)
        self.sbBreaks = DecoratedSpinBox(icon=IconRegistry.from_name('ph.coffee'))
        self.sbBreaks.installEventFilter(
            DisabledClickEventFilter(self.sbBreaks, lambda: qtanim.shake(self.toggleCycle)))
        self.sbBreaks.setMinimum(1)
        self.sbBreaks.setMaximum(25)
        self.sbBreaks.setPrefix('Break (minutes):')
        self.sbBreaks.setValue(5)

        self.frameCycle.layout().addWidget(self.sbCycles, alignment=Qt.AlignmentFlag.AlignRight)
        self.frameCycle.layout().addWidget(self.sbBreaks, alignment=Qt.AlignmentFlag.AlignRight)

        self.toggleCycle.toggled.connect(self._cycleToggled)
        self.toggleCycle.setChecked(True)

        self.btnStart = push_btn(IconRegistry.from_name('fa5s.play', RELAXED_WHITE_COLOR), 'Start writing sprint',
                                 properties=['confirm', 'positive'])

        self.layout().addWidget(self.sbTimer, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(
            group(icon_text('ph.repeat-fill', 'Cycles'), self.toggleCycle, margin=0, spacing=0, margin_top=15),
            alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.frameCycle)
        self.layout().addWidget(self.btnStart, alignment=Qt.AlignmentFlag.AlignCenter)

    def value(self) -> int:
        return self.sbTimer.value() * 60

    def cycles(self) -> int:
        return self.sbCycles.value() if self.toggleCycle.isChecked() else 1

    def breakTime(self) -> int:
        return self.sbBreaks.value() * 60 if self.toggleCycle.isChecked() else 0

    def _cycleToggled(self, toggled: bool):
        self.sbCycles.setEnabled(toggled)
        self.sbBreaks.setEnabled(toggled)


class SprintWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._model: Optional[TimerModel] = None
        self._compact: bool = False

        hbox(self)

        self.btnTimer = tool_btn(IconRegistry.timer_icon(), transparent_=True)
        self.btnPause = tool_btn(IconRegistry.pause_icon(color='grey'), transparent_=True, checkable=True)
        self.btnPause.installEventFilter(OpacityEventFilter(self.btnPause, leaveOpacity=0.7))
        self.btnReset = tool_btn(QIcon(), transparent_=True)
        self.btnReset.installEventFilter(
            ButtonIconSwitchEventFilter(self.btnReset, IconRegistry.from_name('fa5.stop-circle', 'grey'),
                                        IconRegistry.from_name('fa5.stop-circle', '#ED6868')))
        self.btnReset.installEventFilter(OpacityEventFilter(self.btnReset, leaveOpacity=0.7))

        self.time = QTimeEdit()
        self.time.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.time.setWrapping(False)
        self.time.setReadOnly(True)
        self.time.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.time.setProperty("showGroupSeparator", False)
        self.time.setDisplayFormat("mm:ss")
        self.time.setCurrentSection(QDateTimeEdit.Section.MinuteSection)
        transparent(self.time)

        self.layout().addWidget(self.btnTimer)
        self.layout().addWidget(self.time)
        self.layout().addWidget(self.btnPause)
        self.layout().addWidget(self.btnReset)

        self._timer_setup = TimerSetupWidget()
        self._menu = MenuWidget(self.btnTimer)
        self._menu.addWidget(self._timer_setup)
        transparent_menu(self._menu)
        self._menu.installEventFilter(MenuOverlayEventFilter(self._menu))

        self._timer_setup.btnStart.clicked.connect(self.start)
        self.btnPause.clicked.connect(self._pauseStartTimer)
        self.btnReset.clicked.connect(self._reset)

        self.setModel(TimerModel())
        self._effect: Optional[QSoundEffect] = None

    def model(self) -> TimerModel:
        return self._model

    def setModel(self, model: TimerModel):
        self._model = model
        self._model.valueChanged.connect(self._updateTimer)
        self._model.finished.connect(self._finished)
        self._toggleState(self._model.isActive())

    def setCompactMode(self, compact: bool):
        self._compact = compact
        self._toggleState(self.model().isActive())
        self.time.setStyleSheet(f'border: 0px; color: {RELAXED_WHITE_COLOR}; background-color: rgba(0,0,0,0);')

    def start(self):
        self._toggleState(True)
        self._model.start(self._timer_setup.value(), self._timer_setup.cycles(), self._timer_setup.breakTime())
        self._updateTimer()
        self._menu.close()

    def _toggleState(self, running: bool):
        self.time.setVisible(running)
        if running:
            self.btnPause.setChecked(True)
            self.btnPause.setIcon(IconRegistry.pause_icon(color='grey'))
        if self._compact:
            self.btnTimer.setHidden(running)
            retain_when_hidden(self.btnPause)
            retain_when_hidden(self.btnReset)
            self.btnPause.setHidden(True)
            self.btnReset.setHidden(True)
        else:
            self.btnPause.setVisible(running)
            self.btnReset.setVisible(running)

    def _updateTimer(self):
        mins, secs = self._model.remainingTime()
        time = datetime.time(minute=mins, second=secs)
        self.time.setTime(time)

    def _pauseStartTimer(self, played: bool):
        self.model().toggle()
        if played:
            self.btnPause.setIcon(IconRegistry.pause_icon(color='grey'))
        else:
            self.btnPause.setIcon(IconRegistry.play_icon())

    def _reset(self):
        self.model().stop()
        self._toggleState(False)

    def _finished(self):
        if self._effect is None:
            self._effect = QSoundEffect()
            self._effect.setSource(QUrl.fromLocalFile(resource_registry.cork))
            self._effect.setVolume(0.3)
        self._effect.play()
