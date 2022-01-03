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
from dataclasses import dataclass
from typing import Optional

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QDialog

from src.main.python.plotlyst.core.domain import NovelDescriptor, Novel, Plot, PlotType, Character
from src.main.python.plotlyst.view.generated.novel_creation_dialog_ui import Ui_NovelCreationDialog
from src.main.python.plotlyst.view.generated.plot_editor_dialog_ui import Ui_PlotEditorDialog
from src.main.python.plotlyst.view.icons import IconRegistry, avatars


class NovelEditionDialog(QDialog, Ui_NovelCreationDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.btnCancel.setIcon(IconRegistry.cancel_icon())
        self.btnConfirm.setIcon(IconRegistry.ok_icon())
        self.btnCancel.clicked.connect(self.reject)
        self.btnConfirm.clicked.connect(self.accept)

    def display(self, novel: Optional[NovelDescriptor] = None) -> Optional[str]:
        if novel:
            self.lineTitle.setText(novel.title)
        result = self.exec()
        if result == QDialog.DialogCode.Rejected:
            return None
        return self.lineTitle.text()


@dataclass
class PlotEditionResult:
    text: str
    plot_type: PlotType
    character: Optional[Character] = None


class PlotEditorDialog(QDialog, Ui_PlotEditorDialog):
    def __init__(self, novel: Novel, plot: Optional[Plot] = None, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.novel = novel

        self.rbMainPlot.setIcon(IconRegistry.cause_and_effect_icon())
        self.rbInternalPlot.setIcon(IconRegistry.conflict_self_icon())
        self.rbSubplot.setIcon(IconRegistry.from_name('mdi.source-branch'))

        self.lineKeyphrase.textChanged.connect(lambda x: self.btnSave.setEnabled(len(x) > 0))

        for char in self.novel.characters:
            self.cbCharacter.addItem(QIcon(avatars.pixmap(char)), char.name, char)
        if self.cbCharacter.count() == 0:
            self.cbCharacter.addItem('No character available yet', None)

        self.cbCharacter.setCurrentIndex(0)

        if plot:
            self.lineKeyphrase.setText(plot.text)
            if plot.plot_type == PlotType.Main:
                self.rbMainPlot.setChecked(True)
            elif plot.plot_type == PlotType.Internal:
                self.rbInternalPlot.setChecked(True)
            elif plot.plot_type == PlotType.Subplot:
                self.rbSubplot.setChecked(True)

            char = plot.character(self.novel)
            if char:
                self.cbCharacter.setCurrentText(char.name)

        self.btnSave.clicked.connect(self.accept)
        self.btnClose.clicked.connect(self.reject)

    def display(self) -> Optional[PlotEditionResult]:
        result = self.exec()
        if result == QDialog.DialogCode.Rejected:
            return None
        plot_type = PlotType.Main
        if self.rbInternalPlot.isChecked():
            plot_type = PlotType.Internal
        elif self.rbSubplot.isChecked():
            plot_type = PlotType.Subplot
        return PlotEditionResult(self.lineKeyphrase.text(), plot_type, self.cbCharacter.currentData())
