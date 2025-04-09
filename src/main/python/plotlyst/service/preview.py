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
import uuid
from typing import Optional

from PyQt6.QtCore import Qt, QSize
from overrides import overrides
from qthandy import decr_icon

from plotlyst.common import DEFAULT_PREMIUM_LINK
from plotlyst.core.domain import Novel, Diagram, DiagramData, Character, CharacterPreferences, AvatarPreferences
from plotlyst.service.image import LoadedImage
from plotlyst.view.common import push_btn, open_url, label
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


def preview_novel() -> Novel:
    novel = Novel('Preview', tutorial=True)
    novel.characters.append(
        _preview_character('Jane Doe', uuid.UUID('dd72a22e-2fff-495b-9e68-abeb0d726462'), 'mdi.alpha-j-circle-outline'))
    novel.characters.append(
        _preview_character('Anne', uuid.UUID('a6af7bab-f7c7-4f87-bb83-b5f3db8eb7a7'), 'mdi.flower-poppy'))
    novel.characters.append(
        _preview_character('Zsolt', uuid.UUID('66c17718-d4ac-4088-b9c9-0914add0ebb3'), 'mdi.alpha-z-box'))

    return novel


def _preview_character(name: str, id_, icon: str) -> Character:
    return Character(name, id=id_, prefs=CharacterPreferences(
        avatar=AvatarPreferences(use_image=False, use_custom_icon=True, icon=icon)))


class MindmapPreviewPopup(PreviewPopup):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.editor = MindmapPreview(preview_novel())

        diagram = Diagram()
        diagram.loaded = True
        diagram.data = DiagramData()

        self.editor.setDiagram(diagram)

        self.frame.layout().insertWidget(0, self.editor)
        self.frame.layout().insertWidget(0, label(
            "This is a preview of the Mindmap feature. Feel free to explore the different mindmap items and connectors, but note that your work won't be saved.",
            description=True, wordWrap=True))

        self.setMinimumSize(self._adjustedSize(0.9, 0.8, 600, 500))

    @overrides
    def sizeHint(self) -> QSize:
        return self._adjustedSize(0.9, 0.8, 600, 500)


def launch_preview(preview: str):
    if preview == MINDMAP_PREVIEW:
        MindmapPreviewPopup.popup()
    else:
        if asked("To try this feature out, please upgrade to the latest version of Plotlyst.", 'Old Plotlyst version',
                 btnConfirmText='Understood', btnCancelText='Close'):
            open_url(DEFAULT_PREMIUM_LINK)
