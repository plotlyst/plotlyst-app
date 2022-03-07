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
from abc import abstractmethod
from typing import Any, List

from PyQt5.QtCore import QModelIndex, Qt, QAbstractTableModel
from overrides import overrides

from src.main.python.plotlyst.core.domain import Novel, SelectionItem, Conflict, SceneStage, Plot, PlotType, TagType, \
    Tag
from src.main.python.plotlyst.event.core import emit_event
from src.main.python.plotlyst.events import PlotCreatedEvent, NovelReloadRequestedEvent
from src.main.python.plotlyst.model.common import SelectionItemsModel, DefaultSelectionItemsModel
from src.main.python.plotlyst.settings import STORY_LINE_COLOR_CODES
from src.main.python.plotlyst.view.icons import avatars, IconRegistry
from src.main.python.plotlyst.worker.persistence import RepositoryPersistenceManager


class _NovelSelectionItemsModel(SelectionItemsModel):

    def __init__(self, novel: Novel):
        self.novel = novel
        self.repo = RepositoryPersistenceManager.instance()
        super().__init__()

    @abstractmethod
    @overrides
    def _newItem(self) -> QModelIndex:
        pass

    @abstractmethod
    @overrides
    def item(self, index: QModelIndex) -> SelectionItem:
        pass

    @overrides
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.DisplayRole) -> bool:
        updated = super().setData(index, value, role)
        if updated and role != Qt.CheckStateRole:
            self.repo.update_novel(self.novel)
        return updated


class NovelPlotsModel(_NovelSelectionItemsModel):
    ColPlotType: int = 3
    ColCharacter: int = 4
    ColValueType: int = 5

    @overrides
    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self.novel.plots)

    @overrides
    def columnCount(self, parent: QModelIndex = None) -> int:
        return 6

    @overrides
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                if section == self.ColName:
                    return 'Plot title'
                if section == self.ColPlotType:
                    return 'Type'
                if section == self.ColCharacter:
                    return 'Linked character'
                if section == self.ColValueType:
                    return 'Value'
            if role == Qt.DecorationRole:
                if section == self.ColCharacter:
                    return IconRegistry.character_icon('white', 'white')

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if index.column() < self.ColPlotType:
            return super(NovelPlotsModel, self).data(index, role)
        plot: Plot = self.novel.plots[index.row()]
        if index.column() == self.ColPlotType:
            if plot.plot_type == PlotType.Main:
                if role == Qt.DisplayRole:
                    return 'Main'
                if role == Qt.DecorationRole:
                    return IconRegistry.cause_and_effect_icon()
            if plot.plot_type == PlotType.Internal:
                if role == Qt.DisplayRole:
                    return 'Internal'
                if role == Qt.DecorationRole:
                    return IconRegistry.conflict_self_icon()
            if plot.plot_type == PlotType.Subplot:
                if role == Qt.DisplayRole:
                    return 'Subplot'
                if role == Qt.DecorationRole:
                    return IconRegistry.from_name('mdi.source-branch')
        if index.column() == self.ColCharacter:
            character = plot.character(self.novel)
            if character:
                if role == Qt.DisplayRole:
                    return character.name
                if role == Qt.DecorationRole:
                    return avatars.avatar(character)

    @overrides
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.DisplayRole) -> bool:
        updated = super().setData(index, value, role)

        if not updated:
            if index.column() == self.ColPlotType:
                self.novel.plots[index.row()].plot_type = value
                updated = True
            if index.column() == self.ColCharacter:
                self.novel.plots[index.row()].character_id = value.id
                updated = True

            if updated and role != Qt.CheckStateRole:
                self.repo.update_novel(self.novel)
        return updated

    @overrides
    def columnIsEditable(self, column: int) -> bool:
        return column in [self.ColName, self.ColCharacter, self.ColPlotType, self.ColValueType]

    @overrides
    def item(self, index: QModelIndex) -> SelectionItem:
        return self.novel.plots[index.row()]

    @overrides
    def _newItem(self) -> QModelIndex:
        plot = Plot(text='')
        self.novel.plots.append(plot)
        plot.color_hexa = STORY_LINE_COLOR_CODES[
            (len(self.novel.plots) - 1) % len(STORY_LINE_COLOR_CODES)]
        self.repo.update_novel(self.novel)

        emit_event(PlotCreatedEvent(self))

        return self.index(self.rowCount() - 1, 0)

    @overrides
    def remove(self, index: QModelIndex):
        super().remove(index)
        self.novel.plots.pop(index.row())

        self.repo.update_novel(self.novel)
        emit_event(NovelReloadRequestedEvent(self))


class NovelTagsModel(_NovelSelectionItemsModel):

    def __init__(self, novel: Novel, tagType: TagType, tags: List[Tag]):
        super(NovelTagsModel, self).__init__(novel)
        self.tagType = tagType
        self.tags = tags

    @overrides
    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self.tags)

    @overrides
    def item(self, index: QModelIndex) -> SelectionItem:
        return self.tags[index.row()]

    @overrides
    def _newItem(self) -> QModelIndex:
        tag = Tag(text='', tag_type=self.tagType.text)
        self.novel.tags[self.tagType].append(tag)
        self.repo.update_novel(self.novel)

        return self.index(self.rowCount() - 1, 0)

    @overrides
    def remove(self, index: QModelIndex):
        super().remove(index)
        self.novel.tags[self.tagType].pop(index.row())

        self.repo.update_novel(self.novel)
        emit_event(NovelReloadRequestedEvent(self))


class NovelConflictsModel(QAbstractTableModel):
    ColPov = 0
    ColType = 1
    ColPhrase = 2

    ConflictRole = Qt.UserRole + 1

    def __init__(self, novel: Novel, parent=None):
        super(NovelConflictsModel, self).__init__(parent)
        self.novel = novel

    @overrides
    def rowCount(self, parent: QModelIndex = ...) -> int:
        return len(self.novel.conflicts)

    @overrides
    def columnCount(self, parent: QModelIndex = ...) -> int:
        return 3

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        conflict: Conflict = self.novel.conflicts[index.row()]
        if role == self.ConflictRole:
            return conflict
        if index.column() == self.ColPov and role == Qt.DecorationRole:
            return avatars.avatar(conflict.character(self.novel))
        if index.column() == self.ColType and role == Qt.DecorationRole:
            if conflict.conflicting_character(self.novel):
                return avatars.avatar(conflict.conflicting_character(self.novel))
            else:
                return IconRegistry.conflict_type_icon(conflict.type)
        if index.column() == self.ColPhrase and role == Qt.DisplayRole:
            return conflict.text

    @overrides
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        flags = super(NovelConflictsModel, self).flags(index)
        if index.column() == self.ColPhrase:
            return flags | Qt.ItemIsEditable
        return flags

    @overrides
    def setData(self, index: QModelIndex, value: Any, role: int = ...) -> bool:
        if index.column() == self.ColPhrase and role == Qt.EditRole:
            self.novel.conflicts[index.row()].text = value
            RepositoryPersistenceManager.instance().update_novel(self.novel)
            return True
        return False


class NovelStagesModel(DefaultSelectionItemsModel):
    @overrides
    def _newItem(self) -> QModelIndex:
        self._items.append(SceneStage(''))
        return self.index(self.rowCount() - 1, 0)
