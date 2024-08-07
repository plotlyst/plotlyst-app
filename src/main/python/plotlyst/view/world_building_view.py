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
from dataclasses import dataclass
from typing import Optional

import qtanim
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from overrides import overrides
from qthandy import line
from qthandy.filter import OpacityEventFilter

from plotlyst.common import PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import Novel, WorldBuildingEntity
from plotlyst.env import app_env
from plotlyst.resources import resource_registry
from plotlyst.settings import settings
from plotlyst.view._view import AbstractNovelView
from plotlyst.view.common import link_buttons_to_pages, ButtonPressResizeEventFilter, shadow, \
    insert_before_the_end
from plotlyst.view.generated.world_building_view_ui import Ui_WorldBuildingView
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import apply_bg_image
from plotlyst.view.widget.tree import TreeSettings
from plotlyst.view.widget.world.editor import WorldBuildingEntityEditor, WorldBuildingEditorSettingsWidget, EntityLayoutType
from plotlyst.view.widget.world.glossary import WorldBuildingGlossaryEditor
from plotlyst.view.widget.world.map import WorldBuildingMapView
from plotlyst.view.widget.world.tree import EntityAdditionMenu


@dataclass
class WorldBuildingPalette:
    bg_color: str
    primary_color: str
    secondary_color: str
    tertiary_color: str


class WorldBuildingView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel)
        self.ui = Ui_WorldBuildingView()
        self.ui.setupUi(self.widget)
        apply_bg_image(self.ui.pageEntity, resource_registry.paper_bg)
        apply_bg_image(self.ui.pageGlossary, resource_registry.paper_bg)
        apply_bg_image(self.ui.scrollAreaWidgetContents, resource_registry.paper_bg)
        self._palette = WorldBuildingPalette(bg_color='#ede0d4', primary_color='#510442', secondary_color='#DABFA7',
                                             tertiary_color='#E3D0BD')
        # background: #F2F2F2;
        # 692345;
        self.ui.wdgCenterEditor.setStyleSheet(f'''
        #wdgCenterEditor {{
            background: {self._palette.bg_color};
            border-radius: 12px;
        }}
        ''')
        self.ui.lblBanner.setPixmap(QPixmap(resource_registry.vintage_pocket_banner))

        self._entity: Optional[WorldBuildingEntity] = None

        self.ui.btnNew.setIcon(IconRegistry.plus_icon(color='white'))
        self.ui.btnNew.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnNew))
        self.ui.btnTreeToggle.setIcon(IconRegistry.from_name('mdi.file-tree-outline'))
        self.ui.btnTreeToggle.clicked.connect(lambda x: qtanim.toggle_expansion(self.ui.wdgWorldContainer, x))
        self.ui.btnSettings.setIcon(IconRegistry.cog_icon())

        width = settings.worldbuilding_editor_max_width()
        self.ui.wdgCenterEditor.setMaximumWidth(width)
        self.ui.wdgSideBar.setStyleSheet(f'#wdgSideBar {{background: {self._palette.bg_color};}}')
        self._wdgSettings = WorldBuildingEditorSettingsWidget(width)
        self._wdgSettings.setMaximumWidth(150)
        self.ui.wdgSideBar.layout().addWidget(self._wdgSettings, alignment=Qt.AlignmentFlag.AlignRight)
        self._wdgSettings.widthChanged.connect(self._editor_max_width_changed)
        self._wdgSettings.layoutChanged.connect(self._layout_changed)
        self.ui.btnSettings.clicked.connect(lambda x: qtanim.toggle_expansion(self.ui.wdgSideBar, x))
        self.ui.wdgSideBar.setHidden(True)

        self.ui.btnSettings.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnSettings))
        self.ui.btnSettings.installEventFilter(OpacityEventFilter(self.ui.btnSettings, 0.9, leaveOpacity=0.7))
        shadow(self.ui.wdgWorldContainer)
        self._additionMenu = EntityAdditionMenu(self.ui.btnNew)
        self._additionMenu.entityTriggered.connect(self.ui.treeWorld.addEntity)
        self.ui.iconReaderMode.setIcon(IconRegistry.from_name('fa5s.eye'))

        self.ui.wdgSeparator.layout().addWidget(line(color=self._palette.primary_color))

        self.ui.btnWorldView.setIcon(IconRegistry.world_building_icon())
        self.ui.btnMapView.setIcon(IconRegistry.from_name('fa5s.map-marked-alt', color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnHistoryView.setIcon(
            IconRegistry.from_name('mdi.timeline-outline', color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnGlossaryView.setIcon(IconRegistry.from_name('mdi.book-alphabet', color_on=PLOTLYST_SECONDARY_COLOR))

        self.ui.splitterNav.setSizes([150, 500])
        font = self.ui.lineName.font()
        font.setPointSize(32)
        font.setFamily(app_env.sans_serif_font())
        self.ui.lineName.setFont(font)
        self.ui.lineName.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ui.lineName.setStyleSheet(f'''
        QLineEdit {{
            border: 0px;
            background-color: rgba(0, 0, 0, 0);
            color: {self._palette.primary_color}; 
        }}''')

        self.ui.lineName.textEdited.connect(self._name_edited)

        self._editor = WorldBuildingEntityEditor(self.novel)
        insert_before_the_end(self.ui.wdgCenterEditor, self._editor)

        self.ui.treeWorld.setSettings(TreeSettings(font_incr=2, bg_color=self._palette.bg_color,
                                                   action_buttons_color=self._palette.primary_color,
                                                   selection_bg_color=self._palette.secondary_color,
                                                   hover_bg_color=self._palette.tertiary_color,
                                                   selection_text_color=self._palette.primary_color))
        self.ui.treeWorld.setNovel(self.novel)
        self.ui.treeWorld.entitySelected.connect(self._selection_changed)
        self.ui.treeWorld.selectRoot()

        self.map = WorldBuildingMapView(self.novel)
        self.ui.pageMap.layout().addWidget(self.map)

        self.glossaryEditor = WorldBuildingGlossaryEditor(self.novel)
        self.ui.wdgGlossaryParent.layout().addWidget(self.glossaryEditor)

        link_buttons_to_pages(self.ui.stackedWidget, [(self.ui.btnWorldView, self.ui.pageEntity),
                                                      (self.ui.btnMapView, self.ui.pageMap),
                                                      (self.ui.btnHistoryView, self.ui.pageTimeline),
                                                      (self.ui.btnGlossaryView, self.ui.pageGlossary)])
        self.ui.btnWorldView.setChecked(True)

        self.ui.iconReaderMode.setHidden(True)
        self.ui.readerModeToggle.setHidden(True)
        self.ui.btnHistoryView.setHidden(True)

        self.ui.btnTreeToggle.setChecked(True)

    @overrides
    def refresh(self):
        pass

    def _selection_changed(self, entity: WorldBuildingEntity):
        self._entity = entity
        self._wdgSettings.setEntity(self._entity)
        self.ui.lineName.setText(self._entity.name)
        self._editor.setEntity(self._entity)

    def _name_edited(self, name: str):
        self._entity.name = name
        self.ui.treeWorld.updateEntity(self._entity)
        self.repo.update_world(self.novel)

    def _icon_changed(self, icon_name: str, color: QColor):
        self._entity.icon = icon_name
        self._entity.icon_color = color.name()
        self.ui.treeWorld.updateEntity(self._entity)

    def _editor_max_width_changed(self, value: int):
        self.ui.wdgCenterEditor.setMaximumWidth(value)
        settings.set_worldbuilding_editor_max_width(value)

    def _layout_changed(self, layoutType: EntityLayoutType):
        if self._entity:
            if layoutType == EntityLayoutType.SIDE:
                self._entity.side_visible = True
            else:
                self._entity.side_visible = False

            self.repo.update_world(self.novel)
            self._editor.layoutChangedEvent()
