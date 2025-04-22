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
import pickle
from typing import List, Any, Dict, Optional

import emoji
from PyQt6.QtCore import QModelIndex, Qt, QVariant, QSortFilterProxyModel, QMimeData, QByteArray, pyqtSignal, \
    QAbstractTableModel
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import QApplication
from overrides import overrides

from plotlyst.common import ALT_BACKGROUND_COLOR
from plotlyst.core.domain import Novel, Scene, CharacterArc, Character, \
    SelectionItem, SceneStage, SceneStructureAgenda, ScenePurposeType
from plotlyst.event.core import emit_event
from plotlyst.events import SceneStatusChangedEvent
from plotlyst.model.common import AbstractHorizontalHeaderBasedTableModel, SelectionItemsModel
from plotlyst.service.cache import acts_registry
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import emoji_font
from plotlyst.view.icons import IconRegistry, avatars


class BaseScenesTableModel:

    def verticalHeaderData(self, section: int, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return str(section + 1)
        if role == Qt.ItemDataRole.DecorationRole:
            return IconRegistry.hashtag_icon()


class ScenesTableModel(AbstractHorizontalHeaderBasedTableModel, BaseScenesTableModel):
    orderChanged = pyqtSignal()
    valueChanged = pyqtSignal(QModelIndex)
    sceneChanged = pyqtSignal(Scene)
    SceneRole = Qt.ItemDataRole.UserRole + 1

    MimeType: str = 'application/scene'

    ColPov = 0
    ColTitle = 1
    ColStorylines = 2
    ColCharacters = 3
    ColType = 4
    ColTime = 5
    ColArc = 6
    ColProgress = 7
    ColSynopsis = 8

    def __init__(self, novel: Novel, parent=None):
        self.novel = novel
        _headers = [''] * 9
        _headers[self.ColTitle] = 'Title'
        _headers[self.ColType] = 'Type'
        _headers[self.ColPov] = 'POV'
        _headers[self.ColStorylines] = 'Storylines'
        _headers[self.ColCharacters] = 'Characters'
        _headers[self.ColTime] = 'Day'
        _headers[self.ColArc] = 'Arc'
        _headers[self.ColProgress] = ''
        _headers[self.ColSynopsis] = 'Synopsis'
        super().__init__(_headers, parent)
        self._dragEnabled: bool = True

        self._action_icon = IconRegistry.action_scene_icon()
        self._resolved_action_icon = IconRegistry.action_scene_icon(resolved=True)
        self._trade_off_action_icon = IconRegistry.action_scene_icon(trade_off=True)
        self._motion_action_icon = IconRegistry.action_scene_icon(motion=True)
        self._reaction_icon = IconRegistry.reaction_scene_icon()

        self._character_insight_icon = IconRegistry.character_development_scene_icon()
        self._emotion_icon = IconRegistry.mood_scene_icon()
        self._setup_icon = IconRegistry.setup_scene_icon()
        self._exposition_icon = IconRegistry.exposition_scene_icon()

    def setDragEnabled(self, enabled: bool):
        self._dragEnabled = enabled

    @overrides
    def rowCount(self, parent: QModelIndex = Qt.ItemDataRole.DisplayRole) -> int:
        return len(self.novel.scenes)

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return QVariant()

        scene: Scene = self.novel.scenes[index.row()]
        if role == self.SceneRole:
            return scene
        elif role == Qt.ItemDataRole.FontRole:
            return QApplication.font()
        elif role == Qt.ItemDataRole.DisplayRole:
            if index.column() == self.ColTitle:
                return scene.title_or_index(self.novel)
            if index.column() == self.ColSynopsis:
                return scene.synopsis
            if index.column() == self.ColTime:
                return scene.day
        elif role == Qt.ItemDataRole.DecorationRole:
            if index.column() == self.ColType:
                if scene.wip:
                    return IconRegistry.wip_icon()
                elif scene.purpose == ScenePurposeType.Story:
                    if scene.outcome_resolution():
                        return self._resolved_action_icon
                    elif scene.outcome_trade_off():
                        return self._trade_off_action_icon
                    elif scene.outcome_motion():
                        return self._motion_action_icon
                    return self._action_icon
                elif scene.purpose == ScenePurposeType.Reaction:
                    return self._reaction_icon
                elif scene.purpose == ScenePurposeType.Setup:
                    return self._setup_icon
                elif scene.purpose == ScenePurposeType.Emotion:
                    return self._emotion_icon
                elif scene.purpose == ScenePurposeType.Character:
                    return self._character_insight_icon
                elif scene.purpose == ScenePurposeType.Exposition:
                    return self._exposition_icon
            elif index.column() == self.ColProgress:
                if scene.plot_pos_progress or scene.plot_neg_progress:
                    return IconRegistry.plot_charge_icon(scene.plot_pos_progress, scene.plot_neg_progress)
                elif scene.progress:
                    return IconRegistry.charge_icon(scene.progress)
            elif index.column() == self.ColPov:
                if scene.pov:
                    return avatars.avatar(scene.pov)
        elif role == Qt.ItemDataRole.ToolTipRole:
            if index.column() == self.ColPov:
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
        if self._dragEnabled:
            flags = flags | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled
        if index.column() == self.ColSynopsis:
            return flags | Qt.ItemFlag.ItemIsEditable
        if index.column() == self.ColArc:
            return flags | Qt.ItemFlag.ItemIsEditable
        if index.column() == self.ColTime:
            return flags | Qt.ItemFlag.ItemIsEditable
        return flags

    @overrides
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        scene: Scene = self.novel.scenes[index.row()]

        if index.column() == self.ColSynopsis:
            scene.synopsis = value
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
        self.sceneChanged.emit(scene)
        return True

    @overrides
    def mimeData(self, indexes: List[QModelIndex]) -> QMimeData:
        mime_data = QMimeData()
        scene = self.novel.scenes[indexes[0].row()]
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
        old_index = self.novel.scenes.index(scene)
        if row < old_index:
            new_index = row
        else:
            new_index = row - 1
        self.novel.scenes.insert(new_index, self.novel.scenes.pop(old_index))

        self.orderChanged.emit()
        return True



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

    def resetActsFilter(self):
        self.acts_filter.clear()
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
            else:
                return QApplication.font()
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() > self.ColNoneStage:
                return Qt.AlignmentFlag.AlignCenter
        if role == Qt.ItemDataRole.DisplayRole and index.column() > 1:
            if self._scene(index).stage and self._scene(index).stage.id == self._stage(index).id:
                return emoji.emojize(':check_mark:')
        if role == Qt.ItemDataRole.BackgroundRole and index.column() > self.ColNoneStage and self._highlighted_stage:
            if self.novel.stages[index.column() - 2] == self._highlighted_stage:
                return QBrush(QColor(ALT_BACKGROUND_COLOR))
        if role == Qt.ItemDataRole.DisplayRole and index.column() == self.ColTitle:
            return self._scene(index).title_or_index(self.novel)

    @overrides
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if index.column() == self.ColTitle or index.column() == self.ColNoneStage:
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
        scene = self._scene(index)
        if index.column() == self.ColNoneStage:
            scene.stage = None
        else:
            scene.stage = self._stage(index)

        RepositoryPersistenceManager.instance().update_scene(scene)
        self.modelReset.emit()
        emit_event(self.novel, SceneStatusChangedEvent(self, scene))

    def setHighlightedStage(self, stage: SceneStage):
        self._highlighted_stage = stage
        self.modelReset.emit()

    def _scene(self, index: QModelIndex) -> Scene:
        return self.novel.scenes[index.row()]

    def _stage(self, index: QModelIndex):
        return self.novel.stages[index.column() - 2]


class SceneConflictsModel(SelectionItemsModel):

    def __init__(self, novel: Novel, scene: Scene, agenda: SceneStructureAgenda, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.scene = scene
        self.agenda = agenda
        self._conflicts = []
        self.update()

    def update(self):
        if self.agenda.character_id:
            self._conflicts = [x for x in self.novel.conflicts if x.character_id == self.agenda.character_id]

    @overrides
    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self._conflicts)

    @overrides
    def _newItem(self) -> QModelIndex:
        pass

    @overrides
    def _insertItem(self, row: int) -> QModelIndex:
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
                    return avatars.avatar(conflict.conflicting_character(self.novel))
                else:
                    return IconRegistry.conflict_type_icon(conflict.type)
        return super(SceneConflictsModel, self).data(index, role)
