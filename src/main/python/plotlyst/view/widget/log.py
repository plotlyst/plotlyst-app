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
import logging
from logging import LogRecord, WARNING

from PyQt6.QtCore import Qt, QModelIndex, QTimer
from PyQt6.QtGui import QClipboard
from PyQt6.QtWidgets import QTableView, QSplitter, QTextBrowser, QWidget, QApplication
from qthandy import vbox

from plotlyst.model.log import LogTableModel
from plotlyst.service.log import LogHandler
from plotlyst.view.common import stretch_col, push_btn, tool_btn, label, fade_in
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.display import PopupDialog


class LogsPopup(PopupDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.tblView = QTableView()
        self.tblView.setWordWrap(True)

        logger = logging.getLogger()
        for handler in logger.handlers:
            if isinstance(handler, LogHandler):
                self.tblView.setModel(handler.model)
                break

        stretch_col(self.tblView, 1)
        self.tblView.setColumnWidth(0, 30)
        self.tblView.setColumnWidth(2, 200)
        self.tblView.clicked.connect(self._logClicked)

        self.textDisplay = QTextBrowser()
        self.textDisplay.setProperty('error', True)
        self.wdgErrorDisplay = QWidget()
        vbox(self.wdgErrorDisplay)
        self.btnCopy = tool_btn(IconRegistry.from_name('fa5.copy', 'grey'), transparent_=True, tooltip='Copy text')
        self.btnCopy.clicked.connect(self._copyError)
        self.lblCopied = label('Copied', description=True)
        self.wdgErrorDisplay.layout().addWidget(group(self.btnCopy, self.lblCopied),
                                                alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgErrorDisplay.layout().addWidget(self.textDisplay)
        self.lblCopied.setHidden(True)

        self.splitterDisplay = QSplitter()
        self.splitterDisplay.setChildrenCollapsible(False)
        self.splitterDisplay.addWidget(self.tblView)
        self.splitterDisplay.addWidget(self.wdgErrorDisplay)
        self.splitterDisplay.setMinimumSize(800, 400)
        self.wdgErrorDisplay.setHidden(True)

        self.btnClose = push_btn(text='Close', properties=['confirm', 'cancel'])
        self.btnClose.clicked.connect(self.accept)

        self.frame.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)
        self.frame.layout().addWidget(self.splitterDisplay)
        self.frame.layout().addWidget(self.btnClose, alignment=Qt.AlignmentFlag.AlignRight)

    def display(self):
        self.exec()

    def _logClicked(self, index: QModelIndex):
        record: LogRecord = index.data(LogTableModel.LogRecordRole)
        if record.levelno >= WARNING:
            self.textDisplay.setText(record.exc_text if record.exc_text else record.msg)
            self.wdgErrorDisplay.setVisible(True)
        else:
            self.wdgErrorDisplay.setVisible(False)

    def _copyError(self):
        text = self.textDisplay.toPlainText()
        clipboard = QApplication.clipboard()
        clipboard.setText(text, QClipboard.Mode.Clipboard)

        fade_in(self.lblCopied)
        QTimer.singleShot(450, lambda: self.lblCopied.setHidden(True))
