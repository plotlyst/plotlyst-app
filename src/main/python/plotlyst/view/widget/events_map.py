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
from enum import Enum
from typing import Optional, List

from PyQt6.QtCore import QRectF, Qt, QPointF, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QColor, QPainter, QPen, QKeyEvent, QFontMetrics, QResizeEvent, QTransform
from PyQt6.QtWidgets import QGraphicsScene, QWidget, QAbstractGraphicsShapeItem, QGraphicsSceneHoverEvent, \
    QGraphicsSceneMouseEvent, QStyleOptionGraphicsItem, QGraphicsTextItem, QApplication, QGraphicsRectItem
from overrides import overrides
from qthandy import transparent, hbox, vbox, sp, margins, incr_icon
from qtmenu import MenuWidget

from src.main.python.plotlyst.common import PLOTLYST_SECONDARY_COLOR
from src.main.python.plotlyst.core.domain import Novel, Character, CharacterNode, Node
from src.main.python.plotlyst.view.common import tool_btn, shadow, frame, ExclusiveOptionalButtonGroup, \
    TooltipPositionEventFilter
from src.main.python.plotlyst.view.icons import avatars, IconRegistry
from src.main.python.plotlyst.view.widget.characters import CharacterSelectorMenu
from src.main.python.plotlyst.view.widget.graphics import BaseGraphicsView, NodeItem, ConnectorItem
from src.main.python.plotlyst.view.widget.input import AutoAdjustableLineEdit


def draw_rect(painter: QPainter, item: QAbstractGraphicsShapeItem):
    painter.setPen(QPen(Qt.GlobalColor.red, 1, Qt.PenStyle.DashLine))
    painter.drawRoundedRect(item.boundingRect(), 2, 2)


def draw_center(painter: QPainter, item: QAbstractGraphicsShapeItem):
    painter.setPen(QPen(Qt.GlobalColor.red, 1, Qt.PenStyle.DashLine))
    painter.drawEllipse(item.boundingRect().center(), 1, 1)


def draw_zero(painter: QPainter):
    painter.setPen(QPen(Qt.GlobalColor.blue, 1, Qt.PenStyle.DashLine))
    painter.drawEllipse(QPointF(0, 0), 1, 1)


def draw_helpers(painter: QPainter, item: QAbstractGraphicsShapeItem):
    draw_rect(painter, item)
    draw_center(painter, item)
    draw_zero(painter)


class ItemType(Enum):
    Event = 0


class MindMapNode(NodeItem):
    def mindMapScene(self) -> 'EventsMindMapScene':
        return self.scene()

    def linkMode(self) -> bool:
        return self.mindMapScene().linkMode()


class SocketItem(QAbstractGraphicsShapeItem):
    def __init__(self, parent: 'ConnectableNode'):
        super(SocketItem, self).__init__(parent)

        self._size = 16
        self.setAcceptHoverEvents(True)
        self._hovered = False
        self._linkAvailable = True
        self.setToolTip('Connect')

        self._connectors: List[ConnectorItem] = []

    @overrides
    def boundingRect(self):
        return QRectF(0, 0, self._size, self._size)

    @overrides
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = ...) -> None:
        if self._linkAvailable:
            painter.setPen(QPen(QColor(PLOTLYST_SECONDARY_COLOR), 2))
        else:
            painter.setPen(QPen(QColor('lightgrey'), 2))

        radius = 7 if self._hovered else 5
        painter.drawEllipse(QPointF(self._size / 2, self._size // 2), radius, radius)
        if self._hovered and self.mindMapScene().linkMode():
            painter.drawEllipse(QPointF(self._size / 2, self._size // 2), 2, 2)

    @overrides
    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._hovered = True
        if self.mindMapScene().linkMode() and self.mindMapScene().linkSource().parentItem() == self.parentItem():
            self._linkAvailable = False
        else:
            self._linkAvailable = True
        self.setToolTip('Connect' if self._linkAvailable else 'Cannot connect to itself')
        self.update()

    @overrides
    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._hovered = False
        self._linkAvailable = True
        self.setToolTip('Connect')
        self.update()

    @overrides
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        event.accept()

    @overrides
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self.mindMapScene().linkMode():
            if self.mindMapScene().linkSource().parentItem() != self.parentItem():
                self.mindMapScene().link(self)
        else:
            self.mindMapScene().startLink(self)

    def addConnector(self, connector: ConnectorItem):
        self._connectors.append(connector)

    def rearrangeConnectors(self):
        for con in self._connectors:
            con.rearrange()

    def removeConnectors(self):
        for con in self._connectors:
            self.scene().removeItem(con)
        self._connectors.clear()

    def mindMapScene(self) -> 'EventsMindMapScene':
        return self.scene()


class SelectorRectItem(QGraphicsRectItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._startingPoint: QPointF = QPointF(0, 0)
        self._rect = QRectF()

        self.setPen(QPen(Qt.GlobalColor.gray, 1, Qt.PenStyle.DashLine))

    def start(self, pos: QPointF):
        self._startingPoint = pos
        self._rect.setTopLeft(pos)
        self.setRect(self._rect)

    def adjust(self, pos: QPointF):
        x1 = min(self._startingPoint.x(), pos.x())
        y1 = min(self._startingPoint.y(), pos.y())
        x2 = max(self._startingPoint.x(), pos.x())
        y2 = max(self._startingPoint.y(), pos.y())

        self._rect.setTopLeft(QPointF(x1, y1))
        self._rect.setBottomRight(QPointF(x2, y2))

        self.setRect(self._rect)


class PlaceholderItem(SocketItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEnabled(False)
        self.setAcceptHoverEvents(False)
        self.setToolTip('Click to add a new node')


class ConnectableNode(MindMapNode):
    def __init__(self, node: Node, parent=None):
        super().__init__(node, parent)
        self._sockets: List[SocketItem] = []

    def removeConnectors(self):
        for socket in self._sockets:
            socket.removeConnectors()

    @overrides
    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if self.linkMode() or event.modifiers() & Qt.KeyboardModifier.AltModifier:
            self._setSocketsVisible()

    @overrides
    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if not self.isSelected():
            self._setSocketsVisible(False)

    @overrides
    def _onPosChanged(self):
        for socket in self._sockets:
            socket.rearrangeConnectors()

    @overrides
    def _onSelection(self, selected: bool):
        self._setSocketsVisible(selected)

    def _setSocketsVisible(self, visible: bool = True):
        for socket in self._sockets:
            socket.setVisible(visible)


class EventItem(ConnectableNode):
    Margin: int = 30
    Padding: int = 20

    def __init__(self, node: Node, parent=None):
        super().__init__(node, parent)
        self._text: str = 'New event'
        self.setPos(node.x, node.y)

        self._metrics = QFontMetrics(QApplication.font())
        self._textRect: QRect = QRect(0, 0, 1, 1)
        self._width = 1
        self._height = 1
        self._nestedRectWidth = 1
        self._nestedRectHeight = 1

        self._socketLeft = SocketItem(self)
        self._socketTopLeft = SocketItem(self)
        self._socketTopCenter = SocketItem(self)
        self._socketTopRight = SocketItem(self)
        self._socketRight = SocketItem(self)
        self._socketBottomLeft = SocketItem(self)
        self._socketBottomCenter = SocketItem(self)
        self._socketBottomRight = SocketItem(self)
        self._sockets.extend([self._socketLeft,
                              self._socketTopLeft, self._socketTopCenter, self._socketTopRight,
                              self._socketRight,
                              self._socketBottomRight, self._socketBottomCenter, self._socketBottomLeft])
        self._setSocketsVisible(False)

        self._recalculateRect()

    def text(self) -> str:
        return self._text

    def setText(self, text: str):
        self._text = text
        self._recalculateRect()
        self.prepareGeometryChange()
        self.setSelected(False)
        self.update()

    def textRect(self) -> QRect:
        return self._textRect

    def textSceneRect(self) -> QRectF:
        return self.mapRectToScene(self._textRect.toRectF())

    @overrides
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.gray, 2, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(self.Margin, self.Margin, self._nestedRectWidth, self._nestedRectHeight, 2, 2)

        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawText(self._textRect, Qt.AlignmentFlag.AlignCenter, self._text)
        painter.drawRoundedRect(self.Margin, self.Margin, self._nestedRectWidth, self._nestedRectHeight, 24, 24)

    @overrides
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.mindMapScene().editEventText(self)

    def _recalculateRect(self):
        self._textRect = self._metrics.boundingRect(self._text)
        self._textRect.moveTopLeft(QPoint(self.Margin + self.Padding, self.Margin + self.Padding))
        self._width = self._textRect.width() + self.Margin * 2 + self.Padding * 2
        self._height = self._textRect.height() + self.Margin * 2 + self.Padding * 2

        self._nestedRectWidth = self._textRect.width() + self.Padding * 2
        self._nestedRectHeight = self._textRect.height() + self.Padding * 2

        socketWidth = self._socketLeft.boundingRect().width()
        socketRad = socketWidth / 2
        socketPadding = (self.Margin - socketWidth) / 2
        self._socketTopCenter.setPos(self._width / 2 - socketRad, socketPadding)
        self._socketTopLeft.setPos(self._nestedRectWidth / 3 - socketRad, socketPadding)
        self._socketTopRight.setPos(self._nestedRectWidth, socketPadding)
        self._socketRight.setPos(self._width - self.Margin + socketPadding, self._height / 2 - socketRad)
        self._socketBottomCenter.setPos(self._width / 2 - socketRad, self._height - self.Margin + socketPadding)
        self._socketBottomLeft.setPos(self._nestedRectWidth / 3 - socketRad,
                                      self._height - self.Margin + socketPadding)
        self._socketBottomRight.setPos(self._nestedRectWidth, self._height - self.Margin + socketPadding)
        self._socketLeft.setPos(socketPadding, self._height / 2 - socketRad)


class CharacterItem(ConnectableNode):
    Margin: int = 25

    def __init__(self, node: Node, character: Optional[Character], parent=None):
        super().__init__(node, parent)
        self._character: Optional[Character] = character
        self.setPos(node.x, node.y)
        self._size: int = 68

        self._socketTop = SocketItem(self)
        self._socketRight = SocketItem(self)
        self._socketBottom = SocketItem(self)
        self._socketLeft = SocketItem(self)
        self._sockets.extend([self._socketLeft, self._socketTop, self._socketRight, self._socketBottom])
        socketWidth = self._socketTop.boundingRect().width()
        half = self.Margin + (self._size - socketWidth) / 2
        padding = (self.Margin - socketWidth) / 2
        self._socketTop.setPos(half, padding)
        self._socketRight.setPos(self._size + self.Margin + padding, half)
        self._socketBottom.setPos(half, self._size + self.Margin + padding)
        self._socketLeft.setPos(padding, half)

        self._setSocketsVisible(False)

    @overrides
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._size + self.Margin * 2, self._size + self.Margin * 2)

    def setCharacter(self, character: Character):
        self._character = character
        self.update()

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.gray, 2, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(self.Margin, self.Margin, self._size, self._size, 2, 2)

        if self._character is None:
            avatar = IconRegistry.character_icon()
        else:
            avatar = avatars.avatar(self._character)
        avatar.paint(painter, self.Margin, self.Margin, self._size, self._size)


class TextLineEditorPopup(MenuWidget):

    def __init__(self, text: str, rect: QRect, parent=None):
        super().__init__(parent)
        transparent(self)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._lineEdit = AutoAdjustableLineEdit(defaultWidth=rect.width())
        self._lineEdit.setText(text)
        self.addWidget(self._lineEdit)

        self._lineEdit.editingFinished.connect(self.hide)

    @overrides
    def showEvent(self, QShowEvent):
        self._lineEdit.setFocus()

    def text(self) -> str:
        return self._lineEdit.text()


class AdditionMode(Enum):
    NONE = 0
    EVENT = 1
    CHARACTER = 2


class EventsMindMapScene(QGraphicsScene):
    cancelItemAddition = pyqtSignal()
    itemAdded = pyqtSignal()
    characterAdded = pyqtSignal(CharacterItem)
    editEvent = pyqtSignal(EventItem)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._linkMode: bool = False
        self._additionMode: AdditionMode = AdditionMode.NONE

        self._selectionMode = False
        self._selectionRect = SelectorRectItem()
        self.addItem(self._selectionRect)
        self._selectionRect.setVisible(False)

        self._placeholder: Optional[PlaceholderItem] = None
        self._connectorPlaceholder: Optional[ConnectorItem] = None

        if novel.characters:
            characterItem = CharacterItem(CharacterNode(50, 50), novel.characters[0])

            self.addItem(characterItem)
        eventItem = EventItem(Node(400, 100))
        self.addItem(eventItem)

    def linkMode(self) -> bool:
        return self._linkMode

    def linkSource(self) -> Optional[SocketItem]:
        if self._connectorPlaceholder is not None:
            return self._connectorPlaceholder.source()

    def startLink(self, source: SocketItem):
        self._linkMode = True
        self._placeholder = PlaceholderItem()
        self._placeholder.setVisible(False)
        self._placeholder.setEnabled(False)
        self.addItem(self._placeholder)
        self._connectorPlaceholder = ConnectorItem(source, self._placeholder)
        self.addItem(self._connectorPlaceholder)

        self._placeholder.setPos(source.scenePos())
        self._connectorPlaceholder.rearrange()

    def endLink(self):
        self._linkMode = False
        self.removeItem(self._connectorPlaceholder)
        self.removeItem(self._placeholder)
        self._connectorPlaceholder = None
        self._placeholder = None

    def link(self, target: SocketItem):
        connector = ConnectorItem(self._connectorPlaceholder.source(), target)
        self._connectorPlaceholder.source().addConnector(connector)
        target.addConnector(connector)
        self.addItem(connector)
        self.endLink()

    def editEventText(self, item: EventItem):
        self.editEvent.emit(item)

    def addNewItem(self, pos: QPointF, itemType: ItemType):
        if itemType == ItemType.Event:
            item = QGraphicsTextItem('Type')
        else:
            return

        item.setPos(pos)
        connector = ConnectorItem(self._connectorPlaceholder.source(), item)
        self.addItem(item)
        self.addItem(connector)

        self.endLink()

    def isAdditionMode(self) -> bool:
        return self._additionMode != AdditionMode.NONE

    def startAdditionMode(self, mode: AdditionMode):
        self._additionMode = mode

    def endAdditionMode(self):
        self._additionMode = AdditionMode.NONE

    @overrides
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            if self.linkMode():
                self.endLink()
            elif self.isAdditionMode():
                self.cancelItemAddition.emit()
            else:
                self.clearSelection()
        elif event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            for item in self.selectedItems():
                if isinstance(item, ConnectableNode):
                    item.removeConnectors()
                self.removeItem(item)
        elif not event.modifiers() and len(self.selectedItems()) == 1:
            item = self.selectedItems()[0]
            if isinstance(item, EventItem):
                self.editEvent.emit(item)

    @overrides
    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if not self.isAdditionMode() and event.button() & Qt.MouseButton.LeftButton and not self.itemAt(
                event.scenePos(), QTransform()):
            self._selectionRect.start(event.scenePos())
            self._selectionMode = True
        elif event.button() & Qt.MouseButton.RightButton or event.button() & Qt.MouseButton.MiddleButton:
            return
        super().mousePressEvent(event)

    @overrides
    def mouseMoveEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if self.linkMode():
            self._placeholder.setPos(event.scenePos())
            self._connectorPlaceholder.rearrange()
        elif self._selectionMode:
            self._selectionRect.adjust(event.scenePos())
            self._selectionRect.setVisible(True)
            self._updateSelection()
        super().mouseMoveEvent(event)

    @overrides
    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if self.linkMode():
            if event.button() & Qt.MouseButton.RightButton:
                self.endLink()
        elif self.isAdditionMode() and event.button() & Qt.MouseButton.RightButton:
            self.cancelItemAddition.emit()
        elif self._selectionMode and event.button() & Qt.MouseButton.LeftButton:
            self._selectionMode = False
            self._selectionRect.setVisible(False)
            self._updateSelection()
        elif self._additionMode == AdditionMode.EVENT:
            self._addNewEvent(event.scenePos())
        elif self._additionMode == AdditionMode.CHARACTER:
            self._addNewCharacter(event.scenePos())

        super().mouseReleaseEvent(event)

    def _addNewEvent(self, scenePos: QPointF):
        item = EventItem(self.toEventNode(scenePos))
        self.addItem(item)
        self.itemAdded.emit()

    def _addNewCharacter(self, scenePos: QPointF):
        item = CharacterItem(self.toCharacterNode(scenePos), character=None)
        self.addItem(item)
        self.characterAdded.emit(item)

    def _updateSelection(self):
        if not self._selectionRect.rect().isValid():
            return
        self.clearSelection()
        items_in_rect = self.items(self._selectionRect.rect(), Qt.ItemSelectionMode.IntersectsItemBoundingRect)
        for item in items_in_rect:
            item.setSelected(True)

    @staticmethod
    def toEventNode(scenePos: QPointF) -> Node:
        node = Node(scenePos.x(), scenePos.y())
        node.x = node.x - EventItem.Margin - EventItem.Padding
        node.y = node.y - EventItem.Margin - EventItem.Padding
        return node

    @staticmethod
    def toCharacterNode(scenePos: QPointF) -> Node:
        node = Node(scenePos.x(), scenePos.y())
        node.x = node.x - CharacterItem.Margin
        node.y = node.y - CharacterItem.Margin
        return node


class EventsMindMapView(BaseGraphicsView):

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._scene = EventsMindMapScene(self._novel)
        self.setScene(self._scene)
        self.setBackgroundBrush(QColor('#e9ecef'))

        self._scene.itemAdded.connect(self._endAddition)
        self._scene.characterAdded.connect(self._endCharacterAddition)
        self._scene.cancelItemAddition.connect(self._endAddition)
        self._scene.editEvent.connect(self._editEvent)

        self._controlsNavBar = frame(self)
        self._controlsNavBar.setProperty('relaxed-white-bg', True)
        self._controlsNavBar.setProperty('rounded', True)
        sp(self._controlsNavBar).h_max()
        shadow(self._controlsNavBar)

        self._btnAddEvent = tool_btn(
            IconRegistry.from_name('mdi.calendar-plus'), 'Add new event', True,
            icon_resize=False, properties=['transparent-rounded-bg-on-hover', 'top-selector'],
            parent=self._controlsNavBar)
        self._btnAddCharacter = tool_btn(
            IconRegistry.character_icon('#040406'), 'Add new character', True,
            icon_resize=False, properties=['transparent-rounded-bg-on-hover', 'top-selector'],
            parent=self._controlsNavBar)
        self._btnGroup = ExclusiveOptionalButtonGroup()
        self._btnGroup.addButton(self._btnAddEvent)
        self._btnGroup.addButton(self._btnAddCharacter)
        for btn in self._btnGroup.buttons():
            btn.installEventFilter(TooltipPositionEventFilter(btn))
            incr_icon(btn, 2)
        self._btnGroup.buttonClicked.connect(self._startAddition)
        vbox(self._controlsNavBar, 5, 6)
        self._controlsNavBar.layout().addWidget(self._btnAddEvent)
        self._controlsNavBar.layout().addWidget(self._btnAddCharacter)

        self._wdgZoomBar = frame(self)
        self._wdgZoomBar.setProperty('relaxed-white-bg', True)
        self._wdgZoomBar.setProperty('rounded', True)
        shadow(self._wdgZoomBar)
        hbox(self._wdgZoomBar, 2, spacing=6)
        margins(self._wdgZoomBar, left=10, right=10)

        self._btnZoomIn = tool_btn(IconRegistry.plus_circle_icon('lightgrey'), 'Zoom in', transparent_=True,
                                   parent=self._wdgZoomBar)
        self._btnZoomOut = tool_btn(IconRegistry.minus_icon('lightgrey'), 'Zoom out', transparent_=True,
                                    parent=self._wdgZoomBar)
        self._btnZoomIn.clicked.connect(lambda: self.scale(1.1, 1.1))
        self._btnZoomOut.clicked.connect(lambda: self.scale(0.9, 0.9))

        self._wdgZoomBar.layout().addWidget(self._btnZoomOut)
        self._wdgZoomBar.layout().addWidget(self._btnZoomIn)
        self.__arrangeSideBars()

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        super(EventsMindMapView, self).resizeEvent(event)
        self.__arrangeSideBars()

    # def _displayNewNodeMenu(self, placeholder: PlaceholderItem):
    #     menu = MenuWidget(self)
    #     menu.addAction(
    #         action('Event',
    #                slot=lambda: self._scene.addNewItem(placeholder.sceneBoundingRect().center(), ItemType.Event)))
    #
    #     view_pos = self.mapFromScene(placeholder.sceneBoundingRect().center())
    #     menu.exec(self.mapToGlobal(view_pos))

    def _editEvent(self, item: EventItem):
        def setText(text: str):
            item.setText(text)

        popup = TextLineEditorPopup(item.text(), item.textRect(), parent=self)
        view_pos = self.mapFromScene(item.textSceneRect().topLeft())
        popup.exec(self.mapToGlobal(view_pos))

        popup.aboutToHide.connect(lambda: setText(popup.text()))

    def _startAddition(self):
        if self._btnAddEvent.isChecked():
            self._scene.startAdditionMode(AdditionMode.EVENT)
        elif self._btnAddCharacter.isChecked():
            self._scene.startAdditionMode(AdditionMode.CHARACTER)

        if not QApplication.overrideCursor():
            QApplication.setOverrideCursor(Qt.CursorShape.PointingHandCursor)

    def _endAddition(self):
        btn = self._btnGroup.checkedButton()
        if btn:
            btn.setChecked(False)
        QApplication.restoreOverrideCursor()
        self._scene.endAdditionMode()

    def _endCharacterAddition(self, item: CharacterItem):
        def select(character: Character):
            item.setCharacter(character)

        self._endAddition()
        popup = CharacterSelectorMenu(self._novel, parent=self)
        popup.selected.connect(select)
        view_pos = self.mapFromScene(item.sceneBoundingRect().topRight())
        popup.exec(self.mapToGlobal(view_pos))

    def __arrangeSideBars(self):
        self._wdgZoomBar.setGeometry(10, self.height() - self._wdgZoomBar.sizeHint().height() - 10,
                                     self._wdgZoomBar.sizeHint().width(),
                                     self._wdgZoomBar.sizeHint().height())
        self._controlsNavBar.setGeometry(10, 100, self._controlsNavBar.sizeHint().width(),
                                         self._controlsNavBar.sizeHint().height())
