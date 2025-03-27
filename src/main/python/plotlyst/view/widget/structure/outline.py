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
from enum import Enum, auto
from functools import partial
from typing import Optional

import qtanim
from PyQt6.QtCore import Qt, QEvent, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QEnterEvent, QResizeEvent, QDragEnterEvent
from PyQt6.QtWidgets import QWidget, QDialog, QButtonGroup
from overrides import overrides
from qthandy import line, vbox, margins, hbox, spacer, sp, incr_icon, transparent, italic, clear_layout, vspacer, \
    translucent
from qthandy.filter import OpacityEventFilter, DropEventFilter

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, MAX_NUMBER_OF_ACTS, act_color, ALT_BACKGROUND_COLOR
from plotlyst.core.domain import StoryBeat, StoryBeatType, midpoints, hook_beat, motion_beat, \
    disturbance_beat, characteristic_moment_beat, normal_world_beat, general_beat, StoryStructure, turn_beat, \
    twist_beat, inciting_incident_beat, refusal_beat, synchronicity_beat, establish_beat, trigger_beat, \
    first_pinch_point_beat, second_pinch_point_beat, crisis, climax_beat, resolution_beat, contrast_beat, \
    retrospection_beat, revelation_beat, dark_moment, plot_point, plot_point_ponr, plot_point_aha, \
    plot_point_rededication, danger_beat, copy_beat, TemplateStoryStructureType, StoryStructureDisplayType
from plotlyst.view.common import label, push_btn, wrap, tool_btn, scrolled
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.display import PopupDialog, Icon
from plotlyst.view.widget.outline import OutlineTimelineWidget, OutlineItemWidget
from plotlyst.view.widget.structure.beat import BeatsPreview
from plotlyst.view.widget.structure.timeline import StoryStructureTimelineWidget


class StoryStructureBeatWidget(OutlineItemWidget):
    StoryStructureBeatBeatMimeType: str = 'application/story-structure-beat'
    actChanged = pyqtSignal()

    def __init__(self, beat: StoryBeat, structure: StoryStructure, parent=None):
        self.beat = beat
        super().__init__(beat, parent)
        self._structure = structure
        self._allowActs = structure.custom
        self._structurePreview: Optional[StoryStructureTimelineWidget] = None
        self._text.setText(self.beat.notes)
        self._text.setMaximumSize(220, 110)
        self._initStyle(name=self.beat.text,
                        desc=self.beat.placeholder if self.beat.placeholder else self.beat.description,
                        tooltip=self.beat.description)

        if self.beat.text == 'Beat':
            translucent(self._btnName, 0.5)

        if self._allowActs:
            self._btnEndsAct = tool_btn(QIcon(),
                                        transparent_=True, checkable=True,
                                        parent=self)
            self.refreshActButton()
            self._btnEndsAct.installEventFilter(
                OpacityEventFilter(self._btnEndsAct, leaveOpacity=0.3, enterOpacity=0.7, ignoreCheckedButton=True))
            self._btnEndsAct.setChecked(self.beat.ends_act)
            self._btnEndsAct.setVisible(self._btnEndsAct.isChecked())
            self._btnEndsAct.toggled.connect(self._actEndChanged)

    def attachStructurePreview(self, structurePreview: 'StoryStructureTimelineWidget'):
        self._structurePreview = structurePreview

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        if self.beat not in midpoints and not self.beat.ends_act:
            super().enterEvent(event)
        if self._structurePreview:
            self._structurePreview.highlightBeat(self.beat)
        if self._allowActs and (self._structure.acts < self._maxNumberOfActs() or self._btnEndsAct.isChecked()):
            self.refreshActButton()
            self._btnEndsAct.setVisible(True)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        super().leaveEvent(event)
        if self._structurePreview:
            self._structurePreview.unhighlightBeats()
        if self._allowActs:
            self._btnEndsAct.setVisible(self._btnEndsAct.isChecked())

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._allowActs:
            self._btnEndsAct.setGeometry(5, self.iconFixedSize, 25, 25)

    @overrides
    def mimeType(self) -> str:
        return self.StoryStructureBeatBeatMimeType

    @overrides
    def copy(self) -> 'StoryStructureBeatWidget':
        return StoryStructureBeatWidget(self.beat, self._structure)

    def refreshActButton(self):
        self._btnEndsAct.setToolTip('Remove act' if self._btnEndsAct.isChecked() else 'Toggle new act')
        self._btnEndsAct.setIcon(IconRegistry.act_icon(max(self.beat.act, 1), self._structure, 'grey'))

        if self.beat.act_colorized:
            self._initStyle(name=self.beat.text,
                            desc=self.beat.placeholder if self.beat.placeholder else self.beat.description,
                            tooltip=self.beat.description)

    @overrides
    def _color(self) -> str:
        return self.beat.icon_color

    @overrides
    def _icon(self) -> QIcon:
        qcolor = QColor(self.beat.icon_color)
        qcolor.setAlpha(self._colorAlpha)
        if self.beat.icon:
            return IconRegistry.from_name(self.beat.icon, qcolor)
        elif self.beat.seq:
            return IconRegistry.from_name(f'mdi.numeric-{self.beat.seq}', qcolor, scale=1.5)

    @overrides
    def _textChanged(self):
        self.beat.notes = self._text.toPlainText()
        self.changed.emit()

    def _actEndChanged(self, toggled: bool):
        self.beat.ends_act = toggled
        if toggled:
            self._structure.increaseAct()
            qtanim.glow(self._btnEndsAct, color=QColor(act_color(max(self.beat.act, 1), self._structure.acts)))
            self._btnRemove.setHidden(True)
        else:
            self._structure.decreaseAct()
            self._btnRemove.setVisible(True)
        self._structure.update_acts()

        self.changed.emit()
        self.actChanged.emit()

    def _maxNumberOfActs(self) -> int:
        if self._structure.expected_acts is not None:
            return self._structure.expected_acts
        return MAX_NUMBER_OF_ACTS


class _StoryBeatSection(QWidget):
    def __init__(self, beat: StoryBeat, parent=None):
        super().__init__(parent)
        vbox(self, 0, spacing=0)

        self._label = push_btn(IconRegistry.from_name(beat.icon, beat.icon_color),
                               text=beat.text, transparent_=True,
                               tooltip=beat.description, checkable=True, icon_resize=False,
                               pointy_=False)
        self.btnAdd = push_btn(IconRegistry.plus_icon(PLOTLYST_SECONDARY_COLOR), 'Add', tooltip=f'Add {beat.text}')
        italic(self.btnAdd)
        self.btnAdd.setStyleSheet(f'border: 0px; color: {PLOTLYST_SECONDARY_COLOR};')
        self.wdgHeader = group(self._label, spacer(), self.btnAdd, margin=0)
        self.layout().addWidget(self.wdgHeader)
        self.desc = label(beat.description, description=True, wordWrap=True)
        self.layout().addWidget(wrap(self.desc, margin_left=20))

        self.setMinimumWidth(450)

        self.wdgHeader.installEventFilter(self)
        self.desc.installEventFilter(self)

    @overrides
    def eventFilter(self, watched: 'QObject', event: 'QEvent') -> bool:
        if event.type() == QEvent.Type.Enter:
            self.setStyleSheet(f'background: {ALT_BACKGROUND_COLOR};')
        elif event.type() == QEvent.Type.Leave:
            self.setStyleSheet('')
        return super().eventFilter(watched, event)


class StoryStructureElements(Enum):
    Beginning = auto()
    Catalyst = auto()
    Escalation = auto()
    Midpoint = auto()
    Plot_points = auto()
    Climax = auto()
    # Falling_action = auto()
    Ending = auto()


story_structure_element_icons = {
    StoryStructureElements.Beginning: 'mdi.ray-start',
    StoryStructureElements.Catalyst: 'fa5s.vial',
    StoryStructureElements.Escalation: 'mdi.slope-uphill',
    StoryStructureElements.Midpoint: 'mdi.middleware-outline',
    StoryStructureElements.Plot_points: 'mdi.pillar',
    StoryStructureElements.Climax: 'fa5s.chevron-up',
    # StoryStructureElements.Falling_action: 'mdi.slope-downhill',
    StoryStructureElements.Ending: 'fa5s.water',
}


class StoryBeatSelectorPopup(PopupDialog):
    LAST_ELEMENT = StoryStructureElements.Beginning

    def __init__(self, structure: StoryStructure, parent=None):
        super().__init__(parent)
        self._structure = structure
        self._beat: Optional[StoryBeat] = None

        self.wdgTitle = QWidget()
        hbox(self.wdgTitle)
        self.wdgTitle.layout().addWidget(spacer())
        icon = Icon()
        icon.setIcon(IconRegistry.story_structure_icon())
        incr_icon(icon, 4)
        self.wdgTitle.layout().addWidget(icon)
        if self._structure.template_type == TemplateStoryStructureType.TWISTS:
            title = 'Twists and turns beats'
        else:
            title = 'Common story structure beats'
        self.wdgTitle.layout().addWidget(label(title, bold=True, h4=True))
        self.wdgTitle.layout().addWidget(spacer())
        self.wdgTitle.layout().addWidget(self.btnReset)
        self.frame.layout().addWidget(self.wdgTitle)

        if self._structure.template_type != TemplateStoryStructureType.TWISTS:
            self._addBeat(general_beat, self.frame)
        self.wdgSelector = QWidget()
        hbox(self.wdgSelector)
        self.frame.layout().addWidget(self.wdgSelector)
        self.wdgSecondarySelector = QWidget()
        hbox(self.wdgSecondarySelector).addWidget(spacer())
        self.frame.layout().addWidget(self.wdgSecondarySelector)

        self.frame.layout().addWidget(line())

        self.wdgEditor = QWidget()
        vbox(self.wdgEditor, 0, 0)
        self.frame.layout().addWidget(self.wdgEditor)
        self._scrollarea, self.wdgCenter = scrolled(self.wdgEditor, frameless=True, h_on=False)
        self._scrollarea.setProperty('transparent', True)
        transparent(self.wdgCenter)
        vbox(self.wdgCenter, 10, spacing=8)
        margins(self.wdgCenter, bottom=20)

        margins(self.wdgCenter, right=20, top=15)

        self.btnClose = push_btn(text='Close', properties=['confirm', 'cancel'])
        sp(self.btnClose).h_exp()
        self.btnClose.clicked.connect(self.reject)
        self.frame.layout().addWidget(self.btnClose, alignment=Qt.AlignmentFlag.AlignRight)

        if self._structure.template_type == TemplateStoryStructureType.TWISTS:
            self._addBeat(twist_beat)
            self._addBeat(turn_beat)
            self._addBeat(danger_beat)
            self.wdgCenter.layout().addWidget(vspacer())
        else:
            self.btnGroup = QButtonGroup()
            for element in StoryStructureElements:
                if element == StoryStructureElements.Plot_points and not self._structure.custom:
                    continue
                btn = push_btn(
                    IconRegistry.from_name(story_structure_element_icons[element], 'grey',
                                           color_on=PLOTLYST_SECONDARY_COLOR),
                    text=element.name.replace('_', ' '), checkable=True,
                    properties=['secondary-selector', 'transparent-rounded-bg-on-hover'])

                if element in [StoryStructureElements.Midpoint, StoryStructureElements.Plot_points]:
                    self.wdgSecondarySelector.layout().addWidget(btn)
                else:
                    self.wdgSelector.layout().addWidget(btn)
                btn.toggled.connect(partial(self._elementsToggled, element))
                self.btnGroup.addButton(btn)
                if element == StoryBeatSelectorPopup.LAST_ELEMENT:
                    btn.setChecked(True)

            self.wdgSecondarySelector.layout().addWidget(spacer())
            if not self.btnGroup.checkedButton():
                self.btnGroup.buttons()[0].setChecked(True)

    def display(self) -> Optional[StoryBeat]:
        result = self.exec()
        if result == QDialog.DialogCode.Accepted:
            return copy_beat(self._beat)

    def _addHeader(self, name: str, icon: QIcon):
        icon_ = Icon()
        icon_.setIcon(icon)
        header = label(name, bold=True)
        self.wdgCenter.layout().addWidget(group(icon_, header), alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgCenter.layout().addWidget(line(color='lightgrey'))

    def _addBeat(self, beat: StoryBeat, parent=None):
        if parent is None:
            parent = self.wdgCenter
        wdg = _StoryBeatSection(beat)
        margins(wdg, left=15)
        parent.layout().addWidget(wdg)
        wdg.btnAdd.clicked.connect(partial(self._addClicked, beat))

    def _elementsToggled(self, element: StoryStructureElements, toggled: bool):
        if not toggled:
            return
        StoryBeatSelectorPopup.LAST_ELEMENT = element
        clear_layout(self.wdgCenter)
        if element == StoryStructureElements.Beginning:
            self._addBeat(hook_beat)
            self._addBeat(motion_beat)
            self._addBeat(disturbance_beat)
            self._addBeat(characteristic_moment_beat)
            self._addBeat(normal_world_beat)
        elif element == StoryStructureElements.Catalyst:
            self._addBeat(inciting_incident_beat)
            self._addBeat(synchronicity_beat)
            self._addBeat(refusal_beat)
            self._addHeader('2-step inciting incident', IconRegistry.inciting_incident_icon('black'))
            self._addBeat(trigger_beat)
            self._addBeat(establish_beat)
        elif element == StoryStructureElements.Escalation:
            self._addBeat(turn_beat)
            self._addBeat(twist_beat)
            self._addBeat(danger_beat)
            self._addBeat(revelation_beat)
            self._addBeat(first_pinch_point_beat)
            self._addBeat(second_pinch_point_beat)
            self._addBeat(dark_moment)
        elif element == StoryStructureElements.Midpoint:
            for midpoint in midpoints:
                self._addBeat(midpoint)
        elif element == StoryStructureElements.Plot_points:
            self._addBeat(plot_point)
            self._addBeat(plot_point_ponr)
            self._addBeat(plot_point_aha)
            self._addBeat(plot_point_rededication)
        elif element == StoryStructureElements.Climax:
            self._addBeat(climax_beat)
            self._addBeat(crisis)
        elif element == StoryStructureElements.Ending:
            self._addBeat(resolution_beat)
            self._addBeat(contrast_beat)
            self._addBeat(retrospection_beat)

        self.wdgCenter.layout().addWidget(vspacer())

    def _addClicked(self, beat: StoryBeat):
        self._beat = beat
        self.accept()


class StoryStructureOutline(OutlineTimelineWidget):
    beatChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._structureTimeline: Optional[StoryStructureTimelineWidget] = None
        self._beatsPreview: Optional[BeatsPreview] = None
        self._structure: Optional[StoryStructure] = None

    def attachStructurePreview(self, structureTimeline: StoryStructureTimelineWidget):
        self._structureTimeline = structureTimeline
        for wdg in self._beatWidgets:
            wdg.attachStructurePreview(self._structureTimeline)

    def attachBeatsPreview(self, beats: BeatsPreview):
        self._beatsPreview = beats

    @overrides
    def setStructure(self, structure: StoryStructure):
        self.clear()
        self._structure = structure
        self._items = structure.beats

        for item in self._structure.sorted_beats():
            if item.type == StoryBeatType.BEAT and item.enabled:
                self._addBeatWidget(item)
        if not self._items:
            self.layout().addWidget(self._newPlaceholderWidget(displayText=True))


    @overrides
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(StoryStructureBeatWidget.StoryStructureBeatBeatMimeType):
            event.accept()
        else:
            event.ignore()

    @overrides
    def _newBeatWidget(self, item: StoryBeat) -> StoryStructureBeatWidget:
        widget = StoryStructureBeatWidget(item, self._structure, parent=self)
        widget.attachStructurePreview(self._structureTimeline)
        widget.changed.connect(self.beatChanged)
        widget.actChanged.connect(partial(self._actChanged, widget))
        widget.removed.connect(self._beatRemovedClicked)
        widget.dragStarted.connect(partial(self._dragStarted, widget))
        widget.dragStopped.connect(self._dragFinished)

        widget.installEventFilter(DropEventFilter(widget, [StoryStructureBeatWidget.StoryStructureBeatBeatMimeType],
                                                  motionDetection=Qt.Orientation.Horizontal,
                                                  motionSlot=partial(self._dragMoved, widget),
                                                  droppedSlot=self._dropped))

        return widget

    def _beatRemovedClicked(self, wdg: StoryStructureBeatWidget):
        def teardown():
            if self._beatsPreview:
                QTimer.singleShot(150, self._beatsPreview.refresh)

        if wdg.beat.custom:
            self._structureTimeline.removeBeat(wdg.beat)
            self._beatRemoved(wdg, teardownFunction=teardown)
        else:
            wdg.beat.enabled = False
            self._structureTimeline.toggleBeatVisibility(wdg.beat)
            self._beatWidgetRemoved(wdg, teardownFunction=teardown)

        self._structure.normalize_beats()

    @overrides
    def _placeholderClicked(self, placeholder: QWidget):
        self._currentPlaceholder = placeholder
        beat: Optional[StoryBeat] = StoryBeatSelectorPopup.popup(self._structure)
        if beat:
            if beat.ends_act:
                exp = self._structure.expected_acts if self._structure.expected_acts is not None else MAX_NUMBER_OF_ACTS
                if self._structure.acts == exp:
                    beat.ends_act = False

            self._insertBeat(beat)

            if beat.ends_act:
                self._structure.increaseAct()
                self._structure.update_acts()
                self._actChanged()

    def _insertBeat(self, beat: StoryBeat):
        def teardown():
            if self._beatsPreview:
                QTimer.singleShot(150, self._beatsPreview.refresh)

        wdg = self._newBeatWidget(beat)
        self._insertWidget(beat, wdg, teardownFunction=teardown)
        self._recalculatePercentage(wdg)
        self._structureTimeline.insertBeat(beat)

    def _recalculatePercentage(self, wdg: StoryStructureBeatWidget):
        if self._structure.display_type == StoryStructureDisplayType.Proportional_timeline:
            beat = wdg.item
            i = self._beatWidgets.index(wdg)
            if i > 0:
                percentBefore = self._beatWidgets[i - 1].item.percentage
                if i < len(self._beatWidgets) - 1:
                    percentAfter = self._beatWidgets[i + 1].item.percentage
                else:
                    percentAfter = 99
                beat.percentage = percentBefore + (percentAfter - percentBefore) / 2
            else:
                beat.percentage = 1
        else:
            self._structure.normalize_beats()

        self._structure.update_acts()

    @overrides
    def _insertDroppedItem(self, wdg: OutlineItemWidget):
        super()._insertDroppedItem(wdg)
        self._recalculatePercentage(wdg)
        self._structureTimeline.setStructure(self._novel, self._structure)
        QTimer.singleShot(150, self._beatsPreview.refresh)
        self.timelineChanged.emit()

    def _actChanged(self, wdg: Optional[StoryStructureBeatWidget] = None):
        if wdg:
            self._structureTimeline.refreshBeat(wdg.beat)

        self._structureTimeline.refreshActs()
        for wdg in self._beatWidgets:
            beat: StoryBeat = wdg.item
            if beat.ends_act:
                wdg.refreshActButton()
                self._structureTimeline.refreshBeat(beat)
            elif beat.act_colorized:
                self._structureTimeline.refreshBeat(beat)

        self.timelineChanged.emit()
