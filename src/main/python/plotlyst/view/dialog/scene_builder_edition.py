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
from typing import Optional, List

from PyQt6.QtCore import QVariantAnimation, QVariant, pyqtSlot, QEasingCurve, QEventLoop, QTimer
from PyQt6.QtGui import QIcon, QPalette, QColor
from PyQt6.QtWidgets import QDialog, QApplication, QLabel
from overrides import overrides

from src.main.python.plotlyst.core.domain import Scene, Character, NpcCharacter, SceneBuilderElement
from src.main.python.plotlyst.core.text import generate_text_from_scene_builder
from src.main.python.plotlyst.view.generated.scene_builder_preview_dialog_ui import Ui_SceneBuilderPreviewDialog
from src.main.python.plotlyst.view.generated.scene_element_edition_dialog_ui import Ui_SceneElementEditionDialog
from src.main.python.plotlyst.view.icons import avatars, IconRegistry


@dataclass
class SceneElementEditionResult:
    text: str = ''
    character: Optional[Character] = None


class SceneElementEditionDialog(QDialog, Ui_SceneElementEditionDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.lineText.textEdited.connect(self._on_text_edit)

    def display(self, scene: Scene) -> Optional[SceneElementEditionResult]:
        self._setup(scene)
        if not self.cbCharacter.count():
            self.cbCharacter.setHidden(True)
        result = self.exec()
        if result == QDialog.DialogCode.Rejected:
            return None
        return SceneElementEditionResult(text=self.lineText.text(), character=self.cbCharacter.currentData())

    def _setup(self, scene: Scene):
        pass

    def _on_text_edit(self, text: str):
        if len(text) == 1:
            self.lineText.setText(text.upper())


class CharacterBasedEditionDialog(SceneElementEditionDialog):
    @overrides
    def _setup(self, scene: Scene):
        for char in scene.characters:
            self.cbCharacter.addItem(QIcon(avatars.pixmap(char)), char.name, char)
        self.cbCharacter.insertSeparator(self.cbCharacter.count())
        self.cbCharacter.addItem(IconRegistry.portrait_icon(), 'Other', NpcCharacter('Other'))

        super()._setup(scene)


class DialogEditionDialog(CharacterBasedEditionDialog):

    @overrides
    def _setup(self, scene: Scene):
        if scene.pov:
            self.cbCharacter.addItem(QIcon(avatars.pixmap(scene.pov)), scene.pov.name, scene.pov)
            self.cbCharacter.insertSeparator(1)
        super()._setup(scene)


class FadingLabel(QLabel):
    def __init__(self):
        super(FadingLabel, self).__init__()
        self.animation = QVariantAnimation()
        self.animation.valueChanged.connect(self.changeColor)

    @pyqtSlot(QVariant)
    def changeColor(self, color):
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.WindowText, color)
        self.setPalette(palette)

    def _startFadeIn(self):
        self.animation.stop()
        self.animation.setStartValue(QColor(0, 0, 0, 0))
        self.animation.setEndValue(QColor(0, 0, 0, 255))
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.InBack)
        self.animation.start()

    def _startFadeOut(self):
        self.animation.stop()
        self.animation.setStartValue(QColor(0, 0, 0, 255))
        self.animation.setEndValue(QColor(0, 0, 0, 0))
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutBack)
        self.animation.start()

    def startAnimation(self):
        self._startFadeIn()
        loop = QEventLoop()
        self.animation.finished.connect(loop.quit)
        loop.exec_()
        QTimer.singleShot(350, self._startFadeOut)


class SceneBuilderPreviewDialog(QDialog, Ui_SceneBuilderPreviewDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.lblAnimated = FadingLabel()
        self.lblAnimated.setText('Copied!')
        self.lblAnimated.setVisible(False)
        self.horizontalLayout.insertWidget(1, self.lblAnimated)
        self.btnCopy.setIcon(IconRegistry.copy_icon())
        self.btnCopy.clicked.connect(self._copy)

    def display(self, elements: List[SceneBuilderElement]):
        self.textBrowser.setText(generate_text_from_scene_builder(elements))
        self.exec()

    def _copy(self):
        QApplication.clipboard().setText(self.textBrowser.toPlainText())
        self.lblAnimated.setVisible(True)
        self.lblAnimated.startAnimation()
