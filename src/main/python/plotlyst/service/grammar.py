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
import logging
from typing import Optional, Set

import language_tool_python
from PyQt6.QtCore import QRunnable
from language_tool_python import LanguageTool
from language_tool_python.download_lt import LATEST_VERSION
from overrides import overrides

from plotlyst.core.domain import Novel, Event, Location
from plotlyst.event.core import emit_global_event, emit_info, EventListener
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import LanguageToolSet, CharacterChangedEvent, RequestMilieuDictionaryResetEvent


class LanguageToolServerSetupWorker(QRunnable):

    def __init__(self, lang: str = 'en-US'):
        super(LanguageToolServerSetupWorker, self).__init__()
        self.lang = lang

    @overrides
    def run(self) -> None:
        try:
            tool = language_tool_python.LanguageTool(self.lang, config={'cacheSize': 1000, 'pipelineCaching': True})
            tool.check('Test sentence.')
            language_tool_proxy.set(tool)
        except Exception as e:
            language_tool_proxy.set_error(str(e))


class LanguageToolProxy:

    def __init__(self):
        self._language_tool: Optional[LanguageTool] = None
        self._error: Optional[str] = None

    def set(self, language_tool: LanguageTool):
        self._language_tool = language_tool
        self._error = None
        logging.info(f'Grammar checker was set up with version {LATEST_VERSION}.')
        emit_info('Grammar checker was set up.')
        emit_global_event(LanguageToolSet(self, self._language_tool))

    def set_error(self, error_msg: str):
        self._error = error_msg
        logging.error(self._error)
        emit_info('Could not initialize LanguageTool grammar checker')

    def is_set(self) -> bool:
        return self._language_tool is not None

    def is_failed(self) -> bool:
        return self._error is not None

    @property
    def error(self) -> Optional[str]:
        return self._error

    @property
    def tool(self) -> LanguageTool:
        if self.is_set():
            return self._language_tool
        else:
            raise IOError('LanguageTool local server was not initialized yet')


language_tool_proxy = LanguageToolProxy()


class Dictionary(EventListener):
    def __init__(self):
        self.novel: Optional[Novel] = None
        self.words: Set[str] = set()

    @overrides
    def event_received(self, event: Event):
        self.refresh()

    def set_novel(self, novel: Novel):
        self.novel = novel
        dispatcher = event_dispatchers.instance(self.novel)
        dispatcher.register(self, CharacterChangedEvent, RequestMilieuDictionaryResetEvent)
        self.refresh()

    def refresh(self):
        self.words.clear()
        for character in self.novel.characters:
            self.words.add(character.name)
            if character.alias:
                self.words.add(character.alias)
        for location in self.novel.locations:
            self._add_locations(location)

    def _add_locations(self, location: Location):
        self.words.add(location.name)
        for child in location.children:
            self._add_locations(child)

    def is_known_word(self, word: str) -> bool:
        return word in self.words or word in self.novel.world.glossary


dictionary = Dictionary()
