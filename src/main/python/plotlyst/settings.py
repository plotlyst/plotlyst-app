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
from typing import Optional, List, Dict

from PyQt6.QtCore import QCoreApplication, QSettings


class AppSettings:
    WORKSPACE = 'workspace'
    LAUNCHED_BEFORE = 'launchedBefore'
    LAST_NOVEL_ID = 'lastNovelId'
    TOOLBAR_QUICK_SETTINGS = 'toolbarQuickSettings'
    WORLDBUILDING_EDITOR_MAX_WIDTH = 'worldbuildingEditorMaxWidth'

    def __init__(self):
        self._settings: QSettings = QSettings()

    def init_org(self):
        QCoreApplication.setOrganizationName('Plotlyst')
        QCoreApplication.setOrganizationDomain('plotlyst.com')
        QCoreApplication.setApplicationName('Plotlyst')
        self._settings = QSettings()

    def clear(self):
        self._settings.clear()

    def workspace(self) -> Optional[str]:
        return self._settings.value(self.WORKSPACE)

    def set_workspace(self, value: str):
        self._settings.setValue(self.WORKSPACE, value)

    def first_launch(self) -> bool:
        return not self._settings.value(self.LAUNCHED_BEFORE, False)

    def set_launched_before(self):
        self._settings.setValue(self.LAUNCHED_BEFORE, True)

    def last_novel_id(self) -> Optional[int]:
        return self._settings.value(self.LAST_NOVEL_ID)

    def set_last_novel_id(self, value: int):
        self._settings.setValue(self.LAST_NOVEL_ID, value)

    def hint_showed(self, hint_id: str) -> bool:
        return self._settings.value(hint_id) == 'true'

    def set_hint_showed(self, hint_id: str):
        self._settings.setValue(hint_id, 'true')

    def reset_hint_showed(self, hint_id: str):
        self._settings.remove(hint_id)

    def toolbar_quick_settings(self) -> bool:
        return self._settings.value(self.TOOLBAR_QUICK_SETTINGS, True, type=bool)

    def set_toolbar_quick_settings(self, visible: bool):
        self._settings.setValue(self.TOOLBAR_QUICK_SETTINGS, visible)

    def worldbuilding_editor_max_width(self) -> int:
        return self._settings.value(self.WORLDBUILDING_EDITOR_MAX_WIDTH, 1000, type=int)

    def set_worldbuilding_editor_max_width(self, value: int):
        self._settings.setValue(self.WORLDBUILDING_EDITOR_MAX_WIDTH, value)


settings = AppSettings()

STORY_LINE_COLOR_CODES: Dict[str, List[str]] = {
    'main': [
        '#03396c',  # yale blue
        '#338740',  # sea green
        '#cc3363',  # dogwood rose
        '#b388eb',  # lavender
        '#6d597a',  # chinese violate
        '#FAAE4A',  # princeton orange
        '#F50574',  # rose
    ],
    'internal': [
        '#0FADBB',  # moonstone
        '#e8c2ca',  # fairy tale
        '#fcd5ce',  # pale dogwood
    ],
    'subplot': [
        '#d4a373',  # buff
        '#b7b7a4',  # ash grey
        '#D48172',  # coral pink
        '#93a8ac',  # cadet grey
    ],
    'relation': [
        '#cdb4db',  # thistle
        '#b56576'  # china rose
    ],
    'global': [
        'black'
    ]

}

CHARACTER_INITIAL_AVATAR_COLOR_CODES: List[str] = [
    '#03396c',  # Deep navy blue
    '#0e9aa7',  # Bright teal
    '#62c370',  # Fresh green
    '#cc3363',  # Deep magenta
    '#4db6ac',  # Light teal
    '#1b5e20',  # Forest green
    '#00796b',  # Muted green-teal
    '#62a6e5',  # Sky blue
    '#007bb8',  # Bright blue
    '#81c784',  # Light green

    '#4e342e',  # Dark brown
    '#6f9b5a',  # Olive green
    '#e57373',  # Warm muted red
    '#b388eb',  # Soft lavender
    '#ff6f61',  # Coral red
    '#795548',  # Brown

    '#9575cd',  # Muted purple
    '#26a69a',  # Teal
    '#7986cb',  # Periwinkle
    '#4caf50',  # Medium green

    '#f06292',  # Hot pink
    '#81d4fa',  # Light blue
    '#ef5350',  # Light red
    '#7b1fa2',  # Dark magenta
    '#455a64',  # Dark cyan
    '#bdbdbd',  # Gray
    '#90a4ae',  # Cool gray
    '#9c27b0',  # Rich purple

    '#c2185b',  # Dark pink
    '#ff9800',  # Bright orange
    '#e1bee7',  # Pale violet
    '#8bc34a',  # Lime green
    '#ffc107',  # Soft amber
]
