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
import re
from enum import Enum, auto
from functools import partial
from typing import Optional, List, Tuple, Dict

from PyQt6.QtCore import pyqtSignal, Qt, QObject, QEvent, QSize
from PyQt6.QtGui import QShowEvent, QCursor
from PyQt6.QtWidgets import QWidget, QStackedWidget, QFrame, QButtonGroup, QPushButton
from overrides import overrides
from qthandy import vspacer, spacer, transparent, bold, vbox, hbox, line, margins, incr_font, sp, grid, incr_icon, \
    flow, clear_layout, pointy, decr_icon, vline, translucent, decr_font
from qthandy.filter import OpacityEventFilter, VisibilityToggleEventFilter
from qtmenu import MenuWidget, ActionTooltipDisplayMode

from plotlyst.common import MAXIMUM_SIZE, PLOTLYST_SECONDARY_COLOR, RELAXED_WHITE_COLOR
from plotlyst.core.domain import StoryStructure, Novel, TagType, SelectionItem, Tag, NovelSetting, ScenesView
from plotlyst.env import app_env
from plotlyst.event.core import emit_global_event
from plotlyst.events import SelectNovelEvent
from plotlyst.model.characters_model import CharactersTableModel
from plotlyst.model.common import SelectionItemsModel
from plotlyst.model.novel import NovelTagsModel
from plotlyst.resources import resource_registry
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import link_buttons_to_pages, action, label, push_btn, frame, scroll_area, \
    ExclusiveOptionalButtonGroup, exclusive_buttons, fade, ButtonPressResizeEventFilter, open_url
from plotlyst.view.generated.imported_novel_overview_ui import Ui_ImportedNovelOverview
from plotlyst.view.icons import IconRegistry, avatars
from plotlyst.view.layout import group
from plotlyst.view.style.base import apply_white_menu, apply_border_image
from plotlyst.view.style.theme import BG_PRIMARY_COLOR
from plotlyst.view.widget.button import SelectorToggleButton, SmallToggleButton, DotsMenuButton
from plotlyst.view.widget.display import Subtitle, IconText, Icon, PopupDialog, icon_text
from plotlyst.view.widget.input import Toggle, AutoAdjustableTextEdit
from plotlyst.view.widget.items_editor import ItemsEditorWidget
from plotlyst.view.widget.labels import LabelsEditorWidget
from plotlyst.view.widget.manuscript import ManuscriptLanguageSettingWidget
from plotlyst.view.widget.settings import NovelPanelSettingsWidget, NovelSettingToggle
from plotlyst.view.widget.utility import IconPicker


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
    finished = pyqtSignal()

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self.stack = QStackedWidget()
        hbox(self).addWidget(self.stack)

        self.pagePanels = QWidget()
        vbox(self.pagePanels)
        self.pagePersonality = QWidget()
        vbox(self.pagePersonality, spacing=5)
        margins(self.pagePersonality, left=15, right=15)
        self.pageScenes = QWidget()
        vbox(self.pageScenes)
        margins(self.pageScenes, left=15, right=15)
        self.pageManuscript = QWidget()
        vbox(self.pageManuscript)
        self.stack.addWidget(self.pagePanels)
        self.stack.addWidget(self.pagePersonality)
        self.stack.addWidget(self.pageScenes)
        self.stack.addWidget(self.pageManuscript)

        self.wdgPanelSettings = NovelPanelSettingsWidget()
        self.wdgPanelSettings.setNovel(self._novel)
        self.lblCounter = label('')
        self._updateCounter()
        self.wdgPanelSettings.clicked.connect(self._updateCounter)
        if app_env.profile().get('license_type', 'FREE') != 'FREE':
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

            self.wdgTop = QWidget()
            hbox(self.wdgTop)
            self.wdgTop.layout().addWidget(self.lblCounter, alignment=Qt.AlignmentFlag.AlignLeft)
            self.wdgTop.layout().addWidget(self.btnRecommend, alignment=Qt.AlignmentFlag.AlignRight)
            self.pagePanels.layout().addWidget(self.wdgTop)
            self.pagePanels.layout().addWidget(line())
        self.pagePanels.layout().addWidget(self.wdgPanelSettings)
        self.pagePanels.layout().addWidget(vspacer())
        self.pagePanels.layout().addWidget(
            label('You can always change these settings later', description=True, decr_font_diff=1),
            alignment=Qt.AlignmentFlag.AlignRight)

        self.pagePersonality.layout().addWidget(label('Character Personality Types', h3=True),
                                                alignment=Qt.AlignmentFlag.AlignCenter)
        self.pagePersonality.layout().addWidget(line())
        self.pagePersonality.layout().addWidget(label(
            "Which common personality types and styles would you like to track for your characters? (can be changed later)",
            description=True, wordWrap=True))
        self._addNovelSetting(NovelSetting.Character_enneagram, self.pagePersonality)
        self._addNovelSetting(NovelSetting.Character_mbti, self.pagePersonality)
        self._addNovelSetting(NovelSetting.Character_work_style, self.pagePersonality)
        self._addNovelSetting(NovelSetting.Character_love_style, self.pagePersonality)
        self.pagePersonality.layout().addWidget(vspacer())

        self.pageScenes.layout().addWidget(label('Scene and Chapter Settings', h3=True),
                                           alignment=Qt.AlignmentFlag.AlignCenter)
        self.pageScenes.layout().addWidget(label(
            "Would you like to write scenes and arrange them inside chapters, or work with chapters only? (can be changed later)",
            description=True, wordWrap=True))
        self.pageScenes.layout().addWidget(line())
        self._addNovelSetting(NovelSetting.Scenes_organization, self.pageScenes)
        self._addNovelSetting(NovelSetting.Track_pov, self.pageScenes)
        self.pageScenes.layout().addWidget(vspacer())

        self.langSetting = ManuscriptLanguageSettingWidget(self._novel)
        self.langSetting.setMaximumWidth(MAXIMUM_SIZE)
        self.pageManuscript.layout().addWidget(label('Manuscript Language', h3=True),
                                               alignment=Qt.AlignmentFlag.AlignCenter)
        self.pageManuscript.layout().addWidget(line())
        self.pageManuscript.layout().addWidget(label(
            "Choose your manuscript's language for spellcheck (optional and can be changed later)",
            description=True, wordWrap=True))
        self.pageManuscript.layout().addWidget(self.langSetting, alignment=Qt.AlignmentFlag.AlignCenter)
        self.pageManuscript.layout().addWidget(label(
            "If your language isn't listed, ignore this step and press Finish",
            description=True, decr_font_diff=1), alignment=Qt.AlignmentFlag.AlignRight)

    def next(self):
        i = self.stack.currentIndex()
        if i < self.stack.count() - 1:
            self.stack.setCurrentIndex(i + 1)

        if self.stack.currentWidget() is self.pagePersonality and not self._novel.prefs.toggled(
                NovelSetting.Characters):
            self.next()

    def hasMore(self) -> bool:
        return self.stack.currentIndex() < self.stack.count() - 1

    def _addNovelSetting(self, personality: NovelSetting, page: QWidget):
        toggle = NovelSettingToggle(self._novel, personality)
        toggle.settingToggled.connect(self._settingToggled)
        page.layout().addWidget(toggle)

    def _settingToggled(self, setting: NovelSetting, toggled: bool):
        self._novel.prefs.settings[setting.value] = toggled

    def _updateCounter(self):
        toggledSettings = self.wdgPanelSettings.toggledSettings()
        self.lblCounter.setText(f'<html><i>Selected features: <b>{len(toggledSettings)}/8')

        self._novel.prefs.panels.scenes_view = None
        if len(toggledSettings) == 1:
            if NovelSetting.Manuscript in toggledSettings:
                self._novel.prefs.panels.scenes_view = ScenesView.MANUSCRIPT

    def _recommend(self, writerType: WriterType):
        if writerType == WriterType.Architect:
            self.wdgPanelSettings.checkAllSettings(True)
        elif writerType == WriterType.Planner:
            self.wdgPanelSettings.checkSettings([NovelSetting.Management], False)
        elif writerType == WriterType.Explorer:
            self.wdgPanelSettings.checkSettings(
                [NovelSetting.Manuscript, NovelSetting.Characters, NovelSetting.Documents,
                 NovelSetting.Storylines])
        elif writerType == WriterType.Intuitive:
            self.wdgPanelSettings.checkSettings(
                [NovelSetting.Manuscript, NovelSetting.Characters, NovelSetting.Documents])
        elif writerType == WriterType.Free_spirit:
            self.wdgPanelSettings.checkSettings([NovelSetting.Manuscript])

        self._updateCounter()


spice_descriptions = {
    1: 'Romance with minimal physical intimacy, limited to kissing and hand-holding',
    2: 'Implied or closed-door content with strong romantic tension but little to no explicit detail',
    3: 'Some explicit content, but with milder language and less frequent or detailed intimate scenes',
    4: 'Explicit content with strong language and multiple detailed intimate scenes',
    5: 'Highly explicit content with multiple detailed intimate scenes. All erotica would belong here',
}


class SpiceWidget(QWidget):
    spiceChanged = pyqtSignal(int)
    spiceHoverEntered = pyqtSignal(int)
    spiceHoverLeft = pyqtSignal(int)

    def __init__(self, parent=None, editable: bool = False):
        super().__init__(parent)
        self._editable = editable
        self._spice = 0
        hbox(self, 0, 0)
        self.btnGroup = QButtonGroup()
        self.btnGroup.buttonClicked.connect(self._spiceChanged)

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Enter:
            i = self.btnGroup.buttons().index(watched)
            self.spiceHoverEntered.emit(i + 1)
        elif event.type() == QEvent.Type.Leave:
            i = self.btnGroup.buttons().index(watched)
            self.spiceHoverLeft.emit(i + 1)
        return super().eventFilter(watched, event)

    def spice(self) -> int:
        return self._spice

    def setSpice(self, value: int):
        self._spice = value
        clear_layout(self)
        for i in range(5):
            icon = Icon()
            icon.setCheckable(self._editable)
            if self._editable:
                icon.installEventFilter(OpacityEventFilter(icon))
                icon.installEventFilter(ButtonPressResizeEventFilter(icon))
                icon.installEventFilter(self)
                pointy(icon)
                self.btnGroup.addButton(icon)
            if value > i:
                icon.setIcon(IconRegistry.from_name('mdi6.chili-mild', '#c1121f'))
            else:
                icon.setIcon(IconRegistry.from_name('mdi6.chili-mild', 'grey'))
            incr_icon(icon, 12 if self._editable else 8)
            self.layout().addWidget(icon)

        self.layout().addWidget(spacer())

    def _spiceChanged(self):
        for i, btn in enumerate(self.btnGroup.buttons()):
            if btn.isChecked():
                self._spice = i + 1
                break

        for i, icon in enumerate(self.btnGroup.buttons()):
            if self._spice > i:
                icon.setIcon(IconRegistry.from_name('mdi6.chili-mild', '#c1121f'))
            else:
                icon.setIcon(IconRegistry.from_name('mdi6.chili-mild', 'grey'))

        self.spiceChanged.emit(self._spice)


class GenreSelectorButton(SelectorToggleButton):
    variantChanged = pyqtSignal()

    def __init__(self, genreLabel: str, parent=None):
        super().__init__(Qt.ToolButtonStyle.ToolButtonTextBesideIcon, minWidth=50, parent=parent)
        self._genreLabel = genreLabel
        self._name, self._icon = extract_genre_info(genreLabel)
        if self._icon:
            self.setIcon(IconRegistry.from_name(self._icon))
        self.setText(self._name)

    def name(self) -> str:
        return self._name

    def genre(self) -> str:
        return self._genreLabel

    def displayVariants(self):
        menu = MenuWidget()
        wdg = IconPicker(list(genre_icons[self._name].values()), maxColumn=3, iconSize=28)
        wdg.iconSelected.connect(self._variantSelected)
        menu.addSection('Variants')
        menu.addSeparator()
        menu.addWidget(wdg)

        menu.exec(QCursor.pos())

    def setVariant(self, icon: str):
        for k, variant in genre_icons[self._name].items():
            if variant == icon:
                self._genreLabel = f'{self._name} #{k}'
                self._icon = icon
                self.setIcon(IconRegistry.from_name(self._icon))

    def _variantSelected(self, icon: str):
        self.setVariant(icon)

        if self.isChecked():
            self.variantChanged.emit()


class DescriptorLabelSelector(QWidget):
    selectionChanged = pyqtSignal()

    def __init__(self, parent=None, exclusive: bool = True):
        super().__init__(parent)
        flow(self)
        margins(self, left=20, right=20)
        if exclusive:
            self.btnGroup = ExclusiveOptionalButtonGroup(self)
        else:
            self.btnGroup = QButtonGroup()
            self.btnGroup.setExclusive(False)

        self.btnGroup.buttonClicked.connect(self.selectionChanged)

    def selected(self) -> List[str]:
        labels = []
        for btn in self.btnGroup.buttons():
            if btn.isChecked():
                labels.append(btn.genre())

        return labels

    def setLabels(self, labels: List[str], selected: List[str]):
        for label in labels:
            btn = SelectorToggleButton(Qt.ToolButtonStyle.ToolButtonTextBesideIcon, minWidth=50)
            btn.setText(label)
            self.btnGroup.addButton(btn)
            if label in selected:
                btn.setChecked(True)
            self.layout().addWidget(btn)

    def setGenres(self, genres: List[str], selected: List[str]):
        selected_variants = [extract_genre_info(x) for x in selected]

        secondary_btns = []

        for genre_label in genres:
            wdg = QWidget(self)
            vbox(wdg, 0, 0)

            btnDots = DotsMenuButton(wdg)

            btn = GenreSelectorButton(genre_label, parent=wdg)
            self.btnGroup.addButton(btn)
            for variant in selected_variants:
                if variant[0] == btn.name():
                    btn.setChecked(True)
                    btn.setVariant(variant[1])
                    break

            btn.variantChanged.connect(self.selectionChanged)
            btnDots.clicked.connect(btn.displayVariants)

            wdg.layout().addWidget(group(btn, btnDots, margin=0, spacing=0))
            wdg.installEventFilter(VisibilityToggleEventFilter(btnDots, wdg))
            self.layout().addWidget(wdg)

    # def addSecondaryLabels(self, label: str, secondary: List[str], selected: List[str]):
    #     btnMenu = tool_btn(IconRegistry.from_name('mdi.chevron-down', 'grey'), transparent_=True)
    #     decr_icon(btnMenu, 4)
    #     btn = SelectorToggleButton(Qt.ToolButtonStyle.ToolButtonTextBesideIcon, minWidth=50)
    #     btn.setText(label)
    #     self.btnGroup.addButton(btn)
    #     if label in selected:
    #         btn.setChecked(True)
    #     self.layout().addWidget(group(btn, btnMenu, margin=0, spacing=0))
    #
    #     menu = MenuWidget(btnMenu)
    #     apply_white_menu(menu)
    #     wdg = QWidget()
    #     flow(wdg)
    #     for sec in secondary:
    #         btn = SelectorToggleButton(Qt.ToolButtonStyle.ToolButtonTextBesideIcon, minWidth=50)
    #         btn.setText(sec)
    #         self.btnGroup.addButton(btn)
    #         if sec in selected:
    #             btn.setChecked(True)
    #         wdg.layout().addWidget(btn)
    #     menu.addWidget(wdg)


genre_icons = {
    'Fantasy': {0: 'mdi.creation', 1: 'mdi.unicorn', 2: 'fa5s.hat-wizard', 3: 'ph.sword-fill',
                4: 'mdi6.shield-sword-outline', 5: 'fa5s.gem', 6: 'mdi.castle', 7: 'mdi6.magic-staff',
                8: 'mdi.crystal-ball', 9: 'mdi6.axe-battle', 10: 'fa5s.dragon'},
    'Sci-Fi': {0: 'mdi.hexagon-multiple', 1: 'fa5s.rocket', 2: 'mdi.alien', 3: 'ri.space-ship-fill', 4: 'ei.cog-alt',
               5: 'fa5s.virus', 6: 'mdi.robot', 7: 'mdi.antenna', 8: 'fa5s.syringe', 9: 'fa5s.space-shuttle',
               10: 'mdi.space-invaders',
               11: 'mdi.space-station'},
    'Romance': {0: 'ei.heart', 1: 'fa5s.kiss-wink-heart', 2: 'mdi.lipstick'},
    'Mystery': {0: 'fa5s.puzzle-piece', 1: 'fa5s.user-secret', 2: 'mdi.magnify', 3: 'mdi.incognito',
                4: 'fa5s.question-circle'},
    'Action': {0: 'fa5s.running', 1: 'fa5s.bomb', 2: 'mdi.sword-cross'},
    'Thriller': {0: 'ri.knife-blood-line', 1: 'mdi.skull-crossbones', 2: 'mdi.run-fast', 3: 'mdi.eye-outline'},
    'Horror': {0: 'ri.ghost-2-line', 1: 'mdi.blood-bag', 2: 'mdi.spider-web'},
    'Crime': {0: 'mdi.pistol', 1: 'mdi.handcuffs', 2: 'mdi.police-badge', 3: 'fa5s.fingerprint'},
    'Caper': {0: 'mdi.robber', 1: 'fa5s.mask', 2: 'fa5s.fingerprint'},
    'Coming of Age': {0: 'ri.seedling-line', 1: 'mdi.human-child'},
    'Cozy': {0: 'ri.home-heart-line', 1: 'fa5s.mug-hot'},
    'Historical Fiction': {0: 'fa5s.hourglass-end', 1: 'mdi.castle', 2: 'fa5s.scroll', 3: 'mdi.fountain',
                           4: 'mdi.fountain-pen'},
    'Suspense': {0: 'mdi.eye-outline', 1: 'ph.heartbeat-thin', 2: 'fa5s.user-secret'},
    'Religious Fiction': {0: 'mdi6.hands-pray', 1: 'fa5s.bible', 2: 'fa5s.book', 3: 'fa5s.cross', 4: 'mdi.candle'},
    'War': {0: 'fa5s.skull', 1: 'mdi.tank', 2: 'mdi.chemical-weapon', 3: 'mdi.pistol', 4: 'mdi6.axe-battle'},
    'Western': {0: 'fa5s.hat-cowboy', 1: 'mdi.horseshoe'},
    'Upmarket': {0: 'ph.pen-nib', 1: 'mdi.book-open-variant', 2: 'mdi.script-outline'},
    'Literary Fiction': {0: 'ri.quill-pen-line', 1: 'fa5s.pen-nib', 2: 'mdi.script-outline'},
    'Society': {0: 'mdi6.account-group', 1: 'fa5s.balance-scale-left'},
    'Memoir': {0: 'mdi6.mirror-variant', 1: 'mdi.notebook'},
    "Children's Books": {0: 'mdi6.teddy-bear', 1: 'mdi.balloon'},
    'Slice of Life': {0: 'fa5s.apple-alt', 1: 'mdi.coffee', 2: 'mdi6.notebook-heart-outline'},
    'Comedy': {0: 'fa5.laugh-beam', 1: 'mdi.emoticon-happy-outline'},
    'Contemporary': {0: 'fa5s.mobile-alt', 1: 'mdi.city'},
}


def extract_genre_info(genre: str) -> Tuple[str, str]:
    name, version = re.match(r'^(.*?)(?: #(\d+))?$', genre).groups()
    version = int(version) if version else 0

    icon = genre_icons[name][version] if genre_icons[name].keys() else ''

    return name, icon


class NovelDescriptorsEditorPopup(PopupDialog):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel
        self.frame.layout().setSpacing(3)

        self.btnClose = push_btn(text='Close', properties=['confirm', 'cancel'])
        self.btnClose.clicked.connect(self.accept)

        self.scroll = scroll_area(h_on=False, frameless=True)
        self.center = QFrame()
        vbox(self.center)
        margins(self.center, bottom=15)
        self.scroll.setWidget(self.center)
        self.center.setProperty('white-bg', True)

        self.frame.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)
        self.frame.layout().addWidget(label('Novel Descriptors', h3=True), alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame.layout().addWidget(self.scroll)

        self.lblStandalone = icon_text('ei.book', 'Standalone')
        self.toggleStandalone = Toggle()
        self.lblSeries = icon_text('ph.books', 'Series')
        self.toggleSeries = Toggle()

        self.wdgBookType = group(self.lblStandalone, self.toggleStandalone, vline(), self.lblSeries, self.toggleSeries,
                                 margin_top=15)
        btngroup = exclusive_buttons(self, self.toggleStandalone, self.toggleSeries, optional=True)
        btngroup.buttonClicked.connect(self._typeSelected)
        if self.novel.descriptors.type == 'Standalone':
            self.toggleStandalone.setChecked(True)
        elif self.novel.descriptors.type == 'Series':
            self.toggleSeries.setChecked(True)
        self.center.layout().addWidget(self.wdgBookType, alignment=Qt.AlignmentFlag.AlignLeft)

        self._addHeader('Genres', 'mdi.drama-masks', 'Select the primary genres')
        self.genreSelector = DescriptorLabelSelector(exclusive=False)
        self.genreSelector.setGenres([
            'Fantasy', 'Sci-Fi', 'Romance', 'Mystery', 'Action',
            'Thriller', 'Horror', 'Crime', 'Caper', 'Coming of Age',
            'Cozy', 'Historical Fiction', 'Suspense', 'Religious Fiction', 'War', 'Western', 'Upmarket',
            'Literary Fiction', 'Society', 'Memoir', "Children's Books",
            'Slice of Life', 'Comedy', 'Contemporary'
        ], self.novel.descriptors.genres)
        self.genreSelector.selectionChanged.connect(self._genreSelected)
        self.center.layout().addWidget(self.genreSelector)

        self._addHeader('Audience', 'ei.group', 'Select the target audience of your novel')
        self.audienceSelector = DescriptorLabelSelector()
        self.audienceSelector.setLabels(['Children', 'Middle grade', 'Young adult', 'New adult', 'Adult'],
                                        [self.novel.descriptors.audience])
        self.audienceSelector.selectionChanged.connect(self._audienceSelected)
        self.center.layout().addWidget(self.audienceSelector)

        self._addHeader('Mood', 'mdi.emoticon-outline', "Select your novel's expected mood and atmosphere",
                        ref='Source: The StoryGraph', refLink='https://www.thestorygraph.com/')
        self.moodSelector = DescriptorLabelSelector(exclusive=False)
        self.moodSelector.setLabels(
            ['adventurous', 'challenging', 'dark', 'emotional', 'funny', 'hopeful', 'inspiring',
             'lighthearted', 'mysterious', 'reflective', 'relaxing', 'sad', 'tense'], self.novel.descriptors.mood)
        self.moodSelector.selectionChanged.connect(self._moodSelected)
        self.center.layout().addWidget(self.moodSelector)

        self._addHeader('Style', 'fa5s.pen-fancy', "Select your novel's writing style",
                        ref='Source: Wonderbook',
                        refLink='https://www.amazon.com/Wonderbook-Illustrated-Creating-Imaginative-Fiction/dp/1419704427')
        self.styleSelector = DescriptorLabelSelector()
        self.styleSelector.setLabels(['Stark', 'Conventional', 'Conspicuous', 'Lush'],
                                     [self.novel.descriptors.style])
        self.styleSelector.selectionChanged.connect(self._styleSelected)
        self.center.layout().addWidget(self.styleSelector)

        self.wdgSpice = SpiceWidget(editable=True)
        self.wdgSpice.spiceHoverEntered.connect(self._updateSpiceDescription)
        self.wdgSpice.spiceHoverLeft.connect(self._resetSpiceDescription)
        margins(self.wdgSpice, left=10)
        toggle = self._addHeader('Spice', 'mdi6.chili-mild', "", checkable=True, wdg=self.wdgSpice,
                                 ref='Source: romancerehab.com',
                                 refLink='https://www.romancerehab.com/chili-pepper-heat-rating-scale.html')
        self.descSpice = label('', description=True)
        self.center.layout().addWidget(self.descSpice)
        self.wdgSpice.setSpice(self.novel.descriptors.spice)
        self.wdgSpice.setVisible(self.novel.descriptors.has_spice)
        self.wdgSpice.spiceChanged.connect(self._spiceValueChanged)
        self._resetSpiceDescription()
        toggle.toggled.connect(self._spiceToggled)
        toggle.setChecked(self.novel.descriptors.has_spice)

        self.center.layout().addWidget(vspacer())

        self.frame.layout().addWidget(self.btnClose, alignment=Qt.AlignmentFlag.AlignRight)

        self.setMinimumSize(self._adjustedSize(0.8, 0.7, 600, 500))

    @overrides
    def sizeHint(self) -> QSize:
        return self._adjustedSize(0.8, 0.7, 600, 500)

    def display(self):
        self.exec()

    def _addHeader(self, title: str, icon: str = '', desc: str = '', ref: str = '', refLink: str = '',
                   checkable: bool = False, wdg: Optional[QWidget] = None) -> Optional[
        SmallToggleButton]:
        lbl = IconText()
        lbl.setText(title)
        bold(lbl)
        incr_font(lbl)
        if icon:
            lbl.setIcon(IconRegistry.from_name(icon))

        toggle = None

        refLbl = push_btn(IconRegistry.from_name('fa5s.external-link-alt'), ref, transparent_=True)
        translucent(refLbl, 0.5)
        decr_icon(refLbl, 4)
        decr_font(refLbl)

        if checkable:
            toggle = SmallToggleButton()
            self.center.layout().addWidget(group(lbl, toggle, wdg, spacer(), refLbl, margin_top=10, margin_left=0))
        else:
            self.center.layout().addWidget(group(lbl, spacer(), refLbl, margin_top=10, margin_left=0))
        if desc:
            self.center.layout().addWidget(label(desc, description=True))

        if refLink:
            refLbl.clicked.connect(lambda: open_url(refLink))
        else:
            refLbl.setHidden(True)

        return toggle

    def _genreSelected(self):
        self.novel.descriptors.genres[:] = self.genreSelector.selected()

    def _audienceSelected(self):
        audience = self.audienceSelector.selected()
        self.novel.descriptors.audience = audience[0] if audience else ''

    def _styleSelected(self):
        style = self.styleSelector.selected()
        self.novel.descriptors.style = style[0] if style else ''

    def _moodSelected(self):
        self.novel.descriptors.mood[:] = self.moodSelector.selected()

    def _typeSelected(self):
        if self.toggleStandalone.isChecked():
            self.novel.descriptors.type = 'Standalone'
        elif self.toggleSeries.isChecked():
            self.novel.descriptors.type = 'Series'
        else:
            self.novel.descriptors.type = ''

    def _spiceToggled(self, toggled: bool):
        self.novel.descriptors.has_spice = toggled
        fade(self.wdgSpice, toggled)
        self._resetSpiceDescription()

    def _updateSpiceDescription(self, spice: int):
        self.descSpice.setText(spice_descriptions[spice])

    def _resetSpiceDescription(self):
        if self.novel.descriptors.has_spice and self.novel.descriptors.spice:
            self.descSpice.setText(spice_descriptions[self.novel.descriptors.spice])
        else:
            self.descSpice.clear()

    def _spiceValueChanged(self, spice: int):
        self.novel.descriptors.spice = spice


class NovelDescriptorsDisplay(QWidget):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel

        self.card = frame()
        self.card.setProperty('large-rounded', True)
        self.card.setProperty('relaxed-white-bg', True)
        self.card.setMaximumWidth(1000)
        hbox(self).addWidget(self.card)
        vbox(self.card, 10, spacing=35)
        margins(self.card, top=25, bottom=40)

        self.wdgTitle = QWidget()
        self.wdgTitle.setProperty('border-image', True)
        pointy(self.wdgTitle)
        hbox(self.wdgTitle)
        self.wdgTitle.setFixedHeight(150)
        self.wdgTitle.setMaximumWidth(1000)
        apply_border_image(self.wdgTitle, resource_registry.frame1)
        self.wdgTitle.installEventFilter(OpacityEventFilter(self.wdgTitle, 0.8, 1.0))

        self.lineNovelTitle = label(novel.title)
        self.lineNovelTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        transparent(self.lineNovelTitle)
        incr_font(self.lineNovelTitle, 10)
        self.wdgTitle.layout().addWidget(self.lineNovelTitle, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.lineNovelTitle.setText(novel.title)

        self.scrollDescriptors = scroll_area(h_on=False, frameless=True)
        self.wdgDescriptors = QWidget()
        self.wdgDescriptors.installEventFilter(OpacityEventFilter(self.wdgDescriptors, 0.9, 1.0))
        pointy(self.wdgDescriptors)
        self.wdgDescriptors.setProperty('relaxed-white-bg', True)
        self.scrollDescriptors.setWidget(self.wdgDescriptors)
        self._grid = grid(self.wdgDescriptors, v_spacing=20, h_spacing=15)
        margins(self.wdgDescriptors, left=45, right=45)
        sp(self.wdgDescriptors).v_exp()

        self.wdgGenres = self._labels()
        margins(self.wdgGenres, top=5)
        self.wdgAudience = self._labels()
        self.wdgMood = self._labels()
        margins(self.wdgMood, top=5)
        self.wdgStyle = self._labels()

        self._grid.addWidget(self._label('Genres', 'mdi.drama-masks'), 0, 0, alignment=Qt.AlignmentFlag.AlignRight)
        self._grid.addWidget(self.wdgGenres, 0, 1)
        self._grid.addWidget(self._label('Audience', 'ei.group'), 1, 0, alignment=Qt.AlignmentFlag.AlignRight)
        self._grid.addWidget(self.wdgAudience, 1, 1)
        self._grid.addWidget(self._label('Mood', 'mdi.emoticon-outline'), 2, 0, alignment=Qt.AlignmentFlag.AlignRight)
        self._grid.addWidget(self.wdgMood, 2, 1)
        self._grid.addWidget(self._label('Style', 'fa5s.pen-fancy'), 3, 0, alignment=Qt.AlignmentFlag.AlignRight)
        self._grid.addWidget(self.wdgStyle, 3, 1)

        self.wdgRightSide = QWidget()
        vbox(self.wdgRightSide, spacing=8)
        self._lblStandalone = self._label('Standalone', 'ei.book', major=False)
        self._words = self._label('', 'mdi.book-open-page-variant-outline', major=False)
        self.wdgRightSide.layout().addWidget(self._lblStandalone, alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgRightSide.layout().addWidget(self._words, alignment=Qt.AlignmentFlag.AlignLeft)

        self._updateWc()
        self._grid.addWidget(self.wdgRightSide, 0, 2, 1, 2, alignment=Qt.AlignmentFlag.AlignTop)

        self.lblSpice = self._label('Spice', 'mdi6.chili-mild')
        self.wdgSpice = SpiceWidget()
        self.wdgSpice.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._grid.addWidget(self.lblSpice, 4, 0, alignment=Qt.AlignmentFlag.AlignRight)
        self._grid.addWidget(self.wdgSpice, 4, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        if self.novel.descriptors.has_spice:
            self.wdgSpice.setSpice(self.novel.descriptors.spice)
        else:
            self.lblSpice.setHidden(True)
            self.wdgSpice.setHidden(True)

        self._grid.addWidget(vspacer(), 10, 0)

        self.card.layout().addWidget(self.wdgTitle)
        self.card.layout().addWidget(self.scrollDescriptors)

        self.textPremise = AutoAdjustableTextEdit()
        self.textPremise.setMaximumWidth(500)
        self.textPremise.setPlaceholderText("Premise: encapsulate your story's core idea in 1-2 sentences")
        transparent(self.textPremise)
        self.textPremise.setFontItalic(True)
        # self.ui.btnPremiseIcon.setIcon(IconRegistry.from_name('mdi.label-variant'))
        self.textPremise.setText(self.novel.premise)
        self.textPremise.textChanged.connect(self._premise_changed)

        self.wdgPremiseParent = QWidget()
        hbox(self.wdgPremiseParent).addWidget(self.textPremise)
        self._grid.addWidget(self.wdgPremiseParent, 8, 0, 1, 3)

        self.wdgTitle.installEventFilter(self)
        self.wdgDescriptors.installEventFilter(self)

        self.repo = RepositoryPersistenceManager.instance()
        self.refresh()

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched == self.wdgDescriptors and event.type() == QEvent.Type.MouseButtonPress:
            self._edit()
        elif watched == self.wdgTitle and event.type() == QEvent.Type.MouseButtonPress:
            emit_global_event(SelectNovelEvent(self, self.novel))
        return super().eventFilter(watched, event)

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._updateWc()

    def refreshTitle(self):
        self.lineNovelTitle.setText(self.novel.title)
        self.lineNovelTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def refresh(self):
        if self.novel.descriptors.type:
            self._lblStandalone.setText(self.novel.descriptors.type)
            self._lblStandalone.setVisible(True)
            if self.novel.descriptors.type == 'Standalone':
                self._lblStandalone.setIcon(IconRegistry.from_name('ei.book', 'grey'))
            else:
                self._lblStandalone.setIcon(IconRegistry.from_name('ph.books', 'grey'))
        else:
            self._lblStandalone.setHidden(True)

        if self.novel.descriptors.audience:
            lbl = label(self.novel.descriptors.audience, incr_font_diff=2)
            font = lbl.font()
            font.setFamily(app_env.serif_font())
            lbl.setFont(font)
            lbl.setStyleSheet(f'''
                   QLabel {{
                       border: 1px solid lightgrey;
                       background: {BG_PRIMARY_COLOR};
                       padding: 10px 5px 10px 5px;
                       border-radius: 12px;
                   }}
                   ''')
            self.wdgAudience.layout().addWidget(lbl)

        if self.novel.descriptors.style:
            lbl = label(self.novel.descriptors.style, incr_font_diff=1)
            font = lbl.font()
            if self.novel.descriptors.style == 'Stark':
                font.setFamily(app_env.mono_font())
            elif self.novel.descriptors.style == 'Conventional':
                font.setFamily(app_env.serif_font())
            elif self.novel.descriptors.style == 'Conspicuous':
                font.setFamily(app_env.sans_serif_font())
            elif self.novel.descriptors.style == 'Lush':
                font.setFamily(app_env.cursive_font())
            lbl.setFont(font)
            lbl.setStyleSheet(f'''
                   QLabel {{
                       border: 1px solid lightgrey;
                       padding: 10px 5px 10px 5px;
                       border-radius: 12px;
                   }}
                   ''')
            self.wdgStyle.layout().addWidget(lbl)

        for mood in self.novel.descriptors.mood:
            lbl = label(mood, decr_font_diff=1)
            font = lbl.font()
            font.setFamily(app_env.sans_serif_font())
            lbl.setFont(font)
            lbl.setStyleSheet(f'''
                               QLabel {{
                                   border: 1px solid lightgrey;
                                   color: {PLOTLYST_SECONDARY_COLOR};
                                   background: rgba(0, 0, 0, 0);
                                   border-radius: 4px;
                               }}
                               ''')
            self.wdgMood.layout().addWidget(lbl)

        for genre in self.novel.descriptors.genres:
            lbl = QPushButton()
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            name, icon = extract_genre_info(genre)
            if icon:
                lbl.setIcon(IconRegistry.from_name(icon, RELAXED_WHITE_COLOR))
            lbl.setText(name)
            font = lbl.font()
            font.setFamily(app_env.sans_serif_font())
            lbl.setFont(font)
            incr_font(lbl)
            lbl.setStyleSheet(f'''
                               QPushButton {{
                                   border: 1px solid lightgrey;
                                   background: {PLOTLYST_SECONDARY_COLOR};
                                   color: {RELAXED_WHITE_COLOR};
                                   padding: 10px;
                                   border-radius: 12px;
                               }}
                               ''')
            self.wdgGenres.layout().addWidget(lbl)

        self.lblSpice.setVisible(self.novel.descriptors.has_spice)
        self.wdgSpice.setVisible(self.novel.descriptors.has_spice)
        if self.novel.descriptors.has_spice:
            self.wdgSpice.setSpice(self.novel.descriptors.spice)
            self.wdgSpice.setToolTip(spice_descriptions[self.novel.descriptors.spice])

    def _label(self, text: str, icon: str = '', major: bool = True) -> IconText:
        lbl = IconText()
        lbl.setText(text)
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        if icon:
            lbl.setIcon(IconRegistry.from_name(icon, 'grey'))
        lbl.setStyleSheet('color: grey; border: 0px;')

        incr_font(lbl, 3 if major else 0)
        incr_icon(lbl, 3 if major else 0)

        return lbl

    def _labels(self) -> QWidget:
        wdg = QWidget()
        sp(wdg).v_max()
        flow(wdg)
        return wdg

    def _updateWc(self):
        wc = 0
        for scene in self.novel.scenes:
            if not scene.manuscript or not scene.manuscript.statistics:
                continue
            wc += scene.manuscript.statistics.wc

        self._words.setText(f'Word count: {wc:,}')

    def _premise_changed(self):
        text = self.textPremise.toPlainText()
        self.novel.premise = text
        self.repo.update_novel(self.novel)

    def _edit(self):
        NovelDescriptorsEditorPopup.popup(self.novel)

        clear_layout(self.wdgGenres)
        clear_layout(self.wdgAudience)
        clear_layout(self.wdgStyle)
        clear_layout(self.wdgMood)

        self.refresh()
        self.repo.update_novel(self.novel)
