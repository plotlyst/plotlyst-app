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
from datetime import datetime, timedelta
from typing import Optional

import qtanim
from PyQt6.QtCore import QPoint, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QColor, QMovie
from PyQt6.QtWidgets import QWidget, QButtonGroup, QToolButton, QFrame, QLabel
from overrides import overrides
from qthandy import vbox, hbox, pointy, line, incr_font, decr_font, spacer, bold, translucent, margins
from qthandy.filter import OpacityEventFilter
from qtmenu import MenuWidget

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, RELAXED_WHITE_COLOR
from plotlyst.core.domain import Novel, DailyProductivity, ProductivityType
from plotlyst.env import app_env
from plotlyst.resources import resource_registry
from plotlyst.service.productivity import find_daily_productivity, set_daily_productivity
from plotlyst.view.common import label, frame, ButtonPressResizeEventFilter, to_rgba_str
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import transparent_menu
from plotlyst.view.style.button import apply_button_palette_color
from plotlyst.view.widget.display import IconText, OverlayWidget, icon_text


class ProductivityTypeButton(QToolButton):
    def __init__(self, category: ProductivityType, parent=None):
        super().__init__(parent)
        self.category = category
        self.setIcon(IconRegistry.from_name(category.icon, 'grey', RELAXED_WHITE_COLOR))
        self.setCheckable(True)
        self.setText(category.text)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setIconSize(QSize(24, 24))
        self.setMinimumWidth(80)
        self.installEventFilter(ButtonPressResizeEventFilter(self))
        pointy(self)
        # self.installEventFilter(OpacityEventFilter(self, ignoreCheckedButton=True))
        if app_env.is_mac():
            incr_font(self)

        hover_bg = to_rgba_str(QColor(self.category.icon_color), 45)
        checked_bg = to_rgba_str(QColor(self.category.icon_color), 150)
        self.setStyleSheet(f'''
                            QToolButton {{
                                border: 1px hidden lightgrey;
                                border-radius: 10px;
                                padding: 2px;
                            }}
                            QToolButton:hover:!checked {{
                                background: {hover_bg};
                            }}
                            QToolButton:checked {{
                                background: {checked_bg};
                                color: {RELAXED_WHITE_COLOR};
                            }}
                            ''')

        self.toggled.connect(self._toggled)
        self.clicked.connect(self._clicked)

    def _toggled(self, toggled: bool):
        bold(self, toggled)

    def _clicked(self, checked: bool):
        if checked:
            color = QColor(self.category.icon_color)
            color.setAlpha(175)
            qtanim.glow(self, radius=8, color=color, reverseAnimation=False,
                        teardown=lambda: self.setGraphicsEffect(None))


class DayCircleButton(QToolButton):
    def __init__(self, day: str, parent=None):
        super().__init__(parent)
        self.setIcon(IconRegistry.from_name('fa5.circle', 'lightgrey'))
        self.setText(day)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setIconSize(QSize(32, 32))

        if not app_env.is_mac():
            decr_font(self)

        self.setStyleSheet(f'''
                            QToolButton {{
                                border: 1px hidden lightgrey;
                                color: grey;
                            }}
                            ''')

    def setCategory(self, category: ProductivityType):
        self.setIcon(IconRegistry.from_name('mdi.circle-slice-8', category.icon_color))

    def activateCategory(self, category: ProductivityType):
        self.setCategory(category)
        color = QColor(category.icon_color)
        color.setAlpha(175)
        qtanim.glow(self, color=color, radius=12, loop=2, duration=150)

    def setActive(self):
        bold(self)
        self.setIcon(IconRegistry.from_name('mdi.record-circle-outline', 'grey'))


class DaysDisplayWidget(QWidget):
    def __init__(self, productivity: DailyProductivity, parent=None):
        super().__init__(parent)
        vbox(self, 0, 0)
        margins(self, top=40)

        self.wdgDays = frame()
        self.wdgDays.setProperty('white-bg', True)
        self.wdgDays.setProperty('large-rounded', True)
        hbox(self.wdgDays)
        self.wdgDays.layout().addWidget(spacer())

        weekday_number = datetime.today().weekday()
        for i, day in enumerate(['M', 'T', 'W', 'T', 'F', 'S', 'S']):
            btn = DayCircleButton(day)
            if weekday_number == i:
                self._todayBtn = btn
                btn.setActive()

            if i <= weekday_number:
                days_ago = weekday_number - i
                past_date = (datetime.today() - timedelta(days=days_ago)).strftime('%Y-%m-%d')

                category = find_daily_productivity(productivity, past_date)
                if category:
                    btn.setCategory(category)
                if i < weekday_number:
                    translucent(btn)
            else:
                btn.setDisabled(True)
                translucent(btn)

            self.wdgDays.layout().addWidget(btn)
        self.wdgDays.layout().addWidget(spacer())
        self.layout().addWidget(self.wdgDays)

    def activateCategory(self, category: ProductivityType):
        self._todayBtn.activateCategory(category)


class ProductivityTrackingWidget(QFrame):
    categorySelected = pyqtSignal()

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel
        vbox(self, 15, 5)
        self.setProperty('bg', True)
        self.setProperty('large-rounded', True)

        self.wdgTypes = frame()
        self.wdgTypes.setProperty('white-bg', True)
        self.wdgTypes.setProperty('large-rounded', True)
        hbox(self.wdgTypes, 5, 8)
        self.btnGroup = QButtonGroup()
        self.btnGroup.buttonClicked.connect(self._categorySelected)

        today_category = find_daily_productivity(self.novel.productivity)
        for category in self.novel.productivity.categories:
            btn = ProductivityTypeButton(category)
            self.btnGroup.addButton(btn)
            self.wdgTypes.layout().addWidget(btn)
            if today_category and today_category is category:
                btn.setChecked(True)

        self.lblAnimation = QLabel(self)
        self.lblAnimation.setHidden(True)

        self.wdgDays = DaysDisplayWidget(self.novel.productivity)

        title = icon_text('mdi6.progress-star-four-points', 'Daily productivity tracker')
        incr_font(title, 3)
        # self.layout().addWidget(label('Daily productivity tracker', h5=True), alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(label('In which category did you make the most progress today?', description=True))
        self.layout().addWidget(line(color='lightgrey'))
        self.layout().addWidget(self.wdgTypes)
        self.layout().addWidget(self.wdgDays)

    @overrides
    def mousePressEvent(self, event: QMouseEvent) -> None:
        pass

    def _categorySelected(self):
        btn = self.btnGroup.checkedButton()
        self.lblAnimation.setGeometry(btn.pos().x(), 0, 200, 100)
        self.movie = QMovie(resource_registry.confetti_anim)
        self.movie.frameChanged.connect(self._checkAnimation)
        self.lblAnimation.setMovie(self.movie)
        self.lblAnimation.setVisible(True)
        self.movie.start()

        self.wdgDays.activateCategory(btn.category)
        set_daily_productivity(self.novel, btn.category)

        self.categorySelected.emit()

    def _checkAnimation(self, frame_number: int):
        if frame_number == self.movie.frameCount() - 1:
            self.movie.stop()
            self.lblAnimation.setHidden(True)


class ProductivityButton(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self, spacing=0)
        self._novel: Optional[Novel] = None
        self._trackerWdg: Optional[ProductivityTrackingWidget] = None
        self._overlay: Optional[OverlayWidget] = None

        self.icon = IconText()
        self.icon.setIcon(IconRegistry.from_name('mdi6.progress-star-four-points', color=PLOTLYST_SECONDARY_COLOR))
        self.icon.setText('Days:')
        apply_button_palette_color(self.icon, PLOTLYST_SECONDARY_COLOR)
        self.icon.clicked.connect(self._popup)

        self.streak = label('0', incr_font_diff=4, color=PLOTLYST_SECONDARY_COLOR)
        self.streak.setStyleSheet(f'''
            color: {PLOTLYST_SECONDARY_COLOR};
            font-family: {app_env.serif_font()};
            ''')

        self._menu = MenuWidget()
        transparent_menu(self._menu)
        self._menu.aboutToHide.connect(self._hide)

        self.layout().addWidget(self.icon)
        self.layout().addWidget(self.streak)

        pointy(self)
        self.installEventFilter(OpacityEventFilter(self, leaveOpacity=0.7))

    def setNovel(self, novel: Novel):
        self._novel = novel
        self._updateStreak()

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._popup()

    def _updateStreak(self):
        self.streak.setText(str(len(self._novel.productivity.progress.keys())))

    def _popup(self):
        self._menu.clear()
        self._trackerWdg = ProductivityTrackingWidget(self._novel)
        self._trackerWdg.categorySelected.connect(self._updateStreak)
        self._menu.addWidget(self._trackerWdg)

        self._overlay = OverlayWidget.getActiveWindowOverlay(alpha=75)
        self._overlay.show()

        self._menu.exec(self.mapToGlobal(QPoint(0, self.sizeHint().height() + 10)))

    def _hide(self):
        if self._overlay:
            self._overlay.hide()
            self._overlay = None
