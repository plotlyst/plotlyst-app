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
from PyQt6.QtWidgets import QPushButton
from qthandy.filter import OpacityEventFilter

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.env import app_env
from plotlyst.event.core import emit_global_event
from plotlyst.events import PreviewFeatureEvent
from plotlyst.view.common import push_btn
from plotlyst.view.icons import IconRegistry


def preview_button(preview: str, parent=None, connect: bool = True) -> QPushButton:
    btnPreview = push_btn(IconRegistry.from_name('fa5s.rocket', RELAXED_WHITE_COLOR), 'TRY IT OUT',
                          properties=['confirm', 'positive'], parent=parent)
    font = btnPreview.font()
    font.setFamily(app_env.serif_font())
    font.setPointSize(font.pointSize() - 1)
    btnPreview.setFont(font)
    btnPreview.installEventFilter(OpacityEventFilter(btnPreview, 0.8, 0.6))

    if connect:
        btnPreview.clicked.connect(lambda: emit_global_event(PreviewFeatureEvent(btnPreview, preview)))

    return btnPreview
