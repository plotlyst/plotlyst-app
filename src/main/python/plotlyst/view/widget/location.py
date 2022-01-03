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

from PyQt6.QtCore import Qt

from src.main.python.plotlyst.core.domain import Location, ProfileTemplate, location_name_field, Novel
from src.main.python.plotlyst.view.widget.template import ProfileTemplateView, LabelsSelectionWidget
from src.main.python.plotlyst.worker.persistence import RepositoryPersistenceManager


class LocationProfileTemplateView(ProfileTemplateView):
    def __init__(self, novel: Novel, location: Location, profile: ProfileTemplate):
        super().__init__(location.template_values, profile)
        self.novel = novel
        self.location = location

        for widget in self.widgets:
            if widget.field.id == location_name_field.id:
                self._name_widget = widget

        self._name_widget.wdgEditor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._name_widget.setFocus()

        self._name_widget.setValue(self.location.name)

        for widget in self.widgets:
            if isinstance(widget.wdgEditor, LabelsSelectionWidget):
                widget.wdgEditor.selectionChanged.connect(self._save)

        self._name_widget.wdgEditor.textChanged.connect(self._save)

        self.repo = RepositoryPersistenceManager.instance()

    def _save(self):
        self.location.name = self._name_widget.value()
        self.location.template_values.clear()
        self.location.template_values.extend(self.values())
        self.repo.update_novel(self.novel)
