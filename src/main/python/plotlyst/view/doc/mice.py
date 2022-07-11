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
from typing import Dict

import qtanim
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget
from qthandy import incr_font, vbox, retain_when_hidden, gc, vspacer

from src.main.python.plotlyst.core.domain import MiceQuotient, Document, MiceThread, MiceType, Scene
from src.main.python.plotlyst.env import app_env
from src.main.python.plotlyst.view.common import VisibilityToggleEventFilter
from src.main.python.plotlyst.view.generated.mice_doc_ui import Ui_MiceQuotientDoc
from src.main.python.plotlyst.view.generated.mice_thread_ui import Ui_MiceThread
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.widget.scenes import SceneSelector

mice_colors: Dict[MiceType, str] = {MiceType.MILIEU: '#2d6a4f',
                                    MiceType.INQUIRY: '#7b2cbf',
                                    MiceType.CHARACTER: 'darkBlue',
                                    MiceType.EVENT: '#d90429'}


class MiceThreadWidget(QWidget, Ui_MiceThread):
    removed = pyqtSignal(QWidget)
    changed = pyqtSignal()

    def __init__(self, thread: MiceThread, parent=None):
        super(MiceThreadWidget, self).__init__(parent)
        self.setupUi(self)
        self.thread: MiceThread = thread
        if thread.type == MiceType.MILIEU:
            self.icon.setIcon(IconRegistry.from_name('fa5s.map-marked-alt', mice_colors[MiceType.MILIEU]))
        elif thread.type == MiceType.INQUIRY:
            self.icon.setIcon(IconRegistry.from_name('ei.question', mice_colors[MiceType.INQUIRY]))
        elif thread.type == MiceType.CHARACTER:
            self.icon.setIcon(IconRegistry.from_name('fa5s.user', mice_colors[MiceType.CHARACTER]))
        else:
            self.icon.setIcon(IconRegistry.from_name('fa5s.meteor', mice_colors[MiceType.EVENT]))

        self.lineText.setStyleSheet(f'border: 1px solid {mice_colors[thread.type]}')
        self.lineText.setText(thread.text)
        self.lineText.textEdited.connect(self._textChanged)

        retain_when_hidden(self.btnRemoval)
        self.installEventFilter(VisibilityToggleEventFilter(target=self.btnRemoval, parent=self))

        self.beginningSceneSelector = SceneSelector(app_env.novel, 'Beginning')
        self.beginningSceneSelector.sceneSelected.connect(self._beginningChanged)
        scene = self.thread.beginning_scene(app_env.novel)
        if scene:
            self.beginningSceneSelector.setScene(scene)

        self.endingSceneSelector = SceneSelector(app_env.novel, 'Ending')
        self.endingSceneSelector.sceneSelected.connect(self._endingChanged)
        scene = self.thread.ending_scene(app_env.novel)
        if scene:
            self.endingSceneSelector.setScene(scene)

        self.layout().insertWidget(2, self.beginningSceneSelector)
        self.layout().insertWidget(4, self.endingSceneSelector)

        self.btnRemoval.clicked.connect(lambda: self.removed.emit(self))

    def _textChanged(self, text: str):
        self.thread.text = text
        self.changed.emit()

    def _beginningChanged(self, scene: Scene):
        self.thread.beginning_scene_id = scene.id
        self.changed.emit()

    def _endingChanged(self, scene: Scene):
        self.thread.ending_scene_id = scene.id
        self.changed.emit()


class MiceQuotientDoc(QWidget, Ui_MiceQuotientDoc):
    changed = pyqtSignal()

    def __init__(self, doc: Document, mice: MiceQuotient, parent=None):
        super(MiceQuotientDoc, self).__init__(parent)
        self.setupUi(self)
        self.doc = doc
        self.mice = mice

        color = mice_colors[MiceType.MILIEU]
        self.btnMilieu.initStyleSheet(color, color=color)
        color = mice_colors[MiceType.INQUIRY]
        self.btnInquiry.initStyleSheet(color, color=color)
        color = mice_colors[MiceType.CHARACTER]
        self.btnCharacter.initStyleSheet(color, color=color)
        color = mice_colors[MiceType.EVENT]
        self.btnEvent.initStyleSheet(color, color=color)

        incr_font(self.btnTitle, 15)

        self.btnTitle.setText(self.doc.title)
        self.btnTitle.setIcon(IconRegistry.from_name(self.doc.icon, self.doc.icon_color))

        self.btnMilieu.clicked.connect(lambda: self._addNewThread(MiceType.MILIEU))
        self.btnInquiry.clicked.connect(lambda: self._addNewThread(MiceType.INQUIRY))
        self.btnCharacter.clicked.connect(lambda: self._addNewThread(MiceType.CHARACTER))
        self.btnEvent.clicked.connect(lambda: self._addNewThread(MiceType.EVENT))

        vbox(self.wdgThreads)
        self.wdgThreads.layout().addWidget(vspacer())

        for thread in self.mice.threads:
            self._addThread(thread)

    def _addNewThread(self, type: MiceType):
        thread = MiceThread(type)
        self.mice.threads.append(thread)

        self._addThread(thread)

    def _addThread(self, thread):
        widget = MiceThreadWidget(thread, self.wdgThreads)
        widget.changed.connect(self.changed.emit)
        widget.removed.connect(self._removeThreadWidget)
        self.wdgThreads.layout().insertWidget(self.wdgThreads.layout().count() - 1, widget)
        if self.isVisible():
            anim = qtanim.glow(widget, color=QColor(mice_colors[thread.type]))
            anim.finished.connect(lambda: widget.setGraphicsEffect(None))
        self.changed.emit()

    def _removeThreadWidget(self, widget: MiceThreadWidget):
        self.mice.threads.remove(widget.thread)
        self.wdgThreads.layout().removeWidget(widget)
        gc(widget)
        self.changed.emit()
