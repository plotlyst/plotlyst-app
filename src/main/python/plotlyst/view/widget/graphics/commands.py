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
from enum import Enum, auto
from typing import Any, Optional, List

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QUndoCommand
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsScene
from overrides import overrides


class MergeableCommandType(Enum):
    TEXT = auto()
    SIZE = auto()


class MergeableGraphicsItemCommand(QUndoCommand):
    def __init__(self, type: MergeableCommandType, item: QGraphicsItem, func, old: Any, new: Any, parent=None):
        super().__init__(parent)
        self.type = type
        self.item = item
        self.func = func
        self.old = old
        self.new = new

    @overrides
    def id(self) -> int:
        return self.type.value

    @overrides
    def mergeWith(self, other: 'MergeableGraphicsItemCommand') -> bool:
        if self.type == other.type and self.item is other.item:
            self.new = other.new
            return True
        return False

    @overrides
    def redo(self) -> None:
        self.func(self.new)

    @overrides
    def undo(self) -> None:
        self.func(self.old)


class TextEditingCommand(MergeableGraphicsItemCommand):
    def __init__(self, item: QGraphicsItem, new: Any, parent=None):
        super().__init__(MergeableCommandType.TEXT, item, item.setText, item.text(), new, parent)


class SizeEditingCommand(MergeableGraphicsItemCommand):
    def __init__(self, item: QGraphicsItem, new: Any, parent=None):
        super().__init__(MergeableCommandType.SIZE, item, item.setSize, item.size(), new, parent)


class GraphicsItemCommand(QUndoCommand):
    def __init__(self, item: QGraphicsItem, func, old: Any, new: Any, parent=None):
        super().__init__(parent)
        self.item = item
        self.func = func
        self.old = old
        self.new = new

    @overrides
    def redo(self) -> None:
        self.func(self.new)

    @overrides
    def undo(self) -> None:
        self.func(self.old)


class NoteEditorCommand(QUndoCommand):
    def __init__(self, item: QGraphicsItem, oldText: str, oldHeight: int, newText: str, newHeight: int, parent=None):
        super().__init__(parent)
        self.type = MergeableCommandType.TEXT
        self.item = item
        self.oldText = oldText
        self.oldHeight = oldHeight
        self.newText = newText
        self.newHeight = newHeight

    @overrides
    def id(self) -> int:
        return self.type.value

    @overrides
    def mergeWith(self, other: QUndoCommand) -> bool:
        if isinstance(other, NoteEditorCommand) and self.item is other.item:
            self.newText = other.newText
            self.newHeight = other.newHeight
            return True
        return False

    @overrides
    def redo(self) -> None:
        self.item.setText(self.newText, self.newHeight)

    @overrides
    def undo(self) -> None:
        self.item.setText(self.oldText, self.oldHeight)


class PosChangedCommand(QUndoCommand):
    def __init__(self, item: QGraphicsItem, old: QPointF, new: QPointF, parent=None):
        super().__init__(parent)
        self.item = item
        self.old = old
        self.new = new
        self._first = True

    @overrides
    def redo(self) -> None:
        if self._first:
            self._first = False
            return
        self.item.setPosCommandEnabled(False)
        self.item.setPos(self.new)
        self.item.updatePos()
        self.item.setPosCommandEnabled(True)

    @overrides
    def undo(self) -> None:
        self.item.setPosCommandEnabled(False)
        self.item.setPos(self.old)
        self.item.updatePos()
        self.item.setPosCommandEnabled(True)


class ResizeItemCommand(QUndoCommand):
    def __init__(self, item: QGraphicsItem, old: QPointF, new: QPointF, parent=None):
        super().__init__(parent)
        self.item = item
        self.old = old
        self.new = new
        self._first = True

    @overrides
    def redo(self) -> None:
        if self._first:
            self._first = False
            return
        self.item.setPosCommandEnabled(False)
        self.item.updatePos()
        self.item.parentItem().rearrangeSize(self.new)
        self.item.setPosCommandEnabled(True)

    @overrides
    def undo(self) -> None:
        self.item.setPosCommandEnabled(False)
        self.item.updatePos()
        self.item.parentItem().rearrangeSize(self.old)
        self.item.setPosCommandEnabled(True)

class ItemAdditionCommand(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, item: QGraphicsItem, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.item = item
        self._first = True

    @overrides
    def redo(self) -> None:
        if self._first:
            self._first = False
            return
        self.scene.addNetworkItem(self.item)

    @overrides
    def undo(self) -> None:
        self.scene.removeNetworkItem(self.item)


class ItemRemovalCommand(QUndoCommand):
    def __init__(self, scene: QGraphicsScene, item: QGraphicsItem, connectors: Optional[List[QGraphicsItem]] = None,
                 parent=None):
        super().__init__(parent)
        self.scene = scene
        self.item = item
        self.connectors = connectors
        self._first = True

    @overrides
    def redo(self) -> None:
        if self._first:
            self._first = False
            return
        self.scene.removeNetworkItem(self.item)

    @overrides
    def undo(self) -> None:
        self.scene.addNetworkItem(self.item, self.connectors)

# class ConnectorAdditionCommand(QUndoCommand):
#     def __init__(self, scene: QGraphicsScene, item: QGraphicsItem, parent=None):
#         super().__init__(parent)
#         self.scene = scene
#         self.item = item
#         self._first = True
#
#     @overrides
#     def redo(self) -> None:
#         if self._first:
#             self._first = False
#             return
#         self.scene.addConnectorItem(self.item)
#
#     @overrides
#     def undo(self) -> None:
#         self.scene.removeConnectorItem(self.item)
