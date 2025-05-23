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
from functools import partial
from typing import Optional, Dict, List

import qtanim
from PyQt6.QtCore import QPointF, Qt, QRectF, pyqtSignal, QSize
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsView, QGraphicsItem, QGraphicsOpacityEffect, QSlider, QWidget
from overrides import overrides
from qthandy import decr_font, vbox, translucent, flow, sp, hbox
from qthandy.filter import OpacityEventFilter

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import GraphicsItemType, Diagram, DiagramData, Novel, Node, DynamicPlotPrincipleGroup, \
    DynamicPlotPrinciple, Character, DynamicPlotPrincipleType
from plotlyst.service.cache import entities_registry
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import shadow, frame, tool_btn, fade_out_and_gc, insert_before_the_end
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.characters import CharacterSelectorMenu
from plotlyst.view.widget.display import IconText
from plotlyst.view.widget.graphics import NetworkGraphicsView, NetworkScene, NodeItem, CharacterItem, \
    PlaceholderSocketItem, ConnectorItem
from plotlyst.view.widget.graphics.items import IconItem
from plotlyst.view.widget.plot.progression import DynamicPlotPrincipleWidget


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
        self.label.setText('Sympathy')
        translucent(self.label, 0.7)
        translucent(self.slider, 0.7)
        self.label.setIcon(IconRegistry.from_name('fa5.heart', '#f25c54'))
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
        self.__addIcon(Node(355, 195, GraphicsItemType.ICON, icon='fa5.heart', color='#f25c54', size=20))
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
        self.setBackgroundBrush(QColor(RELAXED_WHITE_COLOR))
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


class AllyPlotPrincipleWidget(DynamicPlotPrincipleWidget):
    def __init__(self, novel: Novel, principle: DynamicPlotPrinciple, parent=None,
                 nameAlignment=Qt.AlignmentFlag.AlignCenter):
        super().__init__(novel, principle, parent, nameAlignment)
        if self.principle.node is None:
            self._btnName.setText('Ally/Enemy')

    def updateAlly(self):
        self._btnName.setIcon(IconRegistry.from_name(self.principle.type.icon(), self._color()))
        self._initStyle(name=self.principle.type.display_name(), desc=self.principle.type.placeholder())
        qcolor = QColor(self._color())
        qcolor.setAlpha(125)
        shadow(self._text, color=qcolor)

    @overrides
    def _color(self) -> str:
        if self.principle.node is None:
            return 'grey'
        return super()._color()


class AlliesPrinciplesGroupWidget(QWidget):
    changed = pyqtSignal()

    def __init__(self, novel: Novel, principleGroup: DynamicPlotPrincipleGroup, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.group = principleGroup

        self._wdgPrinciples = QWidget()
        flow(self._wdgPrinciples)

        self._supporterSlider = AlliesSupportingSlider()
        self._emotionSlider = AlliesEmotionalSlider()

        self._leftEditor = QWidget()
        sp(self._leftEditor).h_max()
        vbox(self._leftEditor, spacing=0)
        self._toolbar = frame()
        self._toolbar.setProperty('relaxed-white-bg', True)
        self._toolbar.setProperty('rounded-on-top', True)
        hbox(self._toolbar)
        self._toolbar.layout().addWidget(self._supporterSlider)
        self._toolbar.layout().addWidget(self._emotionSlider)

        self.view = AlliesGraphicsView(self.novel, self.group)

        self._leftEditor.layout().addWidget(self._toolbar)
        self._leftEditor.layout().addWidget(self.view)

        hbox(self)
        self.layout().addWidget(self._leftEditor, alignment=Qt.AlignmentFlag.AlignTop)
        self.layout().addWidget(self._wdgPrinciples)

        self.btnAdd = tool_btn(IconRegistry.plus_icon('grey'), transparent_=True)
        self.btnAdd.installEventFilter(OpacityEventFilter(self.btnAdd))
        self.btnAdd.setIconSize(QSize(48, 48))
        self.btnAdd.setFixedHeight(200)
        self.btnAdd.clicked.connect(self._addAlly)
        self._wdgPrinciples.layout().addWidget(self.btnAdd)

        for principle in self.group.principles:
            self._initBubbleWidget(principle)

        self.view.alliesScene().posChanged.connect(self._posChanged)
        self.view.alliesScene().allyChanged.connect(self._allyChanged)

        self._supporterSlider.setPrinciples(self.group.principles)
        self._emotionSlider.setPrinciples(self.group.principles)

    def refreshCharacters(self):
        for i in range(self._wdgPrinciples.layout().count()):
            item = self._wdgPrinciples.layout().itemAt(i)
            if item.widget() and isinstance(item.widget(), AllyPlotPrincipleWidget):
                wdg: AllyPlotPrincipleWidget = item.widget()
                wdg.refreshCharacters()

    def _addAlly(self):
        principle = DynamicPlotPrinciple(type=DynamicPlotPrincipleType.NEUTRAL)
        self.group.principles.append(principle)
        self.view.addNewAlly(principle)
        self._initBubbleWidget(principle)

        self.changed.emit()

    def _removeAlly(self, bubble: AllyPlotPrincipleWidget):
        self.view.removeAlly(bubble.principle)
        self.group.principles.remove(bubble.principle)
        fade_out_and_gc(self._wdgPrinciples, bubble)

        self.changed.emit()

    def _posChanged(self, _: DynamicPlotPrinciple):
        self._supporterSlider.setPrinciples(self.group.principles)
        self._emotionSlider.setPrinciples(self.group.principles)

        self.changed.emit()

    def _allyChanged(self, principle: DynamicPlotPrinciple):
        for i in range(self._wdgPrinciples.layout().count()):
            item = self._wdgPrinciples.layout().itemAt(i)
            if item.widget() and isinstance(item.widget(), AllyPlotPrincipleWidget):
                wdg: AllyPlotPrincipleWidget = item.widget()
                if wdg.principle == principle:
                    wdg.updateAlly()
                    break

        self.changed.emit()

    def _initBubbleWidget(self, principle: DynamicPlotPrinciple):
        bubble = AllyPlotPrincipleWidget(self.novel, principle)
        bubble.removed.connect(partial(self._removeAlly, bubble))
        bubble.characterChanged.connect(partial(self.view.updateAlly, principle))
        insert_before_the_end(self._wdgPrinciples, bubble)
