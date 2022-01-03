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
from typing import Optional

import emoji
from PyQt6.QtWidgets import QDialog
from fbs_runtime import platform

from src.main.python.plotlyst.core.domain import BackstoryEvent, NEUTRAL, VERY_HAPPY, VERY_UNHAPPY, UNHAPPY, HAPPY
from src.main.python.plotlyst.view.common import emoji_font
from src.main.python.plotlyst.view.generated.backstory_editor_dialog_ui import Ui_BackstoryEditorDialog
from src.main.python.plotlyst.view.icons import IconRegistry


class BackstoryEditorDialog(QDialog, Ui_BackstoryEditorDialog):
    def __init__(self, backstory: Optional[BackstoryEvent] = None, parent=None):
        super(BackstoryEditorDialog, self).__init__(parent)
        self.setupUi(self)

        self.btnBaby.setIcon(IconRegistry.baby_icon())
        self.btnChild.setIcon(IconRegistry.child_icon())
        self.btnTeenager.setIcon(IconRegistry.teenager_icon())
        self.btnAdult.setIcon(IconRegistry.adult_icon())
        self.btnGroupAge.buttonToggled.connect(self._btn_age_toggled)
        self.btnAdult.setChecked(True)

        if platform.is_windows():
            self._emoji_font = emoji_font(14)
        else:
            self._emoji_font = emoji_font(20)

        self.btnVeryUnhappy.setFont(self._emoji_font)
        self.btnVeryUnhappy.setText(emoji.emojize(':fearful_face:'))
        self.btnUnHappy.setFont(self._emoji_font)
        self.btnUnHappy.setText(emoji.emojize(':worried_face:'))
        self.btnNeutral.setFont(self._emoji_font)
        self.btnNeutral.setText(emoji.emojize(':neutral_face:'))
        self.btnHappy.setFont(self._emoji_font)
        self.btnHappy.setText(emoji.emojize(':slightly_smiling_face:'))
        self.btnVeryHappy.setFont(self._emoji_font)
        self.btnVeryHappy.setText(emoji.emojize(':smiling_face_with_smiling_eyes:'))

        self.lineKeyphrase.textChanged.connect(lambda x: self.btnSave.setEnabled(len(x) > 0))
        self.sbAge.valueChanged.connect(self._age_changed)

        self.btnSave.setDisabled(True)
        self.btnSave.clicked.connect(self.accept)
        self.btnClose.clicked.connect(self.reject)

        if backstory:
            self.lineKeyphrase.setText(backstory.keyphrase)
            if backstory.age > 0:
                self.sbAge.setValue(backstory.age)
            elif backstory.as_baby:
                self.btnBaby.setChecked(True)
            elif backstory.as_child:
                self.btnChild.setChecked(True)
            elif backstory.as_teenager:
                self.btnTeenager.setChecked(True)
            elif backstory.as_adult:
                self.btnAdult.setChecked(True)

            if backstory.emotion == VERY_UNHAPPY:
                self.btnVeryUnhappy.setChecked(True)
            if backstory.emotion == UNHAPPY:
                self.btnUnHappy.setChecked(True)
            if backstory.emotion == NEUTRAL:
                self.btnNeutral.setChecked(True)
            if backstory.emotion == HAPPY:
                self.btnHappy.setChecked(True)
            if backstory.emotion == VERY_HAPPY:
                self.btnVeryHappy.setChecked(True)

    def display(self) -> Optional[BackstoryEvent]:
        result = self.exec()
        if result == QDialog.DialogCode.Rejected:
            return None

        emotion = NEUTRAL
        if self.btnVeryUnhappy.isChecked():
            emotion = VERY_UNHAPPY
        elif self.btnUnHappy.isChecked():
            emotion = UNHAPPY
        elif self.btnHappy.isChecked():
            emotion = HAPPY
        elif self.btnVeryHappy.isChecked():
            emotion = VERY_HAPPY

        return BackstoryEvent(self.lineKeyphrase.text(), synopsis='', age=self.sbAge.value(), emotion=emotion,
                              as_baby=self.btnBaby.isChecked(), as_child=self.btnChild.isChecked(),
                              as_teenager=self.btnTeenager.isChecked(), as_adult=self.btnAdult.isChecked())

    def _age_changed(self, value: int):
        if 0 < value <= 3:
            self.btnBaby.setChecked(True)
        elif 3 < value <= 12:
            self.btnChild.setChecked(True)
        elif 12 < value <= 18:
            self.btnTeenager.setChecked(True)
        elif value > 18:
            self.btnAdult.setChecked(True)

        self.lblAge.setText(str(value))

    def _btn_age_toggled(self):
        if self.btnBaby.isChecked():
            self.lblAge.setText('0-3')
        elif self.btnChild.isChecked():
            self.lblAge.setText('3-12')
        elif self.btnTeenager.isChecked():
            self.lblAge.setText('12-18')
        elif self.btnAdult.isChecked():
            self.lblAge.setText('Adulthood')
