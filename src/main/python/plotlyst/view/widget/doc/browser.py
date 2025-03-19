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
from functools import partial
from pathlib import Path
from typing import Set, Optional, Dict, Iterable

from PyQt6.QtCore import pyqtSignal, Qt, QMimeData, QPointF, QDir, QTimer
from PyQt6.QtWidgets import QFileDialog
from overrides import overrides
from qthandy import clear_layout, vspacer, translucent, gc
from qthandy.filter import DragEventFilter, DropEventFilter
from qtmenu import MenuWidget, ActionTooltipDisplayMode

from plotlyst.common import recursive
from plotlyst.core.domain import Document, Novel, DocumentType, Character, PremiseBuilder, Diagram, DiagramData
from plotlyst.env import app_env
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import fade_out_and_gc, action
from plotlyst.view.icons import IconRegistry, avatars
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.widget.characters import CharacterSelectorMenu
from plotlyst.view.widget.confirm import confirmed
from plotlyst.view.widget.display import PremiumMessagePopup
from plotlyst.view.widget.tree import TreeView, ContainerNode, TreeSettings


class DocumentAdditionMenu(MenuWidget):
    documentTriggered = pyqtSignal(Document)

    def __init__(self, novel: Novel, parent=None):
        super(DocumentAdditionMenu, self).__init__(parent)
        self._novel = novel

        self.addAction(action('Document', IconRegistry.document_edition_icon(), self._documentSelected))
        self.addAction(action('Mind map', IconRegistry.from_name('ri.mind-map'), self._mindmapSelected))
        self.addSeparator()
        self.addAction(action('Link PDF', IconRegistry.from_name('fa5.file-pdf'), self._openPdf))
        self.addSeparator()

        self._character_menu = CharacterSelectorMenu(self._novel)
        self._character_menu.selected.connect(self._characterSelected)
        self._character_menu.setTitle('Characters')
        self._character_menu.setIcon(IconRegistry.character_icon())
        self.addMenu(self._character_menu)

        if app_env.profile().get('extra-docs', False):
            self.addSeparator()
            self._otherMenu = MenuWidget()
            self._otherMenu.setTooltipDisplayMode(ActionTooltipDisplayMode.DISPLAY_UNDER)
            self._otherMenu.setTitle('Other')
            self._otherMenu.addAction(action('Premise builder', IconRegistry.from_name('mdi.flower'),
                                             lambda: self._premiseSelected(),
                                             tooltip="Turn ideas into concepts, and develop a final premise"))

            self.addMenu(self._otherMenu)

        apply_white_menu(self)

    def _characterSelected(self, character: Character):
        self._documentSelected(character=character)
        self._character_menu.close()

    def _documentSelected(self, character: Optional[Character] = None):
        doc = Document('', type=DocumentType.DOCUMENT, icon='mdi.file-document')
        if character:
            doc.title = ''
            doc.character_id = character.id
        doc.loaded = True

        self.documentTriggered.emit(doc)

    def _mindmapSelected(self):
        if app_env.profile().get('mindmap', False):
            doc = Document('Mindmap', type=DocumentType.MIND_MAP, icon='ri.mind-map', diagram=Diagram(''))
            doc.diagram.data = DiagramData()
            doc.diagram.loaded = True
            self.documentTriggered.emit(doc)
        else:
            PremiumMessagePopup.popup('Mindmap', 'ri.mind-map', 'https://plotlyst.com/docs/characters/')

    def _premiseSelected(self):
        doc = Document('Premise', type=DocumentType.PREMISE, icon='mdi.flower')
        doc.data = PremiseBuilder()
        doc.data_id = doc.data.id
        doc.loaded = True
        self.documentTriggered.emit(doc)

    def _openPdf(self):
        filename, _ = QFileDialog.getOpenFileName(None, 'Open PDF', QDir.homePath(), 'PDF files (*.pdf)')
        if filename:
            title = Path(filename).stem
            title = title.capitalize().replace('_', ' ')
            doc = Document(title, type=DocumentType.PDF, icon='fa5.file-pdf', file=filename)
            self.documentTriggered.emit(doc)


class DocumentNode(ContainerNode):
    added = pyqtSignal(Document)

    def __init__(self, novel: Novel, doc: Document, parent=None, settings: Optional[TreeSettings] = None):
        super().__init__(doc.display_name(), parent, settings=settings)
        self._novel = novel
        self._doc = doc
        self.setTranslucentIconEnabled(True)

        if not self._doc.character_id:
            self._actionChangeIcon.setVisible(True)
            self._actionChangeTitle.setVisible(True)
        menu = DocumentAdditionMenu(self._novel, self._btnAdd)
        menu.documentTriggered.connect(self.added)
        self.refresh()

        if doc.type == DocumentType.MIND_MAP and not app_env.profile().get('mindmap'):
            self.setDisabled(True)

    def doc(self) -> Document:
        return self._doc

    def refresh(self):
        self._lblTitle.setText(self._doc.display_name())

        if self._doc.character_id:
            char = self._doc.character(self._novel)
            if char is not None:
                self._lblTitle.setText(char.name)
                self._icon.setIcon(avatars.avatar(char))
            self._icon.setVisible(True)
        elif self._doc.icon:
            self._icon.setIcon(IconRegistry.from_name(self._doc.icon, self._doc.icon_color))
            self._icon.setVisible(True)
        else:
            self._icon.setHidden(True)

    @overrides
    def _titleValue(self) -> str:
        return self._doc.title

    @overrides
    def _titleChanged(self, title: str):
        self._doc.title = title

    @overrides
    def _iconChanged(self, iconName: str, iconColor: str):
        self._doc.icon = iconName
        self._doc.icon_color = iconColor


class DocumentsTreeView(TreeView):
    DOC_MIME_TYPE: str = 'application/document'
    documentSelected = pyqtSignal(Document)
    documentDeleted = pyqtSignal(Document)
    documentIconChanged = pyqtSignal(Document)
    documentTitleChanged = pyqtSignal(Document)

    def __init__(self, parent=None, settings: Optional[TreeSettings] = None):
        super(DocumentsTreeView, self).__init__(parent)
        self._novel: Optional[Novel] = None
        self._settings = settings
        self._docs: Dict[Document, DocumentNode] = {}
        self._selectedDocuments: Set[Document] = set()

        self._dummyWdg: Optional[DocumentNode] = None
        self._toBeRemoved: Optional[DocumentNode] = None

        self._centralWidget.setProperty('bg', True)

        self.repo = RepositoryPersistenceManager.instance()

    def setSettings(self, settings: TreeSettings):
        self._settings = settings

    def setNovel(self, novel: Novel):
        self._novel = novel

        self.refresh()

    def addDocument(self, doc: Document):
        self._novel.documents.append(doc)
        wdg = self.__initDocWidget(doc)
        self._centralWidget.layout().insertWidget(self._centralWidget.layout().count() - 1, wdg)
        wdg.select()
        self._docSelectionChanged(wdg, wdg.isSelected())

        self._save()

    def documents(self) -> Iterable[Document]:
        return self._docs.keys()

    def refresh(self):
        def addChildWdg(parent: Document, child: Document):
            childWdg = self.__initDocWidget(child)
            self._docs[parent].addChild(childWdg)

        self.clearSelection()
        self._docs.clear()
        clear_layout(self._centralWidget)

        for doc in self._novel.documents:
            wdg = self.__initDocWidget(doc)
            self._centralWidget.layout().addWidget(wdg)
            recursive(doc, lambda parent: parent.children, addChildWdg)

        self._centralWidget.layout().addWidget(vspacer())

    def updateDocument(self, doc: Document):
        self._docs[doc].refresh()

    def clearSelection(self):
        for doc in self._selectedDocuments:
            self._docs[doc].deselect()
        self._selectedDocuments.clear()

    def _docSelectionChanged(self, wdg: DocumentNode, selected: bool):
        if selected:
            self.clearSelection()
            self._selectedDocuments.add(wdg.doc())
            QTimer.singleShot(10, lambda: self.documentSelected.emit(wdg.doc()))
        elif wdg.doc() in self._selectedDocuments:
            self._selectedDocuments.remove(wdg.doc())

    def _dragStarted(self, wdg: DocumentNode):
        wdg.setHidden(True)
        self._dummyWdg = DocumentNode(self._novel, wdg.doc(), settings=self._settings)
        self._dummyWdg.setPlusButtonEnabled(False)
        self._dummyWdg.setMenuEnabled(False)
        translucent(self._dummyWdg)
        self._dummyWdg.setHidden(True)
        self._dummyWdg.setParent(self._centralWidget)
        self._dummyWdg.setAcceptDrops(True)
        self._dummyWdg.installEventFilter(
            DropEventFilter(self._dummyWdg, [self.DOC_MIME_TYPE], droppedSlot=self._drop))

    def _dragStopped(self, wdg: DocumentNode):
        if self._dummyWdg:
            gc(self._dummyWdg)
            self._dummyWdg = None

        if self._toBeRemoved:
            gc(self._toBeRemoved)
            self._toBeRemoved = None
        else:
            wdg.setVisible(True)

    def _dragMovedOnDoc(self, wdg: DocumentNode, edge: Qt.Edge, point: QPointF):
        i = wdg.parent().layout().indexOf(wdg)
        if edge == Qt.Edge.TopEdge:
            wdg.parent().layout().insertWidget(i, self._dummyWdg)
        elif point.x() > 50:
            wdg.insertChild(0, self._dummyWdg)
        else:
            wdg.parent().layout().insertWidget(i + 1, self._dummyWdg)

        self._dummyWdg.setVisible(True)

    def _drop(self, mimeData: QMimeData):
        self.clearSelection()

        if self._dummyWdg.isHidden():
            return
        ref: Document = mimeData.reference()
        self._toBeRemoved = self._docs[ref]
        new_widget = self.__initDocWidget(ref)
        for child in self._toBeRemoved.childrenWidgets():
            new_widget.addChild(child)

        if self._dummyWdg.parent() is self._centralWidget:
            new_index = self._centralWidget.layout().indexOf(self._dummyWdg)
            if self._toBeRemoved.parent() is self._centralWidget:  # swap order on top
                old_index = self._centralWidget.layout().indexOf(self._toBeRemoved)
                self._novel.documents.remove(ref)
                if old_index < new_index:
                    self._novel.documents.insert(new_index - 1, ref)
                else:
                    self._novel.documents.insert(new_index, ref)
            else:
                self._removeFromParentDoc(ref, self._toBeRemoved)
                self._novel.documents.insert(new_index, ref)

            self._centralWidget.layout().insertWidget(new_index, new_widget)
        elif isinstance(self._dummyWdg.parent().parent(), DocumentNode):
            doc_parent_wdg: DocumentNode = self._dummyWdg.parent().parent()
            new_index = doc_parent_wdg.containerWidget().layout().indexOf(self._dummyWdg)
            if self._toBeRemoved.parent() is not self._centralWidget and \
                    self._toBeRemoved.parent().parent() is self._dummyWdg.parent().parent():  # swap under same parent doc
                old_index = doc_parent_wdg.indexOf(self._toBeRemoved)
                doc_parent_wdg.doc().children.remove(ref)
                if old_index < new_index:
                    doc_parent_wdg.doc().children.insert(new_index - 1, ref)
                else:
                    doc_parent_wdg.doc().children.insert(new_index, ref)
            else:
                self._removeFromParentDoc(ref, self._toBeRemoved)
                doc_parent_wdg.doc().children.insert(new_index, ref)

            doc_parent_wdg.insertChild(new_index, new_widget)

        self._dummyWdg.setHidden(True)
        self._save()

    def _addDoc(self, wdg: DocumentNode, newDoc: Document):
        newWdg = self.__initDocWidget(newDoc)
        wdg.addChild(newWdg)
        wdg.doc().children.append(newDoc)
        self._save()

    def _deleteDocWidget(self, wdg: DocumentNode):
        doc = wdg.doc()
        title = f'Are you sure you want to delete the document "{doc.title if doc.title else "Untitled"}"?'
        msg = 'This action cannot be undone, and the document and all its content will be lost.'
        if not confirmed(msg, title):
            return
        if doc in self._selectedDocuments:
            self._selectedDocuments.remove(doc)
        self._docs.pop(doc)

        fade_out_and_gc(wdg.parent(), wdg)

        self.repo.delete_doc(self._novel, doc)
        self.documentDeleted.emit(doc)

        self._removeFromParentDoc(doc, wdg)
        self._save()

    def _removeFromParentDoc(self, doc: Document, wdg: DocumentNode):
        if wdg.parent() is self._centralWidget:
            self._novel.documents.remove(doc)
        else:
            parent: DocumentNode = wdg.parent().parent()
            parent.doc().children.remove(doc)

    def _save(self):
        self.repo.update_novel(self._novel)

    def _iconChanged(self, doc: Document):
        self._save()
        self.documentIconChanged.emit(doc)

    def _titleChanged(self, doc: Document):
        self._save()
        self.documentTitleChanged.emit(doc)

    def __initDocWidget(self, doc: Document) -> DocumentNode:
        wdg = DocumentNode(self._novel, doc, settings=self._settings)
        wdg.selectionChanged.connect(partial(self._docSelectionChanged, wdg))
        wdg.deleted.connect(partial(self._deleteDocWidget, wdg))
        wdg.added.connect(partial(self._addDoc, wdg))
        wdg.iconChanged.connect(partial(self._iconChanged, doc))
        wdg.titleChanged.connect(partial(self._titleChanged, doc))
        wdg.installEventFilter(
            DragEventFilter(wdg, self.DOC_MIME_TYPE, dataFunc=lambda wdg: wdg.doc(),
                            grabbed=wdg.titleLabel(),
                            startedSlot=partial(self._dragStarted, wdg),
                            finishedSlot=partial(self._dragStopped, wdg)))
        wdg.titleWidget().setAcceptDrops(True)
        wdg.titleWidget().installEventFilter(
            DropEventFilter(wdg, [self.DOC_MIME_TYPE],
                            motionDetection=Qt.Orientation.Vertical,
                            motionSlot=partial(self._dragMovedOnDoc, wdg),
                            droppedSlot=self._drop
                            )
        )

        self._docs[doc] = wdg

        return wdg
