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
from typing import List, Any, Set, Optional, Dict

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, QAbstractItemModel, QSortFilterProxyModel, pyqtSignal, \
    QVariant
from PyQt6.QtGui import QFont, QColor, QBrush
from overrides import overrides

from src.main.python.plotlyst.common import WIP_COLOR, PIVOTAL_COLOR
from src.main.python.plotlyst.core.domain import SelectionItem, Novel, Scene
from src.main.python.plotlyst.model.tree_model import TreeItemModel
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.worker.cache import acts_registry


def emit_column_changed_in_tree(model: TreeItemModel, column: int, parent: QModelIndex):
    model.dataChanged.emit(model.index(0, column, parent),
                           model.index(model.rowCount(parent) - 1, column, parent))


def emit_column_changed(model: QAbstractItemModel, column: int = 0):
    model.dataChanged.emit(model.index(0, column),
                           model.index(model.rowCount() - 1, column))


class AbstractHorizontalHeaderBasedTableModel(QAbstractTableModel):

    def __init__(self, headers: List[str], parent=None):
        super().__init__(parent)
        self.headers = headers

    @overrides
    def columnCount(self, parent: QModelIndex = Qt.ItemDataRole.DisplayRole) -> int:
        return len(self.headers)

    @overrides
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.headers[section]

            return str(section + 1)
        return super().headerData(section, orientation, role)


def proxy(model: QAbstractItemModel) -> QSortFilterProxyModel:
    _proxy = QSortFilterProxyModel()
    _proxy.setSourceModel(model)
    _proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    _proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    return _proxy


class SelectionItemsModel(QAbstractTableModel):
    selection_changed = pyqtSignal()
    item_edited = pyqtSignal()
    ItemRole: int = Qt.ItemDataRole.UserRole + 1

    ColIcon: int = 0
    ColBgColor: int = 1
    ColName: int = 2

    def __init__(self, parent=None):
        super(SelectionItemsModel, self).__init__(parent)
        self._checkable: bool = False
        self._checkable_column: int = 0
        self._checked: Set[SelectionItem] = set()
        self._editable: bool = True

    def selections(self) -> Set[SelectionItem]:
        return self._checked

    def setCheckable(self, checkable: bool, column: int):
        self._checkable = checkable
        self._checkable_column = column
        self.modelReset.emit()

    def setEditable(self, editable: bool):
        self._editable = editable
        self.modelReset.emit()

    def checkItem(self, item: SelectionItem):
        if self._checkable:
            self._checked.add(item)
            self.selection_changed.emit()

    def uncheckItem(self, item: SelectionItem):
        if self._checkable and item in self._checked:
            self._checked.remove(item)
            self.selection_changed.emit()

    def uncheckAll(self):
        self._checked.clear()
        self.modelReset.emit()

    def add(self) -> int:
        index = self._newItem()
        item = self.item(index)
        if self._checkable:
            self._checked.add(item)
            self.selection_changed.emit()

        self.modelReset.emit()

        return index.row()

    @abstractmethod
    def _newItem(self) -> QModelIndex:
        pass

    def remove(self, index: QModelIndex):
        if self._checkable:
            self.uncheckItem(self.item(index))
        self.modelReset.emit()

    @overrides
    def columnCount(self, parent: QModelIndex = None) -> int:
        return 3

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        item = self.item(index)
        if role == self.ItemRole:
            return item
        if index.column() == self.ColIcon and role == Qt.ItemDataRole.DecorationRole:
            if item.icon:
                return IconRegistry.from_name(item.icon,
                                              item.icon_color)
            return IconRegistry.icons_icon('lightgrey')
        if index.column() == self.ColIcon and role == Qt.ItemDataRole.BackgroundRole:
            if item.icon and item.icon_color in ['#ffffff', 'white']:
                return QBrush(QColor('lightGrey'))
        if index.column() == self.ColName and role == Qt.ItemDataRole.DisplayRole:
            return item.text
        if role == Qt.ItemDataRole.CheckStateRole and self._checkable and index.column() == self._checkable_column:
            return Qt.CheckState.Checked if item in self._checked else Qt.CheckState.Unchecked
        if role == Qt.ItemDataRole.FontRole and self._checkable and index.column() == self._checkable_column:
            if item in self._checked:
                font = QFont()
                font.setBold(True)
                return font
        if index.column() == self.ColBgColor:
            if role == Qt.ItemDataRole.BackgroundRole and item.color_hexa:
                return QBrush(QColor(item.color_hexa))
            if role == Qt.ItemDataRole.DecorationRole and (
                    not item.color_hexa or item.color_hexa in ['white', '#ffffff']):
                return IconRegistry.from_name('mdi.palette', color='lightgrey')

    @overrides
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        if self._checkable and index.column() == self._checkable_column:
            flags = flags | Qt.ItemFlag.ItemIsUserCheckable
        if self._editable and self.columnIsEditable(index.column()):
            flags = flags | Qt.ItemFlag.ItemIsEditable

        return flags

    @overrides
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.DisplayRole) -> bool:
        item: SelectionItem = self.item(index)
        if role == Qt.ItemDataRole.EditRole:
            if index.column() == self.ColName:
                was_checked = item in self._checked
                if was_checked:
                    self._checked.remove(item)
                item.text = value
                if was_checked:
                    self._checked.add(item)
                self.item_edited.emit()
                return True
        if role == Qt.ItemDataRole.DecorationRole:
            item.icon = value[0]
            item.icon_color = value[1]
            self.item_edited.emit()
            return True
        if role == Qt.ItemDataRole.CheckStateRole:
            if value == Qt.CheckState.Checked:
                self._checked.add(item)
            elif value == Qt.CheckState.Unchecked:
                self._checked.remove(item)
            self.selection_changed.emit()
            return True
        if role == Qt.ItemDataRole.BackgroundRole:
            item.color_hexa = value
            self.item_edited.emit()
            return True
        return False

    def items(self) -> List[SelectionItem]:
        _items = []
        for row in range(self.rowCount()):
            _items.append(self.item(self.index(row, 0)))
        return _items

    @abstractmethod
    def item(self, index: QModelIndex) -> SelectionItem:
        pass

    def defaultEditableColumn(self) -> int:
        return self.ColName

    def columnIsEditable(self, column: int) -> bool:
        return column == self.ColName


class DefaultSelectionItemsModel(SelectionItemsModel):

    def __init__(self, items: List[SelectionItem], parent=None):
        super(DefaultSelectionItemsModel, self).__init__(parent)
        self._items = items

    @overrides
    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self._items)

    @overrides
    def _newItem(self) -> QModelIndex:
        self._items.append(SelectionItem('new'))
        return self.index(self.rowCount() - 1, 0)

    @overrides
    def item(self, index: QModelIndex) -> SelectionItem:
        return self._items[index.row()]

    @overrides
    def remove(self, index: QModelIndex):
        super().remove(index)
        self._items.pop(index.row())


class DistributionModel(QAbstractTableModel):
    SortRole: int = Qt.ItemDataRole.UserRole + 1
    SceneRole: int = Qt.ItemDataRole.UserRole + 2

    IndexMeta: int = 0
    IndexTags: int = 1

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel
        self._highlighted_scene: Optional[QModelIndex] = None
        self._highlighted_tags: List[QModelIndex] = []

    @overrides
    def columnCount(self, parent: QModelIndex = None) -> int:
        return len(self.novel.scenes) + 2

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == self.SceneRole:
            if index.column() > self.IndexTags:
                return self.novel.scenes[index.column() - 2]
            else:
                return None
        if index.column() == self.IndexTags:
            if role == Qt.ItemDataRole.ForegroundRole:
                if self._highlighted_tags and index not in self._highlighted_tags:
                    return QBrush(QColor(Qt.GlobalColor.gray))
                else:
                    return self._dataForTag(index, role)
            elif role == self.SortRole:
                count = 0
                for i, _ in enumerate(self.novel.scenes):
                    if self._match_by_row_col(index.row(), i + 2):
                        count += 1
                return count
            else:
                return self._dataForTag(index, role)
        elif index.column() == self.IndexMeta:
            return self._dataForMeta(index, role)
        elif role == Qt.ItemDataRole.ToolTipRole:
            tooltip = f'{index.column() - 1}. {self.novel.scenes[index.column() - 2].title}'
            if self.novel.scenes[index.column() - 2].beat:
                tooltip += f' ({self.novel.scenes[index.column() - 2].beat.text})'
            return tooltip
        elif role == Qt.ItemDataRole.BackgroundRole:
            if self._match(index):
                if self._highlighted_scene:
                    if self._highlighted_scene.column() != index.column():
                        return QBrush(QColor(Qt.GlobalColor.gray))
                if self._highlighted_tags:
                    if not all([self._match_by_row_col(x.row(), index.column()) for x in self._highlighted_tags]):
                        return QBrush(QColor(Qt.GlobalColor.gray))
                if self.novel.scenes[index.column() - 2].wip:
                    return QBrush(QColor(WIP_COLOR))
                if self.novel.scenes[index.column() - 2].beat:
                    return QBrush(QColor(PIVOTAL_COLOR))
                return QBrush(QColor('darkblue'))
        return QVariant()

    @overrides
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)

        if self._highlighted_scene and index.column() == self.IndexTags:
            if not self._match_by_row_col(index.row(), self._highlighted_scene.column()):
                return Qt.ItemFlag.NoItemFlags

        return flags

    def commonScenes(self) -> int:
        matches = 0
        for y in range(2, self.columnCount()):
            if all(self._match_by_row_col(x.row(), y) for x in self._highlighted_tags):
                matches += 1
        return matches

    def highlightTags(self, indexes: List[QModelIndex]):
        self._highlighted_tags = indexes
        self._highlighted_scene = None
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))

    def highlightScene(self, index: QModelIndex):
        if self._match(index):
            self._highlighted_scene = index
        else:
            self._highlighted_scene = None

        self._highlighted_tags.clear()
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))

    def _match(self, index: QModelIndex):
        return self._match_by_row_col(index.row(), index.column())

    @abstractmethod
    def _dataForTag(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        pass

    def _dataForMeta(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        return QVariant()

    @abstractmethod
    def _match_by_row_col(self, row: int, column: int) -> bool:
        pass


class DistributionFilterProxyModel(QSortFilterProxyModel):

    def __init__(self):
        super().__init__()
        self.acts_filter: Dict[int, bool] = {}

    def setActsFilter(self, act: int, filter: bool):
        self.acts_filter[act] = filter
        self.invalidateFilter()

    @overrides
    def filterAcceptsColumn(self, source_column: int, source_parent: QModelIndex) -> bool:
        filtered = super().filterAcceptsColumn(source_column, source_parent)
        if not filtered:
            return filtered

        scene: Optional[Scene] = self.sourceModel().data(self.sourceModel().index(0, source_column),
                                                         role=DistributionModel.SceneRole)
        if not scene:
            return filtered

        for act, toggled in self.acts_filter.items():
            if acts_registry.act(scene) == act and not toggled:
                return False

        return filtered


class ActionBasedTreeModel:
    def __init__(self):
        self._action_index: Optional[QModelIndex] = None

    def displayAction(self, index: QModelIndex):
        self._updateActionIndex(index)
        self._emitActionsChanged(index)

    def _updateActionIndex(self, index: QModelIndex):
        if index.row() >= 0:
            if self._action_index and self._action_index.row() == index.row() \
                    and self._action_index.parent() == index.parent():  # same index
                return
            self._action_index = index
        else:
            self._action_index = None

    @abstractmethod
    def _emitActionsChanged(self, index: QModelIndex):
        pass
