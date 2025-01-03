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

from PyQt6.QtWidgets import QWidget
from qthandy import hbox, vbox, margins


def group(*widgets, vertical: bool = True, margin: int = 2, spacing: int = 3, margin_top: int = 0, margin_left: int = 0,
          margin_right: int = 0,
          parent=None) -> QWidget:
    container = QWidget(parent)
    if vertical:
        hbox(container, margin, spacing)
    else:
        vbox(container, margin, spacing)

    if margin_top:
        margins(container, top=margin_top)
    if margin_left:
        margins(container, left=margin_left)
    if margin_right:
        margins(container, right=margin_right)

    for w in widgets:
        container.layout().addWidget(w)
    return container
