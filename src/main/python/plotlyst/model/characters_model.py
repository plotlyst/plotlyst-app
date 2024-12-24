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
from typing import Any, Optional

from PyQt6.QtCore import QModelIndex, Qt, QVariant, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QApplication
from overrides import overrides

from plotlyst.common import RELAXED_WHITE_COLOR, MAXIMUM_SIZE
from plotlyst.core.domain import Character, Novel, Scene, SelectionItem
from plotlyst.core.template import enneagram_field
from plotlyst.model.common import AbstractHorizontalHeaderBasedTableModel
from plotlyst.view.icons import avatars, IconRegistry


class CharactersTableModel(AbstractHorizontalHeaderBasedTableModel):
    CharacterRole = Qt.ItemDataRole.UserRole + 1
    SortRole = Qt.ItemDataRole.UserRole + 2

    ColName = 0
    ColRole = 1
    ColAge = 2
    ColGender = 3
    ColOccupation = 4
    ColEnneagram = 5
    ColMbti = 6
    ColSummary = 7

    def __init__(self, novel: Novel, parent=None):
        self._novel = novel
        _headers = [''] * 8
        _headers[self.ColName] = 'Name'
        _headers[self.ColRole] = ''
        _headers[self.ColAge] = 'Age'
        _headers[self.ColGender] = ''
        _headers[self.ColOccupation] = 'Occupation'
        _headers[self.ColEnneagram] = ''
        _headers[self.ColMbti] = 'MBTI'
        _headers[self.ColSummary] = 'Summary'
        super().__init__(_headers, parent)

    @overrides
    def rowCount(self, parent: QModelIndex = Qt.ItemDataRole.DisplayRole) -> int:
        return len(self._novel.characters)

    @overrides
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal:
            if section == self.ColRole:
                if role == Qt.ItemDataRole.DecorationRole:
                    return IconRegistry.from_name('fa5s.chess-bishop', color=RELAXED_WHITE_COLOR)
                elif role == Qt.ItemDataRole.ToolTipRole:
                    return 'Character role'
            elif section == self.ColEnneagram:
                if role == Qt.ItemDataRole.DecorationRole:
                    return IconRegistry.from_name('mdi.numeric-9-circle', color=RELAXED_WHITE_COLOR)
                elif role == Qt.ItemDataRole.ToolTipRole:
                    return 'Enneagram'
            elif section == self.ColGender:
                if role == Qt.ItemDataRole.DecorationRole:
                    return IconRegistry.from_name('mdi.gender-female', color=RELAXED_WHITE_COLOR)
                elif role == Qt.ItemDataRole.ToolTipRole:
                    return 'Gender'
            else:
                return super().headerData(section, orientation, role)

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        character: Character = self._novel.characters[index.row()]
        if role == self.CharacterRole:
            return character

        if role == Qt.ItemDataRole.FontRole:
            font = QApplication.font()
            if not character.name:
                font.setItalic(True)
            return font

        if index.column() == self.ColName:
            if role == Qt.ItemDataRole.DisplayRole or role == self.SortRole:
                return character.displayed_name() or 'Character'
            if role == Qt.ItemDataRole.DecorationRole:
                return avatars.avatar(character)
            if role == Qt.ItemDataRole.ForegroundRole and not character.name:
                return QColor('grey')

        if index.column() == self.ColRole:
            return self._dataForSelectionItem(character.role, role, displayText=False)
        if index.column() == self.ColAge:
            if character.age and not character.age_infinite:
                if role == Qt.ItemDataRole.DisplayRole or role == self.SortRole:
                    return character.age
            if character.age_infinite:
                if role == Qt.ItemDataRole.DecorationRole:
                    return IconRegistry.from_name('mdi.infinity')
                if role == self.SortRole:
                    return MAXIMUM_SIZE
        if index.column() == self.ColGender:
            if character.gender and role == Qt.ItemDataRole.DecorationRole:
                return IconRegistry.gender_icon(character.gender)
            if role == self.SortRole:
                return len(character.gender)
        if index.column() == self.ColOccupation:
            if role == Qt.ItemDataRole.DisplayRole or role == self.SortRole:
                return character.occupation
        if index.column() == self.ColEnneagram:
            enneagram = character.enneagram()
            if role == self.SortRole:
                return enneagram_field.selections.index(enneagram) if enneagram else -1
            return self._dataForSelectionItem(enneagram, role, displayText=False)
        if index.column() == self.ColMbti:
            return self._dataForSelectionItem(character.mbti(), role)
        if index.column() == self.ColSummary:
            if role == Qt.ItemDataRole.DisplayRole:
                return character.summary

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
        self.beginResetModel()
        self.endResetModel()

    @overrides
    def columnCount(self, parent: QModelIndex = Qt.ItemDataRole.DisplayRole) -> int:
        return 1

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not self.scene:
            return QVariant()

        if role == Qt.ItemDataRole.FontRole:
            return QApplication.font()

        character: Character = self._novel.characters[index.row()]
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
        if self._novel.characters[index.row()] is self.scene.pov:
            return Qt.ItemFlag.NoItemFlags
        return flags | Qt.ItemFlag.ItemIsUserCheckable

    def toggleSelection(self, index: QModelIndex):
        character = self._novel.characters[index.row()]
        if character is self.scene.pov:
            return
        if character in self.scene.characters:
            self.scene.characters.remove(character)
        else:
            self.scene.characters.append(character)

        self.selection_changed.emit()
        self.layoutChanged.emit()

    def update(self):
        if self.scene.pov in self.scene.characters:
            self.scene.characters.remove(self.scene.pov)
        self.modelReset.emit()
