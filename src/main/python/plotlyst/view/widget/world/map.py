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
from functools import partial
from typing import Optional, Any

import qtanim
from PyQt6.QtCore import Qt, QPoint, QSize, QPointF, QRectF, pyqtSignal, QTimer, QObject
from PyQt6.QtGui import QColor, QPixmap, QShowEvent, QResizeEvent, QImage, QPainter, QKeyEvent, QIcon, QUndoStack, \
    QPainterPath, QPen, QMouseEvent
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem, QAbstractGraphicsShapeItem, QWidget, \
    QGraphicsSceneMouseEvent, QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QFrame, QLineEdit, \
    QApplication, QGraphicsSceneDragDropEvent, QSlider, QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPathItem, \
    QGraphicsView, QGraphicsEffect
from overrides import overrides
from qthandy import busy, vbox, sp, line, incr_font, flow, incr_icon, bold, vline, \
    margins, decr_font, translucent
from qthandy.filter import DragEventFilter, OpacityEventFilter, InstantTooltipEventFilter
from qtmenu import MenuWidget, ActionTooltipDisplayMode
from qtpy import sip

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, RELAXED_WHITE_COLOR, PLOTLYST_TERTIARY_COLOR, PLOTLYST_MAIN_COLOR
from plotlyst.core.domain import Novel, WorldBuildingMap, WorldBuildingMarker, GraphicsItemType, Location, Point
from plotlyst.resources import resource_registry
from plotlyst.service.cache import entities_registry
from plotlyst.service.image import load_image, upload_image, LoadedImage
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import tool_btn, action, shadow, TooltipPositionEventFilter, dominant_color, push_btn, \
    ExclusiveOptionalButtonGroup, restyle
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.graphics import BaseGraphicsView
from plotlyst.view.widget.graphics.editor import ZoomBar, BaseItemToolbar, \
    SecondarySelectorWidget
from plotlyst.view.widget.graphics.items import IconBadge
from plotlyst.view.widget.input import AutoAdjustableTextEdit
from plotlyst.view.widget.utility import IconSelectorDialog
from plotlyst.view.widget.world.editor import MilieuSelectorPopup


class PopupText(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet('''QFrame {
                    background: #ede0d4;
                    border-radius: 12px;
                }''')
        shadow(self)
        vbox(self, 10, spacing=6)

        self.lineTitle = QLineEdit()
        self.lineTitle.setProperty('transparent', True)
        self.lineTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lineTitle.setPlaceholderText('Location')
        incr_font(self.lineTitle)
        bold(self.lineTitle)
        self.lineTitle.setReadOnly(True)

        self.textEdit = AutoAdjustableTextEdit()
        self.textEdit.setProperty('transparent', True)
        self.textEdit.setProperty('rounded', True)
        self.textEdit.setReadOnly(True)

        self.layout().addWidget(self.lineTitle)
        self.layout().addWidget(line(color='lightgrey'))
        self.layout().addWidget(self.textEdit)

        self.setFixedWidth(200)

        sp(self).v_max()

    def setText(self, name: str, text: str):
        self.lineTitle.setText(name)
        self.textEdit.setText(text)
        self.textEdit.setVisible(len(text) > 0)


marker_colors = ['#ef233c', '#0077b6', '#fb8500', '#B28DC8', '#CE9861']
marker_selected_colors = {
    '#ef233c': '#A50C1E',
    '#0077b6': '#00669D',
    '#fb8500': '#C46900',
    '#B28DC8': '#9967B6',
    '#CE9861': '#C3803D',
}


class MarkerColorSelectorWidget(QWidget):
    colorSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        flow(self, 2, 2)
        margins(self, bottom=5)
        for color in marker_colors:
            btn = tool_btn(IconRegistry.from_name('fa5s.map-marker', color), transparent_=True)
            btn.setIconSize(QSize(32, 32))
            btn.clicked.connect(partial(self.colorSelected.emit, color))
            self.layout().addWidget(btn)


class MarkerIconSelectorWidget(QWidget):
    iconReset = pyqtSignal()
    iconSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.icons = ['mdi.castle', 'mdi.tower-fire', 'mdi.lighthouse-on', 'mdi.warehouse', 'mdi6.hoop-house',
                      'ph.house-line-bold', 'mdi.city-variant', 'mdi6.town-hall', 'fa5s.place-of-worship',
                      'mdi.water-well',
                      'mdi.treasure-chest', 'fa5s.flag',
                      'mdi6.axe-battle', 'mdi.sword-cross',
                      'mdi.horse-human',
                      'fa5s.dragon',
                      'fa5s.skull', 'fa5s.skull-crossbones', 'ri.ghost-2-fill', 'mdi.grave-stone',
                      'fa5s.train', 'mdi.ship-wheel', 'mdi.sail-boat',
                      'fa5s.mountain', 'fa5s.tree', 'mdi.tree', 'mdi.island', 'mdi.circle'
                      ]
        vbox(self)
        self.wdgIcons = QWidget()
        flow(self.wdgIcons, 0, 1)
        margins(self.wdgIcons, bottom=5)
        self.btnCustom = push_btn(IconRegistry.icons_icon(), 'Custom icon', transparent_=True)
        decr_font(self.btnCustom)
        self.btnCustom.clicked.connect(self._selectCustomIcon)

        for icon in self.icons:
            btn = tool_btn(IconRegistry.from_name(icon), transparent_=True)
            btn.setIconSize(QSize(24, 24))
            btn.clicked.connect(partial(self.iconSelected.emit, icon))
            self.wdgIcons.layout().addWidget(btn)

        self.layout().addWidget(self.wdgIcons)
        self.layout().addWidget(line())
        self.layout().addWidget(self.btnCustom, alignment=Qt.AlignmentFlag.AlignLeft)

    def _selectCustomIcon(self):
        result = IconSelectorDialog.popup(pickColor=False)
        if result:
            self.iconSelected.emit(result[0])


class MarkerItemToolbar(BaseItemToolbar):
    def __init__(self, novel: Novel, undoStack: QUndoStack, parent=None):
        super().__init__(undoStack, parent)
        self._novel = novel
        self._item: Optional[MarkerItem] = None

        self._btnMilieuLink = tool_btn(IconRegistry.world_building_icon(), tooltip='Link to milieu', transparent_=True)
        self._btnMilieuLink.clicked.connect(self._linkToMilieu)
        if self._novel.tutorial:
            self._btnMilieuLink.setDisabled(True)
            self._btnMilieuLink.setToolTip('Milieu link is disabled in preview mode')
            self._btnMilieuLink.installEventFilter(InstantTooltipEventFilter(self._btnMilieuLink))

        self._btnColor = tool_btn(IconRegistry.from_name('fa5s.map-marker', color='black'), 'Change style',
                                  transparent_=True)

        self._colorPicker = MarkerColorSelectorWidget(self)
        self._colorSecondaryWidget = SecondarySelectorWidget(self)
        margins(self._colorSecondaryWidget, bottom=5, left=0, right=0, top=2)
        self._colorSecondaryWidget.addWidget(self._colorPicker, 0, 0)
        self.addSecondaryWidget(self._btnColor, self._colorSecondaryWidget)
        self._colorPicker.colorSelected.connect(self._colorChanged)

        self._btnIcon = tool_btn(IconRegistry.from_name('mdi.emoticon-outline'), 'Change icon', transparent_=True)
        self._iconPicker = MarkerIconSelectorWidget(self)
        self._iconSecondaryWidget = SecondarySelectorWidget(self)
        margins(self._iconSecondaryWidget, bottom=5, left=0, right=0, top=2)
        self._iconSecondaryWidget.addWidget(self._iconPicker, 0, 0)
        self.addSecondaryWidget(self._btnIcon, self._iconSecondaryWidget)
        self._iconPicker.iconSelected.connect(self._iconChanged)

        self._sbRange = QSlider()
        self._sbRange.setOrientation(Qt.Orientation.Horizontal)
        self._sbRange.valueChanged.connect(self._sizeChanged)

        self._toolbar.layout().addWidget(self._btnMilieuLink)
        self._toolbar.layout().addWidget(vline())
        self._toolbar.layout().addWidget(self._btnColor)
        self._toolbar.layout().addWidget(self._btnIcon)
        self._toolbar.layout().addWidget(vline())
        self._toolbar.layout().addWidget(self._sbRange)

        self._iconPicker.setFixedWidth(self.sizeHint().width())

    def setMarker(self, item: 'MarkerItem'):
        self._item = None
        self._hideSecondarySelectors()

        marker = item.marker()
        if marker.ref:
            self._btnMilieuLink.setIcon(IconRegistry.world_building_icon(PLOTLYST_TERTIARY_COLOR))
        else:
            self._btnMilieuLink.setIcon(IconRegistry.world_building_icon())

        self._btnColor.setIcon(IconRegistry.from_name('fa5s.map-marker', color=marker.color))

        if marker.type == GraphicsItemType.MAP_MARKER:
            self._sbRange.setMinimum(30)
            self._sbRange.setMaximum(90)
            self._sbRange.setValue(50)
            self._sbRange.setValue(marker.size if marker.size else 50)
        else:
            self._sbRange.setMinimum(-70 if marker.ref else -40)
            self._sbRange.setMaximum(20)
            self._sbRange.setValue(marker.opacity)
        self._toolbar.updateGeometry()

        self._item = item

    @busy
    def _linkToMilieu(self, _):
        element: Location = MilieuSelectorPopup.popup(self._novel)
        if element and self._item:
            self._item.setLocation(element)
            self._item.setSelected(False)
            self._item.highlight()
            self._btnMilieuLink.setIcon(IconRegistry.world_building_icon(PLOTLYST_TERTIARY_COLOR))

    def _colorChanged(self, color: str):
        if self._item:
            self._item.setColor(color)
            self._btnColor.setIcon(IconRegistry.from_name('fa5s.map-marker', color=color))

    def _iconChanged(self, icon: str):
        if self._item:
            translucent(self._iconSecondaryWidget, 0.1)
            self._item.setIcon(icon)
            QTimer.singleShot(500, lambda: self._iconSecondaryWidget.setGraphicsEffect(None))

    def _sizeChanged(self, value: int):
        if self._item:
            if self._item.marker().type == GraphicsItemType.MAP_MARKER:
                self._item.setSize(value)
            else:
                self._item.setOpacityDiff(value)


class BaseMapItem:
    def __init__(self):
        self.__default_type_size = 25
        self._typeSize = self.__default_type_size
        self._marker = None

        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        self._posChangedTimer = QTimer()
        self._posChangedTimer.setInterval(1000)
        self._posChangedTimer.timeout.connect(self._posChangedOnTimeout)

    def marker(self) -> WorldBuildingMarker:
        return self._marker

    def mapScene(self) -> 'WorldBuildingMapScene':
        return self.scene()

    def activate(self):
        self._checkRef()

    def highlight(self):
        self.mapScene().highlightItem(self)

    def setLocation(self, location: Location):
        self._marker.ref = location.id
        if location.icon:
            self.setIcon(location.icon)
        else:
            self.resetIcon()
        self.mapScene().markerChangedEvent(self)

    def setColor(self, color: str):
        self._marker.color = color
        self._marker.color_selected = marker_selected_colors[color]
        self.refresh()

    def setIcon(self, icon: str):
        self._marker.icon = icon
        self.refresh()

    def resetIcon(self):
        pass

    def refresh(self):
        self.update()
        self.mapScene().markerChangedEvent(self)

    def _hoverEnter(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if not self.isSelected():
            effect = QGraphicsOpacityEffect()
            effect.setOpacity(0.8)
            self.setGraphicsEffect(effect)
            self._typeSize = self.__default_type_size + 1
            self.update()

            if self._marker.ref:
                if entities_registry.location(str(self._marker.ref)):
                    QTimer.singleShot(250, self._triggerPopup)
                else:
                    self._marker.ref = None
                    self.mapScene().markerChangedEvent(self)

    def _hoverLeave(self, event: 'QGraphicsSceneHoverEvent') -> None:
        if not self.isSelected():
            self.setGraphicsEffect(None)
            self._checkRef()
            self._typeSize = self.__default_type_size
            self.update()

            if self._marker.ref:
                self.scene().hidePopupEvent()

    def _onSelection(self, selected: bool):
        if selected:
            effect = QGraphicsDropShadowEffect()
            effect.setBlurRadius(12)
            effect.setOffset(0)
            effect.setColor(QColor(RELAXED_WHITE_COLOR))
            self.setGraphicsEffect(effect)

            self._typeSize = self.__default_type_size + 2
        else:
            self._typeSize = self.__default_type_size
            self.setGraphicsEffect(None)
            self._checkRef()

    def _checkRef(self):
        if self._marker.ref:
            effect = self._effectWithRef()
            if effect:
                self.setGraphicsEffect(effect)
        else:
            self.setGraphicsEffect(self._effectWithoutRef())

    def _effectWithRef(self) -> Optional[QGraphicsEffect]:
        return None

    def _effectWithoutRef(self) -> QGraphicsEffect:
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(0.5 + self._marker.opacity / 100)
        return effect

    def _posChangedOnTimeout(self):
        self._posChangedTimer.stop()
        self._marker.x = self.scenePos().x()
        self._marker.y = self.scenePos().y()
        scene = self.mapScene()
        if scene:
            scene.markerChangedEvent(self)

    def _triggerPopup(self):
        if not self.isSelected() and self.isUnderMouse():
            self.mapScene().showPopupEvent(self)


class MarkerItem(QAbstractGraphicsShapeItem, BaseMapItem):
    DEFAULT_MARKER_WIDTH: int = 50
    DEFAULT_MARKER_HEIGHT: int = 70

    def __init__(self, marker: WorldBuildingMarker, parent=None):
        super().__init__(parent)
        self._marker = marker
        self._width = marker.size if marker.size else self.DEFAULT_MARKER_WIDTH
        self._height = int(self._width * (self.DEFAULT_MARKER_HEIGHT / self.DEFAULT_MARKER_WIDTH))
        self.__default_type_size = self._width // 2
        self._typeSize = self.__default_type_size

        self._iconMarker = IconRegistry.from_name('fa5s.map-marker', self._marker.color)
        self._iconMarkerSelected = IconRegistry.from_name('fa5s.map-marker', self._marker.color_selected)
        if self._marker.icon:
            self._iconType = IconRegistry.from_name(self._marker.icon, RELAXED_WHITE_COLOR)
        else:
            self._iconType = QIcon()

        self.setPos(self._marker.x, self._marker.y)

        self._checkRef()

    def setSize(self, size: int):
        self._width = size
        self._height = int(size * (self.DEFAULT_MARKER_HEIGHT / self.DEFAULT_MARKER_WIDTH))
        self.__default_type_size = self._width // 2
        self._typeSize = self.__default_type_size

        self._marker.size = self._width

        self.prepareGeometryChange()
        self.update()
        self.mapScene().markerChangedEvent(self)

    @overrides
    def resetIcon(self):
        self._marker.icon = 'mdi.circle'
        self.refresh()

    @overrides
    def refresh(self):
        self._iconMarker = IconRegistry.from_name('fa5s.map-marker', self._marker.color)
        self._iconMarkerSelected = IconRegistry.from_name('fa5s.map-marker', self._marker.color_selected)
        if self._marker.icon:
            self._iconType = IconRegistry.from_name(self._marker.icon, RELAXED_WHITE_COLOR)

        super().refresh()

    @overrides
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

    @overrides
    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: Optional[QWidget] = ...) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        if self.isSelected():
            painter.setBrush(QColor(RELAXED_WHITE_COLOR))
            marker = self._iconMarkerSelected
        else:
            marker = self._iconMarker
        marker.paint(painter, 0, 0, self._width, self._height)
        if self._marker.icon:
            self._iconType.paint(painter, (self._width - self._typeSize) // 2,
                                 int((self._height - self._typeSize) * 1 / 3),
                                 self._typeSize,
                                 self._typeSize)

    @overrides
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._posChangedTimer.start()
            scene = self.mapScene()
            if scene:
                scene.itemMovedEvent(self)
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            self._onSelection(value)
        return super().itemChange(change, value)

    @overrides
    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._hoverEnter(event)

    @overrides
    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._hoverLeave(event)


class BaseMapAreaItem(BaseMapItem):

    def __init__(self):
        super().__init__()
        self._iconItem: Optional[IconBadge] = None

    def setMarker(self, marker: WorldBuildingMarker):
        self._marker = marker
        self.setPen(QPen(Qt.GlobalColor.black, 1))
        color = QColor(marker.color)
        color.setAlpha(125)
        self.setBrush(color)
        if self._marker.icon:
            self._initIconItem()
            self._iconItem.setIcon(IconRegistry.from_name(self._marker.icon, RELAXED_WHITE_COLOR))

        self._checkRef()

    @overrides
    def setIcon(self, icon: str):
        self._marker.icon = icon
        if self._iconItem is None:
            self._initIconItem()

        self._iconItem.setIcon(IconRegistry.from_name(self._marker.icon, RELAXED_WHITE_COLOR))
        self._iconItem.setVisible(True)
        self.refresh()

    @overrides
    def resetIcon(self):
        if self._iconItem:
            self._iconItem.setVisible(False)

    def setOpacityDiff(self, diff: int):
        self._marker.opacity = diff
        self._checkRef()

        self.mapScene().markerChangedEvent(self)

    @overrides
    def refresh(self):
        color = QColor(self._marker.color)
        color.setAlpha(125)
        self.setBrush(color)

        if self._marker.icon:
            self._iconItem.setIcon(IconRegistry.from_name(self._marker.icon, RELAXED_WHITE_COLOR))
        super().refresh()

    @overrides
    def _effectWithRef(self) -> Optional[QGraphicsEffect]:
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(0.7 + self._marker.opacity / 100)
        return effect

    def _initIconItem(self):
        self._iconItem = IconBadge(self, borderEnabled=False)
        self._iconItem.setVisible(True)
        self._iconItem.setPos(self.boundingRect().center().x() - 16,
                              self.boundingRect().center().y() - 16)


class AreaSquareItem(QGraphicsRectItem, BaseMapAreaItem):
    def __init__(self, marker: WorldBuildingMarker, rect: QRectF, parent=None):
        super().__init__(rect, parent)
        self.setMarker(marker)

    @overrides
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._posChangedTimer.start()
            scene = self.mapScene()
            if scene:
                scene.itemMovedEvent(self)
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            self._onSelection(value)
        return super().itemChange(change, value)

    @overrides
    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._hoverEnter(event)

    @overrides
    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._hoverLeave(event)

    @overrides
    def _posChangedOnTimeout(self):
        self._posChangedTimer.stop()
        self._marker.x = self.rect().x() + self.scenePos().x()
        self._marker.y = self.rect().y() + self.scenePos().y()
        scene = self.mapScene()
        if scene:
            scene.markerChangedEvent(self)


class AreaCircleItem(QGraphicsEllipseItem, BaseMapAreaItem):
    def __init__(self, marker: WorldBuildingMarker, rect: QRectF, parent=None):
        super().__init__(rect, parent)
        self.setMarker(marker)

    @overrides
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._posChangedTimer.start()
            scene = self.mapScene()
            if scene:
                scene.itemMovedEvent(self)
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            self._onSelection(value)
        return super().itemChange(change, value)

    @overrides
    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._hoverEnter(event)

    @overrides
    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._hoverLeave(event)

    @overrides
    def _posChangedOnTimeout(self):
        self._posChangedTimer.stop()
        self._marker.x = self.rect().x() + self.scenePos().x()
        self._marker.y = self.rect().y() + self.scenePos().y()
        scene = self.mapScene()
        if scene:
            scene.markerChangedEvent(self)


class AreaCustomPathItem(QGraphicsPathItem, BaseMapAreaItem):
    def __init__(self, marker: WorldBuildingMarker, path: QPainterPath, parent=None):
        super().__init__(path, parent)
        self.setMarker(marker)
        self._threshold = 5
        self._last_point = None

    @overrides
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._posChangedTimer.start()
            scene = self.mapScene()
            if scene:
                scene.itemMovedEvent(self)
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            self._onSelection(value)
        return super().itemChange(change, value)

    @overrides
    def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._hoverEnter(event)

    @overrides
    def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent') -> None:
        self._hoverLeave(event)

    def addPoint(self, point: QPointF):
        path = self.path()
        if self._last_point is None:
            path.moveTo(point)
            self._last_point = point
        else:
            if self._distance(self._last_point, point) < self._threshold:
                return
            path.lineTo(point)
            self._last_point = point
            self._marker.points.append(Point(int(point.x()), int(point.y())))

        self.setPath(path)

    def finish(self, point: QPointF):
        path = self.path()
        path.lineTo(point)
        self.setPath(path)

        self._last_point = None

    def _distance(self, p1: QPointF, p2: QPointF) -> float:
        return math.hypot(p2.x() - p1.x(), p2.y() - p1.y())

    @overrides
    def _posChangedOnTimeout(self):
        self._posChangedTimer.stop()
        self._marker.x += self.scenePos().x()
        self._marker.y += self.scenePos().y()
        for point in self._marker.points:
            point.x += self.scenePos().x()
            point.y += self.scenePos().y()
        scene = self.mapScene()
        if scene:
            scene.markerChangedEvent(self)


class AreaSelectorWidget(SecondarySelectorWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._btnSquare = self.addItemTypeButton(GraphicsItemType.MAP_AREA_SQUARE,
                                                 IconRegistry.from_name('mdi.select'),
                                                 'Select a square-shaped area', 0, 0)
        self._btnCircle = self.addItemTypeButton(GraphicsItemType.MAP_AREA_CIRCLE,
                                                 IconRegistry.from_name('mdi.selection-ellipse'),
                                                 'Select a circle-shaped area', 1, 0)
        self._btnCustom = self.addItemTypeButton(GraphicsItemType.MAP_AREA_CUSTOM,
                                                 IconRegistry.from_name('mdi.draw'),
                                                 'Draw and select a custom area', 2, 0)

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        self._btnCustom.setChecked(True)


class WorldBuildingMapScene(QGraphicsScene):
    showPopup = pyqtSignal(BaseMapItem)
    hidePopup = pyqtSignal()
    cancelItemAddition = pyqtSignal()
    itemAdded = pyqtSignal()
    itemMoved = pyqtSignal()

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._map: Optional[WorldBuildingMap] = None
        self._animParent = QObject()
        self._additionDescriptor: Optional[GraphicsItemType] = None
        self._area_start_point = None
        self._current_area_item: Optional[BaseMapItem] = None

        self.repo = RepositoryPersistenceManager.instance()

    def map(self) -> Optional[WorldBuildingMap]:
        return self._map

    def isAdditionMode(self) -> bool:
        return self._additionDescriptor is not None

    def isAreaAdditionMode(self) -> bool:
        if self._additionDescriptor and self._additionDescriptor.name.startswith('MAP_AREA'):
            return True
        return False

    def showPopupEvent(self, item: MarkerItem):
        self.showPopup.emit(item)

    def hidePopupEvent(self):
        self.hidePopup.emit()

    @overrides
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            if self.isAdditionMode():
                self.cancelItemAddition.emit()
                self.endAdditionMode()

        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            for item in self.selectedItems():
                self._removeItem(item)

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
        if event.mimeData().hasFormat(GraphicsItemType.MAP_MARKER.mimeType()):
            self._addMarker(event.scenePos())
            event.accept()
        else:
            event.ignore()

    @busy
    def loadMap(self, map: WorldBuildingMap) -> Optional[QGraphicsPixmapItem]:
        self.clear()
        if map.ref:
            image: Optional[QImage] = load_image(self._novel, map.ref)
        else:
            image = QImage(resource_registry.paper_bg)
        if image:
            self._map = map
            item = QGraphicsPixmapItem()
            item.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
            item.setPixmap(QPixmap.fromImage(image))
            self.addItem(item)

            for marker in self._map.markers:
                if marker.type == GraphicsItemType.MAP_MARKER:
                    markerItem = MarkerItem(marker)
                elif marker.type == GraphicsItemType.MAP_AREA_SQUARE:
                    rect = QRectF(marker.x, marker.y, marker.width, marker.height)
                    markerItem = AreaSquareItem(marker, rect)
                elif marker.type == GraphicsItemType.MAP_AREA_CIRCLE:
                    rect = QRectF(marker.x, marker.y, marker.width, marker.height)
                    markerItem = AreaCircleItem(marker, rect)
                elif marker.type == GraphicsItemType.MAP_AREA_CUSTOM:
                    path = QPainterPath(QPointF(marker.x, marker.y))
                    for point in marker.points:
                        path.lineTo(point.x, point.y)
                    path.lineTo(marker.x, marker.y)
                    markerItem = AreaCustomPathItem(marker, path)
                else:
                    continue
                self.addItem(markerItem)
                markerItem.activate()

            return item
        else:
            self._map = None

    @overrides
    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if self.isAreaAdditionMode() and event.button() == Qt.MouseButton.LeftButton:
            self._addArea(event.scenePos())
        super().mousePressEvent(event)

    @overrides
    def mouseMoveEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if self._current_area_item:
            current_point = event.scenePos()
            if self._additionDescriptor != GraphicsItemType.MAP_AREA_CUSTOM:
                rect = QRectF(self._area_start_point,
                              current_point).normalized()  # normalize to handle negative coordinates
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    size = min(rect.width(), rect.height())
                    rect = QRectF(self._area_start_point, self._area_start_point + QPointF(size, size)).normalized()
                self._current_area_item.setRect(rect)
                self._current_area_item.marker().width = int(rect.width())
                self._current_area_item.marker().height = int(rect.height())
            else:
                self._current_area_item.addPoint(event.scenePos())

        super().mouseMoveEvent(event)

    @overrides
    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent') -> None:
        if self._current_area_item:
            if self._additionDescriptor == GraphicsItemType.MAP_AREA_CUSTOM:
                self._current_area_item.finish(self._area_start_point)
                self.repo.update_world(self._novel)

            self._current_area_item.activate()

        self._area_start_point = None
        self._current_area_item = None
        if self.isAdditionMode() and event.button() & Qt.MouseButton.RightButton:
            self.cancelItemAddition.emit()
            self.endAdditionMode()
        elif self.isAdditionMode():
            if self._additionDescriptor == GraphicsItemType.MAP_MARKER:
                self._addMarker(event.scenePos())
            elif self.isAreaAdditionMode():
                self.cancelItemAddition.emit()
                self.endAdditionMode()

        super().mouseReleaseEvent(event)

    @overrides
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._map:
            self._addMarker(event.scenePos())

    def markerChangedEvent(self, _: MarkerItem):
        self.repo.update_world(self._novel)

    def itemMovedEvent(self, _: MarkerItem):
        self.itemMoved.emit()

    def startAdditionMode(self, itemType: GraphicsItemType):
        self._additionDescriptor = itemType

    def endAdditionMode(self):
        self._additionDescriptor = None

    def highlightItem(self, item: BaseMapItem):
        anim = qtanim.glow(item, duration=250, radius=50, loop=1, color=QColor(PLOTLYST_MAIN_COLOR),
                           teardown=item.activate)
        anim.setParent(self._animParent)

    def _addMarker(self, pos: QPointF):
        pos = pos - QPointF(MarkerItem.DEFAULT_MARKER_WIDTH / 2, MarkerItem.DEFAULT_MARKER_HEIGHT)
        marker = WorldBuildingMarker(pos.x(), pos.y())
        self._map.markers.append(marker)
        markerItem = MarkerItem(marker)
        self.addItem(markerItem)
        self.repo.update_world(self._novel)

        anim = qtanim.fade_in(markerItem, teardown=markerItem.activate)
        anim.setParent(self._animParent)

        self.itemAdded.emit()
        self.endAdditionMode()

    def _addArea(self, pos: QPointF):
        self._area_start_point = pos
        marker = WorldBuildingMarker(self._area_start_point.x(), self._area_start_point.y(),
                                     type=self._additionDescriptor, icon='')
        self._map.markers.append(marker)
        if self._additionDescriptor == GraphicsItemType.MAP_AREA_SQUARE:
            self._current_area_item = AreaSquareItem(marker, QRectF(self._area_start_point, self._area_start_point))
        elif self._additionDescriptor == GraphicsItemType.MAP_AREA_CIRCLE:
            self._current_area_item = AreaCircleItem(marker, QRectF(self._area_start_point, self._area_start_point))
        else:
            path = QPainterPath(self._area_start_point)
            self._current_area_item = AreaCustomPathItem(marker, path)
        self.addItem(self._current_area_item)

    def _removeItem(self, item: QGraphicsItem):
        def remove():
            self._map.markers.remove(item.marker())
            self.repo.update_world(self._novel)
            self.removeItem(item)

        anim = qtanim.fade_out(item, teardown=remove, hide_if_finished=False)
        anim.setParent(self._animParent)


class WorldBuildingMapView(BaseGraphicsView):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._shown = False
        self._bgItem: Optional[QGraphicsPixmapItem] = None

        self._wdgZoomBar = ZoomBar(self)
        self._wdgZoomBar.zoomed.connect(self._scale)
        self._wdgZoomBar.setHidden(True)

        self._controlsNavBar = self._roundedFrame()
        sp(self._controlsNavBar).h_max()
        shadow(self._controlsNavBar)
        vbox(self._controlsNavBar, 5, 6)
        self._controlsNavBar.setHidden(True)

        self._btnGroup = ExclusiveOptionalButtonGroup()

        self._btnAddMarker = self._newControlButton(IconRegistry.from_name('fa5s.map-marker'),
                                                    'Add new marker (or double-click on the map)',
                                                    GraphicsItemType.MAP_MARKER)
        self._btnAddArea = self._newControlButton(IconRegistry.from_name('mdi.select'),
                                                  'Add a new area',
                                                  GraphicsItemType.MAP_AREA_CUSTOM)

        self._wdgSecondaryAreaSelector = AreaSelectorWidget(self)
        self._wdgSecondaryAreaSelector.setVisible(False)
        self._wdgSecondaryAreaSelector.selected.connect(self._startAddition)

        # self._wdgEditor = EntityEditorWidget(self)
        # self._wdgEditor.setHidden(True)

        self.undoStack = QUndoStack()
        self.undoStack.setUndoLimit(100)

        self._markerEditor = MarkerItemToolbar(self._novel, self.undoStack, self)
        self._markerEditor.setVisible(False)

        self._popup = PopupText(self)
        self._popup.setHidden(True)

        self._btnEdit = tool_btn(IconRegistry.plus_edit_icon(PLOTLYST_SECONDARY_COLOR), parent=self)
        self._btnEdit.installEventFilter(OpacityEventFilter(self._btnEdit, 0.9, 0.7))
        self._btnEdit.setObjectName('btnEdit')

        self._menuEdit = MenuWidget(self._btnEdit)
        self._menuEdit.setTooltipDisplayMode(ActionTooltipDisplayMode.DISPLAY_UNDER)
        self._menuEdit.aboutToShow.connect(self._fillUpEditMenu)

        self.setBackgroundBrush(QColor('#F2F2F2'))
        self._scene = WorldBuildingMapScene(self._novel)
        self.setScene(self._scene)
        self._scene.selectionChanged.connect(self._selectionChanged)
        self._scene.showPopup.connect(self._showPopup)
        self._scene.hidePopup.connect(self._hidePopup)
        self._scene.itemAdded.connect(self._endAddition)
        self._scene.itemMoved.connect(self._itemMoved)
        self._scene.cancelItemAddition.connect(self._endAddition)
        # self._wdgEditor.changed.connect(self._scene.markerChangedEvent)

        self.repo = RepositoryPersistenceManager.instance()

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        if not self._shown:
            self._shown = True
            if self._novel.world.maps:
                self._loadMap(self._novel.world.maps[0])

    @overrides
    def itemAt(self, pos: QPoint) -> QGraphicsItem:
        item = super().itemAt(pos)
        if self._bgItem and item is self._bgItem:
            return None

        return item

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._arrangeSideBars()

    @overrides
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._scene.isAreaAdditionMode():
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        super().mousePressEvent(event)

    @overrides
    def _scale(self, scale: float):
        super()._scale(scale)
        self._wdgZoomBar.updateScaledFactor(self.scaledFactor())

    def _arrangeSideBars(self):
        self._wdgZoomBar.setGeometry(10, self.height() - self._wdgZoomBar.sizeHint().height() - 25,
                                     self._wdgZoomBar.sizeHint().width(),
                                     self._wdgZoomBar.sizeHint().height())
        self.__arrangeEditBtn()

        self._controlsNavBar.setGeometry(10, 100, self._controlsNavBar.sizeHint().width(),
                                         self._controlsNavBar.sizeHint().height())

        secondary_x = self._controlsNavBar.pos().x() + self._controlsNavBar.sizeHint().width() + 5
        secondary_y = self._controlsNavBar.pos().y() + self._btnAddArea.pos().y()
        self._wdgSecondaryAreaSelector.setGeometry(secondary_x, secondary_y,
                                                   self._wdgSecondaryAreaSelector.sizeHint().width(),
                                                   self._wdgSecondaryAreaSelector.sizeHint().height())

    def __arrangeEditBtn(self):
        self._btnEdit.setGeometry(self.width() - self._btnEdit.sizeHint().width() - 20,
                                  self.height() - self._btnEdit.sizeHint().height() - 20,
                                  self._btnEdit.sizeHint().width(),
                                  self._btnEdit.sizeHint().height())

    def _newControlButton(self, icon: QIcon, tooltip: str, itemType: GraphicsItemType):
        btn = tool_btn(icon, tooltip,
                       True, icon_resize=False,
                       properties=['transparent-rounded-bg-on-hover', 'top-selector'],
                       parent=self._controlsNavBar)
        btn.installEventFilter(DragEventFilter(btn, itemType.mimeType(), lambda x: itemType))

        btn.installEventFilter(TooltipPositionEventFilter(btn))
        incr_icon(btn, 2)

        self._btnGroup.addButton(btn)
        self._controlsNavBar.layout().addWidget(btn)
        btn.clicked.connect(partial(self._mainControlClicked, itemType))

        return btn

    def _mainControlClicked(self, itemType: GraphicsItemType, checked: bool):
        if checked:
            self._startAddition(itemType)
        else:
            self._endAddition()
            self._scene.endAdditionMode()

    def _startAddition(self, itemType: GraphicsItemType):
        for btn in self._btnGroup.buttons():
            if not btn.isChecked():
                btn.setDisabled(True)

        if not QApplication.overrideCursor():
            QApplication.setOverrideCursor(Qt.CursorShape.PointingHandCursor)

        if itemType.name.startswith('MAP_AREA'):
            self._wdgSecondaryAreaSelector.setVisible(True)
        else:
            self._wdgSecondaryAreaSelector.setVisible(False)

        self._scene.startAdditionMode(itemType)

    def _endAddition(self):
        for btn in self._btnGroup.buttons():
            btn.setEnabled(True)
            if btn.isChecked():
                btn.setChecked(False)

        self._wdgSecondaryAreaSelector.setHidden(True)
        QApplication.restoreOverrideCursor()

    def _loadMap(self, map: WorldBuildingMap):
        self._bgItem = self._scene.loadMap(map)
        if self._bgItem is None:
            return

        if map.dominant_color:
            bg_color = QColor(map.dominant_color)
        else:
            bg_color = dominant_color(self._bgItem.pixmap())
            map.dominant_color = bg_color.name()
        self.setBackgroundBrush(bg_color)
        # call to calculate rect size
        _ = self._scene.sceneRect()
        self.centerOn(self._bgItem)
        self._controlsNavBar.setVisible(True)
        self._wdgZoomBar.setVisible(True)

        if map.ref:
            self._btnEdit.setIconSize(QSize(32, 32))
            self._btnEdit.setStyleSheet(f'''
                    #btnEdit {{
                        border: 2px solid {PLOTLYST_SECONDARY_COLOR};
                        border-radius: 26px;
                        background: {RELAXED_WHITE_COLOR};
                        padding: 8px;
                    }}
                    ''')
        else:
            self._btnEdit.setIconSize(QSize(48, 48))
            self._btnEdit.setStyleSheet(f'''
                    #btnEdit {{
                        border: 2px solid {PLOTLYST_SECONDARY_COLOR};
                        border-radius: 36px;
                        background: {RELAXED_WHITE_COLOR};
                        padding: 10px;
                    }}
                    ''')
        restyle(self._btnEdit)
        self.__arrangeEditBtn()

    def _addNewMap(self):
        loadedImage: Optional[LoadedImage] = upload_image(self._novel)
        if loadedImage:
            if not self._novel.world.maps:
                map = WorldBuildingMap(loadedImage.ref)
                self._novel.world.maps.append(map)
            else:
                map = self._novel.world.maps[0]
                map.ref = loadedImage.ref
                map.dominant_color = ''
            self._loadMap(map)
            self.repo.update_world(self._novel)

    def _selectionChanged(self):
        if sip.isdeleted(self._scene):
            return
        if len(self._scene.selectedItems()) == 1:
            item = self._scene.selectedItems()[0]
            self._markerEditor.setMarker(item)
            self._hidePopup()
            self._popupAbove(self._markerEditor, item)
        else:
            self._markerEditor.setVisible(False)

    def _showPopup(self, item: BaseMapItem):
        location = entities_registry.location(str(item.marker().ref))
        if location:
            self._popup.setText(location.name, location.summary)
            self._popupAbove(self._popup, item)

    def _hidePopup(self):
        self._popup.setHidden(True)

    def _itemMoved(self):
        self._markerEditor.setVisible(False)
        self._hidePopup()

    def _fillUpEditMenu(self):
        self._menuEdit.clear()
        addAction = action('Add map', IconRegistry.plus_icon(), tooltip="Upload an image for your map",
                           slot=self._addNewMap)
        if self._scene.map() and self._scene.map().ref:
            addAction.setText('Replace map')
            addAction.setToolTip('Replace your current map with a new image')
        self._menuEdit.addAction(addAction)
