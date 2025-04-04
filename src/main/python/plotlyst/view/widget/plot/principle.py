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
from typing import List, Optional, Dict

from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QObject
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import QWidget
from overrides import overrides
from qthandy import bold, margins, italic, vbox, transparent, \
    hbox, spacer, sp, pointy, line, underline
from qthandy.filter import OpacityEventFilter
from qtmenu import MenuWidget, ActionTooltipDisplayMode

from plotlyst.common import RELAXED_WHITE_COLOR, CONFLICT_SELF_COLOR
from plotlyst.core.domain import Plot, PlotType, PlotPrinciple, \
    PlotPrincipleType, PlotEventType, DynamicPlotPrincipleGroupType
from plotlyst.core.template import antagonist_role
from plotlyst.view.common import shadow, label, tool_btn, push_btn, scrolled, action, wrap
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.widget.display import Icon, PopupDialog
from plotlyst.view.widget.input import Toggle, TextEditBubbleWidget


def principle_icon(type: PlotPrincipleType, color_on=None) -> QIcon:
    if type == PlotPrincipleType.GOAL:
        return IconRegistry.goal_icon('grey', color_on or 'darkBlue')
    elif type == PlotPrincipleType.ANTAGONIST:
        return IconRegistry.from_name(antagonist_role.icon, 'grey', color_on or antagonist_role.icon_color)
    elif type == PlotPrincipleType.CONFLICT:
        return IconRegistry.conflict_icon('grey', color_on or '#f3a712')
    elif type == PlotPrincipleType.STAKES:
        return IconRegistry.from_name('mdi.sack', 'grey', color_on or '#e9c46a')
    elif type == PlotPrincipleType.QUESTION:
        return IconRegistry.from_name('ei.question-sign', 'grey', color_on or 'darkBlue')
    elif type == PlotPrincipleType.THEME:
        return IconRegistry.theme_icon('grey', color_on or '#9d4edd')

    elif type == PlotPrincipleType.POSITIVE_CHANGE:
        return IconRegistry.from_name('mdi.emoticon-happy', 'grey', color_on or '#588157')
    elif type == PlotPrincipleType.NEGATIVE_CHANGE:
        return IconRegistry.from_name('mdi6.emoticon-devil', 'grey', color_on or '#c1121f')
    elif type == PlotPrincipleType.DESIRE:
        return IconRegistry.from_name('ei.star-alt', 'grey', color_on or '#e9c46a')
    elif type == PlotPrincipleType.NEED:
        return IconRegistry.from_name('mdi.key', 'grey', color_on or '#cbc0d3')
    elif type == PlotPrincipleType.EXTERNAL_CONFLICT:
        return IconRegistry.conflict_icon('grey', color_on or '#f3a712')
    elif type == PlotPrincipleType.INTERNAL_CONFLICT:
        return IconRegistry.conflict_self_icon('grey', color_on or CONFLICT_SELF_COLOR)
    elif type == PlotPrincipleType.FLAW:
        return IconRegistry.from_name('mdi.virus', 'grey', color_on or '#b5179e')

    elif type == PlotPrincipleType.LINEAR_PROGRESSION:
        return IconRegistry.from_name('mdi.middleware', 'grey', color_on or 'black')
    elif type == PlotPrincipleType.DYNAMIC_ELEMENTS:
        return IconRegistry.from_name('mdi6.chart-timeline-variant-shimmer', 'grey', color_on or 'black')

    elif type == PlotPrincipleType.SKILL_SET:
        return IconRegistry.from_name('fa5s.tools', 'grey', color_on or 'black')
    elif type == PlotPrincipleType.TICKING_CLOCK:
        return IconRegistry.ticking_clock_icon('grey')
    elif type == PlotPrincipleType.WAR:
        return IconRegistry.from_name('mdi.skull', 'grey', color_on or 'black')
    elif type == PlotPrincipleType.WAR_MENTAL_EFFECT:
        return IconRegistry.from_name('mdi6.head-flash-outline', 'grey', color_on or 'black')
    elif type == PlotPrincipleType.MONSTER:
        return IconRegistry.from_name('ri.ghost-2-fill', 'grey', color_on or antagonist_role.icon_color)
    elif type == PlotPrincipleType.CONFINED_SPACE:
        return IconRegistry.from_name('fa5s.house-user', 'grey', color_on or '#ffb703')
    elif type == PlotPrincipleType.CRIME:
        return IconRegistry.from_name('ri.knife-blood-fill', 'grey', color_on or 'black')
    elif type == PlotPrincipleType.SLEUTH:
        return IconRegistry.from_name('mdi.incognito', 'grey', color_on or 'black')
    elif type == PlotPrincipleType.AUTHORITY:
        return IconRegistry.from_name('mdi.incognito', 'grey', color_on or antagonist_role.icon_color)
    elif type == PlotPrincipleType.MACGUFFIN:
        return IconRegistry.from_name('fa5s.parachute-box', 'grey', color_on or '#0077b6')
    elif type == PlotPrincipleType.CRIME_CLOCK:
        return IconRegistry.ticking_clock_icon('grey')
    elif type == PlotPrincipleType.SCHEME:
        return IconRegistry.from_name('mdi.floor-plan', 'grey', color_on or 'black')
    elif type == PlotPrincipleType.SELF_DISCOVERY:
        return IconRegistry.from_name('mdi.fingerprint', 'grey', color_on or '#cdb4db')
    elif type == PlotPrincipleType.LOSS_OF_INNOCENCE:
        return IconRegistry.from_name('fa5s.dove', 'grey', color_on or '#a2d2ff')
    elif type == PlotPrincipleType.MATURITY:
        return IconRegistry.from_name('ri.seedling-fill', 'grey', color_on or '#2a9d8f')
    elif type == PlotPrincipleType.FIRST_LOVE:
        return IconRegistry.from_name('fa5s.heart', 'grey', color_on or '#e76f51')
    elif type == PlotPrincipleType.MENTOR:
        return IconRegistry.from_name('mdi.compass-rose', 'grey', color_on or '#80ced7')

    else:
        return QIcon()


_principle_hints = {
    PlotPrincipleType.GOAL: "Is there a main goal that drives this plot?",
    PlotPrincipleType.ANTAGONIST: "Is there an antagonistic force (human or otherwise) that confronts the plot?",
    PlotPrincipleType.CONFLICT: "Is there conflict that hinders the character's goal?",
    PlotPrincipleType.STAKES: "Is there anything at stake if the storyline is not resolved?",
    PlotPrincipleType.QUESTION: "Is there a leading question associated to this storyline that is answered in the end?",

    PlotPrincipleType.POSITIVE_CHANGE: "Does the character change positively?",
    PlotPrincipleType.NEGATIVE_CHANGE: "Does the character change negatively?",
    PlotPrincipleType.DESIRE: "Is there an - often wrong - desire that drives the character's decisions?",
    PlotPrincipleType.NEED: "Is there a need that the character does not pursuit yet could solve their problems?",
    PlotPrincipleType.EXTERNAL_CONFLICT: "Are there external obstacles that force the character to change?",
    PlotPrincipleType.INTERNAL_CONFLICT: "Does the character face an internal dilemma?",
    PlotPrincipleType.FLAW: "Is there a major flaw, misbelief, or imperfection the character has to overcome?",

    PlotPrincipleType.THEME: "Is there thematic relevance associated to this storyline?",
    PlotPrincipleType.LINEAR_PROGRESSION: "Track linear progression in this storyline",
    PlotPrincipleType.DYNAMIC_ELEMENTS: "Track evolving and unpredictable elements that add complexity and engagement to the storyline",

    PlotPrincipleType.SKILL_SET: "Does the character possess unique skills and abilities to resolve the storyline?",
    PlotPrincipleType.TICKING_CLOCK: "Is there deadline in which the character must take actions?",
    PlotPrincipleType.WAR: "Is there a central war in the storyline?",
    PlotPrincipleType.WAR_MENTAL_EFFECT: "Is the war's psychological impact on the characters explored?",
    PlotPrincipleType.MONSTER: "Is there a monster that pursues a victim?",
    PlotPrincipleType.CONFINED_SPACE: "Does the story unfold in a confined or isolated space to increase tension?",

    PlotPrincipleType.CRIME: "Does the story revolve around a crime?",
    PlotPrincipleType.SLEUTH: "Is there a detective figure who wants to solve the crime?",
    PlotPrincipleType.AUTHORITY: "Is there an authority figure who chases the criminal protagonist?",
    PlotPrincipleType.CRIME_CLOCK: "Is there a deadline to solve the crime?",
    PlotPrincipleType.MACGUFFIN: "Is there an object or desire the characters pursue?",
    PlotPrincipleType.SCHEME: "Is there a well-organized scheme to carry out a crime?",

    PlotPrincipleType.SELF_DISCOVERY: "Will the character understand themselves, their identity or their place better in the world?",
    PlotPrincipleType.LOSS_OF_INNOCENCE: "Does the character forgo a loss of innocence and experience the realities of life?",
    PlotPrincipleType.MATURITY: "Does the character go through personal growth and maturity?",
    PlotPrincipleType.FIRST_LOVE: "Is there a first love the character experiences?",
    PlotPrincipleType.MENTOR: "Is there a mentor figure who guides the character?",
}


def principle_hint(principle_type: PlotPrincipleType, plot_type: Optional[PlotType] = None) -> str:
    if plot_type and plot_type == PlotType.Relation:
        if principle_type == PlotPrincipleType.GOAL:
            return "Is there a shared goal the characters aim for in this relationship plot?"
        if principle_type == PlotPrincipleType.CONFLICT:
            return "Is there any conflict that challenges the relationship?"
        if principle_type == PlotPrincipleType.STAKES:
            return "Is there anything at stake if the characters don't maintain or evolve their relation?"

    return _principle_hints[principle_type]


_principle_placeholders = {
    PlotPrincipleType.GOAL: "What's the main goal that drives this plot?",
    PlotPrincipleType.ANTAGONIST: "Who or what stands in opposition to resolve the storyline?",
    PlotPrincipleType.CONFLICT: "How does conflict hinder the goal?",
    PlotPrincipleType.STAKES: "What's at stake if the storyline is not resolved?",
    PlotPrincipleType.QUESTION: "What is the leading question in this storyline?",
    PlotPrincipleType.THEME: "How does the storyline express the theme?",

    PlotPrincipleType.POSITIVE_CHANGE: "How does the character change positively?",
    PlotPrincipleType.NEGATIVE_CHANGE: "How does the character change negatively?",
    PlotPrincipleType.DESIRE: "What does the character want?",
    PlotPrincipleType.NEED: "What does the character actually need?",
    PlotPrincipleType.EXTERNAL_CONFLICT: "What external obstacles force the character to change?",
    PlotPrincipleType.INTERNAL_CONFLICT: "What internal dilemma of conflict the character has to face?",
    PlotPrincipleType.FLAW: "What kind of flaw the character has to overcome?",

    PlotPrincipleType.SKILL_SET: "What unique skills or abilities the character possess?",
    PlotPrincipleType.TICKING_CLOCK: "What is the deadline in which the character must act?",
    PlotPrincipleType.WAR: "What's the central war in this storyline?",
    PlotPrincipleType.WAR_MENTAL_EFFECT: "How is the war's psychological impact on the characters explored?",

    PlotPrincipleType.MONSTER: "What is the monster that pursues the victim?",
    PlotPrincipleType.CONFINED_SPACE: "What enclosed or confined space is present to increase tension?",

    PlotPrincipleType.CRIME: "What's the central crime the story revolves around?",
    PlotPrincipleType.SLEUTH: "Who is the detective character who wants to solve the crime",
    PlotPrincipleType.AUTHORITY: "Who is authority figure who chases the criminal protagonist?",
    PlotPrincipleType.CRIME_CLOCK: "What is the deadline of solving the crime?",
    PlotPrincipleType.MACGUFFIN: "What object or desire do the characters pursue?",
    PlotPrincipleType.SCHEME: "Is there a well-organized scheme to carry out a crime?",

    PlotPrincipleType.SELF_DISCOVERY: "How will the character grow and understand themselves  or their identity better",
    PlotPrincipleType.LOSS_OF_INNOCENCE: "How does the character experience a loss of innocence and the realities of life?",
    PlotPrincipleType.MATURITY: "How does the character go through personal growth and maturity?",
    PlotPrincipleType.FIRST_LOVE: "How does the first love contributes to the character's growth?",
    PlotPrincipleType.MENTOR: "Who and how guides the character?",
}


def principle_placeholder(principle_type: PlotPrincipleType, plot_type: PlotType) -> str:
    if plot_type == PlotType.Relation:
        if principle_type == PlotPrincipleType.GOAL:
            return "What is a shared goal the characters aim for?"
        if principle_type == PlotPrincipleType.CONFLICT:
            return "How does conflict challenge the relationship?"
        if principle_type == PlotPrincipleType.STAKES:
            return "What's at stake if the characters don't maintain or evolve their relation?"
    return _principle_placeholders[principle_type]


principle_type_index: Dict[PlotPrincipleType, int] = {
    PlotPrincipleType.QUESTION: 0,
    PlotPrincipleType.GOAL: 1,
    PlotPrincipleType.ANTAGONIST: 2,
    PlotPrincipleType.CONFLICT: 3
}


def plot_event_icon(type: PlotEventType) -> QIcon:
    if type == PlotEventType.PROGRESS:
        return IconRegistry.charge_icon(1)
    elif type == PlotEventType.SETBACK:
        return IconRegistry.charge_icon(-1)
    elif type == PlotEventType.CRISIS:
        return IconRegistry.crisis_icon()
    elif type == PlotEventType.COST:
        return IconRegistry.cost_icon()
    elif type == PlotEventType.TOOL:
        return IconRegistry.tool_icon()


plot_event_type_hint = {
    PlotEventType.PROGRESS: 'How does the plot progress and get closer to resolution?',
    PlotEventType.SETBACK: 'How does the plot face conflict and get further from resolution?',
    PlotEventType.CRISIS: "The lowest moment. Often an impossible choice between two equally good or bad outcomes.",
    PlotEventType.COST: 'What does the character need to sacrifice to progress further with the plot?',
    PlotEventType.TOOL: 'What kind of tool does the character acquire which helps them resolve the plot?',
}


class _PlotPrincipleToggle(QWidget):
    def __init__(self, principleType: PlotPrincipleType, plotType: Optional[PlotType] = None, parent=None):
        super().__init__(parent)
        vbox(self, 0, spacing=0)
        self._principleType = principleType

        hint = principle_hint(self._principleType, plotType)
        self._label = push_btn(principle_icon(self._principleType),
                               text=self._principleType.display_name(), transparent_=True,
                               tooltip=hint, checkable=True, icon_resize=False,
                               pointy_=False)
        bold(self._label)

        self.toggle = Toggle(self)
        self.layout().addWidget(group(self._label, spacer(), self.toggle, margin=0))
        desc = label(hint, description=True)
        self.layout().addWidget(wrap(desc, margin_left=20))

        self.toggle.toggled.connect(self._label.setChecked)


internal_principles = {PlotPrincipleType.POSITIVE_CHANGE, PlotPrincipleType.NEGATIVE_CHANGE,
                       PlotPrincipleType.DESIRE, PlotPrincipleType.NEED, PlotPrincipleType.EXTERNAL_CONFLICT,
                       PlotPrincipleType.INTERNAL_CONFLICT, PlotPrincipleType.FLAW}


class PrincipleSelectorObject(QObject):
    principleToggled = pyqtSignal(PlotPrincipleType, bool)
    editorToggled = pyqtSignal(DynamicPlotPrincipleGroupType, bool)


class GenrePrincipleSelectorDialog(PopupDialog):

    def __init__(self, plot: Plot, selector: PrincipleSelectorObject, parent=None):
        super().__init__(parent)
        self.selectorObject = selector
        self.wdgTitle = QWidget()
        self._active_types = set([x.type for x in plot.principles])
        hbox(self.wdgTitle)
        self.wdgTitle.layout().addWidget(spacer())
        self.wdgTitle.layout().addWidget(
            tool_btn(IconRegistry.genre_icon(), icon_resize=False, pointy_=False, transparent_=True))
        self.wdgTitle.layout().addWidget(label('Genre specific principles', bold=True, h4=True))
        self.wdgTitle.layout().addWidget(spacer())
        self.wdgTitle.layout().addWidget(self.btnReset)
        self._scrollarea, self._wdgCenter = scrolled(self.frame, frameless=True, h_on=False)
        self._scrollarea.setProperty('transparent', True)
        transparent(self._wdgCenter)
        vbox(self._wdgCenter)
        self._wdgCenter.layout().addWidget(self.wdgTitle)
        margins(self._wdgCenter, right=20)

        self._addHeader('Action', 'fa5s.running')
        self._addPrinciple(PlotPrincipleType.SKILL_SET)
        self._addPrinciple(PlotPrincipleType.TICKING_CLOCK)
        self._addHeader('War', 'ri.sword-fill')
        self._addPrinciple(PlotPrincipleType.WAR)
        self._addPrinciple(PlotPrincipleType.WAR_MENTAL_EFFECT)
        self._addHeader('Horror', 'ri.knife-blood-fill')
        self._addPrinciple(PlotPrincipleType.MONSTER)
        self._addPrinciple(PlotPrincipleType.CONFINED_SPACE)

        self._crimeHeaderIcon = Icon()
        self._btnCrimeToggle = Toggle()
        pointy(self._btnCrimeToggle)
        self._wdgCenter.layout().addWidget(group(self._crimeHeaderIcon, label('Crime', bold=True),
                                                 label('(criminal protagonist'), self._btnCrimeToggle, label(')')),
                                           alignment=Qt.AlignmentFlag.AlignLeft)
        self._wdgCenter.layout().addWidget(line(color='lightgrey'))
        self._addPrinciple(PlotPrincipleType.CRIME)
        self._crimeClockPrinciple = self._addPrinciple(PlotPrincipleType.CRIME_CLOCK)
        self._crimeSleuthPrinciple = self._addPrinciple(PlotPrincipleType.SLEUTH)
        self._crimeMacGuffinPrinciple = self._addPrinciple(PlotPrincipleType.MACGUFFIN)
        self._crimeAuthorityPrinciple = self._addPrinciple(PlotPrincipleType.AUTHORITY)
        self._criminalToggled(self._btnCrimeToggle.isChecked())
        self._btnCrimeToggle.toggled.connect(self._criminalToggled)

        self._addHeader('Caper', 'mdi.robber')
        self._addPrinciple(PlotPrincipleType.SCHEME)

        self._addHeader('Coming of age', 'ri.seedling-line')
        self._addPrinciple(PlotPrincipleType.SELF_DISCOVERY)
        self._addPrinciple(PlotPrincipleType.LOSS_OF_INNOCENCE)
        self._addPrinciple(PlotPrincipleType.MATURITY)
        self._addPrinciple(PlotPrincipleType.FIRST_LOVE)
        self._addPrinciple(PlotPrincipleType.MENTOR)

        self.btnClose = push_btn(text='Close', properties=['confirm', 'cancel'])
        sp(self.btnClose).h_exp()
        self.btnClose.clicked.connect(self.reject)

        self.frame.layout().addWidget(self.btnClose, alignment=Qt.AlignmentFlag.AlignRight)

    def display(self):
        self.exec()

    def _addHeader(self, name: str, icon_name: str):
        icon = Icon()
        icon.setIcon(IconRegistry.from_name(icon_name))
        header = label(name, bold=True)
        self._wdgCenter.layout().addWidget(group(icon, header), alignment=Qt.AlignmentFlag.AlignLeft)
        self._wdgCenter.layout().addWidget(line(color='lightgrey'))

    def _criminalToggled(self, toggled: bool):
        self._crimeClockPrinciple.setVisible(not toggled)
        self._crimeSleuthPrinciple.setVisible(not toggled)
        self._crimeAuthorityPrinciple.setVisible(toggled)
        if toggled:
            self._crimeHeaderIcon.setIcon(IconRegistry.from_name('fa5s.mask'))
        else:
            self._crimeHeaderIcon.setIcon(IconRegistry.from_name('mdi.handcuffs'))

    def _addPrinciple(self, principle: PlotPrincipleType) -> _PlotPrincipleToggle:
        wdg = _PlotPrincipleToggle(principle)
        margins(wdg, left=15)
        if principle in self._active_types:
            wdg.toggle.setChecked(True)
        wdg.toggle.toggled.connect(partial(self.selectorObject.principleToggled.emit, principle))
        self._wdgCenter.layout().addWidget(wdg)

        return wdg


class PlotPrinciplesWidget(QWidget):
    principleToggled = pyqtSignal(PlotPrincipleType, bool)

    def __init__(self, plotType: PlotType, principles: List[PlotPrinciple], parent=None):
        super().__init__(parent)
        self.plotType = plotType

        vbox(self, spacing=0)

        active_types = set([x.type for x in principles])
        if self.plotType == PlotType.Internal:
            principles = internal_principles
        elif self.plotType == PlotType.Relation:
            principles = [PlotPrincipleType.QUESTION, PlotPrincipleType.GOAL, PlotPrincipleType.CONFLICT,
                          PlotPrincipleType.STAKES]
        else:
            principles = [PlotPrincipleType.QUESTION, PlotPrincipleType.GOAL, PlotPrincipleType.ANTAGONIST,
                          PlotPrincipleType.CONFLICT,
                          PlotPrincipleType.STAKES]

        for principle in principles:
            wdg = _PlotPrincipleToggle(principle, self.plotType)
            if principle in active_types:
                wdg.toggle.setChecked(True)
            wdg.toggle.toggled.connect(partial(self.principleToggled.emit, principle))
            self.layout().addWidget(wdg)


class PlotPrincipleSelectorMenu(MenuWidget):
    principleToggled = pyqtSignal(PlotPrincipleType, bool)
    progressionToggled = pyqtSignal(bool)
    dynamicPrinciplesToggled = pyqtSignal(bool)
    genresSelected = pyqtSignal()

    def __init__(self, plot: Plot, parent=None):
        super(PlotPrincipleSelectorMenu, self).__init__(parent)
        self._plot = plot
        apply_white_menu(self)

        self._selectors = PlotPrinciplesWidget(self._plot.plot_type, self._plot.principles)
        margins(self._selectors, left=15)
        self._selectors.principleToggled.connect(self.principleToggled)

        self.btnGenres = push_btn(IconRegistry.genre_icon(color=RELAXED_WHITE_COLOR), 'Browse genre principles',
                                  properties=['base', 'positive'])
        self.btnGenres.installEventFilter(OpacityEventFilter(self.btnGenres, 0.8, 0.6))
        underline(self.btnGenres)
        italic(self.btnGenres)
        self.btnGenres.clicked.connect(self._genresClicked)
        self.addWidget(group(spacer(), self.btnGenres))

        self.addSection('Select principles that are relevant to this storyline')
        self.addSeparator()
        self.addWidget(self._selectors)
        if self._plot.plot_type in [PlotType.Main, PlotType.Subplot]:
            menu = MenuWidget(self)
            apply_white_menu(menu)
            menu.setTitle('Combine with character development')
            menu.setIcon(IconRegistry.conflict_self_icon())
            char_arc_selectors = PlotPrinciplesWidget(PlotType.Internal, self._plot.principles)
            char_arc_selectors.principleToggled.connect(self.principleToggled)
            menu.addSection('Extend with principles that are relevant to character development')
            menu.addSeparator()
            menu.addWidget(char_arc_selectors)
            self.addSeparator()
            self.addMenu(menu)

        self.addSection('Narrative dynamics')
        self.addSeparator()
        wdg = _PlotPrincipleToggle(PlotPrincipleType.DYNAMIC_ELEMENTS, self._plot.plot_type)
        wdg.toggle.setChecked(self._plot.has_dynamic_principles)
        wdg.toggle.toggled.connect(self.dynamicPrinciplesToggled)
        margins(wdg, left=15)
        self.addWidget(wdg)

        # wdg = _PlotPrincipleToggle(PlotPrincipleType.THEME, self._plot.plot_type)
        # margins(wdg, left=15)
        # wdg.setDisabled(True)
        # self.addWidget(wdg)

        wdg = _PlotPrincipleToggle(PlotPrincipleType.LINEAR_PROGRESSION, self._plot.plot_type)
        wdg.toggle.setChecked(self._plot.has_progression)
        wdg.toggle.toggled.connect(self.progressionToggled)
        margins(wdg, left=15)
        self.addWidget(wdg)

    def _genresClicked(self):
        def trigger():
            self.hide()
            self.genresSelected.emit()

        QTimer.singleShot(50, trigger)


class PlotDynamicPrincipleSelectorMenu(MenuWidget):
    triggered = pyqtSignal(DynamicPlotPrincipleGroupType)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTooltipDisplayMode(ActionTooltipDisplayMode.DISPLAY_UNDER)
        apply_white_menu(self)
        self._addGroup(DynamicPlotPrincipleGroupType.ESCALATION)
        self._addGroup(DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES)
        # self.addSection('Fantasy', IconRegistry.from_name('msc.wand'))
        # self.addSeparator()
        # self._addGroup(DynamicPlotPrincipleGroupType.ELEMENTS_OF_WONDER)

        self.addSection('Mystery', IconRegistry.from_name('fa5s.puzzle-piece'))
        self.addSeparator()
        self._addGroup(DynamicPlotPrincipleGroupType.SUSPECTS)

        self.addSection('Horror', IconRegistry.from_name('ri.knife-blood-fill'))
        self.addSeparator()
        self._addGroup(DynamicPlotPrincipleGroupType.EVOLUTION_OF_THE_MONSTER)

        self.addSection('Caper', IconRegistry.from_name('mdi.robber'))
        self.addSeparator()
        self._addGroup(DynamicPlotPrincipleGroupType.CAST)

    def _addGroup(self, group: DynamicPlotPrincipleGroupType):
        self.addAction(action(group.display_name(), tooltip=group.description(),
                              icon=IconRegistry.from_name(group.icon(), group.color()),
                              slot=partial(self.triggered.emit, group)))


class PlotPrincipleEditor(TextEditBubbleWidget):
    principleEdited = pyqtSignal()

    def __init__(self, principle: PlotPrinciple, plotType: PlotType, parent=None):
        super().__init__(parent)
        self._principle = principle

        self._title.setText(principle.type.display_name())
        self._title.setIcon(principle_icon(principle.type))
        self._title.setCheckable(True)
        self._title.setChecked(True)

        hint = principle_placeholder(principle.type, plotType)
        self._textedit.setPlaceholderText(hint)
        self._textedit.setToolTip(hint)
        self._textedit.setText(principle.value)
        if plotType != PlotType.Internal and principle.type in internal_principles:
            shadow(self._textedit, color=QColor(CONFLICT_SELF_COLOR))
        else:
            shadow(self._textedit)

    def activate(self):
        self._textedit.setFocus()

    def principle(self) -> PlotPrinciple:
        return self._principle

    @overrides
    def _textChanged(self):
        self._principle.value = self._textedit.toPlainText()
        self.principleEdited.emit()
