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
from typing import Dict, Optional

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QWidget, QSlider
from overrides import overrides
from qthandy import vbox, spacer, hbox, bold, decr_icon, translucent

from plotlyst.core.domain import Motivation, Scene, Novel, CharacterAgency
from plotlyst.view.common import label, tool_btn, push_btn
from plotlyst.view.generated.scene_goal_stakes_ui import Ui_GoalReferenceStakesEditor
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.button import ChargeButton


class MotivationDisplay(QWidget, Ui_GoalReferenceStakesEditor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self._novel: Optional[Novel] = None
        self._scene: Optional[Scene] = None
        self._agenda: Optional[CharacterAgency] = None
        bold(self.lblTitle)

        self._sliders: Dict[Motivation, QSlider] = {
            Motivation.PHYSIOLOGICAL: self.sliderPhysiological,
            Motivation.SAFETY: self.sliderSecurity,
            Motivation.BELONGING: self.sliderBelonging,
            Motivation.ESTEEM: self.sliderEsteem,
            Motivation.SELF_ACTUALIZATION: self.sliderActualization,
            Motivation.SELF_TRANSCENDENCE: self.sliderTranscendence,
        }

        for slider in self._sliders.values():
            slider.setEnabled(False)
        translucent(self)

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        pass

    def setNovel(self, novel: Novel):
        self._novel = novel

    def setScene(self, scene: Scene):
        self._scene = scene

    def setAgenda(self, agenda: CharacterAgency):
        self._agenda = agenda
        self._refresh()

    def _refresh(self):
        for slider in self._sliders.values():
            slider.setValue(0)
        for scene in self._novel.scenes:
            if scene is self._scene:
                break
            for agenda in scene.agency:
                if agenda.character_id and agenda.character_id == self._agenda.character_id:
                    for mot, v in agenda.motivations.items():
                        slider = self._sliders[Motivation(mot)]
                        slider.setValue(slider.value() + v)


class MotivationChargeLabel(QWidget):
    def __init__(self, motivation: Motivation, simplified: bool = False, parent=None):
        super().__init__(parent)
        self._motivation = motivation
        hbox(self, margin=0 if simplified else 1, spacing=0)
        if simplified:
            self._btn = tool_btn(IconRegistry.from_name(self._motivation.icon(), self._motivation.color()),
                                 icon_resize=False, transparent_=True)
        else:
            self._btn = push_btn(IconRegistry.from_name(self._motivation.icon(), self._motivation.color()),
                                 text=motivation.display_name(), icon_resize=False,
                                 transparent_=True)
        self._btn.setCursor(Qt.CursorShape.ArrowCursor)
        decr_icon(self._btn, 2)

        self._lblCharge = label('', description=True, italic=True, decr_font_diff=1)

        self.layout().addWidget(self._btn)
        self.layout().addWidget(self._lblCharge)

    def setCharge(self, charge: int):
        bold(self._btn, charge > 0)
        if charge == 0:
            self._lblCharge.clear()
        else:
            self._lblCharge.setText(f'+{charge}')


class MotivationCharge(QWidget):
    charged = pyqtSignal(int)
    MAX_CHARGE: int = 5

    def __init__(self, motivation: Motivation, parent=None):
        super().__init__(parent)
        hbox(self)
        self._motivation = motivation
        self._charge = 0

        self._label = MotivationChargeLabel(self._motivation)
        self._posCharge = ChargeButton(positive=True)
        self._posCharge.clicked.connect(lambda: self._changeCharge(1))
        self._negCharge = ChargeButton(positive=False)
        self._negCharge.clicked.connect(lambda: self._changeCharge(-1))
        self._negCharge.setHidden(True)

        self.layout().addWidget(self._label)
        self.layout().addWidget(spacer())
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
        self.layout().addWidget(label("Does the character's motivation change?"))

        self._editors: Dict[Motivation, MotivationCharge] = {}
        self._addEditor(Motivation.PHYSIOLOGICAL)
        self._addEditor(Motivation.SAFETY)
        self._addEditor(Motivation.BELONGING)
        self._addEditor(Motivation.ESTEEM)
        self._addEditor(Motivation.SELF_ACTUALIZATION)
        self._addEditor(Motivation.SELF_TRANSCENDENCE)

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
