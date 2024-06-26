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
from functools import partial
from typing import Dict, Optional, Union, Set
from typing import List

import qtanim
from PyQt6.QtCore import Qt, QObject, QEvent, QSize, pyqtSignal, QModelIndex, QItemSelection
from PyQt6.QtGui import QDragEnterEvent, QResizeEvent, QCursor, QColor, QDropEvent
from PyQt6.QtWidgets import QSizePolicy, QWidget, QFrame, QToolButton, QSplitter, \
    QPushButton, QTreeView, QLabel, QTableView, \
    QAbstractItemView, QButtonGroup, QAbstractButton
from overrides import overrides
from qthandy import busy, margins, gc, pointy, vline, grid, line, retain_when_hidden
from qthandy import transparent, translucent, flow, \
    clear_layout, hbox, btn_popup, italic
from qthandy.filter import InstantTooltipEventFilter, DragEventFilter
from qtmenu import MenuWidget

from plotlyst.common import ACT_ONE_COLOR, ACT_THREE_COLOR, ACT_TWO_COLOR, PLOTLYST_SECONDARY_COLOR
from plotlyst.core.client import json_client
from plotlyst.core.domain import Scene, Novel, SceneOutcome, StoryBeat, StoryBeatType, Tag, SceneStage, \
    ReaderPosition, InformationAcquisition, Document, \
    StoryStructure, NovelSetting, CardSizeRatio
from plotlyst.core.help import scene_disaster_outcome_help, scene_trade_off_outcome_help, \
    scene_resolution_outcome_help, scene_motion_outcome_help
from plotlyst.env import app_env
from plotlyst.event.core import emit_critical, Event, EventListener, emit_event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import SceneStatusChangedEvent, \
    ActiveSceneStageChanged, AvailableSceneStagesChanged, NovelConflictTrackingToggleEvent
from plotlyst.model.common import DistributionFilterProxyModel
from plotlyst.model.distribution import CharactersScenesDistributionTableModel, TagScenesDistributionTableModel, \
    ConflictScenesDistributionTableModel, InformationScenesDistributionTableModel
from plotlyst.model.novel import NovelTagsTreeModel, TagNode
from plotlyst.model.scenes_model import ScenesTableModel
from plotlyst.service.cache import acts_registry
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import PopupMenuBuilder, action, stretch_col, \
    tool_btn, label, ExclusiveOptionalButtonGroup, set_tab_icon
from plotlyst.view.generated.scene_drive_editor_ui import Ui_SceneDriveTrackingEditor
from plotlyst.view.generated.scene_dstribution_widget_ui import Ui_CharactersScenesDistributionWidget
from plotlyst.view.generated.scenes_view_preferences_widget_ui import Ui_ScenesViewPreferences
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.button import SecondaryActionPushButton, \
    FadeOutButtonGroup
from plotlyst.view.widget.characters import CharacterSelectorButtons
from plotlyst.view.widget.input import DocumentTextEditor
from plotlyst.view.widget.labels import SelectionItemLabel, SceneLabel


class SceneOutcomeSelector(QWidget):
    selected = pyqtSignal(SceneOutcome)

    def __init__(self, parent=None, autoSelect: bool = True, extended: bool = False):
        super().__init__(parent)
        self._outcome = SceneOutcome.DISASTER
        hbox(self)
        self.btnDisaster = tool_btn(IconRegistry.disaster_icon(color='grey'), scene_disaster_outcome_help,
                                    checkable=True)
        self.btnResolution = tool_btn(IconRegistry.success_icon(color='grey'), scene_resolution_outcome_help,
                                      checkable=True)
        self.btnTradeOff = tool_btn(IconRegistry.tradeoff_icon(color='grey'), scene_trade_off_outcome_help,
                                    checkable=True)
        self.btnMotion = tool_btn(IconRegistry.motion_icon(color='grey'), scene_motion_outcome_help,
                                  checkable=True)
        self._initStyle(self.btnDisaster, '#FDD7D2')
        self._initStyle(self.btnTradeOff, '#F0C4E1')
        self._initStyle(self.btnResolution, '#CDFAEC')
        self._initStyle(self.btnMotion, '#E6CBAF')

        self.btnGroupOutcome = QButtonGroup()
        self._initButtonGroup()
        if autoSelect:
            self.btnDisaster.setChecked(True)

        self.layout().addWidget(self.btnDisaster)
        self.layout().addWidget(self.btnTradeOff)
        self.layout().addWidget(self.btnResolution)

        self._lineMotion = vline()
        self.layout().addWidget(self._lineMotion)
        self.layout().addWidget(self.btnMotion)
        self._lineMotion.setVisible(extended)
        self.btnMotion.setVisible(extended)

    def reset(self):
        btn = self.btnGroupOutcome.checkedButton()
        if btn:
            self.btnGroupOutcome.removeButton(self.btnDisaster)
            self.btnGroupOutcome.removeButton(self.btnResolution)
            self.btnGroupOutcome.removeButton(self.btnTradeOff)
            self.btnGroupOutcome.removeButton(self.btnMotion)
            btn.setChecked(False)

            self.btnGroupOutcome = QButtonGroup()
            self._initButtonGroup()

    def refresh(self, outcome: SceneOutcome):
        if outcome == SceneOutcome.DISASTER:
            self.btnDisaster.setChecked(True)
        elif outcome == SceneOutcome.RESOLUTION:
            self.btnResolution.setChecked(True)
        elif outcome == SceneOutcome.TRADE_OFF:
            self.btnTradeOff.setChecked(True)
        elif outcome == SceneOutcome.MOTION:
            self.btnMotion.setChecked(True)

    def _clicked(self, checked: bool):
        if not checked:
            return
        if self.btnDisaster.isChecked():
            self._outcome = SceneOutcome.DISASTER
        elif self.btnResolution.isChecked():
            self._outcome = SceneOutcome.RESOLUTION
        elif self.btnTradeOff.isChecked():
            self._outcome = SceneOutcome.TRADE_OFF
        elif self.btnMotion.isChecked():
            self._outcome = SceneOutcome.MOTION

        self.selected.emit(self._outcome)

    def _initButtonGroup(self):
        self.btnGroupOutcome.setExclusive(True)
        self.btnGroupOutcome.addButton(self.btnDisaster)
        self.btnGroupOutcome.addButton(self.btnTradeOff)
        self.btnGroupOutcome.addButton(self.btnResolution)
        self.btnGroupOutcome.addButton(self.btnMotion)

        self.btnGroupOutcome.buttonClicked.connect(self._clicked)

    def _initStyle(self, btn: QToolButton, color: str):
        btn.setIconSize(QSize(20, 20))
        btn.setStyleSheet(f'''
        QToolButton {{
            border-radius: 12px;
            border: 1px hidden lightgrey;
            padding: 2px;
        }}
        QToolButton:hover {{
            background: {color};
        }}
        ''')


class SceneTagSelector(QWidget):
    def __init__(self, novel: Novel, parent=None):
        super(SceneTagSelector, self).__init__(parent)
        self.novel = novel

        hbox(self)
        self.btnSelect = QToolButton(self)
        self.btnSelect.setIcon(IconRegistry.tag_plus_icon())
        self.btnSelect.setCursor(Qt.CursorShape.PointingHandCursor)

        self._tagsModel = NovelTagsTreeModel(self.novel)
        self._tagsModel.selectionChanged.connect(self._selectionChanged)
        self._treeSelectorView = QTreeView()
        self._treeSelectorView.setCursor(Qt.CursorShape.PointingHandCursor)
        self._treeSelectorView.setModel(self._tagsModel)
        self._treeSelectorView.setHeaderHidden(True)
        self._treeSelectorView.clicked.connect(self._toggle)
        self._treeSelectorView.expandAll()
        self._tagsModel.modelReset.connect(self._treeSelectorView.expandAll)
        btn_popup(self.btnSelect, self._treeSelectorView)

        self.wdgTags = QFrame(self)
        flow(self.wdgTags)

        self.layout().addWidget(group(self.btnSelect, QLabel('Tags:'), margin=0), alignment=Qt.AlignmentFlag.AlignTop)
        self.layout().addWidget(self.wdgTags)

    def setScene(self, scene: Scene):
        self._tagsModel.clear()
        for tag in scene.tags(self.novel):
            self._tagsModel.check(tag)

    def tags(self) -> List[Tag]:
        return self._tagsModel.checkedTags()

    def _selectionChanged(self):
        tags = self._tagsModel.checkedTags()
        clear_layout(self.wdgTags)
        for tag in tags:
            label = SelectionItemLabel(tag, self.wdgTags, removalEnabled=True)
            label.removalRequested.connect(partial(self._tagsModel.uncheck, tag))
            self.wdgTags.layout().addWidget(label)

    def _toggle(self, index: QModelIndex):
        node = index.data(NovelTagsTreeModel.NodeRole)
        if isinstance(node, TagNode):
            self._tagsModel.toggle(node.tag)


class SceneSelector(SecondaryActionPushButton):
    sceneSelected = pyqtSignal(Scene)

    def __init__(self, novel: Novel, text: str = '', parent=None):
        super(SceneSelector, self).__init__(parent)
        self.novel = novel
        self.setText(text)
        italic(self)
        self.setIcon(IconRegistry.scene_icon('grey'))

        self._lstScenes = QTableView()
        self._lstScenes.verticalHeader().setHidden(True)
        self._lstScenes.horizontalHeader().setHidden(True)
        self._lstScenes.verticalHeader().setDefaultSectionSize(20)
        self._lstScenes.horizontalHeader().setDefaultSectionSize(24)
        self._lstScenes.setShowGrid(False)
        self._lstScenes.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._lstScenes.clicked.connect(self._selected)
        pointy(self._lstScenes)
        self.menu = btn_popup(self, self._lstScenes)
        self.menu.aboutToShow.connect(self._beforePopup)

    @busy
    def _beforePopup(self):
        self._scenesModel = ScenesTableModel(self.novel)

        self._lstScenes.setModel(self._scenesModel)
        for col in range(self._scenesModel.columnCount()):
            self._lstScenes.hideColumn(col)
        self._lstScenes.showColumn(ScenesTableModel.ColPov)
        self._lstScenes.showColumn(ScenesTableModel.ColType)
        self._lstScenes.showColumn(ScenesTableModel.ColTitle)
        self._lstScenes.horizontalHeader().swapSections(ScenesTableModel.ColType, ScenesTableModel.ColTitle)

        stretch_col(self._lstScenes, ScenesTableModel.ColTitle)

    def _selected(self, index: QModelIndex):
        scene = index.data(ScenesTableModel.SceneRole)
        self.sceneSelected.emit(scene)
        self.menu.hide()


class SceneLabelLinkWidget(QWidget):
    sceneSelected = pyqtSignal(Scene)

    def __init__(self, novel: Novel, text: str = '', parent=None):
        super(SceneLabelLinkWidget, self).__init__(parent)
        self.novel = novel
        self.scene: Optional[Scene] = None

        self.label: Optional[SceneLabel] = None

        hbox(self)
        self.btnSelect = SceneSelector(self.novel, text, parent=self)
        self.layout().addWidget(self.btnSelect)
        self.btnSelect.sceneSelected.connect(self.sceneSelected.emit)

    def setScene(self, scene: Scene):
        self.scene = scene
        if self.label is None:
            self.label = SceneLabel(self.scene)
            self.layout().addWidget(self.label)
            self.label.clicked.connect(self.btnSelect.menu.show)
        else:
            self.label.setScene(scene)

        self.btnSelect.setHidden(True)


class SceneFilterWidget(QWidget):
    def __init__(self, novel: Novel, parent=None):
        super(SceneFilterWidget, self).__init__(parent)
        self.novel = novel
        self.povFilter = CharacterSelectorButtons()
        margins(self.povFilter, left=15)
        self.povFilter.setExclusive(False)
        self.povFilter.setCharacters(self.novel.pov_characters())

        self.btnAct1 = tool_btn(IconRegistry.act_one_icon(), base=True, checkable=True)
        self.btnAct2 = tool_btn(IconRegistry.act_two_icon(), base=True, checkable=True)
        self.btnAct3 = tool_btn(IconRegistry.act_three_icon(), base=True, checkable=True)
        self.btnAct1.setChecked(True)
        self.btnAct2.setChecked(True)
        self.btnAct3.setChecked(True)
        self.wdgActs = QWidget()
        hbox(self.wdgActs)
        margins(self.wdgActs, left=15)
        self.wdgActs.layout().addWidget(self.btnAct1)
        self.wdgActs.layout().addWidget(self.btnAct2)
        self.wdgActs.layout().addWidget(self.btnAct3)

        grid(self)
        self.layout().addWidget(label('Point of view:'), 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.povFilter, 0, 1)
        self.layout().addWidget(label('Acts:', ), 1, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.wdgActs, 1, 1, alignment=Qt.AlignmentFlag.AlignLeft)


class _BeatButton(QToolButton):
    def __init__(self, beat: StoryBeat, parent=None):
        super(_BeatButton, self).__init__(parent)
        self.beat = beat
        self.setStyleSheet('QToolButton {background-color: rgba(0,0,0,0); border:0px;} QToolTip {border: 0px;}')
        self.installEventFilter(InstantTooltipEventFilter(self))

    def dataFunc(self, _):
        return self.beat


def is_midpoint(beat: StoryBeat) -> bool:
    return beat.text == 'Midpoint'


class SceneStoryStructureWidget(QWidget):
    BeatMimeType = 'application/story-beat'

    beatSelected = pyqtSignal(StoryBeat)
    beatRemovalRequested = pyqtSignal(StoryBeat)
    actsResized = pyqtSignal()
    beatMoved = pyqtSignal(StoryBeat)

    def __init__(self, parent=None):
        super(SceneStoryStructureWidget, self).__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self._checkOccupiedBeats: bool = True
        self._beatsCheckable: bool = False
        self._beatsMoveable: bool = False
        self._removalContextMenuEnabled: bool = False
        self._actsClickable: bool = False
        self._actsResizeable: bool = False
        self._beatCursor = Qt.CursorShape.PointingHandCursor
        self.novel: Optional[Novel] = None
        self.structure: Optional[StoryStructure] = None
        self._acts: List[QPushButton] = []
        self._beats: Dict[StoryBeat, QToolButton] = {}
        self._containers: Dict[StoryBeat, QPushButton] = {}
        self._actsSplitter: Optional[QSplitter] = None
        self.btnCurrentScene = QToolButton(self)
        self._currentScenePercentage = 1
        self.btnCurrentScene.setIcon(IconRegistry.circle_icon(color=PLOTLYST_SECONDARY_COLOR))
        self.btnCurrentScene.setHidden(True)
        transparent(self.btnCurrentScene)
        self._wdgLine = QWidget(self)
        hbox(self._wdgLine, 0, 0)
        self._lineHeight: int = 22
        self._beatHeight: int = 20
        self._margin: int = 5
        self._containerTopMargin: int = 6

    def checkOccupiedBeats(self) -> bool:
        return self._checkOccupiedBeats

    def setCheckOccupiedBeats(self, value: bool):
        self._checkOccupiedBeats = value

    def beatsCheckable(self) -> bool:
        return self._beatsCheckable

    def setBeatsCheckable(self, value: bool):
        self._beatsCheckable = value

    def setBeatsMoveable(self, enabled: bool):
        self._beatsMoveable = enabled
        self.setAcceptDrops(enabled)

    def setRemovalContextMenuEnabled(self, value: bool):
        self._removalContextMenuEnabled = value

    def beatCursor(self) -> int:
        return self._beatCursor

    def setBeatCursor(self, value: int):
        self._beatCursor = value

    def setStructure(self, novel: Novel, structure: Optional[StoryStructure] = None):
        self.novel = novel
        self.structure = structure if structure else novel.active_story_structure
        self._acts.clear()
        self._beats.clear()

        occupied_beats = acts_registry.occupied_beats()
        for beat in self.structure.beats:
            if beat.type == StoryBeatType.CONTAINER:
                btn = QPushButton(self)
                if beat.percentage_end - beat.percentage > 7:
                    btn.setText(beat.text)
                self._containers[beat] = btn
                btn.setStyleSheet(f'''
                    QPushButton {{border-top:2px dashed {beat.icon_color}; color: {beat.icon_color};}}
                ''')
                italic(btn)
                translucent(btn)
            else:
                btn = _BeatButton(beat, self)
                self._beats[beat] = btn

            self.__initButton(beat, btn, occupied_beats)

        self._actsSplitter = QSplitter(self._wdgLine)
        self._actsSplitter.setContentsMargins(0, 0, 0, 0)
        self._actsSplitter.setChildrenCollapsible(False)
        self._actsSplitter.setHandleWidth(1)
        self._wdgLine.layout().addWidget(self._actsSplitter)

        act = self._actButton('Act 1', ACT_ONE_COLOR, left=True)
        self._acts.append(act)
        self._wdgLine.layout().addWidget(act)
        self._actsSplitter.addWidget(act)
        act = self._actButton('Act 2', ACT_TWO_COLOR)
        self._acts.append(act)
        self._actsSplitter.addWidget(act)

        act = self._actButton('Act 3', ACT_THREE_COLOR, right=True)
        self._acts.append(act)
        self._actsSplitter.addWidget(act)
        for btn in self._acts:
            btn.setEnabled(self._actsClickable)

        beats = self.structure.act_beats()
        if not len(beats) == 2:
            return emit_critical('Only 3 acts are supported at the moment for story structure widget')

        self._actsSplitter.setSizes([int(10 * beats[0].percentage),
                                     int(10 * (beats[1].percentage - beats[0].percentage)),
                                     int(10 * (100 - beats[1].percentage))])
        self._actsSplitter.setEnabled(self._actsResizeable)
        self._actsSplitter.splitterMoved.connect(self._actResized)
        self.update()

    def __initButton(self, beat: StoryBeat, btn: Union[QAbstractButton, _BeatButton], occupied_beats: Set[StoryBeat]):
        if beat.icon:
            btn.setIcon(IconRegistry.from_name(beat.icon, beat.icon_color))
        btn.setToolTip(f'<b style="color: {beat.icon_color}">{beat.text}')
        if beat.type == StoryBeatType.BEAT:
            btn.toggled.connect(partial(self._beatToggled, btn))
            btn.clicked.connect(partial(self._beatClicked, btn))
            btn.installEventFilter(self)
            if self._beatsMoveable and not beat.ends_act and not is_midpoint(beat):
                btn.installEventFilter(
                    DragEventFilter(btn, self.BeatMimeType, btn.dataFunc, hideTarget=True))
                btn.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                btn.setCursor(self._beatCursor)
            if self._checkOccupiedBeats and beat not in occupied_beats:
                if self._beatsCheckable:
                    btn.setCheckable(True)
                self._beatToggled(btn, False)
        if not beat.enabled:
            btn.setHidden(True)

    @overrides
    def minimumSizeHint(self) -> QSize:
        beat_height = self._beatHeight * 2 if self._containers else self._beatHeight
        return QSize(300, self._lineHeight + beat_height + 6)

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if isinstance(watched, QToolButton) and watched.isCheckable() and not watched.isChecked():
            if event.type() == QEvent.Type.Enter:
                translucent(watched)
            elif event.type() == QEvent.Type.Leave:
                translucent(watched, 0.2)
        return super(SceneStoryStructureWidget, self).eventFilter(watched, event)

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
    def resizeEvent(self, event: QResizeEvent) -> None:
        self._rearrangeBeats()
        if self._actsResizeable and self._acts:
            self._acts[0].setMinimumWidth(max(self._xForPercentage(15), 1))
            self._acts[0].setMaximumWidth(self._xForPercentage(30))
            self._acts[2].setMinimumWidth(max(self._xForPercentage(10), 1))
            self._acts[2].setMaximumWidth(self._xForPercentage(30))

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
        self._wdgLine.setGeometry(0, 0, self.width(), self._lineHeight)
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
        btn.setStyleSheet(
            f'QToolButton {{border: 3px dotted {PLOTLYST_SECONDARY_COLOR}; border-radius: 5;}} QToolTip {{border: 0px;}}')
        btn.setFixedSize(self._beatHeight + 6, self._beatHeight + 6)
        qtanim.glow(btn, color=QColor(beat.icon_color))

    def refreshBeat(self, beat: StoryBeat):
        if beat.type == StoryBeatType.BEAT:
            btn = self._beats.get(beat)
            if beat.icon:
                btn.setIcon(IconRegistry.from_name(beat.icon, beat.icon_color))
            btn.setToolTip(f'<b style="color: {beat.icon_color}">{beat.text}')

    def replaceBeat(self, old: StoryBeat, new: StoryBeat):
        if old.type == StoryBeatType.BEAT and new.type == StoryBeatType.BEAT:
            btn = self._beats.pop(old)
            self._beats[new] = btn
            btn.setIcon(IconRegistry.from_name(new.icon, new.icon_color))
            btn.setToolTip(f'<b style="color: {new.icon_color}">{new.text}')
            btn.beat = new

    def removeBeat(self, beat: StoryBeat):
        if beat.type == StoryBeatType.BEAT:
            btn = self._beats.pop(beat)
            gc(btn)

    def insertBeat(self, beat: StoryBeat):
        if beat.type == StoryBeatType.BEAT:
            btn = _BeatButton(beat, self)
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
        else:
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
            transparent(btn)
            btn.setFixedSize(self._beatHeight, self._beatHeight)

    def clearHighlights(self):
        self.unhighlightBeats()
        self.btnCurrentScene.setHidden(True)

    def toggleBeat(self, beat: StoryBeat, toggled: bool):
        btn = self._beats.get(beat)
        if btn is None:
            return

        if toggled:
            btn.setCheckable(False)
        else:
            pointy(btn)
            btn.setCheckable(True)
            self._beatToggled(btn, False)

    def toggleBeatVisibility(self, beat: StoryBeat):
        btn = self._beats.get(beat)
        if btn is None:
            return

        if beat.enabled:
            qtanim.fade_in(btn)
        else:
            qtanim.fade_out(btn)

    def _actButton(self, text: str, color: str, left: bool = False, right: bool = False) -> QPushButton:
        act = QPushButton(self)
        act.setText(text)
        act.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        act.setFixedHeight(self._lineHeight)
        act.setCursor(Qt.CursorShape.PointingHandCursor)
        act.setCheckable(True)
        act.setStyleSheet(f'''
        QPushButton {{
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 {color}, stop: 1 {color});
            border: 1px solid #8f8f91;
            border-top-left-radius: {8 if left else 0}px;
            border-bottom-left-radius: {8 if left else 0}px;
            border-top-right-radius: {8 if right else 0}px;
            border-bottom-right-radius: {8 if right else 0}px;
            color:white;
            padding: 0px;
        }}
        ''')

        act.setChecked(True)
        act.toggled.connect(partial(self._actToggled, act))

        return act

    def _actToggled(self, btn: QToolButton, toggled: bool):
        translucent(btn, 1.0 if toggled else 0.2)

    def _beatToggled(self, btn: QToolButton, toggled: bool):
        translucent(btn, 1.0 if toggled else 0.2)

    def _beatClicked(self, btn: _BeatButton):
        if btn.isCheckable() and btn.isChecked():
            self.beatSelected.emit(btn.beat)
            btn.setCheckable(False)
        elif not btn.isCheckable() and self._removalContextMenuEnabled:
            builder = PopupMenuBuilder.from_widget_position(self, self.mapFromGlobal(QCursor.pos()))
            builder.add_action('Remove', IconRegistry.trash_can_icon(),
                               lambda: self.beatRemovalRequested.emit(btn.beat))
            builder.popup()

    def _actResized(self, pos: int, index: int):
        old_percentage = 0
        new_percentage = 0
        for beat in self._beats.keys():
            if beat.ends_act and beat.act == index:
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

        self._rearrangeBeats()
        self.actsResized.emit()


class ScenesPreferencesWidget(QWidget, Ui_ScenesViewPreferences):
    DEFAULT_CARD_WIDTH: int = 175
    settingToggled = pyqtSignal(NovelSetting, bool)
    cardWidthChanged = pyqtSignal(int)
    cardRatioChanged = pyqtSignal(CardSizeRatio)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.novel = novel

        self.btnCardsWidth.setIcon(IconRegistry.from_name('ei.resize-horizontal'))
        self.btnPov.setIcon(IconRegistry.eye_open_icon())
        self.btnPurpose.setIcon(IconRegistry.from_name('fa5s.yin-yang'))
        self.btnCharacters.setIcon(IconRegistry.character_icon())
        self.btnStorylines.setIcon(IconRegistry.storylines_icon())
        self.btnStage.setIcon(IconRegistry.progress_check_icon())

        self.btnTablePov.setIcon(IconRegistry.eye_open_icon())
        self.btnTableStorylines.setIcon(IconRegistry.storylines_icon())
        self.btnTableCharacters.setIcon(IconRegistry.character_icon())
        self.btnTablePurpose.setIcon(IconRegistry.from_name('fa5s.yin-yang'))

        self.tabCards.layout().insertWidget(1, line(color='lightgrey'))
        self.tabTable.layout().insertWidget(1, line(color='lightgrey'))
        # self.tabCards.layout().insertWidget(6, wrap(line(color='lightgrey'), margin_left=10))

        self.btnGroup = ExclusiveOptionalButtonGroup()
        self.btnGroup.addButton(self.cbCharacters)
        self.btnGroup.addButton(self.cbStorylines)

        self.cbPov.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_CARD_POV))
        self.cbPurpose.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_CARD_PURPOSE))
        self.cbStage.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_CARD_STAGE))

        self.cbTablePov.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_TABLE_POV))
        self.cbTableStorylines.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_TABLE_STORYLINES))
        self.cbTableCharacters.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_TABLE_CHARACTERS))
        self.cbTablePurpose.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_TABLE_PURPOSE))

        self.cbPov.clicked.connect(partial(self.settingToggled.emit, NovelSetting.SCENE_CARD_POV))
        self.cbPurpose.clicked.connect(partial(self.settingToggled.emit, NovelSetting.SCENE_CARD_PURPOSE))
        self.cbStage.clicked.connect(partial(self.settingToggled.emit, NovelSetting.SCENE_CARD_STAGE))

        self.cbTablePov.clicked.connect(partial(self.settingToggled.emit, NovelSetting.SCENE_TABLE_POV))
        self.cbTableStorylines.clicked.connect(partial(self.settingToggled.emit, NovelSetting.SCENE_TABLE_STORYLINES))
        self.cbTableCharacters.clicked.connect(partial(self.settingToggled.emit, NovelSetting.SCENE_TABLE_CHARACTERS))
        self.cbTablePurpose.clicked.connect(partial(self.settingToggled.emit, NovelSetting.SCENE_TABLE_PURPOSE))

        self.sliderCards.setValue(self.novel.prefs.setting(NovelSetting.SCENE_CARD_WIDTH, self.DEFAULT_CARD_WIDTH))
        self.sliderCards.valueChanged.connect(self.cardWidthChanged)

        # self.rb23.clicked.connect(partial(self.cardRatioChanged.emit, CardSizeRatio.RATIO_2_3))
        # self.rb34.clicked.connect(partial(self.cardRatioChanged.emit, CardSizeRatio.RATIO_3_4))
        self.rb23.setHidden(True)
        self.rb34.setHidden(True)

        self.wdgCharacters.setHidden(True)
        self.wdgStorylines.setHidden(True)

        set_tab_icon(self.tabWidget, self.tabCards, IconRegistry.cards_icon())
        set_tab_icon(self.tabWidget, self.tabTable, IconRegistry.table_icon())

    def showCardsTab(self):
        self.tabWidget.setCurrentWidget(self.tabCards)

    def showTableTab(self):
        self.tabWidget.setCurrentWidget(self.tabTable)


class SceneNotesEditor(DocumentTextEditor):

    def __init__(self, parent=None):
        super(SceneNotesEditor, self).__init__(parent)
        self._scene: Optional[Scene] = None
        self.setTitleVisible(False)
        self.setPlaceholderText('Scene notes')

        self.textEdit.textChanged.connect(self._save)

        self.repo = RepositoryPersistenceManager.instance()

    def setScene(self, scene: Scene):
        self._scene = scene
        if self._scene.document is None:
            self._scene.document = Document('', scene_id=self._scene.id)
            self._scene.document.loaded = True
        if not scene.document.loaded:
            json_client.load_document(app_env.novel, scene.document)

        self.setText(scene.document.content, '')

    def _save(self):
        if self._scene is None:
            return
        self._scene.document.content = self.textEdit.toHtml()
        self.repo.update_doc(app_env.novel, self._scene.document)


class SceneStageButton(QToolButton, EventListener):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene: Optional[Scene] = None
        self._novel: Optional[Novel] = None
        self._stageOk: bool = False

        transparent(self)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        pointy(self)

        self.repo = RepositoryPersistenceManager.instance()

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, (ActiveSceneStageChanged, AvailableSceneStagesChanged)):
            self.updateStage()
        elif isinstance(event, SceneStatusChangedEvent) and event.scene == self._scene:
            self.updateStage()

    def setScene(self, scene: Scene, novel: Novel):
        self._scene = scene
        self._novel = novel

        dispatcher = event_dispatchers.instance(self._novel)
        dispatcher.register(self, ActiveSceneStageChanged, SceneStatusChangedEvent, AvailableSceneStagesChanged)

        self.updateStage()

    def stageOk(self) -> bool:
        return self._stageOk

    def updateStage(self):
        if self._scene is None:
            return
        self._stageOk = False
        active_stage = self._novel.active_stage
        if self._scene.stage and active_stage:
            active_stage_index = self._novel.stages.index(active_stage)
            scene_stage_index = self._novel.stages.index(self._scene.stage)

            if scene_stage_index >= active_stage_index:
                self._stageOk = True
                self.setIcon(IconRegistry.ok_icon(PLOTLYST_SECONDARY_COLOR))

        if not self._stageOk:
            self.setIcon(IconRegistry.progress_check_icon('grey'))

        menu = MenuWidget(self)
        for stage in self._novel.stages:
            act = action(stage.text, slot=partial(self._changeStage, stage), checkable=True, parent=menu)
            act.setChecked(self._scene.stage == stage)
            menu.addAction(act)

    def _changeStage(self, stage: SceneStage):
        self._scene.stage = stage
        self.updateStage()
        self.repo.update_scene(self._scene)

        emit_event(self._novel, SceneStatusChangedEvent(self, self._scene))


class SceneDriveTrackingEditor(QWidget, Ui_SceneDriveTrackingEditor):
    def __init__(self, parent=None):
        super(SceneDriveTrackingEditor, self).__init__(parent)
        self.setupUi(self)
        self.scene: Optional[Scene] = None

        self.sliderWorld.valueChanged.connect(self._worldBuildingChanged)
        self.sliderTension.valueChanged.connect(self._tensionChanged)

        self.informationBtnGroup = FadeOutButtonGroup()
        self.informationBtnGroup.addButton(self.btnDiscovery)
        self.informationBtnGroup.addButton(self.btnRevelation)
        self.informationBtnGroup.buttonClicked.connect(self._informationClicked)

        self.readerPosBtnGroup = FadeOutButtonGroup()
        self.readerPosBtnGroup.addButton(self.btnReaderSuperior)
        self.readerPosBtnGroup.addButton(self.btnReaderInferior)
        self.readerPosBtnGroup.buttonClicked.connect(self._readerPosClicked)

        self.btnDeuxExMachina.clicked.connect(self._deusExClicked)

    def reset(self):
        self.scene = None
        self.sliderWorld.setValue(0)
        self.sliderTension.setValue(0)
        self.readerPosBtnGroup.reset()
        self.informationBtnGroup.reset()
        self.btnDeuxExMachina.setChecked(False)

    def setScene(self, scene: Scene):
        self.reset()
        self.scene = scene

        self.sliderWorld.setValue(self.scene.drive.worldbuilding)
        self.sliderTension.setValue(self.scene.drive.tension)
        self.btnDeuxExMachina.setChecked(self.scene.drive.deus_ex_machina)

        if self.scene.drive.new_information == InformationAcquisition.DISCOVERY:
            self.informationBtnGroup.toggle(self.btnDiscovery)
        elif self.scene.drive.new_information == InformationAcquisition.REVELATION:
            self.informationBtnGroup.toggle(self.btnRevelation)

        if self.scene.drive.reader_position == ReaderPosition.SUPERIOR:
            self.readerPosBtnGroup.toggle(self.btnReaderSuperior)
        elif self.scene.drive.reader_position == ReaderPosition.INFERIOR:
            self.readerPosBtnGroup.toggle(self.btnReaderInferior)

    def _worldBuildingChanged(self, value: int):
        if value > 0 and self.sliderWorld.isVisible():
            qtanim.glow(self.sliderWorld, radius=12, color=QColor('#40916c'))

        if self.scene:
            self.scene.drive.worldbuilding = value

    def _tensionChanged(self, value: int):
        if value > 0 and self.sliderTension.isVisible():
            qtanim.glow(self.sliderTension, radius=12, color=QColor('#d00000'))

        if self.scene:
            self.scene.drive.tension = value

    def _readerPosClicked(self):
        if self.readerPosBtnGroup.checkedButton() == self.btnReaderSuperior:
            self.scene.drive.reader_position = ReaderPosition.SUPERIOR
        elif self.readerPosBtnGroup.checkedButton() == self.btnReaderInferior:
            self.scene.drive.reader_position = ReaderPosition.INFERIOR

    def _informationClicked(self):
        if self.informationBtnGroup.checkedButton() == self.btnDiscovery:
            self.scene.drive.new_information = InformationAcquisition.DISCOVERY
        elif self.informationBtnGroup.checkedButton() == self.btnRevelation:
            self.scene.drive.new_information = InformationAcquisition.REVELATION

    def _deusExClicked(self, checked: bool):
        self.scene.drive.deus_ex_machina = checked


class ScenesDistributionWidget(QWidget, Ui_CharactersScenesDistributionWidget, EventListener):
    avg_text: str = 'Characters per scene: '
    common_text: str = 'Common scenes: '

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.novel = novel
        self.average = 0

        self.btnCharacters.setIcon(IconRegistry.character_icon())
        self.btnConflicts.setIcon(IconRegistry.conflict_icon('black', color_on=PLOTLYST_SECONDARY_COLOR))
        self.btnTags.setIcon(IconRegistry.tags_icon())
        self.btnInformation.setIcon(IconRegistry.from_name('fa5s.book-reader', color_on=PLOTLYST_SECONDARY_COLOR))
        self.btnTags.setHidden(True)

        self._model = CharactersScenesDistributionTableModel(self.novel)
        self._scenes_proxy = DistributionFilterProxyModel()
        self._scenes_proxy.setSourceModel(self._model)
        self._scenes_proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._scenes_proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._scenes_proxy.setSortRole(CharactersScenesDistributionTableModel.SortRole)
        self._scenes_proxy.sort(CharactersScenesDistributionTableModel.IndexTags, Qt.SortOrder.DescendingOrder)
        self.tblSceneDistribution.horizontalHeader().setDefaultSectionSize(26)
        self.tblSceneDistribution.setModel(self._scenes_proxy)
        self.tblSceneDistribution.hideColumn(0)
        self.tblSceneDistribution.hideColumn(1)
        self.tblCharacters.setModel(self._scenes_proxy)
        self.tblCharacters.hideColumn(0)
        self.tblCharacters.setColumnWidth(CharactersScenesDistributionTableModel.IndexTags, 70)
        self.tblCharacters.setMaximumWidth(70)

        self.tblCharacters.selectionModel().selectionChanged.connect(self._on_character_selected)
        self.tblSceneDistribution.selectionModel().selectionChanged.connect(self._on_scene_selected)

        self.btnCharacters.toggled.connect(self._toggle_characters)
        self.btnConflicts.toggled.connect(self._toggle_conflicts)
        self.btnInformation.toggled.connect(self._toggle_information)
        self.btnTags.toggled.connect(self._toggle_tags)

        transparent(self.spinAverage)
        retain_when_hidden(self.spinAverage)

        self.btnCharacters.setChecked(True)
        self.btnConflicts.setVisible(self.novel.prefs.toggled(NovelSetting.Track_conflict))
        event_dispatchers.instance(self.novel).register(self, NovelConflictTrackingToggleEvent)

        self.refresh()

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, NovelConflictTrackingToggleEvent):
            self.btnConflicts.setVisible(event.toggled)
            if self.btnConflicts.isChecked():
                self.btnCharacters.setChecked(True)

    def refresh(self):
        if self.novel.scenes:
            self.average = sum([len(x.characters) + 1 for x in self.novel.scenes]) / len(self.novel.scenes)
        else:
            self.average = 0
        for col in range(self._model.columnCount()):
            if col == CharactersScenesDistributionTableModel.IndexTags:
                continue
            self.tblCharacters.hideColumn(col)
        self.spinAverage.setValue(self.average)
        self.tblSceneDistribution.horizontalHeader().setMaximumSectionSize(15)
        self._model.modelReset.emit()

    def setActsFilter(self, act: int, filter: bool):
        self._scenes_proxy.setActsFilter(act, filter)

    def _toggle_characters(self, toggled: bool):
        if toggled:
            self._model = CharactersScenesDistributionTableModel(self.novel)
            self._scenes_proxy.setSourceModel(self._model)
            self.tblCharacters.hideColumn(0)
            self.tblCharacters.setColumnWidth(CharactersScenesDistributionTableModel.IndexTags, 70)
            self.tblCharacters.setMaximumWidth(70)

            self.spinAverage.setVisible(True)

    # def _toggle_goals(self, toggled: bool):
    #     if toggled:
    #         self._model = GoalScenesDistributionTableModel(self.novel)
    #         self._scenes_proxy.setSourceModel(self._model)
    #         self.tblCharacters.hideColumn(0)
    #         self.tblCharacters.setColumnWidth(CharactersScenesDistributionTableModel.IndexTags, 170)
    #         self.tblCharacters.setMaximumWidth(170)
    #
    #         self.spinAverage.setVisible(False)

    def _toggle_conflicts(self, toggled: bool):
        if toggled:
            self._model = ConflictScenesDistributionTableModel(self.novel)
            self._scenes_proxy.setSourceModel(self._model)
            self.tblCharacters.showColumn(0)
            self.tblCharacters.setColumnWidth(CharactersScenesDistributionTableModel.IndexMeta, 34)
            self.tblCharacters.setColumnWidth(CharactersScenesDistributionTableModel.IndexTags, 170)
            self.tblCharacters.setMaximumWidth(204)

            self.spinAverage.setVisible(False)

    def _toggle_information(self, toggled: bool):
        if toggled:
            self._model = InformationScenesDistributionTableModel(self.novel)
            self._scenes_proxy.setSourceModel(self._model)
            self.tblCharacters.hideColumn(0)
            self.tblCharacters.setColumnWidth(CharactersScenesDistributionTableModel.IndexTags, 170)
            self.tblCharacters.setMaximumWidth(170)

            self.spinAverage.setVisible(False)

    def _toggle_tags(self, toggled: bool):
        if toggled:
            self._model = TagScenesDistributionTableModel(self.novel)
            self._scenes_proxy.setSourceModel(self._model)
            self.tblCharacters.hideColumn(0)
            self.tblCharacters.setColumnWidth(CharactersScenesDistributionTableModel.IndexTags, 170)
            self.tblCharacters.setMaximumWidth(170)

            self.spinAverage.setVisible(False)

    def _on_character_selected(self):
        selected = self.tblCharacters.selectionModel().selectedIndexes()
        self._model.highlightTags(
            [self._scenes_proxy.mapToSource(x) for x in selected])

        if selected and len(selected) > 1:
            self.spinAverage.setPrefix(self.common_text)
            self.spinAverage.setValue(self._model.commonScenes())
        else:
            self.spinAverage.setPrefix(self.avg_text)
            self.spinAverage.setValue(self.average)

        self.tblSceneDistribution.clearSelection()

    def _on_scene_selected(self, selection: QItemSelection):
        indexes = selection.indexes()
        if not indexes:
            return
        self._model.highlightScene(self._scenes_proxy.mapToSource(indexes[0]))
        self.tblCharacters.clearSelection()
