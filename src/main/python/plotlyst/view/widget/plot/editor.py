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
from typing import Set, Dict, Tuple, List, Optional

from PyQt6.QtCore import pyqtSignal, Qt, QSize, QTimer, QEvent, QObject, QRectF
from PyQt6.QtGui import QColor, QIcon, QResizeEvent, QEnterEvent, QPaintEvent, QPainter, QRadialGradient, QPainterPath
from PyQt6.QtWidgets import QWidget, QStackedWidget, QButtonGroup, QScrollArea, QFrame, QLabel
from overrides import overrides
from qthandy import flow, incr_font, \
    margins, italic, clear_layout, vspacer, sp, vbox, transparent, incr_icon, bold, hbox, line, spacer, busy
from qthandy.filter import OpacityEventFilter, VisibilityToggleEventFilter
from qtmenu import MenuWidget, ActionTooltipDisplayMode

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, BLACK_COLOR, RELAXED_WHITE_COLOR
from plotlyst.core.domain import Novel, Plot, PlotType, Character, PlotPrinciple, \
    PlotPrincipleType, PlotProgressionItem, \
    PlotProgressionItemType, DynamicPlotPrincipleGroupType, LayoutType, DynamicPlotPrincipleGroup, BackstoryEvent, \
    Position
from plotlyst.core.template import antagonist_role
from plotlyst.event.core import EventListener, Event, emit_event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import CharacterChangedEvent, CharacterDeletedEvent, StorylineCreatedEvent, \
    StorylineRemovedEvent, StorylineCharacterAssociationChanged, StorylineChangedEvent
from plotlyst.service.cache import entities_registry
from plotlyst.service.persistence import RepositoryPersistenceManager, delete_plot
from plotlyst.settings import STORY_LINE_COLOR_CODES
from plotlyst.view.common import action, fade_out_and_gc, label, frame, tool_btn, columns, \
    push_btn, link_buttons_to_pages, scroll_area, rows, exclusive_buttons, scroll_to_bottom
from plotlyst.view.generated.plot_editor_widget_ui import Ui_PlotEditor
from plotlyst.view.icons import IconRegistry, avatars
from plotlyst.view.layout import group
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.widget.button import SelectorToggleButton
from plotlyst.view.widget.characters import CharacterAvatar, CharacterSelectorMenu
from plotlyst.view.widget.confirm import confirmed
from plotlyst.view.widget.display import SeparatorLineWithShadow, PopupDialog, IconText, icon_text
from plotlyst.view.widget.input import AutoAdjustableLineEdit, Toggle
from plotlyst.view.widget.plot.allies import AlliesPrinciplesGroupWidget
from plotlyst.view.widget.plot.escalation import StorylineEscalationEditorWidget
from plotlyst.view.widget.plot.matrix import StorylinesImpactMatrix
from plotlyst.view.widget.plot.principle import PlotPrincipleEditor, \
    PrincipleSelectorObject, principle_type_index, principle_icon, principle_hint
from plotlyst.view.widget.plot.progression import DynamicPlotPrinciplesWidget
from plotlyst.view.widget.plot.timeline import StorylineTimelineWidget, StorylineVillainEvolutionWidget
from plotlyst.view.widget.tree import TreeView, ContainerNode
from plotlyst.view.widget.utility import ColorPicker, IconSelectorDialog


class PlotNode(ContainerNode):
    def __init__(self, plot: Plot, parent=None):
        super(PlotNode, self).__init__(plot.text, parent)
        self._plot = plot
        self.setPlusButtonEnabled(False)
        incr_font(self._lblTitle)
        margins(self._wdgTitle, top=5, bottom=5)

        self.refresh()

    def plot(self) -> Plot:
        return self._plot

    def refresh(self):
        if self._plot.icon:
            self._icon.setIcon(IconRegistry.from_name(self._plot.icon, self._plot.icon_color))
            self._icon.setVisible(True)
        else:
            self._icon.setHidden(True)

        self._lblTitle.setText(self._plot.text)


class ImpactNode(ContainerNode):
    def __init__(self, parent=None):
        super().__init__('Impact matrix', IconRegistry.from_name('mdi6.camera-metering-matrix'), parent)
        self.setPlusButtonEnabled(False)
        self.setMenuEnabled(False)
        incr_font(self._lblTitle)
        margins(self._wdgTitle, top=5, bottom=5)


class PlotTreeView(TreeView, EventListener):
    plotSelected = pyqtSignal(Plot)
    plotRemoved = pyqtSignal(Plot)
    impactGridSelected = pyqtSignal()

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._plots: Dict[Plot, PlotNode] = {}
        self._characterNodes: Dict[Character, ContainerNode] = {}
        self._selectedPlots: Set[Plot] = set()

        self._impactNode: Optional[ImpactNode] = None

        self.refresh()

        event_dispatchers.instance(self._novel).register(self, StorylineCharacterAssociationChanged,
                                                         CharacterChangedEvent)

    @overrides
    def event_received(self, event: Event):
        self.refresh()

    def refresh(self):
        self._selectedPlots.clear()
        self._characterNodes.clear()
        self._plots.clear()
        clear_layout(self._centralWidget)

        characters = [x.character(self._novel) for x in self._novel.plots if x.character_id]
        characters_set = set(characters)
        characters_set.discard(None)
        if characters_set:
            for character in characters:
                if character in self._characterNodes.keys():
                    continue
                node = ContainerNode(character.name, avatars.avatar(character), readOnly=True)
                node.setSelectionEnabled(False)
                self._characterNodes[character] = node
                self._centralWidget.layout().addWidget(self._characterNodes[character])

        for plot in self._novel.plots:
            wdg = self.__initPlotWidget(plot)
            if plot.character_id and self._characterNodes:
                character = plot.character(self._novel)
                self._characterNodes[character].addChild(wdg)
            else:
                self._centralWidget.layout().addWidget(wdg)

        self._centralWidget.layout().addWidget(line())
        self._impactNode = ImpactNode()
        self._impactNode.selectionChanged.connect(self._impactGridSelectionChanged)
        self._centralWidget.layout().addWidget(self._impactNode)

        self._centralWidget.layout().addWidget(vspacer())

    def refreshPlot(self, plot: Plot):
        self._plots[plot].refresh()

    def refreshCharacters(self):
        self.refresh()

    def addPlot(self, plot: Plot):
        wdg = self.__initPlotWidget(plot)
        self._centralWidget.layout().insertWidget(self._centralWidget.layout().count() - 3, wdg)

    def selectPlot(self, plot: Plot):
        self._plots[plot].select()
        wdg = self._plots[plot]
        self._plotSelectionChanged(wdg, wdg.isSelected())

    def removePlot(self, plot: Plot):
        self._removePlot(self._plots[plot])

    def clearSelection(self):
        for plot in self._selectedPlots:
            self._plots[plot].deselect()
        self._selectedPlots.clear()

    def _plotSelectionChanged(self, wdg: PlotNode, selected: bool):
        if selected:
            self.clearSelection()
            self._impactNode.deselect()
            self._selectedPlots.add(wdg.plot())
            QTimer.singleShot(10, lambda: self.plotSelected.emit(wdg.plot()))
        elif wdg.plot() in self._selectedPlots:
            self._selectedPlots.remove(wdg.plot())

    def _impactGridSelectionChanged(self, selected: bool):
        if selected:
            self.clearSelection()
            QTimer.singleShot(10, lambda: self.impactGridSelected.emit())

    def _removePlot(self, wdg: PlotNode):
        plot = wdg.plot()
        title = f'Are you sure you want to delete the storyline "{plot.text}"?'
        if not confirmed("This action cannot be undone.", title):
            return
        if plot in self._selectedPlots:
            self._selectedPlots.remove(plot)
        self._plots.pop(plot)

        characterNode = None
        if plot.character_id and self._characterNodes:
            character = plot.character(self._novel)
            characterNode = self._characterNodes[character]
            if len(characterNode.childrenWidgets()) == 1:
                self._characterNodes.pop(character)  # remove parent too
            else:
                characterNode = None  # keep parent

        fade_out_and_gc(wdg.parent(), wdg)
        if characterNode:
            fade_out_and_gc(self._centralWidget, characterNode)

        self.plotRemoved.emit(wdg.plot())

    def __initPlotWidget(self, plot: Plot) -> PlotNode:
        if plot not in self._plots.keys():
            wdg = PlotNode(plot)
            wdg.selectionChanged.connect(partial(self._plotSelectionChanged, wdg))
            wdg.deleted.connect(partial(self._removePlot, wdg))
            self._plots[plot] = wdg

        return self._plots[plot]


class PrincipleSelectorButton(SelectorToggleButton):
    displayHint = pyqtSignal(str)
    hideHint = pyqtSignal()

    def __init__(self, principle: PlotPrincipleType, selector: PrincipleSelectorObject, parent=None):
        super().__init__(minWidth=70, parent=parent)
        self.principle = principle
        self.selector = selector

        self.setText(principle.display_name())
        self.setIcon(principle_icon(principle, BLACK_COLOR))
        self._hint = f'{self.text()}: {principle_hint(principle)}'

        self.clicked.connect(self._clicked)

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        self.displayHint.emit(self._hint)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        self.hideHint.emit()

    def _clicked(self, checked: bool):
        self.selector.principleToggled.emit(self.principle, checked)


class PlotElementSelectorPopup(PopupDialog):
    def __init__(self, plot: Plot, selector: PrincipleSelectorObject, parent=None):
        super().__init__(parent)
        self._plot = plot
        self._selector = selector

        self.stack = QStackedWidget()
        self.pagePrinciples = rows()
        self.pageEditors = rows()
        self.stack.addWidget(self.pagePrinciples)
        self.stack.addWidget(self.pageEditors)

        self.btnPrinciples = push_btn(IconRegistry.from_name('mdi.cube', 'grey', PLOTLYST_SECONDARY_COLOR),
                                      'Core principles',
                                      properties=['secondary-selector', 'transparent'], checkable=True)
        incr_font(self.btnPrinciples, 2)
        incr_icon(self.btnPrinciples, 4)
        self.btnEditors = push_btn(IconRegistry.from_name('fa5s.cubes', 'grey', PLOTLYST_SECONDARY_COLOR),
                                   'Complex elements',
                                   properties=['secondary-selector', 'transparent'], checkable=True)
        incr_font(self.btnEditors, 2)
        incr_icon(self.btnEditors, 4)
        exclusive_buttons(self, self.btnPrinciples, self.btnEditors)

        link_buttons_to_pages(self.stack,
                              [(self.btnPrinciples, self.pagePrinciples), (self.btnEditors, self.pageEditors)])
        self.btnPrinciples.setChecked(True)

        self.scroll = scroll_area(h_on=False, frameless=True)
        self.center = QFrame()
        self.pagePrinciples.layout().addWidget(self.scroll)
        vbox(self.center)
        margins(self.center, bottom=15)
        self.scroll.setWidget(self.center)
        self.center.setProperty('white-bg', True)

        self._addHeader('Plot principles', 'mdi6.note-text-outline')
        self._hintPlot = label(' ', description=True, wordWrap=True)
        self.center.layout().addWidget(self._hintPlot)
        self.wdgPlotPrinciples = self._addFlowContainer()

        self._addHeader('Character arc principles', 'mdi.mirror')
        self._hintCharacter = label(' ', description=True, wordWrap=True)
        self.center.layout().addWidget(self._hintCharacter)
        self.wdgCharacterPrinciples = self._addFlowContainer()

        self._addHeader('Genre specific principles', 'mdi.drama-masks')
        self._hintGenre = label(' ', description=True, wordWrap=True)
        self.center.layout().addWidget(self._hintGenre)
        self.wdgGenrePrinciples = self._addFlowContainer()
        self.wdgGenrePrinciples.layout().setSpacing(8)

        selected_principles = set(x.type for x in self._plot.principles)
        self._addPrinciples(self.wdgPlotPrinciples,
                            [PlotPrincipleType.QUESTION, PlotPrincipleType.GOAL, PlotPrincipleType.ANTAGONIST,
                             PlotPrincipleType.CONFLICT, PlotPrincipleType.STAKES], selected_principles, self._hintPlot)

        self._addPrinciples(self.wdgCharacterPrinciples,
                            [PlotPrincipleType.POSITIVE_CHANGE, PlotPrincipleType.NEGATIVE_CHANGE,
                             PlotPrincipleType.DESIRE, PlotPrincipleType.NEED, PlotPrincipleType.EXTERNAL_CONFLICT,
                             PlotPrincipleType.INTERNAL_CONFLICT, PlotPrincipleType.FLAW], selected_principles,
                            self._hintCharacter)
        self._addGenrePrinciples(self.wdgGenrePrinciples,
                                 [PlotPrincipleType.SKILL_SET, PlotPrincipleType.TICKING_CLOCK], selected_principles,
                                 self._hintGenre, 'Action', 'fa5s.running')
        self._addGenrePrinciples(self.wdgGenrePrinciples,
                                 [PlotPrincipleType.SCHEME], selected_principles,
                                 self._hintGenre, 'Caper', 'mdi.robber')
        self._addGenrePrinciples(self.wdgGenrePrinciples,
                                 [PlotPrincipleType.MONSTER, PlotPrincipleType.CONFINED_SPACE], selected_principles,
                                 self._hintGenre, 'Horror', 'ri.knife-blood-fill')
        self._addGenrePrinciples(self.wdgGenrePrinciples,
                                 [PlotPrincipleType.CRIME, PlotPrincipleType.CRIME_CLOCK, PlotPrincipleType.SLEUTH,
                                  PlotPrincipleType.AUTHORITY,
                                  PlotPrincipleType.MACGUFFIN], selected_principles,
                                 self._hintGenre, 'Crime', 'fa5s.mask')
        self._addGenrePrinciples(self.wdgGenrePrinciples,
                                 [PlotPrincipleType.SELF_DISCOVERY, PlotPrincipleType.LOSS_OF_INNOCENCE,
                                  PlotPrincipleType.MATURITY, PlotPrincipleType.FIRST_LOVE, PlotPrincipleType.MENTOR],
                                 selected_principles,
                                 self._hintGenre, 'Coming of age', 'ri.seedling-line')

        self.scrollComplex = scroll_area(h_on=False, frameless=True)
        self.centerComplex = QFrame()
        self.pageEditors.layout().addWidget(self.scrollComplex)
        vbox(self.centerComplex, spacing=0)
        margins(self.centerComplex, bottom=15)
        self.scrollComplex.setWidget(self.centerComplex)
        self.centerComplex.setProperty('white-bg', True)

        self._addComplexSelector(DynamicPlotPrincipleGroupType.TIMELINE, self._plot.has_progression)
        self._addComplexSelector(DynamicPlotPrincipleGroupType.ESCALATION, self._plot.has_escalation)
        self._addComplexSelector(DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES, self._plot.has_allies)
        self._addComplexSelector(DynamicPlotPrincipleGroupType.SUSPECTS, self._plot.has_suspects)
        self._addComplexSelector(DynamicPlotPrincipleGroupType.CAST, self._plot.has_cast)
        self._addComplexSelector(DynamicPlotPrincipleGroupType.EVOLUTION_OF_THE_MONSTER, self._plot.has_villain)
        self.centerComplex.layout().addWidget(vspacer())

        self.btnClose = push_btn(text='Close', properties=['confirm', 'cancel'])
        self.btnClose.clicked.connect(self.accept)

        self.center.layout().addWidget(vspacer())

        self.frame.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)
        self.frame.layout().addWidget(group(self.btnPrinciples, self.btnEditors),
                                      alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame.layout().addWidget(self.stack)
        self.frame.layout().addWidget(self.btnClose, alignment=Qt.AlignmentFlag.AlignRight)

        self.setMinimumSize(self._adjustedSize(0.8, 0.8, 450, 350))

    @overrides
    def sizeHint(self) -> QSize:
        return self._adjustedSize(0.8, 0.8, 450, 350)

    def display(self):
        self.exec()

    def _addHeader(self, title: str, icon: str = ''):
        lbl = IconText()
        lbl.setText(title)
        bold(lbl)
        incr_icon(lbl, 2)
        if icon:
            lbl.setIcon(IconRegistry.from_name(icon))

        self.center.layout().addWidget(lbl, alignment=Qt.AlignmentFlag.AlignLeft)
        self.center.layout().addWidget(line())

    def _addFlowContainer(self) -> QWidget:
        wdg = QWidget()
        flow(wdg)
        margins(wdg, left=20, top=0)
        sp(wdg).v_max()
        self.center.layout().addWidget(wdg)

        return wdg

    def _addGenrePrinciples(self, parent: QWidget, principles: List[PlotPrincipleType], active: Set[PlotPrincipleType],
                            hintLbl: QLabel, genre: str, genre_icon: str):
        wdg = frame()
        wdg.setProperty('muted-bg', True)
        wdg.setProperty('rounded', True)
        hbox(wdg, 3, spacing=2)
        wdg.layout().addWidget(icon_text(genre_icon, f'{genre}:', opacity=0.5), alignment=Qt.AlignmentFlag.AlignVCenter)
        self._addPrinciples(wdg, principles, active, hintLbl)

        parent.layout().addWidget(wdg)

    def _addPrinciples(self, parent: QWidget, principles: List[PlotPrincipleType], active: Set[PlotPrincipleType],
                       hintLbl: QLabel):
        for principle in principles:
            btn = PrincipleSelectorButton(principle, self._selector)
            if principle in active:
                btn.setChecked(True)
            btn.displayHint.connect(hintLbl.setText)
            btn.hideHint.connect(lambda: hintLbl.setText(' '))
            parent.layout().addWidget(btn)

    def _addComplexSelector(self, complexType: DynamicPlotPrincipleGroupType, default: bool):
        toggle = Toggle()
        wdg = rows(5, 0)
        lbl = icon_text(complexType.icon(), complexType.display_name())
        wdg.layout().addWidget(group(lbl, spacer(), toggle))
        wdg.layout().addWidget(label(complexType.description(), description=True, wordWrap=True))

        toggle.setChecked(default)

        toggle.clicked.connect(partial(self._selector.editorToggled.emit, complexType))

        self.centerComplex.layout().addWidget(wdg)


class PlotWidget(QWidget, EventListener):
    titleChanged = pyqtSignal()
    iconChanged = pyqtSignal()
    characterChanged = pyqtSignal()
    removalRequested = pyqtSignal()

    def __init__(self, novel: Novel, plot: Plot, parent=None):
        super(PlotWidget, self).__init__(parent)
        self.novel = novel
        self.plot: Plot = plot
        self._principles: Dict[PlotPrincipleType, PlotPrincipleEditor] = {}

        vbox(self, 10)

        self._alliesEditor: Optional[AlliesPrinciplesGroupWidget] = None
        self._timelineEditor: Optional[StorylineTimelineWidget] = None
        self._villainEditor: Optional[StorylineVillainEvolutionWidget] = None
        self._suspectsEditor: Optional[DynamicPlotPrinciplesWidget] = None
        self._castEditor: Optional[DynamicPlotPrinciplesWidget] = None

        self.btnPlotIcon = tool_btn(QIcon(), transparent_=True)
        self.btnPlotIcon.setIconSize(QSize(48, 48))
        self.btnPlotIcon.installEventFilter(OpacityEventFilter(self.btnPlotIcon, enterOpacity=0.7, leaveOpacity=1.0))
        self._updateIcon()

        self.lineName = AutoAdjustableLineEdit()
        transparent(self.lineName)
        incr_font(self.lineName, 6)
        self.lineName.setText(self.plot.text)
        self.lineName.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lineName.textChanged.connect(self._nameEdited)

        iconMenu = MenuWidget(self.btnPlotIcon)
        colorPicker = ColorPicker(self)
        colorPicker.setFixedSize(300, 150)
        colorPicker.colorPicked.connect(self._colorChanged)
        colorMenu = MenuWidget()
        colorMenu.setTitle('Color')
        colorMenu.setIcon(IconRegistry.from_name('fa5s.palette'))
        colorMenu.addWidget(colorPicker)
        iconMenu.addMenu(colorMenu)
        iconMenu.addSeparator()
        iconMenu.addAction(
            action('Change icon', icon=IconRegistry.icons_icon(), slot=self._changeIcon, parent=iconMenu))

        self._divider = SeparatorLineWithShadow(color=self.plot.icon_color)

        # self.btnSettings = DotsMenuButton(self)
        # contextMenu = MenuWidget(self.btnSettings)
        # contextMenu.addAction(action('Remove plot', IconRegistry.trash_can_icon(), self.removalRequested.emit))
        self.btnEditElements = tool_btn(IconRegistry.plus_edit_icon('grey'), 'Edit elements', transparent_=True,
                                        parent=self)
        self.btnEditElements.setIconSize(QSize(32, 32))
        self.btnEditElements.installEventFilter(OpacityEventFilter(self.btnEditElements, leaveOpacity=0.7))
        incr_icon(self.btnEditElements, 2)
        self.installEventFilter(VisibilityToggleEventFilter(target=self.btnEditElements, parent=self))
        self.btnEditElements.clicked.connect(self._editElements)

        self.btnInit = push_btn(IconRegistry.plus_edit_icon(RELAXED_WHITE_COLOR), 'Initialize elements',
                                properties=['confirm', 'positive'])
        incr_icon(self.btnInit, 2)
        incr_font(self.btnInit)
        self.btnInit.clicked.connect(self._editElements)

        self._characterSelector = CharacterAvatar(self, 88, 120, 92, 8)
        menu = CharacterSelectorMenu(self.novel, self._characterSelector.btnAvatar)
        menu.selected.connect(self._characterSelected)
        self._characterSelector.setToolTip('Link character to this storyline')
        self._characterSelector.setGeometry(4, 4, 115, 115)

        if self.plot.character_id:
            character = entities_registry.character(str(self.plot.character_id))
            if character:
                self._characterSelector.setCharacter(character)

        if self.plot.plot_type == PlotType.Global or self.plot.plot_type == PlotType.Relation:
            self._characterSelector.setHidden(True)

        self.wdgNavs = columns(0)
        margins(self.wdgNavs, top=10)
        self.btnPrinciples = push_btn(
            IconRegistry.from_name('mdi6.note-text-outline', 'grey', PLOTLYST_SECONDARY_COLOR), text='Principles',
            properties=['secondary-selector', 'transparent'], checkable=True)
        self.btnPrinciples.installEventFilter(
            OpacityEventFilter(self.btnPrinciples, leaveOpacity=0.7, ignoreCheckedButton=True))
        self.btnTimeline = push_btn(
            IconRegistry.from_name('mdi.timeline-text-outline', 'grey', PLOTLYST_SECONDARY_COLOR), text='Timeline',
            properties=['secondary-selector', 'transparent'], checkable=True)
        self.btnTimeline.installEventFilter(
            OpacityEventFilter(self.btnTimeline, leaveOpacity=0.7, ignoreCheckedButton=True))
        self.btnEscalation = push_btn(
            IconRegistry.from_name('ph.shuffle-bold', 'grey', PLOTLYST_SECONDARY_COLOR), text='Escalation',
            properties=['secondary-selector', 'transparent'], checkable=True)
        self.btnEscalation.installEventFilter(
            OpacityEventFilter(self.btnEscalation, leaveOpacity=0.7, ignoreCheckedButton=True))
        self.btnAllies = push_btn(
            IconRegistry.from_name(DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES.icon(), 'grey',
                                   PLOTLYST_SECONDARY_COLOR), text='Allies',
            properties=['secondary-selector', 'transparent'], checkable=True)
        self.btnAllies.installEventFilter(
            OpacityEventFilter(self.btnAllies, leaveOpacity=0.7, ignoreCheckedButton=True))
        self.btnSuspects = push_btn(
            IconRegistry.from_name(DynamicPlotPrincipleGroupType.SUSPECTS.icon(), 'grey',
                                   PLOTLYST_SECONDARY_COLOR), text='Suspects',
            properties=['secondary-selector', 'transparent'], checkable=True)
        self.btnSuspects.installEventFilter(
            OpacityEventFilter(self.btnSuspects, leaveOpacity=0.7, ignoreCheckedButton=True))
        self.btnCast = push_btn(
            IconRegistry.from_name(DynamicPlotPrincipleGroupType.CAST.icon(), 'grey',
                                   PLOTLYST_SECONDARY_COLOR), text='Cast',
            properties=['secondary-selector', 'transparent'], checkable=True)
        self.btnCast.installEventFilter(
            OpacityEventFilter(self.btnCast, leaveOpacity=0.7, ignoreCheckedButton=True))
        self.btnMonster = push_btn(
            IconRegistry.from_name(DynamicPlotPrincipleGroupType.EVOLUTION_OF_THE_MONSTER.icon(), 'grey',
                                   PLOTLYST_SECONDARY_COLOR), text='Monster',
            properties=['secondary-selector', 'transparent'], checkable=True)
        self.btnMonster.installEventFilter(
            OpacityEventFilter(self.btnMonster, leaveOpacity=0.7, ignoreCheckedButton=True))

        self.wdgNavs.layout().addWidget(self.btnPrinciples)
        self.wdgNavs.layout().addWidget(self.btnTimeline)
        self.wdgNavs.layout().addWidget(self.btnEscalation)
        self.wdgNavs.layout().addWidget(self.btnAllies)
        self.wdgNavs.layout().addWidget(self.btnSuspects)
        self.wdgNavs.layout().addWidget(self.btnCast)
        self.wdgNavs.layout().addWidget(self.btnMonster)
        self.btnTimeline.setVisible(self.plot.has_progression)
        self.btnEscalation.setVisible(self.plot.has_escalation)
        self.btnAllies.setVisible(self.plot.has_allies)
        self.btnSuspects.setVisible(self.plot.has_suspects)
        self.btnCast.setVisible(self.plot.has_cast)
        self.btnMonster.setVisible(self.plot.has_villain)
        self._navWidth: int = self.wdgNavs.sizeHint().width()

        self.btnGroup = QButtonGroup(self)
        self.btnGroup.addButton(self.btnPrinciples)
        self.btnGroup.addButton(self.btnTimeline)
        self.btnGroup.addButton(self.btnEscalation)
        self.btnGroup.addButton(self.btnAllies)
        self.btnGroup.addButton(self.btnSuspects)
        self.btnGroup.addButton(self.btnCast)
        self.btnGroup.addButton(self.btnMonster)
        self.btnPrinciples.setChecked(True)

        self.stack = QStackedWidget(self)
        self.pagePrinciples, self.wdgPrinciples = self.__page(LayoutType.FLOW)
        self.pageTimeline, self.wdgTimeline = self.__page()
        self.pageEscalation, self.wdgEscalation = self.__page()
        self.pageAllies, self.wdgAllies = self.__page()
        margins(self.wdgAllies, left=5, right=5)
        self.pageSuspects, self.wdgSuspects = self.__page()
        self.pageCast, self.wdgCast = self.__page()
        self.pageMonster, self.wdgMonster = self.__page()
        self.wdgMonster.installEventFilter(self)

        link_buttons_to_pages(self.stack, [(self.btnPrinciples, self.pagePrinciples),
                                           (self.btnTimeline, self.pageTimeline),
                                           (self.btnEscalation, self.pageEscalation),
                                           (self.btnAllies, self.pageAllies),
                                           (self.btnSuspects, self.pageSuspects),
                                           (self.btnCast, self.pageCast),
                                           (self.btnMonster, self.pageMonster),
                                           ])

        self.layout().addWidget(self.btnPlotIcon, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.lineName, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.wdgNavs, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._divider)
        self.layout().addWidget(self.btnInit, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.stack)

        for principle in self.plot.principles:
            self._initPrincipleEditor(principle)

        self.repo = RepositoryPersistenceManager.instance()

        dispatcher = event_dispatchers.instance(self.novel)
        dispatcher.register(self, CharacterChangedEvent, CharacterDeletedEvent)

        if self.plot.has_allies:
            self._addGroup(DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES)
        if self.plot.has_progression:
            self._addGroup(DynamicPlotPrincipleGroupType.TIMELINE)
        if self.plot.has_escalation:
            self._addGroup(DynamicPlotPrincipleGroupType.ESCALATION)
        if self.plot.has_villain:
            self._addGroup(DynamicPlotPrincipleGroupType.EVOLUTION_OF_THE_MONSTER)
        if self.plot.has_suspects:
            self._addGroup(DynamicPlotPrincipleGroupType.SUSPECTS)
        if self.plot.has_cast:
            self._addGroup(DynamicPlotPrincipleGroupType.CAST)

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.btnEditElements.setGeometry(self.width() - self.btnEditElements.sizeHint().width() - 10, 10,
                                         self.btnEditElements.sizeHint().width(),
                                         self.btnEditElements.sizeHint().height())

        self.__updateNavLayout()

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.wdgMonster and isinstance(event, QPaintEvent):
            painter = QPainter(self.wdgMonster)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            rect: QRectF = self.wdgMonster.rect().toRectF()
            corner_radius = 12

            path = QPainterPath()
            path.addRoundedRect(rect, corner_radius, corner_radius)

            center = rect.center()
            radius = max(rect.width(), rect.height()) / 2
            gradient = QRadialGradient(center, radius)

            gradient.setColorAt(0.0, QColor('#872210'))
            gradient.setColorAt(0.5, QColor(antagonist_role.icon_color))
            gradient.setColorAt(1.0, QColor("#FAB2A5"))

            painter.fillPath(path, gradient)

            IconRegistry.from_name('ri.ghost-2-fill').paint(
                painter, self.wdgMonster.rect(), alignment=Qt.AlignmentFlag.AlignCenter
            )

        return super().eventFilter(watched, event)

    @overrides
    def event_received(self, event: Event):
        if self.plot.plot_type == PlotType.Global:
            pass
        elif isinstance(event, CharacterDeletedEvent):
            if self._characterSelector.character() and self._characterSelector.character().id == event.character.id:
                self._characterSelector.reset()
            # if self._characterRelationSelector and self._characterRelationSelector.character() and self._characterRelationSelector.character().id == event.character.id:
            #     self._characterRelationSelector.reset()
        elif isinstance(event, CharacterChangedEvent):
            if self._characterSelector.character() and self._characterSelector.character().id == event.character.id:
                self._characterSelector.updateAvatar()
            # if self._characterRelationSelector and self._characterRelationSelector.character() and self._characterRelationSelector.character().id == event.character.id:
            #     self._characterRelationSelector.updateAvatar()

        if self._alliesEditor:
            self._alliesEditor.refreshCharacters()
        if self._suspectsEditor:
            self._suspectsEditor.refreshCharacters()
        if self._castEditor:
            self._castEditor.refreshCharacters()

    def _updateIcon(self):
        if self.plot.icon:
            self.btnPlotIcon.setIcon(IconRegistry.from_name(self.plot.icon, self.plot.icon_color))

    def _nameEdited(self, name: str):
        self.plot.text = name
        self._save()
        self.titleChanged.emit()

    def _characterSelected(self, character: Character):
        self._characterSelector.setCharacter(character)
        self.plot.set_character(character)
        self._save()
        self.characterChanged.emit()

    def _relationCharacterSelected(self, character: Character):
        self._characterRelationSelector.setCharacter(character)
        self.plot.set_relation_character(character)
        self._save()

    def _changeIcon(self):
        result = IconSelectorDialog.popup(pickColor=False, color=QColor(self.plot.icon_color))
        if result:
            self.plot.icon = result[0]

    def _colorChanged(self, color: QColor):
        self.plot.icon_color = color.name()
        self._divider.setColor(self.plot.icon_color)
        self._updateIcon()
        self._save()
        self.iconChanged.emit()

    def _editElements(self):
        object = PrincipleSelectorObject()
        object.principleToggled.connect(self._principleToggled)
        object.editorToggled.connect(self._editorToggled)
        PlotElementSelectorPopup.popup(self.plot, object)

    def _principleToggled(self, principleType: PlotPrincipleType, toggled: bool):
        self.btnInit.setHidden(True)
        if toggled:
            principle = PlotPrinciple(principleType)
            self._initPrincipleEditor(principle)
            self.plot.principles.append(principle)
        else:
            principle = next((_principle for _principle in self.plot.principles if _principle.type == principleType),
                             None)
            if principle:
                self.plot.principles.remove(principle)
                wdg = self._principles.pop(principle.type)
                fade_out_and_gc(self.wdgPrinciples, wdg)

        self._save()

    def _editorToggled(self, editorType: DynamicPlotPrincipleGroupType, toggled: bool):
        self.btnInit.setHidden(True)
        if editorType == DynamicPlotPrincipleGroupType.TIMELINE:
            self.plot.has_progression = toggled
            btn = self.btnTimeline
            page = self.pageTimeline
        elif editorType == DynamicPlotPrincipleGroupType.ESCALATION:
            self.plot.has_escalation = toggled
            btn = self.btnEscalation
            page = self.pageEscalation
        elif editorType == DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES:
            self.plot.has_allies = toggled
            btn = self.btnAllies
            page = self.pageAllies
        elif editorType == DynamicPlotPrincipleGroupType.SUSPECTS:
            self.plot.has_suspects = toggled
            btn = self.btnSuspects
            page = self.pageSuspects
        elif editorType == DynamicPlotPrincipleGroupType.CAST:
            self.plot.has_cast = toggled
            btn = self.btnCast
            page = self.pageCast
        elif editorType == DynamicPlotPrincipleGroupType.EVOLUTION_OF_THE_MONSTER:
            self.plot.has_villain = toggled
            btn = self.btnMonster
            page = self.pageMonster
        else:
            return

        btn.setVisible(toggled)
        if toggled:
            self._addGroup(editorType)
            btn.setChecked(True)
        else:
            self._clearGroup(editorType)
            if self.stack.currentWidget() is page:
                self.btnPrinciples.setChecked(True)

        self._navWidth = self.wdgNavs.sizeHint().width()
        self.__updateNavLayout()

    def _initPrincipleEditor(self, principle: PlotPrinciple):
        self.btnInit.setHidden(True)
        editor = PlotPrincipleEditor(principle, self.plot.plot_type)
        editor.principleEdited.connect(self._save)
        # self.wdgPrinciples.layout().insertWidget(principle_type_index[principle.type], editor)
        index = principle_type_index.get(principle.type, principle.type.value)
        self.wdgPrinciples.layout().insertWidget(index, editor)
        self._principles[principle.type] = editor

        return editor

    def _addGroup(self, groupType: DynamicPlotPrincipleGroupType):
        self.btnInit.setHidden(True)
        if groupType == DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES:
            if self.plot.allies is None:
                self.plot.allies = DynamicPlotPrincipleGroup(groupType)
                self._save()
            self._alliesEditor = AlliesPrinciplesGroupWidget(self.novel, self.plot.allies)
            self._alliesEditor.changed.connect(self._save)
            self.wdgAllies.layout().addWidget(self._alliesEditor)
        if groupType == DynamicPlotPrincipleGroupType.TIMELINE:
            if not self.plot.timeline:
                self.plot.timeline.append(BackstoryEvent('', ''))
                self._save()
            self._timelineEditor = StorylineTimelineWidget(self.plot)
            self._timelineEditor.refresh()
            self._timelineEditor.changed.connect(self._save)
            self._timelineEditor.addedToTheEnd.connect(lambda: scroll_to_bottom(self.pageTimeline))
            self.wdgTimeline.layout().addWidget(self._timelineEditor)
        if groupType == DynamicPlotPrincipleGroupType.EVOLUTION_OF_THE_MONSTER:
            if not self.plot.villain:
                self.plot.villain.append(BackstoryEvent('', '', position=Position.CENTER))
                self._save()
            self._villainEditor = StorylineVillainEvolutionWidget(self.plot)
            self._villainEditor.refresh()
            self._villainEditor.changed.connect(self._save)
            self._villainEditor.addedToTheEnd.connect(lambda: scroll_to_bottom(self.pageMonster))
            self.wdgMonster.layout().addWidget(self._villainEditor)
        if groupType == DynamicPlotPrincipleGroupType.SUSPECTS:
            if self.plot.suspects is None:
                self.plot.suspects = DynamicPlotPrincipleGroup(groupType)
                self._save()
            self._suspectsEditor = DynamicPlotPrinciplesWidget(self.novel, self.plot.suspects)
            self._suspectsEditor.timelineChanged.connect(self._save)
            self.wdgSuspects.layout().addWidget(self._suspectsEditor)
            self._suspectsEditor.setStructure(self.plot.suspects.principles)
        if groupType == DynamicPlotPrincipleGroupType.CAST:
            if self.plot.cast is None:
                self.plot.cast = DynamicPlotPrincipleGroup(groupType)
                self._save()
            self._castEditor = DynamicPlotPrinciplesWidget(self.novel, self.plot.cast)
            self._castEditor.timelineChanged.connect(self._save)
            self.wdgCast.layout().addWidget(self._castEditor)
            self._castEditor.setStructure(self.plot.cast.principles)
        if groupType == DynamicPlotPrincipleGroupType.ESCALATION:
            if self.plot.escalation is None:
                self.plot.escalation = DynamicPlotPrincipleGroup(groupType)
                self._save()
            self._escalationEditor = StorylineEscalationEditorWidget(self.novel, self.plot)
            self._escalationEditor.changed.connect(self._save)
            self.wdgEscalation.layout().addWidget(self._escalationEditor)

    def _clearGroup(self, groupType: DynamicPlotPrincipleGroupType):
        if groupType == DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES:
            clear_layout(self.wdgAllies)
            self._alliesEditor = None
        elif groupType == DynamicPlotPrincipleGroupType.TIMELINE:
            clear_layout(self.wdgTimeline)
            self._timelineEditor = None
        elif groupType == DynamicPlotPrincipleGroupType.ESCALATION:
            clear_layout(self.wdgEscalation)
            self._escalationEditor = None
        elif groupType == DynamicPlotPrincipleGroupType.EVOLUTION_OF_THE_MONSTER:
            clear_layout(self.wdgMonster)
            self._villainEditor = None
        elif groupType == DynamicPlotPrincipleGroupType.SUSPECTS:
            clear_layout(self.wdgSuspects)
            self._suspectsEditor = None
        elif groupType == DynamicPlotPrincipleGroupType.CAST:
            clear_layout(self.wdgCast)
            self._castEditor = None

    def _save(self):
        self.repo.update_novel(self.novel)

    def __page(self, layoutType: LayoutType = LayoutType.VERTICAL) -> Tuple[QScrollArea, QWidget]:
        scroll_ = scroll_area(frameless=True)
        wdg = QWidget()
        if layoutType == LayoutType.VERTICAL:
            vbox(wdg)
        elif layoutType == LayoutType.FLOW:
            flow(wdg, spacing=6)
        scroll_.setWidget(wdg)
        wdg.setProperty('relaxed-white-bg', True)

        margins(wdg, left=20, right=20, top=5)

        self.stack.addWidget(scroll_)

        return scroll_, wdg

    def __updateNavLayout(self):
        if self.width() <= self.wdgNavs.width() + 25:
            self.btnPrinciples.setText('')
            self.btnTimeline.setText('')
            self.btnSuspects.setText('')
            self.btnAllies.setText('')
            self.btnCast.setText('')
            self.btnMonster.setText('')
        elif self.width() > self._navWidth + 25 and self.btnPrinciples.text() == '':
            self.btnPrinciples.setText('Principles')
            self.btnTimeline.setText('Timeline')
            self.btnSuspects.setText('Suspects')
            self.btnAllies.setText('Allies')
            self.btnCast.setText('Cast')
            self.btnMonster.setText('Monster')


class PlotEditor(QWidget, Ui_PlotEditor):
    def __init__(self, novel: Novel, parent=None):
        super(PlotEditor, self).__init__(parent)
        self.setupUi(self)
        self.novel = novel

        self._wdgList = PlotTreeView(self.novel)
        self.wdgPlotListParent.layout().addWidget(self._wdgList)
        self._wdgList.plotSelected.connect(self._plotSelected)
        self._wdgList.plotRemoved.connect(self._plotRemoved)
        self._wdgList.impactGridSelected.connect(self._displayImpactMatrix)
        self.stack.setCurrentWidget(self.pageDisplay)

        self.wdgEditor = frame()
        vbox(self.wdgEditor, 0, 0)
        self.wdgEditor.setProperty('relaxed-white-bg', True)
        self.wdgEditor.setProperty('large-rounded', True)
        self.wdgEditor.setMaximumWidth(1000)
        self.pageDisplay.layout().addWidget(self.wdgEditor)

        self._wdgImpactMatrix = StorylinesImpactMatrix(self.novel)
        self.scrollMatrix.layout().addWidget(self._wdgImpactMatrix)

        self.splitter.setSizes([150, 550])

        italic(self.btnAdd)
        self.btnAdd.setIcon(IconRegistry.plus_icon('white'))

        menu = MenuWidget(self.btnAdd, largeIcons=True)
        menu.setTooltipDisplayMode(ActionTooltipDisplayMode.DISPLAY_UNDER)
        menu.addAction(
            action('Main plot', IconRegistry.storylines_icon(), slot=lambda: self.newPlot(PlotType.Main),
                   tooltip="The central storyline that drives the narrative", incr_font_=1))
        menu.addAction(
            action('Character arc', IconRegistry.conflict_self_icon(), lambda: self.newPlot(PlotType.Internal),
                   tooltip="The transformation or personal growth of a character", incr_font_=1))
        menu.addAction(
            action('Subplot', IconRegistry.subplot_icon(), lambda: self.newPlot(PlotType.Subplot),
                   tooltip="A secondary storyline to complement the main plot", incr_font_=1))
        menu.addSeparator()
        menu.addAction(action('Relationship plot', IconRegistry.from_name('fa5s.people-arrows'),
                              slot=lambda: self.newPlot(PlotType.Relation),
                              tooltip="Relationship dynamics between two or more characters", incr_font_=1))
        menu.addAction(action('Global storyline', IconRegistry.from_name('fa5s.globe'),
                              slot=lambda: self.newPlot(PlotType.Global),
                              tooltip="A broader storyline that can encompass multiple storylines without serving as the central plot itself",
                              incr_font_=1))
        apply_white_menu(menu)

        self.repo = RepositoryPersistenceManager.instance()

        if self.novel.plots:
            self._wdgList.selectPlot(self.novel.plots[0])

    def widgetList(self) -> PlotTreeView:
        return self._wdgList

    def newPlot(self, plot_type: PlotType):
        if plot_type == PlotType.Internal:
            name = 'Character arc'
            icon = 'mdi.mirror'
        elif plot_type == PlotType.Subplot:
            name = 'Subplot'
            icon = 'mdi.source-branch'
        elif plot_type == PlotType.Relation:
            name = 'Relationship'
            icon = 'fa5s.people-arrows'
        elif plot_type == PlotType.Global:
            name = 'Global storyline'
            icon = 'fa5s.globe'
        else:
            name = 'Main plot'
            icon = 'fa5s.theater-masks'
        plot = Plot(name, plot_type=plot_type, icon=icon,
                    progression=[PlotProgressionItem(type=PlotProgressionItemType.BEGINNING),
                                 PlotProgressionItem(type=PlotProgressionItemType.MIDDLE),
                                 PlotProgressionItem(type=PlotProgressionItemType.ENDING)])
        self.novel.plots.append(plot)

        plot_colors = list(STORY_LINE_COLOR_CODES[plot_type.value])
        for plot in self.novel.plots:
            if plot.plot_type == plot_type and plot.icon_color in plot_colors:
                plot_colors.remove(plot.icon_color)
        if plot_colors:
            plot.icon_color = plot_colors[0]
        else:
            plot_colors = STORY_LINE_COLOR_CODES[plot_type.value]
            number_of_plots = len([x for x in self.novel.plots if x.plot_type == plot_type])
            plot.icon_color = plot_colors[(number_of_plots - 1) % len(plot_colors)]

        self._wdgList.addPlot(plot)
        self.repo.update_novel(self.novel)
        self._wdgList.selectPlot(plot)
        self._wdgImpactMatrix.refresh()

        emit_event(self.novel, StorylineCreatedEvent(self, plot))

    def _plotSelected(self, plot: Plot) -> PlotWidget:
        self.stack.setCurrentWidget(self.pageDisplay)

        widget = PlotWidget(self.novel, plot, self.pageDisplay)
        widget.removalRequested.connect(partial(self._remove, widget))
        widget.titleChanged.connect(partial(self._plotChanged, widget.plot))
        widget.iconChanged.connect(partial(self._plotChanged, widget.plot))
        widget.characterChanged.connect(self._wdgList.refreshCharacters)

        clear_layout(self.wdgEditor)
        self.wdgEditor.layout().addWidget(widget)

        return widget

    def _plotChanged(self, plot: Plot):
        self._wdgList.refreshPlot(plot)
        emit_event(self.novel, StorylineChangedEvent(self, plot), delay=20)

    def _remove(self, wdg: PlotWidget):
        self._wdgList.removePlot(wdg.plot)

    def _plotRemoved(self, plot: Plot):
        if self.wdgEditor.layout().count():
            item = self.wdgEditor.layout().itemAt(0)
            if item.widget() and isinstance(item.widget(), PlotWidget):
                if item.widget().plot == plot:
                    clear_layout(self.wdgEditor)
        delete_plot(self.novel, plot)

        self._wdgImpactMatrix.refresh()
        emit_event(self.novel, StorylineRemovedEvent(self, plot))

    @busy
    def _displayImpactMatrix(self):
        self.stack.setCurrentWidget(self.pageMatrix)
