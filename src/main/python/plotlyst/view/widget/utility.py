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
from typing import Any, Optional, Tuple, List

from PyQt6.QtCore import QModelIndex, Qt, QAbstractListModel, pyqtSignal, QSize, QEvent, QRect, QPoint
from PyQt6.QtGui import QColor, QBrush, QResizeEvent, QMouseEvent, QPixmap, QPainter
from PyQt6.QtWidgets import QWidget, QListView, QSizePolicy, QToolButton, QButtonGroup, QDialog, QColorDialog, \
    QApplication, QPushButton
from overrides import overrides
from qthandy import flow, transparent, pointy, grid, vline, line, translucent, decr_icon, hbox
from qtmenu import MenuWidget

from plotlyst.common import RELAXED_WHITE_COLOR, PLOTLYST_SECONDARY_COLOR, RED_COLOR, PLOTLYST_TERTIARY_COLOR
from plotlyst.model.common import proxy
from plotlyst.view.common import ButtonPressResizeEventFilter, tool_btn, push_btn, shadow, action, restyle, \
    rounded_pixmap, label, calculate_resized_dimensions
from plotlyst.view.generated.icon_selector_widget_ui import Ui_IconsSelectorWidget
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget._icons import icons_registry
from plotlyst.view.widget.button import SecondaryActionToolButton
from plotlyst.view.widget.display import PopupDialog


class ColorButton(QToolButton):
    def __init__(self, color: str, parent=None):
        super(ColorButton, self).__init__(parent)
        self.color = color
        self.setCheckable(True)
        pointy(self)
        self.setIcon(IconRegistry.from_name('fa5s.circle', color=color))
        transparent(self)
        self.setIconSize(QSize(24, 24))
        self.installEventFilter(ButtonPressResizeEventFilter(self))


BASE_COLORS = ['darkBlue', '#0077b6', '#00b4d8', '#007200', '#2a9d8f', '#94d2bd', '#ffd000', '#f48c06',
               '#e85d04',
               '#dc2f02',
               '#ffc6ff', '#b5179e', '#7209b7', '#d6ccc2', '#6c757d', '#dda15e', '#bc6c25', 'black']


class ColorPicker(QWidget):
    colorPicked = pyqtSignal(QColor)

    def __init__(self, parent=None, maxColumn: Optional[int] = None, colors=None):
        super().__init__(parent)
        if maxColumn:
            grid(self, 1, 1, 1)
        else:
            flow(self)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        self.btnGroup = QButtonGroup(self)
        self.btnGroup.setExclusive(True)

        if colors is None:
            colors = BASE_COLORS
        row = -1
        for i, color in enumerate(colors):
            btn = ColorButton(color, self)

            self.btnGroup.addButton(btn)
            if maxColumn:
                if i % maxColumn == 0:
                    row += 1
                    col = 0
                else:
                    col = i % maxColumn
                self.layout().addWidget(btn, row, col)
            else:
                self.layout().addWidget(btn)

        self._btnCustomColor = tool_btn(IconRegistry.from_name('msc.symbol-color'), transparent_=True,
                                        tooltip='Select a custom color')
        self._btnCustomColor.clicked.connect(self._customColorClicked)
        self.layout().addWidget(vline())
        self.layout().addWidget(self._btnCustomColor)
        self.btnGroup.buttonClicked.connect(self._clicked)

    def color(self) -> QColor:
        btn = self.btnGroup.checkedButton()
        if btn:
            return QColor(btn.color)
        else:
            return QColor(Qt.GlobalColor.black)

    def _clicked(self, btn: ColorButton):
        self.colorPicked.emit(QColor(btn.color))

    def _customColorClicked(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.colorPicked.emit(color)


class IconPicker(QWidget):
    iconSelected = pyqtSignal(str)

    def __init__(self, icons: List[str], parent=None, maxColumn: Optional[int] = None, iconSize: int = 22):
        super().__init__(parent)
        if maxColumn:
            grid(self, 1, 1, 1)
        else:
            flow(self)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

        row = -1
        for i, icon in enumerate(icons):
            if icon:
                btn = tool_btn(IconRegistry.from_name(icon), transparent_=True)
                btn.setIconSize(QSize(iconSize, iconSize))
            else:
                btn = tool_btn(IconRegistry.from_name('ei.remove-circle', RED_COLOR), transparent_=True)
                btn.setIconSize(QSize(iconSize - 4, iconSize - 4))

            btn.clicked.connect(partial(self.iconSelected.emit, icon))
            if maxColumn:
                if i % maxColumn == 0:
                    row += 1
                    col = 0
                else:
                    col = i % maxColumn
                self.layout().addWidget(btn, row, col)
            else:
                self.layout().addWidget(btn)


class ColorSelectorButton(QToolButton):
    colorChanged = pyqtSignal(str)

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.color = color
        pointy(self)
        self.setIcon(IconRegistry.from_name('fa5s.square', color=color))
        transparent(self)
        self.setIconSize(QSize(24, 24))
        self.installEventFilter(ButtonPressResizeEventFilter(self))
        shadow(self)

        self.clicked.connect(self._clicked)

    def _clicked(self):
        qcolor = QColorDialog.getColor(options=QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if qcolor.isValid():
            color = qcolor.name()
            self.setIcon(IconRegistry.from_name('fa5s.square', color=color))
            self.colorChanged.emit(color)


class IconSelectorWidget(QWidget, Ui_IconsSelectorWidget):
    iconSelected = pyqtSignal(str, QColor)
    model = None

    def __init__(self, parent=None):
        super(IconSelectorWidget, self).__init__(parent)
        self.setupUi(self)

        self.btnFilterIcon.setIcon(IconRegistry.from_name('mdi.magnify'))

        self.btnPeople.setIcon(IconRegistry.from_name('mdi.account', color_on=PLOTLYST_SECONDARY_COLOR))
        self.btnPeople.setToolTip('People and emotions')
        self.btnFood.setIcon(IconRegistry.from_name('fa5s.ice-cream', color_on=PLOTLYST_SECONDARY_COLOR))
        self.btnFood.setToolTip('Food and beverage')
        self.btnNature.setIcon(IconRegistry.from_name('mdi.nature', color_on=PLOTLYST_SECONDARY_COLOR))
        self.btnNature.setToolTip('Nature')
        self.btnSports.setIcon(IconRegistry.from_name('fa5s.football-ball', color_on=PLOTLYST_SECONDARY_COLOR))
        self.btnSports.setToolTip('Sports')
        self.btnObjects.setIcon(IconRegistry.from_name('fa5.lightbulb', color_on=PLOTLYST_SECONDARY_COLOR))
        self.btnObjects.setToolTip('Objects')
        self.btnPlaces.setIcon(IconRegistry.from_name('ei.globe', color_on=PLOTLYST_SECONDARY_COLOR))
        self.btnPlaces.setToolTip('Places and travel')
        self.btnCharacters.setIcon(
            IconRegistry.from_name('mdi6.alphabetical-variant', color_on=PLOTLYST_SECONDARY_COLOR))
        self.btnCharacters.setToolTip('Numbers and characters')
        self.btnSymbols.setIcon(IconRegistry.from_name('mdi.symbol', color_on=PLOTLYST_SECONDARY_COLOR))
        self.btnSymbols.setToolTip('Symbols')
        self.btnAll.setChecked(True)

        self.colorPicker = ColorPicker(self)
        self.colorPicker.colorPicked.connect(self._colorPicked)
        self.wdgTop.layout().insertWidget(0, self.colorPicker)

        if IconSelectorWidget.model is None:
            filtered_icons = []
            for type, icons_list in icons_registry.items():
                for icon in icons_list:
                    if icon and icon != 'fa5s.' and icon != 'mdi.':
                        filtered_icons.append(self._IconItem(type, icon))
            IconSelectorWidget.model = self._Model(filtered_icons)

        self._proxy = proxy(IconSelectorWidget.model)
        self._proxy.setFilterRole(self._Model.IconTypeRole)
        self.lstIcons.setModel(self._proxy)
        self.lstIcons.setViewMode(QListView.ViewMode.IconMode)
        self.lstIcons.clicked.connect(self._iconClicked)

        self.lineFilter.textChanged.connect(self._textChanged)

        self.buttonGroup.buttonToggled.connect(self._filterToggled)
        self.lineFilter.setFocus()

    def setColor(self, color: QColor):
        self.model.setColor(color)

    def _colorPicked(self, color: QColor):
        self.model.setColor(color)

    def _textChanged(self, text: str):
        self.btnAll.setChecked(True)
        self._proxy.setFilterRole(self._Model.IconAliasRole)
        self._proxy.setFilterRegularExpression(text)

    def _filterToggled(self):
        self._proxy.setFilterRole(self._Model.IconTypeRole)
        if self.btnPeople.isChecked():
            self._proxy.setFilterFixedString('People')
        elif self.btnFood.isChecked():
            self._proxy.setFilterFixedString('Food')
        elif self.btnNature.isChecked():
            self._proxy.setFilterFixedString('Animals & Nature')
        elif self.btnSports.isChecked():
            self._proxy.setFilterFixedString('Sports & Activities')
        elif self.btnPlaces.isChecked():
            self._proxy.setFilterFixedString('Travel & Places')
        elif self.btnObjects.isChecked():
            self._proxy.setFilterFixedString('Objects')
        elif self.btnCharacters.isChecked():
            self._proxy.setFilterFixedString('Numbers and Characters')
        elif self.btnSymbols.isChecked():
            self._proxy.setFilterFixedString('Symbols')
        elif self.btnAll.isChecked():
            self._proxy.setFilterFixedString('')

    def _iconClicked(self, index: QModelIndex):
        icon_alias: str = index.data(role=self._Model.IconAliasRole)
        self.iconSelected.emit(icon_alias, QColor(self.model.color))

    class _IconItem:
        def __init__(self, type: str, name: str):
            self.type = type
            self.name = name

    class _Model(QAbstractListModel):

        IconAliasRole = Qt.ItemDataRole.UserRole + 1
        IconTypeRole = Qt.ItemDataRole.UserRole + 2

        def __init__(self, icons):
            super().__init__()
            self.icons = icons
            self.color: str = 'black'

        @overrides
        def rowCount(self, parent: QModelIndex = ...) -> int:
            return len(self.icons)

        @overrides
        def data(self, index: QModelIndex, role: int) -> Any:
            if role == self.IconAliasRole:
                return self.icons[index.row()].name
            if role == self.IconTypeRole:
                return self.icons[index.row()].type
            if role == Qt.ItemDataRole.DecorationRole:
                return IconRegistry.from_name(self.icons[index.row()].name, self.color)
            if role == Qt.ItemDataRole.BackgroundRole:
                if self.color == '#ffffff':
                    return QBrush(Qt.GlobalColor.lightGray)
                else:
                    return QBrush(QColor(RELAXED_WHITE_COLOR))

            if role == Qt.ItemDataRole.ToolTipRole:
                return self.icons[index.row()].name.split('.')[1].replace('-', ' ').capitalize()

        def setColor(self, color: QColor):
            self.color = color.name()
            self.modelReset.emit()


class IconSelectorDialog(PopupDialog):

    def __init__(self, pickColor: bool = True, color: QColor = QColor(Qt.GlobalColor.black), parent=None):
        super().__init__(parent)
        self.resize(500, 500)

        self._icon = ''
        self._color: Optional[QColor] = None
        self.selector = IconSelectorWidget(self)
        self.selector.colorPicker.setVisible(pickColor)
        self.selector.setColor(color)
        self.selector.iconSelected.connect(self._icon_selected)

        self.btnClose = push_btn(text='Close', properties=['confirm', 'cancel'])
        self.btnClose.clicked.connect(self.reject)

        self.frame.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)
        self.frame.layout().addWidget(self.selector)
        self.frame.layout().addWidget(self.btnClose, alignment=Qt.AlignmentFlag.AlignRight)

    def display(self) -> Optional[Tuple[str, QColor]]:
        result = self.exec()
        if result == QDialog.DialogCode.Accepted and self._icon:
            return self._icon, self._color

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        self.selector.lstIcons.model().modelReset.emit()
        self.selector.lstIcons.update()

    def _icon_selected(self, icon_alias: str, color: QColor):
        self._icon = icon_alias
        self._color = color

        self.accept()


class IconSelectorButton(SecondaryActionToolButton):
    iconSelected = pyqtSignal(str, QColor)

    def __init__(self, parent=None, selectedIconSize: int = 32, defaultIconSize: int = 24):
        super(IconSelectorButton, self).__init__(parent)
        self._selectedIconSize = QSize(selectedIconSize, selectedIconSize)
        self._defaultIconSize = QSize(defaultIconSize, defaultIconSize)

        self._selected: bool = False
        self.installEventFilter(ButtonPressResizeEventFilter(self))
        self.reset()
        self.clicked.connect(self._displayIcons)

    def setSelectedIconSize(self, size: QSize):
        self._selectedIconSize = size
        if self._selected:
            self.setIconSize(self._selectedIconSize)

    def setDefaultIconSize(self, size: QSize):
        self._defaultIconSize = size

    def selectIcon(self, icon: str, icon_color: str):
        self.setIcon(IconRegistry.from_name(icon, icon_color))
        transparent(self)
        self.setIconSize(self._selectedIconSize)
        self._selected = True

    def reset(self):
        self.setIconSize(self._defaultIconSize)
        self.setIcon(IconRegistry.icons_icon())
        self.initStyleSheet()
        self._selected = False

    def _displayIcons(self):
        result = IconSelectorDialog.popup()
        if result:
            self.selectIcon(result[0], result[1].name())
            self.iconSelected.emit(result[0], result[1])


class IconPickerMenu(MenuWidget):
    iconSelected = pyqtSignal(str)

    def __init__(self, icons: List[str], maxColumn: Optional[int] = None, iconSize: int = 22, parent=None):
        super().__init__(parent)

        self.picker = IconPicker(icons, self, maxColumn, iconSize)
        self.picker.iconSelected.connect(self.iconSelected)

        self.addWidget(self.picker)
        self.addSeparator()
        self.addAction(action('Custom icon...', IconRegistry.icons_icon(), slot=self._customIconTriggered))

    def _customIconTriggered(self):
        result = IconSelectorDialog.popup(pickColor=False)
        if result:
            self.iconSelected.emit(result[0])


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
        def mouseMoveEvent(self, event: QMouseEvent) -> None:
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
        def leaveEvent(self, _: QEvent) -> None:
            QApplication.restoreOverrideCursor()
            self._pressedPoint = None

        @overrides
        def mousePressEvent(self, event: QMouseEvent) -> None:
            self._pressedPoint = event.pos()
            self._originalSize = self.geometry()

        @overrides
        def mouseReleaseEvent(self, _: QMouseEvent) -> None:
            self._pressedPoint = None
            self.cropped.emit()
