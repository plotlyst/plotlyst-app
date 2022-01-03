"""
MIT License

Copyright (c) 2019 Martin Fitzpatrick
              2021 Zsolt Kovari

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from overrides import overrides
from qtpy.QtCore import Qt, QRect, QPoint, QSize, QRectF, QPointF, QPropertyAnimation, QEasingCurve, \
    Property, QSequentialAnimationGroup
from qtpy.QtGui import QBrush, QColor, QPen, QPaintEvent, QPainter
from qtpy.QtWidgets import QCheckBox


class _Toggle(QCheckBox):
    # Based on https://github.com/pythonguis/python-qtwidgets
    _transparent_pen = QPen(Qt.GlobalColor.transparent)
    _light_grey_pen = QPen(Qt.lightGray)

    def __init__(self, parent=None, bar_color=Qt.GlobalColor.gray, checked_color="#00B0FF",
                 handle_color=Qt.GlobalColor.white):
        super().__init__(parent)
        self._bar_brush = QBrush(bar_color)
        self._bar_checked_brush = QBrush(QColor(checked_color).lighter())

        self._handle_brush = QBrush(handle_color)
        self._handle_checked_brush = QBrush(QColor(checked_color))

        self._handle_position: float = 0
        self._pulse_radius: float = 0

        self.setContentsMargins(8, 0, 8, 0)

        self.stateChanged.connect(self.handle_state_change)

    @overrides
    def sizeHint(self) -> QSize:
        return QSize(58, 45)

    @overrides
    def hitButton(self, pos: QPoint) -> bool:
        return self.contentsRect().contains(pos)

    @overrides
    def paintEvent(self, event: QPaintEvent):
        contRect = self.contentsRect()
        handleRadius = round(0.24 * contRect.height())

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(self._transparent_pen)
        barRect = QRectF(
            0, 0,
            contRect.width() - handleRadius, 0.40 * contRect.height()
        )
        barRect.moveCenter(contRect.center())
        rounding = barRect.height() / 2

        # the handle will move along this line
        trailLength = contRect.width() - 2 * handleRadius
        xPos = contRect.x() + handleRadius + trailLength * self._handle_position

        if self.isChecked():
            painter.setBrush(self._bar_checked_brush)
            painter.drawRoundedRect(barRect, rounding, rounding)
            painter.setBrush(self._handle_checked_brush)
        else:
            painter.setBrush(self._bar_brush)
            painter.drawRoundedRect(barRect, rounding, rounding)
            painter.setPen(self._light_grey_pen)
            painter.setBrush(self._handle_brush)

        painter.drawEllipse(
            QPointF(xPos, barRect.center().y()),
            handleRadius, handleRadius)

        painter.end()

    def handle_state_change(self, value):
        self._handle_position = 1 if value else 0

    @Property(float)
    def handle_position(self) -> float:
        return self._handle_position

    @handle_position.setter
    def handle_position(self, pos):
        self._handle_position = pos
        self.update()

    @Property(float)
    def pulse_radius(self) -> float:
        return self._pulse_radius

    @pulse_radius.setter
    def pulse_radius(self, pos):
        self._pulse_radius = pos
        self.update()


class AnimatedToggle(_Toggle):

    def __init__(self, *args, pulse_unchecked_color="#44999999",
                 pulse_checked_color="#4400B0EE", **kwargs):

        self._pulse_radius = 0

        super().__init__(*args, **kwargs)

        self.animation = QPropertyAnimation(self, b"handle_position", self)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation.setDuration(200)

        self.pulse_anim = QPropertyAnimation(self, b"pulse_radius", self)
        self.pulse_anim.setDuration(350)
        self.pulse_anim.setStartValue(10)
        self.pulse_anim.setEndValue(20)

        self.animations_group = QSequentialAnimationGroup()
        self.animations_group.addAnimation(self.animation)
        self.animations_group.addAnimation(self.pulse_anim)

        self._pulse_unchecked_animation = QBrush(QColor(pulse_unchecked_color))
        self._pulse_checked_animation = QBrush(QColor(pulse_checked_color))

    @overrides
    def handle_state_change(self, value):
        self.animations_group.stop()
        if value:
            self.animation.setEndValue(1)
        else:
            self.animation.setEndValue(0)
        self.animations_group.start()

    @overrides
    def paintEvent(self, event: QPaintEvent):
        contRect = self.contentsRect()
        handleRadius = round(0.24 * contRect.height())

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(self._transparent_pen)
        barRect = QRect(
            0, 0,
            contRect.width() - handleRadius, 0.40 * contRect.height()
        )
        barRect.moveCenter(contRect.center())
        rounding = barRect.height() / 2

        # the handle will move along this line
        trailLength = contRect.width() - 2 * handleRadius

        xPos = contRect.x() + handleRadius + trailLength * self._handle_position

        if self.pulse_anim.state() == QPropertyAnimation.Running:
            painter.setBrush(
                self._pulse_checked_animation if
                self.isChecked() else self._pulse_unchecked_animation)
            painter.drawEllipse(QPointF(xPos, barRect.center().y()),
                                self._pulse_radius, self._pulse_radius)

        if self.isChecked():
            painter.setBrush(self._bar_checked_brush)
            painter.drawRoundedRect(barRect, rounding, rounding)
            painter.setBrush(self._handle_checked_brush)
        else:
            painter.setBrush(self._bar_brush)
            painter.drawRoundedRect(barRect, rounding, rounding)
            painter.setPen(self._light_grey_pen)
            painter.setBrush(self._handle_brush)

        painter.drawEllipse(
            QPointF(xPos, barRect.center().y()),
            handleRadius, handleRadius)

        painter.end()
