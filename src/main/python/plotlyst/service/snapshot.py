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
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication, QPixmap, QPainter
from PyQt6.QtWidgets import QWidget
from overrides import overrides
from qthandy import vbox, clear_layout, transparent

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import SnapshotType, Novel
from plotlyst.view.common import push_btn, frame
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.report.productivity import ProductivityCalendar
from plotlyst.view.widget.display import PopupDialog
from plotlyst.view.widget.manuscript import ManuscriptProgressCalendar


class SnapshotCanvasEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.canvas = QWidget()


class ProductivitySnapshotEditor(SnapshotCanvasEditor):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel
        vbox(self.canvas)
        transparent(self.canvas)

        calendar = ProductivityCalendar(self.novel.productivity)
        self.canvas.layout().addWidget(calendar)


class WritingSnapshotEditor(SnapshotCanvasEditor):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel
        vbox(self.canvas)
        transparent(self.canvas)

        calendar = ManuscriptProgressCalendar(self.novel)
        self.canvas.layout().addWidget(calendar)


class SocialSnapshotPopup(PopupDialog):
    def __init__(self, novel: Novel, snapshotType: Optional[SnapshotType] = None, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.frame.setProperty('bg', True)
        self.frame.setProperty('white-bg', False)

        self.canvasContainer = frame()
        self.canvasContainer.setProperty('white-bg', True)
        self.canvasContainer.setProperty('large-rounded', True)
        vbox(self.canvasContainer, 0, 0)
        # self.canvasContainer.setFixedSize(450, 450)
        self.canvasContainer.setFixedSize(200, 356)

        self.btnExport = push_btn(IconRegistry.from_name('fa5s.copy', RELAXED_WHITE_COLOR), text='Export',
                                  properties=['confirm', 'positive'])
        self.btnExport.clicked.connect(self._export)
        self.btnCancel = push_btn(text='Close', properties=['confirm', 'cancel'])
        self.btnCancel.clicked.connect(self.reject)

        self.frame.layout().addWidget(self.canvasContainer)
        self.frame.layout().addWidget(group(self.btnCancel, self.btnExport), alignment=Qt.AlignmentFlag.AlignRight)

        if snapshotType:
            self._selectType(snapshotType)

    def display(self):
        self.exec()

    def _selectType(self, snapshotType: SnapshotType):
        clear_layout(self.canvasContainer)

        if snapshotType == SnapshotType.Productivity:
            editor = ProductivitySnapshotEditor(self.novel)
            self.canvasContainer.layout().addWidget(editor.canvas)
        elif snapshotType == SnapshotType.Writing:
            editor = WritingSnapshotEditor(self.novel)
            self.canvasContainer.layout().addWidget(editor.canvas)

    @overrides
    def paintEvent(self, event):
        super().paintEvent(event)
        scale_factor = 4
        pixmap = QPixmap(self.canvasContainer.size() * scale_factor)

        painter = QPainter(pixmap)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing |
                               QPainter.RenderHint.TextAntialiasing |
                               QPainter.RenderHint.SmoothPixmapTransform)

        painter.scale(scale_factor, scale_factor)

        self.canvasContainer.render(painter)

        painter.end()

        self.exported_pixmap = pixmap

    def _export(self, scale_factor=3):
        if hasattr(self, 'exported_pixmap'):
            clipboard = QGuiApplication.clipboard()
            clipboard.setPixmap(self.exported_pixmap)
