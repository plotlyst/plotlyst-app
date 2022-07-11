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

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QMouseEvent
from PyQt5.QtWidgets import QWidget, QLabel, QFrame, QToolButton, QSizePolicy
from overrides import overrides
from qthandy import hbox, FlowLayout, vline, vbox, clear_layout, transparent, btn_popup

from src.main.python.plotlyst.common import truncate_string
from src.main.python.plotlyst.core.domain import Character, Conflict, SelectionItem, Novel, ScenePlotReference, \
    CharacterGoal, PlotValue, Scene
from src.main.python.plotlyst.env import app_env
from src.main.python.plotlyst.model.common import SelectionItemsModel
from src.main.python.plotlyst.view.common import text_color_with_bg_color, VisibilityToggleEventFilter
from src.main.python.plotlyst.view.icons import set_avatar, IconRegistry, avatars
from src.main.python.plotlyst.view.widget.display import Icon
from src.main.python.plotlyst.view.widget.input import RemovalButton
from src.main.python.plotlyst.view.widget.items_editor import ItemsEditorWidget


class Label(QFrame):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super(Label, self).__init__(parent)
        hbox(self, 0, 2)

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.clicked.emit()


class LabelsWidget(QWidget):

    def __init__(self, parent=None):
        super(LabelsWidget, self).__init__(parent)
        self.setLayout(FlowLayout())

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
        clear_layout(self)


class CharacterLabel(Label):
    def __init__(self, character: Character, parent=None):
        super(CharacterLabel, self).__init__(parent)
        self.character = character
        self.btnAvatar = QToolButton()
        self.btnAvatar.setStyleSheet('border: 0px;')
        self.btnAvatar.setIcon(QIcon(avatars.avatar(self.character)))
        self.btnAvatar.setIconSize(QSize(24, 24))
        self.layout().addWidget(self.btnAvatar)
        self.layout().addWidget(QLabel(truncate_string(character.name)))

        role = self.character.role
        if role:
            if not self.character.prefs.avatar.use_role:
                self.lblRole = QLabel()
                self.lblRole.setPixmap(IconRegistry.from_name(role.icon, role.icon_color).pixmap(QSize(24, 24)))
                self.layout().addWidget(vline())
                self.layout().addWidget(self.lblRole)
            border_color = role.icon_color
        else:
            border_color = '#bad7f2'

        self.setStyleSheet(f'''
        CharacterLabel {{
            border: 2px solid {border_color}; 
            border-radius: 8px; padding-left: 3px; padding-right: 3px;}}
        ''')


class CharacterAvatarLabel(QToolButton):
    def __init__(self, character: Character, size: int = 24, parent=None):
        super(CharacterAvatarLabel, self).__init__(parent)
        self.setStyleSheet('border: 0px;')
        self.setIcon(avatars.avatar(character))
        self.setIconSize(QSize(size, size))


class ConflictLabel(Label):
    removalRequested = pyqtSignal()

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
            icon = IconRegistry.conflict_type_icon(self.conflict.type)
            self.lblAvatar.setPixmap(icon.pixmap(QSize(24, 24)))
        self.layout().addWidget(self.lblAvatar)
        self.layout().addWidget(QLabel(self.conflict.text))

        self.btnRemoval = RemovalButton()
        self.layout().addWidget(self.btnRemoval)
        self.btnRemoval.clicked.connect(self.removalRequested.emit)

        self.setStyleSheet('''
                ConflictLabel {
                    border: 2px solid #f3a712;
                    border-radius: 8px; padding-left: 3px; padding-right: 3px;}
                ''')
        self.installEventFilter(VisibilityToggleEventFilter(self.btnRemoval, self))


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
    removalRequested = pyqtSignal()

    def __init__(self, item: SelectionItem, parent=None, removalEnabled: bool = False):
        super(SelectionItemLabel, self).__init__(parent)
        self.item = item

        self.btnIcon = QToolButton(self)
        self.btnIcon.clicked.connect(self.clicked.emit)
        transparent(self.btnIcon)
        self.layout().addWidget(self.btnIcon)
        if self.item.icon:
            self.btnIcon.setIcon(IconRegistry.from_name(self.item.icon, self.item.icon_color))
        else:
            self.btnIcon.setHidden(True)

        self.lblText = QLabel(self.item.text)
        self.layout().addWidget(self.lblText)
        self.btnRemoval = RemovalButton(self)
        self.layout().addWidget(self.btnRemoval)
        self.btnRemoval.clicked.connect(self.removalRequested.emit)
        self.btnRemoval.setVisible(removalEnabled)
        if removalEnabled:
            self.installEventFilter(VisibilityToggleEventFilter(self.btnRemoval, self))

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
        if not self.item.color_hexa and self.item.icon:
            return self.item.icon_color
        return '#2e5266'


class PlotLabel(SelectionItemLabel):
    @overrides
    def _borderColor(self):
        return self.item.icon_color


class PlotValueLabel(SelectionItemLabel):

    def __init__(self, item: PlotValue, parent=None, removalEnabled: bool = False):
        super(PlotValueLabel, self).__init__(item, parent, removalEnabled)
        self.value = item
        if item.negative:
            versusIcon = QToolButton(self)
            transparent(versusIcon)
            versusIcon.setIcon(IconRegistry.from_name('fa5s.arrows-alt-h'))
            self.layout().insertWidget(2, versusIcon)
            self.lblNegative = QLabel(item.negative)
            self.layout().insertWidget(3, self.lblNegative)

    @overrides
    def _borderColor(self):
        return self.item.icon_color


class ScenePlotValueLabel(PlotLabel):
    def __init__(self, plot_value: ScenePlotReference, parent=None, removalEnabled: bool = True):
        super(ScenePlotValueLabel, self).__init__(plot_value.plot, parent, removalEnabled)
        self.lblText.clear()
        self.lblText.hide()
        if not self.item.icon:
            self.btnIcon.setVisible(True)
            self.btnIcon.setIcon(IconRegistry.plot_type_icon(plot_value.plot.plot_type))


class CharacterGoalLabel(SelectionItemLabel):
    def __init__(self, novel: Novel, characterGoal: CharacterGoal, parent=None, removalEnabled: bool = False):
        super(CharacterGoalLabel, self).__init__(characterGoal.goal(novel), parent, removalEnabled)

        self.lblGoal = QLabel()
        self.lblGoal.setPixmap(IconRegistry.goal_icon().pixmap(QSize(24, 24)))
        self.layout().insertWidget(0, self.lblGoal)

    @overrides
    def _borderColor(self):
        return 'darkBlue'


class SceneLabel(Label):
    def __init__(self, scene: Scene, parent=None):
        super(SceneLabel, self).__init__(parent)

        self.btnTypeIcon = Icon()

        self.lblTitle = QLabel(self)
        self.layout().addWidget(self.btnTypeIcon)
        self.layout().addWidget(self.lblTitle)

        self.setScene(scene)

        self.setStyleSheet(f'''
                            SceneLabel {{
                                border: 1px solid black;
                                border-radius: 8px; padding: 2px;
                                }}
                            ''')

    def setScene(self, scene: Scene):
        self.btnTypeIcon.setIcon(IconRegistry.scene_type_icon(scene))
        self.lblTitle.setText(scene.title_or_index(app_env.novel))


class LabelsEditorWidget(QFrame):
    def __init__(self, alignment=Qt.Horizontal, checkable: bool = True, parent=None):
        super(LabelsEditorWidget, self).__init__(parent)
        self.checkable = checkable
        self.setLineWidth(1)
        self.setFrameShape(QFrame.Box)
        self.setStyleSheet('LabelsEditorWidget {background: white;}')
        if alignment == Qt.Horizontal:
            hbox(self, 2, 1)
        else:
            vbox(self, 2, 1)
        self._labels_index = {}
        self.clear()

        self.btnEdit = QToolButton(self)
        self.btnEdit.setIcon(IconRegistry.plus_edit_icon())

        self._model = self._initModel()
        self._model.item_edited.connect(self._selectionChanged)
        if self.checkable:
            self._model.setCheckable(True, SelectionItemsModel.ColName)
        self._popup = self._initPopupWidget()
        self._model.selection_changed.connect(self._selectionChanged)

        btn_popup(self.btnEdit, self._popup)
        self.layout().addWidget(self.btnEdit, alignment=Qt.AlignTop)

        self._wdgLabels = LabelsWidget()
        self._wdgLabels.setStyleSheet('LabelsWidget {border: 1px solid black;}')
        self._wdgLabels.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
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
