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
import pickle
from typing import Optional

import emoji
from PyQt6.QtCore import Qt, QMimeData, QObject, QEvent, QByteArray
from PyQt6.QtGui import QDrag, QMouseEvent
from PyQt6.QtWidgets import QDialog, QToolButton
from overrides import overrides

from src.main.python.plotlyst.core.domain import age_field, gender_field, \
    enneagram_field, TemplateField, TemplateFieldType, ProfileTemplate, goal_field, fear_field, misbelief_field, \
    desire_field, default_character_profiles, role_field, mbti_field, traits_field, Novel
from src.main.python.plotlyst.model.template import TemplateFieldSelectionModel
from src.main.python.plotlyst.view.common import ask_confirmation, emoji_font
from src.main.python.plotlyst.view.generated.character_profile_editor_dialog_ui import Ui_CharacterProfileEditorDialog
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.widget.template import ProfileTemplateEditor
from src.main.python.plotlyst.worker.persistence import RepositoryPersistenceManager


class CharacterProfileEditorDialog(Ui_CharacterProfileEditorDialog, QDialog):
    MimeType: str = 'application/template-field'

    def __init__(self, profile: ProfileTemplate, parent=None):
        super().__init__(parent)

        self.setupUi(self)
        self.profile = profile
        self._restore_requested: bool = False

        self.btnAge.setIcon(IconRegistry.from_name('mdi.numeric'))
        self.btnGender.setIcon(IconRegistry.from_name('mdi.gender-female', color='#fface4'))
        self.btnRole.setIcon(IconRegistry.from_name('fa5s.user-tag'))
        self.btnFear.setIcon(IconRegistry.from_name('mdi.spider-thread'))
        self.btnGoal.setIcon(IconRegistry.goal_icon())
        self.btnEnneagram.setIcon(IconRegistry.from_name('mdi.numeric-9-box-outline'))
        self.btnMbti.setIcon(IconRegistry.from_name('ei.group-alt'))
        self.btnTraits.setIcon(IconRegistry.from_name('ei.adjust'))
        self.btnDesire.setIcon(IconRegistry.from_name('fa5s.coins', color='#e1bc29'))
        self.btnMisbelief.setIcon(IconRegistry.error_icon())
        self.btnCustomText.setIcon(IconRegistry.from_name('mdi.format-text'))
        self.btnCustomNumber.setIcon(IconRegistry.from_name('mdi.numeric'))
        self.btnCustomChoices.setIcon(IconRegistry.from_name('mdi.format-list-bulleted-type'))

        self.btnSettings.setIcon(IconRegistry.from_name('ei.cog'))
        self.btnSettings.toggled.connect(self.wdgSettings.setVisible)

        self.profile_editor = ProfileTemplateEditor(self.profile)
        self.wdgEditor.layout().addWidget(self.profile_editor)

        self.btnRestore.setIcon(IconRegistry.restore_alert_icon('white'))
        self.btnRestore.clicked.connect(self._restore_default)

        for w in self.profile_editor.widgets:
            self._field_added(w.field)

        self._selected_field: Optional[TemplateField] = None

        self.profile_editor.fieldAdded.connect(self._field_added)
        self.profile_editor.fieldSelected.connect(self._field_selected)
        self.profile_editor.placeholderSelected.connect(self._placeholder_selected)
        self.btnRemove.setIcon(IconRegistry.minus_icon())
        self.btnRemove.clicked.connect(self._remove_field)

        self.lineLabel.textEdited.connect(self._label_edited)
        self.lineEmoji.setFont(emoji_font(16))
        self.lineEmoji.textEdited.connect(self._emoji_edited)

        self.btnAge.installEventFilter(self)
        self.btnGender.installEventFilter(self)
        self.btnRole.installEventFilter(self)
        self.btnFear.installEventFilter(self)
        self.btnGoal.installEventFilter(self)
        self.btnEnneagram.installEventFilter(self)
        self.btnMbti.installEventFilter(self)
        self.btnTraits.installEventFilter(self)
        self.btnDesire.installEventFilter(self)
        self.btnMisbelief.installEventFilter(self)
        self.btnCustomText.installEventFilter(self)
        self.btnCustomNumber.installEventFilter(self)
        self.btnCustomChoices.installEventFilter(self)

        self._dragged: Optional[QToolButton] = None
        self.cbShowLabel.clicked.connect(self._show_label_clicked)
        self.btnCancel.clicked.connect(self.reject)
        self.btnSave.clicked.connect(self.accept)

        self.stackedSettings.setCurrentWidget(self.pageInfo)

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        self._dragged = watched
        if event.type() == QEvent.Type.MouseButtonPress:
            self.mousePressEvent(event)
        elif event.type() == QEvent.Type.MouseMove:
            self.mouseMoveEvent(event)
        elif event.type() == QEvent.Type.MouseButtonRelease:
            self.mouseReleaseEvent(event)
        return super().eventFilter(watched, event)

    @overrides
    def mousePressEvent(self, event: QMouseEvent):
        self._dragged = None

    @overrides
    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton and self._dragged and self._dragged.isEnabled():
            drag = QDrag(self._dragged)
            pix = self._dragged.grab()
            if self._dragged is self.btnAge:
                field = age_field
            elif self._dragged is self.btnGender:
                field = gender_field
            elif self._dragged is self.btnRole:
                field = role_field
            elif self._dragged is self.btnEnneagram:
                field = enneagram_field
            elif self._dragged is self.btnMbti:
                field = mbti_field
            elif self._dragged is self.btnTraits:
                field = traits_field
            elif self._dragged is self.btnGoal:
                field = goal_field
            elif self._dragged is self.btnFear:
                field = fear_field
            elif self._dragged is self.btnMisbelief:
                field = misbelief_field
            elif self._dragged is self.btnDesire:
                field = desire_field
            elif self._dragged is self.btnCustomText:
                field = TemplateField(name='Label', type=TemplateFieldType.TEXT, custom=True)
            elif self._dragged is self.btnCustomNumber:
                field = TemplateField(name='Label', type=TemplateFieldType.NUMERIC, custom=True, compact=True)
            elif self._dragged is self.btnCustomChoices:
                field = TemplateField(name='Label', type=TemplateFieldType.TEXT_SELECTION, custom=True, compact=True)
            else:
                field = TemplateField(name=self._dragged.text(), type=TemplateFieldType.TEXT)
            mimedata = QMimeData()
            mimedata.setData(self.MimeType, QByteArray(pickle.dumps(field)))
            drag.setMimeData(mimedata)
            drag.setPixmap(pix)
            drag.setHotSpot(event.pos())
            drag.destroyed.connect(self._dragDestroyed)
            drag.exec()

    def display(self) -> Optional[ProfileTemplate]:
        result = self.exec()

        if result == QDialog.DialogCode.Rejected:
            return None
        if self._restore_requested:
            return default_character_profiles()[0]
        return self.profile_editor.profile()

    def _dragDestroyed(self):
        self._dragged = None

    def _field_added(self, field: TemplateField):
        self._enable_in_inventory(field, False)
        if field.custom:
            self.btnSettings.setChecked(True)

    def _enable_in_inventory(self, field: TemplateField, enabled: bool):
        if field.id == age_field.id:
            self.btnAge.setEnabled(enabled)
        elif field.id == gender_field.id:
            self.btnGender.setEnabled(enabled)
        elif field.id == role_field.id:
            self.btnRole.setEnabled(enabled)
        elif field.id == enneagram_field.id:
            self.btnEnneagram.setEnabled(enabled)
        elif field.id == mbti_field.id:
            self.btnMbti.setEnabled(enabled)
        elif field.id == traits_field.id:
            self.btnTraits.setEnabled(enabled)
        elif field.id == goal_field.id:
            self.btnGoal.setEnabled(enabled)
        elif field.id == fear_field.id:
            self.btnFear.setEnabled(enabled)
        elif field.id == desire_field.id:
            self.btnDesire.setEnabled(enabled)
        elif field.id == misbelief_field.id:
            self.btnMisbelief.setEnabled(enabled)

    def _field_selected(self, field: TemplateField):
        self._selected_field = field
        self.stackedSettings.setCurrentWidget(self.pageSettings)
        self.btnRemove.setVisible(not field.frozen)
        self.btnRemove.setEnabled(not field.frozen)
        self.cbShowLabel.setChecked(field.show_label)
        self.lineLabel.setText(field.name)
        if field.emoji:
            self.lineEmoji.setText(emoji.emojize(field.emoji))
        else:
            self.lineEmoji.clear()
        if field.custom:
            if field.type == TemplateFieldType.TEXT_SELECTION:
                self.wdgChoicesEditor.setModel(TemplateFieldSelectionModel(field))
                self.wdgChoicesEditor.setVisible(True)
            else:
                self.wdgChoicesEditor.setHidden(True)
        else:
            self.wdgChoicesEditor.setHidden(True)

    def _placeholder_selected(self):
        self._selected_field = None
        self.stackedSettings.setCurrentWidget(self.pageInfo)
        self.btnRemove.setDisabled(True)

    def _remove_field(self):
        self._enable_in_inventory(self._selected_field, True)
        self.profile_editor.removeSelected()
        self._selected_field = None
        self.stackedSettings.setCurrentWidget(self.pageInfo)
        self.btnRemove.setDisabled(True)

    def _restore_default(self):
        if ask_confirmation('Are you sure you want to restore the default profile? Your current changes will be lost.'):
            self._restore_requested = True
            self.accept()

    def _show_label_clicked(self, checked: bool):
        if self._selected_field:
            self._selected_field.show_label = checked
            self.profile_editor.setShowLabelForSelected(checked)
            if self._selected_field.custom:
                self.lineLabel.setEnabled(checked)

    def _label_edited(self, text: str):
        if self._selected_field:
            self._selected_field.name = text
            self.profile_editor.updateLabelForSelected(text)

    def _emoji_edited(self, emoji_str: str):
        alias = emoji.demojize(emoji_str)
        if alias.startswith(':'):
            self._selected_field.emoji = alias
            self.profile_editor.updateEmojiForSelected(alias)
        else:
            self.lineEmoji.clear()


def customize_character_profile(novel: Novel, index: int, parent=None) -> bool:
    profile = CharacterProfileEditorDialog(novel.character_profiles[index],
                                           parent).display()
    if profile:
        novel.character_profiles[index] = profile
        RepositoryPersistenceManager.instance().update_novel(novel)

        return True
    return False
