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
import math
import pickle
from functools import partial
from typing import Optional, Tuple, List

import qtawesome
from PyQt5.QtCore import Qt, QRectF, QModelIndex, QRect, QPoint, QObject, QEvent, QBuffer, QIODevice, QSize, QMimeData, \
    QByteArray
from PyQt5.QtGui import QPixmap, QPainterPath, QPainter, QFont, QColor, QIcon, QDrag
from PyQt5.QtWidgets import QWidget, QSizePolicy, QColorDialog, QAbstractItemView, \
    QMenu, QAction, QAbstractButton, \
    QStackedWidget, QAbstractScrollArea, QLineEdit, QHeaderView, QScrollArea, QFrame
from fbs_runtime import platform
from overrides import overrides
from qthandy import opaque, hbox

from src.main.python.plotlyst.env import app_env


def rounded_pixmap(original: QPixmap) -> QPixmap:
    size = min(original.width(), original.height())

    rounded = QPixmap(size, size)
    rounded.fill(Qt.transparent)

    path = QPainterPath()
    path.addEllipse(QRectF(rounded.rect()))
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setClipPath(path)
    painter.fillRect(rounded.rect(), Qt.black)

    painter.drawPixmap(0, 0, original.width(), original.height(), original)
    painter.end()

    return rounded


def emoji_font(size: int = 13) -> QFont:
    if platform.is_mac():
        return QFont('Apple Color Emoji', size)
    if platform.is_windows():
        return QFont('Segoe UI Emoji', size)
    return QFont('Noto Emoji', size)


def show_color_picker(default_color: QColor = QColor('white')) -> QColor:
    if platform.is_linux():
        color: QColor = QColorDialog.getColor(QColor(default_color),
                                              options=QColorDialog.DontUseNativeDialog)
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


def action(text: str, icon: Optional[QIcon] = None, slot=None, parent=None, checkable: bool = False) -> QAction:
    _action = QAction(text)
    if icon:
        _action.setIcon(icon)
    if slot:
        _action.triggered.connect(slot)
    if parent:
        _action.setParent(parent)
    _action.setCheckable(checkable)

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

    def add_separator(self):
        self.menu.addSeparator()

    def add_section(self, text: str, icon: Optional[QIcon] = None):
        action = self.menu.addSection(text)
        if icon:
            action.setIcon(icon)

    def add_submenu(self, text: str, icon: Optional[QIcon] = None) -> QMenu:
        submenu = QMenu(text, self.menu)
        if icon:
            submenu.setIcon(icon)
        self.menu.addMenu(submenu)

        return submenu

    def popup(self):
        self.menu.popup(self._viewport.mapToGlobal(self.pos))


class OpacityEventFilter(QObject):

    def __init__(self, enterOpacity: float = 1.0, leaveOpacity: float = 0.4,
                 parent: QWidget = None, ignoreCheckedButton: bool = False):
        super(OpacityEventFilter, self).__init__(parent)
        self.enterOpacity = enterOpacity
        self.leaveOpacity = leaveOpacity
        self.ignoreCheckedButton = ignoreCheckedButton
        self._parent = parent
        if not ignoreCheckedButton or not self._checkedButton(parent):
            opaque(parent, leaveOpacity)
        if parent and isinstance(parent, QAbstractButton):
            parent.toggled.connect(self._btnToggled)

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if self.ignoreCheckedButton and self._checkedButton(watched) or not watched.isEnabled():
            return super(OpacityEventFilter, self).eventFilter(watched, event)
        if event.type() == QEvent.Enter:
            opaque(watched, self.enterOpacity)
        elif event.type() == QEvent.Leave:
            opaque(watched, self.leaveOpacity)

        return super(OpacityEventFilter, self).eventFilter(watched, event)

    def _checkedButton(self, obj: QObject) -> bool:
        return isinstance(obj, QAbstractButton) and obj.isChecked()

    def _btnToggled(self, toggled: bool):
        if toggled:
            opaque(self._parent, self.enterOpacity)
        else:
            opaque(self._parent, self.leaveOpacity)


class VisibilityToggleEventFilter(QObject):

    def __init__(self, target: QWidget, parent: QWidget = None, reverse: bool = False):
        super(VisibilityToggleEventFilter, self).__init__(parent)
        self.target = target
        self.reverse = reverse
        self.target.setHidden(True)
        self._frozen: bool = False

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if self._frozen:
            return super(VisibilityToggleEventFilter, self).eventFilter(watched, event)
        if event.type() == QEvent.Enter:
            self.target.setVisible(True if not self.reverse else False)
        elif event.type() == QEvent.Leave:
            self.target.setHidden(True if not self.reverse else False)

        return super(VisibilityToggleEventFilter, self).eventFilter(watched, event)

    def freeze(self):
        self._frozen = True

    def resume(self):
        self._frozen = False
        self.target.setHidden(True if not self.reverse else False)


class DisabledClickEventFilter(QObject):

    def __init__(self, slot, parent: QWidget = None):
        super(DisabledClickEventFilter, self).__init__(parent)
        self._slot = slot

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.MouseButtonRelease and not watched.isEnabled():
            self._slot()

        return super(DisabledClickEventFilter, self).eventFilter(watched, event)


class DragEventFilter(QObject):
    def __init__(self, watched, mimeType: str, dataFunc):
        super(DragEventFilter, self).__init__(watched)
        self._pressed: bool = False
        self.mimeType = mimeType
        self.dataFunc = dataFunc

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.MouseButtonPress:
            self._pressed = True
        elif event.type() == QEvent.MouseButtonRelease:
            self._pressed = False
        elif event.type() == QEvent.MouseMove and self._pressed:
            drag = QDrag(watched)
            pix = watched.grab()
            mimedata = QMimeData()
            mimedata.setData(self.mimeType, QByteArray(pickle.dumps(self.dataFunc(watched))))
            drag.setMimeData(mimedata)
            drag.setPixmap(pix)
            drag.setHotSpot(event.pos())
            drag.exec_()
        return super(DragEventFilter, self).eventFilter(watched, event)


def link_buttons_to_pages(stack: QStackedWidget, buttons: List[Tuple[QAbstractButton, QWidget]]):
    def _open(widget: QWidget, toggled: bool):
        if toggled:
            stack.setCurrentWidget(widget)

    for btn, wdg in buttons:
        btn.toggled.connect(partial(_open, wdg))


def link_editor_to_btn(editor: QWidget, btn: QAbstractButton):
    if isinstance(editor, QLineEdit):
        editor.textChanged.connect(lambda: btn.setEnabled((len(editor.text()) > 0)))


def scroll_to_top(scroll_area: QAbstractScrollArea):
    scroll_area.verticalScrollBar().setValue(0)


def hmax(widget: QWidget):
    vpol = widget.sizePolicy().verticalPolicy()
    widget.setSizePolicy(QSizePolicy.Maximum, vpol)


def spin(btn: QAbstractButton, color: str = 'black'):
    spin_icon = qtawesome.icon('fa5s.spinner', color=color,
                               animation=qtawesome.Spin(btn))
    btn.setIcon(spin_icon)


def icon_to_html_img(icon: QIcon, size: int = 20) -> str:
    if app_env.is_mac() and size > 15:
        size = size - 10
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    pixmap = icon.pixmap(QSize(size, size))
    pixmap.save(buffer, "PNG", quality=100)
    return f"<img src='data:image/png;base64, {bytes(buffer.data().toBase64()).decode()}'>"


def pointy(widget):
    widget.setCursor(Qt.PointingHandCursor)


def autoresize_col(view: QAbstractItemView, col: int):
    view.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)


def stretch_col(view: QAbstractItemView, col: int):
    view.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)


def scrolled(parent: QWidget, frameless: bool = False) -> Tuple[QScrollArea, QWidget]:
    scrollArea = QScrollArea(parent)
    scrollArea.setFocusPolicy(Qt.NoFocus)
    scrollArea.setWidgetResizable(True)

    widget = QWidget(scrollArea)
    scrollArea.setWidget(widget)
    if not parent.layout():
        hbox(parent, 0, 0)
    parent.layout().addWidget(scrollArea)

    if frameless:
        scrollArea.setFrameStyle(QFrame.NoFrame)

    return scrollArea, widget
