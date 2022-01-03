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

from PyQt6.QtCore import QModelIndex, QRect, QPoint, Qt
from PyQt6.QtGui import QSyntaxHighlighter, QTextDocument, QTextCharFormat, QTextBlockUserData
from PyQt6.QtWidgets import QHeaderView, QMenu, QWidgetAction, QListView, QWidget
from language_tool_python import LanguageTool
from overrides import overrides

from src.main.python.plotlyst.core.client import json_client
from src.main.python.plotlyst.core.domain import Novel, Document, Character, DocumentType, \
    Causality, CausalityItem
from src.main.python.plotlyst.core.text import parse_structure_to_richtext
from src.main.python.plotlyst.events import SceneChangedEvent, SceneDeletedEvent
from src.main.python.plotlyst.model.characters_model import CharactersTableModel
from src.main.python.plotlyst.model.common import emit_column_changed_in_tree
from src.main.python.plotlyst.model.docs_model import DocumentsTreeModel, DocumentNode
from src.main.python.plotlyst.view._view import AbstractNovelView
from src.main.python.plotlyst.view.common import spacer_widget, PopupMenuBuilder
from src.main.python.plotlyst.view.dialog.utility import IconSelectorDialog
from src.main.python.plotlyst.view.generated.docs_sidebar_widget_ui import Ui_DocumentsSidebarWidget
from src.main.python.plotlyst.view.generated.notes_view_ui import Ui_NotesView
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.layout import clear_layout
from src.main.python.plotlyst.view.widget.causality import CauseAndEffectDiagram
from src.main.python.plotlyst.view.widget.input import RotatedButton, RichTextEditor


class DocumentsView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel, [SceneChangedEvent, SceneDeletedEvent])
        self.ui = Ui_NotesView()
        self.ui.setupUi(self.widget)
        self._current_doc: Optional[Document] = None
        self.language_tool: Optional[LanguageTool] = None

        self.model = DocumentsTreeModel(self.novel)
        self.ui.treeDocuments.setModel(self.model)
        self.ui.treeDocuments.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ui.treeDocuments.setColumnWidth(DocumentsTreeModel.ColMenu, 20)
        self.ui.treeDocuments.setColumnWidth(DocumentsTreeModel.ColPlus, 24)
        self.ui.treeDocuments.clicked.connect(self._doc_clicked)
        self.ui.treeDocuments.expandAll()
        self.model.modelReset.connect(self.refresh)

        self.textEditor: Optional[RichTextEditor] = None
        self.highlighter: Optional[GrammarHighlighter] = None

        self.ui.btnAdd.setIcon(IconRegistry.plus_icon())
        self.ui.btnAdd.clicked.connect(self._add_doc)
        self.ui.btnRemove.setIcon(IconRegistry.minus_icon())
        self.ui.btnRemove.clicked.connect(self._remove_doc)

    @overrides
    def refresh(self):
        self.ui.treeDocuments.expandAll()
        self.ui.btnRemove.setEnabled(False)

    def set_language_tool(self, tool: LanguageTool):
        self.language_tool = tool
        if self.highlighter:
            self.highlighter.setLanguageTool(self.language_tool)

    def _add_doc(self, parent: Optional[QModelIndex] = None, character: Optional[Character] = None,
                 doc_type: DocumentType = DocumentType.DOCUMENT):
        doc = Document('New Document', type=doc_type)
        if character:
            doc.title = ''
            doc.character_id = character.id
        if doc_type == DocumentType.CAUSE_AND_EFFECT or doc_type == DocumentType.REVERSED_CAUSE_AND_EFFECT:
            casuality = Causality(items=[CausalityItem('Story ending')])
            doc.data = casuality
            doc.data_id = casuality.id
            json_client.save_document(self.novel, doc)
        if doc_type == DocumentType.STORY_STRUCTURE:
            doc.title = self.novel.story_structure.title
            doc.icon = self.novel.story_structure.icon
            doc.icon_color = self.novel.story_structure.icon_color

        doc.loaded = True

        if parent:
            index = self.model.insertDocUnder(doc, parent)
        else:
            index = self.model.insertDoc(doc)
        self.ui.treeDocuments.select(index)
        self.ui.btnRemove.setEnabled(True)
        self._edit(index)

        if doc_type == DocumentType.STORY_STRUCTURE:
            self.textEditor.textEditor.insertHtml(parse_structure_to_richtext(self.novel.story_structure))
            self._save()

    def _doc_clicked(self, index: QModelIndex):
        self.ui.btnRemove.setEnabled(True)
        if index.column() == 0:
            self._edit(index)
        elif index.column() == DocumentsTreeModel.ColMenu:
            self._show_menu_popup(index)
        elif index.column() == DocumentsTreeModel.ColPlus:
            self._show_docs_popup(index)

    def _init_text_editor(self):
        self._clear_text_editor()

        self.textEditor = RichTextEditor(self.ui.docEditorPage)
        self.ui.docEditorPage.layout().addWidget(self.textEditor)
        self.textEditor.textEditor.textChanged.connect(self._save)
        self.textEditor.textTitle.textChanged.connect(self._title_changed)
        self.highlighter = GrammarHighlighter(self.textEditor.textEditor.document(), self.language_tool)

    def _clear_text_editor(self):
        clear_layout(self.ui.docEditorPage.layout())

    def _show_menu_popup(self, index: QModelIndex):
        rect: QRect = self.ui.treeDocuments.visualRect(index)
        menu = QMenu(self.ui.treeDocuments)
        menu.addAction(IconRegistry.icons_icon(), 'Edit icon', lambda: self._change_icon(index))

        menu.popup(self.ui.treeDocuments.viewport().mapToGlobal(QPoint(rect.x(), rect.y())))

    def _show_docs_popup(self, index: QModelIndex):
        def add_character(char_index: QModelIndex):
            char = char_index.data(CharactersTableModel.CharacterRole)
            self._add_doc(index, character=char)

        builder = PopupMenuBuilder.from_index(self.ui.treeDocuments, index)
        builder.add_action('Document', IconRegistry.document_edition_icon(), lambda: self._add_doc(index))

        character_menu = builder.add_submenu('Characters', IconRegistry.character_icon())
        _view = QListView()
        _view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        _view.clicked.connect(add_character)
        _view.setModel(CharactersTableModel(self.novel))
        action = QWidgetAction(character_menu)
        action.setDefaultWidget(_view)
        character_menu.addAction(action)

        builder.add_action('Reversed Cause and Effect', IconRegistry.reversed_cause_and_effect_icon(),
                           lambda: self._add_doc(index, doc_type=DocumentType.REVERSED_CAUSE_AND_EFFECT))
        struc = self.novel.story_structure
        builder.add_action(struc.title, IconRegistry.from_name(struc.icon, color=struc.icon_color),
                           lambda: self._add_doc(index, doc_type=DocumentType.STORY_STRUCTURE))

        builder.popup()

    def _remove_doc(self):
        selected = self.ui.treeDocuments.selectionModel().selectedIndexes()
        if not selected:
            return
        self.model.removeDoc(selected[0])
        self._clear_text_editor()

    def _edit(self, index: QModelIndex):
        self._init_text_editor()
        node: DocumentNode = index.data(DocumentsTreeModel.NodeRole)
        self._current_doc = node.document

        if not self._current_doc.loaded:
            json_client.load_document(self.novel, self._current_doc)

        char = node.document.character(self.novel)

        if self._current_doc.type in [DocumentType.DOCUMENT, DocumentType.STORY_STRUCTURE]:
            self.ui.stackedEditor.setCurrentWidget(self.ui.docEditorPage)
            if char:
                self.textEditor.setText(self._current_doc.content, char.name, title_read_only=True)
            else:
                self.textEditor.setText(self._current_doc.content, self._current_doc.title)
        else:
            self.ui.stackedEditor.setCurrentWidget(self.ui.customEditorPage)
            while self.ui.customEditorPage.layout().count():
                item = self.ui.customEditorPage.layout().takeAt(0)
                item.widget().deleteLater()
            if self._current_doc.type == DocumentType.REVERSED_CAUSE_AND_EFFECT:
                widget = CauseAndEffectDiagram(self._current_doc.data, reversed_=True)
                widget.model.changed.connect(self._save)
                self.ui.customEditorPage.layout().addWidget(widget)

    def _change_icon(self, index: QModelIndex):
        result = IconSelectorDialog().display()
        if result:
            node: DocumentNode = index.data(DocumentsTreeModel.NodeRole)
            node.document.icon = result[0]
            node.document.icon_color = result[1].name()
            self.repo.update_novel(self.novel)

    def _save(self):
        if not self._current_doc:
            return
        if self._current_doc.type in [DocumentType.DOCUMENT, DocumentType.STORY_STRUCTURE]:
            self._current_doc.content = self.textEditor.textEditor.toHtml()
        json_client.save_document(self.novel, self._current_doc)

    def _title_changed(self):
        if self._current_doc:
            new_title = self.textEditor.textTitle.toPlainText()
            if new_title and new_title != self._current_doc.title:
                self._current_doc.title = new_title
                emit_column_changed_in_tree(self.model, 0, QModelIndex())
                self.repo.update_novel(self.novel)


# partially based on https://gist.github.com/ssokolow/0e69b9bd9ca442163164c8a9756aa15f
class GrammarHighlighter(QSyntaxHighlighter):

    def __init__(self, document: QTextDocument, tool: Optional[LanguageTool] = None):
        super(GrammarHighlighter, self).__init__(document)
        self._misspelling_format = QTextCharFormat()
        self._misspelling_format.setUnderlineColor(Qt.GlobalColor.red)
        self._misspelling_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)

        self._style_format = QTextCharFormat()
        self._style_format.setUnderlineColor(Qt.GlobalColor.blue)
        self._style_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)

        self._formats_per_issue = {'misspelling': self._misspelling_format, 'style': self._style_format}

        self._language_tool: Optional[LanguageTool] = tool

    def setLanguageTool(self, tool: LanguageTool):
        self._language_tool = tool
        self.rehighlight()

    @overrides
    def highlightBlock(self, text: str) -> None:
        if self._language_tool:
            matches = self._language_tool.check(text)
            misspellings = []
            for m in matches:
                self.setFormat(m.offset, m.errorLength,
                               self._formats_per_issue.get(m.ruleIssueType, self._misspelling_format))
                misspellings.append((m.offset, m.errorLength, m.replacements))
            data = QTextBlockUserData()
            data.misspelled = misspellings
            self.setCurrentBlockUserData(data)


class DocumentsSidebar(QWidget, AbstractNovelView, Ui_DocumentsSidebarWidget):

    def __init__(self, novel: Novel, parent=None):
        super(DocumentsSidebar, self).__init__(parent)
        self.novel = novel
        self.setupUi(self)
        self._updateDocs()

    @overrides
    def refresh(self):
        self._updateDocs()

    def _updateDocs(self):
        while self.scrollAreaWidgetContents.layout().count():
            item = self.scrollAreaWidgetContents.layout().takeAt(0)
            item.widget().deleteLater()
        for doc in self.novel.documents:
            btn = RotatedButton()
            btn.setText(doc.title)
            self.scrollAreaWidgetContents.layout().addWidget(btn)
        self.scrollAreaWidgetContents.layout().addWidget(spacer_widget(vertical=True))
