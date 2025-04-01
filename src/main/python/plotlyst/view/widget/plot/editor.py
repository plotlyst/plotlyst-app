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
from typing import Set, Dict

import qtanim
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QTimer
from PyQt6.QtGui import QColor, QCursor, QIcon
from PyQt6.QtWidgets import QWidget
from overrides import overrides
from qthandy import flow, incr_font, \
    margins, italic, clear_layout, vspacer, sp, pointy, vbox, transparent
from qthandy.filter import OpacityEventFilter
from qtmenu import MenuWidget, ActionTooltipDisplayMode

from plotlyst.core.domain import Novel, Plot, PlotValue, PlotType, Character, PlotPrinciple, \
    PlotPrincipleType, PlotProgressionItem, \
    PlotProgressionItemType, DynamicPlotPrincipleGroupType
from plotlyst.env import app_env
from plotlyst.event.core import EventListener, Event, emit_event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import CharacterChangedEvent, CharacterDeletedEvent, StorylineCreatedEvent, \
    StorylineRemovedEvent, StorylineCharacterAssociationChanged, StorylineChangedEvent
from plotlyst.service.persistence import RepositoryPersistenceManager, delete_plot
from plotlyst.settings import STORY_LINE_COLOR_CODES
from plotlyst.view.common import action, fade_out_and_gc, insert_before_the_end, label, frame, tool_btn
from plotlyst.view.dialog.novel import PlotValueEditorDialog
from plotlyst.view.generated.plot_editor_widget_ui import Ui_PlotEditor
from plotlyst.view.icons import IconRegistry, avatars
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.widget.confirm import confirmed
from plotlyst.view.widget.display import SeparatorLineWithShadow
from plotlyst.view.widget.input import AutoAdjustableLineEdit
from plotlyst.view.widget.labels import PlotValueLabel
from plotlyst.view.widget.plot.matrix import StorylinesImpactMatrix
from plotlyst.view.widget.plot.principle import PlotPrincipleEditor, \
    PrincipleSelectorObject, GenrePrincipleSelectorDialog, principle_type_index
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


class PlotTreeView(TreeView, EventListener):
    plotSelected = pyqtSignal(Plot)
    plotRemoved = pyqtSignal(Plot)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._plots: Dict[Plot, PlotNode] = {}
        self._characterNodes: Dict[Character, ContainerNode] = {}
        self._selectedPlots: Set[Plot] = set()

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
                self._characterNodes[character] = ContainerNode(character.name, avatars.avatar(character),
                                                                readOnly=True)
                self._centralWidget.layout().addWidget(self._characterNodes[character])

        for plot in self._novel.plots:
            wdg = self.__initPlotWidget(plot)
            if plot.character_id and self._characterNodes:
                character = plot.character(self._novel)
                self._characterNodes[character].addChild(wdg)
            else:
                self._centralWidget.layout().addWidget(wdg)

        self._centralWidget.layout().addWidget(vspacer())

    def refreshPlot(self, plot: Plot):
        self._plots[plot].refresh()

    def refreshCharacters(self):
        self.refresh()

    def addPlot(self, plot: Plot):
        wdg = self.__initPlotWidget(plot)
        self._centralWidget.layout().insertWidget(self._centralWidget.layout().count() - 1, wdg)

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
            self._selectedPlots.add(wdg.plot())
            QTimer.singleShot(10, lambda: self.plotSelected.emit(wdg.plot()))
        elif wdg.plot() in self._selectedPlots:
            self._selectedPlots.remove(wdg.plot())

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

        vbox(self, 0)

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

        self.wdgPrinciples = QWidget()
        flow(self.wdgPrinciples, spacing=6)
        margins(self.wdgPrinciples, left=30)
        for principle in self.plot.principles:
            self._initPrincipleEditor(principle)

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

        self.layout().addWidget(self.btnPlotIcon, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.lineName, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._divider)
        self.layout().addWidget(self.wdgPrinciples)

        self.repo = RepositoryPersistenceManager.instance()

        dispatcher = event_dispatchers.instance(self.novel)
        dispatcher.register(self, CharacterChangedEvent, CharacterDeletedEvent)

        # self.btnPrincipleEditor.setIcon(IconRegistry.plus_edit_icon('grey'))
        # transparent(self.btnPrincipleEditor)
        # retain_when_hidden(self.btnPrincipleEditor)
        # decr_icon(self.btnPrincipleEditor)

        # self._principleSelectorMenu = PlotPrincipleSelectorMenu(self.plot, self.btnPrincipleEditor)
        # self._principleSelectorMenu.principleToggled.connect(self._principleToggled)
        # self._principleSelectorMenu.progressionToggled.connect(self._progressionToggled)
        # self._principleSelectorMenu.dynamicPrinciplesToggled.connect(self._dynamicPrinciplesToggled)
        # self._principleSelectorMenu.genresSelected.connect(self._genresSelected)
        # self.btnPrincipleEditor.installEventFilter(ButtonPressResizeEventFilter(self.btnPrincipleEditor))
        # self.btnPrincipleEditor.installEventFilter(OpacityEventFilter(self.btnPrincipleEditor, leaveOpacity=0.7))

        # self._dynamicPrincipleSelectorMenu = PlotDynamicPrincipleSelectorMenu(self.btnDynamicPrincipleEditor)
        # self.btnDynamicPrincipleEditor.setIcon(IconRegistry.plus_icon('grey'))
        # transparent(self.btnDynamicPrincipleEditor)
        # retain_when_hidden(self.btnDynamicPrincipleEditor)
        # decr_icon(self.btnDynamicPrincipleEditor)
        # self.btnDynamicPrincipleEditor.installEventFilter(ButtonPressResizeEventFilter(self.btnDynamicPrincipleEditor))
        # self.btnDynamicPrincipleEditor.installEventFilter(
        #     OpacityEventFilter(self.btnDynamicPrincipleEditor, leaveOpacity=0.7))

        # self._dynamicPrinciplesEditor = DynamicPlotPrinciplesEditor(self.novel, self.plot)
        # margins(self._dynamicPrinciplesEditor, left=40, right=40)
        # self.wdgDynamicPrinciples.layout().addWidget(self._dynamicPrinciplesEditor)
        # self._dynamicPrincipleSelectorMenu.triggered.connect(self._addDynamicGroup)

        # self.btnPrinciples.setIcon(IconRegistry.from_name('mdi6.note-text-outline', 'grey'))
        # incr_icon(self.btnPrinciples, 2)
        # incr_font(self.btnPrinciples, 2)
        # self.btnPrinciples.installEventFilter(ButtonPressResizeEventFilter(self.btnPrinciples))
        # self.btnPrinciples.installEventFilter(OpacityEventFilter(self.btnPrinciples, leaveOpacity=0.7))
        # self.btnPrinciples.clicked.connect(lambda: self._principleSelectorMenu.exec())

        # self.btnDynamicPrinciples.setIcon(IconRegistry.from_name('mdi6.chart-timeline-variant-shimmer', 'grey'))
        # self.btnProgression.setIcon(IconRegistry.rising_action_icon('grey'))
        # if self.plot.plot_type == PlotType.Internal:
        #     self.btnProgression.setText('Transformation')
        # elif self.plot.plot_type == PlotType.Relation:
        #     self.btnProgression.setText('Evolution')

        # for btn in [self.btnProgression, self.btnDynamicPrinciples]:
        #     translucent(btn, 0.7)
        #     incr_icon(btn)
        #     incr_font(btn)
        # self.btnDynamicPrinciples.clicked.connect(lambda: self._dynamicPrincipleSelectorMenu.exec())

        # self.btnValues.setText('' if self.plot.values else 'Values')
        # self.btnValues.setIcon(IconRegistry.from_name('fa5s.chevron-circle-down', 'grey'))
        # self.btnValues.installEventFilter(OpacityEventFilter(self.btnValues, 0.9, 0.7))
        # self.btnValues.clicked.connect(self._newValue)
        # hbox(self.wdgValues)
        # self._btnAddValue = SecondaryActionPushButton(self)
        # self._btnAddValue.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        # decr_font(self._btnAddValue)
        # self._btnAddValue.setIconSize(QSize(14, 14))
        # retain_when_hidden(self._btnAddValue)
        # self._btnAddValue.setIcon(IconRegistry.plus_icon('grey'))
        # for value in self.plot.values:
        #     self._addValue(value)

        # self.btnRelationArrow.setHidden(True)
        # self._characterRelationSelector: Optional[CharacterAvatar] = None
        # if self.plot.plot_type == PlotType.Global:
        #     pass
        # elif self.plot.plot_type == PlotType.Relation:
        #     self.btnRelationArrow.setVisible(True)
        #     self.btnRelationArrow.setIcon(IconRegistry.from_name('ph.arrows-counter-clockwise-fill'))
        #
        #     self._characterSelector = CharacterAvatar(self, 60, 100, 64, 8)
        #     self._characterRelationSelector = CharacterAvatar(self, 60, 100, 64, 8)
        #     self._characterSelector.setToolTip('Associate a character to this relationship plot')
        #     self._characterRelationSelector.setToolTip('Associate a character to this relationship plot')
        #     sourceMenu = CharacterSelectorMenu(self.novel, self._characterSelector.btnAvatar)
        #     sourceMenu.selected.connect(self._characterSelected)
        #     targetMenu = CharacterSelectorMenu(self.novel, self._characterRelationSelector.btnAvatar)
        #     targetMenu.selected.connect(self._relationCharacterSelected)
        #     self._characterSelector.setFixedSize(90, 90)
        #     self._characterRelationSelector.setFixedSize(90, 90)
        #     self.wdgHeader.layout().insertWidget(0, self._characterSelector,
        #                                          alignment=Qt.AlignmentFlag.AlignCenter)
        #     self.wdgHeader.layout().insertWidget(0, spacer())
        #     self.wdgHeader.layout().addWidget(self._characterRelationSelector, alignment=Qt.AlignmentFlag.AlignCenter)
        #     self.wdgHeader.layout().addWidget(spacer())
        #
        #     character = self.plot.character(novel)
        #     if character is not None:
        #         self._characterSelector.setCharacter(character)
        #     character = self.plot.relation_character(novel)
        #     if character is not None:
        #         self._characterRelationSelector.setCharacter(character)
        # else:
        #     self._characterSelector = CharacterAvatar(self, 88, 120, 92, 8)
        #     menu = CharacterSelectorMenu(self.novel, self._characterSelector.btnAvatar)
        #     menu.selected.connect(self._characterSelected)
        #     self._characterSelector.setToolTip('Link character to this storyline')
        #     self._characterSelector.setGeometry(20, 20, 115, 115)
        #     character = self.plot.character(novel)
        #     if character is not None:
        #         self._characterSelector.setCharacter(character)

        # self.wdgValues.layout().addWidget(self._btnAddValue)
        # self.wdgValues.layout().addWidget(spacer())
        # self._btnAddValue.clicked.connect(self._newValue)

        # self.installEventFilter(VisibilityToggleEventFilter(target=self.btnSettings, parent=self))
        # self.installEventFilter(VisibilityToggleEventFilter(target=self._btnAddValue, parent=self))
        # self.installEventFilter(VisibilityToggleEventFilter(target=self.btnPrincipleEditor, parent=self))
        # self.installEventFilter(VisibilityToggleEventFilter(target=self.btnDynamicPrincipleEditor, parent=self))

        # self._timeline = PlotEventsTimeline(self.novel, self.plot.plot_type)
        # self.wdgEventsParent.layout().addWidget(self._timeline)
        # self._timeline.setStructure(self.plot.progression)
        # self._timeline.timelineChanged.connect(self._timelineChanged)

        # self.wdgProgression.setVisible(self.plot.has_progression)
        # self.wdgDynamicPrinciples.setVisible(self.plot.has_dynamic_principles)

        # contextMenu = MenuWidget(self.btnSettings)
        # contextMenu.addAction(action('Remove plot', IconRegistry.trash_can_icon(), self.removalRequested.emit))

    @overrides
    def event_received(self, event: Event):
        if self.plot.plot_type == PlotType.Global:
            pass
        elif isinstance(event, CharacterDeletedEvent):
            if self._characterSelector.character() and self._characterSelector.character().id == event.character.id:
                self._characterSelector.reset()
            if self._characterRelationSelector and self._characterRelationSelector.character() and self._characterRelationSelector.character().id == event.character.id:
                self._characterRelationSelector.reset()
        elif isinstance(event, CharacterChangedEvent):
            if self._characterSelector.character() and self._characterSelector.character().id == event.character.id:
                self._characterSelector.updateAvatar()
            if self._characterRelationSelector and self._characterRelationSelector.character() and self._characterRelationSelector.character().id == event.character.id:
                self._characterRelationSelector.updateAvatar()

        self._dynamicPrinciplesEditor.refreshCharacters()

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
        result = IconSelectorDialog.popup(color=QColor(self.plot.icon_color))
        if result:
            self.plot.icon = result[0]
            self._colorChanged(result[1])

    def _colorChanged(self, color: QColor):
        self.plot.icon_color = color.name()
        self._divider.setColor(self.plot.icon_color)
        self._updateIcon()
        self._save()
        self.iconChanged.emit()

    def _principleToggled(self, principleType: PlotPrincipleType, toggled: bool):
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

        # self._btnAddValue.setVisible(True)
        self.btnSettings.setVisible(True)
        self.btnPrincipleEditor.setVisible(True)

        self._save()

    def _progressionToggled(self, toggled: bool):
        self.plot.has_progression = toggled
        if self.plot.has_progression:
            qtanim.fade_in(self.wdgProgression, teardown=lambda: self.wdgProgression.setGraphicsEffect(None))
        else:
            qtanim.fade_out(self.wdgProgression, teardown=lambda: self.wdgProgression.setGraphicsEffect(None))
        self._save()

    def _dynamicPrinciplesToggled(self, toggled: bool):
        self.plot.has_dynamic_principles = toggled
        if self.plot.has_dynamic_principles:
            qtanim.fade_in(self.wdgDynamicPrinciples,
                           teardown=lambda: self.wdgDynamicPrinciples.setGraphicsEffect(None))
        else:
            qtanim.fade_out(self.wdgDynamicPrinciples,
                            teardown=lambda: self.wdgDynamicPrinciples.setGraphicsEffect(None))
        self._save()

    def _genresSelected(self):
        object = PrincipleSelectorObject()
        object.principleToggled.connect(self._principleToggled)
        GenrePrincipleSelectorDialog.popup(self.plot, object)

    def _addDynamicGroup(self, groupType: DynamicPlotPrincipleGroupType):
        wdg = self._dynamicPrinciplesEditor.addNewGroup(groupType)
        wdg.show()
        self.scrollArea.ensureWidgetVisible(wdg, 50, 150)

    def _initPrincipleEditor(self, principle: PlotPrinciple):
        editor = PlotPrincipleEditor(principle, self.plot.plot_type)
        editor.principleEdited.connect(self._save)
        # self.wdgPrinciples.layout().insertWidget(principle_type_index[principle.type], editor)
        index = principle_type_index.get(principle.type, principle.type.value)
        self.wdgPrinciples.layout().insertWidget(index, editor)
        self._principles[principle.type] = editor

        return editor

    def _save(self):
        self.repo.update_novel(self.novel)

    def _timelineChanged(self):
        self._save()

    def _newValue(self):
        value = PlotValueEditorDialog().display()
        if value:
            self.plot.values.append(value)
            self.wdgValues.layout().removeWidget(self._btnAddValue)
            self._addValue(value)
            self.wdgValues.layout().addWidget(self._btnAddValue)

            self._save()

    def _addValue(self, value: PlotValue):
        label = PlotValueLabel(value, parent=self.wdgValues, simplified=True)
        sp(label).h_max()
        label.installEventFilter(OpacityEventFilter(label, leaveOpacity=0.7))
        pointy(label)
        insert_before_the_end(self.wdgValues, label)
        label.removalRequested.connect(partial(self._removeValue, label))
        label.clicked.connect(partial(self._plotValueClicked, label))

        self.btnValues.setText('')

    def _removeValue(self, label: PlotValueLabel):
        if app_env.test_env():
            self.__destroyValue(label)
        else:
            anim = qtanim.fade_out(label, duration=150, hide_if_finished=False)
            anim.finished.connect(partial(self.__destroyValue, label))

    def _editValue(self, label: PlotValueLabel):
        value = PlotValueEditorDialog().display(label.value)
        if value:
            label.value.text = value.text
            label.value.negative = value.negative
            label.value.icon = value.icon
            label.value.icon_color = value.icon_color
            label.refresh()
            self._save()

    def _plotValueClicked(self, label: PlotValueLabel):
        menu = MenuWidget()
        menu.addAction(action('Edit', IconRegistry.edit_icon(), partial(self._editValue, label)))
        menu.addSeparator()
        menu.addAction(action('Remove', IconRegistry.trash_can_icon(), label.removalRequested.emit))
        menu.exec(QCursor.pos())

    def __destroyValue(self, label: PlotValueLabel):
        self.plot.values.remove(label.value)
        self._save()
        fade_out_and_gc(self.wdgValues, label)
        self.btnValues.setText('' if self.plot.values else 'Values')


class PlotEditor(QWidget, Ui_PlotEditor):
    def __init__(self, novel: Novel, parent=None):
        super(PlotEditor, self).__init__(parent)
        self.setupUi(self)
        self.novel = novel

        self._wdgList = PlotTreeView(self.novel)
        self.wdgPlotListParent.layout().addWidget(self._wdgList)
        self._wdgList.plotSelected.connect(self._plotSelected)
        self._wdgList.plotRemoved.connect(self._plotRemoved)
        self.stack.setCurrentWidget(self.pageDisplay)

        self.wdgEditor = frame()
        vbox(self.wdgEditor, 10, 0)
        self.wdgEditor.setProperty('relaxed-white-bg', True)
        self.wdgEditor.setProperty('large-rounded', True)
        self.wdgEditor.setMaximumWidth(1000)
        self.pageDisplay.layout().addWidget(self.wdgEditor)

        self._wdgImpactMatrix = StorylinesImpactMatrix(self.novel)
        self.scrollMatrix.layout().addWidget(self._wdgImpactMatrix)

        self.splitter.setSizes([150, 550])

        italic(self.btnAdd)
        self.btnAdd.setIcon(IconRegistry.plus_icon('white'))
        # self.btnImpactMatrix.setIcon(IconRegistry.from_name('mdi6.camera-metering-matrix'))
        # self.btnImpactMatrix.clicked.connect(self._displayImpactMatrix)

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
        # self.btnImpactMatrix.setChecked(False)
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
        if self.pageDisplay.layout().count():
            item = self.pageDisplay.layout().itemAt(0)
            if item.widget() and isinstance(item.widget(), PlotWidget):
                if item.widget().plot == plot:
                    clear_layout(self.pageDisplay)
        delete_plot(self.novel, plot)

        self._wdgImpactMatrix.refresh()
        emit_event(self.novel, StorylineRemovedEvent(self, plot))

    def _displayImpactMatrix(self, checked: bool):
        self._wdgList.clearSelection()
        if checked:
            self.stack.setCurrentWidget(self.pageMatrix)
        else:
            self.stack.setCurrentWidget(self.pageDisplay)
