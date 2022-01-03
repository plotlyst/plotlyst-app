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
import pickle
from typing import Any, Dict, List

from PyQt6.QtCore import QModelIndex, Qt, QMimeData, QByteArray, pyqtSignal, QPersistentModelIndex, QVariant
from PyQt6.QtGui import QFont, QColor
from anytree import Node
from overrides import overrides

from src.main.python.plotlyst.core.domain import Novel, Chapter, Scene
from src.main.python.plotlyst.model.common import ActionBasedTreeModel, emit_column_changed_in_tree
from src.main.python.plotlyst.model.tree_model import TreeItemModel
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.worker.persistence import RepositoryPersistenceManager


class ChapterNode(Node):
    def __init__(self, chapter: Chapter, parent):
        super().__init__(chapter.title, parent)
        self.chapter = chapter


class SceneNode(Node):
    def __init__(self, scene: Scene, parent):
        super(SceneNode, self).__init__(scene.title, parent)
        self.scene = scene


class EmptyNode(Node):
    pass


class UncategorizedChapterNode(Node):
    def __init__(self, parent):
        super(UncategorizedChapterNode, self).__init__('<Uncategorized>', parent)


class SceneMimeData(QMimeData):
    def __init__(self, node: SceneNode):
        self.node = node
        super(SceneMimeData, self).__init__()


class ChaptersTreeModel(TreeItemModel, ActionBasedTreeModel):
    MimeType: str = 'application/scene'
    orderChanged = pyqtSignal()

    ColPlus: int = 1

    def __init__(self, novel: Novel, parent=None):
        super(ChaptersTreeModel, self).__init__(parent)
        self.novel = novel
        self.repo = RepositoryPersistenceManager.instance()

        self.update()

    @overrides
    def columnCount(self, parent: QModelIndex) -> int:
        return 2

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if index.column() > 0 and self._action_index and index.row() == self._action_index.row() \
                and self._action_index.parent() == index.parent():
            if role == Qt.ItemDataRole.DecorationRole:
                if index.column() == self.ColPlus:
                    return IconRegistry.plus_circle_icon()
        if index.column() > 0:
            if role == self.NodeRole:
                return index.internalPointer()
            return QVariant()

        node = index.internalPointer()
        if isinstance(node, ChapterNode):
            if role == Qt.ItemDataRole.DisplayRole:
                return f'Chapter {index.row() + 1}'
            if role == Qt.ItemDataRole.DecorationRole:
                return IconRegistry.chapter_icon()
        if isinstance(node, UncategorizedChapterNode) or (
                isinstance(node, SceneNode) and isinstance(node.parent, UncategorizedChapterNode)):
            if role == Qt.ItemDataRole.FontRole:
                font = QFont()
                font.setItalic(True)
                return font
            if role == Qt.ItemDataRole.ForegroundRole:
                return QColor(Qt.GlobalColor.gray)
        if isinstance(node, UncategorizedChapterNode) and role == Qt.ItemDataRole.DisplayRole:
            if node.children:
                return f'{node.name} ({len(node.children)})'
        if isinstance(node, SceneNode) and role == Qt.ItemDataRole.DisplayRole:
            if not node.name:
                return f'Scene {self.novel.scenes.index(node.scene) + 1}'

        return super().data(index, role)

    def update(self):
        self.root.children = []
        self._action_index = None
        chapters: Dict[str, ChapterNode] = {}
        for chapter in self.novel.chapters:
            chapters[chapter.sid()] = ChapterNode(chapter, self.root)
        for scene in self.novel.scenes:
            if scene.chapter:
                SceneNode(scene, chapters[scene.chapter.sid()])

        EmptyNode('', self.root)  # to mimic empty space
        dummy_parent = UncategorizedChapterNode(self.root)
        for scene in self.novel.scenes:
            if not scene.chapter:
                SceneNode(scene, dummy_parent)

    def newChapter(self, index: int = -1) -> Chapter:
        if index < 0:
            index = len(self.novel.chapters)
        chapter = Chapter(title='')
        self.novel.chapters.insert(index, chapter)

        self.update()
        self.modelReset.emit()

        return chapter

    def removeChapter(self, index: QModelIndex):
        node = index.internalPointer()
        if isinstance(node, SceneNode):
            return

        node.parent = None

        self.novel.chapters.remove(node.chapter)
        self.repo.update_novel(self.novel)
        for scene in self.novel.scenes:
            if scene.chapter and scene.chapter.id == node.chapter.id:
                scene.chapter = None
                self.repo.update_scene(scene)
        self._action_index = None
        self.update()
        self.modelReset.emit()

    @overrides
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        node = index.internalPointer()
        if isinstance(node, SceneNode):
            return flags | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled
        return flags | Qt.ItemFlag.ItemIsDropEnabled

    @overrides
    def mimeData(self, indexes: List[QModelIndex]) -> QMimeData:
        node = indexes[0].internalPointer()
        mime_data = SceneMimeData(node)
        mime_data.setData(self.MimeType, QByteArray(pickle.dumps(node.scene)))
        return mime_data

    @overrides
    def mimeTypes(self) -> List[str]:
        return [self.MimeType]

    @overrides
    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int,
                        parent: QModelIndex) -> bool:
        if row >= 0 and parent.internalPointer() == self.root:
            return False
        if not data.hasFormat(self.MimeType):
            return False
        if not isinstance(data, SceneMimeData):
            return False
        if not isinstance(parent.internalPointer(), (ChapterNode, UncategorizedChapterNode)):
            return False

        return True

    @overrides
    def dropMimeData(self, data: SceneMimeData, action: Qt.DropAction, row: int, column: int,
                     parent: QModelIndex) -> bool:
        parent_node: Node = parent.internalPointer()
        node: SceneNode = data.node
        if isinstance(parent_node, ChapterNode):
            node.scene.chapter = parent_node.chapter
            self._dropUnderNode(parent_node, node, row)

        if isinstance(parent_node, UncategorizedChapterNode):
            node.scene.chapter = None
            self._dropUnderNode(parent_node, node, row)

        old_index = self.novel.scenes.index(node.scene)
        new_index = [x for x in self.root.leaves if isinstance(x, SceneNode)].index(node)
        if old_index != new_index:
            self.novel.scenes.insert(new_index, self.novel.scenes.pop(old_index))
            self.orderChanged.emit()
        parent = self.rootIndex()
        self.layoutAboutToBeChanged.emit([QPersistentModelIndex(parent)])
        self.layoutChanged.emit([QPersistentModelIndex(parent)])
        RepositoryPersistenceManager.instance().update_scene(node.scene)

        return True

    @overrides
    def _updateActionIndex(self, index: QModelIndex):
        super(ChaptersTreeModel, self)._updateActionIndex(index)

        node = index.internalPointer()
        if isinstance(node, (UncategorizedChapterNode, EmptyNode)):
            self._action_index = None
        elif isinstance(node, SceneNode):
            if node.scene.chapter is None:
                self._action_index = None

    @overrides
    def _emitActionsChanged(self, index: QModelIndex):
        emit_column_changed_in_tree(self, self.ColPlus, index)

    def _dropUnderNode(self, parent_node: Node, node: SceneNode, row: int):
        old_parent_node: Node = node.parent
        if old_parent_node is not parent_node:
            old_parent_node.children = [x for x in old_parent_node.children if x is not node]
        node.parent = parent_node

        if row >= 0:
            children_list = list(parent_node.children)
            old_index = children_list.index(node)
            new_index = row
            if old_parent_node is parent_node and new_index > old_index:
                new_index -= 1
            children_list[old_index], children_list[new_index] = children_list[new_index], children_list[old_index]
            parent_node.children = children_list
        else:
            parent_node.children = sorted(parent_node.children, key=lambda x: x.scene.sequence)
