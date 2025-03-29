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
from plotlyst.view.style.theme import BG_SECONDARY_COLOR

style = f'''

QTabWidget::pane[borderless=true] {{
    border-top: 1px solid lightgrey;
}}

QTabWidget::tab-bar:top[centered=false] {{
    top: 1px;
}}

QTabWidget::tab-bar:bottom[centered=false] {{
    bottom: 1px;
}}

QTabWidget::tab-bar:left[centered=false] {{
    right: 1px;
}}

QTabWidget::tab-bar:right[centered=false] {{
    left: 1px;
}}

QTabWidget::tab-bar {{
    alignment: left;
}}

QTabWidget::tab-bar[centered=true] {{
    alignment: center;
}}

QTabBar::tab {{
    border: 1px solid lightgrey;
    border-radius: 3px;
}}

QTabBar::tab:selected {{
    background: #F5F6F8;
}}

QTabBar::tab:!selected {{
    background: #DBDBE7;
}}

QTabBar::tab:!selected:hover {{
    background: #B5B5B5;
}}

QTabBar::tab:top:!selected {{
    margin-top: 3px;
}}

QTabBar::tab:top:!selected:hover {{
    margin-top: 1px;
}}

QTabBar::tab:bottom:!selected {{
    margin-bottom: 3px;
}}

QTabBar::tab:top, QTabBar::tab:bottom {{
    margin-right: -1px;
    padding: 5px 10px 5px 10px;
}}

QTabBar::tab:top:selected {{
    border-bottom-color: none;
}}

QTabBar::tab:bottom:selected {{
    border-top-color: none;
}}

QTabBar::tab:top:last, QTabBar::tab:bottom:last,
QTabBar::tab:top:only-one, QTabBar::tab:bottom:only-one {{
    margin-right: 0;
}}

QTabBar::tab:left:!selected {{
    margin-right: 3px;
}}

QTabBar::tab:right:!selected {{
    margin-left: 3px;
}}

QTabBar::tab:left, QTabBar::tab:right {{
    min-height: 8ex;
    margin-bottom: -1px;
    padding: 5px 5px 5px 5px;
}}

QTabBar::tab:left:selected {{
    border-left-color: none;
}}

QTabBar::tab:right:selected {{
    border-right-color: none;
}}

QTabBar::tab:left:last, QTabBar::tab:right:last,
QTabBar::tab:left:only-one, QTabBar::tab:right:only-one {{
    margin-bottom: 0;
}}

QTabWidget::pane[large-rounded=true] {{
    border: 1px solid lightgrey;
    border-radius: 15px;
}}

QTabWidget::pane[relaxed-white-bg=true] {{
    background-color: {BG_SECONDARY_COLOR};
}}

QTabWidget[transparent=true] {{
    border: 0px;
}}
'''
