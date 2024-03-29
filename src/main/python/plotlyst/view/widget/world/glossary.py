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
from typing import Optional, Any

import qtanim
from PyQt6.QtCore import pyqtSignal, Qt, QModelIndex
from PyQt6.QtWidgets import QWidget, QLineEdit, QTableView, QApplication, QDialog
from overrides import overrides
from qthandy import vbox, hbox, sp
from qthandy.filter import DisabledClickEventFilter

from plotlyst.common import IGNORE_CAPITALIZATION_PROPERTY
from plotlyst.core.domain import Novel, GlossaryItem
from plotlyst.core.template import SelectionItem
from plotlyst.model.common import SelectionItemsModel
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import push_btn
from plotlyst.view.widget.display import PopupDialog
from plotlyst.view.widget.input import AutoAdjustableTextEdit
from plotlyst.view.widget.items_editor import ItemsEditorWidget


class GlossaryModel(SelectionItemsModel):
    glossaryRemoved = pyqtSignal()

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._items = list(self._novel.world.glossary.values())

    @overrides
    def rowCount(self, parent: QModelIndex = None) -> int:
        return len(self._items)

    @overrides
    def columnCount(self, parent: QModelIndex = None) -> int:
        return 4

    @overrides
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.FontRole:
            font = QApplication.font()
            font.setPointSize(13)
            if index.column() == self.ColName:
                font.setBold(True)
            return font
        if index.column() == self.ColName:
            if role == Qt.ItemDataRole.DisplayRole:
                return self._items[index.row()].key
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return Qt.AlignmentFlag.AlignTop
        if index.column() == 3:
            if role == Qt.ItemDataRole.DisplayRole:
                return self._items[index.row()].text
        return super().data(index, role)

    def refresh(self):
        self._items = list(self._novel.world.glossary.values())
        self.modelReset.emit()

    @overrides
    def _newItem(self) -> QModelIndex:
        pass

    @overrides
    def _insertItem(self, row: int) -> QModelIndex:
        pass

    @overrides
    def item(self, index: QModelIndex) -> SelectionItem:
        return self._items[index.row()]

    @overrides
    def remove(self, index: QModelIndex):
        glossary = self._items[index.row()]
        self._novel.world.glossary.pop(glossary.key)
        self.refresh()
        self.glossaryRemoved.emit()


class GlossaryEditorDialog(PopupDialog):
    def __init__(self, glossary: Optional[GlossaryItem] = None, parent=None):
        super().__init__(parent)
        self._glossary = glossary

        self.lineKey = QLineEdit()
        self.lineKey.setProperty('white-bg', True)
        self.lineKey.setProperty('rounded', True)
        self.lineKey.setProperty(IGNORE_CAPITALIZATION_PROPERTY, True)
        self.lineKey.setPlaceholderText('Term')
        self.lineKey.textChanged.connect(self._keyChanged)

        self.textDefinition = AutoAdjustableTextEdit(height=150)
        self.textDefinition.setProperty('white-bg', True)
        self.textDefinition.setProperty('rounded', True)
        self.textDefinition.setPlaceholderText('Define term')

        self.wdgTitle = QWidget()
        hbox(self.wdgTitle)
        self.wdgTitle.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)

        self.btnConfirm = push_btn(text='Confirm', properties=['base', 'positive'])
        sp(self.btnConfirm).h_exp()
        self.btnConfirm.clicked.connect(self.accept)
        self.btnConfirm.setDisabled(True)
        self.btnConfirm.installEventFilter(
            DisabledClickEventFilter(self.btnConfirm, lambda: qtanim.shake(self.lineKey)))

        if self._glossary:
            self.lineKey.setText(self._glossary.key)
            self.textDefinition.setText(self._glossary.text)

        self.frame.layout().addWidget(self.wdgTitle)
        self.frame.layout().addWidget(self.lineKey)
        self.frame.layout().addWidget(self.textDefinition)
        self.frame.layout().addWidget(self.btnConfirm)

    def display(self) -> GlossaryItem:
        result = self.exec()

        if result == QDialog.DialogCode.Accepted:
            if self._glossary is None:
                self._glossary = GlossaryItem('')
            self._glossary.key = self.lineKey.text()
            self._glossary.text = self.textDefinition.toMarkdown().strip()

            return self._glossary

    def _keyChanged(self, key: str):
        self.btnConfirm.setEnabled(len(key) > 0)

    @classmethod
    def edit(cls, glossary: Optional[GlossaryItem] = None) -> Optional[GlossaryItem]:
        return cls.popup(glossary)


class WorldBuildingGlossaryEditor(QWidget):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        vbox(self)
        self.editor = ItemsEditorWidget()
        self.editor.setInlineEditionEnabled(False)
        self.editor.setInlineAdditionEnabled(False)
        self.editor.btnAdd.clicked.connect(self._addNew)
        self.editor.editRequested.connect(self._edit)
        self.glossaryModel = GlossaryModel(self._novel)
        self.editor.setModel(self.glossaryModel)
        self.editor.tableView.setColumnHidden(GlossaryModel.ColIcon, True)
        self.editor.tableView.setColumnWidth(GlossaryModel.ColName, 200)
        self.editor.tableView.setContentsMargins(10, 15, 10, 5)

        self.glossaryModel.modelReset.connect(self.editor.tableView.resizeRowsToContents)
        self.glossaryModel.glossaryRemoved.connect(self._save)

        self.editor.tableView.setStyleSheet('QTableView::item { border: 0px; padding: 5px; }')
        self.editor.tableView.resizeRowsToContents()
        self.editor.tableView.setAlternatingRowColors(True)
        self.editor.tableView.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

        self.layout().addWidget(self.editor)
        self.repo = RepositoryPersistenceManager.instance()

    def _addNew(self):
        glossary = GlossaryEditorDialog.edit()
        if glossary:
            self._updateGlossary(glossary)

    def _edit(self, item: GlossaryItem):
        edited_glossary = GlossaryEditorDialog.edit(item)
        if edited_glossary:
            self._novel.world.glossary.pop(item.key)
            self._updateGlossary(edited_glossary)

    def _updateGlossary(self, glossary: GlossaryItem):
        self._novel.world.glossary[glossary.key] = glossary
        self.glossaryModel.refresh()
        self._save()

    def _save(self):
        self.repo.update_world(self._novel)
