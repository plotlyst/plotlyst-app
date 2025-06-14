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

from typing import Optional

from PyQt6.QtGui import QImage
from PyQt6.QtGui import QShowEvent
from overrides import overrides
from qthandy import line, decr_icon

from plotlyst.common import BLACK_COLOR
from plotlyst.core.client import json_client
from plotlyst.core.domain import GraphicsItemType, NODE_SUBTYPE_TOOL, NODE_SUBTYPE_COST, Diagram
from plotlyst.core.domain import Node
from plotlyst.core.domain import Novel
from plotlyst.service.image import LoadedImage, upload_image, load_image
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import tool_btn
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.characters import CharacterSelectorMenu
from plotlyst.view.widget.graphics import NetworkGraphicsView, NetworkScene, EventItem, NodeItem
from plotlyst.view.widget.graphics.editor import EventItemToolbar, ConnectorToolbar, \
    SecondarySelectorWidget, CharacterToolbar, NoteToolbar, IconItemToolbar, EventSelectorWidget


class EventsMindMapScene(NetworkScene):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel

        self.repo = RepositoryPersistenceManager.instance()

    # @overrides
    # def keyPressEvent(self, event: QKeyEvent) -> None:
    #     super().keyPressEvent(event)
    #     if not event.modifiers() and not event.key() == Qt.Key.Key_Escape and len(self.selectedItems()) == 1:
    #         item = self.selectedItems()[0]
    #         if isinstance(item, (EventItem, NoteItem)):
    #             self.editItem.emit(item)

    @overrides
    def isSnapToGrid(self) -> bool:
        return self._diagram.settings.snap_to_grid

    def setSnapToGrid(self, enabled: bool):
        self._diagram.settings.snap_to_grid = enabled
        self._save()

    @overrides
    def _load(self):
        json_client.load_diagram(self._novel, self._diagram)

    @overrides
    def _save(self):
        self.repo.update_diagram(self._novel, self._diagram)

    @overrides
    def _uploadImage(self) -> Optional[LoadedImage]:
        return upload_image(self._novel)

    @overrides
    def _loadImage(self, node: Node) -> Optional[QImage]:
        return load_image(self._novel, node.image_ref)


class EventsMindMapView(NetworkGraphicsView):

    def __init__(self, novel: Novel, parent=None):
        self._novel = novel
        super().__init__(parent)
        self._btnAddEvent = self._newControlButton(
            IconRegistry.from_name('mdi6.shape-square-rounded-plus'), 'Add new event', GraphicsItemType.EVENT)
        self._btnAddText = self._newControlButton(
            IconRegistry.from_name('mdi6.format-text'), 'Add new text', GraphicsItemType.TEXT)
        self._btnAddNote = self._newControlButton(
            IconRegistry.from_name('msc.note'), 'Add new note', GraphicsItemType.NOTE)
        self._btnAddCharacter = self._newControlButton(
            IconRegistry.character_icon(BLACK_COLOR), 'Add new character', GraphicsItemType.CHARACTER)
        self._btnAddIcon = self._newControlButton(
            IconRegistry.from_name('mdi.emoticon-outline'), 'Add new icon', GraphicsItemType.ICON)
        self._btnAddImage = self._newControlButton(IconRegistry.image_icon(), 'Add new image',
                                                   GraphicsItemType.IMAGE)

        self._controlsNavBar.layout().addWidget(line())
        self._controlsNavBar.layout().addWidget(self._btnUndo)
        self._controlsNavBar.layout().addWidget(self._btnRedo)
        # self._btnAddSticker = self._newControlButton(IconRegistry.from_name('mdi6.sticker-circle-outline'),
        #                                              'Add new sticker',
        #                                              GraphicsItemType.COMMENT)
        # self._btnAddSticker.setDisabled(True)
        # self._btnAddSticker.setToolTip('Feature is not yet available')

        self._wdgSecondaryEventSelector = EventSelectorWidget(self)
        self._wdgSecondaryEventSelector.setVisible(False)
        self._wdgSecondaryEventSelector.selected.connect(self._startAddition)
        # self._wdgSecondaryStickerSelector = StickerSelectorWidget(self)
        # self._wdgSecondaryStickerSelector.setVisible(False)
        # self._wdgSecondaryStickerSelector.selected.connect(self._startAddition)

        # self._stickerEditor = StickerEditor(self)
        # self._stickerEditor.setVisible(False)

        self._settingsBar.setVisible(True)
        self._btnGrid = tool_btn(IconRegistry.from_name('mdi.dots-grid'), "Snap elements to an invisible grid",
                                 True, icon_resize=False,
                                 properties=['transparent-rounded-bg-on-hover', 'top-selector'],
                                 parent=self._settingsBar)
        decr_icon(self._btnGrid, 2)
        self._settingsBar.layout().addWidget(self._btnGrid)
        self._btnGrid.clicked.connect(self._scene.setSnapToGrid)

        self._itemEditor = EventItemToolbar(self.undoStack, self)
        self._itemEditor.setVisible(False)

        self._connectorEditor = ConnectorToolbar(self.undoStack, self)
        self._connectorEditor.setVisible(False)
        self._characterEditor = CharacterToolbar(self.undoStack, self)
        self._characterEditor.changeCharacter.connect(self._editCharacterItem)
        self._characterEditor.setVisible(False)
        self._noteEditor = NoteToolbar(self.undoStack, self)
        self._noteEditor.setVisible(False)
        self._iconEditor = IconItemToolbar(self.undoStack, self)
        self._iconEditor.setVisible(False)

        self._arrangeSideBars()

    @overrides
    def setDiagram(self, diagram: Diagram):
        super().setDiagram(diagram)
        self._btnGrid.setChecked(diagram.settings.snap_to_grid)

    @overrides
    def _initScene(self) -> NetworkScene:
        return EventsMindMapScene(self._novel)

    @overrides
    def _startAddition(self, itemType: GraphicsItemType, subType: str = ''):
        super()._startAddition(itemType, subType)

        if itemType == GraphicsItemType.EVENT:
            self._wdgSecondaryEventSelector.setVisible(True)
        else:
            self._wdgSecondaryEventSelector.setHidden(True)

    #         self._wdgSecondaryStickerSelector.setHidden(True)
    #     elif itemType == GraphicsItemType.COMMENT:
    #         self._wdgSecondaryStickerSelector.setVisible(True)
    #         self._wdgSecondaryEventSelector.setHidden(True)
    #     elif itemType == GraphicsItemType.CHARACTER:
    #         self._wdgSecondaryStickerSelector.setHidden(True)
    #         self._wdgSecondaryEventSelector.setHidden(True)
    #     elif itemType == GraphicsItemType.ICON:
    #         self._wdgSecondaryStickerSelector.setHidden(True)
    #         self._wdgSecondaryEventSelector.setHidden(True)

    @overrides
    def _endAddition(self, itemType: Optional[GraphicsItemType] = None, item: Optional[NodeItem] = None):
        super()._endAddition(itemType, item)
        self._wdgSecondaryEventSelector.setHidden(True)

    #     self._wdgSecondaryStickerSelector.setHidden(True)

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

        # secondary_x = self._controlsNavBar.pos().x() + self._controlsNavBar.sizeHint().width() + 5
        # secondary_y = self._controlsNavBar.pos().y() + self._btnAddSticker.pos().y()
        # self._wdgSecondaryStickerSelector.setGeometry(secondary_x, secondary_y,
        #                                               self._wdgSecondaryStickerSelector.sizeHint().width(),
        #                                               self._wdgSecondaryStickerSelector.sizeHint().height())

    # @overrides
    # def _editEventItem(self, item: EventItem):
    #     def setText(text: str):
    #         item.setText(text)
    #
    #     popup = TextLineEditorPopup(item.text(), item.textRect(), parent=self)
    #     font = QApplication.font()
    #     font.setPointSize(max(int(item.fontSize() * self._scaledFactor), font.pointSize()))
    #     popup.setFont(font)
    #     view_pos = self.mapFromScene(item.textSceneRect().topLeft())
    #     popup.aboutToHide.connect(lambda: setText(popup.text()))
    #
    #     popup.exec(self.mapToGlobal(view_pos))

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
        self._btnComment = self.addItemTypeButton(GraphicsItemType.COMMENT,
                                                  IconRegistry.from_name('mdi.comment-text-outline'),
                                                  'Add new comment', 0, 0)
        self._btnTool = self.addItemTypeButton(GraphicsItemType.STICKER, IconRegistry.tool_icon('black', 'black'),
                                               'Add new tool',
                                               0, 1, subType=NODE_SUBTYPE_TOOL)
        self._btnCost = self.addItemTypeButton(GraphicsItemType.STICKER, IconRegistry.cost_icon('black', 'black'),
                                               'Add new cost',
                                               1, 0, subType=NODE_SUBTYPE_COST)

        self._btnComment.setChecked(True)

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        self._btnComment.setChecked(True)
