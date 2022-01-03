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
from typing import Union, List, Iterable, Set

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QFrame, QToolButton, QVBoxLayout, QMenu, QWidgetAction, \
    QSizePolicy, QPushButton
from overrides import overrides

from src.main.python.plotlyst.common import truncate_string
from src.main.python.plotlyst.core.domain import Character, Conflict, ConflictType, SelectionItem, Novel
from src.main.python.plotlyst.model.common import SelectionItemsModel
from src.main.python.plotlyst.view.common import line, text_color_with_bg_color
from src.main.python.plotlyst.view.icons import set_avatar, IconRegistry, avatars
from src.main.python.plotlyst.view.layout import FlowLayout
from src.main.python.plotlyst.view.widget.items_editor import ItemsEditorWidget


class Label(QFrame):
    def __init__(self, parent=None):
        super(Label, self).__init__(parent)
        _layout = QHBoxLayout()
        _layout.setSpacing(2)
        _layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(_layout)


class LabelsWidget(QWidget):

    def __init__(self, parent=None):
        super(LabelsWidget, self).__init__(parent)
        self.setLayout(FlowLayout(margin=0, spacing=3))

    def addText(self, text: str, color: str = '#7c98b3'):
        label = QLabel(truncate_string(text, 40))
        text_color = text_color_with_bg_color(color)
        label.setStyleSheet(
            f'''QLabel {{
                background-color: {color}; border-radius: 6px; color: {text_color};
            }}''')

        self.layout().addWidget(label)

    def addLabel(self, label: Union[Label, QLabel]):
        self.layout().addWidget(label)

    def clear(self):
        self.layout().clear()


class CharacterLabel(Label):
    def __init__(self, character: Character, pov: bool = False, parent=None):
        super(CharacterLabel, self).__init__(parent)
        self.character = character
        self.btnAvatar = QToolButton()
        self.btnAvatar.setStyleSheet('border: 0px;')
        self.btnAvatar.setIcon(QIcon(avatars.pixmap(self.character)))
        self.btnAvatar.setIconSize(QSize(24, 24))
        self.layout().addWidget(self.btnAvatar)
        self.layout().addWidget(QLabel(truncate_string(character.name)))

        role = self.character.role()
        if role:
            self.lblRole = QLabel()
            self.lblRole.setPixmap(IconRegistry.from_name(role.icon, role.icon_color).pixmap(QSize(24, 24)))
            self.layout().addWidget(line(vertical=True))
            self.layout().addWidget(self.lblRole)

        border_size = 3 if pov else 2
        border_color = '#3f7cac' if pov else '#bad7f2'

        self.setStyleSheet(f'''
        CharacterLabel {{
            border: {border_size}px solid {border_color}; 
            border-radius: 8px; padding-left: 3px; padding-right: 3px;}}
        ''')


class CharacterAvatarLabel(QToolButton):
    def __init__(self, character: Character, size: int = 24, parent=None):
        super(CharacterAvatarLabel, self).__init__(parent)
        self.setStyleSheet('border: 0px;')
        self.setIcon(QIcon(avatars.pixmap(character)))
        self.setIconSize(QSize(size, size))


class ConflictLabel(Label):
    def __init__(self, novel: Novel, conflict: Conflict, parent=None):
        super(ConflictLabel, self).__init__(parent)
        self.novel = novel
        self.conflict = conflict

        self.lblConflict = QLabel()
        self.lblConflict.setPixmap(IconRegistry.conflict_icon().pixmap(QSize(24, 24)))
        self.layout().addWidget(self.lblConflict)

        self.lblAvatar = QLabel()
        if self.conflict.conflicting_character(self.novel):
            set_avatar(self.lblAvatar, self.conflict.conflicting_character(self.novel), 24)
        else:
            if self.conflict.type == ConflictType.CHARACTER:
                icon = IconRegistry.conflict_character_icon()
            elif self.conflict.type == ConflictType.SOCIETY:
                icon = IconRegistry.conflict_society_icon()
            elif self.conflict.type == ConflictType.NATURE:
                icon = IconRegistry.conflict_nature_icon()
            elif self.conflict.type == ConflictType.TECHNOLOGY:
                icon = IconRegistry.conflict_technology_icon()
            elif self.conflict.type == ConflictType.SUPERNATURAL:
                icon = IconRegistry.conflict_supernatural_icon()
            elif self.conflict.type == ConflictType.SELF:
                icon = IconRegistry.conflict_self_icon()
            else:
                icon = IconRegistry.conflict_icon()
            self.lblAvatar.setPixmap(icon.pixmap(QSize(24, 24)))
        self.layout().addWidget(self.lblAvatar)
        self.layout().addWidget(QLabel(self.conflict.text))

        self.setStyleSheet('''
                ConflictLabel {
                    border: 2px solid #f3a712;
                    border-radius: 8px; padding-left: 3px; padding-right: 3px;}
                ''')


class TraitLabel(QLabel):
    def __init__(self, trait: str, positive: bool = True, parent=None):
        super(TraitLabel, self).__init__(parent)

        self.setText(trait)

        if positive:
            bg_color = '#519872'
            border_color = '#034732'
        else:
            bg_color = '#db5461'
            border_color = '#ef2917'
        self.setStyleSheet(f'''TraitLabel {{
            background-color: {bg_color};
            border: 2px solid {border_color};
            border-radius: 8px;
            color: white;
            padding-left: 0px; padding-right: 0px; padding-top: 0px; padding-bottom: 0px;
        }}''')


class SelectionItemLabel(Label):
    def __init__(self, item: SelectionItem, parent=None):
        super(SelectionItemLabel, self).__init__(parent)
        self.item = item

        if self.item.icon:
            self.lblIcon = QLabel()
            self.lblIcon.setPixmap(IconRegistry.from_name(self.item.icon, self.item.icon_color).pixmap(QSize(24, 24)))
            self.layout().addWidget(self.lblIcon)

        self.lblText = QLabel(self.item.text)
        self.layout().addWidget(self.lblText)

        if item.color_hexa:
            bg_color = item.color_hexa
            text_color = text_color_with_bg_color(bg_color)
        else:
            bg_color = 'white'
            text_color = 'black'

        self.setStyleSheet(f'''
                        SelectionItemLabel {{
                            border: 2px solid {self._borderColor()};
                            border-radius: 8px; padding-left: 3px; padding-right: 3px;
                            background-color: {bg_color};
                            }}
                        QLabel {{
                            color: {text_color};
                        }}
                        ''')

    def _borderColor(self) -> str:
        return '#2e5266'


class GoalLabel(SelectionItemLabel):
    def __init__(self, item: SelectionItem, parent=None):
        super(GoalLabel, self).__init__(item, parent)
        self.item = item

        self.lblGoal = QLabel()
        self.lblGoal.setPixmap(IconRegistry.goal_icon().pixmap(QSize(24, 24)))
        self.layout().insertWidget(0, self.lblGoal)

    @overrides
    def _borderColor(self):
        return 'darkBlue'


class LabelsEditorWidget(QFrame):
    def __init__(self, alignment=Qt.Orientation.Horizontal, checkable: bool = True, parent=None):
        super(LabelsEditorWidget, self).__init__(parent)
        self.checkable = checkable
        self.setLineWidth(1)
        self.setFrameShape(QFrame.Shape.Box)
        self.setStyleSheet('LabelsEditorWidget {background: white;}')
        if alignment == Qt.Orientation.Horizontal:
            self.setLayout(QHBoxLayout())
        else:
            self.setLayout(QVBoxLayout())
        self.layout().setSpacing(1)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self._labels_index = {}
        self.clear()

        self.btnEdit = QPushButton()
        self.btnEdit.setIcon(IconRegistry.plus_edit_icon())
        self.btnEdit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)
        self.btnEdit.setStyleSheet('QPushButton::menu-indicator{width:0px;} QPushButton {padding:1 5 1 5;}')

        self._model = self._initModel()
        self._model.item_edited.connect(self._selectionChanged)
        if self.checkable:
            self._model.setCheckable(True, SelectionItemsModel.ColName)
        self._popup = self._initPopupWidget()
        self._model.selection_changed.connect(self._selectionChanged)

        menu = QMenu(self.btnEdit)
        action = QWidgetAction(menu)
        action.setDefaultWidget(self._popup)
        menu.addAction(action)
        self.btnEdit.setMenu(menu)
        self.layout().addWidget(self.btnEdit, alignment=Qt.AlignmentFlag.AlignTop)

        self._wdgLabels = LabelsWidget()
        self._wdgLabels.setStyleSheet('LabelsWidget {border: 1px solid black;}')
        self._wdgLabels.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.layout().addWidget(self._wdgLabels)

    def clear(self):
        self._labels_index.clear()
        for item in self.items():
            self._labels_index[item.text] = item

    @abstractmethod
    def _initModel(self) -> SelectionItemsModel:
        pass

    @abstractmethod
    def items(self) -> List[SelectionItem]:
        pass

    def selectedItems(self) -> Set[SelectionItem]:
        return self._model.selections()

    def value(self) -> List[str]:
        return [x.text for x in self._model.selections()]

    def setValue(self, values: List[str]):
        self._model.uncheckAll()
        for v in values:
            item = self._labels_index.get(v)
            if item:
                self._model.checkItem(item)
        self._model.modelReset.emit()
        self._selectionChanged()

    def _initPopupWidget(self) -> QWidget:
        wdg = ItemsEditorWidget()
        wdg.setModel(self._model)
        return wdg

    def _selectionChanged(self):
        self._wdgLabels.clear()
        self._addItems(self._model.selections())

    def _addItems(self, items: Iterable[SelectionItem]):
        for item in items:
            self._wdgLabels.addLabel(SelectionItemLabel(item))
