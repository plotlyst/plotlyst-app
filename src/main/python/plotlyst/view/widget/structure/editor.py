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

import copy
import uuid
from functools import partial
from typing import Optional

import qtanim
from PyQt6.QtCore import Qt, QEvent, QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QPushButton, QSizePolicy, QButtonGroup
from overrides import overrides
from qthandy import translucent, gc, flow, hbox, clear_layout, vbox, sp, margins, vspacer, \
    incr_font, bold, busy, italic, incr_icon, spacer, transparent, pointy
from qthandy.filter import OpacityEventFilter
from qtmenu import MenuWidget

from plotlyst.common import act_color, PLOTLYST_SECONDARY_COLOR, MAX_NUMBER_OF_ACTS
from plotlyst.core.domain import StoryStructure, Novel, StoryBeat, \
    Character, StoryBeatType, StoryStructureDisplayType, TemplateStoryStructureType
from plotlyst.event.core import EventListener, Event, emit_event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import NovelStoryStructureUpdated, CharacterChangedEvent, CharacterDeletedEvent, \
    NovelSyncEvent, NovelStoryStructureActivationRequest
from plotlyst.service.cache import acts_registry
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import ButtonPressResizeEventFilter, set_tab_icon, label, frame, shadow, action, \
    set_tab_visible, push_btn
from plotlyst.view.generated.story_structure_settings_ui import Ui_StoryStructureSettings
from plotlyst.view.icons import IconRegistry, avatars
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.style.button import apply_button_palette_color
from plotlyst.view.widget.characters import CharacterSelectorMenu
from plotlyst.view.widget.confirm import confirmed
from plotlyst.view.widget.display import IconText, PopupDialog, Icon
from plotlyst.view.widget.input import AutoAdjustableTextEdit, TextInputDialog
from plotlyst.view.widget.settings import SettingBaseWidget
from plotlyst.view.widget.structure.beat import BeatsPreview
from plotlyst.view.widget.structure.outline import StoryStructureOutline
from plotlyst.view.widget.structure.selector import ActToolButton
from plotlyst.view.widget.structure.template import StoryStructureSelectorDialog


class _StoryStructureButton(QPushButton):
    def __init__(self, structure: StoryStructure, novel: Novel, parent=None):
        super(_StoryStructureButton, self).__init__(parent)
        self._structure = structure
        self.novel = novel
        self.setText(structure.title)
        self.setCheckable(True)
        pointy(self)
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Maximum)

        self.setStyleSheet('''
            QPushButton {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 0,
                                      stop: 0 #f8edeb);
                border: 1px solid #fec89a;
                border-radius: 6px;
                padding: 3px;
            }
            QPushButton:checked {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 0,
                                      stop: 0 #FFCBBA);
                border: 2px solid #FD9235;
                padding: 3px;

            }
            ''')
        self.refresh()

        self._toggled(self.isChecked())
        self.installEventFilter(OpacityEventFilter(self, 0.7, 0.5, ignoreCheckedButton=True))
        self.installEventFilter(ButtonPressResizeEventFilter(self))
        self.toggled.connect(self._toggled)

    def structure(self) -> StoryStructure:
        return self._structure

    def refresh(self, animated: bool = False):
        self.setText(self._structure.title)

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


class BeatNotesWidget(QWidget):
    notesChanged = pyqtSignal()

    def __init__(self, beat: StoryBeat, parent=None):
        super().__init__(parent)
        self._beat = beat

        vbox(self)
        self._text = AutoAdjustableTextEdit(height=80)
        incr_font(self._text, 2)
        self._text.setProperty('rounded', True)
        self._text.setProperty('white-bg', True)
        self._text.setPlaceholderText(f'Describe {beat.text}')
        self._text.setMaximumWidth(400)
        shadow(self._text)
        self._text.setMarkdown(self._beat.notes)
        self._text.textChanged.connect(self._textChanged)

        self._title = IconText()
        bold(self._title)
        self._title.setText(beat.text)
        self._title.setIcon(IconRegistry.from_name(beat.icon, beat.icon_color))
        incr_font(self._title, 2)
        self.layout().addWidget(self._title, alignment=Qt.AlignmentFlag.AlignLeft)
        # self.layout().addWidget(label(beat.description, description=True, wordWrap=True))
        self.layout().addWidget(self._text)

    def _textChanged(self):
        self._beat.notes = self._text.toMarkdown()
        self.notesChanged.emit()


class ActNotesWidget(QWidget):
    notesChanged = pyqtSignal()

    def __init__(self, act: int, structure: StoryStructure, parent=None):
        super().__init__(parent)
        self._act = act
        self._structure = structure

        hbox(self, spacing=15)

        self._wdgContainer = QWidget()
        hbox(self._wdgContainer, spacing=15)

        self._text = AutoAdjustableTextEdit(height=300)
        incr_font(self._text, 3)
        self._text.setMaximumWidth(1200)
        self._text.setPlaceholderText(f'Describe the events in act {act}')
        self._text.setProperty('transparent', True)
        self._text.setMarkdown(structure.acts_text.get(act, ''))
        self._text.textChanged.connect(self._textChanged)
        color = act_color(act, self._structure.acts)

        self._wdgBar = QWidget()
        self._wdgBar.setStyleSheet(f'background: {color}')
        self._wdgBar.setFixedWidth(6)
        sp(self._wdgBar).v_exp()

        self._wdgActEditor = frame()
        self._wdgActEditor.setProperty('white-bg', True)
        self._wdgActEditor.setMaximumWidth(1200)
        qcolor = QColor(color)
        qcolor.setAlpha(75)
        shadow(self._wdgActEditor, color=qcolor)
        vbox(self._wdgActEditor)
        margins(self._wdgActEditor, left=15)
        self._wdgActEditor.layout().addWidget(label(f'Act {act}', h3=True), alignment=Qt.AlignmentFlag.AlignLeft)
        self._wdgActEditor.layout().addWidget(self._text)
        self._wdgActEditor.layout().addWidget(vspacer())

        self._wdgContainer.layout().addWidget(self._wdgActEditor)

        self.layout().addWidget(self._wdgBar)
        self.layout().addWidget(self._wdgContainer)

    def _textChanged(self):
        self._structure.acts_text[self._act] = self._text.toMarkdown()
        self.notesChanged.emit()


class StoryStructureNotes(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._structure: Optional[StoryStructure] = None
        vbox(self)
        self._novel: Optional[Novel] = None

        self.repo = RepositoryPersistenceManager.instance()

    def setNovel(self, novel: Novel):
        self._novel = novel

    def setStructure(self, structure: StoryStructure):
        self._structure = structure
        self.refresh()

    def refresh(self):
        clear_layout(self)

        act1 = ActNotesWidget(1, self._structure)
        act1.notesChanged.connect(self._save)
        act2 = ActNotesWidget(2, self._structure)
        act2.notesChanged.connect(self._save)
        act3 = ActNotesWidget(3, self._structure)
        act3.notesChanged.connect(self._save)

        self.layout().addWidget(act1)
        self.layout().addWidget(act2)
        self.layout().addWidget(act3)

    def _save(self):
        self.repo.update_novel(self._novel)


class TimelineSettingToggle(SettingBaseWidget):
    changed = pyqtSignal()

    def __init__(self, structure: StoryStructure, parent=None):
        super().__init__(parent)
        self.structure = structure
        self._title.setText('Proportional Timeline')
        self._description.setText(
            "Consider pacing and story beats' locations according to their proportional occurrence within the story")

        self._toggle.setChecked(self.structure.display_type == StoryStructureDisplayType.Proportional_timeline)

    @overrides
    def _clicked(self, toggled: bool):
        if toggled:
            self.structure.display_type = StoryStructureDisplayType.Proportional_timeline
        else:
            self.structure.display_type = StoryStructureDisplayType.Sequential_timeline

        self.changed.emit()


class ActSetting(QWidget):
    changed = pyqtSignal()

    def __init__(self, structure: StoryStructure, parent=None):
        super().__init__(parent)
        self.structure = structure

        self._title = QPushButton('Expected number of acts')
        apply_button_palette_color(self._title, PLOTLYST_SECONDARY_COLOR)
        transparent(self._title)
        incr_font(self._title, 2)

        self._btnGroup = QButtonGroup()
        self._wdgButtons = QWidget()
        hbox(self._wdgButtons)

        self._wdgButtons.layout().addWidget(spacer())
        expected_act = self.structure.expected_acts if self.structure.expected_acts is not None else MAX_NUMBER_OF_ACTS
        for act in range(0, MAX_NUMBER_OF_ACTS + 1):
            btn = ActToolButton(act, self.structure, colorOn=PLOTLYST_SECONDARY_COLOR)
            if expected_act == act:
                btn.setChecked(True)
            self._btnGroup.addButton(btn)
            self._wdgButtons.layout().addWidget(btn)
        self._wdgButtons.layout().addWidget(spacer())
        self._btnGroup.buttonClicked.connect(self._clicked)

        vbox(self)
        self.layout().addWidget(self._title, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self._wdgButtons)

    def _clicked(self):
        self.structure.expected_acts = self._btnGroup.checkedButton().act
        self.changed.emit()


class StoryStructureSettingsPopup(PopupDialog):
    def __init__(self, structure: StoryStructure, parent=None):
        super().__init__(parent)
        self.structure = structure
        # self.setMinimumSize(550, 250)

        self.wdgTitle = QWidget()
        hbox(self.wdgTitle)
        self.wdgTitle.layout().addWidget(spacer())
        icon = Icon()
        icon.setIcon(IconRegistry.cog_icon())
        incr_icon(icon, 4)
        self.wdgTitle.layout().addWidget(icon)
        self.wdgTitle.layout().addWidget(label('Story structure settings', bold=True, h4=True))
        self.wdgTitle.layout().addWidget(spacer())
        self.wdgTitle.layout().addWidget(self.btnReset)
        self.frame.layout().addWidget(self.wdgTitle)

        self.timelineToggle = TimelineSettingToggle(self.structure)
        self.frame.layout().addWidget(self.timelineToggle)

        if self.structure.custom:
            self.actSetting = ActSetting(self.structure)
            self.frame.layout().addWidget(self.actSetting)

        self.btnClose = push_btn(text='Close', properties=['confirm', 'cancel'])
        self.btnClose.clicked.connect(self.reject)
        self.frame.layout().addWidget(self.btnClose, alignment=Qt.AlignmentFlag.AlignRight)

    def display(self):
        self.exec()


class StoryStructureEditor(QWidget, Ui_StoryStructureSettings, EventListener):
    def __init__(self, parent=None):
        super(StoryStructureEditor, self).__init__(parent)
        self.setupUi(self)
        flow(self.wdgTemplates)

        self.btnNew.setIcon(IconRegistry.plus_icon('white'))
        self.btnNew.installEventFilter(ButtonPressResizeEventFilter(self.btnNew))
        menu = MenuWidget(self.btnNew)
        apply_white_menu(menu)
        menu.addAction(action('Apply a template structure (recommended)',
                              icon=IconRegistry.template_icon(color=PLOTLYST_SECONDARY_COLOR),
                              slot=self._selectTemplateStructure))
        menu.addSeparator()
        menu.addAction(action('Start a new empty structure...', slot=self._addNewEmptyStructure))

        self.btnDelete.setIcon(IconRegistry.trash_can_icon())
        self.btnDelete.installEventFilter(ButtonPressResizeEventFilter(self.btnDelete))
        self.btnDelete.installEventFilter(OpacityEventFilter(self.btnDelete, leaveOpacity=0.6))
        self.btnDelete.clicked.connect(self._removeStructure)
        self.btnCopy.setIcon(IconRegistry.copy_icon())
        self.btnCopy.installEventFilter(ButtonPressResizeEventFilter(self.btnCopy))
        self.btnCopy.installEventFilter(OpacityEventFilter(self.btnCopy, leaveOpacity=0.6))
        self.btnCopy.clicked.connect(self._duplicateStructure)
        self.btnEdit.setIcon(IconRegistry.edit_icon())
        self.btnEdit.installEventFilter(ButtonPressResizeEventFilter(self.btnEdit))
        self.btnEdit.installEventFilter(OpacityEventFilter(self.btnEdit, leaveOpacity=0.6))
        self.btnEdit.clicked.connect(self._editStructure)
        self.btnLinkCharacter.setIcon(IconRegistry.character_icon())
        self.btnLinkCharacter.installEventFilter(ButtonPressResizeEventFilter(self.btnLinkCharacter))
        self.btnLinkCharacter.installEventFilter(OpacityEventFilter(self.btnLinkCharacter, leaveOpacity=0.6))
        self.btnLinkCharacter.clicked.connect(self._showCharacterMenu)
        self.btnConfigure.setIcon(IconRegistry.cog_icon(color='grey'))
        italic(self.btnConfigure)
        self.btnConfigure.installEventFilter(ButtonPressResizeEventFilter(self.btnConfigure))
        self.btnConfigure.installEventFilter(OpacityEventFilter(self.btnConfigure))
        self.btnConfigure.clicked.connect(self._configureStructure)

        set_tab_icon(self.tabWidget, self.tabOutline,
                     IconRegistry.from_name('mdi6.timeline-outline', rotated=90, color_on=PLOTLYST_SECONDARY_COLOR))
        set_tab_icon(self.tabWidget, self.tabOverview,
                     IconRegistry.from_name('mdi6.grid', color_on=PLOTLYST_SECONDARY_COLOR))
        set_tab_icon(self.tabWidget, self.tabNotes, IconRegistry.document_edition_icon())
        set_tab_visible(self.tabWidget, self.tabNotes, False)

        self.btnGroupStructure = QButtonGroup()
        self.btnGroupStructure.setExclusive(True)

        self.wdgStructureOutline = StoryStructureOutline()
        self.wdgStructureOutline.attachStructurePreview(self.wdgPreview)
        self.wdgStructureOutline.timelineChanged.connect(self._timelineChanged)
        self.wdgStructureOutline.beatChanged.connect(self._save)
        self.wdgOutline.layout().addWidget(self.wdgStructureOutline)

        # self._structureNotes = StoryStructureNotes()
        # hbox(self.notes).addWidget(self._structureNotes)
        hbox(self.beats, 5, 0)

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
                    self._save()
        elif isinstance(event, NovelStoryStructureActivationRequest):
            for btn in self.btnGroupStructure.buttons():
                if btn.structure() is event.structure:
                    btn.setChecked(True)
            self._save()
            self._emit()
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

        self.wdgStructureOutline.setNovel(self.novel)

        self._beatsPreview = BeatsPreview(self.novel, toggleBeats=False)
        self.beats.layout().addWidget(self._beatsPreview)
        self._beatsPreview.attachStructurePreview(self.wdgPreview)
        self.wdgStructureOutline.attachBeatsPreview(self._beatsPreview)

        # self._structureNotes.setNovel(self.novel)
        for structure in self.novel.story_structures:
            self._addStructureWidget(structure)

    def _addStructureWidget(self, structure: StoryStructure):
        btn = _StoryStructureButton(structure, self.novel)
        self.btnGroupStructure.addButton(btn)
        self.wdgTemplates.layout().addWidget(btn)
        if structure.active:
            btn.setChecked(True)
            self._refreshStructure(structure)
        btn.toggled.connect(partial(self._activeStructureToggled, structure))
        btn.clicked.connect(partial(self._activeStructureClicked, structure))

        self._toggleDeleteButton()

    def _addNewEmptyStructure(self):
        structure = StoryStructure('Story structure', icon='mdi6.bridge', custom=True, acts=0)
        self._addNewStructure(structure)

    def _addNewStructure(self, structure: StoryStructure):
        self.novel.story_structures.append(structure)
        self._addStructureWidget(structure)
        self.btnGroupStructure.buttons()[-1].setChecked(True)
        self._save()
        self._emit()

    def _removeStructure(self):
        if len(self.novel.story_structures) < 2:
            return

        structure = self.novel.active_story_structure
        number_of_beats = len([x for x in structure.beats if x.enabled and x.type == StoryBeatType.BEAT])
        occupied = len(acts_registry.occupied_beats())
        title = f'Are you sure you want to delete the story structure "{structure.title}"?'
        msg = '<html><ul><li>This operation cannot be undone.<li>All scene associations to this structure will be unlinked.'
        if occupied:
            msg += f'<li>Number of linked structure beats to scenes: <b>{occupied}/{number_of_beats}</b>'
        if not confirmed(msg, title):
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
            self._emit()
        self._save()

        self._toggleDeleteButton()

    def _duplicateStructure(self):
        structure = copy.deepcopy(self.novel.active_story_structure)
        structure.active = False
        for beat in structure.beats:
            if beat.custom:
                beat.id = uuid.uuid4()
            beat.notes = ''
        self._addNewStructure(structure)

    def _editStructure(self):
        if self.novel.active_story_structure.custom:
            name = TextInputDialog.edit('Rename story structure', 'Edit structure name',
                                        value=self.novel.active_story_structure.title)
            if name:
                self.novel.active_story_structure.title = name
                self.btnGroupStructure.checkedButton().refresh(animated=False)
                self._save()
                self._emit()
        else:
            StoryStructureSelectorDialog.popup(self.novel, self.novel.active_story_structure)
            if self.novel.active_story_structure.template_type == TemplateStoryStructureType.CUSTOM:
                self.btnGroupStructure.checkedButton().refresh(animated=False)

            self._activeStructureToggled(self.novel.active_story_structure, True)
            self._emit()

    def _showCharacterMenu(self):
        if self.novel.active_story_structure.character_id:
            menu = MenuWidget()
            menu.addAction(
                action('Unlink character', IconRegistry.from_name('fa5s.unlink'), slot=self._characterUnlinked))
        else:
            menu = CharacterSelectorMenu(self.novel)
            menu.selected.connect(self._characterLinked)
        menu.exec()

    def _characterLinked(self, character: Character):
        self.novel.active_story_structure.set_character(character)
        self.__handleCharacterLinkChange()

    def _characterUnlinked(self):
        self.novel.active_story_structure.reset_character()
        self.__handleCharacterLinkChange()

    def __handleCharacterLinkChange(self):
        self.btnGroupStructure.checkedButton().refresh(True)
        self._save()
        self._activeStructureToggled(self.novel.active_story_structure, True)
        self._emit()

    def _selectTemplateStructure(self):
        structure: Optional[StoryStructure] = StoryStructureSelectorDialog.popup(self.novel)
        if structure:
            self._addNewStructure(structure)

    def _configureStructure(self):
        structure = self.novel.active_story_structure
        StoryStructureSettingsPopup.popup(self.novel.active_story_structure)
        self.wdgPreview.setStructure(self.novel, structure)
        self.wdgPreview.setHidden(structure.display_type == StoryStructureDisplayType.Sequential_timeline)
        self._save()
        self._emit()

    @busy
    def _refreshStructure(self, structure: StoryStructure):
        self.wdgStructureOutline.setStructure(structure)
        self.wdgPreview.setStructure(self.novel, structure)

        self.wdgPreview.setHidden(structure.display_type == StoryStructureDisplayType.Sequential_timeline)
        self._beatsPreview.attachStructurePreview(self.wdgPreview)
        self.wdgStructureOutline.attachStructurePreview(self.wdgPreview)
        self._beatsPreview.setStructure(structure)

    def _activeStructureToggled(self, structure: StoryStructure, toggled: bool):
        if not toggled:
            return

        for struct in self.novel.story_structures:
            struct.active = False
        structure.active = True
        acts_registry.refresh()
        QTimer.singleShot(20, lambda: self._refreshStructure(structure))

    def _activeStructureClicked(self, _: StoryStructure, toggled: bool):
        if not toggled:
            return

        self._save()
        self._emit()

    def __initWdgPreview(self):
        self.wdgPreview.setCheckOccupiedBeats(False)
        self.wdgPreview.setBeatsMoveable(True)
        self.wdgPreview.setActsClickable(False)
        self.wdgPreview.setActsResizeable(True)
        self.wdgPreview.actsResized.connect(self._emit)
        self.wdgPreview.beatMoved.connect(self._beatMoved)

    def _timelineChanged(self):
        self._save()
        self._emit()

    def _beatMoved(self):
        def refresh(structure: StoryStructure):
            self.wdgStructureOutline.setStructure(structure)
            self._beatsPreview.setStructure(structure)

        QTimer.singleShot(20, lambda: refresh(self.novel.active_story_structure))
        self._emit()

    def _toggleDeleteButton(self):
        self.btnDelete.setEnabled(len(self.novel.story_structures) > 1)

    def _save(self):
        self.repo.update_novel(self.novel)

    def _emit(self):
        emit_event(self.novel, NovelStoryStructureUpdated(self))
