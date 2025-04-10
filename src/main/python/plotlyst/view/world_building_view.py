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
from typing import Optional, List

import qtanim
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QWidget, QGraphicsColorizeEffect
from overrides import overrides
from qthandy import incr_icon, incr_font
from qthandy.filter import OpacityEventFilter

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, RELAXED_WHITE_COLOR
from plotlyst.core.domain import Novel, WorldBuildingEntity, NovelDescriptor
from plotlyst.env import app_env
from plotlyst.resources import resource_registry
from plotlyst.service.cache import try_location, entities_registry
from plotlyst.settings import settings
from plotlyst.view._view import AbstractNovelView
from plotlyst.view.common import link_buttons_to_pages, ButtonPressResizeEventFilter, shadow, \
    insert_before_the_end, to_rgba_str
from plotlyst.view.generated.world_building_view_ui import Ui_WorldBuildingView
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import apply_bg_image
from plotlyst.view.widget.display import PremiumOverlayWidget
from plotlyst.view.widget.importing import ImportLocationPopup
from plotlyst.view.widget.tree import TreeSettings
from plotlyst.view.widget.world.editor import WorldBuildingEntityEditor, WorldBuildingEditorSettingsWidget, \
    EntityLayoutType
from plotlyst.view.widget.world.glossary import WorldBuildingGlossaryEditor
from plotlyst.view.widget.world.map import WorldBuildingMapView
from plotlyst.view.widget.world.milieu import LocationEditor
from plotlyst.view.widget.world.theme import WorldBuildingPalette
from plotlyst.view.widget.world.tree import EntityAdditionMenu


class WorldBuildingSeparatorWidget(QWidget):
    def __init__(self, palette: WorldBuildingPalette):
        super().__init__()
        self._palette = palette
        self.svg_renderer = QSvgRenderer(resource_registry.divider1)
        self.setMinimumSize(400, 55)

        self.refreshColor()

    def refreshColor(self):
        effect = QGraphicsColorizeEffect(self)
        effect.setColor(QColor(self._palette.primary_color))
        self.setGraphicsEffect(effect)

    @overrides
    def paintEvent(self, event):
        painter = QPainter(self)
        rect = QRectF(0, 0, self.width(), self.height())
        self.svg_renderer.render(painter, rect)


class WorldBuildingView(AbstractNovelView):

    def __init__(self, novel: Novel, main_window=None):
        super().__init__(novel)
        self.ui = Ui_WorldBuildingView()
        self.ui.setupUi(self.widget)
        self.main_window = main_window
        apply_bg_image(self.ui.pageEntity, resource_registry.paper_bg)
        apply_bg_image(self.ui.pageGlossary, resource_registry.paper_bg)
        apply_bg_image(self.ui.scrollAreaWidgetContents, resource_registry.paper_bg)
        self._palette = WorldBuildingPalette(bg_color='#ede0d4', primary_color='#510442', secondary_color='#DABFA7',
                                             tertiary_color='#E3D0BD')
        self._separator = WorldBuildingSeparatorWidget(self._palette)
        self.ui.wdgNameHeader.layout().addWidget(self._separator)

        self._entity: Optional[WorldBuildingEntity] = None

        self.ui.btnNew.setIcon(IconRegistry.plus_icon(color=RELAXED_WHITE_COLOR))
        self.ui.btnNew.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnNew))
        self.ui.btnTreeToggle.setIcon(IconRegistry.from_name('mdi.file-tree-outline'))
        self.ui.btnTreeToggle.clicked.connect(lambda x: qtanim.toggle_expansion(self.ui.wdgWorldContainer, x))
        self.ui.btnSettings.setIcon(IconRegistry.cog_icon())

        self.ui.btnAddLocation.setIcon(IconRegistry.plus_icon(color=RELAXED_WHITE_COLOR))
        self.ui.btnAddLocation.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnAddLocation))
        self.ui.btnTreeToggleMilieu.setIcon(IconRegistry.from_name('mdi.file-tree-outline'))
        self.ui.btnTreeToggleMilieu.clicked.connect(lambda x: qtanim.toggle_expansion(self.ui.wdgMilieuSidebar, x))

        self.locationEditor = LocationEditor(self.novel)
        self.ui.wdgMilieuCenterEditor.layout().insertWidget(0, self.locationEditor)

        self.ui.treeLocations.locationSelected.connect(self.locationEditor.setLocation)
        self.ui.treeLocations.locationDeleted.connect(self.locationEditor.locationDeletedEvent)
        self.ui.treeLocations.updateWorldBuildingEntity.connect(self._update_world_building_entity)
        self.ui.treeLocations.unlinkWorldBuildingEntity.connect(self._unlink_world_building_entity)
        self.ui.treeLocations.setNovel(self.novel)
        self.locationEditor.locationNameChanged.connect(self.ui.treeLocations.updateItem)
        self.ui.btnAddLocation.clicked.connect(self.ui.treeLocations.addNewLocation)
        self.ui.splitterMilieuNav.setSizes([175, 500])

        if self.novel.parent:
            self.set_series_enabled(True)

        width = settings.worldbuilding_editor_max_width()
        self.ui.wdgCenterEditor.setMaximumWidth(width)
        self._wdgSettings = WorldBuildingEditorSettingsWidget(width, self._palette)
        self._wdgSettings.setMaximumWidth(150)
        self.ui.wdgSideBar.layout().addWidget(self._wdgSettings, alignment=Qt.AlignmentFlag.AlignRight)
        self._wdgSettings.widthChanged.connect(self._editor_max_width_changed)
        self._wdgSettings.layoutChanged.connect(self._layout_changed)
        self._wdgSettings.paletteChanged.connect(self._palette_changed)
        self.ui.btnSettings.clicked.connect(lambda x: qtanim.toggle_expansion(self.ui.wdgSideBar, x))
        self.ui.wdgSideBar.setHidden(True)

        self.ui.btnSettings.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnSettings))
        self.ui.btnSettings.installEventFilter(OpacityEventFilter(self.ui.btnSettings, 0.9, leaveOpacity=0.7))
        shadow(self.ui.wdgWorldContainer)
        self._additionMenu = EntityAdditionMenu(self.novel, self.ui.btnNew)
        self._additionMenu.entityTriggered.connect(self.ui.treeWorld.addEntity)
        self._additionMenu.topicsSelected.connect(self.ui.treeWorld.addEntities)

        self.ui.btnMilieuView.setIcon(IconRegistry.world_building_icon())
        self.ui.btnWorldView.setIcon(IconRegistry.from_name('ri.quill-pen-fill'))
        self.ui.btnMapView.setIcon(IconRegistry.from_name('fa5s.map-marked-alt', color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnHistoryView.setIcon(
            IconRegistry.from_name('mdi.timeline-outline', color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnGlossaryView.setIcon(IconRegistry.from_name('mdi.book-alphabet', color_on=PLOTLYST_SECONDARY_COLOR))

        for btn in self.ui.buttonGroup.buttons():
            incr_icon(btn, 2)
            incr_font(btn, 2)

        self.ui.splitterNav.setSizes([150, 500])
        font = self.ui.lineName.font()
        font.setPointSize(32)
        font.setFamily(app_env.serif_font())
        self.ui.lineName.setFont(font)
        self.ui.lineName.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.ui.lineName.textEdited.connect(self._name_edited)

        self._editor = WorldBuildingEntityEditor(self.novel, self._palette)
        insert_before_the_end(self.ui.wdgCenterEditor, self._editor)

        self.ui.treeWorld.setSettings(TreeSettings(font_incr=2, bg_color=self._palette.bg_color,
                                                   action_buttons_color=self._palette.primary_color,
                                                   selection_bg_color=self._palette.secondary_color,
                                                   hover_bg_color=self._palette.tertiary_color,
                                                   selection_text_color=self._palette.primary_color))
        self.ui.treeWorld.setNovel(self.novel)
        self.ui.treeWorld.entitySelected.connect(self._selection_changed)
        self.ui.treeWorld.milieuLinked.connect(self._milieu_linked)
        self.ui.treeWorld.milieuUnlinked.connect(self._milieu_unlinked)
        self.ui.treeWorld.selectRoot()

        self.map = WorldBuildingMapView(self.novel)
        self.ui.pageMap.layout().addWidget(self.map)

        self.glossaryEditor = WorldBuildingGlossaryEditor(self.novel, self._palette)
        self.ui.wdgGlossaryParent.layout().addWidget(self.glossaryEditor)

        link_buttons_to_pages(self.ui.stackedWidget, [(self.ui.btnMilieuView, self.ui.pageMilieu),
                                                      (self.ui.btnWorldView, self.ui.pageEntity),
                                                      (self.ui.btnMapView, self.ui.pageMap),
                                                      (self.ui.btnHistoryView, self.ui.pageTimeline),
                                                      (self.ui.btnGlossaryView, self.ui.pageGlossary)])
        self.ui.btnMilieuView.setChecked(True)

        self.ui.btnHistoryView.setHidden(True)

        self._update_style()

        if not app_env.profile().get('world-building', False):
            PremiumOverlayWidget.worldbuildingOverlay(self.ui.wdgMilieuCenterEditor)
            PremiumOverlayWidget.worldbuildingOverlay(self.ui.wdgCenterEditor)
            PremiumOverlayWidget.worldbuildingOverlay(self.ui.pageMap)
            PremiumOverlayWidget.worldbuildingOverlay(self.ui.pageGlossary)

    @overrides
    def refresh(self):
        pass

    def set_series_enabled(self, enabled: bool):
        pass
        # if enabled:
        #     self._location_series_menu = MenuWidget()
        #     self._location_series_menu.addAction(
        #         action('Add new location', IconRegistry.location_icon(), slot=self.ui.treeLocations.addNewLocation))
        #     self._location_series_menu.addSeparator()
        #     self._location_series_menu.addAction(
        #         action('Import from series...', IconRegistry.series_icon(), slot=self.import_from_series))
        # else:
        #     if self._location_series_menu:
        #         gc(self._location_series_menu)
        #         self._location_series_menu = None

    def import_from_series(self):
        series = entities_registry.series(self.novel)
        if series:
            novels: List[NovelDescriptor] = self.main_window.seriesNovels(series)
            novels[:] = [x for x in novels if x.id != self.novel.id]
            locations = ImportLocationPopup.popup(series, novels)
            if locations:
                self.novel.locations.extend(locations)
                self.ui.treeLocations.setNovel(self.novel)
                self.repo.update_novel(self.novel)

    def _update_style(self):
        trans_bg_color = to_rgba_str(QColor(self._palette.bg_color), 235)
        self.ui.wdgCenterEditor.setStyleSheet(f'''
                #wdgCenterEditor {{
                    background: {trans_bg_color};
                    border-radius: 12px;
                }}
                ''')
        self.ui.wdgSideBar.setStyleSheet(f'#wdgSideBar {{background: {self._palette.bg_color};}}')
        self.ui.lineName.setStyleSheet(f'''
                QLineEdit {{
                    border: 0px;
                    background-color: rgba(0, 0, 0, 0);
                    color: {self._palette.primary_color}; 
                }}''')
        self.ui.wdgGlossaryParent.setStyleSheet(f'QWidget {{background: {self._palette.bg_color};}}')

    def _selection_changed(self, entity: WorldBuildingEntity):
        self._entity = entity
        self._wdgSettings.setEntity(self._entity)
        self._update_name()
        self._editor.setEntity(self._entity)

    def _update_name(self):
        if self._entity.ref:
            location = try_location(self._entity)
            if location:
                self.ui.lineName.setText(location.name)
                self.ui.lineName.setReadOnly(True)
            else:
                self.ui.treeWorld.updateEntity(self._entity)
                self.ui.lineName.setReadOnly(False)
        else:
            self.ui.lineName.setText(self._entity.name)
            self.ui.lineName.setReadOnly(False)

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

    def _palette_changed(self):
        self._update_style()
        self._separator.refreshColor()

    def _update_world_building_entity(self, entity: WorldBuildingEntity):
        self.ui.treeWorld.updateEntity(entity)
        if self._entity is entity:
            self._update_name()

    def _milieu_linked(self, entity: WorldBuildingEntity):
        if self._entity is entity:
            self._update_name()

    def _milieu_unlinked(self, entity: WorldBuildingEntity):
        if self._entity is entity:
            self._update_name()

    def _unlink_world_building_entity(self, entity: WorldBuildingEntity):
        entity.ref = None
        self.ui.treeWorld.updateEntity(entity)
        if self._entity is entity:
            self._update_name()

        self.repo.update_world(self.novel)
