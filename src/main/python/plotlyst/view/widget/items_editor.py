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
from typing import Optional, List

from PyQt6.QtCore import QModelIndex, Qt, pyqtSignal, QPoint, QSortFilterProxyModel
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QAbstractItemView, QTableView, QDialog
from qthandy import vbox, spacer, hbox, vline
from qthandy.filter import OpacityEventFilter

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import SelectionItem
from plotlyst.model.common import SelectionItemsModel
from plotlyst.view.common import show_color_picker, PopupMenuBuilder, tool_btn, push_btn
from plotlyst.view.delegates import TextItemDelegate
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.confirm import confirmed
from plotlyst.view.widget.display import PopupDialog
from plotlyst.view.widget.utility import IconSelectorDialog


class ItemsEditorWidget(QWidget):
    editRequested = pyqtSignal(SelectionItem)

    def __init__(self, parent=None):
        super(ItemsEditorWidget, self).__init__(parent)
        self.model: Optional[SelectionItemsModel] = None
        self.proxy: Optional[QSortFilterProxyModel] = None

        self.bgColorFieldEnabled: bool = False
        self.askRemovalConfirmation: bool = False
        self.insertionEnabled: bool = False
        self.removeAllEnabled: bool = True
        self.inlineEditionEnabled: bool = True
        self.inlineAdditionEnabled: bool = True
        self.removalEnabled: bool = True
        self.iconEditionEnabled: bool = True

        vbox(self)
        self.toolbar = QWidget()
        hbox(self.toolbar, spacing=5)
        self.btnAdd = tool_btn(IconRegistry.plus_icon(), tooltip='Add new item', transparent_=True)
        self.btnAdd.clicked.connect(self._add)
        self.btnAdd.setShortcut('Ctrl+N')
        self.btnAdd.installEventFilter(OpacityEventFilter(self.btnAdd, 1.0, 0.7))

        self.btnEdit = tool_btn(IconRegistry.edit_icon(), tooltip='Edit selected item', transparent_=True)
        self.btnEdit.clicked.connect(self._edit)
        self.btnEdit.setDisabled(True)
        self.btnEdit.setShortcut(Qt.Key.Key_E)
        self.btnEdit.installEventFilter(OpacityEventFilter(self.btnEdit, 1.0, 0.7))

        self.btnRemove = tool_btn(IconRegistry.minus_icon(), tooltip='Remove selected item', transparent_=True)
        self.btnRemove.clicked.connect(self._remove)
        self.btnRemove.setDisabled(True)
        self.btnRemove.setShortcut(Qt.Key.Key_Delete)
        self.btnRemove.installEventFilter(OpacityEventFilter(self.btnRemove, 1.0, 0.7))

        self.toolbar.layout().addWidget(self.btnAdd)
        self.toolbar.layout().addWidget(self.btnEdit)
        self.toolbar.layout().addWidget(vline())
        self.toolbar.layout().addWidget(self.btnRemove)
        self.toolbar.layout().addWidget(spacer())

        self.tableView = QTableView()
        self.tableView.setShowGrid(False)
        self.tableView.horizontalHeader().setVisible(False)
        self.tableView.horizontalHeader().setDefaultSectionSize(24)
        self.tableView.horizontalHeader().setMinimumSectionSize(20)
        self.tableView.horizontalHeader().setStretchLastSection(True)
        self.tableView.verticalHeader().setVisible(False)
        self.tableView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tableView.customContextMenuRequested.connect(self._contextMenu)

        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.tableView)

    def setModel(self, model: SelectionItemsModel, proxy: Optional[QSortFilterProxyModel] = None):
        self.model = model
        self.proxy = proxy
        if proxy:
            self.tableView.setModel(proxy)
        else:
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
            self.tableView.setEditTriggers(
                QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.AnyKeyPressed)
        else:
            self.tableView.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.tableView.doubleClicked.connect(self._edit)

    def setInlineAdditionEnabled(self, enabled: bool):
        self.inlineAdditionEnabled = enabled

    def setIconEditionEnabled(self, enabled: bool):
        self.iconEditionEnabled = enabled

    def setAdditionEnabled(self, enabled: bool):
        self.btnAdd.setEnabled(enabled)
        self.btnAdd.setVisible(enabled)

    def setInsertionEnabled(self, enabled: bool):
        self.insertionEnabled = enabled

    def setRemoveEnabled(self, enabled: bool):
        self.removalEnabled = enabled
        self._item_selected()

    def setRemoveAllEnabled(self, enabled: bool):
        self.removeAllEnabled = enabled
        self._item_selected()

    def refresh(self):
        self.model.modelReset.emit()
        self.btnEdit.setEnabled(False)
        self.btnRemove.setEnabled(False)

    def _add(self):
        if not self.inlineAdditionEnabled:
            return
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
        index = self._selectedIndex()
        if not index:
            return
        if self.inlineEditionEnabled:
            if self.model.columnIsEditable(index.column()):
                self.tableView.edit(index)
        else:
            item = index.data(SelectionItemsModel.ItemRole)
            self.editRequested.emit(item)

    def _remove(self):
        index = self._selectedIndex()
        if not index:
            return
        item = index.data(SelectionItemsModel.ItemRole)
        if self.askRemovalConfirmation and not confirmed('This action cannot be undone.',
                                                         f'Are you sure you want to remove the element "{self._itemDisplayText(item)}"?'):
            return
        self.model.remove(index)

        self.btnEdit.setDisabled(True)
        self.btnRemove.setDisabled(True)

    def _item_selected(self):
        selection = len(self.tableView.selectedIndexes()) > 0
        self.btnEdit.setEnabled(selection)
        if selection and self.removalEnabled:
            if not self.removeAllEnabled and self.model.rowCount() == 1:
                self.btnRemove.setDisabled(True)
            else:
                self.btnRemove.setEnabled(selection)
        else:
            self.btnRemove.setEnabled(False)

    def _item_clicked(self, index: QModelIndex):
        if index.column() == SelectionItemsModel.ColIcon and self.iconEditionEnabled:
            result = IconSelectorDialog.popup()
            if result:
                self.model.setData(index, (result[0], result[1].name()), role=Qt.ItemDataRole.DecorationRole)
        if index.column() == SelectionItemsModel.ColBgColor:
            color: QColor = show_color_picker()
            if color.isValid():
                self.model.setData(index, color.name(), role=Qt.ItemDataRole.BackgroundRole)
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

    def _itemDisplayText(self, item: SelectionItem) -> str:
        return item.text

    def _selectedIndex(self) -> Optional[QModelIndex]:
        indexes = self.tableView.selectedIndexes()
        if not indexes:
            return

        if self.proxy:
            return self.proxy.mapToSource(indexes[0])
        else:
            return indexes[0]


class ItemsEditorPopup(PopupDialog):
    def __init__(self, model: SelectionItemsModel, parent=None):
        super().__init__(parent)
        self.model = model
        self.wdgItemsEditor = ItemsEditorWidget()
        self.wdgItemsEditor.setModel(self.model)
        self.wdgItemsEditor.tableView.setColumnHidden(SelectionItemsModel.ColIcon, True)
        self.wdgItemsEditor.setRemoveAllEnabled(False)
        self.wdgItemsEditor.setInsertionEnabled(True)
        self.wdgItemsEditor.setMinimumSize(300, 300)

        self.btnConfirm = push_btn(icon=IconRegistry.from_name('fa5s.check', RELAXED_WHITE_COLOR),
                                   text='Apply', properties=['confirm', 'positive'])
        self.btnConfirm.clicked.connect(self.accept)

        self.btnCancel = push_btn(text='Cancel', properties=['confirm', 'cancel'])
        self.btnCancel.clicked.connect(self.reject)

        self.frame.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)
        self.frame.layout().addWidget(self.wdgItemsEditor)
        self.frame.layout().addWidget(group(self.btnCancel, self.btnConfirm), alignment=Qt.AlignmentFlag.AlignRight)

    def display(self) -> List[SelectionItem]:
        result = self.exec()
        if result == QDialog.DialogCode.Accepted:
            return self.model.items()
        return []
