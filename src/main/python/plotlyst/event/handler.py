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
import asyncio
import logging
import traceback
from typing import Optional, List, Dict, TypeVar

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QMessageBox, QWidget, QStatusBar, QApplication

from src.main.python.plotlyst.env import app_env
from src.main.python.plotlyst.event.core import EventLog, Severity, \
    emit_critical, EventListener, Event
from src.main.python.plotlyst.view.dialog.error import ErrorMessageBox


class EventLogHandler:
    parent: Optional[QWidget] = None

    def __init__(self, statusbar: QStatusBar):
        self.statusbar = statusbar
        self._error_event = asyncio.Event()

    def on_info_event(self, event: EventLog, time: int) -> None:
        if app_env.test_env():
            return
        if not event.highlighted:
            self.statusbar.showMessage(event.message, time)
            self.statusbar.setStyleSheet('color: #235789;')
        self._handle_highlighted_event(event, Severity.INFO)

    def on_error_event(self, event: EventLog, time: int) -> None:
        if not self._error_event.is_set():
            if not event.highlighted:
                self.statusbar.showMessage(event.message, time)
                self.statusbar.setStyleSheet('color: red')
            self._handle_highlighted_event(event, Severity.ERROR)
            if event.details:
                logging.error(event.details)
            else:
                logging.error(event.message)
            self._error_event.set()

            QTimer.singleShot(50, self._error_event.clear)
            QTimer.singleShot(50, self._reset_statusbar_color)

    def _handle_highlighted_event(self, event: EventLog, severity: Severity):
        if not event.highlighted:
            return
        QApplication.setOverrideCursor(QCursor(Qt.ArrowCursor))
        if severity == Severity.INFO:
            QMessageBox.information(self.parent, 'Information', event.message)
        if severity == Severity.WARNING:
            ErrorMessageBox(msg=event.message, warning=True, parent=self.parent).display()
        if severity == Severity.ERROR:
            ErrorMessageBox(msg=event.message, details=event.details, parent=self.parent).display()

        QApplication.restoreOverrideCursor()

    def _reset_statusbar_color(self) -> None:
        self.statusbar.setStyleSheet('color: black')


class DialogExceptionHandler:

    def init(self):
        pass

    def handle(self, exception_type, exception_value: Exception, exception_traceback):
        msg = ''.join(exception_value.args)
        details: List[str] = traceback.format_exception(exception_type, exception_value, exception_traceback)
        emit_critical(msg, ''.join(details))


TEvent = TypeVar('TEvent', bound=Event)


class EventDispatcher:

    def __init__(self):
        self._listeners: Dict[TEvent, List[EventListener]] = {}

    def register(self, listener: EventListener, event_type):
        if event_type not in self._listeners.keys():
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)

    def clear(self):
        self._listeners.clear()

    def deregister(self, listener: EventListener, event_type):
        if event_type not in self._listeners.keys():
            return
        if listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)

    def dispatch(self, event: Event):
        if type(event) in self._listeners.keys():
            for listener in self._listeners[type(event)]:
                if event.source != listener:
                    listener.event_received(event)


event_dispatcher = EventDispatcher()
