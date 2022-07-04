"""
Plotlyst
Copyright (C) 2021-2022  Zsolt Kovari

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

from PyQt5.QtCore import QModelIndex, QTimer, Qt
from PyQt5.QtWidgets import QHeaderView, QApplication
from overrides import overrides
from qthandy import opaque, incr_font, bold, btn_popup, margins, transparent

from src.main.python.plotlyst.core.domain import Novel, Document
from src.main.python.plotlyst.event.core import emit_event, emit_critical, emit_info
from src.main.python.plotlyst.events import NovelUpdatedEvent, SceneChangedEvent, OpenDistractionFreeMode, \
    ChapterChangedEvent, SceneDeletedEvent, ExitDistractionFreeMode
from src.main.python.plotlyst.model.chapters_model import ChaptersTreeModel, SceneNode, ChapterNode
from src.main.python.plotlyst.service.grammar import language_tool_proxy
from src.main.python.plotlyst.service.persistence import flush_or_fail
from src.main.python.plotlyst.view._view import AbstractNovelView
from src.main.python.plotlyst.view.common import OpacityEventFilter
from src.main.python.plotlyst.view.generated.manuscript_view_ui import Ui_ManuscriptView
from src.main.python.plotlyst.view.icons import IconRegistry, avatars
from src.main.python.plotlyst.view.widget.chart import ManuscriptLengthChart
from src.main.python.plotlyst.view.widget.manuscript import ManuscriptContextMenuWidget, \
    DistractionFreeManuscriptEditor, ManuscriptTextEdit


class ManuscriptView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel, [NovelUpdatedEvent, SceneChangedEvent, ChapterChangedEvent, SceneDeletedEvent])
        self.ui = Ui_ManuscriptView()
        self.ui.setupUi(self.widget)
        self.ui.splitter.setSizes([100, 500])
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageOverview)

        self.ui.btnTitle.setText(self.novel.title)

        self.ui.btnStoryGoal.setText('80,000')
        self.ui.btnTitle.clicked.connect(self._homepage)
        self.ui.btnStoryGoal.clicked.connect(self._homepage)

        self.chart_manuscript = ManuscriptLengthChart()
        self.ui.chartChaptersLength.setChart(self.chart_manuscript)
        self.chart_manuscript.refresh(self.novel)

        bold(self.ui.lineSceneTitle)
        incr_font(self.ui.lineSceneTitle)
        transparent(self.ui.lineSceneTitle)
        self.ui.lineSceneTitle.textEdited.connect(self._scene_title_edited)

        self.ui.btnDistractionFree.setIcon(IconRegistry.from_name('fa5s.expand-alt'))
        self.ui.btnSpellCheckIcon.setIcon(IconRegistry.from_name('fa5s.spell-check'))
        self.ui.btnAnalysisIcon.setIcon(IconRegistry.from_name('fa5s.glasses'))
        self.ui.btnContext.setIcon(IconRegistry.context_icon())
        self.ui.btnContext.installEventFilter(OpacityEventFilter(leaveOpacity=0.7, parent=self.ui.btnContext))
        self._contextMenuWidget = ManuscriptContextMenuWidget(novel, self.widget)
        btn_popup(self.ui.btnContext, self._contextMenuWidget)
        self._contextMenuWidget.languageChanged.connect(self._language_changed)
        self.ui.cbSpellCheck.toggled.connect(self._spellcheck_toggled)
        self.ui.cbSpellCheck.clicked.connect(self._spellcheck_clicked)
        self.ui.btnAnalysis.toggled.connect(self._analysis_toggled)
        self.ui.btnAnalysis.clicked.connect(self._analysis_clicked)
        self.ui.wdgReadability.cbAdverbs.toggled.connect(self._adverb_highlight_toggled)
        self._spellcheck_toggled(self.ui.btnSpellCheckIcon.isChecked())
        self._analysis_toggled(self.ui.btnAnalysis.isChecked())

        self._dist_free_editor = DistractionFreeManuscriptEditor(self.ui.pageDistractionFree)
        self._dist_free_editor.exitRequested.connect(self._exit_distraction_free)
        self.ui.pageDistractionFree.layout().addWidget(self._dist_free_editor)

        self.chaptersModel = ChaptersTreeModel(self.novel)
        self.ui.treeChapters.setModel(self.chaptersModel)
        self.ui.treeChapters.expandAll()
        self.chaptersModel.modelReset.connect(self.ui.treeChapters.expandAll)
        self.ui.treeChapters.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.ui.treeChapters.setColumnWidth(ChaptersTreeModel.ColPlus, 24)
        self.ui.treeChapters.clicked.connect(self._edit)

        self.ui.wdgTopAnalysis.setHidden(True)
        self.ui.wdgSideAnalysis.setHidden(True)

        self.ui.textEdit.textChanged.connect(self._text_changed)
        self.ui.textEdit.selectionChanged.connect(self._text_selection_changed)
        self.ui.btnDistractionFree.clicked.connect(self._enter_distraction_free)

        self._update_story_goal()

    @overrides
    def refresh(self):
        self.chaptersModel.update()
        self.chaptersModel.modelReset.emit()

    def _enter_distraction_free(self):
        emit_event(OpenDistractionFreeMode(self))
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageDistractionFree)
        margins(self.widget, 0, 0, 0, 0)
        self.ui.wdgTitle.setHidden(True)
        self.ui.treeChapters.setHidden(True)
        self._dist_free_editor.activate(self.ui.textEdit, self.ui.wdgSprint.model())
        self._dist_free_editor.setWordDisplay(self.ui.lblWordCount)

    def _exit_distraction_free(self):
        emit_event(ExitDistractionFreeMode(self))
        self._dist_free_editor.deactivate()
        margins(self.widget, 4, 2, 2, 2)
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageText)
        self.ui.wdgTitle.setVisible(True)
        self.ui.treeChapters.setVisible(True)

        self.ui.wdgBottom.layout().addWidget(self.ui.lblWordCount, alignment=Qt.AlignCenter)
        self.ui.lblWordCount.setStyleSheet('color: black')
        self.ui.lblWordCount.setVisible(True)
        self.ui.wdgEditor.layout().insertWidget(0, self.ui.textEdit)
        self.ui.wdgReadability.cbAdverbs.setChecked(False)

    def _update_story_goal(self):
        wc = sum([x.manuscript.statistics.wc for x in self.novel.scenes if x.manuscript and x.manuscript.statistics])
        self.ui.btnStoryGoal.setText(f'{wc} word{"s" if wc > 1 else ""}')
        self.ui.progressStory.setValue(int(wc / 80000 * 100))

    def _edit(self, index: QModelIndex):
        node = index.data(ChaptersTreeModel.NodeRole)
        self.ui.textEdit.setGrammarCheckEnabled(False)
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageText)

        if isinstance(node, SceneNode):
            if not node.scene.manuscript:
                node.scene.manuscript = Document('', scene_id=node.scene.id)
                self.repo.update_scene(node.scene)

            self.ui.textEdit.setScene(node.scene)

            if node.scene.title:
                self.ui.lineSceneTitle.setText(node.scene.title)
                self.ui.lineSceneTitle.setPlaceholderText('Scene title')
            else:
                self.ui.lineSceneTitle.clear()
                self.ui.lineSceneTitle.setPlaceholderText(node.scene.title_or_index(self.novel))

            if node.scene.pov:
                self.ui.btnPov.setIcon(avatars.avatar(node.scene.pov))
                self.ui.btnPov.setVisible(True)
            else:
                self.ui.btnPov.setHidden(True)
            scene_type_icon = IconRegistry.scene_type_icon(node.scene)
            if scene_type_icon:
                self.ui.btnSceneType.setIcon(scene_type_icon)
                self.ui.btnSceneType.setVisible(True)
            else:
                self.ui.btnSceneType.setHidden(True)
        elif isinstance(node, ChapterNode):
            scenes = self.novel.scenes_in_chapter(node.chapter)
            for scene in scenes:
                if not scene.manuscript:
                    scene.manuscript = Document('', scene_id=scene.id)
                    self.repo.update_scene(scene)
            if scenes:
                self.ui.textEdit.setChapterScenes(scenes)
            else:
                self.ui.stackedWidget.setCurrentWidget(self.ui.pageEmpty)

            self.ui.lineSceneTitle.setText(node.chapter.title_index(self.novel))
            self.ui.btnPov.setHidden(True)
            self.ui.btnSceneType.setHidden(True)

        if self.ui.stackedWidget.currentWidget() == self.ui.pageText:
            self.ui.textEdit.setMargins(30, 30, 30, 30)
            self._text_changed()

            if self.ui.cbSpellCheck.isChecked():
                self.ui.textEdit.setGrammarCheckEnabled(True)
                self.ui.textEdit.asyncCheckGrammer()

            if self.ui.btnAnalysis.isChecked():
                self.ui.wdgReadability.checkTextDocuments(self.ui.textEdit.documents())

    def _text_changed(self):
        wc = self.ui.textEdit.statistics().word_count
        self.ui.lblWordCount.setWordCount(wc)
        self._update_story_goal()
        self.ui.wdgReadability.setTextDocumentsUpdated(self.ui.textEdit.documents())

    def _text_selection_changed(self, editor: ManuscriptTextEdit):
        fragment = editor.textCursor().selection()
        if fragment:
            self.ui.lblWordCount.calculateSecondaryWordCount(fragment.toPlainText())
        else:
            self.ui.lblWordCount.clearSecondaryWordCount()

    def _scene_title_edited(self, text: str):
        pass

    def _homepage(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageOverview)
        self.ui.treeChapters.clearSelection()

        self.chart_manuscript.refresh(self.novel)

    def _spellcheck_toggled(self, toggled: bool):
        opaque(self.ui.btnSpellCheckIcon, 1 if toggled else 0.4)

    def _spellcheck_clicked(self, checked: bool):
        if checked:
            if language_tool_proxy.is_failed():
                self.ui.cbSpellCheck.setChecked(False)
                emit_critical(language_tool_proxy.error)
            else:
                self.ui.wdgReadability.cbAdverbs.setChecked(False)
                self.ui.textEdit.setGrammarCheckEnabled(True)
                self.ui.textEdit.asyncCheckGrammer()
        else:
            self.ui.textEdit.setGrammarCheckEnabled(False)
            self.ui.textEdit.checkGrammar()

    def _analysis_toggled(self, toggled: bool):
        opaque(self.ui.btnAnalysisIcon, 1 if toggled else 0.4)

    def _analysis_clicked(self, checked: bool):
        if not checked:
            return

        self.ui.wdgReadability.checkTextDocuments(self.ui.textEdit.documents())

    def _adverb_highlight_toggled(self, toggled: bool):
        if toggled:
            if self.ui.cbSpellCheck.isChecked():
                self.ui.cbSpellCheck.setChecked(False)
                self.ui.textEdit.setGrammarCheckEnabled(False)
                self.ui.textEdit.checkGrammar()
        self.ui.textEdit.setWordTagHighlighterEnabled(toggled)

    def _language_changed(self, lang: str):
        emit_info('Application is shutting down. Persist workspace...')
        self.novel.lang_settings.lang = lang
        self.repo.update_project_novel(self.novel)
        flush_or_fail()
        QTimer.singleShot(1000, QApplication.exit)
