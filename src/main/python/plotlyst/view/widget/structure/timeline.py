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

import pickle
from enum import Enum
from functools import partial
from typing import List, Optional, Dict, Union, Set

import qtanim
from PyQt6.QtCore import Qt, QEvent, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QDragEnterEvent, QDropEvent, QResizeEvent, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QWidget, QToolButton, QSizePolicy, QPushButton, QSplitter, QAbstractButton, QToolTip
from overrides import overrides
from qthandy import hbox, transparent, italic, translucent, gc, clear_layout, vbox, margins, decr_font, pointy
from qthandy.filter import InstantTooltipEventFilter, DragEventFilter

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, act_color, RELAXED_WHITE_COLOR
from plotlyst.core.domain import StoryBeat, StoryBeatType, Novel, \
    StoryStructure, Scene, StoryStructureDisplayType, TemplateStoryStructureType
from plotlyst.service.cache import acts_registry
from plotlyst.view.common import to_rgba_str, ButtonPressResizeEventFilter
from plotlyst.view.icons import IconRegistry


class _BeatButtonStyle(Enum):
    Icon = 0
    Circle = 1
    Text = 2


class _BeatButton(QToolButton):
    BeatMimeType = 'application/story-beat'

    def __init__(self, beat: StoryBeat, structure: StoryStructure, parent=None, selectable: bool = False):
        super(_BeatButton, self).__init__(parent)
        self.beat = beat
        self.structure = structure
        self._selectable = selectable
        self._style = _BeatButtonStyle.Icon

        self.setCheckable(self._selectable)
        self.toggled.connect(self._checked)

        color = '#454E56' if self._selectable else beat.icon_color

        if self._selectable:
            self.installEventFilter(ButtonPressResizeEventFilter(self))

        if beat.icon:
            self.setIcon(IconRegistry.from_name(beat.icon, color, beat.icon_color))
        elif beat.seq:
            if self.structure.template_type == TemplateStoryStructureType.SPINE:
                icon = f'mdi.numeric-{beat.seq}-box'
            else:
                icon = f'mdi.numeric-{beat.seq}'
            self.setIcon(IconRegistry.from_name(icon, color, beat.icon_color, scale=1.5))

        self.installEventFilter(InstantTooltipEventFilter(self))
        transparent(self)

        self._dragEventFilter = DragEventFilter(self, self.BeatMimeType, self.dataFunc, hideTarget=True)
        self._dragEnabled: bool = False

    def dataFunc(self, _):
        return self.beat

    def setBorderStyle(self):
        self._style = _BeatButtonStyle.Circle
        self._initBorderStyle(125)

    def setDragEnabled(self, enabled: bool):
        if self._dragEnabled == enabled:
            return

        self._dragEnabled = enabled
        if enabled:
            self.installEventFilter(self._dragEventFilter)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.removeEventFilter(self._dragEventFilter)
            self.setCursor(Qt.CursorShape.ArrowCursor)

    @overrides
    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ToolTip:
            tip = f'''<html><div style="color: {self.beat.icon_color}"><b align=center>{self.beat.text}</b>
            <p/>
            <hr/>
            <p/>
            {self.beat.notes}</div>
            '''
            QToolTip.showText(event.globalPos(), tip)
            return True

        return super().event(event)

    def setTextStyle(self):
        self._style = _BeatButtonStyle.Text
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        decr_font(self, 2)
        self.setText(self.beat.text)

    @overrides
    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)

    def activateSelection(self, value: bool):
        if not self._selectable:
            return
        if value or self.isChecked():
            self.setEnabled(True)
            pointy(self)
        else:
            self.setDisabled(True)
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _checked(self, toggled: bool):
        if self._style == _BeatButtonStyle.Circle:
            self._initBorderStyle(125)

        qtanim.glow(self, color=QColor(self.beat.icon_color if toggled else 'grey'))

    def _initBorderStyle(self, opacity: int):
        if self._selectable and not self.isChecked():
            color_translucent = 'lightgrey'
        else:
            color_translucent = to_rgba_str(QColor(self.beat.icon_color), opacity)
        self.setStyleSheet(f'''
                            QToolButton {{
                                            background: {RELAXED_WHITE_COLOR};
                                            border: 2px solid {color_translucent};
                                            border-radius: 17px;
                                            padding: 4px;
                                        }}
                            QToolButton:menu-indicator {{
                                width: 0;
                            }}
                            ''')

    def highlight(self):
        if self._style == _BeatButtonStyle.Circle:
            self._initBorderStyle(255)
        else:
            self.setStyleSheet(
                f'QToolButton {{border: 3px dotted {PLOTLYST_SECONDARY_COLOR}; border-radius: 5;}} QToolTip {{border: 0px;}}')
            self.setIconSize(QSize(24, 24))
        qtanim.glow(self, color=QColor(self.beat.icon_color))

    def unhighlight(self):
        if self._style == _BeatButtonStyle.Circle:
            self._initBorderStyle(125)
        else:
            transparent(self)
            self.setIconSize(QSize(20, 20))


class _ContainerButton(QPushButton):
    def __init__(self, beat: StoryBeat, parent=None):
        super().__init__(parent)
        if beat.percentage_end - beat.percentage > 7:
            self.setText(beat.text)
        self.setStyleSheet(f'''
                            QPushButton {{border-top:2px dashed {beat.icon_color}; color: {beat.icon_color};}}
                        ''')
        italic(self)
        translucent(self)


class _ActButton(QPushButton):
    def __init__(self, structure: StoryStructure, act: int, parent=None, left: bool = False, right: bool = False):
        super().__init__(parent)
        self.structure = structure
        self.act = act
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(10)
        if act == 0:
            self.setText('Structure')
        else:
            self.setText(self.structure.acts_text.get(self.act, f'Act {self.act}'))
        color = act_color(self.act, self.structure.acts)
        self.setStyleSheet(f'''
                QPushButton {{
                    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 {color}, stop: 1 {color});
                    border: 1px solid #8f8f91;
                    border-top-left-radius: {8 if left else 0}px;
                    border-bottom-left-radius: {8 if left else 0}px;
                    border-top-right-radius: {8 if right else 0}px;
                    border-bottom-right-radius: {8 if right else 0}px;
                    color:white;
                    padding: 2px;
                }}
                ''')


class StoryStructureTimelineWidget(QWidget):
    BeatMimeType = 'application/story-beat'

    beatToggled = pyqtSignal(StoryBeat, bool)
    actsResized = pyqtSignal()
    beatMoved = pyqtSignal(StoryBeat)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self._checkOccupiedBeats: bool = True
        self._beatsCheckable: bool = False
        self._beatSelectionActive: bool = False
        self._beatsMoveable: bool = False
        self._actsClickable: bool = False
        self._actsResizeable: bool = False

        self.novel: Optional[Novel] = None
        self.structure: Optional[StoryStructure] = None

        self._acts: List[QPushButton] = []
        self._beats: Dict[StoryBeat, _BeatButton] = {}
        self._containers: Dict[StoryBeat, QPushButton] = {}
        self._actsSplitter: Optional[QSplitter] = None
        self.btnCurrentScene = QToolButton(self)
        self._currentScenePercentage = 1
        self.btnCurrentScene.setIcon(IconRegistry.circle_icon(color=PLOTLYST_SECONDARY_COLOR))
        self.btnCurrentScene.setHidden(True)
        transparent(self.btnCurrentScene)
        self._wdgLine = QWidget(self)
        hbox(self._wdgLine, 0, 0)
        self._lineHeight: int = 25
        self._beatHeight: int = 20
        self._containerTopMargin: int = 6
        vbox(self, 0, 0).addWidget(self._wdgLine)

    def checkOccupiedBeats(self) -> bool:
        return self._checkOccupiedBeats

    def setCheckOccupiedBeats(self, value: bool):
        self._checkOccupiedBeats = value

    def beatsCheckable(self) -> bool:
        return self._beatsCheckable

    def setBeatsSelectable(self, value: bool):
        self._beatsCheckable = value

    def activateBeatSelection(self, active: bool):
        self._beatSelectionActive = active
        for beat in self._beats.values():
            beat.activateSelection(active)

    def setBeatsMoveable(self, enabled: bool):
        self._beatsMoveable = enabled
        self.setAcceptDrops(enabled)

    def isProportionalDisplay(self) -> bool:
        if self.structure and self.structure.display_type == StoryStructureDisplayType.Sequential_timeline:
            return False
        return True

    def setStructure(self, novel: Novel, structure: Optional[StoryStructure] = None):
        self.novel = novel
        self.structure = structure if structure else novel.active_story_structure
        for wdg in self._containers.values():
            gc(wdg)
        self._containers.clear()
        for wdg in self._beats.values():
            gc(wdg)
        self._beats.clear()

        occupied_beats = acts_registry.occupied_beats()
        for beat in self.structure.sorted_beats():
            if beat.type == StoryBeatType.CONTAINER:
                btn = _ContainerButton(beat, self)
                self._containers[beat] = btn
            else:
                btn = _BeatButton(beat, self.structure, parent=self, selectable=self._beatsCheckable)
                self._beats[beat] = btn

            self.__initButton(beat, btn, occupied_beats)

        if self._containers:
            margins(self, bottom=self._beatHeight * 2 + self._containerTopMargin)
        else:
            margins(self, bottom=self._beatHeight + self._containerTopMargin)

        if self.isProportionalDisplay():
            self.refreshActs()
            self._rearrangeBeats()
        else:
            self._clearActs()
            for wdg in self._beats.values():
                self._wdgLine.layout().addWidget(wdg)

    def __initButton(self, beat: StoryBeat, btn: Union[QAbstractButton, _BeatButton], occupied_beats: Set[StoryBeat]):
        if beat.type == StoryBeatType.BEAT:
            btn.clicked.connect(partial(self._beatClicked, btn))
            # btn.installEventFilter(self)
            self._refreshBeatButtonDragStatus(btn)
            if not self.isProportionalDisplay():
                if self.structure.template_type == TemplateStoryStructureType.SPINE:
                    btn.setTextStyle()
                else:
                    btn.setBorderStyle()
            if self._checkOccupiedBeats:
                btn.setChecked(beat in occupied_beats)
                btn.activateSelection(btn.isChecked())
                # if self._beatsCheckable:
                #     btn.setSelectable(True)
                # self._beatToggled(btn, False)
        btn.setVisible(beat.enabled)

    # @overrides
    # def eventFilter(self, watched: QObject, event: QEvent) -> bool:
    #     if isinstance(watched, QToolButton) and watched.isCheckable() and not watched.isChecked():
    #         if event.type() == QEvent.Type.Enter:
    #             translucent(watched)
    #         elif event.type() == QEvent.Type.Leave:
    #             translucent(watched, 0.2)
    #     return super().eventFilter(watched, event)

    @overrides
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat(self.BeatMimeType):
            event.accept()
        else:
            event.ignore()

    @overrides
    def dropEvent(self, event: QDropEvent) -> None:
        dropped_beat: StoryBeat = pickle.loads(event.mimeData().data(self.BeatMimeType))

        for beat in self._beats.keys():
            if beat == dropped_beat:
                beat.percentage = self._percentageForX(event.position().x() - self._beatHeight // 2)
                self._rearrangeBeats()
                event.accept()
                self.beatMoved.emit(beat)
                break

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        if self.isProportionalDisplay():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(0.5)
        pen = QPen()
        pen.setColor(QColor('grey'))

        pen.setWidth(3)
        painter.setPen(pen)

        y = self._beatHeight // 2 + 5
        painter.drawLine(0, y, self.width(), y)

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        if self.structure.display_type != StoryStructureDisplayType.Proportional_timeline:
            super().resizeEvent(event)
            return

        self._rearrangeBeats()

    def _rearrangeBeats(self):
        for beat, btn in self._beats.items():
            btn.setGeometry(self._xForPercentage(beat.percentage), self._lineHeight,
                            self._beatHeight,
                            self._beatHeight)
        for beat, btn in self._containers.items():
            x = self._xForPercentage(beat.percentage)
            btn.setGeometry(x + self._beatHeight // 2,
                            self._lineHeight + self._beatHeight + self._containerTopMargin,
                            self._xForPercentage(beat.percentage_end) - x,
                            self._beatHeight)
        if self.btnCurrentScene:
            self.btnCurrentScene.setGeometry(
                int(self.width() * self._currentScenePercentage / 100 - self._lineHeight // 2),
                self._lineHeight,
                self._beatHeight,
                self._beatHeight)

    def _xForPercentage(self, percentage: int) -> int:
        return int(self.width() * percentage / 100 - self._lineHeight // 2)

    def _percentageForX(self, x: int) -> float:
        return (x + self._lineHeight // 2) * 100 / self.width()

    def uncheckActs(self):
        for act in self._acts:
            act.setChecked(False)

    def setActChecked(self, act: int, checked: bool = True):
        self._acts[act - 1].setChecked(checked)

    def setActsClickable(self, clickable: bool):
        self._actsClickable = clickable
        for act in self._acts:
            act.setEnabled(clickable)

    def setActsResizeable(self, enabled: bool):
        self._actsResizeable = enabled
        if self._actsSplitter:
            self._actsSplitter.setEnabled(self._actsResizeable)

    def highlightBeat(self, beat: StoryBeat):
        self.clearHighlights()
        btn = self._beats.get(beat)
        if btn is None:
            return

        if self.isProportionalDisplay():
            btn.setFixedSize(self._beatHeight + 6, self._beatHeight + 6)
        btn.highlight()

    def refreshBeat(self, beat: StoryBeat):
        if beat.type == StoryBeatType.BEAT:
            btn = self._beats.get(beat)
            if beat.icon:
                btn.setIcon(IconRegistry.from_name(beat.icon, beat.icon_color))
            btn.setToolTip(f'<b style="color: {beat.icon_color}">{beat.text}')
            self._refreshBeatButtonDragStatus(btn)

    def refreshActs(self):
        self._clearActs()

        act_beats = self.structure.act_beats()
        acts = len(act_beats) + 1 if act_beats else 0
        if acts:
            self._actsSplitter = QSplitter(self._wdgLine)
            self._actsSplitter.setContentsMargins(0, 0, 0, 0)
            self._actsSplitter.setChildrenCollapsible(False)
            self._actsSplitter.setHandleWidth(1)
            self._wdgLine.layout().addWidget(self._actsSplitter)
            for act in range(1, acts + 1):
                left = False
                right = False
                if act == 1:
                    left = True
                elif act == acts:
                    right = True

                actBtn = self._actButton(act, left=left, right=right)
                self._acts.append(actBtn)
                self._wdgLine.layout().addWidget(actBtn)
                self._actsSplitter.addWidget(actBtn)

            splitter_sizes = []
            for i in range(len(act_beats) + 1):
                if i == 0:
                    size = int(10 * act_beats[i].percentage)
                elif i > 0 and i == len(act_beats):
                    size = int(10 * (100 - act_beats[-1].percentage))
                else:
                    size = int(10 * (act_beats[i].percentage - act_beats[i - 1].percentage))
                splitter_sizes.append(size)

            self._actsSplitter.setSizes(splitter_sizes)
            self._actsSplitter.setEnabled(self._actsResizeable)
            self._actsSplitter.splitterMoved.connect(self._actResized)
        else:  # no acts
            actBtn = self._actButton(0, left=True, right=True)
            self._wdgLine.layout().addWidget(actBtn)

    def _clearActs(self):
        self._acts.clear()
        self._actsSplitter = None
        clear_layout(self._wdgLine)

    def replaceBeat(self, old: StoryBeat, new: StoryBeat):
        if old.type == StoryBeatType.BEAT and new.type == StoryBeatType.BEAT:
            btn = self._beats.pop(old)
            self._beats[new] = btn
            btn.setIcon(IconRegistry.from_name(new.icon, new.icon_color))
            btn.setToolTip(f'<b style="color: {new.icon_color}">{new.text}')
            btn.beat = new

            self.toggleBeatVisibility(new)

    def removeBeat(self, beat: StoryBeat):
        if beat.type == StoryBeatType.BEAT:
            btn = self._beats.pop(beat)
            gc(btn)

    def insertBeat(self, beat: StoryBeat):
        if beat.type == StoryBeatType.BEAT:
            btn = _BeatButton(beat, self.structure, parent=self, selectable=self._beatsCheckable)
            self._beats[beat] = btn
            self.__initButton(beat, btn, set())
            self._rearrangeBeats()
            btn.setVisible(True)

    def highlightScene(self, scene: Scene):
        if not self.isVisible():
            return

        beat = scene.beat(self.novel)
        if beat:
            self.highlightBeat(beat)
        elif self.isProportionalDisplay():
            self.clearHighlights()
            index = self.novel.scenes.index(scene)
            previous_beat_scene = None
            previous_beat = None
            next_beat_scene = None
            next_beat = None
            for _scene in reversed(self.novel.scenes[0: index]):
                previous_beat = _scene.beat(self.novel)
                if previous_beat:
                    previous_beat_scene = _scene
                    break
            for _scene in self.novel.scenes[index: len(self.novel.scenes)]:
                next_beat = _scene.beat(self.novel)
                if next_beat:
                    next_beat_scene = _scene
                    break

            min_percentage = previous_beat.percentage if previous_beat else 1
            max_percentage = next_beat.percentage if next_beat else 99
            min_index = self.novel.scenes.index(previous_beat_scene) if previous_beat_scene else 0
            max_index = self.novel.scenes.index(next_beat_scene) if next_beat_scene else len(self.novel.scenes) - 1

            if max_index - min_index == 0:
                return

            self._currentScenePercentage = min_percentage + (max_percentage - min_percentage) / (
                    max_index - min_index) * (index - min_index)

            self.btnCurrentScene.setVisible(True)
            self.btnCurrentScene.setGeometry(
                int(self.width() * self._currentScenePercentage / 100 - self._lineHeight // 2),
                self._lineHeight,
                self._beatHeight,
                self._beatHeight)

    def unhighlightBeats(self):
        for btn in self._beats.values():
            btn.unhighlight()
            if self.isProportionalDisplay():
                btn.setFixedSize(self._beatHeight, self._beatHeight)

    def clearHighlights(self):
        self.unhighlightBeats()
        self.btnCurrentScene.setHidden(True)

    def toggleBeat(self, beat: StoryBeat, toggled: bool):
        if not self._beatsCheckable:
            return

        btn = self._beats.get(beat)
        if btn is None:
            return
        btn.setChecked(toggled)
        btn.activateSelection(self._beatSelectionActive)

    def toggleBeatVisibility(self, beat: StoryBeat):
        btn = self._beats.get(beat)
        if btn is None:
            return

        if beat.enabled:
            qtanim.fade_in(btn)
        else:
            qtanim.fade_out(btn)

    def _actButton(self, act: int, left: bool = False, right: bool = False) -> QPushButton:
        actBtn = _ActButton(self.structure, act, self, left, right)
        actBtn.setFixedHeight(self._lineHeight)
        actBtn.setEnabled(self._actsClickable)
        actBtn.toggled.connect(partial(self._actToggled, actBtn))

        return actBtn

    def _actToggled(self, btn: _ActButton, toggled: bool):
        translucent(btn, 1.0 if toggled else 0.2)

    def _beatClicked(self, btn: _BeatButton, toggled: bool):
        if self._beatsCheckable:
            self.beatToggled.emit(btn.beat, toggled)
            btn.activateSelection(self._beatSelectionActive)

    def _refreshBeatButtonDragStatus(self, btn: _BeatButton):
        if self._beatsMoveable and not btn.beat.ends_act and self.isProportionalDisplay():
            btn.setDragEnabled(True)
        else:
            btn.setDragEnabled(False)

    def _actResized(self, pos: int, act: int):
        old_percentage = 0
        new_percentage = 0

        for beat in self._beats.keys():
            if beat.ends_act and beat.act == act:
                old_percentage = beat.percentage
                beat.percentage = self._percentageForX(pos - self._beatHeight // 2)
                new_percentage = beat.percentage
                break

        if new_percentage:
            for con in self._containers:
                if con.percentage == old_percentage:
                    con.percentage = new_percentage
                elif con.percentage_end == old_percentage:
                    con.percentage_end = new_percentage

            act_percentages = self._calculateActPercentages()

            for beat in self._beats.keys():
                if beat.act == act:
                    if beat.ends_act:
                        continue
                    act_start_percentage = act_percentages[beat.act - 1][0]
                    act_range = old_percentage - act_start_percentage

                    if act_range > 0:
                        relative_percentage = (beat.percentage - act_start_percentage) / act_range
                        new_act_range = new_percentage - act_start_percentage
                        beat.percentage = act_start_percentage + (relative_percentage * new_act_range)

        self._rearrangeBeats()
        self.actsResized.emit()

    def _calculateActPercentages(self):
        total_width = self._actsSplitter.width()
        percentages = []
        for act_button in self._acts:
            button_geometry = act_button.geometry()
            act_start = button_geometry.left()
            act_width = button_geometry.width()
            act_start_percentage = act_start / total_width
            act_end_percentage = (act_start + act_width) / total_width
            percentages.append((act_start_percentage, act_end_percentage))
        return percentages
