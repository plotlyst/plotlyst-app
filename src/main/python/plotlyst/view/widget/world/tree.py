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
import uuid
from functools import partial
from typing import Optional, Dict, Set, List

from PyQt6.QtCore import pyqtSignal, QMimeData, Qt, QPointF, QTimer
from overrides import overrides
from qthandy import vspacer, clear_layout, transparent, translucent, gc, margins, busy
from qthandy.filter import DragEventFilter, DropEventFilter
from qtmenu import MenuWidget

from plotlyst.common import recursive
from plotlyst.core.domain import Novel, WorldBuildingEntity, WorldBuildingEntityElement, WorldBuildingEntityElementType, \
    Location
from plotlyst.event.core import emit_event
from plotlyst.events import WorldEntityAddedEvent, WorldEntityDeletedEvent, ItemLinkedEvent, ItemUnlinkedEvent
from plotlyst.service.cache import try_location
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import action, fade_out_and_gc
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.widget.confirm import confirmed
from plotlyst.view.widget.tree import TreeView, ContainerNode, TreeSettings
from plotlyst.view.widget.world.editor import MilieuSelectorPopup, WorldBuildingTopicSelectionDialog


class EntityAdditionMenu(MenuWidget):
    entityTriggered = pyqtSignal(WorldBuildingEntity)
    topicsSelected = pyqtSignal(list)

    def __init__(self, novel: Novel, parent=None):
        super(EntityAdditionMenu, self).__init__(parent)
        self._novel = novel
        # self.setTooltipDisplayMode(ActionTooltipDisplayMode.DISPLAY_UNDER)
        self.addAction(action('Article', IconRegistry.from_name('ri.quill-pen-fill'),
                              slot=self._entityTriggered,
                              tooltip='Write an article about any physical, human, or abstract entity in the world, e.g., kingdom, magic, religion, etc.'))
        self.addSeparator()
        milieuAction = action('Link milieu...', IconRegistry.world_building_icon(), slot=self._linkToMilieu,
                              tooltip="Link a milieu element")
        self.addAction(milieuAction)
        if self._novel.tutorial:
            milieuAction.setToolTip('Milieu link is disabled in preview mode')
            milieuAction.setDisabled(True)

        self.addAction(
            action('Select topics...', IconRegistry.from_name('mdi.card-text-outline'), slot=self._linkToTopics,
                   tooltip="Link to common worldbuilding topics"))

        apply_white_menu(self)

    def _entityTriggered(self):
        entity = self.__newEntity('', elements=self.__newElements())
        self.entityTriggered.emit(entity)

    @busy
    def _linkToMilieu(self, _):
        element: Location = MilieuSelectorPopup.popup(self._novel)
        if element:
            entity = self.__newEntity('', elements=self.__newElements(), ref=element.id)
            self.entityTriggered.emit(entity)

    def _linkToTopics(self):
        topics = WorldBuildingTopicSelectionDialog.popup()
        if topics:
            entities = []
            for topic in topics:
                entity = self.__newEntity(topic.text, icon=topic.icon, elements=self.__newElements(), ref=topic.id)
                entities.append(entity)
            self.topicsSelected.emit(entities)

    def __newEntity(self, name: str, elements: List[WorldBuildingEntityElement], ref: Optional[uuid.UUID] = None,
                    icon: str = '') -> WorldBuildingEntity:
        return WorldBuildingEntity(name, elements=elements, ref=ref, icon=icon, side_visible=False)

    def __newElements(self) -> List[WorldBuildingEntityElement]:
        main_section = WorldBuildingEntityElement(WorldBuildingEntityElementType.Main_Section)
        main_section.blocks.append(WorldBuildingEntityElement(WorldBuildingEntityElementType.Header))
        main_section.blocks.append(WorldBuildingEntityElement(WorldBuildingEntityElementType.Text))
        return [main_section]


class EntityNode(ContainerNode):
    addEntity = pyqtSignal(WorldBuildingEntity)
    addEntities = pyqtSignal(list)
    milieuLinked = pyqtSignal(Location)
    milieuUnlinked = pyqtSignal()

    def __init__(self, novel: Novel, entity: WorldBuildingEntity, parent=None, settings: Optional[TreeSettings] = None):
        self._actionLinkMilieu = action('Link milieu', IconRegistry.world_building_icon(), slot=self._linkToMilieu,
                                        tooltip="Link a milieu element")
        if novel.tutorial:
            self._actionLinkMilieu.setToolTip('Milieu link is disabled in preview mode')
            self._actionLinkMilieu.setDisabled(True)
        self._actionUnlinkMilieu = action('Unlink milieu', IconRegistry.from_name('fa5s.unlink'),
                                          slot=self._unlinkMilieu,
                                          tooltip="Unlink from a milieu element")
        self._novel = novel
        self._entity = entity
        super(EntityNode, self).__init__(entity.name, parent=parent, settings=settings)

        self.setPlusButtonEnabled(True)
        self.setTranslucentIconEnabled(True)
        self._initAdditionMenu()

        self._placeholderName: str = 'New article'

        self.refresh()

    def entity(self) -> WorldBuildingEntity:
        return self._entity

    def refresh(self):
        if self._entity.ref:
            location = try_location(self._entity)
            if location:
                self._lblTitle.setText(location.name)
        else:
            self._lblTitle.setText(self._entity.name if self._entity.name else self._placeholderName)

        if self._entity.icon:
            self._icon.setIcon(IconRegistry.from_name(self._entity.icon, self._entity.icon_color))
        else:
            self._icon.setIcon(IconRegistry.from_name('msc.debug-stackframe-dot'))
        self._icon.setVisible(True)

    @overrides
    def _initMenuActions(self, menu: MenuWidget):
        menu.addAction(self._actionLinkMilieu)
        menu.addAction(self._actionUnlinkMilieu)
        self._actionLinkMilieu.setVisible(self._entity.ref is None)
        self._actionUnlinkMilieu.setVisible(self._entity.ref is not None)

        menu.addSeparator()
        menu.addAction(self._actionDelete)

    def _initAdditionMenu(self):
        self._additionMenu = EntityAdditionMenu(self._novel, self._btnAdd)
        self._additionMenu.entityTriggered.connect(self.addEntity)
        self._additionMenu.topicsSelected.connect(self.addEntities)
        self.setPlusMenu(self._additionMenu)

    @busy
    def _linkToMilieu(self, _):
        element: Location = MilieuSelectorPopup.popup(self._novel)
        if element:
            self.milieuLinked.emit(element)
            self._actionLinkMilieu.setVisible(False)
            self._actionUnlinkMilieu.setVisible(True)

    def _unlinkMilieu(self):
        self._actionLinkMilieu.setVisible(True)
        self._actionUnlinkMilieu.setVisible(False)
        self.milieuUnlinked.emit()


class RootNode(EntityNode):

    def __init__(self, novel: Novel, entity: WorldBuildingEntity, parent=None, settings: Optional[TreeSettings] = None):
        super(RootNode, self).__init__(novel, entity, parent=parent, settings=settings)
        self.setMenuEnabled(False)
        self.setPlusButtonEnabled(False)

    @overrides
    def _initMenuActions(self, menu: MenuWidget):
        pass


class WorldBuildingTreeView(TreeView):
    WORLD_ENTITY_MIMETYPE = 'application/world-entity'
    entitySelected = pyqtSignal(WorldBuildingEntity)
    milieuLinked = pyqtSignal(WorldBuildingEntity)
    milieuUnlinked = pyqtSignal(WorldBuildingEntity)
    childEntitiesAdded = pyqtSignal()

    def __init__(self, parent=None, settings: Optional[TreeSettings] = None):
        super(WorldBuildingTreeView, self).__init__(parent)
        self._novel: Optional[Novel] = None
        self._settings: Optional[TreeSettings] = settings
        self._root: Optional[RootNode] = None
        self._entities: Dict[WorldBuildingEntity, EntityNode] = {}
        self._selectedEntities: Set[WorldBuildingEntity] = set()
        transparent(self)
        margins(self._centralWidget, left=10)

        self._dummyWdg: Optional[EntityNode] = None
        self._toBeRemoved: Optional[EntityNode] = None

        self.repo = RepositoryPersistenceManager.instance()

    def selectRoot(self):
        self._root.select()
        self._entitySelectionChanged(self._root, self._root.isSelected())

    def selectEntity(self, entity: WorldBuildingEntity):
        node = self._entities[entity]
        node.select()
        self._entitySelectionChanged(node, True)

    def setSettings(self, settings: TreeSettings):
        self._settings = settings
        self._centralWidget.setStyleSheet(f'#centralWidget {{background: {settings.bg_color};}}')

    def setNovel(self, novel: Novel):
        self._novel = novel
        self._root = RootNode(self._novel, self._novel.world.root_entity, settings=self._settings)
        self._root.selectionChanged.connect(partial(self._entitySelectionChanged, self._root))
        self.refresh()

    def addEntity(self, entity: WorldBuildingEntity):
        wdg = self.__initEntityWidget(entity)
        self._root.addChild(wdg)
        self.rootEntity().children.append(entity)
        self._save()

        emit_event(self._novel, WorldEntityAddedEvent(self, entity))

    def addEntities(self, entities: List[WorldBuildingEntity]):
        for entity in entities:
            self.addEntity(entity)

    def rootEntity(self) -> WorldBuildingEntity:
        return self._novel.world.root_entity

    def refresh(self):
        def addChildWdg(parent: WorldBuildingEntity, child: WorldBuildingEntity):
            childWdg = self.__initEntityWidget(child)
            self._entities[parent].addChild(childWdg)

        self.clearSelection()
        self._entities.clear()
        clear_layout(self._centralWidget)

        self._entities[self.rootEntity()] = self._root
        self._centralWidget.layout().addWidget(self._root)
        for entity in self.rootEntity().children:
            wdg = self.__initEntityWidget(entity)
            self._root.addChild(wdg)
            recursive(entity, lambda parent: parent.children, addChildWdg)
        self._centralWidget.layout().addWidget(vspacer())

    def updateEntity(self, entity: WorldBuildingEntity):
        self._entities[entity].refresh()

    def clearSelection(self):
        for entity in self._selectedEntities:
            self._entities[entity].deselect()
        self._selectedEntities.clear()

    def _linkMilieu(self, node: EntityNode, location: Location):
        entity = node.entity()
        if entity.ref:
            emit_event(self._novel, ItemUnlinkedEvent(self, entity, entity.ref))

        entity.ref = location.id
        node.refresh()
        self.milieuLinked.emit(entity)
        emit_event(self._novel, ItemLinkedEvent(self, entity))

    def _unlinkMilieu(self, node: EntityNode):
        entity = node.entity()
        if entity.ref:
            emit_event(self._novel, ItemUnlinkedEvent(self, entity, entity.ref))

            entity.ref = None
            node.refresh()
            self.milieuUnlinked.emit(entity)
            self._save()

    def _entitySelectionChanged(self, node: EntityNode, selected: bool):
        if selected:
            self.clearSelection()
            self._selectedEntities.add(node.entity())
            QTimer.singleShot(10, lambda: self.entitySelected.emit(node.entity()))
        elif node.entity() in self._selectedEntities:
            self._selectedEntities.remove(node.entity())

    def _addEntity(self, parent: EntityNode, entity: WorldBuildingEntity):
        wdg = self.__initEntityWidget(entity)
        parent.addChild(wdg)
        parent.entity().children.append(entity)
        self._save()

        emit_event(self._novel, WorldEntityAddedEvent(self, entity))

    def _addEntities(self, parent: EntityNode, entities: List[WorldBuildingEntity]):
        for entity in entities:
            self._addEntity(parent, entity)
        self.childEntitiesAdded.emit()

    def _removeEntity(self, node: EntityNode):
        entity = node.entity()

        name = entity.name
        if entity.ref:
            location = try_location(entity)
            if location:
                name = location.name

        title = f'Are you sure you want to delete the entity "{name if name else "Untitled"}"?'
        msg = 'This action cannot be undone, and the article and all its content will be lost.'
        if not confirmed(msg, title):
            return

        self.clearSelection()
        self.selectRoot()

        node.parent().parent().entity().children.remove(entity)
        fade_out_and_gc(node.parent(), node)
        self._save()

        emit_event(self._novel, WorldEntityDeletedEvent(self, entity))

    def _dragStarted(self, wdg: EntityNode):
        wdg.setHidden(True)
        self._dummyWdg = self._nodeClass()(self._novel, wdg.entity(), settings=self._settings)
        self._dummyWdg.setPlusButtonEnabled(False)
        self._dummyWdg.setMenuEnabled(False)
        translucent(self._dummyWdg)
        self._dummyWdg.setHidden(True)
        self._dummyWdg.setParent(self._centralWidget)
        self._dummyWdg.setAcceptDrops(True)
        self._dummyWdg.installEventFilter(
            DropEventFilter(self._dummyWdg, [self.WORLD_ENTITY_MIMETYPE], droppedSlot=self._drop))

    def _dragStopped(self, wdg: EntityNode):
        if self._dummyWdg:
            gc(self._dummyWdg)
            self._dummyWdg = None

        if self._toBeRemoved:
            gc(self._toBeRemoved)
            self._toBeRemoved = None
        else:
            wdg.setVisible(True)

    def _dragMovedOnEntity(self, wdg: EntityNode, edge: Qt.Edge, point: QPointF):
        i = wdg.parent().layout().indexOf(wdg)
        if edge == Qt.Edge.TopEdge:
            wdg.parent().layout().insertWidget(i, self._dummyWdg)
        elif point.x() > 50:
            wdg.insertChild(0, self._dummyWdg)
        else:
            wdg.parent().layout().insertWidget(i + 1, self._dummyWdg)

        self._dummyWdg.setVisible(True)

    def _drop(self, mimeData: QMimeData):
        self.clearSelection()

        if self._dummyWdg.isHidden():
            return
        ref: WorldBuildingEntity = mimeData.reference()
        self._toBeRemoved = self._entities[ref]
        new_widget = self.__initEntityWidget(ref)
        for child in self._toBeRemoved.childrenWidgets():
            new_widget.addChild(child)

        entity_parent_wdg: EntityNode = self._dummyWdg.parent().parent()
        new_index = entity_parent_wdg.containerWidget().layout().indexOf(self._dummyWdg)
        if self._toBeRemoved.parent() is not self._centralWidget and \
                self._toBeRemoved.parent().parent() is self._dummyWdg.parent().parent():  # swap under same parent doc
            old_index = entity_parent_wdg.indexOf(self._toBeRemoved)
            entity_parent_wdg.entity().children.remove(ref)
            if old_index < new_index:
                entity_parent_wdg.entity().children.insert(new_index - 1, ref)
            else:
                entity_parent_wdg.entity().children.insert(new_index, ref)
        else:
            self._removeFromParentEntity(ref, self._toBeRemoved)
            entity_parent_wdg.entity().children.insert(new_index, ref)

        entity_parent_wdg.insertChild(new_index, new_widget)

        self._dummyWdg.setHidden(True)
        self._save()

    def _save(self):
        self.repo.update_world(self._novel)

    def _removeFromParentEntity(self, entity: WorldBuildingEntity, wdg: EntityNode):
        parent: EntityNode = wdg.parent().parent()
        parent.entity().children.remove(entity)

    def _nodeClass(self):
        return EntityNode

    def __initEntityWidget(self, entity: WorldBuildingEntity) -> EntityNode:
        node = self._nodeClass()(self._novel, entity, settings=self._settings)
        node.selectionChanged.connect(partial(self._entitySelectionChanged, node))
        node.milieuLinked.connect(partial(self._linkMilieu, node))
        node.milieuUnlinked.connect(partial(self._unlinkMilieu, node))
        node.addEntity.connect(partial(self._addEntity, node))
        node.addEntities.connect(partial(self._addEntities, node))
        node.deleted.connect(partial(self._removeEntity, node))

        node.installEventFilter(
            DragEventFilter(node, self.WORLD_ENTITY_MIMETYPE, dataFunc=lambda node: node.entity(),
                            grabbed=node.titleLabel(),
                            startedSlot=partial(self._dragStarted, node),
                            finishedSlot=partial(self._dragStopped, node)))
        node.titleWidget().setAcceptDrops(True)
        node.titleWidget().installEventFilter(
            DropEventFilter(node, [self.WORLD_ENTITY_MIMETYPE],
                            motionDetection=Qt.Orientation.Vertical,
                            motionSlot=partial(self._dragMovedOnEntity, node),
                            droppedSlot=self._drop
                            )
        )

        self._entities[entity] = node
        return node
