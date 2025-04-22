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
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QMessageBox, QFileDialog

from plotlyst.env import app_env


def select_new_project_directory() -> Optional[str]:
    workspace = QFileDialog.getExistingDirectory(None, 'Choose a directory for your novels')

    if not workspace:
        return None

    if not os.path.exists(workspace):
        QMessageBox.warning(None, 'Invalid project directory',
                            f"The chosen directory doesn't exist: {workspace}")
    elif os.path.isfile(workspace):
        QMessageBox.warning(None, 'Invalid project directory',
                            f"The chosen path should be a directory, not a file: {workspace}")
    elif not os.access(workspace, os.W_OK):
        QMessageBox.warning(None, 'Invalid project directory',
                            f"The chosen directory cannot be written: {workspace}")
    else:
        return workspace


def default_exported_location(filename: str) -> str:
    try:
        home = Path.home()
        if home:
            return str(home.joinpath(filename))
        else:
            return filename
    except Exception:
        return filename


def default_directory() -> Optional[str]:
    home = Path.home()
    if not home:
        return None

    if app_env.is_mac():
        plotlyst = home.joinpath('Plotlyst')
    elif app_env.is_windows():
        from plotlyst.service._win_known_folders import get_windows_path, FOLDERID, UserHandle, \
            PathNotFoundException
        try:
            plotlyst = get_windows_path(FOLDERID.Documents, UserHandle.current)
            if plotlyst:
                plotlyst = Path(plotlyst).joinpath('Plotlyst')
            else:
                plotlyst = home.joinpath('Documents/Plotlyst')
        except PathNotFoundException:
            plotlyst = home.joinpath('Documents/Plotlyst')
    else:
        plotlyst = home.joinpath('plotlyst')

    if plotlyst.exists() and plotlyst.is_file():
        return None
    if not plotlyst.exists():
        plotlyst.mkdir(exist_ok=True)
    if not os.access(str(plotlyst), os.W_OK):
        return None

    return str(plotlyst)
