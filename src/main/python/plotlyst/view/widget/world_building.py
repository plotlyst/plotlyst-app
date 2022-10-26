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
from typing import Optional, List

from PyQt6.QtCore import Qt, QRectF, QRect, QPoint
from PyQt6.QtGui import QMouseEvent, QWheelEvent, QPainter, QColor, QPen, QFontMetrics, QFont, QIcon
from PyQt6.QtWidgets import QGraphicsView, QAbstractGraphicsShapeItem, QStyleOptionGraphicsItem, \
    QWidget, QGraphicsSceneMouseEvent, QGraphicsItem, QGraphicsScene, QGraphicsSceneHoverEvent, QInputDialog, QLineEdit, \
    QGraphicsLineItem
from overrides import overrides

from src.main.python.plotlyst.core.domain import WorldBuildingEntity
from src.main.python.plotlyst.view.common import pointy
from src.main.python.plotlyst.view.icons import IconRegistry

LINE_WIDTH: int = 4


class ConnectorItem(QAbstractGraphicsShapeItem):

    def __init__(self, target: QGraphicsItem):
        super(ConnectorItem, self).__init__()
        self._target = target

    @overrides
    def boundingRect(self):
        # TODO fix for curving line
        return QRectF(0, -LINE_WIDTH / 2, self._target.pos().x() - self.pos().x(), LINE_WIDTH)

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering)

        painter.setPen(QPen(QColor('#219ebc'), LINE_WIDTH))
        painter.drawLine(0, 0, self.boundingRect().width(), 0)


class PlusItem(QAbstractGraphicsShapeItem):
    def __init__(self, parent: 'WorldBuildingItemGroup'):
        super(PlusItem, self).__init__(parent)
        self._parent = parent
        self._plusIcon = IconRegistry.plus_circle_icon('lightgrey')
        self.setAcceptHoverEvents(True)
        pointy(self)

    @overrides
    def boundingRect(self):
        return QRectF(0, 0, 25, 25)

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering)

        self._plusIcon.paint(painter, 0, 0, 25, 25)

    @overrides
    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._plusIcon = IconRegistry.plus_circle_icon('#457b9d')
        self.update()

    @overrides
    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._plusIcon = IconRegistry.plus_circle_icon('lightgrey')
        self.update()

    @overrides
    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        event.accept()

    @overrides
    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        self._parent.addChild()


class EditItem(QAbstractGraphicsShapeItem):

    def __init__(self, parent: 'WorldBuildingItem'):
        super(EditItem, self).__init__(parent)
        self._parent = parent
        self._editIcon = IconRegistry.edit_icon('white')
        self._hovered = False
        self._pressed = False
        self.setAcceptHoverEvents(True)
        pointy(self)

    @overrides
    def boundingRect(self):
        return QRectF(0, 0, 20, 20)

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering)

        painter.setPen(Qt.GlobalColor.white)
        if self._hovered:
            color = '#b100e8'
        else:
            color = '#7209b7'
        painter.setBrush(QColor(color))
        if self._pressed:
            painter.drawEllipse(0, 0, 19, 19)
        else:
            painter.drawEllipse(0, 0, 20, 20)
        self._editIcon.paint(painter, 1, 1, 18, 18)

    @overrides
    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        event.accept()
        self._pressed = True
        self.update()

    @overrides
    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        self._pressed = False
        self.update()
        self._edit()

    @overrides
    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._hovered = True
        self.update()

    @overrides
    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._hovered = False
        self.update()

    def _edit(self):
        text, ok = QInputDialog.getText(self.scene().views()[0], 'Edit', 'Edit text', QLineEdit.EchoMode.Normal,
                                        self._parent.text())
        if ok:
            self._parent.setText(text)


class CollapseItem(QAbstractGraphicsShapeItem):
    def __init__(self, parent: 'WorldBuildingItemGroup'):
        super(CollapseItem, self).__init__(parent)
        self._parent = parent
        self._size = 15
        self._toggled = True
        pointy(self)

    @overrides
    def boundingRect(self):
        return QRectF(0, 0, self._size + LINE_WIDTH * 2, self._size + LINE_WIDTH * 2)

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering)

        painter.setPen(QPen(QColor('#219ebc'), LINE_WIDTH))
        painter.drawEllipse(0, 0, self._size, self._size)
        if not self._toggled:
            painter.setBrush(QColor('#219ebc'))
            painter.drawEllipse(6, 6, 3, 3)

    @overrides
    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        event.accept()

    @overrides
    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        self._toggled = not self._toggled
        self._parent.setChildrenVisible(self._toggled)
        self.update()


class WorldBuildingItem(QAbstractGraphicsShapeItem):

    def __init__(self, entity: WorldBuildingEntity, parent: 'WorldBuildingItemGroup'):
        super(WorldBuildingItem, self).__init__(parent)
        self._entity = entity
        self._parent = parent

        self._icon: Optional[QIcon] = None
        self._font = QFont('Helvetica', 14)
        self._metrics = QFontMetrics(self._font)
        self._rect = QRect(0, 0, 1, 1)
        self._textRect = QRect(0, 0, 1, 1)
        self._penWidth = 1
        self._recalculateRect()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

        self._editItem = EditItem(self)
        self.update()

    def text(self) -> str:
        return self._entity.name

    def setText(self, text: str):
        self._entity.name = text
        self._recalculateRect()
        self.prepareGeometryChange()
        self._parent.rearrangeItems()
        self.update()

    def setIcon(self, icon: QIcon):
        self._icon = icon
        self._recalculateRect()
        self.update()

    @overrides
    def update(self, rect: QRectF = ...) -> None:
        self._editItem.setPos(self._rect.x() + self._rect.width() - 20, self._rect.y() - 5)
        self._editItem.setVisible(False)
        super(WorldBuildingItem, self).update()

    def _recalculateRect(self):
        self._textRect = self._metrics.boundingRect(self.text())
        self._textRect.moveTopLeft(QPoint(0, 0))

        x_diff = 10
        icon_diff = 40 if self._icon else 0

        self._rect = QRect(0, 0, self._textRect.width() + x_diff + icon_diff + self._penWidth * 2,
                           self._textRect.height() + 10 + self._penWidth * 2)

        self._textRect.moveLeft(x_diff / 2 + icon_diff)

    @overrides
    def boundingRect(self):
        return QRectF(self._rect)

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering)

        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.black, self._penWidth, Qt.PenStyle.DashLine))
            painter.drawRoundedRect(self._rect, 2, 2)

        painter.setBrush(QColor('#219ebc'))
        pen = QPen(QColor('#219ebc'), self._penWidth)
        painter.setPen(pen)
        painter.drawRoundedRect(self._rect, 25, 25)

        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(self._font)
        painter.drawText(self._textRect.x(), self._textRect.height(), self.text())
        if self._icon:
            self._icon.paint(painter, 13, 8, 25, 25)

    @overrides
    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        self.setSelected(True)

    @overrides
    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._editItem.setVisible(True)

    @overrides
    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._editItem.setVisible(False)


class WorldBuildingItemGroup(QAbstractGraphicsShapeItem):
    def __init__(self, entity: WorldBuildingEntity, parent=None):
        super(WorldBuildingItemGroup, self).__init__(parent)
        self._entity = entity
        self._childrenEntityItems: List['WorldBuildingItemGroup'] = []
        self._connecters: List[ConnectorItem] = []

        self._collapseDistance = 30

        self._item = WorldBuildingItem(self._entity, parent=self)
        self._item.setIcon(IconRegistry.book_icon('white'))
        self._item.setPos(0, 0)

        self._plusItem = PlusItem(parent=self)
        self._collapseItem = CollapseItem(parent=self)
        self._lineItem = QGraphicsLineItem(parent=self)
        self.rearrangeItems()
        self.setAcceptHoverEvents(True)

    def childrenEntityItems(self) -> List['WorldBuildingItemGroup']:
        return self._childrenEntityItems

    def rearrangeItems(self) -> None:
        self._plusItem.setPos(self._item.boundingRect().x() + self._item.boundingRect().width() + 10,
                              self._item.boundingRect().y() + 10)
        self._plusItem.setVisible(False)
        self._updateConnector()
        if self.scene():
            self.worldBuildingScene().rearrangeItems()

    def _updateConnector(self):
        if self._childrenEntityItems:
            self._collapseItem.setVisible(True)
            self._lineItem.setVisible(True)
            self._collapseItem.setPos(self._plusItem.pos().x() + self._collapseDistance, self._plusItem.y() + 4)
            self._lineItem.setPen(QPen(QColor('#219ebc'), LINE_WIDTH))
            self._lineItem.setLine(self._item.boundingRect().x() + self._item.boundingRect().width(),
                                   self._plusItem.y() + 12, self._plusItem.pos().x() + self._collapseDistance,
                                   self._plusItem.y() + 12)
        else:
            self._collapseItem.setVisible(False)
            self._lineItem.setVisible(False)

    @overrides
    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._plusItem.setVisible(True)

    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._plusItem.setVisible(False)

    @overrides
    def boundingRect(self):
        rect_f = QRectF(self._item.boundingRect())
        rect_f.setWidth(rect_f.width() + self._collapseDistance + self._collapseItem.boundingRect().width())
        return rect_f

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        pass

    def addChild(self):
        child = WorldBuildingEntity('Entity')
        self._entity.children.append(child)
        self._childrenEntityItems.append(WorldBuildingItemGroup(child, parent=self))

        self._updateConnector()
        self.worldBuildingScene().rearrangeItems()

    def addConnector(self, connector: ConnectorItem):
        self._connecters.append(connector)

    def setChildrenVisible(self, visible: bool):
        for child in self._childrenEntityItems:
            child.setVisible(visible)

        for connector in self._connecters:
            connector.setVisible(visible)

    def worldBuildingScene(self) -> Optional['WorldBuildingEditorScene']:
        scene = self.scene()
        if scene is not None and isinstance(scene, WorldBuildingEditorScene):
            return scene


class WorldBuildingEditorScene(QGraphicsScene):

    def __init__(self, entity: WorldBuildingEntity, parent=None):
        super(WorldBuildingEditorScene, self).__init__(parent)
        self._root = entity
        self._itemHorizontalDistance = 40

        self._rootItem = WorldBuildingItemGroup(self._root)
        self.addItem(self._rootItem)

        self.rearrangeItems()

    @overrides
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        items = self.items(event.scenePos())
        if not items:
            self.clearSelection()

        super(WorldBuildingEditorScene, self).mouseReleaseEvent(event)

    def rearrangeItems(self):
        self._rootItem.setPos(0, 0)
        for child in self._rootItem.childrenEntityItems():
            child.setPos(self._rootItem.boundingRect().width() + self._itemHorizontalDistance, self._rootItem.y())
            connector = ConnectorItem(child)
            connector.setPos(self._rootItem.boundingRect().width() + LINE_WIDTH, child.boundingRect().height() // 2 + 3)
            self.addItem(connector)
            self._rootItem.addConnector(connector)
            # print(child.pos())
            # print(child.boundingRect().height())
            # connector.setPos(-self._itemHorizontalDistance + LINE_WIDTH, child.boundingRect().height() // 2 + 3)


class WorldBuildingEditor(QGraphicsView):
    def __init__(self, entity: WorldBuildingEntity, parent=None):
        super(WorldBuildingEditor, self).__init__(parent)
        self._moveOriginX = 0
        self._moveOriginY = 0

        self._scene = WorldBuildingEditorScene(entity)
        self.setScene(self._scene)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)

    @overrides
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._moveOriginX = event.pos().x()
            self._moveOriginY = event.pos().y()
        super(WorldBuildingEditor, self).mousePressEvent(event)

    @overrides
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.MiddleButton:
            oldPoint = self.mapToScene(self._moveOriginX, self._moveOriginY)
            newPoint = self.mapToScene(event.pos())
            translation = newPoint - oldPoint
            self.translate(translation.x(), translation.y())

            self._moveOriginX = event.pos().x()
            self._moveOriginY = event.pos().y()
        else:
            super(WorldBuildingEditor, self).mouseMoveEvent(event)

    @overrides
    def wheelEvent(self, event: QWheelEvent) -> None:
        super(WorldBuildingEditor, self).wheelEvent(event)
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            diff = event.angleDelta().y()
            scale = (diff // 120) / 10
            self.scale(1 + scale, 1 + scale)
