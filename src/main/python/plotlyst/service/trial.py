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
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton
from qthandy.filter import OpacityEventFilter

from plotlyst.common import RELAXED_WHITE_COLOR, DEFAULT_PREMIUM_LINK
from plotlyst.env import app_env
from plotlyst.view.common import push_btn, open_url
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.confirm import asked
from plotlyst.view.widget.display import PopupDialog


class TrialPopup(PopupDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.btnClose = push_btn(IconRegistry.from_name('ei.remove'), 'Close', properties=['confirm', 'cancel'])
        self.btnClose.clicked.connect(self.reject)

        self.frame.layout().addWidget(self.btnClose, alignment=Qt.AlignmentFlag.AlignRight)

    def display(self):
        self.exec()


def launch_trial(trial: str):
    if trial == 'mindmap':
        TrialPopup.popup()
    else:
        if asked("To try this feature out, please upgrade to the latest version of Plotlyst.", 'Old Plotlyst version',
                 btnConfirmText='Understood', btnCancelText='Close'):
            open_url(DEFAULT_PREMIUM_LINK)


def trial_button(trial: str) -> QPushButton:
    btnTrial = push_btn(IconRegistry.from_name('fa5s.rocket', RELAXED_WHITE_COLOR), 'TRY IT OUT',
                        properties=['confirm', 'positive'])
    font = btnTrial.font()
    font.setFamily(app_env.serif_font())
    font.setPointSize(font.pointSize() - 1)
    btnTrial.setFont(font)
    btnTrial.installEventFilter(OpacityEventFilter(btnTrial, 0.8, 0.6))

    btnTrial.clicked.connect(lambda: launch_trial(trial))

    return btnTrial
