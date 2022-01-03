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
from typing import Optional

from PyQt6.QtCore import QModelIndex
from PyQt6.QtWidgets import QHeaderView
from overrides import overrides

from src.main.python.plotlyst.core.domain import Novel, Location
from src.main.python.plotlyst.model.locations_model import LocationsTreeModel, LocationNode
from src.main.python.plotlyst.view._view import AbstractNovelView
from src.main.python.plotlyst.view.generated.locations_view_ui import Ui_LocationsView
from src.main.python.plotlyst.view.icons import IconRegistry
from src.main.python.plotlyst.view.widget.location import LocationProfileTemplateView


class LocationsView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel)
        self.ui = Ui_LocationsView()
        self.ui.setupUi(self.widget)

        self.model = LocationsTreeModel(self.novel)
        self.ui.treeLocations.setModel(self.model)
        self.ui.treeLocations.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ui.treeLocations.setColumnWidth(1, 20)
        self.ui.treeLocations.clicked.connect(self._location_clicked)
        self.ui.treeLocations.expandAll()
        self.model.modelReset.connect(self.refresh)

        self.ui.btnAdd.setIcon(IconRegistry.plus_icon())
        self.ui.btnAdd.clicked.connect(self._add_location)
        self.ui.btnRemove.setIcon(IconRegistry.minus_icon())
        self.ui.btnRemove.clicked.connect(self._remove_location)

    @overrides
    def refresh(self):
        self.ui.treeLocations.expandAll()
        self.ui.btnRemove.setEnabled(False)

    def _add_location(self, parent: Optional[QModelIndex] = None):
        location = Location('New location')
        if parent:
            index = self.model.insertLocationUnder(location, parent)
        else:
            index = self.model.insertLocation(location)
        self.ui.treeLocations.select(index)
        self.ui.btnRemove.setEnabled(True)
        # self._edit(index)

    def _remove_location(self):
        selected = self.ui.treeLocations.selectionModel().selectedIndexes()
        if not selected:
            return
        self.model.removeLocation(selected[0])

    def _location_clicked(self, index: QModelIndex):
        self.ui.btnRemove.setEnabled(True)
        if index.column() == 1:
            self._add_location(index)
        else:
            if self.ui.wdgEditor.layout().count():
                item = self.ui.wdgEditor.layout().takeAt(0)
                item.widget().deleteLater()
            node: LocationNode = index.data(LocationsTreeModel.NodeRole)
            profile = LocationProfileTemplateView(self.novel, node.location, self.novel.location_profiles[0])
            self.ui.wdgEditor.layout().addWidget(profile)
