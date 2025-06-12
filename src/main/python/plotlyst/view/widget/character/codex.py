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
from functools import partial
from typing import List, Optional

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QFrame
from overrides import overrides
from qthandy import vspacer, spacer, vbox, margins, hbox, sp
from qthandy.filter import OpacityEventFilter
from qtmenu import MenuWidget

from plotlyst.common import RELAXED_WHITE_COLOR, PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import WorldBuildingEntity, Character, Novel, WorldBuildingEntityElement, \
    WorldBuildingEntityElementType
from plotlyst.env import app_env
from plotlyst.view.common import wrap, action, to_rgba_str, push_btn
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.style.base import apply_white_menu, transparent_menu
from plotlyst.view.widget.button import DotsMenuButton
from plotlyst.view.widget.character.topic import CharacterTopicSelectionDialog
from plotlyst.view.widget.display import SeparatorLineWithShadow, MenuOverlayEventFilter
from plotlyst.view.widget.input import AutoAdjustableLineEdit
from plotlyst.view.widget.tree import TreeSettings
from plotlyst.view.widget.world.editor import WorldBuildingEntityEditor
from plotlyst.view.widget.world.theme import WorldBuildingPalette
from plotlyst.view.widget.world.tree import EntityNode, WorldBuildingTreeView, RootNode


class CharacterCodexAdditionMenu(MenuWidget):
    entityTriggered = pyqtSignal(WorldBuildingEntity)
    topicsSelected = pyqtSignal(list)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel

        self.addAction(action('Page', IconRegistry.from_name('ri.typhoon-fill'),
                              slot=self._entityTriggered,
                              tooltip='Create a new page about your character'))
        self.addSeparator()

        self.addAction(
            action('Select topics...', IconRegistry.from_name('mdi.card-text-outline'), slot=self._linkToTopics,
                   tooltip="Link to common characterization topics"))

        apply_white_menu(self)

    def _entityTriggered(self):
        entity = self.__newEntity('', elements=self.__newElements())
        self.entityTriggered.emit(entity)

    def _linkToTopics(self):
        topics = CharacterTopicSelectionDialog.popup()
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


class CharacterCodexNode(EntityNode):
    def __init__(self, novel: Novel, entity: WorldBuildingEntity, parent=None, settings: Optional[TreeSettings] = None):
        super().__init__(novel, entity, parent, settings)
        self._actionLinkMilieu.setVisible(False)
        self._placeholderName = 'New page'

    @overrides
    def _initMenuActions(self, menu: MenuWidget):
        menu.addAction(self._actionDelete)

    @overrides
    def _initAdditionMenu(self):
        self._additionMenu = CharacterCodexAdditionMenu(self._novel, self._btnAdd)
        self._additionMenu.entityTriggered.connect(self.addEntity)
        self._additionMenu.topicsSelected.connect(self.addEntities)
        self.setPlusMenu(self._additionMenu)


class CharacterCodexTreeView(WorldBuildingTreeView):

    def __init__(self, parent=None, settings: Optional[TreeSettings] = None):
        super().__init__(parent, settings)
        self._character: Optional[Character] = None

    @overrides
    def rootEntity(self) -> WorldBuildingEntity:
        return self._character.codex

    def setCharacter(self, character: Character, novel: Novel):
        self._character = character
        self._novel = novel
        self._root = RootNode(self._novel, character.codex, settings=self._settings)
        self._root.selectionChanged.connect(partial(self._entitySelectionChanged, self._root))
        self.refresh()

    @overrides
    def _nodeClass(self):
        return CharacterCodexNode


class CharacterCodexEditor(QFrame):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel
        self._character: Optional[Character] = None
        self._codexEntity: Optional[WorldBuildingEntity] = None

        vbox(self, 0, 0)

        self._palette = WorldBuildingPalette(bg_color='#ede0d4', primary_color='#510442',
                                             secondary_color='#DABFA7',
                                             tertiary_color='#E3D0BD')
        self.editor = WorldBuildingEntityEditor(self.novel, self._palette)
        margins(self.editor, top=15)
        trans_bg_color = to_rgba_str(QColor(self._palette.bg_color), 245)
        self.setObjectName('codexEditor')
        self.setStyleSheet(f'''
                               #codexEditor {{
                                   background: {trans_bg_color};
                               }}
                           ''')

        self.treeView = CharacterCodexTreeView(settings=TreeSettings(font_incr=2))
        self.treeView.entitySelected.connect(self._entitySelected)
        self.btnAdd = push_btn(IconRegistry.plus_icon(color=RELAXED_WHITE_COLOR), 'Add new page',
                               properties=['positive', 'base'])
        menu = CharacterCodexAdditionMenu(self.novel, self.btnAdd)
        menu.entityTriggered.connect(self.treeView.addEntity)
        menu.topicsSelected.connect(self.treeView.addEntities)
        self.btnTree = push_btn(IconRegistry.from_name('mdi.file-tree-outline'), 'Pages', transparent_=True)
        self.btnTree.installEventFilter(OpacityEventFilter(self.btnTree))
        self.treeMenu = MenuWidget(self.btnTree)
        self.treeMenu.installEventFilter(MenuOverlayEventFilter(self.treeMenu))
        self.treeMenu.aboutToShow.connect(self._beforeOpenTreeMenu)
        wdgHeader = QFrame()
        hbox(wdgHeader)
        margins(wdgHeader, bottom=5)
        sp(wdgHeader).v_max()
        wdgHeader.setStyleSheet(f'.QFrame {{background: {PLOTLYST_SECONDARY_COLOR};}}')
        wdgHeader.layout().addWidget(self.btnAdd)
        wdgHeader.layout().addWidget(spacer())
        self.treeMenu.addWidget(wdgHeader)
        self.treeMenu.addWidget(self.treeView)
        transparent_menu(self.treeMenu)
        self.btnContext = DotsMenuButton()

        menu.topicsSelected.connect(self.btnTree.click)
        self.treeView.childEntitiesAdded.connect(self.btnTree.click)

        self.lineName = AutoAdjustableLineEdit()
        self.lineName.setPlaceholderText('Page')
        font = self.lineName.font()
        font.setPointSize(26)
        font.setFamily(app_env.serif_font())
        self.lineName.setFont(font)

        self.lineName.setStyleSheet(f'''
                        QLineEdit {{
                            border: 0px;
                            background-color: rgba(0, 0, 0, 0);
                            color: {self._palette.primary_color}; 
                        }}''')
        self.lineName.textEdited.connect(self._titleChanged)

        self.layout().addWidget(group(self.btnTree, spacer(), self.btnContext))

        self.layout().addWidget(wrap(self.lineName, margin_bottom=5), alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(SeparatorLineWithShadow())
        self.layout().addWidget(self.editor)
        self.layout().addWidget(vspacer())

    def setCharacter(self, character: Character):
        self._character = character
        if self._character.codex.children:
            entity = self._character.codex.children[0]
        else:
            entity = self._character.codex
        self.treeView.setCharacter(self._character, self.novel)
        self.treeView.selectEntity(entity)

        self._entitySelected(entity)

    def _beforeOpenTreeMenu(self):
        self.treeView.setFixedSize(self.parent().size().width() * 2 // 3, int(self.parent().size().height() * 0.5))
        self.treeMenu._frame.updateGeometry()

    def _entitySelected(self, entity: WorldBuildingEntity):
        self._codexEntity = entity
        self.editor.setEntity(self._codexEntity)
        self.lineName.setText(self._codexEntity.name)

    def _titleChanged(self, text: str):
        self._codexEntity.name = text
        self.treeView.updateEntity(self._codexEntity)
