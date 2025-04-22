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
from typing import Optional, List, Dict

from PyQt6.QtCore import pyqtSignal
from overrides import overrides
from qthandy import clear_layout, vspacer

from plotlyst.common import recursive
from plotlyst.core.domain import WorldConceit, WorldBuilding, WorldConceitType, Novel
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import fade_in
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.input import TextEditBubbleWidget
from plotlyst.view.widget.tree import ItemBasedNode, TreeSettings, ItemBasedTreeView, ContainerNode
from plotlyst.view.widget.world.theme import WorldBuildingPalette


class ConceitBubble(TextEditBubbleWidget):
    nameEdited = pyqtSignal()
    textChanged = pyqtSignal()
    iconChanged = pyqtSignal()

    def __init__(self, conceit: WorldConceit, palette: WorldBuildingPalette, parent=None):
        super().__init__(parent, titleEditable=True, titleMaxWidth=150, iconEditable=True)
        self.conceit = conceit
        self.palette = palette

        self._removalEnabled = True

        icon = self.conceit.icon if self.conceit.icon else self.conceit.type.icon()
        color = self.conceit.icon_color if self.conceit.icon_color else self.palette.primary_color
        self._title.setIcon(IconRegistry.from_name(icon, color))
        self._title.setText(self.conceit.name)
        self._title.lineEdit.textEdited.connect(self._titleEdited)
        self._title.iconChanged.connect(self._iconChanged)
        self._textedit.setPlaceholderText('An element of wonder that deviates from our world')
        self._textedit.setStyleSheet(f'''
            QTextEdit {{
                border: 1px solid {self.palette.secondary_color};
                border-radius: 6px;
                padding: 4px;
                background-color: {self.palette.tertiary_color};
            }}
        ''')
        self._textedit.setText(self.conceit.text)

    def _titleEdited(self, text: str):
        self.conceit.name = text
        self.nameEdited.emit()

    def _textChanged(self):
        self.conceit.text = self._textedit.toPlainText()
        self.textChanged.emit()

    def _iconChanged(self, icon: str, color: str):
        self.conceit.icon = icon
        if color == 'black' or color == '#000000':
            color = self.palette.primary_color
            self._title.setIcon(IconRegistry.from_name(icon, color))
        self.conceit.icon_color = color
        self.iconChanged.emit()


class ConceitNode(ItemBasedNode):
    added = pyqtSignal()

    def __init__(self, conceit: WorldConceit, parent=None, readOnly: bool = False,
                 settings: Optional[TreeSettings] = None):
        super().__init__(conceit.name, parent=parent, settings=settings)
        self._conceit = conceit
        self.setPlusButtonEnabled(not readOnly)
        self.setMenuEnabled(not readOnly)
        self.setTranslucentIconEnabled(True)
        self._actionChangeIcon.setVisible(False)
        self._btnAdd.clicked.connect(self.added)
        self.refresh()
        self._icon.setVisible(True)

    @overrides
    def item(self) -> WorldConceit:
        return self._conceit

    @overrides
    def refresh(self):
        self._lblTitle.setText(self._conceit.name if self._conceit.name else 'Conceit')
        if self._conceit.icon:
            self._icon.setIcon(IconRegistry.from_name(self._conceit.icon, self._conceit.icon_color))
        else:
            self._icon.setIcon(IconRegistry.dot_icon())

    @overrides
    def _iconChanged(self, iconName: str, iconColor: str):
        pass


class ConceitRootNode(ItemBasedNode):
    def __init__(self, root: WorldConceit, parent=None, settings: Optional[TreeSettings] = None):
        super().__init__('Conceits', parent, settings=settings)
        self._root = root
        self.setMenuEnabled(False)
        self.setPlusButtonEnabled(False)

    @overrides
    def item(self) -> WorldConceit:
        return self._root


class ConceitTypeNode(ItemBasedNode):
    def __init__(self, conceit: WorldConceit, parent=None, settings: Optional[TreeSettings] = None):
        super().__init__(conceit.name, IconRegistry.from_name(conceit.type.icon()), parent, settings=settings)
        self._conceit = conceit
        self.setMenuEnabled(False)
        self.setPlusButtonEnabled(False)

    @overrides
    def item(self) -> WorldConceit:
        return self._conceit


class ConceitsTreeView(ItemBasedTreeView):
    CONCEIT_ENTITY_MIMETYPE = 'application/world-conceit'
    conceitSelected = pyqtSignal(WorldConceit)
    rootSelected = pyqtSignal()
    conceitTypeSelected = pyqtSignal(WorldConceitType)
    conceitDeleted = pyqtSignal(WorldConceit)

    def __init__(self, novel: Novel, palette: WorldBuildingPalette, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._palette = palette
        self._world: WorldBuilding = novel.world
        self._readOnly = False
        self._settings = TreeSettings(bg_color=self._palette.bg_color,
                                      action_buttons_color=self._palette.primary_color,
                                      selection_bg_color=self._palette.secondary_color,
                                      hover_bg_color=self._palette.tertiary_color,
                                      selection_text_color=self._palette.primary_color)
        self._centralWidget.setStyleSheet(f'#centralWidget {{background: {self._settings.bg_color};}}')
        self._root = WorldConceit('Conceits', None)
        self._rootNode: Optional[ConceitRootNode] = None

        self.repo = RepositoryPersistenceManager.instance()

        self.refresh()

    def refresh(self):
        def addChildWdg(parent: WorldConceit, child: WorldConceit):
            childWdg = self._initNode(child)
            self._nodes[parent].addChild(childWdg)

        self.clearSelection()
        self._nodes.clear()
        clear_layout(self._centralWidget)

        self._rootNode = ConceitRootNode(self._root, settings=self._settings)
        self._nodes[self._root] = self._rootNode
        self._rootNode.selectionChanged.connect(partial(self._selectionChanged, self._rootNode))
        self._centralWidget.layout().addWidget(self._rootNode)

        typeNodes: Dict[WorldConceitType, ContainerNode] = {}
        for conceitType in WorldConceitType:
            conceit = WorldConceit(conceitType.name, type=conceitType)
            typeNode = ConceitTypeNode(conceit, settings=self._settings)
            typeNodes[conceitType] = typeNode
            self._nodes[conceit] = typeNode
            typeNode.selectionChanged.connect(partial(self._selectionChanged, typeNode))
            self._rootNode.addChild(typeNode)

        for conceit in self._world.conceits:
            node = self._initNode(conceit)
            typeNodes[conceit.type].addChild(node)
            recursive(conceit, lambda parent: parent.children, addChildWdg)
        self._centralWidget.layout().addWidget(vspacer())

        for node in typeNodes.values():
            if not node.childrenWidgets():
                node.setVisible(False)

        self._rootNode.select()
        self._selectionChanged(self._rootNode, True)

    @overrides
    def _emitSelectionChanged(self, conceit: WorldConceit):
        if conceit == self._root:
            self.rootSelected.emit()
        elif isinstance(self._nodes[conceit], ConceitTypeNode):
            self.conceitTypeSelected.emit(conceit.type)
        else:
            self.conceitSelected.emit(conceit)

    @overrides
    def _mimeType(self) -> str:
        return self.CONCEIT_ENTITY_MIMETYPE

    @overrides
    def _topLevelItems(self) -> List[WorldConceit]:
        return self._world.conceits

    @overrides
    def _node(self, conceit: WorldConceit) -> ConceitNode:
        return ConceitNode(conceit, settings=self._settings)

    @overrides
    def _save(self):
        self.repo.update_world(self._novel)

    def _addConceitUnder(self, parent: ConceitNode):
        conceit = WorldConceit('Conceit', type=parent.item().type)
        child = self._initNode(conceit)
        parent.addChild(child)
        fade_in(child)

        parent.item().children.append(conceit)
        self._save()

    def _deleteConceit(self, node: ConceitNode):
        conceit: WorldConceit = node.item()
        if isinstance(node.parent().parent(), ConceitNode):
            parent: ConceitNode = node.parent().parent()
            parent.item().children.remove(conceit)
        else:
            self._novel.world.conceits.remove(conceit)

        self._deleteNode(node)
        self.conceitDeleted.emit(conceit)
        self._save()

    @overrides
    def _initNode(self, conceit: WorldConceit) -> ConceitNode:
        node = ConceitNode(conceit, readOnly=self._readOnly, settings=self._settings)
        self._nodes[conceit] = node
        node.selectionChanged.connect(partial(self._selectionChanged, node))
        node.added.connect(partial(self._addConceitUnder, node))
        node.deleted.connect(partial(self._deleteConceit, node))

        # if not self._readOnly:
        #     self._enhanceWithDnd(node)

        return node
