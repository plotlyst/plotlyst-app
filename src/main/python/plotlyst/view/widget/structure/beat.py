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
from typing import Optional, Dict

from PyQt6.QtCore import QEvent, QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import QFrame, QWidget
from overrides import overrides
from qthandy import transparent, gc, clear_layout, italic, flow, vbox, hbox, translucent, bold, retain_when_hidden

from plotlyst.common import act_color, RELAXED_WHITE_COLOR
from plotlyst.core.domain import StoryStructure, Novel, StoryBeat, \
    StoryBeatType, midpoints
from plotlyst.view.common import label
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.display import Icon
from plotlyst.view.widget.input import Toggle, AutoAdjustableTextEdit
from plotlyst.view.widget.structure.timeline import StoryStructureTimelineWidget


class BeatWidget(QFrame):
    beatHighlighted = pyqtSignal(StoryBeat)
    beatToggled = pyqtSignal(StoryBeat)

    def __init__(self, novel: Novel, beat: StoryBeat, checkOccupiedBeats: bool = True, parent=None,
                 toggleEnabled: bool = True):
        super().__init__(parent)
        self.setObjectName('BeatWidget')
        self._novel = novel
        self.beat = beat
        self._checkOccupiedBeats = checkOccupiedBeats
        self._toggleEnabled = toggleEnabled

        self.lblTitle = label(bold=True)
        transparent(self.lblTitle)
        self.textDescription = AutoAdjustableTextEdit()
        # self.textDescription.setMaximumHeight(130)
        self.textDescription.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textDescription.setReadOnly(True)
        italic(self.textDescription)
        self.textDescription.setProperty('transparent', True)
        self.textDescription.setProperty('description', True)
        self.btnIcon = Icon()
        self.cbToggle = Toggle()
        # transparent(self.btnIcon)
        # bold(self.lblTitle)
        # bold(self.lblSceneTitle)

        # self.btnSceneSelector = SceneSelector(app_env.novel)
        # decr_icon(self.btnSceneSelector, 2)
        # retain_when_hidden(self.btnSceneSelector)
        # self.layoutRight.insertWidget(0, self.btnSceneSelector,
        #                               alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        # self.btnSceneSelector.setHidden(True)
        # self.btnSceneSelector.sceneSelected.connect(self._sceneLinked)
        # transparent(self.wdgToggleParent)
        #
        # retain_when_hidden(self.cbToggle)

        if self._canBeToggled():
            retain_when_hidden(self.cbToggle)
        else:
            self.cbToggle.setDisabled(True)
        self.cbToggle.setHidden(True)
        self.cbToggle.setChecked(self.beat.enabled)
        self.cbToggle.toggled.connect(self._beatToggled)
        self.cbToggle.clicked.connect(self._beatClicked)

        # self.scene: Optional[Scene] = None
        # self.repo = RepositoryPersistenceManager.instance()

        vbox(self, 4, 2)
        self.wdgTop = QWidget()
        hbox(self.wdgTop)
        self.wdgTop.layout().addWidget(self.btnIcon)
        self.wdgTop.layout().addWidget(self.lblTitle)
        self.wdgTop.layout().addWidget(self.cbToggle, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(self.wdgTop)
        self.layout().addWidget(self.textDescription)
        self.updateInfo()
        self._beatToggled(self.cbToggle.isChecked())
        # self.refresh()

        self.installEventFilter(self)

        # self._synopsisConnector = DelayedSignalSlotConnector(self.textSynopsis.textChanged, self._synopsisEdited,
        #                                                      parent=self)
        # dispatcher = event_dispatchers.instance(self._novel)
        # dispatcher.register(self, SceneChangedEvent, SceneDeletedEvent)

    def updateInfo(self):
        self.lblTitle.setText(self.beat.text)
        self.textDescription.setText(self.beat.description)
        if self.beat.icon:
            self.btnIcon.setIcon(IconRegistry.from_name(self.beat.icon, self.beat.icon_color))
        elif self.beat.seq:
            self.btnIcon.setIcon(
                IconRegistry.from_name(f'mdi.numeric-{self.beat.seq}', self.beat.icon_color, scale=1.5))

        self.lblTitle.setStyleSheet(f'''
            QLabel {{
                background-color: {RELAXED_WHITE_COLOR};
            }}
            QLabel:enabled {{color: {self.beat.icon_color};}}
            QLabel:disabled {{color:grey;}}
        ''')

    # def refresh(self):
    #     self.stackedWidget.setCurrentWidget(self.pageInfo)
    #     if not self._checkOccupiedBeats:
    #         return
    #
    #     self.scene = acts_registry.scene(self.beat)
    #     if self.scene:
    #         self.lblTitle.setEnabled(True)
    #         self.btnIcon.setEnabled(True)
    #         self.stackedWidget.setCurrentWidget(self.pageScene)
    #         self.lblSceneTitle.setText(self.scene.title)
    #         self.textSynopsis.setText(self.scene.synopsis)
    #         if self.scene.pov:
    #             self.btnPov.setIcon(avatars.avatar(self.scene.pov))
    #     else:
    #         self.lblTitle.setDisabled(True)
    #         self.btnIcon.setDisabled(True)
    #         self.textSynopsis.clear()

    # @overrides
    # def event_received(self, event: Event):
    #     self._synopsisConnector.freeze()
    #     self.refresh()
    #     self._synopsisConnector.freeze(False)

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Enter:
            if self._canBeToggled():
                self.cbToggle.setVisible(True)
            # self.btnSceneSelector.setVisible(self._infoPage() and self._checkOccupiedBeats and self.beat.enabled)
            self.setStyleSheet(
                f'.BeatWidget {{background-color: {act_color(self.beat.act, self._novel.active_story_structure.acts, translucent=True)};}}')
            self.beatHighlighted.emit(self.beat)
        elif event.type() == QEvent.Type.Leave:
            self.cbToggle.setHidden(True)
            # self.btnSceneSelector.setHidden(True)
            self.setStyleSheet(f'.BeatWidget {{background-color: {RELAXED_WHITE_COLOR};}}')

        return super().eventFilter(watched, event)

    # def _infoPage(self) -> bool:
    #     return self.stackedWidget.currentWidget() == self.pageInfo
    #
    # def _scenePage(self) -> bool:
    #     return self.stackedWidget.currentWidget() == self.pageScene

    def _canBeToggled(self):
        if not self._toggleEnabled:
            return False
        if self.beat in midpoints or self.beat.ends_act:
            return False
        return True

    def _beatToggled(self, toggled: bool):
        translucent(self.textDescription, 1 if toggled else 0.5)
        self.lblTitle.setEnabled(toggled)
        self.btnIcon.setEnabled(toggled)
        self.textDescription.setEnabled(toggled)
        bold(self.lblTitle, toggled)

    def _beatClicked(self, checked: bool):
        self.beat.enabled = checked
        self.beatToggled.emit(self.beat)
    # self.btnSceneSelector.setVisible(self._infoPage() and self._checkOccupiedBeats and self.beat.enabled)

    # def _sceneLinked(self, scene: Scene):
    #     scene.link_beat(app_env.novel.active_story_structure, self.beat)
    #     self.repo.update_scene(self.scene)
    #     emit_event(self._novel, SceneChangedEvent(self, scene))
    #     self.refresh()
    #     qtanim.glow(self.lblTitle, color=QColor(self.beat.icon_color))

    # def _synopsisEdited(self):
    #     if self.scene:
    #         self.scene.synopsis = self.textSynopsis.toPlainText()
    #         self.repo.update_scene(self.scene)
    #         emit_event(self._novel, SceneChangedEvent(self, self.scene))


class BeatsPreview(QFrame):
    def __init__(self, novel: Novel, checkOccupiedBeats: bool = True, toggleBeats: bool = True, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._checkOccupiedBeats = checkOccupiedBeats
        self._toggleBeats = toggleBeats
        self._layout = flow(self, spacing=10)
        self._beats: Dict[StoryBeat, BeatWidget] = {}
        self._structurePreview: Optional[StoryStructureTimelineWidget] = None
        self._structure: Optional[StoryStructure] = None

        self.setProperty('relaxed-white-bg', True)

    def attachStructurePreview(self, structurePreview: StoryStructureTimelineWidget):
        self._structurePreview = structurePreview

    def setStructure(self, structure: StoryStructure):
        self._structure = structure
        self.refresh()

    def refresh(self):
        self._beats.clear()
        clear_layout(self._layout)
        for beat in self._structure.sorted_beats():
            if beat.type != StoryBeatType.BEAT:
                continue
            if not self._toggleBeats and not beat.enabled:
                continue
            wdg = self.__initBeatWidget(beat)
            self._layout.addWidget(wdg)

    def refreshBeat(self, beat: StoryBeat):
        wdg = self._beats[beat]
        wdg.updateInfo()
        self._structurePreview.refreshBeat(beat)

    def replaceBeat(self, oldBeat: StoryBeat, newBeat: StoryBeat):
        for i, beat in enumerate(self._structure.beats):
            if beat == oldBeat:
                self._structure.beats[i] = newBeat
                break
        oldWdg = self._beats.pop(oldBeat)
        newWdg = self.__initBeatWidget(newBeat)
        i = self._layout.indexOf(oldWdg)
        self._layout.insertWidget(i, newWdg)
        gc(oldWdg)
        self._structurePreview.replaceBeat(oldBeat, newBeat)

    def removeBeat(self, beat: StoryBeat):
        self._structure.beats.remove(beat)
        wdg = self._beats.pop(beat)
        self._layout.removeWidget(wdg)
        gc(wdg)
        self._structurePreview.removeBeat(beat)

    def insertBeat(self, newBeat: StoryBeat):
        insert_to = -1
        for i, beat in enumerate(self._structure.beats):
            if beat.percentage > newBeat.percentage:
                insert_to = i
                break
        self._structure.beats.insert(insert_to, newBeat)
        newWdg = self.__initBeatWidget(newBeat)
        self._layout.insertWidget(insert_to, newWdg)
        self._structurePreview.insertBeat(newBeat)

    def __initBeatWidget(self, beat: StoryBeat) -> BeatWidget:
        wdg = BeatWidget(self._novel, beat, self._checkOccupiedBeats, toggleEnabled=self._toggleBeats)
        self._beats[beat] = wdg
        wdg.setMinimumWidth(200)
        wdg.setMaximumWidth(300)
        wdg.beatHighlighted.connect(self._structurePreview.highlightBeat)
        wdg.beatToggled.connect(partial(self._structurePreview.toggleBeatVisibility, beat))

        return wdg
