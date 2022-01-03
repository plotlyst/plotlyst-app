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
from anytree import Node
from overrides import overrides

from src.main.python.plotlyst.core.domain import Novel, Location
from src.main.python.plotlyst.model.common import emit_column_changed_in_tree, ActionBasedTreeModel
from src.main.python.plotlyst.model.tree_model import TreeItemModel, NodeMimeData
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.worker.persistence import RepositoryPersistenceManager


class LocationNode(Node):
    def __init__(self, location: Location, parent: Node):
        super().__init__(location.name, parent)
        self.location = location


class LocationMimeData(NodeMimeData):
    def __init__(self, node: LocationNode):
        self.location = node.location
        super(LocationMimeData, self).__init__(node)


class LocationsTreeModel(TreeItemModel, ActionBasedTreeModel):
    MimeType: str = 'application/location'

    def __init__(self, novel: Novel):
        super(LocationsTreeModel, self).__init__()
        self.dragAndDropEnabled = True
        self.novel = novel
        self.repo = RepositoryPersistenceManager.instance()
        for location in self.novel.locations:
            self._initNodes(location, self.root)

    def _initNodes(self, location: Location, parent_node: LocationNode):
        new_node = LocationNode(location, parent_node)
        for child in location.children:
            self._initNodes(child, new_node)

    @overrides
    def columnCount(self, parent: QModelIndex) -> int:
        return 2

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == self.NodeRole:
            return super(LocationsTreeModel, self).data(index, role)
        if index.column() == 0:
            location: Location = index.internalPointer().location
            if role == Qt.ItemDataRole.DisplayRole:
                return index.internalPointer().location.name
            if role == Qt.ItemDataRole.DecorationRole:
                if location.icon:
                    return IconRegistry.from_name(location.icon, location.icon_color)
            return super(LocationsTreeModel, self).data(index, role)
        if index.column() == 1 and self._action_index and index.row() == self._action_index.row() \
                and self._action_index.parent() == index.parent():
            if role == Qt.ItemDataRole.DecorationRole:
                return IconRegistry.plus_circle_icon('lightGrey')

    @overrides
    def dropMimeData(self, data: LocationMimeData, action: Qt.DropAction, row: int, column: int,
                     parent: QModelIndex) -> bool:
        old_parent: Node = data.node.parent
        if old_parent is self.root:
            old_index = self.novel.locations.index(data.location)
            self.novel.locations.remove(data.location)
        elif isinstance(old_parent, LocationMimeData):
            old_index = old_parent.location.children.index(data.location)
            old_parent.location.children.remove(data.location)
        else:
            return False

        node_changed: bool = super().dropMimeData(data, action, row, column, parent)
        if not node_changed:
            return False

        if data.node.parent is old_parent and old_index < row:
            row -= 1

        if data.node.parent is self.root:
            self.novel.locations.insert(row, data.location)
        else:
            data.node.parent.location.children.insert(row, data.location)

        self.repo.update_novel(self.novel)
        return True

    @overrides
    def _mimeDataClass(self):
        return LocationMimeData

    @overrides
    def _emitActionsChanged(self, index: QModelIndex):
        emit_column_changed_in_tree(self, 1, index)

    def insertLocation(self, location: Location) -> QModelIndex:
        LocationNode(location, self.root)
        self.novel.locations.append(location)
        self.modelReset.emit()
        self.repo.update_novel(self.novel)

        return self.index(self.rowCount(QModelIndex()) - 1, 0, QModelIndex())

    def insertLocationUnder(self, location: Location, index: QModelIndex) -> QModelIndex:
        node: LocationNode = index.internalPointer()
        node.location.children.append(location)
        LocationNode(location, node)
        self.modelReset.emit()
        self.repo.update_novel(self.novel)

        parent_index = self.index(index.row(), 0, index.parent())
        return self.index(len(node.location.children) - 1, 0, parent_index)

    def removeLocation(self, index: QModelIndex):
        self._action_index = None
        node: LocationNode = index.internalPointer()
        location: Location = node.location

        parent_node = index.parent().internalPointer()
        if parent_node:
            parent_node.location.children.remove(location)
        else:
            self.novel.locations.remove(location)

        node.parent = None
        self.repo.update_novel(self.novel)

        self.modelReset.emit()
