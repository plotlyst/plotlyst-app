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
import math
import sys
from collections import Counter
from functools import partial
from typing import Optional, Tuple, List, Union
from uuid import UUID

import qtanim
import qtawesome
from PyQt6.QtCharts import QChart, QChartView
from PyQt6.QtCore import QRectF, QModelIndex, QRect, QPoint, QBuffer, QIODevice, QSize, QObject, QEvent, Qt, QTimer, \
    QUrl
from PyQt6.QtGui import QPixmap, QPainterPath, QPainter, QFont, QColor, QIcon, QAction, QDesktopServices
from PyQt6.QtWidgets import QWidget, QSizePolicy, QColorDialog, QAbstractItemView, \
    QMenu, QAbstractButton, \
    QStackedWidget, QAbstractScrollArea, QLineEdit, QHeaderView, QScrollArea, QFrame, QTabWidget, \
    QGraphicsDropShadowEffect, QTableView, QPushButton, QToolButton, QButtonGroup, QToolTip, QApplication, QMainWindow, \
    QLabel, QGraphicsObject, QTextEdit
from fbs_runtime import platform
from overrides import overrides
from qthandy import hbox, vbox, margins, gc, transparent, spacer, sp, pointy, incr_font, decr_font
from qthandy.filter import DisabledClickEventFilter

from plotlyst.common import WHITE_COLOR
from plotlyst.env import app_env
from plotlyst.settings import CHARACTER_INITIAL_AVATAR_COLOR_CODES
from plotlyst.view.stylesheet import APP_STYLESHEET


def rounded_pixmap(original: QPixmap) -> QPixmap:
    size = min(original.width(), original.height())

    rounded = QPixmap(size, size)
    rounded.fill(Qt.GlobalColor.transparent)

    path = QPainterPath()
    path.addEllipse(QRectF(rounded.rect()))
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setClipPath(path)
    painter.fillRect(rounded.rect(), Qt.GlobalColor.black)

    painter.drawPixmap(0, 0, original.width(), original.height(), original)
    painter.end()

    return rounded


def emoji_font() -> QFont:
    if platform.is_mac():
        return QFont('Apple Color Emoji', 16)
    if platform.is_windows():
        return QFont('Segoe UI Emoji', 14)
    return QFont('Noto Emoji', 18)


def show_color_picker(default_color: QColor = QColor('white')) -> QColor:
    if platform.is_linux():
        color: QColor = QColorDialog.getColor(QColor(default_color),
                                              options=QColorDialog.ColorDialogOption.DontUseNativeDialog)
    else:
        color = QColorDialog.getColor(QColor(default_color))

    return color


def text_color_with_bg_qcolor(color: QColor) -> str:
    return _text_color_with_rgb(color.red(), color.green(), color.blue())


def text_color_with_bg_color(bg_color: str) -> str:
    rgb = QColor(bg_color).getRgb()
    return _text_color_with_rgb(rgb[0], rgb[1], rgb[2])


def _text_color_with_rgb(r: int, g: int, b: int) -> str:
    hsp = math.sqrt(0.299 * (r * r) + 0.587 * (g * g) + 0.114 * (b * b))
    return 'black' if hsp > 171.5 else WHITE_COLOR


def stronger_color(hex_color: str, factor: float = 1.5) -> str:
    color = QColor(hex_color)
    h, s, v, a = color.getHsv()
    s = min(255, int(s * factor))  # Scale up the saturation but cap at 255
    v = max(0, int(v / factor))  # Darken the color
    color.setHsv(h, s, v, a)
    return color.name()


def action(text: str, icon: Optional[QIcon] = None, slot=None, parent=None, checkable: bool = False,
           tooltip: str = '', incr_font_: Optional[int] = None) -> QAction:
    _action = QAction(text)
    if icon:
        _action.setIcon(icon)
    if slot:
        _action.triggered.connect(slot)
    if parent:
        _action.setParent(parent)
    if incr_font_ is not None:
        incr_font(_action, incr_font_)
    _action.setCheckable(checkable)
    _action.setToolTip(tooltip)

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


class ButtonPressResizeEventFilter(QObject):
    def __init__(self, parent):
        super(ButtonPressResizeEventFilter, self).__init__(parent)
        self._originalSize: Optional[QSize] = None
        self._reducedSize: Optional[QSize] = None
        if isinstance(parent, (QPushButton, QToolButton)):
            if parent.menu():
                parent.menu().aboutToHide.connect(lambda: self._resetSize(parent))

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if isinstance(watched, QAbstractButton):
            if event.type() == QEvent.Type.MouseButtonPress and watched.isEnabled():
                if self._originalSize is None:
                    self._calculateSize(watched)
                watched.setIconSize(self._reducedSize)
            elif event.type() == QEvent.Type.MouseButtonRelease and watched.isEnabled():
                self._resetSize(watched)

        return super(ButtonPressResizeEventFilter, self).eventFilter(watched, event)

    def _calculateSize(self, watched):
        self._originalSize = watched.iconSize()
        self._reducedSize = watched.iconSize()
        self._reducedSize.setWidth(self._originalSize.width() - 1)
        self._reducedSize.setHeight(self._originalSize.height() - 1)

    def _resetSize(self, watched):
        if self._originalSize is None:
            self._calculateSize(watched)
        watched.setIconSize(self._originalSize)


class ButtonIconSwitchEventFilter(QObject):
    def __init__(self, parent: QAbstractButton, idleIcon: QIcon, activeIcon: QIcon):
        super().__init__(parent)
        self._idleIcon = idleIcon
        self._activeIcon = activeIcon
        parent.setIcon(self._idleIcon)

    @overrides
    def eventFilter(self, watched: QAbstractButton, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Enter:
            watched.setIcon(self._activeIcon)
        elif event.type() == QEvent.Type.Leave:
            watched.setIcon(self._idleIcon)
        return super().eventFilter(watched, event)


class MouseEventDelegate(QObject):
    def __init__(self, target, delegate):
        super().__init__(target)
        self._delegate = delegate

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress:
            self._delegate.mousePressEvent(event)
            return False
        elif event.type() == QEvent.Type.MouseButtonRelease:
            self._delegate.mouseReleaseEvent(event)
            return False
        elif event.type() == QEvent.Type.Enter:
            self._delegate.enterEvent(event)
        elif event.type() == QEvent.Type.Leave:
            self._delegate.leaveEvent(event)
        return super(MouseEventDelegate, self).eventFilter(watched, event)


class TooltipPositionEventFilter(QObject):
    def __init__(self, parent, tooltip_position=Qt.AlignmentFlag.AlignRight):
        super().__init__(parent)
        self._tooltip_position = tooltip_position

    @overrides
    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.ToolTip:
            # get the position of the widget's corner in global coordinates
            # if self.tooltip_position & Qt.AlignmentFlag.AlignLeft:
            #     pos: QPoint = watched.mapToGlobal(watched.rect().topLeft())
            #     metrics = QFontMetrics(QToolTip.font())
            # tooltip_pos = pos - (metrics.boundingRect(watched.tooltip()).height(), 0)
            # elif self.tooltip_position & Qt.AlignmentFlag.AlignRight:
            # pos = global_pos(watched)
            pos = watched.mapToGlobal(watched.rect().topRight())
            pos.setX(pos.x() + 10)
            # elif self.tooltip_position & Qt.AlignmentFlag.AlignTop:
            #     pos = watched.mapToGlobal(watched.rect().topLeft())
            #     pos = pos - (0, QToolTip.fontMetrics().height())
            # elif self.tooltip_position & Qt.AlignmentFlag.AlignBottom:
            #     pos = watched.mapToGlobal(watched.rect().bottomLeft())
            #     pos = pos + (0, 10)

            QToolTip.showText(pos, watched.toolTip(), watched)

            return True

        return super().eventFilter(watched, event)


def link_buttons_to_pages(stack: QStackedWidget, buttons: List[Tuple[QAbstractButton, QWidget]]):
    def _open(widget: QWidget, toggled: bool):
        if toggled:
            stack.setCurrentWidget(widget)

    for btn, wdg in buttons:
        btn.toggled.connect(partial(_open, wdg))


def link_editor_to_btn(editor: QWidget, btn: QAbstractButton, disabledShake: bool = False):
    if isinstance(editor, QLineEdit):
        editor.textChanged.connect(lambda: btn.setEnabled((len(editor.text()) > 0)))
    elif isinstance(editor, QTextEdit):
        editor.textChanged.connect(lambda: btn.setEnabled((len(editor.toPlainText()) > 0)))

    if disabledShake:
        # btn.installEventFilter(DisabledClickEventFilter(btn, slot=lambda: qtanim.shake(editor)))
        btn.installEventFilter(DisabledClickEventFilter(btn, lambda: qtanim.shake(editor)))


def scroll_to_top(scroll_area: QAbstractScrollArea):
    scroll_area.verticalScrollBar().setValue(0)


def scroll_to_bottom(scroll_area: QAbstractScrollArea):
    scroll_area.verticalScrollBar().setValue(scroll_area.verticalScrollBar().maximum())


def hmax(widget: QWidget):
    vpol = widget.sizePolicy().verticalPolicy()
    widget.setSizePolicy(QSizePolicy.Policy.Maximum, vpol)


def wrap(widget: QWidget, margin_left: int = 0, margin_top: int = 0, margin_right: int = 0,
         margin_bottom: int = 0) -> QWidget:
    parent = QWidget()
    vbox(parent, 0, 0).addWidget(widget)
    margins(parent, margin_left, margin_top, margin_right, margin_bottom)

    return parent


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


def restyle(widget: QWidget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def shadow(wdg: QWidget, offset: int = 2, radius: int = 0, color=Qt.GlobalColor.lightGray):
    effect = QGraphicsDropShadowEffect()
    if isinstance(wdg, QObject) and not isinstance(wdg, QGraphicsObject):
        effect.setParent(wdg)
    effect.setBlurRadius(radius)
    effect.setOffset(offset, offset)
    effect.setColor(color)
    wdg.setGraphicsEffect(effect)


def autoresize_col(view: QTableView, col: int):
    view.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)


def stretch_col(view: QTableView, col: int):
    view.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)


def scrolled(parent: QWidget, frameless: bool = False, h_on: bool = True, v_on: bool = True) -> Tuple[
    QScrollArea, QWidget]:
    """Usage: self._scrollarea, self._wdgCenter = scrolled(self)"""
    scrollArea = QScrollArea(parent)
    scrollArea.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    scrollArea.setWidgetResizable(True)
    if not h_on:
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    if not v_on:
        scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    widget = QWidget(scrollArea)
    scrollArea.setWidget(widget)
    if parent.layout() is None:
        hbox(parent, 0, 0)
    parent.layout().addWidget(scrollArea)

    if frameless:
        scrollArea.setFrameStyle(QFrame.Shape.NoFrame)

    return scrollArea, widget


def scroll_area(h_on: bool = True, v_on: bool = True, frameless: bool = False) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    scroll.setWidgetResizable(True)
    if frameless:
        scroll.setFrameStyle(QFrame.Shape.NoFrame)
    if not h_on:
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    if not v_on:
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    return scroll


def set_tab_icon(tabs: QTabWidget, widget: QWidget, icon: QIcon):
    i = tabs.indexOf(widget)
    tabs.setTabIcon(i, icon)


def set_tab_visible(tabs: QTabWidget, widget: QWidget, visible: bool = True):
    i = tabs.indexOf(widget)
    tabs.setTabVisible(i, visible)


def set_tab_enabled(tabs: QTabWidget, widget: QWidget, enabled: bool = True):
    i = tabs.indexOf(widget)
    tabs.setTabEnabled(i, enabled)


def set_tab_settings(tabs: QTabWidget, widget: QWidget, text: Optional[str] = None, icon: Optional[QIcon] = None,
                     tooltip: Optional[str] = None, visible: Optional[bool] = None, enabled: Optional[bool] = None):
    i = tabs.indexOf(widget)
    if text is not None:
        tabs.setTabText(i, text)
    if icon is not None:
        tabs.setTabIcon(i, icon)
    if tooltip is not None:
        tabs.setTabToolTip(i, tooltip)
    if visible is not None:
        tabs.setTabVisible(i, visible)
    if enabled is not None:
        tabs.setTabEnabled(i, enabled)


def fade_out_and_gc(parent: QWidget, widget: QWidget, duration: int = 200, teardown=None):
    def destroy():
        remove_and_gc(parent, widget)
        if teardown:
            teardown()

    widget.setDisabled((True))
    anim = qtanim.fade_out(widget, duration)
    anim.finished.connect(destroy)


def remove_and_gc(parent: QWidget, widget: QWidget):
    widget.setHidden(True)
    parent.layout().removeWidget(widget)
    gc(widget)


def insert_before_the_end(parent: QWidget, widget: QWidget, leave: int = 1, alignment=None):
    i = parent.layout().count() - leave
    if alignment:
        parent.layout().insertWidget(i, widget, alignment=alignment)
    else:
        parent.layout().insertWidget(i, widget)


def insert_before(parent: QWidget, widget: QWidget, reference: QWidget):
    i = parent.layout().indexOf(reference)
    parent.layout().insertWidget(i, widget)


def insert_after(parent: QWidget, widget: QWidget, reference: QWidget, alignment=None):
    i = parent.layout().indexOf(reference)
    if alignment is not None:
        parent.layout().insertWidget(i + 1, widget, alignment=alignment)
    else:
        parent.layout().insertWidget(i + 1, widget)


def tool_btn(icon: QIcon, tooltip: str = '', checkable: bool = False, base: bool = False,
             icon_resize: bool = True, pointy_: bool = True, transparent_: bool = False, properties: List[str] = None,
             parent=None) -> QToolButton:
    btn = QToolButton()
    _init_btn(btn, icon=icon, tooltip=tooltip, checkable=checkable, base=base, icon_resize=icon_resize, pointy_=pointy_,
              transparent_=transparent_, properties=properties, parent=parent)
    return btn


def push_btn(icon: Optional[QIcon] = None, text: str = '', tooltip: str = '', checkable: bool = False,
             base: bool = False,
             icon_resize: bool = True, pointy_: bool = True, transparent_: bool = False, properties: List[str] = None,
             parent=None) -> QPushButton:
    btn = QPushButton()
    btn.setText(text)
    _init_btn(btn, icon=icon, tooltip=tooltip, checkable=checkable, base=base, icon_resize=icon_resize, pointy_=pointy_,
              transparent_=transparent_, properties=properties, parent=parent)

    return btn


def _init_btn(btn: QAbstractButton, icon: Optional[QIcon] = None, tooltip: str = '', checkable: bool = False,
              base: bool = False,
              icon_resize: bool = True, pointy_: bool = True, transparent_: bool = False, properties: List[str] = None,
              parent=None):
    if icon:
        btn.setIcon(icon)
    btn.setToolTip(tooltip)
    btn.setCheckable(checkable)
    if pointy_:
        pointy(btn)
    if base:
        btn.setProperty('base', True)
    if icon_resize:
        btn.installEventFilter(ButtonPressResizeEventFilter(btn))
    if transparent_:
        transparent(btn)
    if properties:
        for prop in properties:
            btn.setProperty(prop, True)
    if parent:
        btn.setParent(parent)


def frame(parent=None):
    frame_ = QFrame(parent)
    frame_.setFrameShape(QFrame.Shape.StyledPanel)
    return frame_


def label(text: str = '', bold: Optional[bool] = None, italic: Optional[bool] = None, underline: Optional[bool] = None,
          description: Optional[bool] = None, wordWrap: Optional[bool] = None, h1: Optional[bool] = None,
          h2: Optional[bool] = None, h3: Optional[bool] = None, h4: Optional[bool] = None, h5: Optional[bool] = None,
          color=None, decr_font_diff: int = 0, incr_font_diff: int = 0,
          parent=None) -> QLabel:
    lbl = QLabel(text, parent)
    font = lbl.font()
    if bold:
        font.setBold(bold)
    if italic:
        font.setItalic(italic)
    if underline:
        font.setUnderline(underline)
    lbl.setFont(font)

    if description:
        lbl.setProperty('description', description)
    if h1:
        lbl.setProperty('h1', h1)
    elif h2:
        lbl.setProperty('h2', h2)
    elif h3:
        lbl.setProperty('h3', h3)
    elif h4:
        lbl.setProperty('h4', h4)
    elif h5:
        lbl.setProperty('h5', h5)

    if color:
        lbl.setStyleSheet(f'color: {color};')

    if decr_font_diff:
        decr_font(lbl, decr_font_diff)
    if incr_font_diff:
        incr_font(lbl, incr_font_diff)

    if wordWrap:
        lbl.setWordWrap(wordWrap)

    return lbl


class ExclusiveOptionalButtonGroup(QButtonGroup):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setExclusive(False)
        self._checkedButton: Optional[QAbstractButton] = None

        self.buttonToggled.connect(self._buttonToggled)

    @overrides
    def setExclusive(self, _: bool) -> None:
        super(ExclusiveOptionalButtonGroup, self).setExclusive(False)

    def reset(self):
        if self.checkedButton():
            self.checkedButton().setChecked(False)

    def _buttonToggled(self, button: QAbstractButton, toggled: bool):
        if toggled and self._checkedButton and self._checkedButton is not button:
            self._checkedButton.setChecked(False)

        if toggled:
            self._checkedButton = button


class DelayedSignalSlotConnector(QObject):
    def __init__(self, signal, slot, delay: int = 1000, parent=None):
        super().__init__(parent)
        self._slot = slot
        self._delay = delay
        self._signal_args = ()
        self._signal_kwargs = {}

        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._call)

        self._frozen: bool = False

        signal.connect(self._on_signal_emitted)

    def freeze(self, frozen: bool = True):
        self._frozen = frozen

    def _call(self):
        self._timer.stop()
        self._slot(*self._signal_args, **self._signal_kwargs)

    def _on_signal_emitted(self, *args, **kwargs):
        self._signal_args = args
        self._signal_kwargs = kwargs
        if not self._frozen:
            self._timer.start(self._delay)


def spawn(cls):
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    main_window = QMainWindow()
    wdgCentral = QWidget()
    vbox(wdgCentral)
    main_window.setCentralWidget(wdgCentral)

    widget = cls()
    wdgDisplay = QWidget()
    hbox(wdgDisplay)
    if isinstance(widget, QChart):
        view = QChartView()
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setChart(widget)
        wdgDisplay.layout().addWidget(view)
    else:
        wdgDisplay.layout().addWidget(widget)

    btnClose = QPushButton("Close")
    sp(btnClose).h_max()
    btnClose.clicked.connect(main_window.close)
    wdgCentral.layout().addWidget(spacer())
    wdgCentral.layout().addWidget(wdgDisplay)
    wdgCentral.layout().addWidget(btnClose, alignment=Qt.AlignmentFlag.AlignCenter)
    wdgCentral.layout().addWidget(spacer())

    main_window.show()

    sys.exit(app.exec())


def any_menu_visible(*buttons: Union[QPushButton, QToolButton]) -> bool:
    for btn in buttons:
        if btn.menu().isVisible():
            return True

    return False


def open_url(url: str):
    QDesktopServices.openUrl(QUrl(url))


def to_rgba_str(color: QColor, alpha: int = 255) -> str:
    return f'rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})'


def calculate_resized_dimensions(width: int, height: int, max_size: int = 512):
    if max(width, height) > max_size:
        ratio = width / height
        if width > height:
            w, h = max_size, max_size / ratio
        elif width < height:
            w, h = max_size * ratio, max_size
        else:
            w = h = max_size
    else:
        w, h = width, height

    return int(w), int(h)


def fade_in(wdg: QWidget):
    qtanim.fade_in(wdg, duration=150, teardown=lambda: wdg.setGraphicsEffect(None))


def fade_out(wdg: QWidget):
    qtanim.fade_out(wdg, duration=150, teardown=lambda: wdg.setGraphicsEffect(None))


def fade(wdg: QWidget, visible: bool):
    if visible:
        fade_in(wdg)
    else:
        fade_out(wdg)


def dominant_color(pixmap: QPixmap) -> QColor:
    image = pixmap.toImage()
    resize_factor = 0.5
    skip = 5
    new_width = int(image.width() * resize_factor)
    new_height = int(image.height() * resize_factor)
    downsampled_image = image.scaled(new_width, new_height)
    colors = []
    for x in range(0, downsampled_image.width(), skip):
        for y in range(0, downsampled_image.height(), skip):
            pixel_color = image.pixelColor(x, y).rgb()
            colors.append(pixel_color)

    color_counter = Counter(colors)
    dominant_rgb = color_counter.most_common(1)[0][0]
    return QColor(dominant_rgb)

  
def columns(margin: int = 2, spacing: int = 3) -> QWidget:
    wdg = QWidget()
    hbox(wdg, margin, spacing)
    return wdg


def rows(margin: int = 2, spacing: int = 3) -> QWidget:
    wdg = QWidget()
    vbox(wdg, margin, spacing)
    return wdg

  
def exclusive_buttons(parent: QObject, *buttons, optional=False) -> QButtonGroup:
    btnGroup = ExclusiveOptionalButtonGroup(parent) if optional else QButtonGroup(parent)
    btnGroup.setExclusive(True)
    for btn in buttons:
        btnGroup.addButton(btn)
    return btnGroup


def default_character_color(uuid_: UUID) -> str:
    return CHARACTER_INITIAL_AVATAR_COLOR_CODES[uuid_.int % len(CHARACTER_INITIAL_AVATAR_COLOR_CODES)]
