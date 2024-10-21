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
from functools import partial
from typing import Optional, List

import qtanim
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QWidget, QLineEdit, QGraphicsColorizeEffect, QGridLayout
from overrides import overrides
from qthandy import vbox, incr_font, vspacer, line, clear_layout, incr_icon, decr_icon, margins, spacer, hbox, grid, sp
from qthandy.filter import OpacityEventFilter, DisabledClickEventFilter
from qtmenu import MenuWidget

from plotlyst.common import recursive
from plotlyst.core.domain import Novel, Location, WorldBuildingEntity, LocationSensorType, SensoryPerception
from plotlyst.event.core import emit_event
from plotlyst.events import LocationAddedEvent, LocationDeletedEvent, \
    RequestMilieuDictionaryResetEvent
from plotlyst.service.cache import entities_registry
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import fade_in, insert_before_the_end, DelayedSignalSlotConnector, push_btn, tool_btn, label, \
    fade_out_and_gc
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.widget.confirm import confirmed
from plotlyst.view.widget.display import Emoji
from plotlyst.view.widget.input import DecoratedTextEdit, Toggle
from plotlyst.view.widget.settings import SettingBaseWidget
from plotlyst.view.widget.tree import TreeSettings, ItemBasedTreeView, ItemBasedNode


class LocationNode(ItemBasedNode):
    added = pyqtSignal()

    def __init__(self, location: Location, parent=None, readOnly: bool = False,
                 settings: Optional[TreeSettings] = None):
        super().__init__(location.name, parent=parent, settings=settings)
        self._location = location
        self.setPlusButtonEnabled(not readOnly)
        self.setMenuEnabled(not readOnly)
        self.setTranslucentIconEnabled(True)
        self._actionChangeIcon.setVisible(False)
        self._btnAdd.clicked.connect(self.added)
        self.refresh()

    @overrides
    def item(self) -> Location:
        return self._location

    @overrides
    def refresh(self):
        self._lblTitle.setText(self._location.name if self._location.name else 'Location')
        # if self._novel.icon:
        #     self._icon.setIcon(IconRegistry.from_name(self._novel.icon, self._novel.icon_color))
        # else:
        self._icon.setIcon(IconRegistry.location_icon('black'))
        self._icon.setVisible(True)

    @overrides
    def _iconChanged(self, iconName: str, iconColor: str):
        pass
        # self._novel.icon = iconName
        # self._novel.icon_color = iconColor


class LocationsTreeView(ItemBasedTreeView):
    LOCATION_ENTITY_MIMETYPE = 'application/milieu-location'
    locationSelected = pyqtSignal(Location)
    locationDeleted = pyqtSignal(Location)
    updateWorldBuildingEntity = pyqtSignal(WorldBuildingEntity)
    unlinkWorldBuildingEntity = pyqtSignal(WorldBuildingEntity)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._novel: Optional[Novel] = None
        self._readOnly = False
        self._settings = TreeSettings(font_incr=2)

        self.repo = RepositoryPersistenceManager.instance()

    def setNovel(self, novel: Novel, readOnly: bool = False):
        def addChildWdg(parent: Location, child: Location):
            childWdg = self._initNode(child)
            self._nodes[parent].addChild(childWdg)

        self._novel = novel
        self._readOnly = readOnly

        self.clearSelection()
        self._nodes.clear()

        clear_layout(self._centralWidget)
        for location in self._novel.locations:
            node = self._initNode(location)
            self._centralWidget.layout().addWidget(node)
            recursive(location, lambda parent: parent.children, addChildWdg)
        self._centralWidget.layout().addWidget(vspacer())

        if self._novel.locations:
            node = self._nodes[self._novel.locations[0]]
            node.select()
            self._selectionChanged(node, True)

    @overrides
    def updateItem(self, location: Location):
        super().updateItem(location)
        for ref in entities_registry.refs(location):
            if isinstance(ref, WorldBuildingEntity):
                self.updateWorldBuildingEntity.emit(ref)

    def addNewLocation(self):
        location = Location()
        node = self._initNode(location)
        insert_before_the_end(self._centralWidget, node)
        node.select()
        self._selectionChanged(node, node.isSelected())

        self._novel.locations.append(location)
        self._save()

        emit_event(self._novel, LocationAddedEvent(self, location))

    def _addLocationUnder(self, node: LocationNode):
        location = Location()
        child = self._initNode(location)
        node.addChild(child)
        fade_in(child)

        node.item().children.append(location)
        self._save()
        emit_event(self._novel, LocationAddedEvent(self, location))

    def _deleteLocation(self, node: LocationNode):
        loc: Location = node.item()
        title = f'Are you sure you want to delete the location "{loc.name if loc.name else "Untitled"}"?'
        msg = 'This action cannot be undone, and the location and all its references will be lost.'
        if not confirmed(msg, title):
            return

        if isinstance(node.parent().parent(), LocationNode):
            parent: LocationNode = node.parent().parent()
            parent.item().children.remove(loc)
        else:
            self._novel.locations.remove(loc)

        self._deleteNode(node)
        self.locationDeleted.emit(loc)

        for ref in entities_registry.refs(loc):
            if isinstance(ref, WorldBuildingEntity):
                self.unlinkWorldBuildingEntity.emit(ref)

        self._save()
        emit_event(self._novel, LocationDeletedEvent(self, loc))

    @overrides
    def _emitSelectionChanged(self, location: Location):
        self.locationSelected.emit(location)

    @overrides
    def _mimeType(self) -> str:
        return self.LOCATION_ENTITY_MIMETYPE

    @overrides
    def _topLevelItems(self) -> List[Location]:
        return self._novel.locations

    @overrides
    def _node(self, location: Location) -> LocationNode:
        return LocationNode(location, settings=self._settings)

    @overrides
    def _save(self):
        self.repo.update_novel(self._novel)

    @overrides
    def _removeFromParentEntity(self, location: Location, node: LocationNode):
        if node.parent() is self._centralWidget:
            self._novel.locations.remove(location)
        else:
            super()._removeFromParentEntity(location, node)

    @overrides
    def _initNode(self, location: Location) -> LocationNode:
        node = LocationNode(location, readOnly=self._readOnly, settings=self._settings)
        self._nodes[location] = node
        node.selectionChanged.connect(partial(self._selectionChanged, node))
        node.added.connect(partial(self._addLocationUnder, node))
        node.deleted.connect(partial(self._deleteLocation, node))

        if not self._readOnly:
            self._enhanceWithDnd(node)

        return node


class LocationAttributeSetting(SettingBaseWidget):
    settingChanged = pyqtSignal(LocationSensorType, bool)

    def __init__(self, attrType: LocationSensorType, parent=None):
        super().__init__(parent)
        self._attrType = attrType
        self._title.setText(attrType.display_name())
        self._title.setIcon(IconRegistry.from_name(attrType.icon()))
        self._description.setWordWrap(False)
        self._description.setText(attrType.description())
        self._toggle.setChecked(False)

        margins(self, left=10)

        self._title.installEventFilter(DisabledClickEventFilter(self._wdgTitle, lambda: qtanim.shake(self._toggle)))
        self._wdgTitle.installEventFilter(DisabledClickEventFilter(self._wdgTitle, lambda: qtanim.shake(self._toggle)))

    @overrides
    def _clicked(self, toggled: bool):
        self.settingChanged.emit(self._attrType, toggled)


class LocationAttributeTextEdit(DecoratedTextEdit):
    changed = pyqtSignal()

    def __init__(self, attrType: LocationSensorType, perception: SensoryPerception, parent=None,
                 nightMode: bool = False):
        super().__init__(parent)
        self._perception = perception
        self._nightMode = nightMode

        self.setProperty('rounded', True)
        if nightMode:
            self.setProperty('night-mode', True)
        else:
            self.setProperty('white-bg', True)
        desc = attrType.description()
        self.setPlaceholderText(desc)
        self.setMaximumWidth(600)
        self.setEmoji(attrType.emoji(), desc)

        if self._nightMode:
            self.setText(self._perception.night_text)
            effect = QGraphicsColorizeEffect()
            if attrType == LocationSensorType.SOUND:
                emojieffect = QGraphicsColorizeEffect()
                emojieffect.setColor(Qt.GlobalColor.gray)
                self.decoration().setGraphicsEffect(emojieffect)
            effect.setColor(Qt.GlobalColor.black)
            self.setGraphicsEffect(effect)
        else:
            self.setText(self._perception.text)
        self.textChanged.connect(self._textChanged)

        sp(self).v_exp()

    def _textChanged(self):
        if self._nightMode:
            self._perception.night_text = self.toPlainText()
        else:
            self._perception.text = self.toPlainText()

        self.changed.emit()


class LocationAttributeSelectorMenu(MenuWidget):
    settingChanged = pyqtSignal(LocationSensorType, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        apply_white_menu(self)
        self.settingSight = LocationAttributeSetting(LocationSensorType.SIGHT)
        self.settingSound = LocationAttributeSetting(LocationSensorType.SOUND)
        self.settingSmell = LocationAttributeSetting(LocationSensorType.SMELL)
        self.settingTaste = LocationAttributeSetting(LocationSensorType.TASTE)
        self.settingTexture = LocationAttributeSetting(LocationSensorType.TEXTURE)

        self.settingSight.settingChanged.connect(self.settingChanged)
        self.settingSound.settingChanged.connect(self.settingChanged)
        self.settingSmell.settingChanged.connect(self.settingChanged)
        self.settingTaste.settingChanged.connect(self.settingChanged)
        self.settingTexture.settingChanged.connect(self.settingChanged)

        self.toggleDayNight = Toggle()
        effect = QGraphicsColorizeEffect(self.toggleDayNight)
        effect.setColor(Qt.GlobalColor.black)
        self.toggleDayNight.setGraphicsEffect(effect)

        self.wdgPerceptionsHeader = QWidget()
        hbox(self.wdgPerceptionsHeader, spacing=0)
        self.wdgPerceptionsHeader.layout().addWidget(label('Sensory perceptions'))
        self.wdgPerceptionsHeader.layout().addWidget(spacer())
        self.wdgPerceptionsHeader.layout().addWidget(label('Day-night cycle', description=True))
        self.wdgPerceptionsHeader.layout().addWidget(Emoji(self, ':sun_with_face:'))
        self.wdgPerceptionsHeader.layout().addWidget(label('/'))
        self.wdgPerceptionsHeader.layout().addWidget(Emoji(self, ':waxing_crescent_moon:'))
        self.wdgPerceptionsHeader.layout().addWidget(self.toggleDayNight)

        self.addWidget(self.wdgPerceptionsHeader)
        self.addSeparator()

        self.addWidget(self.settingSight)
        self.addWidget(self.settingSound)
        self.addWidget(self.settingSmell)
        self.addWidget(self.settingTaste)
        self.addWidget(self.settingTexture)

    def reset(self):
        self.settingSight.setChecked(False)
        self.settingSound.setChecked(False)
        self.settingSmell.setChecked(False)
        self.settingTaste.setChecked(False)
        self.settingTexture.setChecked(False)

    def setTypeChecked(self, attrType: LocationSensorType, checked: bool):
        if attrType == LocationSensorType.SIGHT:
            self.settingSight.setChecked(checked)
        elif attrType == LocationSensorType.SOUND:
            self.settingSound.setChecked(checked)
        elif attrType == LocationSensorType.SMELL:
            self.settingSmell.setChecked(checked)
        elif attrType == LocationSensorType.TASTE:
            self.settingTaste.setChecked(checked)
        elif attrType == LocationSensorType.TEXTURE:
            self.settingTexture.setChecked(checked)


class LocationEditor(QWidget):
    locationNameChanged = pyqtSignal(Location)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._location: Optional[Location] = None

        self.lineEditName = QLineEdit()
        self.lineEditName.setPlaceholderText('Location name')
        self.lineEditName.setProperty('transparent', True)
        incr_font(self.lineEditName, 8)
        self.lineEditName.textEdited.connect(self._nameEdited)
        DelayedSignalSlotConnector(self.lineEditName.textEdited, self._nameSet, parent=self)

        self.textSummary = DecoratedTextEdit()
        self.textSummary.setProperty('rounded', True)
        self.textSummary.setProperty('white-bg', True)
        self.textSummary.setPlaceholderText('Summarize this location')
        self.textSummary.setMaximumSize(450, 85)
        self.textSummary.setEmoji(':scroll:', 'Summary')
        self.textSummary.textChanged.connect(self._summaryChanged)

        self.btnAttributes = push_btn(IconRegistry.from_name('mdi6.note-text-outline', 'grey'), text='Attributes',
                                      transparent_=True)
        self.btnAttributesEditor = tool_btn(IconRegistry.plus_edit_icon('grey'), transparent_=True)
        incr_icon(self.btnAttributes, 2)
        incr_font(self.btnAttributes, 2)
        decr_icon(self.btnAttributesEditor)
        self.btnAttributes.installEventFilter(OpacityEventFilter(self.btnAttributes, leaveOpacity=0.7))

        self._attributesSelectorMenu = LocationAttributeSelectorMenu(self.btnAttributesEditor)
        self._attributesSelectorMenu.toggleDayNight.clicked.connect(self._dayNightToggled)
        self._attributesSelectorMenu.settingChanged.connect(self._settingChanged)
        self.btnAttributes.clicked.connect(lambda: self._attributesSelectorMenu.exec())

        self.wdgDayNightHeader = QWidget()
        hbox(self.wdgDayNightHeader)
        self.wdgDayNightHeader.layout().addWidget(Emoji(emoji=':sun_with_face:'))
        self.wdgDayNightHeader.layout().addWidget(Emoji(emoji=':waxing_crescent_moon:'))
        self.wdgDayNightHeader.setHidden(True)
        margins(self.wdgDayNightHeader, left=15)

        self.wdgAttributes = QWidget()
        self._gridAttributesLayout: QGridLayout = grid(self.wdgAttributes)
        sp(self.wdgAttributes).v_max()
        spac = spacer()
        sp(spac).h_preferred()
        self._gridAttributesLayout.addWidget(spac, 25, 1, 1, 1)
        margins(self.wdgAttributes, left=15)
        self._gridAttributesLayout.setVerticalSpacing(15)
        self._gridAttributesLayout.setHorizontalSpacing(7)

        vbox(self)
        self.layout().addWidget(self.lineEditName)
        self.layout().addWidget(line())
        self.layout().addWidget(self.textSummary)
        self.layout().addWidget(group(self.btnAttributes, self.btnAttributesEditor, margin=0, spacing=0, margin_top=15),
                                alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.wdgDayNightHeader)
        self.layout().addWidget(self.wdgAttributes)
        self.layout().addWidget(vspacer())

        self.repo = RepositoryPersistenceManager.instance()

        self.setVisible(False)

    def setLocation(self, location: Location):
        clear_layout(self.wdgAttributes)
        self._attributesSelectorMenu.reset()

        self.setVisible(True)
        self._location = location
        self.lineEditName.setText(self._location.name)
        self.textSummary.setText(self._location.summary)

        for k, v in self._location.sensory_detail.perceptions.items():
            if v.enabled:
                attrType = LocationSensorType[k]
                self._addAttribute(attrType, v)
                self._attributesSelectorMenu.setTypeChecked(attrType, True)

        self.wdgDayNightHeader.setVisible(self._location.sensory_detail.night_mode)
        self._attributesSelectorMenu.toggleDayNight.setChecked(self._location.sensory_detail.night_mode)

        if not self._location.name:
            self.lineEditName.setFocus()

    def locationDeletedEvent(self, location: Location):
        if location is self._location:
            self.setVisible(False)

    def _nameEdited(self, name: str):
        self._location.name = name
        self._save()
        self.locationNameChanged.emit(self._location)

    def _nameSet(self, _: str):
        emit_event(self._novel, RequestMilieuDictionaryResetEvent(self))

    def _summaryChanged(self):
        self._location.summary = self.textSummary.toPlainText()
        self._save()

    def _dayNightToggled(self, toggled: bool):
        self.wdgDayNightHeader.setVisible(toggled)
        self._location.sensory_detail.night_mode = toggled

        for k, v in self._location.sensory_detail.perceptions.items():
            attrType = LocationSensorType[k]
            if v.enabled and toggled:
                wdg = self._initPerceptionWidget(attrType, v, nightMode=True)
                self._gridAttributesLayout.addWidget(wdg, attrType.value, 1, 1, 1,
                                                     alignment=Qt.AlignmentFlag.AlignTop)
            elif v.enabled and not toggled:
                self._removeAttribute(attrType, nightMode=True)

        self._save()

    def _settingChanged(self, attrType: LocationSensorType, toggled: bool):
        if attrType.name not in self._location.sensory_detail.perceptions:
            self._location.sensory_detail.perceptions[attrType.name] = SensoryPerception()

        perception = self._location.sensory_detail.perceptions[attrType.name]
        perception.enabled = toggled
        if toggled:
            wdg = self._addAttribute(attrType, perception)
            fade_in(wdg)
        else:
            item = self._gridAttributesLayout.itemAtPosition(attrType.value, 0)
            if item and item.widget():
                fade_out_and_gc(self.wdgAttributes, item.widget())
            self._removeAttribute(attrType)
            if self._location.sensory_detail.night_mode:
                self._removeAttribute(attrType, nightMode=True)

        self._save()

    def _addAttribute(self, attrType: LocationSensorType, perception: SensoryPerception) -> LocationAttributeTextEdit:
        wdg = self._initPerceptionWidget(attrType, perception)
        self._gridAttributesLayout.addWidget(wdg, attrType.value, 0, 1, 1, alignment=Qt.AlignmentFlag.AlignTop)
        if self._location.sensory_detail.night_mode:
            wdgNight = self._initPerceptionWidget(attrType, perception, nightMode=True)
            self._gridAttributesLayout.addWidget(wdgNight, attrType.value, 1, 1, 1, alignment=Qt.AlignmentFlag.AlignTop)
        return wdg

    def _removeAttribute(self, attrType: LocationSensorType, nightMode: bool = False):
        col = 1 if nightMode else 0
        item = self._gridAttributesLayout.itemAtPosition(attrType.value, col)
        if item and item.widget():
            fade_out_and_gc(self.wdgAttributes, item.widget())

    def _save(self):
        self.repo.update_novel(self._novel)

    def _initPerceptionWidget(self, attrType: LocationSensorType,
                              perception: SensoryPerception, nightMode: bool = False) -> LocationAttributeTextEdit:
        wdg = LocationAttributeTextEdit(attrType, perception, nightMode=nightMode)
        wdg.changed.connect(self._save)
        return wdg
