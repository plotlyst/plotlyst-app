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
import os
from typing import Optional

import qtanim
from PyQt6.QtGui import QFont
from overrides import overrides
from qthandy import clear_layout, margins, bold, italic
from qttextedit.ops import TextEditorSettingsSection, FontSectionSettingWidget, FontSizeSectionSettingWidget, \
    TextWidthSectionSettingWidget

from plotlyst.core.client import json_client
from plotlyst.core.domain import Novel, Document, DocumentType, FontSettings
from plotlyst.env import app_env
from plotlyst.event.core import Event
from plotlyst.events import CharacterChangedEvent, CharacterDeletedEvent
from plotlyst.service.cache import entities_registry
from plotlyst.view._view import AbstractNovelView
from plotlyst.view.common import ButtonPressResizeEventFilter
from plotlyst.view.generated.notes_view_ui import Ui_NotesView
from plotlyst.view.icons import IconRegistry, avatars
from plotlyst.view.widget.doc.browser import DocumentAdditionMenu
from plotlyst.view.widget.doc.premise import PremiseBuilderWidget
from plotlyst.view.widget.input import DocumentTextEditor
from plotlyst.view.widget.pdf import PdfView
from plotlyst.view.widget.story_map import EventsMindMapView
from plotlyst.view.widget.tree import TreeSettings


class DocumentsView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel, [CharacterChangedEvent, CharacterDeletedEvent])
        self.ui = Ui_NotesView()
        self.ui.setupUi(self.widget)
        self._current_doc: Optional[Document] = None

        self.ui.btnDocuments.setIcon(IconRegistry.document_edition_icon())
        bold(self.ui.lblTitle)

        italic(self.ui.lblMissingFile)
        self.ui.btnMissingFile.setIcon(IconRegistry.from_name('mdi6.file-alert-outline'))
        bold(self.ui.lblMissingFileReference)
        italic(self.ui.lblMissingFileReference)

        self.ui.btnTreeToggle.setIcon(IconRegistry.from_name('mdi.file-tree-outline'))
        self.ui.btnTreeToggleSecondary.setIcon(IconRegistry.from_name('mdi.file-tree-outline'))
        self.ui.btnTreeToggleSecondary.setHidden(True)
        self.ui.btnTreeToggle.clicked.connect(self._hide_sidebar)
        self.ui.btnTreeToggleSecondary.clicked.connect(self._show_sidebar)

        self._mindmapView = EventsMindMapView(self.novel)
        self.ui.mindmapPage.layout().addWidget(self._mindmapView)

        self.ui.splitter.setSizes([150, 500])

        self.ui.treeDocuments.setSettings(TreeSettings(font_incr=2))
        self.ui.treeDocuments.setNovel(self.novel)
        self.ui.treeDocuments.documentSelected.connect(self._edit)
        self.ui.treeDocuments.documentDeleted.connect(self._clear_text_editor)
        self.ui.treeDocuments.documentIconChanged.connect(self._icon_changed)
        self.ui.treeDocuments.documentTitleChanged.connect(self._title_changed)

        self.textEditor: Optional[DocumentTextEditor] = None
        self.pdfView = PdfView(self.ui.pdfPage)
        self.ui.pdfPage.layout().addWidget(self.pdfView)

        self.ui.btnAdd.setIcon(IconRegistry.plus_icon('white'))
        self.ui.btnAdd.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnAdd))
        menu = DocumentAdditionMenu(self.novel, self.ui.btnAdd)
        menu.documentTriggered.connect(self._add_doc)

        self.ui.stackedEditor.setCurrentWidget(self.ui.emptyPage)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, CharacterChangedEvent):
            for doc in self.ui.treeDocuments.documents():
                if doc.character_id == event.character.id:
                    self.ui.treeDocuments.updateDocument(doc)
            if self._current_doc and self._current_doc.character_id == event.character.id:
                self.textEditor.setTitle(event.character.name)
                self.textEditor.setTitleIcon(avatars.avatar(event.character))
            return
        if isinstance(event, CharacterDeletedEvent):
            for doc in self.ui.treeDocuments.documents():
                if doc.character_id == event.character.id:
                    doc.reset_character()
                    doc.title = 'Character'
                    self.ui.treeDocuments.updateDocument(doc)

                    if self._current_doc == doc:
                        self.textEditor.setTitle(doc.title)
                        self.textEditor.setTitleIcon(IconRegistry.from_name(doc.icon))
                        self.textEditor.setTitleReadOnly(False)

                    self.repo.update_novel(self.novel)
            return

        super().event_received(event)

    @overrides
    def refresh(self):
        self.ui.treeDocuments.refresh()

    def _add_doc(self, doc: Document):
        self.ui.treeDocuments.addDocument(doc)

        if doc.type == DocumentType.PREMISE:
            self.repo.update_doc(self.novel, doc)

    def _init_text_editor(self):
        def settings_ready():
            self.textEditor.settingsWidget().setSectionVisible(TextEditorSettingsSection.TEXT_WIDTH, True)
            self.textEditor.settingsWidget().setSectionVisible(TextEditorSettingsSection.PAGE_WIDTH, False)
            fontSection: FontSectionSettingWidget = self.textEditor.settingsWidget().section(
                TextEditorSettingsSection.FONT)
            fontSection.fontSelected.connect(self._fontChanged)

            sizeSection: FontSizeSectionSettingWidget = self.textEditor.settingsWidget().section(
                TextEditorSettingsSection.FONT_SIZE)
            sizeSection.sizeChanged.connect(self._fontSizeChanged)

            widthSection: TextWidthSectionSettingWidget = self.textEditor.settingsWidget().section(
                TextEditorSettingsSection.TEXT_WIDTH)
            widthSection.widthChanged.connect(self._textWidthChanged)

        self._clear_text_editor()

        self.textEditor = DocumentTextEditor(self.ui.docEditorPage)
        self.textEditor.textEdit.setBlockPlaceholderEnabled(True)
        margins(self.textEditor, top=50, right=10)
        self.ui.docEditorPage.layout().addWidget(self.textEditor)

        if app_env.platform() in self.novel.prefs.docs.font.keys():
            font_: QFont = self.textEditor.textEdit.font()
            fontSettings = self._getFontSettings()
            if fontSettings.family:
                font_.setFamily(fontSettings.family)
            if fontSettings.font_size:
                font_.setPointSize(fontSettings.font_size)
            if fontSettings.text_width:
                self.textEditor.setCharacterWidth(fontSettings.text_width)
            else:
                self.textEditor.setCharacterWidth(70)

            self.textEditor.textEdit.setFont(font_)
        self.textEditor.textTitle.setPlaceholderText('Untitled')
        self.textEditor.textEdit.textChanged.connect(self._save)
        self.textEditor.titleChanged.connect(self._title_changed_in_editor)
        self.textEditor.iconChanged.connect(self._icon_changed_in_editor)
        self.textEditor.settingsAttached.connect(settings_ready)

    def _clear_text_editor(self):
        self.pdfView.closeDocument()
        clear_layout(self.ui.docEditorPage.layout())
        self.ui.stackedEditor.setCurrentWidget(self.ui.emptyPage)

    def _edit(self, doc: Document):
        self._current_doc = doc

        if self._current_doc.type in [DocumentType.DOCUMENT, DocumentType.STORY_STRUCTURE]:
            self._edit_document()
        elif self._current_doc.type == DocumentType.MIND_MAP:
            self._edit_mindmap()
        elif self._current_doc.type == DocumentType.PDF:
            self._edit_pdf()
        elif self._current_doc.type == DocumentType.PREMISE:
            self._edit_premise()

    def _edit_document(self):
        self._init_text_editor()
        if not self._current_doc.loaded:
            json_client.load_document(self.novel, self._current_doc)
        self.ui.stackedEditor.setCurrentWidget(self.ui.docEditorPage)
        self.textEditor.setGrammarCheckEnabled(False)

        char = entities_registry.character(str(self._current_doc.character_id))
        if char:
            self.textEditor.setText(self._current_doc.content, char.name, icon=avatars.avatar(char),
                                    title_read_only=True)
        else:
            if self._current_doc.icon:
                icon = IconRegistry.from_name(self._current_doc.icon, self._current_doc.icon_color)
            else:
                icon = None
            self.textEditor.setText(self._current_doc.content, self._current_doc.title, icon)

        if self.novel.prefs.docs.grammar_check:
            self.textEditor.setGrammarCheckEnabled(True)
            self.textEditor.asyncCheckGrammar()

    def _edit_pdf(self):
        self.pdfView.closeDocument()
        if os.path.exists(self._current_doc.file):
            self.pdfView.load(self._current_doc.file)
            self.ui.stackedEditor.setCurrentWidget(self.ui.pdfPage)
        else:
            self.ui.lblMissingFileReference.setText(self._current_doc.file)
            self.ui.stackedEditor.setCurrentWidget(self.ui.missingFilePage)

    def _edit_premise(self):
        clear_layout(self.ui.customEditorPage)

        if not self._current_doc.loaded:
            json_client.load_document(self.novel, self._current_doc)

        wdg = PremiseBuilderWidget(self._current_doc, self._current_doc.data)
        wdg.changed.connect(self._save)
        self.ui.customEditorPage.layout().addWidget(wdg)

        self.ui.stackedEditor.setCurrentWidget(self.ui.customEditorPage)

    def _edit_mindmap(self):
        clear_layout(self.ui.customEditorPage)

        self._mindmapView.resetZoom()
        self._mindmapView.setDiagram(self._current_doc.diagram)

        self.ui.stackedEditor.setCurrentWidget(self.ui.mindmapPage)

    def _icon_changed(self, doc: Document):
        if doc is self._current_doc and self._current_doc.type == DocumentType.DOCUMENT:
            self.textEditor.setTitleIcon(IconRegistry.from_name(doc.icon, doc.icon_color))

    def _icon_changed_in_editor(self, name: str, color: str):
        if self._current_doc:
            self._current_doc.icon = name
            self._current_doc.icon_color = color
            self.ui.treeDocuments.updateDocument(self._current_doc)
            self.repo.update_novel(self.novel)

    def _save(self):
        if not self._current_doc:
            return
        if self._current_doc.type in [DocumentType.DOCUMENT, DocumentType.STORY_STRUCTURE]:
            self._current_doc.content = self.textEditor.textEdit.toHtml()
        self.repo.update_doc(self.novel, self._current_doc)

    def _title_changed(self, doc: Document):
        if doc is self._current_doc and doc.type == DocumentType.DOCUMENT:
            self.textEditor.setTitle(doc.title)

    def _title_changed_in_editor(self, title: str):
        if self._current_doc:
            if title != self._current_doc.title:
                self._current_doc.title = title
                self.ui.treeDocuments.updateDocument(self._current_doc)
                self.repo.update_novel(self.novel)

    def _fontChanged(self, family: str):
        fontSettings = self._getFontSettings()
        fontSettings.family = family
        self.repo.update_novel(self.novel)

    def _fontSizeChanged(self, size: int):
        fontSettings = self._getFontSettings()
        fontSettings.font_size = size
        self.repo.update_novel(self.novel)

    def _textWidthChanged(self, width: int):
        fontSettings = self._getFontSettings()
        fontSettings.text_width = width
        self.repo.update_novel(self.novel)

    def _getFontSettings(self) -> FontSettings:
        if app_env.platform() not in self.novel.prefs.docs.font.keys():
            self.novel.prefs.docs.font[app_env.platform()] = FontSettings()
        return self.novel.prefs.docs.font[app_env.platform()]

    def _hide_sidebar(self):
        qtanim.toggle_expansion(self.ui.wdgDocs, False, teardown=lambda: qtanim.fade_in(self.ui.btnTreeToggleSecondary))
        self.ui.btnTreeToggleSecondary.setChecked(False)
        margins(self.ui.docEditorPage, left=40)
        margins(self.ui.customEditorPage, left=40)

    def _show_sidebar(self):
        qtanim.toggle_expansion(self.ui.wdgDocs, True)
        self.ui.btnTreeToggle.setChecked(True)
        self.ui.btnTreeToggleSecondary.setVisible(False)
        margins(self.ui.docEditorPage, left=0)
        margins(self.ui.customEditorPage, left=0)
