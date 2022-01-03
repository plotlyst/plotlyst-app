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
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from PyQt6.QtCore import QTimer, QRunnable, QThreadPool, QObject
from overrides import overrides

from src.main.python.plotlyst.core.client import client
from src.main.python.plotlyst.core.domain import Novel, Character, Scene, NovelDescriptor
from src.main.python.plotlyst.env import app_env


class OperationType(Enum):
    DELETE = 0
    INSERT = 1
    UPDATE = 2


@dataclass
class Operation:
    type: OperationType
    novel_descriptor: Optional[NovelDescriptor] = None
    novel: Optional[Novel] = None
    character: Optional[Character] = None
    scene: Optional[Scene] = None
    update_image: bool = False


class RepositoryPersistenceManager(QObject):
    __instance = None

    def __init__(self):
        super(RepositoryPersistenceManager, self).__init__()
        self._operations: List[Operation] = []
        self._pool = QThreadPool.globalInstance()
        self._finished_event = asyncio.Event()

        self._timer = QTimer()
        self._timer.setInterval(60 * 1000)  # 1 min
        self._timer.timeout.connect(self.flush)
        if not app_env.test_env():
            self._timer.start()

    @classmethod
    def instance(cls):
        if not cls.__instance:
            cls.__instance = RepositoryPersistenceManager()
        return cls.__instance

    def flush(self, sync: bool = False) -> bool:
        if self._finished_event.is_set():
            return False

        if self._operations:
            operations_to_persist = []
            operations_to_persist.extend(self._operations)
            if sync:
                _persist_operations(operations_to_persist)
            else:
                self._finished_event.set()
                _runnable = _PersistenceRunnable(operations_to_persist, self._finished_event)
                self._pool.start(_runnable)
            self._operations.clear()

        return True

    def insert_novel(self, novel: Novel):
        self._operations.append(Operation(OperationType.INSERT, novel=novel))
        self._persist_if_test_env()

    def delete_novel(self, novel: Novel):
        self._operations.append(Operation(OperationType.DELETE, novel=novel))
        self._persist_if_test_env()

    def update_project_novel(self, novel: NovelDescriptor):
        self._operations.append(Operation(OperationType.UPDATE, novel_descriptor=novel))
        self._persist_if_test_env()

    def update_novel(self, novel: Novel):
        self._operations.append(Operation(OperationType.UPDATE, novel=novel))
        self._persist_if_test_env()

    def insert_character(self, novel: Novel, character: Character):
        self._operations.append(Operation(OperationType.INSERT, novel=novel, character=character))
        self._persist_if_test_env()

    def update_character(self, character: Character, update_avatar: bool = False):
        self._operations.append(Operation(OperationType.UPDATE, character=character, update_image=update_avatar))
        self._persist_if_test_env()

    def delete_character(self, novel: Novel, character: Character):
        self._operations.append(Operation(OperationType.DELETE, novel=novel, character=character))
        self._persist_if_test_env()

    def update_scene(self, scene: Scene):
        self._operations.append(Operation(OperationType.UPDATE, scene=scene))
        self._persist_if_test_env()

    def insert_scene(self, novel: Novel, scene: Scene):
        self._operations.append(Operation(OperationType.INSERT, novel=novel, scene=scene))
        self._persist_if_test_env()

    def delete_scene(self, novel: Novel, scene: Scene):
        self._operations.append(Operation(OperationType.DELETE, novel=novel, scene=scene))
        self._persist_if_test_env()

    def _persist_if_test_env(self):
        if app_env.test_env():
            _persist_operations(self._operations)
            self._operations.clear()


class _PersistenceRunnable(QRunnable):
    def __init__(self, operations: List[Operation], finished: asyncio.Event):
        super(_PersistenceRunnable, self).__init__()
        self.operations = operations
        self.finished = finished

    @overrides
    def run(self) -> None:
        try:
            _persist_operations(self.operations)
        finally:
            self.finished.clear()


def flush_or_fail():
    attempts = 0
    repo = RepositoryPersistenceManager.instance()
    while not repo.flush(sync=True) and attempts < 30:
        time.sleep(1)
        attempts += 1
    if attempts >= 30:
        raise IOError('Could not save novel')


def _persist_operations(operations: List[Operation]):
    for op in operations:
        if op.scene and op.type == OperationType.UPDATE:
            client.update_scene(op.scene)
        elif op.scene and op.novel and op.type == OperationType.INSERT:
            client.insert_scene(op.novel, op.scene)
        elif op.scene and op.novel and op.type == OperationType.DELETE:
            client.delete_scene(op.novel, op.scene)

        elif op.character and op.type == OperationType.UPDATE:
            client.update_character(op.character, op.update_image)
        elif op.character and op.novel and op.type == OperationType.INSERT:
            client.insert_character(op.novel, op.character)
        elif op.character and op.novel and op.type == OperationType.DELETE:
            client.delete_character(op.novel, op.character)

        elif op.novel and op.type == OperationType.UPDATE:
            client.update_novel(op.novel)
        elif op.novel and op.type == OperationType.INSERT:
            client.insert_novel(op.novel)
        elif op.novel and op.type == OperationType.DELETE:
            client.delete_novel(op.novel)

        elif op.novel_descriptor and op.type == OperationType.UPDATE:
            client.update_project_novel(op.novel_descriptor)

        else:
            logging.error('Unrecognized operation %s', op.type)
