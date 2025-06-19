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
from typing import Optional, Dict, Set, Any, List
from uuid import UUID

from overrides import overrides

from plotlyst.common import recursive
from plotlyst.core.domain import Novel, Scene, StoryBeat, Character, Location, NovelDescriptor
from plotlyst.event.core import EventListener, Event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import SceneChangedEvent, SceneDeletedEvent, SceneStoryBeatChangedEvent, \
    CharacterChangedEvent, CharacterDeletedEvent, LocationAddedEvent, LocationDeletedEvent, WorldEntityAddedEvent, \
    WorldEntityDeletedEvent, ItemLinkedEvent, ItemUnlinkedEvent


class NovelActsRegistry(EventListener):

    def __init__(self):
        self.novel: Optional[Novel] = None
        self._acts_per_scenes: Dict[Scene, int] = {}
        self._beats: Set[StoryBeat] = set()
        self._scenes_per_beats: Dict[StoryBeat, Scene] = {}

    def set_novel(self, novel: Novel):
        self.novel = novel
        dispatcher = event_dispatchers.instance(self.novel)
        dispatcher.register(self, SceneChangedEvent, SceneDeletedEvent, SceneStoryBeatChangedEvent)
        self.refresh()

    @overrides
    def event_received(self, event: Event):
        if self.novel:
            self.refresh()

    def refresh(self):
        self._acts_per_scenes.clear()
        self._scenes_per_beats.clear()
        self._beats.clear()

        act = 1
        for index, scene in enumerate(self.novel.scenes):
            beat: StoryBeat = scene.beat(self.novel)
            if beat is None:
                self._acts_per_scenes[scene] = act
                continue

            self._beats.add(beat)
            self._scenes_per_beats[beat] = scene
            if beat.act > act and not beat.ends_act:
                act = beat.act

            self._acts_per_scenes[scene] = act

            if beat.ends_act:
                act = beat.act + 1

    def act(self, scene: Scene) -> int:
        return self._acts_per_scenes.get(scene, 1)

    def occupied_beats(self) -> Set[StoryBeat]:
        return self._beats

    def scene(self, beat: StoryBeat) -> Optional[Scene]:
        return self._scenes_per_beats.get(beat)

    def occupied(self, beat: StoryBeat) -> bool:
        return beat in self._scenes_per_beats.keys()


acts_registry = NovelActsRegistry()


class EntitiesRegistry(EventListener):
    def __init__(self):
        self.novel: Optional[Novel] = None
        self._characters: Dict[str, Character] = {}
        self._locations: Dict[str, Location] = {}
        self._references: Dict[str, List[Any]] = {}
        self._series: Dict[str, NovelDescriptor] = {}

    def set_novel(self, novel: Novel):
        self.novel = novel
        dispatcher = event_dispatchers.instance(self.novel)
        dispatcher.register(self, CharacterChangedEvent, CharacterDeletedEvent, LocationAddedEvent,
                            LocationDeletedEvent, WorldEntityAddedEvent, WorldEntityDeletedEvent, ItemLinkedEvent,
                            ItemUnlinkedEvent)
        self.refresh()

    def set_series(self, series: List[NovelDescriptor]):
        self._series.clear()

        for ser in series:
            self._series[str(ser.id)] = ser

    def series(self, novel: NovelDescriptor) -> Optional[NovelDescriptor]:
        if novel.parent:
            return self._series.get(str(novel.parent))

    def character(self, s_id: str) -> Optional[Character]:
        return self._characters.get(s_id, None)

    def location(self, s_id: str) -> Optional[Location]:
        return self._locations.get(s_id, None)

    @overrides
    def event_received(self, event: Event):
        if self.novel is None:
            return

        if isinstance(event, (CharacterChangedEvent, CharacterDeletedEvent)):
            self._refreshCharacters()
        elif isinstance(event, LocationAddedEvent):
            self._refreshLocations()
        elif isinstance(event, LocationDeletedEvent):
            self._refreshLocations()
            self._references.pop(str(event.location.id), None)
        elif isinstance(event, WorldEntityAddedEvent):
            if event.entity.ref:
                self.__addReference(event.entity.ref, event.entity)
        elif isinstance(event, WorldEntityDeletedEvent):
            if event.entity.ref:
                self.__removeReference(event.entity, event.entity.ref)
        elif isinstance(event, ItemLinkedEvent):
            self.__addReference(event.item.ref, event.item)
        elif isinstance(event, ItemUnlinkedEvent):
            self.__removeReference(event.item, event.ref)

    def refresh(self):
        self._refreshCharacters()
        self._refreshLocations()
        self._refreshReferences()

    def refs(self, item: Any) -> List[Any]:
        return self._references.get(str(item.id), [])

    def _refreshCharacters(self):
        self._characters.clear()
        for character in self.novel.characters:
            self._characters[str(character.id)] = character

    def _refreshLocations(self):
        def addChild(_: Location, child: Location):
            self._locations[str(child.id)] = child

        self._locations.clear()
        for location in self.novel.locations:
            self._locations[str(location.id)] = location
            recursive(location, lambda parent: parent.children, addChild)

    def _refreshReferences(self):
        def addChild(_: Any, child: Any):
            if child.ref:
                self.__addReference(child.ref, child)

        for entity in self.novel.world.root_entity.children:
            if entity.ref:
                self.__addReference(entity.ref, entity)
            recursive(entity, lambda parent: parent.children, addChild)

    def __addReference(self, id: UUID, ref: Any):
        if str(id) not in self._references.keys():
            self._references[str(id)] = []
        self._references[str(id)].append(ref)

    def __removeReference(self, source: Any, id: UUID):
        self._references[str(id)].remove(source)


entities_registry = EntitiesRegistry()


def try_location(item) -> Optional[Location]:
    if item.ref:
        location = entities_registry.location(str(item.ref))
        if location:
            return location
        else:
            item.ref = None
