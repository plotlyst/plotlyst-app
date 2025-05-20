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

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget
from overrides import overrides
from qthandy import margins, transparent
from qtmenu import MenuWidget, ActionTooltipDisplayMode

from plotlyst.core.domain import Novel, DynamicPlotPrincipleGroupType, DynamicPlotPrinciple, DynamicPlotPrincipleType, \
    DynamicPlotPrincipleGroup, LayoutType, Character
from plotlyst.service.cache import entities_registry
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import action
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.characters import CharacterSelectorButton
from plotlyst.view.widget.outline import OutlineItemWidget, OutlineTimelineWidget


class DynamicPlotPrincipleWidget(OutlineItemWidget):
    characterChanged = pyqtSignal(Character)

    def __init__(self, novel: Novel, principle: DynamicPlotPrinciple, parent=None,
                 nameAlignment=Qt.AlignmentFlag.AlignCenter, colorfulShadow: bool = True):
        self.novel = novel
        self.principle = principle
        super().__init__(principle, parent, colorfulShadow=colorfulShadow, nameAlignment=nameAlignment)
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

        self.setMinimumHeight(150)
        self.setMinimumWidth(210)

        self._btnName.setIcon(QIcon())


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
        self._groupType = groupType
        super().__init__(parent, paintTimeline=False, layout=LayoutType.VERTICAL, framed=True, frameColor='grey')
        self.setProperty('white-bg', True)
        self.setProperty('large-rounded', True)
        margins(self, 0, 0, 0, 0)
        self.layout().setSpacing(0)


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
        _menu = DynamicPlotPrincipleSelectorMenu(self._groupType)
        _menu.selected.connect(self._insertPrinciple)

        _menu.exec(self.mapToGlobal(self._currentPlaceholder.pos()))

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

    def refreshCharacters(self):
        for wdg in self._beatWidgets:
            if isinstance(wdg, DynamicPlotPrincipleWidget):
                wdg.refreshCharacters()

    @overrides
    def _newBeatWidget(self, item: DynamicPlotPrinciple) -> OutlineItemWidget:
        wdg = DynamicPlotMultiPrincipleWidget(self.novel, item, self.group.type)
        wdg.removed.connect(self._beatRemoved)
        return wdg

    @overrides
    def _newPlaceholderWidget(self, displayText: bool = False) -> QWidget:
        wdg = super()._newPlaceholderWidget(displayText)
        if self.group.type == DynamicPlotPrincipleGroupType.CAST:
            text = 'Add a new cast member'
        elif self.group.type == DynamicPlotPrincipleGroupType.SUSPECTS:
            text = 'Add a new suspect'
        else:
            text = 'Add a new element'

        if displayText:
            wdg.btn.setText(text)
        else:
            wdg.btn.setToolTip(text)
        return wdg

    @overrides
    def _placeholderClicked(self, placeholder: QWidget):
        self._currentPlaceholder = placeholder
        if self.group.type == DynamicPlotPrincipleGroupType.SUSPECTS:
            self._insertPrinciple(DynamicPlotPrincipleType.SUSPECT)
        elif self.group.type == DynamicPlotPrincipleGroupType.CAST:
            self._insertPrinciple(DynamicPlotPrincipleType.CREW_MEMBER)

    def _insertPrinciple(self, principleType: DynamicPlotPrincipleType):
        item = DynamicPlotPrinciple(type=principleType)

        widget = self._newBeatWidget(item)
        self._insertWidget(item, widget)

        self.principleAdded.emit(item)

    @overrides
    def _beatRemoved(self, wdg: OutlineItemWidget, teardownFunction=None):
        principle = wdg.item
        super()._beatRemoved(wdg, teardownFunction)

        self.principleRemoved.emit(principle)
