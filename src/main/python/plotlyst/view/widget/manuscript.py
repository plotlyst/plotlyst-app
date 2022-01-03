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
import datetime
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QUrl
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import QWidget, QMenu, QWidgetAction

from src.main.python.plotlyst.resources import resource_registry
from src.main.python.plotlyst.view.common import retain_size_when_hidden
from src.main.python.plotlyst.view.generated.sprint_widget_ui import Ui_SprintWidget
from src.main.python.plotlyst.view.generated.timer_setup_widget_ui import Ui_TimerSetupWidget
from src.main.python.plotlyst.view.icons import IconRegistry


class TimerModel(QObject):
    DefaultValue: int = 60 * 5

    valueChanged = pyqtSignal()
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super(TimerModel, self).__init__(parent)
        self.value: int = self.DefaultValue

        self._timer = QTimer()
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    def start(self, value: int):
        self.value = value
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self.value = self.DefaultValue

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
        self.value -= 1
        self.valueChanged.emit()

        if self.value == 0:
            self._timer.stop()
            self.finished.emit()


class TimerSetupWidget(QWidget, Ui_TimerSetupWidget):
    def __init__(self, parent=None):
        super(TimerSetupWidget, self).__init__(parent)
        self.setupUi(self)

    def value(self) -> int:
        return self.sbTimer.value() * 60


class SprintWidget(QWidget, Ui_SprintWidget):
    def __init__(self, parent=None):
        super(SprintWidget, self).__init__(parent)
        self.setupUi(self)
        self._model = None
        self._compact: bool = False
        self.setModel(TimerModel())

        self._toggleState(False)

        self.btnTimer.setIcon(IconRegistry.timer_icon())
        self.btnReset.setIcon(IconRegistry.restore_alert_icon('#9b2226'))
        menu = QMenu(self.btnTimer)
        action = QWidgetAction(menu)
        self._timer_setup = TimerSetupWidget()
        action.setDefaultWidget(self._timer_setup)
        menu.addAction(action)
        self.btnTimer.setMenu(menu)

        self._timer_setup.btnStart.clicked.connect(self.start)
        self.btnPause.clicked.connect(self._pauseStartTimer)
        self.btnReset.clicked.connect(self._reset)

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
        self.time.setStyleSheet('border: 0px; color: white; background-color: rgba(0,0,0,0);')

    def start(self):
        self._toggleState(True)
        self._model.start(self._timer_setup.value())
        self._updateTimer()
        self.btnTimer.menu().hide()

    def _toggleState(self, running: bool):
        self.time.setVisible(running)
        if running:
            self.btnPause.setChecked(True)
            self.btnPause.setIcon(IconRegistry.pause_icon())
        if self._compact:
            self.btnTimer.setHidden(running)
            retain_size_when_hidden(self.btnPause)
            retain_size_when_hidden(self.btnReset)
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
            self.btnPause.setIcon(IconRegistry.pause_icon())
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
