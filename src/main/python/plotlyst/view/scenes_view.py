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
from typing import Optional, List

import qtanim
from PyQt6.QtCore import Qt, QModelIndex, \
    QPoint
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QWidget, QHeaderView
from overrides import overrides
from qthandy import incr_font, translucent, busy, bold, sp, transparent, incr_icon, retain_when_hidden
from qthandy.filter import InstantTooltipEventFilter, OpacityEventFilter
from qtmenu import MenuWidget

from plotlyst.common import PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import Scene, Novel, Chapter, SceneStage, Event, ScenePurposeType, \
    StoryStructure, NovelSetting, CardSizeRatio, Character, StoryBeat
from plotlyst.env import app_env
from plotlyst.event.core import EventListener, emit_event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import SceneChangedEvent, SceneDeletedEvent, NovelStoryStructureUpdated, \
    SceneSelectedEvent, SceneSelectionClearedEvent, AvailableSceneStagesChanged, CharacterChangedEvent, \
    CharacterDeletedEvent, \
    NovelAboutToSyncEvent, NovelSyncEvent, NovelStoryStructureActivationRequest, NovelPanelCustomizationEvent, \
    NovelStorylinesToggleEvent, NovelStructureToggleEvent, NovelPovTrackingToggleEvent, SceneAddedEvent, \
    SceneStoryBeatChangedEvent, ActiveSceneStageChanged, NovelScenesOrganizationToggleEvent
from plotlyst.events import SceneOrderChangedEvent
from plotlyst.model.common import SelectionItemsModel
from plotlyst.model.novel import NovelStagesModel
from plotlyst.model.scenes_model import ScenesTableModel, ScenesFilterProxyModel, ScenesStageTableModel
from plotlyst.service.cache import acts_registry
from plotlyst.service.persistence import delete_scene
from plotlyst.view._view import AbstractNovelView
from plotlyst.view.common import ButtonPressResizeEventFilter, action, restyle, insert_after
from plotlyst.view.delegates import ScenesViewDelegate
from plotlyst.view.dialog.items import ItemsEditorDialog
from plotlyst.view.generated.scenes_title_ui import Ui_ScenesTitle
from plotlyst.view.generated.scenes_view_ui import Ui_ScenesView
from plotlyst.view.icons import IconRegistry
from plotlyst.view.scene_editor import SceneEditor
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.widget.cards import SceneCard, SceneCardFilter
from plotlyst.view.widget.chart import ActDistributionChart
from plotlyst.view.widget.display import ChartView
from plotlyst.view.widget.input import RotatedButtonOrientation
from plotlyst.view.widget.novel import StoryStructureSelectorMenu
from plotlyst.view.widget.progress import SceneStageProgressCharts
from plotlyst.view.widget.scene.story_map import StoryMap, StoryMapDisplayMode
from plotlyst.view.widget.scenes import SceneFilterWidget, \
    ScenesPreferencesWidget, ScenesDistributionWidget, ScenePreferencesTabType
from plotlyst.view.widget.structure.selector import ActSelectorButtons
from plotlyst.view.widget.tree import TreeSettings


class ScenesTitle(QWidget, Ui_ScenesTitle, EventListener):

    def __init__(self, novel: Novel, parent=None):
        super(ScenesTitle, self).__init__(parent)
        self.novel = novel
        self.setupUi(self)
        self.btnScenes.setIcon(IconRegistry.scene_icon())
        incr_font(self.lblTitle)
        bold(self.lblTitle)
        self.btnScene.setIcon(IconRegistry.action_scene_icon())
        self.btnSequel.setIcon(IconRegistry.reaction_scene_icon())
        translucent(self.btnScene, 0.6)
        translucent(self.btnSequel, 0.6)
        self.refreshTitle()

        flag = app_env.profile().get('scene-purpose', False)
        self.btnScene.setVisible(flag)
        self.btnSequel.setVisible(flag)

        self._chartDistribution = ActDistributionChart()
        self._chartDistributionView = ChartView()
        self._chartDistributionView.setFixedSize(356, 356)
        self._chartDistributionView.setChart(self._chartDistribution)

        menu = MenuWidget(self.btnCount)
        menu.addWidget(self._chartDistributionView)
        sp(self._chartDistributionView).h_exp().v_exp()
        self.refresh()

        dispatcher = event_dispatchers.instance(self.novel)
        dispatcher.register(self, SceneChangedEvent, SceneAddedEvent, SceneDeletedEvent, NovelSyncEvent,
                            NovelStoryStructureUpdated)

    @overrides
    def event_received(self, event: Event):
        self.refresh()

    def refresh(self):
        self.btnCount.setText(f'#{len(self.novel.scenes)}')
        self.btnScene.setText(f'{len([x for x in self.novel.scenes if x.purpose == ScenePurposeType.Story])}')
        self.btnSequel.setText(f'{len([x for x in self.novel.scenes if x.purpose == ScenePurposeType.Reaction])}')

        self.refreshDistributionChart()

    def refreshTitle(self):
        self.lblTitle.setText('Scenes' if self.novel.prefs.is_scenes_organization() else 'Chapters')

    def refreshDistributionChart(self):
        self._chartDistribution.refresh(self.novel)


class ScenesOutlineView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel,
                         [NovelStoryStructureUpdated, CharacterChangedEvent, SceneAddedEvent, SceneChangedEvent,
                          SceneDeletedEvent,
                          SceneOrderChangedEvent, NovelAboutToSyncEvent, NovelStorylinesToggleEvent,
                          NovelStructureToggleEvent, NovelPovTrackingToggleEvent, NovelScenesOrganizationToggleEvent,
                          SceneStoryBeatChangedEvent])
        self.ui = Ui_ScenesView()
        self.ui.setupUi(self.widget)

        self._scene_added: Optional[Scene] = None

        self.title = ScenesTitle(self.novel)
        self.ui.wdgTitleParent.layout().addWidget(self.title)

        self.editor: Optional[SceneEditor] = None
        self.editor = SceneEditor(self.novel)
        self.editor.close.connect(self._on_close_editor)
        self.ui.pageEditor.layout().addWidget(self.editor.widget)

        self.storymap_view: Optional[StoryMap] = None
        self.stagesModel: Optional[ScenesStageTableModel] = None
        self.stagesProgress: Optional[SceneStageProgressCharts] = None
        self.characters_distribution: Optional[ScenesDistributionWidget] = None

        self.tblModel = ScenesTableModel(novel)
        # self.tblModel.setDragEnabled(not self.novel.is_readonly())
        self.tblModel.setDragEnabled(False)
        self._proxy = ScenesFilterProxyModel()
        self._proxy.setSourceModel(self.tblModel)
        self._proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.ui.tblScenes.setModel(self._proxy)
        self.ui.tblScenes.horizontalHeader().setFixedHeight(30)
        self.ui.tblScenes.horizontalHeader().setProperty('main-header', True)
        self.ui.tblScenes.verticalHeader().setFixedWidth(40)
        self.ui.tblScenes.verticalHeader().setVisible(True)
        self.tblModel.orderChanged.connect(self._on_scene_moved_in_table)
        self.tblModel.sceneChanged.connect(self._on_scene_changed_in_table)
        self.ui.tblScenes.setColumnWidth(ScenesTableModel.ColTitle, 250)
        self.ui.tblScenes.setColumnWidth(ScenesTableModel.ColCharacters, 170)
        self.ui.tblScenes.setColumnWidth(ScenesTableModel.ColType, 55)
        self.ui.tblScenes.setColumnWidth(ScenesTableModel.ColPov, 60)
        self.ui.tblScenes.setColumnWidth(ScenesTableModel.ColProgress, 55)
        self.ui.tblScenes.setColumnWidth(ScenesTableModel.ColSynopsis, 400)
        self.ui.tblScenes.setItemDelegate(ScenesViewDelegate())
        self.ui.tblScenes.hideColumn(ScenesTableModel.ColTime)

        self.ui.splitterLeft.setSizes([120, 500])

        self._addSceneMenu = MenuWidget(self.ui.btnNewWithMenu)
        self._addSceneMenu.addAction(action('Add scene', IconRegistry.scene_icon(), self._new_scene))
        self._addSceneMenu.addAction(
            action('Add chapter', IconRegistry.chapter_icon(), self.ui.treeChapters.addChapter))

        self.ui.treeChapters.setSettings(TreeSettings(font_incr=2))
        self.ui.treeChapters.setNovel(self.novel, readOnly=self.novel.is_readonly())
        self.ui.treeChapters.chapterSelected.connect(self._on_chapter_selected)
        self.ui.treeChapters.sceneSelected.connect(self.ui.cards.selectCard)
        self.ui.treeChapters.sceneDoubleClicked.connect(self._switch_to_editor)

        self.ui.wgtChapters.setVisible(self.ui.btnChaptersToggle.isChecked())
        self.ui.btnChaptersToggle.setIcon(IconRegistry.chapter_icon())
        self.ui.btnChaptersToggle.setChecked(self.novel.prefs.panels.scene_chapters_sidebar_toggled)
        self._handle_scenes_organization()
        self.ui.btnChaptersToggle.clicked.connect(self._hide_chapters_clicked)
        self.ui.wgtChapters.setVisible(self.ui.btnChaptersToggle.isChecked())

        self._actFilter = ActSelectorButtons(self.novel)
        insert_after(self.ui.widget, self._actFilter, self.ui.lineBeforeActFilter)
        self._actFilter.actToggled.connect(self._proxy.setActsFilter)
        self._actFilter.reset.connect(self._proxy.resetActsFilter)

        self.ui.btnCardsView.setIcon(IconRegistry.cards_icon())
        self.ui.btnTableView.setIcon(IconRegistry.table_icon())
        self.ui.btnStoryStructure.setIcon(IconRegistry.story_structure_icon(color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnStoryStructureSelector.setIcon(IconRegistry.from_name('mdi.chevron-down'))
        self._structureSelectorMenu = StoryStructureSelectorMenu(self.novel, self.ui.btnStoryStructureSelector)
        self._structureSelectorMenu.selected.connect(self._active_story_structure_changed)
        self.ui.btnStoryStructureSelector.setHidden(True)
        self.ui.btnStatusView.setIcon(IconRegistry.progress_check_icon('black'))
        self.ui.btnCharactersDistributionView.setIcon(
            IconRegistry.from_name('fa5s.chess-board', color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnStorymap.setIcon(
            IconRegistry.from_name('mdi.transit-connection-horizontal', color_on=PLOTLYST_SECONDARY_COLOR))

        self.ui.btnStorymap.setVisible(self.novel.prefs.toggled(NovelSetting.Storylines))
        structure_visible = self.novel.prefs.toggled(NovelSetting.Structure)
        self.ui.btnStoryStructure.setVisible(structure_visible)
        self.ui.wdgStoryStructure.setVisible(structure_visible)

        if not app_env.profile().get('storylines', False):
            self.ui.btnStorymap.setHidden(True)
            self.ui.btnGroupViews.removeButton(self.ui.btnStorymap)

        self.setNavigableButtonGroup(self.ui.btnGroupViews)

        self.ui.wdgOrientation.setHidden(True)
        self.ui.rbHorizontal.setIcon(IconRegistry.from_name('fa5s.grip-lines'))
        self.ui.rbVertical.setIcon(IconRegistry.from_name('fa5s.grip-lines-vertical'))
        self.ui.btnStoryMapDisplay.setIcon(IconRegistry.from_name('mdi.source-branch', rotated=90))
        self.ui.btnStoryGridDisplay.setIcon(IconRegistry.from_name('mdi6.timeline-text-outline'))
        incr_font(self.ui.btnStoryMapDisplay, 2)
        incr_icon(self.ui.btnStoryMapDisplay, 2)
        incr_font(self.ui.btnStoryGridDisplay, 2)
        incr_icon(self.ui.btnStoryGridDisplay, 2)
        retain_when_hidden(self.ui.wdgStorymapToolbar)
        self.ui.wdgStorymapSelectors.setHidden(True)

        self.ui.btnStageCustomize.setIcon(IconRegistry.cog_icon())
        transparent(self.ui.btnStageCustomize)
        self.ui.btnStageCustomize.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnStageCustomize))
        self.ui.btnStageCustomize.installEventFilter(OpacityEventFilter(self.ui.btnStageCustomize, enterOpacity=0.7))
        self.ui.btnStageCustomize.clicked.connect(self._customize_stages)

        self.selected_card: Optional[SceneCard] = None
        self._card_filter = SceneCardFilter()
        self._actFilter.actToggled.connect(self._filter_cards)
        self._actFilter.reset.connect(self._filter_cards)
        self.ui.btnStoryStructure.toggled.connect(self._story_structure_toggled)
        self.ui.cards.selectionCleared.connect(self._selection_cleared)
        self.ui.cards.cardSelected.connect(self._card_selected)
        self.ui.cards.cardDoubleClicked.connect(self._on_edit)
        self.ui.cards.cardEntered.connect(lambda x: self.ui.wdgStoryStructure.highlightScene(x.scene))
        self.ui.cards.cardLeft.connect(lambda x: self.ui.wdgStoryStructure.clearHighlights())
        self.ui.cards.cardCustomContextMenuRequested.connect(self._show_card_menu)

        self.ui.btnPreferences.setIcon(IconRegistry.preferences_icon())
        self.prefs_widget = ScenesPreferencesWidget(self.novel)
        self.prefs_widget.settingToggled.connect(self._scene_prefs_toggled)
        self.prefs_widget.tabChanged.connect(self._scene_prefs_tab_changed)
        self.prefs_widget.cardWidthChanged.connect(self._scene_card_width_changed)
        self.prefs_widget.cardRatioChanged.connect(self._scene_card_ratio_changed)
        self.ui.cards.setCardsWidth(
            self.novel.prefs.setting(NovelSetting.SCENE_CARD_WIDTH, ScenesPreferencesWidget.DEFAULT_CARD_WIDTH))
        menu = MenuWidget(self.ui.btnPreferences)
        apply_white_menu(menu)
        menu.addWidget(self.prefs_widget)

        self.ui.btnGroupViews.buttonToggled.connect(self._switch_view)
        self.ui.btnCardsView.setChecked(True)

        self.ui.wdgStoryStructureParent.setHidden(True)
        self.ui.wdgStoryStructure.setActsClickable(False)
        self.ui.wdgStoryStructure.setBeatsSelectable(True)
        self.ui.wdgStoryStructure.beatToggled.connect(self._beat_toggled)
        self.ui.wdgStoryStructure.setStructure(self.novel)

        self.ui.btnFilter.setIcon(IconRegistry.filter_icon())

        self._scene_filter = SceneFilterWidget(self.novel)
        filterMenu = MenuWidget(self.ui.btnFilter)
        filterMenu.addWidget(self._scene_filter)
        self._toggle_act_filters()
        self._scene_filter.povFilter.characterToggled.connect(self._proxy.setCharacterFilter)
        self._scene_filter.povFilter.characterToggled.connect(self._filter_cards)

        self._actFilter.actClicked.connect(self._scene_filter.wdgActs.setActChecked)
        self._scene_filter.wdgActs.actClicked.connect(self._actFilter.setActChecked)

        self._init_cards()

        self.ui.tblScenes.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.tblScenes.customContextMenuRequested.connect(self._on_custom_menu_requested)

        self.ui.tblScenes.selectionModel().selectionChanged.connect(self._on_scene_selected)
        self.ui.tblScenes.doubleClicked.connect(self.ui.btnEdit.click)

        self.ui.btnEdit.setIcon(IconRegistry.edit_icon())
        self.ui.btnEdit.clicked.connect(self._on_edit)
        self.ui.btnNew.setIcon(IconRegistry.plus_icon(color='white'))
        self.ui.btnNewWithMenu.setIcon(IconRegistry.plus_icon(color='white'))
        self.ui.btnNew.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnNew))
        self.ui.btnNewWithMenu.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnNewWithMenu))
        self.ui.btnNew.clicked.connect(self._new_scene)
        self.ui.btnDelete.setIcon(IconRegistry.trash_can_icon(color='white'))
        if app_env.is_mac():
            self.ui.btnDelete.setShortcut(QKeySequence('Ctrl+Backspace'))
        self.ui.btnDelete.clicked.connect(self._on_delete)

        if self.novel.is_readonly():
            for btn in [self.ui.btnNew, self.ui.btnNewWithMenu, self.ui.btnDelete]:
                btn.setDisabled(True)
                btn.setToolTip('Option is disabled in Scrivener synchronization mode')
                btn.installEventFilter(InstantTooltipEventFilter(btn))

        self.ui.cards.orderChanged.connect(self._on_scene_cards_swapped)
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageView)

    def close_event(self):
        if self.ui.stackedWidget.currentWidget() == self.ui.pageEditor:
            self.editor.close_event()

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, (CharacterChangedEvent, CharacterDeletedEvent)):
            self._handle_character_changed(event.character)
            return
        elif isinstance(event, SceneChangedEvent):
            self._handle_scene_changed(event.scene)
            return
        elif isinstance(event, SceneDeletedEvent):
            self._handle_scene_deletion(event.scene)
            return
        elif isinstance(event, SceneAddedEvent):
            i = self.novel.scenes.index(event.scene)
            card = self.__init_card_widget(event.scene)
            self.ui.cards.insertAt(i, card)
            self._handle_scene_added()
            return
        elif isinstance(event, SceneOrderChangedEvent):
            self.ui.cards.reorderCards(self.novel.scenes)
            self._handle_scene_order_changed()
            return
        elif isinstance(event, SceneStoryBeatChangedEvent):
            self.ui.wdgStoryStructure.toggleBeat(event.beat, event.toggled)
            return
        elif isinstance(event, NovelStoryStructureUpdated):
            self._handle_structure_update()
            return
        elif isinstance(event, NovelSyncEvent):
            self._sync(event)
            return
        elif isinstance(event, NovelPanelCustomizationEvent):
            if isinstance(event, NovelStorylinesToggleEvent):
                self.ui.btnStorymap.setVisible(event.toggled)
                if self.ui.btnStorymap.isChecked():
                    self.ui.btnCardsView.setChecked(True)
            elif isinstance(event, NovelStructureToggleEvent):
                self.ui.btnStoryStructure.setVisible(event.toggled)
                self.ui.wdgStoryStructure.setVisible(event.toggled)
                self.ui.btnStoryStructureSelector.setVisible(
                    event.toggled and self.ui.btnStoryStructure.isChecked() and len(self.novel.story_structures) > 1)
            elif isinstance(event, NovelPovTrackingToggleEvent):
                self.ui.tblScenes.setColumnHidden(self.tblModel.ColPov, not event.toggled)
            elif isinstance(event, NovelScenesOrganizationToggleEvent):
                self._handle_scenes_organization_event()
            return

        super(ScenesOutlineView, self).event_received(event)

    @busy
    @overrides
    def refresh(self):
        self.tblModel.modelReset.emit()
        self.ui.treeChapters.refresh()
        self.ui.btnEdit.setDisabled(True)
        self.ui.btnDelete.setDisabled(True)

        if self.stagesModel:
            self.stagesModel.modelReset.emit()
        if self.stagesProgress:
            self.stagesProgress.refresh()
        if self.characters_distribution:
            self.characters_distribution.refresh()

    def _sync(self, event: NovelSyncEvent):
        self.selected_card = None
        self.ui.cards.clearSelection()

        for scene in event.new_scenes:
            card = self.__init_card_widget(scene)
            self.ui.cards.addCard(card)

        self.ui.cards.reorderCards(self.novel.scenes)
        for card in self.ui.cards.cards():
            card.quickRefresh()

        self.refresh()
        self._filter_cards()

    def _switch_view(self):
        height = 50
        columns = self._default_columns()

        if self.ui.btnStatusView.isChecked():
            self.ui.stackScenes.setCurrentWidget(self.ui.pageStages)
            self.ui.tblScenes.clearSelection()
            if not self.stagesModel:
                self._init_stages_view()
        elif self.ui.btnCardsView.isChecked():
            self.ui.stackScenes.setCurrentWidget(self.ui.pageCards)
            self.ui.tblScenes.clearSelection()
            self.prefs_widget.showCardsTab()
        elif self.ui.btnStorymap.isChecked():
            self.ui.stackScenes.setCurrentWidget(self.ui.pageStorymap)
            self.ui.tblScenes.clearSelection()
            self.ui.tblSceneStages.clearSelection()
            if not self.storymap_view:
                self.storymap_view = StoryMap()
                self.ui.scrollAreaStoryMap.layout().addWidget(self.storymap_view)
                self.ui.btnGroupStoryMapView.buttonClicked.connect(self._story_map_mode_clicked)
                self.ui.cbStoryMapDetailed.clicked.connect(self._story_map_mode_clicked)
                self.ui.rbHorizontal.clicked.connect(
                    lambda: self.storymap_view.setOrientation(Qt.Orientation.Horizontal))
                self.ui.rbVertical.clicked.connect(lambda: self.storymap_view.setOrientation(Qt.Orientation.Vertical))
                self._actFilter.actToggled.connect(self.storymap_view.setActsFilter)
                self._actFilter.reset.connect(self.storymap_view.resetActsFilter)
                filters = self._actFilter.actFilters()
                if filters:
                    for k, v in filters.items():
                        self.storymap_view.setActsFilter(k, v)
                self.storymap_view.sceneSelected.connect(self._storymap_scene_selected)
                self.storymap_view.setNovel(self.novel)
        elif self.ui.btnCharactersDistributionView.isChecked():
            self.ui.stackScenes.setCurrentWidget(self.ui.pageCharactersDistribution)
            self.ui.tblScenes.clearSelection()
            self.ui.tblSceneStages.clearSelection()
            if not self.characters_distribution:
                self.characters_distribution = ScenesDistributionWidget(self.novel)
                self.ui.pageCharactersDistribution.layout().addWidget(self.characters_distribution)
                self._actFilter.actToggled.connect(self.characters_distribution.setActsFilter)
                self._actFilter.reset.connect(self.characters_distribution.resetActsFilter)
                filters = self._actFilter.actFilters()
                if filters:
                    for k, v in filters.items():
                        self.characters_distribution.setActsFilter(k, v)
        elif self.ui.btnTableView.isChecked():
            self.ui.stackScenes.setCurrentWidget(self.ui.pageDefault)
            self.ui.tblSceneStages.clearSelection()
            self.prefs_widget.showTableTab()

        self._toggle_table_columns(columns)

        self.ui.tblScenes.verticalHeader().setDefaultSectionSize(height)

        emit_event(self.novel, SceneSelectionClearedEvent(self))

    def _on_scene_selected(self):
        indexes = self.ui.tblScenes.selectedIndexes()
        selection = len(indexes) > 0
        self._enable_action_buttons(selection)
        if selection:
            scene = indexes[0].data(ScenesTableModel.SceneRole)
            self.ui.treeChapters.selectScene(scene)
            emit_event(self.novel, SceneSelectedEvent(self, scene))

    def _on_chapter_selected(self, chapter: Chapter):
        self.ui.tblScenes.clearSelection()
        if self.selected_card:
            self.selected_card.clearSelection()
            self.selected_card = None
        if not self.novel.is_readonly():
            self.ui.btnDelete.setEnabled(True)
        self.ui.btnEdit.setEnabled(False)

    def _hide_chapters_clicked(self, toggled: bool):
        def select_scene():
            if toggled and self.selected_card:
                self.ui.treeChapters.selectScene(self.selected_card.scene)

        if self.novel.prefs.is_scenes_organization():
            self.ui.btnNew.setHidden(toggled)
            self.ui.btnNewWithMenu.setVisible(toggled)
        else:
            self.ui.btnNew.setVisible(True)
            self.ui.btnNewWithMenu.setHidden(True)
        qtanim.toggle_expansion(self.ui.wgtChapters, toggled, teardown=select_scene)

        if self.novel.prefs.panels.scene_chapters_sidebar_toggled != toggled:
            self.novel.prefs.panels.scene_chapters_sidebar_toggled = toggled
            self.repo.update_novel(self.novel)

    def _on_edit(self):
        scene: Optional[Scene] = self._selected_scene()
        if scene:
            self._switch_to_editor(scene)

    def _selected_scene(self) -> Optional[Scene]:
        if self.ui.btnCardsView.isChecked() and self.selected_card:
            return self.selected_card.scene
        scenes = self.ui.treeChapters.selectedScenes()
        if scenes:
            return scenes[0]
        else:
            indexes = None
            if self.ui.btnTableView.isChecked():
                indexes = self.ui.tblScenes.selectedIndexes()

            if indexes:
                return indexes[0].data(role=ScenesTableModel.SceneRole)
            else:
                return None

    @busy
    def _switch_to_editor(self, scene: Scene):
        self.title.setHidden(True)
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageEditor)
        if self._scene_added is not None:
            self.editor.refresh()
        self.editor.set_scene(scene)
        self.editor.ui.lineTitle.setFocus()

    @busy
    def _on_close_editor(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageView)
        self.title.setVisible(True)
        self._scene_filter.povFilter.updateCharacters(self.novel.pov_characters(), checkAll=True)

        if self._scene_added is not None:
            emit_event(self.novel, SceneAddedEvent(self, self._scene_added), delay=10)

            self._handle_scene_added()
        self._scene_added = None

    @busy
    def _new_scene(self, _):
        scene = self.novel.new_scene()
        self.novel.scenes.append(scene)
        self.repo.insert_scene(self.novel, scene)

        card = self.__init_card_widget(scene)
        self.ui.cards.addCard(card)
        self._scene_added = scene
        self._switch_to_editor(scene)

    def _scene_context_menu(self, scene: Scene) -> MenuWidget:
        menu = MenuWidget()
        unit = 'scene' if self.novel.prefs.is_scenes_organization() else 'chapter'
        menu.addAction(action('Edit', IconRegistry.edit_icon(), self._on_edit))
        action_ = action(f'Insert new {unit}', IconRegistry.plus_icon('black'),
                         partial(self._insert_scene_after, scene))
        action_.setDisabled(self.novel.is_readonly())
        menu.addAction(action_)
        menu.addSeparator()
        action_ = action('Delete', IconRegistry.trash_can_icon(), self.ui.btnDelete.click)
        action_.setDisabled(self.novel.is_readonly())
        menu.addAction(action_)

        return menu

    def _show_card_menu(self, card: SceneCard, _: QPoint):
        menu = self._scene_context_menu(card.scene)
        menu.exec()

    def _init_cards(self):
        self.selected_card = None
        self.ui.cards.clear()

        for scene in self.novel.scenes:
            card = self.__init_card_widget(scene)
            self.ui.cards.addCard(card)

        self._filter_cards()

    def __init_card_widget(self, scene: Scene) -> SceneCard:
        card = SceneCard(scene, self.novel, self.ui.cards)
        card.setDragEnabled(not self.novel.is_readonly())
        return card

    def _filter_cards(self):
        self._card_filter.setActsFilter(self._actFilter.actFilters())
        self._card_filter.setActivePovs(self._scene_filter.povFilter.characters(all=False))
        self.ui.cards.applyFilter(self._card_filter)

    def _story_structure_toggled(self, toggled: bool):
        if toggled:
            qtanim.fade_in(self.ui.wdgStoryStructureParent,
                           teardown=lambda: self.ui.wdgStoryStructureParent.setGraphicsEffect(None))
        else:
            qtanim.fade_out(self.ui.wdgStoryStructureParent,
                            teardown=lambda: self.ui.wdgStoryStructureParent.setGraphicsEffect(None))

        if toggled:
            self.ui.btnStoryStructureSelector.setVisible(len(self.novel.story_structures) > 1)
            if self.ui.btnStoryStructureSelector.isVisible():
                self.ui.btnStoryStructure.setProperty('side-button-right', True)
                restyle(self.ui.btnStoryStructure)
        else:
            self.ui.btnStoryStructureSelector.setHidden(True)
            self.ui.btnStoryStructure.setProperty('side-button-right', False)
            restyle(self.ui.btnStoryStructure)

    @busy
    def _active_story_structure_changed(self, structure: StoryStructure):
        emit_event(self.novel, NovelStoryStructureActivationRequest(self, self.novel, structure))

    def _card_selected(self, card: SceneCard):
        if self.selected_card and self.selected_card is not card:
            self.selected_card.clearSelection()
        self.selected_card = card
        self._enable_action_buttons(True)
        if self.ui.treeChapters.isVisible():
            self.ui.treeChapters.selectScene(card.scene)
        emit_event(self.novel, SceneSelectedEvent(self, card.scene))

    def _storymap_scene_selected(self, scene: Scene):
        self.ui.wdgStoryStructure.highlightScene(scene)
        if self.ui.treeChapters.isVisible():
            self.ui.treeChapters.selectScene(scene)

    def _selection_cleared(self):
        self._enable_action_buttons(False)
        self.selected_card = None
        self.ui.treeChapters.clearSelection()

    def _enable_action_buttons(self, enabled: bool):
        if not self.novel.is_readonly():
            self.ui.btnDelete.setEnabled(enabled)
        self.ui.btnEdit.setEnabled(enabled)
        self.ui.wdgStoryStructure.activateBeatSelection(enabled)

    def _customize_stages(self):
        diag = ItemsEditorDialog(NovelStagesModel(copy.deepcopy(self.novel.stages)))
        diag.wdgItemsEditor.tableView.setColumnHidden(SelectionItemsModel.ColIcon, True)
        diag.wdgItemsEditor.setRemoveAllEnabled(False)
        diag.wdgItemsEditor.setInsertionEnabled(True)
        items = diag.display()
        if items:
            self.novel.stages.clear()
            self.novel.stages.extend(items)

            for scene in self.novel.scenes:
                if scene.stage not in self.novel.stages:
                    scene.stage = None
                    self.repo.update_scene(scene)

            self.repo.update_novel(self.novel)
            self._init_stages_view()
            emit_event(self.novel, AvailableSceneStagesChanged(self))

    def _init_stages_view(self):
        def change_stage(stage: SceneStage):
            self.stagesProgress.setStage(stage)
            self.ui.btnStageSelector.setText(stage.text)
            self.stagesModel.setHighlightedStage(stage)
            self.novel.prefs.active_stage_id = stage.id
            self.repo.update_novel(self.novel)
            emit_event(self.novel, ActiveSceneStageChanged(self, stage), delay=10)

        def header_clicked(col: int):
            if col > 1:
                stage = self.novel.stages[col - 2]
                change_stage(stage)

        if self.stagesModel:
            self.stagesModel.modelReset.emit()
        else:
            self.stagesModel = ScenesStageTableModel(self.novel)
            self._stages_proxy = ScenesFilterProxyModel()
            self._stages_proxy.setSourceModel(self.stagesModel)
            self._stages_proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self._stages_proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.ui.tblSceneStages.setModel(self._stages_proxy)

            self._actFilter.actToggled.connect(self._stages_proxy.setActsFilter)
            self._actFilter.reset.connect(self._stages_proxy.resetActsFilter)
            filters = self._actFilter.actFilters()
            if filters:
                for k, v in filters.items():
                    self._stages_proxy.setActsFilter(k, v)
            self.ui.tblSceneStages.horizontalHeader().setProperty('main-header', True)
            restyle(self.ui.tblSceneStages.horizontalHeader())
            self.ui.tblSceneStages.horizontalHeader().sectionClicked.connect(header_clicked)
            self.ui.tblSceneStages.verticalHeader().setFixedWidth(40)
            self.ui.tblSceneStages.setColumnWidth(ScenesStageTableModel.ColTitle, 250)

        for col in range(1, self.stagesModel.columnCount()):
            self.ui.tblSceneStages.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
            w = self.ui.tblSceneStages.horizontalHeader().sectionSize(col)
            self.ui.tblSceneStages.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            self.ui.tblSceneStages.setColumnWidth(col, w + 10)

        if not self.stagesProgress:
            self.stagesProgress = SceneStageProgressCharts(self.novel)
            self.ui.wdgProgressCharts.layout().addWidget(self.stagesProgress)

            self.ui.tblSceneStages.clicked.connect(
                lambda x: self.stagesModel.changeStage(self._stages_proxy.mapToSource(x)))

            self.ui.btnStageSelector.setOrientation(RotatedButtonOrientation.VerticalBottomToTop)
            self.ui.btnStageSelector.setIcon(IconRegistry.progress_check_icon())

        menu = MenuWidget(self.ui.btnStageSelector)
        for stage in self.novel.stages:
            menu.addAction(action(stage.text, slot=partial(change_stage, stage)))
        menu.addSeparator()
        menu.addAction(action('Customize', IconRegistry.cog_icon(), slot=self._customize_stages))

        if not self.novel.prefs.active_stage_id:
            self.novel.prefs.active_stage_id = self.stagesProgress.stage().id
            self.repo.update_novel(self.novel)
        self.ui.btnStageSelector.setText(self.stagesProgress.stage().text)
        self.stagesModel.setHighlightedStage(self.stagesProgress.stage())

        if self.novel.scenes:
            self.stagesProgress.refresh()
            # if not self.ui.wdgProgressCharts.layout().count():
            #     for i, chartview in enumerate(self.stagesProgress.charts()):
            #         self.ui.wdgProgressCharts.layout().insertWidget(i, chartview)

    def _on_custom_menu_requested(self, pos: QPoint):
        index: QModelIndex = self.ui.tblScenes.indexAt(pos)
        menu = self._scene_context_menu(index.data(ScenesTableModel.SceneRole))
        menu.exec(self.ui.tblScenes.viewport().mapToGlobal(pos))

    def _insert_scene_after(self, scene: Scene, chapter: Optional[Chapter] = None):
        new_scene = self.novel.insert_scene_after(scene, chapter)
        self.repo.insert_scene(self.novel, new_scene)

        ref_card = self.ui.cards.card(scene)
        card = self.__init_card_widget(new_scene)
        self.ui.cards.insertAfter(ref_card, card)

        for card in self.ui.cards.cards():
            card.quickRefresh()

        self._scene_added = new_scene
        self._switch_to_editor(new_scene)

    def _on_delete(self):
        scene: Optional[Scene] = self._selected_scene()
        if scene and delete_scene(self.novel, scene):
            self._handle_scene_deletion(scene)
            emit_event(self.novel, SceneDeletedEvent(self, scene))

        elif not scene:
            chapters = self.ui.treeChapters.selectedChapters()
            if chapters:
                self.ui.treeChapters.removeChapter(chapters[0])

    def _on_scene_cards_swapped(self, scenes: List[Scene], droppedCard: SceneCard):
        droppedScene = droppedCard.scene
        i = scenes.index(droppedScene)
        if i == 0 and len(scenes) > 1:  # first pos
            if scenes[1].chapter:
                droppedScene.chapter = scenes[1].chapter
                self.repo.update_scene(droppedScene)
        elif i == len(scenes) - 1 and i > 0:  # last pos
            droppedScene.chapter = scenes[i - 1].chapter
            self.repo.update_scene(droppedScene)
        elif i < len(scenes) - 1:
            droppedScene.chapter = scenes[i + 1].chapter
            self.repo.update_scene(droppedScene)

        self.novel.scenes[:] = scenes
        self._handle_scene_order_changed()
        self.selected_card = None
        emit_event(self.novel, SceneOrderChangedEvent(self))

    def _on_scene_moved_in_table(self):
        self.ui.cards.reorderCards(self.novel.scenes)
        self._handle_scene_order_changed()
        emit_event(self.novel, SceneOrderChangedEvent(self))

    def _on_scene_changed_in_table(self, scene: Scene):
        emit_event(self.novel, SceneChangedEvent(self, scene))
        self._handle_scene_changed(scene)

    def _handle_scene_changed(self, scene: Scene):
        card = self.ui.cards.card(scene)
        if card:
            card.refresh()

        if self.characters_distribution:
            self.characters_distribution.refreshAverage()

    def _handle_scene_order_changed(self):
        self.repo.update_novel(self.novel)
        for card in self.ui.cards.cards():
            card.quickRefresh()

    def _handle_scene_deletion(self, scene: Scene):
        self.selected_card = None
        self.ui.cards.remove(scene)
        self._update_table_models()

    def _handle_scene_added(self):
        self._update_table_models()

    def _update_table_models(self):
        self.tblModel.modelReset.emit()
        if self.stagesModel:
            self.stagesModel.modelReset.emit()
        if self.stagesProgress:
            self.stagesProgress.refresh()
        if self.characters_distribution:
            self.characters_distribution.refresh()

    @busy
    def _handle_character_changed(self, _: Character):
        self._scene_filter.povFilter.updateCharacters(self.novel.pov_characters(), checkAll=True)
        for card in self.ui.cards.cards():
            card.refreshPov()
            card.refreshCharacters()

    def _handle_structure_update(self):
        if self.ui.btnStoryStructure.isChecked():
            self.ui.btnStoryStructureSelector.setVisible(len(self.novel.story_structures) > 1)
        self._toggle_act_filters()

        self.ui.wdgStoryStructure.setStructure(self.novel)
        if self._selected_scene():
            self.ui.wdgStoryStructure.activateBeatSelection(True)

        for card in self.ui.cards.cards():
            card.refreshBeat()

    def _handle_scenes_organization_event(self):
        self._handle_scenes_organization()
        self.title.refreshTitle()
        for card in self.ui.cards.cards():
            card.quickRefresh()

    def _handle_scenes_organization(self):
        scenes_organized = self.novel.prefs.is_scenes_organization()
        unit = 'scene' if scenes_organized else 'chapter'
        self.ui.btnNewWithMenu.setVisible(scenes_organized and self.ui.btnChaptersToggle.isChecked())
        self.ui.btnNew.setVisible(not scenes_organized or not self.ui.btnChaptersToggle.isChecked())
        self.ui.btnNew.setToolTip(f'Add new {unit}')
        self.ui.btnEdit.setToolTip(f'Edit selected {unit}')
        self.ui.btnDelete.setToolTip(f'Delete {unit}')

    def _story_map_mode_clicked(self):
        if self.ui.btnStoryMapDisplay.isChecked():
            if self.ui.cbStoryMapDetailed.isChecked():
                self.storymap_view.setMode(StoryMapDisplayMode.TITLE)
            else:
                self.storymap_view.setMode(StoryMapDisplayMode.DOTS)
            self.ui.wdgStorymapToolbar.setVisible(True)
        elif self.ui.btnStoryGridDisplay.isChecked():
            self.ui.wdgStorymapToolbar.setVisible(False)
            self.storymap_view.setMode(StoryMapDisplayMode.DETAILED)

    def _scene_prefs_toggled(self, setting: NovelSetting, toggled: bool):
        self.novel.prefs.settings[setting.value] = toggled
        self.repo.update_novel(self.novel)

        if setting.scene_card_setting():
            self.ui.cards.setSetting(setting, toggled)
        elif setting.scene_table_setting():
            self._toggle_table_columns(self._default_columns())

    def _scene_prefs_tab_changed(self, tab_type: ScenePreferencesTabType):
        if tab_type == ScenePreferencesTabType.CARDS:
            self.ui.btnCardsView.setChecked(True)
        elif tab_type == ScenePreferencesTabType.TABLE:
            self.ui.btnTableView.setChecked(True)

    def _scene_card_width_changed(self, width: int):
        self.novel.prefs.settings[NovelSetting.SCENE_CARD_WIDTH.value] = width
        self.repo.update_novel(self.novel)

        self.ui.cards.setCardsWidth(width)

    def _scene_card_ratio_changed(self, ratio: CardSizeRatio):
        self.ui.cards.setCardsSizeRatio(ratio)

    def _default_columns(self) -> List[int]:
        default_columns = [ScenesTableModel.ColTitle]

        if self.novel.prefs.toggled(NovelSetting.SCENE_TABLE_POV):
            default_columns.append(ScenesTableModel.ColPov)
        if app_env.profile().get('storylines') and self.novel.prefs.toggled(NovelSetting.SCENE_TABLE_STORYLINES):
            default_columns.append(ScenesTableModel.ColStorylines)
        if self.novel.prefs.toggled(NovelSetting.SCENE_TABLE_CHARACTERS):
            default_columns.append(ScenesTableModel.ColCharacters)
        if app_env.profile().get('scene-purpose') and self.novel.prefs.toggled(NovelSetting.SCENE_TABLE_PURPOSE):
            default_columns.append(ScenesTableModel.ColType)
        if app_env.profile().get('scene-progression') and self.novel.prefs.toggled(
                NovelSetting.SCENE_TABLE_PLOT_PROGRESS):
            default_columns.append(ScenesTableModel.ColProgress)

        default_columns.append(ScenesTableModel.ColSynopsis)

        return default_columns

    def _toggle_table_columns(self, columns: List[int]):
        for col in range(self.tblModel.columnCount()):
            if col in columns:
                if col == self.tblModel.ColPov:
                    self.ui.tblScenes.setColumnHidden(self.tblModel.ColPov,
                                                      not self.novel.prefs.toggled(NovelSetting.Track_pov))
                else:
                    self.ui.tblScenes.showColumn(col)
                continue
            self.ui.tblScenes.hideColumn(col)

    def _toggle_act_filters(self):
        acts = self.novel.active_story_structure.acts
        self._actFilter.setVisible(acts > 0)
        self._scene_filter.lblActs.setVisible(acts > 0)
        self.ui.lineBeforeActFilter.setVisible(acts > 0)

    def _beat_toggled(self, beat: StoryBeat, toggled: bool):
        if toggled:
            scene = self._selected_scene()
            if scene is None:
                return

            previous_beat = scene.beat(self.novel)
            if previous_beat and previous_beat != beat:
                scene.remove_beat(self.novel)
                self.ui.wdgStoryStructure.toggleBeat(previous_beat, False)
            scene.link_beat(self.novel.active_story_structure, beat)
        else:
            scene = acts_registry.scene(beat)
            scene.remove_beat(self.novel)

        card = self.ui.cards.card(scene)
        card.refreshBeat()
        self.repo.update_scene(scene)
        emit_event(self.novel, SceneStoryBeatChangedEvent(self, scene, beat, toggled=toggled))

        self.title.refreshDistributionChart()
        if self.stagesProgress:
            self.stagesProgress.refresh()
