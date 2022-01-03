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
import pickle
from typing import List, Any, Dict, Optional

import emoji
from PyQt6.QtCore import QModelIndex, Qt, QVariant, QSortFilterProxyModel, QMimeData, QByteArray, pyqtSignal, \
    QAbstractTableModel
from PyQt6.QtGui import QIcon, QFont, QBrush, QColor
from overrides import overrides

from src.main.python.plotlyst.common import WIP_COLOR, PIVOTAL_COLOR
from src.main.python.plotlyst.core.domain import Novel, Scene, CharacterArc, Character, \
    SelectionItem, SceneGoal, SceneStage, SceneType, SceneStructureItem
from src.main.python.plotlyst.model.common import AbstractHorizontalHeaderBasedTableModel, SelectionItemsModel
from src.main.python.plotlyst.view.common import emoji_font
from src.main.python.plotlyst.view.icons import IconRegistry, avatars
from src.main.python.plotlyst.worker.cache import acts_registry
from src.main.python.plotlyst.worker.persistence import RepositoryPersistenceManager


class BaseScenesTableModel:

    def verticalHeaderData(self, section: int, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return str(section + 1)
        if role == Qt.ItemDataRole.DecorationRole:
            return IconRegistry.hashtag_icon()


class ScenesTableModel(AbstractHorizontalHeaderBasedTableModel, BaseScenesTableModel):
    orderChanged = pyqtSignal()
    valueChanged = pyqtSignal(QModelIndex)
    SceneRole = Qt.ItemDataRole.UserRole + 1

    MimeType: str = 'application/scene'

    ColPov = 0
    ColTitle = 1
    ColCharacters = 2
    ColType = 3
    ColTime = 4
    ColBeginning = 5
    ColMiddle = 6
    ColEnd = 7
    ColArc = 8
    ColSynopsis = 9

    def __init__(self, novel: Novel, parent=None):
        self.novel = novel
        self._data: List[Scene] = novel.scenes
        _headers = [''] * 10
        _headers[self.ColTitle] = 'Title'
        _headers[self.ColType] = 'Type'
        _headers[self.ColPov] = 'POV'
        _headers[self.ColCharacters] = 'Characters'
        _headers[self.ColTime] = 'Day'
        _headers[self.ColBeginning] = 'Beginning'
        _headers[self.ColMiddle] = 'Middle'
        _headers[self.ColEnd] = 'End'
        _headers[self.ColArc] = 'Arc'
        _headers[self.ColSynopsis] = 'Synopsis'
        super().__init__(_headers, parent)
        self._relax_colors = False

        self._action_icon = IconRegistry.action_scene_icon()
        self._resolved_action_icon = IconRegistry.action_scene_icon(resolved=True)
        self._trade_off_action_icon = IconRegistry.action_scene_icon(trade_off=True)
        self._reaction_icon = IconRegistry.reaction_scene_icon()
        self._wip_brush = QBrush(QColor(WIP_COLOR))
        self._pivotal_brush = QBrush(QColor(PIVOTAL_COLOR))

    @overrides
    def rowCount(self, parent: QModelIndex = Qt.ItemDataRole.DisplayRole) -> int:
        return len(self._data)

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return QVariant()

        scene: Scene = self._data[index.row()]
        if role == self.SceneRole:
            return scene
        elif role == Qt.ItemDataRole.FontRole:
            if scene.wip or not scene.title:
                font = QFont()
                font.setItalic(True)
                return font
        elif role == Qt.ItemDataRole.BackgroundRole:
            if not self._relax_colors or index.column() == self.ColTitle or index.column() == self.ColPov:
                if scene.wip:
                    return self._wip_brush
                elif scene.beat:
                    return self._pivotal_brush
        elif role == Qt.ItemDataRole.DisplayRole:
            if index.column() == self.ColTitle:
                return scene.title if scene.title else f'Scene {self.novel.scenes.index(scene) + 1}'
            if index.column() == self.ColSynopsis:
                return scene.synopsis
            if index.column() == self.ColTime:
                return scene.day
            if index.column() == self.ColBeginning:
                return scene.beginning
            if index.column() == self.ColMiddle:
                return scene.middle
            if index.column() == self.ColEnd:
                return scene.end
        elif role == Qt.ItemDataRole.DecorationRole:
            if index.column() == self.ColType:
                if scene.wip:
                    return IconRegistry.wip_icon()
                elif scene.type == SceneType.ACTION:
                    if scene.outcome_resolution():
                        return self._resolved_action_icon
                    if scene.outcome_trade_off():
                        return self._trade_off_action_icon
                    return self._action_icon
                elif scene.type == SceneType.REACTION:
                    return self._reaction_icon
            elif index.column() == self.ColPov:
                if scene.pov:
                    return QIcon(avatars.pixmap(scene.pov))
            elif index.column() == self.ColBeginning:
                if scene.type == SceneType.ACTION:
                    return IconRegistry.goal_icon()
                if scene.type == SceneType.REACTION:
                    return IconRegistry.reaction_icon()
                return IconRegistry.invisible_white_icon()
            elif index.column() == self.ColMiddle:
                if scene.type == SceneType.ACTION:
                    if scene.middle:
                        return IconRegistry.conflict_icon()
                    else:
                        return IconRegistry.conflict_icon(color='lightgrey')
                if scene.type == SceneType.REACTION:
                    return IconRegistry.dilemma_icon()
                return IconRegistry.invisible_white_icon()
            elif index.column() == self.ColEnd:
                if scene.type == SceneType.ACTION:
                    if scene.outcome_resolution():
                        return IconRegistry.success_icon()
                    if scene.outcome_trade_off():
                        return IconRegistry.tradeoff_icon()
                    return IconRegistry.disaster_icon()
                if scene.type == SceneType.REACTION:
                    return IconRegistry.decision_icon()
                return IconRegistry.invisible_white_icon()
        elif role == Qt.ItemDataRole.ToolTipRole:
            if index.column() == self.ColType:
                if scene.beginning:
                    tip = f' - {scene.beginning}\n\n'
                    tip += f' - {scene.middle}\n\n'
                    tip += f' - {scene.end}'
                    return tip
                elif scene.middle:
                    return scene.middle
                elif scene.end:
                    return scene.end
            elif index.column() == self.ColPov:
                return scene.pov.name if scene.pov else ''
            elif index.column() == self.ColSynopsis:
                return scene.synopsis

    @overrides
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal:
            return super(ScenesTableModel, self).headerData(section, orientation, role)
        else:
            return self.verticalHeaderData(section, role)

    @overrides
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        flags = flags | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled
        if index.column() == self.ColSynopsis:
            return flags | Qt.ItemFlag.ItemIsEditable
        if index.column() == self.ColBeginning:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable
        if index.column() == self.ColMiddle:
            if self._data[index.row()].type == SceneType.ACTION:
                return Qt.ItemFlag.ItemIsEnabled
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable
        if index.column() == self.ColEnd:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable
        if index.column() == self.ColArc:
            return flags | Qt.ItemFlag.ItemIsEditable
        if index.column() == self.ColTime:
            return flags | Qt.ItemFlag.ItemIsEditable
        return flags

    @overrides
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        scene: Scene = self._data[index.row()]

        if index.column() == self.ColSynopsis:
            scene.synopsis = value
        elif index.column() == self.ColBeginning:
            scene.beginning = value
        elif index.column() == self.ColMiddle:
            scene.middle = value
        elif index.column() == self.ColEnd:
            scene.end = value
        elif index.column() == self.ColArc:
            if scene.arcs:
                for arc in scene.arcs:
                    if arc.character is scene.pov:
                        arc.arc = value
            else:
                scene.arcs.append(CharacterArc(value, scene.pov))
        elif index.column() == self.ColTime:
            scene.day = value
        else:
            return False
        self.valueChanged.emit(index)
        return True

    @overrides
    def mimeData(self, indexes: List[QModelIndex]) -> QMimeData:
        mime_data = QMimeData()
        scene = self._data[indexes[0].row()]
        mime_data.setData(self.MimeType, QByteArray(pickle.dumps(scene)))
        return mime_data

    @overrides
    def mimeTypes(self) -> List[str]:
        return [self.MimeType]

    @overrides
    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int,
                        parent: QModelIndex) -> bool:
        if row < 0:
            return False
        if not data.hasFormat(self.MimeType):
            return False

        return True

    @overrides
    def dropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex) -> bool:
        if row < 0:
            return False
        if not data.hasFormat(self.MimeType):
            return False

        scene: Scene = pickle.loads(data.data(self.MimeType))
        old_index = self._data.index(scene)
        if row < old_index:
            new_index = row
        else:
            new_index = row - 1
        self._data.insert(new_index, self._data.pop(old_index))

        self.orderChanged.emit()
        return True

    def setRelaxColors(self, enabled: bool):
        self._relax_colors = enabled


class ScenesFilterProxyModel(QSortFilterProxyModel):

    def __init__(self):
        super().__init__()
        self.character_filter: Dict[str, bool] = {}
        self.acts_filter: Dict[int, bool] = {}
        self.empty_pov_filter: bool = False

    def setCharacterFilter(self, character: Character, filter: bool):
        self.character_filter[str(character.id)] = filter
        self.invalidateFilter()

    def setActsFilter(self, act: int, filter: bool):
        self.acts_filter[act] = filter
        self.invalidateFilter()

    def setEmptyPovFilter(self, filter: bool):
        self.empty_pov_filter = filter
        self.invalidateFilter()

    @overrides
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        filtered = super(ScenesFilterProxyModel, self).filterAcceptsRow(source_row, source_parent)
        if not filtered:
            return filtered

        scene: Scene = self.sourceModel().data(self.sourceModel().index(source_row, 0), role=ScenesTableModel.SceneRole)
        if not scene:
            return filtered

        if self.empty_pov_filter and not scene.pov:
            return False

        if scene.pov and not self.character_filter.get(str(scene.pov.id), True):
            return False

        for act, toggled in self.acts_filter.items():
            if acts_registry.act(scene) == act and not toggled:
                return False

        return filtered


class ScenesStageTableModel(QAbstractTableModel, BaseScenesTableModel):
    SceneRole: int = Qt.ItemDataRole.UserRole + 1

    ColTitle: int = 0
    ColNoneStage: int = 1

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel
        self._highlighted_stage: Optional[SceneStage] = None

    @overrides
    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self.novel.scenes)

    @overrides
    def columnCount(self, parent: QModelIndex = ...) -> int:
        return len(self.novel.stages) + 2  # stages + title + None stage

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == self.SceneRole:
            return self._scene(index)
        if role == Qt.ItemDataRole.DecorationRole:
            if not self._scene(index).stage and index.column() == self.ColNoneStage:
                return IconRegistry.wip_icon()
        if role == Qt.ItemDataRole.FontRole:
            if index.column() > self.ColNoneStage:
                return emoji_font()
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() > self.ColNoneStage:
                return Qt.AlignmentFlag.AlignCenter
        if role == Qt.ItemDataRole.DisplayRole:
            if self._scene(index).stage and self._scene(index).stage.id == self._stage(index).id:
                return emoji.emojize(':check_mark:')
        if role == Qt.ItemDataRole.BackgroundRole and index.column() > self.ColNoneStage and self._highlighted_stage:
            if self.novel.stages[index.column() - 2] == self._highlighted_stage:
                return QBrush(QColor('#c1e0f7'))
        if role == Qt.ItemDataRole.DisplayRole and index.column() == self.ColTitle:
            return self._scene(index).title

    @overrides
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.column() == self.ColTitle:
            return Qt.ItemFlag.ItemIsEnabled
        return super(ScenesStageTableModel, self).flags(index)

    @overrides
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                if section == self.ColTitle:
                    return 'Title'
                if section == self.ColNoneStage:
                    return 'None'
                return self.novel.stages[section - 2].text.replace(' ', '\n')
        else:
            return self.verticalHeaderData(section, role)

    def changeStage(self, index: QModelIndex):
        if index.column() == self.ColTitle:
            return
        if index.column() == self.ColNoneStage:
            self._scene(index).stage = None
        else:
            self._scene(index).stage = self._stage(index)

        RepositoryPersistenceManager.instance().update_scene(self._scene(index))
        self.modelReset.emit()

    def setHighlightedStage(self, stage: SceneStage):
        self._highlighted_stage = stage
        self.modelReset.emit()

    def _scene(self, index: QModelIndex) -> Scene:
        return self.novel.scenes[index.row()]

    def _stage(self, index: QModelIndex):
        return self.novel.stages[index.column() - 2]


class SceneConflictsModel(SelectionItemsModel):

    def __init__(self, novel: Novel, scene: Scene, scene_structure_item: SceneStructureItem, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.scene = scene
        self.scene_structure_item = scene_structure_item
        self._conflicts = []
        self.update()

    def update(self):
        if self.scene.pov:
            self._conflicts = [x for x in self.novel.conflicts if x.character_id == self.scene.pov.id]

    @overrides
    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self._conflicts)

    @overrides
    def _newItem(self) -> QModelIndex:
        pass

    @overrides
    def item(self, index: QModelIndex) -> SelectionItem:
        return self._conflicts[index.row()]

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        conflict = self._conflicts[index.row()]
        if index.column() == self.ColIcon:
            if role == Qt.ItemDataRole.DecorationRole:
                if conflict.conflicting_character(self.novel):
                    if conflict.character(self.novel).avatar:
                        return QIcon(avatars.pixmap(conflict.conflicting_character(self.novel)))
                    else:
                        return avatars.name_initial_icon(conflict.conflicting_character(self.novel))
                else:
                    return IconRegistry.conflict_type_icon(conflict.type)
        return super(SceneConflictsModel, self).data(index, role)


class SceneGoalsModel(SelectionItemsModel):

    def __init__(self, novel: Novel, scene_structure_item: SceneStructureItem):
        self.novel = novel
        self.scene_structure_item = scene_structure_item
        super(SceneGoalsModel, self).__init__()
        self.repo = RepositoryPersistenceManager.instance()

    @overrides
    def item(self, index: QModelIndex) -> SelectionItem:
        return self.novel.scene_goals[index.row()]

    @overrides
    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self.novel.scene_goals)

    @overrides
    def _newItem(self) -> QModelIndex:
        goal = SceneGoal('')
        row = 0
        self.novel.scene_goals.insert(row, goal)
        self.repo.update_novel(self.novel)

        return self.index(row, 0)

    @overrides
    def remove(self, index: QModelIndex):
        super(SceneGoalsModel, self).remove(index)
        self.novel.scene_goals.pop(index.row())
        self.repo.update_novel(self.novel)

    @overrides
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.DisplayRole) -> bool:
        updated = super(SceneGoalsModel, self).setData(index, value, role)
        if updated and role != Qt.ItemDataRole.CheckStateRole:
            self.repo.update_novel(self.novel)
        return updated
