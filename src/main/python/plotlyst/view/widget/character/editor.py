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
import copy
import random
from abc import abstractmethod
from enum import Enum, auto
from functools import partial
from typing import Tuple, Optional, Dict, List

import emoji
import qtanim
from PyQt6.QtCharts import QPieSeries, QPieSlice
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QRectF
from PyQt6.QtGui import QIcon, QColor, QMouseEvent, QKeySequence
from PyQt6.QtWidgets import QWidget, QSlider, QTextBrowser, QButtonGroup, QToolButton, QLineEdit, QDialog, QFrame
from overrides import overrides
from qthandy import vbox, pointy, hbox, sp, vspacer, underline, decr_font, flow, clear_layout, translucent, line, grid, \
    spacer, incr_font, margins, incr_icon, decr_icon
from qthandy.filter import OpacityEventFilter, DisabledClickEventFilter
from qtmenu import MenuWidget

from plotlyst.common import PLOTLYST_MAIN_COLOR, CHARACTER_MAJOR_COLOR, \
    CHARACTER_SECONDARY_COLOR, RELAXED_WHITE_COLOR, PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import BackstoryEvent, Character, StrengthWeaknessAttribute
from plotlyst.core.help import enneagram_help, mbti_help, character_roles_description, \
    character_role_examples, work_style_help, love_style_help
from plotlyst.core.template import SelectionItem, enneagram_field, TemplateField, mbti_field, \
    promote_role, demote_role, Role, protagonist_role, antagonist_role, major_role, secondary_role, tertiary_role, \
    love_interest_role, supporter_role, adversary_role, contagonist_role, guide_role, confidant_role, sidekick_role, \
    foil_role, henchmen_role, love_style_field, disc_field
from plotlyst.env import app_env
from plotlyst.view.common import push_btn, action, tool_btn, label, wrap, restyle, \
    scroll_area, emoji_font, frame
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.widget.button import SecondaryActionPushButton, SelectionItemPushButton
from plotlyst.view.widget.chart import BaseChart, SelectionItemPieSlice
from plotlyst.view.widget.confirm import asked
from plotlyst.view.widget.display import Icon, MajorRoleIcon, SecondaryRoleIcon, MinorRoleIcon, \
    IconText, RoleIcon, TruitySourceWidget, PopupDialog, ChartView
from plotlyst.view.widget.input import Toggle, DecoratedSpinBox
from plotlyst.view.widget.labels import TraitLabel
from plotlyst.view.widget.timeline import TimelineLinearWidget, BackstoryCard, TimelineTheme
from plotlyst.view.widget.utility import IconSelectorDialog


class LifeStage(Enum):
    Infancy = auto()
    Preschool = auto()
    Early_childhood = auto()
    Children = auto()
    Teenagers = auto()
    Early_adulthood = auto()
    Middle_adulthood = auto()
    Late_adulthood = auto()
    Senior = auto()

    def display_name(self) -> str:
        return self.name.replace('_', ' ')

    def range(self) -> Tuple[int, int]:
        if self == LifeStage.Infancy:
            return 0, 2
        elif self == LifeStage.Preschool:
            return 3, 5
        elif self == LifeStage.Early_childhood:
            return 6, 7
        elif self == LifeStage.Children:
            return 8, 12
        elif self == LifeStage.Teenagers:
            return 13, 19
        elif self == LifeStage.Early_adulthood:
            return 20, 30
        elif self == LifeStage.Middle_adulthood:
            return 31, 65
        elif self == LifeStage.Late_adulthood:
            return 65, 79
        elif self == LifeStage.Senior:
            return 80, 100

    def icon(self) -> str:
        if self == LifeStage.Infancy:
            return 'fa5s.baby'
        elif self == LifeStage.Preschool:
            return 'fa5s.child'
        elif self == LifeStage.Early_childhood:
            return 'fa5s.child'
        elif self == LifeStage.Children:
            return 'fa5s.child'
        elif self == LifeStage.Teenagers:
            return 'mdi.human'
        elif self == LifeStage.Early_adulthood:
            return 'ei.adult'
        elif self == LifeStage.Middle_adulthood:
            return 'ei.adult'
        elif self == LifeStage.Late_adulthood:
            return 'ei.adult'
        elif self == LifeStage.Senior:
            return 'mdi.human-cane'

    def description(self) -> str:
        if self == LifeStage.Infancy:
            return "Early bonding, motor and language development, sensory exploration."
        elif self == LifeStage.Preschool:
            return "Social and cognitive growth, school readiness, creative play."
        elif self == LifeStage.Early_childhood:
            return "Transition into formal schooling, moral and ethical development, continued play and creativity"
        elif self == LifeStage.Children:
            return "Development of competitiveness, skill building, and motivation"
        elif self == LifeStage.Teenagers:
            return "Exploration of identity, self-discovery, and peer relationships"
        elif self == LifeStage.Early_adulthood:
            return "Career and life planning, independence, and personal growth."
        elif self == LifeStage.Middle_adulthood:
            return "Coping with life transitions, self-reflection, and reassessment of goals"
        elif self == LifeStage.Late_adulthood:
            return "Retirement transition, legacy considerations, and life reflection."
        elif self == LifeStage.Senior:
            return "Health management, end-of-life planning, and legacy concerns."


class CharacterAgeEditor(QFrame):
    valueChanged = pyqtSignal(int)
    infiniteToggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self, 10, 10)
        self.setProperty('relaxed-white-bg', True)
        self.setProperty('large-rounded', True)

        self._btnInfinite = push_btn(IconRegistry.from_name('mdi.infinity', 'grey', PLOTLYST_MAIN_COLOR),
                                     'Infinite',
                                     checkable=True, transparent_=True,
                                     tooltip='Immortal or any character with an extraordinary lifespan')
        self._btnInfinite.installEventFilter(
            OpacityEventFilter(self._btnInfinite, leaveOpacity=0.7, ignoreCheckedButton=True))
        self._btnInfinite.toggled.connect(self._infiniteToggled)

        self._spinbox = DecoratedSpinBox(self)
        self._spinbox.setPrefix('Age: ')
        self._spinbox.setMinimum(0)
        self._spinbox.setMaximum(65000)
        self._spinbox.setValue(0)
        incr_font(self._spinbox.spinBox, 6)

        self._btnStage = push_btn(text='Life stage', transparent_=True)
        self._menuStages = MenuWidget(self._btnStage)
        self._menuStages.addSection('Select a stage to generate an age')
        self._menuStages.addSeparator()
        self._addAction(LifeStage.Infancy)
        self._addAction(LifeStage.Preschool)
        self._addAction(LifeStage.Early_childhood)
        self._addAction(LifeStage.Children)
        self._addAction(LifeStage.Teenagers)
        self._addAction(LifeStage.Early_adulthood)
        self._addAction(LifeStage.Middle_adulthood)
        self._addAction(LifeStage.Late_adulthood)
        self._addAction(LifeStage.Senior)

        self._text = QTextBrowser()
        self._text.setMaximumSize(200, 150)
        self._text.setProperty('transparent', True)

        self._spinbox.valueChanged.connect(self._spinboxValueChanged)

        self.frameHint = frame()
        vbox(self.frameHint, 4)
        self.frameHint.setProperty('muted-bg', True)
        self.frameHint.setProperty('large-rounded', True)
        self.frameHint.layout().addWidget(self._btnStage, alignment=Qt.AlignmentFlag.AlignCenter)
        self.frameHint.layout().addWidget(self._text)

        self.layout().addWidget(self._btnInfinite, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(self._spinbox, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.frameHint)

    def value(self) -> int:
        return self._spinbox.value()

    def setValue(self, age: int):
        self._spinbox.setValue(age)

    def setInfinite(self, infinite: bool):
        self._btnInfinite.setChecked(infinite)

    @overrides
    def setFocus(self):
        self._spinbox.setFocus()

    def reset(self):
        self._spinbox.setValue(self._spinbox.minimum())
        self._btnInfinite.setChecked(False)
        self._btnStage.setText('Life stage')
        self._btnStage.setIcon(QIcon())
        self._text.clear()

    def minimum(self) -> int:
        return self._spinbox.minimum()

    def _addAction(self, stage: LifeStage):
        self._menuStages.addAction(action(stage.display_name(), slot=partial(self._stageClicked, stage)))

    def _stageClicked(self, stage: LifeStage):
        if self._btnInfinite.isChecked():
            self._btnInfinite.setChecked(False)
            self.infiniteToggled.emit(False)

        range = stage.range()
        age = random.randint(range[0], range[1])
        self._spinbox.setValue(age)

    def _spinboxValueChanged(self, value: int):
        self._setStageFromAge(value)
        self.valueChanged.emit(value)

    def _infiniteToggled(self, toggled: bool):
        self._spinbox.setDisabled(toggled)

        if toggled:
            self._btnStage.setText('Infinite')
            self._btnStage.setIcon(IconRegistry.from_name('mdi.infinity'))
            self._text.setText(self._btnInfinite.toolTip())
        else:
            self._btnStage.setText('Life stage')
            self._btnStage.setIcon(QIcon())
            self._text.clear()

            self._setStageFromAge(self._spinbox.value())

        self.infiniteToggled.emit(toggled)

    def _setStageFromAge(self, age: int):
        if age > 100:
            self._setStage(LifeStage.Senior)
            return

        for stage in LifeStage:
            range = stage.range()
            if range[0] <= age <= range[1]:
                self._setStage(stage)
                break

    def _setStage(self, stage: LifeStage):
        self._btnStage.setText(stage.display_name())
        self._btnStage.setIcon(IconRegistry.from_name(stage.icon()))
        self._text.setText(stage.description())


class PersonalitySelectorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected: Optional[SelectionItem] = None

        self.btnIgnore = push_btn(IconRegistry.from_name('ri.share-forward-fill'), 'Ignore', transparent_=True)
        underline(self.btnIgnore)
        decr_font(self.btnIgnore)
        self.btnIgnore.installEventFilter(OpacityEventFilter(self.btnIgnore))

        vbox(self)
        self.layout().addWidget(self.btnIgnore, alignment=Qt.AlignmentFlag.AlignRight)

    def value(self) -> SelectionItem:
        return self._selected

    def setValue(self, value: SelectionItem):
        pass

    def reset(self):
        pass


class EnneagramSelectorWidget(PersonalitySelectorWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.wdgSelector = QWidget()
        hbox(self.wdgSelector, 10, spacing=6)
        self.layout().addWidget(self.wdgSelector)
        self._buttons: Dict[str, QToolButton] = {}
        self.btnGroup = QButtonGroup()

        for item in enneagram_field.selections:
            self._addItem(item)

        self.layout().addWidget(line(color='lightgrey'))

        self.title = label('', h4=True)
        self.layout().addWidget(self.title, alignment=Qt.AlignmentFlag.AlignCenter)

        self.text = QTextBrowser()
        self.text.setProperty('transparent', True)
        self.layout().addWidget(wrap(self.text, margin_left=10, margin_right=10))

        self.wdgLabels = QWidget()
        flow(self.wdgLabels)
        self.layout().addWidget(wrap(self.wdgLabels, margin_left=10, margin_right=10, margin_bottom=10))

        self.btnSelect = push_btn(IconRegistry.ok_icon('white'), 'Select enneagram', properties=['positive', 'base'])
        self.layout().addWidget(self.btnSelect, alignment=Qt.AlignmentFlag.AlignRight)

        self.reset()

    @overrides
    def setValue(self, value: SelectionItem):
        self._selected = value
        self._buttons[value.text].setChecked(True)

    @overrides
    def reset(self):
        self.btnGroup.buttons()[0].setChecked(True)

    def _addItem(self, item: SelectionItem):
        btn = tool_btn(IconRegistry.from_name(item.icon, 'lightgrey', item.icon_color), checkable=True,
                       transparent_=True)
        btn.setShortcut(QKeySequence(str(item.meta.get('number', 1))))
        btn.setIconSize(QSize(32, 32))
        btn.installEventFilter(OpacityEventFilter(btn, leaveOpacity=0.5, ignoreCheckedButton=True))
        btn.toggled.connect(partial(self._toggled, item))
        self.btnGroup.addButton(btn)
        self._buttons[item.text] = btn
        self.wdgSelector.layout().addWidget(btn)

    def _toggled(self, item: SelectionItem, checked: bool):
        if not checked:
            return

        self._selected = item
        self.title.setText(item.text)
        self.text.setText(enneagram_help.get(item.text, ''))
        clear_layout(self.wdgLabels)
        if 'positive' in item.meta.keys():
            for trait in item.meta['positive']:
                label = TraitLabel(trait)
                translucent(label, 0.8)
                decr_font(label)
                self.wdgLabels.layout().addWidget(label)
        if 'negative' in item.meta.keys():
            for trait in item.meta['negative']:
                label = TraitLabel(trait, positive=False)
                translucent(label, 0.8)
                decr_font(label)
                self.wdgLabels.layout().addWidget(label)


class MbtiSelectorWidget(PersonalitySelectorWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.wdgSelector = QWidget()
        grid(self.wdgSelector)
        self.layout().addWidget(self.wdgSelector)

        self._buttons: Dict[str, QToolButton] = {}
        self.btnGroup = QButtonGroup()

        for i, item in enumerate(mbti_field.selections):
            self._addItem(item, i)

        self.text = QTextBrowser()
        self.text.setProperty('transparent', True)
        self.layout().addWidget(wrap(self.text, margin_left=10, margin_right=10))

        self.btnSelect = push_btn(IconRegistry.ok_icon('white'), 'Select MBTI', properties=['positive', 'base'])

        self.wdgBottom = QWidget()
        hbox(self.wdgBottom)
        ref = TruitySourceWidget()
        self.wdgBottom.layout().addWidget(ref, alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgBottom.layout().addWidget(self.btnSelect, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(self.wdgBottom)

        self.reset()

    @overrides
    def setValue(self, value: SelectionItem):
        self._selected = value
        self._buttons[value.text].setChecked(True)

    @overrides
    def reset(self):
        self.btnGroup.buttons()[0].setChecked(True)

    def _addItem(self, item: SelectionItem, index: int):
        btn = tool_btn(IconRegistry.from_name(item.icon, 'grey', item.icon_color), transparent_=True, checkable=True)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        if app_env.is_mac():
            incr_font(btn)
        btn.setText(item.text)
        btn.setIconSize(QSize(32, 32))
        btn.installEventFilter(OpacityEventFilter(btn, leaveOpacity=0.5, ignoreCheckedButton=True))
        btn.toggled.connect(partial(self._toggled, item))
        self.btnGroup.addButton(btn)
        self._buttons[item.text] = btn

        cluster = index // 4
        row = index % 2
        col = index % 4 // 2
        self.wdgSelector.layout().addWidget(btn, row, col + cluster * 2)

    def _toggled(self, item: SelectionItem, checked: bool):
        if not checked:
            return

        self._selected = item
        self.text.setText(mbti_help.get(item.text, ''))


love_style_opaque_colors = {
    'Activity': '#B7B2D2',
    'Appreciation': '#EBA9AE',
    'Emotional': '#FFA4C2',
    'Financial': '#FFBA6A',
    'Intellectual': '#8AD6FF',
    'Physical': '#FAD1B0',
    'Practical': '#84DED4',
}

work_style_opaque_colors = {
    'Drive': '#F39BA2',
    'Influence': '#9BBB9A',
    'Clarity': '#F1D99E',
    'Support': '#60C9E3',
}


class LoveStylePie(BaseChart):
    sliceClicked = pyqtSignal(SelectionItem, bool)
    sliceHovered = pyqtSignal(SelectionItem, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selectedSlice: Optional[SelectionItemPieSlice] = None
        self.series = QPieSeries()
        self.setTitle("Select your character's preferred love style")

        for i, item in enumerate(love_style_field.selections):
            slice = SelectionItemPieSlice(item, love_style_opaque_colors[item.text])
            slice.setValue(1)
            self.series.append(slice)

        self.series.hovered.connect(partial(self._hovered))
        self.series.clicked.connect(partial(self._clicked))
        self.addSeries(self.series)

        self.setPlotArea(QRectF(0, 0, 450, 450))

    def _hovered(self, slice: SelectionItemPieSlice, state: bool):
        if slice is self._selectedSlice:
            return
        if state:
            slice.highlight()
        else:
            slice.reset()

        self.sliceHovered.emit(slice.item, state)

    def _clicked(self, slice: SelectionItemPieSlice):
        if self._selectedSlice:
            self._selectedSlice.reset()
            if self._selectedSlice is slice:
                self._selectedSlice = None
                self.sliceClicked.emit(slice.item, False)
                return

        self._selectedSlice = slice
        self._selectedSlice.select()
        self.sliceClicked.emit(slice.item, True)


class WorkStylePie(BaseChart):
    sliceClicked = pyqtSignal(SelectionItem, bool)
    sliceHovered = pyqtSignal(SelectionItem, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selectedSlice: Optional[SelectionItemPieSlice] = None
        self.setTitle("Select your character's dominant working style")
        self.series = QPieSeries()

        for i, item in enumerate(disc_field.selections):
            slice = SelectionItemPieSlice(item, work_style_opaque_colors[item.text],
                                          labelPosition=QPieSlice.LabelPosition.LabelInsideHorizontal)
            slice.setValue(1)
            self.series.append(slice)

        self.series.hovered.connect(partial(self._hovered))
        self.series.clicked.connect(partial(self._clicked))
        self.addSeries(self.series)

        self.setPlotArea(QRectF(0, 0, 450, 450))

    def _hovered(self, slice: SelectionItemPieSlice, state: bool):
        if slice is self._selectedSlice:
            return
        if state:
            slice.highlight()
        else:
            slice.reset()

        self.sliceHovered.emit(slice.item, state)

    def _clicked(self, slice: SelectionItemPieSlice):
        if self._selectedSlice:
            self._selectedSlice.reset()
            if self._selectedSlice is slice:
                self._selectedSlice = None
                self.sliceClicked.emit(slice.item, False)
                return

        self._selectedSlice = slice
        self._selectedSlice.select()
        self.sliceClicked.emit(slice.item, True)


class LoveStyleSelectorWidget(PersonalitySelectorWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pieView = ChartView()
        self.pie = LoveStylePie()
        self.pie.sliceClicked.connect(self._itemClicked)
        self.pie.sliceHovered.connect(self._itemHovered)
        self.pieView.setChart(self.pie)
        self.pieView.setMaximumSize(450, 450)
        self.layout().addWidget(self.pieView)

        self.btnSelect = push_btn(IconRegistry.ok_icon('white'), 'Select Love Style', properties=['positive', 'base'])
        self.btnSelect.setDisabled(True)
        self.btnSelect.installEventFilter(DisabledClickEventFilter(self.btnSelect, lambda: qtanim.shake(self.pieView)))

        self.lblHelp = label('', wordWrap=True)
        self.lblHelp.setMinimumHeight(80)
        self.layout().addWidget(wrap(self.lblHelp, margin_left=10, margin_right=10, margin_bottom=25))

        self.wdgBottom = QWidget()
        hbox(self.wdgBottom)
        ref = TruitySourceWidget()
        self.wdgBottom.layout().addWidget(ref, alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgBottom.layout().addWidget(self.btnSelect, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(self.wdgBottom)

    def _itemClicked(self, item: SelectionItem, checked: bool):
        self.btnSelect.setEnabled(checked)
        if checked:
            self._selected = item
        else:
            self._selected = None

    def _itemHovered(self, item: SelectionItem, hovered: bool):
        if hovered:
            self.lblHelp.setText(love_style_help[item.text])
        else:
            if self._selected:
                self.lblHelp.setText(love_style_help[self._selected.text])
            else:
                self.lblHelp.clear()


class WorkStyleSelectorWidget(PersonalitySelectorWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pieView = ChartView()
        self.pie = WorkStylePie()
        self.pie.sliceClicked.connect(self._itemClicked)
        self.pie.sliceHovered.connect(self._itemHovered)
        self.pieView.setChart(self.pie)
        self.pieView.setMaximumSize(450, 450)
        self.layout().addWidget(self.pieView)

        self.btnSelect = push_btn(IconRegistry.ok_icon('white'), 'Select Work Style', properties=['positive', 'base'])
        self.btnSelect.setDisabled(True)
        self.btnSelect.installEventFilter(DisabledClickEventFilter(self.btnSelect, lambda: qtanim.shake(self.pieView)))

        self.lblHelp = label('', wordWrap=True)
        self.lblHelp.setMinimumHeight(80)
        self.layout().addWidget(wrap(self.lblHelp, margin_left=10, margin_right=10, margin_bottom=25))

        self.wdgBottom = QWidget()
        hbox(self.wdgBottom)
        ref = TruitySourceWidget()
        self.wdgBottom.layout().addWidget(ref, alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgBottom.layout().addWidget(self.btnSelect, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(self.wdgBottom)

    def _itemClicked(self, item: SelectionItem, checked: bool):
        self.btnSelect.setEnabled(checked)
        if checked:
            self._selected = item
        else:
            self._selected = None

    def _itemHovered(self, item: SelectionItem, hovered: bool):
        if hovered:
            self.lblHelp.setText(work_style_help[item.text])
        else:
            if self._selected:
                self.lblHelp.setText(work_style_help[self._selected.text])
            else:
                self.lblHelp.clear()


class PersonalitySelector(SecondaryActionPushButton):
    selected = pyqtSignal(SelectionItem)
    ignored = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ignored = False
        self._padding = 5

        self._selected: Optional[SelectionItem] = None
        self._selector: Optional[PersonalitySelectorWidget] = None
        self._items: Dict[str, SelectionItem] = {}
        for item in self.field().selections:
            self._items[item.text] = item

        incr_font(self, 2)

        self._menu = MenuWidget(self)
        self._menu.aboutToShow.connect(self._selectorShown)
        apply_white_menu(self._menu)

    def value(self) -> Optional[str]:
        if self._ignored:
            return None
        return self._selected.text if self._selected else ''

    def setValue(self, value: str):
        self._selected = self._items.get(value)
        if self._selected:
            self._updateValue()
        else:
            self.setText(f'{self.field().name}...')
            self.setIcon(IconRegistry.empty_icon())

        self._ignored = False
        if value is None:
            self._updateIgnoredValue()

    @abstractmethod
    def field(self) -> TemplateField:
        pass

    @abstractmethod
    def _initSelector(self):
        pass

    def _selectorShown(self):
        if self._selector is None:
            self._initSelector()
            self._menu.addWidget(self._selector)

        if self._selected:
            self._selector.setValue(self._selected)
        else:
            self._selector.reset()

    def _updateValue(self):
        self.setText(self._selected.text)
        self.setIconSize(QSize(32, 32))
        self.setIcon(IconRegistry.from_name(self._selected.icon, self._selected.icon_color))
        self.initStyleSheet(self._selected.icon_color, 'solid', self._selected.icon_color, RELAXED_WHITE_COLOR)

    def _updateIgnoredValue(self):
        self._ignored = True
        self.setIconSize(QSize(20, 20))
        self.setIcon(IconRegistry.from_name('ei.remove-circle', 'grey'))
        self.initStyleSheet()

    def _ignoreClicked(self):
        self._menu.close()
        if asked(
                "The personality type won't be considered for this character. You can enable it back anytime.",
                f'Ignore personality type "{self.field().name}" for this character?'):
            self._updateIgnoredValue()
            self.ignored.emit()

    def _selectionClicked(self):
        self._ignored = False
        self._menu.close()
        value = self._selector.value()
        self._selected = value
        self._updateValue()
        self.selected.emit(value)


class EnneagramSelector(PersonalitySelector):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText('Enneagram...')
        self.setIcon(IconRegistry.from_name('mdi.numeric-9-circle', 'grey'))

    @overrides
    def field(self) -> TemplateField:
        return enneagram_field

    @overrides
    def _initSelector(self):
        self._selector = EnneagramSelectorWidget(self)
        self._selector.btnIgnore.clicked.connect(self._ignoreClicked)
        self._selector.btnIgnore.setToolTip('Ignore Enneagram personality type for this character')
        self._selector.btnSelect.clicked.connect(self._selectionClicked)


class MbtiSelector(PersonalitySelector):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText('MBTI...')
        self.setIcon(IconRegistry.from_name('mdi.head-question-outline', 'grey'))

    @overrides
    def field(self) -> TemplateField:
        return mbti_field

    @overrides
    def _initSelector(self):
        self._selector = MbtiSelectorWidget(self)
        self._selector.btnIgnore.clicked.connect(self._ignoreClicked)
        self._selector.btnIgnore.setToolTip('Ignore MBTI personality type for this character')
        self._selector.btnSelect.clicked.connect(self._selectionClicked)


class LoveStyleSelector(PersonalitySelector):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText('Love style...')
        self.setIcon(IconRegistry.from_name('fa5s.heart', 'grey'))

    @overrides
    def field(self) -> TemplateField:
        return love_style_field

    @overrides
    def _initSelector(self):
        self._selector = LoveStyleSelectorWidget(self)
        self._selector.btnIgnore.clicked.connect(self._ignoreClicked)
        self._selector.btnIgnore.setToolTip('Ignore love style for this character')
        self._selector.btnSelect.clicked.connect(self._selectionClicked)


class DiscSelector(PersonalitySelector):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText('Work style...')
        self.setIcon(IconRegistry.from_name('fa5s.briefcase', 'grey'))

    @overrides
    def field(self) -> TemplateField:
        return disc_field

    @overrides
    def _initSelector(self):
        self._selector = WorkStyleSelectorWidget(self)
        self._selector.btnIgnore.clicked.connect(self._ignoreClicked)
        self._selector.btnIgnore.setToolTip('Ignore work style for this character')
        self._selector.btnSelect.clicked.connect(self._selectionClicked)


class EmotionEditorSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(parent)

        pointy(self)
        self.setMinimum(1)
        self.setMaximum(9)
        self.setPageStep(1)
        self.setMaximumWidth(100)
        self.setValue(5)
        self.setOrientation(Qt.Orientation.Horizontal)
        self.valueChanged.connect(self._valueChanged)

    def _valueChanged(self, value: int):
        for v in range(0, 11):
            self.setProperty(f'emotion_{v}', False)

        self.setProperty(f'emotion_{value}', True)
        restyle(self)


class BackstoryEditorMenu(MenuWidget):
    emotionChanged = pyqtSignal(int)
    iconSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        wdgEmotion = QWidget()
        vbox(wdgEmotion, 1, 1)
        self._iconEmotion = Icon()
        self._iconEmotion.setIconSize(QSize(32, 32))
        self._iconEmotion.setIcon(IconRegistry.emotion_icon_from_feeling(5))
        self.emotionSlider = EmotionEditorSlider()
        self.emotionSlider.setMaximumWidth(200)
        self.emotionSlider.valueChanged.connect(self._emotionChanged)
        sp(self.emotionSlider).h_exp()
        wdgEmotion.layout().addWidget(self._iconEmotion, alignment=Qt.AlignmentFlag.AlignCenter)
        wdgEmotion.layout().addWidget(self.emotionSlider)
        self.wdgIcons = QWidget()
        self.wdgIcons.setMaximumHeight(200)
        flow(self.wdgIcons)
        self._addIcon('ri.calendar-event-fill')
        self._addIcon('fa5s.birthday-cake')
        self._addIcon('fa5s.graduation-cap')
        self._addIcon('fa5s.briefcase')
        self._addIcon('ei.heart')
        self._addIcon('fa5s.user-friends')
        self._addIcon('fa5s.skull-crossbones')
        self._addIcon('mdi.knife-military')
        self._addIcon('fa5s.car-crash')
        self._addIcon('mdi.ladder')
        self._addIcon('fa5s.heart-broken')
        self._addIcon('fa5s.award')
        self._addIcon('mdi6.human-male-female-child')
        self._addIcon('fa5s.home')
        self._addIcon('fa5s.gavel')
        self._addIcon('fa5s.gift')
        self._addIcon('fa5s.medkit')
        self._addIcon('ph.coin-fill')
        self._addIcon('fa5s.user-injured')
        self._addIcon('mdi.trophy-broken')

        self.addWidget(wdgEmotion)
        self.addWidget(self.wdgIcons)
        self.addSeparator()
        self.addAction(action('Custom icon...', IconRegistry.icons_icon(), slot=self._customIconTriggered))

        self._freeze = False

    def setEmotion(self, value: int):
        self._freeze = True
        self.emotionSlider.setValue(value)
        self._freeze = False

    def _addIcon(self, icon: str):
        def select():
            self.iconSelected.emit(icon)
            self.close()

        btn = tool_btn(IconRegistry.from_name(icon), transparent_=True)
        btn.clicked.connect(select)
        incr_icon(btn, 4)
        self.wdgIcons.layout().addWidget(btn)

    def _emotionChanged(self, value: int):
        self._iconEmotion.setIcon(IconRegistry.emotion_icon_from_feeling(value))
        if not self._freeze:
            self.emotionChanged.emit(value)

    def _customIconTriggered(self):
        result = IconSelectorDialog.popup(pickColor=False)
        if result:
            self.iconSelected.emit(result[0])


class CharacterBackstoryCard(BackstoryCard):
    def __init__(self, backstory: BackstoryEvent, theme: TimelineTheme, parent=None):
        super(CharacterBackstoryCard, self).__init__(backstory, theme, parent, iconPicker=False)
        self.btnType.clicked.connect(self._showMenu)
        self.refresh()

    def _showMenu(self):
        self.menu = BackstoryEditorMenu()
        self.menu.setEmotion(self.backstory.emotion)
        self.menu.emotionChanged.connect(self._emotionChanged)
        self.menu.iconSelected.connect(self._iconChanged)

        self.menu.exec()

    def _emotionChanged(self, value: int):
        self.backstory.emotion = value
        self._refreshStyle()
        self.edited.emit()


class CharacterTimelineWidget(TimelineLinearWidget):

    def __init__(self, parent=None):
        super(CharacterTimelineWidget, self).__init__(parent=parent)
        self.character: Optional[Character] = None
        self._endSpacerMinHeight = 200
        self.setAddButtonEnabled(PLOTLYST_SECONDARY_COLOR)

    def setCharacter(self, character: Character):
        self.character = character
        self.refresh()

    @overrides
    def events(self) -> List[BackstoryEvent]:
        return self.character.backstory

    @overrides
    def cardClass(self):
        return CharacterBackstoryCard


class CharacterRoleSelector(QFrame):
    roleSelected = pyqtSignal(SelectionItem)
    rolePromoted = pyqtSignal(SelectionItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self, 0, 0)

        self.setProperty('large-rounded', True)

        self.wdgSidebar = QWidget()
        self.wdgSidebar.setProperty('relaxed-white-bg', True)
        vbox(self.wdgSidebar)
        margins(self.wdgSidebar, left=10, top=15, right=10)
        self.wdgDisplay = QWidget()
        self.wdgDisplay.setProperty('bg', True)
        vbox(self.wdgDisplay)
        margins(self.wdgDisplay, left=20, right=20)
        self.layout().addWidget(self.wdgSidebar)
        self.layout().addWidget(self.wdgDisplay)

        self.textBrowser = QTextBrowser()
        incr_font(self.textBrowser)
        self.textBrowser.setProperty('rounded', True)
        self.textBrowser.setMinimumSize(400, 300)

        self.buttonGroup = QButtonGroup()

        self._addRoleItem(protagonist_role)
        self._addRoleItem(antagonist_role)
        self.wdgSidebar.layout().addWidget(line(color='lightgrey'))
        self._addRoleItem(major_role)
        self._addRoleItem(secondary_role)
        self._addRoleItem(tertiary_role)
        self.wdgSidebar.layout().addWidget(line(color='lightgrey'))
        self._addRoleItem(love_interest_role)
        self._addRoleItem(supporter_role)
        self._addRoleItem(adversary_role)
        self._addRoleItem(guide_role)
        self._addRoleItem(confidant_role)
        self._addRoleItem(sidekick_role)
        self.wdgSidebar.layout().addWidget(line(color='lightgrey'))
        self._addRoleItem(contagonist_role)
        self._addRoleItem(foil_role)
        self.wdgSidebar.layout().addWidget(line(color='lightgrey'))
        self._addRoleItem(henchmen_role)
        self.wdgSidebar.layout().addWidget(vspacer())

        self.iconMajor = MajorRoleIcon()
        self.iconMajor.setToolTip("The selected role is a major character role")
        self.iconMajor.setText('Major')
        self.iconSecondary = SecondaryRoleIcon()
        self.iconSecondary.setToolTip("The selected role is a secondary character role")
        self.iconSecondary.setText('Secondary')
        self.iconMinor = MinorRoleIcon()
        self.iconMinor.setToolTip("The selected role is a minor character role")
        self.iconMinor.setText('Tertiary')
        for btn in [self.iconMajor, self.iconSecondary, self.iconMinor]:
            decr_font(btn, 2)
            decr_icon(btn, 4)
            translucent(btn, 0.5)

        self.iconRole = RoleIcon()
        incr_font(self.iconRole, 2)
        self.btnPromote = SecondaryActionPushButton()
        incr_icon(self.btnPromote, 4)
        incr_font(self.btnPromote)
        self.btnPromote.setPadding(3)
        self._updatePromotionButton(False)
        self.btnPromote.clicked.connect(self._promoted)

        self._currentRole = protagonist_role
        self._currentButton: Optional[SelectionItemPushButton] = None

        self.btnSelect = push_btn(IconRegistry.ok_icon(RELAXED_WHITE_COLOR), 'Select',
                                  properties=['confirm', 'positive'])
        self.btnSelect.clicked.connect(self._select)

        self.wdgDisplayHeader = QWidget()
        hbox(self.wdgDisplayHeader)
        self.wdgDisplayHeader.layout().addWidget(spacer())
        self.wdgDisplayHeader.layout().addWidget(self.btnPromote)
        self.wdgDisplayHeader.layout().addWidget(self.iconMajor)
        self.wdgDisplayHeader.layout().addWidget(self.iconSecondary)
        self.wdgDisplayHeader.layout().addWidget(self.iconMinor)

        self.wdgExamples = frame()
        self.wdgExamples.setProperty('muted-bg', True)
        self.wdgExamples.setProperty('large-rounded', True)
        self.examplesScrollArea = scroll_area(False, False, True)
        self.examplesScrollArea.setWidget(self.wdgExamples)
        self.wdgExamples.setMinimumSize(400, 150)
        self.examplesScrollArea.setMinimumSize(400, 150)
        flow(self.wdgExamples, 8, 8)

        self.wdgDisplay.layout().addWidget(self.wdgDisplayHeader)
        self.wdgDisplay.layout().addWidget(line(color='lightgrey'))
        self.wdgDisplay.layout().addWidget(self.iconRole, alignment=Qt.AlignmentFlag.AlignCenter)
        self.wdgDisplay.layout().addWidget(self.textBrowser)
        self.wdgDisplay.layout().addWidget(label('Examples:', description=True), alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgDisplay.layout().addWidget(self.examplesScrollArea)
        self.wdgDisplay.layout().addWidget(vspacer())
        self.wdgDisplay.layout().addWidget(self.btnSelect)

        self.buttonGroup.buttons()[0].setChecked(True)

    def _addRoleItem(self, role: Role):
        copied_role = copy.deepcopy(role)
        btn = SelectionItemPushButton()
        btn.setCheckable(True)
        btn.setSelectionItem(copied_role)
        self.buttonGroup.addButton(btn)
        btn.setStyleSheet('''
                        QPushButton {
                            border: 1px hidden black;
                            padding: 2px;
                        }
                        QPushButton:hover {
                            background-color: #e9ecef;
                        }
                        QPushButton:checked {
                            background-color: #ced4da;
                        }
                    ''')
        btn.toggled.connect(partial(self._roleToggled, btn, copied_role))
        btn.itemDoubleClicked.connect(self._select)
        self.wdgSidebar.layout().addWidget(btn)

    @overrides
    def mouseReleaseEvent(self, a0: QMouseEvent) -> None:
        pass

    def setActiveRole(self, role: Role):
        for btn in self.buttonGroup.buttons():
            if btn.selectionItem().text == role.text:
                btn.setSelectionItem(role)
                btn.setChecked(True)
                self._updatePromotionButton(role.promoted)
                self._currentRole.promoted = role.promoted
                self._updateRolePriorityIcon()
                self.iconRole.setRole(role, showText=True)
                break

    def _roleToggled(self, btn: SelectionItemPushButton, role: Role, toggled: bool):
        if toggled:
            self._currentButton = btn
            self._currentRole = role
            self.iconRole.setRole(role, showText=True)
            self.textBrowser.setHtml(character_roles_description[role])
            self.btnPromote.setVisible(role.can_be_promoted)
            self.btnPromote.setChecked(role.promoted)
            self._updatePromotionButton(role.promoted)
            self._updateRolePriorityIcon()

            clear_layout(self.wdgExamples)
            for example in character_role_examples(role):
                iconText = IconText()
                if example.icon:
                    iconText.setIcon(IconRegistry.from_name(example.icon))
                text = example.name
                if example.display_title:
                    text += f' ({example.title})'
                iconText.setText(text)

                self.wdgExamples.layout().addWidget(iconText)

    def _updatePromotionButton(self, promoted: bool):
        if promoted:
            self.btnPromote.setText('Demote')
            self.btnPromote.setToolTip('Demote to a secondary character')
            self.btnPromote.setIcon(IconRegistry.from_name('mdi.chevron-double-down', CHARACTER_SECONDARY_COLOR))
            color = CHARACTER_SECONDARY_COLOR
        else:
            self.btnPromote.setText('Promote')
            self.btnPromote.setToolTip('Promote to a major character')
            self.btnPromote.setIcon(IconRegistry.from_name('mdi.chevron-double-up', CHARACTER_MAJOR_COLOR))
            color = CHARACTER_MAJOR_COLOR
        self.btnPromote.initStyleSheet(border_color=color, border_style='solid', color=color,
                                       bg_color=RELAXED_WHITE_COLOR, border_radius=12)

    def _updateRolePriorityIcon(self, anim: bool = False):
        self.iconMajor.setHidden(True)
        self.iconSecondary.setHidden(True)
        self.iconMinor.setHidden(True)

        if self._currentRole.is_major():
            self.iconMajor.setVisible(True)
            if anim:
                qtanim.glow(self.iconMajor, color=QColor(CHARACTER_MAJOR_COLOR),
                            teardown=lambda: translucent(self.iconMajor, 0.5))
        elif self._currentRole.is_secondary():
            self.iconSecondary.setVisible(True)
            if anim:
                qtanim.glow(self.iconSecondary, color=QColor(CHARACTER_SECONDARY_COLOR),
                            teardown=lambda: translucent(self.iconSecondary, 0.5))
        else:
            self.iconMinor.setVisible(True)

    def _promoted(self):
        if self._currentRole.promoted:
            demote_role(self._currentRole)
        else:
            promote_role(self._currentRole)
        self._currentRole.promoted = not self._currentRole.promoted
        self._updateRolePriorityIcon(anim=True)

        qtanim.fade_out(self.btnPromote)
        self._updatePromotionButton(self._currentRole.promoted)
        qtanim.fade_in(self.btnPromote)

        self.iconRole.setRole(self._currentRole, showText=True)
        self._currentButton.setSelectionItem(self._currentRole)
        self.rolePromoted.emit(self._currentRole)

    def _select(self):
        self.roleSelected.emit(self._currentRole)


class StrengthWeaknessEditor(PopupDialog):
    def __init__(self, attribute: Optional[StrengthWeaknessAttribute] = None, parent=None):
        super().__init__(parent)
        self.wdgTitle = QWidget()
        hbox(self.wdgTitle)
        self.wdgTitle.layout().addWidget(label('Define a new strength or weakness', h4=True),
                                         alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgTitle.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)

        self.lineKey = QLineEdit()
        self.lineKey.setProperty('white-bg', True)
        self.lineKey.setProperty('rounded', True)
        self.lineKey.setPlaceholderText('Attribute')
        self.lineKey.textChanged.connect(self._changed)

        self.toggleStrength = Toggle()
        self.toggleWeakness = Toggle()
        self.btnGroup = QButtonGroup()
        self.btnGroup.setExclusive(False)
        self.btnGroup.addButton(self.toggleStrength)
        self.btnGroup.addButton(self.toggleWeakness)
        self.toggleStrength.setChecked(True)
        self.toggleWeakness.setChecked(True)
        self.btnGroup.buttonToggled.connect(self._changed)

        self.btnConfirm = push_btn(text='Confirm', properties=['confirm', 'positive'])
        self.btnConfirm.clicked.connect(self.accept)
        self.btnConfirm.setDisabled(True)
        self.btnConfirm.installEventFilter(
            DisabledClickEventFilter(self.btnConfirm, self._disabledClick))
        self.btnCancel = push_btn(text='Cancel', properties=['confirm', 'cancel'])
        self.btnCancel.clicked.connect(self.reject)

        if attribute:
            self.lineKey.setText(attribute.name)
            self.toggleStrength.setChecked(attribute.has_strength)
            self.toggleWeakness.setChecked(attribute.has_weakness)

        self.emojiStrength = label('')
        self.emojiStrength.setFont(emoji_font())
        self.emojiStrength.setText(emoji.emojize(':flexed_biceps:'))
        self.emojiWeakness = label('')
        self.emojiWeakness.setFont(emoji_font())
        self.emojiWeakness.setText(emoji.emojize(':nauseated_face:'))

        self.frame.layout().addWidget(self.wdgTitle)
        self.frame.layout().addWidget(
            label('Define an attribute that is either a character strength, a weakness, or both',
                  description=True, wordWrap=True), alignment=Qt.AlignmentFlag.AlignLeft)
        self.frame.layout().addWidget(self.lineKey)
        self.frame.layout().addWidget(line())
        self.frame.layout().addWidget(
            group(self.emojiStrength, label('Is it a character strength?'), spacer(), self.toggleStrength))
        self.frame.layout().addWidget(
            group(self.emojiWeakness, label('Is it a character weakness?'), spacer(), self.toggleWeakness))
        self.frame.layout().addWidget(group(self.btnCancel, self.btnConfirm), alignment=Qt.AlignmentFlag.AlignRight)

    def display(self) -> Optional[StrengthWeaknessAttribute]:
        result = self.exec()
        if result == QDialog.DialogCode.Accepted:
            return StrengthWeaknessAttribute(self.lineKey.text(), has_strength=self.toggleStrength.isChecked(),
                                             has_weakness=self.toggleWeakness.isChecked())

    def _changed(self):
        self.btnConfirm.setEnabled(len(self.lineKey.text()) > 0 and self.btnGroup.checkedButton() is not None)

    def _disabledClick(self):
        if not self.lineKey.text():
            qtanim.shake(self.lineKey)
        elif not self.btnGroup.checkedButton():
            qtanim.shake(self.toggleStrength)
            qtanim.shake(self.toggleWeakness)



