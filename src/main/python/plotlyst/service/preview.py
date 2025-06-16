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

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QTabWidget
from overrides import overrides
from qthandy import decr_icon

from plotlyst.common import DEFAULT_PREMIUM_LINK
from plotlyst.core.domain import Novel, Diagram, DiagramData, Character, CharacterPreferences, AvatarPreferences, Scene, \
    Plot, PlotType, ScenePlotReference, MINDMAP_PREVIEW, NETWORK_PREVIEW, BACKSTORY_PREVIEW, STORY_GRID_PREVIEW, \
    STORY_MAP_PREVIEW, WORLD_BUILDING_PREVIEW, SCENE_FUNCTIONS_PREVIEW
from plotlyst.resources import resource_registry
from plotlyst.view.common import push_btn, open_url, label, scroll_area, rows
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import apply_bg_image
from plotlyst.view.widget.character.editor import CharacterTimelineWidget
from plotlyst.view.widget.character.network import CharacterNetworkView, RelationsEditorScene
from plotlyst.view.widget.confirm import asked
from plotlyst.view.widget.display import PopupDialog
from plotlyst.view.widget.graphics import NetworkScene
from plotlyst.view.widget.scene.functions import SceneFunctionsWidget
from plotlyst.view.widget.scene.reader_drive import ReaderInformationEditor
from plotlyst.view.widget.scene.story_grid import ScenesGridWidget
from plotlyst.view.widget.scene.story_map import StoryMap
from plotlyst.view.widget.story_map import EventsMindMapView, EventsMindMapScene
from plotlyst.view.world_building_view import WorldBuildingView


def preview_novel() -> Novel:
    novel = Novel.new_novel('Preview')
    novel.tutorial = True
    novel.characters.append(
        _preview_character('Jane Doe', uuid.UUID('dd72a22e-2fff-495b-9e68-abeb0d726462'), 'mdi.alpha-j-circle-outline'))
    novel.characters.append(
        _preview_character('Anne', uuid.UUID('a6af7bab-f7c7-4f87-bb83-b5f3db8eb7a7'), 'mdi.flower-poppy'))
    novel.characters.append(
        _preview_character('Zsolt', uuid.UUID('66c17718-d4ac-4088-b9c9-0914add0ebb3'), 'mdi.alpha-z-box'))

    for i in range(10):
        novel.scenes.append(Scene(''))

    novel.plots.append(Plot('Character arc', plot_type=PlotType.Internal, icon='mdi.mirror', icon_color='#0FADBB'))
    novel.plots.append(Plot('Subplot', plot_type=PlotType.Subplot, icon='mdi.source-branch', icon_color='#d4a373'))

    novel.scenes[0].plot_values.append(ScenePlotReference(novel.plots[0]))
    novel.scenes[1].plot_values.append(ScenePlotReference(novel.plots[1]))
    novel.scenes[2].plot_values.append(ScenePlotReference(novel.plots[0]))
    novel.scenes[3].plot_values.append(ScenePlotReference(novel.plots[0]))
    novel.scenes[3].plot_values.append(ScenePlotReference(novel.plots[2]))

    novel.scenes[0].pov = novel.characters[0]
    novel.scenes[1].pov = novel.characters[0]
    novel.scenes[2].pov = novel.characters[0]
    novel.scenes[3].pov = novel.characters[1]

    return novel


def preview_diagram() -> Diagram:
    diagram = Diagram()
    diagram.loaded = True
    diagram.data = DiagramData()
    return diagram


def _preview_character(name: str, id_, icon: str) -> Character:
    return Character(name, id=id_, prefs=CharacterPreferences(
        avatar=AvatarPreferences(use_image=False, use_custom_icon=True, icon=icon)))


class PreviewPopup(PopupDialog):
    def __init__(self, widthPerc: float = 0.9, heightPerc: float = 0.8, minWidth: int = 600, minHeight: int = 500,
                 parent=None):
        super().__init__(parent)
        self._widthPerc = widthPerc
        self._heightPerc = heightPerc
        self._minWidth = minWidth
        self._minHeight = minHeight

        self.btnClose = push_btn(IconRegistry.from_name('ei.remove'), 'Close', properties=['confirm', 'cancel'])
        self.btnClose.clicked.connect(self.reject)
        decr_icon(self.btnClose, 4)

        self.frame.layout().addWidget(self.btnClose, alignment=Qt.AlignmentFlag.AlignRight)

        self.setMinimumSize(self._adjustedSize(self._widthPerc, self._heightPerc, self._minWidth, self._minHeight))

    @overrides
    def sizeHint(self) -> QSize:
        return self._adjustedSize(self._widthPerc, self._heightPerc, self._minWidth, self._minHeight)

    def display(self):
        self.exec()


class MindmapPreviewPopup(PreviewPopup):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.editor = self.MindmapPreview(preview_novel())
        self.editor.setDiagram(preview_diagram())

        self.frame.layout().insertWidget(0, self.editor)
        self.frame.layout().insertWidget(0, label(
            "This is a preview of the Mindmap feature. Feel free to explore the different mindmap items and connectors, but note that your work won't be saved.",
            description=True, wordWrap=True))

    class MindmapPreviewScene(EventsMindMapScene):

        @overrides
        def _load(self):
            pass

        @overrides
        def _save(self):
            pass

    class MindmapPreview(EventsMindMapView):

        @overrides
        def _initScene(self) -> NetworkScene:
            return MindmapPreviewPopup.MindmapPreviewScene(self._novel)


class NetworkPreviewPopup(PreviewPopup):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.editor = self.NetworkPreview(preview_novel())
        self.editor.setDiagram(preview_diagram())

        self.frame.layout().insertWidget(0, self.editor)
        self.frame.layout().insertWidget(0, label(
            "This is a preview of the Character Network feature. Feel free to explore this feature, but note that your work won't be saved.",
            description=True, wordWrap=True))

    class NetworkPreviewScene(RelationsEditorScene):

        @overrides
        def _load(self):
            pass

        @overrides
        def _save(self):
            pass

    class NetworkPreview(CharacterNetworkView):

        @overrides
        def _initScene(self) -> NetworkScene:
            return NetworkPreviewPopup.NetworkPreviewScene(self._novel)


class BackstoryPreviewPopup(PreviewPopup):
    def __init__(self, parent=None):
        super().__init__(widthPerc=0.5, minWidth=450, parent=parent)

        scroll = scroll_area()
        wdgEditor = rows()
        scroll.setWidget(wdgEditor)
        wdgEditor.setProperty('bg-image', True)
        apply_bg_image(wdgEditor, resource_registry.cover1)

        self.editor = CharacterTimelineWidget()
        self.editor.setCharacter(preview_novel().characters[0])
        wdgEditor.layout().addWidget(self.editor)

        self.frame.layout().insertWidget(0, scroll)


class StoryGridPreviewPopup(PreviewPopup):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.editor = ScenesGridWidget(preview_novel())
        self.frame.layout().insertWidget(0, self.editor)


class StoryMapPreviewPopup(PreviewPopup):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.editor = StoryMap()
        self.editor.setNovel(preview_novel())
        self.frame.layout().insertWidget(0, self.editor)


class WorldBuildingPreviewPopup(PreviewPopup):
    def __init__(self, parent=None):
        super().__init__(heightPerc=0.9, parent=parent)
        self.editor = WorldBuildingView(preview_novel())
        self.frame.layout().insertWidget(0, self.editor.widget)


class SceneFunctionsPreviewPopup(PreviewPopup):
    def __init__(self, parent=None):
        super().__init__(heightPerc=0.8, parent=parent)
        novel = preview_novel()
        scene = novel.scenes[6]

        self.tabs = QTabWidget()
        self.tabs.setProperty('centered', True)

        self.tabFunctions = rows()
        self.tabInfo = rows()
        self.tabFunctions.setProperty('muted-bg', True)
        self.tabInfo.setProperty('muted-bg', True)
        self.tabs.addTab(self.tabFunctions, IconRegistry.from_name('mdi.yin-yang'), "Scene functions")
        self.tabs.addTab(self.tabInfo, IconRegistry.from_name('fa5s.book-reader'), "Reader's information")

        self.functionsEditor = SceneFunctionsWidget(novel)
        self.functionsEditor.setScene(scene)
        self.tabFunctions.layout().addWidget(self.functionsEditor)

        self.infoEditor = ReaderInformationEditor(novel)
        self.infoEditor.setScene(scene)
        self.tabInfo.layout().addWidget(self.infoEditor)

        self.frame.layout().insertWidget(0, self.tabs)


def launch_preview(preview: str):
    if preview == MINDMAP_PREVIEW:
        MindmapPreviewPopup.popup()
    elif preview == NETWORK_PREVIEW:
        NetworkPreviewPopup.popup()
    elif preview == BACKSTORY_PREVIEW:
        BackstoryPreviewPopup.popup()
    elif preview == STORY_GRID_PREVIEW:
        StoryGridPreviewPopup.popup()
    elif preview == STORY_MAP_PREVIEW:
        StoryMapPreviewPopup.popup()
    elif preview == WORLD_BUILDING_PREVIEW:
        WorldBuildingPreviewPopup.popup()
    elif preview == SCENE_FUNCTIONS_PREVIEW:
        SceneFunctionsPreviewPopup.popup()
    else:
        if asked("To try this feature out, please download the latest version of Plotlyst.",
                 'Old version of Plotlyst detected',
                 btnConfirmText='Understood', btnCancelText='Close'):
            open_url(DEFAULT_PREMIUM_LINK)
