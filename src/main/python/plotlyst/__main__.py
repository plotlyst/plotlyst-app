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
from plotlyst.service.profile import verify_profile

try:
    import logging
    import argparse
    import os
    import subprocess
    import sys
    import traceback
    from typing import Optional

    from fbs_runtime.excepthook import enable_excepthook_for_threads
    from overrides import overrides

    from plotlyst.version import plotlyst_display_version
    from plotlyst.env import AppMode, app_env
    from plotlyst.resources import resource_registry, resource_manager
    from plotlyst.settings import settings
    from plotlyst.service.persistence import flush_or_fail
    from plotlyst.service.dir import select_new_project_directory, default_directory
    from plotlyst.service.log import setup_logging

    from PyQt6.QtGui import QFont, QIcon, QPixmap
    from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
    from fbs_runtime.application_context.PyQt6 import ApplicationContext
    from fbs_runtime import platform
    from fbs_runtime.application_context import cached_property, is_frozen

    from plotlyst.core.client import json_client
    from plotlyst.event.handler import handle_exception
    from plotlyst.view.main_window import MainWindow
    from plotlyst.view.stylesheet import APP_STYLESHEET
except Exception as ex:
    app = QApplication(sys.argv)
    QMessageBox.critical(None, 'Could not launch application', traceback.format_exc())
    raise ex


class AppContext(ApplicationContext):

    @overrides
    def run(self):
        pass


if __name__ == '__main__':
    if app_env.is_windows():
        app = QApplication(sys.argv)
        appctxt = None
    else:
        appctxt = AppContext()
        app = appctxt.app
    app.setApplicationName('Plotlyst')
    app.setApplicationVersion(plotlyst_display_version)

    sys.excepthook = handle_exception
    enable_excepthook_for_threads()

    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', type=lambda mode: AppMode[mode.upper()], choices=list(AppMode), default=AppMode.PROD)
    parser.add_argument('--clear', action='store_true')
    args = parser.parse_args()
    app_env.mode = args.mode

    setup_logging()

    if platform.is_linux():
        font = QFont('Helvetica', max(QApplication.font().pointSize(), 12))
        logging.info(f'Linux OS was detected. Set font to Helvetica, {font.pointSize()}pt')
        QApplication.setFont(font)
    elif QApplication.font().pointSize() < 12:
        font = QApplication.font()
        font.setPointSize(12)
        QApplication.setFont(font)
    app.setStyleSheet(APP_STYLESHEET)
    settings.init_org()
    if args.clear:
        settings.clear()
    try:
        resource_registry.set_up(appctxt)
    except FileNotFoundError as ex:
        QMessageBox.critical(None, 'Could not locate resource file', traceback.format_exc())

    resource_manager.init()

    if not verify_profile():
        QMessageBox.critical(None, 'Signature verification failed',
                             'Plotlyst could not verify the signature. The file may have been tampered with or the distribution is invalid.\nIf you experience this with a fresh installation, contact the developer please.')
        sys.exit(1)

    if app_env.is_windows():
        icon = QIcon(resource_registry.plotlyst_icon)
        app.setWindowIcon(icon)

    workspace: Optional[str] = settings.workspace()
    if not workspace or not os.path.exists(workspace):
        workspace = default_directory()
    changed_dir = False
    while True:
        if not workspace:
            workspace = select_new_project_directory()
        if workspace:
            settings.set_workspace(workspace)
            break
    try:
        json_client.init(workspace)
    except Exception as ex:
        QMessageBox.critical(None, 'Could not initialize database', traceback.format_exc())
        raise ex
    splash_pixmap = QPixmap(resource_registry.banner)
    splash = QSplashScreen(splash_pixmap)
    splash.show()
    app.processEvents()

    try:
        window = MainWindow()
    except Exception as ex:
        QMessageBox.critical(None, 'Could not create main window', traceback.format_exc())
        raise ex

    window.show()
    splash.finish(window)
    window.activateWindow()
    # first_launch = settings.first_launch()
    # if first_launch:
    #     QTimer.singleShot(1000, AboutDialog.popup)
    #     settings.set_launched_before()
    sys.exit(app.exec_())
