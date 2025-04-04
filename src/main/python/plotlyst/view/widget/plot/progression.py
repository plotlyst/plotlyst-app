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
from functools import partial
from typing import List

from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QSize
from PyQt6.QtGui import QIcon, QEnterEvent, QPaintEvent, QPainter, QBrush, QColor
from PyQt6.QtWidgets import QWidget
from overrides import overrides
from qthandy import vbox, margins, transparent, hbox, sp, flow
from qthandy.filter import OpacityEventFilter
from qtmenu import MenuWidget, ActionTooltipDisplayMode

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import Novel, PlotType, PlotProgressionItem, \
    PlotProgressionItemType, DynamicPlotPrincipleGroupType, DynamicPlotPrinciple, DynamicPlotPrincipleType, Plot, \
    DynamicPlotPrincipleGroup, LayoutType, Character
from plotlyst.core.template import antagonist_role
from plotlyst.service.cache import entities_registry
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import frame, action, shadow, tool_btn, insert_before_the_end, fade_out_and_gc
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.style.button import apply_button_palette_color
from plotlyst.view.widget.characters import CharacterSelectorButton
from plotlyst.view.widget.outline import OutlineItemWidget, OutlineTimelineWidget
from plotlyst.view.widget.plot.allies import AlliesGraphicsView, AlliesSupportingSlider, AlliesEmotionalSlider

storyline_progression_steps_descriptions = {
    PlotType.Main: {
        PlotProgressionItemType.BEGINNING: 'The initial state of the plot',
        PlotProgressionItemType.MIDDLE: "The middle state of the plot's progression",
        PlotProgressionItemType.ENDING: 'The resolution of the plot',
        PlotProgressionItemType.EVENT: "A progress or setback in the plot"
    },
    PlotType.Internal: {
        PlotProgressionItemType.BEGINNING: "The starting point of the character's change",
        PlotProgressionItemType.MIDDLE: 'The middle stage of the character transformation',
        PlotProgressionItemType.ENDING: 'How the character changed by the end of the story',
        PlotProgressionItemType.EVENT: "A step towards or away from the character's change"
    },
    PlotType.Subplot: {
        PlotProgressionItemType.BEGINNING: 'The initial state of the subplot',
        PlotProgressionItemType.MIDDLE: "The middle state of the subplot's progression",
        PlotProgressionItemType.ENDING: 'The resolution of the subplot',
        PlotProgressionItemType.EVENT: 'A progress or setback in the subplot'
    },
    PlotType.Relation: {
        PlotProgressionItemType.BEGINNING: 'The initial state of the relationship',
        PlotProgressionItemType.MIDDLE: "The middle state of the relationship's evolution",
        PlotProgressionItemType.ENDING: 'The final state of the relationship',
        PlotProgressionItemType.EVENT: 'A change in the relationship where it gets either worse or better'
    },
    PlotType.Global: {
        PlotProgressionItemType.BEGINNING: 'The initial state of the global storyline',
        PlotProgressionItemType.MIDDLE: "The middle state of the global storyline's progression",
        PlotProgressionItemType.ENDING: 'The resolution of the global storyline',
        PlotProgressionItemType.EVENT: "A progress or setback in the global storyline"
    },
}


class PlotProgressionEventWidget(OutlineItemWidget):
    def __init__(self, novel: Novel, type: PlotType, item: PlotProgressionItem, parent=None):
        self._type = type
        self.beat = item
        self.novel = novel
        super().__init__(item, parent)
        self._btnIcon.removeEventFilter(self._dragEventFilter)
        self._btnIcon.setCursor(Qt.CursorShape.ArrowCursor)
        self.setAcceptDrops(False)

        self._initStyle()

    @overrides
    def mimeType(self) -> str:
        return ''

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        if self.beat.type == PlotProgressionItemType.EVENT:
            self._btnRemove.setVisible(True)

    @overrides
    def _descriptions(self) -> dict:
        return storyline_progression_steps_descriptions[self._type]

    @overrides
    def _icon(self) -> QIcon:
        color = self._color()
        if self.beat.type == PlotProgressionItemType.BEGINNING:
            return IconRegistry.cause_icon(color)
        elif self.beat.type == PlotProgressionItemType.MIDDLE:
            return IconRegistry.from_name('mdi.middleware-outline', color)
        elif self.beat.type == PlotProgressionItemType.ENDING:
            return IconRegistry.from_name('mdi.ray-end', color)
        else:
            return IconRegistry.from_name('msc.debug-stackframe-dot', color)

    @overrides
    def _color(self) -> str:
        return 'grey'

    @overrides
    def _initStyle(self):
        name = None
        if self.beat.type == PlotProgressionItemType.ENDING:
            name = 'End'
        elif self.beat.type == PlotProgressionItemType.EVENT:
            name = ''
        super()._initStyle(name=name)


class PlotEventsTimeline(OutlineTimelineWidget):
    def __init__(self, novel: Novel, type: PlotType, parent=None):
        super().__init__(parent)
        self._type = type
        self.setNovel(novel)

    @overrides
    def setStructure(self, items: List[PlotProgressionItem]):
        super().setStructure(items)
        self._hideFirstAndLastItems()

    @overrides
    def _newBeatWidget(self, item: PlotProgressionItem) -> PlotProgressionEventWidget:
        widget = PlotProgressionEventWidget(self._novel, self._type, item, parent=self)
        widget.removed.connect(self._beatRemoved)

        return widget

    @overrides
    def _insertWidget(self, item: PlotProgressionItem, widget: PlotProgressionEventWidget):
        super()._insertWidget(item, widget)
        self._hideFirstAndLastItems()

    @overrides
    def _placeholderClicked(self, placeholder: QWidget):
        self._currentPlaceholder = placeholder
        self._insertBeat(PlotProgressionItemType.EVENT)

    def _insertBeat(self, beatType: PlotProgressionItemType):
        item = PlotProgressionItem(type=beatType)
        widget = self._newBeatWidget(item)
        self._insertWidget(item, widget)

    def _hideFirstAndLastItems(self):
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if i == 0 or i == self.layout().count() - 1:
                item.widget().setVisible(False)
            else:
                item.widget().setVisible(True)


class DynamicPlotPrincipleWidget(OutlineItemWidget):
    characterChanged = pyqtSignal(Character)

    def __init__(self, novel: Novel, principle: DynamicPlotPrinciple, parent=None,
                 nameAlignment=Qt.AlignmentFlag.AlignCenter):
        self.novel = novel
        self.principle = principle
        super().__init__(principle, parent, colorfulShadow=True, nameAlignment=nameAlignment)
        self._initStyle(name=self.principle.type.display_name(), desc=self.principle.type.placeholder())
        self._btnIcon.setHidden(True)

        self._btnName.setIcon(IconRegistry.from_name(self.principle.type.icon(), self._color()))

        self._hasCharacter = principle.type in [DynamicPlotPrincipleType.ALLY, DynamicPlotPrincipleType.ENEMY,
                                                DynamicPlotPrincipleType.SUSPECT,
                                                DynamicPlotPrincipleType.CREW_MEMBER, DynamicPlotPrincipleType.NEUTRAL]
        if self._hasCharacter:
            margins(self, top=8)
            self._charSelector = CharacterSelectorButton(self.novel, parent=self, iconSize=28)
            self._charSelector.characterSelected.connect(self._characterSelected)
            self._charSelector.setGeometry(5, 0, self._charSelector.sizeHint().width(),
                                           self._charSelector.sizeHint().height())

            if self.principle.character_id:
                character = entities_registry.character(self.principle.character_id)
                if character:
                    self._charSelector.setCharacter(character)

        if principle.type == DynamicPlotPrincipleType.MONSTER:
            self._btnName.setFixedHeight(45)
            apply_button_palette_color(self._btnName, RELAXED_WHITE_COLOR)
            self._btnName.setGraphicsEffect(None)
            self._btnName.setText('Evolution')
            self._btnName.setIcon(IconRegistry.from_name(self.principle.type.icon(), RELAXED_WHITE_COLOR))

    @overrides
    def mimeType(self) -> str:
        return f'application/{self.principle.type.name.lower()}'

    def refreshCharacters(self):
        if self._hasCharacter and self.principle.character_id:
            character = entities_registry.character(self.principle.character_id)
            if character:
                self._charSelector.setCharacter(character)
            else:
                self._charSelector.clear()
                self.principle.character_id = ''
                RepositoryPersistenceManager.instance().update_novel(self.novel)

    @overrides
    def _color(self) -> str:
        return self.principle.type.color()

    def _characterSelected(self, character: Character):
        self.principle.character_id = str(character.id)
        self.characterChanged.emit(character)
        RepositoryPersistenceManager.instance().update_novel(self.novel)


class AllyPlotPrincipleWidget(DynamicPlotPrincipleWidget):
    def __init__(self, novel: Novel, principle: DynamicPlotPrinciple, parent=None,
                 nameAlignment=Qt.AlignmentFlag.AlignCenter):
        super().__init__(novel, principle, parent, nameAlignment)
        if self.principle.node is None:
            self._btnName.setText('Ally/Enemy')

    def updateAlly(self):
        self._btnName.setIcon(IconRegistry.from_name(self.principle.type.icon(), self._color()))
        self._initStyle(name=self.principle.type.display_name(), desc=self.principle.type.placeholder())
        qcolor = QColor(self._color())
        qcolor.setAlpha(125)
        shadow(self._text, color=qcolor)

    @overrides
    def _color(self) -> str:
        if self.principle.node is None:
            return 'grey'
        return super()._color()


class DynamicPlotMultiPrincipleWidget(DynamicPlotPrincipleWidget):
    def __init__(self, novel: Novel, principle: DynamicPlotPrinciple, groupType: DynamicPlotPrincipleGroupType,
                 parent=None):
        super().__init__(novel, principle, parent)
        self.elements = DynamicPlotMultiPrincipleElements(novel, principle.type, groupType)
        self.elements.setStructure(principle.elements)
        self._text.setHidden(True)
        self.layout().addWidget(self.elements)


class DynamicPlotPrincipleElementWidget(DynamicPlotPrincipleWidget):
    def __init__(self, novel: Novel, principle: DynamicPlotPrinciple, parent=None):
        super().__init__(novel, principle, parent, nameAlignment=Qt.AlignmentFlag.AlignLeft)
        self._text.setGraphicsEffect(None)
        transparent(self._text)


class DynamicPlotMultiPrincipleElements(OutlineTimelineWidget):
    def __init__(self, novel: Novel, principleType: DynamicPlotPrincipleType, groupType: DynamicPlotPrincipleGroupType,
                 parent=None):
        self.novel = novel
        self._principleType = principleType
        super().__init__(parent, paintTimeline=False, layout=LayoutType.FLOW, framed=True,
                         frameColor=self._principleType.color())
        self.setProperty('white-bg', True)
        self.setProperty('large-rounded', True)
        margins(self, 0, 0, 0, 0)
        self.layout().setSpacing(0)

        self._menu = DynamicPlotPrincipleSelectorMenu(groupType)
        self._menu.selected.connect(self._insertPrinciple)

    @overrides
    def _newBeatWidget(self, item: DynamicPlotPrinciple) -> OutlineItemWidget:
        wdg = DynamicPlotPrincipleElementWidget(self.novel, item)
        wdg.removed.connect(self._beatRemoved)
        return wdg

    @overrides
    def _newPlaceholderWidget(self, displayText: bool = False) -> QWidget:
        wdg = super()._newPlaceholderWidget(displayText)
        margins(wdg, top=2)
        if displayText:
            wdg.btn.setText('Insert element')
        wdg.btn.setToolTip('Insert new element')
        return wdg

    @overrides
    def _placeholderClicked(self, placeholder: QWidget):
        self._currentPlaceholder = placeholder
        self._menu.exec(self.mapToGlobal(self._currentPlaceholder.pos()))

    def _insertPrinciple(self, principleType: DynamicPlotPrincipleType):
        item = DynamicPlotPrinciple(type=principleType)

        widget = self._newBeatWidget(item)
        self._insertWidget(item, widget)


class DynamicPlotPrincipleSelectorMenu(MenuWidget):
    selected = pyqtSignal(DynamicPlotPrincipleType)

    def __init__(self, groupType: DynamicPlotPrincipleGroupType, parent=None):
        super().__init__(parent)
        self.setTooltipDisplayMode(ActionTooltipDisplayMode.DISPLAY_UNDER)
        if groupType == DynamicPlotPrincipleGroupType.ESCALATION:
            self._addPrinciple(DynamicPlotPrincipleType.TURN)
            self._addPrinciple(DynamicPlotPrincipleType.TWIST)
            self._addPrinciple(DynamicPlotPrincipleType.DANGER)
        elif groupType == DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES:
            self._addPrinciple(DynamicPlotPrincipleType.ALLY)
            self._addPrinciple(DynamicPlotPrincipleType.ENEMY)
        elif groupType == DynamicPlotPrincipleGroupType.SUSPECTS:
            self._addPrinciple(DynamicPlotPrincipleType.DESCRIPTION)
            self._addPrinciple(DynamicPlotPrincipleType.CLUES)
            self._addPrinciple(DynamicPlotPrincipleType.MOTIVE)
            self._addPrinciple(DynamicPlotPrincipleType.RED_HERRING)
            self._addPrinciple(DynamicPlotPrincipleType.ALIBI)
            self._addPrinciple(DynamicPlotPrincipleType.SECRETS)
            self._addPrinciple(DynamicPlotPrincipleType.RED_FLAGS)
            self._addPrinciple(DynamicPlotPrincipleType.CRIMINAL_RECORD)
            self._addPrinciple(DynamicPlotPrincipleType.EVIDENCE_AGAINST)
            self._addPrinciple(DynamicPlotPrincipleType.EVIDENCE_IN_FAVOR)
            self._addPrinciple(DynamicPlotPrincipleType.BEHAVIOR_DURING_INVESTIGATION)
        elif groupType == DynamicPlotPrincipleGroupType.CAST:
            self._addPrinciple(DynamicPlotPrincipleType.SKILL_SET)
            self._addPrinciple(DynamicPlotPrincipleType.MOTIVATION)
            self._addPrinciple(DynamicPlotPrincipleType.CONTRIBUTION)
            self._addPrinciple(DynamicPlotPrincipleType.WEAK_LINK)
            self._addPrinciple(DynamicPlotPrincipleType.HIDDEN_AGENDA)
            self._addPrinciple(DynamicPlotPrincipleType.NICKNAME)

    def _addPrinciple(self, principleType: DynamicPlotPrincipleType):
        self.addAction(action(principleType.display_name(),
                              icon=IconRegistry.from_name(principleType.icon(), principleType.color()),
                              tooltip=principleType.description(), slot=partial(self.selected.emit, principleType)))


class DynamicPlotPrinciplesWidget(OutlineTimelineWidget):
    principleAdded = pyqtSignal(DynamicPlotPrinciple)
    principleRemoved = pyqtSignal(DynamicPlotPrinciple)
    characterChanged = pyqtSignal(DynamicPlotPrinciple, Character)

    def __init__(self, novel: Novel, group: DynamicPlotPrincipleGroup, parent=None):
        super().__init__(parent, paintTimeline=False, layout=LayoutType.FLOW)
        self.layout().setSpacing(1)
        self.novel = novel
        self.group = group
        self._hasMenu = self.group.type in [DynamicPlotPrincipleGroupType.ESCALATION]
        if self._hasMenu:
            self._menu = DynamicPlotPrincipleSelectorMenu(self.group.type)
            self._menu.selected.connect(self._insertPrinciple)

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        if self.group.type != DynamicPlotPrincipleGroupType.EVOLUTION_OF_THE_MONSTER:
            return super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(antagonist_role.icon_color))
        painter.setBrush(QBrush(QColor(antagonist_role.icon_color)))

        height = 50
        offset = 20
        for i, wdg in enumerate(self._beatWidgets):
            painter.setOpacity(0.4 + (i + 1) * 0.6 / len(self._beatWidgets))
            painter.drawConvexPolygon([
                QPointF(wdg.x() - offset, wdg.y()),
                QPointF(wdg.x(), wdg.y() + height / 2),
                QPointF(wdg.x() - offset, wdg.y() + height),
                QPointF(wdg.x() + wdg.width(), wdg.y() + height),
                QPointF(wdg.x() + wdg.width() + offset, wdg.y() + height / 2),
                QPointF(wdg.x() + wdg.width(), wdg.y())
            ])

    def refreshCharacters(self):
        for wdg in self._beatWidgets:
            if isinstance(wdg, DynamicPlotPrincipleWidget):
                wdg.refreshCharacters()

    def updatePrinciple(self, principle: DynamicPlotPrinciple):
        for wdg in self._beatWidgets:
            if isinstance(wdg, AllyPlotPrincipleWidget):
                if wdg.principle == principle:
                    wdg.updateAlly()
                    return

    @overrides
    def _newBeatWidget(self, item: DynamicPlotPrinciple) -> OutlineItemWidget:
        if self.group.type in [DynamicPlotPrincipleGroupType.SUSPECTS, DynamicPlotPrincipleGroupType.CAST]:
            wdg = DynamicPlotMultiPrincipleWidget(self.novel, item, self.group.type)
        elif self.group.type == DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES:
            wdg = AllyPlotPrincipleWidget(self.novel, item)
            wdg.characterChanged.connect(partial(self.characterChanged.emit, item))
        else:
            wdg = DynamicPlotPrincipleWidget(self.novel, item)
        wdg.removed.connect(self._beatRemoved)
        return wdg

    @overrides
    def _newPlaceholderWidget(self, displayText: bool = False) -> QWidget:
        wdg = super()._newPlaceholderWidget(displayText)
        if self.group.type == DynamicPlotPrincipleGroupType.CAST:
            text = 'Add a new cast member'
        elif self.group.type == DynamicPlotPrincipleGroupType.SUSPECTS:
            text = 'Add a new suspect'
        elif self.group.type == DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES:
            text = 'Add a new character'
        elif self.group.type == DynamicPlotPrincipleGroupType.EVOLUTION_OF_THE_MONSTER:
            text = 'Add a new evolution'
        else:
            text = 'Add a new element'

        if displayText:
            wdg.btn.setText(text)
        wdg.btn.setToolTip(text)
        return wdg

    @overrides
    def _placeholderClicked(self, placeholder: QWidget):
        self._currentPlaceholder = placeholder
        if self._hasMenu:
            self._menu.exec(self.mapToGlobal(self._currentPlaceholder.pos()))
        elif self.group.type == DynamicPlotPrincipleGroupType.ELEMENTS_OF_WONDER:
            self._insertPrinciple(DynamicPlotPrincipleType.WONDER)
        elif self.group.type == DynamicPlotPrincipleGroupType.EVOLUTION_OF_THE_MONSTER:
            self._insertPrinciple(DynamicPlotPrincipleType.MONSTER)
        elif self.group.type == DynamicPlotPrincipleGroupType.SUSPECTS:
            self._insertPrinciple(DynamicPlotPrincipleType.SUSPECT)
        elif self.group.type == DynamicPlotPrincipleGroupType.CAST:
            self._insertPrinciple(DynamicPlotPrincipleType.CREW_MEMBER)
        elif self.group.type == DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES:
            self._insertPrinciple(DynamicPlotPrincipleType.ALLY)

    def _insertPrinciple(self, principleType: DynamicPlotPrincipleType):
        item = DynamicPlotPrinciple(type=principleType)

        widget = self._newBeatWidget(item)
        self._insertWidget(item, widget)

        self.principleAdded.emit(item)

    def _beatRemoved(self, wdg: OutlineItemWidget, teardownFunction=None):
        principle = wdg.item
        super()._beatRemoved(wdg, teardownFunction)

        self.principleRemoved.emit(principle)


class BasePlotPrinciplesGroupWidget(QWidget):

    def __init__(self, principleGroup: DynamicPlotPrincipleGroup, parent=None):
        super().__init__(parent)
        self.group = principleGroup
        vbox(self)


class DynamicPlotPrinciplesGroupWidget(BasePlotPrinciplesGroupWidget):

    def __init__(self, novel: Novel, principleGroup: DynamicPlotPrincipleGroup, parent=None):
        super().__init__(principleGroup, parent)
        self._wdgPrinciples = DynamicPlotPrinciplesWidget(novel, self.group)
        self._wdgPrinciples.setStructure(self.group.principles)
        self.frame.layout().addWidget(self._wdgPrinciples)

    def refreshCharacters(self):
        self._wdgPrinciples.refreshCharacters()


class AlliesPrinciplesGroupWidget(QWidget):
    changed = pyqtSignal()

    def __init__(self, novel: Novel, principleGroup: DynamicPlotPrincipleGroup, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.group = principleGroup

        self._wdgPrinciples = QWidget()
        flow(self._wdgPrinciples)

        self._supporterSlider = AlliesSupportingSlider()
        self._emotionSlider = AlliesEmotionalSlider()

        self._leftEditor = QWidget()
        sp(self._leftEditor).h_max()
        vbox(self._leftEditor, spacing=0)
        self._toolbar = frame()
        self._toolbar.setProperty('relaxed-white-bg', True)
        self._toolbar.setProperty('rounded-on-top', True)
        hbox(self._toolbar)
        self._toolbar.layout().addWidget(self._supporterSlider)
        self._toolbar.layout().addWidget(self._emotionSlider)

        self.view = AlliesGraphicsView(self.novel, self.group)

        self._leftEditor.layout().addWidget(self._toolbar)
        self._leftEditor.layout().addWidget(self.view)

        hbox(self)
        self.layout().addWidget(self._leftEditor, alignment=Qt.AlignmentFlag.AlignTop)
        self.layout().addWidget(self._wdgPrinciples)

        self.btnAdd = tool_btn(IconRegistry.plus_icon('grey'), transparent_=True)
        self.btnAdd.installEventFilter(OpacityEventFilter(self.btnAdd))
        self.btnAdd.setIconSize(QSize(48, 48))
        self.btnAdd.setFixedHeight(200)
        self.btnAdd.clicked.connect(self._addAlly)
        self._wdgPrinciples.layout().addWidget(self.btnAdd)

        for principle in self.group.principles:
            self._initBubbleWidget(principle)

        self.view.alliesScene().posChanged.connect(self._posChanged)
        self.view.alliesScene().allyChanged.connect(self._allyChanged)

        self._supporterSlider.setPrinciples(self.group.principles)
        self._emotionSlider.setPrinciples(self.group.principles)

    def _addAlly(self):
        principle = DynamicPlotPrinciple(type=DynamicPlotPrincipleType.NEUTRAL)
        self.group.principles.append(principle)
        self.view.addNewAlly(principle)
        self._initBubbleWidget(principle)

        self.changed.emit()

    def _removeAlly(self, bubble: AllyPlotPrincipleWidget):
        self.view.removeAlly(bubble.principle)
        self.group.principles.remove(bubble.principle)
        fade_out_and_gc(self._wdgPrinciples, bubble)

        self.changed.emit()

    def _posChanged(self, _: DynamicPlotPrinciple):
        self._supporterSlider.setPrinciples(self.group.principles)
        self._emotionSlider.setPrinciples(self.group.principles)

        self.changed.emit()

    def _allyChanged(self, principle: DynamicPlotPrinciple):
        for i in range(self._wdgPrinciples.layout().count()):
            item = self._wdgPrinciples.layout().itemAt(i)
            if item.widget() and isinstance(item.widget(), AllyPlotPrincipleWidget):
                wdg: AllyPlotPrincipleWidget = item.widget()
                if wdg.principle == principle:
                    wdg.updateAlly()
                    break

        self.changed.emit()

    def _initBubbleWidget(self, principle: DynamicPlotPrinciple):
        bubble = AllyPlotPrincipleWidget(self.novel, principle)
        bubble.removed.connect(partial(self._removeAlly, bubble))
        bubble.characterChanged.connect(partial(self.view.updateAlly, principle))
        insert_before_the_end(self._wdgPrinciples, bubble)


class DynamicPlotPrinciplesEditor(QWidget):
    def __init__(self, novel: Novel, plot: Plot, parent=None):
        super().__init__(parent)
        # self.novel = novel
        # self.plot = plot
        # vbox(self, 5, 10)

        # for group in self.plot.dynamic_principles:
        #     self._addGroup(group)
        #
        # self.repo = RepositoryPersistenceManager.instance()

    def refreshCharacters(self):
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item.widget() and isinstance(item.widget(), DynamicPlotPrinciplesGroupWidget):
                item.widget().refreshCharacters()

    def addNewGroup(self, groupType: DynamicPlotPrincipleGroupType) -> DynamicPlotPrinciplesGroupWidget:
        group = DynamicPlotPrincipleGroup(groupType)
        if groupType == DynamicPlotPrincipleGroupType.ELEMENTS_OF_WONDER:
            group.principles.append(DynamicPlotPrinciple(type=DynamicPlotPrincipleType.WONDER))
        elif groupType == DynamicPlotPrincipleGroupType.EVOLUTION_OF_THE_MONSTER:
            group.principles.append(DynamicPlotPrinciple(type=DynamicPlotPrincipleType.MONSTER))
            group.principles.append(DynamicPlotPrinciple(type=DynamicPlotPrincipleType.MONSTER))
        elif groupType == DynamicPlotPrincipleGroupType.ESCALATION:
            group.principles.append(DynamicPlotPrinciple(type=DynamicPlotPrincipleType.TURN))
        elif groupType == DynamicPlotPrincipleGroupType.SUSPECTS:
            group.principles.append(DynamicPlotPrinciple(type=DynamicPlotPrincipleType.SUSPECT))
        elif groupType == DynamicPlotPrincipleGroupType.CAST:
            group.principles.append(DynamicPlotPrinciple(type=DynamicPlotPrincipleType.CREW_MEMBER))

        self.plot.dynamic_principles.append(group)
        wdg = self._addGroup(group)
        self._save()

        return wdg

    # def _addGroup(self, group: DynamicPlotPrincipleGroup) -> DynamicPlotPrinciplesGroupWidget:
    #     if group.type == DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES:
    #         wdg = AlliesPrinciplesGroupWidget(self.novel, group)
    #     else:
    #         wdg = DynamicPlotPrinciplesGroupWidget(self.novel, group)
    #     wdg.remove.connect(partial(self._removeGroup, wdg))
    #     self.layout().addWidget(wdg)
    #
    #     return wdg

    # def _removeGroup(self, wdg: DynamicPlotPrinciplesGroupWidget):
    #     title = f'Are you sure you want to delete the storyline elements "{wdg.group.type.display_name()}"?'
    #     if wdg.group.principles and not confirmed("This action cannot be undone.", title):
    #         return
    #
    #     self.plot.dynamic_principles.remove(wdg.group)
    #     fade_out_and_gc(self, wdg)
    #     self._save()

    # def _save(self):
    #     self.repo.update_novel(self.novel)
