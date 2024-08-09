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

import math
from abc import abstractmethod
from enum import Enum
from typing import Any, Optional, List

from PyQt6.QtCore import Qt, QRectF, QPointF, QPoint, QRect
from PyQt6.QtGui import QPainter, QPen, QPainterPath, QColor, QIcon, QPolygonF, QBrush, QFontMetrics, QImage, QFont, \
    QTextDocument, QUndoStack
from PyQt6.QtWidgets import QAbstractGraphicsShapeItem, QGraphicsItem, QGraphicsPathItem, QGraphicsSceneMouseEvent, \
    QStyleOptionGraphicsItem, QWidget, \
    QGraphicsSceneHoverEvent, QGraphicsPolygonItem, QApplication, QGraphicsOpacityEffect, QGraphicsTextItem
from overrides import overrides
from qthandy import pointy

from plotlyst.common import RELAXED_WHITE_COLOR, PLOTLYST_SECONDARY_COLOR, PLOTLYST_TERTIARY_COLOR, \
    WHITE_COLOR
from plotlyst.core.domain import Node, Relation, Connector, Character, GraphicsItemType, to_node
from plotlyst.env import app_env
from plotlyst.service.image import LoadedImage
from plotlyst.view.common import shadow, calculate_resized_dimensions, text_color_with_bg_qcolor
from plotlyst.view.icons import IconRegistry, avatars
from plotlyst.view.widget.graphics.commands import PosChangedCommand, ResizeItemCommand


def v_center(ref_height: int, item_height: int) -> int:
    return (ref_height - item_height) // 2


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


def alt_modifier(event: QGraphicsSceneHoverEvent) -> bool:
    return event.modifiers() & Qt.KeyboardModifier.AltModifier


class ResizeIconItem(QAbstractGraphicsShapeItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._size: int = 32
        self._ratio: float = 1
        self._keepAspectRatio = False
        self._icon = IconRegistry.from_name('mdi.resize-bottom-right', 'grey')
        self._activated = False
        self._posCommandEnabled = True
        self._previousPos: Optional[QPointF] = None
        self.setAcceptHoverEvents(True)

        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

    def networkScene(self) -> 'NetworkScene':
        return self.scene()

    def setRatio(self, ratio: float):
        self._ratio = ratio

    def setKeepAspectRatio(self, keep: bool):
        self._keepAspectRatio = keep

    @overrides
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._size, self._size)

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        self._icon.paint(painter, 3, 3, self._size - 5, self._size - 5)

    @overrides
    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self.parentItem().setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)

    @overrides
    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self.parentItem().setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

    def posCommandEnabled(self) -> bool:
        return self._posCommandEnabled

    def setPosCommandEnabled(self, enabled: bool):
        self._posCommandEnabled = enabled

    @overrides
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self._activated:
            if self._keepAspectRatio:
                value.setY(value.x() / self._ratio)
                self.setPos(value)

            self.networkScene().itemResizedEvent(self)
            self.parentItem().rearrangeSize(value)
        return super().itemChange(change, value)

    def updatePos(self):
        if self._posCommandEnabled:
            stack: QUndoStack = self.networkScene().undoStack()
            stack.push(ResizeItemCommand(self, self._previousPos, self.pos()))

        self._previousPos = self.pos()

    def activate(self):
        self._activated = True
        if self._previousPos is None:
            self._previousPos = self.pos()

    def deactivate(self):
        self._activated = False


class LabelItem(QAbstractGraphicsShapeItem):
    Margin: int = 0
    Padding: int = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text: str = ''
        self._color: QColor = QColor('black')
        self._font = QApplication.font()
        self._font.setPointSize(self._font.pointSize() - 1)
        self._font.setFamily(app_env.serif_font())
        self._metrics = QFontMetrics(self._font)
        self._textRect: QRect = QRect(0, 0, 1, 1)
        self._width = 1
        self._height = 1
        self._nestedRectWidth = 1
        self._nestedRectHeight = 1
        self._recalculateRect()

    def text(self) -> str:
        return self._text

    def setText(self, text: str):
        self._text = text
        self._refresh()

    def setColor(self, color: QColor):
        self._color = color
        self.update()

    @overrides
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        painter.setPen(QPen(self._color, 1))
        painter.setBrush(self._color)
        painter.drawRoundedRect(self.Margin, self.Margin, self._nestedRectWidth, self._nestedRectHeight, 6, 6)
        painter.setFont(self._font)
        text_color = text_color_with_bg_qcolor(self._color)
        painter.setPen(QPen(QColor(text_color), 1))
        painter.drawText(self._textRect, Qt.AlignmentFlag.AlignCenter, self._text)

    @overrides
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        event.accept()

    @overrides
    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseReleaseEvent(event)
        self.parentItem().setSelected(True)

    def _refresh(self):
        self._recalculateRect()
        self.prepareGeometryChange()
        self.update()

    def _recalculateRect(self):
        self._textRect = self._metrics.boundingRect(self._text)
        self._textRect.moveTopLeft(QPoint(self.Margin + self.Padding, self.Margin + self.Padding))
        self._textRect.moveTopLeft(QPoint(self._textRect.x(), self._textRect.y()))
        self._width = self._textRect.width() + self.Margin * 2 + self.Padding * 2
        self._height = self._textRect.height() + self.Margin * 2 + self.Padding * 2
        self._nestedRectWidth = self._textRect.width() + self.Padding * 2
        self._nestedRectHeight = self._textRect.height() + self.Padding * 2


class IconBadge(QAbstractGraphicsShapeItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._size: int = 32
        self._icon: Optional[QIcon] = None
        self._color: QColor = QColor('black')

    def setIcon(self, icon: QIcon, borderColor: Optional[QColor] = None):
        self._icon = icon
        if borderColor:
            self._color = borderColor
        self.update()

    @overrides
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._size, self._size)

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        painter.setPen(QPen(self._color, 2))
        painter.setBrush(QColor(RELAXED_WHITE_COLOR))
        painter.drawEllipse(0, 0, self._size, self._size)

        if self._icon:
            self._icon.paint(painter, 3, 3, self._size - 5, self._size - 5)

    @overrides
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        event.accept()

    @overrides
    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        super().mouseReleaseEvent(event)
        self.parentItem().setSelected(True)


class AbstractSocketItem(QAbstractGraphicsShapeItem):
    def __init__(self, angle: float, size: int = 16, parent=None):
        super().__init__(parent)
        self._size = size
        self._angle: float = angle
        self._hovered = False
        self._linkAvailable = True

        self.setToolTip('Connect')
        self.setAcceptHoverEvents(True)

        self._connectors: List[ConnectorItem] = []

    def angle(self) -> float:
        return self._angle

    def setAngle(self, angle: float):
        self._angle = angle

    @overrides
    def boundingRect(self):
        return QRectF(0, 0, self._size, self._size)

    @overrides
    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._hovered = True
        if self.networkScene().linkMode() and self.networkScene().linkSource().parentItem() == self.parentItem():
            self._linkAvailable = False
        else:
            self._linkAvailable = True
        self.setToolTip('Connect' if self._linkAvailable else 'Cannot connect to itself')
        self.prepareGeometryChange()
        self.update()

        for connector in self._connectors:
            connector.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

    @overrides
    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._hovered = False
        self._linkAvailable = True
        self.setToolTip('Connect')
        self.prepareGeometryChange()
        self.update()

        for connector in self._connectors:
            connector.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

    @overrides
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        event.accept()

    @overrides
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self.networkScene().linkMode():
            if self.networkScene().linkSource().parentItem() != self.parentItem():
                self.networkScene().link(self)
        else:
            self.networkScene().startLink(self)

    def connectors(self) -> List['ConnectorItem']:
        return self._connectors

    def addConnector(self, connector: 'ConnectorItem'):
        self._connectors.append(connector)

    def rearrangeConnectors(self):
        for con in self._connectors:
            con.rearrange()

    def parentColorChangedEvent(self, node: 'NodeItem'):
        for connector in self._connectors:
            connector.colorChangedEvent(node)

    def removeConnectors(self):
        self._connectors.clear()

    def removeConnector(self, connector: 'ConnectorItem'):
        self._connectors.remove(connector)

    def networkScene(self) -> 'NetworkScene':
        return self.scene()


class FilledSocketItem(AbstractSocketItem):
    Size: int = 20

    def __init__(self, angle: float, parent=None):
        super().__init__(angle, self.Size, parent)
        pointy(self)

    @overrides
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = ...) -> None:
        color = PLOTLYST_SECONDARY_COLOR if self._hovered else PLOTLYST_TERTIARY_COLOR
        painter.setPen(QPen(QColor(color), 1))
        painter.setBrush(QColor(color))

        radius = self.Size // 2
        painter.drawEllipse(QPointF(self.Size / 2, self.Size // 2), radius, radius)


class DotCircleSocketItem(AbstractSocketItem):

    @overrides
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = ...) -> None:
        if self._linkAvailable:
            painter.setPen(QPen(QColor(PLOTLYST_SECONDARY_COLOR), 2))
        else:
            painter.setPen(QPen(QColor('lightgrey'), 2))

        radius = 7 if self._hovered else 5
        painter.drawEllipse(QPointF(self._size / 2, self._size // 2), radius, radius)
        if self._hovered and self.networkScene().linkMode():
            painter.drawEllipse(QPointF(self._size / 2, self._size // 2), 2, 2)


class PlaceholderSocketItem(AbstractSocketItem):
    def __init__(self, parent=None):
        super().__init__(0, parent=parent)
        self.setEnabled(False)
        self.setAcceptHoverEvents(False)

    @overrides
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = ...) -> None:
        pass


class ConnectorType(Enum):
    Linear = 0
    Curved = 1


class ConnectorCPSocket(QAbstractGraphicsShapeItem):
    def __init__(self, size: int = 16, parent=None):
        super().__init__(parent)
        self._size = size
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self._color = QColor('black')

    def setColor(self, color: QColor):
        self._color = color
        self.update()

    @overrides
    def boundingRect(self):
        return QRectF(0, 0, self._size, self._size)

    @overrides
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = ...) -> None:
        painter.setPen(QPen(self._color, 2))
        radius = 5
        painter.drawEllipse(QPointF(self._size / 2, self._size // 2), radius, radius)

    @overrides
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.parentItem().rearrangeCP(value)
        return super().itemChange(change, value)


class ConnectorItem(QGraphicsPathItem):

    def __init__(self, source: AbstractSocketItem, target: AbstractSocketItem,
                 pen: Optional[QPen] = None):
        super(ConnectorItem, self).__init__()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self._source = source
        self._target = target
        self._connector: Optional[Connector] = None
        self._color: QColor = QColor('black')
        self._relation: Optional[Relation] = None
        self._icon: Optional[str] = None
        self._defaultLineType: ConnectorType = ConnectorType.Curved
        self._cp = ConnectorCPSocket(parent=self)
        self._cp.setVisible(False)
        if pen:
            self.setPen(pen)
        else:
            self.setPen(QPen(self._color, 2))

        self._arrowhead = QPolygonF([
            QPointF(0, -5),
            QPointF(10, 0),
            QPointF(0, 5),
        ])
        self._endArrowheadItem = QGraphicsPolygonItem(self._arrowhead, self)
        self._endArrowheadItem.setPen(QPen(self._color, 1))
        self._endArrowheadItem.setBrush(self._color)
        self._startArrowheadItem = QGraphicsPolygonItem(self._arrowhead, self)
        self._startArrowheadItem.setPen(QPen(self._color, 1))
        self._startArrowheadItem.setBrush(self._color)
        self._startArrowheadItem.setVisible(False)

        self._iconBadge = IconBadge(self)
        self._iconBadge.setVisible(False)

        self._label = LabelItem(self)
        self._label.setVisible(False)

        self.rearrange()

    def networkScene(self) -> 'NetworkScene':
        return self.scene()

    def source(self) -> AbstractSocketItem:
        return self._source

    def target(self) -> AbstractSocketItem:
        return self._target

    def connector(self) -> Optional[Connector]:
        return self._connector

    def setConnector(self, connector: Connector):
        self._connector = None
        self.setPenStyle(connector.pen)
        self.setSize(connector.width)
        self.setStartArrowEnabled(connector.start_arrow_enabled)
        self.setEndArrowEnabled(connector.end_arrow_enabled)
        if connector.color:
            color = connector.color
        elif isinstance(self._target.parentItem(), NodeItem):
            node: Node = self._target.parentItem().node()
            color = node.color
        else:
            color = 'black'
        self._label.setText(connector.text)

        self.setColor(QColor(color))
        if connector.icon:
            self.setIcon(connector.icon)
        if connector.cp_x is not None:
            self._cp.setPos(connector.cp_x, connector.cp_y)
        self._connector = connector
        self.rearrange()

    def penStyle(self) -> Qt.PenStyle:
        return self.pen().style()

    def setPenStyle(self, penStyle: Qt.PenStyle):
        pen = self.pen()
        pen.setStyle(penStyle)
        self.setPen(pen)
        self.update()
        if self._connector:
            self._connector.pen = penStyle
            self.networkScene().connectorChangedEvent(self)

    def text(self) -> str:
        if self._connector:
            return self._connector.text if self._connector.text else self._connector.type

        return ''

    def setText(self, text: str):
        self._connector.text = text
        self._label.setText(text)
        self.rearrange()
        self.networkScene().connectorChangedEvent(self)

    def size(self) -> int:
        return self.pen().width()

    def setSize(self, width: int):
        pen = self.pen()
        pen.setWidth(width)
        self.setPen(pen)

        arrowPen = self._endArrowheadItem.pen()
        prevWidth = arrowPen.width()
        self._endArrowheadItem.setScale(1.0 + (width - prevWidth) / 10)
        self._startArrowheadItem.setScale(1.0 + (width - prevWidth) / 10)

        self.rearrange()
        if self._connector:
            self._connector.width = width
            self.networkScene().connectorChangedEvent(self)

    def startArrowEnabled(self) -> bool:
        if self._connector:
            return self._connector.start_arrow_enabled
        return False

    def setStartArrowEnabled(self, enabled: bool):
        self._startArrowheadItem.setVisible(enabled)
        if self._connector:
            self._connector.start_arrow_enabled = enabled
            self.networkScene().connectorChangedEvent(self)

    def endArrowEnabled(self) -> bool:
        if self._connector:
            return self._connector.end_arrow_enabled
        return False

    def setEndArrowEnabled(self, enabled: bool):
        self._endArrowheadItem.setVisible(enabled)
        if self._connector:
            self._connector.end_arrow_enabled = enabled
            self.networkScene().connectorChangedEvent(self)

    def relation(self) -> Optional[Relation]:
        return self._relation

    def setRelation(self, relation: Relation):
        self._icon = relation.icon

        self._setColor(QColor(relation.icon_color))

        self._relation = relation
        self._iconBadge.setIcon(IconRegistry.from_name(relation.icon, relation.icon_color), self._color)
        self._iconBadge.setVisible(True)

        self.rearrange()

        if self._connector:
            self._connector.type = relation.text
            self._connector.icon = relation.icon
            self._connector.color = relation.icon_color
            self.networkScene().connectorChangedEvent(self)

    def icon(self) -> Optional[str]:
        return self._icon

    def setIcon(self, icon: Optional[str]):
        self._icon = icon
        if self._icon:
            self._iconBadge.setIcon(IconRegistry.from_name(self._icon, self._color.name()), self._color)
            self._iconBadge.setVisible(True)
        else:
            self._iconBadge.setVisible(False)
        self.rearrange()

        if self._connector:
            self._connector.icon = icon
            self.networkScene().connectorChangedEvent(self)

    def color(self) -> QColor:
        return self._color

    def setColor(self, color: QColor):
        self._setColor(color)

        self.update()

        if self._connector:
            self._connector.color = color.name()
            self.networkScene().connectorChangedEvent(self)

    @overrides
    def shape(self) -> QPainterPath:
        rect = self.path().boundingRect()
        if rect.width() < 10:
            rect.moveTopLeft(QPointF(rect.x() - 15, rect.y()))
            rect.setWidth(30)
        elif rect.height() < 10:
            rect.moveTopLeft(QPointF(rect.x(), rect.y() - 15))
            rect.setHeight(30)
        else:
            return super().shape()
        path = QPainterPath()
        path.addRect(rect)
        return path

    @overrides
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            self._onSelection(value)
        return super().itemChange(change, value)

    def rearrange(self):
        self.setPos(self._source.sceneBoundingRect().center())

        start: QPointF = self.scenePos()
        end: QPointF = self._target.sceneBoundingRect().center()
        width: float = end.x() - start.x()
        height: float = end.y() - start.y()
        endPoint: QPointF = QPointF(width, height)

        path = QPainterPath()
        if self._connector and self._connector.cp_x is not None:
            self._rearrangeCurvedConnector(path, endPoint)
        else:
            self._rearrangeLinearConnector(path, width, height)

        self._endArrowheadItem.setPos(width, height)
        self._startArrowheadItem.setPos(0, 0)
        self._rearrangeIcon(path)
        self._rearrangeText(path)

        self.setPath(path)

    def rearrangeCP(self, pos: QPointF):
        if self._connector:
            self._connector.cp_x = pos.x()
            self._connector.cp_y = pos.y()

            self.rearrange()
            if self.networkScene():
                self.networkScene().connectorChangedEvent(self)

    def colorChangedEvent(self, nodeItem: 'NodeItem'):
        if nodeItem is self._target.parentItem():
            if not self._connector.color:
                self._setColor(QColor(nodeItem.node().color))

    def _onSelection(self, selected: bool):
        self._cp.setVisible(selected)

    def _rearrangeLinearConnector(self, path: QPainterPath, width: float, height: float):
        path.lineTo(width, height)
        endArrowAngle = math.degrees(math.atan2(height, width))
        self._endArrowheadItem.setRotation(endArrowAngle)
        self._startArrowheadItem.setRotation(endArrowAngle + 180)

    def _rearrangeCurvedConnector(self, path: QPainterPath, endPoint: QPointF):
        path.quadTo(QPointF(self._connector.cp_x, self._connector.cp_y), endPoint)

        end = path.pointAtPercent(1)
        close_to_end = path.pointAtPercent(0.98)
        endArrowAngle = math.degrees(math.atan2(end.y() - close_to_end.y(), end.x() - close_to_end.x()))
        self._endArrowheadItem.setRotation(endArrowAngle)

        start = path.pointAtPercent(0)
        close_to_start = path.pointAtPercent(0.2)
        startArrowAngle = math.degrees(math.atan2(start.y() - close_to_start.y(), start.x() - close_to_start.x()))
        self._startArrowheadItem.setRotation(startArrowAngle)

    def _rearrangeIcon(self, path: QPainterPath):
        if self._icon:
            point = path.pointAtPercent(0.5)
            self._iconBadge.setPos(point.x() - self._iconBadge.boundingRect().width() / 2,
                                   point.y() - self._iconBadge.boundingRect().height() / 2)

    def _rearrangeCPSocket(self, path: QPainterPath):
        point = path.pointAtPercent(0.4)
        self._cp.setPos(point.x() - self._cp.boundingRect().width() / 2,
                        point.y() - self._cp.boundingRect().height() / 2)

    def _rearrangeText(self, path: QPainterPath):
        if not self._label.text():
            self._label.setVisible(False)
            return

        if self._icon:
            point = self._iconBadge.pos()

            x_diff = self._label.boundingRect().width() - self._iconBadge.boundingRect().width()
            point.setX(point.x() - x_diff / 2)
            point.setY(point.y() + self._iconBadge.boundingRect().height() + 2)
        else:
            point = path.pointAtPercent(0.5)
            point -= QPointF(self._label.boundingRect().width() / 2, self._label.boundingRect().height() / 2)
        self._label.setPos(point)
        self._label.setVisible(True)

    def _setColor(self, color: QColor):
        self._color = color
        pen = self.pen()
        pen.setColor(self._color)
        self.setPen(pen)

        arrowPen = self._endArrowheadItem.pen()
        arrowPen.setColor(self._color)
        self._endArrowheadItem.setPen(arrowPen)
        self._endArrowheadItem.setBrush(self._color)

        if self._icon:
            self._iconBadge.setIcon(IconRegistry.from_name(self._icon, self._color.name()), self._color)

        self._cp.setColor(color)
        self._label.setColor(color)

    def _inProximity(self, width: float, height: float) -> bool:
        return abs(height) < 5 or abs(width) < 100


class NodeItem(QAbstractGraphicsShapeItem):
    def __init__(self, node: Node, parent=None):
        super().__init__(parent)
        self._node = node

        self.setPos(node.x, node.y)
        self._sockets: List[AbstractSocketItem] = []

        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        self._posCommandEnabled = True
        self._previousPos: QPointF = self.pos()

    def node(self) -> Node:
        return self._node

    def icon(self) -> Optional[str]:
        return self._node.icon

    def color(self) -> QColor:
        return QColor(self._node.color)

    def networkScene(self) -> 'NetworkScene':
        return self.scene()

    def connectors(self) -> List[ConnectorItem]:
        connectors = []
        for socket in self._sockets:
            connectors.extend(socket.connectors())

        return connectors

    def clearConnectors(self):
        for socket in self._sockets:
            socket.removeConnectors()

    def posCommandEnabled(self) -> bool:
        return self._posCommandEnabled

    def setPosCommandEnabled(self, enabled: bool):
        self._posCommandEnabled = enabled

    @overrides
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._onPosChanged()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            self._onSelection(value)
        return super(NodeItem, self).itemChange(change, value)

    @abstractmethod
    def socket(self, angle: float) -> AbstractSocketItem:
        pass

    def rearrangeConnectors(self):
        for socket in self._sockets:
            socket.rearrangeConnectors()

    def _onPosChanged(self):
        self.rearrangeConnectors()
        self.networkScene().itemMovedEvent(self)

    def _onSelection(self, selected: bool):
        pass

    def updatePos(self):
        if self._posCommandEnabled:
            stack: QUndoStack = self.networkScene().undoStack()
            stack.push(PosChangedCommand(self, self._previousPos, self.pos()))
        self._node.x = self.scenePos().x()
        self._node.y = self.scenePos().y()
        scene = self.networkScene()
        if scene:
            scene.nodeChangedEvent(self._node)

        self._previousPos = self.pos()


class CircleShapedNodeItem(NodeItem):
    Margin: int = 20
    PenWidth: int = 2

    def __init__(self, node: Node, parent=None):
        super().__init__(node, parent)
        self._size: int = node.size
        self._center = QPointF()
        self._outerRadius = 0

        self._linkDisplayedMode: bool = False

        self._socket = FilledSocketItem(0, self)
        self._socket.setVisible(False)

    def size(self) -> int:
        return self._node.size

    def setSize(self, value: int):
        self._node.size = value
        self._size = value
        self._socket.setVisible(False)
        self._recalculate()
        self.prepareGeometryChange()
        for socket in self._sockets:
            x, y = self.socketPosFromAngle(socket.angle())
            socket.setPos(x, y)
        self.update()
        self.rearrangeConnectors()

        self.networkScene().nodeChangedEvent(self._node)

    @overrides
    def socket(self, angle: float) -> AbstractSocketItem:
        x, y = self.socketPosFromAngle(angle)
        self._socket.setAngle(angle)
        self._socket.setPos(x, y)

        return self._socket

    def socketPosFromAngle(self, angle: float):
        angle_radians = math.radians(angle)
        x = self._center.x() + self._outerRadius * math.cos(angle_radians) - FilledSocketItem.Size // 2
        y = self._center.y() + self._outerRadius * math.sin(angle_radians) - FilledSocketItem.Size // 2

        return x, y

    def addSocket(self, socket: AbstractSocketItem):
        self._sockets.append(socket)
        socket.setVisible(False)
        self._socket = FilledSocketItem(socket.angle(), self)
        self._socket.setVisible(False)

    @overrides
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._size + self.Margin * 2, self._size + self.Margin * 2)

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        if self._linkDisplayedMode:
            painter.setPen(QPen(QColor(PLOTLYST_TERTIARY_COLOR), self.PenWidth, Qt.PenStyle.DashLine))
            brush = QBrush(QColor(PLOTLYST_TERTIARY_COLOR), Qt.BrushStyle.Dense5Pattern)
            painter.setBrush(brush)
            painter.drawEllipse(self._center, self._outerRadius, self._outerRadius)
        elif self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.gray, self.PenWidth, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(self.Margin, self.Margin, self._size, self._size, 2, 2)

    @overrides
    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if self.networkScene().linkMode() or alt_modifier(event):
            self._setConnectionEnabled(True)
            self.update()

    @overrides
    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if self._linkDisplayedMode and not self.isSelected():
            self._setConnectionEnabled(False)
            self.update()

    @overrides
    def hoverMoveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if not self._linkDisplayedMode and alt_modifier(event):
            self._setConnectionEnabled(True)
        if self._linkDisplayedMode:
            angle = math.degrees(math.atan2(
                event.pos().y() - self._center.y(), event.pos().x() - self._center.x()
            ))
            x, y = self.socketPosFromAngle(angle)
            self._socket.setAngle(angle)
            self._socket.setPos(x, y)
            self.prepareGeometryChange()

            self.update()

    @overrides
    def _onSelection(self, selected: bool):
        super()._onSelection(selected)
        self._setConnectionEnabled(selected)

    def _recalculate(self):
        self._center.setX(self.Margin + self._size / 2)
        self._center.setY(self.Margin + self._size / 2)
        self._outerRadius = self._size // 2 + self.Margin // 2

    def _setConnectionEnabled(self, enabled: bool):
        self._linkDisplayedMode = enabled
        self._socket.setVisible(enabled)
        self.update()


class CharacterItem(CircleShapedNodeItem):
    def __init__(self, character: Character, node: Node, parent=None):
        super(CharacterItem, self).__init__(node, parent)
        self._character = character

        self._label = QGraphicsTextItem(self._character.name, self)
        font = self._label.font()
        font.setFamily(app_env.sans_serif_font())
        font.setPointSize(font.pointSize() + 1)
        self._label.setFont(font)

        self._recalculate()

    def character(self) -> Character:
        return self._character

    def setCharacter(self, character: Character):
        self._character = character
        self._node.set_character(self._character)
        self._refreshLabel()
        self.update()
        self.networkScene().nodeChangedEvent(self._node)

    def text(self) -> str:
        return self._node.text

    def setText(self, text: str):
        self._node.text = text
        self._refreshLabel()
        self.networkScene().nodeChangedEvent(self._node)

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        super().paint(painter, option, widget)

        avatar = avatars.avatar(self._character)
        avatar.paint(painter, self.Margin, self.Margin, self._size, self._size)

        if not self._node.text and self._character.name != self._label.toPlainText():
            self._refreshLabel()

    @overrides
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.networkScene().editItemEvent(self)

    @overrides
    def _recalculate(self):
        super()._recalculate()
        self._refreshLabel()

    def _refreshLabel(self):
        if self._node.text:
            self._label.setPlainText(self._node.text)
        else:
            self._label.setPlainText(self._character.name)
        x_diff = self._label.boundingRect().width() - self.boundingRect().width()
        self._label.setPos(- x_diff / 2, self.boundingRect().height() - self.Margin)

    @overrides
    def _onSelection(self, selected: bool):
        super()._onSelection(selected)
        if selected:
            effect = QGraphicsOpacityEffect()
            effect.setOpacity(0.3)
            self._label.setGraphicsEffect(effect)
        else:
            self._label.setGraphicsEffect(None)


class IconItem(CircleShapedNodeItem):
    def __init__(self, node: Node, parent=None):
        super().__init__(node, parent)
        color_str = node.color if node.icon else 'grey'
        self._icon = IconRegistry.from_name(node.icon if node.icon else 'fa5s.icons', color_str)
        self._color: QColor = QColor(color_str)

        self._recalculate()

    def setIcon(self, icon: str):
        self._node.icon = icon
        if icon:
            self._icon = IconRegistry.from_name(self._node.icon, self._node.color)
        else:
            self._icon = IconRegistry.from_name('fa5s.icons', 'grey')
        self.update()
        self.networkScene().nodeChangedEvent(self._node)

    def setColor(self, color: QColor):
        self._node.color = color.name()
        self._icon = IconRegistry.from_name(self._node.icon if self._node.icon else 'fa5s.icons', self._node.color)
        self.update()
        self.networkScene().nodeChangedEvent(self._node)
        for socket in self._sockets:
            socket.parentColorChangedEvent(self)

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        super().paint(painter, option, widget)
        self._icon.paint(painter, self.Margin, self.Margin, self._size, self._size)


class EventItem(NodeItem):
    Margin: int = 15
    Padding: int = 12

    def __init__(self, node: Node, parent=None):
        super().__init__(node, parent)
        self._placeholderText: str = 'New event'
        self._text: str = self._node.text if self._node.text else ''
        self._setTooltip()

        self._icon: Optional[QIcon] = None
        self._iconSize: int = 0
        self._iconTextSpacing: int = 3

        if self._node.icon:
            self._icon = IconRegistry.from_name(self._node.icon, self._node.color)

        self._font = QApplication.font()
        self._font.setFamily(app_env.sans_serif_font())
        self._textRect: QRect = QRect(0, 0, 1, 1)
        self._width = 1
        self._height = 1
        self._nestedRectWidth = 1
        self._nestedRectHeight = 1

        self._socketLeft = DotCircleSocketItem(180, parent=self)
        self._socketTopLeft = DotCircleSocketItem(135, parent=self)
        self._socketTopCenter = DotCircleSocketItem(90, parent=self)
        self._socketTopRight = DotCircleSocketItem(45, parent=self)
        self._socketRight = DotCircleSocketItem(0, parent=self)
        self._socketBottomLeft = DotCircleSocketItem(-135, parent=self)
        self._socketBottomCenter = DotCircleSocketItem(-90, parent=self)
        self._socketBottomRight = DotCircleSocketItem(-45, parent=self)
        self._sockets.extend([self._socketLeft,
                              self._socketTopLeft, self._socketTopCenter, self._socketTopRight,
                              self._socketRight,
                              self._socketBottomRight, self._socketBottomCenter, self._socketBottomLeft])
        self._setSocketsVisible(False)

        self._font.setPointSize(self._node.size)
        self._font.setBold(self._node.bold)
        self._font.setItalic(self._node.italic)
        self._font.setUnderline(self._node.underline)
        self._metrics = QFontMetrics(self._font)

        self._recalculateRect()

    def text(self) -> str:
        return self._text

    def setText(self, text: str):
        self._text = text
        self._node.text = text
        self._setTooltip()
        self.setSelected(False)
        self._refresh()
        self.networkScene().nodeChangedEvent(self._node)

    def setItemType(self, itemType: GraphicsItemType, subType: str = ''):
        new_node = to_node(0, 0, itemType, subType, default_size=QApplication.font().pointSize())
        self._node.type = new_node.type
        self._node.subtype = new_node.subtype
        self._node.icon = new_node.icon
        self._node.color = new_node.color
        self._node.size = new_node.size

        self._font.setPointSize(self._node.size)
        self._metrics = QFontMetrics(self._font)

        if self._node.icon:
            self._icon = IconRegistry.from_name(self._node.icon, self._node.color)
        else:
            self._icon = None
        self._refresh()
        self.networkScene().nodeChangedEvent(self._node)

    @overrides
    def socket(self, angle: float) -> AbstractSocketItem:
        if angle == 0:
            return self._socketRight
        elif angle == 45:
            return self._socketTopRight
        elif angle == 90:
            return self._socketTopCenter
        elif angle == 135:
            return self._socketTopLeft
        elif angle == 180:
            return self._socketLeft
        elif angle == -135:
            return self._socketBottomLeft
        elif angle == -90:
            return self._socketBottomCenter
        elif angle == -45:
            return self._socketBottomRight

    @overrides
    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if self.networkScene().linkMode() or alt_modifier(event):
            self._setSocketsVisible()

    @overrides
    def hoverMoveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if not self.networkScene().linkMode() and alt_modifier(event):
            self._setSocketsVisible()

    @overrides
    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if not self.isSelected():
            self._setSocketsVisible(False)

    def setIcon(self, icon: str):
        self._node.icon = icon
        if icon:
            self._icon = IconRegistry.from_name(self._node.icon, self._node.color)
        else:
            self._icon = None
        self._refresh()
        self.networkScene().nodeChangedEvent(self._node)

    def setColor(self, color: QColor):
        self._node.color = color.name()
        if self._icon:
            self._icon = IconRegistry.from_name(self._node.icon, self._node.color)
        self._refresh()
        self.networkScene().nodeChangedEvent(self._node)
        for socket in self._sockets:
            socket.parentColorChangedEvent(self)

    def setFontSettings(self, size: Optional[int] = None, bold: Optional[bool] = None, italic: Optional[bool] = None,
                        underline: Optional[bool] = None):
        if size is not None:
            self._font.setPointSize(size)
            self._node.size = size
        if bold is not None:
            self._font.setBold(bold)
            self._node.bold = bold
        if italic is not None:
            self._font.setItalic(italic)
            self._node.italic = italic
        if underline is not None:
            self._font.setUnderline(underline)
            self._node.underline = underline

        self._metrics = QFontMetrics(self._font)
        self._refresh()
        self.networkScene().nodeChangedEvent(self._node)

    def font(self) -> QFont:
        return self._font

    def fontSize(self) -> int:
        return self._font.pointSize()

    def bold(self) -> bool:
        return self._font.bold()

    def italic(self) -> bool:
        return self._font.italic()

    def underline(self) -> bool:
        return self._font.underline()

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

        painter.setPen(QPen(QColor(self._node.color), 1))
        painter.setBrush(QColor(WHITE_COLOR))
        painter.drawRoundedRect(self.Margin, self.Margin, self._nestedRectWidth, self._nestedRectHeight, 24, 24)
        painter.setFont(self._font)
        painter.drawText(self._textRect, Qt.AlignmentFlag.AlignCenter,
                         self._text if self._text else self._placeholderText)

        if self._icon:
            self._icon.paint(painter, self.Margin + self.Padding - self._iconTextSpacing,
                             self.Margin + v_center(self.Padding * 2 + self._textRect.height(), self._iconSize),
                             self._iconSize, self._iconSize)

    @overrides
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.networkScene().editItemEvent(self)

    def _setTooltip(self):
        self.setToolTip(self._text if self._text else self._placeholderText)

    def _setSocketsVisible(self, visible: bool = True):
        for socket in self._sockets:
            socket.setVisible(visible)

    @overrides
    def _onSelection(self, selected: bool):
        super()._onSelection(selected)
        self._setSocketsVisible(selected)

    def _refresh(self):
        self._recalculateRect()
        self.prepareGeometryChange()
        self.update()
        self.rearrangeConnectors()

    def _recalculateRect(self):
        self._textRect = self._metrics.boundingRect(self._text if self._text else self._placeholderText)
        self._iconSize = int(self._textRect.height() * 1.25) if self._icon else 0
        self._textRect.moveTopLeft(QPoint(self.Margin + self.Padding, self.Margin + self.Padding))
        self._textRect.moveTopLeft(QPoint(self._textRect.x() + self._iconSize, self._textRect.y()))

        self._width = self._textRect.width() + self._iconSize + self.Margin * 2 + self.Padding * 2
        self._height = self._textRect.height() + self.Margin * 2 + self.Padding * 2

        self._nestedRectWidth = self._textRect.width() + self.Padding * 2 + self._iconSize
        self._nestedRectHeight = self._textRect.height() + self.Padding * 2

        socketWidth = self._socketLeft.boundingRect().width()
        socketRad = socketWidth / 2
        socketPadding = (self.Margin - socketWidth) / 2
        self._socketTopCenter.setPos(self._width / 2 - socketRad, socketPadding)
        self._socketTopLeft.setPos(self._nestedRectWidth / 3 - socketRad, socketPadding)

        centerDistance = self._socketTopCenter.pos().x() - self._socketTopLeft.pos().x()
        self._socketTopRight.setPos(self._socketTopCenter.pos().x() + centerDistance, socketPadding)
        self._socketRight.setPos(self._width - self.Margin + socketPadding, self._height / 2 - socketRad)
        self._socketBottomCenter.setPos(self._width / 2 - socketRad, self._height - self.Margin + socketPadding)
        self._socketBottomLeft.setPos(self._nestedRectWidth / 3 - socketRad,
                                      self._height - self.Margin + socketPadding)
        self._socketBottomRight.setPos(self._socketBottomCenter.pos().x() + centerDistance,
                                       self._height - self.Margin + socketPadding)
        self._socketLeft.setPos(socketPadding, self._height / 2 - socketRad)


class TextItem(EventItem):
    def __init__(self, node: Node, parent=None):
        super().__init__(node, parent)

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.gray, 2, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(self.Margin, self.Margin, self._nestedRectWidth, self._nestedRectHeight, 2, 2)

        painter.setPen(QPen(QColor(self._node.color), 1))
        # painter.setBrush(QColor(WHITE_COLOR))
        # painter.drawRoundedRect(self.Margin, self.Margin, self._nestedRectWidth, self._nestedRectHeight, 24, 24)
        painter.setFont(self._font)
        painter.drawText(self._textRect, Qt.AlignmentFlag.AlignCenter,
                         self._text if self._text else self._placeholderText)

    @overrides
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.networkScene().editItemEvent(self)


class NoteItem(NodeItem):
    Margin: int = 20
    Padding: int = 2
    TextPadding: int = 20

    def __init__(self, node: Node, parent=None):
        super().__init__(node, parent)
        self._font = QApplication.font()
        self._textRect: QRect = QRect(self.Margin + self.Padding + self.TextPadding,
                                      self.Margin + self.Padding + self.TextPadding,
                                      node.width if node.width else 140, node.height if node.height else 30,
                                      )
        self._nestedRectWidth = 200
        self._nestedRectHeight = 70
        self._width = self._nestedRectWidth + 2 * self.Padding + 2 * self.Margin
        self._height = self._nestedRectHeight + 2 * self.Padding + 2 * self.Margin
        self._placeholderText = 'Begin typing'

        self._socketLeft = DotCircleSocketItem(180, parent=self)
        self._socketTopCenter = DotCircleSocketItem(90, parent=self)
        self._socketRight = DotCircleSocketItem(0, parent=self)
        self._socketBottomCenter = DotCircleSocketItem(-90, parent=self)
        self._sockets.extend([self._socketLeft, self._socketTopCenter, self._socketRight, self._socketBottomCenter])
        self._setSocketsVisible(False)

        self._resizeItem = ResizeIconItem(self)

        self._recalculateRect()
        self._resizeItem.setVisible(False)
        if not self._node.transparent:
            shadow(self)

    def text(self) -> str:
        return self._node.text

    def height(self) -> int:
        return self._node.height

    def setText(self, text: str, height: int):
        self._node.text = text
        self._textRect.setHeight(height)
        self._node.height = height

        self.networkScene().nodeChangedEvent(self._node)
        self._refresh()

    def transparent(self) -> bool:
        return self._node.transparent

    def setTransparent(self, transparent: bool):
        self._node.transparent = transparent
        self.networkScene().nodeChangedEvent(self._node)
        self.update()
        if transparent:
            self.setGraphicsEffect(None)
        else:
            shadow(self)

    @overrides
    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if not self.isSelected():
            self._resizeItem.setVisible(True)
            if self.networkScene().linkMode() or alt_modifier(event):
                self._setSocketsVisible()

    @overrides
    def hoverMoveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if not self.networkScene().linkMode() and alt_modifier(event):
            self._setSocketsVisible()

    @overrides
    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if not self.isSelected():
            self._resizeItem.setVisible(False)
            self._setSocketsVisible(False)

    @overrides
    def socket(self, angle: float) -> AbstractSocketItem:
        if angle == 0:
            return self._socketRight
        elif angle == 90:
            return self._socketTopCenter
        elif angle == 180:
            return self._socketLeft
        elif angle == -90:
            return self._socketBottomCenter

    @overrides
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

    def textRect(self) -> QRect:
        return self._textRect

    def textSceneRect(self) -> QRectF:
        return self.mapRectToScene(self._textRect.toRectF())

    def rearrangeSize(self, pos: QPointF):
        height = int(pos.y()) - self.TextPadding
        width = int(pos.x()) - self.TextPadding
        self._textRect.setWidth(width)
        self._textRect.setHeight(height)

        self._node.height = height
        self._node.width = width
        self.networkScene().nodeChangedEvent(self._node)
        self._refresh()

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.gray, 2, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(self.Margin, self.Margin, self._nestedRectWidth + 2 * self.Padding,
                                    self._nestedRectHeight + 2 * self.Padding, 2, 2)

        if not self._node.transparent:
            painter.setPen(QPen(QColor('lightgrey'), 1))
            painter.setBrush(QColor(WHITE_COLOR))
            painter.drawRoundedRect(self.Margin + self.Padding, self.Margin + self.Padding, self._nestedRectWidth,
                                    self._nestedRectHeight, 6, 6)

        if self._node.text:
            painter.setPen(QPen(QColor(self._node.color), 1))
        else:
            painter.setPen(QPen(QColor('grey'), 1))
        painter.setFont(self._font)
        if self._node.text:
            doc = QTextDocument()
            doc.setMarkdown(self._node.text)
            painter.translate(self._textRect.x(), self._textRect.y())
            doc.drawContents(painter)
        else:
            painter.drawText(self._textRect, Qt.AlignmentFlag.AlignLeft, self._placeholderText)

    @overrides
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.networkScene().editItemEvent(self)

    def _setSocketsVisible(self, visible: bool = True):
        for socket in self._sockets:
            socket.setVisible(visible)

    @overrides
    def _onSelection(self, selected: bool):
        super()._onSelection(selected)
        self._setSocketsVisible(selected)
        self._resizeItem.setVisible(selected)

    def _refresh(self):
        self._recalculateRect()
        self.prepareGeometryChange()
        self.update()
        self.rearrangeConnectors()

    def _recalculateRect(self):
        self._nestedRectWidth = self._textRect.width() + 2 * self.TextPadding
        self._nestedRectHeight = self._textRect.height() + 2 * self.TextPadding
        self._width = self._nestedRectWidth + 2 * self.Padding + 2 * self.Margin
        self._height = self._nestedRectHeight + 2 * self.Padding + 2 * self.Margin

        socketWidth = self._socketLeft.boundingRect().width()
        socketRad = socketWidth / 2
        socketPadding = (self.Margin - socketWidth) / 2
        self._socketTopCenter.setPos(self._width / 2 - socketRad, socketPadding)
        self._socketRight.setPos(self._width - self.Margin + socketPadding, self._height / 2 - socketRad)
        self._socketBottomCenter.setPos(self._width / 2 - socketRad, self._height - self.Margin + socketPadding)
        self._socketLeft.setPos(socketPadding, self._height / 2 - socketRad)

        self._resizeItem.deactivate()
        self._resizeItem.setPos(self._textRect.width() + self.TextPadding + 10,
                                self._textRect.height() + self.TextPadding + 10)
        self._resizeItem.activate()


class ImageItem(NodeItem):
    Margin: int = 20
    Padding: int = 2
    PlaceholderPadding: int = 20
    MinimumImageSize: int = 30

    def __init__(self, node: Node, parent=None):
        super().__init__(node, parent)
        self._imageWidth = node.width if node.width else 200
        self._imageHeight = node.height if node.height else 200
        self._imageRect = QRect(self.Margin + self.Padding, self.Margin + self.Padding, self._imageWidth,
                                self._imageHeight)
        self._image: Optional[QImage] = None

        self._width = 0
        self._height = 0
        self._placeholderPadding = 0
        self._placeholderColor = 'lightgrey'

        if self._node.image_ref is None:
            pointy(self)

        self._socketLeft = DotCircleSocketItem(180, parent=self)
        self._socketTopCenter = DotCircleSocketItem(90, parent=self)
        self._socketRight = DotCircleSocketItem(0, parent=self)
        self._socketBottomCenter = DotCircleSocketItem(-90, parent=self)
        self._sockets.extend([self._socketLeft, self._socketTopCenter, self._socketRight, self._socketBottomCenter])
        self._setSocketsVisible(False)

        self._resizeItem = ResizeIconItem(self)
        self._resizeItem.setKeepAspectRatio(True)
        self._resizeItem.setRatio(self._imageWidth / self._imageHeight)

        self._recalculateRect()
        self._resizeItem.setVisible(False)

    def hasImage(self) -> bool:
        return self._node.image_ref is not None

    def setImage(self, image: QImage):
        self._image = image

    def setLoadedImage(self, image: LoadedImage):
        self.setImage(image.image)
        self._node.image_ref = image.ref
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

        w, h = calculate_resized_dimensions(self._image.width(), self._image.height(), 200)
        self._imageWidth = w
        self._imageHeight = h
        self._node.width = w
        self._node.height = h
        self._resizeItem.setRatio(self._imageWidth / self._imageHeight)

        self._refresh()

        self.networkScene().nodeChangedEvent(self._node)

    @overrides
    def socket(self, angle: float) -> AbstractSocketItem:
        if angle == 0:
            return self._socketRight
        elif angle == 90:
            return self._socketTopCenter
        elif angle == 180:
            return self._socketLeft
        elif angle == -90:
            return self._socketBottomCenter

    def rearrangeSize(self, pos: QPointF):
        height = int(pos.y())
        width = int(pos.x())
        if width < self.MinimumImageSize or height < self.MinimumImageSize:
            self._recalculateRect()
            return

        self._imageWidth = width
        self._imageHeight = height

        self._refresh()

        self._node.width = self._imageWidth
        self._node.height = self._imageHeight
        self.networkScene().nodeChangedEvent(self._node)

    @overrides
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

    @overrides
    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if self.hasImage() and not self.isSelected():
            self._resizeItem.setVisible(True)
            if self.networkScene().linkMode() or alt_modifier(event):
                self._setSocketsVisible()
        elif not self.hasImage():
            self._placeholderColor = 'grey'
            self.update()

    @overrides
    def hoverMoveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if self.hasImage() and not self.networkScene().linkMode() and alt_modifier(event):
            self._setSocketsVisible()

    @overrides
    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if self.hasImage():
            if not self.isSelected():
                self._resizeItem.setVisible(False)
                self._setSocketsVisible(False)
        else:
            self._placeholderColor = 'lightgrey'
            self.update()

    @overrides
    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if not self.hasImage():
            self._placeholderPadding = 4
            self.update()
        super().mousePressEvent(event)

    @overrides
    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if not self.hasImage():
            self._placeholderPadding = 0
            self.update()
            self.networkScene().requestImageUpload(self)
        super().mouseReleaseEvent(event)

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.gray, 2, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(self.Margin, self.Margin, self._imageWidth + 2 * self.Padding,
                                    self._imageHeight + 2 * self.Padding, 2, 2)

        if self.hasImage():
            if not self._image:
                self.networkScene().loadImage(self)
            if self._image:
                painter.drawImage(self._imageRect, self._image)
        else:
            painter.setPen(QPen(QColor('lightgrey'), 1))
            painter.setBrush(QColor(WHITE_COLOR))
            painter.drawRoundedRect(self.Margin + self.Padding, self.Margin + self.Padding, self._imageWidth,
                                    self._imageHeight, 6, 6)
            IconRegistry.image_icon(color=self._placeholderColor).paint(painter,
                                                                        self.Margin + self.Padding + self.PlaceholderPadding,
                                                                        self.Margin + self.Padding + self.PlaceholderPadding,
                                                                        self._imageWidth - 2 * self.PlaceholderPadding - self._placeholderPadding,
                                                                        self._imageHeight - 2 * self.PlaceholderPadding - self._placeholderPadding)

    def _refresh(self):
        self._recalculateRect()
        self.prepareGeometryChange()
        self.update()
        self.rearrangeConnectors()

    def _recalculateRect(self):
        self._width = self._imageWidth + self.Margin * 2 + self.Padding * 2
        self._height = self._imageHeight + self.Margin * 2 + self.Padding * 2
        self._imageRect = QRect(self.Margin + self.Padding, self.Margin + self.Padding, self._imageWidth,
                                self._imageHeight)

        socketWidth = self._socketLeft.boundingRect().width()
        socketRad = socketWidth / 2
        socketPadding = (self.Margin - socketWidth) / 2
        self._socketTopCenter.setPos(self._width / 2 - socketRad, socketPadding)
        self._socketRight.setPos(self._width - self.Margin + socketPadding, self._height / 2 - socketRad)
        self._socketBottomCenter.setPos(self._width / 2 - socketRad, self._height - self.Margin + socketPadding)
        self._socketLeft.setPos(socketPadding, self._height / 2 - socketRad)

        self._resizeItem.deactivate()
        self._resizeItem.setPos(self._imageRect.width() - 10,
                                self._imageRect.height() - 10)
        self._resizeItem.activate()

    @overrides
    def _onSelection(self, selected: bool):
        super()._onSelection(selected)
        self._setSocketsVisible(selected)
        self._resizeItem.setVisible(selected)

    def _setSocketsVisible(self, visible: bool = True):
        for socket in self._sockets:
            socket.setVisible(visible)
