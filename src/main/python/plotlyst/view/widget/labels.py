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
from abc import abstractmethod
from typing import Union, List, Iterable, Set

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QMouseEvent
from PyQt6.QtWidgets import QWidget, QLabel, QFrame, QToolButton, QSizePolicy, QPushButton
from overrides import overrides
from qthandy import hbox, vbox, clear_layout, transparent, flow, incr_font, translucent, italic
from qthandy.filter import VisibilityToggleEventFilter, OpacityEventFilter
from qtmenu import MenuWidget

from plotlyst.common import truncate_string, RELAXED_WHITE_COLOR, RED_COLOR, PLOTLYST_SECONDARY_COLOR, \
    PLOTLYST_MAIN_COLOR
from plotlyst.core.domain import Character, SelectionItem, Novel, ScenePlotReference, \
    CharacterGoal, PlotValue, Scene, GoalReference, NovelDescriptor
from plotlyst.env import app_env
from plotlyst.model.common import SelectionItemsModel
from plotlyst.view.common import text_color_with_bg_color, tool_btn, ButtonPressResizeEventFilter
from plotlyst.view.icons import IconRegistry, avatars
from plotlyst.view.widget.display import Icon
from plotlyst.view.widget.input import RemovalButton
from plotlyst.view.widget.items_editor import ItemsEditorWidget


class Label(QFrame):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super(Label, self).__init__(parent)
        hbox(self, 0, 2)

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.clicked.emit()


class LabelsWidget(QFrame):

    def __init__(self, parent=None):
        super(LabelsWidget, self).__init__(parent)
        flow(self)

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
        transparent(self.btnAvatar)
        self.btnAvatar.setIcon(QIcon(avatars.avatar(self.character)))
        self.btnAvatar.setIconSize(QSize(24, 24))
        self.btnAvatar.clicked.connect(self.clicked.emit)
        self.layout().addWidget(self.btnAvatar)
        self.layout().addWidget(QLabel(truncate_string(character.displayed_name())))

        # role = self.character.role
        # if role:
        #     if not self.character.prefs.avatar.use_role:
        #         self.lblRole = QLabel()
        #         self.lblRole.setPixmap(IconRegistry.from_name(role.icon, role.icon_color).pixmap(QSize(24, 24)))
        #         self.layout().addWidget(vline())
        #         self.layout().addWidget(self.lblRole)
        #     border_color = role.icon_color
        # else:
        #     border_color = PLOTLYST_TERTIARY_COLOR

        # self.setStyleSheet(f'''
        # CharacterLabel {{
        #     border: 2px solid {border_color};
        #     border-radius: 8px; padding-left: 3px; padding-right: 3px;}}
        # ''')


class CharacterAvatarLabel(QToolButton):
    def __init__(self, character: Character, size: int = 24, parent=None):
        super(CharacterAvatarLabel, self).__init__(parent)
        transparent(self)
        self.setIcon(avatars.avatar(character))
        self.setToolTip(character.name)
        self.setIconSize(QSize(size, size))


class TraitLabel(QLabel):
    def __init__(self, trait: str, positive: bool = True, parent=None):
        super(TraitLabel, self).__init__(parent)

        self.setText(trait)
        if app_env.is_mac():
            incr_font(self)

        if positive:
            bg_color = '#519872'
            border_color = '#034732'
        else:
            bg_color = RED_COLOR
            border_color = '#ef2917'
        self.setStyleSheet(f'''TraitLabel {{
            background-color: {bg_color};
            border: 1px solid {border_color};
            border-radius: 8px;
            padding: 2px;
            color: white;
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

        self.lblText = QLabel()
        self.layout().addWidget(self.lblText)
        self.btnRemoval = RemovalButton(self)
        self.layout().addWidget(self.btnRemoval)
        self.btnRemoval.clicked.connect(self.removalRequested.emit)
        self.btnRemoval.setVisible(removalEnabled)
        if removalEnabled:
            self.installEventFilter(VisibilityToggleEventFilter(self.btnRemoval, self))

        self._initLabel()

    def _initLabel(self):
        if self.item.icon:
            self.btnIcon.setIcon(IconRegistry.from_name(self.item.icon, self.item.icon_color))
        else:
            self.btnIcon.setHidden(True)
        self.lblText.setText(self.item.text)
        self._initStyle()

    def _initStyle(self):
        if self.item.color_hexa:
            bg_color = self.item.color_hexa
            text_color = text_color_with_bg_color(bg_color)
        else:
            bg_color = RELAXED_WHITE_COLOR
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
                                SelectionItemLabel:disabled {{
                                    border: 2px solid lightgrey;
                                }}
                                ''')

    def _borderColor(self) -> str:
        if not self.item.color_hexa and self.item.icon:
            return self.item.icon_color
        return '#2e5266'


class PlotValueLabel(SelectionItemLabel):

    def __init__(self, item: PlotValue, parent=None, removalEnabled: bool = False, simplified: bool = False):
        super(PlotValueLabel, self).__init__(item, parent, removalEnabled)
        self.value = item
        self._simplified = simplified

        if not simplified:
            self._versusIcon = QToolButton(self)
            transparent(self._versusIcon)
            self._versusIcon.setIcon(IconRegistry.from_name('fa5s.arrows-alt-h'))
            self.layout().insertWidget(2, self._versusIcon)
            self.lblNegative = QLabel()
            self.layout().insertWidget(3, self.lblNegative)

        self.refresh()

    def refresh(self):
        self._initLabel()
        if not self._simplified:
            self.lblNegative.setText(self.value.negative)
            self.lblNegative.setVisible(True if self.value.negative else False)
            self._versusIcon.setVisible(True if self.value.negative else False)

    @overrides
    def _borderColor(self):
        return self.item.icon_color


class ScenePlotValueLabel(SelectionItemLabel):
    def __init__(self, plot_value: ScenePlotReference, parent=None, removalEnabled: bool = True):
        super(ScenePlotValueLabel, self).__init__(plot_value.plot, parent, removalEnabled)
        self.lblText.clear()
        self.lblText.hide()
        if not self.item.icon:
            self.btnIcon.setVisible(True)
            self.btnIcon.setIcon(IconRegistry.plot_type_icon(plot_value.plot.plot_type))


class CharacterGoalLabel(SelectionItemLabel):
    def __init__(self, novel: Novel, characterGoal: CharacterGoal, goalRef: GoalReference, parent=None,
                 removalEnabled: bool = False):
        super(CharacterGoalLabel, self).__init__(characterGoal.goal(novel), parent, removalEnabled)
        self.goalRef = goalRef

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

        self.setStyleSheet('SceneLabel {border: 1px solid black; border-radius: 8px; padding: 2px;}')

    def setScene(self, scene: Scene):
        self.btnTypeIcon.setIcon(IconRegistry.scene_type_icon(scene))
        self.lblTitle.setText(scene.title_or_index(app_env.novel))


class SeriesLabel(QPushButton):
    def __init__(self, parent=None, transparent: bool = False):
        super().__init__(parent)
        border_type = 'hidden' if transparent else 'solid'
        self.setStyleSheet(f'''SeriesLabel {{
                    border: 1px {border_type} {PLOTLYST_MAIN_COLOR};
                    border-radius: 14px;
                    padding-left: 8px;
                    padding-right: 8px;
                    padding-top: 4px;
                    padding-bottom: 4px;
                    color: {PLOTLYST_MAIN_COLOR};
                }}''')
        translucent(self, 0.7)
        italic(self)
        self.installEventFilter(ButtonPressResizeEventFilter(self))

    def setSeries(self, series: NovelDescriptor):
        self.setText(series.title)
        if series.icon:
            self.setIcon(IconRegistry.from_name(series.icon, PLOTLYST_SECONDARY_COLOR))
        else:
            self.setIcon(IconRegistry.series_icon(PLOTLYST_SECONDARY_COLOR))


class EmotionLabel(Label):
    def __init__(self, parent=None):
        super(EmotionLabel, self).__init__(parent)
        self.lblTitle = QLabel(self)
        self.layout().addWidget(self.lblTitle)

    def setEmotion(self, emotion: str, color: str):
        self.lblTitle.setText(emotion)
        self.setStyleSheet(f'''
                        EmotionLabel {{
                            border: 2px solid {color};
                            border-radius: 12px;
                            padding-left: 3px; padding-right: 3px;
                            background-color: {RELAXED_WHITE_COLOR};
                            }}
                        QLabel {{
                            color: {color};
                        }}
                        ''')


class LabelsEditorWidget(QFrame):
    def __init__(self, alignment=Qt.Orientation.Horizontal, checkable: bool = True, parent=None):
        super(LabelsEditorWidget, self).__init__(parent)
        self._frozen: bool = False

        self.checkable = checkable
        self.setLineWidth(1)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setProperty('white-bg', True)
        self.setProperty('rounded', True)
        if alignment == Qt.Orientation.Horizontal:
            hbox(self, 5, 3)
        else:
            vbox(self, 5, 3)
        self._labels_index = {}
        self.clear()

        self.btnEdit = tool_btn(IconRegistry.plus_edit_icon(), transparent_=True)
        self.btnEdit.installEventFilter(OpacityEventFilter(self.btnEdit, leaveOpacity=0.8))

        self._model = self._initModel()
        self._model.item_edited.connect(self._selectionChanged)
        if self.checkable:
            self._model.setCheckable(True, SelectionItemsModel.ColName)
        self._popup = self._initPopupWidget()
        self._model.selection_changed.connect(self._selectionChanged)

        menu = MenuWidget(self.btnEdit)
        menu.addWidget(self._popup)
        self.layout().addWidget(self.btnEdit, alignment=Qt.AlignmentFlag.AlignTop)

        self._wdgLabels = LabelsWidget()
        self._wdgLabels.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.layout().addWidget(self._wdgLabels)

    def clear(self):
        self._labels_index.clear()
        for item in self.items():
            self._labels_index[item.text] = item

    def popupEditor(self) -> QWidget:
        return self._popup

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
        self._frozen = True
        for v in values:
            item = self._labels_index.get(v)
            if item:
                self._model.checkItem(item)
        self._model.modelReset.emit()
        self._frozen = False
        self._selectionChanged()

    def _initPopupWidget(self) -> QWidget:
        wdg = ItemsEditorWidget()
        wdg.setModel(self._model)
        wdg.setInlineEditionEnabled(False)
        wdg.setAdditionEnabled(False)
        wdg.setRemoveEnabled(False)
        wdg.setIconEditionEnabled(False)
        wdg.toolbar.setHidden(True)
        return wdg

    def _selectionChanged(self):
        if self._frozen:
            return
        self._wdgLabels.clear()
        self._addItems(self._model.selections())

    def _addItems(self, items: Iterable[SelectionItem]):
        for item in items:
            self._wdgLabels.addLabel(SelectionItemLabel(item))
