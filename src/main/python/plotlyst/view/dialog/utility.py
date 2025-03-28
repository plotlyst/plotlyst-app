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
from enum import Enum
from functools import partial
from typing import Optional

from PyQt6 import QtGui
from PyQt6.QtCore import Qt, QSize, QEvent, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QPainter
from PyQt6.QtWidgets import QDialog, QToolButton, QPushButton, QApplication, QWidget
from overrides import overrides
from qthandy import line, hbox, translucent, decr_icon

from plotlyst.common import PLOTLYST_TERTIARY_COLOR
from plotlyst.view.common import rounded_pixmap, calculate_resized_dimensions, label, push_btn, restyle, tool_btn
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.display import PopupDialog


class _AvatarButton(QToolButton):
    def __init__(self, pixmap: QPixmap, parent=None):
        super(_AvatarButton, self).__init__(parent)
        self.pixmap = pixmap
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._size = 128
        self.setIconSize(QSize(self._size, self._size))
        self.setIcon(QIcon(pixmap.scaled(self._size, self._size, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)))


class Corner(Enum):
    TopLeft = 0
    TopRight = 1
    BottomRight = 2
    BottomLeft = 3


class ImageCropDialog(PopupDialog):
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._pixmap = pixmap
        self.cropped = None
        self.lblPreview = label()
        self.lblImage = label()

        self._cropFrame = self.CropFrame(self.lblImage)
        w, h = calculate_resized_dimensions(pixmap.width(), pixmap.height(), max_size=300)
        self._cropFrame.setGeometry(1, 1, w - 2, h - 2)
        self._cropFrame.setFixedSize(min(w - 2, h - 2), min(w - 2, h - 2))
        self.scaled = pixmap.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)
        self.lblImage.setPixmap(self.scaled)

        wdgFrameColors = QWidget()
        hbox(wdgFrameColors, 0)
        for color in ['#d90429', '#3a5a40', '#0077b6', PLOTLYST_TERTIARY_COLOR]:
            btn = tool_btn(IconRegistry.from_name('mdi.crop-free', color=color), transparent_=True)
            translucent(btn, 0.7)
            decr_icon(btn, 4)
            btn.clicked.connect(partial(self._cropFrame.setColor, color))
            wdgFrameColors.layout().addWidget(btn)

        self.btnConfirm = push_btn(text='Confirm', properties=['confirm', 'positive'])
        self.btnConfirm.clicked.connect(self.accept)
        self.btnCancel = push_btn(text='Cancel', properties=['confirm', 'cancel'])
        self.btnCancel.clicked.connect(self.reject)

        self.frame.layout().addWidget(label('Crop image', h4=True), alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame.layout().addWidget(self.lblPreview, alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame.layout().addWidget(line())
        self.frame.layout().addWidget(wdgFrameColors, alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame.layout().addWidget(self.lblImage, alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame.layout().addWidget(group(self.btnCancel, self.btnConfirm), alignment=Qt.AlignmentFlag.AlignRight)

        self._cropFrame.cropped.connect(self._updatePreview)

    def display(self) -> Optional[QPixmap]:
        self._updatePreview()
        result = self.exec()
        if result == QDialog.DialogCode.Accepted:
            return self.cropped

    def _updatePreview(self):
        self.cropped = QPixmap(self._cropFrame.width(), self._cropFrame.height())

        painter = QPainter(self.cropped)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cropped_rect = self.scaled.rect()
        cropped_rect.setX(self._cropFrame.pos().x())
        cropped_rect.setY(self._cropFrame.pos().y())
        cropped_rect.setWidth(self.cropped.width())
        cropped_rect.setHeight(self.cropped.height())
        painter.drawPixmap(self.cropped.rect(), self.scaled, cropped_rect)
        painter.end()

        self.lblPreview.setPixmap(
            rounded_pixmap(self.cropped.scaled(128, 128, Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation)))

    class CropFrame(QPushButton):
        cropped = pyqtSignal()
        cornerRange: int = 15
        minSize: int = 20

        def __init__(self, parent):
            super().__init__(parent)
            self.setStyleSheet(f'QPushButton {{border: 3px dashed {PLOTLYST_TERTIARY_COLOR};}}')
            self.setMouseTracking(True)
            self._pressedPoint: Optional[QPoint] = None
            self._resizeCorner: Optional[Corner] = None
            self._originalSize: QRect = self.geometry()

        def setColor(self, color: str):
            self.setStyleSheet(f'QPushButton {{border: 3px dashed {color};}}')
            restyle(self)

        @overrides
        def enterEvent(self, event: QEvent) -> None:
            if not QApplication.overrideCursor():
                QApplication.setOverrideCursor(Qt.CursorShape.SizeAllCursor)

        @overrides
        def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
            if self._pressedPoint:
                x_diff = event.pos().x() - self._pressedPoint.x()
                y_diff = event.pos().y() - self._pressedPoint.y()
                parent_rect = self.parent().rect()

                if self._resizeCorner == Corner.TopLeft:
                    new_size = max(self.geometry().width() - x_diff, self.geometry().height() - y_diff)
                    new_size = max(new_size, self.minSize)
                    new_x = max(self.geometry().x() + (self.geometry().width() - new_size), 0)
                    new_y = max(self.geometry().y() + (self.geometry().height() - new_size), 0)
                    if new_x and new_y:
                        self.setGeometry(new_x, new_y, new_size, new_size)
                        self.setFixedSize(new_size, new_size)
                elif self._resizeCorner == Corner.TopRight:
                    new_size = max(self._originalSize.width() + x_diff, self.geometry().height() - y_diff)
                    new_size = max(new_size, self.minSize)
                    new_x = self.geometry().x()
                    new_y = max(self.geometry().y() + (self.geometry().height() - new_size), 0)
                    if new_y and new_x + new_size < parent_rect.width():
                        self.setGeometry(new_x, new_y, new_size, new_size)
                        self.setFixedSize(new_size, new_size)
                elif self._resizeCorner == Corner.BottomRight:
                    size_diff = min(self._originalSize.width() + x_diff, self._originalSize.height() + y_diff)
                    new_size = max(min(size_diff, parent_rect.right() - self.geometry().x(),
                                       parent_rect.bottom() - self.geometry().y()), self.minSize)
                    self.setFixedSize(new_size, new_size)
                elif self._resizeCorner == Corner.BottomLeft:
                    new_size = max(self.geometry().width() - x_diff, self._originalSize.height() + y_diff)
                    new_size = max(new_size, self.minSize)
                    new_x = max(self.geometry().x() + (self.geometry().width() - new_size), 0)
                    new_y = self.geometry().y()
                    if new_x and new_y:
                        self.setGeometry(new_x, new_y, new_size, new_size)
                        self.setFixedSize(new_size, new_size)
                else:
                    if self._xMovementAllowed(x_diff):
                        self.setGeometry(self.geometry().x() + x_diff, self.geometry().y(), self.width(), self.height())
                    if self._yMovementAllowed(y_diff):
                        self.setGeometry(self.geometry().x(), self.geometry().y() + y_diff, self.width(), self.height())

            else:
                self._resizeCorner = None
                if event.pos().x() < self.cornerRange and event.pos().y() < self.cornerRange:
                    self._resizeCorner = Corner.TopLeft
                    QApplication.changeOverrideCursor(Qt.CursorShape.SizeFDiagCursor)
                elif event.pos().x() > self.width() - self.cornerRange \
                        and event.pos().y() > self.height() - self.cornerRange:
                    self._resizeCorner = Corner.BottomRight
                    QApplication.changeOverrideCursor(Qt.CursorShape.SizeFDiagCursor)
                elif event.pos().x() > self.width() - self.cornerRange and event.pos().y() < self.cornerRange:
                    self._resizeCorner = Corner.TopRight
                    QApplication.changeOverrideCursor(Qt.CursorShape.SizeBDiagCursor)
                elif event.pos().x() < self.cornerRange and event.pos().y() > self.height() - self.cornerRange:
                    self._resizeCorner = Corner.BottomLeft
                    QApplication.changeOverrideCursor(Qt.CursorShape.SizeBDiagCursor)
                else:
                    QApplication.changeOverrideCursor(Qt.CursorShape.SizeAllCursor)

        def _xMovementAllowed(self, diff: int) -> bool:
            return 0 < self.geometry().x() + diff \
                and self.geometry().x() + diff + self.width() < self.parent().width()

        def _yMovementAllowed(self, diff: int) -> bool:
            return 0 < self.geometry().y() + diff \
                and self.geometry().y() + diff + self.height() < self.parent().height()

        @overrides
        def leaveEvent(self, event: QEvent) -> None:
            QApplication.restoreOverrideCursor()
            self._pressedPoint = None

        @overrides
        def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
            self._pressedPoint = event.pos()
            self._originalSize = self.geometry()

        @overrides
        def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
            self._pressedPoint = None
            self.cropped.emit()
