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

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import QApplication
from overrides import overrides

from src.main.python.plotlyst.core.client import json_client
from src.main.python.plotlyst.core.domain import Character, DiagramNodeType, NODE_SUBTYPE_TOOL, NODE_SUBTYPE_COST
from src.main.python.plotlyst.core.domain import Node
from src.main.python.plotlyst.core.domain import Novel
from src.main.python.plotlyst.service.persistence import RepositoryPersistenceManager
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.widget.characters import CharacterSelectorMenu
from src.main.python.plotlyst.view.widget.graphics import NetworkGraphicsView, NetworkScene, EventItem, \
    NodeItem
from src.main.python.plotlyst.view.widget.graphics.editor import EventSelectorWidget, TextLineEditorPopup, \
    EventItemToolbar, ConnectorToolbar, SecondarySelectorWidget


class EventsMindMapScene(NetworkScene):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel

        self.repo = RepositoryPersistenceManager.instance()

    @overrides
    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)
        if not event.modifiers() and not event.key() == Qt.Key.Key_Escape and len(self.selectedItems()) == 1:
            item = self.selectedItems()[0]
            if isinstance(item, EventItem):
                self.editItem.emit(item)

    @overrides
    def _character(self, node: Node) -> Optional[Character]:
        return node.character(self._novel) if node.character_id else None

    @overrides
    def _load(self):
        json_client.load_diagram(self._novel, self._diagram)

    @overrides
    def _save(self):
        self.repo.update_diagram(self._novel, self._diagram)


class EventsMindMapView(NetworkGraphicsView):

    def __init__(self, novel: Novel, parent=None):
        self._novel = novel
        super().__init__(parent)
        self._btnAddEvent = self._newControlButton(
            IconRegistry.from_name('mdi6.shape-square-rounded-plus'), 'Add new event', DiagramNodeType.EVENT)
        self._btnAddCharacter = self._newControlButton(
            IconRegistry.character_icon('#040406'), 'Add new character', DiagramNodeType.CHARACTER)
        self._btnAddSticker = self._newControlButton(IconRegistry.from_name('mdi6.sticker-circle-outline'),
                                                     'Add new sticker',
                                                     DiagramNodeType.COMMENT)

        self._wdgSecondaryEventSelector = EventSelectorWidget(self)
        self._wdgSecondaryEventSelector.setVisible(False)
        self._wdgSecondaryEventSelector.selected.connect(self._startAddition)
        self._wdgSecondaryStickerSelector = StickerSelectorWidget(self)
        self._wdgSecondaryStickerSelector.setVisible(False)
        self._wdgSecondaryStickerSelector.selected.connect(self._startAddition)

        # self._stickerEditor = StickerEditor(self)
        # self._stickerEditor.setVisible(False)

        self._itemEditor = EventItemToolbar(self)
        self._itemEditor.setVisible(False)

        self._connectorEditor = ConnectorToolbar(self)
        self._connectorEditor.setVisible(False)

        self._arrangeSideBars()

    @overrides
    def _initScene(self) -> NetworkScene:
        return EventsMindMapScene(self._novel)

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        if self._diagram is None:
            self.setDiagram(self._novel.events_map)

    @overrides
    def _startAddition(self, itemType: DiagramNodeType, subType: str = ''):
        super()._startAddition(itemType, subType)

        if itemType == DiagramNodeType.EVENT:
            self._wdgSecondaryEventSelector.setVisible(True)
            self._wdgSecondaryStickerSelector.setHidden(True)
        elif itemType == DiagramNodeType.COMMENT:
            self._wdgSecondaryStickerSelector.setVisible(True)
            self._wdgSecondaryEventSelector.setHidden(True)
        elif itemType == DiagramNodeType.CHARACTER:
            self._wdgSecondaryStickerSelector.setHidden(True)
            self._wdgSecondaryEventSelector.setHidden(True)

    @overrides
    def _endAddition(self, itemType: Optional[DiagramNodeType] = None, item: Optional[NodeItem] = None):
        super()._endAddition(itemType, item)
        self._wdgSecondaryEventSelector.setHidden(True)
        self._wdgSecondaryStickerSelector.setHidden(True)

    @overrides
    def _characterSelectorMenu(self) -> CharacterSelectorMenu:
        return CharacterSelectorMenu(self._novel, parent=self)

    @overrides
    def _arrangeSideBars(self):
        super()._arrangeSideBars()

        secondary_x = self._controlsNavBar.pos().x() + self._controlsNavBar.sizeHint().width() + 5
        secondary_y = self._controlsNavBar.pos().y() + self._btnAddEvent.pos().y()
        self._wdgSecondaryEventSelector.setGeometry(secondary_x, secondary_y,
                                                    self._wdgSecondaryEventSelector.sizeHint().width(),
                                                    self._wdgSecondaryEventSelector.sizeHint().height())

        secondary_x = self._controlsNavBar.pos().x() + self._controlsNavBar.sizeHint().width() + 5
        secondary_y = self._controlsNavBar.pos().y() + self._btnAddSticker.pos().y()
        self._wdgSecondaryStickerSelector.setGeometry(secondary_x, secondary_y,
                                                      self._wdgSecondaryStickerSelector.sizeHint().width(),
                                                      self._wdgSecondaryStickerSelector.sizeHint().height())

    @overrides
    def _editEventItem(self, item: EventItem):
        def setText(text: str):
            item.setText(text)

        popup = TextLineEditorPopup(item.text(), item.textRect(), parent=self)
        font = QApplication.font()
        font.setPointSize(max(int(item.fontSize() * self._scaledFactor), font.pointSize()))
        popup.setFont(font)
        view_pos = self.mapFromScene(item.textSceneRect().topLeft())
        popup.exec(self.mapToGlobal(view_pos))

        popup.aboutToHide.connect(lambda: setText(popup.text()))

    @overrides
    def _showEventItemToolbar(self, item: EventItem):
        self._itemEditor.setItem(item)
        self._popupAbove(self._itemEditor, item)

    @overrides
    def _hideItemToolbar(self):
        super()._hideItemToolbar()
        self._itemEditor.setVisible(False)


class StickerSelectorWidget(SecondarySelectorWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._btnComment = self.addItemTypeButton(DiagramNodeType.COMMENT,
                                                  IconRegistry.from_name('mdi.comment-text-outline'),
                                                  'Add new comment', 0, 0)
        self._btnTool = self.addItemTypeButton(DiagramNodeType.STICKER, IconRegistry.tool_icon('black', 'black'),
                                               'Add new tool',
                                               0, 1, subType=NODE_SUBTYPE_TOOL)
        self._btnCost = self.addItemTypeButton(DiagramNodeType.STICKER, IconRegistry.cost_icon('black', 'black'),
                                               'Add new cost',
                                               1, 0, subType=NODE_SUBTYPE_COST)

        self._btnComment.setChecked(True)

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        self._btnComment.setChecked(True)