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
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QSlider, QTextEdit, QButtonGroup
from overrides import overrides
from qthandy import hbox, vbox, incr_icon, pointy, incr_font, vspacer, line, margins, vline, translucent, spacer, \
    decr_icon
from qtmenu import MenuWidget

from plotlyst.common import PLACEHOLDER_TEXT_COLOR, RELAXED_WHITE_COLOR, PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import Conflict, Novel, CharacterAgency, Character, ConflictType
from plotlyst.env import app_env
from plotlyst.service.cache import entities_registry
from plotlyst.view.common import tool_btn, label, frame, rows, columns, push_btn, wrap, action
from plotlyst.view.icons import IconRegistry, avatars
from plotlyst.view.layout import group
from plotlyst.view.style.base import transparent_menu
from plotlyst.view.widget.button import SelectorToggleButton
from plotlyst.view.widget.characters import CharacterSelectorButton
from plotlyst.view.widget.display import MenuOverlayEventFilter
from plotlyst.view.widget.input import DecoratedLineEdit


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

        self._iconColor = '#e57c04'
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
        super().__init__(Qt.ToolButtonStyle.ToolButtonTextBesideIcon, minWidth=80, checkedColor='#f3a712',
                         hoverColor='#FBE6BB', parent=parent)
        self.scope = conflictType
        self.setText(conflictType.display_name())
        self.setIcon(IconRegistry.from_name(conflictType.icon()))


class ConflictSelectorPopup(MenuWidget):
    conflictChanged = pyqtSignal(Conflict)
    remove = pyqtSignal()

    def __init__(self, novel: Novel, agency: CharacterAgency, conflict: Optional[Conflict] = None, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.agency = agency
        if conflict:
            self.conflict = conflict
        else:
            self.conflict = Conflict('', scope=ConflictType.PERSONAL)
        transparent_menu(self)

        self.wdgFrame = frame()
        vbox(self.wdgFrame, 10, 8)
        self.wdgFrame.setProperty('white-bg', True)
        self.wdgFrame.setProperty('large-rounded', True)

        self.btnGroupConflicts = QButtonGroup()
        self.btnGroupConflicts.buttonClicked.connect(self._scopeChanged)

        self.wdgPersonal = rows(0)
        self.wdgGlobal = rows(0)

        self.lineKey = DecoratedLineEdit(defaultWidth=150)
        self.lineKey.setIcon(IconRegistry.conflict_icon(PLOTLYST_SECONDARY_COLOR, PLOTLYST_SECONDARY_COLOR))
        self.lineKey.lineEdit.setPlaceholderText('Keyphrase')
        self.lineKey.setText(self.conflict.text)
        incr_font(self.lineKey.lineEdit, 2)
        incr_icon(self.lineKey.icon, 6)
        self.lineKey.lineEdit.textEdited.connect(self._keyPhraseEdited)

        self.wdgKeyPhraseFrame = frame()
        self.wdgKeyPhraseFrame.setProperty('large-rounded', True)
        self.wdgKeyPhraseFrame.setProperty('muted-bg', True)
        hbox(self.wdgKeyPhraseFrame, 10).addWidget(self.lineKey)

        self.characterSelector = CharacterSelectorButton(self.novel)
        character = entities_registry.character(str(self.agency.character_id))
        if character:
            self.characterSelector.characterSelectorMenu().excludeCharacter(character)
        self.characterSelector.characterSelected.connect(self._characterSelected)

        self.btnResetCharacter = tool_btn(IconRegistry.trash_can_icon('lightgrey'), transparent_=True)
        decr_icon(self.btnResetCharacter, 2)
        self.btnResetCharacter.clicked.connect(self._resetCharacter)

        self.btnConfirm = push_btn(IconRegistry.ok_icon(RELAXED_WHITE_COLOR), 'Confirm',
                                   properties=['confirm', 'positive'])
        self.btnConfirm.clicked.connect(self._confirm)

        self.wdgScope = columns(0, 8)
        margins(self.wdgScope, bottom=35)
        self.wdgScope.layout().addWidget(self.wdgPersonal)
        self.wdgScope.layout().addWidget(vline())
        self.wdgScope.layout().addWidget(self.wdgGlobal)
        self.wdgScope.layout().addWidget(spacer())

        self.wdgFrame.layout().addWidget(
            label(
                "Define the conflict with an optional keyphrase.\nFor interpersonal conflicts, select the character involved in the conflict",
                description=True))

        self.wdgFrame.layout().addWidget(
            group(self.wdgKeyPhraseFrame, label('Interpersonal:', description=True), self.characterSelector,
                  self.btnResetCharacter,
                  margin_left=15), alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgFrame.layout().addWidget(
            wrap(label("Select the scope of the conflict", description=True), margin_top=25))
        self.wdgFrame.layout().addWidget(self.wdgScope)
        self.wdgFrame.layout().addWidget(self.btnConfirm, alignment=Qt.AlignmentFlag.AlignRight)

        btnPersonal = self.__initConflictScope(ConflictType.PERSONAL, self.wdgPersonal)
        incr_font(btnPersonal, 2)
        self.wdgPersonal.layout().addWidget(line())
        self.__initConflictScope(ConflictType.INTERNAL, self.wdgPersonal)
        self.__initConflictScope(ConflictType.MILIEU, self.wdgPersonal)
        btn = self.__initConflictScope(ConflictType.GLOBAL, self.wdgGlobal)
        incr_font(btn, 2)
        self.wdgGlobal.layout().addWidget(line())
        self.__initConflictScope(ConflictType.SOCIAL, self.wdgGlobal)

        self.wdgPersonal.layout().addWidget(vspacer())
        self.wdgGlobal.layout().addWidget(vspacer())

        self.addWidget(self.wdgFrame)

        if self.agency.character_id:
            character = entities_registry.character(str(self.agency.character_id))
            if character:
                btnPersonal.setIcon(avatars.avatar(character))

        if self.conflict.character_id:
            self.characterSelector.setCharacterById(self.conflict.character_id)
        else:
            self.btnResetCharacter.setHidden(True)

        self.lineKey.lineEdit.setFocus()

    def _keyPhraseEdited(self, text: str):
        self.conflict.text = text

    def _scopeChanged(self):
        btn = self.btnGroupConflicts.checkedButton()
        self.conflict.scope = btn.scope

    def _characterSelected(self, character: Character):
        self.conflict.character_id = character.id
        self.btnResetCharacter.setVisible(True)

    def _resetCharacter(self):
        self.characterSelector.clear()
        self.conflict.character_id = None
        self.btnResetCharacter.setHidden(True)

    def _confirm(self):
        self.conflictChanged.emit(self.conflict)

    def __initConflictScope(self, scope: ConflictType, parent: QWidget) -> _ConflictSelectorButton:
        btn = _ConflictSelectorButton(scope)
        self.btnGroupConflicts.addButton(btn)

        if scope == self.conflict.scope:
            btn.setChecked(True)

        parent.layout().addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        return btn


class ConflictReferenceWidget(QWidget):
    removed = pyqtSignal()

    def __init__(self, novel: Novel, agency: CharacterAgency, conflict: Conflict, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.agency = agency
        self.conflict = conflict
        self._contextMenu: Optional[MenuWidget] = None
        self._menu: Optional[MenuWidget] = None

        vbox(self, 0, 0)

        self._iconConflict = tool_btn(QIcon(), transparent_=True)
        incr_icon(self._iconConflict, 2)
        translucent(self._iconConflict, 0.7)
        self._iconConflict.clicked.connect(self._openMenu)

        self._interpersonalCharacterIcon = tool_btn(QIcon(), transparent_=True)
        incr_icon(self._interpersonalCharacterIcon, 8)
        self._interpersonalCharacterIcon.clicked.connect(self._openMenu)

        self._lblConflict = label('', wordWrap=True, color=self.conflict.display_color())
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
        self._textedit.setStyleSheet(
            f'color: {PLACEHOLDER_TEXT_COLOR}; border: 0px; padding: 2px; background-color: rgba(0, 0, 0, 0);')
        self._textedit.setMaximumSize(165, 85)

        self._textedit.setPlaceholderText("What kind of conflict does the character have to face?")
        self._textedit.setText(self.conflict.desc)
        self._textedit.textChanged.connect(self._textChanged)

        self.layout().addWidget(group(self._iconConflict, self._interpersonalCharacterIcon, margin=0, spacing=0),
                                alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._lblConflict)
        self.layout().addWidget(self._textedit)

        self._refresh()

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonRelease:
            self._openMenu()
        return super().eventFilter(watched, event)

    def _textChanged(self):
        self.conflict.desc = self._textedit.toPlainText()

    def _openMenu(self):
        self._contextMenu = MenuWidget()
        self._contextMenu.addAction(action('Edit conflict', IconRegistry.edit_icon(), slot=self._edit))
        self._contextMenu.addSeparator()
        self._contextMenu.addAction(action('Delete', IconRegistry.trash_can_icon(), slot=self.removed))
        self._contextMenu.exec()

    def _edit(self):
        self._menu = ConflictSelectorPopup(self.novel, self.agency, self.conflict)
        self._menu.installEventFilter(MenuOverlayEventFilter(self._menu))
        self._menu.aboutToHide.connect(self._refresh)
        self._menu.conflictChanged.connect(self._menu.hide)
        self._menu.exec()

    def _refresh(self):
        self._lblConflict.setText(self.conflict.display_name())
        self._lblConflict.setStyleSheet(f'color: {self.conflict.display_color()};')
        self._iconConflict.setIcon(IconRegistry.from_name(self.conflict.display_icon(), self.conflict.display_color()))

        if self.conflict.character_id:
            character = entities_registry.character(str(self.conflict.character_id))
            if character:
                self._interpersonalCharacterIcon.setIcon(avatars.avatar(character))

            self._interpersonalCharacterIcon.setVisible(True)
        else:
            self._interpersonalCharacterIcon.setVisible(False)

        self._menu = None
