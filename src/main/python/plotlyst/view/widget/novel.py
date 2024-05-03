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
from enum import Enum, auto
from functools import partial
from typing import Optional, List

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QWidget, QStackedWidget
from overrides import overrides
from qthandy import vspacer, spacer, transparent, bold, vbox, hbox, line
from qtmenu import MenuWidget, ActionTooltipDisplayMode

from plotlyst.core.domain import StoryStructure, Novel, TagType, SelectionItem, Tag, NovelSetting
from plotlyst.model.characters_model import CharactersTableModel
from plotlyst.model.common import SelectionItemsModel
from plotlyst.model.novel import NovelTagsModel
from plotlyst.view.common import link_buttons_to_pages, action, label, push_btn
from plotlyst.view.generated.imported_novel_overview_ui import Ui_ImportedNovelOverview
from plotlyst.view.icons import IconRegistry, avatars
from plotlyst.view.layout import group
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.widget.display import Subtitle
from plotlyst.view.widget.items_editor import ItemsEditorWidget
from plotlyst.view.widget.labels import LabelsEditorWidget
from plotlyst.view.widget.settings import NovelPanelSettingsWidget


class TagLabelsEditor(LabelsEditorWidget):

    def __init__(self, novel: Novel, tagType: TagType, tags: List[Tag], parent=None):
        self.novel = novel
        self.tagType = tagType
        self.tags = tags
        super(TagLabelsEditor, self).__init__(checkable=False, parent=parent)
        self.btnEdit.setIcon(IconRegistry.tag_plus_icon())
        self.editor.model.item_edited.connect(self._updateTags)
        self.editor.model.modelReset.connect(self._updateTags)
        self._updateTags()

    @overrides
    def _initPopupWidget(self) -> QWidget:
        self.editor: ItemsEditorWidget = super(TagLabelsEditor, self)._initPopupWidget()
        self.editor.setBgColorFieldEnabled(True)
        return self.editor

    @overrides
    def _initModel(self) -> SelectionItemsModel:
        return NovelTagsModel(self.novel, self.tagType, self.tags)

    @overrides
    def items(self) -> List[SelectionItem]:
        return self.tags

    def _updateTags(self):
        self._wdgLabels.clear()
        self._addItems(self.tags)


class TagTypeDisplay(QWidget):
    def __init__(self, novel: Novel, tagType: TagType, parent=None):
        super(TagTypeDisplay, self).__init__(parent)
        self.tagType = tagType
        self.novel = novel

        vbox(self)
        self.subtitle = Subtitle(self)
        self.subtitle.lblTitle.setText(tagType.text)
        self.subtitle.lblDescription.setText(tagType.description)
        if tagType.icon:
            self.subtitle.setIconName(tagType.icon, tagType.icon_color)
        self.labelsEditor = TagLabelsEditor(self.novel, tagType, self.novel.tags[tagType])
        self.layout().addWidget(self.subtitle)
        self.layout().addWidget(group(spacer(20), self.labelsEditor))


class TagsEditor(QWidget):
    def __init__(self, parent=None):
        super(TagsEditor, self).__init__(parent)
        self.novel: Optional[Novel] = None
        vbox(self)

    def setNovel(self, novel: Novel):
        self.novel = novel

        for tag_type in self.novel.tags.keys():
            self.layout().addWidget(TagTypeDisplay(self.novel, tag_type, self))
        self.layout().addWidget(vspacer())


class ImportedNovelOverview(QWidget, Ui_ImportedNovelOverview):
    def __init__(self, parent=None):
        super(ImportedNovelOverview, self).__init__(parent)
        self.setupUi(self)

        self._novel: Optional[Novel] = None

        self.btnCharacters.setIcon(IconRegistry.character_icon())
        self.btnLocations.setIcon(IconRegistry.location_icon())
        self.btnLocations.setHidden(True)
        self.btnScenes.setIcon(IconRegistry.scene_icon())
        transparent(self.btnTitle)
        self.btnTitle.setIcon(IconRegistry.book_icon())
        bold(self.btnTitle)

        link_buttons_to_pages(self.stackedWidget,
                              [(self.btnCharacters, self.pageCharacters), (self.btnLocations, self.pageLocations),
                               (self.btnScenes, self.pageScenes)])

        self._charactersModel: Optional[CharactersTableModel] = None

        self.toggleSync.clicked.connect(self._syncClicked)

    def setNovel(self, novel: Novel):
        self._novel = novel
        self.btnTitle.setText(self._novel.title)

        if novel.characters:
            self._charactersModel = CharactersTableModel(self._novel)
            self.lstCharacters.setModel(self._charactersModel)
            self.btnCharacters.setChecked(True)
        else:
            self.btnCharacters.setDisabled(True)

        self.treeChapters.setNovel(self._novel, readOnly=True)

    def _syncClicked(self, checked: bool):
        self._novel.import_origin.sync = checked


class StoryStructureSelectorMenu(MenuWidget):
    selected = pyqtSignal(StoryStructure)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel

        self.aboutToShow.connect(self._fillUpMenu)

    def _fillUpMenu(self):
        self.clear()
        self.addSection('Select a story structure to be displayed')
        self.addSeparator()

        for structure in self._novel.story_structures:
            if structure.character_id:
                icon = avatars.avatar(structure.character(self._novel))
            elif structure:
                icon = IconRegistry.from_name(structure.icon, structure.icon_color)
            else:
                icon = None
            action_ = action(structure.title, icon, slot=partial(self.selected.emit, structure), checkable=True,
                             parent=self)
            action_.setChecked(structure.active)
            self.addAction(action_)


class WriterType(Enum):
    Architect = auto()
    Planner = auto()
    Explorer = auto()
    Intuitive = auto()
    Free_spirit = auto()


class NovelCustomizationWizard(QWidget):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self.stack = QStackedWidget()
        hbox(self).addWidget(self.stack)

        self.pagePanels = QWidget()
        self.wdgPanelSettings = NovelPanelSettingsWidget()
        self.wdgPanelSettings.setNovel(self._novel)
        self.lblCounter = label('')
        self._updateCounter()
        self.wdgPanelSettings.clicked.connect(self._updateCounter)
        self.btnRecommend = push_btn(IconRegistry.from_name('mdi.trophy-award'), 'Recommend me', transparent_=True)
        menuRecommendation = MenuWidget(self.btnRecommend)
        apply_white_menu(menuRecommendation)
        menuRecommendation.setTooltipDisplayMode(ActionTooltipDisplayMode.DISPLAY_UNDER)
        menuRecommendation.addSection("Recommend me features if my writing style fits into...")
        menuRecommendation.addAction(
            action('Architect', IconRegistry.from_name('fa5s.drafting-compass'),
                   tooltip='Someone who follows meticulous planning and detailed outlines before writing',
                   slot=lambda: self._recommend(WriterType.Architect)))
        menuRecommendation.addAction(
            action('Planner', IconRegistry.from_name('fa5.calendar-alt'),
                   tooltip='Someone who enjoys some planning but allows for flexibility',
                   slot=lambda: self._recommend(WriterType.Planner)))
        menuRecommendation.addAction(action(
            'Explorer', IconRegistry.from_name('fa5s.binoculars'),
            tooltip='Someone who enjoys discovering their story as they write with very little directions or planning beforehand',
            slot=lambda: self._recommend(WriterType.Explorer)))
        menuRecommendation.addAction(
            action('Intuitive', IconRegistry.from_name('fa5.lightbulb'),
                   tooltip='Someone who writes based on intuition and inspiration with minimal to no planning',
                   slot=lambda: self._recommend(WriterType.Intuitive)))
        menuRecommendation.addAction(
            action('Free spirit', IconRegistry.from_name('mdi.bird'),
                   tooltip='Someone who enjoys the spontaneity of writing without constraints',
                   slot=lambda: self._recommend(WriterType.Free_spirit)))

        vbox(self.pagePanels)
        self.wdgTop = QWidget()
        hbox(self.wdgTop)
        self.wdgTop.layout().addWidget(self.lblCounter, alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgTop.layout().addWidget(self.btnRecommend, alignment=Qt.AlignmentFlag.AlignRight)
        self.pagePanels.layout().addWidget(self.wdgTop)
        self.pagePanels.layout().addWidget(line())
        self.pagePanels.layout().addWidget(self.wdgPanelSettings)
        self.pagePanels.layout().addWidget(vspacer())
        self.pagePanels.layout().addWidget(label('You can always change these settings later', description=True),
                                           alignment=Qt.AlignmentFlag.AlignRight)
        self.pagePersonality = QWidget()

        self.stack.addWidget(self.pagePanels)
        self.stack.addWidget(self.pagePersonality)

    def _updateCounter(self):
        self.lblCounter.setText(f'<html><i>Selected features: <b>9/{len(self.wdgPanelSettings.toggledSettings())}')

    def _recommend(self, writerType: WriterType):
        if writerType == WriterType.Architect:
            self.wdgPanelSettings.checkSettings([NovelSetting.Mindmap], False)
        elif writerType == WriterType.Planner:
            self.wdgPanelSettings.checkSettings([NovelSetting.Management], False)
        elif writerType == WriterType.Explorer:
            self.wdgPanelSettings.checkSettings(
                [NovelSetting.Manuscript, NovelSetting.Characters, NovelSetting.Documents, NovelSetting.Mindmap,
                 NovelSetting.Storylines])
        elif writerType == WriterType.Intuitive:
            self.wdgPanelSettings.checkSettings(
                [NovelSetting.Manuscript, NovelSetting.Characters, NovelSetting.Documents])
        elif writerType == WriterType.Free_spirit:
            self.wdgPanelSettings.checkSettings([NovelSetting.Manuscript])

        self._updateCounter()
