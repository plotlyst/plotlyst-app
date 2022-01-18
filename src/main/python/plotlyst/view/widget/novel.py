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
import copy
from functools import partial
from typing import Optional

from PyQt5.QtCore import Qt, QEvent, QObject, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QPushButton, QSizePolicy, QFrame, QButtonGroup
from overrides import overrides

from src.main.python.plotlyst.core.domain import StoryStructure, Novel, StoryBeat, \
    three_act_structure, save_the_cat, weiland_10_beats, Character, story_circle
from src.main.python.plotlyst.event.core import emit_event, EventListener, Event
from src.main.python.plotlyst.event.handler import event_dispatcher
from src.main.python.plotlyst.events import NovelStoryStructureUpdated
from src.main.python.plotlyst.view.common import set_opacity, OpacityEventFilter, transparent, spacer_widget, bold, \
    popup, gc
from src.main.python.plotlyst.view.generated.beat_widget_ui import Ui_BeatWidget
from src.main.python.plotlyst.view.generated.story_structure_character_link_widget_ui import \
    Ui_StoryStructureCharacterLink
from src.main.python.plotlyst.view.generated.story_structure_selector_ui import Ui_StoryStructureSelector
from src.main.python.plotlyst.view.generated.story_structure_settings_ui import Ui_StoryStructureSettings
from src.main.python.plotlyst.view.icons import IconRegistry, avatars
from src.main.python.plotlyst.view.layout import FlowLayout, clear_layout
from src.main.python.plotlyst.view.widget.scenes import SceneStoryStructureWidget
from src.main.python.plotlyst.worker.persistence import RepositoryPersistenceManager


class _StoryStructureButton(QPushButton):
    def __init__(self, structure: StoryStructure, novel: Novel, parent=None):
        super(_StoryStructureButton, self).__init__(parent)
        self._structure = structure
        self.novel = novel
        self.setText(structure.title)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Maximum)
        if self._structure.character_id:
            self.setIcon(QIcon(avatars.pixmap(self._structure.character(self.novel))))
        elif self._structure.icon:
            self.setIcon(IconRegistry.from_name(self._structure.icon, self._structure.icon_color))

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
        self._toggled(self.isChecked())
        self.installEventFilter(OpacityEventFilter(0.7, 0.5, self, ignoreCheckedButton=True))
        self.toggled.connect(self._toggled)

    def structure(self) -> StoryStructure:
        return self._structure

    def _toggled(self, toggled: bool):
        set_opacity(self, 1.0 if toggled else 0.5)
        font = self.font()
        font.setBold(toggled)
        self.setFont(font)


class BeatWidget(QFrame, Ui_BeatWidget):
    beatHighlighted = pyqtSignal(StoryBeat)
    beatToggled = pyqtSignal(StoryBeat)

    def __init__(self, beat: StoryBeat, parent=None):
        super(BeatWidget, self).__init__(parent)
        self.setupUi(self)
        self.beat = beat
        self.lblTitle.setText(self.beat.text)
        self.lblDescription.setText(f'Description of this beat {self.beat.text}')
        transparent(self.lblTitle)
        transparent(self.lblDescription)
        transparent(self.btnIcon)
        if beat.icon:
            self.btnIcon.setIcon(IconRegistry.from_name(beat.icon, beat.icon_color))
        self.lblTitle.setStyleSheet(f'color: {beat.icon_color};')

        self.cbToggle.setHidden(True)
        if not self._canBeToggled():
            self.cbToggle.setDisabled(True)
        self.cbToggle.toggled.connect(self._beatToggled)
        self.cbToggle.clicked.connect(self._beatClicked)
        self.cbToggle.setChecked(self.beat.enabled)

        self.repo = RepositoryPersistenceManager.instance()

        self.installEventFilter(self)

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Enter:
            if self._canBeToggled():
                self.cbToggle.setVisible(True)
            self.setStyleSheet('.BeatWidget {background-color: #DBF5FA;}')
            self.beatHighlighted.emit(self.beat)
        elif event.type() == QEvent.Leave:
            if self._canBeToggled():
                self.cbToggle.setHidden(True)
            self.setStyleSheet('.BeatWidget {background-color: white;}')

        return super(BeatWidget, self).eventFilter(watched, event)

    def _canBeToggled(self):
        if self.beat.text == 'Midpoint' or self.beat.ends_act:
            return False
        return True

    def _beatToggled(self, toggled: bool):
        set_opacity(self, 1 if toggled else 0.3)
        bold(self.lblTitle, toggled)

    def _beatClicked(self, checked: bool):
        self.beat.enabled = checked
        self.beatToggled.emit(self.beat)


class StoryStructureSelector(QWidget, Ui_StoryStructureSelector):
    structureClicked = pyqtSignal(StoryStructure, bool)

    def __init__(self, parent=None):
        super(StoryStructureSelector, self).__init__(parent)
        self.setupUi(self)
        self.novel: Optional[Novel] = None
        self.cb3act.clicked.connect(partial(self.structureClicked.emit, three_act_structure))
        self.cbWeiland10Beats.clicked.connect(partial(self.structureClicked.emit, weiland_10_beats))
        self.cbSaveTheCat.clicked.connect(partial(self.structureClicked.emit, save_the_cat))
        self.cbStoryCircle.clicked.connect(partial(self.structureClicked.emit, story_circle))
        self.buttonGroup.buttonToggled.connect(self._btnToggled)

    def setNovel(self, novel: Novel):
        self.novel = novel

        self.cb3act.setChecked(False)
        self.cbWeiland10Beats.setChecked(False)
        self.cbSaveTheCat.setChecked(False)

        for structure in self.novel.story_structures:
            if structure.id == three_act_structure.id:
                self.cb3act.setChecked(True)
            elif structure.id == weiland_10_beats.id:
                self.cbWeiland10Beats.setChecked(True)
            elif structure.id == save_the_cat.id:
                self.cbSaveTheCat.setChecked(True)

    def _btnToggled(self):
        checked_buttons = []
        for btn in self.buttonGroup.buttons():
            btn.setVisible(True)
            if btn.isChecked():
                if checked_buttons:
                    return
                checked_buttons.append(btn)

        if len(checked_buttons) == 1:
            checked_buttons[0].setHidden(True)


class StoryStructureCharacterLinkWidget(QWidget, Ui_StoryStructureCharacterLink, EventListener):
    linkCharacter = pyqtSignal(Character)
    unlinkCharacter = pyqtSignal(Character)

    def __init__(self, novel: Novel, parent=None):
        super(StoryStructureCharacterLinkWidget, self).__init__(parent)
        self.setupUi(self)
        self.novel = novel
        self.wdgCharacters.setExclusive(False)
        self.wdgCharacters.setCharacters(novel.characters, checkAll=False)
        self.wdgCharacters.characterToggled.connect(self._characterToggled)
        event_dispatcher.register(self, NovelStoryStructureUpdated)

        self.refresh()

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, NovelStoryStructureUpdated):
            self.refresh()

    def refresh(self):
        self.wdgCharacters.clear()
        for char in self.novel.characters:
            if char is self.novel.active_story_structure.character(self.novel):
                self.wdgCharacters.addCharacter(char)
            else:
                self.wdgCharacters.addCharacter(char, checked=False)

    def _characterToggled(self, character: Character, toggled: bool):
        if toggled:
            self.linkCharacter.emit(character)
        else:
            self.unlinkCharacter.emit(character)


class StoryStructureEditor(QWidget, Ui_StoryStructureSettings):
    def __init__(self, parent=None):
        super(StoryStructureEditor, self).__init__(parent)
        self.setupUi(self)
        self.wdgTemplates.setLayout(FlowLayout(2, 3))

        self.btnTemplateEditor.setIcon(IconRegistry.plus_edit_icon())
        self.btnLinkCharacter.setIcon(IconRegistry.character_icon())
        self.btnLinkCharacter.setStyleSheet('''
            QPushButton {
                border: 2px dotted grey;
                border-radius: 6px;
                font: italic;
            }
            QPushButton:hover {
                border: 2px dotted darkBlue;
            }
        ''')
        self.wdgCharacterLink: Optional[StoryStructureCharacterLinkWidget] = None
        self.structureSelector = StoryStructureSelector(self.btnTemplateEditor)
        self.structureSelector.structureClicked.connect(self._structureSelectionChanged)
        popup(self.btnTemplateEditor, self.structureSelector, hideMenuIcon=False)
        self.btnGroupStructure = QButtonGroup()
        self.btnGroupStructure.setExclusive(True)

        self.novel: Optional[Novel] = None
        self.beats.installEventFilter(self)
        self.repo = RepositoryPersistenceManager.instance()

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Leave:
            self.wdgPreview.unhighlightBeats()

        return super(StoryStructureEditor, self).eventFilter(watched, event)

    def setNovel(self, novel: Novel):
        self.novel = novel
        self.wdgCharacterLink = StoryStructureCharacterLinkWidget(self.novel)
        self.wdgCharacterLink.linkCharacter.connect(self._linkCharacter)
        self.wdgCharacterLink.unlinkCharacter.connect(self._unlinkCharacter)
        popup(self.btnLinkCharacter, self.wdgCharacterLink)
        self.structureSelector.setNovel(self.novel)
        for structure in self.novel.story_structures:
            self._addStructure(structure)

    def _addStructure(self, structure: StoryStructure):
        btn = _StoryStructureButton(structure, self.novel)
        btn.toggled.connect(partial(self._activeStructureToggled, structure))
        btn.clicked.connect(partial(self._activeStructureClicked, structure))
        self.btnGroupStructure.addButton(btn)
        self.wdgTemplates.layout().addWidget(btn)
        if structure.active:
            btn.setChecked(True)

    def _removeStructure(self, structure: StoryStructure):
        to_be_removed = []
        activate_new = False
        for btn in self.btnGroupStructure.buttons():
            if btn.structure().id == structure.id and btn.structure().character_id == structure.character_id:
                to_be_removed.append(btn)
                if btn.isChecked():
                    activate_new = True

        for btn in to_be_removed:
            self.btnGroupStructure.removeButton(btn)
            self.wdgTemplates.layout().removeWidget(btn)
            gc(btn)
        if activate_new and self.btnGroupStructure.buttons():
            self.btnGroupStructure.buttons()[0].setChecked(True)
            emit_event(NovelStoryStructureUpdated(self))

    def _linkCharacter(self, character: Character):
        new_structure = copy.deepcopy(self.novel.active_story_structure)
        new_structure.set_character(character)
        self.novel.story_structures.append(new_structure)
        self._addStructure(new_structure)
        self.repo.update_novel(self.novel)
        emit_event(NovelStoryStructureUpdated(self))

    def _unlinkCharacter(self, character: Character):
        active_structure_id = self.novel.active_story_structure.id
        matched_structures = [x for x in self.novel.story_structures if
                              x.id == active_structure_id and x.character_id == character.id]
        if matched_structures:
            for st in matched_structures:
                self.novel.story_structures.remove(st)
                self._removeStructure(st)

    def _activeStructureToggled(self, structure: StoryStructure, toggled: bool):
        if not toggled:
            return
        clear_layout(self.beats.layout())

        for struct in self.novel.story_structures:
            struct.active = False
        structure.active = True

        if self.wdgPreview.novel is not None:
            item = self.layout().takeAt(1)
            item.widget().deleteLater()
            self.wdgPreview = SceneStoryStructureWidget(self)
            self.layout().insertWidget(1, self.wdgPreview)
        self.wdgPreview.setNovel(self.novel, checkOccupiedBeats=False)
        row = 0
        col = 0
        for beat in structure.beats:
            wdg = BeatWidget(beat)
            if beat.act - 1 > col:  # new act
                self.beats.layout().addWidget(spacer_widget(vertical=True), row + 1, col)
                col = beat.act - 1
                row = 0
            self.beats.layout().addWidget(wdg, row, col)
            row += 1
            wdg.beatHighlighted.connect(self.wdgPreview.highlightBeat)
            wdg.beatToggled.connect(self._beatToggled)

    def _activeStructureClicked(self, structure: StoryStructure, toggled: bool):
        if not toggled:
            return

        self.repo.update_novel(self.novel)
        emit_event(NovelStoryStructureUpdated(self))

    def _beatToggled(self, beat: StoryBeat):
        self.wdgPreview.toggleBeatVisibility(beat)
        self.repo.update_novel(self.novel)

    def _structureSelectionChanged(self, structure: StoryStructure, toggled: bool):
        if toggled:
            if structure.id == story_circle.id:
                print('circle add')
                pass
            else:
                self.novel.story_structures.append(structure)
                self._addStructure(structure)
        else:
            if structure.id == story_circle.id:
                print('circle remove')
                return
            matched_structures = [x for x in self.novel.story_structures if x.id == structure.id]
            if matched_structures:
                for st in matched_structures:
                    self.novel.story_structures.remove(st)
            self._removeStructure(structure)

        self.repo.update_novel(self.novel)
