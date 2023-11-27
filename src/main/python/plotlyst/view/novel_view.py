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
from typing import Optional

from PyQt6.QtCore import QObject, QEvent
from overrides import overrides
from qthandy import retain_when_hidden, decr_icon, gc
from qthandy.filter import OpacityEventFilter

from src.main.python.plotlyst.common import PLOTLYST_MAIN_COLOR
from src.main.python.plotlyst.core.client import json_client
from src.main.python.plotlyst.core.domain import Novel, Document, NovelSetting
from src.main.python.plotlyst.event.core import emit_global_event, Event
from src.main.python.plotlyst.events import NovelUpdatedEvent, \
    SceneChangedEvent, NovelStorylinesToggleEvent, NovelStructureToggleEvent, NovelMindmapToggleEvent, \
    NovelPanelCustomizationEvent
from src.main.python.plotlyst.resources import resource_registry
from src.main.python.plotlyst.view._view import AbstractNovelView
from src.main.python.plotlyst.view.common import ButtonPressResizeEventFilter, set_tab_icon, set_tab_visible, tool_btn
from src.main.python.plotlyst.view.dialog.novel import NovelEditionDialog, SynopsisEditorDialog
from src.main.python.plotlyst.view.generated.novel_view_ui import Ui_NovelView
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.style.base import apply_border_image
from src.main.python.plotlyst.view.widget.plot import PlotEditor
from src.main.python.plotlyst.view.widget.settings import NovelSettingsWidget
from src.main.python.plotlyst.view.widget.story_map import EventsMindMapView


class NovelView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel, [SceneChangedEvent, NovelMindmapToggleEvent, NovelStorylinesToggleEvent,
                                 NovelStructureToggleEvent], global_event_types=[NovelUpdatedEvent])
        self.ui = Ui_NovelView()
        self.ui.setupUi(self.widget)

        set_tab_icon(self.ui.tabWidget, self.ui.tabEvents,
                     IconRegistry.from_name('ri.mind-map', color_on=PLOTLYST_MAIN_COLOR))
        set_tab_icon(self.ui.tabWidget, self.ui.tabStructure,
                     IconRegistry.story_structure_icon(color_on=PLOTLYST_MAIN_COLOR))
        set_tab_icon(self.ui.tabWidget, self.ui.tabPlot, IconRegistry.storylines_icon(color_on=PLOTLYST_MAIN_COLOR))
        set_tab_icon(self.ui.tabWidget, self.ui.tabSynopsis,
                     IconRegistry.from_name('fa5s.scroll', color_on=PLOTLYST_MAIN_COLOR))
        set_tab_icon(self.ui.tabWidget, self.ui.tabTags, IconRegistry.tags_icon(color_on=PLOTLYST_MAIN_COLOR))
        set_tab_icon(self.ui.tabWidget, self.ui.tabSettings, IconRegistry.cog_icon(color_on=PLOTLYST_MAIN_COLOR))

        set_tab_visible(self.ui.tabWidget, self.ui.tabEvents, self.novel.prefs.toggled(NovelSetting.Mindmap))
        set_tab_visible(self.ui.tabWidget, self.ui.tabPlot, self.novel.prefs.toggled(NovelSetting.Storylines))
        set_tab_visible(self.ui.tabWidget, self.ui.tabStructure, self.novel.prefs.toggled(NovelSetting.Structure))

        self.ui.btnEditNovel.setIcon(IconRegistry.edit_icon(color_on='darkBlue'))
        self.ui.btnEditNovel.installEventFilter(OpacityEventFilter(parent=self.ui.btnEditNovel))
        self.ui.btnEditNovel.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnEditNovel))
        self.ui.btnEditNovel.clicked.connect(self._edit_novel)
        retain_when_hidden(self.ui.btnEditNovel)
        self.ui.wdgTitle.installEventFilter(self)
        self.ui.btnEditNovel.setHidden(True)

        self.ui.textPremise.setStyleSheet('font-size: 16pt;')
        self.ui.textPremise.setToolTip('Premise')
        self.ui.textPremise.setFontItalic(True)
        self.ui.btnPremiseIcon.setIcon(IconRegistry.from_name('mdi.label-variant'))
        self._dialogSynopsisEditor: Optional[SynopsisEditorDialog] = None

        self._btnSynopsisExtendEdit = tool_btn(IconRegistry.expand_icon(), tooltip='Edit in full view',
                                               transparent_=True)
        decr_icon(self._btnSynopsisExtendEdit, 2)
        self._btnSynopsisExtendEdit.installEventFilter(
            OpacityEventFilter(self._btnSynopsisExtendEdit, leaveOpacity=0.55))
        self.ui.subtitleSynopsis.addWidget(self._btnSynopsisExtendEdit)
        self._btnSynopsisExtendEdit.clicked.connect(self._expandSynopsisEditor)

        self.ui.lblTitle.setText(self.novel.title)
        self.ui.textPremise.setText(self.novel.premise)
        self.ui.textPremise.textChanged.connect(self._premise_changed)
        self.ui.textSynopsis.setPlaceholderText("Write down your story's main events")
        self.ui.textSynopsis.setMargins(0, 10, 0, 10)
        self.ui.textSynopsis.textEdit.setSidebarEnabled(False)
        self.ui.textSynopsis.textEdit.setTabChangesFocus(True)
        self.ui.textSynopsis.setGrammarCheckEnabled(self.novel.prefs.docs.grammar_check)

        self.ui.textSynopsis.setToolbarVisible(False)
        self.ui.textSynopsis.setTitleVisible(False)
        if self.novel.synopsis:
            json_client.load_document(self.novel, self.novel.synopsis)
            self.ui.textSynopsis.setText(self.novel.synopsis.content)
            self.ui.lblSynopsisWords.setWordCount(self.ui.textSynopsis.textEdit.statistics().word_count)
        self.ui.textSynopsis.textEdit.textChanged.connect(self._synopsis_changed)

        self._eventsMap = EventsMindMapView(self.novel)
        self.ui.wdgEventsMapParent.layout().addWidget(self._eventsMap)

        self.ui.wdgStructure.setNovel(self.novel)
        self.ui.wdgTitle.setFixedHeight(150)
        apply_border_image(self.ui.wdgTitle, resource_registry.frame1)

        self.plot_editor = PlotEditor(self.novel)
        self.ui.wdgPlotContainer.layout().addWidget(self.plot_editor)

        self.ui.wdgTagsContainer.setNovel(self.novel)

        self._settings = NovelSettingsWidget(self.novel)
        self.ui.wdgSettings.layout().addWidget(self._settings)

        self.ui.tabWidget.setCurrentWidget(self.ui.tabSynopsis)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, NovelPanelCustomizationEvent):
            if isinstance(event, NovelMindmapToggleEvent):
                set_tab_visible(self.ui.tabWidget, self.ui.tabEvents, event.toggled)
            elif isinstance(event, NovelStorylinesToggleEvent):
                set_tab_visible(self.ui.tabWidget, self.ui.tabPlot, event.toggled)
            elif isinstance(event, NovelStructureToggleEvent):
                set_tab_visible(self.ui.tabWidget, self.ui.tabStructure, event.toggled)
        else:
            super().event_received(event)

    @overrides
    def refresh(self):
        self.ui.lblTitle.setText(self.novel.title)

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Enter:
            self.ui.btnEditNovel.setVisible(True)
        elif event.type() == QEvent.Type.Leave:
            self.ui.btnEditNovel.setHidden(True)

        return super(NovelView, self).eventFilter(watched, event)

    def _edit_novel(self):
        title = NovelEditionDialog().display(self.novel)
        if title:
            self.novel.title = title
            self.repo.update_project_novel(self.novel)
            self.ui.lblTitle.setText(self.novel.title)
            emit_global_event(NovelUpdatedEvent(self, self.novel))

    def _premise_changed(self):
        text = self.ui.textPremise.toPlainText()
        self.novel.premise = text
        self.repo.update_novel(self.novel)

    def _expandSynopsisEditor(self):
        if self.novel.synopsis is None:
            self.__init_synopsis_doc()
        self._dialogSynopsisEditor = SynopsisEditorDialog(self.novel)
        self.ui.textSynopsis.setDisabled(True)
        self._btnSynopsisExtendEdit.setDisabled(True)
        self._dialogSynopsisEditor.accepted.connect(self._closeSynopsisEditor)
        self._dialogSynopsisEditor.rejected.connect(self._closeSynopsisEditor)
        self._dialogSynopsisEditor.show()

    def _closeSynopsisEditor(self):
        self.ui.textSynopsis.setEnabled(True)
        self.ui.textSynopsis.setText(self._dialogSynopsisEditor.synopsis())
        self._btnSynopsisExtendEdit.setEnabled(True)
        gc(self._dialogSynopsisEditor)
        self._dialogSynopsisEditor = None

    def _synopsis_changed(self):
        if self.novel.synopsis is None:
            self.__init_synopsis_doc()
        self.novel.synopsis.content = self.ui.textSynopsis.textEdit.toHtml()
        self.ui.lblSynopsisWords.setWordCount(self.ui.textSynopsis.textEdit.statistics().word_count)
        self.repo.update_doc(self.novel, self.novel.synopsis)

    def __init_synopsis_doc(self):
        self.novel.synopsis = Document('Synopsis')
        self.novel.synopsis.loaded = True
        self.repo.update_novel(self.novel)
