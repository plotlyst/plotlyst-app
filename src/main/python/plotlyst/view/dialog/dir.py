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

import qtawesome
from PyQt6.QtWidgets import QDialog

from src.main.python.plotlyst.view.generated.directory_picker_dialog_ui import Ui_DirectoryPickerDialog


class DirectoryPickerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_DirectoryPickerDialog()
        self.ui.setupUi(self)
        self.ui.btnDir.setIcon(qtawesome.icon('fa5s.folder-open', color='white'))
        self.ui.btnDir.clicked.connect(self.accept)

    def display(self):
        self.exec()
