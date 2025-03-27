"""
Plotlyst
Copyright (C) 2021-2025  Zsolt Kovari

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
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import QWidget
from qthandy import vbox, sp


class PdfView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self, 0, 0)

        self._view = QPdfView(self)
        self._view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self._view.setPageMode(QPdfView.PageMode.MultiPage)
        self.layout().addWidget(self._view)
        self._doc = QPdfDocument(self)
        self._view.setDocument(self._doc)

        sp(self._view).h_exp().v_exp()
        sp(self).h_exp().v_exp()

    def load(self, file_path: str):
        self._doc.load(file_path)
        self._view.pageNavigator()
        self._view.setZoomFactor(0.9)

    def closeDocument(self):
        self._doc.close()