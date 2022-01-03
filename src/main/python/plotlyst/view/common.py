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
import functools
import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any

from PyQt6.QtCore import Qt, QRectF, QModelIndex, QRect, QPoint
from PyQt6.QtGui import QPixmap, QPainterPath, QPainter, QCursor, QFont, QColor, QIcon, QAction
from PyQt6.QtWidgets import QWidget, QApplication, QMessageBox, QSizePolicy, QFrame, QColorDialog, QAbstractItemView, \
    QMenu, QGraphicsOpacityEffect, QProxyStyle, QStyle, QStyleOption, QStyleHintReturn
from fbs_runtime import platform
from overrides import overrides


class EditorCommandType(Enum):
    UPDATE_SCENE_SEQUENCES = 5


@dataclass
class EditorCommand:
    type: EditorCommandType
    value: Optional[Any] = None

    @staticmethod
    def close_editor():
        return EditorCommand(EditorCommandType.CLOSE_CURRENT_EDITOR)

    @staticmethod
    def display_scenes():
        return EditorCommand(EditorCommandType.DISPLAY_SCENES)

    @staticmethod
    def display_characters():
        return EditorCommand(EditorCommandType.DISPLAY_CHARACTERS)


def rounded_pixmap(original: QPixmap) -> QPixmap:
    size = max(original.width(), original.height())

    rounded = QPixmap(size, size)
    rounded.fill(Qt.GlobalColor.transparent)
    path = QPainterPath()
    path.addEllipse(QRectF(rounded.rect()))
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setClipPath(path)
    painter.fillRect(rounded.rect(), Qt.GlobalColor.black)
    x = int((original.width() - size) / 2)
    y = int((original.height() - size) / 2)

    painter.drawPixmap(x, y, original.width(), original.height(), original)
    painter.end()

    return rounded


def ask_confirmation(message: str, parent: Optional[QWidget] = None) -> bool:
    """Raise a confirmation dialog. Return True if the user clicked Yes, False otherwise."""
    QApplication.setOverrideCursor(QCursor(Qt.CursorShape.ArrowCursor))
    status: int = QMessageBox.question(parent, 'Confirmation', message)
    QApplication.restoreOverrideCursor()
    if status & QMessageBox.StandardButton.Yes:
        return True
    return False


def spacer_widget(max_width: Optional[int] = None, vertical: bool = False) -> QWidget:
    spacer = QWidget()
    if vertical:
        spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
    else:
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    if max_width:
        spacer.setMaximumWidth(max_width)
    return spacer


def line(vertical: bool = False) -> QFrame:
    line = QFrame()
    if vertical:
        line.setFrameShape(QFrame.Shape.VLine)
    else:
        line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)

    return line


def busy(func):
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.BusyCursor))
        try:
            return func(*args, **kwargs)
        finally:
            QApplication.restoreOverrideCursor()

    return wrapper_timer


def emoji_font(size: int = 13) -> QFont:
    if platform.is_mac():
        return QFont('Apple Color Emoji', size)
    if platform.is_windows():
        return QFont('Segoe UI Emoji', size)
    return QFont('Noto Emoji', size)


def show_color_picker(default_color: QColor = QColor('white')) -> QColor:
    if platform.is_linux():
        color: QColor = QColorDialog.getColor(QColor(default_color),
                                              options=QColorDialog.ColorDialogOption.DontUseNativeDialog)
    else:
        color = QColorDialog.getColor(QColor(default_color))

    return color


def text_color_with_bg_color(bg_color: str) -> str:
    rgb = QColor(bg_color).getRgb()
    r = rgb[0]
    g = rgb[1]
    b = rgb[2]
    hsp = math.sqrt(0.299 * (r * r) + 0.587 * (g * g) + 0.114 * (b * b))
    return 'black' if hsp > 127.5 else 'white'


def action(text: str, icon: Optional[QIcon] = None, slot=None) -> QAction:
    _action = QAction(text)
    if icon:
        _action.setIcon(icon)
    if slot:
        _action.triggered.connect(slot)

    return _action


class PopupMenuBuilder:
    def __init__(self, parent: QWidget, viewport: QWidget, pos: QPoint):
        self._parent = parent
        self._viewport = viewport
        self.menu = QMenu(parent)
        self.pos = pos

    @staticmethod
    def from_index(view: QAbstractItemView, index: QModelIndex) -> 'PopupMenuBuilder':
        rect: QRect = view.visualRect(index)
        return PopupMenuBuilder(view, view.viewport(), QPoint(rect.x(), rect.y()))

    @staticmethod
    def from_widget_position(widget: QWidget, pos: QPoint) -> 'PopupMenuBuilder':
        return PopupMenuBuilder(widget, widget, pos)

    def add_action(self, text: str, icon: Optional[QIcon] = None, slot=None) -> QAction:
        _action = action(text, icon, slot)
        _action.setParent(self.menu)
        self.menu.addAction(_action)
        return _action

    def add_submenu(self, text: str, icon: Optional[QIcon] = None) -> QMenu:
        submenu = QMenu(text, self.menu)
        if icon:
            submenu.setIcon(icon)
        self.menu.addMenu(submenu)

        return submenu

    def popup(self):
        self.menu.popup(self._viewport.mapToGlobal(self.pos))


def retain_size_when_hidden(widget: QWidget):
    policy = widget.sizePolicy()
    policy.setRetainSizeWhenHidden(True)
    widget.setSizePolicy(policy)


def set_opacity(wdg: QWidget, opacity: float):
    op = QGraphicsOpacityEffect(wdg)
    op.setOpacity(opacity)
    wdg.setGraphicsEffect(op)


class InstantTooltipStyle(QProxyStyle):
    @overrides
    def styleHint(self, hint: QStyle.StyleHint, option: Optional[QStyleOption] = None, widget: Optional[QWidget] = None,
                  returnData: Optional[QStyleHintReturn] = None) -> int:
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay or hint == QStyle.StyleHint.SH_ToolTip_FallAsleepDelay:
            return 0

        return super(InstantTooltipStyle, self).styleHint(hint, option, widget, returnData)
