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

from PyQt6.QtCore import Qt, QSize
from overrides import overrides
from qthandy import decr_icon

from plotlyst.common import DEFAULT_PREMIUM_LINK
from plotlyst.core.domain import Novel, Diagram, DiagramData
from plotlyst.service.image import LoadedImage
from plotlyst.view.common import push_btn, open_url
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.confirm import asked
from plotlyst.view.widget.display import PopupDialog
from plotlyst.view.widget.graphics import NetworkScene
from plotlyst.view.widget.story_map import EventsMindMapView, EventsMindMapScene

MINDMAP_PREVIEW = 'mindmap'


class PreviewPopup(PopupDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.btnClose = push_btn(IconRegistry.from_name('ei.remove'), 'Close', properties=['confirm', 'cancel'])
        self.btnClose.clicked.connect(self.reject)
        decr_icon(self.btnClose, 4)

        self.frame.layout().addWidget(self.btnClose, alignment=Qt.AlignmentFlag.AlignRight)

    def display(self):
        self.exec()


class MindmapPreviewScene(EventsMindMapScene):

    @overrides
    def _load(self):
        pass

    @overrides
    def _save(self):
        pass

    @overrides
    def _uploadImage(self) -> Optional[LoadedImage]:
        pass


class MindmapPreview(EventsMindMapView):

    @overrides
    def _initScene(self) -> NetworkScene:
        return MindmapPreviewScene(self._novel)


class MindmapPreviewPopup(PreviewPopup):
    def __init__(self, parent=None):
        super().__init__(parent)

        novel = Novel('Preview', tutorial=True)
        self.editor = MindmapPreview(novel)

        diagram = Diagram()
        diagram.loaded = True
        diagram.data = DiagramData()

        self.editor.setDiagram(diagram)

        self.frame.layout().insertWidget(0, self.editor)

        self.setMinimumSize(self._adjustedSize(0.9, 0.8, 600, 500))

    @overrides
    def sizeHint(self) -> QSize:
        return self._adjustedSize(0.9, 0.8, 600, 500)


def launch_trial(trial: str):
    if trial == MINDMAP_PREVIEW:
        MindmapPreviewPopup.popup()
    else:
        if asked("To try this feature out, please upgrade to the latest version of Plotlyst.", 'Old Plotlyst version',
                 btnConfirmText='Understood', btnCancelText='Close'):
            open_url(DEFAULT_PREMIUM_LINK)

# def trial_button(trial: str) -> QPushButton:
#     btnTrial = push_btn(IconRegistry.from_name('fa5s.rocket', RELAXED_WHITE_COLOR), 'TRY IT OUT',
#                         properties=['confirm', 'positive'])
#     font = btnTrial.font()
#     font.setFamily(app_env.serif_font())
#     font.setPointSize(font.pointSize() - 1)
#     btnTrial.setFont(font)
#     btnTrial.installEventFilter(OpacityEventFilter(btnTrial, 0.8, 0.6))
#
#     btnTrial.clicked.connect(lambda: launch_trial(trial))
#
#     return btnTrial
