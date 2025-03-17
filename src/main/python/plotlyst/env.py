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
import os
import subprocess
from enum import Enum

import nltk
from fbs_runtime import platform


class AppMode(Enum):
    DEV = 0
    PROD = 1


class AppEnvironment:
    def __init__(self):
        self._mode: AppMode = AppMode.PROD
        self._novel = None
        self._plotlyst_cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'plotlyst')
        self._nltk_data = os.path.join(self._plotlyst_cache_dir, 'nltk')
        nltk.data.path.insert(0, self._nltk_data)
        os.environ['LTP_PATH'] = os.path.join(self._plotlyst_cache_dir, 'language_tool_python')

        self._profile = {}

    @property
    def mode(self) -> AppMode:
        return self._mode

    @mode.setter
    def mode(self, value: AppMode):
        self._mode = value

    @property
    def novel(self):
        return self._novel

    @novel.setter
    def novel(self, novel):
        self._novel = novel

    @property
    def cache_dir(self) -> str:
        return self._plotlyst_cache_dir

    @property
    def nltk_data(self) -> str:
        return self._nltk_data

    def is_dev(self) -> bool:
        return self._mode == AppMode.DEV

    def is_prod(self) -> bool:
        return self._mode == AppMode.PROD

    def is_plus(self) -> bool:
        return False

    def test_env(self) -> bool:
        if os.getenv('PLOTLYST_TEST_ENV'):
            return True
        return False

    def platform(self) -> str:
        return platform.name()

    def is_mac(self) -> bool:
        return platform.is_mac()

    def is_linux(self) -> bool:
        return platform.is_linux()

    def is_windows(self) -> bool:
        return platform.is_windows()

    def sans_serif_font(self) -> str:
        if self.is_linux():
            return 'Sans Serif'
        elif self.is_mac():
            return 'Helvetica'
        elif self.is_windows():
            return 'Segoe UI'

    def serif_font(self) -> str:
        if self.is_linux():
            return 'Serif'
        elif self.is_mac():
            return 'Times New Roman'
        elif self.is_windows():
            return 'Times New Roman'

    def mono_font(self) -> str:
        if self.is_linux():
            return 'Monospace'
        elif self.is_mac():
            return 'Courier New'
        elif self.is_windows():
            return 'Courier New'

    def cursive_font(self) -> str:
        if self.is_linux():
            return 'Cursive'
        elif self.is_mac():
            return 'Apple Chancery'
        elif self.is_windows():
            return 'Segoe Print'

    def profile(self):
        return self._profile

    def setProfile(self, profile):
        self._profile = profile


app_env = AppEnvironment()


def open_location(location: str):
    if not location:
        return

    if app_env.is_windows():
        os.system("start " + location)
    elif app_env.is_linux():
        subprocess.run(["xdg-open", location])
    elif app_env.is_mac():
        os.system("open " + location)
