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
from typing import Optional, List

import qtanim
from PyQt6.QtCore import Qt, QModelIndex, \
    QPoint
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QWidget, QHeaderView
from overrides import overrides
from qthandy import incr_font, translucent, btn_popup, clear_layout, busy, bold, sp, transparent
from qthandy.filter import InstantTooltipEventFilter, OpacityEventFilter
from qtmenu import MenuWidget

from src.main.python.plotlyst.common import PLOTLYST_SECONDARY_COLOR
from src.main.python.plotlyst.core.domain import Scene, Novel, Chapter, SceneStage, Event, ScenePurposeType, \
    StoryStructure, NovelSetting
from src.main.python.plotlyst.env import app_env
from src.main.python.plotlyst.event.core import EventListener, emit_event
from src.main.python.plotlyst.event.handler import event_dispatchers
from src.main.python.plotlyst.events import SceneChangedEvent, SceneDeletedEvent, NovelStoryStructureUpdated, \
    SceneSelectedEvent, SceneSelectionClearedEvent, ActiveSceneStageChanged, \
    ChapterChangedEvent, AvailableSceneStagesChanged, CharacterChangedEvent, CharacterDeletedEvent, \
    NovelAboutToSyncEvent, NovelSyncEvent, NovelStoryStructureActivationRequest, NovelPanelCustomizationEvent, \
    NovelStorylinesToggleEvent, NovelStructureToggleEvent
from src.main.python.plotlyst.events import SceneOrderChangedEvent
from src.main.python.plotlyst.model.common import SelectionItemsModel
from src.main.python.plotlyst.model.novel import NovelStagesModel
from src.main.python.plotlyst.model.scenes_model import ScenesTableModel, ScenesFilterProxyModel, ScenesStageTableModel
from src.main.python.plotlyst.service.persistence import delete_scene
from src.main.python.plotlyst.view._view import AbstractNovelView
from src.main.python.plotlyst.view.common import PopupMenuBuilder, ButtonPressResizeEventFilter, action, restyle
from src.main.python.plotlyst.view.delegates import ScenesViewDelegate
from src.main.python.plotlyst.view.dialog.items import ItemsEditorDialog
from src.main.python.plotlyst.view.generated.scenes_title_ui import Ui_ScenesTitle
from src.main.python.plotlyst.view.generated.scenes_view_ui import Ui_ScenesView
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.scene_editor import SceneEditor
from src.main.python.plotlyst.view.widget.cards import SceneCard, SceneCardFilter
from src.main.python.plotlyst.view.widget.characters import CharactersScenesDistributionWidget
from src.main.python.plotlyst.view.widget.chart import ActDistributionChart
from src.main.python.plotlyst.view.widget.display import ChartView
from src.main.python.plotlyst.view.widget.input import RotatedButtonOrientation
from src.main.python.plotlyst.view.widget.novel import StoryStructureSelectorMenu
from src.main.python.plotlyst.view.widget.progress import SceneStageProgressCharts
from src.main.python.plotlyst.view.widget.scenes import SceneFilterWidget, SceneStoryStructureWidget, \
    ScenesPreferencesWidget, StoryMap, StoryMapDisplayMode
from src.main.python.plotlyst.view.widget.scenes import StoryLinesMapWidget
from src.main.python.plotlyst.view.widget.tree import TreeSettings


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

        self._chartDistribution = ActDistributionChart()
        self._chartDistributionView = ChartView()
        self._chartDistributionView.setFixedSize(356, 356)
        self._chartDistributionView.setChart(self._chartDistribution)

        menu = MenuWidget(self.btnCount)
        menu.addWidget(self._chartDistributionView)
        sp(self._chartDistributionView).h_exp().v_exp()
        self.refresh()

        dispatcher = event_dispatchers.instance(self.novel)
        dispatcher.register(self, SceneChangedEvent, SceneDeletedEvent, NovelSyncEvent)

    @overrides
    def event_received(self, event: Event):
        self.refresh()

    def refresh(self):
        self.btnCount.setText(f'#{len(self.novel.scenes)}')
        self.btnScene.setText(f'{len([x for x in self.novel.scenes if x.purpose == ScenePurposeType.Story])}')
        self.btnSequel.setText(f'{len([x for x in self.novel.scenes if x.purpose == ScenePurposeType.Reaction])}')

        self._chartDistribution.refresh(self.novel)


class ScenesOutlineView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel,
                         [NovelStoryStructureUpdated, CharacterChangedEvent, SceneChangedEvent, ChapterChangedEvent,
                          SceneDeletedEvent,
                          SceneOrderChangedEvent, NovelAboutToSyncEvent, NovelStorylinesToggleEvent,
                          NovelStructureToggleEvent])
        self.ui = Ui_ScenesView()
        self.ui.setupUi(self.widget)

        self.title = ScenesTitle(self.novel)
        self.ui.wdgTitleParent.layout().addWidget(self.title)

        self.editor: Optional[SceneEditor] = None
        self.editor = SceneEditor(self.novel)
        self.editor.close.connect(self._on_close_editor)
        self.ui.pageEditor.layout().addWidget(self.editor.widget)

        self.storymap_view: Optional[StoryLinesMapWidget] = None
        self.stagesModel: Optional[ScenesStageTableModel] = None
        self.stagesProgress: Optional[SceneStageProgressCharts] = None
        self.characters_distribution: Optional[CharactersScenesDistributionWidget] = None

        self.tblModel = ScenesTableModel(novel)
        self.tblModel.setDragEnabled(not self.novel.is_readonly())
        self._default_columns = [ScenesTableModel.ColTitle, ScenesTableModel.ColPov, ScenesTableModel.ColType,
                                 ScenesTableModel.ColCharacters,
                                 ScenesTableModel.ColSynopsis]
        self._proxy = ScenesFilterProxyModel()
        self._proxy.setSourceModel(self.tblModel)
        self._proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.ui.tblScenes.setModel(self._proxy)
        self.ui.tblScenes.horizontalHeader().setFixedHeight(30)
        self.ui.tblScenes.horizontalHeader().setProperty('main-header', True)
        self.ui.tblScenes.verticalHeader().setFixedWidth(40)
        self.ui.tblScenes.verticalHeader().setVisible(True)
        self.tblModel.orderChanged.connect(self._on_scene_moved)
        self.ui.tblScenes.setColumnWidth(ScenesTableModel.ColTitle, 250)
        self.ui.tblScenes.setColumnWidth(ScenesTableModel.ColCharacters, 170)
        self.ui.tblScenes.setColumnWidth(ScenesTableModel.ColType, 55)
        self.ui.tblScenes.setColumnWidth(ScenesTableModel.ColPov, 60)
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
        self.ui.btnNewWithMenu.setVisible(self.ui.btnChaptersToggle.isChecked())
        self.ui.btnChaptersToggle.setIcon(IconRegistry.chapter_icon())
        self.ui.btnChaptersToggle.setChecked(self.novel.prefs.panels.scene_chapters_sidebar_toggled)
        self.ui.btnChaptersToggle.clicked.connect(self._hide_chapters_clicked)
        self.ui.wgtChapters.setVisible(self.ui.btnChaptersToggle.isChecked())

        self.ui.btnAct1.setIcon(IconRegistry.act_one_icon(color='grey'))
        self.ui.btnAct2.setIcon(IconRegistry.act_two_icon(color='grey'))
        self.ui.btnAct3.setIcon(IconRegistry.act_three_icon(color='grey'))
        self.ui.btnAct1.toggled.connect(partial(self._proxy.setActsFilter, 1))
        self.ui.btnAct2.toggled.connect(partial(self._proxy.setActsFilter, 2))
        self.ui.btnAct3.toggled.connect(partial(self._proxy.setActsFilter, 3))

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
        self.setNavigableButtonGroup(self.ui.btnGroupViews)

        self.ui.btnStorymap.setVisible(self.novel.prefs.toggled(NovelSetting.Storylines))
        structure_visible = self.novel.prefs.toggled(NovelSetting.Structure)
        self.ui.btnStoryStructure.setVisible(structure_visible)
        self.ui.wdgStoryStructure.setVisible(structure_visible)

        self.ui.rbDots.setIcon(IconRegistry.from_name('fa5s.circle'))
        self.ui.rbTitles.setIcon(IconRegistry.from_name('ei.text-width'))
        self.ui.rbDetailed.setIcon(IconRegistry.from_name('mdi.card-text-outline'))
        self.ui.wdgOrientation.setHidden(True)
        self.ui.rbHorizontal.setIcon(IconRegistry.from_name('fa5s.grip-lines'))
        self.ui.rbVertical.setIcon(IconRegistry.from_name('fa5s.grip-lines-vertical'))

        self.ui.btnStageCustomize.setIcon(IconRegistry.cog_icon())
        transparent(self.ui.btnStageCustomize)
        self.ui.btnStageCustomize.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnStageCustomize))
        self.ui.btnStageCustomize.installEventFilter(OpacityEventFilter(self.ui.btnStageCustomize, enterOpacity=0.7))
        self.ui.btnStageCustomize.clicked.connect(self._customize_stages)

        self.selected_card: Optional[SceneCard] = None
        self._card_filter = SceneCardFilter()
        self.ui.btnAct1.toggled.connect(self._filter_cards)
        self.ui.btnAct2.toggled.connect(self._filter_cards)
        self.ui.btnAct3.toggled.connect(self._filter_cards)
        self.ui.btnStoryStructure.toggled.connect(self._story_structure_toggled)
        self.ui.cards.selectionCleared.connect(self._selection_cleared)
        self.ui.cards.cardSelected.connect(self._card_selected)
        self.ui.cards.cardDoubleClicked.connect(self._on_edit)
        self.ui.cards.cardEntered.connect(lambda x: self.ui.wdgStoryStructure.highlightScene(x.scene))
        self.ui.cards.cardCustomContextMenuRequested.connect(self._show_card_menu)

        self.ui.btnGroupViews.buttonToggled.connect(self._switch_view)
        self.ui.btnCardsView.setChecked(True)

        self.ui.wdgStoryStructureParent.setHidden(True)
        self.ui.wdgStoryStructure.setBeatCursor(Qt.CursorShape.ArrowCursor)
        self.ui.wdgStoryStructure.setStructure(self.novel)
        self.ui.wdgStoryStructure.setActsClickable(False)

        self.ui.btnFilter.setIcon(IconRegistry.filter_icon())
        self.ui.btnPreferences.setIcon(IconRegistry.preferences_icon())
        self.prefs_widget = ScenesPreferencesWidget()
        self.prefs_widget.sliderCards.valueChanged.connect(self.ui.cards.setCardsWidth)
        self.ui.cards.setCardsWidth(self.prefs_widget.sliderCards.value())
        menu = MenuWidget(self.ui.btnPreferences)
        menu.addWidget(self.prefs_widget)

        self._scene_filter = SceneFilterWidget(self.novel)
        filterMenu = MenuWidget(self.ui.btnFilter)
        filterMenu.addWidget(self._scene_filter)
        self._scene_filter.povFilter.characterToggled.connect(self._proxy.setCharacterFilter)
        self._scene_filter.povFilter.characterToggled.connect(self._filter_cards)

        self.ui.btnAct1.clicked.connect(self._scene_filter.btnAct1.setChecked)
        self.ui.btnAct2.clicked.connect(self._scene_filter.btnAct2.setChecked)
        self.ui.btnAct3.clicked.connect(self._scene_filter.btnAct3.setChecked)

        self._scene_filter.btnAct1.clicked.connect(self.ui.btnAct1.setChecked)
        self._scene_filter.btnAct2.clicked.connect(self.ui.btnAct2.setChecked)
        self._scene_filter.btnAct3.clicked.connect(self.ui.btnAct3.setChecked)

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
                btn.setToolTip('Option disabled in Scrivener synchronization mode')
                btn.installEventFilter(InstantTooltipEventFilter(btn))

        self.ui.cards.orderChanged.connect(self._on_scene_cards_swapped)
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageView)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, (CharacterChangedEvent, CharacterDeletedEvent)):
            self._scene_filter.povFilter.updateCharacters(self.novel.pov_characters(), checkAll=True)
        elif isinstance(event, NovelStoryStructureUpdated):
            if self.ui.btnStoryStructure.isChecked():
                self.ui.btnStoryStructureSelector.setVisible(len(self.novel.story_structures) > 1)
        elif isinstance(event, NovelPanelCustomizationEvent):
            if isinstance(event, NovelStorylinesToggleEvent):
                self.ui.btnStorymap.setVisible(event.toggled)
                if self.ui.btnStorymap.isChecked():
                    self.ui.btnCardsView.setChecked(True)
            elif isinstance(event, NovelStructureToggleEvent):
                self.ui.btnStoryStructure.setVisible(event.toggled)
                self.ui.wdgStoryStructure.setVisible(event.toggled)
            return

        super(ScenesOutlineView, self).event_received(event)

    @overrides
    def refresh(self):
        self.tblModel.modelReset.emit()
        self.ui.treeChapters.refresh()
        self.ui.btnEdit.setDisabled(True)
        self.ui.btnDelete.setDisabled(True)

        if self.ui.wdgStoryStructure.novel is not None:
            clear_layout(self.ui.wdgStoryStructureParent)
            self.ui.wdgStoryStructure = SceneStoryStructureWidget(self.ui.wdgStoryStructureParent)
            self.ui.wdgStoryStructure.setBeatCursor(Qt.CursorShape.ArrowCursor)
            self.ui.wdgStoryStructureParent.layout().addWidget(self.ui.wdgStoryStructure)
        self.ui.wdgStoryStructure.setStructure(self.novel)
        self.ui.wdgStoryStructure.setActsClickable(False)

        if self.stagesModel:
            self.stagesModel.modelReset.emit()
        if self.stagesProgress:
            self.stagesProgress.refresh()
        if self.characters_distribution:
            self.characters_distribution.refresh()

        self._init_cards()

    def _switch_view(self):
        height = 50
        relax_colors = False
        columns = self._default_columns

        if self.ui.btnStatusView.isChecked():
            self.ui.stackScenes.setCurrentWidget(self.ui.pageStages)
            self.ui.tblScenes.clearSelection()
            if not self.stagesModel:
                self._init_stages_view()
        elif self.ui.btnCardsView.isChecked():
            self.ui.stackScenes.setCurrentWidget(self.ui.pageCards)
            self.ui.tblScenes.clearSelection()
        elif self.ui.btnStorymap.isChecked():
            self.ui.stackScenes.setCurrentWidget(self.ui.pageStorymap)
            self.ui.tblScenes.clearSelection()
            self.ui.tblSceneStages.clearSelection()
            if not self.storymap_view:
                self.storymap_view = StoryMap()
                self.ui.scrollAreaStoryMap.layout().addWidget(self.storymap_view)
                self.ui.rbDots.clicked.connect(lambda: self.storymap_view.setMode(StoryMapDisplayMode.DOTS))
                self.ui.rbTitles.clicked.connect(lambda: self.storymap_view.setMode(StoryMapDisplayMode.TITLE))
                self.ui.rbDetailed.clicked.connect(lambda: self.storymap_view.setMode(StoryMapDisplayMode.DETAILED))
                self.ui.rbHorizontal.clicked.connect(
                    lambda: self.storymap_view.setOrientation(Qt.Orientation.Horizontal))
                self.ui.rbVertical.clicked.connect(lambda: self.storymap_view.setOrientation(Qt.Orientation.Vertical))
                self.ui.btnAct1.toggled.connect(partial(self.storymap_view.setActsFilter, 1))
                self.ui.btnAct2.toggled.connect(partial(self.storymap_view.setActsFilter, 2))
                self.ui.btnAct3.toggled.connect(partial(self.storymap_view.setActsFilter, 3))
                self.storymap_view.setActsFilter(1, self.ui.btnAct1.isChecked())
                self.storymap_view.setActsFilter(2, self.ui.btnAct2.isChecked())
                self.storymap_view.setActsFilter(3, self.ui.btnAct3.isChecked())
                self.storymap_view.sceneSelected.connect(self.ui.wdgStoryStructure.highlightScene)
                self.storymap_view.setNovel(self.novel)
        elif self.ui.btnCharactersDistributionView.isChecked():
            self.ui.stackScenes.setCurrentWidget(self.ui.pageCharactersDistribution)
            self.ui.tblScenes.clearSelection()
            self.ui.tblSceneStages.clearSelection()
            if not self.characters_distribution:
                self.characters_distribution = CharactersScenesDistributionWidget(self.novel)
                self.ui.pageCharactersDistribution.layout().addWidget(self.characters_distribution)
                self.ui.btnAct1.toggled.connect(partial(self.characters_distribution.setActsFilter, 1))
                self.ui.btnAct2.toggled.connect(partial(self.characters_distribution.setActsFilter, 2))
                self.ui.btnAct3.toggled.connect(partial(self.characters_distribution.setActsFilter, 3))
                self.characters_distribution.setActsFilter(1, self.ui.btnAct1.isChecked())
                self.characters_distribution.setActsFilter(2, self.ui.btnAct2.isChecked())
                self.characters_distribution.setActsFilter(3, self.ui.btnAct3.isChecked())
        else:
            self.ui.stackScenes.setCurrentWidget(self.ui.pageDefault)
            self.ui.tblSceneStages.clearSelection()

        self.tblModel.setRelaxColors(relax_colors)
        for col in range(self.tblModel.columnCount()):
            if col in columns:
                self.ui.tblScenes.showColumn(col)
                continue
            self.ui.tblScenes.hideColumn(col)
        self.ui.tblScenes.verticalHeader().setDefaultSectionSize(height)

        emit_event(self.novel, SceneSelectionClearedEvent(self))

    def _on_scene_selected(self):
        indexes = self.ui.tblScenes.selectedIndexes()
        selection = len(indexes) > 0
        if not self.novel.is_readonly():
            self.ui.btnDelete.setEnabled(selection)
        self.ui.btnEdit.setEnabled(selection)
        if selection:
            self.ui.treeChapters.clearSelection()
            emit_event(self.novel, SceneSelectedEvent(self, indexes[0].data(ScenesTableModel.SceneRole)))

    def _on_chapter_selected(self, chapter: Chapter):
        self.ui.tblScenes.clearSelection()
        if self.selected_card:
            self.selected_card.clearSelection()
            self.selected_card = None

        self.ui.btnDelete.setEnabled(False)
        self.ui.btnEdit.setEnabled(False)

    def _hide_chapters_clicked(self, toggled: bool):
        qtanim.toggle_expansion(self.ui.wgtChapters, toggled)
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
        self.editor.set_scene(scene)

    @busy
    def _on_close_editor(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageView)
        self.title.setVisible(True)
        self._scene_filter.povFilter.updateCharacters(self.novel.pov_characters(), checkAll=True)

        emit_event(self.novel, SceneChangedEvent(self, self.editor.scene))
        self.refresh()

    @busy
    def _new_scene(self, _):
        scene = self.novel.new_scene()
        self.novel.scenes.append(scene)
        self.repo.insert_scene(self.novel, scene)
        self._switch_to_editor(scene)

    def _show_card_menu(self, card: SceneCard, _: QPoint):
        menu = MenuWidget(card)
        menu.addAction(action('Edit', IconRegistry.edit_icon(), self._on_edit))
        action_ = action('Insert new scene', IconRegistry.plus_icon('black'),
                         partial(self._insert_scene_after, card.scene))
        action_.setDisabled(self.novel.is_readonly())
        menu.addAction(action_)
        menu.addSeparator()
        action_ = action('Delete', IconRegistry.trash_can_icon(), self.ui.btnDelete.click)
        action_.setDisabled(self.novel.is_readonly())
        menu.addAction(action_)
        menu.exec()

    def _init_cards(self):
        self.selected_card = None
        bar_value = self.ui.scrollArea.verticalScrollBar().value()
        self.ui.cards.clear()

        for scene in self.novel.scenes:
            card = SceneCard(scene, self.novel, self.ui.cards)
            card.setDragEnabled(not self.novel.is_readonly())
            self.ui.cards.addCard(card)

        # restore scrollbar that might have moved
        if bar_value <= self.ui.scrollArea.verticalScrollBar().maximum():
            self.ui.scrollArea.verticalScrollBar().setValue(bar_value)

        self._filter_cards()

    def _filter_cards(self):
        self._card_filter.setActsFilter(
            {1: self.ui.btnAct1.isChecked(), 2: self.ui.btnAct2.isChecked(), 3: self.ui.btnAct3.isChecked()})
        self._card_filter.setActivePovs(self._scene_filter.povFilter.characters(all=False))
        self.ui.cards.applyFilter(self._card_filter)

    def _story_structure_toggled(self, toggled: bool):
        self.ui.wdgStoryStructureParent.setVisible(toggled)
        if toggled:
            self.ui.btnStoryStructureSelector.setVisible(len(self.novel.story_structures) > 1)
        else:
            self.ui.btnStoryStructureSelector.setHidden(True)

    @busy
    def _active_story_structure_changed(self, structure: StoryStructure):
        emit_event(self.novel, NovelStoryStructureActivationRequest(self, self.novel, structure))

    def _card_selected(self, card: SceneCard):
        if self.selected_card and self.selected_card is not card:
            self.selected_card.clearSelection()
        self.selected_card = card
        self._enable_action_buttons(True)
        self.ui.treeChapters.selectScene(card.scene)
        emit_event(self.novel, SceneSelectedEvent(self, card.scene))

    def _selection_cleared(self):
        self._enable_action_buttons(False)
        self.ui.treeChapters.clearSelection()

    def _enable_action_buttons(self, enabled: bool):
        if not self.novel.is_readonly():
            self.ui.btnDelete.setEnabled(enabled)
        self.ui.btnEdit.setEnabled(enabled)

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
            emit_event(self.novel, ActiveSceneStageChanged(self, stage))

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
            self.ui.btnAct1.toggled.connect(partial(self._stages_proxy.setActsFilter, 1))
            self.ui.btnAct2.toggled.connect(partial(self._stages_proxy.setActsFilter, 2))
            self.ui.btnAct3.toggled.connect(partial(self._stages_proxy.setActsFilter, 3))
            self._stages_proxy.setActsFilter(1, self.ui.btnAct1.isChecked())
            self._stages_proxy.setActsFilter(2, self.ui.btnAct2.isChecked())
            self._stages_proxy.setActsFilter(3, self.ui.btnAct3.isChecked())
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
            if not self.ui.wdgProgressCharts.layout().count():
                for i, chartview in enumerate(self.stagesProgress.charts()):
                    self.ui.wdgProgressCharts.layout().insertWidget(i, chartview)

    def _on_custom_menu_requested(self, pos: QPoint):
        def toggle_wip(scene: Scene):
            scene.wip = not scene.wip
            self.repo.update_scene(scene)
            self.refresh()

        index: QModelIndex = self.ui.tblScenes.indexAt(pos)
        scene: Scene = index.data(ScenesTableModel.SceneRole)

        builder = PopupMenuBuilder.from_widget_position(self.ui.tblScenes, pos)
        builder.add_action('Toggle WIP status', IconRegistry.wip_icon(), lambda: toggle_wip(scene))
        action_ = builder.add_action('Insert new scene', IconRegistry.plus_icon(),
                                     lambda: self._insert_scene_after(index.data(ScenesTableModel.SceneRole)))
        action_.setDisabled(self.novel.is_readonly())
        builder.add_separator()
        action_ = builder.add_action('Delete', IconRegistry.trash_can_icon(), self.ui.btnDelete.click)
        action_.setDisabled(self.novel.is_readonly())

        builder.popup()

    def _insert_scene_after(self, scene: Scene, chapter: Optional[Chapter] = None):
        new_scene = self.novel.insert_scene_after(scene, chapter)
        self.repo.insert_scene(self.novel, new_scene)
        emit_event(self.novel, SceneChangedEvent(self, new_scene))

        self.refresh()
        self._switch_to_editor(new_scene)

    def _on_delete(self):
        scene: Optional[Scene] = self._selected_scene()
        if scene and delete_scene(self.novel, scene):
            emit_event(self.novel, SceneDeletedEvent(self, scene))
            self.refresh()

        # elif not scene:
        #     chapters = self.ui.treeChapters.selectedChapters()
        #     title = chapters[0].title_index(self.novel)
        #     if chapters:
        #         if ask_confirmation(
        #                 f'Are you sure you want to delete chapter "{title}"? (scenes will remain)'):
        #             self.chaptersModel.removeChapter(index)
        #             emit_event(ChapterChangedEvent(self))

    def _on_scene_cards_swapped(self, scenes: List[Scene]):
        self.novel.scenes[:] = scenes

        self.tblModel.modelReset.emit()

        if self.stagesModel:
            self.stagesModel.modelReset.emit()
        if self.stagesProgress:
            self.stagesProgress.refresh()
        if self.characters_distribution:
            self.characters_distribution.refresh()

        self.repo.update_novel(self.novel)

        emit_event(self.novel, SceneOrderChangedEvent(self))

    def _on_scene_moved(self):
        self.repo.update_novel(self.novel)
        self.refresh()
