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
from functools import partial
from typing import Dict

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QWidget, QPushButton
from overrides import overrides
from qthandy import vbox, spacer, hbox, decr_icon, translucent, decr_font, sp, transparent, italic

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import Motivation, Scene, Novel, CharacterAgency
from plotlyst.view.common import label
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.button import ChargeButton


class MotivationPyramidStepButton(QPushButton):
    def __init__(self, mot: Motivation, parent=None):
        super().__init__(parent)
        self.setIcon(IconRegistry.from_name(mot.icon(), mot.color()))

        self.setFixedWidth(180 - mot.value * 30)
        self.setStyleSheet(f'''
                   QPushButton {{
                       background-color: {RELAXED_WHITE_COLOR};
                       border: 1px solid lightgrey;
                       border-bottom: 1px hidden grey;
                       padding: 4px;
                   }}
               ''')
        self.setEnabled(False)

    def setValue(self, value: int):
        pass


class MotivationDisplay(QWidget):
    def __init__(self, novel: Novel, scene: Scene, agency: CharacterAgency, parent=None):
        super().__init__(parent)
        self._novel: Novel = novel
        self._scene: Scene = scene
        self._agenda: CharacterAgency = agency

        vbox(self, 5, 0)

        self._steps = {}
        for mot in Motivation:
            self._steps[mot] = MotivationPyramidStepButton(mot)

        self.layout().addWidget(self._steps[Motivation.SELF_TRANSCENDENCE], alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._steps[Motivation.SELF_ACTUALIZATION], alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._steps[Motivation.ESTEEM], alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._steps[Motivation.BELONGING], alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._steps[Motivation.SAFETY], alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._steps[Motivation.PHYSIOLOGICAL], alignment=Qt.AlignmentFlag.AlignCenter)

        self._refresh()

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        pass

    def _refresh(self):
        pass
        # for btn in self._steps.values():
        #     btn.setDisabled(True)
        # for scene in self._novel.scenes:
        #     if scene is self._scene:
        #         break
        #     for agenda in scene.agency:
        #         if agenda.character_id and agenda.character_id == self._agenda.character_id:
        #             for mot, v in agenda.motivations.items():
        #                 slider = self._sliders[Motivation(mot)]
        #                 slider.setValue(slider.value() + v)


class MotivationChargeLabel(QPushButton):
    def __init__(self, motivation: Motivation, parent=None):
        super().__init__(parent)
        self._motivation = motivation
        sp(self).h_max()
        self.setIcon(IconRegistry.from_name(self._motivation.icon(), self._motivation.color()))

        transparent(self)
        italic(self)
        decr_icon(self, 2)
        decr_font(self)

        translucent(self)

    def setCharge(self, charge: int):
        if charge == 0:
            self.setText(' ' * 5)
        else:
            self.setText(f'+{charge}')


class MotivationCharge(QWidget):
    charged = pyqtSignal(int)
    MAX_CHARGE: int = 5

    def __init__(self, motivation: Motivation, parent=None):
        super().__init__(parent)
        hbox(self, 0, 0)
        self._motivation = motivation
        self._charge = 0

        self._label = MotivationChargeLabel(self._motivation)
        self._posCharge = ChargeButton(positive=True)
        self._posCharge.clicked.connect(lambda: self._changeCharge(1))
        self._negCharge = ChargeButton(positive=False)
        self._negCharge.clicked.connect(lambda: self._changeCharge(-1))
        self._negCharge.setHidden(True)

        self.layout().addWidget(label(self._motivation.display_name()))
        self.layout().addWidget(spacer())
        self.layout().addWidget(self._label)
        self.layout().addWidget(self._negCharge)
        self.layout().addWidget(self._posCharge)

    def setValue(self, value: int):
        self._charge = min(value, self.MAX_CHARGE)
        self._update()

    def _changeCharge(self, charge: int):
        self._charge += charge
        self._update()

        self.charged.emit(self._charge)

    def _update(self):
        self._label.setCharge(self._charge)
        if self._charge == 0:
            self._negCharge.setHidden(True)
        else:
            self._negCharge.setVisible(True)
        if self._charge == self.MAX_CHARGE:
            self._posCharge.setHidden(True)
        else:
            self._posCharge.setVisible(True)


class MotivationEditor(QWidget):
    motivationChanged = pyqtSignal(Motivation, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self)
        # self.layout().addWidget(label("Does the character's motivation change?"))

        self._editors: Dict[Motivation, MotivationCharge] = {}
        self._addEditor(Motivation.SELF_TRANSCENDENCE)
        self._addEditor(Motivation.SELF_ACTUALIZATION)
        self._addEditor(Motivation.ESTEEM)
        self._addEditor(Motivation.BELONGING)
        self._addEditor(Motivation.SAFETY)
        self._addEditor(Motivation.PHYSIOLOGICAL)

    def _addEditor(self, motivation: Motivation):
        wdg = MotivationCharge(motivation)
        self._editors[motivation] = wdg
        wdg.charged.connect(partial(self.motivationChanged.emit, motivation))
        self.layout().addWidget(wdg)

    def reset(self):
        for editor in self._editors.values():
            editor.setValue(0)

    def setMotivations(self, motivations: Dict[Motivation, int]):
        self.reset()
        for mot, v in motivations.items():
            self._editors[mot].setValue(v)
