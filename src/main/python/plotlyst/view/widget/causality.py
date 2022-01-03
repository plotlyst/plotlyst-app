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

from PyQt6.QtWidgets import QWidget

from src.main.python.plotlyst.core.domain import Causality
from src.main.python.plotlyst.model.causality import CaualityTreeModel
from src.main.python.plotlyst.view.delegates import TextItemDelegate
from src.main.python.plotlyst.view.generated.cause_and_effect_editor_ui import Ui_CauseAndEffectEditor
from src.main.python.plotlyst.view.icons import IconRegistry


class CauseAndEffectDiagram(QWidget, Ui_CauseAndEffectEditor):

    def __init__(self, causality: Causality, reversed_: bool = False, parent=None):
        super(CauseAndEffectDiagram, self).__init__(parent)
        self.setupUi(self)
        self.causality: Causality = causality
        self.model = CaualityTreeModel(self.causality)
        self.treeView.setModel(self.model)
        self.treeView.setItemDelegate(TextItemDelegate())
        self.treeView.expandAll()
        self.treeView.selectionModel().selectionChanged.connect(self._selected)
        self.model.modelReset.connect(self.treeView.expandAll)

        if reversed_:
            self.btnAddChild.setIcon(IconRegistry.cause_icon())
            self.btnAddChild.setToolTip('Add cause')
        self.btnEdit.setIcon(IconRegistry.edit_icon())
        self.btnDelete.setIcon(IconRegistry.wrong_icon('black'))

        self.btnEdit.clicked.connect(lambda: self.treeView.edit(self.treeView.selectedIndexes()[0]))
        self.btnAddChild.clicked.connect(self._addChild)
        self.btnDelete.clicked.connect(self._delete)

    def _selected(self):
        selected = bool(self.treeView.selectedIndexes())
        self.btnAddChild.setEnabled(selected)
        self.btnEdit.setEnabled(selected)
        self.btnDelete.setEnabled(selected)

    def _addChild(self):
        index = self.treeView.selectedIndexes()[0]
        self.model.addChild(index, 'Cause')

    def _delete(self):
        index = self.treeView.selectedIndexes()[0]
        self.model.delete(index)
