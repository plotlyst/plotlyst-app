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

import qtawesome
from PyQt6.QtWidgets import QMessageBox


class ErrorMessageBox(QMessageBox):
    def __init__(self, msg: str, details: Optional[str] = None, warning: bool = False, parent=None):
        super().__init__(parent=parent)
        self.setText(msg)
        self.setWindowIcon(qtawesome.icon('fa5s.bomb'))

        if details:
            self.setDetailedText(details)
            for btn in self.buttons():
                if btn.text().startswith('Show Details'):
                    btn.click()

        if warning:
            self.setIcon(QMessageBox.Icon.Warning)
            self.setWindowTitle('Warning')
        else:
            self.setIcon(QMessageBox.Icon.Critical)
            self.setWindowTitle('Error')

    def display(self) -> int:
        return self.exec()
