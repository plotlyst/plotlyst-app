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
from functools import partial
from typing import Optional, List

import qtanim
from PyQt6.QtCore import QItemSelection, QPoint
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QWidget
from overrides import overrides
from qthandy import busy, incr_font, bold
from qthandy.filter import InstantTooltipEventFilter, OpacityEventFilter
from qtmenu import MenuWidget

from plotlyst.common import PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import Novel, Character, CardSizeRatio, NovelSetting, NovelDescriptor
from plotlyst.env import app_env
from plotlyst.event.core import EventListener, Event, emit_event
from plotlyst.event.handler import event_dispatchers, global_event_dispatcher
from plotlyst.events import CharacterChangedEvent, CharacterDeletedEvent, NovelSyncEvent
from plotlyst.model.characters_model import CharactersTableModel
from plotlyst.model.common import proxy
from plotlyst.resources import resource_registry
from plotlyst.service.cache import entities_registry
from plotlyst.service.persistence import delete_character
from plotlyst.service.preview import NETWORK_PREVIEW
from plotlyst.view._view import AbstractNovelView
from plotlyst.view.character_editor import CharacterEditor
from plotlyst.view.common import link_buttons_to_pages, ButtonPressResizeEventFilter, \
    action
from plotlyst.view.generated.characters_title_ui import Ui_CharactersTitle
from plotlyst.view.generated.characters_view_ui import Ui_CharactersView
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import apply_bg_image, apply_white_menu
from plotlyst.view.widget.cards import CharacterCard
from plotlyst.view.widget.character.comp import CharacterComparisonWidget, \
    CharacterComparisonAttribute
from plotlyst.view.widget.character.comp import CharactersTreeView
from plotlyst.view.widget.character.network import CharacterNetworkView
from plotlyst.view.widget.character.prefs import CharactersPreferencesWidget
from plotlyst.view.widget.character.profile import CharacterOnboardingPopup, CharacterNameEditorPopup
from plotlyst.view.widget.characters import CharactersProgressWidget
from plotlyst.view.widget.display import PremiumOverlayWidget
from plotlyst.view.widget.importing import ImportCharacterPopup
from plotlyst.view.widget.tour.core import CharacterNewButtonTourEvent, TourEvent, \
    CharacterCardTourEvent, CharacterPerspectivesTourEvent, CharacterPerspectiveCardsTourEvent, \
    CharacterPerspectiveTableTourEvent, CharacterPerspectiveNetworkTourEvent, CharacterPerspectiveComparisonTourEvent, \
    CharacterPerspectiveProgressTourEvent, CharacterDisplayTourEvent


class CharactersTitle(QWidget, Ui_CharactersTitle, EventListener):

    def __init__(self, novel: Novel, parent=None):
        super(CharactersTitle, self).__init__(parent)
        self.novel = novel
        self.setupUi(self)
        self.btnCharacter.setIcon(IconRegistry.character_icon())
        incr_font(self.lblTitle)
        bold(self.lblTitle)

        self.refresh()

        dispatcher = event_dispatchers.instance(self.novel)
        dispatcher.register(self, CharacterChangedEvent)
        dispatcher.register(self, CharacterDeletedEvent)
        dispatcher.register(self, NovelSyncEvent)

    @overrides
    def event_received(self, event: Event):
        self.refresh()

    def refresh(self):
        self.btnMajor.setText(str(len(self.novel.major_characters())))
        self.btnSecondary.setText(str(len(self.novel.secondary_characters())))
        self.btnMinor.setText(str(len(self.novel.minor_characters())))


class CharactersView(AbstractNovelView):

    def __init__(self, novel: Novel, main_window=None):
        super().__init__(novel)
        self.ui = Ui_CharactersView()
        self.ui.setupUi(self.widget)
        self.main_window = main_window
        self.editor = CharacterEditor(self.novel)
        self.ui.pageEditor.layout().addWidget(self.editor.widget)
        self.editor.close.connect(self._on_close_editor)
        self.title = CharactersTitle(self.novel)
        self.ui.wdgTitleParent.layout().addWidget(self.title)

        self.model = CharactersTableModel(novel)
        self._proxy = proxy(self.model)
        self.ui.tblCharacters.setModel(self._proxy)
        self._proxy.setSortRole(CharactersTableModel.SortRole)

        self.ui.tblCharacters.setColumnWidth(CharactersTableModel.ColName, 200)
        self.ui.tblCharacters.setColumnWidth(CharactersTableModel.ColRole, 40)
        self.ui.tblCharacters.setColumnWidth(CharactersTableModel.ColAge, 40)
        self.ui.tblCharacters.setColumnWidth(CharactersTableModel.ColGender, 40)
        self.ui.tblCharacters.setColumnWidth(CharactersTableModel.ColEnneagram, 40)
        self.ui.tblCharacters.setColumnWidth(CharactersTableModel.ColMbti, 90)
        self.ui.tblCharacters.horizontalHeader().setProperty('main-header', True)

        for setting in [NovelSetting.CHARACTER_TABLE_ROLE, NovelSetting.CHARACTER_TABLE_AGE,
                        NovelSetting.CHARACTER_TABLE_GENDER,
                        NovelSetting.CHARACTER_TABLE_OCCUPATION,
                        NovelSetting.CHARACTER_TABLE_ENNEAGRAM,
                        NovelSetting.CHARACTER_TABLE_MBTI]:
            self._toggle_column(setting)

        self.ui.tblCharacters.selectionModel().selectionChanged.connect(self._on_character_selected)
        self.ui.tblCharacters.doubleClicked.connect(self.ui.btnEdit.click)
        self.ui.btnCardsView.setIcon(IconRegistry.cards_icon())
        self.ui.btnTableView.setIcon(IconRegistry.table_icon())
        self.ui.btnComparison.setIcon(
            IconRegistry.from_name('mdi.compare-horizontal', color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnRelationsView.setIcon(
            IconRegistry.from_name('ph.share-network-bold', color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnProgressView.setIcon(IconRegistry.progress_check_icon('black'))

        if not app_env.profile().get('character-comparison', False):
            self.ui.btnComparison.setHidden(True)
            self.ui.btnGroupViews.removeButton(self.ui.btnComparison)

        self.setNavigableButtonGroup(self.ui.btnGroupViews)

        self.ui.btnEdit.setIcon(IconRegistry.edit_icon())
        self.ui.btnEdit.clicked.connect(self._on_edit)
        self.ui.btnNew.setIcon(IconRegistry.plus_icon(color='white'))
        self.ui.btnNew.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnNew))
        self.ui.btnNew.clicked.connect(self._on_new)
        if app_env.is_mac():
            self.ui.btnDelete.setShortcut(QKeySequence('Ctrl+Backspace'))
        self.ui.btnDelete.setIcon(IconRegistry.trash_can_icon(color='white'))
        self.ui.btnDelete.clicked.connect(self._on_delete)

        self.ui.btnPreferences.setIcon(IconRegistry.preferences_icon())
        self.prefs_widget = CharactersPreferencesWidget(self.novel)
        self.prefs_widget.settingToggled.connect(self._character_prefs_toggled)
        menu = MenuWidget(self.ui.btnPreferences)
        apply_white_menu(menu)
        menu.addWidget(self.prefs_widget)

        if self.novel.is_readonly():
            for btn in [self.ui.btnNew, self.ui.btnDelete]:
                btn.setDisabled(True)
                btn.setToolTip('Option disabled in Scrivener synchronization mode')
                btn.installEventFilter(InstantTooltipEventFilter(btn))

        if self.novel.parent:
            self.set_series_enabled(True)

        self.selected_card: Optional[CharacterCard] = None
        self.ui.cards.selectionCleared.connect(lambda: self._enable_action_buttons(False))
        self.ui.cards.cardSelected.connect(self._card_selected)
        self.ui.cards.cardDoubleClicked.connect(self._on_edit)
        self.ui.cards.cardCustomContextMenuRequested.connect(self._show_card_menu)
        self.ui.cards.setCardsSizeRatio(CardSizeRatio.RATIO_2_3)
        self.ui.cards.setCardsWidth(142)
        self._init_cards()

        self.ui.btnSummaryComparison.setIcon(IconRegistry.synopsis_icon(color_on=PLOTLYST_SECONDARY_COLOR))
        # self.ui.btnBigFiveComparison.setIcon(IconRegistry.big_five_icon(color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnBigFiveComparison.setHidden(True)
        self.ui.btnFacultiesComparison.setIcon(
            IconRegistry.from_name('mdi6.head-lightbulb', color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnBackstoryComparison.setIcon(IconRegistry.backstory_icon('black', color_on=PLOTLYST_SECONDARY_COLOR))

        self.ui.splitterCompTree.setSizes([150, 500])
        self._wdgComparison = CharacterComparisonWidget(self.novel, self.ui.pageComparison)
        self.ui.scrollAreaComparisonContent.layout().addWidget(self._wdgComparison)
        self._wdgCharactersCompTree = CharactersTreeView(self.novel)
        self.ui.wdgCharactersCompTreeParent.layout().addWidget(self._wdgCharactersCompTree)
        self.ui.btnCharactersToggle.setIcon(IconRegistry.character_icon())
        self.ui.btnCharactersToggle.clicked.connect(
            partial(qtanim.toggle_expansion, self.ui.wdgCharactersCompTreeParent))

        self._wdgCharactersCompTree.characterToggled.connect(self._wdgComparison.updateCharacter)
        self.ui.btnSummaryComparison.clicked.connect(
            lambda: self._wdgComparison.displayAttribute(CharacterComparisonAttribute.SUMMARY))
        self.ui.btnFacultiesComparison.clicked.connect(
            lambda: self._wdgComparison.displayAttribute(CharacterComparisonAttribute.FACULTIES))
        # self.ui.btnBigFiveComparison.clicked.connect(
        #     lambda: self._wdgComparison.displayAttribute(CharacterComparisonAttribute.BIG_FIVE))
        self.ui.btnBackstoryComparison.clicked.connect(
            lambda: self._wdgComparison.displayAttribute(CharacterComparisonAttribute.BACKSTORY))
        for btn in self.ui.btnGroupComparison.buttons():
            btn.installEventFilter(OpacityEventFilter(btn, ignoreCheckedButton=True))
        self.ui.btnGroupComparison.buttonClicked.connect(self._comparison_type_clicked)

        self._relations = CharacterNetworkView(self.novel)
        self.ui.relationsParent.layout().addWidget(self._relations)
        self.ui.wdgGraphSelectorParent.setVisible(False)

        self.ui.networkSplitter.setSizes([100, 500])

        self._progress = CharactersProgressWidget()
        self.ui.pageProgressView.layout().addWidget(self._progress)
        self._progress.setNovel(self.novel)
        self._progress.characterClicked.connect(self._edit_character)
        self._progress.refresh()

        if not app_env.profile().get('network', False):
            self._networkOverlay = PremiumOverlayWidget(self.ui.pageRelationsView, 'Character network',
                                                        icon='ph.share-network-bold',
                                                        alt_link='https://plotlyst.com/docs/characters/',
                                                        preview=NETWORK_PREVIEW)

        self.ui.btnGroupViews.buttonToggled.connect(self._switch_view)
        link_buttons_to_pages(self.ui.stackCharacters, [(self.ui.btnCardsView, self.ui.pageCardsView),
                                                        (self.ui.btnTableView, self.ui.pageTableView),
                                                        (self.ui.btnRelationsView, self.ui.pageRelationsView),
                                                        (self.ui.btnComparison, self.ui.pageComparison),
                                                        (self.ui.btnProgressView, self.ui.pageProgressView)])
        self.ui.btnCardsView.setChecked(True)

        self.ui.cards.orderChanged.connect(self._characters_swapped)
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageView)

        global_event_dispatcher.register(self, CharacterNewButtonTourEvent, CharacterCardTourEvent,
                                         CharacterPerspectivesTourEvent, CharacterPerspectiveCardsTourEvent,
                                         CharacterPerspectiveTableTourEvent,
                                         CharacterPerspectiveNetworkTourEvent, CharacterPerspectiveComparisonTourEvent,
                                         CharacterPerspectiveProgressTourEvent, CharacterDisplayTourEvent)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, TourEvent):
            self.__handle_tour_event(event)
        elif isinstance(event, NovelSyncEvent):
            self._sync()
            return
        else:
            super().event_received(event)

    def close_event(self):
        if self.ui.stackedWidget.currentWidget() == self.ui.pageEditor:
            self.editor.close_event()

    def set_series_enabled(self, enabled: bool):
        pass
        # if enabled:
        #     self._series_menu = MenuWidget()
        #     self._series_menu.addAction(action('Add new character', IconRegistry.character_icon(), slot=self._on_new))
        #     self._series_menu.addSeparator()
        #     self._series_menu.addAction(
        #         action('Import from series...', IconRegistry.series_icon(), slot=self.import_from_series))
        # else:
        #     if self._series_menu:
        #         gc(self._series_menu)
        #         self._series_menu = None

    @overrides
    def refresh(self):
        self.model.modelReset.emit()
        self.ui.btnEdit.setDisabled(True)
        self.ui.btnDelete.setDisabled(True)

        self._progress.refreshNext()
        self._wdgCharactersCompTree.refresh()

    def _sync(self):
        self.refresh()
        self._init_cards()

    def _show_card_menu(self, card: CharacterCard, pos: QPoint):
        menu = MenuWidget()
        menu.addAction(action('Edit profile', IconRegistry.edit_icon(), self._on_edit))
        menu.addAction(
            action('Edit displayed name', IconRegistry.from_name('mdi.badge-account-outline'), self._on_edit_name))
        menu.addSeparator()
        action_ = action('Delete', IconRegistry.trash_can_icon(), self.ui.btnDelete.click)
        action_.setDisabled(self.novel.is_readonly())
        menu.addAction(action_)
        menu.exec()

    def _init_cards(self):
        self.selected_card = None
        self.ui.cards.clear()

        for character in self.novel.characters:
            card = self.__init_card_widget(character)
            self.ui.cards.addCard(card)

    def __init_card_widget(self, character: Character) -> CharacterCard:
        return CharacterCard(character, self.ui.cards)

    def _on_character_selected(self, selection: QItemSelection):
        self._enable_action_buttons(len(selection.indexes()) > 0)

    def _enable_action_buttons(self, enabled: bool):
        if not self.novel.is_readonly():
            self.ui.btnDelete.setEnabled(enabled)
        self.ui.btnEdit.setEnabled(enabled)

    def _card_selected(self, card: CharacterCard):
        if self.selected_card and self.selected_card is not card:
            self.selected_card.clearSelection()
        self.selected_card = card
        if not self.novel.is_readonly():
            self.ui.btnDelete.setEnabled(True)
        self.ui.btnEdit.setEnabled(True)

    def _characters_swapped(self, characters: List[Character], _: CharacterCard):
        self.novel.characters[:] = characters

        self.selected_card = None

        self.refresh()
        self.repo.update_novel(self.novel)

    def _switch_view(self):
        if self.ui.btnCardsView.isChecked():
            self._enable_action_buttons(bool(self.selected_card))
            self.ui.wdgToolbar.setVisible(True)
        elif self.ui.btnTableView.isChecked():
            self._enable_action_buttons(len(self.ui.tblCharacters.selectedIndexes()) > 0)
            self.ui.wdgToolbar.setVisible(True)
        elif self.ui.btnRelationsView.isChecked():
            self._relations.refresh()
            self.ui.wdgToolbar.setVisible(False)
        elif self.ui.btnComparison.isChecked():
            self.ui.wdgToolbar.setVisible(False)
        else:
            self.ui.wdgToolbar.setVisible(False)

    def _on_edit(self):
        character = None
        if self.ui.btnTableView.isChecked():
            indexes = self.ui.tblCharacters.selectedIndexes()
            if indexes:
                character = indexes[0].data(role=CharactersTableModel.CharacterRole)
        else:
            character = self.selected_card.character

        if character:
            self._edit_character(character)

    def _on_edit_name(self):
        character = self.selected_card.character
        CharacterNameEditorPopup.popup(character)
        self.repo.update_character(character)
        self.selected_card.refresh()

        emit_event(self.novel, CharacterChangedEvent(self, character))
        self.refresh()

    @busy
    def _edit_character(self, character: Character):
        self.title.setHidden(True)
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageEditor)

        self.editor.set_character(character)
        self.editor.ui.lineName.setFocus()

    @busy
    def _on_close_editor(self, character: Character):
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageView)
        self.title.setVisible(True)
        card = self.ui.cards.card(character)
        if card:
            card.refresh()

        emit_event(self.novel, CharacterChangedEvent(self, character))
        self.refresh()

    def import_from_series(self):
        series = entities_registry.series(self.novel)
        if series:
            novels: List[NovelDescriptor] = self.main_window.seriesNovels(series)
            novels[:] = [x for x in novels if x.id != self.novel.id]
            characters = ImportCharacterPopup.popup(series, novels)
            if characters:
                for character in characters:
                    self.novel.characters.append(character)
                    self.repo.insert_character(self.novel, character)
                    self.repo.update_doc(self.novel, character.document)
                    card = self.__init_card_widget(character)
                    self.ui.cards.addCard(card)

                emit_event(self.novel, CharacterChangedEvent(self, characters[0]))
                self.refresh()

    def _on_new(self):
        character = Character('')
        for personality in [NovelSetting.Character_enneagram, NovelSetting.Character_mbti,
                            NovelSetting.Character_love_style, NovelSetting.Character_work_style]:
            character.prefs.settings[personality.value] = self.novel.prefs.toggled(personality)

        self.novel.characters.append(character)
        self.repo.insert_character(self.novel, character)
        card = self.__init_card_widget(character)
        self.ui.cards.addCard(card)

        if CharacterOnboardingPopup.popup(character):
            self._edit_character(character)
        else:
            card.refresh()
            emit_event(self.novel, CharacterChangedEvent(self, character))
            self.refresh()

    @busy
    def _on_delete(self, checked: bool):
        character = None
        if self.ui.btnTableView.isChecked():
            indexes = self.ui.tblCharacters.selectedIndexes()
            if indexes:
                character = indexes[0].data(role=CharactersTableModel.CharacterRole)
        else:
            character = self.selected_card.character

        if character and delete_character(self.novel, character):
            self.selected_card = None
            emit_event(self.novel, CharacterDeletedEvent(self, character))
            self.ui.cards.remove(character)
            self.refresh()

    def _comparison_type_clicked(self):
        btn = self.ui.btnGroupComparison.checkedButton()
        if btn is self.ui.btnBackstoryComparison:
            apply_bg_image(self.ui.scrollAreaComparisonContent, resource_registry.cover1)
        else:
            self.ui.scrollAreaComparisonContent.setStyleSheet('')

    def _character_prefs_toggled(self, setting: NovelSetting, toggled: bool):
        self.novel.prefs.settings[setting.value] = toggled
        self.repo.update_novel(self.novel)

        self._toggle_column(setting)

    def _toggle_column(self, setting: NovelSetting):
        default = True

        if setting == NovelSetting.CHARACTER_TABLE_ROLE:
            col = CharactersTableModel.ColRole
        elif setting == NovelSetting.CHARACTER_TABLE_AGE:
            default = False
            col = CharactersTableModel.ColAge
        elif setting == NovelSetting.CHARACTER_TABLE_GENDER:
            default = False
            col = CharactersTableModel.ColGender
        elif setting == NovelSetting.CHARACTER_TABLE_OCCUPATION:
            default = False
            col = CharactersTableModel.ColOccupation
        elif setting == NovelSetting.CHARACTER_TABLE_ENNEAGRAM:
            col = CharactersTableModel.ColEnneagram
        elif setting == NovelSetting.CHARACTER_TABLE_MBTI:
            col = CharactersTableModel.ColMbti
        else:
            return

        self.ui.tblCharacters.setColumnHidden(col, not self.novel.prefs.toggled(setting, default))

    def __handle_tour_event(self, event: TourEvent):
        if isinstance(event, CharacterNewButtonTourEvent):
            self._tour_service.addWidget(self.ui.btnNew, event)
        elif isinstance(event, CharacterCardTourEvent):
            card = self.ui.cards.cardAt(0)
            self._tour_service.addWidget(card, event)
        elif isinstance(event, CharacterPerspectivesTourEvent):
            self._tour_service.addWidget(self.ui.wdgPerspectives, event)
        elif isinstance(event, CharacterPerspectiveCardsTourEvent):
            if event.click_before:
                self.ui.btnCardsView.click()
            self._tour_service.addWidget(self.ui.btnCardsView, event)
        elif isinstance(event, CharacterPerspectiveTableTourEvent):
            if event.click_before:
                self.ui.btnTableView.click()
            self._tour_service.addWidget(self.ui.btnTableView, event)
        elif isinstance(event, CharacterPerspectiveComparisonTourEvent):
            if event.click_before:
                self.ui.btnComparison.click()
            self._tour_service.addWidget(self.ui.btnComparison, event)
        elif isinstance(event, CharacterPerspectiveNetworkTourEvent):
            if event.click_before:
                self.ui.btnRelationsView.click()
            self._tour_service.addWidget(self.ui.btnRelationsView, event)
        elif isinstance(event, CharacterPerspectiveProgressTourEvent):
            if event.click_before:
                self.ui.btnProgressView.click()
            self._tour_service.addWidget(self.ui.btnProgressView, event)
        elif isinstance(event, CharacterDisplayTourEvent):
            self._tour_service.addWidget(self.widget, event)
