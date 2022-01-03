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
from typing import Any, List

from PyQt6.QtCore import QAbstractItemModel, QModelIndex, QVariant, Qt, QMimeData, QByteArray
from anytree import Node
from overrides import overrides


class NodeMimeData(QMimeData):
    def __init__(self, node: Node):
        self.node = node
        super(NodeMimeData, self).__init__()


class TreeItemModel(QAbstractItemModel):
    NodeRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.root = Node('root')
        self.dragAndDropEnabled: bool = False

    def rootNode(self) -> Node:
        return self.root

    def setRootNode(self, node: Node):
        self.root = node

    @overrides
    def index(self, row: int, column: int, parent: QModelIndex) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent_node: Node
        if not parent.isValid():
            parent_node = self.root
        else:
            parent_node = parent.internalPointer()

        if row >= len(parent_node.children):
            return QModelIndex()

        child_node = parent_node.children[row]
        return self.createIndex(row, column, child_node)

    @overrides
    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        child_node: Node = index.internalPointer()
        parent_node: Node = child_node.parent

        if parent_node == self.root:
            return QModelIndex()

        if not parent_node or parent_node.parent == self.root or not parent_node.parent:
            parent_node_index = 0
        else:
            parent_node_index = parent_node.parent.children.index(parent_node)

        return self.createIndex(parent_node_index, 0, parent_node)

    @overrides
    def rowCount(self, parent: QModelIndex) -> int:
        if parent.column() > 0:
            return 0

        parent_node: Node
        if not parent.isValid():
            parent_node = self.root
        else:
            parent_node = parent.internalPointer()

        return len(parent_node.children) if parent_node else 0

    @overrides
    def columnCount(self, parent: QModelIndex) -> int:
        if parent.isValid():
            node: Node = parent.internalPointer()
            return node.depth
        return 1

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return QVariant()
        if role == self.NodeRole:
            return index.internalPointer()
        if role == Qt.ItemDataRole.DisplayRole:
            node: Node = index.internalPointer()
            return node.name

    @overrides
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        if self.dragAndDropEnabled:
            return flags | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled
        return super().flags(index)

    @overrides
    def mimeTypes(self) -> List[str]:
        return [self.MimeType]

    @overrides
    def canDropMimeData(self, data: NodeMimeData, action: Qt.DropAction, row: int, column: int,
                        parent: QModelIndex) -> bool:
        if all(not data.hasFormat(x) for x in self.mimeTypes()):
            return False
        if not isinstance(data, self._mimeDataClass()):
            return False
        if parent.isValid():
            if data.node is parent.internalPointer() or (data.node.parent is parent.internalPointer() and row < 0):
                return False

        return True

    @overrides
    def mimeData(self, indexes: List[QModelIndex]) -> QMimeData:
        node = indexes[0].internalPointer()
        clazz = self._mimeDataClass()
        mime_data = clazz(node)
        mime_data.setData(self.MimeType, QByteArray(pickle.dumps(node)))
        return mime_data

    @overrides
    def dropMimeData(self, data: NodeMimeData, action: Qt.DropAction, row: int, column: int,
                     parent: QModelIndex) -> bool:
        if parent.isValid():
            parent_node = parent.internalPointer()
        else:
            parent_node = self.root

        node: Node = data.node
        node.parent = parent_node
        if node and row >= 0:
            self._repositionNodeUnder(node, parent_node, row)

        self.modelReset.emit()
        return True

    def rootIndex(self) -> QModelIndex:
        return self.index(0, 0, QModelIndex())

    def _mimeDataClass(self):
        return NodeMimeData

    def _repositionNodeUnder(self, node, parent, row: int):
        children_list = list(parent.children)
        old_index = children_list.index(node)
        new_index = row
        if old_index < new_index:
            new_index -= 1
        children_list.pop(old_index)
        children_list.insert(new_index, node)
        parent.children = children_list
