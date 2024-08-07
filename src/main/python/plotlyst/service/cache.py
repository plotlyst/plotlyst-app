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
from typing import Optional, Dict, Set

from overrides import overrides

from plotlyst.core.domain import Novel, Scene, StoryBeat, Character
from plotlyst.event.core import EventListener, Event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import SceneChangedEvent, SceneDeletedEvent, SceneStoryBeatChangedEvent, \
    CharacterChangedEvent, CharacterDeletedEvent


class NovelActsRegistry(EventListener):

    def __init__(self):
        self.novel: Optional[Novel] = None
        self._acts_per_scenes: Dict[Scene, int] = {}
        self._beats: Set[StoryBeat] = set()
        self._scenes_per_beats: Dict[StoryBeat, Scene] = {}
        self._acts_endings: Dict[int, int] = {}

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
        self._acts_endings.clear()

        act = 1
        for index, scene in enumerate(self.novel.scenes):
            self._acts_per_scenes[scene] = act

            beat = scene.beat(self.novel)
            if beat:
                self._beats.add(beat)
                self._scenes_per_beats[beat] = scene
                if beat.ends_act:
                    self._acts_endings[beat.act] = index
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


class CharactersRegistry(EventListener):
    def __init__(self, parent=None):
        self.novel: Optional[Novel] = None
        self._characters: Dict[str, Character] = {}

    def set_novel(self, novel: Novel):
        self.novel = novel
        dispatcher = event_dispatchers.instance(self.novel)
        dispatcher.register(self, CharacterChangedEvent, CharacterDeletedEvent)
        self.refresh()

    def character(self, s_id: str) -> Optional[Character]:
        return self._characters.get(s_id, None)

    @overrides
    def event_received(self, event: Event):
        if self.novel:
            self.refresh()

    def refresh(self):
        if self.novel:
            self._characters.clear()
            for character in self.novel.characters:
                self._characters[str(character.id)] = character


characters_registry = CharactersRegistry()
