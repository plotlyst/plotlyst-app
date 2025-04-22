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
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QWidget, QApplication
from qthandy import hbox

from plotlyst.resources import resource_registry
from plotlyst.view.common import push_btn, label
from plotlyst.view.widget.display import PopupDialog


class AboutDialog(PopupDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.wdgBanner = QWidget()
        self.wdgBanner.setProperty('banner-bg', True)
        self.lblBanner = QLabel()
        self.lblBanner.setPixmap(QPixmap(resource_registry.banner))
        self.btnClose = push_btn(text='Close', properties=['confirm', 'cancel'])
        self.btnClose.clicked.connect(self.accept)
        hbox(self.wdgBanner).addWidget(self.lblBanner, alignment=Qt.AlignmentFlag.AlignCenter)

        version = QApplication.instance().applicationVersion()

        self.frame.layout().addWidget(self.wdgBanner)
        self.frame.layout().addWidget(label("Plotlyst is an indie software developed by Zsolt Kovari", h4=True))
        self.frame.layout().addWidget(label('Copyright (C) 2021-2025  Zsolt Kovari', description=True))
        self.frame.layout().addWidget(label(f'Version: {version}', description=True))
        self.frame.layout().addWidget(self.btnClose, alignment=Qt.AlignmentFlag.AlignRight)

    def display(self):
        self.exec()
