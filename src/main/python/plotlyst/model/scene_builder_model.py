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
import copy
import pickle
from typing import Any, List, Optional

import emoji
from PyQt6.QtCore import QModelIndex, Qt, QMimeData, QByteArray
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from anytree import Node
from overrides import overrides

from src.main.python.plotlyst.core.domain import Character, Scene, NpcCharacter, SceneBuilderElement, \
    SceneBuilderElementType
from src.main.python.plotlyst.model.tree_model import TreeItemModel
from src.main.python.plotlyst.view.common import emoji_font
from src.main.python.plotlyst.view.dialog.scene_builder_edition import SceneElementEditionDialog, DialogEditionDialog, \
    CharacterBasedEditionDialog, SceneElementEditionResult
from src.main.python.plotlyst.view.icons import avatars, IconRegistry


class SceneInventoryNode(Node):
    def __init__(self, name: str, emoji_name: str, parent):
        super().__init__(name, parent)
        self.emoji = emoji.emojize(emoji_name)
        self.character: Optional[Character] = None
        self.tension: bool = False
        self.suspense: bool = False
        self.stakes: bool = False


class CharacterEntryNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Character entry', ':door:', parent)


class DialogSpeechNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Speech', ':speaking_head:', parent)


class DialogActionBeatNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Action beat', ':clapping_hands:', parent)


class SightNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Sight', ':eyes:', parent)


class SoundNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Sound', ':speaker_high_volume:', parent)


class SmellNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Smell', ':nose:', parent)


class TasteNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Taste', ':tongue:', parent)


class TouchNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Touch', ':handshake:', parent)


class ActionNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Action', ':play_button:', parent)


class ReactionNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Reaction', ':blue_circle:', parent)


class FeelingNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Feeling', ':broken_heart:', parent)


class ReflexNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Reflex', ':hand_with_fingers_splayed:', parent)


class MonologNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Monolog', ':thinking_face:', parent)


class EmotionalChangeNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Emotional change', ':chart_increasing:', parent)


class GoalNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Goal', ':bullseye:', parent)


class DisasterNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Disaster', ':bomb:', parent)


class ResolutionNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Resolution', ':trophy:', parent)


class DecisionNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Decision', ':brain:', parent)


class EndingNode(SceneInventoryNode):
    def __init__(self, parent: Node):
        super().__init__('Ending', ':chequered_flag:', parent)


def convert_to_node(element: SceneBuilderElement, parent: Node) -> SceneInventoryNode:
    if element.type == SceneBuilderElementType.SPEECH:
        node = DialogSpeechNode(parent)
    elif element.type == SceneBuilderElementType.ACTION_BEAT:
        node = DialogActionBeatNode(parent)
    elif element.type == SceneBuilderElementType.CHARACTER_ENTRY:
        node = CharacterEntryNode(parent)
    elif element.type == SceneBuilderElementType.REACTION:
        node = ReactionNode(parent)
    elif element.type == SceneBuilderElementType.SIGHT:
        node = SightNode(parent)
    elif element.type == SceneBuilderElementType.SOUND:
        node = SoundNode(parent)
    elif element.type == SceneBuilderElementType.SMELL:
        node = SmellNode(parent)
    elif element.type == SceneBuilderElementType.TASTE:
        node = TasteNode(parent)
    elif element.type == SceneBuilderElementType.TOUCH:
        node = TouchNode(parent)
    elif element.type == SceneBuilderElementType.FEELING:
        node = FeelingNode(parent)
    elif element.type == SceneBuilderElementType.REFLEX:
        node = ReflexNode(parent)
    elif element.type == SceneBuilderElementType.ACTION:
        node = ActionNode(parent)
    elif element.type == SceneBuilderElementType.MONOLOG:
        node = MonologNode(parent)
    elif element.type == SceneBuilderElementType.EMOTIONAL_CHANGE:
        node = EmotionalChangeNode(parent)
    elif element.type == SceneBuilderElementType.GOAL:
        node = GoalNode(parent)
    elif element.type == SceneBuilderElementType.DISASTER:
        node = DisasterNode(parent)
    elif element.type == SceneBuilderElementType.RESOLUTION:
        node = ResolutionNode(parent)
    elif element.type == SceneBuilderElementType.DECISION:
        node = DecisionNode(parent)
    elif element.type == SceneBuilderElementType.ENDING:
        node = EndingNode(parent)
    else:
        raise ValueError('Unknown SceneBuilderElement type')

    node.name = element.text
    node.character = element.character
    node.stakes = element.has_stakes
    node.tension = element.has_tension
    node.suspense = element.has_suspense
    return node


def convert_to_element_type(node: SceneInventoryNode) -> SceneBuilderElementType:
    if isinstance(node, DialogActionBeatNode):
        return SceneBuilderElementType.ACTION_BEAT
    elif isinstance(node, DialogSpeechNode):
        return SceneBuilderElementType.SPEECH
    elif isinstance(node, ReactionNode):
        return SceneBuilderElementType.REACTION
    elif isinstance(node, CharacterEntryNode):
        return SceneBuilderElementType.CHARACTER_ENTRY
    elif isinstance(node, SightNode):
        return SceneBuilderElementType.SIGHT
    elif isinstance(node, SoundNode):
        return SceneBuilderElementType.SOUND
    elif isinstance(node, SmellNode):
        return SceneBuilderElementType.SMELL
    elif isinstance(node, TasteNode):
        return SceneBuilderElementType.TASTE
    elif isinstance(node, TouchNode):
        return SceneBuilderElementType.TOUCH
    elif isinstance(node, FeelingNode):
        return SceneBuilderElementType.FEELING
    elif isinstance(node, ReflexNode):
        return SceneBuilderElementType.REFLEX
    elif isinstance(node, ActionNode):
        return SceneBuilderElementType.ACTION
    elif isinstance(node, MonologNode):
        return SceneBuilderElementType.MONOLOG
    elif isinstance(node, EmotionalChangeNode):
        return SceneBuilderElementType.EMOTIONAL_CHANGE
    elif isinstance(node, DisasterNode):
        return SceneBuilderElementType.DISASTER
    elif isinstance(node, ResolutionNode):
        return SceneBuilderElementType.RESOLUTION
    elif isinstance(node, GoalNode):
        return SceneBuilderElementType.GOAL
    elif isinstance(node, DecisionNode):
        return SceneBuilderElementType.DECISION
    elif isinstance(node, EndingNode):
        return SceneBuilderElementType.ENDING
    else:
        raise ValueError('Unknown node type')


class InternalSceneElementMimeData(QMimeData):
    def __init__(self, node: SceneInventoryNode):
        self.node = node
        super().__init__()


class _SceneBuilderTreeModel(TreeItemModel):
    MimeType: str = 'application/scene_element'

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.FontRole:
            return emoji_font(QApplication.font().pointSize())
        if role == self.NodeRole:
            return super(_SceneBuilderTreeModel, self).data(index, role)
        node = index.internalPointer()
        if isinstance(node, SceneInventoryNode):
            return self._dataForInventoryNode(node, index.column(), role)
        elif index.column() == 0:
            return super(_SceneBuilderTreeModel, self).data(index, role)

    def _dataForInventoryNode(self, node: SceneInventoryNode, column: int, role: int):
        if column == 0:
            if role == Qt.ItemDataRole.DisplayRole:
                return f'{node.emoji}{node.name}'
            if role == Qt.ItemDataRole.DecorationRole:
                if node.character:
                    if isinstance(node.character, NpcCharacter):
                        return IconRegistry.portrait_icon()
                    return QIcon(avatars.pixmap(node.character))

    @overrides
    def mimeData(self, indexes: List[QModelIndex]) -> QMimeData:
        node = indexes[0].internalPointer()
        mime_data = QMimeData()
        mime_data.setData(self.MimeType, QByteArray(pickle.dumps(node)))
        return mime_data

    @overrides
    def mimeTypes(self) -> List[str]:
        return [self.MimeType]

    def deleteItem(self, index: QModelIndex):
        node = index.internalPointer()
        node.parent = None

        self.modelReset.emit()


class SceneBuilderInventoryTreeModel(_SceneBuilderTreeModel):

    def __init__(self):
        super(SceneBuilderInventoryTreeModel, self).__init__()

        CharacterEntryNode(self.root)
        dialog = Node('Dialog', self.root)
        DialogSpeechNode(dialog)
        DialogActionBeatNode(dialog)
        sensor = Node('Sensors', self.root)
        SightNode(sensor)
        SoundNode(sensor)
        SmellNode(sensor)
        TasteNode(sensor)
        TouchNode(sensor)
        reaction = ReactionNode(self.root)
        FeelingNode(reaction)
        ReflexNode(reaction)
        MonologNode(reaction)
        ActionNode(reaction)
        DialogSpeechNode(reaction)

        ActionNode(self.root)
        # SceneInventoryNode('External conflict', ':crossed_swords:', self.root)
        # SceneInventoryNode('Internal conflict', ':angry_face_with_horns:', self.root)
        EmotionalChangeNode(self.root)
        # SceneInventoryNode('Tension', ':confounded_face:', self.root)
        # SceneInventoryNode('Suspense', ':flushed_face:', self.root)
        # SceneInventoryNode('Stakes', ':face_screaming_in_fear:', self.root)
        GoalNode(self.root)
        DisasterNode(self.root)
        ResolutionNode(self.root)
        DecisionNode(self.root)
        EndingNode(self.root)

    @overrides
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        node = index.internalPointer()
        if isinstance(node, SceneInventoryNode):
            return flags | Qt.ItemFlag.ItemIsDragEnabled
        return flags


class SceneBuilderPaletteTreeModel(_SceneBuilderTreeModel):

    def __init__(self, scene: Scene):
        super(SceneBuilderPaletteTreeModel, self).__init__(None)
        self.scene = scene

    def setElements(self, elements: List[SceneBuilderElement]):
        for el in elements:
            self._createNode(el, self.root)

        self.modelReset.emit()

    def _createNode(self, element: SceneBuilderElement, parent: Node):
        node = convert_to_node(element, parent)
        for child in element.children:
            self._createNode(child, node)

    @overrides
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        node = index.internalPointer()
        if isinstance(node, SceneInventoryNode):
            return flags | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsEditable
        return flags | Qt.ItemFlag.ItemIsDropEnabled

    @overrides
    def setData(self, index: QModelIndex, value: Any, role: int = ...) -> bool:
        node = index.internalPointer()
        if isinstance(node, CharacterEntryNode):
            node.name = value.name
            node.character = value
        else:
            node.name = value

        self.modelReset.emit()
        return True

    @overrides
    def mimeData(self, indexes: List[QModelIndex]) -> QMimeData:
        node = indexes[0].internalPointer()
        mime_data = InternalSceneElementMimeData(node)
        mime_data.setData(self.MimeType, QByteArray(pickle.dumps(node)))
        return mime_data

    @overrides
    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int,
                        parent: QModelIndex) -> bool:
        if isinstance(data, InternalSceneElementMimeData) and parent.isValid():
            return data.node is not parent.internalPointer()
        return True

    @overrides
    def dropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int,
                     parent: QModelIndex) -> bool:
        if parent.isValid():
            parent_node = parent.internalPointer()
        else:
            parent_node = self.root

        if isinstance(data, InternalSceneElementMimeData):
            node: Optional[SceneInventoryNode] = data.node
        else:  # from the inventory
            node = pickle.loads(data.data(self.MimeType))
            if not self._initNode(node):
                return False

        node.parent = parent_node
        if node and row >= 0:
            self._repositionNodeUnder(node, parent_node, row)

        self.modelReset.emit()
        return True

    def insertNode(self, node: SceneInventoryNode):
        new_node = copy.deepcopy(node)
        if not self._initNode(new_node):
            return
        new_node.parent = self.root
        self.modelReset.emit()

    def _initNode(self, node: SceneInventoryNode) -> bool:
        if isinstance(node, (DialogSpeechNode, DialogActionBeatNode)):
            result = DialogEditionDialog().display(self.scene)
        elif isinstance(node, CharacterEntryNode):
            result = CharacterBasedEditionDialog().display(self.scene)
        elif isinstance(node, ReactionNode):
            result = SceneElementEditionResult('Reaction')
            for child in node.children:
                if isinstance(child, DialogSpeechNode) and self.scene.pov:
                    child.character = self.scene.pov
        else:
            result = SceneElementEditionDialog().display(self.scene)

        if result is None:  # edition cancelled
            return False
        node.character = result.character
        node.name = result.text

        return True

    def _repositionNodeUnder(self, node, parent, row: int):
        children_list = list(parent.children)
        old_index = children_list.index(node)
        new_index = row
        if old_index < new_index:
            new_index -= 1
        children_list.pop(old_index)
        children_list.insert(new_index, node)
        parent.children = children_list
