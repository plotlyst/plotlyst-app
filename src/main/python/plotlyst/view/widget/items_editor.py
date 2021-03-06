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

from PyQt5.QtCore import QModelIndex, Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QAbstractItemView
from qthandy import ask_confirmation

from src.main.python.plotlyst.core.domain import SelectionItem
from src.main.python.plotlyst.model.common import SelectionItemsModel
from src.main.python.plotlyst.view.common import show_color_picker, PopupMenuBuilder
from src.main.python.plotlyst.view.delegates import TextItemDelegate
from src.main.python.plotlyst.view.dialog.utility import IconSelectorDialog
from src.main.python.plotlyst.view.generated.items_editor_widget_ui import Ui_ItemsEditorWidget
from src.main.python.plotlyst.view.icons import IconRegistry


class ItemsEditorWidget(QWidget, Ui_ItemsEditorWidget):
    editRequested = pyqtSignal(SelectionItem)

    def __init__(self, parent=None):
        super(ItemsEditorWidget, self).__init__(parent)
        self.setupUi(self)
        self.model: Optional[SelectionItemsModel] = None

        self.bgColorFieldEnabled: bool = False
        self.askRemovalConfirmation: bool = False
        self.insertionEnabled: bool = False
        self.removeAllEnabled: bool = True
        self.inlineEditionEnabled: bool = True

        self.btnAdd.setIcon(IconRegistry.plus_icon())
        self.btnAdd.clicked.connect(self._add)

        self.btnEdit.clicked.connect(self._edit)
        self.btnEdit.setIcon(IconRegistry.edit_icon())
        self.btnEdit.setDisabled(True)

        self.btnRemove.clicked.connect(self._remove)
        self.btnRemove.setDisabled(True)
        self.btnRemove.setIcon(IconRegistry.minus_icon())

        self.tableView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableView.customContextMenuRequested.connect(self._contextMenu)

    def setModel(self, model: SelectionItemsModel):
        self.model = model
        self.tableView.setModel(self.model)
        self.tableView.selectionModel().selectionChanged.connect(self._item_selected)
        self.tableView.clicked.connect(self._item_clicked)
        self.tableView.setItemDelegate(TextItemDelegate())
        self.setBgColorFieldEnabled(self.bgColorFieldEnabled)

    def setAskRemovalConfirmation(self, ask: bool):
        self.askRemovalConfirmation = ask

    def setBgColorFieldEnabled(self, enabled: bool):
        self.bgColorFieldEnabled = enabled
        if self.bgColorFieldEnabled:
            self.tableView.showColumn(SelectionItemsModel.ColBgColor)
        else:
            self.tableView.hideColumn(SelectionItemsModel.ColBgColor)

    def setInlineEditionEnabled(self, enabled: bool):
        self.inlineEditionEnabled = enabled

        if self.inlineEditionEnabled:
            self.tableView.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.AnyKeyPressed)
        else:
            self.tableView.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.tableView.doubleClicked.connect(self._edit)

    def setAdditionEnabled(self, enabled: bool):
        self.btnAdd.setEnabled(enabled)
        self.btnAdd.setVisible(enabled)

    def setInsertionEnabled(self, enabled: bool):
        self.insertionEnabled = enabled

    def setRemoveAllEnabled(self, enabled: bool):
        self.removeAllEnabled = enabled
        self._item_selected()

    def refresh(self):
        self.model.modelReset.emit()
        self.btnEdit.setEnabled(False)
        self.btnRemove.setEnabled(False)

    def _add(self):
        row = self.model.add()
        if row == 0:
            self.tableView.scrollToTop()
        else:
            self.tableView.scrollToBottom()
        self._editAfterInsert(row)

    def _editAfterInsert(self, row: int):
        default_editable_col = self.model.defaultEditableColumn()
        if default_editable_col >= 0:
            index = self.model.index(row, default_editable_col)
            if self.inlineEditionEnabled:
                self.tableView.edit(index)
            else:
                self.editRequested.emit(self.model.item(index))

    def _insert(self, row: int):
        if row < 0:
            row = 0
        elif row >= self.model.rowCount():
            return self._add()

        self.model.insert(row)
        self._editAfterInsert(row)

    def _edit(self):
        indexes = self.tableView.selectedIndexes()
        if not indexes:
            return
        if self.inlineEditionEnabled:
            if self.model.columnIsEditable(indexes[0].column()):
                self.tableView.edit(indexes[0])
        else:
            self.editRequested.emit(self.model.item(indexes[0]))

    def _remove(self):
        indexes = self.tableView.selectedIndexes()
        if not indexes:
            return
        item: SelectionItem = self.model.item(indexes[0])
        if self.askRemovalConfirmation and not ask_confirmation(f'Are you sure you want to remove "{item.text}"?'):
            return
        self.model.remove(indexes[0])

        self.btnEdit.setDisabled(True)
        self.btnRemove.setDisabled(True)

    def _item_selected(self):
        selection = len(self.tableView.selectedIndexes()) > 0
        self.btnEdit.setEnabled(selection)
        if selection:
            if not self.removeAllEnabled and self.model.rowCount() == 1:
                self.btnRemove.setDisabled(True)
            else:
                self.btnRemove.setEnabled(selection)

    def _item_clicked(self, index: QModelIndex):
        if index.column() == SelectionItemsModel.ColIcon:
            result = IconSelectorDialog(self).display()
            if result:
                self.model.setData(index, (result[0], result[1].name()), role=Qt.DecorationRole)
        if index.column() == SelectionItemsModel.ColBgColor:
            color: QColor = show_color_picker()
            if color.isValid():
                self.model.setData(index, color.name(), role=Qt.BackgroundRole)
            self.tableView.clearSelection()

    def _contextMenu(self, pos: QPoint):
        if not self.insertionEnabled:
            return

        index = self.tableView.selectedIndexes()[0]

        builder = PopupMenuBuilder.from_widget_position(self.tableView, pos)
        builder.add_action('Insert before', IconRegistry.from_name('mdi6.arrow-up-right'),
                           lambda: self._insert(index.row()))
        builder.add_action('Insert after', IconRegistry.from_name('mdi6.arrow-down-right'),
                           lambda: self._insert(index.row() + 1))
        builder.popup()
