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
from functools import partial
from typing import Optional, List

import emoji
from PyQt6.QtCore import QObject, pyqtSignal, QModelIndex, QItemSelectionModel, \
    QAbstractItemModel, Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QStyledItemDelegate, QStyleOptionViewItem, QTextEdit, QLineEdit, QComboBox, \
    QWidgetAction, QTableView
from fbs_runtime import platform
from overrides import overrides

from src.main.python.plotlyst.core.client import json_client
from src.main.python.plotlyst.core.domain import Novel, Scene, SceneBuilderElement, Document, ScenePlotValue, StoryBeat
from src.main.python.plotlyst.model.characters_model import CharactersSceneAssociationTableModel
from src.main.python.plotlyst.model.scene_builder_model import SceneBuilderInventoryTreeModel, \
    SceneBuilderPaletteTreeModel, CharacterEntryNode, SceneInventoryNode, convert_to_element_type
from src.main.python.plotlyst.model.scenes_model import ScenesTableModel
from src.main.python.plotlyst.view.common import emoji_font
from src.main.python.plotlyst.view.dialog.scene_builder_edition import SceneBuilderPreviewDialog
from src.main.python.plotlyst.view.generated.scene_editor_ui import Ui_SceneEditor
from src.main.python.plotlyst.view.icons import IconRegistry, avatars
from src.main.python.plotlyst.view.widget.input import RotatedButtonOrientation
from src.main.python.plotlyst.view.widget.labels import CharacterLabel
from src.main.python.plotlyst.view.widget.scenes import SceneDramaticQuestionsWidget, SceneTagsWidget
from src.main.python.plotlyst.worker.cache import acts_registry
from src.main.python.plotlyst.worker.persistence import RepositoryPersistenceManager


class SceneEditor(QObject):
    commands_sent = pyqtSignal(QWidget, list)

    def __init__(self, novel: Novel, scene: Optional[Scene] = None):
        super().__init__()
        self.widget = QWidget()
        self.ui = Ui_SceneEditor()
        self.ui.setupUi(self.widget)
        self.novel = novel
        self.scene: Optional[Scene] = None

        if platform.is_windows():
            self._emoji_font = emoji_font(14)
        else:
            self._emoji_font = emoji_font(20)

        self.ui.btnAttributes.setOrientation(RotatedButtonOrientation.VerticalBottomToTop)
        self.ui.btnNotes.setOrientation(RotatedButtonOrientation.VerticalBottomToTop)
        self.ui.btnNotes.setIcon(IconRegistry.document_edition_icon())
        self.ui.btnBuilder.setOrientation(RotatedButtonOrientation.VerticalBottomToTop)

        self.ui.btnEditCharacters.setIcon(IconRegistry.plus_edit_icon())

        self.ui.lblDayEmoji.setFont(self._emoji_font)
        self.ui.lblDayEmoji.setText(emoji.emojize(':spiral_calendar:'))
        self.ui.lblTitleEmoji.setFont(self._emoji_font)
        self.ui.lblTitleEmoji.setText(emoji.emojize(':clapper_board:'))
        self.ui.lblSynopsisEmoji.setFont(self._emoji_font)
        self.ui.lblSynopsisEmoji.setText(emoji.emojize(':scroll:'))

        self.ui.wdgStructure.setNovel(self.novel)
        self.ui.wdgStructure.setActsClickable(False)
        self.ui.wdgStructure.beatSelected.connect(self._beat_selected)
        self.ui.wdgStructure.beatRemovalRequested.connect(self._beat_removed)

        self.ui.cbPov.addItem('Select POV ...', None)
        self.ui.cbPov.addItem('', None)
        for char in self.novel.characters:
            self.ui.cbPov.addItem(QIcon(avatars.pixmap(char)), char.name, char)
        self.ui.cbPov.view().setRowHidden(0, True)

        self.ui.textNotes.setTitleVisible(False)

        self.tblCharacters = QTableView()
        self.tblCharacters.setShowGrid(False)
        self.tblCharacters.verticalHeader().setVisible(False)
        self.tblCharacters.horizontalHeader().setVisible(False)
        self.tblCharacters.horizontalHeader().setDefaultSectionSize(200)
        self.tblCharacters.setCursor(Qt.PointingHandCursor)

        self._characters_model = CharactersSceneAssociationTableModel(self.novel)
        self._characters_model.selection_changed.connect(self._character_changed)
        self.tblCharacters.setModel(self._characters_model)
        self.tblCharacters.clicked.connect(self._characters_model.toggleSelection)

        action = QWidgetAction(self.ui.btnEditCharacters)
        action.setDefaultWidget(self.tblCharacters)
        self.ui.btnEditCharacters.addAction(action)

        self.scenes_model = ScenesTableModel(self.novel)
        self.ui.lstScenes.setModel(self.scenes_model)
        self.ui.lstScenes.setModelColumn(ScenesTableModel.ColTitle)
        self.ui.lstScenes.clicked.connect(self._new_scene_selected)

        self.ui.btnClose.setIcon(IconRegistry.return_icon())
        self.ui.btnClose.clicked.connect(self._on_close)
        self.ui.btnPrevious.setIcon(IconRegistry.arrow_left_thick_icon())
        self.ui.btnPrevious.clicked.connect(self._on_previous_scene)
        self.ui.btnNext.setIcon(IconRegistry.arrow_right_thick_icon())
        self.ui.btnNext.clicked.connect(self._on_next_scene)

        self._scene_builder_inventory_model = SceneBuilderInventoryTreeModel()
        self.ui.treeInventory.setModel(self._scene_builder_inventory_model)
        self.ui.treeInventory.doubleClicked.connect(self._on_dclick_scene_builder_inventory)
        self.ui.treeInventory.expandAll()

        self.ui.btnDelete.setIcon(IconRegistry.minus_icon())
        self.ui.btnDelete.clicked.connect(self._on_delete_scene_builder_element)
        self.ui.btnEdit.setIcon(IconRegistry.edit_icon())
        self.ui.btnEdit.clicked.connect(self._on_edit_scene_builder_element)
        self.ui.btnPreview.clicked.connect(self._on_preview_scene_builder)

        self.questionsEditor = SceneDramaticQuestionsWidget(self.novel)
        self.ui.wdgDramaticQuestions.layout().addWidget(self.questionsEditor)

        self.tagsEditor = SceneTagsWidget(self.novel)
        self.tagsEditor.setMinimumHeight(50)
        self.ui.wdgTagsContainer.layout().addWidget(self.tagsEditor)

        self._save_enabled = False
        self._update_view(scene)

        self.ui.cbPov.currentIndexChanged.connect(self._on_pov_changed)
        self.ui.btnGroupPages.buttonToggled.connect(self._page_toggled)

        self.repo = RepositoryPersistenceManager.instance()
        self.ui.btnAttributes.setChecked(True)

    def _update_view(self, scene: Optional[Scene] = None):
        if scene:
            self.scene = scene
            self._new_scene = False
            index = self.scenes_model.index(self.scene.sequence, ScenesTableModel.ColTitle)
            self.ui.lstScenes.selectionModel().select(index, QItemSelectionModel.Select)
        else:
            self.scene = Scene('')
            if len(self.novel.scenes) > 1:
                self.scene.day = self.novel.scenes[-1].day
            self._new_scene = True

        if self.scene.pov:
            self.ui.cbPov.setCurrentText(self.scene.pov.name)
        else:
            self.ui.cbPov.setCurrentIndex(0)
        self._update_pov_avatar()
        self.ui.sbDay.setValue(self.scene.day)

        self.ui.wdgSceneStructure.setScene(self.novel, self.scene)

        self.ui.lineTitle.setText(self.scene.title)
        self.ui.textSynopsis.setText(self.scene.synopsis)

        self.ui.wdgStructure.unhighlightBeats()
        if self.scene.beat:
            self.ui.wdgStructure.highlightBeat(self.scene.beat)
        self.ui.wdgStructure.uncheckActs()
        self.ui.wdgStructure.setActChecked(acts_registry.act(self.scene))

        if self.ui.btnNotes.isChecked() or (self.scene.document and self.scene.document.loaded):
            self._update_notes()
        else:
            self.ui.textNotes.clear()

        self._characters_model.setScene(self.scene)
        self._character_changed()

        self.questionsEditor.clear()
        self.questionsEditor.setValue([x.plot.text for x in self.scene.plot_values])

        self.tagsEditor.clear()
        self.tagsEditor.setValue(self.scene.tags)

        if self._new_scene:
            self.ui.btnPrevious.setDisabled(True)
            self.ui.btnPrevious.setHidden(True)
            self.ui.btnNext.setDisabled(True)
            self.ui.btnNext.setHidden(True)
        else:
            if self.scene.sequence == 0:
                self.ui.btnPrevious.setDisabled(True)
            else:
                self.ui.btnPrevious.setEnabled(True)
            if self.scene.sequence == len(self.novel.scenes) - 1:
                self.ui.btnNext.setDisabled(True)
            else:
                self.ui.btnNext.setEnabled(True)

        self._scene_builder_palette_model = SceneBuilderPaletteTreeModel(self.scene)
        self.ui.treeSceneBuilder.setModel(self._scene_builder_palette_model)
        self.ui.treeSceneBuilder.selectionModel().selectionChanged.connect(self._on_scene_builder_selection_changed)
        self._scene_builder_palette_model.modelReset.connect(self.ui.treeSceneBuilder.expandAll)
        self.ui.treeSceneBuilder.setColumnWidth(0, 400)
        self.ui.treeSceneBuilder.setColumnWidth(1, 40)
        self.ui.treeSceneBuilder.setColumnWidth(2, 40)
        self.ui.treeSceneBuilder.expandAll()
        self.ui.treeSceneBuilder.setItemDelegate(ScenesBuilderDelegate(self, self.scene))
        self._scene_builder_palette_model.setElements(self.scene.builder_elements)

        self._save_enabled = True

    def _page_toggled(self):
        if self.ui.btnAttributes.isChecked():
            self.ui.stackedWidget.setCurrentWidget(self.ui.pageStructure)
        elif self.ui.btnNotes.isChecked():
            self.ui.stackedWidget.setCurrentWidget(self.ui.pageNotes)
            self._update_notes()
        elif self.ui.btnBuilder.isChecked():
            self.ui.stackedWidget.setCurrentWidget(self.ui.pageBuilder)

    def _beat_selected(self, beat: StoryBeat):
        if self.scene.beat and self.scene.beat != beat:
            self.ui.wdgStructure.toggleBeat(self.scene.beat, False)
        self.scene.beat = beat
        self.ui.wdgStructure.unhighlightBeats()
        self.ui.wdgStructure.highlightBeat(beat)

    def _beat_removed(self, beat: StoryBeat):
        if self.scene.beat and self.scene.beat == beat:
            self.scene.beat = None
            self.ui.wdgStructure.unhighlightBeats()
            self.ui.wdgStructure.toggleBeat(beat, False)

    def _update_notes(self):
        if self.scene.document:
            if not self.scene.document.loaded:
                json_client.load_document(self.novel, self.scene.document)
            self.ui.textNotes.setText(self.scene.document.content, self.scene.title, title_read_only=True)
        else:
            self.ui.textNotes.clear()

    def _on_pov_changed(self):
        pov = self.ui.cbPov.currentData()
        if pov:
            self.scene.pov = pov
        else:
            self.scene.pov = None
        self._update_pov_avatar()
        self._characters_model.update()
        self.ui.cbPov.setStyleSheet('''
                        QComboBox {border: 0px black solid;}
                        ''')
        self._character_changed()
        if self._save_enabled:
            self.ui.wdgSceneStructure.updatePov()

    def _update_pov_avatar(self):
        if self.scene.pov:
            if self.scene.pov.avatar:
                pixmap = avatars.pixmap(self.scene.pov)
                self.ui.lblAvatar.setPixmap(
                    pixmap.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation))
            else:
                pixmap = avatars.name_initial_icon(self.scene.pov).pixmap(128, 128)
                self.ui.lblAvatar.setPixmap(pixmap)
        else:
            self.ui.lblAvatar.setPixmap(IconRegistry.portrait_icon().pixmap(QSize(128, 128)))

    def _character_changed(self):
        self.ui.wdgCharacters.clear()

        if self.scene.pov:
            self.ui.wdgCharacters.addLabel(CharacterLabel(self.scene.pov, pov=True))
        for character in self.scene.characters:
            self.ui.wdgCharacters.addLabel(CharacterLabel(character))

        self._save_scene()

    def _save_scene(self):
        if not self._save_enabled:
            return

        self.scene.title = self.ui.lineTitle.text()
        self.scene.synopsis = self.ui.textSynopsis.toPlainText()
        self.scene.agendas.clear()
        self.scene.agendas.extend(self.ui.wdgSceneStructure.agendas())
        self.scene.day = self.ui.sbDay.value()

        self.scene.plot_values.clear()
        scene_plots = [ScenePlotValue(x) for x in self.questionsEditor.selectedItems()]
        self.scene.plot_values.extend(scene_plots)

        self.scene.tags.clear()
        self.scene.tags.extend(self.tagsEditor.value())

        if self._new_scene:
            self.novel.scenes.append(self.scene)
            self.scene.sequence = self.novel.scenes.index(self.scene)
            self.repo.insert_scene(self.novel, self.scene)
        else:
            self.repo.update_scene(self.scene)

        if not self.scene.document:
            self.scene.document = Document('', scene_id=self.scene.id)
            self.scene.document.loaded = True

        if self.scene.document.loaded:
            self.scene.document.content = self.ui.textNotes.textEditor.toHtml()
            json_client.save_document(self.novel, self.scene.document)
        self._new_scene = False

    def _on_close(self):
        self.scene.builder_elements.clear()
        self.scene.builder_elements.extend(self._scene_builder_elements())
        self._save_scene()

    def __get_scene_builder_element(self, scene: Scene, node: SceneInventoryNode, seq: int) -> SceneBuilderElement:
        children = []
        for child_seq, child in enumerate(node.children):
            children.append(self.__get_scene_builder_element(self.scene, child, child_seq))

        return SceneBuilderElement(type=convert_to_element_type(node), text=node.name,
                                   children=children,
                                   character=node.character, has_suspense=node.suspense, has_tension=node.tension,
                                   has_stakes=node.stakes)

    def _on_previous_scene(self):
        row = self.scene.sequence - 1
        self.ui.lstScenes.selectionModel().select(self.scenes_model.index(row, ScenesTableModel.ColTitle),
                                                  QItemSelectionModel.ClearAndSelect)
        self._new_scene_selected(self.scenes_model.index(row, 0))

    def _on_next_scene(self):
        row = self.scene.sequence + 1
        self.ui.lstScenes.selectionModel().select(self.scenes_model.index(row, ScenesTableModel.ColTitle),
                                                  QItemSelectionModel.ClearAndSelect)
        self._new_scene_selected(self.scenes_model.index(row, 0))

    def _new_scene_selected(self, index: QModelIndex):
        self.scene.builder_elements.clear()
        self.scene.builder_elements.extend(self._scene_builder_elements())
        self._save_scene()

        scene = self.scenes_model.data(index, role=ScenesTableModel.SceneRole)
        self._save_enabled = False
        self._update_view(scene)

    def _scene_builder_elements(self) -> List[SceneBuilderElement]:
        elements: List[SceneBuilderElement] = []
        for seq, node in enumerate(self._scene_builder_palette_model.root.children):
            elements.append(self.__get_scene_builder_element(self.scene, node, seq))

        return elements

    def _on_dclick_scene_builder_inventory(self, index: QModelIndex):
        node = index.data(SceneBuilderInventoryTreeModel.NodeRole)
        if isinstance(node, SceneInventoryNode):
            self._scene_builder_palette_model.insertNode(node)

    def _on_scene_builder_selection_changed(self):
        indexes = self.ui.treeSceneBuilder.selectedIndexes()
        self.ui.btnDelete.setEnabled(bool(indexes))
        self.ui.btnEdit.setEnabled(bool(indexes))

    def _on_delete_scene_builder_element(self):
        indexes = self.ui.treeSceneBuilder.selectedIndexes()
        if not indexes:
            return
        self._scene_builder_palette_model.deleteItem(indexes[0])
        self.ui.btnDelete.setDisabled(True)

    def _on_preview_scene_builder(self):
        SceneBuilderPreviewDialog().display(self._scene_builder_elements())

    def _on_edit_scene_builder_element(self):
        indexes = self.ui.treeSceneBuilder.selectedIndexes()
        if not indexes:
            return
        self.ui.treeSceneBuilder.edit(indexes[0])


class ScenesBuilderDelegate(QStyledItemDelegate):

    def __init__(self, view: SceneEditor, scene: Scene, parent=None):
        super(ScenesBuilderDelegate, self).__init__(parent)
        self.scene = scene
        self.view = view
        self._close_shortcut = self.view.ui.btnClose.shortcut()

    @overrides
    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        node = index.internalPointer()
        if isinstance(node, CharacterEntryNode):
            return QComboBox(parent)
        lineedit = QLineEdit(parent)
        lineedit.textEdited.connect(partial(self._on_text_edit, lineedit))
        self.view.ui.btnClose.setShortcut('')
        lineedit.destroyed.connect(lambda: self.view.ui.btnClose.setShortcut(self._close_shortcut))
        return lineedit

    @overrides
    def setEditorData(self, editor: QWidget, index: QModelIndex):
        if isinstance(editor, QTextEdit) or isinstance(editor, QLineEdit):
            node = index.internalPointer()
            editor.setText(node.name)
        elif isinstance(editor, QComboBox):
            for char in self.scene.characters:
                editor.addItem(QIcon(avatars.pixmap(char)), char.name, char)
            editor.activated.connect(lambda: self._commit_and_close(editor))
            editor.showPopup()

    @overrides
    def setModelData(self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex):
        if isinstance(editor, QComboBox):
            model.setData(index, editor.currentData(Qt.ItemDataRole.UserRole))
        elif isinstance(editor, QLineEdit):
            model.setData(index, editor.text())

    def _on_text_edit(self, editor: QLineEdit, text: str):
        if len(text) == 1:
            editor.setText(text.upper())

    def _commit_and_close(self, editor):
        self.commitData.emit(editor)
        self.closeEditor.emit(editor)
