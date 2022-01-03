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
import atexit
from typing import List, Optional

import qtawesome
from PyQt6.QtCore import Qt, QThreadPool, QObject, QEvent
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QMainWindow, QWidget, QApplication, QLineEdit, QTextEdit, QToolButton, QButtonGroup
from fbs_runtime import platform
from language_tool_python import LanguageTool
from overrides import overrides

from src.main.python.plotlyst.common import EXIT_CODE_RESTART
from src.main.python.plotlyst.core.client import client
from src.main.python.plotlyst.core.domain import Novel
from src.main.python.plotlyst.env import app_env
from src.main.python.plotlyst.event.core import event_log_reporter, EventListener, Event, emit_event, event_sender, \
    emit_critical, emit_info
from src.main.python.plotlyst.event.handler import EventLogHandler, event_dispatcher
from src.main.python.plotlyst.events import NovelReloadRequestedEvent, NovelReloadedEvent, NovelDeletedEvent, \
    SceneChangedEvent, NovelUpdatedEvent, OpenDistractionFreeMode
from src.main.python.plotlyst.settings import settings
from src.main.python.plotlyst.view.characters_view import CharactersView
from src.main.python.plotlyst.view.comments_view import CommentsView
from src.main.python.plotlyst.view.common import EditorCommand, spacer_widget, EditorCommandType, busy
from src.main.python.plotlyst.view.dialog.about import AboutDialog
from src.main.python.plotlyst.view.dialog.template import customize_character_profile
from src.main.python.plotlyst.view.docs_view import DocumentsView, DocumentsSidebar
from src.main.python.plotlyst.view.generated.main_window_ui import Ui_MainWindow
from src.main.python.plotlyst.view.home_view import HomeView
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.layout import clear_layout
from src.main.python.plotlyst.view.locations_view import LocationsView
from src.main.python.plotlyst.view.manuscript_view import ManuscriptView, SentenceHighlighter
from src.main.python.plotlyst.view.novel_view import NovelView
from src.main.python.plotlyst.view.reports_view import ReportsView
from src.main.python.plotlyst.view.scenes_view import ScenesOutlineView
from src.main.python.plotlyst.view.widget.input import RichTextEditor
from src.main.python.plotlyst.worker.cache import acts_registry
from src.main.python.plotlyst.worker.grammar import LanguageToolServerSetupWorker
from src.main.python.plotlyst.worker.persistence import RepositoryPersistenceManager, flush_or_fail


class MainWindow(QMainWindow, Ui_MainWindow, EventListener):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.resize(1000, 630)
        if app_env.is_dev():
            self.resize(1200, 830)
        if app_env.is_prod():
            self.setWindowState(Qt.WindowState.WindowMaximized)
        self.novel = None
        self._current_text_widget = None
        self.manuscript_view: Optional[ManuscriptView] = None
        self.reports_view: Optional[ReportsView] = None
        last_novel_id = settings.last_novel_id()
        if last_novel_id is not None:
            has_novel = client.has_novel(last_novel_id)
            if has_novel:
                self.novel = client.fetch_novel(last_novel_id)
        if self.novel is None:
            _novels = client.novels()
            if _novels:
                self.novel = client.fetch_novel(_novels[0].id)

        if self.novel:
            acts_registry.set_novel(self.novel)

        self._init_menubar()
        self._init_toolbar()

        self._init_views()

        self.event_log_handler = EventLogHandler(self.statusBar())
        event_log_reporter.info.connect(self.event_log_handler.on_info_event)
        event_log_reporter.error.connect(self.event_log_handler.on_error_event)
        event_sender.send.connect(event_dispatcher.dispatch)
        QApplication.instance().focusChanged.connect(self._focus_changed)
        self._register_events()

        self.sliderDocWidth.valueChanged.connect(
            lambda x: self.wdgDistractionFreeEditor.layout().setContentsMargins(self.width() / 3 - x, 0,
                                                                                self.width() / 3 - x, 0))
        self.wdgSprint.setCompactMode(True)
        self.wdgBottom.installEventFilter(self)
        self.btnReturn.setIcon(IconRegistry.from_name('mdi.arrow-collapse', 'white'))
        self.btnReturn.clicked.connect(lambda: self._toggle_fullscreen(on=False))
        self._sentenceHighlighter: Optional[SentenceHighlighter] = None
        self.btnFocus.setIcon(IconRegistry.from_name('mdi.credit-card', color_on='darkblue'))
        self.btnFocus.toggled.connect(self._toggle_manuscript_focus)

        self.repo = RepositoryPersistenceManager.instance()

        self.language_tool: Optional[LanguageTool] = None
        self._threadpool = QThreadPool()
        self._language_tool_setup_worker = LanguageToolServerSetupWorker(self)
        if not app_env.test_env():
            emit_info('Start initializing grammar checker...')
            self._threadpool.start(self._language_tool_setup_worker)

    def set_language_tool(self, tool: LanguageTool):
        self.language_tool = tool
        atexit.register(self.language_tool.close)
        if self.docs_view:
            self.notes_view.set_language_tool(self.language_tool)
        emit_info('Grammar checker was set up.')

    def set_language_tool_error(self, error: str):
        emit_critical('Could not initialize grammar checker', error)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, NovelReloadRequestedEvent):
            updated_novel = self._flush_end_fetch_novel()
            self.novel.update_from(updated_novel)
            emit_event(NovelReloadedEvent(self))
        elif isinstance(event, NovelDeletedEvent):
            if self.novel and event.novel.id == self.novel.id:
                self.novel = None
                self._clear_novel_views()
                for btn in self.buttonGroup.buttons():
                    if btn is not self.btnHome:
                        btn.setHidden(True)
        elif isinstance(event, NovelUpdatedEvent):
            if self.novel and event.novel.id == self.novel.id:
                self.novel.title = event.novel.title
        elif isinstance(event, SceneChangedEvent):
            event_dispatcher.deregister(self, SceneChangedEvent)
        elif isinstance(event, OpenDistractionFreeMode):
            self.stackMainPanels.setCurrentWidget(self.pageDistractionFree)
            clear_layout(self.wdgDistractionFreeEditor.layout())
            if event.timer and event.timer.isActive():
                self.wdgHeader.setVisible(True)
                self.wdgSprint.setModel(event.timer)
            else:
                self.wdgHeader.setHidden(True)
            self.wdgDistractionFreeEditor.layout().addWidget(event.editor)
            event.editor.setFocus()
            self.wdgBottom.setVisible(True)
            self.sliderDocWidth.setMaximum(self.width() / 3)
            if self.sliderDocWidth.value() <= 2:
                self.sliderDocWidth.setValue(self.sliderDocWidth.maximum() // 2)
            self.btnComments.setChecked(False)
            self._toggle_fullscreen(on=True)

    @overrides
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            if self.stackMainPanels.currentWidget() is self.pageDistractionFree:
                self._toggle_fullscreen(on=False)
        event.accept()

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.wdgBottom and event.type() == QEvent.Type.Leave:
            self.wdgBottom.setHidden(True)
        return super(MainWindow, self).eventFilter(watched, event)

    def _toggle_fullscreen(self, on: bool):
        self.statusbar.setHidden(on)
        self.toolBar.setHidden(on)
        if not platform.is_mac():
            self.menubar.setHidden(on)
            if not on:
                self.showMaximized()
        if not self.isFullScreen():
            if on:
                self.showFullScreen()
        if on:
            self._toggle_manuscript_focus(self.btnFocus.isChecked())
        else:
            editor = self.wdgDistractionFreeEditor.layout().itemAt(0).widget()
            self._toggle_manuscript_focus(False)
            self.manuscript_view.restore_editor(editor)
            self.stackMainPanels.setCurrentWidget(self.pageManuscript)

    def _toggle_manuscript_focus(self, toggled: bool):
        if toggled:
            editor: RichTextEditor = self.wdgDistractionFreeEditor.layout().itemAt(0).widget()
            self._sentenceHighlighter = SentenceHighlighter(editor.textEditor)
        elif self._sentenceHighlighter is not None:
            self._sentenceHighlighter.deleteLater()
            self._sentenceHighlighter = None

    @busy
    def _flush_end_fetch_novel(self):
        flush_or_fail()
        updated_novel = client.fetch_novel(self.novel.id)
        return updated_novel

    @busy
    def _init_views(self):
        self.home_view = HomeView()
        self.btnHome.setIcon(IconRegistry.home_icon())
        self.pageHome.layout().addWidget(self.home_view.widget)
        self.home_view.loadNovel.connect(self._load_new_novel)

        self.buttonGroup.buttonToggled.connect(self._on_view_changed)
        self.btnHome.setChecked(True)

        if not self.novel:
            for btn in self.buttonGroup.buttons():
                if btn is not self.btnHome:
                    btn.setHidden(True)
            return

        for btn in self.buttonGroup.buttons():
            btn.setVisible(True)

        self.novel_view = NovelView(self.novel)
        self.characters_view = CharactersView(self.novel)
        self.scenes_outline_view = ScenesOutlineView(self.novel)
        self.scenes_outline_view.commands_sent.connect(self._on_received_commands)
        self.locations_view = LocationsView(self.novel)
        self.comments_view = CommentsView(self.novel)
        self.pageComments.layout().addWidget(self.comments_view.widget)
        self.wdgSidebar.setCurrentWidget(self.pageComments)

        self.docs_view = DocumentsSidebar(self.novel)
        self.wdgDocs.layout().addWidget(self.docs_view)

        self.notes_view = DocumentsView(self.novel)

        self.btnNovel.setIcon(IconRegistry.book_icon())
        self.btnCharacters.setIcon(IconRegistry.character_icon())
        self.btnScenes.setIcon(IconRegistry.scene_icon())
        self.btnLocations.setIcon(IconRegistry.location_icon())
        self.btnNotes.setIcon(IconRegistry.document_edition_icon())

        self.pageNovel.layout().addWidget(self.novel_view.widget)
        self.pageCharacters.layout().addWidget(self.characters_view.widget)
        self.pageScenes.layout().addWidget(self.scenes_outline_view.widget)
        self.pageLocations.layout().addWidget(self.locations_view.widget)
        self.pageNotes.layout().addWidget(self.notes_view.widget)

        if self.novel.scenes:
            self.btnScenes.setChecked(True)
        else:
            self.btnCharacters.setChecked(True)

    def _on_view_changed(self):
        if self.btnHome.isChecked():
            self.stackedWidget.setCurrentWidget(self.pageHome)
            self.home_view.activate()
        elif self.btnNovel.isChecked():
            self.stackedWidget.setCurrentWidget(self.pageNovel)
            self.novel_view.activate()
        elif self.btnCharacters.isChecked():
            self.stackedWidget.setCurrentWidget(self.pageCharacters)
            self.characters_view.activate()
        elif self.btnScenes.isChecked():
            self.stackedWidget.setCurrentWidget(self.pageScenes)
            self.scenes_outline_view.activate()
        elif self.btnLocations.isChecked():
            self.stackedWidget.setCurrentWidget(self.pageLocations)
            self.locations_view.activate()
        elif self.btnNotes.isChecked():
            self.stackedWidget.setCurrentWidget(self.pageNotes)
            self.notes_view.activate()

    def _init_menubar(self):
        if app_env.is_prod():
            self.menuFile.removeAction(self.actionRestart)
        else:
            self.actionRestart.setIcon(qtawesome.icon('mdi.restart'))
            self.actionRestart.triggered.connect(lambda: QApplication.instance().exit(EXIT_CODE_RESTART))

        self.actionImportScrivener.triggered.connect(self._import_from_scrivener)
        self.actionAbout.triggered.connect(lambda: AboutDialog().exec())
        self.actionIncreaseFontSize.setIcon(IconRegistry.increase_font_size_icon())
        self.actionIncreaseFontSize.triggered.connect(self._increase_font_size)
        self.actionDecreaseFontSize.setIcon(IconRegistry.decrease_font_size_icon())
        self.actionDecreaseFontSize.triggered.connect(self.decrease_font_size)
        self.actionCut.setIcon(IconRegistry.cut_icon())
        self.actionCut.triggered.connect(self._cut_text)
        self.actionCopy.setIcon(IconRegistry.copy_icon())
        self.actionCopy.triggered.connect(self._copy_text)
        self.actionPaste.setIcon(IconRegistry.paste_icon())
        self.actionPaste.triggered.connect(self._paste_text)

        self.actionCharacterTemplateEditor.triggered.connect(lambda: customize_character_profile(self.novel, 0, self))

    def _init_toolbar(self):
        self.outline_mode = QToolButton(self.toolBar)
        self.outline_mode.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.outline_mode.setText('Plan')
        self.outline_mode.setCheckable(True)
        self.outline_mode.setIcon(IconRegistry.decision_icon(color='black'))

        self.manuscript_mode = QToolButton(self.toolBar)
        self.manuscript_mode.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.manuscript_mode.setText('Write')
        self.manuscript_mode.setIcon(IconRegistry.edit_icon(color_on='darkBlue'))
        self.manuscript_mode.setCheckable(True)

        self.reports_mode = QToolButton(self.toolBar)
        self.reports_mode.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.reports_mode.setText('Analyze')
        self.reports_mode.setIcon(IconRegistry.reports_icon())
        self.reports_mode.setCheckable(True)

        self._mode_btn_group = QButtonGroup()
        self._mode_btn_group.addButton(self.outline_mode)
        self._mode_btn_group.addButton(self.manuscript_mode)
        self._mode_btn_group.addButton(self.reports_mode)
        self._mode_btn_group.setExclusive(True)
        self._mode_btn_group.buttonToggled.connect(self._panel_toggled)

        self.btnComments = QToolButton(self.toolBar)
        self.btnComments.setIcon(IconRegistry.from_name('mdi.comment-outline', color='#2e86ab'))
        self.btnComments.setMinimumWidth(50)
        self.btnComments.setCheckable(True)
        self.btnComments.toggled.connect(self.wdgSidebar.setVisible)

        self.toolBar.addWidget(spacer_widget(5))
        self.toolBar.addAction(IconRegistry.home_icon(), 'Home')
        self.toolBar.addSeparator()
        self.toolBar.addWidget(self.outline_mode)
        self.toolBar.addWidget(self.manuscript_mode)
        self.toolBar.addWidget(self.reports_mode)
        self.toolBar.addWidget(spacer_widget())
        self.toolBar.addWidget(self.btnComments)

        self.wdgSidebar.setHidden(True)
        self.wdgDocs.setHidden(True)

        self.outline_mode.setChecked(True)

    def _panel_toggled(self):
        if self.outline_mode.isChecked():
            self.stackMainPanels.setCurrentWidget(self.pageOutline)
            self._on_view_changed()
        elif self.manuscript_mode.isChecked():
            self.stackMainPanels.setCurrentWidget(self.pageManuscript)
            if not self.manuscript_view:
                self.manuscript_view = ManuscriptView(self.novel)
                self.pageManuscript.layout().addWidget(self.manuscript_view.widget)
            self.manuscript_view.activate()
        elif self.reports_mode.isChecked():
            self.stackMainPanels.setCurrentWidget(self.pageReports)
            if not self.reports_view:
                self.reports_view = ReportsView(self.novel)
                self.pageReports.layout().addWidget(self.reports_view.widget)
            self.reports_view.activate()

    def _import_from_scrivener(self):
        self.btnHome.click()
        self.home_view.import_from_scrivener()

    def _increase_font_size(self):
        current_font = QApplication.font()
        self._set_font_size(current_font.pointSize() + 1)

    def decrease_font_size(self):
        current_font = QApplication.font()
        self._set_font_size(current_font.pointSize() - 1)

    def _set_font_size(self, value: int):
        current_font = QApplication.font()
        current_font.setPointSizeF(value)
        QApplication.instance().setFont(current_font)

        for widget in QApplication.allWidgets():
            if widget is self.menubar:
                continue
            font = widget.font()
            font.setPointSizeF(value)
            widget.setFont(font)

    @busy
    def _load_new_novel(self, novel: Novel):
        if self.novel and self.novel.id == novel.id:
            return

        self.repo.flush()
        event_dispatcher.clear()
        self.pageHome.layout().removeWidget(self.home_view.widget)
        self.home_view.widget.deleteLater()
        if self.novel:
            self._clear_novel_views()

        self.novel = client.fetch_novel(novel.id)
        acts_registry.set_novel(self.novel)
        self._init_views()
        settings.set_last_novel_id(self.novel.id)
        self._register_events()

    def _register_events(self):
        event_dispatcher.register(self, NovelReloadRequestedEvent)
        event_dispatcher.register(self, NovelDeletedEvent)
        event_dispatcher.register(self, NovelUpdatedEvent)
        event_dispatcher.register(self, OpenDistractionFreeMode)
        if self.novel and not self.novel.scenes:
            event_dispatcher.register(self, SceneChangedEvent)

    def _clear_novel_views(self):
        self.pageNovel.layout().removeWidget(self.novel_view.widget)
        self.novel_view.widget.deleteLater()
        self.pageCharacters.layout().removeWidget(self.characters_view.widget)
        self.characters_view.widget.deleteLater()
        self.pageScenes.layout().removeWidget(self.scenes_outline_view.widget)
        self.scenes_outline_view.widget.deleteLater()
        self.pageNotes.layout().removeWidget(self.notes_view.widget)
        self.notes_view.widget.deleteLater()
        self.pageComments.layout().removeWidget(self.comments_view.widget)
        self.comments_view.widget.deleteLater()

        if self.pageManuscript.layout().count():
            self.pageManuscript.layout().removeWidget(self.manuscript_view.widget)
            self.manuscript_view.widget.deleteLater()
            self.manuscript_view = None

    def _on_received_commands(self, widget: QWidget, commands: List[EditorCommand]):
        for cmd in commands:
            if cmd.type == EditorCommandType.UPDATE_SCENE_SEQUENCES:
                for index, scene in enumerate(self.novel.scenes):
                    scene.sequence = index
                self.repo.update_novel(self.novel)

    def _focus_changed(self, old_widget: QWidget, current_widget: QWidget):
        if isinstance(current_widget, (QLineEdit, QTextEdit)):
            text_actions_enabled = True
            self._current_text_widget = current_widget
        else:
            text_actions_enabled = False
            self._current_text_widget = None
        self.actionCut.setEnabled(text_actions_enabled)
        self.actionCopy.setEnabled(text_actions_enabled)
        self.actionPaste.setEnabled(text_actions_enabled)

    def _cut_text(self):
        if self._current_text_widget:
            self._current_text_widget.cut()

    def _copy_text(self):
        if self._current_text_widget:
            self._current_text_widget.copy()

    def _paste_text(self):
        if self._current_text_widget:
            self._current_text_widget.paste()
