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

from PyQt5.QtCore import QModelIndex, Qt, QSize
from PyQt5.QtWidgets import QHeaderView, QWidgetAction, QListView
from fbs_runtime import platform
from overrides import overrides
from qthandy import clear_layout

from src.main.python.plotlyst.core.client import json_client
from src.main.python.plotlyst.core.domain import Novel, Document, Character, DocumentType, \
    Causality, CausalityItem, MiceQuotient
from src.main.python.plotlyst.core.text import parse_structure_to_richtext
from src.main.python.plotlyst.events import SceneChangedEvent, SceneDeletedEvent
from src.main.python.plotlyst.model.characters_model import CharactersTableModel
from src.main.python.plotlyst.model.common import emit_column_changed_in_tree
from src.main.python.plotlyst.model.docs_model import DocumentsTreeModel, DocumentNode
from src.main.python.plotlyst.view._view import AbstractNovelView
from src.main.python.plotlyst.view.common import PopupMenuBuilder
from src.main.python.plotlyst.view.dialog.utility import IconSelectorDialog
from src.main.python.plotlyst.view.doc.mice import MiceQuotientDoc
from src.main.python.plotlyst.view.generated.notes_view_ui import Ui_NotesView
from src.main.python.plotlyst.view.icons import IconRegistry, avatars
from src.main.python.plotlyst.view.widget.causality import CauseAndEffectDiagram
from src.main.python.plotlyst.view.widget.input import DocumentTextEditor


class DocumentsView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel, [SceneChangedEvent, SceneDeletedEvent])
        self.ui = Ui_NotesView()
        self.ui.setupUi(self.widget)
        self._current_doc: Optional[Document] = None

        self.ui.splitter.setSizes([150, 500])

        self.model = DocumentsTreeModel(self.novel)
        self.ui.treeDocuments.setModel(self.model)
        self.ui.treeDocuments.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.ui.treeDocuments.setColumnWidth(DocumentsTreeModel.ColMenu, 20)
        self.ui.treeDocuments.setColumnWidth(DocumentsTreeModel.ColPlus, 24)
        self.ui.treeDocuments.clicked.connect(self._doc_clicked)
        self.ui.treeDocuments.expandAll()
        self.model.modelReset.connect(self.refresh)

        if platform.is_mac():
            self.ui.btnAdd.setIconSize(QSize(15, 15))

        self.textEditor: Optional[DocumentTextEditor] = None

        self.ui.btnAdd.setIcon(IconRegistry.plus_icon())
        self.ui.btnAdd.clicked.connect(self._add_doc)

    @overrides
    def refresh(self):
        self.ui.treeDocuments.expandAll()

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
            self.repo.update_doc(self.novel, doc)
        elif doc_type == DocumentType.MICE:
            doc.title = 'MICE Threads'
            doc.icon = 'mdi.rodent'
            doc.icon_color = '#6c757d'
            doc.data = MiceQuotient()
            doc.data_id = doc.data.id
            self.repo.update_doc(self.novel, doc)
        elif doc_type == DocumentType.STORY_STRUCTURE:
            doc.title = self.novel.active_story_structure.title
            doc.icon = self.novel.active_story_structure.icon
            doc.icon_color = self.novel.active_story_structure.icon_color

        doc.loaded = True

        if parent:
            index = self.model.insertDocUnder(doc, parent)
        else:
            index = self.model.insertDoc(doc)
        self.ui.treeDocuments.select(index)
        self._edit(index)

        if doc_type == DocumentType.STORY_STRUCTURE:
            self.textEditor.textEdit.insertHtml(parse_structure_to_richtext(self.novel.active_story_structure))
            self._save()

    def _doc_clicked(self, index: QModelIndex):
        if index.column() == 0:
            self._edit(index)
        elif index.column() == DocumentsTreeModel.ColMenu:
            self._show_menu_popup(index)
        elif index.column() == DocumentsTreeModel.ColPlus:
            self._show_docs_popup(index)

    def _init_text_editor(self):
        self._clear_text_editor()

        self.textEditor = DocumentTextEditor(self.ui.docEditorPage)
        self.ui.docEditorPage.layout().addWidget(self.textEditor)
        self.textEditor.textEdit.textChanged.connect(self._save)
        self.textEditor.textTitle.textChanged.connect(self._title_changed)

    def _clear_text_editor(self):
        clear_layout(self.ui.docEditorPage.layout())

    def _show_menu_popup(self, index: QModelIndex):
        builder = PopupMenuBuilder.from_index(self.ui.treeDocuments, index)
        builder.add_action('Edit icon', IconRegistry.icons_icon(), lambda: self._change_icon(index))
        builder.add_separator()
        builder.add_action('Delete', IconRegistry.minus_icon(), self._remove_doc)

        builder.popup()

    def _show_docs_popup(self, index: QModelIndex):
        def add_character(char_index: QModelIndex):
            char = char_index.data(CharactersTableModel.CharacterRole)
            self._add_doc(index, character=char)

        builder = PopupMenuBuilder.from_index(self.ui.treeDocuments, index)
        builder.add_action('Document', IconRegistry.document_edition_icon(), lambda: self._add_doc(index))

        character_menu = builder.add_submenu('Characters', IconRegistry.character_icon())
        _view = QListView()
        _view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        _view.clicked.connect(add_character)
        _view.setModel(CharactersTableModel(self.novel))
        action = QWidgetAction(character_menu)
        action.setDefaultWidget(_view)
        character_menu.addAction(action)

        builder.add_action('MICE threads', IconRegistry.from_name('mdi.rodent', '#6c757d'),
                           lambda: self._add_doc(index, doc_type=DocumentType.MICE))

        # builder.add_action('Reversed Cause and Effect', IconRegistry.reversed_cause_and_effect_icon(),
        #                    lambda: self._add_doc(index, doc_type=DocumentType.REVERSED_CAUSE_AND_EFFECT))
        # struc = self.novel.active_story_structure
        # builder.add_action(struc.title, IconRegistry.from_name(struc.icon, color=struc.icon_color),
        #                    lambda: self._add_doc(index, doc_type=DocumentType.STORY_STRUCTURE))

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
            self.textEditor.setGrammarCheckEnabled(False)
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
                self.textEditor.asyncCheckGrammer()
        else:
            self.ui.stackedEditor.setCurrentWidget(self.ui.customEditorPage)
            clear_layout(self.ui.customEditorPage)
            if self._current_doc.type == DocumentType.REVERSED_CAUSE_AND_EFFECT:
                widget = CauseAndEffectDiagram(self._current_doc.data, reversed_=True)
                widget.model.changed.connect(self._save)
            elif self._current_doc.type == DocumentType.MICE:
                widget = MiceQuotientDoc(self._current_doc, self._current_doc.data)
                widget.changed.connect(self._save)
            else:
                return
            self.ui.customEditorPage.layout().addWidget(widget)

    def _change_icon(self, index: QModelIndex):
        result = IconSelectorDialog().display()
        if result:
            node: DocumentNode = index.data(DocumentsTreeModel.NodeRole)
            node.document.icon = result[0]
            node.document.icon_color = result[1].name()
            self.repo.update_novel(self.novel)
            self.textEditor.setTitleIcon(IconRegistry.from_name(node.document.icon, node.document.icon_color))

    def _save(self):
        if not self._current_doc:
            return
        if self._current_doc.type in [DocumentType.DOCUMENT, DocumentType.STORY_STRUCTURE]:
            self._current_doc.content = self.textEditor.textEdit.toHtml()
        self.repo.update_doc(self.novel, self._current_doc)

    def _title_changed(self):
        if self._current_doc:
            new_title = self.textEditor.textTitle.text()
            if new_title and new_title != self._current_doc.title:
                self._current_doc.title = new_title
                emit_column_changed_in_tree(self.model, 0, QModelIndex())
                self.repo.update_novel(self.novel)
