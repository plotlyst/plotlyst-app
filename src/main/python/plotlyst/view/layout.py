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
from typing import List, Optional

from PyQt6.QtCore import QRect, Qt, QSize, QPoint
from PyQt6.QtWidgets import QSizePolicy, QLayout, QLayoutItem
from overrides import overrides


# based on https://doc.qt.io/qt-5/qtwidgets-layouts-flowlayout-example.html
class FlowLayout(QLayout):
    def __init__(self, margin: int = -1, spacing: int = -1, parent=None):
        super().__init__(parent)
        self._items: List[QLayoutItem] = []
        self.setSpacing(spacing)
        if parent:
            self.setContentsMargins(margin, margin, margin, margin)

    @overrides
    def addItem(self, item: QLayoutItem):
        self._items.append(item)

    @overrides
    def count(self) -> int:
        return len(self._items)

    def clear(self):
        while self.count():
            item = self.takeAt(0)
            if item:
                item.widget().deleteLater()

    @overrides
    def itemAt(self, index: int) -> Optional[QLayoutItem]:
        if 0 <= index < self.count():
            return self._items[index]
        return None

    @overrides
    def takeAt(self, index: int) -> Optional[QLayoutItem]:
        if 0 <= index < self.count():
            return self._items.pop(index)
        return None

    @overrides
    def hasHeightForWidth(self) -> bool:
        return True

    @overrides
    def heightForWidth(self, width) -> int:
        return self._arrange(QRect(0, 0, width, 0), True)

    @overrides
    def setGeometry(self, rect: QRect):
        super(FlowLayout, self).setGeometry(rect)
        self._arrange(rect, False)

    @overrides
    def sizeHint(self) -> QSize:
        return self.minimumSize()

    @overrides
    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())

        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)

        return size

    def _arrange(self, rect: QRect, testOnly: bool) -> int:
        left, top, right, bottom = self.getContentsMargins()
        effectiveRect: QRect = rect.adjusted(left, top, -right, -bottom)
        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0

        for item in self._items:
            widget = item.widget()
            spaceX = self.spacing()
            if spaceX == -1:
                spaceX = widget.style().layoutSpacing(QSizePolicy.ControlType.PushButton,
                                                      QSizePolicy.ControlType.PushButton,
                                                      Qt.Orientation.Horizontal)
            spaceY = self.spacing()
            if spaceY == -1:
                spaceY = widget.style().layoutSpacing(QSizePolicy.ControlType.PushButton,
                                                      QSizePolicy.ControlType.PushButton,
                                                      Qt.Orientation.Vertical)

            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y() + bottom


def clear_layout(layout: QLayout):
    while layout.count():
        item = layout.takeAt(0)
        item.widget().deleteLater()
