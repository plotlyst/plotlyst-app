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
from functools import partial
from typing import Optional

import qtanim
from PyQt5.QtCore import pyqtSignal, Qt, pyqtProperty, QTimer, QEvent
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QPushButton, QSizePolicy, QToolButton, QAbstractButton, QLabel, QButtonGroup
from overrides import overrides
from qthandy import hbox, opaque, bold, incr_font

from src.main.python.plotlyst.core.domain import SelectionItem
from src.main.python.plotlyst.view.common import OpacityEventFilter, pointy
from src.main.python.plotlyst.view.icons import IconRegistry


class SelectionItemPushButton(QPushButton):
    itemClicked = pyqtSignal(SelectionItem)
    itemDoubleClicked = pyqtSignal(SelectionItem)

    def __init__(self, parent=None):
        super(SelectionItemPushButton, self).__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.item: Optional[SelectionItem] = None
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.clicked.connect(self._checkDoubleClick)

    def setSelectionItem(self, item: SelectionItem):
        self.item = item
        self.setText(item.text)
        if item.icon:
            self.setIcon(IconRegistry.from_name(item.icon, item.icon_color))

        self.clicked.connect(partial(self.itemClicked.emit, item))
        self.toggled.connect(self._toggled)

    def _toggled(self, checked: bool):
        font = self.font()
        font.setBold(checked)
        self.setFont(font)

    def _checkDoubleClick(self):
        if not self.item:
            return
        if self.timer.isActive():
            self.itemDoubleClicked.emit(self.item)
            self.timer.stop()
        else:
            self.timer.start(250)


class _SecondaryActionButton(QAbstractButton):
    def __init__(self, parent=None):
        super(_SecondaryActionButton, self).__init__(parent)
        self._iconName: str = ''
        self._iconColor: str = 'black'
        self._checkedColor: str = 'black'
        self.initStyleSheet()
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Maximum)
        self.installEventFilter(OpacityEventFilter(leaveOpacity=0.7, parent=self))

    def initStyleSheet(self, border_color: str = 'grey', border_style: str = 'dashed', color: str = 'grey'):
        self.setStyleSheet(f'''
                {self.__class__.__name__} {{
                    border: 2px {border_style} {border_color};
                    border-radius: 6px;
                    color: {color};
                    padding: 2px;
                }}
                {self.__class__.__name__}:pressed {{
                    border: 2px solid {border_color};
                }}
                {self.__class__.__name__}:checked {{
                    border: 2px solid {self._checkedColor};
                }}
                {self.__class__.__name__}::menu-indicator {{width:0px;}}
            ''')

    def setBorderColor(self, color_name: str):
        self.initStyleSheet(color_name)
        self.update()

    def _setIcon(self):
        if self._iconName:
            self.setIcon(IconRegistry.from_name(self._iconName, self._iconColor, color_on=self._checkedColor))


class SecondaryActionToolButton(QToolButton, _SecondaryActionButton):
    @pyqtProperty(str)
    def iconName(self):
        return self._iconName

    @iconName.setter
    def iconName(self, value):
        self._iconName = value
        self._setIcon()

    @pyqtProperty(str)
    def iconColor(self):
        return self._iconColor

    @iconColor.setter
    def iconColor(self, value):
        self._iconColor = value
        self._setIcon()

    @pyqtProperty(str)
    def checkedColor(self):
        return self._checkedColor

    @checkedColor.setter
    def checkedColor(self, value):
        self._checkedColor = value
        self.initStyleSheet()
        self._setIcon()


class SecondaryActionPushButton(QPushButton, _SecondaryActionButton):
    @pyqtProperty(str)
    def iconName(self):
        return self._iconName

    @iconName.setter
    def iconName(self, value):
        self._iconName = value
        self._setIcon()

    @pyqtProperty(str)
    def iconColor(self):
        return self._iconColor

    @iconColor.setter
    def iconColor(self, value):
        self._iconColor = value
        self._setIcon()

    @pyqtProperty(str)
    def checkedColor(self):
        return self._checkedColor

    @checkedColor.setter
    def checkedColor(self, value):
        self._checkedColor = value
        self.initStyleSheet()
        self._setIcon()


class WordWrappedPushButton(QPushButton):
    def __init__(self, parent=None):
        super(WordWrappedPushButton, self).__init__(parent)
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.NoTextInteraction)
        self.label.setAlignment(Qt.AlignCenter)
        hbox(self, 0, 0).addWidget(self.label, alignment=Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Maximum)

    @overrides
    def setText(self, text: str):
        self.label.setText(text)
        self.setFixedHeight(self.label.height() + 5)


class FadeOutButtonGroup(QButtonGroup):
    def __init__(self, parent=None):
        super(FadeOutButtonGroup, self).__init__(parent)
        self.buttonClicked.connect(self._clicked)
        self.setExclusive(False)
        self._opacity = 0.7
        self._fadeInDuration = 250

    def setButtonOpacity(self, opacity: float):
        self._opacity = opacity

    def setFadeInDuration(self, duration: int):
        self._fadeInDuration = duration

    def toggle(self, btn: QAbstractButton):
        btn.setChecked(not btn.isChecked())
        for other_btn in self.buttons():
            if other_btn is btn:
                continue

            if btn.isChecked():
                other_btn.setChecked(False)
                other_btn.setDisabled(True)
                other_btn.setHidden(True)
            else:
                other_btn.setEnabled(True)
                other_btn.setVisible(True)

    def _clicked(self, btn: QAbstractButton):
        for other_btn in self.buttons():
            if other_btn is btn:
                continue

            if btn.isChecked():
                other_btn.setChecked(False)
                other_btn.setDisabled(True)
                qtanim.fade_out(other_btn)
            else:
                other_btn.setEnabled(True)
                anim = qtanim.fade_in(other_btn, duration=self._fadeInDuration)
                anim.finished.connect(partial(opaque, other_btn, self._opacity))


class ToolbarButton(QToolButton):
    def __init__(self, parent=None):
        super(ToolbarButton, self).__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setCheckable(True)
        pointy(self)

        self.toggled.connect(lambda x: bold(self, x))

        self.setStyleSheet('''
            QToolButton:checked {
                color: #240046;
                background-color: #e2cfea;
            }
        ''')

        incr_font(self, 1)

    @overrides
    def enterEvent(self, event: QEvent) -> None:
        qtanim.colorize(self, color=QColor('#7B2CBF'))
