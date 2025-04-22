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
from typing import List, Any, Optional

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QWidget, QButtonGroup
from overrides import overrides
from qthandy import busy

from plotlyst.core.domain import Novel
from plotlyst.env import app_env
from plotlyst.event.core import EventListener, Event
from plotlyst.event.handler import global_event_dispatcher, event_dispatchers
from plotlyst.events import CharacterDeletedEvent, NovelSyncEvent
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.service.tour import TourService
from plotlyst.view.dialog.novel import DetachedWindow


class AbstractView(QObject, EventListener):

    def __init__(self, global_event_types: Optional[List[Any]] = None):
        super().__init__(None)
        self._refresh_on_activation: bool = False
        self.widget = QWidget()
        self.title: Optional[QWidget] = None
        self._navigable_button_group: Optional[QButtonGroup] = None
        if global_event_types:
            self._global_event_types = global_event_types
        else:
            self._global_event_types = []

        for event in self._global_event_types:
            global_event_dispatcher.register(self, event)

        self._tour_service = TourService.instance()
        self.repo = RepositoryPersistenceManager.instance()

    def setNavigableButtonGroup(self, group: QButtonGroup):
        self._navigable_button_group = group
        for i, btn in enumerate(self._navigable_button_group.buttons()):
            self._navigable_button_group.setId(btn, i)
            btn.setShortcut(f"{i + 1}")

    @overrides
    def event_received(self, event: Event):
        if self.widget.isVisible():
            self.refresh()
        else:
            self._refresh_on_activation = True

    def activate(self):
        if self._refresh_on_activation:
            if app_env.test_env():
                self.refresh()
            else:
                QTimer.singleShot(10, self.refresh)
            self._refresh_on_activation = False

    @abstractmethod
    def refresh(self):
        pass

    def jumpToPrevious(self):
        if self._navigable_button_group is None:
            return

        id_ = self._navigable_button_group.checkedId()
        if id_ == 0:
            id_ = len(self._navigable_button_group.buttons()) - 1
        else:
            id_ -= 1
        self._navigable_button_group.button(id_).setChecked(True)

    def jumpToNext(self):
        if self._navigable_button_group is None:
            return

        id_ = self._navigable_button_group.checkedId()
        if id_ == len(self._navigable_button_group.buttons()) - 1:
            id_ = 0
        else:
            id_ += 1
        self._navigable_button_group.button(id_).setChecked(True)


class AbstractNovelView(AbstractView):

    def __init__(self, novel: Novel, event_types: Optional[List[Any]] = None,
                 global_event_types: Optional[List[Any]] = None):
        events = event_types if event_types else []

        if CharacterDeletedEvent not in events:
            events.append(CharacterDeletedEvent)
        if NovelSyncEvent not in events:
            events.append(NovelSyncEvent)
        super().__init__(global_event_types)

        self.novel = novel
        self._detached: bool = False
        self._old_parent: Optional[QWidget] = None
        self._dispatcher = event_dispatchers.instance(self.novel)
        self._dispatcher.register(self, *events)

    def isDetached(self) -> bool:
        return self._detached

    def detach(self) -> Optional[DetachedWindow]:
        if self._detached:
            return None

        self._old_parent = self.widget.parent()
        self._old_parent.layout().removeWidget(self.widget)
        window = DetachedWindow(self.widget)
        self._detached = True
        return window

    def restore(self):
        self._old_parent.layout().addWidget(self.widget)
        self._detached = False

    @busy
    @abstractmethod
    def refresh(self):
        pass
