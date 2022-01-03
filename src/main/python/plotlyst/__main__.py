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
from src.main.python.plotlyst.resources import resource_registry

try:
    import argparse
    import os
    import subprocess
    import sys
    import traceback
    from typing import Optional

    from overrides import overrides

    from src.main.python.plotlyst.env import AppMode, app_env
    from src.main.python.plotlyst.settings import settings
    from src.main.python.plotlyst.view.dialog.dir import DirectoryPickerDialog
    from src.main.python.plotlyst.worker.persistence import flush_or_fail

    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import QFileDialog, QApplication, QMessageBox
    from fbs_runtime.application_context.PyQt6 import ApplicationContext
    from fbs_runtime import PUBLIC_SETTINGS, platform
    from fbs_runtime.application_context import cached_property, is_frozen
    from fbs_runtime.excepthook.sentry import SentryExceptionHandler

    from src.main.python.plotlyst.common import EXIT_CODE_RESTART
    from src.main.python.plotlyst.core.client import json_client
    from src.main.python.plotlyst.event.handler import DialogExceptionHandler
    from src.main.python.plotlyst.view.dialog.about import AboutDialog
    from src.main.python.plotlyst.view.main_window import MainWindow
    from src.main.python.plotlyst.view.stylesheet import APP_STYLESHEET
except Exception as ex:
    appctxt = ApplicationContext()
    QMessageBox.critical(None, 'Could not launch application', traceback.format_exc())
    raise ex


class AppContext(ApplicationContext):

    @overrides
    def run(self):
        pass

    @cached_property
    def exception_handlers(self):
        result = super().exception_handlers
        result.append(self.dialog_exception_handler)
        if is_frozen():
            result.append(self.sentry_exception_handler)
        return result

    @cached_property
    def sentry_exception_handler(self):
        return SentryExceptionHandler(
            PUBLIC_SETTINGS['sentry_dsn'],
            PUBLIC_SETTINGS['version'],
            PUBLIC_SETTINGS['environment'], callback=self._on_sentry_init
        )

    @cached_property
    def dialog_exception_handler(self):
        return DialogExceptionHandler()

    def _on_sentry_init(self):
        scope = self.sentry_exception_handler.scope
        from fbs_runtime import platform
        scope.set_extra('os', platform.name())


if __name__ == '__main__':
    appctxt = AppContext()

    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', type=lambda mode: AppMode[mode.upper()], choices=list(AppMode), default=AppMode.PROD)
    args = parser.parse_args()
    app_env.mode = args.mode
    while True:
        app = appctxt.app
        if platform.is_linux() and QApplication.font().pointSize() < 12:
            font = QFont('Helvetica', 12)
            QApplication.setFont(font)
        app.setStyleSheet(APP_STYLESHEET)
        settings.init_org()
        resource_registry.set_up(appctxt)

        workspace: Optional[str] = settings.workspace()

        changed_dir = False
        while True:
            if not workspace:
                picker = DirectoryPickerDialog()
                picker.display()
                workspace = QFileDialog.getExistingDirectory(None, 'Choose directory')
                changed_dir = True

            if not workspace:
                exit(0)

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
                if changed_dir:
                    settings.set_workspace(workspace)
                break
            workspace = None

        try:
            json_client.init(workspace)
        except Exception as ex:
            QMessageBox.critical(None, 'Could not initialize database', traceback.format_exc())
            raise ex

        try:
            window = MainWindow()
        except Exception as ex:
            QMessageBox.critical(None, 'Could not create main window', traceback.format_exc())
            raise ex

        window.show()
        window.activateWindow()

        first_launch = settings.first_launch()
        if first_launch:
            AboutDialog().exec()
            settings.set_launched_before()

        exit_code = appctxt.app.exec_()
        flush_or_fail()

        if exit_code < EXIT_CODE_RESTART:
            break

        # restart process
        subprocess.call('./gen.sh')
        python = sys.executable
        os.execl(python, python, *sys.argv)
