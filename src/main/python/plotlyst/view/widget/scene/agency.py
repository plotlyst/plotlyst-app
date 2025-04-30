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
from typing import Dict, Optional, Tuple, Union

import qtanim
from PyQt6.QtCore import Qt, QEvent, pyqtSignal, QSize, QTimer, QMimeData
from PyQt6.QtGui import QEnterEvent, QCursor, QDragEnterEvent, QDragLeaveEvent, QResizeEvent
from PyQt6.QtWidgets import QWidget, QGridLayout, QButtonGroup, QAbstractButton, QFrame
from overrides import overrides
from qtanim import fade_in
from qthandy import hbox, spacer, sp, bold, vbox, translucent, clear_layout, margins, vspacer, \
    flow, retain_when_hidden, transparent, incr_icon, line, grid, decr_font, decr_icon
from qthandy.filter import OpacityEventFilter, DragEventFilter, DropEventFilter, VisibilityToggleEventFilter
from qtmenu import MenuWidget

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, PLOTLYST_TERTIARY_COLOR
from plotlyst.core.domain import Motivation, Novel, Scene, CharacterAgency, Character, StoryElementType, \
    StoryElement
from plotlyst.env import app_env
from plotlyst.event.core import Event, EventListener
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import NovelEmotionTrackingToggleEvent, \
    NovelMotivationTrackingToggleEvent, NovelConflictTrackingToggleEvent, CharacterDeletedEvent
from plotlyst.service.cache import entities_registry
from plotlyst.view.common import push_btn, label, fade_out_and_gc, tool_btn, action, shadow, frame, scroll_area, rows, \
    columns
from plotlyst.view.icons import IconRegistry, avatars
from plotlyst.view.layout import group
from plotlyst.view.style.base import apply_white_menu, transparent_menu
from plotlyst.view.widget.button import SelectorToggleButton, DotsMenuButton
from plotlyst.view.widget.character.editor import EmotionEditorSlider
from plotlyst.view.widget.characters import CharacterSelectorMenu
from plotlyst.view.widget.confirm import confirmed
from plotlyst.view.widget.display import ArrowButton, SeparatorLineWithShadow, ConnectorWidget, \
    MenuOverlayEventFilter, Icon, icon_text
from plotlyst.view.widget.input import RemovalButton, TextEditBubbleWidget
from plotlyst.view.widget.scene.conflict import ConflictIntensityEditor, CharacterConflictSelector
from plotlyst.view.widget.scene.motivation import MotivationDisplay, MotivationEditor, MotivationChargeLabel


class SceneAgendaEmotionEditor(QWidget):
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

        self.reset()

    def activate(self):
        self._activated = True
        self._slider.setVisible(True)
        self._icon.setText('')

    def reset(self):
        # super().reset()
        self._slider.setVisible(False)
        self._icon.setIcon(IconRegistry.from_name('mdi.emoticon-neutral', 'lightgrey'))
        self._icon.setText('Emotion')
        translucent(self._icon, 0.4)

    def setValue(self, value: int):
        self.activate()
        if self._slider.value() == value:
            self.emotionChanged.emit(value)
        else:
            self._slider.setValue(value)

    def _iconClicked(self):
        if not self._activated:
            self.setValue(5)
            qtanim.fade_in(self._slider, 150)

    def _valueChanged(self, value: int):
        self._icon.setIcon(IconRegistry.emotion_icon_from_feeling(value))
        self.emotionChanged.emit(value)


class SceneAgendaMotivationEditor(QWidget):
    motivationChanged = pyqtSignal(Motivation, int)

    def __init__(self, novel: Novel, scene: Scene, agency: CharacterAgency, parent=None):
        super().__init__(parent)
        hbox(self, 1, 1)

        self._motivationDisplay = MotivationDisplay(novel, scene, agency)
        self._motivationEditor = MotivationEditor()
        self._motivationEditor.motivationChanged.connect(self._valueChanged)

        self._wdgLabels = QWidget()
        flow(self._wdgLabels, 0, 0)
        self._labels: Dict[Motivation, MotivationChargeLabel] = {}

        self._icon = push_btn(IconRegistry.from_name('fa5s.fist-raised', 'lightgrey'), transparent_=True)

        self._menu = MenuWidget(self._icon)
        self._wdgEditor = columns()
        self._wdgEditor.layout().addWidget(self._motivationDisplay)
        self._wdgEditor.layout().addWidget(self._motivationEditor)
        apply_white_menu(self._menu)
        self._menu.addWidget(self._wdgEditor)

        self.layout().addWidget(self._icon, alignment=Qt.AlignmentFlag.AlignTop)
        self.layout().addWidget(self._wdgLabels)

        if agency.motivations:
            values = {Motivation(k): v for k, v in agency.motivations.items()}
            self._motivationEditor.setMotivations(values)
            for mot, v in values.items():
                if v:
                    self._updateLabels(mot, v)

    def _valueChanged(self, motivation: Motivation, value: int):
        self.motivationChanged.emit(motivation, value)
        self._updateLabels(motivation, value)
        self._motivationDisplay.refresh()

    def _updateLabels(self, motivation: Motivation, value: int):
        if motivation not in self._labels.keys():
            lbl = MotivationChargeLabel(motivation)
            self._labels[motivation] = lbl
            self._wdgLabels.layout().addWidget(lbl)
        if value:
            self._labels[motivation].setCharge(value)
        else:
            fade_out_and_gc(self._wdgLabels, self._labels.pop(motivation))


class SceneAgendaConflictEditor(QWidget):
    conflictReset = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self)

        self._novel: Optional[Novel] = None
        self._scene: Optional[Scene] = None
        self._agenda: Optional[CharacterAgency] = None

        self._icon.setIcon(IconRegistry.conflict_icon('lightgrey'))
        self._icon.setText('Conflict')
        # self._icon.installEventFilter(self._opacityFilter)

        self._sliderIntensity = ConflictIntensityEditor()
        self._sliderIntensity.intensityChanged.connect(self._intensityChanged)

        self._wdgConflicts = QWidget()
        hbox(self._wdgConflicts)

        self._wdgSliders = QWidget()
        hbox(self._wdgSliders).addWidget(self._sliderIntensity, alignment=Qt.AlignmentFlag.AlignLeft)
        # self._wdgSliders.layout().addWidget(self._btnReset, alignment=Qt.AlignmentFlag.AlignRight)

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

    def reset(self):
        # super().reset()
        self._wdgSliders.setVisible(False)
        self._wdgConflicts.setVisible(False)
        self._icon.setVisible(True)
        if self._agenda:
            self._agenda.intensity = 0
            self._agenda.conflict_references.clear()

    def setValue(self, value: int):
        self._sliderIntensity.setValue(value)
        self.activate()

    def _iconClicked(self):
        if not self._activated:
            self.setValue(1)
            qtanim.fade_in(self._sliderIntensity, 150)
            # self._btnReset.setVisible(True)

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


class _CharacterChangeSelectorToggle(SelectorToggleButton):
    hovered = pyqtSignal()
    left = pyqtSignal()

    def __init__(self, type_: StoryElementType, parent=None):
        super().__init__(minWidth=80, parent=parent)
        self.setIcon(IconRegistry.from_name(type_.icon()))
        self.setText(type_.displayed_name().replace(' ', '\n'))
        decr_icon(self, 4)
        if not app_env.is_mac():
            decr_font(self)

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        self.hovered.emit()

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        self.left.emit()


class AgencyElementWidget:
    def __init__(self):
        pass


class StoryElementConnector(ConnectorWidget, AgencyElementWidget):
    remove = pyqtSignal()

    def __init__(self, element: StoryElement, parent=None, removalEnabled: bool = False):
        super().__init__(parent)
        self.element = element
        self._removalEnabled = removalEnabled
        if self._removalEnabled:
            self._btnRemove = RemovalButton(self)
            self.installEventFilter(VisibilityToggleEventFilter(self._btnRemove, self))
            self._btnRemove.raise_()
            self._btnRemove.clicked.connect(self.remove)

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        if self._removalEnabled:
            self._btnRemove.setGeometry(self.width() - self._btnRemove.sizeHint().width(), 0,
                                        self._btnRemove.sizeHint().width(),
                                        self._btnRemove.sizeHint().height())


class StoryElementPreviewIcon(Icon):
    hovered = pyqtSignal()
    left = pyqtSignal()
    remove = pyqtSignal()

    def __init__(self, element: StoryElement, parent=None):
        super().__init__(parent)
        self.element = element
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        self.setText(element.type.displayed_name().replace(' ', '\n'))
        self.setIcon(IconRegistry.from_name(element.type.icon()))
        decr_font(self, 2)

        self._btnRemove = RemovalButton(self)
        self.installEventFilter(VisibilityToggleEventFilter(self._btnRemove, self))
        self._btnRemove.raise_()
        self._btnRemove.clicked.connect(self.remove)

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        self.hovered.emit()

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        self.left.emit()

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        self._btnRemove.setGeometry(self.width() - self._btnRemove.sizeHint().width(), 0,
                                    self._btnRemove.sizeHint().width(),
                                    self._btnRemove.sizeHint().height())


agency_element_mime_type = 'aplication/agency-element'


class _PlaceholderWidget(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    @overrides
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(agency_element_mime_type):
            event.accept()
            self.setStyleSheet(f'background: {PLOTLYST_TERTIARY_COLOR};')

    @overrides
    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self.setStyleSheet('')


class CharacterChangesSelectorPopup(MenuWidget):
    DEFAULT_DESC: str = "Reflect how a character changes or takes action that impacts the story"
    DEFAULT_ICON: str = 'ph.user-focus'
    INITIAL_COL: int = 1
    TRANSITION_COL: int = 2
    FINAL_COL: int = 3

    added = pyqtSignal(list)

    def __init__(self, agenda: CharacterAgency):  # agenda: CharacterAgency
        super().__init__()
        self.agenda = agenda
        transparent_menu(self)
        self._initialized = False
        self._selectors: Dict[StoryElementType, _CharacterChangeSelectorToggle] = {}

        self._dragged: Optional[StoryElementPreviewIcon] = None
        self._dropped: bool = False
        self._droppedRow: int = -1
        self._droppedCol: int = -1
        self._draggedRow: int = -1
        self._draggedCol: int = -1

        self.btnGroup = QButtonGroup()
        self.btnGroup.setExclusive(False)

        self.wdgFrame = frame()
        vbox(self.wdgFrame, 5)
        self.wdgFrame.setProperty('white-bg', True)
        self.wdgFrame.setProperty('large-rounded', True)

        self.wdgEditor = columns(5, 20)

        self.lblDesc = icon_text(self.DEFAULT_ICON, self.DEFAULT_DESC, opacity=0.8)
        self.wdgFrame.layout().addWidget(self.lblDesc, alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgFrame.layout().addWidget(self.wdgEditor)

        self.wdgTools = rows(0)
        self.wdgRightSide = rows(0)
        margins(self.wdgRightSide, top=50)
        self.wdgPreviewParent = frame()
        vbox(self.wdgPreviewParent)
        self.wdgPreviewParent.setProperty('muted-bg', True)
        self.wdgPreviewParent.setProperty('large-rounded', True)

        self.wdgRightSide.layout().addWidget(self.wdgPreviewParent)
        self.wdgEditor.layout().addWidget(self.wdgTools)
        self.wdgEditor.layout().addWidget(self.wdgRightSide)

        self.wdgSelectors = QWidget()
        grid(self.wdgSelectors, 0, 5, 2)
        scroll = scroll_area(h_on=False, frameless=True)
        scroll.setMaximumHeight(400)
        transparent(scroll)
        transparent(self.wdgSelectors)
        scroll.setWidget(self.wdgSelectors)

        self.wdgTools.layout().addWidget(scroll)

        self.wdgPreview = frame()
        sp(self.wdgPreview).v_max()
        grid(self.wdgPreview, 2, 5, 5)
        scrollPreview = scroll_area(h_on=False, frameless=True)
        transparent(scrollPreview)
        transparent(self.wdgPreview)
        scrollPreview.setMinimumWidth(200)
        scrollPreview.setWidget(self.wdgPreview)
        self.wdgPreviewParent.layout().addWidget(label('Preview', h5=True), alignment=Qt.AlignmentFlag.AlignCenter)

        self.wdgPreviewParent.layout().addWidget(scrollPreview)
        retain_when_hidden(self.wdgPreviewParent)
        self.wdgPreviewParent.setHidden(True)

        self._initPreview()

        self.wdgSelectors.layout().addWidget(label('Initial state', description=True, centered=True, decr_font_diff=1),
                                             0,
                                             self.INITIAL_COL)
        self.wdgSelectors.layout().addWidget(label('Transition', description=True, centered=True, decr_font_diff=1), 0,
                                             self.TRANSITION_COL)
        self.wdgSelectors.layout().addWidget(label('Final state', description=True, centered=True, decr_font_diff=1), 0,
                                             self.FINAL_COL)
        self.wdgSelectors.layout().addWidget(line(color='lightgrey'), 1, self.INITIAL_COL, 1, 3)

        row = 2
        self.selectorGoal, btnQuickAddGoal = self.__initSelector(StoryElementType.Goal, row, self.INITIAL_COL,
                                                                 quickAdd=True)
        self.selectorConflict = self.__initSelector(StoryElementType.Conflict, row, self.TRANSITION_COL)
        self.selectorOutcome = self.__initSelector(StoryElementType.Outcome, row, self.FINAL_COL)
        row += 1

        self.selectorDilemma, btnQuickAddDilemma = self.__initSelector(StoryElementType.Dilemma, row,
                                                                       self.TRANSITION_COL, quickAdd=True)
        self.selectorDecision = self.__initSelector(StoryElementType.Decision, row, self.FINAL_COL)
        row += 1

        self.selectorExpectation, btnQuickAddExpectation = self.__initSelector(StoryElementType.Expectation, row,
                                                                               self.INITIAL_COL, quickAdd=True)
        self.selectorRealization = self.__initSelector(StoryElementType.Realization, row, self.FINAL_COL)
        row += 1

        self.selectorEmotion, btnQuickAddEmotion = self.__initSelector(StoryElementType.Emotion, row, self.INITIAL_COL,
                                                                       quickAdd=True)
        self.selectorEmotionChange = self.__initSelector(StoryElementType.Emotion_change, row, self.FINAL_COL)
        row += 1

        self.selectorInternalState, btnQuickAddInternal = self.__initSelector(StoryElementType.Character_internal_state,
                                                                              row, self.INITIAL_COL, quickAdd=True)
        # self.selectorInternalConflict: _CharacterChangeSelectorToggle = self.__initSelector(
        #     StoryElementType.Internal_conflict, row, self.TRANSITION_COL)
        self.selectorInternalChange = self.__initSelector(StoryElementType.Character_internal_state_change, row,
                                                          self.FINAL_COL)
        row += 1

        self.selectorExternalState, btnQuickAddExternal = self.__initSelector(StoryElementType.Character_state, row,
                                                                              self.INITIAL_COL, quickAdd=True)
        self.selectorCatalyst = self.__initSelector(StoryElementType.Catalyst, row, self.TRANSITION_COL)
        self.selectorExternalChange: _CharacterChangeSelectorToggle = self.__initSelector(
            StoryElementType.Character_state_change, row, self.FINAL_COL)
        row += 1

        self.selectorAction, btnQuickAddAction = self.__initSelector(StoryElementType.Action, row, self.TRANSITION_COL,
                                                                     quickAdd=True)
        self.selectorImpact = self.__initSelector(StoryElementType.Impact, row, self.FINAL_COL)
        row += 1

        self.selectorMotivation = self.__initSelector(StoryElementType.Motivation, row, self.FINAL_COL)

        if self.agenda.elements:
            self.wdgPreviewParent.setVisible(True)

        for el in self.agenda.elements:
            if el.type != StoryElementType.Connector:
                self._selectors[el.type].setChecked(True)
            self.__initPreviewIcon(el, el.row, el.col)

        for row in range(2, self.wdgPreview.layout().rowCount()):
            self._fillInRow(row)

        btnQuickAddGoal.clicked.connect(
            lambda: self._quickSelect(self.selectorGoal, self.selectorConflict, self.selectorOutcome))
        btnQuickAddDilemma.clicked.connect(lambda: self._quickSelect(self.selectorDilemma, self.selectorDecision))
        btnQuickAddExpectation.clicked.connect(
            lambda: self._quickSelect(self.selectorExpectation, self.selectorRealization))
        btnQuickAddInternal.clicked.connect(
            lambda: self._quickSelect(self.selectorInternalState, self.selectorInternalChange))
        btnQuickAddEmotion.clicked.connect(
            lambda: self._quickSelect(self.selectorEmotion, self.selectorEmotionChange))
        btnQuickAddExternal.clicked.connect(
            lambda: self._quickSelect(self.selectorExternalState, self.selectorCatalyst, self.selectorExternalChange))
        btnQuickAddAction.clicked.connect(lambda: self._quickSelect(self.selectorAction, self.selectorImpact))

        self.addWidget(self.wdgFrame)

        self._initialized = True

    def _toggled(self, type_: StoryElementType, col: int, toggled: bool):
        if not self._initialized:
            return
        layout: QGridLayout = self.wdgPreview.layout()
        if toggled:
            row = self._nextRowToInsert(type_, col)
            item = layout.itemAtPosition(row, col)
            if item and item.widget():
                if isinstance(item.widget(), _PlaceholderWidget):
                    layout.removeWidget(item.widget())
                else:
                    row += 1

            element = StoryElement(type_, row=row, col=col)
            self.agenda.elements.append(element)

            wdg = self.__initPreviewIcon(element, row, col)
            fade_in(wdg)

            if type_ != StoryElementType.Emotion_change:
                self._checkForConnector(row, col, added=True)
            self._fillInRow(row)
        else:
            for el in self.agenda.elements:
                if el.type == type_:
                    item = layout.itemAtPosition(el.row, el.col)
                    fade_out_and_gc(self.wdgPreview, item.widget(), teardown=lambda: self._fillInRow(el.row))

                    self._checkForConnector(el.row, col, added=False)
                    self.agenda.elements.remove(el)

                    if el.type == StoryElementType.Motivation:
                        self.agenda.motivations.clear()
                    break

        self.wdgPreviewParent.setVisible(True)

    def _typeHovered(self, type_: StoryElementType):
        self.lblDesc.setIcon(IconRegistry.from_name(type_.icon(), PLOTLYST_SECONDARY_COLOR))
        self.lblDesc.setText(type_.placeholder())

    def _typeLeft(self):
        self.lblDesc.setIcon(IconRegistry.from_name(self.DEFAULT_ICON))
        self.lblDesc.setText(self.DEFAULT_DESC)

    def _nextRowToInsert(self, type_: StoryElementType, col: int):
        row = self.wdgPreview.layout().rowCount() - 1
        if col == self.INITIAL_COL and self._hasElement(row, self.TRANSITION_COL):
            if type_ == StoryElementType.Goal and self._hasElement(row, self.TRANSITION_COL, StoryElementType.Conflict):
                return row
            if type_ == StoryElementType.Expectation and self._hasElement(row, self.TRANSITION_COL,
                                                                          StoryElementType.Realization):
                return row
            row += 1

        return row

    def _hasElement(self, row: int, col: int, type_: Optional[StoryElementType] = None) -> bool:
        item = self.wdgPreview.layout().itemAtPosition(row, col)
        if item and item.widget() and isinstance(item.widget(), StoryElementPreviewIcon):
            if not type_ or item.widget().element.type == type_:
                return True

    def _elementAt(self, row: int, col: int) -> Optional[StoryElement]:
        item = self.wdgPreview.layout().itemAtPosition(row, col)
        if item and item.widget() and isinstance(item.widget(), StoryElementPreviewIcon):
            return StoryElement(item.widget().element)

    def _hasConnector(self, row: int, col: int) -> bool:
        item = self.wdgPreview.layout().itemAtPosition(row, col)
        if item and item.widget() and isinstance(item.widget(), StoryElementConnector):
            return True

    def _reset(self):
        if confirmed(f"Are you sure you want to reset this agency and remove all elements?", 'Reset character agency'):
            for btn in self.btnGroup.buttons():
                if btn.isChecked():
                    btn.setChecked(False)

            clear_layout(self.wdgPreview)
            self.agenda.elements.clear()
            self._initPreview()

    def _initPreview(self):
        self.wdgPreview.layout().addWidget(label('Initial state', description=True, centered=True), 0, 1,
                                           Qt.AlignmentFlag.AlignCenter)
        connector = ConnectorWidget()
        translucent(connector, 0.3)
        # self.wdgPreview.layout().addWidget(label('Transition', description=True, centered=True), 0, 2)
        self.wdgPreview.layout().addWidget(connector, 0, 2)
        self.wdgPreview.layout().addWidget(label('Final state', description=True, centered=True), 0, 3,
                                           Qt.AlignmentFlag.AlignCenter)
        self.wdgPreview.layout().addWidget(line(color='lightgrey'), 1, 1, 1, 3)

    def _fillInRow(self, row: int):
        for col in range(1, 4):
            if not self.wdgPreview.layout().itemAtPosition(row, col):
                wdg = _PlaceholderWidget()
                wdg.installEventFilter(
                    DropEventFilter(wdg, [agency_element_mime_type], droppedSlot=partial(self._droppedAt, row, col)))
                self.wdgPreview.layout().addWidget(wdg, row, col)

    def _checkForConnector(self, row: int, col: int, added: bool):
        if added:
            if col == self.FINAL_COL and self._hasElement(row, self.INITIAL_COL) and not self._hasElement(row,
                                                                                                          self.TRANSITION_COL):
                self._clearPlaceholder(row, self.TRANSITION_COL)
                connector = StoryElement(StoryElementType.Connector, row=row, col=self.TRANSITION_COL)
                self.agenda.elements.append(connector)
                self.__initPreviewIcon(connector, row, self.TRANSITION_COL)

        elif col == self.FINAL_COL and self._hasConnector(row, self.TRANSITION_COL):
            item = self.wdgPreview.layout().itemAtPosition(row, self.TRANSITION_COL)
            self.agenda.elements.remove(item.widget().element)
            fade_out_and_gc(self.wdgPreview, item.widget(), teardown=lambda: self._fillInRow(row))

    def _clearPlaceholder(self, row: int, col: int):
        item = self.wdgPreview.layout().itemAtPosition(row, col)
        if item and item.widget() and isinstance(item.widget(), _PlaceholderWidget):
            self.wdgPreview.layout().removeWidget(item.widget())

    def _deleteElement(self, wdg: Union[StoryElementPreviewIcon, ConnectorWidget], row: int, col: int):
        if wdg.element.type == StoryElementType.Connector:
            fade_out_and_gc(self.wdgPreview, wdg, teardown=lambda: self._fillInRow(row))
            self.agenda.elements.remove(wdg.element)
        else:
            self._selectors[wdg.element.type].setChecked(False)
            # self._toggled(wdg.element.type, col, False)

    def _quickSelect(self, *selectors):
        if all(x.isChecked() for x in selectors):
            for btn in selectors:
                btn.setChecked(False)
        else:
            for btn in selectors:
                btn.setChecked(True)

    def _dragStarted(self, wdg: StoryElementPreviewIcon, row: int, col: int):
        self._dragged = wdg
        self._dragged.setDisabled(True)
        self._draggedRow = row
        self._draggedCol = col

    def _droppedAt(self, row: int, col: int, mimeData: QMimeData):
        self._dropped = True
        self._droppedRow = row
        self._droppedCol = col

    def _dragFinished(self):
        if self._dropped:
            row = self._droppedRow
            col = self._droppedCol
            self._dragged.element.row = row
            self._dragged.element.col = col
            self._clearPlaceholder(row, col)
            self.__initPreviewIcon(self._dragged.element, row, col)
            self._checkForConnector(row, col, added=True)

            fade_out_and_gc(self.wdgPreview, self._dragged, teardown=lambda: self._fillInRow(self._draggedRow))
            self._checkForConnector(self._draggedRow, self._draggedCol, added=False)
            self._dropped = False
            self._droppedRow = -1
            self._droppedCol = -1
        else:
            self._dragged.setEnabled(True)
        self._dragged = None

    def __initSelector(self, type_: StoryElementType, row: int, col: int,
                       quickAdd: bool = False) -> Tuple[_CharacterChangeSelectorToggle, Optional[QAbstractButton]]:
        selector = _CharacterChangeSelectorToggle(type_)
        self._selectors[type_] = selector
        self.btnGroup.addButton(selector)

        selector.toggled.connect(partial(self._toggled, type_, col))
        selector.hovered.connect(partial(self._typeHovered, type_))
        selector.left.connect(self._typeLeft)

        self.wdgSelectors.layout().addWidget(selector, row, col, Qt.AlignmentFlag.AlignLeft)

        if quickAdd:
            btnQuickAdd = tool_btn(IconRegistry.from_name('mdi.check-all', 'grey'))
            decr_icon(btnQuickAdd, 4)
            btnQuickAdd.installEventFilter(OpacityEventFilter(btnQuickAdd, leaveOpacity=0.7))
            self.wdgSelectors.layout().addWidget(btnQuickAdd, row, 0)
            return selector, btnQuickAdd

        return selector

    def __initPreviewIcon(self, el: StoryElement, row: int, col: int) -> StoryElementPreviewIcon:
        if el.type == StoryElementType.Connector:
            wdg = StoryElementConnector(el, removalEnabled=True)
        else:
            wdg = StoryElementPreviewIcon(el)
            wdg.hovered.connect(partial(self._typeHovered, el.type))
            wdg.left.connect(self._typeLeft)
            wdg.installEventFilter(
                DragEventFilter(wdg, agency_element_mime_type, lambda x: wdg.element,
                                startedSlot=partial(self._dragStarted, wdg, row, col), finishedSlot=self._dragFinished))

        wdg.remove.connect(partial(self._deleteElement, wdg, row, col))
        self.wdgPreview.layout().addWidget(wdg, row, col, Qt.AlignmentFlag.AlignCenter)

        return wdg


class CharacterChangeBubble(TextEditBubbleWidget, AgencyElementWidget):
    def __init__(self, element: StoryElement, parent=None):
        super().__init__(parent)
        margins(self, left=1, right=1)
        self.element = element
        self.setProperty('large-rounded', True)
        self.setProperty('relaxed-white-bg', True)
        transparent(self._textedit)
        self.setMaximumWidth(170)
        self._textedit.setMaximumSize(165, 105)

        self._title.setIcon(IconRegistry.from_name(self.element.type.icon(), PLOTLYST_SECONDARY_COLOR))
        self._title.setText(self.element.type.displayed_name())
        bold(self._title, False)
        tip = self.element.type.placeholder()
        self._textedit.setPlaceholderText(tip)
        self._textedit.setToolTip(tip)
        self._textedit.setText(self.element.text)

        shadow(self)
        translucent(self._title, 0.7)

    def addBottomWidget(self, wdg: QWidget):
        self.layout().addWidget(wdg)

    @overrides
    def _textChanged(self):
        self.element.text = self._textedit.toPlainText()


class CharacterMotivationChange(CharacterChangeBubble):
    def __init__(self, novel: Novel, scene: Scene, agency: CharacterAgency, element: StoryElement, parent=None):
        super().__init__(element, parent)
        self._agency = agency

        self.motivationEditor = SceneAgendaMotivationEditor(novel, scene, agency)
        self.motivationEditor.motivationChanged.connect(self._motivationChanged)
        self.addBottomWidget(self.motivationEditor)

        self._textedit.setMaximumSize(165, 95)

    def _motivationChanged(self, motivation: Motivation, value: int):
        self._agency.motivations[motivation.value] = value


class CharacterEmotionChange(QFrame, AgencyElementWidget):
    def __init__(self, element: StoryElement, agency: CharacterAgency, parent=None):
        super().__init__(parent)
        self.element = element
        self.agency = agency
        vbox(self)

        self._icon = push_btn(IconRegistry.from_name('mdi.emoticon-neutral', 'lightgrey'), transparent_=True)
        incr_icon(self._icon, 12)
        self._icon.clicked.connect(self._displayEditor)

        self.layout().addWidget(self._icon, alignment=Qt.AlignmentFlag.AlignCenter)

        if not self.element.value:
            self.element.value = 5

        self._update()

    def _displayEditor(self):
        menu = MenuWidget()
        emotionSlider = EmotionEditorSlider()
        emotionSlider.setMaximumWidth(200)
        emotionSlider.setValue(self.element.value)
        emotionSlider.valueChanged.connect(self._emotionChanged)
        menu.addWidget(emotionSlider)

        menu.exec(self.mapToGlobal(self._icon.rect().topRight()))

    def _emotionChanged(self, value: int):
        self.element.value = value
        self._update()

    def _update(self):
        self._icon.setIcon(IconRegistry.emotion_icon_from_feeling(self.element.value))


class CharacterAgencyEditor(QWidget):
    removed = pyqtSignal()
    reset = pyqtSignal()

    def __init__(self, novel: Novel, scene: Scene, agenda: CharacterAgency, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.scene = scene
        self.agenda = agenda
        vbox(self, spacing=0)
        margins(self, left=15)
        self._charDisplay = tool_btn(IconRegistry.character_icon(), transparent_=True)
        self._charDisplay.setIconSize(QSize(36, 36))
        self._menuSelector: Optional[CharacterChangesSelectorPopup] = None
        self._menu = MenuWidget()
        self._menu.addAction(action('Edit agency', IconRegistry.edit_icon(), slot=self.openSelector))
        self._menu.addSeparator()
        self._menu.addAction(action('Reset agency', IconRegistry.from_name('ph.x-light'), slot=self.reset))
        self._menu.addAction(action('Remove agency', IconRegistry.trash_can_icon(), slot=self.removed))
        self._charDisplay.clicked.connect(lambda: self._menu.exec(QCursor.pos()))

        self.btnAdd = push_btn(IconRegistry.plus_icon('grey'), 'Track character changes', transparent_=True)
        self.btnAdd.installEventFilter(OpacityEventFilter(self.btnAdd, leaveOpacity=0.7))
        self.btnAdd.clicked.connect(self.openSelector)

        self.wdgElements = QWidget()
        grid(self.wdgElements)

        # self._btnDots = DotsMenuButton()
        # self._btnDots.clicked.connect(lambda: self._menu.exec(QCursor.pos()))

        self.layout().addWidget(self.wdgElements)
        # self.installEventFilter(VisibilityToggleEventFilter(self._btnDots, self))

        if self.agenda.character_id:
            character = entities_registry.character(str(self.agenda.character_id))
            if character:
                self._charDisplay.setIcon(avatars.avatar(character))

        self.refresh()

    def refresh(self):
        clear_layout(self.wdgElements)

        header1 = label('Initial', centered=True, description=True, incr_font_diff=1)
        header1.setFixedWidth(170)
        header3 = label('Final', centered=True, description=True, incr_font_diff=1)
        header3.setFixedWidth(170)

        btnDots = DotsMenuButton()
        btnDots.clicked.connect(lambda: self._menu.exec(QCursor.pos()))

        self.wdgElements.layout().addWidget(header1, 0, 1, Qt.AlignmentFlag.AlignBottom)
        self.wdgElements.layout().addWidget(group(self._charDisplay, self.btnAdd, margin=0, spacing=0), 0, 2, 1, 3)
        self.wdgElements.layout().addWidget(header3, 0, 5, Qt.AlignmentFlag.AlignBottom)
        self.wdgElements.layout().addWidget(btnDots, 0, 6, Qt.AlignmentFlag.AlignTop)
        self.wdgElements.layout().addWidget(SeparatorLineWithShadow(), 1, 1, 1, 5)

        for el in sorted(self.agenda.elements, key=lambda x: (x.row, x.col)):
            wdg = self.__initElementWidget(el)
            col = el.col
            if col == 2:
                col = 3
            elif col == 3:
                col = 5

            if el.type == StoryElementType.Connector:
                self.wdgElements.layout().addWidget(wdg, el.row, col - 1, 1, 3)
                continue

            self.wdgElements.layout().addWidget(wdg, el.row, col,
                                                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)

            if col == 3 and self._hasElement(el.row, 1):
                arrow = ArrowButton(Qt.Edge.RightEdge, readOnly=True)
                arrow.setState(arrow.STATE_MAX)
                incr_icon(arrow, 4)
                self.wdgElements.layout().addWidget(arrow, el.row, 2, Qt.AlignmentFlag.AlignCenter)

            if col == 5 and self._hasElement(el.row, 3):
                arrow = ArrowButton(Qt.Edge.RightEdge, readOnly=True)
                arrow.setState(1)
                incr_icon(arrow, 4)
                self.wdgElements.layout().addWidget(arrow, el.row, 4, Qt.AlignmentFlag.AlignCenter)

    def openSelector(self):
        def added():
            self._menuSelector.hide()
            self.refresh()
            self._menuSelector = None

        self._menuSelector = CharacterChangesSelectorPopup(self.agenda)
        self._menuSelector.installEventFilter(MenuOverlayEventFilter(self._menuSelector))
        self._menuSelector.aboutToHide.connect(added)
        self._menuSelector.exec(self.btnAdd.mapToGlobal(self.btnAdd.rect().bottomLeft()))

    def _emotionChanged(self, emotion: int):
        self.agenda.emotion = emotion

    def _hasElement(self, row: int, col: int) -> bool:
        item = self.wdgElements.layout().itemAtPosition(row, col)
        if item and item.widget() and isinstance(item.widget(), CharacterChangeBubble):
            return True

    def __initElementWidget(self, element: StoryElement) -> AgencyElementWidget:
        if element.type == StoryElementType.Connector:
            wdg = StoryElementConnector(element)
        elif element.type == StoryElementType.Motivation:
            wdg = CharacterMotivationChange(self.novel, self.scene, self.agenda, element)
        elif element.type == StoryElementType.Emotion or element.type == StoryElementType.Emotion_change:
            wdg = CharacterEmotionChange(element, self.agenda)
        else:
            wdg = CharacterChangeBubble(element)

        return wdg


class SceneAgencyEditor(QWidget, EventListener):
    agencyAdded = pyqtSignal(CharacterAgencyEditor)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._scene: Optional[Scene] = None
        self._unsetCharacterSlot = None

        vbox(self)
        margins(self, left=15)

        self.btnAdd = push_btn(IconRegistry.plus_icon('grey'),
                               text='Add new character agency')
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
        # if isinstance(event, NovelPanelCustomizationEvent):
        #     for i in range(self.wdgAgendas.layout().count()):
        #         item = self.wdgAgendas.layout().itemAt(i)
        #         wdg = item.widget()
        #         if wdg and isinstance(wdg, CharacterAgencyEditor):
        #             wdg.updateElementsVisibility()
        if isinstance(event, CharacterDeletedEvent):
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
        QTimer.singleShot(20, lambda: self.agencyAdded.emit(wdg))
        QTimer.singleShot(70, wdg.openSelector)

    def _agencyRemoved(self, wdg: CharacterAgencyEditor):
        if confirmed(f"Are you sure you want to delete this agency?", 'Delete character agency'):
            agency = wdg.agenda
            self._scene.agency.remove(agency)
            fade_out_and_gc(self.wdgAgendas, wdg)

    def _agencyReset(self, wdg: CharacterAgencyEditor):
        if confirmed(f"Are you sure you want to reset this agency and remove all elements?", 'Reset character agency'):
            wdg.agenda.elements.clear()
            wdg.refresh()

    def __initAgencyWidget(self, agenda: CharacterAgency) -> CharacterAgencyEditor:
        wdg = CharacterAgencyEditor(self._novel, self._scene, agenda)
        wdg.removed.connect(partial(self._agencyRemoved, wdg))
        wdg.reset.connect(partial(self._agencyReset, wdg))
        self.wdgAgendas.layout().addWidget(wdg)

        return wdg
