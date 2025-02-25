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

import copy
from enum import Enum, auto
from functools import partial
from typing import Optional, List, Tuple, Set

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtWidgets import QWidget, QPushButton, QDialog, QScrollArea, QLabel, QButtonGroup, QStackedWidget
from overrides import overrides
from qthandy import vspacer, spacer, transparent, bold, vbox, incr_font, \
    hbox, margins, pointy, incr_icon, busy, flow, vline
from qthandy.filter import OpacityEventFilter
from qtmenu import MenuWidget

from plotlyst.common import WHITE_COLOR, RELAXED_WHITE_COLOR, PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import StoryStructure, Novel, StoryBeat, \
    three_act_structure, heros_journey, hook_beat, motion_beat, \
    disturbance_beat, normal_world_beat, characteristic_moment_beat, midpoint, midpoint_ponr, midpoint_mirror, \
    midpoint_proactive, crisis, first_plot_point, first_plot_point_ponr, first_plot_points, midpoints, story_spine, \
    twists_and_turns, twist_beat, turn_beat, danger_beat, copy_beat, midpoint_false_victory, \
    midpoint_re_dedication, second_plot_points, second_plot_point_aha, second_plot_point, midpoint_hero_ordeal, \
    midpoint_hero_mirror, second_plot_point_hero_road_back, second_plot_point_hero_ordeal, hero_reward, \
    hero_false_victory, pace_driven_structure, TemplateStoryStructureType, tension_driven_structure, \
    transformation_driven_structure
from plotlyst.view.common import ExclusiveOptionalButtonGroup, push_btn, label
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.widget.display import IconText, ReferencesButton, PopupDialog
from plotlyst.view.widget.input import Toggle
from plotlyst.view.widget.structure.beat import BeatsPreview
from plotlyst.view.widget.structure.outline import StoryStructureTimelineWidget


class _AbstractStructureEditor(QWidget):
    def __init__(self, novel: Novel, structure: StoryStructure, parent=None, newStructure: bool = True):
        super(_AbstractStructureEditor, self).__init__(parent)
        self._novel = novel
        self._structure = structure
        vbox(self)
        self.wdgTitle = IconText(self)
        self.wdgTitle.setText(structure.title)
        if structure.icon:
            self.wdgTitle.setIcon(IconRegistry.from_name(structure.icon, structure.icon_color))
        bold(self.wdgTitle)
        incr_font(self.wdgTitle, 2)
        self.wdgCustom = QWidget()

        self.wdgPreview = StoryStructureTimelineWidget(self)
        self.wdgPreview.setCheckOccupiedBeats(False)
        self.wdgPreview.setBeatsMoveable(True)
        self.wdgPreview.setActsClickable(False)
        self.wdgPreview.setActsResizeable(True)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        vbox(self._scroll)

        self.beatsPreview = BeatsPreview(novel, checkOccupiedBeats=False)
        self._scroll.setWidget(self.beatsPreview)
        self.beatsPreview.attachStructurePreview(self.wdgPreview)
        self.wdgPreview.setStructure(novel, self._structure)
        self.beatsPreview.setStructure(self._structure)
        self.layout().addWidget(self.wdgTitle)
        # self.layout().addWidget(line())
        self.layout().addWidget(self.wdgCustom)
        self.layout().addWidget(vspacer(20))
        self.layout().addWidget(self.wdgPreview)
        self.layout().addWidget(self._scroll)

        # self.wdgPreview.actsResized.connect(lambda: emit_event(NovelStoryStructureUpdated(self)))
        # self.wdgPreview.beatMoved.connect(lambda: emit_event(NovelStoryStructureUpdated(self)))

    def structure(self) -> StoryStructure:
        return self._structure


class BeatCustomization(Enum):
    pass


class _ThreeActBeginning(BeatCustomization):
    Hook = auto()
    Disturbance = auto()
    Motion = auto()
    Characteristic_moment = auto()
    Normal_world = auto()


class _ThreeActFirstPlotPoint(BeatCustomization):
    First_plot_point = auto()
    Point_of_no_return = auto()


class _ThreeActSecondPlotPoint(BeatCustomization):
    Second_plot_point = auto()
    Aha_moment = auto()


class _ThreeActMidpoint(BeatCustomization):
    Turning_point = auto()
    Point_of_no_return = auto()
    Mirror_moment = auto()
    Proactive = auto()
    False_victory = auto()
    Re_dedication = auto()


class _ThreeActEnding(BeatCustomization):
    Crisis = auto()


def beat_option_title(option: BeatCustomization) -> str:
    if option == _ThreeActMidpoint.Re_dedication:
        return 'Re-dedication'
    return option.name.replace('_', ' ')


def beat_option_description(option: BeatCustomization) -> str:
    if option == _ThreeActBeginning.Hook:
        return hook_beat.description
    elif option == _ThreeActBeginning.Motion:
        return motion_beat.description
    elif option == _ThreeActBeginning.Disturbance:
        return disturbance_beat.description
    elif option == _ThreeActBeginning.Normal_world:
        return normal_world_beat.description
    elif option == _ThreeActBeginning.Characteristic_moment:
        return characteristic_moment_beat.description

    elif option == _ThreeActFirstPlotPoint.First_plot_point:
        return first_plot_point.description
    elif option == _ThreeActFirstPlotPoint.Point_of_no_return:
        return first_plot_point_ponr.description


    elif option == _ThreeActMidpoint.Turning_point:
        return midpoint.description
    elif option == _ThreeActMidpoint.Point_of_no_return:
        return midpoint_ponr.description
    elif option == _ThreeActMidpoint.Mirror_moment:
        return midpoint_mirror.description
    elif option == _ThreeActMidpoint.Proactive:
        return midpoint_proactive.description
    elif option == _ThreeActMidpoint.False_victory:
        return midpoint_false_victory.description
    elif option == _ThreeActMidpoint.Re_dedication:
        return midpoint_re_dedication.description

    elif option == _ThreeActSecondPlotPoint.Second_plot_point:
        return second_plot_point.description
    elif option == _ThreeActSecondPlotPoint.Aha_moment:
        return second_plot_point_aha.description

    elif option == _ThreeActEnding.Crisis:
        return crisis.description


def beat_option_icon(option: BeatCustomization) -> Tuple[str, str]:
    if option == _ThreeActBeginning.Hook:
        return hook_beat.icon, hook_beat.icon_color
    elif option == _ThreeActBeginning.Motion:
        return motion_beat.icon, motion_beat.icon_color
    elif option == _ThreeActBeginning.Disturbance:
        return disturbance_beat.icon, disturbance_beat.icon_color
    elif option == _ThreeActBeginning.Normal_world:
        return normal_world_beat.icon, normal_world_beat.icon_color
    elif option == _ThreeActBeginning.Characteristic_moment:
        return characteristic_moment_beat.icon, characteristic_moment_beat.icon_color

    elif option == _ThreeActFirstPlotPoint.First_plot_point:
        return first_plot_point.icon, first_plot_point.icon_color
    elif option == _ThreeActFirstPlotPoint.Point_of_no_return:
        return first_plot_point_ponr.icon, first_plot_point_ponr.icon_color

    elif option == _ThreeActMidpoint.Turning_point:
        return midpoint.icon, midpoint.icon_color
    elif option == _ThreeActMidpoint.Point_of_no_return:
        return midpoint_ponr.icon, midpoint_ponr.icon_color
    elif option == _ThreeActMidpoint.Mirror_moment:
        return midpoint_mirror.icon, midpoint_mirror.icon_color
    elif option == _ThreeActMidpoint.Proactive:
        return midpoint_proactive.icon, midpoint_proactive.icon_color
    elif option == _ThreeActMidpoint.False_victory:
        return midpoint_false_victory.icon, midpoint_false_victory.icon_color
    elif option == _ThreeActMidpoint.Re_dedication:
        return midpoint_re_dedication.icon, midpoint_re_dedication.icon_color

    elif option == _ThreeActSecondPlotPoint.Second_plot_point:
        return second_plot_point.icon, second_plot_point.icon_color
    elif option == _ThreeActSecondPlotPoint.Aha_moment:
        return second_plot_point_aha.icon, second_plot_point_aha.icon_color

    elif option == _ThreeActEnding.Crisis:
        return crisis.icon, crisis.icon_color


def option_from_beat(beat: StoryBeat) -> Optional[BeatCustomization]:
    if beat == hook_beat:
        return _ThreeActBeginning.Hook
    elif beat == motion_beat:
        return _ThreeActBeginning.Motion
    elif beat == disturbance_beat:
        return _ThreeActBeginning.Disturbance
    elif beat == normal_world_beat:
        return _ThreeActBeginning.Normal_world
    elif beat == characteristic_moment_beat:
        return _ThreeActBeginning.Characteristic_moment

    elif beat == first_plot_point:
        return _ThreeActFirstPlotPoint.First_plot_point
    elif beat == first_plot_point_ponr:
        return _ThreeActFirstPlotPoint.Point_of_no_return

    elif beat == midpoint:
        return _ThreeActMidpoint.Turning_point
    elif beat == midpoint_ponr:
        return _ThreeActMidpoint.Point_of_no_return
    elif beat == midpoint_mirror:
        return _ThreeActMidpoint.Mirror_moment
    elif beat == midpoint_proactive:
        return _ThreeActMidpoint.Proactive
    elif beat == midpoint_false_victory:
        return _ThreeActMidpoint.False_victory
    elif beat == midpoint_re_dedication:
        return _ThreeActMidpoint.Re_dedication

    elif beat == second_plot_point:
        return _ThreeActSecondPlotPoint.Second_plot_point
    elif beat == second_plot_point_aha:
        return _ThreeActSecondPlotPoint.Aha_moment

    elif beat == crisis:
        return _ThreeActEnding.Crisis

    return None


def find_first_plot_point(structure: StoryStructure) -> Optional[StoryBeat]:
    return next((x for x in structure.beats if x in first_plot_points), None)


def find_second_plot_point(structure: StoryStructure) -> Optional[StoryBeat]:
    return next((x for x in structure.beats if x in second_plot_points), None)


def find_midpoint(structure: StoryStructure) -> Optional[StoryBeat]:
    return next((x for x in structure.beats if x in midpoints), None)


def find_beat_in(structure: StoryStructure, beats: Set[StoryBeat]) -> Optional[StoryBeat]:
    return next((x for x in structure.beats if x in beats), None)


def find_beat(structure: StoryStructure, beat: StoryBeat) -> Optional[StoryBeat]:
    return next((x for x in structure.beats if x == beat), None)


def find_crisis(structure: StoryStructure) -> Optional[StoryBeat]:
    return next((x for x in structure.beats if x == crisis), None)


class BeatOptionToggle(QWidget):
    def __init__(self, option: BeatCustomization, parent=None):
        super(BeatOptionToggle, self).__init__(parent)
        hbox(self, spacing=0)
        self.option = option
        self.toggle = Toggle()
        self.layout().addWidget(self.toggle, alignment=Qt.AlignmentFlag.AlignTop)
        desc = QLabel(beat_option_description(option))
        desc.setProperty('description', True)
        btnTitle = QPushButton(beat_option_title(option))
        btnTitle.setIcon(IconRegistry.from_name(*beat_option_icon(option)))
        pointy(btnTitle)
        transparent(btnTitle)
        btnTitle.clicked.connect(self.toggle.click)
        wdgTop = QWidget()
        vbox(wdgTop, 0)
        wdgTop.layout().addWidget(btnTitle, alignment=Qt.AlignmentFlag.AlignLeft)
        wdgTop.layout().addWidget(desc)
        self.layout().addWidget(wdgTop)
        self.layout().addWidget(spacer())


class ActOptionsButton(QPushButton):
    def __init__(self, text: str, act: int, parent=None):
        super(ActOptionsButton, self).__init__(text, parent)
        pointy(self)

        self.setProperty('structure-customization', True)
        if act == 1:
            self.setProperty('act-one', True)
        elif act == 2:
            self.setProperty('act-two', True)
        else:
            self.setProperty('act-three', True)


class StructureOptionsWidget(QWidget):
    optionSelected = pyqtSignal(BeatCustomization)
    optionsReset = pyqtSignal()

    def __init__(self, options: List[BeatCustomization], parent=None, checked: Optional[BeatCustomization] = None):
        super(StructureOptionsWidget, self).__init__(parent)
        vbox(self)
        self.btnGroup = ExclusiveOptionalButtonGroup()
        for opt in options:
            wdg = BeatOptionToggle(opt)
            self.layout().addWidget(wdg)
            self.btnGroup.addButton(wdg.toggle)
            if opt == checked:
                wdg.toggle.setChecked(True)

            wdg.toggle.clicked.connect(partial(self._clicked, opt))

    def _clicked(self, option: BeatCustomization, checked: bool):
        if not checked:
            if not self.btnGroup.checkedButton():
                self.optionsReset.emit()
            return

        self.optionSelected.emit(option)


class StructureOptionsMenu(MenuWidget):
    def __init__(self, parent: QWidget, title: str, options: List[BeatCustomization],
                 checked: Optional[BeatCustomization] = None):
        super(StructureOptionsMenu, self).__init__(parent)
        apply_white_menu(self)
        self.addSection(title)
        self.addSeparator()

        self.options = StructureOptionsWidget(options, self, checked=checked)
        self.addWidget(self.options)


class _ThreeActStructureEditor(_AbstractStructureEditor):
    def __init__(self, novel: Novel, structure: StoryStructure, parent=None, newStructure: bool = True):
        super().__init__(novel, structure, parent, newStructure)
        vbox(self.wdgCustom)
        margins(self.wdgCustom, top=10, left=10)

        self.btnBeginning = ActOptionsButton('Beginning', 1)
        self.btnBeginning.setIcon(IconRegistry.cause_icon())
        checked = option_from_beat(structure.beats[0])
        menu = StructureOptionsMenu(self.btnBeginning, 'Select the beginning',
                                    [_ThreeActBeginning.Hook, _ThreeActBeginning.Disturbance,
                                     _ThreeActBeginning.Motion, _ThreeActBeginning.Characteristic_moment,
                                     _ThreeActBeginning.Normal_world], checked=checked)
        menu.options.optionSelected.connect(self._beginningChanged)
        menu.options.optionsReset.connect(self._beginningReset)

        self.btnFirstPlotPoint = ActOptionsButton('First Plot Point', 1)
        self.btnFirstPlotPoint.setIcon(IconRegistry.from_name('mdi6.chevron-double-right'))
        fpp_beat = find_first_plot_point(self._structure)
        checked = _ThreeActFirstPlotPoint.Point_of_no_return if fpp_beat == first_plot_point_ponr else None
        menu = StructureOptionsMenu(self.btnFirstPlotPoint, 'Customize',
                                    [_ThreeActFirstPlotPoint.Point_of_no_return], checked=checked)
        menu.options.optionSelected.connect(self._firstPlotPointChanged)
        menu.options.optionsReset.connect(self._firstPlotPointReset)

        self.btnMidpoint = ActOptionsButton('Midpoint', 2)
        self.btnMidpoint.setIcon(IconRegistry.from_name('mdi.middleware-outline', '#2e86ab'))

        midpoint_beat = find_midpoint(self._structure)
        checked = option_from_beat(midpoint_beat) if midpoint_beat else None
        menu = StructureOptionsMenu(self.btnMidpoint, 'Select the midpoint',
                                    [_ThreeActMidpoint.Turning_point, _ThreeActMidpoint.Point_of_no_return,
                                     _ThreeActMidpoint.Mirror_moment, _ThreeActMidpoint.Proactive,
                                     _ThreeActMidpoint.Re_dedication,
                                     _ThreeActMidpoint.False_victory], checked=checked)
        menu.options.optionSelected.connect(self._midpointChanged)
        menu.options.optionsReset.connect(self._midpointReset)

        self.btnSecondPlotPoint = ActOptionsButton('Second Plot Point', 2)
        self.btnSecondPlotPoint.setIcon(IconRegistry.from_name('mdi6.chevron-triple-right'))
        spp_beat = find_second_plot_point(self._structure)
        checked = _ThreeActSecondPlotPoint.Aha_moment if spp_beat == second_plot_point_aha else None
        menu = StructureOptionsMenu(self.btnSecondPlotPoint, 'Customize',
                                    [_ThreeActSecondPlotPoint.Aha_moment], checked=checked)
        menu.options.optionSelected.connect(self._secondPlotPointChanged)
        menu.options.optionsReset.connect(self._secondPlotPointReset)

        crisis_beat = find_crisis(self._structure)
        checked = option_from_beat(crisis_beat) if crisis_beat else None
        self.btnEnding = ActOptionsButton('Ending', 3)
        self.btnEnding.setIcon(IconRegistry.reversed_cause_and_effect_icon())
        menu = StructureOptionsMenu(self.btnEnding, 'Extend the ending',
                                    [_ThreeActEnding.Crisis], checked=checked)
        menu.options.optionSelected.connect(self._endingChanged)
        menu.options.optionsReset.connect(self._endingReset)

        self.toggle4act = Toggle()
        self.toggle4act.setChecked(midpoint_beat.ends_act)

        lbl = push_btn(text='Split 2nd act into two parts', transparent_=True)
        lbl.clicked.connect(self.toggle4act.animateClick)

        wdgCustomization = QWidget()
        flow(wdgCustomization, spacing=10)
        margins(wdgCustomization, left=25, right=25)
        wdgCustomization.layout().addWidget(self.btnBeginning)
        wdgCustomization.layout().addWidget(self.btnFirstPlotPoint)
        wdgCustomization.layout().addWidget(self.btnMidpoint)
        wdgCustomization.layout().addWidget(self.btnSecondPlotPoint)
        wdgCustomization.layout().addWidget(self.btnEnding)

        # wdg = group(spacer(), self.btnBeginning, self.btnFirstPlotPoint, self.btnMidpoint, self.btnSecondPlotPoint,
        #             self.btnEnding, spacer(), spacing=15)
        # wdg.layout().insertWidget(1, self.lblCustomization, alignment=Qt.AlignmentFlag.AlignBottom)
        # wdg.layout().addWidget(group(lbl, self.toggle4act, spacing=0, margin=0))
        self.toggle4act.toggled.connect(self._mindpointSplit)
        self.wdgCustom.layout().addWidget(group(lbl, self.toggle4act, spacing=0, margin=0),
                                          alignment=Qt.AlignmentFlag.AlignRight)
        self.wdgCustom.layout().addWidget(wdgCustomization)

    def _beginningChanged(self, beginning: _ThreeActBeginning):
        if beginning == _ThreeActBeginning.Hook:
            beat = hook_beat
        elif beginning == _ThreeActBeginning.Motion:
            beat = motion_beat
        elif beginning == _ThreeActBeginning.Disturbance:
            beat = disturbance_beat
        elif beginning == _ThreeActBeginning.Normal_world:
            beat = normal_world_beat
        elif beginning == _ThreeActBeginning.Characteristic_moment:
            beat = characteristic_moment_beat
        else:
            return
        self.beatsPreview.replaceBeat(self._structure.beats[0], copy.deepcopy(beat))

    def _beginningReset(self):
        self.beatsPreview.replaceBeat(self._structure.beats[0], copy.deepcopy(three_act_structure.beats[0]))

    def _firstPlotPointChanged(self, option: _ThreeActFirstPlotPoint):
        if option == _ThreeActFirstPlotPoint.Point_of_no_return:
            beat = first_plot_point_ponr
        else:
            beat = first_plot_point

        current_pp = find_first_plot_point(self._structure)
        if current_pp:
            self.beatsPreview.replaceBeat(current_pp, copy.deepcopy(beat))

    def _firstPlotPointReset(self):
        current_pp = find_first_plot_point(self._structure)
        if current_pp:
            self.beatsPreview.replaceBeat(current_pp, copy.deepcopy(first_plot_point))

    def _secondPlotPointChanged(self, option: _ThreeActSecondPlotPoint):
        if option == _ThreeActSecondPlotPoint.Aha_moment:
            beat = second_plot_point_aha
        else:
            beat = second_plot_point

        current_pp = find_second_plot_point(self._structure)
        if current_pp:
            self.beatsPreview.replaceBeat(current_pp, copy.deepcopy(beat))

    def _secondPlotPointReset(self):
        current_pp = find_second_plot_point(self._structure)
        if current_pp:
            self.beatsPreview.replaceBeat(current_pp, copy.deepcopy(second_plot_point))

    def _midpointChanged(self, midpoint_option: _ThreeActMidpoint):
        if midpoint_option == _ThreeActMidpoint.Turning_point:
            beat = midpoint
        elif midpoint_option == _ThreeActMidpoint.Point_of_no_return:
            beat = midpoint_ponr
        elif midpoint_option == _ThreeActMidpoint.Mirror_moment:
            beat = midpoint_mirror
        elif midpoint_option == _ThreeActMidpoint.Proactive:
            beat = midpoint_proactive
        elif midpoint_option == _ThreeActMidpoint.False_victory:
            beat = midpoint_false_victory
        elif midpoint_option == _ThreeActMidpoint.Re_dedication:
            beat = midpoint_re_dedication
        else:
            return

        current_midpoint = find_midpoint(self._structure)
        if current_midpoint:
            self.beatsPreview.replaceBeat(current_midpoint, copy.deepcopy(beat))

    def _midpointReset(self):
        current_midpoint = find_midpoint(self._structure)
        if current_midpoint:
            self.beatsPreview.replaceBeat(current_midpoint, copy.deepcopy(midpoint))

    def _mindpointSplit(self, split: bool):
        current_midpoint = find_midpoint(self._structure)
        if current_midpoint:
            current_midpoint.ends_act = split
            if current_midpoint.ends_act:
                self._structure.acts += 1
                self._structure.acts_text[2] = 'Act 2/A'
                self._structure.acts_text[3] = 'Act 2/B'
                self._structure.acts_text[4] = 'Act 3'
                self._structure.acts_icon[3] = 'mdi.numeric-2-circle'
                self._structure.acts_icon[4] = 'mdi.numeric-3-circle'
            else:
                self._structure.acts -= 1
                self._structure.acts_text.clear()
                self._structure.acts_icon.clear()
            self._structure.update_acts()
            self.wdgPreview.refreshActs()

    def _endingChanged(self, ending_option: _ThreeActEnding):
        self.beatsPreview.insertBeat(copy.deepcopy(crisis))

    def _endingReset(self):
        self.beatsPreview.removeBeat(crisis)


class _FiveActStructureEditor(_AbstractStructureEditor):
    def __init__(self, novel: Novel, structure: StoryStructure, parent=None, newStructure: bool = True):
        super().__init__(novel, structure, parent, newStructure)


class _SaveTheCatActStructureEditor(_AbstractStructureEditor):
    def __init__(self, novel: Novel, structure: StoryStructure, parent=None, newStructure: bool = True):
        super().__init__(novel, structure, parent, newStructure)


class _CoreStructureEditor(_AbstractStructureEditor):
    def __init__(self, novel: Novel, structure: StoryStructure, parent=None, newStructure: bool = True):
        super().__init__(novel, structure, parent, newStructure)
        hbox(self.wdgCustom)
        margins(self.wdgCustom, top=20)

        self.btnPace = push_btn(IconRegistry.from_name('mdi.lightning-bolt-outline', color_on=PLOTLYST_SECONDARY_COLOR),
                                text='Pace-driven',
                                properties=['transparent-rounded-bg-on-hover', 'secondary-selector'], checkable=True)
        self.btnTension = push_btn(
            IconRegistry.from_name('fa5s.fire', color_on=PLOTLYST_SECONDARY_COLOR),
            text='Tension-driven',
            properties=['transparent-rounded-bg-on-hover', 'secondary-selector'], checkable=True)
        self.btnTransformation = push_btn(
            IconRegistry.from_name('mdi6.butterfly-outline', color_on=PLOTLYST_SECONDARY_COLOR),
            text='Transformation-driven',
            properties=['transparent-rounded-bg-on-hover', 'secondary-selector'],
            checkable=True)

        self.btnGroup = QButtonGroup()
        self.btnGroup.addButton(self.btnPace)
        self.btnGroup.addButton(self.btnTension)
        self.btnGroup.addButton(self.btnTransformation)

        self.btnGroup.buttonClicked.connect(self._typeChanged)

        self.wdgCustom.layout().addWidget(
            group(spacer(), self.btnPace, self.btnTension, self.btnTransformation, spacer()))

        self.wdgCustom.setVisible(newStructure)

        if structure.template_type == TemplateStoryStructureType.PACE:
            self.btnPace.setChecked(True)

    @busy
    def _typeChanged(self, _):
        if self.btnTension.isChecked():
            self._structure = copy.deepcopy(tension_driven_structure)
        elif self.btnPace.isChecked():
            self._structure = copy.deepcopy(pace_driven_structure)
        elif self.btnTransformation.isChecked():
            self._structure = copy.deepcopy(transformation_driven_structure)
        else:
            return

        self.wdgTitle.setText(self._structure.title)
        self.wdgTitle.setIcon(IconRegistry.from_name(self._structure.icon, self._structure.icon_color))

        self.wdgPreview.setStructure(self._novel, self._structure)
        self.beatsPreview.setStructure(self._structure)


class _HerosJourneyStructureEditor(_AbstractStructureEditor):
    def __init__(self, novel: Novel, structure: StoryStructure, parent=None, newStructure: bool = True):
        super().__init__(novel, structure, parent, newStructure)
        hbox(self.wdgCustom)
        margins(self.wdgCustom, top=20)

        ref = ReferencesButton()
        ref.addRefs([
            ('The Hero With a Thousand Faces by Joseph Campbell',
             'https://www.amazon.com/Thousand-Faces-Collected-Joseph-Campbell/dp/1577315936'),
            ("The Writer's Journey by Christopher Vogler",
             'https://www.amazon.com/Writers-Journey-Anniversary-Mythic-Structure/dp/1615933158'),
            ('Writing Archetypal Character Arcs by K.M. Weiland',
             'https://www.amazon.com/Writing-Archetypal-Character-Arcs-Journey-ebook/dp/B0BX2LBLC9'),
            ('A new character-driven Hero’s Journey written by Allen Palmer',
             'https://www.crackingyarns.com.au/2011/04/04/a-new-character-driven-heros-journey-2/')])

        wdg = group(spacer(), spacer(), ref, spacing=15)

        self.toggleOrdeal = Toggle()
        lbl = push_btn(IconRegistry.from_name('mdi6.skull'), text='Ordeal midpoint', transparent_=True,
                       tooltip='Set the ordeal beat to the midpoint')
        lbl.clicked.connect(self.toggleOrdeal.animateClick)
        wdg.layout().insertWidget(0, group(lbl, self.toggleOrdeal, spacing=0, margin=0))
        self.wdgCustom.layout().addWidget(wdg)

        if find_beat(self._structure, midpoint_hero_ordeal):
            self.toggleOrdeal.setChecked(True)

        self.toggleOrdeal.toggled.connect(self._toggleMindpointOrdeal)

    def _toggleMindpointOrdeal(self, toggled: bool):
        self.__replaceBeatIn(midpoint_hero_ordeal if toggled else midpoint_hero_mirror,
                             {midpoint_hero_ordeal, midpoint_hero_mirror})
        self.__replaceBeatIn(second_plot_point_hero_road_back if toggled else second_plot_point_hero_ordeal,
                             {second_plot_point_hero_ordeal, second_plot_point_hero_road_back})
        self.__replaceBeatIn(hero_reward if toggled else hero_false_victory,
                             {hero_reward, hero_false_victory})

    def __replaceBeatIn(self, beat: StoryBeat, match: Set[StoryBeat]):
        current = find_beat_in(self._structure, match)
        if current:
            self.beatsPreview.replaceBeat(current, copy.deepcopy(beat))


class _StorySpineStructureEditor(_AbstractStructureEditor):
    def __init__(self, novel: Novel, structure: StoryStructure, parent=None, newStructure: bool = True):
        super().__init__(novel, structure, parent, newStructure)

        vbox(self.wdgCustom, spacing=15)
        margins(self.wdgCustom, top=20)
        self.wdgCustom.layout().addWidget(label(
            "A simple narrative framework created by Kenn Adams that consists a series of connected phrases, beginning with the status quo, followed by a disrupting event, and ending with resolution.",
            description=True, wordWrap=True))


class _TwistsAndTurnsStructureEditor(_AbstractStructureEditor):
    def __init__(self, novel: Novel, structure: StoryStructure, parent=None, newStructure: bool = True):
        super().__init__(novel, structure, parent, newStructure)
        vbox(self.wdgCustom, spacing=15)
        margins(self.wdgCustom, top=20)
        self.wdgCustom.layout().addWidget(label(
            "A simplified story structure where you can track your story's biggest plot twists, turns, and danger moments.",
            description=True), alignment=Qt.AlignmentFlag.AlignCenter)

        self.wdgButtons = QWidget()
        hbox(self.wdgButtons, spacing=10)
        self.btnTwist = self.__initButton(twist_beat, 'Track twists')
        self.btnTurn = self.__initButton(turn_beat, 'Turning points')
        self.btnDanger = self.__initButton(danger_beat, 'And danger moments')
        if not structure.beats:
            self._addBeat(turn_beat, 10)
            self._addBeat(danger_beat, 33)
            self._addBeat(twist_beat, 50)

        self.wdgButtons.layout().addWidget(self.btnTwist)
        self.wdgButtons.layout().addWidget(self.btnTurn)
        self.wdgButtons.layout().addWidget(self.btnDanger)
        self.wdgCustom.layout().addWidget(self.wdgButtons, alignment=Qt.AlignmentFlag.AlignCenter)

    def _addBeat(self, beat: StoryBeat, percentage: float):
        copied_beat = copy_beat(beat)
        copied_beat.percentage = percentage
        self._structure.beats.append(copied_beat)
        self.wdgPreview.setStructure(self._novel, self._structure)
        self.beatsPreview.setStructure(self._structure)

    def __initButton(self, beat: StoryBeat, text: str) -> QPushButton:
        btn = push_btn(IconRegistry.from_name(beat.icon, beat.icon_color), text, transparent_=True, pointy_=False,
                       icon_resize=False)
        btn.installEventFilter(OpacityEventFilter(btn, leaveOpacity=0.7))
        bold(btn)
        incr_icon(btn, 6)
        incr_font(btn, 2)

        return btn


class StoryStructureSelectorDialog(PopupDialog):
    def __init__(self, novel: Novel, structure: Optional[StoryStructure] = None, parent=None):
        super(StoryStructureSelectorDialog, self).__init__(parent)
        self._novel = novel

        self.wdgCenter = QWidget()
        hbox(self.wdgCenter)

        self.wdgTypesContainer = QWidget()
        self.wdgTypesContainer.setProperty('bg', True)
        vbox(self.wdgTypesContainer, 5, 6)
        margins(self.wdgTypesContainer, top=40)

        self.wdgEditor = QWidget()
        vbox(self.wdgEditor)

        self.stackedWidget = QStackedWidget()
        self.pageThreeAct = QWidget()
        vbox(self.pageThreeAct)
        self.pageHerosJourney = QWidget()
        vbox(self.pageHerosJourney)
        self.pageStorySpine = QWidget()
        vbox(self.pageStorySpine)
        self.pageTwists = QWidget()
        vbox(self.pageTwists)
        self.pageCore = QWidget()
        vbox(self.pageCore)
        self.stackedWidget.addWidget(self.pageThreeAct)
        self.stackedWidget.addWidget(self.pageHerosJourney)
        self.stackedWidget.addWidget(self.pageStorySpine)
        self.stackedWidget.addWidget(self.pageTwists)
        self.stackedWidget.addWidget(self.pageCore)

        self.btnConfirm = push_btn(icon=IconRegistry.from_name('fa5s.check', RELAXED_WHITE_COLOR),
                                   text='Add structure',
                                   properties=['confirm', 'positive'])
        self.btnConfirm.setEnabled(False)
        self.btnConfirm.clicked.connect(self.accept)
        self.btnCancel = push_btn(text='Cancel', properties=['confirm', 'cancel'])
        self.btnCancel.clicked.connect(self.reject)

        self.btnThreeAct = push_btn(IconRegistry.from_name('mdi.numeric-3-circle-outline', color_on=WHITE_COLOR),
                                    text='3-act structure', properties=['main-side-nav'], checkable=True)
        self.btnHerosJourney = push_btn(IconRegistry.from_name('fa5s.mask', color_on=WHITE_COLOR),
                                        text='Hero archetype', properties=['main-side-nav'], checkable=True)
        self.btnStorySpine = push_btn(IconRegistry.from_name('mdi.alpha-s-circle-outline', color_on=WHITE_COLOR),
                                      text='Story spine', properties=['main-side-nav'], checkable=True)
        self.btnCore = push_btn(IconRegistry.from_name('mdi.lightning-bolt-outline', color_on=WHITE_COLOR),
                                text='Core narrative beats', properties=['main-side-nav'], checkable=True)
        # self.btnFiveAct.setIcon(IconRegistry.from_name('mdi.numeric-5-box-outline', color_on=WHITE_COLOR))
        # self.btnSaveTheCat.setIcon(IconRegistry.from_name('fa5s.cat', color_on=WHITE_COLOR))
        self.wdgTypesContainer.layout().addWidget(self.btnCore)
        self.wdgTypesContainer.layout().addWidget(self.btnThreeAct)
        self.wdgTypesContainer.layout().addWidget(self.btnHerosJourney)
        self.wdgTypesContainer.layout().addWidget(self.btnStorySpine)
        self.wdgTypesContainer.layout().addWidget(vspacer())
        self.buttonGroup = QButtonGroup()
        self.buttonGroup.addButton(self.btnThreeAct)
        self.buttonGroup.addButton(self.btnHerosJourney)
        self.buttonGroup.addButton(self.btnStorySpine)
        self.buttonGroup.addButton(self.btnCore)
        self.buttonGroup.buttonClicked.connect(self._structureChanged)

        self.lineSeparator = vline()

        self._structure: Optional[StoryStructure] = None
        self._newStructure = True
        if structure:
            self._newStructure = False
            self.btnConfirm.setHidden(True)
            self.btnCancel.setText('Close')
            self.wdgTypesContainer.setHidden(True)
            self.lineSeparator.setHidden(True)
            page, clazz = self._pageAndClass(structure)
            self.__initEditor(structure, page, clazz, copyStructure=False)
        else:
            self.btnCore.setChecked(True)
            self._structureChanged()

        self.wdgCenter.layout().addWidget(self.wdgTypesContainer)
        self.wdgCenter.layout().addWidget(self.lineSeparator)
        self.wdgCenter.layout().addWidget(self.wdgEditor)

        self.wdgEditor.layout().addWidget(self.stackedWidget)
        self.wdgEditor.layout().addWidget(group(self.btnCancel, self.btnConfirm, margin_top=20),
                                          alignment=Qt.AlignmentFlag.AlignRight)

        self.frame.layout().addWidget(self.wdgCenter)

        self.setMinimumSize(self._adjustedSize(0.95, 0.8, 800, 600))

    @overrides
    def sizeHint(self) -> QSize:
        return self._adjustedSize(0.95, 0.8, 800, 600)

    def structure(self) -> StoryStructure:
        if self.btnCore.isChecked():
            self._structure = self.pageCore.layout().itemAt(0).widget().structure()
        return self._structure

    def display(self) -> Optional[StoryStructure]:
        result = self.exec()
        if result == QDialog.DialogCode.Accepted:
            return self.structure()

    def _structureChanged(self):
        if self.btnThreeAct.isChecked():
            self.__initEditor(three_act_structure, self.pageThreeAct, _ThreeActStructureEditor)
        elif self.btnCore.isChecked():
            self.__initEditor(pace_driven_structure, self.pageCore, _CoreStructureEditor)
        elif self.btnHerosJourney.isChecked():
            self.__initEditor(heros_journey, self.pageHerosJourney, _HerosJourneyStructureEditor)
        elif self.btnStorySpine.isChecked():
            self.__initEditor(story_spine, self.pageStorySpine, _StorySpineStructureEditor)
        else:
            return

        self.btnConfirm.setEnabled(True)

    def __initEditor(self, structure: StoryStructure, page: QWidget, clazz, copyStructure: bool = True):
        self.stackedWidget.setCurrentWidget(page)
        if page.layout().count() == 0:
            if copyStructure:
                self._structure = copy.deepcopy(structure)
            else:
                self._structure = structure
            QTimer.singleShot(150, lambda: self.__initNewWidget(clazz, page))
        else:
            self._structure = page.layout().itemAt(0).widget().structure()

    @busy
    def __initNewWidget(self, clazz, page: QWidget):
        page.setEnabled(False)
        page.layout().addWidget(clazz(self._novel, self._structure, self, self._newStructure))
        page.setEnabled(True)

    def _pageAndClass(self, structure: StoryStructure):
        if structure.title == three_act_structure.title:
            return self.pageThreeAct, _ThreeActStructureEditor
        elif structure.title == heros_journey.title:
            return self.pageHerosJourney, _HerosJourneyStructureEditor
        elif structure.title == story_spine.title:
            return self.pageStorySpine, _StorySpineStructureEditor
        elif structure.title == twists_and_turns.title:
            return self.pageTwists, _TwistsAndTurnsStructureEditor
        elif structure.template_type in [TemplateStoryStructureType.PACE, TemplateStoryStructureType.TENSION,
                                         TemplateStoryStructureType.TRANSFORMATION]:
            return self.pageCore, _CoreStructureEditor
