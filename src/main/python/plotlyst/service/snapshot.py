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
from qthandy import vbox, clear_layout, transparent, vline, hbox, retain_when_hidden, italic, incr_font

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import SnapshotType, Novel
from plotlyst.view.common import push_btn, frame, exclusive_buttons, label, columns
from plotlyst.view.icons import IconRegistry
from plotlyst.view.report.productivity import ProductivityCalendar
from plotlyst.view.widget.button import TopSelectorButton, SelectorToggleButton, YearSelectorButton, MonthSelectorButton
from plotlyst.view.widget.display import PopupDialog, PlotlystFooter, CopiedTextMessage, icon_text
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

        self.calendar = ManuscriptProgressCalendar(self.novel, limitSize=False)
        self.calendar.setDisabled(True)
        self.calendar.setNavigationBarVisible(False)
        self.canvas.layout().addWidget(self.calendar)
        self.canvas.layout().addWidget(PlotlystFooter(), alignment=Qt.AlignmentFlag.AlignLeft)


class SocialSnapshotPopup(PopupDialog):
    def __init__(self, novel: Novel, snapshotType: Optional[SnapshotType] = None, parent=None):
        super().__init__(parent)
        self.novel = novel
        self._exported_pixmap: Optional[QPixmap] = None
        self._snapshotType = snapshotType
        self._editor: Optional[SnapshotCanvasEditor] = None

        self.frame.setProperty('muted-bg', True)
        self.frame.setProperty('white-bg', False)
        self.frame.layout().setSpacing(10)

        self.btnClipboard = TopSelectorButton('fa5.clipboard', 'Clipboard')
        self.btnPng = TopSelectorButton('mdi6.file-png-box', 'PNG')
        self.btnJpg = TopSelectorButton('mdi6.file-jpg-box', 'JPG')

        self._btnGroup = exclusive_buttons(self, self.btnClipboard, self.btnPng, self.btnJpg)
        self.btnExport = push_btn(text='Export', properties=['confirm', 'positive'])
        self.btnExport.clicked.connect(self._export)

        self._btnGroup.buttonToggled.connect(self._formatChanged)
        self.btnClipboard.setChecked(True)

        self.wdgTop = frame()
        self.wdgTop.setProperty('bg', True)
        self.wdgTop.setProperty('large-rounded', True)
        hbox(self.wdgTop, 10, 5)
        self.wdgTop.layout().addWidget(label('Export image to: ', h5=True))
        self.wdgTop.layout().addWidget(self.btnClipboard)
        self.wdgTop.layout().addWidget(self.btnPng)
        self.wdgTop.layout().addWidget(self.btnJpg)
        self.wdgTop.layout().addWidget(vline())
        self.wdgTop.layout().addWidget(self.btnExport)

        self.lblCopied = CopiedTextMessage()
        italic(self.lblCopied)
        retain_when_hidden(self.lblCopied)

        self.btnRatio9_16 = SelectorToggleButton(Qt.ToolButtonStyle.ToolButtonTextOnly, minWidth=60)
        self.btnRatio9_16.setText('9:16')
        incr_font(self.btnRatio9_16)
        self.btnRatio1_1 = SelectorToggleButton(Qt.ToolButtonStyle.ToolButtonTextOnly, minWidth=60)
        self.btnRatio1_1.setText('1:1')
        incr_font(self.btnRatio1_1)

        self.wdgRatios = QWidget()
        hbox(self.wdgRatios)
        self.wdgRatios.layout().addWidget(icon_text('mdi.aspect-ratio', 'Size ratio'))
        self.wdgRatios.layout().addWidget(self.btnRatio9_16)
        self.wdgRatios.layout().addWidget(self.btnRatio1_1)
        self._btnGroupRatios = exclusive_buttons(self, self.btnRatio9_16, self.btnRatio1_1)
        self.btnRatio9_16.setChecked(True)
        self._btnGroupRatios.buttonClicked.connect(self._ratioChanged)

        self.btnYearSelector = YearSelectorButton()
        self.btnYearSelector.selected.connect(self._yearSelected)
        self.btnMonthSelector = MonthSelectorButton()
        self.btnMonthSelector.selected.connect(self._monthSelected)
        self.wdgDateSelectors = columns()
        self.wdgDateSelectors.layout().addWidget(self.btnYearSelector)
        self.wdgDateSelectors.layout().addWidget(self.btnMonthSelector)

        self.canvasContainer = frame()
        self.canvasContainer.setProperty('white-bg', True)
        self.canvasContainer.setProperty('large-rounded', True)
        vbox(self.canvasContainer, 0, 0)
        # self.canvasContainer.setFixedSize(356, 356)
        self.canvasContainer.setFixedSize(200, 356)

        self.btnCancel = push_btn(icon=IconRegistry.from_name('ei.remove', 'grey'), text='Close',
                                  properties=['confirm', 'cancel'])
        self.btnCancel.clicked.connect(self.reject)

        self.frame.layout().addWidget(self.wdgTop, alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame.layout().addWidget(self.lblCopied, alignment=Qt.AlignmentFlag.AlignRight)
        self.frame.layout().addWidget(self.wdgRatios, alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame.layout().addWidget(self.wdgDateSelectors, alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame.layout().addWidget(self.canvasContainer, alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame.layout().addWidget(self.btnCancel, alignment=Qt.AlignmentFlag.AlignRight)

        if self._snapshotType:
            self._selectType(self._snapshotType)

    def display(self):
        self.exec()

    def _selectType(self, snapshotType: SnapshotType):
        clear_layout(self.canvasContainer)

        if snapshotType == SnapshotType.Productivity:
            self._editor = ProductivitySnapshotEditor(self.novel)
            self.canvasContainer.layout().addWidget(self._editor.canvas)
        elif snapshotType == SnapshotType.Writing:
            self._editor = WritingSnapshotEditor(self.novel)
            self.canvasContainer.layout().addWidget(self._editor.canvas)

    @overrides
    def paintEvent(self, event):
        super().paintEvent(event)
        scale_factor = 6
        pixmap = QPixmap(self.canvasContainer.size() * scale_factor)

        painter = QPainter(pixmap)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing |
                               QPainter.RenderHint.TextAntialiasing |
                               QPainter.RenderHint.SmoothPixmapTransform)

        painter.scale(scale_factor, scale_factor)

        self.canvasContainer.render(painter)

        painter.end()

        self._exported_pixmap = pixmap

    def _formatChanged(self):
        if self.btnClipboard.isChecked():
            self.btnExport.setIcon(IconRegistry.from_name('fa5s.copy', RELAXED_WHITE_COLOR))
        elif self.btnPng.isChecked():
            self.btnExport.setIcon(IconRegistry.from_name('mdi6.file-png-box', RELAXED_WHITE_COLOR))
        elif self.btnJpg.isChecked():
            self.btnExport.setIcon(IconRegistry.from_name('mdi6.file-jpg-box', RELAXED_WHITE_COLOR))

    def _ratioChanged(self):
        if self.btnRatio9_16.isChecked():
            self.canvasContainer.setFixedSize(200, 356)
        elif self.btnRatio1_1.isChecked():
            self.canvasContainer.setFixedSize(356, 356)

        self._selectType(self._snapshotType)

    def _yearSelected(self, year: int):
        self._editor.calendar.setCurrentPage(year, self._editor.calendar.monthShown())

    def _monthSelected(self, month: int):
        self._editor.calendar.setCurrentPage(self._editor.calendar.yearShown(), month)

    def _export(self):
        if self._exported_pixmap is None:
            return

        if self.btnClipboard.isChecked():
            clipboard = QGuiApplication.clipboard()
            clipboard.setPixmap(self._exported_pixmap)
            self.lblCopied.trigger()
