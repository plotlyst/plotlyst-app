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
from typing import Optional

from PyQt6.QtCore import pyqtSignal, Qt, QEvent, QObject
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import QWidget, QSlider, QTextEdit, QButtonGroup
from overrides import overrides
from qthandy import hbox, vbox, incr_icon, pointy, incr_font, vspacer, line, margins
from qthandy.filter import VisibilityToggleEventFilter
from qtmenu import MenuWidget

from plotlyst.common import PLACEHOLDER_TEXT_COLOR, RELAXED_WHITE_COLOR, PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import Conflict, Novel, Scene, CharacterAgency, Character, ConflictType
from plotlyst.env import app_env
from plotlyst.service.cache import entities_registry
from plotlyst.view.common import tool_btn, label, frame, rows, columns, push_btn, \
    link_editor_to_btn
from plotlyst.view.icons import IconRegistry, avatars
from plotlyst.view.style.base import transparent_menu
from plotlyst.view.widget.button import SelectorToggleButton
from plotlyst.view.widget.input import RemovalButton, DecoratedLineEdit


class ConflictIntensityEditor(QWidget):
    intensityChanged = pyqtSignal(int)

    def __init__(self, parent=None, minWidth: int = 100):
        super().__init__(parent)
        hbox(self, 0)
        self._slider = QSlider()
        self._slider.setOrientation(Qt.Orientation.Horizontal)
        self._slider.setMinimum(0)
        self._slider.setMaximum(10)
        self._slider.setPageStep(1)
        self._slider.setValue(1)
        self._slider.setMinimumWidth(minWidth)
        self._slider.setMaximumWidth(200)
        self._slider.valueChanged.connect(self._valueChanged)
        self._slider.setProperty('conflict', True)

        self._iconColor = '#f3a712'
        self._icon = tool_btn(IconRegistry.from_name('mdi.battery-charging-10', self._iconColor), transparent_=True)
        tip = 'Conflict intensity'
        self._slider.setToolTip(tip)
        self._icon.setToolTip(tip)

        self.layout().addWidget(self._icon)
        self.layout().addWidget(self._slider)

    def value(self) -> int:
        return self._slider.value()

    def setValue(self, value: int) -> None:
        if value == 0:
            value = 1
        self._slider.setValue(value)

    def _valueChanged(self, value: int):
        if value == 0:
            self.setValue(1)
            return
        iconName = f'mdi.battery-charging-{value * 10}'
        self._icon.setIcon(IconRegistry.from_name(iconName, self._iconColor))
        self.intensityChanged.emit(value)


class _ConflictSelectorButton(SelectorToggleButton):
    def __init__(self, conflictType: ConflictType, parent=None):
        super().__init__(Qt.ToolButtonStyle.ToolButtonTextBesideIcon, minWidth=80, parent=parent)
        self.scope = conflictType
        self.setText(conflictType.display_name())
        self.setIcon(IconRegistry.from_name(conflictType.icon()))


class ConflictSelectorPopup(MenuWidget):
    conflictChanged = pyqtSignal(Conflict)

    def __init__(self, novel: Novel, scene: Scene, agency: CharacterAgency, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.scene = scene
        self.agency = agency
        self._character: Optional[Character] = None
        transparent_menu(self)

        self.wdgFrame = frame()
        vbox(self.wdgFrame, 10, 8)
        self.wdgFrame.setProperty('white-bg', True)
        self.wdgFrame.setProperty('large-rounded', True)

        self.btnGroupConflicts = QButtonGroup()

        self.wdgPersonal = rows(0)
        self.wdgSocial = rows(0)
        self.wdgGlobal = rows(0)

        self.lineKey = DecoratedLineEdit(defaultWidth=150)
        self.lineKey.setIcon(IconRegistry.conflict_icon(PLOTLYST_SECONDARY_COLOR, PLOTLYST_SECONDARY_COLOR))
        self.lineKey.lineEdit.setPlaceholderText('Keyphrase')
        incr_font(self.lineKey.lineEdit, 2)
        incr_icon(self.lineKey.icon, 6)

        self.wdgKeyPhraseFrame = frame()
        self.wdgKeyPhraseFrame.setProperty('large-rounded', True)
        self.wdgKeyPhraseFrame.setProperty('muted-bg', True)
        hbox(self.wdgKeyPhraseFrame, 10).addWidget(self.lineKey)

        self.btnConfirm = push_btn(IconRegistry.ok_icon(RELAXED_WHITE_COLOR), 'Confirm',
                                   properties=['confirm', 'positive'])
        self.btnConfirm.setDisabled(True)
        link_editor_to_btn(self.lineKey.lineEdit, self.btnConfirm, disabledShake=True,
                           shakedWidget=self.wdgKeyPhraseFrame)
        self.btnConfirm.clicked.connect(self._confirm)

        self.wdgScope = columns(0, 8)
        margins(self.wdgScope, bottom=35, top=35)
        self.wdgScope.layout().addWidget(self.wdgPersonal)
        self.wdgScope.layout().addWidget(self.wdgSocial)
        self.wdgScope.layout().addWidget(self.wdgGlobal)

        self.wdgFrame.layout().addWidget(
            label(
                "Define the conflict and select who is directly impacted by it",
                description=True))

        self.wdgFrame.layout().addWidget(self.wdgKeyPhraseFrame, alignment=Qt.AlignmentFlag.AlignCenter)
        self.wdgFrame.layout().addWidget(self.wdgScope)
        self.wdgFrame.layout().addWidget(self.btnConfirm, alignment=Qt.AlignmentFlag.AlignRight)

        btnPersonal = self.__initConflictScope(ConflictType.PERSONAL, self.wdgPersonal)
        incr_font(btnPersonal, 2)
        self.wdgPersonal.layout().addWidget(line())
        self.__initConflictScope(ConflictType.INTERNAL, self.wdgPersonal)
        self.__initConflictScope(ConflictType.MILIEU, self.wdgPersonal)
        btn = self.__initConflictScope(ConflictType.SOCIAL, self.wdgSocial)
        incr_font(btn, 2)
        btn = self.__initConflictScope(ConflictType.GLOBAL, self.wdgGlobal)
        incr_font(btn, 2)

        self.wdgPersonal.layout().addWidget(vspacer())
        self.wdgSocial.layout().addWidget(vspacer())
        self.wdgGlobal.layout().addWidget(vspacer())

        self.addWidget(self.wdgFrame)

        btnPersonal.setChecked(True)

        if self.agency.character_id:
            character = entities_registry.character(str(self.agency.character_id))
            if character:
                btnPersonal.setIcon(avatars.avatar(character))

        self.lineKey.lineEdit.setFocus()

    def _characterSelected(self, character: Character):
        self._character = character

    def _confirm(self):
        conflict = Conflict(self.lineKey.lineEdit.text(), scope=self.btnGroupConflicts.checkedButton().scope)
        self.conflictChanged.emit(conflict)

    def __initConflictScope(self, scope: ConflictType, parent: QWidget) -> _ConflictSelectorButton:
        btn = _ConflictSelectorButton(scope)
        self.btnGroupConflicts.addButton(btn)

        parent.layout().addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return btn


class ConflictReferenceWidget(QWidget):
    removed = pyqtSignal()

    def __init__(self, conflict: Conflict, parent=None):
        super().__init__(parent)
        self.conflict = conflict

        vbox(self, 0, 0)

        self._btnRemove = RemovalButton(self)
        self._btnRemove.clicked.connect(self.removed)
        self._btnRemove.setHidden(True)

        self._iconConflict = tool_btn(IconRegistry.from_name(self.conflict.scope.icon()), transparent_=True)
        incr_icon(self._iconConflict, 8)

        self._lblConflict = label(self.conflict.text, wordWrap=True)
        pointy(self._lblConflict)
        font = self._lblConflict.font()
        font.setFamily(app_env.serif_font())
        self._lblConflict.setFont(font)
        self._lblConflict.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lblConflict.installEventFilter(self)

        self._textedit = QTextEdit(self)
        self._textedit.setTabChangesFocus(True)
        if app_env.is_mac():
            incr_font(self._textedit)
        self._textedit.verticalScrollBar().setVisible(False)
        self._textedit.setStyleSheet(f'color: {PLACEHOLDER_TEXT_COLOR}; border: 0px; padding: 2px;')
        self._textedit.setMaximumSize(165, 85)

        self._textedit.setPlaceholderText("What kind of conflict does the character have to face?")
        self._textedit.setText(self.conflict.desc)
        self._textedit.textChanged.connect(self._textChanged)

        self.layout().addWidget(self._iconConflict, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._lblConflict)
        self.layout().addWidget(self._textedit)

        self.installEventFilter(VisibilityToggleEventFilter(self._btnRemove, self))

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonRelease:
            self._edit()
        return super().eventFilter(watched, event)

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        self._btnRemove.setGeometry(self.width() - self._btnRemove.sizeHint().width(), 2,
                                    self._btnRemove.sizeHint().width(), self._btnRemove.sizeHint().height())

    def _textChanged(self):
        self.conflict.desc = self._textedit.toPlainText()

    def _edit(self):
        pass
