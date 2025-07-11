"""
Plotlyst
Copyright (C) 2021-2025  Zsolt Kovari

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
from typing import List

from overrides import overrides

from plotlyst.core.domain import BackstoryEvent, Plot
from plotlyst.core.template import antagonist_role
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.timeline import TimelineLinearWidget, BackstoryCard, TimelineTheme


class StorylineTimelineCard(BackstoryCard):
    def __init__(self, backstory: BackstoryEvent, theme: TimelineTheme, parent=None):
        super().__init__(backstory, theme, parent=parent)
        self.refresh()

        self.setMinimumWidth(250)


class StorylineTimelineWidget(TimelineLinearWidget):
    def __init__(self, plot: Plot, parent=None):
        theme = TimelineTheme('grey', timeline_opacity=0.6, card_bg_color='#F6EAE1')
        super().__init__(theme, parent)
        self._plot = plot

        self.setAddButtonEnabled()

    @overrides
    def events(self) -> List[BackstoryEvent]:
        return self._plot.timeline

    @overrides
    def cardClass(self):
        return StorylineTimelineCard


class StorylineVillainCard(BackstoryCard):
    def __init__(self, backstory: BackstoryEvent, theme: TimelineTheme, parent=None):
        super().__init__(backstory, theme, parent=parent, iconPicker=False)
        self.refresh()

        self.btnType.setIcon(IconRegistry.from_name('ri.ghost-2-fill', antagonist_role.icon_color))
        self.lineKeyPhrase.setReadOnly(True)
        self.lineKeyPhrase.setText('Evolution')
        self.textSummary.setPlaceholderText("How the monster's power evolves")
        self.setMinimumWidth(400)

    @overrides
    def _frameColor(self):
        return antagonist_role.icon_color


class StorylineVillainEvolutionWidget(TimelineLinearWidget):
    def __init__(self, plot: Plot, parent=None):
        theme = TimelineTheme(antagonist_role.icon_color, card_bg_color='#F6EAE1')
        super().__init__(theme, parent, centerOnly=True)
        self._plot = plot
        self.setAddButtonEnabled('black')

    @overrides
    def events(self) -> List[BackstoryEvent]:
        return self._plot.villain

    @overrides
    def cardClass(self):
        return StorylineVillainCard
