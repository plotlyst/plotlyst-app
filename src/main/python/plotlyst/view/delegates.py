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

from PyQt6 import QtGui
from PyQt6.QtCore import Qt, QModelIndex, \
    QAbstractItemModel, QSize
from PyQt6.QtWidgets import QWidget, QStyledItemDelegate, \
    QStyleOptionViewItem, QTextEdit, QComboBox, QLineEdit, QSpinBox
from overrides import overrides

from src.main.python.plotlyst.core.domain import Scene, VERY_UNHAPPY, UNHAPPY, NEUTRAL, HAPPY, VERY_HAPPY, \
    Character
from src.main.python.plotlyst.model.scenes_model import ScenesTableModel
from src.main.python.plotlyst.view.icons import IconRegistry, avatars
from src.main.python.plotlyst.worker.persistence import RepositoryPersistenceManager


class ScenesViewDelegate(QStyledItemDelegate):
    avatarSize: int = 24

    @overrides
    def paint(self, painter: QtGui.QPainter, option: 'QStyleOptionViewItem', index: QModelIndex) -> None:
        super(ScenesViewDelegate, self).paint(painter, option, index)
        if index.column() == ScenesTableModel.ColCharacters:
            scene: Scene = index.data(ScenesTableModel.SceneRole)
            x = 3
            if scene.pov:
                self._drawAvatar(painter, option, x, scene.pov)
            x += 27
            for char in scene.characters:
                self._drawAvatar(painter, option, x, char)
                x += 27
                if x + 27 >= option.rect.width():
                    return

        elif index.column() == ScenesTableModel.ColArc:
            scene = index.data(ScenesTableModel.SceneRole)
            painter.drawPixmap(option.rect.x() + 3, option.rect.y() + 2,
                               IconRegistry.emotion_icon_from_feeling(scene.pov_arc()).pixmap(
                                   QSize(self.avatarSize, self.avatarSize)))

    def _drawAvatar(self, painter: QtGui.QPainter, option: 'QStyleOptionViewItem', x: int, character: Character):
        if character.avatar:
            painter.drawPixmap(option.rect.x() + x, option.rect.y() + 8,
                               avatars.pixmap(character).scaled(self.avatarSize, self.avatarSize,
                                                                Qt.AspectRatioMode.KeepAspectRatio,
                                                                Qt.TransformationMode.SmoothTransformation))
        else:
            painter.drawPixmap(option.rect.x() + x, option.rect.y() + 8,
                               avatars.name_initial_icon(character).pixmap(QSize(self.avatarSize, self.avatarSize)))

    @overrides
    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        if index.column() == ScenesTableModel.ColArc:
            return QComboBox(parent)
        if index.column() == ScenesTableModel.ColTime:
            return QSpinBox(parent)
        return QTextEdit(parent)

    @overrides
    def setEditorData(self, editor: QWidget, index: QModelIndex):
        edit_data = index.data(Qt.ItemDataRole.EditRole)
        if not edit_data:
            edit_data = index.data(Qt.ItemDataRole.DisplayRole)
        if isinstance(editor, QTextEdit) or isinstance(editor, QLineEdit):
            editor.setText(str(edit_data))
        elif isinstance(editor, QSpinBox):
            editor.setValue(edit_data)
        elif isinstance(editor, QComboBox):
            arc = index.data(ScenesTableModel.SceneRole).pov_arc()
            editor.addItem(IconRegistry.emotion_icon_from_feeling(VERY_UNHAPPY), '', VERY_UNHAPPY)
            if arc == VERY_UNHAPPY:
                editor.setCurrentIndex(0)
            editor.addItem(IconRegistry.emotion_icon_from_feeling(UNHAPPY), '', UNHAPPY)
            if arc == UNHAPPY:
                editor.setCurrentIndex(1)
            editor.addItem(IconRegistry.emotion_icon_from_feeling(NEUTRAL), '', NEUTRAL)
            if arc == NEUTRAL:
                editor.setCurrentIndex(2)
            editor.addItem(IconRegistry.emotion_icon_from_feeling(HAPPY), '', HAPPY)
            if arc == HAPPY:
                editor.setCurrentIndex(3)
            editor.addItem(IconRegistry.emotion_icon_from_feeling(VERY_HAPPY), '', VERY_HAPPY)
            if arc == VERY_HAPPY:
                editor.setCurrentIndex(4)

            editor.activated.connect(lambda: self._commit_and_close(editor))
            editor.showPopup()

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
