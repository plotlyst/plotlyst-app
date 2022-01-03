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
from typing import Optional, List

import qtawesome
from PyQt6.QtCore import pyqtSignal, Qt, QModelIndex, \
    QPoint
from PyQt6.QtWidgets import QWidget, QHeaderView, QMenu, QWidgetAction
from overrides import overrides

from src.main.python.plotlyst.core.domain import Scene, Novel, Chapter, SceneStage
from src.main.python.plotlyst.event.core import emit_event
from src.main.python.plotlyst.events import SceneChangedEvent, SceneDeletedEvent, NovelStoryStructureUpdated, \
    SceneSelectedEvent, SceneSelectionClearedEvent
from src.main.python.plotlyst.model.chapters_model import ChaptersTreeModel, SceneNode, ChapterNode
from src.main.python.plotlyst.model.common import SelectionItemsModel
from src.main.python.plotlyst.model.novel import NovelStagesModel
from src.main.python.plotlyst.model.scenes_model import ScenesTableModel, ScenesFilterProxyModel, ScenesStageTableModel
from src.main.python.plotlyst.view._view import AbstractNovelView
from src.main.python.plotlyst.view.common import EditorCommand, ask_confirmation, EditorCommandType, PopupMenuBuilder, \
    action
from src.main.python.plotlyst.view.delegates import ScenesViewDelegate
from src.main.python.plotlyst.view.dialog.items import ItemsEditorDialog
from src.main.python.plotlyst.view.generated.scenes_view_ui import Ui_ScenesView
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.scene_editor import SceneEditor
from src.main.python.plotlyst.view.timeline_view import TimelineView
from src.main.python.plotlyst.view.widget.cards import SceneCard
from src.main.python.plotlyst.view.widget.characters import CharactersScenesDistributionWidget
from src.main.python.plotlyst.view.widget.input import RotatedButtonOrientation
from src.main.python.plotlyst.view.widget.progress import SceneStageProgressCharts
from src.main.python.plotlyst.view.widget.scenes import SceneFilterWidget
from src.main.python.plotlyst.worker.cache import acts_registry


class ScenesOutlineView(AbstractNovelView):
    commands_sent = pyqtSignal(QWidget, list)

    def __init__(self, novel: Novel):
        super().__init__(novel, [NovelStoryStructureUpdated])
        self.ui = Ui_ScenesView()
        self.ui.setupUi(self.widget)

        self.editor: Optional[SceneEditor] = None
        self.timeline_view: Optional[TimelineView] = None
        self.stagesModel: Optional[ScenesStageTableModel] = None
        self.stagesProgress: Optional[SceneStageProgressCharts] = None
        self.characters_distribution: Optional[CharactersScenesDistributionWidget] = None

        self.tblModel = ScenesTableModel(novel)
        self._default_columns = [ScenesTableModel.ColTitle, ScenesTableModel.ColPov, ScenesTableModel.ColType,
                                 ScenesTableModel.ColCharacters,
                                 ScenesTableModel.ColSynopsis]
        self._actions_view_columns = [ScenesTableModel.ColPov, ScenesTableModel.ColTitle,
                                      ScenesTableModel.ColBeginning,
                                      ScenesTableModel.ColMiddle, ScenesTableModel.ColEnd]
        self._proxy = ScenesFilterProxyModel()
        self._proxy.setSourceModel(self.tblModel)
        self._proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.ui.tblScenes.setModel(self._proxy)
        self.ui.tblScenes.horizontalHeader().setSectionResizeMode(ScenesTableModel.ColTitle, QHeaderView.Fixed)
        self.ui.tblScenes.horizontalHeader().setFixedHeight(30)
        self.ui.tblScenes.verticalHeader().setStyleSheet(
            '''QHeaderView::section {background-color: white; border: 0px; color: black; font-size: 14px;}
               QHeaderView {background-color: white;}''')
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

        self.ui.splitterLeft.setSizes([100, 500])

        self.chaptersModel = ChaptersTreeModel(self.novel)
        self.ui.treeChapters.setModel(self.chaptersModel)
        self.ui.treeChapters.expandAll()
        self.chaptersModel.orderChanged.connect(self._on_scene_moved)
        self.chaptersModel.modelReset.connect(self.ui.treeChapters.expandAll)
        self.ui.treeChapters.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ui.treeChapters.setColumnWidth(ChaptersTreeModel.ColPlus, 24)
        self.ui.treeChapters.selectionModel().selectionChanged.connect(self._on_chapter_selected)
        self.ui.treeChapters.clicked.connect(self._on_chapter_clicked)
        self.ui.treeChapters.doubleClicked.connect(self._on_edit)
        self.ui.btnChaptersToggle.toggled.connect(self._hide_chapters_toggled)
        self._hide_chapters_toggled(self.ui.btnChaptersToggle.isChecked())

        self.ui.btnAct1.setIcon(IconRegistry.act_one_icon())
        self.ui.btnAct2.setIcon(IconRegistry.act_two_icon())
        self.ui.btnAct3.setIcon(IconRegistry.act_three_icon())
        self.ui.btnAct1.toggled.connect(partial(self._proxy.setActsFilter, 1))
        self.ui.btnAct2.toggled.connect(partial(self._proxy.setActsFilter, 2))
        self.ui.btnAct3.toggled.connect(partial(self._proxy.setActsFilter, 3))

        self.ui.btnCardsView.setIcon(IconRegistry.cards_icon())
        self.ui.btnTableView.setIcon(IconRegistry.table_icon())
        self.ui.btnActionsView.setIcon(IconRegistry.action_scene_icon())
        self.ui.btnStatusView.setIcon(IconRegistry.progress_check_icon())
        self.ui.btnCharactersDistributionView.setIcon(qtawesome.icon('fa5s.chess-board'))
        self.ui.btnTimelineView.setIcon(IconRegistry.timeline_icon())

        self.ui.btnStageCustomize.setIcon(IconRegistry.cog_icon())
        self.ui.btnStageCustomize.clicked.connect(self._customize_stages)

        self.scene_cards: List[SceneCard] = []
        self.selected_card: Optional[SceneCard] = None
        self.ui.btnAct1.toggled.connect(self._update_cards)
        self.ui.btnAct2.toggled.connect(self._update_cards)
        self.ui.btnAct3.toggled.connect(self._update_cards)

        self.ui.btnGroupViews.buttonToggled.connect(self._switch_view)
        self.ui.btnCardsView.setChecked(True)

        self.ui.btnFilter.setIcon(IconRegistry.filter_icon())
        action = QWidgetAction(self.ui.btnFilter)
        self._scene_filter = SceneFilterWidget(self.novel)
        action.setDefaultWidget(self._scene_filter)
        self.ui.btnFilter.addAction(action)
        self._scene_filter.povFilter.characterToggled.connect(self._proxy.setCharacterFilter)
        self._scene_filter.povFilter.characterToggled.connect(self._update_cards)

        self._update_cards()

        self.ui.tblScenes.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.tblScenes.customContextMenuRequested.connect(self._on_custom_menu_requested)

        self.ui.tblScenes.selectionModel().selectionChanged.connect(self._on_scene_selected)
        self.ui.tblScenes.doubleClicked.connect(self.ui.btnEdit.click)

        self.ui.btnEdit.setIcon(IconRegistry.edit_icon())
        self.ui.btnEdit.clicked.connect(self._on_edit)
        self.ui.btnNew.setIcon(IconRegistry.plus_icon(color='white'))
        self.ui.btnNew.clicked.connect(self._new_scene)
        self.ui.btnDelete.setIcon(IconRegistry.trash_can_icon(color='white'))
        self.ui.btnDelete.clicked.connect(self._on_delete)

        self.ui.cards.swapped.connect(self._scenes_swapped)

    @overrides
    def refresh(self):
        self.tblModel.modelReset.emit()
        self.chaptersModel.update()
        self.chaptersModel.modelReset.emit()
        self.ui.btnEdit.setDisabled(True)
        self.ui.btnDelete.setDisabled(True)

        if self.stagesModel:
            self.stagesModel.modelReset.emit()
        if self.stagesProgress:
            self.stagesProgress.refresh()
        if self.timeline_view:
            self.timeline_view.refresh()
        if self.characters_distribution:
            self.characters_distribution.refresh()

        self._update_cards()

    def _on_scene_selected(self):
        if self.ui.btnTimelineView.isChecked():
            indexes = self.timeline_view.ui.tblScenes.selectedIndexes()
        else:
            indexes = self.ui.tblScenes.selectedIndexes()
        selection = len(indexes) > 0
        self.ui.btnDelete.setEnabled(selection)
        self.ui.btnEdit.setEnabled(selection)
        if selection:
            self.ui.treeChapters.clearSelection()
            emit_event(
                SceneSelectedEvent(self, indexes[0].data(ScenesTableModel.SceneRole)))

    def _on_chapter_selected(self):
        indexes = self.ui.treeChapters.selectedIndexes()
        if not indexes:
            return

        self.ui.tblScenes.clearSelection()
        if self.selected_card:
            self.selected_card.clearSelection()
            self.selected_card = None

        self.ui.btnDelete.setEnabled(True)
        node = indexes[0].data(ChaptersTreeModel.NodeRole)
        self.ui.btnEdit.setEnabled(isinstance(node, SceneNode))

    def _on_chapter_clicked(self, index: QModelIndex):
        if index.column() == 0:
            return
        chapter = self._selected_chapter()
        if chapter:
            builder = PopupMenuBuilder.from_index(self.ui.treeChapters, index)
            builder.add_action('Add scene', IconRegistry.scene_icon())
            builder.add_action('Insert chapter after', IconRegistry.chapter_icon(),
                               lambda: self._new_chapter(self.novel.chapters.index(chapter) + 1))
            builder.popup()
        else:
            scene = self._selected_scene()
            if scene and scene.chapter:
                self._insert_scene_after(scene)

    def _hide_chapters_toggled(self, toggled: bool):
        self.ui.wgtChapters.setVisible(toggled)
        self.ui.btnChaptersToggle.setIcon(IconRegistry.eye_closed_icon() if toggled else IconRegistry.eye_open_icon())
        if toggled:
            menu = QMenu(self.ui.btnNew)
            menu.addAction(IconRegistry.scene_icon(), 'Add scene', self._new_scene)
            menu.addAction(IconRegistry.chapter_icon(), 'Add chapter', self._new_chapter)
            self.ui.btnNew.setMenu(menu)
        else:
            self.ui.btnNew.setMenu(None)

    def _on_edit(self):
        scene: Optional[Scene] = self._selected_scene()
        if scene:
            self.editor = SceneEditor(self.novel, scene)
            self._switch_to_editor()

    def _selected_scene(self) -> Optional[Scene]:
        if self.ui.btnCardsView.isChecked() and self.selected_card:
            return self.selected_card.scene
        elif self.ui.treeChapters.selectionModel().selectedIndexes():
            index = self.ui.treeChapters.selectionModel().selectedIndexes()[0]
            node = index.data(ChaptersTreeModel.NodeRole)
            if isinstance(node, SceneNode):
                return node.scene
            return None
        else:
            indexes = None
            if self.ui.btnTableView.isChecked() or self.ui.btnActionsView.isChecked():
                indexes = self.ui.tblScenes.selectedIndexes()
            elif self.ui.btnTimelineView.isChecked():
                indexes = self.timeline_view.ui.tblScenes.selectedIndexes()

            if indexes:
                return indexes[0].data(role=ScenesTableModel.SceneRole)
            else:
                return None

    def _selected_chapter(self) -> Optional[Chapter]:
        indexes = self.ui.treeChapters.selectionModel().selectedIndexes()
        if indexes:
            node = indexes[0].data(ChaptersTreeModel.NodeRole)
            if isinstance(node, ChapterNode):
                return node.chapter

    def _switch_to_editor(self):
        self.ui.pageEditor.layout().addWidget(self.editor.widget)
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageEditor)

        self.editor.ui.btnClose.clicked.connect(self._on_close_editor)

    def _on_close_editor(self):
        self.ui.pageEditor.layout().removeWidget(self.editor.widget)
        if self.editor.scene.pov and self.editor.scene.pov not in self._scene_filter.povFilter.characters():
            self._scene_filter.povFilter.addCharacter(self.editor.scene.pov)
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageView)
        self.editor.widget.deleteLater()
        self.editor = None

        emit_event(SceneChangedEvent(self))
        self.refresh()

    def _new_scene(self):
        self.editor = SceneEditor(self.novel)
        self._switch_to_editor()

    def _new_chapter(self, index: int = -1):
        self.chaptersModel.newChapter(index)
        self.repo.update_novel(self.novel)

    def _update_cards(self):
        self.scene_cards.clear()
        self.selected_card = None
        self.ui.cards.clear()

        acts_filter = {1: self.ui.btnAct1.isChecked(), 2: self.ui.btnAct2.isChecked(), 3: self.ui.btnAct3.isChecked()}
        active_povs = self._scene_filter.povFilter.characters(all=False)
        for scene in self.novel.scenes:
            if not acts_filter[acts_registry.act(scene)]:
                continue
            if scene.pov and scene.pov not in active_povs:
                continue
            card = SceneCard(scene)
            self.ui.cards.addCard(card)
            self.scene_cards.append(card)
            card.selected.connect(self._card_selected)
            card.doubleClicked.connect(self._on_edit)

            card.setPopupMenuActions(
                [action('Insert new scene', IconRegistry.plus_icon(), partial(self._insert_scene_after, scene)),
                 action('Delete', IconRegistry.trash_can_icon(), self.ui.btnDelete.click)])

    def _card_selected(self, card: SceneCard):
        if self.selected_card and self.selected_card is not card:
            self.selected_card.clearSelection()
        self.selected_card = card
        self.ui.btnDelete.setEnabled(True)
        self.ui.btnEdit.setEnabled(True)
        emit_event(SceneSelectedEvent(self, card.scene))

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
        elif self.ui.btnTimelineView.isChecked():
            self.ui.stackScenes.setCurrentWidget(self.ui.pageTimeline)
            self.ui.tblScenes.clearSelection()
            self.ui.tblSceneStages.clearSelection()
            if not self.timeline_view:
                self.timeline_view = TimelineView(self.novel)
                self.ui.pageTimeline.layout().addWidget(self.timeline_view.widget)
                self.timeline_view.ui.tblScenes.selectionModel().selectionChanged.connect(self._on_scene_selected)
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

        if self.ui.btnActionsView.isChecked():
            columns = self._actions_view_columns
            height = 60
            relax_colors = True
            self.ui.tblScenes.horizontalHeader().setSectionResizeMode(ScenesTableModel.ColBeginning,
                                                                      QHeaderView.ResizeMode.Stretch)
            self.ui.tblScenes.horizontalHeader().setSectionResizeMode(ScenesTableModel.ColMiddle,
                                                                      QHeaderView.ResizeMode.Stretch)
        self.tblModel.setRelaxColors(relax_colors)
        for col in range(self.tblModel.columnCount()):
            if col in columns:
                self.ui.tblScenes.showColumn(col)
                continue
            self.ui.tblScenes.hideColumn(col)
        self.ui.tblScenes.verticalHeader().setDefaultSectionSize(height)

        emit_event(SceneSelectionClearedEvent(self))

    def _customize_stages(self):
        diag = ItemsEditorDialog(NovelStagesModel(copy.deepcopy(self.novel.stages)))
        diag.wdgItemsEditor.tableView.setColumnHidden(SelectionItemsModel.ColIcon, True)
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

    def _init_stages_view(self):
        def change_stage(stage: SceneStage):
            self.stagesProgress.setStage(stage)
            self.ui.btnStageSelector.setText(stage.text)
            self.stagesModel.setHighlightedStage(stage)

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
            self.ui.tblSceneStages.verticalHeader().setStyleSheet(
                '''QHeaderView::section {background-color: white; border: 0px; color: black; font-size: 14px;}
                   QHeaderView {background-color: white;}''')
            self.ui.tblSceneStages.verticalHeader().setFixedWidth(40)
            self.ui.tblSceneStages.setColumnWidth(ScenesStageTableModel.ColTitle, 250)

        for col in range(1, self.stagesModel.columnCount()):
            self.ui.tblSceneStages.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
            w = self.ui.tblSceneStages.horizontalHeader().sectionSize(col)
            self.ui.tblSceneStages.horizontalHeader().setSectionResizeMode(col, QHeaderView.Interactive)
            self.ui.tblSceneStages.setColumnWidth(col, w + 10)

        if not self.stagesProgress:
            self.stagesProgress = SceneStageProgressCharts(self.novel)

            self.ui.tblSceneStages.clicked.connect(
                lambda x: self.stagesModel.changeStage(self._stages_proxy.mapToSource(x)))
            self.ui.tblSceneStages.clicked.connect(self.stagesProgress.refresh)

            self.ui.btnStageSelector.setOrientation(RotatedButtonOrientation.VerticalBottomToTop)
            self.ui.btnStageSelector.setIcon(IconRegistry.progress_check_icon())

        menu = QMenu(self.ui.btnStageSelector)
        for stage in self.novel.stages:
            menu.addAction(stage.text, partial(change_stage, stage))
        self.ui.btnStageSelector.setMenu(menu)
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

        menu = QMenu(self.ui.tblScenes)
        menu.addAction(IconRegistry.wip_icon(), 'Toggle WIP status', lambda: toggle_wip(scene))
        menu.addAction(IconRegistry.plus_icon(), 'Insert new scene',
                       lambda: self._insert_scene_after(index.data(ScenesTableModel.SceneRole)))
        menu.addSeparator()
        menu.addAction(IconRegistry.trash_can_icon(), 'Delete', self.ui.btnDelete.click)

        menu.popup(self.ui.tblScenes.viewport().mapToGlobal(pos))

    def _insert_scene_after(self, scene: Scene, inherit_chapter: bool = True):
        i = self.novel.scenes.index(scene)
        day = scene.day

        new_scene = Scene('Untitled', day=day)
        if inherit_chapter:
            new_scene.chapter = scene.chapter
        self.novel.scenes.insert(i + 1, new_scene)
        new_scene.sequence = i + 1
        self.repo.insert_scene(self.novel, new_scene)
        emit_event(SceneChangedEvent(self))
        self.refresh()
        self.commands_sent.emit(self.widget, [EditorCommand(EditorCommandType.UPDATE_SCENE_SEQUENCES)])

        self.editor = SceneEditor(self.novel, new_scene)
        self._switch_to_editor()

    def _on_delete(self):
        scene: Optional[Scene] = self._selected_scene()
        if scene and ask_confirmation(f'Are you sure you want to delete scene {scene.title}?'):
            self.novel.scenes.remove(scene)
            self.repo.delete_scene(self.novel, scene)
            self.refresh()
            self.commands_sent.emit(self.widget, [EditorCommand(EditorCommandType.UPDATE_SCENE_SEQUENCES)])
            emit_event(SceneDeletedEvent(self))
        elif not scene:
            chapter = self._selected_chapter()
            if not chapter:
                return
            index = self.ui.treeChapters.selectionModel().selectedIndexes()[0]
            if ask_confirmation(f'Are you sure you want to delete "{index.data()}"? (scenes will remain)'):
                self.chaptersModel.removeChapter(index)

    def _scenes_swapped(self, removed: SceneCard, moved_to: SceneCard):
        self.novel.scenes.remove(removed.scene)
        pos = self.novel.scenes.index(moved_to.scene)
        self.novel.scenes.insert(pos, removed.scene)

        emit_event(SceneChangedEvent(self))
        self.refresh()
        self.repo.update_novel(self.novel)

    def _on_scene_moved(self):
        self.commands_sent.emit(self.widget, [EditorCommand(EditorCommandType.UPDATE_SCENE_SEQUENCES)])
        self.refresh()
