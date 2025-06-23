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

from PyQt6 import QtGui
from PyQt6.QtCore import Qt, QModelIndex, \
    QAbstractItemModel
from PyQt6.QtGui import QPainter, QIcon
from PyQt6.QtWidgets import QWidget, QStyledItemDelegate, \
    QStyleOptionViewItem, QTextEdit, QComboBox, QLineEdit, QSpinBox, QApplication
from overrides import overrides

from plotlyst.core.domain import Scene, Character
from plotlyst.model.scenes_model import ScenesTableModel
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.icons import avatars, IconRegistry


class ScenesViewDelegate(QStyledItemDelegate):
    avatarSize: int = 24
    iconSize: int = 20
    spacing: int = 3

    @overrides
    def paint(self, painter: QtGui.QPainter, option: 'QStyleOptionViewItem', index: QModelIndex) -> None:
        super(ScenesViewDelegate, self).paint(painter, option, index)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if index.column() == ScenesTableModel.ColCharacters:
            scene: Scene = index.data(ScenesTableModel.SceneRole)
            x = self.spacing
            for char in scene.characters:
                self._drawAvatar(painter, option, x, char)
                x += self.spacing + self.avatarSize
                if x + self.spacing + self.avatarSize >= option.rect.width():
                    return
        elif index.column() == ScenesTableModel.ColStorylines:
            scene: Scene = index.data(ScenesTableModel.SceneRole)
            x = self.spacing
            for plot in scene.plots():
                self._drawIcon(painter, IconRegistry.from_name(plot.icon, plot.icon_color), option, x, self.iconSize)
                x += self.spacing + self.iconSize
                if x + self.spacing + self.iconSize >= option.rect.width():
                    return

    def _drawAvatar(self, painter: QtGui.QPainter, option: 'QStyleOptionViewItem', x: int, character: Character):
        self._drawIcon(painter, avatars.avatar(character), option, x, self.avatarSize)

    def _drawIcon(self, painter: QtGui.QPainter, icon: QIcon, option: 'QStyleOptionViewItem', x: int, size: int):
        icon.paint(painter, option.rect.x() + x, option.rect.y() + 8, size,
                   size)

    @overrides
    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        if index.column() == ScenesTableModel.ColTime:
            return QSpinBox(parent)
        editor = QTextEdit(parent)
        editor.setFont(QApplication.font())
        return editor

    @overrides
    def setEditorData(self, editor: QWidget, index: QModelIndex):
        edit_data = index.data(Qt.ItemDataRole.EditRole)
        if not edit_data:
            edit_data = index.data(Qt.ItemDataRole.DisplayRole)
        if isinstance(editor, QTextEdit) or isinstance(editor, QLineEdit):
            editor.setText(str(edit_data))
        elif isinstance(editor, QSpinBox):
            editor.setValue(edit_data)

    @overrides
    def setModelData(self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex):
        if isinstance(editor, QComboBox):
            model.setData(index, editor.currentData(Qt.ItemDataRole.UserRole))
        elif isinstance(editor, QSpinBox):
            model.setData(index, editor.value())
        else:
            model.setData(index, editor.toPlainText())
        scene = index.data(ScenesTableModel.SceneRole)
        RepositoryPersistenceManager.instance().update_scene(scene)

    def _commit_and_close(self, editor):
        self.commitData.emit(editor)
        self.closeEditor.emit(editor)


class TextItemDelegate(QStyledItemDelegate):

    @overrides
    def setEditorData(self, editor: QWidget, index: QModelIndex):
        if isinstance(editor, QLineEdit):
            editor.deselect()
            editor.setText(index.data())
