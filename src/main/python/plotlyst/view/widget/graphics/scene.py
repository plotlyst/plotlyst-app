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

from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Set, Union

import qtanim
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QPoint, QObject
from PyQt6.QtGui import QTransform, \
    QKeyEvent, QKeySequence, QCursor, QImage, QUndoStack
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsSceneMouseEvent, QApplication, \
    QGraphicsSceneDragDropEvent
from overrides import overrides

from plotlyst.core.domain import Node, Diagram, GraphicsItemType, Connector, PlaceholderCharacter, \
    Character, to_node
from plotlyst.service.image import LoadedImage
from plotlyst.view.widget.graphics import NodeItem, CharacterItem, PlaceholderSocketItem, ConnectorItem, \
    AbstractSocketItem, EventItem
from plotlyst.view.widget.graphics.commands import ItemAdditionCommand, ItemRemovalCommand
from plotlyst.view.widget.graphics.items import NoteItem, ImageItem, IconItem, CircleShapedNodeItem, ResizeIconItem


@dataclass
class ItemDescriptor:
    mode: GraphicsItemType
    subType: str = ''


class NetworkScene(QGraphicsScene):
    cancelItemAddition = pyqtSignal()
    itemAdded = pyqtSignal(GraphicsItemType, NodeItem)
    editItem = pyqtSignal(NodeItem)
    itemMoved = pyqtSignal(NodeItem)
    hideItemEditor = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._diagram: Optional[Diagram] = None
        self._undoStack: Optional[QUndoStack] = None
        self._macroUndo: bool = False
        self._movedItems: Set[QGraphicsItem] = set()
        self._linkMode: bool = False
        self._additionDescriptor: Optional[ItemDescriptor] = None
        self._copyDescriptor: Optional[ItemDescriptor] = None
        self._animParent = QObject()

        self._placeholder: Optional[PlaceholderSocketItem] = None
        self._connectorPlaceholder: Optional[ConnectorItem] = None

    def undoStack(self) -> QUndoStack:
        return self._undoStack

    def setUndoStack(self, stack: QUndoStack):
        self._undoStack = stack

    def setDiagram(self, diagram: Diagram):
        self._diagram = diagram
        self.clear()
        if not self._diagram.loaded:
            self._load()

        nodes: Dict[str, NodeItem] = {}
        for node in self._diagram.data.nodes:
            nodeItem = self._addNode(node)
            nodes[str(node.id)] = nodeItem
        for connector in self._diagram.data.connectors:
            source = nodes.get(str(connector.source_id), None)
            target = nodes.get(str(connector.target_id), None)
            if source and target:
                self._addConnector(connector, source, target)

        # trigger scene calculation early so that the view won't jump around for the first click
        self.sceneRect()

    def isAdditionMode(self) -> bool:
        return self._additionDescriptor is not None

    def startAdditionMode(self, itemType: GraphicsItemType, subType: str = ''):
        self._additionDescriptor = ItemDescriptor(itemType, subType)

    def endAdditionMode(self):
        self._additionDescriptor = None

    def linkMode(self) -> bool:
        return self._linkMode

    def linkSource(self) -> Optional[AbstractSocketItem]:
        if self._connectorPlaceholder is not None:
            return self._connectorPlaceholder.source()

    def startLink(self, source: AbstractSocketItem):
        self._linkMode = True
        self._placeholder = PlaceholderSocketItem()
        self._placeholder.setVisible(False)
        self._placeholder.setEnabled(False)
        self.addItem(self._placeholder)
        self._connectorPlaceholder = ConnectorItem(source, self._placeholder)
        self._connectorPlaceholder.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.addItem(self._connectorPlaceholder)

        self._placeholder.setPos(source.scenePos())
        self._connectorPlaceholder.rearrange()
        self.hideItemEditor.emit()

    def endLink(self):
        self._linkMode = False
        self.removeItem(self._connectorPlaceholder)
        self.removeItem(self._placeholder)
        self._connectorPlaceholder = None
        self._placeholder = None

    def link(self, target: AbstractSocketItem):
        sourceNode: NodeItem = self._connectorPlaceholder.source().parentItem()
        targetNode: NodeItem = target.parentItem()

        self._onLink(sourceNode, self._connectorPlaceholder.source(), targetNode, target)
        connectorItem = ConnectorItem(self._connectorPlaceholder.source(), target)
        self._connectorPlaceholder.source().addConnector(connectorItem)
        target.addConnector(connectorItem)

        connector = Connector(
            sourceNode.node().id,
            targetNode.node().id,
            self._connectorPlaceholder.source().angle(), target.angle(),
            pen=connectorItem.penStyle(), width=connectorItem.size()
        )
        if connectorItem.icon():
            connector.icon = connectorItem.icon()
        connectorItem.setConnector(connector)
        if self._diagram:
            self._diagram.data.connectors.append(connector)
        self._save()

        self.addItem(connectorItem)
        self.endLink()

        self._undoStack.push(ItemAdditionCommand(self, connectorItem))

        sourceNode.setSelected(False)
        connectorItem.setSelected(True)

    def editItemEvent(self, item: Node):
        self.editItem.emit(item)

    @overrides
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            if self.linkMode():
                self.endLink()
            elif self.isAdditionMode():
                self.cancelItemAddition.emit()
                self.endAdditionMode()
            else:
                self.clearSelection()
        elif event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            self._removeItems()
        elif event.matches(QKeySequence.StandardKey.Copy) and len(self.selectedItems()) == 1:
            self._copy(self.selectedItems()[0])
        elif event.matches(QKeySequence.StandardKey.Paste):
            self._paste()
        elif not event.modifiers() and not event.key() == Qt.Key.Key_Escape and len(self.selectedItems()) == 1:
            item = self.selectedItems()[0]
            if isinstance(item, (EventItem, NoteItem)):
                self.editItem.emit(item)

    @overrides
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if (not self.isAdditionMode() and not self.linkMode() and
                event.button() & Qt.MouseButton.LeftButton and not self.itemAt(event.scenePos(), QTransform())):
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                pos = self._cursorScenePos()
                if pos:
                    self._addNewItem(pos, GraphicsItemType.EVENT)
            else:
                pass
        elif event.button() & Qt.MouseButton.RightButton or event.button() & Qt.MouseButton.MiddleButton:
            # disallow view movement to clear item selection
            return
        super().mousePressEvent(event)

    @overrides
    def mouseMoveEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if self.linkMode():
            self._placeholder.setPos(event.scenePos())
            self._connectorPlaceholder.rearrange()
        super().mouseMoveEvent(event)

    @overrides
    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if self._movedItems:
            for item in self._movedItems:
                item.updatePos()
            if self._macroUndo:
                self._undoStack.endMacro()
                self._macroUndo = False
            self._movedItems.clear()

        if self.linkMode():
            if event.button() & Qt.MouseButton.RightButton:
                self.endLink()
        elif self.isAdditionMode() and event.button() & Qt.MouseButton.RightButton:
            self.cancelItemAddition.emit()
            self.endAdditionMode()
        elif self._additionDescriptor is not None:
            self._addNewItem(event.scenePos(), self._additionDescriptor.mode, self._additionDescriptor.subType)

        super().mouseReleaseEvent(event)

    @overrides
    def mouseDoubleClickEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if (not self.isAdditionMode() and not self.linkMode() and
                event.button() & Qt.MouseButton.LeftButton and not self.itemAt(event.scenePos(), QTransform())):
            pos = self._cursorScenePos()
            if pos:
                self._addNewItem(pos, GraphicsItemType.EVENT)
        else:
            super().mouseDoubleClickEvent(event)

    @overrides
    def dragEnterEvent(self, event: QGraphicsSceneDragDropEvent) -> None:
        if event.mimeData().formats()[0].startswith('application/node'):
            event.accept()
        else:
            event.ignore()

    @overrides
    def dragMoveEvent(self, event: QGraphicsSceneDragDropEvent) -> None:
        event.accept()

    @overrides
    def dropEvent(self, event: QGraphicsSceneDragDropEvent) -> None:
        self._addNewItem(event.scenePos(), event.mimeData().reference())
        event.accept()

    def itemMovedEvent(self, item: NodeItem):
        if item.posCommandEnabled():
            self._movedItems.add(item)
            if len(self.selectedItems()) > 1 and not self._macroUndo:
                self._undoStack.beginMacro('Move items')
                self._macroUndo = True

        self.itemMoved.emit(item)

    def itemResizedEvent(self, item: ResizeIconItem):
        if item.posCommandEnabled():
            self._movedItems.add(item)

    def nodeChangedEvent(self, node: Node):
        self._save()

    def requestImageUpload(self, item: ImageItem):
        image = self._uploadImage()
        if image:
            item.setLoadedImage(image)

    def loadImage(self, item: ImageItem):
        image = self._loadImage(item.node())
        if image:
            item.setImage(image)

    def connectorChangedEvent(self, connector: ConnectorItem):
        self._save()

    def addNetworkItem(self, item: Union[NodeItem, ConnectorItem], connectors=None):
        def addConnectorItem(connectorItem: ConnectorItem):
            if connectorItem.scene():
                return
            connectorItem.source().addConnector(connectorItem)
            connectorItem.target().addConnector(connectorItem)
            self._diagram.data.connectors.append(connectorItem.connector())
            self.addItem(connectorItem)

        if isinstance(item, NodeItem):
            self._diagram.data.nodes.append(item.node())
            self.addItem(item)
            if connectors:
                for connector in connectors:
                    addConnectorItem(connector)
        elif isinstance(item, ConnectorItem):
            addConnectorItem(item)
        self._save()

    def removeNetworkItem(self, item: Union[NodeItem, ConnectorItem]):
        self._removeItem(item)

    def removeConnectorItem(self, connector: ConnectorItem):
        self._removeItem(connector)

    @staticmethod
    def toCharacterNode(scenePos: QPointF) -> Node:
        node = Node(scenePos.x(), scenePos.y(), type=GraphicsItemType.CHARACTER, size=60)
        node.x = node.x - CharacterItem.Margin
        node.y = node.y - CharacterItem.Margin
        return node

    @staticmethod
    def toIconNode(scenePos: QPointF) -> Node:
        node = Node(scenePos.x(), scenePos.y(), type=GraphicsItemType.ICON, size=60)
        node.x = node.x - IconItem.Margin
        node.y = node.y - IconItem.Margin
        return node

    @staticmethod
    def toEventNode(scenePos: QPointF, itemType: GraphicsItemType, subType: str = '') -> Node:
        node: Node = to_node(scenePos.x(), scenePos.y(), itemType, subType,
                             default_size=QApplication.font().pointSize())
        node.x = node.x - EventItem.Margin - EventItem.Padding
        node.y = node.y - EventItem.Margin - EventItem.Padding
        return node

    @staticmethod
    def toNoteNode(scenePos: QPointF) -> Node:
        node = Node(scenePos.x(), scenePos.y(), type=GraphicsItemType.NOTE)
        node.x = node.x - NoteItem.Margin
        node.y = node.y - NoteItem.Margin
        return node

    @staticmethod
    def toImageNode(scenePos: QPointF) -> Node:
        node = Node(scenePos.x(), scenePos.y(), type=GraphicsItemType.IMAGE)
        node.x = node.x - ImageItem.Margin
        node.y = node.y - ImageItem.Margin
        return node

    def _removeItems(self):
        macro = len(self.selectedItems()) > 1
        if macro:
            self._undoStack.beginMacro('Remove items')
        for item in self.selectedItems():
            connectors = None
            if isinstance(item, NodeItem):
                connectors = item.connectors()

            self._removeItem(item)
            self._undoStack.push(ItemRemovalCommand(self, item, connectors))
        if macro:
            self._undoStack.endMacro()

    def _removeItem(self, item: QGraphicsItem):
        if isinstance(item, NodeItem):
            for connectorItem in item.connectors():
                try:
                    self._clearUpConnectorItem(connectorItem)
                    self.removeItem(connectorItem)
                except ValueError:
                    pass  # connector might have been already removed if a node was deleted first
            # item.clearConnectors()
            if self._diagram:
                self._diagram.data.nodes.remove(item.node())
        elif isinstance(item, ConnectorItem):
            self._clearUpConnectorItem(item)

        if item.scene():
            self.removeItem(item)
        self._save()

    def _clearUpConnectorItem(self, item: ConnectorItem):
        try:
            self._diagram.data.connectors.remove(item.connector())
            item.source().removeConnector(item)
            item.target().removeConnector(item)
        except ValueError:
            pass

    def _addConnector(self, connector: Connector, source: NodeItem, target: NodeItem):
        sourceSocket = source.socket(connector.source_angle)
        targetSocket = target.socket(connector.target_angle)
        connectorItem = ConnectorItem(sourceSocket, targetSocket)

        sourceSocket.addConnector(connectorItem)
        targetSocket.addConnector(connectorItem)

        self.addItem(connectorItem)
        connectorItem.setConnector(connector)

        self._onLink(source, sourceSocket, target, targetSocket)

    def _copy(self, item: NodeItem):
        self._copyDescriptor = ItemDescriptor(item.node().type, item.node().subtype)

    def _paste(self):
        if self._copyDescriptor:
            pos = self._cursorScenePos()
            if pos:
                self._addNewItem(pos, self._copyDescriptor.mode, self._copyDescriptor.subType)

    def _cursorScenePos(self) -> Optional[QPointF]:
        view = self.views()[0]
        if not view.underMouse():
            return
        viewPos: QPoint = view.mapFromGlobal(QCursor.pos())
        return view.mapToScene(viewPos)

    def _addNewItem(self, scenePos: QPointF, itemType: GraphicsItemType, subType: str = '') -> NodeItem:
        if itemType == GraphicsItemType.CHARACTER:
            item = CharacterItem(PlaceholderCharacter('Character'), self.toCharacterNode(scenePos))
        # elif itemType in [DiagramNodeType.COMMENT, DiagramNodeType.STICKER]:
        #     item = StickerItem(Node(scenePos.x(), scenePos.y(), itemType, subType))
        elif itemType == GraphicsItemType.NOTE:
            item = NoteItem(self.toNoteNode(scenePos))
        elif itemType == GraphicsItemType.ICON:
            item = IconItem(self.toIconNode(scenePos))
        elif itemType == GraphicsItemType.IMAGE:
            item = ImageItem(self.toImageNode(scenePos))
        else:
            item = EventItem(self.toEventNode(scenePos, itemType, subType))

        self.addItem(item)
        anim = qtanim.fade_in(item)
        anim.setParent(self._animParent)
        self.itemAdded.emit(itemType, item)
        self.endAdditionMode()

        self._diagram.data.nodes.append(item.node())
        self._save()

        self._undoStack.push(ItemAdditionCommand(self, item))

        return item

    def _addNode(self, node: Node) -> NodeItem:
        if node.type == GraphicsItemType.CHARACTER:
            character = self._character(node)
            if character is None:
                character = PlaceholderCharacter('Character')
            item = CharacterItem(character, node)
        elif node.type == GraphicsItemType.NOTE:
            item = NoteItem(node)
        elif node.type == GraphicsItemType.ICON:
            item = IconItem(node)
        elif node.type == GraphicsItemType.IMAGE:
            item = ImageItem(node)
        else:
            item = EventItem(node)

        self.addItem(item)
        return item

    @abstractmethod
    def _load(self):
        pass

    @abstractmethod
    def _save(self):
        pass

    @abstractmethod
    def _character(self, node: Node) -> Optional[Character]:
        pass

    def _uploadImage(self) -> Optional[LoadedImage]:
        pass

    def _loadImage(self, node: Node) -> Optional[QImage]:
        pass

    def _onLink(self, sourceNode: NodeItem, sourceSocket: AbstractSocketItem, targetNode: NodeItem,
                targetSocket: AbstractSocketItem):
        if isinstance(sourceNode, CircleShapedNodeItem):
            sourceNode.addSocket(sourceSocket)
        if isinstance(targetNode, CircleShapedNodeItem):
            targetNode.addSocket(targetSocket)

    def _updateSelection(self):
        pass
        # self.clearSelection()
        # items_in_rect = self.items(self._selectionRect.rect(), Qt.ItemSelectionMode.IntersectsItemBoundingRect)
        # for item in items_in_rect:
        #     item.setSelected(True)
