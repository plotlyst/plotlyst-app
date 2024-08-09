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

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QUndoStack
from overrides import overrides
from qthandy import vline
from qtmenu import GridMenuWidget

from plotlyst.core.client import json_client
from plotlyst.core.domain import Diagram, Relation, Node
from plotlyst.core.domain import Novel, Character, GraphicsItemType
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import action
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.characters import CharacterSelectorMenu
from plotlyst.view.widget.graphics import NetworkGraphicsView, NetworkScene
from plotlyst.view.widget.graphics.editor import ConnectorToolbar, RelationsButton


class RelationsEditorScene(NetworkScene):
    def __init__(self, novel: Novel, parent=None):
        super(RelationsEditorScene, self).__init__(parent)
        self._novel = novel

        self.repo = RepositoryPersistenceManager.instance()

    @overrides
    def _character(self, node: Node) -> Optional[Character]:
        return node.character(self._novel) if node.character_id else None

    @overrides
    def _load(self):
        json_client.load_diagram(self._novel, self._diagram)

    @overrides
    def _save(self):
        self.repo.update_diagram(self._novel, self._diagram)


class CharacterNetworkView(NetworkGraphicsView):
    def __init__(self, novel: Novel, parent=None):
        self._novel = novel
        super(CharacterNetworkView, self).__init__(parent)

        self._btnAddCharacter = self._newControlButton(IconRegistry.character_icon('#040406'), 'Add new character',
                                                       GraphicsItemType.CHARACTER)
        # self._btnAddSticker = self._newControlButton(IconRegistry.from_name('mdi6.sticker-circle-outline'),
        #                                              'Add new sticker', GraphicsItemType.STICKER)
        # self._btnAddSticker.setDisabled(True)
        # self._btnAddSticker.setToolTip('Feature is not yet available')

        self._connectorEditor = RelationConnectorToolbar(self.undoStack, self)
        self._connectorEditor.setVisible(False)

    @overrides
    def _initScene(self) -> NetworkScene:
        return RelationsEditorScene(self._novel)

    def refresh(self):
        if not self._diagram:
            self.setDiagram(self._novel.character_networks[0])
            self._connectorEditor.setNetwork(self._diagram)

    @overrides
    def _characterSelectorMenu(self) -> CharacterSelectorMenu:
        return CharacterSelectorMenu(self._novel, parent=self)


class RelationSelector(GridMenuWidget):
    relationSelected = pyqtSignal(Relation)

    def __init__(self, network: Diagram = None, parent=None):
        super().__init__(parent)
        self._network = network
        self._romance = Relation('Romance', icon='ei.heart', icon_color='#d1495b')
        self._breakUp = Relation('Breakup', icon='fa5s.heart-broken', icon_color='#d1495b')
        self._affection = Relation('Affection', icon='mdi.sparkles', icon_color='#d1495b')
        self._crush = Relation('Crush', icon='fa5.grin-hearts', icon_color='#d1495b')
        self._unrequited = Relation('Unrequited love', icon='mdi.heart-half-full', icon_color='#d1495b')

        self._colleague = Relation('Colleague', icon='fa5s.briefcase', icon_color='#9c6644')
        self._student = Relation('Student', icon='fa5s.graduation-cap', icon_color='black')
        self._foil = Relation('Foil', icon='fa5s.yin-yang', icon_color='#947eb0')

        self._friendship = Relation('Friendship', icon='fa5s.user-friends', icon_color='#457b9d')
        self._sidekick = Relation('Sidekick', icon='ei.asl', icon_color='#b0a990')
        self._guide = Relation('Guide', icon='mdi.compass-rose', icon_color='#80ced7')
        self._supporter = Relation('Supporter', icon='fa5s.thumbs-up', icon_color='#266dd3')
        self._adversary = Relation('Adversary', icon='fa5s.thumbs-down', icon_color='#9e1946')
        self._betrayal = Relation('Betrayal', icon='mdi6.knife', icon_color='grey')
        self._conflict = Relation('Conflict', icon='mdi.sword-cross', icon_color='#f3a712')

        self._newAction(self._romance, 0, 0)
        self._newAction(self._affection, 0, 1)
        self._newAction(self._crush, 0, 2)
        self._newAction(self._breakUp, 1, 0)
        self._newAction(self._unrequited, 1, 1, 2)
        self.addSeparator(2, 0, colSpan=3)
        self._newAction(self._friendship, 3, 0)
        self._newAction(self._sidekick, 3, 1)
        self._newAction(self._guide, 3, 2)
        self._newAction(self._supporter, 4, 0)
        self._newAction(self._adversary, 4, 1)
        self._newAction(self._betrayal, 5, 0)
        self._newAction(self._conflict, 5, 1)
        self._newAction(self._foil, 6, 0)
        self.addSeparator(7, 0, colSpan=3)
        self._newAction(self._colleague, 8, 0)
        self._newAction(self._student, 8, 1)

    def _newAction(self, relation: Relation, row: int, col: int, colSpan: int = 1, showText: bool = True) -> QAction:
        text = relation.text if showText else ''
        action_ = action(text, IconRegistry.from_name(relation.icon, relation.icon_color))
        action_.setToolTip(relation.text)
        self.addAction(action_, row, col, colSpan=colSpan)
        action_.triggered.connect(lambda: self.relationSelected.emit(relation))

        return action_


class RelationConnectorToolbar(ConnectorToolbar):
    def __init__(self, undoStack: QUndoStack, parent=None):
        super().__init__(undoStack, parent)
        self._btnRelationType = RelationsButton()

        self._relationSelector: Optional[RelationSelector] = None

        self._toolbar.layout().insertWidget(0, self._btnRelationType)
        self._toolbar.layout().insertWidget(1, vline())

    def setNetwork(self, diagram: Diagram):
        self._relationSelector = RelationSelector(diagram, self._btnRelationType)
        self._relationSelector.relationSelected.connect(self._relationChanged)

    def _relationChanged(self, relation: Relation):
        if self._item:
            self._item.setRelation(relation)
            self._updateIcon(relation.icon)
            self._updateColor(relation.icon_color)
