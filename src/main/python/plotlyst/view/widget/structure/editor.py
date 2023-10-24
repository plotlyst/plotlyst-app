"""
Plotlyst
Copyright (C) 2021-2023  Zsolt Kovari

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

import copy
from functools import partial
from typing import Optional

import qtanim
from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtWidgets import QWidget, QPushButton, QSizePolicy, QButtonGroup
from overrides import overrides
from qthandy import translucent, gc, flow, ask_confirmation, hbox
from qthandy.filter import OpacityEventFilter

from src.main.python.plotlyst.core.domain import StoryStructure, Novel, StoryBeat, \
    Character
from src.main.python.plotlyst.event.core import EventListener, Event, emit_event
from src.main.python.plotlyst.event.handler import event_dispatchers
from src.main.python.plotlyst.events import NovelStoryStructureUpdated, CharacterChangedEvent, CharacterDeletedEvent, \
    NovelSyncEvent, NovelStoryStructureActivationRequest
from src.main.python.plotlyst.service.cache import acts_registry
from src.main.python.plotlyst.service.persistence import RepositoryPersistenceManager
from src.main.python.plotlyst.view.common import ButtonPressResizeEventFilter
from src.main.python.plotlyst.view.generated.story_structure_settings_ui import Ui_StoryStructureSettings
from src.main.python.plotlyst.view.icons import IconRegistry, avatars
from src.main.python.plotlyst.view.widget.characters import CharacterSelectorMenu
from src.main.python.plotlyst.view.widget.scenes import SceneStoryStructureWidget
from src.main.python.plotlyst.view.widget.structure.beat import BeatsPreview
from src.main.python.plotlyst.view.widget.structure.selector import StoryStructureSelectorDialog


class _StoryStructureButton(QPushButton):
    def __init__(self, structure: StoryStructure, novel: Novel, parent=None):
        super(_StoryStructureButton, self).__init__(parent)
        self._structure = structure
        self.novel = novel
        self.setText(structure.title)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Maximum)

        self.setStyleSheet('''
            QPushButton {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 0,
                                      stop: 0 #f8edeb);
                border: 2px solid #fec89a;
                border-radius: 6px;
                padding: 2px;
            }
            QPushButton:checked {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 0,
                                      stop: 0 #ffd7ba);
                border: 3px solid #FD9235;
                padding: 1px;
            }
            ''')

        self.refresh()

        self._toggled(self.isChecked())
        self.installEventFilter(OpacityEventFilter(self, 0.7, 0.5, ignoreCheckedButton=True))
        self.toggled.connect(self._toggled)

    def structure(self) -> StoryStructure:
        return self._structure

    def refresh(self, animated: bool = False):
        if self._structure.character_id:
            self.setIcon(avatars.avatar(self._structure.character(self.novel)))
        elif self._structure.icon:
            self.setIcon(IconRegistry.from_name(self._structure.icon, self._structure.icon_color))

        if animated:
            qtanim.glow(self, radius=15, loop=3)

    def _toggled(self, toggled: bool):
        translucent(self, 1.0 if toggled else 0.5)
        font = self.font()
        font.setBold(toggled)
        self.setFont(font)


class StoryStructureNotes(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def setStructure(self, structure: StoryStructure):
        pass


class StoryStructureEditor(QWidget, Ui_StoryStructureSettings, EventListener):
    def __init__(self, parent=None):
        super(StoryStructureEditor, self).__init__(parent)
        self.setupUi(self)
        flow(self.wdgTemplates)

        self.btnNew.setIcon(IconRegistry.plus_icon('white'))
        self.btnNew.installEventFilter(ButtonPressResizeEventFilter(self.btnNew))
        self.btnNew.clicked.connect(self._selectTemplateStructure)

        self.btnDelete.setIcon(IconRegistry.trash_can_icon())
        self.btnDelete.installEventFilter(ButtonPressResizeEventFilter(self.btnDelete))
        self.btnDelete.installEventFilter(OpacityEventFilter(self.btnDelete, leaveOpacity=0.8))
        self.btnDelete.clicked.connect(self._removeStructure)
        self.btnCopy.setIcon(IconRegistry.copy_icon())
        self.btnCopy.installEventFilter(ButtonPressResizeEventFilter(self.btnCopy))
        self.btnCopy.installEventFilter(OpacityEventFilter(self.btnCopy, leaveOpacity=0.8))
        self.btnCopy.clicked.connect(self._duplicateStructure)
        self.btnEdit.setIcon(IconRegistry.edit_icon())
        self.btnEdit.installEventFilter(ButtonPressResizeEventFilter(self.btnEdit))
        self.btnEdit.installEventFilter(OpacityEventFilter(self.btnEdit, leaveOpacity=0.8))
        self.btnEdit.clicked.connect(self._editStructure)
        self.btnLinkCharacter.setIcon(IconRegistry.character_icon())
        self.btnLinkCharacter.installEventFilter(ButtonPressResizeEventFilter(self.btnLinkCharacter))
        self.btnLinkCharacter.installEventFilter(OpacityEventFilter(self.btnLinkCharacter, leaveOpacity=0.8))

        self._characterMenu: Optional[CharacterSelectorMenu] = None

        self.btnGroupStructure = QButtonGroup()
        self.btnGroupStructure.setExclusive(True)

        self._beatsPreview: Optional[BeatsPreview] = None

        self.__initWdgPreview()

        self.novel: Optional[Novel] = None
        self.beats.installEventFilter(self)
        self.repo = RepositoryPersistenceManager.instance()

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, CharacterDeletedEvent):
            for btn in self.btnGroupStructure.buttons():
                structure: StoryStructure = btn.structure()
                if structure.character_id == event.character.id:
                    structure.reset_character()
                    btn.refresh()
                    self.repo.update_novel(self.novel)
        elif isinstance(event, NovelStoryStructureActivationRequest):
            for btn in self.btnGroupStructure.buttons():
                if btn.structure() is event.structure:
                    btn.setChecked(True)
            self.repo.update_novel(self.novel)
            emit_event(self.novel, NovelStoryStructureUpdated(self))
            return

        self._activeStructureToggled(self.novel.active_story_structure, True)

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Leave:
            self.wdgPreview.unhighlightBeats()

        return super(StoryStructureEditor, self).eventFilter(watched, event)

    def setNovel(self, novel: Novel):
        self.novel = novel
        dispatcher = event_dispatchers.instance(self.novel)
        dispatcher.register(self, CharacterChangedEvent, CharacterDeletedEvent, NovelSyncEvent,
                            NovelStoryStructureActivationRequest)

        self._characterMenu = CharacterSelectorMenu(self.novel, self.btnLinkCharacter)
        self._characterMenu.selected.connect(self._characterLinked)

        self._beatsPreview = BeatsPreview(self.novel)
        hbox(self.beats, 0, 0).addWidget(self._beatsPreview)
        self._beatsPreview.attachStructurePreview(self.wdgPreview)

        for structure in self.novel.story_structures:
            self._addStructureWidget(structure)

    def _addStructureWidget(self, structure: StoryStructure):
        btn = _StoryStructureButton(structure, self.novel)
        btn.toggled.connect(partial(self._activeStructureToggled, structure))
        btn.clicked.connect(partial(self._activeStructureClicked, structure))
        self.btnGroupStructure.addButton(btn)
        self.wdgTemplates.layout().addWidget(btn)
        if structure.active:
            btn.setChecked(True)

        self._toggleDeleteButton()

    def _addNewStructure(self, structure: StoryStructure):
        self.novel.story_structures.append(structure)
        self._addStructureWidget(structure)
        self.btnGroupStructure.buttons()[-1].setChecked(True)
        emit_event(self.novel, NovelStoryStructureUpdated(self))

    def _removeStructure(self):
        if len(self.novel.story_structures) < 2:
            return

        structure = self.novel.active_story_structure
        if not ask_confirmation(f'Remove structure "{structure.title}"?'):
            return

        to_be_removed_button: Optional[QPushButton] = None
        for btn in self.btnGroupStructure.buttons():
            if btn.structure() is structure:
                to_be_removed_button = btn
                break
        if not to_be_removed_button:
            return

        self.btnGroupStructure.removeButton(to_be_removed_button)
        self.wdgTemplates.layout().removeWidget(to_be_removed_button)
        gc(to_be_removed_button)
        self.novel.story_structures.remove(structure)
        if self.btnGroupStructure.buttons():
            self.btnGroupStructure.buttons()[-1].setChecked(True)
            emit_event(self.novel, NovelStoryStructureUpdated(self))
        self.repo.update_novel(self.novel)

        self._toggleDeleteButton()

    def _duplicateStructure(self):
        structure = copy.deepcopy(self.novel.active_story_structure)
        self._addNewStructure(structure)
        self._editStructure()

    def _editStructure(self):
        StoryStructureSelectorDialog.display(self.novel, self.novel.active_story_structure)
        self._activeStructureToggled(self.novel.active_story_structure, True)
        emit_event(self.novel, NovelStoryStructureUpdated(self))

    def _characterLinked(self, character: Character):
        self.novel.active_story_structure.set_character(character)
        self.btnGroupStructure.checkedButton().refresh(True)
        self.repo.update_novel(self.novel)
        self._activeStructureToggled(self.novel.active_story_structure, True)
        emit_event(self.novel, NovelStoryStructureUpdated(self))

    def _selectTemplateStructure(self):
        structure: Optional[StoryStructure] = StoryStructureSelectorDialog.display(self.novel)
        if structure:
            self._addNewStructure(structure)

    def _activeStructureToggled(self, structure: StoryStructure, toggled: bool):
        if not toggled:
            return

        for struct in self.novel.story_structures:
            struct.active = False
        structure.active = True
        acts_registry.refresh()
        self._beatsPreview.setStructure(structure)

        if self.wdgPreview.novel is not None:
            item = self.layoutPreview.takeAt(0)
            gc(item.widget())
            self.wdgPreview = SceneStoryStructureWidget(self)
            self.__initWdgPreview()
            self.layoutPreview.addWidget(self.wdgPreview)
        self.wdgPreview.setStructure(self.novel)

    def _activeStructureClicked(self, _: StoryStructure, toggled: bool):
        if not toggled:
            return

        self.repo.update_novel(self.novel)
        emit_event(self.novel, NovelStoryStructureUpdated(self))

    def __initWdgPreview(self):
        self.wdgPreview.setCheckOccupiedBeats(False)
        self.wdgPreview.setBeatCursor(Qt.CursorShape.ArrowCursor)
        self.wdgPreview.setBeatsMoveable(True)
        self.wdgPreview.setActsClickable(False)
        self.wdgPreview.setActsResizeable(True)
        self.wdgPreview.actsResized.connect(lambda: emit_event(self.novel, NovelStoryStructureUpdated(self)))
        self.wdgPreview.beatMoved.connect(lambda: emit_event(self.novel, NovelStoryStructureUpdated(self)))

    def _beatToggled(self, beat: StoryBeat):
        self.wdgPreview.toggleBeatVisibility(beat)
        self.repo.update_novel(self.novel)

    def _toggleDeleteButton(self):
        self.btnDelete.setEnabled(len(self.novel.story_structures) > 1)
