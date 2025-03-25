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
from dataclasses import dataclass
from typing import List

import qtanim
from PyQt6.QtCore import QUrl, QObject, pyqtSignal, QTimer, Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtWidgets import QWidget, QFrame
from qthandy import vbox, incr_font, hbox, decr_icon, translucent, decr_font
from qthandy.filter import OpacityEventFilter, DisabledClickEventFilter
from qtmenu import MenuWidget

from plotlyst.common import RELAXED_WHITE_COLOR, BLACK_COLOR
from plotlyst.env import app_env
from plotlyst.event.core import emit_global_event
from plotlyst.events import ShowRoadmapEvent
from plotlyst.resources import resource_registry
from plotlyst.view.common import push_btn, ButtonIconSwitchEventFilter, frame, tool_btn, restyle
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.style.base import transparent_menu
from plotlyst.view.widget.display import icon_text, TimerDisplay, MenuOverlayEventFilter, PremiumMessagePopup
from plotlyst.view.widget.input import DecoratedSpinBox, Toggle


@dataclass
class CycleInfo:
    cycle: int
    break_time: bool


class TimerModel(QObject):
    DefaultValue: int = 60 * 5

    valueChanged = pyqtSignal()
    sessionStarted = pyqtSignal()
    sessionFinished = pyqtSignal()
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
        self._times.clear()

        if session == 3600:
            session -= 1
        self._times.append(session)
        for i in range(cycles - 1):
            self._times.append(breakTime)
            self._times.append(session)

        self._currentIndex = 0
        self.value = self._times[self._currentIndex]
        self.sessionStarted.emit()
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self.value = self.DefaultValue
        self._times.clear()

    def previous(self):
        self.value = self._times[self._currentIndex]
        if self.isRunning():
            self._timer.start()
        self.valueChanged.emit()

    def next(self):
        self.value = 0
        if self.isRunning():
            self._timer.start()
        self._tick()

    def remainingTime(self):
        minutes = self.value // 60
        seconds = self.value % 60
        return minutes, seconds

    def isRunning(self) -> bool:
        return self._timer.isActive()

    def isSet(self) -> bool:
        return len(self._times) > 0

    def cycle(self) -> CycleInfo:
        return CycleInfo(self._currentIndex // 2 + 1 if len(self._times) > 1 else 0, self._currentIndex % 2 == 1)

    def toggle(self):
        if self._timer.isActive():
            self._timer.stop()
        else:
            self._timer.start()

    def _tick(self):
        if self.value == 0:
            self.sessionFinished.emit()
            if self._currentIndex < len(self._times) - 1:
                self._currentIndex += 1
                self.value = self._times[self._currentIndex]
                self.sessionStarted.emit()
                if self._timer.isActive():
                    self._timer.start()
            else:
                self._timer.stop()
                self.finished.emit()
        else:
            self.value -= 1
            self.valueChanged.emit()


class TimerControlsWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self, 15, 8)
        self.setProperty('bg', True)
        self.setProperty('large-rounded', True)

        self.btnPause = tool_btn(IconRegistry.pause_icon(color='grey'), transparent_=True, checkable=True)
        self.btnPause.setIconSize(QSize(32, 32))
        self.btnPause.installEventFilter(OpacityEventFilter(self.btnPause, leaveOpacity=0.7))
        self.btnPause.toggled.connect(self._pauseToggled)

        self.btnPrevious = tool_btn(IconRegistry.from_name('mdi.skip-previous'), transparent_=True)
        self.btnPrevious.setIconSize(QSize(22, 22))
        self.btnPrevious.installEventFilter(OpacityEventFilter(self.btnPrevious, leaveOpacity=0.7))

        self.btnSkipNext = tool_btn(IconRegistry.from_name('mdi6.skip-next'), transparent_=True)
        self.btnSkipNext.setIconSize(QSize(22, 22))
        self.btnSkipNext.installEventFilter(OpacityEventFilter(self.btnSkipNext, leaveOpacity=0.7))

        self.btnReset = tool_btn(QIcon(), transparent_=True)
        self.btnReset.installEventFilter(
            ButtonIconSwitchEventFilter(self.btnReset, IconRegistry.from_name('fa5.stop-circle', 'grey'),
                                        IconRegistry.from_name('fa5.stop-circle', '#ED6868')))
        self.btnReset.installEventFilter(OpacityEventFilter(self.btnReset, leaveOpacity=0.7))

        self.layout().addWidget(group(self.btnPrevious, self.btnPause, self.btnSkipNext, spacing=15),
                                alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)

    def setRunningState(self, running: bool):
        self.btnPause.setChecked(not running)

    def _pauseToggled(self, toggled: bool):
        if toggled:
            self.btnPause.setIcon(IconRegistry.play_icon())
        else:
            self.btnPause.setIcon(IconRegistry.pause_icon(color='grey'))


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
        if not app_env.profile().get('writing-sprint', False):
            btnPlus = push_btn(text='Plotlyst Plus Feature', transparent_=True)
            decr_font(btnPlus)
            btnPlus.installEventFilter(OpacityEventFilter(btnPlus, leaveOpacity=0.6))
            btnPlus.clicked.connect(lambda: emit_global_event(ShowRoadmapEvent(self)))
            self.layout().addWidget(btnPlus, alignment=Qt.AlignmentFlag.AlignRight)

            self.btnStart.setText('Upgrade')
            self.btnStart.setIcon(IconRegistry.from_name('ei.shopping-cart', RELAXED_WHITE_COLOR))

        self.layout().addWidget(self.sbTimer, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(
            group(icon_text('ph.repeat-fill', 'Cycles'), self.toggleCycle, margin=0, spacing=0, margin_top=15),
            alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.frameCycle)
        self.layout().addWidget(self.btnStart, alignment=Qt.AlignmentFlag.AlignCenter)

    def value(self) -> int:
        return self.sbTimer.value() * 60

    def cycles(self) -> int:
        return self.sbCycles.value() if self.toggleCycle.isChecked() else 0

    def breakTime(self) -> int:
        return self.sbBreaks.value() * 60 if self.toggleCycle.isChecked() else 0

    def _cycleToggled(self, toggled: bool):
        self.sbCycles.setEnabled(toggled)
        self.sbBreaks.setEnabled(toggled)


class SprintWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self, spacing=0)

        self._model = TimerModel()
        self._model.valueChanged.connect(self._updateTimer)
        self._model.sessionStarted.connect(self._sessionStarted)
        self._model.sessionFinished.connect(self._sessionFinished)
        self._model.finished.connect(self._reset)

        self.btnTimerSetup = tool_btn(IconRegistry.timer_icon(), transparent_=True)
        decr_icon(self.btnTimerSetup)
        self.btnTimerSetup.installEventFilter(OpacityEventFilter(self.btnTimerSetup, leaveOpacity=0.5))
        self.btnTimerSetup.clicked.connect(self._showSetup)

        self.btnSessionControls = tool_btn(IconRegistry.from_name('mdi.timer'), transparent_=True)
        self.btnSessionControls.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btnSessionControls.installEventFilter(OpacityEventFilter(self.btnSessionControls, leaveOpacity=0.5))
        self.btnSessionControls.clicked.connect(self._showControls)

        self.btnBreak = tool_btn(IconRegistry.from_name('ph.coffee'), transparent_=True)
        self.btnBreak.setText('Break')
        self.btnBreak.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.btnBreak.installEventFilter(OpacityEventFilter(self.btnBreak, leaveOpacity=0.5))
        self.btnBreak.clicked.connect(self._showControls)

        self.wdgControls = TimerControlsWidget()
        self._menuControls = MenuWidget()
        transparent_menu(self._menuControls)
        self._menuControls.addWidget(self.wdgControls)

        self.time = TimerDisplay()

        self.layout().addWidget(self.btnTimerSetup)
        self.layout().addWidget(self.btnSessionControls)
        self.layout().addWidget(self.time)
        self.layout().addWidget(self.btnBreak)

        self._timer_setup = TimerSetupWidget()
        self._menuSetup = MenuWidget()
        transparent_menu(self._menuSetup)
        self._menuSetup.addWidget(self._timer_setup)
        self._menuSetup.installEventFilter(MenuOverlayEventFilter(self._menuSetup))

        self._timer_setup.btnStart.clicked.connect(self.start)
        self.wdgControls.btnPause.clicked.connect(self._pauseStartTimer)
        self.wdgControls.btnPrevious.clicked.connect(self._model.previous)
        self.wdgControls.btnSkipNext.clicked.connect(self._model.next)
        self.wdgControls.btnReset.clicked.connect(self._reset)

        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._player.setSource(QUrl.fromLocalFile(resource_registry.cork))
        self._audio_output.setVolume(0.3)

        self._toggleState(False)

    def model(self) -> TimerModel:
        return self._model

    def setNightMode(self, enabled: bool):
        color = RELAXED_WHITE_COLOR if enabled else BLACK_COLOR
        stylesheet = f'border: 0px; color: {color}; background-color: rgba(0,0,0,0);'

        self.time.setStyleSheet(stylesheet)
        translucent(self.time, 0.7 if enabled else 1.0)
        self.btnSessionControls.setStyleSheet(stylesheet)
        self.btnBreak.setStyleSheet(stylesheet)
        restyle(self.btnSessionControls)
        restyle(self.btnBreak)

        self.btnSessionControls.setIcon(IconRegistry.from_name('mdi.timer', color))
        self.btnBreak.setIcon(IconRegistry.from_name('ph.coffee', color))

    def start(self):
        if not app_env.profile().get('writing-sprint', False):
            PremiumMessagePopup.popup('Writing sprints', 'mdi.timer-outline', 'https://plotlyst.com/docs/manuscript/')
            return

        self._toggleState(True)
        self._model.start(self._timer_setup.value(), self._timer_setup.cycles(), self._timer_setup.breakTime())
        self._updateTimer()
        self._menuSetup.close()

    def _toggleState(self, running: bool):
        self.btnTimerSetup.setHidden(running)
        self.btnSessionControls.setVisible(running)
        self.btnBreak.setHidden(True)
        self.time.setVisible(running)

        self.wdgControls.setRunningState(running)

    def _sessionStarted(self):
        info = self._model.cycle()
        self.btnSessionControls.setText(f'#{info.cycle}' if info.cycle else '')
        self.btnSessionControls.setHidden(info.break_time)
        self.btnBreak.setVisible(info.break_time)

        self._updateTimer()

    def _sessionFinished(self):
        self._player.play()

    def _updateTimer(self):
        mins, secs = self._model.remainingTime()
        time = datetime.time(minute=mins, second=secs)
        self.time.setTime(time)

    def _showSetup(self):
        self._menuSetup.exec(self.mapToGlobal(self.rect().bottomLeft()))

    def _showControls(self):
        self.wdgControls.setRunningState(self._model.isRunning())
        self._menuControls.exec(self.mapToGlobal(self.rect().bottomLeft()))

    def _pauseStartTimer(self, _: bool):
        self.model().toggle()
        self.wdgControls.setRunningState(self.model().isRunning())

    def _reset(self):
        self.model().stop()
        self._toggleState(False)
        if self._menuControls.isVisible():
            self._menuControls.hide()
