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
from typing import Optional

import qtanim
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QSize
from PyQt6.QtGui import QColor, QIcon, QEnterEvent
from PyQt6.QtWidgets import QWidget, QAbstractButton, QFrame
from overrides import overrides
from qthandy import vbox, margins, hbox, pointy, gc, sp, clear_layout, incr_font, incr_icon, flow, transparent, \
    bold, translucent, line
from qthandy.filter import ObjectReferenceMimeData
from qtmenu import MenuWidget, ActionTooltipDisplayMode

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, RED_COLOR, LIGHTGREY_ACTIVE_COLOR, LIGHTGREY_IDLE_COLOR
from plotlyst.core.domain import Scene, Novel, StoryElementType, Character, SceneFunction, Plot, ScenePlotReference
from plotlyst.service.cache import entities_registry
from plotlyst.view.common import tool_btn, action, label, fade_out_and_gc, fade_in, shadow, insert_before_the_end, rows, \
    push_btn
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.widget.characters import CharacterSelectorButton
from plotlyst.view.widget.display import Icon, icon_text
from plotlyst.view.widget.input import TextEditBubbleWidget
from plotlyst.view.widget.list import ListView, ListItemWidget
from plotlyst.view.widget.scene.plot import SceneStorylineProgressEditor, \
    ScenePlotSelectorMenu


class PrimarySceneFunctionWidget(TextEditBubbleWidget):
    def __init__(self, novel: Novel, scene: Scene, function: SceneFunction, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.scene = scene
        self.function = function
        self._removalEnabled = True

        self.setProperty('large-rounded', True)
        self.setProperty('relaxed-white-bg', True)

        bold(self._title, False)
        translucent(self._title, 0.7)

        self.setMaximumSize(170, 130)
        self._textedit.setText(self.function.text)
        transparent(self._textedit)

    def activate(self):
        shadow(self)

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

        self._btnProgress = tool_btn(IconRegistry.from_name('mdi.chevron-double-up', LIGHTGREY_ACTIVE_COLOR),
                                     transparent_=True,
                                     tooltip='Track progress', parent=self)
        self._btnProgress.setGeometry(0, 4, 20, 20)
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

        editor = SceneStorylineProgressEditor(self._plotRef)
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
        self._textedit.setPlaceholderText("Emotional or thematic effects that stay with the reader")


class ReactionPrimarySceneFunctionWidget(PrimarySceneFunctionWidget):
    def __init__(self, novel: Novel, scene: Scene, function: SceneFunction, parent=None):
        super().__init__(novel, scene, function, parent)

        self._title.setIcon(IconRegistry.from_name('fa5s.heartbeat'))
        self._title.setText('Reaction')
        self._textedit.setPlaceholderText("Emotional or physical responses to events")


class ReflectionPrimarySceneFunctionWidget(PrimarySceneFunctionWidget):
    def __init__(self, novel: Novel, scene: Scene, function: SceneFunction, parent=None):
        super().__init__(novel, scene, function, parent)
        self._title.setIcon(IconRegistry.from_name('mdi.thought-bubble-outline'))
        self._title.setText('Reflection')
        self._textedit.setPlaceholderText("Internal processing and contemplation of events")


class RepercussionPrimarySceneFunctionWidget(PrimarySceneFunctionWidget):
    def __init__(self, novel: Novel, scene: Scene, function: SceneFunction, parent=None):
        super().__init__(novel, scene, function, parent)
        self._title.setIcon(IconRegistry.from_name('fa5s.radiation'))
        self._title.setText('Repercussion')
        self._textedit.setPlaceholderText("The consequences or fallout from previous actions")


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


class _PrimaryFunctionsWidget(QFrame):
    newFunctionSelected = pyqtSignal(StoryElementType)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        vbox(self, 5, 5)

        self.container = QWidget()
        flow(self.container, spacing=5)
        sp(self.container).v_max()

        self.btnPlus: Optional[QAbstractButton] = None

        sp(self).v_max()

    def clear(self):
        clear_layout(self.container)
        wdg = rows()
        wdg.setFixedHeight(140)
        self.btnPlus = push_btn(IconRegistry.plus_icon(LIGHTGREY_IDLE_COLOR))
        self.btnPlus.setIconSize(QSize(36, 36))
        self.btnPlus.setStyleSheet(f'color: {LIGHTGREY_ACTIVE_COLOR}; border: 0px;')
        self.btnPlus.clicked.connect(self._plusClicked)
        wdg.layout().addWidget(self.btnPlus, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.container.layout().addWidget(wdg)

    def addWidget(self, wdg: PrimarySceneFunctionWidget):
        insert_before_the_end(self.container, wdg)
        self.btnPlus.setText('')

    def _plusClicked(self):
        pass


class DriveFunctionsWidget(_PrimaryFunctionsWidget):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(novel, parent)

        header = icon_text('mdi.yin-yang', 'Drive', icon_color='#E19999', opacity=0.9, icon_h_flip=True)
        incr_font(header, 2)
        incr_icon(header, 2)
        self.layout().addWidget(header, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(line(color='#E19999'))
        self.layout().addWidget(self.container)

    @overrides
    def clear(self):
        super().clear()
        self.btnPlus.setText('Drive the story')

    @overrides
    def _plusClicked(self):
        self.newFunctionSelected.emit(StoryElementType.Plot)


class ImpactFunctionsWidget(_PrimaryFunctionsWidget):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(novel, parent)

        header = icon_text('mdi.yin-yang', 'Impact', icon_color='#A5C3D9', opacity=0.9)
        incr_font(header, 2)
        incr_icon(header, 2)
        self.layout().addWidget(header, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.container)

    @overrides
    def clear(self):
        super().clear()
        self.btnPlus.setText('Emotional, dramatic, or thematic impact')

    @overrides
    def _plusClicked(self):
        unit = 'scene' if self._novel.prefs.is_scenes_organization() else 'chapter'
        menu = MenuWidget(largeIcons=True)
        menu.setTooltipDisplayMode(ActionTooltipDisplayMode.DISPLAY_UNDER)
        menu.addSection(
            f"This {unit} primarily reflects the aftermath of events, deepening emotions, themes, or consequences")
        menu.addSeparator()

        menu.addAction(action('Reaction', IconRegistry.from_name('fa5s.heartbeat'),
                              slot=partial(self.newFunctionSelected.emit, StoryElementType.Reaction),
                              tooltip="Emotional or physical responses to events",
                              incr_font_=2))
        menu.addAction(action('Reflection', IconRegistry.from_name('mdi.thought-bubble-outline'),
                              slot=partial(self.newFunctionSelected.emit, StoryElementType.Reflection),
                              tooltip="Internal processing and contemplation of events. Might include analysis of a situation or mystery.",
                              incr_font_=2))
        menu.addAction(action('Repercussion', IconRegistry.from_name('fa5s.radiation'),
                              slot=partial(self.newFunctionSelected.emit, StoryElementType.Repercussion),
                              tooltip="The consequences or fallout from previous actions",
                              incr_font_=2))
        menu.addAction(action('Resonance', IconRegistry.theme_icon('black'),
                              slot=partial(self.newFunctionSelected.emit, StoryElementType.Resonance),
                              tooltip="Lingering emotional or thematic effects that stay with the reader",
                              incr_font_=2))

        menu.exec()


class SceneFunctionsWidget(QFrame):
    storylineLinked = pyqtSignal(ScenePlotReference)
    storylineRemoved = pyqtSignal(ScenePlotReference)
    storylineCharged = pyqtSignal()

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._scene: Optional[Scene] = None

        hbox(self, 10, 8)

        self.wdgDrive = DriveFunctionsWidget(self._novel)
        self.wdgDrive.newFunctionSelected.connect(self.addPrimaryType)

        self.wdgImpact = ImpactFunctionsWidget(self._novel)
        self.wdgImpact.newFunctionSelected.connect(self.addPrimaryType)

        self.layout().addWidget(self.wdgDrive, alignment=Qt.AlignmentFlag.AlignTop)
        self.layout().addWidget(self.wdgImpact, alignment=Qt.AlignmentFlag.AlignTop)

    def setScene(self, scene: Scene):
        self._scene = scene
        self.wdgDrive.clear()
        self.wdgImpact.clear()

        for function in self._scene.functions.primary:
            wdg = self.__initPrimaryWidget(function)
            wdg.activate()

    def addPrimaryType(self, type_: StoryElementType, storyline: Optional[Plot] = None):
        function = SceneFunction(type_)
        self._scene.functions.primary.append(function)

        wdg = self.__initPrimaryWidget(function, storyline)
        qtanim.fade_in(wdg, teardown=wdg.activate)

    def storylineRemovedEvent(self, storyline: Plot):
        for i in range(self.wdgDrive.layout().count()):
            widget = self.wdgDrive.container.layout().itemAt(i).widget()
            if widget and isinstance(widget, _StorylineAssociatedFunctionWidget):
                if widget.function.ref == storyline.id:
                    self._scene.functions.primary.remove(widget.function)
                    self._scene.plot_values.remove(widget.plotRef())
                    fade_out_and_gc(self.wdgDrive, widget)
                    return

    def _removePrimary(self, wdg: PrimarySceneFunctionWidget):
        self._scene.functions.primary.remove(wdg.function)
        if isinstance(wdg, _StorylineAssociatedFunctionWidget):
            ref = wdg.plotRef()
            if ref:
                self._scene.plot_values.remove(ref)
                self.storylineRemoved.emit(ref)

        fade_out_and_gc(self.wdgDrive, wdg)

    def __initPrimaryWidget(self, function: SceneFunction, storyline: Optional[Plot] = None):
        if function.type == StoryElementType.Character:
            wdg = CharacterPrimarySceneFunctionWidget(self._novel, self._scene, function)
        elif function.type == StoryElementType.Mystery:
            wdg = MysteryPrimarySceneFunctionWidget(self._novel, self._scene, function)
        elif function.type == StoryElementType.Resonance:
            wdg = ResonancePrimarySceneFunctionWidget(self._novel, self._scene, function)
        elif function.type == StoryElementType.Reaction:
            wdg = ReactionPrimarySceneFunctionWidget(self._novel, self._scene, function)
        elif function.type == StoryElementType.Reflection:
            wdg = ReflectionPrimarySceneFunctionWidget(self._novel, self._scene, function)
        elif function.type == StoryElementType.Repercussion:
            wdg = RepercussionPrimarySceneFunctionWidget(self._novel, self._scene, function)
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

        if function.type in [StoryElementType.Plot, StoryElementType.Mystery]:
            self.wdgDrive.addWidget(wdg)
        elif function.type in [StoryElementType.Resonance, StoryElementType.Reaction, StoryElementType.Reflection,
                               StoryElementType.Repercussion]:
            self.wdgImpact.addWidget(wdg)

        return wdg
