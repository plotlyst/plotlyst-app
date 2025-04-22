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
from typing import Optional

import qtanim
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QWidget, QPushButton, QMenu, QWidgetAction
from qthandy import hbox, pointy, gc
from qthandy.filter import OpacityEventFilter
from qtmenu import ScrollableMenuWidget

from plotlyst.core.domain import Novel, Scene, GoalReference, CharacterGoal
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.character.plan import CharacterPlansSelectorWidget
from plotlyst.view.widget.labels import CharacterGoalLabel


class SceneGoalSelector(QWidget):
    goalSelected = pyqtSignal()

    def __init__(self, novel: Novel, scene: Scene, simplified: bool = False, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.scene = scene
        self.characterGoal: Optional[CharacterGoal] = None
        self.goalRef: Optional[GoalReference] = None
        hbox(self)

        self.label: Optional[CharacterGoalLabel] = None

        self.btnLinkGoal = QPushButton(self)
        if not simplified:
            self.btnLinkGoal.setText('Track goal')
        self.layout().addWidget(self.btnLinkGoal)
        self.btnLinkGoal.setIcon(IconRegistry.goal_icon())
        pointy(self.btnLinkGoal)
        self.btnLinkGoal.setStyleSheet('''
                QPushButton {
                    border: 2px dotted grey;
                    border-radius: 6px;
                    font: italic;
                }
                QPushButton:hover {
                    border: 2px dotted darkBlue;
                    color: darkBlue;
                    font: normal;
                }
                QPushButton:pressed {
                    border: 2px solid white;
                }
            ''')

        self.btnLinkGoal.installEventFilter(OpacityEventFilter(parent=self.btnLinkGoal))
        menu = ScrollableMenuWidget(self.btnLinkGoal)
        self._goalSelector = CharacterPlansSelectorWidget(self.novel, self.scene.agency[0].character(self.novel))
        menu.addWidget(self._goalSelector)
        self._goalSelector.setMinimumWidth(600)

        self._goalSelector.goalSelected.connect(self._goalSelected)

    def setGoal(self, characterGoal: CharacterGoal, goalRef: GoalReference):
        self.characterGoal = characterGoal
        self.goalRef = goalRef
        self.label = CharacterGoalLabel(self.novel, self.characterGoal, self.goalRef, removalEnabled=True)
        pointy(self.label)
        self.label.clicked.connect(self._goalRefClicked)
        self.label.removalRequested.connect(self._remove)
        self.layout().addWidget(self.label)
        self.btnLinkGoal.setHidden(True)

    def _goalSelected(self, characterGoal: CharacterGoal):
        goal_ref = GoalReference(characterGoal.id)
        self.scene.agency[0].goal_references.append(goal_ref)

        self.btnLinkGoal.menu().hide()
        self.setGoal(characterGoal, goal_ref)
        self.goalSelected.emit()

    def _goalRefClicked(self):
        menu = QMenu(self.label)
        action = QWidgetAction(menu)
        action.setDefaultWidget(GoalStakesEditor(self.goalRef))
        menu.addAction(action)
        menu.popup(QCursor.pos())

    def _remove(self):
        if self.parent():
            anim = qtanim.fade_out(self, duration=150)
            anim.finished.connect(self.__destroy)

    def __destroy(self):
        self.scene.agency[0].remove_goal(self.characterGoal)
        self.parent().layout().removeWidget(self)
        gc(self)
