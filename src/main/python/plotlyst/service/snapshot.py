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
import calendar
from functools import partial
from typing import Optional

from PyQt6.QtCore import Qt, QEvent, QObject, QRectF, QPointF
from PyQt6.QtGui import QGuiApplication, QPixmap, QPainter, QPaintEvent, QPainterPath, QRadialGradient, QColor
from PyQt6.QtWidgets import QWidget, QFileDialog, QButtonGroup
from overrides import overrides
from qthandy import vbox, clear_layout, transparent, vline, hbox, retain_when_hidden, italic, incr_font, margins, \
    vspacer, spacer

from plotlyst.common import RELAXED_WHITE_COLOR, PLOTLYST_MAIN_COLOR
from plotlyst.core.domain import SnapshotType, Novel, LayoutType
from plotlyst.env import app_env
from plotlyst.service.common import today_str
from plotlyst.service.manuscript import daily_overall_progress
from plotlyst.view.common import push_btn, frame, exclusive_buttons, label, columns, set_font, rows, qpainter
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.report.productivity import ProductivityCalendar
from plotlyst.view.widget.button import TopSelectorButton, SelectorToggleButton, YearSelectorButton, MonthSelectorButton
from plotlyst.view.widget.display import PopupDialog, PlotlystFooter, CopiedTextMessage, icon_text, \
    HighQualityPaintedIcon, SeparatorLineWithShadow
from plotlyst.view.widget.manuscript import ManuscriptProgressCalendar


class SnapshotCanvasEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.canvas = QWidget()

    def desc(self) -> str:
        return ''

    def hasDateSelector(self) -> bool:
        return False

    def setYear(self, year: int):
        pass

    def setMonth(self, month: int):
        pass

    def monthName(self) -> str:
        pass

    def exportedName(self) -> str:
        return "snapshot"


class ProductivitySnapshotEditor(SnapshotCanvasEditor):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel
        vbox(self.canvas)
        transparent(self.canvas)

        calendar = ProductivityCalendar(self.novel.productivity)
        self.canvas.layout().addWidget(calendar)


class WritingSnapshotLegend(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self, 0, 0)

        self.layout().addWidget(HighQualityPaintedIcon(IconRegistry.from_name('fa5.square', color='#BB90CE'), size=16))
        self.layout().addWidget(label('1+', description=True, decr_font_diff=2))
        self.layout().addWidget(HighQualityPaintedIcon(IconRegistry.from_name('fa5s.square', color='#EDE1F2'), size=16))
        self.layout().addWidget(label('450+', description=True, decr_font_diff=2))
        self.layout().addWidget(HighQualityPaintedIcon(IconRegistry.from_name('fa5s.square', color='#C8A4D7'), size=16))
        self.layout().addWidget(label('1500+ words', description=True, decr_font_diff=2))


class MonthlyWritingSnapshotEditor(SnapshotCanvasEditor):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel
        vbox(self.canvas, 4)
        margins(self.canvas, top=8)
        transparent(self.canvas)

        self.calendar = ManuscriptProgressCalendar(self.novel, limitSize=False)
        self.calendar.setDisabled(True)
        self.calendar.setNavigationBarVisible(False)
        self.lblTitle = label(calendar.month_name[self.calendar.monthShown()], h4=True, centered=True, wordWrap=True)
        set_font(self.lblTitle, app_env.serif_font())

        self.legend = WritingSnapshotLegend()
        margins(self.legend, top=10)

        self.canvas.layout().addWidget(self.lblTitle)
        self.canvas.layout().addWidget(SeparatorLineWithShadow())
        self.canvas.layout().addWidget(self.legend, alignment=Qt.AlignmentFlag.AlignCenter)
        self.canvas.layout().addWidget(self.calendar)
        self.canvas.layout().addWidget(PlotlystFooter(), alignment=Qt.AlignmentFlag.AlignLeft)

    @overrides
    def desc(self) -> str:
        return 'Capture an image of your monthly writing progress'

    @overrides
    def hasDateSelector(self) -> bool:
        return True

    @overrides
    def setYear(self, year: int):
        self.calendar.setCurrentPage(year, self.calendar.monthShown())

    @overrides
    def setMonth(self, month: int):
        self.calendar.setCurrentPage(self.calendar.yearShown(), month)
        self.lblTitle.setText(calendar.month_name[month])

    @overrides
    def monthName(self) -> str:
        return calendar.month_name[self.calendar.monthShown()]

    @overrides
    def exportedName(self) -> str:
        return f'monthly-progress-{self.monthName().lower()}'


class DailyWritingSnapshotEditor(SnapshotCanvasEditor):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel

        vbox(self.canvas, 4)
        margins(self.canvas, top=8)
        transparent(self.canvas)

        self.lblTitle = label(self.novel.title, h4=True, centered=True, wordWrap=True)
        set_font(self.lblTitle, app_env.serif_font())

        progress = daily_overall_progress(self.novel)
        if progress.added > progress.removed:
            sign = '+'
            action = 'written'
            number = progress.added - progress.removed
        else:
            sign = '-'
            action = 'removed'
            number = progress.removed - progress.added

        self.lblProgress = label(f'{sign}{number}', incr_font_diff=10, centered=True, color=PLOTLYST_MAIN_COLOR)
        self.lblWord = label(f'words {action}', incr_font_diff=3, centered=True, color='#495057')
        self.wdgWordDisplay = rows(0, 0)
        self.wdgWordDisplay.layout().addWidget(self.lblProgress)
        self.wdgWordDisplay.layout().addWidget(self.lblWord)
        margins(self.wdgWordDisplay, bottom=65)

        self.iconDay = HighQualityPaintedIcon(IconRegistry.from_name('mdi6.calendar-today', color='grey'), size=14)
        self.lblDay = label(today_str(), color='grey', decr_font_diff=2)

        self.canvas.layout().addWidget(self.lblTitle)
        self.canvas.layout().addWidget(SeparatorLineWithShadow())
        self.canvas.layout().addWidget(group(self.iconDay, self.lblDay, margin=0, spacing=1, margin_bottom=8),
                                       alignment=Qt.AlignmentFlag.AlignRight)
        self.canvas.layout().addWidget(vspacer())
        self.canvas.layout().addWidget(self.wdgWordDisplay)
        self.canvas.layout().addWidget(vspacer())
        self.canvas.layout().addWidget(PlotlystFooter(), alignment=Qt.AlignmentFlag.AlignLeft)

        self.canvas.installEventFilter(self)

    @overrides
    def desc(self) -> str:
        return 'Capture an image of your daily writing progress'

    @overrides
    def exportedName(self) -> str:
        return f'daily-progress-{today_str()}'

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if isinstance(event, QPaintEvent):
            painter = qpainter(self.canvas)

            rect: QRectF = self.canvas.rect().toRectF()
            corner_radius = 12

            path = QPainterPath()
            path.addRoundedRect(rect, corner_radius, corner_radius)

            radius = max(rect.width(), rect.height()) / 3
            gradient = QRadialGradient(rect.bottomRight() - QPointF(15, -25), radius)

            gradient.setColorAt(0.0, QColor(PLOTLYST_MAIN_COLOR))
            gradient.setColorAt(1.0, QColor(RELAXED_WHITE_COLOR))

            painter.fillPath(path, gradient)

        return super().eventFilter(watched, event)


class SocialSnapshotPopup(PopupDialog):
    def __init__(self, novel: Novel, snapshotType: SnapshotType = SnapshotType.MonthlyWriting, parent=None):
        super().__init__(parent, layoutType=LayoutType.HORIZONTAL)
        self.novel = novel
        self._exported_pixmap: Optional[QPixmap] = None
        self._snapshotType = snapshotType
        self._editor: Optional[SnapshotCanvasEditor] = None

        self.wdgNav = rows(frame_=True)
        self.wdgNav.setProperty('relaxed-white-bg', True)
        self.wdgNav.setProperty('large-rounded-on-left', True)
        self.wdgEditor = rows()
        self.frame.layout().addWidget(self.wdgNav)
        self.frame.layout().addWidget(self.wdgEditor)

        margins(self.frame, left=0, top=0, bottom=0)
        margins(self.wdgNav, top=10)
        margins(self.wdgEditor, top=15, bottom=15)

        self.frame.setProperty('muted-bg', True)
        self.frame.setProperty('white-bg', False)
        self.frame.layout().setSpacing(5)

        self.lblDesc = label('', description=True)

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
        self.wdgTop.layout().addWidget(label('Export image to: ', incr_font_diff=1))
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

        self.wdgRatios = columns()
        margins(self.wdgRatios, bottom=15)
        self.wdgRatios.layout().addWidget(spacer())
        self.wdgRatios.layout().addWidget(icon_text('mdi.aspect-ratio', 'Size ratio'))
        self.wdgRatios.layout().addWidget(self.btnRatio9_16)
        self.wdgRatios.layout().addWidget(self.btnRatio1_1)
        self.wdgRatios.layout().addWidget(spacer())
        self.wdgRatios.layout().addWidget(self.lblCopied)
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

        self.wdgEditor.layout().addWidget(self.lblDesc)
        self.wdgEditor.layout().addWidget(self.wdgTop, alignment=Qt.AlignmentFlag.AlignCenter)
        self.wdgEditor.layout().addWidget(self.wdgRatios)
        self.wdgEditor.layout().addWidget(self.wdgDateSelectors, alignment=Qt.AlignmentFlag.AlignCenter)
        self.wdgEditor.layout().addWidget(self.canvasContainer, alignment=Qt.AlignmentFlag.AlignCenter)
        self.wdgEditor.layout().addWidget(vspacer())
        self.wdgEditor.layout().addWidget(self.btnCancel, alignment=Qt.AlignmentFlag.AlignRight)

        self.btnGroupSelectors = QButtonGroup()
        self.__initSelectorBtn(SnapshotType.MonthlyWriting)
        self.__initSelectorBtn(SnapshotType.DailyWriting)
        self.wdgNav.layout().addWidget(vspacer())

    def display(self):
        self.exec()

    def _typeToggled(self, snapshotType: SnapshotType, toggled: bool):
        if not toggled:
            return
        clear_layout(self.canvasContainer)

        self._snapshotType = snapshotType

        if snapshotType == SnapshotType.Productivity:
            self._editor = ProductivitySnapshotEditor(self.novel)
            self.canvasContainer.layout().addWidget(self._editor.canvas)
        elif snapshotType == SnapshotType.MonthlyWriting:
            self._editor = MonthlyWritingSnapshotEditor(self.novel)
            self.canvasContainer.layout().addWidget(self._editor.canvas)
        elif snapshotType == SnapshotType.DailyWriting:
            self._editor = DailyWritingSnapshotEditor(self.novel)
            self.canvasContainer.layout().addWidget(self._editor.canvas)

        self.lblDesc.setText(self._editor.desc())
        self.wdgDateSelectors.setVisible(self._editor.hasDateSelector())

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

        self._typeToggled(self._snapshotType, True)

    def _yearSelected(self, year: int):
        self._editor.setYear(year)

    def _monthSelected(self, month: int):
        self._editor.setMonth(month)

    def _export(self):
        if self._exported_pixmap is None:
            return

        if self.btnClipboard.isChecked():
            clipboard = QGuiApplication.clipboard()
            clipboard.setPixmap(self._exported_pixmap)
            self.lblCopied.trigger()
        elif self.btnPng.isChecked():
            target_path, _ = QFileDialog.getSaveFileName(self, "Save PNG", f'{self._editor.exportedName()}.png',
                                                         "PNG Files (*.png)")
            if target_path:
                self._exported_pixmap.save(target_path, "PNG")
        elif self.btnJpg.isChecked():
            target_path, _ = QFileDialog.getSaveFileName(self, "Save JPG", f'{self._editor.exportedName()}.jpg',
                                                         "JPEG Files (*.jpg *.jpeg)")
            if target_path:
                self._exported_pixmap.save(target_path, "JPEG")

    def __initSelectorBtn(self, snapshotType: SnapshotType):
        btn = push_btn(IconRegistry.from_name(snapshotType.icon, color_on=RELAXED_WHITE_COLOR),
                       text=snapshotType.display_name, checkable=True,
                       properties=['main-side-nav'])
        self.btnGroupSelectors.addButton(btn)
        self.wdgNav.layout().addWidget(btn)
        btn.toggled.connect(partial(self._typeToggled, snapshotType))

        if self._snapshotType == snapshotType:
            btn.setChecked(True)
