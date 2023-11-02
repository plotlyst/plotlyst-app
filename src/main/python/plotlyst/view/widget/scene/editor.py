"""
Plotlyst
Copyright (C) 2021-2023  Zsolt Kovari

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
from typing import List, Optional, Dict

import qtanim
from PyQt6.QtCore import Qt, QSize, QEvent, pyqtSignal, QObject
from PyQt6.QtGui import QEnterEvent, QIcon, QMouseEvent, QColor, QCursor, QPalette, QPaintEvent, QPainter, QPen
from PyQt6.QtWidgets import QWidget, QTextEdit, QPushButton, QLabel, QFrame, QStackedWidget, QGridLayout, \
    QToolButton, QAbstractButton, QScrollArea, QButtonGroup
from overrides import overrides
from qthandy import vbox, vspacer, transparent, sp, line, incr_font, hbox, pointy, vline, retain_when_hidden, margins, \
    spacer, underline, bold, grid, gc, clear_layout, ask_confirmation, decr_icon, italic
from qthandy.filter import OpacityEventFilter, DisabledClickEventFilter
from qtmenu import MenuWidget

from src.main.python.plotlyst.common import raise_unrecognized_arg, CONFLICT_SELF_COLOR, RELAXED_WHITE_COLOR
from src.main.python.plotlyst.core.domain import Scene, Novel, ScenePurpose, advance_story_scene_purpose, \
    ScenePurposeType, reaction_story_scene_purpose, character_story_scene_purpose, setup_story_scene_purpose, \
    emotion_story_scene_purpose, exposition_story_scene_purpose, scene_purposes, Character, StoryElement, \
    StoryElementType, SceneOutcome, SceneStructureAgenda, Motivation, Plot
from src.main.python.plotlyst.event.core import EventListener, Event, emit_event
from src.main.python.plotlyst.event.handler import event_dispatchers
from src.main.python.plotlyst.events import SceneChangedEvent
from src.main.python.plotlyst.service.persistence import RepositoryPersistenceManager
from src.main.python.plotlyst.view.common import DelayedSignalSlotConnector, action, wrap, label, scrolled, \
    ButtonPressResizeEventFilter, push_btn, tool_btn, insert_before_the_end, fade_out_and_gc
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.layout import group
from src.main.python.plotlyst.view.widget.characters import CharacterSelectorButton
from src.main.python.plotlyst.view.widget.display import Icon
from src.main.python.plotlyst.view.widget.input import RemovalButton
from src.main.python.plotlyst.view.widget.plot import StorylineSelectorMenu
from src.main.python.plotlyst.view.widget.scene.agency import SceneAgendaEmotionEditor, SceneAgendaMotivationEditor, \
    SceneAgendaConflictEditor
from src.main.python.plotlyst.view.widget.scenes import SceneOutcomeSelector


class SceneMiniEditor(QWidget, EventListener):

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._scenes: List[Scene] = []
        self._currentScene: Optional[Scene] = None

        self._lblScene = QLabel()
        incr_font(self._lblScene, 2)
        self._btnScenes = QPushButton()
        incr_font(self._btnScenes, 2)
        transparent(self._btnScenes)
        sp(self._btnScenes).h_max()
        sp(self._lblScene).h_max()
        self._menuScenes = MenuWidget(self._btnScenes)

        self._charSelector = CharacterSelectorButton(self._novel, self, opacityEffectEnabled=False, iconSize=24)
        self._charSelector.setToolTip('Point of view character')
        decr_icon(self._charSelector)
        self._charSelector.characterSelected.connect(self._povChanged)

        self._textSynopsis = QTextEdit()
        self._textSynopsis.setProperty('white-bg', True)
        self._textSynopsis.setProperty('rounded', True)
        self._textSynopsis.setPlaceholderText('Write a short summary of this scene')
        self._textSynopsis.setMaximumSize(200, 200)

        self._layout = vbox(self)
        self._layout.addWidget(self._charSelector, alignment=Qt.AlignmentFlag.AlignLeft)
        self._layout.addWidget(self._btnScenes, alignment=Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self._lblScene, alignment=Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(line())
        self._layout.addWidget(label('Synopsis:', underline=True), alignment=Qt.AlignmentFlag.AlignLeft)
        self._layout.addWidget(self._textSynopsis)
        self._layout.addWidget(vspacer())

        DelayedSignalSlotConnector(self._textSynopsis.textChanged, self._save, parent=self)

        self._repo = RepositoryPersistenceManager.instance()
        dispatcher = event_dispatchers.instance(self._novel)
        dispatcher.register(self, SceneChangedEvent)

    def setScene(self, scene: Scene):
        self.setScenes([scene])

    def setScenes(self, scenes: List[Scene]):
        self.reset()
        self._scenes.extend(scenes)

        if len(self._scenes) > 1:
            for scene in scenes:
                self._menuScenes.addAction(action(
                    scene.title_or_index(self._novel), slot=partial(self.selectScene, scene)
                ))

        self._lblScene.setVisible(len(self._scenes) == 1)
        self._btnScenes.setVisible(len(self._scenes) > 1)

        if self._scenes:
            self.selectScene(self._scenes[0])

    def selectScene(self, scene: Scene):
        self._save()
        self._currentScene = None
        if len(self._scenes) > 1:
            self._btnScenes.setText(scene.title_or_index(self._novel))
        else:
            self._lblScene.setText(scene.title_or_index(self._novel))
        self._textSynopsis.setText(scene.synopsis)
        if scene.pov:
            self._charSelector.setCharacter(scene.pov)
        else:
            self._charSelector.clear()
        self._currentScene = scene

    def reset(self):
        self._save()
        self._currentScene = None
        self._scenes.clear()
        self._charSelector.clear()
        self._btnScenes.setText('')
        self._menuScenes.clear()
        self._textSynopsis.clear()

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, SceneChangedEvent):
            if event.scene is self._currentScene:
                self.selectScene(self._currentScene)

    def _povChanged(self, character: Character):
        self._currentScene.pov = character
        self._repo.update_scene(self._currentScene)
        emit_event(self._novel, SceneChangedEvent(self, self._currentScene))

    def _save(self):
        if self._currentScene and self._currentScene.synopsis != self._textSynopsis.toPlainText():
            self._currentScene.synopsis = self._textSynopsis.toPlainText()
            self._repo.update_scene(self._currentScene)
            emit_event(self._novel, SceneChangedEvent(self, self._currentScene))


def purpose_icon(purpose_type: ScenePurposeType) -> QIcon:
    if purpose_type == ScenePurposeType.Story:
        return IconRegistry.action_scene_icon()
    elif purpose_type == ScenePurposeType.Reaction:
        return IconRegistry.reaction_scene_icon()
    elif purpose_type == ScenePurposeType.Character:
        return IconRegistry.character_development_scene_icon()
    elif purpose_type == ScenePurposeType.Emotion:
        return IconRegistry.emotion_scene_icon()
    elif purpose_type == ScenePurposeType.Setup:
        return IconRegistry.setup_scene_icon()
    elif purpose_type == ScenePurposeType.Exposition:
        return IconRegistry.exposition_scene_icon()
    else:
        raise_unrecognized_arg(purpose_type)


class ScenePurposeTypeButton(QPushButton):
    reset = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene: Optional[Scene] = None
        pointy(self)
        self._opacityFilter = OpacityEventFilter(self, 0.8, 1.0, ignoreCheckedButton=True)
        self.installEventFilter(self._opacityFilter)

        self._menu = MenuWidget(self)
        self._menu.addAction(action('Select new purpose', slot=self.reset.emit))

        self.refresh()

    def setScene(self, scene: Scene):
        self._scene = scene
        self.refresh()

    def refresh(self):
        if self._scene is None or self._scene.purpose is None:
            return
        IconRegistry.action_scene_icon()
        if self._scene.purpose == ScenePurposeType.Other:
            self.setText('Purpose...')
            self.setToolTip('Scene purpose not selected')
            self.setIcon(QIcon())
        else:
            purpose = scene_purposes.get(self._scene.purpose)
            tip = purpose.display_name.replace('\n', ' ')
            self.setText(tip)
            self.setToolTip(f'Scene purpose: {tip}')

        if self._scene.purpose == ScenePurposeType.Exposition:
            self.setIcon(IconRegistry.exposition_scene_icon())
        elif self._scene.purpose == ScenePurposeType.Setup:
            self.setIcon(IconRegistry.setup_scene_icon())
        elif self._scene.purpose == ScenePurposeType.Character:
            self.setIcon(IconRegistry.character_development_scene_icon())
        elif self._scene.purpose == ScenePurposeType.Emotion:
            self.setIcon(IconRegistry.emotion_scene_icon())

        if self._scene.purpose == ScenePurposeType.Other:
            italic(self, True)
            bold(self, False)
        else:
            bold(self, True)
            italic(self, False)

        if self._scene.purpose == ScenePurposeType.Story:
            bgColor = '#f4978e'
            borderColor = '#fb5607'
            resolution = self._scene.outcome == SceneOutcome.RESOLUTION
            trade_off = self._scene.outcome == SceneOutcome.TRADE_OFF
            motion = self._scene.outcome == SceneOutcome.MOTION

            self.setIcon(IconRegistry.action_scene_icon(resolution, trade_off, motion))
            if resolution:
                bgColor = '#12BB86'
                borderColor = '#0b6e4f'
            elif trade_off:
                bgColor = '#E188C2'
                borderColor = '#832161'
            elif motion:
                bgColor = '#E0BD9B'
                borderColor = '#D7AA7D'
        elif self._scene.purpose == ScenePurposeType.Reaction:
            bgColor = '#89c2d9'
            borderColor = '#1a759f'
            self.setIcon(IconRegistry.reaction_scene_icon())
        elif self._scene.purpose == ScenePurposeType.Other:
            bgColor = 'lightgrey'
            borderColor = 'grey'
        else:
            bgColor = 'darkGrey'
            borderColor = 'grey'

        self.setStyleSheet(f'''
            QPushButton {{
                background: {bgColor};
                border: 2px solid {borderColor};
                border-radius: 8px;
                padding: 2px;
            }}
            QPushButton::menu-indicator{{
                width:0px;
            }}
            ''')


class ScenePurposeWidget(QFrame):
    clicked = pyqtSignal()

    def __init__(self, purpose: ScenePurpose, parent=None):
        super().__init__(parent)
        self._purpose = purpose
        self.setMinimumWidth(150)
        self.setMaximumWidth(190)

        self._icon = Icon()
        self._icon.setIcon(purpose_icon(self._purpose.type))
        self._icon.setIconSize(QSize(64, 64))
        self._icon.setDisabled(True)
        self._icon.installEventFilter(self)
        self._title = QLabel(self._purpose.display_name)
        self._title.setProperty('h4', True)
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._wdgInfo = QWidget(self)
        vbox(self._wdgInfo)
        if self._purpose.type == ScenePurposeType.Story or self._purpose.type == ScenePurposeType.Character:
            margins(self._wdgInfo, top=20)
        else:
            margins(self._wdgInfo, top=40)

        if self._purpose.keywords:
            self._wdgInfo.layout().addWidget(label('Keywords:', underline=True))
            keywords = ', '.join(self._purpose.keywords)
            lbl = label(keywords, description=True, wordWrap=True)
            self._wdgInfo.layout().addWidget(wrap(lbl, margin_left=5))
        if self._purpose.pacing:
            lbl = label('Pacing:', underline=True)
            self._wdgInfo.layout().addWidget(wrap(lbl, margin_top=10))
            lbl = label(self._purpose.pacing, description=True)
            self._wdgInfo.layout().addWidget(wrap(lbl, margin_left=5))
        if self._purpose.include:
            lbl = label('May include:', underline=True)
            icons = QWidget()
            icons.setToolTip(self._purpose.help_include)
            hbox(icons, 0, 3)
            margins(icons, left=5)
            for type in self._purpose.include:
                icon = Icon()
                icon.setIcon(purpose_icon(type))
                icon.setDisabled(True)
                icon.setToolTip(scene_purposes[type].display_name)
                icons.layout().addWidget(icon)
            icons.layout().addWidget(spacer())
            self._wdgInfo.layout().addWidget(wrap(lbl, margin_top=10))
            self._wdgInfo.layout().addWidget(icons)

        self._wdgInfo.setHidden(True)
        retain_when_hidden(self._wdgInfo)

        pointy(self)
        vbox(self)
        self.layout().addWidget(self._icon, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._title, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._wdgInfo)
        self.layout().addWidget(vspacer())

        self.installEventFilter(OpacityEventFilter(self))

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress:
            self.mousePressEvent(event)
            return False
        elif event.type() == QEvent.Type.MouseButtonRelease:
            self.mouseReleaseEvent(event)
            return False
        return super().eventFilter(watched, event)

    @overrides
    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._setBgColor(0.1)
        event.accept()

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._setBgColor()
        event.accept()
        self.clicked.emit()

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        self._icon.setEnabled(True)
        self._setBgColor()
        self._wdgInfo.setVisible(True)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        self._icon.setDisabled(True)
        self._wdgInfo.setHidden(True)
        self.setStyleSheet('')

    def _setBgColor(self, opacity: float = 0.04):
        if self._purpose.type == ScenePurposeType.Story:
            self._bgRgb = '254, 74, 73'
        elif self._purpose.type == ScenePurposeType.Reaction:
            self._bgRgb = '75, 134, 180'
        else:
            self._bgRgb = '144, 151, 156'
        self.setStyleSheet(f'ScenePurposeWidget {{background-color: rgba({self._bgRgb}, {opacity});}}')


class ScenePurposeSelectorWidget(QWidget):
    skipped = pyqtSignal()
    selected = pyqtSignal(ScenePurpose)

    def __init__(self, parent=None):
        super().__init__(parent)

        vbox(self)
        self._btnSkip = QPushButton('Ignore')
        self._btnSkip.setIcon(IconRegistry.from_name('ri.share-forward-fill'))
        underline(self._btnSkip)
        transparent(self._btnSkip)
        pointy(self._btnSkip)
        self._btnSkip.installEventFilter(OpacityEventFilter(self._btnSkip))
        self._btnSkip.installEventFilter(ButtonPressResizeEventFilter(self._btnSkip))
        self._btnSkip.clicked.connect(self.skipped.emit)
        self.layout().addWidget(self._btnSkip, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(label("Select the scene's main purpose:", bold=True),
                                alignment=Qt.AlignmentFlag.AlignCenter)

        self._scrollarea, self._wdgPurposes = scrolled(self, frameless=True)
        self._wdgPurposes.setProperty('relaxed-white-bg', True)
        sp(self._scrollarea).h_exp().v_exp()
        sp(self._wdgPurposes).h_exp().v_exp()
        hbox(self._wdgPurposes, 0, 0)
        margins(self._wdgPurposes, top=10)

        self._wdgPurposes.layout().addWidget(spacer())
        for purpose in [advance_story_scene_purpose, reaction_story_scene_purpose, character_story_scene_purpose,
                        setup_story_scene_purpose, emotion_story_scene_purpose, exposition_story_scene_purpose]:
            wdg = ScenePurposeWidget(purpose)
            wdg.clicked.connect(partial(self.selected.emit, purpose))
            self._wdgPurposes.layout().addWidget(wdg)
        self._wdgPurposes.layout().insertWidget(3, vline())
        self._wdgPurposes.layout().addWidget(spacer())


class ArrowButton(QToolButton):
    stateChanged = pyqtSignal(int)
    stateReset = pyqtSignal()

    STATE_MAX: int = 3

    def __init__(self, edge: Qt.Edge, parent=None):
        super().__init__(parent)
        self._state: int = 0
        self._edge = edge
        if edge == Qt.Edge.RightEdge:
            self._icons = ['fa5s.arrow-right', 'fa5s.arrow-right', 'fa5s.arrow-left', 'fa5s.arrows-alt-h']
        elif edge == Qt.Edge.BottomEdge:
            self._icons = ['fa5s.arrow-down', 'fa5s.arrow-down', 'fa5s.arrow-up', 'fa5s.arrows-alt-v']
        pointy(self)
        transparent(self)
        self.setToolTip('Click to change direction')
        self.setCheckable(True)

        self.clicked.connect(self._clicked)
        self.reset()

    def setState(self, state: int):
        self._state = state
        self._handleNewState()

    def reset(self):
        self._state = 0
        self.setIconSize(QSize(15, 15))
        self.setIcon(IconRegistry.from_name(self._icons[self._state], 'lightgrey'))
        self.setChecked(False)

    def _increaseState(self):
        self._state += 1
        self._handleNewState()
        self.stateChanged.emit(self._state)

    def _handleNewState(self):
        self.setIconSize(QSize(22, 22))
        self.setIcon(IconRegistry.from_name(self._icons[self._state], 'black'))
        self.setChecked(True)

    def _clicked(self):
        if self._state == self.STATE_MAX:
            self.reset()
            self.stateReset.emit()
        else:
            self._increaseState()


class SceneElementWidget(QWidget):
    storylineSelected = pyqtSignal(Plot)
    storylineEditRequested = pyqtSignal(Plot)

    def __init__(self, novel: Novel, type: StoryElementType, row: int, col: int, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._type = type
        self._row = row
        self._col = col
        self._scene: Optional[Scene] = None
        self._element: Optional[StoryElement] = None
        self._gridLayout: QGridLayout = grid(self, 0, 2, 2)

        self._btnClose = RemovalButton()
        retain_when_hidden(self._btnClose)
        self._btnClose.clicked.connect(self._deactivate)

        self._storylineLinkEnabled = self._type in [StoryElementType.Event, StoryElementType.Effect]

        self._btnStorylineLink = tool_btn(IconRegistry.storylines_icon(color='lightgrey'), transparent_=True,
                                          tooltip='Link storyline to this element',
                                          parent=self)
        self._btnStorylineLink.installEventFilter(OpacityEventFilter(self._btnStorylineLink, leaveOpacity=0.7))
        self._btnStorylineLink.setVisible(False)
        retain_when_hidden(self._btnStorylineLink)

        if self._storylineLinkEnabled:
            self._storylineMenu = StorylineSelectorMenu(self._novel, self._btnStorylineLink)
            self._storylineMenu.storylineSelected.connect(self._storylineSelected)

        self._arrows: Dict[int, ArrowButton] = {
            90: ArrowButton(Qt.Edge.RightEdge),
            180: ArrowButton(Qt.Edge.BottomEdge),
        }
        for degree, arrow in self._arrows.items():
            retain_when_hidden(arrow)
            arrow.setHidden(True)
            arrow.stateChanged.connect(partial(self._arrowToggled, degree))
            arrow.stateReset.connect(partial(self._arrowReset, degree))
        self._gridLayout.addWidget(self._arrows[90], 1, 2, 2, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        self._gridLayout.addWidget(self._arrows[180], 2, 1, alignment=Qt.AlignmentFlag.AlignCenter)

        self._stackWidget = QStackedWidget(self)
        self._gridLayout.addWidget(self._stackWidget, 1, 1)

        self._pageIdle = QWidget()
        self._pageIdle.installEventFilter(OpacityEventFilter(self._pageIdle))
        self._pageIdle.installEventFilter(self)
        self._pageEditor = QWidget()
        self._stackWidget.addWidget(self._pageIdle)
        self._stackWidget.addWidget(self._pageEditor)

        self._icon: Optional[QIcon] = None
        self._colorActive: Optional[QColor] = None
        self._iconActive = Icon()
        self._iconIdle = Icon()
        self._iconIdle.setIconSize(QSize(48, 48))
        self._iconIdle.setIcon(IconRegistry.from_name('msc.debug-stackframe-dot', 'lightgrey'))
        self._iconIdle.clicked.connect(self.activate)
        self._titleActive = label('', bold=True)
        self._titleIdle = label('', description=True, italic=True, h4=True)
        self._titleIdle.setHidden(True)

        vbox(self._pageIdle)
        vbox(self._pageEditor)

        self._wdgTitle = QWidget()
        hbox(self._wdgTitle)
        self._wdgTitle.layout().addWidget(self._btnStorylineLink, alignment=Qt.AlignmentFlag.AlignLeft)
        self._wdgTitle.layout().addWidget(group(self._iconActive, self._titleActive),
                                          alignment=Qt.AlignmentFlag.AlignCenter)
        self._wdgTitle.layout().addWidget(self._btnClose, alignment=Qt.AlignmentFlag.AlignRight)
        self._pageEditor.layout().addWidget(self._wdgTitle)

        self._pageIdle.layout().addWidget(self._iconIdle, alignment=Qt.AlignmentFlag.AlignCenter)
        self._pageIdle.layout().addWidget(self._titleIdle, alignment=Qt.AlignmentFlag.AlignCenter)

        self._lblClick = label('Click to add', underline=True, description=True)
        retain_when_hidden(self._lblClick)
        self._lblClick.setHidden(True)
        self._pageIdle.layout().addWidget(self._lblClick, alignment=Qt.AlignmentFlag.AlignCenter)
        self._pageIdle.layout().addWidget(vspacer())

        self.reset()

    def element(self) -> Optional[StoryElement]:
        return self._element

    def setScene(self, scene: Scene):
        self._scene = scene
        self.reset()

    @overrides
    def eventFilter(self, watched: 'QObject', event: 'QEvent') -> bool:
        if event.type() == QEvent.Type.MouseButtonRelease:
            self.activate()

        return super().eventFilter(watched, event)

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        if self._stackWidget.currentWidget() == self._pageIdle:
            self._lblClick.setVisible(True)
            self._titleIdle.setVisible(True)
            self._iconIdle.setIcon(self._icon)
        else:
            if self._storylineLinkEnabled:
                self._btnStorylineLink.setVisible(True)
            self._btnClose.setVisible(True)
            for arrow in self._arrows.values():
                arrow.setVisible(True)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        if self._stackWidget.currentWidget() == self._pageIdle:
            self._lblClick.setVisible(False)
            self._titleIdle.setVisible(False)
            self._iconIdle.setIcon(IconRegistry.from_name('msc.debug-stackframe-dot', 'lightgrey'))
        else:
            for arrow in self._arrows.values():
                if not arrow.isChecked():
                    arrow.setHidden(True)
            self._btnClose.setVisible(False)
            if not self._element.ref:
                self._btnStorylineLink.setVisible(False)

    def setIcon(self, icon: str, colorActive: str = 'black'):
        self._icon = IconRegistry.from_name(icon, 'lightgrey')
        self._colorActive = QColor(colorActive)
        self._iconActive.setIcon(IconRegistry.from_name(icon, colorActive))

    def setTitle(self, text: str, color: Optional[str] = None):
        self._titleActive.setText(text)
        self._titleIdle.setText(text)
        if color:
            self._titleActive.setStyleSheet(f'color: {color};')
        else:
            self._titleActive.setStyleSheet('')

    def setElement(self, element: StoryElement):
        self._element = element

        self._pageIdle.setDisabled(True)
        self._stackWidget.setCurrentWidget(self._pageEditor)

        for arrow in self._arrows.values():
            arrow.reset()

        for degree, state in self._element.arrows.items():
            if state > 0:
                self._arrows[degree].setState(state)
                self._arrows[degree].setVisible(True)

        if self._element.ref:
            storyline = next((x for x in self._novel.plots if x.id == self._element.ref), None)
            if storyline is not None:
                self._btnStorylineLink.setIcon(IconRegistry.from_name(storyline.icon, storyline.icon_color))
                self._btnStorylineLink.setVisible(True)

    def reset(self):
        self._btnClose.setHidden(True)
        self._pageIdle.setEnabled(True)
        self._stackWidget.setCurrentWidget(self._pageIdle)
        self._lblClick.setVisible(False)
        self._titleIdle.setVisible(False)
        self._iconIdle.setIcon(IconRegistry.from_name('msc.debug-stackframe-dot', 'lightgrey'))
        self._btnStorylineLink.setIcon(IconRegistry.storylines_icon(color='lightgrey'))
        pointy(self._pageIdle)
        self._element = None

        for arrow in self._arrows.values():
            arrow.reset()
            arrow.setHidden(True)

    def activate(self):
        element = StoryElement(self._type)
        self.setElement(element)
        self._btnClose.setVisible(True)
        if self._storylineLinkEnabled:
            self._btnStorylineLink.setVisible(True)

        qtanim.glow(self._iconActive, duration=150, color=self._colorActive)
        self._elementCreated(element)

    def _deactivate(self):
        self._elementRemoved(self._element)
        self.reset()

    def _storyElements(self) -> List[StoryElement]:
        return self._scene.story_elements

    def _elementCreated(self, element: StoryElement):
        element.row = self._row
        element.col = self._col
        self._storyElements().append(element)

    def _elementRemoved(self, element: StoryElement):
        self._storyElements().remove(element)

    def _storylineSelected(self, storyline: Plot):
        self._element.ref = storyline.id
        self._btnStorylineLink.setIcon(IconRegistry.from_name(storyline.icon, storyline.icon_color))
        qtanim.glow(self._btnStorylineLink, color=QColor(storyline.icon_color))

        self.storylineSelected.emit(storyline)

        self._btnStorylineLink.clicked.disconnect()
        gc(self._storylineMenu)
        self._storylineMenu = MenuWidget(self._btnStorylineLink)
        self._storylineMenu.addAction(
            action('Edit', IconRegistry.edit_icon(), slot=partial(self.storylineEditRequested.emit, storyline)))
        self._storylineMenu.addSeparator()
        self._storylineMenu.addAction(action('Remove', IconRegistry.trash_can_icon(), slot=self._storylineRemoved))

    def _storylineRemoved(self):
        self._element.ref = None
        self._btnStorylineLink.setIcon(IconRegistry.storylines_icon(color='lightgrey'))

        self._btnStorylineLink.clicked.disconnect()
        gc(self._storylineMenu)
        self._storylineMenu = StorylineSelectorMenu(self._novel, self._btnStorylineLink)
        self._storylineMenu.storylineSelected.connect(self._storylineSelected)

    def _arrowToggled(self, degree: int, state: int):
        self._element.arrows[degree] = state

    def _arrowReset(self, degree: int):
        self._element.arrows[degree] = 0


class TextBasedSceneElementWidget(SceneElementWidget):
    def __init__(self, novel: Novel, type: StoryElementType, row: int, col: int, parent=None):
        super().__init__(novel, type, row, col, parent)
        self.setMaximumWidth(210)

        self._textEditor = QTextEdit()
        self._textEditor.setMinimumWidth(170)
        self._textEditor.setMaximumWidth(200)
        self._textEditor.setMinimumHeight(80)
        self._textEditor.setMaximumHeight(100)
        self._textEditor.setTabChangesFocus(True)
        self._textEditor.setAcceptRichText(False)
        self._textEditor.verticalScrollBar().setHidden(True)
        self._textEditor.setProperty('rounded', True)
        self._textEditor.setProperty('white-bg', True)
        self._textEditor.textChanged.connect(self._textChanged)

        self._pageEditor.layout().addWidget(self._textEditor, alignment=Qt.AlignmentFlag.AlignCenter)

    def setPlaceholderText(self, text: str):
        self._textEditor.setPlaceholderText(text)

    @overrides
    def setElement(self, element: StoryElement):
        super().setElement(element)
        self._textEditor.setText(element.text)

    def _textChanged(self):
        if self._element:
            self._element.text = self._textEditor.toPlainText()

    @overrides
    def activate(self):
        super().activate()
        anim = qtanim.fade_in(self._textEditor, duration=150)
        anim.finished.connect(self._activateFinished)

    def _activateFinished(self):
        qtanim.glow(self._textEditor, color=self._colorActive)


class SceneOutcomeEditor(QWidget):
    outcomeChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene: Optional[Scene] = None

        hbox(self)

        self._icon = push_btn(IconRegistry.disaster_icon('lightgrey', 'lightgrey'), transparent_=True)
        self._icon.setIconSize(QSize(28, 28))
        self._icon.installEventFilter(OpacityEventFilter(self._icon, leaveOpacity=0.8))
        self._icon.clicked.connect(self._iconClicked)

        self._btnReset = RemovalButton()
        self._btnReset.clicked.connect(self._resetClicked)
        retain_when_hidden(self._btnReset)

        self._outcomeSelector = SceneOutcomeSelector(autoSelect=False, extended=True)
        self._outcomeSelector.selected.connect(self._outcomeSelected)

        self.layout().addWidget(self._icon)
        self.layout().addWidget(self._outcomeSelector)
        self.layout().addWidget(self._btnReset, alignment=Qt.AlignmentFlag.AlignTop)
        self.layout().addWidget(spacer())

        self.reset()

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        if self._scene.outcome is not None:
            self._btnReset.setVisible(True)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        self._btnReset.setVisible(False)

    def setScene(self, scene: Scene):
        self._scene = scene
        if self._scene.outcome:
            self._outcomeSelector.refresh(self._scene.outcome)
            self._updateOutcome()
        else:
            self._outcomeSelector.reset()

    def reset(self):
        self._icon.setIcon(IconRegistry.disaster_icon('lightgrey'))
        self._icon.setText('Outcome')
        palette = self._icon.palette()
        palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.ButtonText, QColor('lightgrey'))
        self._icon.setPalette(palette)
        self._icon.setVisible(True)

        self._outcomeSelector.setHidden(True)
        self._btnReset.setHidden(True)

    def refresh(self):
        self._outcomeSelector.refresh(self._scene.outcome)
        self._updateOutcome()

    def _iconClicked(self):
        self._icon.setHidden(True)
        self._outcomeSelector.reset()
        qtanim.fade_in(self._outcomeSelector, 150)
        self._btnReset.setVisible(True)

    def _resetClicked(self):
        self._scene.outcome = None
        self._outcomeSelector.reset()
        self.reset()
        self.outcomeChanged.emit()

    def _outcomeSelected(self, outcome: SceneOutcome):
        self._scene.outcome = outcome
        self._updateOutcome()
        self.outcomeChanged.emit()

    def _updateOutcome(self):
        if self._scene.outcome == SceneOutcome.DISASTER:
            color = '#f4442e'
            self._icon.setIcon(IconRegistry.disaster_icon())
        elif self._scene.outcome == SceneOutcome.RESOLUTION:
            color = '#0b6e4f'
            self._icon.setIcon(IconRegistry.success_icon())
        elif self._scene.outcome == SceneOutcome.TRADE_OFF:
            color = '#832161'
            self._icon.setIcon(IconRegistry.tradeoff_icon())
        elif self._scene.outcome == SceneOutcome.MOTION:
            color = '#d4a373'
            self._icon.setIcon(IconRegistry.motion_icon())
        else:
            return
        self._icon.setText(SceneOutcome.to_str(self._scene.outcome))
        palette = self._icon.palette()
        palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.ButtonText, QColor(color))
        self._icon.setPalette(palette)

        self._icon.setVisible(True)
        self._outcomeSelector.setHidden(True)


class EventElementEditor(TextBasedSceneElementWidget):
    def __init__(self, novel: Novel, row: int, col: int, parent=None):
        super().__init__(novel, StoryElementType.Event, row, col, parent)
        self.setTitle('Event')
        self.setIcon('mdi.lightning-bolt-outline')
        self.setPlaceholderText("A pivotal event")


class EffectElementEditor(TextBasedSceneElementWidget):
    def __init__(self, novel: Novel, row: int, col: int, parent=None):
        super().__init__(novel, StoryElementType.Event, row, col, parent)
        self.setTitle('Effect')
        self.setIcon('fa5s.tachometer-alt')
        self.setPlaceholderText("An effect caused by the event")


class AgencyTextBasedElementEditor(TextBasedSceneElementWidget):
    def __init__(self, novel: Novel, row: int, col: int, parent=None):
        super().__init__(novel, StoryElementType.Agency, row, col, parent)
        self._agenda: Optional[SceneStructureAgenda] = None
        self.setTitle('Agency')
        self.setIcon('msc.debug-stackframe-dot')

        self._menu = MenuWidget()
        self._menu.addSection('Common')
        self._menu.addSeparator()
        goal_action = action('Goal', IconRegistry.goal_icon(), slot=partial(self._typeActivated, StoryElementType.Goal))
        self._menu.addAction(goal_action)
        conflict_action = action('Conflict', IconRegistry.conflict_icon(),
                                 slot=partial(self._typeActivated, StoryElementType.Conflict))
        self._menu.addAction(conflict_action)
        decision_action = action('Decision', IconRegistry.crisis_icon(),
                                 slot=partial(self._typeActivated, StoryElementType.Decision))
        self._menu.addAction(decision_action)
        self._menu.addAction(action('Character change', IconRegistry.from_name('mdi.account-cog', '#cdb4db'),
                                    slot=partial(self._typeActivated, StoryElementType.Arc)))
        consequences_action = action('Consequences', IconRegistry.cause_and_effect_icon(),
                                     slot=partial(self._typeActivated, StoryElementType.Consequences))
        self._menu.addAction(consequences_action)

        initiativeMenu = MenuWidget()
        initiativeMenu.setTitle('Initiative and decision-making')
        initiativeMenu.addAction(action('Motivation', IconRegistry.from_name('fa5s.fist-raised', '#94d2bd'),
                                        slot=partial(self._typeActivated, StoryElementType.Motivation)))
        initiativeMenu.addAction(action('Initiative', IconRegistry.decision_icon(),
                                        slot=partial(self._typeActivated, StoryElementType.Initiative)))
        initiativeMenu.addAction(goal_action)
        initiativeMenu.addSeparator()
        initiativeMenu.addAction(action('Catalyst', IconRegistry.from_name('fa5s.vial', '#822faf'),
                                        slot=partial(self._typeActivated, StoryElementType.Catalyst)))
        initiativeMenu.addAction(decision_action)
        initiativeMenu.addAction(action('Plan change', IconRegistry.from_name('mdi.calendar-refresh-outline'),
                                        slot=partial(self._typeActivated, StoryElementType.Plan_change)))

        conflict_menu = MenuWidget()
        conflict_menu.setTitle('Conflict and consequence')
        conflict_menu.addAction(conflict_action)
        conflict_menu.addAction(action('Internal conflict', IconRegistry.conflict_self_icon(),
                                       slot=partial(self._typeActivated, StoryElementType.Internal_conflict)))
        conflict_menu.addAction(action('Dilemma', IconRegistry.dilemma_icon(),
                                       slot=partial(self._typeActivated, StoryElementType.Dilemma)))
        conflict_menu.addSeparator()
        conflict_menu.addAction(consequences_action)
        conflict_menu.addAction(action('Impact on plot', IconRegistry.from_name('mdi.motion-outline', '#d4a373'),
                                       slot=partial(self._typeActivated, StoryElementType.Impact)))
        conflict_menu.addAction(action('Responsibility', IconRegistry.from_name('fa5s.hand-holding-water', '#457b9d'),
                                       slot=partial(self._typeActivated, StoryElementType.Responsibility)))

        interpersonal_menu = MenuWidget()
        interpersonal_menu.setTitle('Interpersonal dynamics')
        interpersonal_menu.addAction(action('Collaboration', IconRegistry.from_name('fa5.handshake', '#03045e'),
                                            slot=partial(self._typeActivated, StoryElementType.Collaboration)))
        interpersonal_menu.addAction(
            action('Subtext', IconRegistry.from_name('mdi6.speaker-off', '#f4a261'),
                   slot=partial(self._typeActivated, StoryElementType.Subtext)))

        self._menu.addSeparator()
        self._menu.addMenu(initiativeMenu)
        self._menu.addMenu(conflict_menu)
        self._menu.addMenu(interpersonal_menu)

    @overrides
    def setElement(self, element: StoryElement):
        self.setType(element.type)
        super().setElement(element)

    @overrides
    def activate(self):
        if self._type == StoryElementType.Agency:
            self._menu.exec(QCursor.pos())
        else:
            super().activate()

    def setAgenda(self, agenda: SceneStructureAgenda):
        self._agenda = agenda
        self.setType(StoryElementType.Agency)
        self.reset()

    def setType(self, type: StoryElementType):
        self._type = type
        if type == StoryElementType.Agency:
            self.setTitle('Agency')
            self.setIcon('msc.debug-stackframe-dot')
            self.setPlaceholderText('Character agency')
        elif type == StoryElementType.Goal:
            self.setTitle('Goal')
            self.setIcon('mdi.target', 'darkBlue')
            self.setPlaceholderText("What's the character's goal in this scene?")
        elif type == StoryElementType.Conflict:
            self.setTitle('Conflict')
            self.setIcon('mdi.sword-cross', '#f3a712')
            self.setPlaceholderText("What kind of conflict does the character have to face?")
        elif type == StoryElementType.Internal_conflict:
            self.setTitle('Internal conflict')
            self.setIcon('mdi.mirror', CONFLICT_SELF_COLOR)
            self.setPlaceholderText("What internal struggles, dilemmas, doubts does the character have to face?")
        elif type == StoryElementType.Dilemma:
            self.setTitle('Dilemma')
            self.setIcon('fa5s.map-signs', '#ba6f4d')
            self.setPlaceholderText("What difficult choice does the character have to face?")
        elif type == StoryElementType.Decision:
            self.setTitle('Decision')
            self.setIcon('mdi.arrow-decision-outline', '#ce2d4f')
            self.setPlaceholderText("What decision does the character have to make?")
        elif type == StoryElementType.Consequences:
            self.setTitle('Consequences')
            self.setIcon('mdi.ray-start-arrow')
            self.setPlaceholderText("What consequences does the character have to face?")
        elif type == StoryElementType.Motivation:
            self.setTitle('Motivation')
            self.setIcon('fa5s.fist-raised', '#94d2bd')
            self.setPlaceholderText("What's the character's motivation?")
        elif type == StoryElementType.Initiative:
            self.setTitle('Initiative')
            self.setIcon('fa5.lightbulb', '#219ebc')
            self.setPlaceholderText("How does the character proactively take action?")
        elif type == StoryElementType.Plan_change:
            self.setTitle('Change of plan')
            self.setIcon('mdi.calendar-refresh-outline')
            self.setPlaceholderText("What new plan does the character come up with?")
        elif type == StoryElementType.Impact:
            self.setTitle('Impact')
            self.setIcon('mdi.motion-outline', '#d4a373')
            self.setPlaceholderText("How does the character's choices or actions impact the plot?")
        elif type == StoryElementType.Responsibility:
            self.setTitle('Responsibility')
            self.setIcon('fa5s.hand-holding-water', '#457b9d')
            self.setPlaceholderText("Does the character have to take responsibility or accountability?")
        elif type == StoryElementType.Arc:
            self.setTitle('Character change')
            self.setIcon('mdi.account-cog', '#cdb4db')
            self.setPlaceholderText("Does the character grow or change?")
        elif type == StoryElementType.Collaboration:
            self.setTitle('Collaboration')
            self.setIcon('fa5.handshake', '#03045e')
            self.setPlaceholderText("Does the character collaborate with someone?")
        elif type == StoryElementType.Subtext:
            self.setTitle('Subtext')
            self.setIcon('mdi6.speaker-off', '#f4a261')
            self.setPlaceholderText("What kind of emotions, thoughts are hidden below the surface?")
        elif type == StoryElementType.Catalyst:
            self.setTitle('Catalyst')
            self.setIcon('fa5s.vial', '#822faf')
            self.setPlaceholderText("What disrupts the character's life and forces them to act?")

    def _typeActivated(self, type: StoryElementType):
        self.setType(type)
        self.activate()

    @overrides
    def _deactivate(self):
        super()._deactivate()
        self.setType(StoryElementType.Agency)

    @overrides
    def _storyElements(self) -> List[StoryElement]:
        return self._agenda.story_elements


class AbstractSceneElementsEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene: Optional[Scene] = None

        hbox(self)
        sp(self).h_exp()
        self._scrollarea, self._wdgElementsParent = scrolled(self, frameless=True)
        self._wdgElementsParent.setProperty('relaxed-white-bg', True)
        vbox(self._wdgElementsParent)

        self._wdgHeader = QWidget()
        hbox(self._wdgHeader)
        self._wdgElements = QWidget()
        grid(self._wdgElements, 2, 2, 2)

        self._wdgElementsParent.layout().addWidget(self._wdgHeader)
        self._wdgElementsParent.layout().addWidget(self._wdgElements)

    def setScene(self, scene: Scene):
        self._scene = scene

    def _newLine(self) -> QFrame:
        line = vline()
        line.setMinimumHeight(200)

        return line


class SceneStorylineEditor(AbstractSceneElementsEditor):
    outcomeChanged = pyqtSignal()
    storylineLinked = pyqtSignal(SceneElementWidget, Plot)
    storylineEditRequested = pyqtSignal(SceneElementWidget, Plot)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel

        self._outcomeEditor = SceneOutcomeEditor()
        self._outcomeEditor.outcomeChanged.connect(self.outcomeChanged)
        margins(self._wdgHeader, left=25)
        self._wdgHeader.layout().setSpacing(5)
        self._wdgHeader.layout().addWidget(self._outcomeEditor)
        self._wdgHeader.layout().addWidget(spacer())
        self._headerLine = line()
        self._wdgElementsParent.layout().insertWidget(1, self._headerLine)

        self._row = 3
        self._col = 5
        for row in range(self._row):
            for col in range(self._col):
                if col == 0:
                    placeholder = EventElementEditor(self._novel, row, col)
                elif col == 4:
                    continue
                else:
                    placeholder = EffectElementEditor(self._novel, row, col)
                placeholder.storylineSelected.connect(partial(self.storylineLinked.emit, placeholder))
                placeholder.storylineEditRequested.connect(partial(self.storylineEditRequested.emit, placeholder))
                self._wdgElements.layout().addWidget(placeholder, row, col, 1, 1)
        self._wdgElements.layout().addWidget(vline(), 0, 3, 3, 1)
        self._wdgElements.layout().addWidget(spacer(), 0, self._col, 1, 1)
        self._wdgElements.layout().addWidget(vspacer(), self._row, 0, 1, 1)
        # self.__newPlotElementEditor()
        #
        # self._btnAddNewPlot = tool_btn(IconRegistry.plus_circle_icon('grey'), 'Add new storyline', transparent_=True,
        #                                parent=self._wdgElements)
        # self._btnAddNewPlot.installEventFilter(OpacityEventFilter(self._btnAddNewPlot))
        # self._btnAddNewPlot.clicked.connect(self._addNewPlot)

        # self._wdgAddNewPlotParent = QWidget()
        # vbox(self._wdgAddNewPlotParent)
        # margins(self._wdgAddNewPlotParent, top=self._storylineElements[0].sizeHint().height() // 2, left=5, right=5)
        # icon = Icon()
        # icon.setIcon(IconRegistry.from_name('fa5s.theater-masks', 'lightgrey'))
        # self._wdgAddNewPlotParent.layout().addWidget(icon)
        # self._wdgAddNewPlotParent.layout().addWidget(self._btnAddNewPlot)
        # self._wdgAddNewPlotParent.setHidden(True)

        # self._themeElement = TextBasedSceneElementWidget()
        # self._themeElement.setText('Theme')
        # self._themeElement.setIcon('mdi.butterfly-outline', '#9d4edd')

        # self._outcomeElement = OutcomeSceneElementEditor()
        # self._outcomeElement.outcomeChanged.connect(self.outcomeChanged.emit)

        # self._consequencesElement = TextBasedSceneElementWidget(StoryElementType.Consequences)
        # self._consequencesElement.setTitle('Consequences')
        # self._consequencesElement.setIcon('mdi.ray-start-arrow')
        # self._consequencesElement.setPlaceholderText("Are there any imminent or later consequences of this scene?")

        # self._wdgElements.layout().addWidget(self._outcomeElement)
        # self._wdgElements.layout().addWidget(self._newLine())
        # self._wdgElements.layout().addWidget(self._storylineElements[0])
        #
        # self._wdgElements.layout().addWidget(self._newLine())
        # self._wdgElements.layout().addWidget(self._consequencesElement)

    @overrides
    def setScene(self, scene: Scene):
        super().setScene(scene)
        self.purposeChangedEvent()
        self._outcomeEditor.setScene(scene)

        for row in range(self._row):
            for col in range(self._col):
                item = self._wdgElements.layout().itemAtPosition(row, col)
                if item and item.widget() and isinstance(item.widget(), SceneElementWidget):
                    item.widget().setScene(scene)

        for element in scene.story_elements:
            item = self._wdgElements.layout().itemAtPosition(element.row, element.col)
            if item and item.widget():
                item.widget().setElement(element)

    def refresh(self):
        self._outcomeEditor.refresh()

    def purposeChangedEvent(self):
        if self._scene.purpose and self._scene.purpose == ScenePurposeType.Story:
            self._wdgHeader.setVisible(True)
            self._headerLine.setVisible(True)
        else:
            self._wdgHeader.setHidden(True)
            self._headerLine.setHidden(True)

    # def _plotSelected(self, plotElement: PlotSceneElementEditor):
    #     insert_after(self._wdgElements, self._wdgAddNewPlotParent, reference=plotElement)
    #     self._wdgAddNewPlotParent.setVisible(True)
    #
    # def _addNewPlot(self):
    #     elementEditor = self.__newPlotElementEditor()
    #     insert_after(self._wdgElements, elementEditor, reference=self._wdgAddNewPlotParent)
    #     self._wdgAddNewPlotParent.setHidden(True)
    #     self._wdgElements.layout().removeWidget(self._wdgAddNewPlotParent)
    #
    #     elementEditor.activate()
    #
    # def __newPlotElementEditor(self) -> PlotSceneElementEditor:
    #     elementEditor = PlotSceneElementEditor(self._novel)
    #     elementEditor.plotSelected.connect(partial(self._plotSelected, elementEditor))
    #
    #     if self._scene:
    #         elementEditor.setScene(self._scene)
    #
    #     self._storylineElements.append(elementEditor)
    #
    #     return elementEditor


class CharacterTab(QAbstractButton):
    characterChanged = pyqtSignal(Character)
    removed = pyqtSignal()

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._character: Optional[Character] = None
        vbox(self, 0, 2)

        self.setCheckable(True)
        self._hovered: bool = False

        self._btnRemoval = RemovalButton()
        self._btnRemoval.setHidden(True)
        self._removalEnabled: bool = False
        self._btnRemoval.clicked.connect(self.removed)

        self._btnCharacterSelector = CharacterSelectorButton(self._novel, parent=self)
        self._btnCharacterSelector.characterSelected.connect(self._characterSelected)
        self._wdgTop = QWidget()
        hbox(self._wdgTop, 0)
        self._wdgTop.layout().addWidget(self._btnCharacterSelector, alignment=Qt.AlignmentFlag.AlignLeft)
        self._wdgTop.layout().addWidget(self._btnRemoval,
                                        alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(self._wdgTop, alignment=Qt.AlignmentFlag.AlignTop)
        self.setMinimumHeight(80)

        self.toggled.connect(self._toggled)

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        if not self.isChecked():
            margins(self, left=1)
            self._hovered = True
            self.update()
        self._btnRemoval.setVisible(self._removalEnabled)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        if not self.isChecked():
            margins(self, left=0)
            self._hovered = False
            self.update()
        self._btnRemoval.setHidden(True)

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QPen(Qt.GlobalColor.lightGray, 1))
        if self.isChecked():
            painter.setBrush(QColor(RELAXED_WHITE_COLOR))
        elif self._hovered:
            painter.setBrush(QColor('lightgrey'))

        painter.drawRoundedRect(event.rect(), 4, 4)

    def setRemovalEnabled(self, enabled: bool):
        self._removalEnabled = enabled

    def updateAvailableCharacters(self, characters: List[Character]):
        self._btnCharacterSelector.characterSelectorMenu().setCharacters(characters)

    def popup(self):
        self._btnCharacterSelector.characterSelectorMenu().exec()

    def setCharacter(self, character: Character):
        self._characterSelected(character)
        self._btnCharacterSelector.setCharacter(character)

    def _characterSelected(self, character: Character):
        self._character = character
        self.characterChanged.emit(self._character)

    def _toggled(self, _: bool):
        margins(self, left=0)
        self._hovered = False


class CharacterTabBar(QScrollArea):
    characterChanged = pyqtSignal(Character)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self.setWidgetResizable(True)
        self._btnPlusTooltip = 'Add new character tab'
        self._removalConfirmationText = 'Remove character tab?'
        self._availableCharacter: List[Character] = []

        self._wdgCentral = QWidget()
        vbox(self._wdgCentral)
        self.setWidget(self._wdgCentral)
        sp(self).v_exp()
        sp(self._wdgCentral).v_exp()
        self._tabs: List[CharacterTab] = []
        self._tabGroup = QButtonGroup()
        self._tabGroup.setExclusive(True)

        sp(self).h_max()
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def addNewTab(self, *args):
        tab = self._newTab(*args)
        tab.updateAvailableCharacters(self._availableCharacter)
        tab.characterChanged.connect(self.characterChanged)
        tab.removed.connect(partial(self._removeTab, tab))
        self._tabs.append(tab)
        self._tabGroup.addButton(tab)
        self._tabsNumberChanged()

        insert_before_the_end(self._wdgCentral, tab, 2)

    def setCharacter(self, character: Character):
        tab: CharacterTab = self._tabGroup.checkedButton()
        tab.setCharacter(character)

    def updateAvailableCharacters(self, characters: List[Character]):
        self._availableCharacter = characters
        for tab in self._tabs:
            tab.updateAvailableCharacters(characters)

    def reset(self):
        self._tabs.clear()
        clear_layout(self._wdgCentral)
        btnPlus = tool_btn(IconRegistry.plus_icon('grey'), transparent_=True, tooltip=self._btnPlusTooltip)
        btnPlus.installEventFilter(OpacityEventFilter(btnPlus))
        btnPlus.clicked.connect(self._addNewClicked)
        self._wdgCentral.layout().addWidget(btnPlus, alignment=Qt.AlignmentFlag.AlignCenter)
        self._wdgCentral.layout().addWidget(vspacer())

    def popup(self):
        btn = self._tabGroup.checkedButton()
        if btn:
            btn.popup()

    def _tabsNumberChanged(self):
        if len(self._tabs) == 1:
            self._tabs[0].setChecked(True)
            self._tabs[0].setRemovalEnabled(False)
        else:
            for tab in self._tabs:
                tab.setRemovalEnabled(True)

    def _addNewClicked(self):
        self.addNewTab()

    def _newTab(self, *args) -> CharacterTab:
        return CharacterTab(*args, novel=self._novel)

    def _removeTab(self, tab: CharacterTab) -> bool:
        if ask_confirmation(self._removalConfirmationText):
            self._tabs.remove(tab)
            self._tabGroup.removeButton(tab)
            fade_out_and_gc(self._wdgCentral, tab)
            self._tabsNumberChanged()

            return True

        return False


class SceneAgendaTab(CharacterTab):
    resetAgenda = pyqtSignal()

    def __init__(self, agenda: SceneStructureAgenda, novel: Novel, parent=None):
        super().__init__(novel, parent)
        self._agenda = agenda
        if self._agenda.character_id:
            self._btnCharacterSelector.setCharacter(self._agenda.character(self._novel))

    def agenda(self) -> SceneStructureAgenda:
        return self._agenda

    @overrides
    def updateAvailableCharacters(self, characters: List[Character]):
        super().updateAvailableCharacters(characters)
        self._btnCharacterSelector.setEnabled(len(characters) > 0)

    def setUnsetCharacterSlot(self, slot):
        self._btnCharacterSelector.installEventFilter(DisabledClickEventFilter(self._btnCharacterSelector, slot))

    @overrides
    def _characterSelected(self, character: Character):
        if self._agenda.character_id and self._agenda.character_id != character.id:
            if not ask_confirmation("Replace character and reset the current agency?"):
                self._btnCharacterSelector.setCharacter(self._agenda.character(self._novel))
                return

            self.resetAgenda.emit()
        self._agenda.set_character(character)
        super()._characterSelected(character)


class SceneAgendasTabBar(CharacterTabBar):
    agendaToggled = pyqtSignal(SceneStructureAgenda, bool)
    resetAgenda = pyqtSignal(SceneStructureAgenda)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(novel, parent)
        self._scene: Optional[Scene] = None
        self._unsetCharacterSlot = None
        self._btnPlusTooltip = 'Add new character agency'
        self._removalConfirmationText = 'Remove character agency?'

    def setScene(self, scene: Scene):
        self._scene = scene
        self.reset()

        for agenda in self._scene.agendas:
            self.addNewTab(agenda)

    def setUnsetCharacterSlot(self, slot):
        self._unsetCharacterSlot = slot
        for tab in self._tabs:
            tab.setUnsetCharacterSlot(self._unsetCharacterSlot)

    @overrides
    def _addNewClicked(self):
        agenda = SceneStructureAgenda()
        self._scene.agendas.append(agenda)
        self.addNewTab(agenda)

    @overrides
    def _newTab(self, *args) -> CharacterTab:
        tab = SceneAgendaTab(*args, novel=self._novel)
        tab.toggled.connect(partial(self.agendaToggled.emit, tab.agenda()))
        tab.resetAgenda.connect(partial(self._resetAgenda, tab.agenda()))
        tab.setUnsetCharacterSlot(self._unsetCharacterSlot)

        return tab

    @overrides
    def _removeTab(self, tab: SceneAgendaTab) -> bool:
        agenda = tab.agenda()
        removed = super()._removeTab(tab)
        if removed:
            self._scene.agendas.remove(agenda)

        return removed

    def _resetAgenda(self, agenda: SceneStructureAgenda):
        agenda.emotion = None
        agenda.intensity = 0
        agenda.motivations.clear()
        agenda.conflict_references.clear()
        agenda.story_elements.clear()

        self.resetAgenda.emit(agenda)


class SceneAgendaEditor(AbstractSceneElementsEditor):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._agenda: Optional[SceneStructureAgenda] = None

        self._characterTabbar = SceneAgendasTabBar(self._novel)
        self._characterTabbar.characterChanged.connect(self._characterSelected)
        self._characterTabbar.agendaToggled.connect(self._agendaToggled)
        self._characterTabbar.resetAgenda.connect(self._agendaReset)
        self._btnAddAgency = tool_btn(IconRegistry.plus_icon('grey'), transparent_=True)
        self._btnAddAgency.clicked.connect(self._characterTabbar.addNewTab)
        # self.layout().insertWidget(0, group(self._characterTabbar, self._btnAddAgency, vertical=False),
        #                            alignment=Qt.AlignmentFlag.AlignTop)
        self.layout().insertWidget(0, self._characterTabbar)

        self._unsetCharacterSlot = None
        self._btnCharacterDelegate = push_btn(IconRegistry.from_name('fa5s.arrow-circle-left'),
                                              'Select character first', transparent_=True)
        self._btnCharacterDelegate.clicked.connect(self._characterDelegateClicked)

        self._emotionEditor = SceneAgendaEmotionEditor()
        self._emotionEditor.emotionChanged.connect(self._emotionChanged)
        self._emotionEditor.deactivated.connect(self._emotionReset)
        self._motivationEditor = SceneAgendaMotivationEditor()
        self._motivationEditor.setNovel(novel)
        self._motivationEditor.motivationChanged.connect(self._motivationChanged)
        self._motivationEditor.deactivated.connect(self._motivationReset)

        self._conflictEditor = SceneAgendaConflictEditor()
        self._conflictEditor.setNovel(self._novel)

        margins(self._wdgHeader, left=25)
        self._wdgHeader.layout().setSpacing(5)
        self._wdgHeader.layout().addWidget(self._btnCharacterDelegate)
        self._wdgHeader.layout().addWidget(self._emotionEditor)
        self._wdgHeader.layout().addWidget(vline())
        self._wdgHeader.layout().addWidget(self._motivationEditor)
        self._wdgHeader.layout().addWidget(vline())
        self._wdgHeader.layout().addWidget(self._conflictEditor)
        self._wdgHeader.layout().addWidget(spacer())
        self._wdgElementsParent.layout().insertWidget(1, line())

        self._row = 3
        self._col = 4
        for row in range(self._row):
            for col in range(self._col):
                placeholder = AgencyTextBasedElementEditor(self._novel, row, col)
                self._wdgElements.layout().addWidget(placeholder, row, col, 1, 1)
        self._wdgElements.layout().addWidget(spacer(), 0, self._col, 1, 1)
        self._wdgElements.layout().addWidget(vspacer(), self._row, 0, 1, 1)

        retain_when_hidden(self._wdgElements)

    @overrides
    def setScene(self, scene: Scene):
        super().setScene(scene)

        self._conflictEditor.setScene(scene)
        self._motivationEditor.setScene(scene)

        self._characterTabbar.setScene(scene)

    def updateAvailableCharacters(self):
        characters = []
        if self._scene.pov:
            characters.append(self._scene.pov)
        characters.extend(self._scene.characters)

        self._characterTabbar.updateAvailableCharacters(characters)

    def setUnsetCharacterSlot(self, func):
        self._unsetCharacterSlot = func
        self._characterTabbar.setUnsetCharacterSlot(self._unsetCharacterSlot)

    def povChangedEvent(self, pov: Character):
        if self._agenda.character_id is None:
            self._characterTabbar.setCharacter(pov)

    def _characterSelected(self, character: Character):
        self._updateElementsVisibility()

    def _agendaReset(self, agenda: SceneStructureAgenda):
        if self._agenda is agenda:
            self._agendaToggled(agenda, True)

    def _agendaToggled(self, agenda: SceneStructureAgenda, toggled: bool):
        if not toggled:
            return

        self._agenda = agenda
        if agenda.emotion is None:
            self._emotionEditor.reset()
        else:
            self._emotionEditor.setValue(agenda.emotion)

        self._motivationEditor.setAgenda(agenda)
        self._conflictEditor.setAgenda(agenda)

        for row in range(self._row):
            for col in range(self._col):
                item = self._wdgElements.layout().itemAtPosition(row, col)
                if item and item.widget():
                    wdg: AgencyTextBasedElementEditor = item.widget()
                    wdg.setAgenda(agenda)

        for element in agenda.story_elements:
            item = self._wdgElements.layout().itemAtPosition(element.row, element.col)
            if item and item.widget():
                wdg: AgencyTextBasedElementEditor = item.widget()
                wdg.setElement(element)

        self._updateElementsVisibility()

    def _emotionChanged(self, emotion: int):
        self._agenda.emotion = emotion

    def _emotionReset(self):
        self._agenda.emotion = None

    def _motivationChanged(self, motivation: Motivation, value: int):
        self._agenda.motivations[motivation.value] = value

    def _motivationReset(self):
        self._agenda.motivations.clear()

    def _characterDelegateClicked(self):
        if not self._scene.characters or self._scene.pov:
            self._unsetCharacterSlot()
        else:
            self._characterTabbar.popup()

    def _updateElementsVisibility(self):
        elements_visible = self._agenda.character_id is not None
        self._btnCharacterDelegate.setVisible(not elements_visible)
        self._wdgElements.setVisible(elements_visible)
        self._emotionEditor.setVisible(elements_visible)
        self._motivationEditor.setVisible(elements_visible)
        self._conflictEditor.setVisible(elements_visible)
