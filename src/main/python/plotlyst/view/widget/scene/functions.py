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
from typing import Optional, Union

import qtanim
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtGui import QColor, QIcon, QEnterEvent
from PyQt6.QtWidgets import QWidget, QAbstractButton, QFrame, QScrollArea
from overrides import overrides
from qthandy import vbox, margins, hbox, pointy, gc, transparent, sp, clear_layout
from qthandy.filter import OpacityEventFilter, ObjectReferenceMimeData
from qtmenu import MenuWidget

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, RED_COLOR
from plotlyst.core.domain import Scene, Novel, StoryElementType, Character, SceneFunction, Plot, ScenePlotReference
from plotlyst.service.cache import entities_registry
from plotlyst.view.common import tool_btn, action, label, fade_out_and_gc, fade_in, frame, scroll_area, \
    columns, rows, h_splitter, v_splitter
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.widget.characters import CharacterSelectorButton
from plotlyst.view.widget.display import Icon
from plotlyst.view.widget.input import TextEditBubbleWidget
from plotlyst.view.widget.list import ListView, ListItemWidget
from plotlyst.view.widget.scene.plot import ScenePlotGeneralProgressEditor, \
    ScenePlotSelectorMenu


class PrimarySceneFunctionWidget(TextEditBubbleWidget):
    def __init__(self, novel: Novel, scene: Scene, function: SceneFunction, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.scene = scene
        self.function = function
        self._removalEnabled = True

        self._textedit.setMinimumSize(165, 100)
        self._textedit.setMaximumSize(190, 110)
        self._textedit.setText(self.function.text)

        margins(self, top=16)

    @overrides
    def _textChanged(self):
        self.function.text = self._textedit.toPlainText()


class _StorylineAssociatedFunctionWidget(PrimarySceneFunctionWidget):
    storylineSelected = pyqtSignal(ScenePlotReference)
    storylineRemoved = pyqtSignal(ScenePlotReference)
    storylineCharged = pyqtSignal()

    def __init__(self, novel: Novel, scene: Scene, function: SceneFunction, parent=None):
        self._plotRef: Optional[ScenePlotReference] = None
        super().__init__(novel, scene, function, parent)
        pointy(self._title)
        self._menu = ScenePlotSelectorMenu(novel, self._title)
        self._menu.plotSelected.connect(self._plotSelected)
        self._menu.setScene(scene)

        self._btnProgress = tool_btn(IconRegistry.from_name('mdi.chevron-double-up', color='grey'),
                                     transparent_=True,
                                     tooltip='Track progress', parent=self)
        self._btnProgress.installEventFilter(OpacityEventFilter(self._btnProgress, leaveOpacity=0.7))
        self._btnProgress.setGeometry(0, 18, 20, 20)
        self._btnProgress.setHidden(True)

        self._progressMenu = MenuWidget(self._btnProgress)
        apply_white_menu(self._progressMenu)

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        super().enterEvent(event)
        if self._plotRef and not self._plotRef.data.charge:
            fade_in(self._btnProgress)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        super().leaveEvent(event)
        if not self._plotRef or not self._plotRef.data.charge and not self._progressMenu.isVisible():
            self._btnProgress.setVisible(False)

    def plot(self) -> Optional[Plot]:
        return next((x for x in self.novel.plots if x.id == self.function.ref), None)

    def setPlot(self, plot: Plot):
        self._plotSelected(plot)

    def plotRef(self) -> ScenePlotReference:
        return self._plotRef

    def setPlotRef(self, ref: ScenePlotReference):
        self._plotRef = ref
        self._setPlotStyle(self._plotRef.plot)
        self._textedit.setText(self._plotRef.data.comment)
        if self._plotRef.data.charge:
            self._btnProgress.setVisible(True)

        editor = ScenePlotGeneralProgressEditor(self._plotRef)
        editor.charged.connect(self._chargeClicked)
        self._progressMenu.clear()
        self._progressMenu.addWidget(editor)

        self._charged()

    @overrides
    def _textChanged(self):
        if self._plotRef:
            self._plotRef.data.comment = self._textedit.toPlainText()
        else:
            super()._textChanged()

    def _chargeClicked(self):
        self._charged()
        if self._plotRef.data.charge:
            self._btnProgress.setVisible(True)
        self.storylineCharged.emit()

    def _charged(self):
        if self._plotRef.data.charge:
            self._btnProgress.setIcon(IconRegistry.charge_icon(self._plotRef.data.charge))
        else:
            self._btnProgress.setIcon(IconRegistry.from_name('mdi.chevron-double-up', color='grey'))

    def _setPlotStyle(self, plot: Plot):
        gc(self._menu)
        self._menu = MenuWidget(self._title)
        self._menu.addAction(
            action('Unlink storyline', IconRegistry.from_name('fa5s.unlink', RED_COLOR), slot=self._plotRemoved))

    def _resetPlotStyle(self):
        pass

    def _storylineParent(self) -> QAbstractButton:
        pass

    def _plotSelected(self, plot: Plot):
        self.function.ref = plot.id
        ref = ScenePlotReference(plot)
        self.scene.plot_values.append(ref)
        self.setPlotRef(ref)
        qtanim.glow(self._storylineParent(), color=QColor(plot.icon_color))
        self.storylineSelected.emit(self._plotRef)

    def _plotRemoved(self):
        self.function.ref = None
        gc(self._menu)
        self._menu = ScenePlotSelectorMenu(self.novel, self._title)
        self._menu.plotSelected.connect(self._plotSelected)
        self._menu.setScene(self.scene)
        self._resetPlotStyle()
        self._btnProgress.setVisible(False)
        self.scene.plot_values.remove(self._plotRef)
        self.storylineRemoved.emit(self._plotRef)
        self._plotRef = None


class PlotPrimarySceneFunctionWidget(_StorylineAssociatedFunctionWidget):
    def __init__(self, novel: Novel, scene: Scene, function: SceneFunction, parent=None):
        super().__init__(novel, scene, function, parent)
        self._textedit.setPlaceholderText("How does the story move forward")
        self._resetPlotStyle()

    @overrides
    def _setPlotStyle(self, plot: Plot):
        super()._setPlotStyle(plot)
        self._title.setIcon(IconRegistry.from_name(plot.icon, plot.icon_color))
        self._title.setText(plot.text)

    @overrides
    def _resetPlotStyle(self):
        self._title.setText('Plot')
        self._title.setIcon(IconRegistry.storylines_icon())

    @overrides
    def _storylineParent(self):
        return self._title


class MysteryPrimarySceneFunctionWidget(PrimarySceneFunctionWidget):
    def __init__(self, novel: Novel, scene: Scene, function: SceneFunction, parent=None):
        super().__init__(novel, scene, function, parent)
        self._title.setIcon(IconRegistry.from_name('ei.question-sign', PLOTLYST_SECONDARY_COLOR))
        self._title.setText('Mystery')
        self._textedit.setPlaceholderText("What mystery is introduced or deepened")


class CharacterPrimarySceneFunctionWidget(PrimarySceneFunctionWidget):
    def __init__(self, novel: Novel, scene: Scene, function: SceneFunction, parent=None):
        super().__init__(novel, scene, function, parent)

        self._title.setIcon(IconRegistry.character_icon())
        self._title.setText('Character insight')
        self._textedit.setPlaceholderText("What do we learn about a character")

        self._title.setHidden(True)
        self._charSelector = CharacterSelectorButton(self.novel, iconSize=32)
        self._charSelector.characterSelected.connect(self._characterSelected)
        wdgHeader = QWidget()
        hbox(wdgHeader, 0, 0)
        wdgHeader.layout().addWidget(self._charSelector)
        wdgHeader.layout().addWidget(label('Character insight', bold=True), alignment=Qt.AlignmentFlag.AlignBottom)
        self.layout().insertWidget(0, wdgHeader, alignment=Qt.AlignmentFlag.AlignCenter)
        margins(self, top=1)

        if self.function.character_id:
            character = entities_registry.character(str(self.function.character_id))
            if character:
                self._charSelector.setCharacter(character)

    def _characterSelected(self, character: Character):
        self.function.character_id = character.id


class ResonancePrimarySceneFunctionWidget(PrimarySceneFunctionWidget):
    def __init__(self, novel: Novel, scene: Scene, function: SceneFunction, parent=None):
        super().__init__(novel, scene, function, parent)

        self._title.setIcon(IconRegistry.theme_icon())
        self._title.setText('Resonance')
        self._textedit.setPlaceholderText("What emotional or thematic impact does this scene have")


class SecondaryFunctionListItemWidget(ListItemWidget):
    def __init__(self, function: SceneFunction, parent=None):
        super().__init__(function, parent)
        self._function = function
        self._icon = Icon()

        if function.type == StoryElementType.Mystery:
            icon = IconRegistry.from_name('ei.question-sign', PLOTLYST_SECONDARY_COLOR)
            placeholder = "Introduce or deepen a mystery"
        elif function.type == StoryElementType.Setup:
            icon = IconRegistry.setup_scene_icon(color=PLOTLYST_SECONDARY_COLOR)
            placeholder = "Sets up a story element for a later payoff"
        elif function.type == StoryElementType.Information:
            icon = IconRegistry.general_info_icon('lightgrey')
            placeholder = "What new information is conveyed"
        elif function.type == StoryElementType.Resonance:
            icon = IconRegistry.theme_icon()
            placeholder = "What emotional or thematic impact does this scene have"
        elif function.type == StoryElementType.Character:
            icon = IconRegistry.character_icon(color=PLOTLYST_SECONDARY_COLOR)
            placeholder = 'What do we learn about a character'
        else:
            icon = QIcon()
            placeholder = 'Fill out this secondary function'

        tip = f'{function.type.name}: {placeholder}'

        self._icon.setIcon(icon)
        self._icon.setToolTip(tip)
        self._lineEdit.setPlaceholderText(placeholder)
        self._lineEdit.setToolTip(tip)

        self.layout().insertWidget(1, self._icon)
        lblName = label(function.type.name, description=True)
        lblName.setFixedWidth(90)
        self.layout().insertWidget(2, lblName)

        self._lineEdit.setText(self._function.text)

    def setCharacterEnabled(self, novel: Novel):
        charSelector = CharacterSelectorButton(novel, iconSize=16)
        charSelector.characterSelected.connect(self._characterSelected)
        self.layout().insertWidget(1, charSelector)
        self._icon.setHidden(True)

        if self._function.character_id:
            character = entities_registry.character(str(self._function.character_id))
            if character:
                charSelector.setCharacter(character)

    def _characterSelected(self, character: Character):
        self._function.character_id = character.id

    @overrides
    def _textChanged(self, text: str):
        super()._textChanged(text)
        self._function.text = text


class SecondaryFunctionsList(ListView):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._scene: Optional[Scene] = None
        margins(self, left=20)
        self._btnAdd.setHidden(True)

    def setScene(self, scene: Scene):
        self._scene = scene

        for function in self._scene.functions.secondary:
            self.addItem(function)

    @overrides
    def addItem(self, item: SceneFunction) -> ListItemWidget:
        wdg = super().addItem(item)
        if item.type == StoryElementType.Character:
            wdg.setCharacterEnabled(self._novel)
        return wdg

    @overrides
    def _addNewItem(self):
        pass

    @overrides
    def _listItemWidgetClass(self):
        return SecondaryFunctionListItemWidget

    @overrides
    def _deleteItemWidget(self, widget: ListItemWidget):
        super()._deleteItemWidget(widget)
        self._scene.functions.secondary.remove(widget.item())

    @overrides
    def _dropped(self, mimeData: ObjectReferenceMimeData):
        wdg = super()._dropped(mimeData)
        if wdg.item().type == StoryElementType.Character:
            wdg.setCharacterEnabled(self._novel)
        items = []
        for wdg in self.widgets():
            items.append(wdg.item())
        self._scene.functions.secondary[:] = items


class SceneFunctionsWidget(QFrame):
    storylineLinked = pyqtSignal(ScenePlotReference)
    storylineRemoved = pyqtSignal(ScenePlotReference)
    storylineCharged = pyqtSignal()

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._scene: Optional[Scene] = None
        self.setProperty('muted-bg', True)

        vbox(self)
        margins(self, left=15)

        self.wdgPlots = self._frame(scroll=True, h_on=True)
        hbox(self.wdgPlots.widget())

        self.wdgCharacter = self._frame(scroll=True, v_on=True)
        vbox(self.wdgCharacter.widget())

        self.wdgResonance = self._frame(scroll=True, h_on=True)
        hbox(self.wdgResonance.widget())

        self.wdgPivotal = self._frame(scroll=True)
        vbox(self.wdgPivotal.widget())
        self.wdgPivotal.setMaximumWidth(150)

        self.wdgMystery = self._frame(scroll=True, v_on=True)
        vbox(self.wdgMystery.widget())
        sp(self.wdgMystery).h_exp()

        self.wdgMiddleContainer = columns()
        self.wdgMiddleContainer.layout().addWidget(self.wdgPivotal)
        self.wdgMiddleContainer.layout().addWidget(self.wdgMystery)

        self.wdgBottomContainer = rows()
        self.wdgBottomContainer.layout().addWidget(self.wdgMiddleContainer)
        self.wdgBottomContainer.layout().addWidget(self.wdgResonance)

        self.wdgLeftContainer = h_splitter(self.wdgCharacter, self.wdgBottomContainer, [250, 150])

        self.wdgCenter = v_splitter(self.wdgPlots, self.wdgLeftContainer, [200, 400])
        self.wdgInfo = self._frame(scroll=True, v_on=True)
        vbox(self.wdgInfo.widget())

        self.listSecondary = SecondaryFunctionsList(self._novel)
        self.wdgInfo.widget().layout().addWidget(self.listSecondary)

        self.splitter = h_splitter(self.wdgCenter, self.wdgInfo, [500, 150])

        self.layout().addWidget(self.splitter)

        # self.btnPrimary = push_btn(IconRegistry.from_name('mdi6.note-text-outline', 'grey'), 'Primary functions',
        #                            transparent_=True)
        # incr_icon(self.btnPrimary, 1)
        # incr_font(self.btnPrimary, 1)
        # self.btnPrimary.installEventFilter(OpacityEventFilter(self.btnPrimary, leaveOpacity=0.7))
        # self.btnPrimaryPlus = tool_btn(IconRegistry.plus_icon('grey'), transparent_=True)
        # self.btnPrimaryPlus.installEventFilter(OpacityEventFilter(self.btnPrimaryPlus, leaveOpacity=0.7))
        # self.menuPrimary = MenuWidget(self.btnPrimaryPlus, largeIcons=True)
        # self.menuPrimary.setTooltipDisplayMode(ActionTooltipDisplayMode.DISPLAY_UNDER)
        # self.menuPrimary.addSection('Select a primary function that this scene fulfills')
        # self.menuPrimary.addSeparator()
        # self.menuPrimary.addAction(action('Advance story', IconRegistry.storylines_icon(),
        #                                   slot=partial(self._addPrimary, StoryElementType.Plot),
        #                                   tooltip="This scene primarily advances or complicates the story \nby affecting the plot, character development, or relationships",
        #                                   incr_font_=2))
        # self.menuPrimary.addAction(
        #     action('Character insight', IconRegistry.character_icon(),
        #            slot=partial(self._addPrimary, StoryElementType.Character),
        #            tooltip="This scene primarily provides new information, layers, \nor development about a character",
        #            incr_font_=2))
        # self.menuPrimary.addAction(action('Mystery', IconRegistry.from_name('ei.question-sign'),
        #                                   slot=partial(self._addPrimary, StoryElementType.Mystery),
        #                                   tooltip="This scene primarily introduces or deepens a mystery \nthat drives the narrative forward",
        #                                   incr_font_=2))
        # self.menuPrimary.addAction(action('Resonance', IconRegistry.theme_icon('black'),
        #                                   slot=partial(self._addPrimary, StoryElementType.Resonance),
        #                                   tooltip="This scene primarily establishes an emotional or thematic impact",
        #                                   incr_font_=2))
        # self.btnPrimary.clicked.connect(self.btnPrimaryPlus.click)
        #
        # self.btnSecondary = push_btn(IconRegistry.from_name('fa5s.list', 'grey'), 'Secondary functions',
        #                              transparent_=True)
        # self.btnSecondary.installEventFilter(OpacityEventFilter(self.btnSecondary, leaveOpacity=0.7))
        # incr_icon(self.btnSecondary, 1)
        # incr_font(self.btnSecondary, 1)
        # self.btnSecondaryPlus = tool_btn(IconRegistry.plus_icon('grey'), transparent_=True)
        # self.btnSecondaryPlus.installEventFilter(OpacityEventFilter(self.btnPrimaryPlus, leaveOpacity=0.7))
        # self.menuSecondary = MenuWidget(self.btnSecondaryPlus)
        # self.menuSecondary.setTooltipDisplayMode(ActionTooltipDisplayMode.DISPLAY_UNDER)
        # self.menuSecondary.addSection('Select a secondary function that this scene also fulfills')
        # self.menuSecondary.addSeparator()
        # self.menuSecondary.addAction(
        #     action('Setup', IconRegistry.setup_scene_icon('black'),
        #            slot=partial(self._addSecondary, StoryElementType.Setup),
        #            tooltip="Sets up a story element for a later payoff", incr_font_=1))
        # self.menuSecondary.addAction(
        #     action('Information', IconRegistry.general_info_icon('black'),
        #            slot=partial(self._addSecondary, StoryElementType.Information),
        #            tooltip="New information to be conveyed", incr_font_=1))
        # self.menuSecondary.addAction(
        #     action('Character insight', IconRegistry.character_icon(),
        #            slot=partial(self._addSecondary, StoryElementType.Character),
        #            tooltip="New information about a character", incr_font_=1))
        # self.menuSecondary.addAction(
        #     action('Mystery', IconRegistry.from_name('ei.question-sign'),
        #            slot=partial(self._addSecondary, StoryElementType.Mystery),
        #            tooltip="A smaller mystery to be introduced or deepened", incr_font_=1))
        # self.menuSecondary.addAction(
        #     action('Resonance', IconRegistry.theme_icon('black'),
        #            slot=partial(self._addSecondary, StoryElementType.Resonance),
        #            tooltip="Emotional or thematic impact", incr_font_=1))
        #
        # self.btnSecondary.clicked.connect(self.btnSecondaryPlus.click)
        #
        # self.wdgPrimary = QWidget()
        # flow(self.wdgPrimary, spacing=13)
        # margins(self.wdgPrimary, left=20, top=0)
        #
        #
        # wdgPrimaryHeader = QWidget()
        # hbox(wdgPrimaryHeader, 0, 0)
        # wdgPrimaryHeader.layout().addWidget(self.btnPrimary)
        # wdgPrimaryHeader.layout().addWidget(self.btnPrimaryPlus, alignment=Qt.AlignmentFlag.AlignBottom)
        # self.layout().addWidget(wdgPrimaryHeader, alignment=Qt.AlignmentFlag.AlignLeft)
        # self.layout().addWidget(self.wdgPrimary)
        #
        # wdgSecondaryHeader = QWidget()
        # hbox(wdgSecondaryHeader, 0, 0)
        # wdgSecondaryHeader.layout().addWidget(self.btnSecondary)
        # wdgSecondaryHeader.layout().addWidget(self.btnSecondaryPlus, alignment=Qt.AlignmentFlag.AlignBottom)
        # self.layout().addWidget(wdgSecondaryHeader, alignment=Qt.AlignmentFlag.AlignLeft)
        # self.layout().addWidget(self.listSecondary)
        # self.layout().addWidget(vspacer())

    def setScene(self, scene: Scene):
        self._scene = scene
        clear_layout(self.wdgPlots.widget())
        clear_layout(self.wdgCharacter.widget())
        clear_layout(self.wdgMystery)
        clear_layout(self.wdgResonance.widget())

        self.listSecondary.clear()
        for function in self._scene.functions.primary:
            self.__initPrimaryWidget(function)
            # self._addPrimaryWidget(function.type, wdg)

        self.listSecondary.setScene(self._scene)

    def addPrimaryType(self, type_: StoryElementType, storyline: Optional[Plot] = None):
        self._addPrimary(type_, storyline)

    def storylineRemovedEvent(self, storyline: Plot):
        for i in range(self.wdgPlots.layout().count()):
            widget = self.wdgPlots.layout().itemAt(i).widget()
            if widget and isinstance(widget, _StorylineAssociatedFunctionWidget):
                if widget.function.ref == storyline.id:
                    self._scene.functions.primary.remove(widget.function)
                    self._scene.plot_values.remove(widget.plotRef())
                    fade_out_and_gc(self.wdgPlots, widget)
                    return

    def _addPrimary(self, type_: StoryElementType, storyline: Optional[Plot] = None):
        function = SceneFunction(type_)
        self._scene.functions.primary.append(function)

        wdg = self.__initPrimaryWidget(function, storyline)
        # self._addPrimaryWidget(type_, wdg)

        qtanim.fade_in(wdg, teardown=lambda: wdg.setGraphicsEffect(None))

    def _addPrimaryWidget(self, type_: StoryElementType, wdg: PrimarySceneFunctionWidget):
        if type_ == StoryElementType.Plot:
            self.wdgPlots.widget().layout().addWidget(wdg)
        elif type_ == StoryElementType.Character:
            self.wdgCharacter.widget().layout().addWidget(wdg)
        elif type_ == StoryElementType.Mystery:
            self.wdgMystery.layout().addWidget(wdg)
        elif type_ == StoryElementType.Resonance:
            self.wdgResonance.widget().layout().addWidget(wdg)

    def _addSecondary(self, type_: StoryElementType):
        function = SceneFunction(type_)
        self._scene.functions.secondary.append(function)
        self.listSecondary.addItem(function)

    def _removePrimary(self, wdg: PrimarySceneFunctionWidget):
        self._scene.functions.primary.remove(wdg.function)
        if isinstance(wdg, _StorylineAssociatedFunctionWidget):
            ref = wdg.plotRef()
            if ref:
                self._scene.plot_values.remove(ref)
                self.storylineRemoved.emit(ref)

        fade_out_and_gc(self.wdgPlots, wdg)

    def __initPrimaryWidget(self, function: SceneFunction, storyline: Optional[Plot] = None):
        if function.type == StoryElementType.Character:
            wdg = CharacterPrimarySceneFunctionWidget(self._novel, self._scene, function)
        elif function.type == StoryElementType.Mystery:
            wdg = MysteryPrimarySceneFunctionWidget(self._novel, self._scene, function)
        elif function.type == StoryElementType.Resonance:
            wdg = ResonancePrimarySceneFunctionWidget(self._novel, self._scene, function)
        else:
            wdg = PlotPrimarySceneFunctionWidget(self._novel, self._scene, function)

        wdg.removed.connect(partial(self._removePrimary, wdg))
        if isinstance(wdg, _StorylineAssociatedFunctionWidget):
            wdg.storylineSelected.connect(self.storylineLinked)
            wdg.storylineRemoved.connect(self.storylineRemoved)
            wdg.storylineCharged.connect(self.storylineCharged)
            if storyline:
                wdg.setPlot(storyline)
            for ref in self._scene.plot_values:
                if ref.plot.id == function.ref:
                    wdg.setPlotRef(ref)
        self._addPrimaryWidget(function.type, wdg)
        return wdg

    def _frame(self, scroll: bool = False, h_on: bool = False, v_on: bool = False) -> Union[QFrame, QScrollArea]:
        if scroll:
            frame_ = scroll_area(h_on, v_on)
            wdg = QWidget()
            transparent(wdg)
            frame_.setWidget(wdg)
        else:
            frame_ = frame()
        frame_.setProperty('large-rounded', True)
        frame_.setProperty('relaxed-white-bg', True)
        return frame_
