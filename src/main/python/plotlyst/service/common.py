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
import datetime

from PyQt6.QtWidgets import QApplication

from plotlyst.view.widget.confirm import asked


def try_shutdown_to_apply_change():
    if asked("To apply the change, the application needs to be closed first.",
             "Do you want to shutdown the application to apply the change?", btnConfirmText='Shutdown'):
        QApplication.quit()


def today_str() -> str:
    today = datetime.date.today()
    return today.strftime("%Y-%m-%d")
