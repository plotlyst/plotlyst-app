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
from typing import Any

from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtGui import QIcon
from anytree import Node
from overrides import overrides

from src.main.python.plotlyst.core.client import json_client
from src.main.python.plotlyst.core.domain import Novel, Document
from src.main.python.plotlyst.model.common import emit_column_changed_in_tree, ActionBasedTreeModel
from src.main.python.plotlyst.model.tree_model import TreeItemModel, NodeMimeData
from src.main.python.plotlyst.view.icons import IconRegistry, avatars
from src.main.python.plotlyst.worker.persistence import RepositoryPersistenceManager


class DocumentNode(Node):
    def __init__(self, doc: Document, parent: Node):
        super().__init__(doc.title, parent)
        self.document = doc


class DocumentMimeData(NodeMimeData):
    def __init__(self, node: DocumentNode):
        super(DocumentMimeData, self).__init__(node)
        self.document = node.document


class DocumentsTreeModel(TreeItemModel, ActionBasedTreeModel):
    MimeType: str = 'application/document'

    ColMenu: int = 1
    ColPlus: int = 2

    def __init__(self, novel: Novel):
        super(DocumentsTreeModel, self).__init__()
        self.dragAndDropEnabled = True
        self.novel = novel
        self.repo = RepositoryPersistenceManager.instance()
        for doc in self.novel.documents:
            self._initNodes(doc, self.root)

    def _initNodes(self, doc: Document, parent_node: DocumentNode):
        new_node = DocumentNode(doc, parent_node)
        for child in doc.children:
            self._initNodes(child, new_node)

    @overrides
    def columnCount(self, parent: QModelIndex) -> int:
        return 3

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == self.NodeRole:
            return super(DocumentsTreeModel, self).data(index, role)
        if index.column() == 0:
            doc: Document = index.internalPointer().document
            char = doc.character(self.novel)
            if role == Qt.ItemDataRole.DisplayRole:
                if char:
                    return char.name
                return index.internalPointer().document.title
            if role == Qt.ItemDataRole.DecorationRole:
                if char:
                    return QIcon(avatars.pixmap(char))
                if doc.icon:
                    return IconRegistry.from_name(doc.icon, doc.icon_color)
            return super(DocumentsTreeModel, self).data(index, role)
        if index.column() > 0 and self._action_index and index.row() == self._action_index.row() \
                and self._action_index.parent() == index.parent():
            if role == Qt.ItemDataRole.DecorationRole:
                if index.column() == self.ColMenu:
                    return IconRegistry.dots_icon('grey')
                if index.column() == self.ColPlus:
                    return IconRegistry.plus_circle_icon()

    @overrides
    def _mimeDataClass(self):
        return DocumentMimeData

    @overrides
    def dropMimeData(self, data: DocumentMimeData, action: Qt.DropAction, row: int, column: int,
                     parent: QModelIndex) -> bool:
        old_parent: Node = data.node.parent
        if old_parent is self.root:
            old_index = self.novel.documents.index(data.document)
            self.novel.documents.remove(data.document)
        elif isinstance(old_parent, DocumentNode):
            old_index = old_parent.document.children.index(data.document)
            old_parent.document.children.remove(data.document)
        else:
            return False

        node_changed: bool = super().dropMimeData(data, action, row, column, parent)
        if not node_changed:
            return False

        if data.node.parent is old_parent and old_index < row:
            row -= 1

        if data.node.parent is self.root:
            self.novel.documents.insert(row, data.document)
        else:
            data.node.parent.document.children.insert(row, data.document)

        self.repo.update_novel(self.novel)
        return True

    @overrides
    def _emitActionsChanged(self, index: QModelIndex):
        emit_column_changed_in_tree(self, self.ColMenu, index)
        emit_column_changed_in_tree(self, self.ColPlus, index)

    def insertDoc(self, doc: Document) -> QModelIndex:
        DocumentNode(doc, self.root)
        self.novel.documents.append(doc)
        self.modelReset.emit()
        self.repo.update_novel(self.novel)

        return self.index(self.rowCount(QModelIndex()) - 1, 0, QModelIndex())

    def insertDocUnder(self, doc: Document, index: QModelIndex) -> QModelIndex:
        node: DocumentNode = index.internalPointer()
        node.document.children.append(doc)
        DocumentNode(doc, node)
        self.modelReset.emit()
        self.repo.update_novel(self.novel)

        parent_index = self.index(index.row(), 0, index.parent())
        return self.index(len(node.document.children) - 1, 0, parent_index)

    def removeDoc(self, index: QModelIndex):
        node: DocumentNode = index.internalPointer()
        doc: Document = node.document

        parent_node = index.parent().internalPointer()
        if parent_node:
            parent_node.document.children.remove(doc)
        else:
            self.novel.documents.remove(doc)

        node.parent = None
        self.repo.update_novel(self.novel)
        self._removeDoc(doc)

        self.modelReset.emit()

    def _removeDoc(self, doc: Document):
        for child in doc.children:
            self._removeDoc(child)
        json_client.delete_document(self.novel, doc)
