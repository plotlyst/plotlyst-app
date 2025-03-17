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
from typing import Optional

from PyQt6.QtCore import Qt, QMarginsF, QSize, QTimer
from PyQt6.QtGui import QTextDocument, QPageSize, QColor, QPageLayout
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewWidget
from PyQt6.QtWidgets import QWidget, QDialog, QSplitter, QGraphicsView
from overrides import overrides
from qthandy import vbox, vspacer, sp, gc, busy

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import Novel
from plotlyst.service.manuscript import export_manuscript_to_docx, format_manuscript, export_manuscript_to_pdf
from plotlyst.view.common import push_btn, label, exclusive_buttons
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.style.theme import BG_MUTED_COLOR
from plotlyst.view.widget.button import TopSelectorButton
from plotlyst.view.widget.display import PopupDialog
from plotlyst.view.widget.settings import Forms


class ManuscriptExportPopup(PopupDialog):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.preview = self.__newPreview()
        self.document: Optional[QTextDocument] = None

        self._btnDocx = TopSelectorButton('mdi.file-word-outline', 'Word (.docx)')
        self._btnPdf = TopSelectorButton('fa5.file-pdf', 'PDF')

        self.wdgEditor = QWidget()
        vbox(self.wdgEditor, 10, 6)
        self.wdgCentral = QSplitter()
        sp(self.wdgCentral).v_exp()
        self.wdgCentral.setChildrenCollapsible(False)
        self.wdgCentral.addWidget(self.preview)
        self.wdgCentral.addWidget(self.wdgEditor)
        self.wdgCentral.setSizes([550, 150])

        self._btnGroup = exclusive_buttons(self, self._btnDocx, self._btnPdf)

        chapterForms = Forms('Chapter titles')
        self.wdgEditor.layout().addWidget(chapterForms)
        self.chapterSceneTitle = chapterForms.addSetting("First scene's title")
        self.chapterScenePov = chapterForms.addSetting("POV character's name")
        chapterForms.setRowVisible(0, self.novel.prefs.is_scenes_organization())
        exclusive_buttons(self.wdgEditor, self.chapterSceneTitle, self.chapterScenePov, optional=True)

        self.chapterSceneTitle.clicked.connect(self._sceneTitleSettingToggled)
        self.chapterScenePov.clicked.connect(self._sceneTitleSettingToggled)

        self.wdgEditor.layout().addWidget(vspacer())

        self.btnExport = push_btn(IconRegistry.from_name('mdi.file-export-outline', RELAXED_WHITE_COLOR),
                                  'Export to docx',
                                  tooltip='Export manuscript',
                                  properties=['confirm', 'positive'])
        self.btnExport.clicked.connect(self.accept)
        self.btnCancel = push_btn(text='Close', properties=['confirm', 'cancel'])
        self.btnCancel.clicked.connect(self.reject)

        self._btnGroup.buttonToggled.connect(self._formatChanged)
        self._btnDocx.setChecked(True)

        self.frame.layout().addWidget(
            group(label('Export manuscript to: ', h5=True), self._btnDocx, self._btnPdf, margin=10, spacing=5),
            alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame.layout().addWidget(self.wdgCentral)
        self.frame.layout().addWidget(group(self.btnCancel, self.btnExport), alignment=Qt.AlignmentFlag.AlignRight)

    @overrides
    def sizeHint(self) -> QSize:
        return self._adjustedSize(0.9, 0.8, 800, 600)

    def display(self):
        self.document = format_manuscript(self.novel)

        result = self.exec()
        if result == QDialog.DialogCode.Accepted:
            if self._btnDocx.isChecked():
                export_manuscript_to_docx(self.novel, sceneTitle=self.chapterSceneTitle.isChecked(),
                                          povTitle=self.chapterScenePov.isChecked())
            elif self._btnPdf.isChecked():
                export_manuscript_to_pdf(self.novel, self.document)

    def _print(self, device: QPrinter):
        device.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
        device.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Inch)  # margin is already set it seems
        self.document.print(device)

    def _formatChanged(self):
        if self._btnDocx.isChecked():
            self.btnExport.setText('Export to docx')
        elif self._btnPdf.isChecked():
            self.btnExport.setText('Export to PDF')

    def _sceneTitleSettingToggled(self):
        QTimer.singleShot(100, self._refreshPreview)

    @busy
    def _refreshPreview(self):
        self.document = format_manuscript(self.novel, sceneTitle=self.chapterSceneTitle.isChecked(),
                                          povTitle=self.chapterScenePov.isChecked())
        gc(self.preview)
        self.preview = self.__newPreview()
        self.wdgCentral.insertWidget(0, self.preview)

    def __newPreview(self) -> QPrintPreviewWidget:
        preview = QPrintPreviewWidget()
        preview.setContentsMargins(0, 0, 0, 0)
        preview.paintRequested.connect(self._print)
        preview.fitToWidth()

        item = preview.layout().itemAt(0)
        if isinstance(item.widget(), QGraphicsView):
            item.widget().setBackgroundBrush(QColor(BG_MUTED_COLOR))
        sp(preview).h_exp()

        return preview
