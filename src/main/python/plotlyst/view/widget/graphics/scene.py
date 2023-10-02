"""
Plotlyst
Copyright (C) 2021-2023  Zsolt Kovari

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
from typing import Optional, Dict

from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QPoint
from PyQt6.QtGui import QTransform, \
    QKeyEvent, QKeySequence, QCursor
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsSceneMouseEvent, QApplication
from overrides import overrides

from src.main.python.plotlyst.core.domain import Node, Diagram, DiagramNodeType, Connector, PlaceholderCharacter, \
    Character, to_node
from src.main.python.plotlyst.view.widget.graphics import NodeItem, CharacterItem, PlaceholderSocketItem, ConnectorItem, \
    AbstractSocketItem, EventItem


@dataclass
class ItemDescriptor:
    mode: DiagramNodeType
    subType: str = ''


class NetworkScene(QGraphicsScene):
    cancelItemAddition = pyqtSignal()
    itemAdded = pyqtSignal(DiagramNodeType, NodeItem)
    editItem = pyqtSignal(NodeItem)
    hideItemEditor = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._diagram: Optional[Diagram] = None
        self._linkMode: bool = False
        self._additionDescriptor: Optional[ItemDescriptor] = None
        self._copyDescriptor: Optional[ItemDescriptor] = None

        self._placeholder: Optional[PlaceholderSocketItem] = None
        self._connectorPlaceholder: Optional[ConnectorItem] = None

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

    def startAdditionMode(self, itemType: DiagramNodeType, subType: str = ''):
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
            pen=connectorItem.penStyle(), width=connectorItem.penWidth(), color=connectorItem.color().name()
        )
        if connectorItem.icon():
            connector.icon = connectorItem.icon()
        connectorItem.setConnector(connector)
        self._diagram.data.connectors.append(connector)
        self._save()

        self.addItem(connectorItem)
        self.endLink()

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
            for item in self.selectedItems():
                self._removeItem(item)
        elif event.matches(QKeySequence.StandardKey.Copy) and len(self.selectedItems()) == 1:
            self._copy(self.selectedItems()[0])
        elif event.matches(QKeySequence.StandardKey.Paste):
            self._paste()

    @overrides
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if (not self.isAdditionMode() and not self.linkMode() and
                event.button() & Qt.MouseButton.LeftButton and not self.itemAt(event.scenePos(), QTransform())):
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                pos = self._cursorScenePos()
                if pos:
                    self._addNewItem(pos, DiagramNodeType.EVENT)
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
        if self.linkMode():
            if event.button() & Qt.MouseButton.RightButton:
                self.endLink()
        elif self.isAdditionMode() and event.button() & Qt.MouseButton.RightButton:
            self.cancelItemAddition.emit()
            self.endAdditionMode()
        elif self._additionDescriptor is not None:
            self._addNewItem(event.scenePos(), self._additionDescriptor.mode, self._additionDescriptor.subType)

        super().mouseReleaseEvent(event)

    def itemChangedEvent(self, item: NodeItem):
        pass

    def nodeChangedEvent(self, node: Node):
        self._save()

    def connectorChangedEvent(self, connector: ConnectorItem):
        self._save()

    @staticmethod
    def toCharacterNode(scenePos: QPointF) -> Node:
        node = Node(scenePos.x(), scenePos.y(), type=DiagramNodeType.CHARACTER)
        node.x = node.x - CharacterItem.Margin
        node.y = node.y - CharacterItem.Margin
        return node

    @staticmethod
    def toEventNode(scenePos: QPointF, itemType: DiagramNodeType, subType: str = '') -> Node:
        node: Node = to_node(scenePos.x(), scenePos.y(), itemType, subType,
                             default_size=QApplication.font().pointSize())
        node.x = node.x - EventItem.Margin - EventItem.Padding
        node.y = node.y - EventItem.Margin - EventItem.Padding
        return node

    def _removeItem(self, item: QGraphicsItem):
        if isinstance(item, NodeItem):
            for connectorItem in item.connectors():
                try:
                    self._clearUpConnectorItem(connectorItem)
                    self.removeItem(connectorItem)
                except ValueError:
                    pass  # connector might have been already removed if a node was deleted first
            item.clearConnectors()
            self._diagram.data.nodes.remove(item.node())
        elif isinstance(item, ConnectorItem):
            self._clearUpConnectorItem(item)

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

    def _addNewItem(self, scenePos: QPointF, itemType: DiagramNodeType, subType: str = '') -> NodeItem:
        if itemType == DiagramNodeType.CHARACTER:
            item = CharacterItem(PlaceholderCharacter('Character'), self.toCharacterNode(scenePos))
        # elif itemType in [DiagramNodeType.COMMENT, DiagramNodeType.STICKER]:
        #     item = StickerItem(Node(scenePos.x(), scenePos.y(), itemType, subType))
        else:
            item = EventItem(self.toEventNode(scenePos, itemType, subType))

        self.addItem(item)
        self.itemAdded.emit(itemType, item)
        self.endAdditionMode()

        self._diagram.data.nodes.append(item.node())
        self._save()

        return item

    def _addNode(self, node: Node) -> NodeItem:
        if node.type == DiagramNodeType.CHARACTER:
            character = self._character(node)
            if character is None:
                character = PlaceholderCharacter('Character')
            item = CharacterItem(character, node)
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

    def _onLink(self, sourceNode: NodeItem, sourceSocket: AbstractSocketItem, targetNode: NodeItem,
                targetSocket: AbstractSocketItem):
        if isinstance(sourceNode, CharacterItem):
            sourceNode.addSocket(sourceSocket)
        if isinstance(targetNode, CharacterItem):
            targetNode.addSocket(targetSocket)

    def _updateSelection(self):
        pass
        # self.clearSelection()
        # items_in_rect = self.items(self._selectionRect.rect(), Qt.ItemSelectionMode.IntersectsItemBoundingRect)
        # for item in items_in_rect:
        #     item.setSelected(True)