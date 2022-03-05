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
from typing import Optional

import qtawesome
from PyQt5.QtCore import Qt, QThreadPool, QObject, QEvent, QTimer
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QMainWindow, QWidget, QApplication, QLineEdit, QTextEdit, QToolButton, QButtonGroup
from fbs_runtime import platform
from overrides import overrides
from qthandy import spacer, busy, gc, clear_layout
from textstat import textstat

from src.main.python.plotlyst.common import EXIT_CODE_RESTART
from src.main.python.plotlyst.core.client import client
from src.main.python.plotlyst.core.domain import Novel
from src.main.python.plotlyst.core.text import sentence_count
from src.main.python.plotlyst.env import app_env
from src.main.python.plotlyst.event.core import event_log_reporter, EventListener, Event, emit_event, event_sender, \
    emit_info
from src.main.python.plotlyst.event.handler import EventLogHandler, event_dispatcher
from src.main.python.plotlyst.events import NovelReloadRequestedEvent, NovelReloadedEvent, NovelDeletedEvent, \
    SceneChangedEvent, NovelUpdatedEvent, OpenDistractionFreeMode, ToggleOutlineViewTitle
from src.main.python.plotlyst.settings import settings
from src.main.python.plotlyst.view.characters_view import CharactersView
from src.main.python.plotlyst.view.comments_view import CommentsView
from src.main.python.plotlyst.view.dialog.about import AboutDialog
from src.main.python.plotlyst.view.dialog.template import customize_character_profile
from src.main.python.plotlyst.view.docs_view import DocumentsView, DocumentsSidebar
from src.main.python.plotlyst.view.generated.main_window_ui import Ui_MainWindow
from src.main.python.plotlyst.view.home_view import HomeView
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.locations_view import LocationsView
from src.main.python.plotlyst.view.manuscript_view import ManuscriptView
from src.main.python.plotlyst.view.novel_view import NovelView
from src.main.python.plotlyst.view.reports_view import ReportsView
from src.main.python.plotlyst.view.scenes_view import ScenesOutlineView
from src.main.python.plotlyst.view.widget.input import CapitalizationEventFilter
from src.main.python.plotlyst.view.widget.manuscript import ManuscriptTextEditor
from src.main.python.plotlyst.worker.cache import acts_registry
from src.main.python.plotlyst.worker.download import NltkResourceDownloadWorker
from src.main.python.plotlyst.worker.grammar import LanguageToolServerSetupWorker, dictionary, language_tool_proxy
from src.main.python.plotlyst.worker.persistence import RepositoryPersistenceManager, flush_or_fail

textstat.sentence_count = sentence_count


class MainWindow(QMainWindow, Ui_MainWindow, EventListener):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.resize(1000, 630)
        if app_env.is_dev():
            self.resize(1200, 830)
        if app_env.is_prod():
            self.setWindowState(Qt.WindowMaximized)
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
            dictionary.set_novel(self.novel)
            app_env.novel = self.novel

        self.home_view = HomeView()
        self.pageHome.layout().addWidget(self.home_view.widget)
        self.home_view.loadNovel.connect(self._load_new_novel)

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
        self.btnFocus.setIcon(IconRegistry.from_name('mdi.credit-card', color_on='darkBlue'))
        self.btnFocus.toggled.connect(self._toggle_manuscript_focus)
        self.btnNightMode.setIcon(IconRegistry.from_name('mdi.weather-night', color_on='darkBlue'))
        self.btnNightMode.toggled.connect(self._toggle_manuscript_night_mode)

        self.repo = RepositoryPersistenceManager.instance()

        self._threadpool = QThreadPool()
        language_tool_setup_worker = LanguageToolServerSetupWorker()
        download_worker = NltkResourceDownloadWorker()
        self._threadpool.start(download_worker)

        if self.novel:
            language_tool_setup_worker.lang = self.novel.lang_settings.lang
        if not app_env.test_env():
            emit_info('Start initializing grammar checker...')
            self._threadpool.start(language_tool_setup_worker)

            QApplication.instance().installEventFilter(CapitalizationEventFilter(self))

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
            event.editor.textEdit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.wdgBottom.setVisible(True)
            self.sliderDocWidth.setMaximum(self.width() / 3)
            if self.sliderDocWidth.value() <= 2:
                self.sliderDocWidth.setValue(self.sliderDocWidth.maximum() // 2)
            self.btnComments.setChecked(False)
            self._toggle_fullscreen(on=True)
        elif isinstance(event, ToggleOutlineViewTitle):
            self.wdgTitle.setVisible(event.visible)

    @overrides
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            if self.stackMainPanels.currentWidget() is self.pageDistractionFree:
                self._toggle_fullscreen(on=False)
        event.accept()

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.wdgBottom and event.type() == QEvent.Leave:
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
            self._toggle_manuscript_night_mode(self.btnNightMode.isChecked())
            QTimer.singleShot(10000, lambda: self.wdgBottom.setHidden(True))
        else:
            editor: ManuscriptTextEditor = self.wdgDistractionFreeEditor.layout().itemAt(0).widget()
            editor.textEdit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self._toggle_manuscript_focus(False)
            self._toggle_manuscript_night_mode(False)
            self.manuscript_view.restore_editor(editor)
            self.stackMainPanels.setCurrentWidget(self.pageManuscript)

    def _toggle_manuscript_focus(self, toggled: bool):
        if toggled:
            if self.btnNightMode.isChecked():
                self.btnNightMode.setChecked(False)
        editor: ManuscriptTextEditor = self.wdgDistractionFreeEditor.layout().itemAt(0).widget()
        editor.setHighlighterEnabled(toggled)

    def _toggle_manuscript_night_mode(self, toggled: bool):
        if toggled:
            if self.btnFocus.isChecked():
                self.btnFocus.setChecked(False)
        editor: ManuscriptTextEditor = self.wdgDistractionFreeEditor.layout().itemAt(0).widget()
        editor.setNightModeEnabled(toggled)

    @busy
    def _flush_end_fetch_novel(self):
        flush_or_fail()
        updated_novel = client.fetch_novel(self.novel.id)
        return updated_novel

    @busy
    def _init_views(self):
        self.buttonGroup.buttonToggled.connect(self._on_view_changed)

        if not self.novel:
            for btn in self.buttonGroup.buttons():
                btn.setHidden(True)
            return

        for btn in self.buttonGroup.buttons():
            btn.setVisible(True)

        self.outline_mode.setEnabled(True)
        self.manuscript_mode.setEnabled(True)
        self.reports_mode.setEnabled(True)

        self.novel_view = NovelView(self.novel)
        self.characters_view = CharactersView(self.novel)
        self.scenes_outline_view = ScenesOutlineView(self.novel)
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
            self.btnNovel.setChecked(True)

    def _on_view_changed(self, btn=None, checked: bool = True):
        if not checked:
            return

        title = None
        if self.btnNovel.isChecked():
            self.stackedWidget.setCurrentWidget(self.pageNovel)
            self.novel_view.activate()
        elif self.btnCharacters.isChecked():
            self.stackedWidget.setCurrentWidget(self.pageCharacters)
            title = self.characters_view.title if self.characters_view.can_show_title() else None
            self.characters_view.activate()
        elif self.btnScenes.isChecked():
            self.stackedWidget.setCurrentWidget(self.pageScenes)
            title = self.scenes_outline_view.title if self.scenes_outline_view.can_show_title() else None
            self.scenes_outline_view.activate()
        elif self.btnLocations.isChecked():
            self.stackedWidget.setCurrentWidget(self.pageLocations)
            title = self.locations_view.title
            self.locations_view.activate()
        elif self.btnNotes.isChecked():
            self.stackedWidget.setCurrentWidget(self.pageNotes)
            title = self.notes_view.title
            self.notes_view.activate()

        if title:
            clear_layout(self.wdgTitle.layout(), auto_delete=False)
            self.wdgTitle.layout().addWidget(title)
            self.wdgTitle.setVisible(True)
        else:
            self.wdgTitle.setHidden(True)

    def _init_menubar(self):
        self.menubar.setContextMenuPolicy(Qt.PreventContextMenu)
        if app_env.is_prod():
            self.menuFile.removeAction(self.actionRestart)
        else:
            self.actionRestart.setIcon(qtawesome.icon('mdi.restart'))
            self.actionRestart.triggered.connect(lambda: QApplication.instance().exit(EXIT_CODE_RESTART))

        self.actionAbout.triggered.connect(lambda: AboutDialog().exec())
        self.actionExport.setIcon(IconRegistry.export_icon())
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
        self.toolBar.setContextMenuPolicy(Qt.PreventContextMenu)
        if platform.is_mac():
            self.toolBar.setStyleSheet('font: 14px;')
        self.home_mode = QToolButton(self.toolBar)
        self.home_mode.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.home_mode.setText('Home')
        self.home_mode.setCheckable(True)
        self.home_mode.setIcon(IconRegistry.home_icon())

        self.outline_mode = QToolButton(self.toolBar)
        self.outline_mode.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.outline_mode.setText('Plan')
        self.outline_mode.setCheckable(True)
        self.outline_mode.setIcon(IconRegistry.decision_icon(color='black'))

        self.manuscript_mode = QToolButton(self.toolBar)
        self.manuscript_mode.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.manuscript_mode.setText('Write')
        self.manuscript_mode.setIcon(IconRegistry.edit_icon(color_on='darkBlue'))
        self.manuscript_mode.setCheckable(True)

        self.reports_mode = QToolButton(self.toolBar)
        self.reports_mode.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.reports_mode.setText('Analyze')
        self.reports_mode.setIcon(IconRegistry.reports_icon())
        self.reports_mode.setCheckable(True)

        self._mode_btn_group = QButtonGroup()
        self._mode_btn_group.addButton(self.home_mode)
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

        self.toolBar.addWidget(spacer(5))
        self.toolBar.addWidget(self.home_mode)
        self.toolBar.addWidget(spacer(5))
        self.toolBar.addSeparator()
        self.toolBar.addWidget(spacer(5))
        self.toolBar.addWidget(self.outline_mode)
        self.toolBar.addWidget(self.manuscript_mode)
        self.toolBar.addWidget(self.reports_mode)
        self.toolBar.addWidget(spacer())
        self.toolBar.addWidget(self.btnComments)

        self.wdgSidebar.setHidden(True)
        self.wdgDocs.setHidden(True)

        if self.novel:
            self.outline_mode.setChecked(True)
        else:
            self.home_mode.setChecked(True)
            self.outline_mode.setDisabled(True)
            self.manuscript_mode.setDisabled(True)
            self.reports_mode.setDisabled(True)

    def _panel_toggled(self):
        if self.home_mode.isChecked():
            self.stackMainPanels.setCurrentWidget(self.pageHome)
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
        self.home_mode.setChecked(True)
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

        self.outline_mode.setEnabled(True)
        self.manuscript_mode.setEnabled(True)
        self.reports_mode.setEnabled(True)

        self.repo.flush()
        event_dispatcher.clear()
        if self.novel:
            self._clear_novel_views()

        self.novel = client.fetch_novel(novel.id)
        acts_registry.set_novel(self.novel)
        dictionary.set_novel(self.novel)
        app_env.novel = self.novel

        if language_tool_proxy.is_set():
            language_tool_proxy.tool.language = self.novel.lang_settings.lang

        self._init_views()
        settings.set_last_novel_id(self.novel.id)
        self._register_events()

        self.outline_mode.setChecked(True)

    def _register_events(self):
        event_dispatcher.register(self, NovelReloadRequestedEvent)
        event_dispatcher.register(self, NovelDeletedEvent)
        event_dispatcher.register(self, NovelUpdatedEvent)
        event_dispatcher.register(self, OpenDistractionFreeMode)
        event_dispatcher.register(self, ToggleOutlineViewTitle)
        if self.novel and not self.novel.scenes:
            event_dispatcher.register(self, SceneChangedEvent)

    def _clear_novel_views(self):
        self.pageNovel.layout().removeWidget(self.novel_view.widget)
        gc(self.novel_view.widget)
        self.pageCharacters.layout().removeWidget(self.characters_view.widget)
        gc(self.characters_view.widget)
        self.pageScenes.layout().removeWidget(self.scenes_outline_view.widget)
        gc(self.scenes_outline_view.widget)
        self.pageNotes.layout().removeWidget(self.notes_view.widget)
        gc(self.notes_view.widget)
        self.pageComments.layout().removeWidget(self.comments_view.widget)
        gc(self.comments_view.widget)
        self.pageLocations.layout().removeWidget(self.locations_view.widget)
        gc(self.locations_view.widget)

        if self.pageManuscript.layout().count():
            self.pageManuscript.layout().removeWidget(self.manuscript_view.widget)
            self.manuscript_view.widget.deleteLater()
            self.manuscript_view = None

        self.outline_mode.setDisabled(True)
        self.manuscript_mode.setDisabled(True)
        self.reports_mode.setDisabled(True)

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
