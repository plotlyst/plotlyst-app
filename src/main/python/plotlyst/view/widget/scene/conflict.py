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
from typing import Optional

import qtanim
from PyQt6.QtCore import pyqtSignal, Qt, QEvent, QObject
from PyQt6.QtGui import QMouseEvent, QResizeEvent
from PyQt6.QtWidgets import QWidget, QSlider, QHeaderView, QFrame, QTextEdit
from overrides import overrides
from qthandy import hbox, vbox, incr_icon, pointy, incr_font
from qthandy.filter import DisabledClickEventFilter, VisibilityToggleEventFilter

from plotlyst.common import RELAXED_WHITE_COLOR, PLACEHOLDER_TEXT_COLOR
from plotlyst.core.domain import Conflict, ConflictReference, Novel, Scene, ConflictType, \
    CharacterAgency, Character
from plotlyst.env import app_env
from plotlyst.event.core import emit_critical
from plotlyst.model.scenes_model import SceneConflictsModel
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import tool_btn, label
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.characters import CharacterSelectorButton
from plotlyst.view.widget.input import RemovalButton


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


class ConflictSelectorWidget(QFrame):
    conflictSelectionChanged = pyqtSignal()

    def __init__(self, novel: Novel, scene: Scene, agenda: CharacterAgency, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.scene = scene
        self.agenda = agenda
        self._character: Optional[Character] = None

        self.repo = RepositoryPersistenceManager.instance()

        self.btnCharacter.setIcon(IconRegistry.conflict_character_icon())
        self.btnCharacter.setToolTip('<b style="color:#c1666b">Character</b>')
        self.btnSociety.setIcon(IconRegistry.conflict_society_icon())
        self.btnSociety.setToolTip('<b style="color:#69306d">Society</b>')
        self.btnNature.setIcon(IconRegistry.conflict_nature_icon())
        self.btnNature.setToolTip('<b style="color:#157a6e">Nature</b>')
        self.btnTechnology.setIcon(IconRegistry.conflict_technology_icon())
        self.btnTechnology.setToolTip('<b style="color:#4a5859">Technology</b>')
        self.btnSupernatural.setIcon(IconRegistry.conflict_supernatural_icon())
        self.btnSupernatural.setToolTip('<b style="color:#ac7b84">Supernatural</b>')
        self.btnSelf.setIcon(IconRegistry.conflict_self_icon())
        self.btnSelf.setToolTip('<b style="color:#94b0da">Self</b>')

        self._model = SceneConflictsModel(self.novel, self.scene, self.agenda)
        self._model.setCheckable(True, SceneConflictsModel.ColName)
        self._model.selection_changed.connect(self._previousConflictSelected)
        self.tblConflicts.setModel(self._model)
        self.tblConflicts.horizontalHeader().hideSection(SceneConflictsModel.ColBgColor)
        self.tblConflicts.horizontalHeader().setSectionResizeMode(SceneConflictsModel.ColIcon,
                                                                  QHeaderView.ResizeMode.ResizeToContents)
        self.tblConflicts.horizontalHeader().setSectionResizeMode(SceneConflictsModel.ColName,
                                                                  QHeaderView.ResizeMode.Stretch)

        self.btnCharacterSelector = CharacterSelectorButton(self.novel)
        self.btnCharacterSelector.characterSelected.connect(self._characterSelected)
        self.wdgEditor.layout().insertWidget(0, self.btnCharacterSelector)
        self.btnAddNew.setIcon(IconRegistry.ok_icon(RELAXED_WHITE_COLOR))
        self.btnAddNew.installEventFilter(DisabledClickEventFilter(self, lambda: qtanim.shake(self.wdgEditor)))
        self.btnAddNew.setDisabled(True)

        self.lineKey.textChanged.connect(self._changed)

        self.btnGroupConflicts.buttonToggled.connect(self._typeToggled)
        self._type = ConflictType.CHARACTER
        self.btnCharacter.setChecked(True)

        self.btnAddNew.clicked.connect(self._addNew)

        self.toolBox.setCurrentWidget(self.pageNew)

    def refresh(self):
        self.btnCharacterSelector.clear()
        self._character = None
        self.tblConflicts.model().update()
        self.tblConflicts.model().modelReset.emit()

    @overrides
    def mousePressEvent(self, event: QMouseEvent) -> None:
        pass

    def _typeToggled(self):
        lbl_prefix = 'Character vs.'
        self.btnCharacterSelector.setVisible(self.btnCharacter.isChecked())
        if self.btnCharacter.isChecked():
            self.lblConflictType.setText(f'{lbl_prefix} <b style="color:#c1666b">Character</b>')
            self._type = ConflictType.CHARACTER
        elif self.btnSociety.isChecked():
            self.lblConflictType.setText(f'{lbl_prefix} <b style="color:#69306d">Society</b>')
            self._type = ConflictType.SOCIETY
        elif self.btnNature.isChecked():
            self.lblConflictType.setText(f'{lbl_prefix} <b style="color:#157a6e">Nature</b>')
            self._type = ConflictType.NATURE
        elif self.btnTechnology.isChecked():
            self.lblConflictType.setText(f'{lbl_prefix} <b style="color:#4a5859">Technology</b>')
            self._type = ConflictType.TECHNOLOGY
        elif self.btnSupernatural.isChecked():
            self.lblConflictType.setText(f'{lbl_prefix} <b style="color:#ac7b84">Supernatural</b>')
            self._type = ConflictType.SUPERNATURAL
        elif self.btnSelf.isChecked():
            self.lblConflictType.setText(f'{lbl_prefix} <b style="color:#94b0da">Self</b>')
            self._type = ConflictType.SELF

        self._changed()

    def _characterSelected(self, character: Character):
        self._character = character
        self._changed()

    def _changed(self):
        if len(self.lineKey.text()) > 0:
            if self.btnCharacter.isChecked() and not self._character:
                self.btnAddNew.setEnabled(False)
            else:
                self.btnAddNew.setEnabled(True)
        else:
            self.btnAddNew.setEnabled(False)

    def _addNew(self):
        if not self.agenda.character_id:
            return emit_critical('Select agenda or POV character first')
        conflict = Conflict(self.lineKey.text(), self._type, character_id=self.agenda.character_id)
        if self._type == ConflictType.CHARACTER and self._character:
            conflict.conflicting_character_id = self._character.id

        self.novel.conflicts.append(conflict)
        self.agenda.conflict_references.append(ConflictReference(conflict.id))
        self.repo.update_novel(self.novel)
        self.conflictSelectionChanged.emit()
        self.refresh()
        self.lineKey.clear()

    def _previousConflictSelected(self):
        conflicts = self._model.selections()
        conflict: Conflict = conflicts.pop()
        self.agenda.conflict_references.append(ConflictReference(conflict.id))
        self.conflictSelectionChanged.emit()


class ConflictReferenceWidget(QWidget):
    removed = pyqtSignal()

    def __init__(self, ref: ConflictReference, conflict: Conflict, parent=None):
        super().__init__(parent)
        self.ref = ref
        self.conflict = conflict

        vbox(self, 0, 0)

        self._btnRemove = RemovalButton(self)
        self._btnRemove.clicked.connect(self.removed)
        self._btnRemove.setHidden(True)

        self._iconConflict = tool_btn(IconRegistry.conflict_society_icon(), transparent_=True)
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
        self._textedit.setText(self.ref.message)
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
        self.ref.message = self._textedit.toPlainText()

    def _edit(self):
        pass

# class CharacterConflictSelector(QWidget):
#     conflictSelected = pyqtSignal()
#
#     def __init__(self, novel: Novel, scene: Scene, agenda: CharacterAgency, parent=None):
#         super().__init__(parent)
#         self.novel = novel
#         self.scene = scene
#         self.agenda = agenda
#         self.conflict: Optional[Conflict] = None
#         self.conflict_ref: Optional[ConflictReference] = None
#         hbox(self)
#
#         self.label: Optional[ConflictLabel] = None
#
#         self.btnLinkConflict = push_btn(IconRegistry.conflict_icon(), 'Track conflict')
#         self.layout().addWidget(self.btnLinkConflict)
#         self.btnLinkConflict.setIcon(IconRegistry.conflict_icon())
#         self.btnLinkConflict.setObjectName('btnSelector')
#         self.btnLinkConflict.setStyleSheet('''
#                         #btnSelector::menu-indicator {
#                             width: 0px;
#                         }
#                         #btnSelector {
#                             border: 2px dotted grey;
#                             border-radius: 6px;
#                             font: italic;
#                         }
#                         #btnSelector:hover {
#                             border: 2px dotted orange;
#                             color: orange;
#                             font: normal;
#                         }
#                         #btnSelector:pressed {
#                             border: 2px solid white;
#                         }
#                     ''')
#
#         self.btnLinkConflict.installEventFilter(OpacityEventFilter(parent=self.btnLinkConflict))
#         self.selectorWidget = CharacterConflictWidget(self.novel, self.scene, self.agenda)
#         self._menu = MenuWidget(self.btnLinkConflict)
#         self._menu.addWidget(self.selectorWidget)
#
#         self.selectorWidget.conflictSelectionChanged.connect(self._conflictSelected)
#
#     def setConflict(self, conflict: Conflict, conflict_ref: ConflictReference):
#         self.conflict = conflict
#         self.conflict_ref = conflict_ref
#         self.label = ConflictLabel(self.novel, self.conflict)
#         self.label.removalRequested.connect(self._remove)
#         self.label.clicked.connect(self._conflictRefClicked)
#         self.layout().addWidget(self.label)
#         self.btnLinkConflict.setHidden(True)
#
#     def _conflictSelected(self):
#         self._menu.hide()
#         new_conflict = self.agenda.conflicts(self.novel)[-1]
#         new_conflict_ref = self.agenda.conflict_references[-1]
#         # self.btnLinkConflict.menu().hide()
#         self.setConflict(new_conflict, new_conflict_ref)
#
#         self.conflictSelected.emit()
#
#     def _conflictRefClicked(self):
#         pass
#
#     def _remove(self):
#         if self.parent():
#             anim = qtanim.fade_out(self, duration=150)
#             anim.finished.connect(self.__destroy)
#
#     def __destroy(self):
#         self.agenda.remove_conflict(self.conflict)
#         self.parent().layout().removeWidget(self)
#         gc(self)
