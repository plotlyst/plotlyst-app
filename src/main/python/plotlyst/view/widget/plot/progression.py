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

from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QIcon, QEnterEvent, QPaintEvent, QPainter, QBrush, QColor
from PyQt6.QtWidgets import QWidget
from overrides import overrides
from qthandy import vbox, incr_icon, bold, spacer, retain_when_hidden, margins, transparent, hbox
from qthandy.filter import VisibilityToggleEventFilter
from qtmenu import MenuWidget, ActionTooltipDisplayMode

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import Novel, PlotType, PlotProgressionItem, \
    PlotProgressionItemType, DynamicPlotPrincipleGroupType, DynamicPlotPrinciple, DynamicPlotPrincipleType, Plot, \
    DynamicPlotPrincipleGroup, LayoutType, Character
from plotlyst.core.template import antagonist_role
from plotlyst.service.cache import entities_registry
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import frame, fade_out_and_gc, action
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.style.button import apply_button_palette_color
from plotlyst.view.style.theme import BG_MUTED_COLOR
from plotlyst.view.widget.characters import CharacterSelectorButton
from plotlyst.view.widget.confirm import confirmed
from plotlyst.view.widget.display import IconText
from plotlyst.view.widget.input import RemovalButton
from plotlyst.view.widget.outline import OutlineItemWidget, OutlineTimelineWidget
from plotlyst.view.widget.plot.allies import AlliesGraphicsView

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
                                                DynamicPlotPrincipleType.CREW_MEMBER]
        if self._hasCharacter:
            self._charSelector = CharacterSelectorButton(self.novel, iconSize=64)
            self._charSelector.characterSelected.connect(self._characterSelected)
            self.layout().insertWidget(0, self._charSelector, alignment=Qt.AlignmentFlag.AlignCenter)

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
        RepositoryPersistenceManager.instance().update_novel(self.novel)


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
        super().__init__(parent, paintTimeline=False, layout=LayoutType.VERTICAL, framed=True,
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

    @overrides
    def _newBeatWidget(self, item: DynamicPlotPrinciple) -> OutlineItemWidget:
        if self.group.type in [DynamicPlotPrincipleGroupType.SUSPECTS, DynamicPlotPrincipleGroupType.CAST]:
            wdg = DynamicPlotMultiPrincipleWidget(self.novel, item, self.group.type)
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


class BasePlotPrinciplesGroupWidget(QWidget):
    remove = pyqtSignal()

    def __init__(self, principleGroup: DynamicPlotPrincipleGroup, parent=None):
        super().__init__(parent)
        self.group = principleGroup
        self.frame = frame()
        self.frame.setObjectName('frame')
        hbox(self.frame, 0, 0)
        self.setStyleSheet(f'''
                                   #frame {{
                                        border: 1px solid lightgrey;
                                        border-radius: 8px;
                                        background: {BG_MUTED_COLOR};
                                   }}
                                   ''')

        vbox(self)

        self._title = IconText()
        self._title.setText(self.group.type.display_name())
        self._title.setIcon(IconRegistry.from_name(self.group.type.icon(), self.group.type.color()))
        incr_icon(self._title, 4)
        bold(self._title)
        apply_button_palette_color(self._title, self.group.type.color())

        self.btnRemove = RemovalButton()
        retain_when_hidden(self.btnRemove)
        self.installEventFilter(VisibilityToggleEventFilter(self.btnRemove, self))
        self.btnRemove.clicked.connect(self.remove)

        self.layout().addWidget(group(self._title, spacer(), self.btnRemove))
        self.layout().addWidget(self.frame)


class DynamicPlotPrinciplesGroupWidget(BasePlotPrinciplesGroupWidget):

    def __init__(self, novel: Novel, principleGroup: DynamicPlotPrincipleGroup, parent=None):
        super().__init__(principleGroup, parent)
        self._wdgPrinciples = DynamicPlotPrinciplesWidget(novel, self.group)
        self._wdgPrinciples.setStructure(self.group.principles)
        self.frame.layout().addWidget(self._wdgPrinciples)

    def refreshCharacters(self):
        self._wdgPrinciples.refreshCharacters()


class AlliesPrinciplesGroupWidget(BasePlotPrinciplesGroupWidget):

    def __init__(self, novel: Novel, principleGroup: DynamicPlotPrincipleGroup, parent=None):
        super().__init__(principleGroup, parent)
        self.novel = novel

        self._wdgPrinciples = DynamicPlotPrinciplesWidget(novel, self.group)
        self._wdgPrinciples.setStructure(self.group.principles)

        self.view = AlliesGraphicsView(self.novel, self.group)
        margins(self.frame, 35, 20, 20, 20)
        self.frame.layout().addWidget(self.view, alignment=Qt.AlignmentFlag.AlignTop)
        self.frame.layout().addWidget(self._wdgPrinciples)


class DynamicPlotPrinciplesEditor(QWidget):
    def __init__(self, novel: Novel, plot: Plot, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.plot = plot
        vbox(self, 5, 10)

        for group in self.plot.dynamic_principles:
            self._addGroup(group)

        self.repo = RepositoryPersistenceManager.instance()

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

    def _addGroup(self, group: DynamicPlotPrincipleGroup) -> DynamicPlotPrinciplesGroupWidget:
        if group.type == DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES:
            wdg = AlliesPrinciplesGroupWidget(self.novel, group)
        else:
            wdg = DynamicPlotPrinciplesGroupWidget(self.novel, group)
        wdg.remove.connect(partial(self._removeGroup, wdg))
        self.layout().addWidget(wdg)

        return wdg

    def _removeGroup(self, wdg: DynamicPlotPrinciplesGroupWidget):
        title = f'Are you sure you want to delete the storyline elements "{wdg.group.type.display_name()}"?'
        if wdg.group.principles and not confirmed("This action cannot be undone.", title):
            return

        self.plot.dynamic_principles.remove(wdg.group)
        fade_out_and_gc(self, wdg)
        self._save()

    def _save(self):
        self.repo.update_novel(self.novel)
