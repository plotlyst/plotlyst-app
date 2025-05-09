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
import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Set

from PyQt6.QtCore import QTimer, QRunnable, QThreadPool, QObject
from overrides import overrides

from plotlyst.core.client import client, json_client
from plotlyst.core.domain import Novel, Character, Scene, NovelDescriptor, Document, Plot, Diagram, \
    WorldBuilding
from plotlyst.env import app_env
from plotlyst.event.core import emit_event
from plotlyst.events import StorylineCharacterAssociationChanged
from plotlyst.view.widget.confirm import confirmed


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
    doc: Optional[Document] = None
    diagram: Optional[Diagram] = None
    world: Optional[WorldBuilding] = None


class RepositoryPersistenceManager(QObject):
    __instance = None

    def __init__(self):
        super(RepositoryPersistenceManager, self).__init__()
        self._operations: List[Operation] = []
        self._pool = QThreadPool.globalInstance()
        self._finished_event = asyncio.Event()
        self._persistence_enabled = True

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

    def set_persistence_enabled(self, enabled: bool):
        self._persistence_enabled = enabled

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
        if self._persistence_enabled:
            self._operations.append(Operation(OperationType.INSERT, novel=novel))
            self._persist_if_test_env()

    def delete_novel(self, novel: Novel):
        if self._persistence_enabled:
            self._operations.append(Operation(OperationType.DELETE, novel=novel))
            self._persist_if_test_env()

    def update_project_novel(self, novel: NovelDescriptor):
        if self._persistence_enabled:
            self._operations.append(Operation(OperationType.UPDATE, novel_descriptor=novel))
            self._persist_if_test_env()

    def update_novel(self, novel: Novel):
        if self._persistence_enabled:
            self._operations.append(Operation(OperationType.UPDATE, novel=novel))
            self._persist_if_test_env()

    def insert_character(self, novel: Novel, character: Character):
        if self._persistence_enabled:
            self._operations.append(Operation(OperationType.INSERT, novel=novel, character=character))
            self._persist_if_test_env()

    def update_character(self, character: Character, update_avatar: bool = False):
        if self._persistence_enabled:
            self._operations.append(Operation(OperationType.UPDATE, character=character, update_image=update_avatar))
        self._persist_if_test_env()

    def delete_character(self, novel: Novel, character: Character):
        if self._persistence_enabled:
            self._operations.append(Operation(OperationType.DELETE, novel=novel, character=character))
            self._persist_if_test_env()

    def update_scene(self, scene: Scene):
        if self._persistence_enabled:
            self._operations.append(Operation(OperationType.UPDATE, scene=scene))
            self._persist_if_test_env()

    def insert_scene(self, novel: Novel, scene: Scene):
        if self._persistence_enabled:
            self._operations.append(Operation(OperationType.INSERT, novel=novel, scene=scene))
            self._persist_if_test_env()

    def delete_scene(self, novel: Novel, scene: Scene):
        if self._persistence_enabled:
            self._operations.append(Operation(OperationType.DELETE, novel=novel, scene=scene))
            self._persist_if_test_env()

    def update_doc(self, novel: Novel, document: Document):
        if self._persistence_enabled:
            self._operations.append(Operation(OperationType.UPDATE, novel=novel, doc=document))
            self._persist_if_test_env()

    def update_diagram(self, novel: Novel, diagram: Diagram):
        if self._persistence_enabled:
            self._operations.append(Operation(OperationType.UPDATE, novel=novel, diagram=diagram))
            self._persist_if_test_env()

    def update_world(self, novel: Novel):
        if self._persistence_enabled:
            self._operations.append(Operation(OperationType.UPDATE, novel=novel, world=novel.world))
            self._persist_if_test_env()

    def delete_doc(self, novel: Novel, document: Document):
        if self._persistence_enabled:
            self._operations.append(Operation(OperationType.DELETE, novel=novel, doc=document))
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
        raise IOError('Could not save Plotlyst workspace')


def _persist_operations(operations: List[Operation]):
    updated_doc_cache: Set[Document] = set()
    updated_novel_cache: Set[Novel] = set()
    updated_scene_cache: Set[Scene] = set()
    updated_character_cache: Set[Character] = set()
    updated_diagram_cache: Set[Diagram] = set()
    updated_world: bool = False

    for op in operations:
        # scenes
        if op.scene and op.type == OperationType.UPDATE:
            if op.scene not in updated_scene_cache:
                client.update_scene(op.scene)
                updated_scene_cache.add(op.scene)
        elif op.scene and op.novel and op.type == OperationType.INSERT:
            client.insert_scene(op.novel, op.scene)
        elif op.scene and op.novel and op.type == OperationType.DELETE:
            client.delete_scene(op.novel, op.scene)

        # characters
        elif op.character and op.type == OperationType.UPDATE:
            if op.character not in updated_character_cache:
                client.update_character(op.character, op.update_image)
                updated_character_cache.add(op.character)
        elif op.character and op.novel and op.type == OperationType.INSERT:
            client.insert_character(op.novel, op.character)
        elif op.character and op.novel and op.type == OperationType.DELETE:
            client.delete_character(op.novel, op.character)

        # novel, document, diagram
        elif op.doc and op.type == OperationType.UPDATE:
            if op.doc not in updated_doc_cache:
                json_client.update_document(op.novel, op.doc)
                updated_doc_cache.add(op.doc)
        elif op.doc and op.type == OperationType.DELETE:
            json_client.delete_document(op.novel, op.doc)

        elif op.diagram and op.type == OperationType.UPDATE:
            if op.diagram not in updated_diagram_cache:
                json_client.update_diagram(op.novel, op.diagram)
                updated_diagram_cache.add(op.diagram)

        elif op.world and op.type == OperationType.UPDATE:
            if not updated_world:
                json_client.update_world(op.novel)
                updated_world = True

        elif op.novel and op.type == OperationType.UPDATE:
            if op.novel not in updated_novel_cache:
                client.update_novel(op.novel)
                updated_novel_cache.add(op.novel)
        elif op.novel and op.type == OperationType.INSERT:
            client.insert_novel(op.novel)
        elif op.novel and op.type == OperationType.DELETE:
            client.delete_novel(op.novel)

        # basic novel descriptor
        elif op.novel_descriptor and op.type == OperationType.UPDATE:
            client.update_project_novel(op.novel_descriptor)

        else:
            logging.error('Unrecognized operation %s', op.type)


def delete_plot(novel: Novel, plot: Plot):
    novel.plots.remove(plot)
    repo = RepositoryPersistenceManager.instance()
    repo.update_novel(novel)

    for scene in novel.scenes:
        before = len(scene.plot_values)
        scene.plot_values = [x for x in scene.plot_values if x.plot.id != plot.id]
        if before != len(scene.plot_values):
            repo.update_scene(scene)


def delete_scene(novel: Novel, scene: Scene, forced: bool = False) -> bool:
    unit = 'scene' if novel.prefs.is_scenes_organization() else 'chapter'
    title = f'Are you sure you want to delete the {unit} "{scene.title_or_index(novel)}"?'
    msg = f'<html>This action cannot be undone.'
    if scene.manuscript and scene.manuscript.statistics and scene.manuscript.statistics.wc:
        msg = f'<html><ul><li>This action cannot be undone.</li>'
        msg += f'<li>Word count number that will be lost: <b>{scene.manuscript.statistics.wc}</b></li>'
    if forced or confirmed(msg, title):
        novel.scenes.remove(scene)
        repo = RepositoryPersistenceManager.instance()
        repo.delete_scene(novel, scene)
        return True

    return False


def delete_character(novel: Novel, character: Character, forced: bool = False) -> bool:
    name = character.name if character.name else 'Unnamed character'
    title = f'Are you sure you want to delete the character "{name}"?'
    msg = "This action cannot be undone, and all this character's information will be lost."
    if forced or confirmed(msg, title):
        novel.characters.remove(character)
        repo = RepositoryPersistenceManager.instance()
        repo.delete_character(novel, character)

        char_id = character.id
        # removed_conflicts = []
        # for conflict in novel.conflicts:
        #     if conflict.character_id == char_id:
        #         removed_conflicts.append(conflict)
        # for conf in removed_conflicts:
        #     novel.conflicts.remove(conf)
        # if removed_conflicts:
        #     repo.update_novel(novel)
        # removed_conflicts = [x.id for x in removed_conflicts]

        for scene in novel.scenes:
            update_scene = False
            if scene.pov is not None and scene.pov.id == char_id:
                scene.pov = None
                update_scene = True
            for char in scene.characters:
                if char.id == char_id:
                    scene.characters.remove(char)
                    update_scene = True
                    break
            for agenda in scene.agency:
                if agenda.character_id == char_id:
                    agenda.conflicts.clear()
                    agenda.motivations.clear()
                    update_scene = True
                    continue

            if update_scene:
                repo.update_scene(scene)

        for plot in novel.plots:
            if plot.character_id == char_id:
                plot.reset_character()
                repo.update_novel(novel)
                emit_event(novel, StorylineCharacterAssociationChanged(QObject(), plot))
            if plot.relation_character_id == char_id:
                plot.reset_relation_character()
                repo.update_novel(novel)

        return True

    return False


def reset_scenes_organization(novel: Novel):
    repo = RepositoryPersistenceManager.instance()
    for scene in novel.scenes:
        if scene.chapter:
            scene.chapter = None
            repo.update_scene(scene)

    novel.chapters.clear()
    repo.update_novel(novel)
