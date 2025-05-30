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
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any, Dict

from PyQt6.QtCore import pyqtSignal, QObject, QTimer

from plotlyst.core.domain import Novel


class Severity(Enum):
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'


@dataclass(eq=True, frozen=True)
class EventLog:
    message: str
    highlighted: bool = False
    details: Optional[str] = None


class EventLogReporter(QObject):
    info = pyqtSignal(EventLog, int)
    warning = pyqtSignal(EventLog, int)
    error = pyqtSignal(EventLog, int)


event_log_reporter = EventLogReporter()


def emit_info(message: str, highlighted: bool = False, time=3000):
    event_log_reporter.info.emit(EventLog(message=message, highlighted=highlighted), time)


def emit_critical(message: str, details: Optional[str] = None, time=5000):
    event_log_reporter.error.emit(EventLog(message=message, details=details, highlighted=True), time)


@dataclass
class Event:
    source: Any


class EventSender(QObject):
    send = pyqtSignal(Event)


class EventSendersRepository:
    def __init__(self):
        self._senders: Dict[Novel, EventSender] = {}

    def instance(self, novel: Novel) -> EventSender:
        if novel not in self._senders.keys():
            self._senders[novel] = EventSender()

        return self._senders[novel]

    def pop(self, novel: Novel):
        self._senders.pop(novel, None)


event_senders = EventSendersRepository()

global_event_sender = EventSender()


class EventListener:

    @abstractmethod
    def event_received(self, event: Event):
        pass


def emit_global_event(event: Event):
    global_event_sender.send.emit(event)


def emit_event(novel: Novel, event: Event, delay: int = 0):
    def func():
        event_senders.instance(novel).send.emit(event)

    if novel.tutorial:
        return

    if delay:
        QTimer.singleShot(10, func)
    else:
        func()
