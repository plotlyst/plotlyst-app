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
from abc import abstractmethod
from functools import partial
from typing import Optional, Dict

from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtGui import QColor, QEnterEvent
from PyQt6.QtWidgets import QWidget, QToolButton, QGraphicsDropShadowEffect
from overrides import overrides
from qthandy import hbox, retain_when_hidden, sp, decr_icon, margins, translucent
from qthandy.filter import VisibilityToggleEventFilter, InstantTooltipEventFilter
from qtmenu import MenuWidget

from plotlyst.core.domain import Novel, Scene, ScenePlotReference, PlotValue, ScenePlotValueCharge, \
    Plot
from plotlyst.view.common import action, tool_btn
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.widget.display import Icon
from plotlyst.view.widget.input import RemovalButton
from plotlyst.view.widget.labels import PlotValueLabel


class PlotValuesDisplay(QWidget):
    def __init__(self, plotReference: ScenePlotReference, parent=None):
        super().__init__(parent)
        self._plotReference = plotReference
        self._values: Dict[PlotValue, PlotValueLabel] = {}

        hbox(self, spacing=9)
        margins(self, right=8)
        for value in self._plotReference.plot.values:
            lbl = PlotValueLabel(value, simplified=True)
            sp(lbl).h_max()
            lbl.setHidden(True)
            self._values[value] = lbl
            self.layout().addWidget(lbl)

    def updateValue(self, value: PlotValue, charge: ScenePlotValueCharge):
        lbl = self._values[value]
        if charge.charge == 0:
            lbl.setHidden(True)
        else:
            lbl.setVisible(True)
            effect = QGraphicsDropShadowEffect()
            if charge.charge > 0:
                effect.setColor(QColor('#52b788'))
                lbl.setEnabled(True)
            else:
                effect.setColor(QColor('#9d0208'))
                lbl.setEnabled(False)

            effect.setOffset(5 * abs(charge.charge), 0)
            effect.setBlurRadius(25)
            lbl.setGraphicsEffect(effect)


class ProgressEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self, spacing=0)
        self._chargeEnabled: bool = True

        self.posCharge = tool_btn(IconRegistry.charge_icon(2, 'grey'), transparent_=True)
        decr_icon(self.posCharge, 4)
        self.posCharge.clicked.connect(lambda: self._changeCharge(1))

        self.negCharge = tool_btn(IconRegistry.charge_icon(-2, 'grey'), transparent_=True)
        decr_icon(self.negCharge, 4)
        self.negCharge.clicked.connect(lambda: self._changeCharge(-1))

        self.btnLock = Icon()
        self.btnLock.setIcon(IconRegistry.from_name('fa5s.lock', 'grey'))
        self.btnLock.installEventFilter(InstantTooltipEventFilter(self.btnLock))
        self.btnLock.setHidden(True)

        self.layout().addWidget(self.posCharge, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.layout().addWidget(self.negCharge, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.layout().addWidget(self.btnLock, alignment=Qt.AlignmentFlag.AlignVCenter)

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        # if self._chargeEnabled:
        #     self.wdgSize.setVisible(True)
        if not self._chargeEnabled:
            self.btnLock.setVisible(True)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        # self.wdgSize.setHidden(True)
        self.btnLock.setHidden(True)

    def refresh(self):
        self._updateButtons()

    @abstractmethod
    def charge(self) -> int:
        pass

    def altCharge(self) -> int:
        return 0

    @abstractmethod
    def _changeCharge(self, charge: int):
        pass

    def _updateButtons(self):
        self.posCharge.setEnabled(True)
        self.negCharge.setEnabled(True)

        self.posCharge.setEnabled(self._chargeEnabled)
        self.negCharge.setEnabled(self._chargeEnabled)

        if self.charge() == 3:
            self.posCharge.setDisabled(True)
        elif self.charge() == -3:
            self.negCharge.setDisabled(True)


class ScenePlotGeneralProgressEditor(ProgressEditor):
    charged = pyqtSignal()

    def __init__(self, plotReference: ScenePlotReference, parent=None):
        super().__init__(parent)
        self.plotReference = plotReference
        self.refresh()

    @abstractmethod
    def charge(self) -> int:
        return self.plotReference.data.charge

    @overrides
    def _changeCharge(self, charge: int):
        self.plotReference.data.charge += charge
        self.refresh()
        self.charged.emit()

    @overrides
    def _updateButtons(self):
        if not self.negCharge.isEnabled():
            self.negCharge.setEnabled(True)
        if not self.posCharge.isEnabled():
            self.posCharge.setEnabled(True)
        if self.charge() == 3:
            self.posCharge.setDisabled(True)
        if self.charge() == -3:
            self.negCharge.setDisabled(True)


class ScenePlotSelectorMenu(MenuWidget):
    plotSelected = pyqtSignal(Plot)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._scene: Optional[Scene] = None

        self.aboutToShow.connect(self._beforeShow)
        apply_white_menu(self)

    def setScene(self, scene: Scene):
        self._scene = scene

    def _beforeShow(self):
        if self._scene is None:
            return
        self.clear()
        occupied_plot_ids = self._occupiedPlotIds()
        self.addSection(
            f'Link storylines to this {"scene" if self._novel.prefs.is_scenes_organization() else "chapter"}')
        self.addSeparator()
        for plot in self._novel.plots:
            action_ = action(plot.text, IconRegistry.from_name(plot.icon, plot.icon_color),
                             partial(self.plotSelected.emit, plot))
            if plot.id in occupied_plot_ids:
                action_.setDisabled(True)
            self.addAction(action_)

        if not self.actions():
            self.addSection('No corresponding storylines were found')

        self._frame.updateGeometry()

    def _occupiedPlotIds(self):
        return [x.plot.id for x in self._scene.plot_values]


class ScenePlotLabels(QWidget):
    reset = pyqtSignal()
    generalProgressCharged = pyqtSignal()

    def __init__(self, scene: Scene, plotref: ScenePlotReference, parent=None):
        super().__init__(parent)
        self._scene = scene
        self._plotref = plotref
        hbox(self, 0, 0)

        self._icon = Icon()
        self._icon.setIcon(IconRegistry.from_name(self._plotref.plot.icon, self._plotref.plot.icon_color))
        self._icon.setToolTip(plotref.plot.text)
        translucent(self._icon, 0.5)

        self._btnReset = RemovalButton()
        self._btnReset.clicked.connect(self.reset.emit)
        retain_when_hidden(self._btnReset)

        self.layout().addWidget(self._icon)
        self.layout().addWidget(self._btnReset)

        self.installEventFilter(VisibilityToggleEventFilter(self._btnReset, self))

    def icon(self) -> QToolButton:
        return self._icon

    def storylineRef(self) -> ScenePlotReference:
        return self._plotref

    def activate(self):
        pass
