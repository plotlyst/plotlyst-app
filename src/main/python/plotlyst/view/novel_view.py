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

from overrides import overrides

from plotlyst.common import PLOTLYST_MAIN_COLOR
from plotlyst.core.domain import Novel, NovelSetting
from plotlyst.event.core import Event
from plotlyst.events import NovelUpdatedEvent, \
    SceneChangedEvent, NovelStorylinesToggleEvent, NovelStructureToggleEvent, NovelPanelCustomizationEvent
from plotlyst.view._view import AbstractNovelView
from plotlyst.view.common import set_tab_icon, set_tab_visible
from plotlyst.view.generated.novel_view_ui import Ui_NovelView
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.novel import NovelDescriptorsDisplay
from plotlyst.view.widget.plot.editor import PlotEditor
from plotlyst.view.widget.settings import NovelSettingsWidget


class NovelView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel, [SceneChangedEvent, NovelStorylinesToggleEvent,
                                 NovelStructureToggleEvent], global_event_types=[NovelUpdatedEvent])
        self.ui = Ui_NovelView()
        self.ui.setupUi(self.widget)

        set_tab_icon(self.ui.tabWidget, self.ui.tabStructure,
                     IconRegistry.story_structure_icon(color_on=PLOTLYST_MAIN_COLOR))
        set_tab_icon(self.ui.tabWidget, self.ui.tabPlot, IconRegistry.storylines_icon(color_on=PLOTLYST_MAIN_COLOR))
        set_tab_icon(self.ui.tabWidget, self.ui.tabDescriptors, IconRegistry.book_icon(color_on=PLOTLYST_MAIN_COLOR))
        set_tab_icon(self.ui.tabWidget, self.ui.tabTags, IconRegistry.tags_icon(color_on=PLOTLYST_MAIN_COLOR))
        set_tab_icon(self.ui.tabWidget, self.ui.tabSettings, IconRegistry.cog_icon(color_on=PLOTLYST_MAIN_COLOR))

        set_tab_visible(self.ui.tabWidget, self.ui.tabPlot, self.novel.prefs.toggled(NovelSetting.Storylines))
        set_tab_visible(self.ui.tabWidget, self.ui.tabStructure, self.novel.prefs.toggled(NovelSetting.Structure))
        set_tab_visible(self.ui.tabWidget, self.ui.tabTags, False)

        self.wdgDescriptors = NovelDescriptorsDisplay(self.novel)
        self.ui.tabDescriptors.layout().addWidget(self.wdgDescriptors)

        self.ui.wdgStructure.setNovel(self.novel)

        self.plot_editor = PlotEditor(self.novel)
        self.ui.tabPlot.layout().addWidget(self.plot_editor)

        self.ui.wdgTagsContainer.setNovel(self.novel)

        self._settings = NovelSettingsWidget(self.novel)
        self.ui.wdgSettings.layout().addWidget(self._settings)

        self.ui.tabWidget.setCurrentWidget(self.ui.tabDescriptors)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, NovelPanelCustomizationEvent):
            if isinstance(event, NovelStorylinesToggleEvent):
                set_tab_visible(self.ui.tabWidget, self.ui.tabPlot, event.toggled)
            elif isinstance(event, NovelStructureToggleEvent):
                set_tab_visible(self.ui.tabWidget, self.ui.tabStructure, event.toggled)
        else:
            super().event_received(event)

    @overrides
    def refresh(self):
        self.wdgDescriptors.refreshTitle()

    def show_settings(self):
        self.ui.tabWidget.setCurrentWidget(self.ui.tabSettings)
