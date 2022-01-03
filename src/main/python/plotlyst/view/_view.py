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
from abc import abstractmethod
from typing import List, Any, Optional

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QWidget
from overrides import overrides

from src.main.python.plotlyst.core.domain import Novel
from src.main.python.plotlyst.event.core import EventListener, Event
from src.main.python.plotlyst.event.handler import event_dispatcher
from src.main.python.plotlyst.events import NovelReloadedEvent
from src.main.python.plotlyst.view.common import busy
from src.main.python.plotlyst.worker.persistence import RepositoryPersistenceManager


class AbstractView(QObject, EventListener):

    def __init__(self, event_types: Optional[List[Any]] = None):
        super().__init__(None)
        self._refresh_on_activation: bool = False
        self.widget = QWidget()
        if event_types:
            self._event_types = event_types
        else:
            self._event_types = []

        for event in self._event_types:
            event_dispatcher.register(self, event)

        self.repo = RepositoryPersistenceManager.instance()

    @overrides
    def event_received(self, event: Event):
        refresh = False
        for et in self._event_types:
            if isinstance(event, et):
                refresh = True
        if refresh:
            if self.widget.isVisible():
                self.refresh()
            else:
                self._refresh_on_activation = True

    def activate(self):
        if self._refresh_on_activation:
            self.refresh()
            self._refresh_on_activation = False

    @abstractmethod
    def refresh(self):
        pass


class AbstractNovelView(AbstractView):

    def __init__(self, novel: Novel, event_types: Optional[List[Any]] = None):
        if event_types:
            events = event_types
        else:
            events = []
        events.append(NovelReloadedEvent)
        super().__init__(events)
        self.novel = novel

    @busy
    @abstractmethod
    def refresh(self):
        pass
