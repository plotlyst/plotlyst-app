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

from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QPaintEvent, QPainter, QBrush, QColor
from PyQt6.QtWidgets import QWidget
from overrides import overrides
from qthandy import margins, transparent
from qtmenu import MenuWidget, ActionTooltipDisplayMode

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import Novel, DynamicPlotPrincipleGroupType, DynamicPlotPrinciple, DynamicPlotPrincipleType, \
    DynamicPlotPrincipleGroup, LayoutType, Character
from plotlyst.core.template import antagonist_role
from plotlyst.service.cache import entities_registry
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import action
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.style.button import apply_button_palette_color
from plotlyst.view.widget.characters import CharacterSelectorButton
from plotlyst.view.widget.outline import OutlineItemWidget, OutlineTimelineWidget


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

        self.principleAdded.emit(item)

    def _beatRemoved(self, wdg: OutlineItemWidget, teardownFunction=None):
        principle = wdg.item
        super()._beatRemoved(wdg, teardownFunction)

        self.principleRemoved.emit(principle)
