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
from dataclasses import dataclass

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QDialog, QWidget
from qthandy import hbox, sp, vbox

from plotlyst.common import RELAXED_WHITE_COLOR, DECONSTRUCTIVE_COLOR, PLOTLYST_SECONDARY_COLOR
from plotlyst.view.common import label, push_btn
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.display import PopupDialog, Icon


@dataclass
class ConfirmationResult:
    confirmed: bool


class BaseDialog(PopupDialog):
    def __init__(self, message: str, title: str = 'Confirm?', parent=None):
        super().__init__(parent)
        self.wdgText = QWidget()
        vbox(self.wdgText, spacing=6)
        self.title = label(title, h4=True, wordWrap=True)
        sp(self.title).v_max()
        self.text = label(message, wordWrap=True, description=True)
        self.text.setMinimumWidth(300)
        self.wdgText.layout().addWidget(self.title)
        self.wdgText.layout().addWidget(self.text)

        self.wdgCenter = QWidget()
        hbox(self.wdgCenter)
        self.icon = Icon()
        self.icon.setIconSize(QSize(40, 40))
        self.wdgCenter.layout().addWidget(self.icon, alignment=Qt.AlignmentFlag.AlignTop)
        self.wdgCenter.layout().addWidget(self.wdgText)
        self.wdgCenter.layout().addWidget(self.btnReset,
                                          alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        self.btnConfirm = push_btn(text='Confirm', properties=['confirm'])
        self.btnConfirm.clicked.connect(self.accept)
        self.btnCancel = push_btn(QIcon(), text='Cancel', properties=['confirm', 'cancel'])
        self.btnCancel.clicked.connect(self.reject)
        self.btnCancel.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.btnConfirm.setFocus()

        self.frame.layout().addWidget(self.wdgCenter)
        self.frame.layout().addWidget(group(self.btnCancel, self.btnConfirm, spacing=6),
                                      alignment=Qt.AlignmentFlag.AlignRight)
        # self.frame.layout().addWidget(line())
        # self.frame.layout().addWidget(vspacer())

    def display(self) -> ConfirmationResult:
        result = self.exec()

        if result == QDialog.DialogCode.Accepted:
            return ConfirmationResult(True)

        return ConfirmationResult(False)


class ConfirmationDialog(BaseDialog):
    def __init__(self, message: str, title: str = 'Confirm?', parent=None):
        super().__init__(message, title, parent)

        self.icon.setIcon(IconRegistry.from_name('ph.warning-circle-fill', DECONSTRUCTIVE_COLOR))
        self.btnConfirm.setProperty('deconstructive', True)
        self.btnConfirm.setText('Delete')
        self.btnConfirm.setIcon(IconRegistry.trash_can_icon(RELAXED_WHITE_COLOR))

    @classmethod
    def confirm(cls, message: str, title: str = 'Confirm?') -> bool:
        return cls.popup(message, title).confirmed


class QuestionDialog(BaseDialog):
    def __init__(self, message: str, title: str, btnConfirmText: str, btnCancelText: str,
                 parent=None):
        super().__init__(message, title, parent)
        self.icon.setIcon(IconRegistry.from_name('fa5s.question', PLOTLYST_SECONDARY_COLOR))
        self.btnConfirm.setText(btnConfirmText)
        self.btnCancel.setText(btnCancelText)
        self.btnConfirm.setProperty('positive', True)

    @classmethod
    def ask(cls, message: str, title: str, btnConfirmText: str, btnCancelText: str) -> bool:
        return cls.popup(message, title, btnConfirmText, btnCancelText).confirmed


def confirmed(message: str, title: str = 'Confirm?') -> bool:
    return ConfirmationDialog.confirm(message, title)


def asked(message: str, title: str, btnConfirmText: str = 'Confirm', btnCancelText: str = 'Cancel') -> bool:
    return QuestionDialog.ask(message, title, btnConfirmText, btnCancelText)
