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
from typing import List

from PyQt6.QtWidgets import QDialog

from src.main.python.plotlyst.core.domain import SelectionItem
from src.main.python.plotlyst.model.common import SelectionItemsModel
from src.main.python.plotlyst.view.generated.items_editor_dialog_ui import Ui_ItemsEditorDialog


class ItemsEditorDialog(QDialog, Ui_ItemsEditorDialog):
    def __init__(self, model: SelectionItemsModel, parent=None):
        super(ItemsEditorDialog, self).__init__(parent)
        self.setupUi(self)
        self.model = model
        self.wdgItemsEditor.setModel(self.model)

    def display(self, ) -> List[SelectionItem]:
        result = self.exec()
        if result == QDialog.DialogCode.Accepted:
            return self.model.items()
        return []
