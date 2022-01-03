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

from PyQt6.QtCore import Qt, QModelIndex, pyqtSignal
from anytree import Node
from overrides import overrides

from src.main.python.plotlyst.core.domain import CausalityItem, Causality
from src.main.python.plotlyst.model.tree_model import TreeItemModel


class _CausalityNode(Node):
    def __init__(self, item: CausalityItem, parent: Node):
        super(_CausalityNode, self).__init__(item.text, parent)
        self.item = item


class CaualityTreeModel(TreeItemModel):
    changed = pyqtSignal()

    def __init__(self, causality: Causality, parent=None):
        def _initNodes(item: CausalityItem, parent: Node):
            node = _CausalityNode(item, parent)
            for link in item.links:
                _initNodes(link, node)

        super().__init__(parent)
        self.causality: Causality = causality
        for item in self.causality.items:
            _initNodes(item, self.root)

    @overrides
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return super().flags(index) | Qt.ItemFlag.ItemIsEditable

    @overrides
    def setData(self, index: QModelIndex, value: Any, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            node: _CausalityNode = index.internalPointer()
            node.item.text = value
            self.changed.emit()
            return True
        return False

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        node: _CausalityNode = index.internalPointer()
        if role == Qt.ItemDataRole.DisplayRole:
            return node.item.text
        return super().data(index, role)

    def addChild(self, index: QModelIndex, name: str = 'Child'):
        node: _CausalityNode = index.internalPointer()
        item = CausalityItem(name)
        node.item.links.append(item)
        _CausalityNode(item, node)

        self.changed.emit()
        self.modelReset.emit()

    def delete(self, index: QModelIndex):
        node: _CausalityNode = index.internalPointer()

        parent_node = index.parent().internalPointer()
        if parent_node:
            parent_node.item.links.remove(node.item)
            node.parent = None

            self.changed.emit()
            self.modelReset.emit()
