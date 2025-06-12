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
from functools import partial
from typing import Optional

import qtanim
from PyQt6.QtCore import pyqtSignal, QObject, QTimer, Qt
from PyQt6.QtWidgets import QWidget, QAbstractButton, QLineEdit, QCompleter
from overrides import overrides
from qthandy import translucent, bold, italic, incr_font
from qthandy.filter import OpacityEventFilter
from qtmenu import MenuWidget

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, RELAXED_WHITE_COLOR
from plotlyst.core.client import json_client
from plotlyst.core.domain import Novel, Character, Document, FEMALE, SelectionItem, BACKSTORY_PREVIEW
from plotlyst.core.template import protagonist_role
from plotlyst.env import app_env
from plotlyst.event.core import EventListener, Event
from plotlyst.event.handler import event_dispatchers, global_event_dispatcher
from plotlyst.events import NovelAboutToSyncEvent
from plotlyst.resources import resource_registry
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.service.tour import TourService
from plotlyst.view.common import set_tab_icon, ButtonPressResizeEventFilter, set_tab_visible, action, scroll_to_bottom
from plotlyst.view.generated.character_editor_ui import Ui_CharacterEditor
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import apply_bg_image, transparent_menu
from plotlyst.view.widget.button import FadeOutButtonGroup, DotsMenuButton
from plotlyst.view.widget.character.codex import CharacterCodexEditor
from plotlyst.view.widget.character.editor import CharacterAgeEditor
from plotlyst.view.widget.character.editor import CharacterRoleSelector
from plotlyst.view.widget.character.profile import CharacterProfileEditor, CharacterNameEditorPopup
from plotlyst.view.widget.confirm import asked
from plotlyst.view.widget.display import PremiumOverlayWidget, MenuOverlayEventFilter
from plotlyst.view.widget.tour.core import CharacterEditorTourEvent, \
    CharacterEditorNameLineEditTourEvent, TourEvent, CharacterEditorNameFilledTourEvent, \
    CharacterEditorAvatarDisplayTourEvent, CharacterEditorAvatarMenuTourEvent, CharacterEditorBackButtonTourEvent, \
    CharacterEditorAvatarMenuCloseTourEvent


class CharacterEditor(QObject, EventListener):
    close = pyqtSignal(Character)

    def __init__(self, novel: Novel):
        super().__init__()
        self.widget = QWidget()
        self.ui = Ui_CharacterEditor()
        self.ui.setupUi(self.widget)
        self.novel = novel
        self.character: Optional[Character] = None

        self._btnMenu = DotsMenuButton()
        self._btnMenu.installEventFilter(OpacityEventFilter(self._btnMenu))
        menu = MenuWidget(self._btnMenu)
        menu.addAction(action('Edit displayed name', IconRegistry.from_name('mdi.badge-account-outline'),
                              self._edit_displayed_name))
        self.ui.wdgToolbar.layout().addWidget(self._btnMenu, alignment=Qt.AlignmentFlag.AlignRight)

        self.ui.wdgBackstory.addedToTheEnd.connect(lambda: scroll_to_bottom(self.ui.scrollAreaBackstory))
        set_tab_visible(self.ui.tabAttributes, self.ui.tabBackstory, app_env.profile().get('backstory', False))
        set_tab_visible(self.ui.tabAttributes, self.ui.tabBinder, app_env.profile().get('backstory', False))
        set_tab_visible(self.ui.tabAttributes, self.ui.tabBackstoryDummy, not app_env.profile().get('backstory', False))

        self.ui.textEdit.setTitleVisible(False)
        self.ui.textEdit.setToolbarVisible(False)
        self.ui.textEdit.setWidthPercentage(95)
        self.ui.textEdit.textEdit.setDocumentMargin(20)
        self.ui.textEdit.textEdit.setBlockPlaceholderEnabled(True)

        self.ui.tabAttributes.currentChanged.connect(self._tab_changed)

        self.ui.btnMale.setIcon(IconRegistry.male_gender_icon())
        self.ui.btnMale.installEventFilter(OpacityEventFilter(parent=self.ui.btnMale, ignoreCheckedButton=True))
        self.ui.btnFemale.setIcon(IconRegistry.female_gender_icon())
        self.ui.btnFemale.installEventFilter(OpacityEventFilter(parent=self.ui.btnFemale, ignoreCheckedButton=True))
        self.ui.btnTransgender.setIcon(IconRegistry.transgender_icon())
        self.ui.btnTransgender.installEventFilter(
            OpacityEventFilter(parent=self.ui.btnTransgender, ignoreCheckedButton=True))
        self.ui.btnTransgender.setHidden(True)
        self.ui.btnNonBinary.setIcon(IconRegistry.non_binary_gender_icon())
        self.ui.btnNonBinary.installEventFilter(
            OpacityEventFilter(parent=self.ui.btnNonBinary, ignoreCheckedButton=True))
        self.ui.btnNonBinary.setHidden(True)
        self.ui.btnGenderless.setIcon(IconRegistry.genderless_icon())
        self.ui.btnGenderless.installEventFilter(
            OpacityEventFilter(parent=self.ui.btnGenderless, ignoreCheckedButton=True))
        self.ui.btnGenderless.setHidden(True)

        self.btnGroupGender = FadeOutButtonGroup()
        self.btnGroupGender.addButton(self.ui.btnMale)
        self.btnGroupGender.addButton(self.ui.btnFemale)
        self.btnGroupGender.addButton(self.ui.btnTransgender)
        self.btnGroupGender.addButton(self.ui.btnNonBinary)
        self.btnGroupGender.addButton(self.ui.btnGenderless)
        self.btnGroupGender.setSecondaryButtons(self.ui.btnTransgender, self.ui.btnNonBinary, self.ui.btnGenderless)
        self.btnGroupGender.buttonClicked.connect(self._gender_clicked)
        self.ui.btnMoreGender.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnMoreGender))
        self.ui.btnMoreGender.clicked.connect(self._display_more_gender_clicked)

        self.ui.btnRole.setIcon(IconRegistry.from_name('fa5s.chess-bishop'))
        self._btnRoleEventFilter = OpacityEventFilter(parent=self.ui.btnRole, leaveOpacity=0.7,
                                                      ignoreCheckedButton=True)
        self.ui.btnRole.installEventFilter(self._btnRoleEventFilter)
        self._roleSelector = CharacterRoleSelector()
        self._roleSelector.roleSelected.connect(self._role_changed)
        self._roleSelector.rolePromoted.connect(self._role_promoted)
        self._roleMenu = MenuWidget(self.ui.btnRole)
        self._roleMenu.addWidget(self._roleSelector)
        transparent_menu(self._roleMenu)
        self._roleMenu.installEventFilter(MenuOverlayEventFilter(self._roleMenu))

        italic(self.ui.btnAge)
        italic(self.ui.btnOccupation)

        self._ageEditor = CharacterAgeEditor()
        self._ageEditor.valueChanged.connect(self._age_changed)
        self._ageEditor.infiniteToggled.connect(self._age_infinite_toggled)
        menu = MenuWidget(self.ui.btnAge)
        menu.addWidget(self._ageEditor)
        transparent_menu(menu)
        menu.installEventFilter(MenuOverlayEventFilter(menu))
        menu.aboutToShow.connect(self._ageEditor.setFocus)

        self._lineOccupation = QLineEdit()
        self._lineOccupation.setProperty('rounded', True)
        self._lineOccupation.setPlaceholderText('Fill out occupation')
        self._lineOccupation.textEdited.connect(self._occupation_changed)
        menu = MenuWidget(self.ui.btnOccupation)
        menu.addWidget(self._lineOccupation)
        menu.aboutToShow.connect(self._lineOccupation.setFocus)
        self._lineOccupation.editingFinished.connect(menu.hide)

        incr_font(self.ui.btnAge)
        incr_font(self.ui.btnOccupation)

        set_tab_icon(self.ui.tabAttributes, self.ui.tabBackstory,
                     IconRegistry.backstory_icon('black', PLOTLYST_SECONDARY_COLOR))
        set_tab_icon(self.ui.tabAttributes, self.ui.tabBackstoryDummy,
                     IconRegistry.backstory_icon('black', PLOTLYST_SECONDARY_COLOR))
        set_tab_icon(self.ui.tabAttributes, self.ui.tabBigFive, IconRegistry.big_five_icon(PLOTLYST_SECONDARY_COLOR))
        set_tab_icon(self.ui.tabAttributes, self.ui.tabNotes, IconRegistry.document_edition_icon())
        set_tab_icon(self.ui.tabAttributes, self.ui.tabBinder,
                     IconRegistry.from_name('ri.typhoon-fill', 'black', PLOTLYST_SECONDARY_COLOR))

        set_tab_visible(self.ui.tabAttributes, self.ui.tabBigFive, False)
        set_tab_visible(self.ui.tabAttributes, self.ui.tabNotes, False)

        self.ui.wdgAvatar.btnAvatar.setToolTip('Character avatar. Click to add an image')
        self.ui.wdgAvatar.avatarUpdated.connect(self._avatar_updated)
        self.ui.wdgAvatar.setFixedSize(180, 180)

        self.ui.splitter.setSizes([400, 400])

        self.ui.lineName.setReadOnly(self.novel.is_readonly())
        self.ui.lineName.textEdited.connect(self._name_edited)

        self.codexEditor = CharacterCodexEditor(self.novel)
        self.ui.scrollAreaBinderWdg.layout().addWidget(self.codexEditor)

        self.profile = CharacterProfileEditor(self.novel)
        self.ui.wdgProfile.layout().addWidget(self.profile)

        apply_bg_image(self.ui.scrollAreaBackstoryContents, resource_registry.cover1)
        if not app_env.profile().get('backstory', False):
            apply_bg_image(self.ui.tabBackstoryDummy, resource_registry.cover1)
            PremiumOverlayWidget(self.ui.tabBackstoryDummy, 'Character backstory',
                                 icon='fa5s.archive',
                                 alt_link='https://plotlyst.com/docs/characters/', preview=BACKSTORY_PREVIEW)

        self.ui.btnClose.clicked.connect(self._save)

        if app_env.profile().get('backstory', False):
            self.ui.tabAttributes.setCurrentWidget(self.ui.tabBackstory)
        else:
            self.ui.tabAttributes.setCurrentWidget(self.ui.tabNotes)

        self.repo = RepositoryPersistenceManager.instance()
        dispatcher = event_dispatchers.instance(self.novel)
        dispatcher.register(self, NovelAboutToSyncEvent)

        self._tour_service = TourService.instance()
        global_event_dispatcher.register(self, CharacterEditorTourEvent, CharacterEditorNameLineEditTourEvent,
                                         CharacterEditorNameFilledTourEvent, CharacterEditorAvatarDisplayTourEvent,
                                         CharacterEditorAvatarMenuTourEvent, CharacterEditorAvatarMenuCloseTourEvent,
                                         CharacterEditorBackButtonTourEvent)

    def set_character(self, character: Character):
        self.character = character

        occupations = set([x.occupation for x in self.novel.characters])
        if occupations:
            self._lineOccupation.setCompleter(QCompleter(occupations))

        if self.character.role:
            self._roleSelector.setActiveRole(self.character.role)
            self._display_role()
        else:
            self._roleSelector.setActiveRole(protagonist_role)
            self._reset_role()

        if self.character.age:
            self._ageEditor.setValue(self.character.age)
        else:
            self._reset_age()
        self._ageEditor.setInfinite(self.character.age_infinite)
        if self.character.occupation:
            self._lineOccupation.setText(self.character.occupation)
            self.ui.btnOccupation.setText(self.character.occupation)
        else:
            self._reset_occupation()

        self.btnGroupGender.reset()
        self.btnGroupGender.setSecondaryLocked(True)
        if self.character.gender:
            for btn in self.btnGroupGender.buttons():
                if self.character.gender == btn.text():
                    self.btnGroupGender.toggle(btn)
            self.ui.btnMoreGender.setHidden(True)
        else:
            self.ui.btnMoreGender.setVisible(True)
            self.ui.btnMale.setVisible(True)
            self.ui.btnFemale.setVisible(True)
            self.ui.btnTransgender.setVisible(False)
            self.ui.btnNonBinary.setVisible(False)
            self.ui.btnGenderless.setVisible(False)

        self.ui.lineName.setText(self.character.name)
        self.ui.wdgAvatar.setCharacter(self.character)
        self.ui.wdgAvatar.setUploadPopupMenu()
        self.ui.wdgBackstory.setCharacter(self.character)
        self.codexEditor.setCharacter(self.character)
        self.profile.setCharacter(self.character)
        if self.character.document and self.character.document.loaded:
            self.ui.textEdit.setText(self.character.document.content, self.character.name, title_read_only=True)
        else:
            self.ui.textEdit.clear()
            self._tab_changed()

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, TourEvent):
            self.__handle_tour_event(event)
        elif isinstance(event, NovelAboutToSyncEvent):
            if self.character is not None:
                self._save()

    def close_event(self):
        if self.character is not None:
            self._save()

    def _name_edited(self, text: str):
        self.character.name = text
        if self.character.prefs.avatar.use_initial:
            self.ui.wdgAvatar.updateAvatar()

    def _tab_changed(self):
        if self.ui.tabAttributes.currentWidget() is self.ui.tabNotes and self.character:
            if self.character.document and not self.character.document.loaded:
                json_client.load_document(self.novel, self.character.document)
                self.ui.textEdit.setText(self.character.document.content, self.character.name, title_read_only=True)

    def _role_promoted(self, role: SelectionItem):
        if self.character.role == role:
            self._display_role()
            if self.character.prefs.avatar.use_role:
                self.ui.wdgAvatar.updateAvatar()

    def _role_changed(self, role: SelectionItem):
        def apply_profile():
            if asked('For minor characters, a simplified character profile is recommended.',
                     'Apply a new character profile for this minor character?', 'Apply (recommended)', 'No'):
                self.profile.applyMinorRoleSettings()

        self._roleMenu.close()
        new_role = copy.deepcopy(role)
        if new_role.text == protagonist_role.text and self.character.gender == FEMALE:
            new_role.icon = 'fa5s.chess-queen'
        self.character.role = new_role
        self._display_role()
        if self.character.prefs.avatar.use_role:
            self.ui.wdgAvatar.updateAvatar()

        if self.character.is_minor():
            QTimer.singleShot(250, apply_profile)

    def _age_changed(self, age: int):
        if self._ageEditor.minimum() == 0:
            italic(self.ui.btnAge, False)
            bold(self.ui.btnAge)
            self.ui.btnAge.iconColor = '#343a40'
        self.ui.btnAge.setText(str(age))
        self.character.age = age

    def _reset_age(self):
        self._ageEditor.reset()
        italic(self.ui.btnAge)
        bold(self.ui.btnAge, False)
        self.ui.btnAge.setText('Age')

    def _age_infinite_toggled(self, toggled: bool):
        if toggled:
            self.ui.btnAge.setIcon(IconRegistry.from_name('mdi.infinity', 'gray'))
            self.ui.btnAge.setText('')
        else:
            self.ui.btnAge.setIcon(IconRegistry.from_name('fa5s.birthday-cake', 'gray'))
            if self.character.age is not None:
                self.ui.btnAge.setText(str(self.character.age))

        self.character.age_infinite = toggled

    def _occupation_changed(self, occupation: str):
        if self.ui.btnOccupation.font().italic():  # first setup
            italic(self.ui.btnOccupation, False)
            bold(self.ui.btnOccupation)
            self.ui.btnOccupation.iconColor = '#343a40'
        self.ui.btnOccupation.setText(occupation)
        self.character.occupation = occupation

    def _reset_occupation(self):
        italic(self.ui.btnOccupation)
        bold(self.ui.btnOccupation, False)
        self.ui.btnOccupation.setText('Occupation')
        self._lineOccupation.clear()

    def _display_role(self):
        self.ui.btnRole.setText(self.character.role.text)
        if self.character.role.icon:
            self.ui.btnRole.setIcon(IconRegistry.from_name(self.character.role.icon, self.character.role.icon_color))

        self.ui.btnRole.initStyleSheet(self.character.role.icon_color, 'solid', self.character.role.icon_color,
                                       RELAXED_WHITE_COLOR)
        self._btnRoleEventFilter.enterOpacity = 0.8

    def _reset_role(self):
        self.ui.btnRole.setIcon(IconRegistry.from_name('fa5s.chess-bishop', 'grey'))
        self.ui.btnRole.setText('Role')
        self.ui.btnRole.initStyleSheet()
        self._btnRoleEventFilter.enterOpacity = 1.0

    def _gender_clicked(self, btn: QAbstractButton):
        if btn.isChecked():
            self.character.gender = btn.text()
            self.ui.btnMoreGender.setVisible(False)
        else:
            self.character.gender = ''
            self.ui.btnMoreGender.setVisible(True)

    def _display_more_gender_clicked(self, toggled: bool):
        self.btnGroupGender.setSecondaryLocked(not toggled)
        for btn in [self.ui.btnTransgender, self.ui.btnNonBinary, self.ui.btnGenderless]:
            if toggled:
                anim = qtanim.fade_in(btn)
            else:
                anim = qtanim.fade_out(btn)
            anim.finished.connect(partial(translucent, btn, 0.4))

        self.ui.btnMoreGender.setText('«' if toggled else '»')

    def _avatar_updated(self):
        if self.character.prefs.avatar.use_role and self.character.role is None:
            qtanim.shake(self.ui.btnRole)

    def _edit_displayed_name(self):
        CharacterNameEditorPopup.popup(self.character)
        self.ui.lineName.setText(self.character.name)
        if self.character.prefs.avatar.use_initial:
            self.ui.wdgAvatar.updateAvatar()

    def _save(self):
        if self.character.role and self.character.role.text == protagonist_role.text:
            if self.character.gender == FEMALE:
                self.character.role.icon = 'fa5s.chess-queen'
            else:
                self.character.role.icon = 'fa5s.chess-king'

        self.repo.update_character(self.character, self.ui.wdgAvatar.imageUploaded())
        self.repo.update_novel(self.novel)  # TODO temporary to update custom labels

        if not self.character.document:
            self.character.document = Document('', character_id=self.character.id)
            self.character.document.loaded = True

        if self.character.document.loaded:
            self.character.document.content = self.ui.textEdit.textEdit.toHtml()
            self.repo.update_doc(self.novel, self.character.document)

        self.close.emit(self.character)
        self.character = None

    def __handle_tour_event(self, event: TourEvent):
        if isinstance(event, CharacterEditorTourEvent):
            self._tour_service.addWidget(self.widget, event)
        elif isinstance(event, CharacterEditorNameLineEditTourEvent):
            self._tour_service.addWidget(self.ui.lineName, event)
        elif isinstance(event, CharacterEditorNameFilledTourEvent):
            self.ui.lineName.setText(event.name)
            self._name_edited(event.name)
            self.ui.wdgAvatar.updateAvatar()
            self._tour_service.next()
        elif isinstance(event, CharacterEditorAvatarDisplayTourEvent):
            self._tour_service.addWidget(self.ui.wdgAvatar, event)
        elif isinstance(event, CharacterEditorAvatarMenuTourEvent):
            self.ui.wdgAvatar.popupMenu().exec()
            QTimer.singleShot(150, lambda: self._tour_service.addWidget(self.ui.wdgAvatar.popupMenu(), event))
        elif isinstance(event, CharacterEditorAvatarMenuCloseTourEvent):
            self.ui.wdgAvatar.popupMenu().close()
            self._tour_service.next()
        elif isinstance(event, CharacterEditorBackButtonTourEvent):
            self._tour_service.addWidget(self.ui.btnClose, event)
