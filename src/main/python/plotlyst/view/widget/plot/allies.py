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
from typing import Optional, Dict, List

import qtanim
from PyQt6.QtCore import QPointF, Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsView, QGraphicsItem, QGraphicsOpacityEffect, QSlider, QWidget
from overrides import overrides
from qthandy import decr_font, vbox, translucent

from plotlyst.core.domain import GraphicsItemType, Diagram, DiagramData, Novel, Node, DynamicPlotPrincipleGroup, \
    DynamicPlotPrinciple, Character, DynamicPlotPrincipleType
from plotlyst.service.cache import entities_registry
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.theme import BG_PRIMARY_COLOR
from plotlyst.view.widget.characters import CharacterSelectorMenu
from plotlyst.view.widget.display import IconText
from plotlyst.view.widget.graphics import NetworkGraphicsView, NetworkScene, NodeItem, CharacterItem, \
    PlaceholderSocketItem, ConnectorItem
from plotlyst.view.widget.graphics.items import IconItem


class AlliesSupportingSlider(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.slider = QSlider()
        self.slider.setOrientation(Qt.Orientation.Horizontal)
        self.slider.setProperty('ally-enemy', True)
        self.slider.setEnabled(False)

        vbox(self)
        self.label = IconText()
        self.label.setText('Support')
        translucent(self.label, 0.7)
        translucent(self.slider, 0.7)
        self.label.setIcon(IconRegistry.from_name('fa5s.thumbs-up'))
        self.layout().addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.slider)

    def setPrinciples(self, principles: List[DynamicPlotPrinciple]):
        ally = 0
        enemy = 0
        for principle in principles:
            if principle.node is None:
                continue
            y = principle.node.y - ALLY_SEPARATOR
            if y > 0:
                enemy += y
            elif y == 0:
                ally += 1
                enemy += 1
            else:
                ally += y

        self.slider.setMaximum(int(abs(ally) + enemy))
        self.slider.setValue(int(abs(ally)))

        if abs(ally) >= enemy:
            self.label.setIcon(IconRegistry.from_name('fa5s.thumbs-up', '#266dd3'))
        else:
            self.label.setIcon(IconRegistry.from_name('fa5s.thumbs-down', '#9e1946'))


class AlliesEmotionalSlider(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.slider = QSlider()
        self.slider.setOrientation(Qt.Orientation.Horizontal)
        self.slider.setProperty('relationship', True)
        self.slider.setEnabled(False)

        vbox(self)
        self.label = IconText()
        self.label.setText('Relationship')
        translucent(self.label, 0.7)
        translucent(self.slider, 0.7)
        self.label.setIcon(IconRegistry.from_name('fa5s.heart', '#f25c54'))
        self.layout().addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.slider)

    def setPrinciples(self, principles: List[DynamicPlotPrinciple]):
        pos = 0
        neg = 0
        for principle in principles:
            if principle.node is None:
                continue
            x = principle.node.x - POSITIVE_RELATION_SEPARATOR
            if x > 0:
                pos += x
            else:
                neg += x

        self.slider.setMaximum(int(abs(neg) + pos))
        self.slider.setValue(int(pos))


ALLY_SEPARATOR: int = 165
POSITIVE_RELATION_SEPARATOR: int = 155


class AlliesGraphicsScene(NetworkScene):
    posChanged = pyqtSignal(DynamicPlotPrinciple)
    allyChanged = pyqtSignal(DynamicPlotPrinciple)

    def __init__(self, novel: Novel, principleGroup: DynamicPlotPrincipleGroup, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._group = principleGroup
        self._anim = None
        self._principles: Dict[Node, DynamicPlotPrinciple] = {}

        self.repo = RepositoryPersistenceManager.instance()

        diagram = Diagram('Allies')
        diagram.data = DiagramData()

        for principle in self._group.principles:
            if principle.node is None:
                self.__initNode(principle)
            self._principles[principle.node] = principle

            diagram.data.nodes.append(principle.node)

        self.setDiagram(diagram)

        socket1 = PlaceholderSocketItem()
        socket1.setPos(0, 200)
        socket2 = PlaceholderSocketItem()
        socket2.setPos(375, 200)
        hline = ConnectorItem(socket1, socket2)
        hline.setColor(QColor('grey'))
        hline.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        hline.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)

        self.addItem(socket1)
        self.addItem(socket2)
        self.addItem(hline)

        mid = 375 // 2
        socket1 = PlaceholderSocketItem()
        socket1.setPos(mid, 385)
        socket2 = PlaceholderSocketItem()
        socket2.setPos(mid, 5)
        vline = ConnectorItem(socket1, socket2)
        vline.setColor(QColor('grey'))
        vline.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        vline.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)

        self.addItem(socket1)
        self.addItem(socket2)
        self.addItem(vline)

        self.__addIcon(Node(mid - 7, -18, GraphicsItemType.ICON, icon='fa5s.thumbs-up', color='#266dd3', size=20))
        self.__addIcon(Node(mid - 7, 360, GraphicsItemType.ICON, icon='fa5s.thumbs-down', color='#9e1946', size=20))
        self.__addIcon(Node(355, 195, GraphicsItemType.ICON, icon='fa5s.heart', color='#f25c54', size=20))
        # self.__addIcon(Node(-17, 195, GraphicsItemType.ICON, icon='fa5s.angry', color='#ef0000', size=20))

    def addNewAlly(self, principle: DynamicPlotPrinciple):
        self.__initNode(principle)
        self._principles[principle.node] = principle
        self._diagram.data.nodes.append(principle.node)
        item = self._addNode(principle.node)

        self._anim = qtanim.fade_in(item)

    def removeAlly(self, principle: DynamicPlotPrinciple):
        item = self.__findItem(principle)
        if item:
            self._principles.pop(item.node())
            self._removeItem(item)

    def updateAlly(self, principle: DynamicPlotPrinciple, character: Character):
        item = self.__findItem(principle)
        if item:
            item.setCharacter(character)

    @overrides
    def itemMovedEvent(self, item: NodeItem):
        super().itemMovedEvent(item)
        principle = self._principles[item.node()]
        principle.node.x = item.pos().x()
        principle.node.y = item.pos().y()

        if item.pos().y() > ALLY_SEPARATOR:
            new_type = DynamicPlotPrincipleType.ENEMY
        elif item.pos().y() == ALLY_SEPARATOR:
            new_type = DynamicPlotPrincipleType.NEUTRAL
        else:
            new_type = DynamicPlotPrincipleType.ALLY

        if principle.type != new_type:
            principle.type = new_type
            self.allyChanged.emit(principle)

        self.posChanged.emit(principle)

    @overrides
    def _addNewDefaultItem(self, pos: QPointF):
        pass

    @overrides
    def _addNode(self, node: Node) -> NodeItem:
        item = super()._addNode(node)

        if isinstance(item, CharacterItem):
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
            item.setConfinedRect(QRectF(-10, -10, 320, 330))
            item.setStickPoint(QPointF(0, ALLY_SEPARATOR), 15)
            item.setZValue(1)
            item.setDoubleClickEditEnabled(False)
            item.setCursor(Qt.CursorShape.OpenHandCursor)
            decr_font(item.labelItem(), 3)
            item.updateLabel()

        return item

    @overrides
    def _save(self):
        self.repo.update_novel(self._novel)

    def __initNode(self, principle: DynamicPlotPrinciple):
        character_id = None
        if principle.character_id:
            character = entities_registry.character(principle.character_id)
            if character:
                character_id = character.id
        principle.node = Node(0, 0, type=GraphicsItemType.CHARACTER, size=40, character_id=character_id)
        self._save()

    def __addIcon(self, node: Node):
        icon = IconItem(node)
        icon.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        icon.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        icon.setDoubleClickEditEnabled(False)
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(0.5)
        icon.setGraphicsEffect(effect)
        self.addItem(icon)

    def __findItem(self, principle: DynamicPlotPrinciple) -> Optional[CharacterItem]:
        for item in self.items():
            if isinstance(item, CharacterItem):
                if item.node() == principle.node:
                    return item


class AlliesGraphicsView(NetworkGraphicsView):
    def __init__(self, novel: Novel, principleGroup: DynamicPlotPrincipleGroup, parent=None):
        self._novel = novel
        self._group = principleGroup
        super().__init__(parent)
        self.setBackgroundBrush(QColor(BG_PRIMARY_COLOR))
        self.setRubberBandEnabled(False)
        self.setScalingEnabled(False)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setSceneRect(15, 15, 370, 370)
        self.setFixedSize(400, 400)

        self._controlsNavBar.setHidden(True)
        self._wdgZoomBar.setHidden(True)

    def alliesScene(self) -> AlliesGraphicsScene:
        return self._scene

    def addNewAlly(self, item: DynamicPlotPrinciple):
        self._scene.addNewAlly(item)

    def removeAlly(self, item: DynamicPlotPrinciple):
        self._scene.removeAlly(item)

    def updateAlly(self, item: DynamicPlotPrinciple, character: Character):
        self._scene.updateAlly(item, character)

    @overrides
    def _initScene(self) -> NetworkScene:
        return AlliesGraphicsScene(self._novel, self._group)

    @overrides
    def _characterSelectorMenu(self) -> CharacterSelectorMenu:
        return CharacterSelectorMenu(self._novel, parent=self)
