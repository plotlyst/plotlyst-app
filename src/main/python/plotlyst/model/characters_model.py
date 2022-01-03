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
from typing import List, Any, Optional

from PyQt6.QtCore import QModelIndex, Qt, QVariant, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from overrides import overrides

from src.main.python.plotlyst.core.domain import Character, Novel, Scene, SelectionItem, enneagram_field
from src.main.python.plotlyst.model.common import AbstractHorizontalHeaderBasedTableModel
from src.main.python.plotlyst.view.icons import avatars, IconRegistry


class CharactersTableModel(AbstractHorizontalHeaderBasedTableModel):
    CharacterRole = Qt.ItemDataRole.UserRole + 1
    SortRole = Qt.ItemDataRole.UserRole + 2

    ColName = 0
    ColRole = 1
    ColEnneagram = 2
    ColMbti = 3
    ColGoals = 4

    def __init__(self, novel: Novel, parent=None):
        self._data: List[Character] = novel.characters
        _headers = [''] * 5
        _headers[self.ColName] = 'Name'
        _headers[self.ColRole] = ''
        _headers[self.ColEnneagram] = ''
        _headers[self.ColMbti] = 'MBTI'
        _headers[self.ColGoals] = 'Story goals'
        super().__init__(_headers, parent)

    @overrides
    def rowCount(self, parent: QModelIndex = Qt.ItemDataRole.DisplayRole) -> int:
        return len(self._data)

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        character: Character = self._data[index.row()]
        if role == self.CharacterRole:
            return character

        if index.column() == self.ColName:
            if role == Qt.ItemDataRole.DisplayRole or role == self.SortRole:
                return character.name
            if role == Qt.ItemDataRole.DecorationRole:
                return QIcon(avatars.pixmap(character))
        if index.column() == self.ColRole:
            return self._dataForSelectionItem(character.role(), role, displayText=False)
        if index.column() == self.ColEnneagram:
            enneagram = character.enneagram()
            if role == self.SortRole:
                return enneagram_field.selections.index(enneagram)
            return self._dataForSelectionItem(enneagram, role, displayText=False)
        if index.column() == self.ColMbti:
            return self._dataForSelectionItem(character.mbti(), role)
        if index.column() == self.ColGoals:
            if role == Qt.ItemDataRole.DisplayRole or role == self.SortRole:
                return ', '.join(character.goals())

    def _dataForSelectionItem(self, item: SelectionItem, role: int, displayText: bool = True, sortByText: bool = True):
        if item is None:
            return QVariant()
        if displayText and role == Qt.ItemDataRole.DisplayRole:
            return item.text
        if sortByText and role == self.SortRole:
            return item.text
        if role == Qt.ItemDataRole.DecorationRole:
            return IconRegistry.from_name(item.icon, item.icon_color)


class CharactersSceneAssociationTableModel(CharactersTableModel):
    selection_changed = pyqtSignal()

    def __init__(self, novel: Novel):
        super().__init__(novel)
        self.scene: Optional[Scene] = None

    def setScene(self, scene: Scene):
        self.scene = scene

    @overrides
    def columnCount(self, parent: QModelIndex = Qt.ItemDataRole.DisplayRole) -> int:
        return 1

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not self.scene:
            return QVariant()

        character: Character = self._data[index.row()]
        if character is self.scene.pov:
            if role == Qt.ItemDataRole.ToolTipRole:
                return 'POV character'
        elif character in self.scene.characters:
            if role == Qt.ItemDataRole.FontRole:
                font = QFont()
                font.setBold(True)
                return font
            elif role == Qt.ItemDataRole.CheckStateRole:
                return Qt.CheckState.Checked
        elif role == Qt.ItemDataRole.CheckStateRole:
            return Qt.CheckState.Unchecked

        return super(CharactersSceneAssociationTableModel, self).data(index, role)

    @overrides
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        if not self.scene:
            return flags
        if self._data[index.row()] is self.scene.pov:
            return Qt.ItemFlag.NoItemFlags
        return flags | Qt.ItemFlag.ItemIsUserCheckable

    def toggleSelection(self, index: QModelIndex):
        character = self._data[index.row()]
        if character is self.scene.pov:
            return
        if character in self.scene.characters:
            self.scene.characters.remove(character)
        else:
            self.scene.characters.append(character)

        self.selection_changed.emit()
        self.modelReset.emit()

    def update(self):
        if self.scene.pov in self.scene.characters:
            self.scene.characters.remove(self.scene.pov)
        self.modelReset.emit()
