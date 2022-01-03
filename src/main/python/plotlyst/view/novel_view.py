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
from typing import List, Optional

import emoji
from PyQt6.QtCore import QPropertyAnimation
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout, QWidget, QHeaderView
from fbs_runtime import platform
from overrides import overrides

from src.main.python.plotlyst.core.client import json_client
from src.main.python.plotlyst.core.domain import Novel, SelectionItem, Plot
from src.main.python.plotlyst.event.core import emit_event
from src.main.python.plotlyst.events import NovelUpdatedEvent, \
    NovelStoryStructureUpdated, SceneChangedEvent
from src.main.python.plotlyst.model.common import SelectionItemsModel
from src.main.python.plotlyst.model.novel import NovelPlotsModel, NovelTagsModel, NovelConflictsModel
from src.main.python.plotlyst.view._view import AbstractNovelView
from src.main.python.plotlyst.view.common import ask_confirmation, emoji_font
from src.main.python.plotlyst.view.delegates import TextItemDelegate
from src.main.python.plotlyst.view.dialog.novel import PlotEditorDialog, PlotEditionResult
from src.main.python.plotlyst.view.generated.novel_view_ui import Ui_NovelView
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.widget.items_editor import ItemsEditorWidget
from src.main.python.plotlyst.view.widget.labels import LabelsEditorWidget


class NovelView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel, [NovelUpdatedEvent, SceneChangedEvent])
        self.ui = Ui_NovelView()
        self.ui.setupUi(self.widget)

        self.ui.lblTitle.setText(self.novel.title)

        self.ui.btnGoalIcon.setIcon(IconRegistry.goal_icon())
        self.ui.btnConflictIcon.setIcon(IconRegistry.conflict_icon())

        self._emoji_font = emoji_font(14) if platform.is_windows() else emoji_font(20)
        self.ui.lblStoryStructureEmoji.setFont(self._emoji_font)
        self.ui.lblStoryStructureEmoji.setText(emoji.emojize(':performing_arts:'))
        self.ui.lblDramaticQuestionEmoji.setFont(self._emoji_font)
        self.ui.lblDramaticQuestionEmoji.setText(emoji.emojize(':chart_increasing:'))
        for story_structure in json_client.project.story_structures:
            icon = IconRegistry.from_name(story_structure.icon,
                                          story_structure.icon_color) if story_structure.icon else QIcon('')
            self.ui.cbStoryStructure.addItem(icon, story_structure.title, story_structure)
        self.ui.cbStoryStructure.setCurrentText(self.novel.story_structure.title)
        self.ui.cbStoryStructure.currentIndexChanged.connect(self._story_structure_changed)

        self.ui.wdgStoryStructureInfo.setVisible(False)
        self._update_story_structure_info()

        self.story_lines_model = NovelPlotsModel(self.novel)
        self.ui.wdgDramaticQuestions.tableView.horizontalHeader().setStretchLastSection(False)
        self.ui.wdgDramaticQuestions.setModel(self.story_lines_model)
        self.ui.wdgDramaticQuestions.setInlineEditionEnabled(False)
        self.ui.wdgDramaticQuestions.editRequested.connect(self._edit_plot)

        self.ui.wdgDramaticQuestions.tableView.horizontalHeader().show()
        self.ui.wdgDramaticQuestions.tableView.setColumnWidth(NovelPlotsModel.ColName, 250)
        self.ui.wdgDramaticQuestions.tableView.setColumnWidth(NovelPlotsModel.ColPlotType, 100)
        self.ui.wdgDramaticQuestions.tableView.setColumnWidth(NovelPlotsModel.ColCharacter, 155)
        self.ui.wdgDramaticQuestions.tableView.setColumnWidth(NovelPlotsModel.ColValueType, 60)
        self.ui.wdgDramaticQuestions.setAskRemovalConfirmation(True)
        self.ui.wdgDramaticQuestions.setBgColorFieldEnabled(True)

        self.ui.btnEdit.setIcon(IconRegistry.edit_icon())
        self.ui.btnRemove.setIcon(IconRegistry.minus_icon())

        self.conflict_model = NovelConflictsModel(self.novel)
        self.ui.tblConflicts.setModel(self.conflict_model)
        self.ui.tblConflicts.horizontalHeader().setSectionResizeMode(NovelConflictsModel.ColPov,
                                                                     QHeaderView.ResizeToContents)
        self.ui.tblConflicts.horizontalHeader().setSectionResizeMode(NovelConflictsModel.ColType,
                                                                     QHeaderView.ResizeToContents)
        self.ui.tblConflicts.horizontalHeader().setSectionResizeMode(NovelConflictsModel.ColPhrase,
                                                                     QHeaderView.ResizeMode.Stretch)
        self.ui.tblConflicts.selectionModel().selectionChanged.connect(self._conflict_selected)
        self.ui.tblConflicts.setItemDelegateForColumn(NovelConflictsModel.ColPhrase, TextItemDelegate())
        self.ui.btnEdit.clicked.connect(self._edit_conflict)
        self.ui.btnRemove.clicked.connect(self._delete_conflict)

        self.ui.lblTagEmoji.setFont(self._emoji_font)
        self.ui.lblTagEmoji.setText(emoji.emojize(':label:'))
        tags_editor = NovelTagsEditor(self.novel)
        _layout = QHBoxLayout()
        _layout.setSpacing(0)
        _layout.setContentsMargins(0, 0, 0, 0)
        self.ui.wdgTagsContainer.setLayout(_layout)
        self.ui.wdgTagsContainer.layout().addWidget(tags_editor)

        self.ui.btnStoryStructureInfo.setText(u'\u00BB')
        self.ui.btnStoryStructureInfo.setIcon(IconRegistry.general_info_icon())
        self.ui.btnStoryStructureInfo.clicked.connect(self._story_structure_info_clicked)

    @overrides
    def refresh(self):
        self.ui.lblTitle.setText(self.novel.title)
        self.story_lines_model.modelReset.emit()
        self.ui.cbStoryStructure.setCurrentText(self.novel.story_structure.title)
        self.conflict_model.modelReset.emit()
        self._conflict_selected()

    def _update_story_structure_info(self):
        self.ui.textStoryStructureInfo.setText('''
        <h3>Info on Story structures</h3>
<p>By selecting a story structure, you will organize your scenes into <strong>Acts.</strong></p>
<p>An Act consists of <strong>Beats&nbsp;</strong>which represent your story's pivotal moments.
The scenes can be associated to such story beats.</p>''')

    def _story_structure_changed(self):
        structure = self.ui.cbStoryStructure.currentData()
        if self.novel.story_structure.id == structure.id:
            return
        beats = [x for x in self.novel.scenes if x.beat]
        if beats and not ask_confirmation(
                'Scenes are already associated to your previous story beats. Continue?'):
            self.ui.cbStoryStructure.setCurrentText(self.novel.story_structure.title)
            return
        for scene in beats:
            scene.beat = None
            self.repo.update_scene(scene)
        self.novel.story_structure = structure
        self.repo.update_novel(self.novel)
        emit_event(NovelStoryStructureUpdated(self))

    def _story_structure_info_clicked(self, checked: bool):
        if checked:
            self.ui.wdgStoryStructureInfo.setVisible(checked)
            self.animation = QPropertyAnimation(self.ui.wdgStoryStructureInfo, b'maximumHeight')
            self.animation.setStartValue(10)
            self.animation.setEndValue(200)
            self.animation.start()
        else:
            self.animation = QPropertyAnimation(self.ui.wdgStoryStructureInfo, b'maximumHeight')
            self.animation.setStartValue(200)
            self.animation.setEndValue(0)
            self.animation.start()

        self.ui.btnStoryStructureInfo.setText(u'\u02C7' if checked else u'\u00BB')

    def _edit_plot(self, plot: Plot):
        edited_plot: Optional[PlotEditionResult] = PlotEditorDialog(self.novel, plot).display()
        if edited_plot is None:
            return

        plot.text = edited_plot.text
        plot.plot_type = edited_plot.plot_type
        plot.set_character(edited_plot.character)

        self.story_lines_model.modelReset.emit()
        self.repo.update_novel(self.novel)

    def _conflict_selected(self):
        selection = bool(self.ui.tblConflicts.selectedIndexes())
        self.ui.btnEdit.setEnabled(selection)
        self.ui.btnRemove.setEnabled(selection)

    def _edit_conflict(self):
        indexes = self.ui.tblConflicts.selectedIndexes()
        if not indexes:
            return
        self.ui.tblConflicts.edit(self.conflict_model.index(indexes[0].row(), NovelConflictsModel.ColPhrase))

    def _delete_conflict(self):
        indexes = self.ui.tblConflicts.selectedIndexes()
        if not indexes:
            return

        conflict = indexes[0].data(NovelConflictsModel.ConflictRole)
        if ask_confirmation(f'Delete conflict "{conflict.text}"'):
            for scene in self.novel.scenes:
                if conflict in scene.conflicts:
                    scene.conflicts.remove(conflict)
                    self.repo.update_scene(scene)
            self.novel.conflicts.remove(conflict)
            self.repo.update_novel(self.novel)


class NovelTagsEditor(LabelsEditorWidget):

    def __init__(self, novel: Novel, parent=None):
        self.novel = novel
        super(NovelTagsEditor, self).__init__(checkable=False, parent=parent)
        self.btnEdit.setIcon(IconRegistry.tag_plus_icon())
        self.editor.model.item_edited.connect(self._updateTags)
        self._updateTags()

    @overrides
    def _initPopupWidget(self) -> QWidget:
        self.editor: ItemsEditorWidget = super(NovelTagsEditor, self)._initPopupWidget()
        self.editor.setBgColorFieldEnabled(True)
        return self.editor

    @overrides
    def _initModel(self) -> SelectionItemsModel:
        return NovelTagsModel(self.novel)

    @overrides
    def items(self) -> List[SelectionItem]:
        return self.novel.tags

    def _updateTags(self):
        self._wdgLabels.clear()
        self._addItems(self.novel.tags)
