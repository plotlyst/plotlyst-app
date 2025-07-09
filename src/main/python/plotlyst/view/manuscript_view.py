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
import qtanim
from PyQt6.QtCore import QTimer, Qt, QObject, QEvent
from PyQt6.QtGui import QScreen
from PyQt6.QtWidgets import QApplication
from overrides import overrides
from qthandy import translucent, bold, margins, transparent, vspacer, decr_icon, vline, incr_icon, busy, \
    retain_when_hidden
from qthandy.filter import OpacityEventFilter, InstantTooltipEventFilter
from qtmenu import MenuWidget

from plotlyst.common import PLOTLYST_MAIN_COLOR, RELAXED_WHITE_COLOR
from plotlyst.core.domain import Novel, Document, Chapter, DocumentProgress
from plotlyst.core.domain import Scene
from plotlyst.event.core import emit_global_event, emit_critical, emit_info, Event, emit_event
from plotlyst.events import SceneChangedEvent, OpenDistractionFreeMode, \
    ExitDistractionFreeMode, NovelSyncEvent, CloseNovelEvent, SceneOrderChangedEvent, SceneAddedEvent, \
    NovelScenesOrganizationToggleEvent
from plotlyst.resources import ResourceType
from plotlyst.service.grammar import language_tool_proxy
from plotlyst.service.persistence import flush_or_fail
from plotlyst.service.resource import ask_for_resource
from plotlyst.view._view import AbstractNovelView
from plotlyst.view.common import tool_btn, ButtonPressResizeEventFilter, action, \
    ExclusiveOptionalButtonGroup, link_buttons_to_pages, scroll_to_bottom, restyle
from plotlyst.view.generated.manuscript_view_ui import Ui_ManuscriptView
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.style.theme import BG_DARK_COLOR
from plotlyst.view.widget.display import Icon
from plotlyst.view.widget.input import Toggle, SpinBoxDialog
from plotlyst.view.widget.manuscript import ManuscriptProgressCalendar, ManuscriptDailyProgress, \
    ManuscriptProgressCalendarLegend, ManuscriptProgressWidget
from plotlyst.view.widget.manuscript.editor import ManuscriptEditor, DistFreeControlsBar, DistFreeDisplayBar
from plotlyst.view.widget.manuscript.export import ManuscriptExportWidget
from plotlyst.view.widget.manuscript.find import ManuscriptFindWidget
from plotlyst.view.widget.manuscript.settings import ManuscriptEditorSettingsWidget
from plotlyst.view.widget.manuscript.sprint import SprintWidget
from plotlyst.view.widget.scene.editor import SceneMiniEditor
from plotlyst.view.widget.tree import TreeSettings


class ManuscriptView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel,
                         event_types=[SceneOrderChangedEvent, SceneAddedEvent, NovelScenesOrganizationToggleEvent])
        self.ui = Ui_ManuscriptView()
        self.ui.setupUi(self.widget)
        self.ui.splitter.setSizes([150, 500])
        self._empty_page()
        self._dist_free_mode: bool = False
        self._last_scroll_value: int = 0

        self.ui.lblWc.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.ui.treeChapters.setAutoSelectNewScenes(True)
        self.ui.btnAdd.setIcon(IconRegistry.plus_icon(RELAXED_WHITE_COLOR))
        self.ui.btnAddScene.setIcon(IconRegistry.plus_icon(RELAXED_WHITE_COLOR))
        self.ui.btnAddScene.clicked.connect(self.ui.treeChapters.addScene)

        self._dist_free_top_bar = DistFreeDisplayBar()
        self._dist_free_top_bar.btnExitDistFreeMode.clicked.connect(self._exit_distraction_free)

        self._dist_free_bottom_bar = DistFreeControlsBar()
        self.widget.layout().insertWidget(0, self._dist_free_top_bar)
        self.widget.layout().addWidget(self._dist_free_bottom_bar)
        self._dist_free_top_bar.setHidden(True)
        self._dist_free_bottom_bar.setHidden(True)

        self.ui.btnSceneInfo.setIcon(IconRegistry.scene_icon(color_on=PLOTLYST_MAIN_COLOR))
        self.ui.btnGoals.setIcon(IconRegistry.goal_icon('black', PLOTLYST_MAIN_COLOR))
        self.ui.btnReadability.setIcon(IconRegistry.from_name('fa5s.glasses', 'black', PLOTLYST_MAIN_COLOR))
        self.ui.btnProgress.setIcon(IconRegistry.from_name('mdi.calendar-month-outline', 'black', PLOTLYST_MAIN_COLOR))
        self.ui.btnFind.setIcon(IconRegistry.from_name('fa5s.search', 'black', PLOTLYST_MAIN_COLOR, hflip=True))
        self.ui.btnExport.setIcon(IconRegistry.from_name('mdi.file-export-outline', 'black', PLOTLYST_MAIN_COLOR))
        self.ui.btnSettings.setIcon(IconRegistry.cog_icon(color_on=PLOTLYST_MAIN_COLOR))

        self.ui.btnReadability.setHidden(True)

        self.ui.btnTreeToggle.setIcon(IconRegistry.from_name('mdi.file-tree-outline'))
        self.ui.btnTreeToggleSecondary.setIcon(IconRegistry.from_name('mdi.file-tree-outline'))
        retain_when_hidden(self.ui.btnTreeToggleSecondary)
        self.ui.btnTreeToggleSecondary.setHidden(True)
        self.ui.btnTreeToggle.clicked.connect(self._hide_sidebar)
        self.ui.btnTreeToggleSecondary.clicked.connect(self._show_sidebar)

        self._btnGroupSideBar = ExclusiveOptionalButtonGroup()
        self._btnGroupSideBar.addButton(self.ui.btnSceneInfo)
        self._btnGroupSideBar.addButton(self.ui.btnGoals)
        self._btnGroupSideBar.addButton(self.ui.btnProgress)
        self._btnGroupSideBar.addButton(self.ui.btnFind)
        self._btnGroupSideBar.addButton(self.ui.btnExport)
        self._btnGroupSideBar.addButton(self.ui.btnSettings)
        for btn in self._btnGroupSideBar.buttons():
            btn.installEventFilter(OpacityEventFilter(btn, enterOpacity=0.7, ignoreCheckedButton=True))
            btn.installEventFilter(ButtonPressResizeEventFilter(btn))

        self._btnGroupSideBar.buttonToggled.connect(self._side_bar_toggled)
        link_buttons_to_pages(self.ui.stackSide,
                              [(self.ui.btnSceneInfo, self.ui.pageInfo), (self.ui.btnGoals, self.ui.pageGoal),
                               (self.ui.btnProgress, self.ui.pageProgress),
                               (self.ui.btnFind, self.ui.pageFind),
                               (self.ui.btnExport, self.ui.pageExport),
                               (self.ui.btnSettings, self.ui.pageSettings)])

        bold(self.ui.lblWordCount)

        self._miniSceneEditor = SceneMiniEditor(self.novel)
        self.ui.pageInfo.layout().addWidget(self._miniSceneEditor)
        self.ui.pageInfo.layout().addWidget(vspacer())

        self.textEditor = ManuscriptEditor()
        self.ui.wdgEditor.layout().addWidget(self.textEditor)

        self._manuscriptDailyProgressDisplay = ManuscriptDailyProgress(self.novel)
        margins(self._manuscriptDailyProgressDisplay, bottom=20)
        self._manuscriptDailyProgressDisplay.refresh()

        self._progressCalendar = ManuscriptProgressCalendar(self.novel)
        self._progressCalendar.clicked.connect(self._manuscriptDailyProgressDisplay.setDate)
        self._progressCalendar.dayChanged.connect(self._manuscriptDailyProgressDisplay.setDate)
        self._manuscriptDailyProgressDisplay.jumpToToday.connect(self._progressCalendar.showToday)
        self.ui.pageProgress.layout().addWidget(self._manuscriptDailyProgressDisplay)
        self.ui.pageProgress.layout().addWidget(self._progressCalendar)
        self.ui.pageProgress.layout().addWidget(ManuscriptProgressCalendarLegend())
        self.ui.pageProgress.layout().addWidget(vspacer())

        self.wdgFind = ManuscriptFindWidget(self.novel)
        self.ui.pageFind.layout().addWidget(self.wdgFind)
        self.textEditor.attachFindWidget(self.wdgFind)
        self.wdgFind.matched.connect(self._term_searched)
        self.wdgFind.reset.connect(self._term_reset)
        self.wdgFind.replaced.connect(self._term_replaced)
        self.wdgFind.wdgResults.matchClicked.connect(self._navigate)

        self._btnDistractionFree = tool_btn(IconRegistry.expand_icon(), 'Enter distraction-free mode',
                                            transparent_=True)
        decr_icon(self._btnDistractionFree)
        self._btnDistractionFree.installEventFilter(
            OpacityEventFilter(self._btnDistractionFree, leaveOpacity=0.5, enterOpacity=0.7))
        self._btnDistractionFree.clicked.connect(self._enter_distraction_free)

        self._wdgSprint = SprintWidget()
        self._spellCheckIcon = Icon()
        self._spellCheckIcon.setIcon(IconRegistry.from_name('fa5s.spell-check'))
        self._spellCheckIcon.setToolTip('Spellcheck')
        self._cbSpellCheck = Toggle()
        self._cbSpellCheck.setToolTip('Toggle spellcheck')

        self.ui.btnHideRightBar.setIcon(IconRegistry.from_name('mdi.chevron-double-right', '#adb5bd'))
        incr_icon(self.ui.btnHideRightBar, 4)
        transparent(self.ui.btnHideRightBar)
        self.ui.btnHideRightBar.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnHideRightBar))
        self.ui.btnHideRightBar.clicked.connect(self._btnGroupSideBar.reset)

        self._progressWdg = ManuscriptProgressWidget(self.novel)
        self._progressWdg.btnEditGoal.clicked.connect(self._edit_wc_goal)
        self.ui.pageGoal.layout().addWidget(self._progressWdg, alignment=Qt.AlignmentFlag.AlignCenter)
        self.ui.pageGoal.layout().addWidget(vspacer())

        self._exportWidget = ManuscriptExportWidget(self.novel)
        self.ui.pageExport.layout().addWidget(self._exportWidget)
        self.ui.pageExport.layout().addWidget(vspacer())

        self._toolbarSeparator = vline()
        self._wdgToolbar = group(self._wdgSprint, self._toolbarSeparator, self._spellCheckIcon,
                                 self._cbSpellCheck, self._btnDistractionFree)
        self.ui.wdgTop.layout().addWidget(self._wdgToolbar, alignment=Qt.AlignmentFlag.AlignRight)
        margins(self._wdgToolbar, right=10, top=0)

        self._addSceneMenu = MenuWidget(self.ui.btnAdd)
        self._addSceneMenu.addAction(action('Add scene', IconRegistry.scene_icon(), self.ui.treeChapters.addScene))
        self._addSceneMenu.addAction(
            action('Add chapter', IconRegistry.chapter_icon(), self.ui.treeChapters.addChapter))

        self._handle_scenes_organization()

        self._settingsWidget = ManuscriptEditorSettingsWidget(novel)
        self._settingsWidget.langSelectionWidget.languageChanged.connect(self._language_changed)
        self.ui.scrollSettings.layout().addWidget(self._settingsWidget)

        self._cbSpellCheck.toggled.connect(self._spellcheck_toggled)
        self._cbSpellCheck.clicked.connect(self._spellcheck_clicked)
        self._spellcheck_toggled(self._cbSpellCheck.isChecked())

        self.ui.treeChapters.setSettings(TreeSettings(font_incr=2))
        self.ui.treeChapters.setNovel(self.novel, readOnly=self.novel.is_readonly())
        self.ui.treeChapters.sceneSelected.connect(self._editScene)
        self.ui.treeChapters.chapterSelected.connect(self._editChapter)
        self.ui.treeChapters.centralWidget().setProperty('bg', True)

        self.ui.wdgSide.setHidden(True)

        self.textEditor.setNovel(self.novel)
        self.textEditor.sceneSeparatorClicked.connect(self._scene_separator_clicked)
        self.textEditor.cleared.connect(self._empty_page)
        self.textEditor.attachSettingsWidget(self._settingsWidget)
        self.textEditor.textChanged.connect(self._text_changed)
        self.textEditor.progressChanged.connect(self._progress_changed)
        self.textEditor.selectionChanged.connect(self._text_selection_changed)
        self.textEditor.sceneTitleChanged.connect(self._scene_title_changed)
        self.textEditor.cursorPositionChanged.connect(self.ui.scrollEditor.ensureVisible)
        self.ui.scrollEditor.verticalScrollBar().valueChanged.connect(self._scroll_changed)
        self._dist_free_bottom_bar.btnFocus.toggled.connect(self.textEditor.setSentenceHighlighterEnabled)
        self._dist_free_bottom_bar.btnTypewriterMode.toggled.connect(self._toggle_typewriter_mode)

        if self.novel.chapters:
            self.ui.treeChapters.selectChapter(self.novel.chapters[0])
            self._editChapter(self.novel.chapters[0])
        elif self.novel.scenes:
            self.ui.treeChapters.selectScene(self.novel.scenes[0])
            self._editScene(self.novel.scenes[0])

        if self.novel.is_readonly():
            self.ui.btnAdd.setDisabled(True)
            self.ui.btnAdd.setToolTip('Option is disabled in Scrivener synchronization mode')
            self.ui.btnAdd.installEventFilter(InstantTooltipEventFilter(self.ui.btnAdd))

        self._update_story_goal()

        self.widget.installEventFilter(self)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, NovelSyncEvent):
            self.textEditor.refresh()
            self._text_changed()
        elif isinstance(event, SceneOrderChangedEvent):
            if self.textEditor.chapter():
                self._editChapter(self.textEditor.chapter())
            return
        elif isinstance(event, SceneAddedEvent):
            if event.scene.chapter and event.scene.chapter == self.textEditor.chapter():
                self._editChapter(self.textEditor.chapter())
            return
        elif isinstance(event, NovelScenesOrganizationToggleEvent):
            self._handle_scenes_organization()
            return
        super(ManuscriptView, self).event_received(event)

    @overrides
    def refresh(self):
        self.ui.treeChapters.refresh()

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if self._dist_free_mode and event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self._exit_distraction_free()
        # event.accept()
        return super().eventFilter(watched, event)

    def _enter_distraction_free(self):
        emit_global_event(OpenDistractionFreeMode(self))
        margins(self.widget, 0, 0, 0, 0)
        margins(self.ui.pageText, left=0)
        self.ui.pageText.setStyleSheet(f'QWidget {{background-color: {BG_DARK_COLOR};}}')
        self._wdgToolbar.setHidden(True)

        self._btnGroupSideBar.reset()
        self.ui.wdgTop.setHidden(True)
        self.ui.wdgLeftSide.setHidden(True)
        self.ui.wdgSideBar.setHidden(True)
        self.ui.wdgBottom.setHidden(True)
        self._dist_free_top_bar.setVisible(True)
        self._dist_free_bottom_bar.setVisible(True)
        self._dist_free_mode = True

        if self._cbSpellCheck.isChecked():
            self.textEditor.resetGrammarChecking()
            self._cbSpellCheck.setChecked(False)

        self.textEditor.initSentenceHighlighter()
        self.textEditor.setNightMode(True)

        self._dist_free_bottom_bar.setWordDisplay(self.ui.lblWordCount)
        self._dist_free_top_bar.activate(self._wdgSprint)
        self._dist_free_bottom_bar.activate()
        self.textEditor.setSentenceHighlighterEnabled(self._dist_free_bottom_bar.btnFocus.isChecked())

        self._toggle_typewriter_mode(self._dist_free_bottom_bar.btnTypewriterMode.isChecked())

        self.ui.scrollEditor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEditor.setFocus()

    def _exit_distraction_free(self):
        emit_global_event(ExitDistractionFreeMode(self))
        margins(self.widget, 4, 2, 2, 2)
        margins(self.ui.pageText, left=self.ui.wdgSideBar.width() if not self.ui.btnTreeToggle.isChecked() else 0,
                bottom=0)
        self.ui.pageText.setStyleSheet('')

        self.ui.wdgTop.setVisible(True)
        self._wdgToolbar.setVisible(True)
        self.ui.wdgLeftSide.setVisible(self.ui.btnTreeToggle.isChecked())
        self.ui.wdgSideBar.setVisible(True)
        self.ui.wdgBottom.setVisible(True)
        self._dist_free_top_bar.setHidden(True)
        self._dist_free_bottom_bar.setHidden(True)

        self._dist_free_mode = False
        self.textEditor.clearSentenceHighlighter()
        self.textEditor.setNightMode(False)

        self.ui.wdgBottom.layout().insertWidget(0, self.ui.lblWordCount, alignment=Qt.AlignmentFlag.AlignCenter)
        self._wdgToolbar.layout().insertWidget(0, self._wdgSprint)
        self._wdgSprint.setNightMode(False)
        self._wdgSprint.setVisible(True)
        self.ui.lblWordCount.setNightModeEnabled(False)
        self.ui.lblWordCount.setVisible(True)

        self.ui.scrollEditor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def _update_story_goal(self):
        wc = sum([x.manuscript.statistics.wc for x in self.novel.scenes if x.manuscript and x.manuscript.statistics])
        self.ui.lblWc.setText(f'{wc:,} word{"s" if wc > 1 else ""}')
        self._progressWdg.setValue(wc)

    def _editScene(self, scene: Scene):
        self._text_page()

        if not scene.manuscript:
            scene.manuscript = Document('', scene_id=scene.id)
            self.repo.update_scene(scene)

        self.textEditor.setScene(scene)
        self._miniSceneEditor.setScene(scene)

        self.ui.btnStage.setEnabled(True)
        self.ui.btnStage.setScene(scene, self.novel)

        self._recheckDocument()

    def _editChapter(self, chapter: Chapter):
        self._text_page()

        scenes = self.novel.scenes_in_chapter(chapter)
        for scene in scenes:
            if not scene.manuscript:
                scene.manuscript = Document('', scene_id=scene.id)
                self.repo.update_scene(scene)
        if scenes:
            self.textEditor.setChapterScenes(chapter, scenes)
            self._miniSceneEditor.setScenes(scenes)
        else:
            self._empty_page('Add a scene to this chapter to start writing')
            self._miniSceneEditor.reset()

        self.ui.btnStage.setDisabled(True)

        self._recheckDocument()

    def _recheckDocument(self):
        if self.ui.stackedWidget.currentWidget() == self.ui.pageText:
            self._text_changed()

            if self._cbSpellCheck.isChecked():
                self.textEditor.asyncCheckGrammar()

    def _text_changed(self):
        wc = self.textEditor.statistics().word_count
        self.ui.lblWordCount.setWordCount(wc)
        self._update_story_goal()

    def _text_selection_changed(self):
        selection = self.textEditor.selection()
        if selection:
            self.ui.lblWordCount.calculateSecondaryWordCount(selection.toPlainText())
        else:
            self.ui.lblWordCount.clearSecondaryWordCount()

    def _scene_title_changed(self, scene: Scene):
        self.repo.update_scene(scene)
        emit_event(self.novel, SceneChangedEvent(self, scene))

    def _progress_changed(self, progress: DocumentProgress):
        if self.ui.btnProgress.isChecked():
            self._manuscriptDailyProgressDisplay.setProgress(progress)

    def _edit_wc_goal(self):
        goal = SpinBoxDialog.edit('Word count goal', value=self.novel.manuscript_goals.target_wc,
                                  min_value=1000, max_value=10000000, step=1000)
        if goal:
            self.novel.manuscript_goals.target_wc = goal
            self.repo.update_novel(self.novel)
            self._refresh_target_wc()

    def _refresh_target_wc(self):
        self._progressWdg.setMaxValue(self.novel.manuscript_goals.target_wc)

    def _side_bar_toggled(self, _, toggled: bool):
        btn = self._btnGroupSideBar.checkedButton()
        if btn is None:
            if self.wdgFind.isActive():
                self.wdgFind.deactivate()
                self.textEditor.resetFind()
            qtanim.collapse(self.ui.wdgSide)
            return

        if toggled and not self.ui.wdgSide.isVisible():
            qtanim.expand(self.ui.wdgSide)

        if btn is self.ui.btnReadability:
            self._analysis_clicked(self.ui.btnReadability.isChecked())
        elif btn is self.ui.btnProgress:
            self._manuscriptDailyProgressDisplay.refresh()
        elif btn is self.ui.btnGoals:
            self._refresh_target_wc()

    def _spellcheck_toggled(self, toggled: bool):
        translucent(self._spellCheckIcon, 1 if toggled else 0.4)

    def _spellcheck_clicked(self, checked: bool):
        if checked:
            if language_tool_proxy.is_failed():
                self._cbSpellCheck.setChecked(False)
                emit_critical(language_tool_proxy.error)
            else:
                if self.wdgFind.isActive():
                    self.wdgFind.deactivate()
                    self.textEditor.resetFind()
                QTimer.singleShot(150, self.textEditor.asyncCheckGrammar)
        else:
            self.textEditor.resetGrammarChecking()

    def _analysis_clicked(self, checked: bool):
        if not checked:
            return

        if not ask_for_resource(ResourceType.NLTK_PUNKT_TOKENIZER):
            self.ui.btnReadability.setChecked(False)
            return

    def _scene_separator_clicked(self, scene: Scene):
        if not self.ui.btnSceneInfo.isChecked():
            self.ui.btnSceneInfo.setChecked(True)
        self._miniSceneEditor.selectScene(scene)

    @busy
    def _language_changed(self, lang: str):
        emit_info('Novel is getting closed. Persist workspace...')
        self.novel.lang_settings.lang = lang
        self.repo.update_project_novel(self.novel)
        flush_or_fail()
        emit_global_event(CloseNovelEvent(self, self.novel))

    def _is_empty_page(self) -> bool:
        return self.ui.stackedWidget.currentWidget() == self.ui.pageEmpty

    def _empty_page(self, message: str = ''):
        self.ui.lblEmptyPage.setText(message)
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageEmpty)
        self.ui.wdgTop.setProperty('relaxed-white-bg', False)
        restyle(self.ui.wdgTop)

    def _text_page(self):
        self.ui.stackedWidget.setCurrentWidget(self.ui.pageText)
        self.ui.wdgTop.setProperty('relaxed-white-bg', True)
        restyle(self.ui.wdgTop)

    def _hide_sidebar(self):
        def finished():
            qtanim.fade_in(self.ui.btnTreeToggleSecondary)
            margins(self.ui.pageText, left=self.ui.wdgSideBar.width())

        qtanim.toggle_expansion(self.ui.wdgLeftSide, False, teardown=finished)
        self.ui.btnTreeToggleSecondary.setChecked(False)

    def _show_sidebar(self):
        qtanim.toggle_expansion(self.ui.wdgLeftSide, True)
        margins(self.ui.pageText, left=0)
        self.ui.btnTreeToggle.setChecked(True)
        self.ui.btnTreeToggleSecondary.setVisible(False)

    def _toggle_typewriter_mode(self, toggled: bool):
        if toggled:
            screen: QScreen = QApplication.screenAt(self.ui.pageText.pos())
            margins(self.ui.pageText, bottom=screen.size().height() // 3)
        else:
            margins(self.ui.pageText, bottom=0)

    def _scroll_changed(self, value: int):
        maximum = self.ui.scrollEditor.verticalScrollBar().maximum()
        if self._last_scroll_value < maximum and value >= self._last_scroll_value:
            if 0 < maximum - value < 40:
                scroll_to_bottom(self.ui.scrollEditor)
        self._last_scroll_value = value

    def _term_searched(self):
        if self._cbSpellCheck.isChecked():
            self.textEditor.resetGrammarChecking()
            self._cbSpellCheck.setChecked(False)
        self.textEditor.activateFind()

    def _term_reset(self):
        self.textEditor.resetFind()

    def _term_replaced(self):
        scene = self.textEditor.scene()
        if scene:
            self.ui.treeChapters.selectScene(scene)
            self._editScene(scene)
        else:
            chapter = self.textEditor.chapter()
            if chapter:
                self.ui.treeChapters.selectChapter(chapter)
                self._editChapter(chapter)

        self._update_story_goal()

    def _navigate(self, context: dict):
        scene = context['scene']
        self.ui.treeChapters.selectScene(scene)
        if self.textEditor.scene() != scene:
            self._editScene(scene)
        self.textEditor.jumpTo(context['start'], context['end'])

    def _handle_scenes_organization(self):
        self.ui.btnAdd.setVisible(self.novel.prefs.is_scenes_organization())
        self.ui.btnAddScene.setVisible(not self.novel.prefs.is_scenes_organization())
