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
from datetime import datetime

from PyQt6.QtCore import Qt, QRect, QDate, QPoint
from PyQt6.QtGui import QPainter, QTextOption, QColor
from PyQt6.QtWidgets import QWidget, QCalendarWidget, QTableView
from overrides import overrides
from qthandy import flow, bold, underline, vbox, margins, hbox, spacer, incr_icon, incr_font
from qthandy.filter import OpacityEventFilter

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import Novel, DailyProductivity, SnapshotType
from plotlyst.env import app_env
from plotlyst.event.core import emit_event
from plotlyst.events import SocialSnapshotRequested
from plotlyst.service.productivity import find_daily_productivity
from plotlyst.view.common import label, scroll_area, tool_btn
from plotlyst.view.icons import IconRegistry
from plotlyst.view.report import AbstractReport
from plotlyst.view.widget.button import YearSelectorButton
from plotlyst.view.widget.display import icon_text, PremiumOverlayWidget

months = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December"
}


class ProductivityReport(AbstractReport, QWidget):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(novel, parent, setupUi=False)
        vbox(self, 0, 8)
        margins(self, bottom=15)

        self.btnSnapshot = tool_btn(IconRegistry.from_name('mdi.camera', 'grey'), 'Take a snapshot for social media',
                                    transparent_=True)
        incr_icon(self.btnSnapshot, 6)
        self.btnSnapshot.installEventFilter(OpacityEventFilter(self.btnSnapshot, leaveOpacity=0.7))
        self.btnSnapshot.clicked.connect(
            lambda: emit_event(novel, SocialSnapshotRequested(self, SnapshotType.Productivity)))
        self.btnSnapshot.setHidden(True)

        self.wdgCalendars = QWidget()
        flow(self.wdgCalendars, 5, 10)
        margins(self.wdgCalendars, left=15, right=15, top=15)

        self.btnYearSelector = YearSelectorButton()
        incr_font(self.btnYearSelector, 4)
        incr_icon(self.btnYearSelector, 2)

        self.wdgCategoriesScroll = scroll_area(False, False, True)
        self.wdgCategories = QWidget()
        self.wdgCategories.setProperty('relaxed-white-bg', True)
        self.wdgCategoriesScroll.setWidget(self.wdgCategories)
        hbox(self.wdgCategories, spacing=10)
        margins(self.wdgCategories, left=25, right=25)

        self.wdgCategories.layout().addWidget(spacer())
        for category in novel.productivity.categories:
            self.wdgCategories.layout().addWidget(
                icon_text('fa5s.circle', category.text, category.icon_color, opacity=0.7))

        self.wdgCategories.layout().addWidget(spacer())

        current_year = datetime.today().year
        for i in range(12):
            wdg = QWidget()
            vbox(wdg)
            calendar = ProductivityCalendar(novel.productivity)
            calendar.setCurrentPage(current_year, i + 1)
            wdg.layout().addWidget(label(months[i + 1], h5=True), alignment=Qt.AlignmentFlag.AlignCenter)
            wdg.layout().addWidget(calendar)
            self.wdgCalendars.layout().addWidget(wdg)

        self.layout().addWidget(self.btnSnapshot, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(label('Daily Productivity Report', h2=True), alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.btnYearSelector, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.wdgCategoriesScroll)
        self.layout().addWidget(self.wdgCalendars)

        if not app_env.profile().get('productivity', False):
            PremiumOverlayWidget(self, 'Daily Productivity Tracking',
                                 icon='mdi6.progress-star-four-points',
                                 alt_link='https://plotlyst.com/docs/')


def date_to_str(date: QDate) -> str:
    return date.toString(Qt.DateFormat.ISODate)


class ProductivityCalendar(QCalendarWidget):
    def __init__(self, productivity: DailyProductivity, parent=None):
        super().__init__(parent)
        self.productivity = productivity

        self.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.HorizontalHeaderFormat.NoHorizontalHeader)
        self.setNavigationBarVisible(False)
        self.setSelectionMode(QCalendarWidget.SelectionMode.SingleSelection)
        self.setFirstDayOfWeek(Qt.DayOfWeek.Monday)

        self.installEventFilter(self)

        widget = self.layout().itemAt(1).widget()
        if isinstance(widget, QTableView):
            widget.setStyleSheet(f'''
                    QTableView {{
                        selection-background-color: {RELAXED_WHITE_COLOR};
                    }}
                    ''')
            widget.horizontalHeader().setMinimumSectionSize(30)
            widget.verticalHeader().setMinimumSectionSize(30)

        today = QDate.currentDate()
        self.setMaximumDate(today)

        self.setDisabled(True)

    @overrides
    def paintCell(self, painter: QPainter, rect: QRect, date: QDate) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if date.month() == self.monthShown():
            option = QTextOption()
            option.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bold(painter, date == self.selectedDate())
            underline(painter, date == self.selectedDate())

            category = find_daily_productivity(self.productivity, date_to_str(date))
            if category:
                painter.setPen(QColor(RELAXED_WHITE_COLOR))
                color = QColor(category.icon_color)
                color.setAlpha(115)
                painter.setBrush(color)
                rad = rect.width() // 2 - 1

                painter.setOpacity(125)

                # IconRegistry.from_name('mdi.circle-slice-8', category.icon_color).paint(painter, rect)
                painter.drawEllipse(rect.center() + QPoint(1, 1), rad, rad)

                return

            if date > self.maximumDate():
                painter.setPen(QColor('#adb5bd'))
            # elif category:
            #     painter.setPen(QColor(RELAXED_WHITE_COLOR))
            elif date == self.maximumDate():
                painter.setPen(QColor('black'))
            else:
                painter.setPen(QColor('grey'))

            painter.drawText(rect.toRectF(), str(date.day()), option)
