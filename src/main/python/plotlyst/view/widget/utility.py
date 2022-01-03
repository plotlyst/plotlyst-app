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
from typing import Any

from PyQt6.QtCore import QModelIndex, Qt, QAbstractListModel, pyqtSignal, QSortFilterProxyModel
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QListView
from overrides import overrides

from src.main.python.plotlyst.view.common import show_color_picker
from src.main.python.plotlyst.view.generated.icon_selector_widget_ui import Ui_IconsSelectorWidget
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.widget._icons import icons_registry


class IconSelectorWidget(QWidget, Ui_IconsSelectorWidget):
    iconSelected = pyqtSignal(str, QColor)

    def __init__(self, parent=None):
        super(IconSelectorWidget, self).__init__(parent)
        self.setupUi(self)

        self.btnFilterIcon.setIcon(IconRegistry.from_name('mdi.magnify'))

        self.btnPeople.setIcon(IconRegistry.from_name('mdi.account', color_on='darkGreen'))
        self.btnFood.setIcon(IconRegistry.from_name('fa5s.ice-cream', color_on='darkGreen'))
        self.btnNature.setIcon(IconRegistry.from_name('mdi.nature', color_on='darkGreen'))
        self.btnSports.setIcon(IconRegistry.from_name('fa5s.football-ball', color_on='darkGreen'))
        self.btnObjects.setIcon(IconRegistry.from_name('fa5.lightbulb', color_on='darkGreen'))
        self.btnPlaces.setIcon(IconRegistry.from_name('ei.globe', color_on='darkGreen'))
        self.btnSymbols.setIcon(IconRegistry.from_name('mdi.symbol', color_on='darkGreen'))
        self.btnAll.setChecked(True)

        # qtawesome._instance()
        # fontMaps = qtawesome._resource['iconic'].charmap
        # for fontCollection, fontData in fontMaps.items():
        #     if fontCollection != 'mdi':
        #         continue
        #     for iconName in fontData:
        #         print(iconName)

        filtered_icons = []
        for type, icons_list in icons_registry.items():
            for icon in icons_list:
                if icon and icon != 'fa5s.' and icon != 'mdi.':
                    filtered_icons.append(self._IconItem(type, icon))
        self.model = self._Model(filtered_icons)
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self.model)
        self._proxy.setFilterRole(self._Model.IconTypeRole)
        self.lstIcons.setModel(self._proxy)
        self.lstIcons.setViewMode(QListView.ViewMode.IconMode)
        self.lstIcons.clicked.connect(self._icon_clicked)

        self.lineFilter.textChanged.connect(self._text_changed)

        self.buttonGroup.buttonToggled.connect(self._filter_toggled)

        self._color: QColor = QColor('black')
        self._update_button_color()

        self.btnColor.clicked.connect(self._change_color)

    def _update_button_color(self):
        self.btnColor.setStyleSheet(f'''
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 {self._color.name()}, stop: 1 {self._color.name()}) ;''')

    def _change_color(self):
        color = show_color_picker(self._color)
        if color.isValid():
            self._color = color
            self._update_button_color()

    def _text_changed(self, text: str):
        self.btnAll.setChecked(True)
        self._proxy.setFilterRole(self._Model.IconAliasRole)
        self._proxy.setFilterRegularExpression(text)

    def _filter_toggled(self):
        self.lineFilter.clear()
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
        elif self.btnSymbols.isChecked():
            self._proxy.setFilterFixedString('Symbols')
        elif self.btnAll.isChecked():
            self._proxy.setFilterFixedString('')

    def _icon_clicked(self, index: QModelIndex):
        icon_alias: str = index.data(role=self._Model.IconAliasRole)
        self.iconSelected.emit(icon_alias, self._color)

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
                return IconRegistry.from_name(self.icons[index.row()].name)
