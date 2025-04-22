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
from typing import Dict, Optional, List

import qtanim
from PyQt6.QtCore import Qt, QEvent, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QEnterEvent, QMouseEvent, QIcon, QCursor
from PyQt6.QtWidgets import QWidget, QSlider, QDialog, QButtonGroup, QFrame
from overrides import overrides
from qtanim import fade_in
from qthandy import hbox, spacer, sp, bold, vbox, translucent, clear_layout, margins, vspacer, \
    line, grid, flow, retain_when_hidden
from qthandy.filter import OpacityEventFilter, VisibilityToggleEventFilter, DisabledClickEventFilter
from qtmenu import MenuWidget

from plotlyst.common import PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import Motivation, Novel, Scene, CharacterAgency, Character, StoryElementType, \
    CharacterAgencyChanges, StoryElement
from plotlyst.event.core import Event, EventListener
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import NovelPanelCustomizationEvent, NovelEmotionTrackingToggleEvent, \
    NovelMotivationTrackingToggleEvent, NovelConflictTrackingToggleEvent, CharacterDeletedEvent
from plotlyst.service.cache import entities_registry
from plotlyst.view.common import push_btn, label, fade_out_and_gc, tool_btn, action, ExclusiveOptionalButtonGroup
from plotlyst.view.generated.scene_goal_stakes_ui import Ui_GoalReferenceStakesEditor
from plotlyst.view.icons import IconRegistry, avatars
from plotlyst.view.layout import group
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.widget.button import ChargeButton, DotsMenuButton
from plotlyst.view.widget.character.editor import EmotionEditorSlider
from plotlyst.view.widget.characters import CharacterSelectorMenu
from plotlyst.view.widget.display import HeaderColumn, ArrowButton, PopupDialog
from plotlyst.view.widget.input import RemovalButton, TextEditBubbleWidget, Toggle
from plotlyst.view.widget.scene.conflict import ConflictIntensityEditor, CharacterConflictSelector


class MotivationDisplay(QWidget, Ui_GoalReferenceStakesEditor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self._novel: Optional[Novel] = None
        self._scene: Optional[Scene] = None
        self._agenda: Optional[CharacterAgency] = None
        bold(self.lblTitle)

        self._sliders: Dict[Motivation, QSlider] = {
            Motivation.PHYSIOLOGICAL: self.sliderPhysiological,
            Motivation.SAFETY: self.sliderSecurity,
            Motivation.BELONGING: self.sliderBelonging,
            Motivation.ESTEEM: self.sliderEsteem,
            Motivation.SELF_ACTUALIZATION: self.sliderActualization,
            Motivation.SELF_TRANSCENDENCE: self.sliderTranscendence,
        }

        for slider in self._sliders.values():
            slider.setEnabled(False)
        translucent(self)

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        pass

    def setNovel(self, novel: Novel):
        self._novel = novel

    def setScene(self, scene: Scene):
        self._scene = scene

    def setAgenda(self, agenda: CharacterAgency):
        self._agenda = agenda
        self._refresh()

    def _refresh(self):
        for slider in self._sliders.values():
            slider.setValue(0)
        for scene in self._novel.scenes:
            if scene is self._scene:
                break
            for agenda in scene.agency:
                if agenda.character_id and agenda.character_id == self._agenda.character_id:
                    for mot, v in agenda.motivations.items():
                        slider = self._sliders[Motivation(mot)]
                        slider.setValue(slider.value() + v)


class MotivationChargeLabel(QWidget):
    def __init__(self, motivation: Motivation, simplified: bool = False, parent=None):
        super().__init__(parent)
        self._motivation = motivation
        hbox(self, margin=0 if simplified else 1, spacing=0)
        if simplified:
            self._btn = tool_btn(IconRegistry.from_name(self._motivation.icon(), self._motivation.color()),
                                 icon_resize=False, transparent_=True)
        else:
            self._btn = push_btn(IconRegistry.from_name(self._motivation.icon(), self._motivation.color()),
                                 text=motivation.display_name(), icon_resize=False,
                                 transparent_=True)
        self._btn.setCursor(Qt.CursorShape.ArrowCursor)

        self._lblCharge = label('', description=True, italic=True)

        self.layout().addWidget(self._btn)
        self.layout().addWidget(self._lblCharge)

    def setCharge(self, charge: int):
        bold(self._btn, charge > 0)
        if charge == 0:
            self._lblCharge.clear()
        else:
            self._lblCharge.setText(f'+{charge}')


class MotivationCharge(QWidget):
    charged = pyqtSignal(int)
    MAX_CHARGE: int = 5

    def __init__(self, motivation: Motivation, parent=None):
        super().__init__(parent)
        hbox(self)
        self._motivation = motivation
        self._charge = 0

        self._label = MotivationChargeLabel(self._motivation)
        self._posCharge = ChargeButton(positive=True)
        self._posCharge.clicked.connect(lambda: self._changeCharge(1))
        self._negCharge = ChargeButton(positive=False)
        self._negCharge.clicked.connect(lambda: self._changeCharge(-1))
        self._negCharge.setHidden(True)

        self.layout().addWidget(self._label)
        self.layout().addWidget(spacer())
        self.layout().addWidget(self._negCharge)
        self.layout().addWidget(self._posCharge)

    def setValue(self, value: int):
        self._charge = min(value, self.MAX_CHARGE)
        self._update()

    def _changeCharge(self, charge: int):
        self._charge += charge
        self._update()

        self.charged.emit(self._charge)

    def _update(self):
        self._label.setCharge(self._charge)
        if self._charge == 0:
            self._negCharge.setHidden(True)
        else:
            self._negCharge.setVisible(True)
        if self._charge == self.MAX_CHARGE:
            self._posCharge.setHidden(True)
        else:
            self._posCharge.setVisible(True)


class MotivationEditor(QWidget):
    motivationChanged = pyqtSignal(Motivation, int)

    def __init__(self, parent=None):
        super().__init__(parent)

        vbox(self)
        self.layout().addWidget(label("Does the character's motivation change?"))

        self._editors: Dict[Motivation, MotivationCharge] = {}
        self._addEditor(Motivation.PHYSIOLOGICAL)
        self._addEditor(Motivation.SAFETY)
        self._addEditor(Motivation.BELONGING)
        self._addEditor(Motivation.ESTEEM)
        self._addEditor(Motivation.SELF_ACTUALIZATION)
        self._addEditor(Motivation.SELF_TRANSCENDENCE)

    def _addEditor(self, motivation: Motivation):
        wdg = MotivationCharge(motivation)
        self._editors[motivation] = wdg
        wdg.charged.connect(partial(self.motivationChanged.emit, motivation))
        self.layout().addWidget(wdg)

    def reset(self):
        for editor in self._editors.values():
            editor.setValue(0)

    def setMotivations(self, motivations: Dict[Motivation, int]):
        self.reset()
        for mot, v in motivations.items():
            self._editors[mot].setValue(v)


class AbstractAgencyEditor(QWidget):
    deactivated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._activated: bool = False
        self._removalEnabled: bool = True

        self._icon = push_btn(QIcon(), transparent_=True)
        self._icon.setIconSize(QSize(28, 28))
        self._opacityFilter = OpacityEventFilter(self._icon)
        self._icon.clicked.connect(self._iconClicked)

        self._btnReset = RemovalButton()
        self._btnReset.clicked.connect(self._resetClicked)
        retain_when_hidden(self._btnReset)

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        if self._activated and self._removalEnabled:
            self._btnReset.setVisible(True)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        self._btnReset.setVisible(False)

    def reset(self):
        self._activated = False
        self._btnReset.setVisible(False)

    def _resetClicked(self):
        self.deactivated.emit()
        self.reset()

    def _iconClicked(self):
        pass


class SceneAgendaEmotionEditor(AbstractAgencyEditor):
    emotionChanged = pyqtSignal(int)
    deactivated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self)
        sp(self).h_max()

        self._icon.setIcon(IconRegistry.from_name('mdi.emoticon-neutral', 'lightgrey'))

        self._slider = EmotionEditorSlider()
        self._slider.valueChanged.connect(self._valueChanged)

        self.layout().addWidget(self._icon)
        self.layout().addWidget(self._slider)
        self.layout().addWidget(spacer(max_stretch=5))
        self.layout().addWidget(self._btnReset, alignment=Qt.AlignmentFlag.AlignTop)

        self.reset()

    def activate(self):
        self._activated = True
        self._slider.setVisible(True)
        self._icon.setText('')
        self._icon.removeEventFilter(self._opacityFilter)

    @overrides
    def reset(self):
        super().reset()
        self._slider.setVisible(False)
        self._icon.setIcon(IconRegistry.from_name('mdi.emoticon-neutral', 'lightgrey'))
        self._icon.setText('Emotion')
        self._icon.installEventFilter(self._opacityFilter)
        translucent(self._icon, 0.4)

    def setValue(self, value: int):
        self.activate()
        if self._slider.value() == value:
            self.emotionChanged.emit(value)
        else:
            self._slider.setValue(value)

        self._btnReset.setHidden(True)

    @overrides
    def _iconClicked(self):
        if not self._activated:
            self.setValue(5)
            qtanim.fade_in(self._slider, 150)
            self._btnReset.setVisible(True)

    def _valueChanged(self, value: int):
        self._icon.setIcon(IconRegistry.emotion_icon_from_feeling(value))
        self.emotionChanged.emit(value)


class SceneAgendaMotivationEditor(AbstractAgencyEditor):
    motivationChanged = pyqtSignal(Motivation, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self)
        sp(self).h_max()
        self._removalEnabled = False

        self._motivationDisplay = MotivationDisplay()
        self._motivationEditor = MotivationEditor()
        self._motivationEditor.motivationChanged.connect(self._valueChanged)

        self._wdgLabels = QWidget()
        hbox(self._wdgLabels, 0, 0)
        self._labels: Dict[Motivation, MotivationChargeLabel] = {}

        self._icon.setIcon(IconRegistry.from_name('fa5s.fist-raised', 'lightgrey'))

        self._menu = MenuWidget(self._icon)
        apply_white_menu(self._menu)
        self._menu.addWidget(self._motivationDisplay)
        self._menu.addSeparator()
        self._menu.addWidget(self._motivationEditor)

        self.layout().addWidget(self._icon)
        self.layout().addWidget(self._wdgLabels)
        self.layout().addWidget(self._btnReset, alignment=Qt.AlignmentFlag.AlignTop)

        self.reset()

    def setNovel(self, novel: Novel):
        self._motivationDisplay.setNovel(novel)

    def setScene(self, scene: Scene):
        self._motivationDisplay.setScene(scene)

    def setAgenda(self, agenda: CharacterAgency):
        self._motivationDisplay.setAgenda(agenda)

        if agenda.motivations:
            values: Dict[Motivation, int] = {}
            for k, v in agenda.motivations.items():
                motivation = Motivation(k)
                values[motivation] = v

            self.setValues(values)
        else:
            self.reset()

    def activate(self):
        self._activated = True
        if self._removalEnabled:
            self._btnReset.setVisible(True)
        self._icon.setText('')
        self._icon.removeEventFilter(self._opacityFilter)

    @overrides
    def reset(self):
        super().reset()
        self._icon.setText('Motivation')
        self._icon.installEventFilter(self._opacityFilter)

        self._motivationEditor.reset()

        self._labels.clear()
        clear_layout(self._wdgLabels)

    def setValues(self, motivations: Dict[Motivation, int]):
        self.activate()
        self._motivationEditor.setMotivations(motivations)
        self._btnReset.setHidden(True)

        self._labels.clear()
        clear_layout(self._wdgLabels)
        for mot, v in motivations.items():
            self._updateLabels(mot, v)

    def _valueChanged(self, motivation: Motivation, value: int):
        self.motivationChanged.emit(motivation, value)
        self._updateLabels(motivation, value)

    def _updateLabels(self, motivation: Motivation, value: int):
        if motivation not in self._labels.keys():
            lbl = MotivationChargeLabel(motivation, simplified=True)
            self._labels[motivation] = lbl
            translucent(lbl, 0.8)
            self._wdgLabels.layout().addWidget(lbl)
            fade_in(lbl, 150)
        if value:
            self._labels[motivation].setCharge(value)
        else:
            fade_out_and_gc(self._wdgLabels, self._labels.pop(motivation))
        if self._labels and not self._activated:
            self.activate()
        elif not self._labels and self._activated:
            self.reset()


class SceneAgendaConflictEditor(AbstractAgencyEditor):
    conflictReset = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self)

        self._novel: Optional[Novel] = None
        self._scene: Optional[Scene] = None
        self._agenda: Optional[CharacterAgency] = None

        self._icon.setIcon(IconRegistry.conflict_icon('lightgrey'))
        self._icon.setText('Conflict')
        self._icon.installEventFilter(self._opacityFilter)

        self._sliderIntensity = ConflictIntensityEditor()
        self._sliderIntensity.intensityChanged.connect(self._intensityChanged)

        self._wdgConflicts = QWidget()
        hbox(self._wdgConflicts)

        self._wdgSliders = QWidget()
        hbox(self._wdgSliders).addWidget(self._sliderIntensity, alignment=Qt.AlignmentFlag.AlignLeft)
        self._wdgSliders.layout().addWidget(self._btnReset, alignment=Qt.AlignmentFlag.AlignRight)

        self.layout().addWidget(self._icon)
        self.layout().addWidget(self._wdgSliders)
        self.layout().addWidget(self._wdgConflicts)

        self.reset()

    def setNovel(self, novel: Novel):
        self._novel = novel

    def setScene(self, scene: Scene):
        self._scene = scene

    def setAgenda(self, agenda: CharacterAgency):
        self._agenda = agenda
        clear_layout(self._wdgConflicts)

        if agenda.intensity > 0 or agenda.conflict_references:
            self.setValue(agenda.intensity)
        else:
            self.reset()

        for ref in agenda.conflict_references:
            conflictSelector = CharacterConflictSelector(self._novel, self._scene, self._agenda)
            conflictSelector.setConflict(ref.conflict(self._novel), ref)
            self._wdgConflicts.layout().addWidget(conflictSelector)

        conflictSelector = CharacterConflictSelector(self._novel, self._scene, self._agenda)
        conflictSelector.conflictSelected.connect(self._conflictSelected)
        self._wdgConflicts.layout().addWidget(conflictSelector, alignment=Qt.AlignmentFlag.AlignLeft)

    def activate(self):
        self._activated = True
        self._wdgSliders.setVisible(True)
        self._wdgConflicts.setVisible(True)
        self._icon.setHidden(True)

    @overrides
    def reset(self):
        super().reset()
        self._wdgSliders.setVisible(False)
        self._wdgConflicts.setVisible(False)
        self._icon.setVisible(True)
        if self._agenda:
            self._agenda.intensity = 0
            self._agenda.conflict_references.clear()

    def setValue(self, value: int):
        self._sliderIntensity.setValue(value)
        self.activate()

    @overrides
    def _iconClicked(self):
        if not self._activated:
            self.setValue(1)
            qtanim.fade_in(self._sliderIntensity, 150)
            self._btnReset.setVisible(True)

    def _intensityChanged(self, value: int):
        if self._agenda:
            self._agenda.intensity = value

        # shadow(self._iconActive, offset=0, radius=value * 2, color=QColor('#f3a712'))
        # shadow(self._titleActive, offset=0, radius=value, color=QColor('#f3a712'))
        # shadow(self._textEditor, offset=0, radius=value * 2, color=QColor('#f3a712'))

    def _conflictSelected(self):
        conflictSelector = CharacterConflictSelector(self._novel, self._scene, self._agenda)
        conflictSelector.conflictSelected.connect(self._conflictSelected)
        self._wdgConflicts.layout().addWidget(conflictSelector)


class _CharacterStateToggle(Toggle):
    def __init__(self, type_: StoryElementType, parent=None):
        super().__init__(parent)
        self.type = type_


class _CharacterChangeSelectorToggle(QWidget):
    def __init__(self, type_: StoryElementType, parent=None):
        super().__init__(parent)
        hbox(self, 0, 0)
        self.toggle = _CharacterStateToggle(type_)
        self.label = push_btn(IconRegistry.from_name(type_.icon(), color='grey', color_on=PLOTLYST_SECONDARY_COLOR),
                              text=type_.displayed_name(), transparent_=True, checkable=True)
        tip = type_.placeholder()
        self.label.setToolTip(tip)
        self.toggle.setToolTip(tip)
        self.label.clicked.connect(self.toggle.click)
        self.toggle.toggled.connect(self._toggled)

        self.layout().addWidget(self.toggle, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.layout().addWidget(self.label)

    def _toggled(self, toggled: bool):
        bold(self.label, toggled)
        self.label.setChecked(toggled)
        self.label.clearFocus()


class CharacterChangesSelectorPopup(PopupDialog):
    def __init__(self, agenda: CharacterAgency, parent=None):
        super().__init__(parent)
        self.agenda = agenda

        self.initialBtnGroup = ExclusiveOptionalButtonGroup()
        self.initialBtnGroup.buttonToggled.connect(self._selectionChanged)
        self.wdgInitial = QWidget()
        vbox(self.wdgInitial)
        self.wdgInitial.layout().addWidget(label('Initial', bold=True), alignment=Qt.AlignmentFlag.AlignCenter)
        self.wdgInitial.layout().addWidget(line())
        self.__initSelector(StoryElementType.Goal, self.wdgInitial, self.initialBtnGroup)
        self.__initSelector(StoryElementType.Character_state, self.wdgInitial, self.initialBtnGroup)
        self.__initSelector(StoryElementType.Character_internal_state, self.wdgInitial, self.initialBtnGroup)
        self.__initSelector(StoryElementType.Expectation, self.wdgInitial, self.initialBtnGroup)
        self.wdgInitial.layout().addWidget(vspacer())

        self.transitionBtnGroup = ExclusiveOptionalButtonGroup()
        self.transitionBtnGroup.buttonToggled.connect(self._selectionChanged)
        self.wdgTransition = QWidget()
        vbox(self.wdgTransition)
        self.wdgTransition.layout().addWidget(label('Transition', bold=True), alignment=Qt.AlignmentFlag.AlignCenter)
        self.wdgTransition.layout().addWidget(line())
        self.__initSelector(StoryElementType.Conflict, self.wdgTransition, self.transitionBtnGroup)
        self.__initSelector(StoryElementType.Internal_conflict, self.wdgTransition, self.transitionBtnGroup)
        self.__initSelector(StoryElementType.Dilemma, self.wdgTransition, self.transitionBtnGroup)
        self.__initSelector(StoryElementType.Choice, self.wdgTransition, self.transitionBtnGroup)
        self.__initSelector(StoryElementType.Catalyst, self.wdgTransition, self.transitionBtnGroup)
        self.__initSelector(StoryElementType.Action, self.wdgTransition, self.transitionBtnGroup)
        self.wdgTransition.layout().addWidget(vspacer())

        self.finalBtnGroup = ExclusiveOptionalButtonGroup()
        self.finalBtnGroup.buttonToggled.connect(self._selectionChanged)
        self.wdgFinal = QWidget()
        vbox(self.wdgFinal)
        self.wdgFinal.layout().addWidget(label('Final', bold=True), alignment=Qt.AlignmentFlag.AlignCenter)
        self.wdgFinal.layout().addWidget(line())
        self.__initSelector(StoryElementType.Outcome, self.wdgFinal, self.finalBtnGroup)
        self.__initSelector(StoryElementType.Realization, self.wdgFinal, self.finalBtnGroup)
        self.__initSelector(StoryElementType.Decision, self.wdgFinal, self.finalBtnGroup)
        self.__initSelector(StoryElementType.Character_state_change, self.wdgFinal, self.finalBtnGroup)
        self.__initSelector(StoryElementType.Character_internal_state_change, self.wdgFinal, self.finalBtnGroup)
        wdgMotivation = self.__initSelector(StoryElementType.Motivation, self.wdgFinal, self.finalBtnGroup)
        for change in self.agenda.changes:
            if change.final and change.final.type == StoryElementType.Motivation:
                wdgMotivation.setDisabled(True)
                wdgMotivation.setToolTip('Motivation was already selected for this character')
                break
        self.wdgFinal.layout().addWidget(vspacer())

        self.wdgSelectors = QWidget()
        hbox(self.wdgSelectors, spacing=40)
        self.wdgSelectors.layout().addWidget(spacer())
        self.wdgSelectors.layout().addWidget(self.wdgInitial)
        self.wdgSelectors.layout().addWidget(self.wdgTransition)
        self.wdgSelectors.layout().addWidget(self.wdgFinal)
        self.wdgSelectors.layout().addWidget(spacer())

        self.btnConfirm = push_btn(text='Confirm', properties=['confirm', 'positive'])
        self.btnConfirm.setFixedWidth(250)
        self.btnConfirm.setShortcut(Qt.Key.Key_Return)
        sp(self.btnConfirm).h_exp()
        self.btnConfirm.clicked.connect(self.accept)
        self.btnConfirm.installEventFilter(
            DisabledClickEventFilter(self.btnConfirm, lambda: qtanim.shake(self.wdgSelectors)))

        self.frame.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)
        self.frame.layout().addWidget(
            label(
                'Select initial, transition, and final states to reflect character agency. Not all states need to be selected at once.',
                description=True))
        self.frame.layout().addWidget(self.wdgSelectors)
        self.frame.layout().addWidget(self.btnConfirm, alignment=Qt.AlignmentFlag.AlignCenter)

        self.btnConfirm.setEnabled(False)

    def display(self) -> Optional[CharacterAgencyChanges]:
        result = self.exec()
        if result == QDialog.DialogCode.Accepted:
            agency = CharacterAgencyChanges()
            if self.initialBtnGroup.checkedButton():
                agency.initial = StoryElement(self.initialBtnGroup.checkedButton().type)
            if self.transitionBtnGroup.checkedButton():
                agency.transition = StoryElement(self.transitionBtnGroup.checkedButton().type)
            if self.finalBtnGroup.checkedButton():
                agency.final = StoryElement(self.finalBtnGroup.checkedButton().type)

            return agency

    def _selectionChanged(self):
        if self.initialBtnGroup.checkedButton() or self.transitionBtnGroup.checkedButton() or self.finalBtnGroup.checkedButton():
            self.btnConfirm.setEnabled(True)
        else:
            self.btnConfirm.setEnabled(False)

    def __initSelector(self, type_: StoryElementType, widget: QWidget,
                       group: QButtonGroup) -> _CharacterChangeSelectorToggle:
        selector = _CharacterChangeSelectorToggle(type_)
        widget.layout().addWidget(selector, alignment=Qt.AlignmentFlag.AlignLeft)
        group.addButton(selector.toggle)

        return selector


class CharacterChangeBubble(TextEditBubbleWidget):
    def __init__(self, element: StoryElement, parent=None):
        super().__init__(parent)
        margins(self, left=1, right=1)
        self.element = element
        self._textedit.setMinimumSize(165, 100)
        self._textedit.setMaximumSize(190, 110)
        # self.setProperty('rounded', True)
        # self.setProperty('white-bg', True)
        self._textedit.setProperty('rounded', False)
        self._textedit.setProperty('transparent', True)
        self.setMaximumWidth(200)

        self._title.setIcon(IconRegistry.from_name(self.element.type.icon(), PLOTLYST_SECONDARY_COLOR))
        self._title.setText(self.element.type.displayed_name())
        tip = self.element.type.placeholder()
        self._textedit.setPlaceholderText(tip)
        self._textedit.setToolTip(tip)
        self._textedit.setText(self.element.text)

    def addBottomWidget(self, wdg: QWidget):
        self.layout().addWidget(wdg)

    @overrides
    def _textChanged(self):
        self.element.text = self._textedit.toPlainText()


class CharacterChangeRow(QFrame):
    Header1Col: int = 0
    Header2Col: int = 2
    Header3Col: int = 4

    def __init__(self, novel: Novel, scene: Scene, agency: CharacterAgency, changes: CharacterAgencyChanges,
                 parent=None):
        super().__init__(parent)
        self._novel = novel
        self._scene = scene
        self._agency = agency
        self._changes = changes
        self.setProperty('white-bg', True)
        self.setProperty('large-rounded', True)

        self.placeholder = QWidget()

        grid(self)
        self.layout().addWidget(self.placeholder, 0, 0, 1, 3)

        row = self.layout().rowCount()
        if self._changes.initial:
            self._addElement(self._changes.initial, row, self.Header1Col)
            if self._changes.transition:
                arrow = ArrowButton(Qt.Edge.RightEdge, readOnly=True)
                arrow.setState(arrow.STATE_MAX)
                self.layout().addWidget(arrow, row, self.Header2Col - 1)
        if self._changes.transition:
            self._addElement(self._changes.transition, row, self.Header2Col)
        if self._changes.final:
            self._addElement(self._changes.final, row, self.Header3Col)
            if self._changes.transition:
                arrow = ArrowButton(Qt.Edge.RightEdge, readOnly=True)
                arrow.setState(1)
                self.layout().addWidget(arrow, row, self.Header3Col - 1)

            dotsBtn = DotsMenuButton()
            dotsBtn.installEventFilter(OpacityEventFilter(dotsBtn))
            self.layout().addWidget(dotsBtn, row, self.Header3Col + 1,
                                    alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            menu = MenuWidget(dotsBtn)
            # menu.addAction(action('Remove character changes', IconRegistry.trash_can_icon(),
            #                       slot=partial(self._removeChange, change, row)))
            row += 1

    def _addElement(self, element: StoryElement, row: int, col: int):
        wdg = CharacterChangeBubble(element)
        if element.type == StoryElementType.Motivation:
            motivationEditor = SceneAgendaMotivationEditor()
            motivationEditor.motivationChanged.connect(self._motivationChanged)
            motivationEditor.setNovel(self._novel)
            motivationEditor.setScene(self._scene)
            motivationEditor.setAgenda(self._agency)
            wdg.addBottomWidget(motivationEditor)
            # motivationEditor.setVisible(self.novel.prefs.toggled(NovelSetting.Track_motivation))
        self.layout().addWidget(wdg, row, col, alignment=Qt.AlignmentFlag.AlignCenter)

    def _motivationChanged(self, motivation: Motivation, value: int):
        pass


class CharacterChangesEditor(QFrame):

    def __init__(self, novel: Novel, scene: Scene, agenda: CharacterAgency, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.scene = scene
        self.agenda = agenda
        self.btnAdd = push_btn(IconRegistry.plus_icon('grey'), 'Track character changes', transparent_=True)
        self.btnAdd.installEventFilter(OpacityEventFilter(self.btnAdd, leaveOpacity=0.7))
        self.btnAdd.clicked.connect(self._openSelector)

        header1 = HeaderColumn('Initial')
        header1.setFixedWidth(200)
        header2 = HeaderColumn('Transition')
        header3 = HeaderColumn('Final')
        header3.setFixedWidth(200)

        vbox(self)
        self.layout().addWidget(group(header1, header2, header3))
        # self._layout.addWidget(header2, 0, 1, 1, 3)
        # self._layout.addWidget(header3, 0, 4)
        self.layout().addWidget(self.btnAdd, alignment=Qt.AlignmentFlag.AlignCenter)

        if self.agenda.changes:
            self._addElements(self.agenda.changes)

    def addNewElements(self, changes: List[CharacterAgencyChanges]):
        self.agenda.changes.extend(changes)
        self._addElements(changes)

    def _openSelector(self):
        agency = CharacterChangesSelectorPopup.popup(self.agenda)
        if agency:
            self.addNewElements([agency])

    def _addElements(self, changes: List[CharacterAgencyChanges]):
        for change in changes:
            wdg = CharacterChangeRow(self.novel, self.scene, self.agenda, change)
            self.layout().addWidget(wdg)

        # def _addElement(element: StoryElement, row: int, col: int):
        #     wdg = CharacterChangeBubble(element)
        #     if element.type == StoryElementType.Motivation:
        #         motivationEditor = SceneAgendaMotivationEditor()
        #         motivationEditor.motivationChanged.connect(self._motivationChanged)
        #         motivationEditor.setNovel(self.novel)
        #         motivationEditor.setScene(self.scene)
        #         motivationEditor.setAgenda(self.agenda)
        #         wdg.addBottomWidget(motivationEditor)
        #         motivationEditor.setVisible(self.novel.prefs.toggled(NovelSetting.Track_motivation))
        #     self._layout.addWidget(wdg, row, col, alignment=Qt.AlignmentFlag.AlignCenter)
        #
        # row = self._layout.rowCount()
        # for change in changes:
        #     if change.initial:
        #         _addElement(change.initial, row, self.Header1Col)
        #         if change.transition:
        #             arrow = ArrowButton(Qt.Edge.RightEdge, readOnly=True)
        #             arrow.setState(arrow.STATE_MAX)
        #             self._layout.addWidget(arrow, row, self.Header2Col - 1)
        #     if change.transition:
        #         _addElement(change.transition, row, self.Header2Col)
        #     if change.final:
        #         _addElement(change.final, row, self.Header3Col)
        #         if change.transition:
        #             arrow = ArrowButton(Qt.Edge.RightEdge, readOnly=True)
        #             arrow.setState(1)
        #             self._layout.addWidget(arrow, row, self.Header3Col - 1)
        #
        #     dotsBtn = DotsMenuButton()
        #     dotsBtn.installEventFilter(OpacityEventFilter(dotsBtn))
        #     self._layout.addWidget(dotsBtn, row, self.Header3Col + 1,
        #                            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        #     menu = MenuWidget(dotsBtn)
        #     menu.addAction(action('Remove character changes', IconRegistry.trash_can_icon(),
        #                           slot=partial(self._removeChange, change, row)))
        #     row += 1

    def _removeChange(self, change: CharacterAgencyChanges, row: int):
        def removeItem(col: int):
            item = self._layout.itemAtPosition(row, col)
            if item:
                fade_out_and_gc(self, item.widget())

        if change.final and change.final.type == StoryElementType.Motivation:
            self.agenda.motivations.clear()

        for i in range(self.Header3Col + 2):
            removeItem(i)
        self.agenda.changes.remove(change)

    def _motivationChanged(self, motivation: Motivation, value: int):
        self.agenda.motivations[motivation.value] = value


class CharacterAgencyEditor(QWidget):
    removed = pyqtSignal()

    def __init__(self, novel: Novel, scene: Scene, agenda: CharacterAgency, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.scene = scene
        self.agenda = agenda
        vbox(self, spacing=10)
        self._charDisplay = tool_btn(IconRegistry.character_icon(), transparent_=True)
        self._charDisplay.setIconSize(QSize(54, 54))
        self._menu = MenuWidget()
        self._menu.addAction(action('Remove agency', IconRegistry.trash_can_icon(), slot=self.removed))
        self._charDisplay.clicked.connect(lambda: self._menu.exec(QCursor.pos()))

        # self._emotionEditor = SceneAgendaEmotionEditor()
        # self._emotionEditor.layout().addWidget(vline())
        # self._emotionEditor.emotionChanged.connect(self._emotionChanged)
        # self._emotionEditor.deactivated.connect(self._emotionReset)

        # self._conflictEditor = SceneAgendaConflictEditor()
        # self._conflictEditor.setNovel(self.novel)

        self._changesEditor = CharacterChangesEditor(self.novel, self.scene, self.agenda)
        margins(self._changesEditor, left=65)

        # self._conflictEditor.setAgenda(agenda)

        self._btnDots = DotsMenuButton()
        self._btnDots.clicked.connect(lambda: self._menu.exec(QCursor.pos()))

        self._wdgHeader = QWidget()
        hbox(self._wdgHeader)
        margins(self._wdgHeader, left=25)
        self._wdgHeader.layout().setSpacing(5)
        self._wdgHeader.layout().addWidget(self._charDisplay, alignment=Qt.AlignmentFlag.AlignLeft)
        # self._wdgHeader.layout().addWidget(self._emotionEditor)
        # self._wdgHeader.layout().addWidget(self._conflictEditor)
        self._wdgHeader.layout().addWidget(spacer())
        self._wdgHeader.layout().addWidget(self._btnDots, alignment=Qt.AlignmentFlag.AlignTop)
        self.layout().addWidget(self._wdgHeader)
        self.layout().addWidget(self._changesEditor)
        self.installEventFilter(VisibilityToggleEventFilter(self._btnDots, self))

        if self.agenda.character_id:
            character = entities_registry.character(str(self.agenda.character_id))
            if character:
                self._charDisplay.setIcon(avatars.avatar(character))

        self.updateElementsVisibility()

    def updateElementsVisibility(self):
        if not self.agenda:
            return
        # elements_visible = self.agenda.character_id is not None
        # self._btnCharacterDelegate.setVisible(not elements_visible)
        # self._wdgElements.setVisible(elements_visible)

        # self._emotionEditor.setVisible(self.novel.prefs.toggled(NovelSetting.Track_emotion))
        # self._motivationEditor.setVisible(self.novel.prefs.toggled(NovelSetting.Track_motivation))
        # self._conflictEditor.setVisible(self.novel.prefs.toggled(NovelSetting.Track_conflict))

    def _emotionChanged(self, emotion: int):
        self.agenda.emotion = emotion

    def _emotionReset(self):
        self.agenda.emotion = None

    def _motivationReset(self):
        self.agenda.motivations.clear()


class SceneAgencyEditor(QWidget, EventListener):
    agencyAdded = pyqtSignal()

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._scene: Optional[Scene] = None
        self._unsetCharacterSlot = None

        vbox(self)
        margins(self, left=15)

        self.btnAdd = push_btn(IconRegistry.plus_icon('grey'),
                               text='Track character goals, conflicts, or changes')
        self.btnAdd.setStyleSheet('QPushButton{color: grey; border: 0px;}')
        self.btnAdd.installEventFilter(OpacityEventFilter(self.btnAdd, leaveOpacity=0.7))
        self.btnAdd.setIconSize(QSize(26, 26))

        self.wdgAgendas = QWidget()
        flow(self.wdgAgendas, spacing=25)
        self.layout().addWidget(self.btnAdd, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.layout().addWidget(self.wdgAgendas)
        self.layout().addWidget(vspacer())

        self._menu = CharacterSelectorMenu(self._novel, self.btnAdd)
        self._menu.selected.connect(self._characterSelected)

        event_dispatchers.instance(self._novel).register(self, NovelEmotionTrackingToggleEvent,
                                                         NovelMotivationTrackingToggleEvent,
                                                         NovelConflictTrackingToggleEvent, CharacterDeletedEvent)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, NovelPanelCustomizationEvent):
            for i in range(self.wdgAgendas.layout().count()):
                item = self.wdgAgendas.layout().itemAt(i)
                wdg = item.widget()
                if wdg and isinstance(wdg, CharacterAgencyEditor):
                    wdg.updateElementsVisibility()
        elif isinstance(event, CharacterDeletedEvent):
            for i in range(self.wdgAgendas.layout().count()):
                wdg = self.wdgAgendas.layout().itemAt(i).widget()
                if isinstance(wdg, CharacterAgencyEditor) and event.character.id == wdg.agenda.character_id:
                    self._agencyRemoved(wdg)

    def setScene(self, scene: Scene):
        self._scene = scene
        clear_layout(self.wdgAgendas)
        for agenda in self._scene.agency:
            self.__initAgencyWidget(agenda)

    def setUnsetCharacterSlot(self, func):
        self._unsetCharacterSlot = func

    def updateAvailableCharacters(self):
        pass

    def povChangedEvent(self, pov: Character):
        pass

    def _characterSelected(self, character: Character):
        def finish():
            wdg.setGraphicsEffect(None)

        agency = CharacterAgency(character.id)
        self._scene.agency.append(agency)
        wdg = self.__initAgencyWidget(agency)
        qtanim.fade_in(wdg, teardown=finish)
        QTimer.singleShot(20, self.agencyAdded)

    def _agencyRemoved(self, wdg: CharacterAgencyEditor):
        agency = wdg.agenda
        self._scene.agency.remove(agency)
        fade_out_and_gc(self.wdgAgendas, wdg)

    def __initAgencyWidget(self, agenda: CharacterAgency) -> CharacterAgencyEditor:
        wdg = CharacterAgencyEditor(self._novel, self._scene, agenda)
        wdg.removed.connect(partial(self._agencyRemoved, wdg))
        self.wdgAgendas.layout().addWidget(wdg)

        return wdg
