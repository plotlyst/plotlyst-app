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
from abc import abstractmethod
from functools import partial
from typing import Dict, Optional, List

import qtanim
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QEvent
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtWidgets import QWidget, QPushButton, QToolButton, QGridLayout, QFormLayout
from overrides import overrides
from qthandy import transparent, sp, vbox, hbox, vspacer, incr_font, pointy, grid, margins, line, spacer, translucent
from qthandy.filter import OpacityEventFilter
from qtmenu import MenuWidget

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, PLOTLYST_TERTIARY_COLOR, DEFAULT_PREMIUM_LINK, RELAXED_WHITE_COLOR
from plotlyst.core.domain import Novel, NovelSetting
from plotlyst.env import app_env
from plotlyst.event.core import emit_event, EventListener, Event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import NovelPanelCustomizationEvent, \
    NovelStructureToggleEvent, NovelStorylinesToggleEvent, NovelCharactersToggleEvent, NovelScenesToggleEvent, \
    NovelWorldBuildingToggleEvent, NovelManuscriptToggleEvent, NovelDocumentsToggleEvent, NovelManagementToggleEvent, \
    NovelEmotionTrackingToggleEvent, NovelMotivationTrackingToggleEvent, NovelConflictTrackingToggleEvent, \
    NovelPovTrackingToggleEvent, NovelCharacterEnneagramToggleEvent, NovelCharacterMbtiToggleEvent, \
    NovelCharacterLoveStyleToggleEvent, NovelCharacterWorkStyleToggleEvent, NovelScenesOrganizationToggleEvent, \
    ScenesOrganizationResetEvent
from plotlyst.service.persistence import RepositoryPersistenceManager, reset_scenes_organization
from plotlyst.view.common import label, ButtonPressResizeEventFilter, push_btn, open_url
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.style.button import apply_button_palette_color
from plotlyst.view.widget.button import SmallToggleButton
from plotlyst.view.widget.confirm import asked
from plotlyst.view.widget.display import Icon
from plotlyst.view.widget.input import Toggle

setting_titles: Dict[NovelSetting, str] = {
    NovelSetting.Structure: 'Story structure',
    NovelSetting.Mindmap: 'Mindmap',
    NovelSetting.Storylines: 'Storylines',
    NovelSetting.Characters: 'Characters',
    NovelSetting.Scenes: 'Narrative manager',
    NovelSetting.Scenes_organization: 'Work with scenes',
    NovelSetting.Track_emotion: 'Track character emotions',
    NovelSetting.Track_motivation: 'Track character motivation',
    NovelSetting.Track_conflict: 'Track character conflicts',
    NovelSetting.World_building: 'World-building',
    NovelSetting.Manuscript: 'Manuscript',
    NovelSetting.Documents: 'Documents',
    NovelSetting.Management: 'Task management',
    NovelSetting.Track_pov: 'Point of view',
    NovelSetting.Character_enneagram: 'Enneagram',
    NovelSetting.Character_mbti: 'MBTI',
    NovelSetting.Character_love_style: 'Love style',
    NovelSetting.Character_work_style: 'Work style',
}
setting_descriptions: Dict[NovelSetting, str] = {
    NovelSetting.Structure: "Follow a story structure to help you with your story's pacing and escalation",
    NovelSetting.Storylines: "Create separate storylines for plot, character's change, subplots, or relationship plots",
    NovelSetting.Characters: "Create a cast of characters with different roles, personalities, backstories, goals, and relationships among them",
    NovelSetting.Scenes: "Manage scenes and chapters in different perspectives, and link characters, structure beats, or storylines to them",
    NovelSetting.Scenes_organization: "Organize your novel into scenes and chapters. Otherwise if turned off, you will write and manage chapters only.",
    NovelSetting.Track_emotion: "Track and visualize how characters' emotions shift between positive and negative throughout the scenes",
    NovelSetting.Track_motivation: "Track and visualize how characters' motivation change throughout the scenes",
    NovelSetting.Track_conflict: 'Track the frequency and the type of conflicts the characters face',
    NovelSetting.World_building: "Develop your story's world by creating fictional settings and lore",
    NovelSetting.Manuscript: "Write your story in Plotlyst using the manuscript panel",
    NovelSetting.Documents: "Create documents and mind maps for your planning or research",
    NovelSetting.Management: "Stay organized by tracking your tasks in a simple Kanban board",
    NovelSetting.Track_pov: "Track the point of view characters of your story",
    NovelSetting.Character_enneagram: 'Consider enneagram personality type for characters',
    NovelSetting.Character_mbti: 'Consider MBTI personality type for characters',
    NovelSetting.Character_love_style: "Consider the characters' preferred love style",
    NovelSetting.Character_work_style: "Consider the characters' most typical working style",
}

panel_events = [NovelCharactersToggleEvent,
                NovelManuscriptToggleEvent, NovelScenesToggleEvent,
                NovelDocumentsToggleEvent, NovelStructureToggleEvent,
                NovelStorylinesToggleEvent, NovelWorldBuildingToggleEvent,
                NovelManagementToggleEvent]

setting_events: Dict[NovelSetting, NovelPanelCustomizationEvent] = {
    NovelSetting.Structure: NovelStructureToggleEvent,
    NovelSetting.Storylines: NovelStorylinesToggleEvent,
    NovelSetting.Characters: NovelCharactersToggleEvent,
    NovelSetting.Character_enneagram: NovelCharacterEnneagramToggleEvent,
    NovelSetting.Character_mbti: NovelCharacterMbtiToggleEvent,
    NovelSetting.Character_love_style: NovelCharacterLoveStyleToggleEvent,
    NovelSetting.Character_work_style: NovelCharacterWorkStyleToggleEvent,
    NovelSetting.Scenes: NovelScenesToggleEvent,
    NovelSetting.Scenes_organization: NovelScenesOrganizationToggleEvent,
    NovelSetting.Track_emotion: NovelEmotionTrackingToggleEvent,
    NovelSetting.Track_motivation: NovelMotivationTrackingToggleEvent,
    NovelSetting.Track_conflict: NovelConflictTrackingToggleEvent,
    NovelSetting.Track_pov: NovelPovTrackingToggleEvent,
    NovelSetting.World_building: NovelWorldBuildingToggleEvent,
    NovelSetting.Manuscript: NovelManuscriptToggleEvent,
    NovelSetting.Documents: NovelDocumentsToggleEvent,
    NovelSetting.Management: NovelManagementToggleEvent
}


def setting_icon(setting: NovelSetting, color=PLOTLYST_SECONDARY_COLOR, color_on=PLOTLYST_SECONDARY_COLOR) -> QIcon:
    if setting == NovelSetting.Structure:
        return IconRegistry.story_structure_icon(color=color, color_on=color_on)
    elif setting == NovelSetting.Storylines:
        return IconRegistry.storylines_icon(color=color, color_on=color_on)
    elif setting == NovelSetting.Characters:
        return IconRegistry.character_icon(color=color, color_on=color_on)
    elif setting == NovelSetting.Character_enneagram:
        return IconRegistry.from_name('mdi.numeric-9-circle', color=color, color_on=color_on)
    elif setting == NovelSetting.Character_mbti:
        return IconRegistry.from_name('mdi.head-question-outline', color=color, color_on=color_on)
    elif setting == NovelSetting.Character_love_style:
        return IconRegistry.from_name('fa5s.heart', color=color, color_on=color_on)
    elif setting == NovelSetting.Character_work_style:
        return IconRegistry.from_name('fa5s.briefcase', color=color, color_on=color_on)
    elif setting == NovelSetting.Scenes:
        return IconRegistry.scene_icon(color=color, color_on=color_on)
    elif setting == NovelSetting.Scenes_organization:
        return IconRegistry.from_name('mdi6.movie-filter-outline', color=color, color_on=color_on)
    elif setting == NovelSetting.Track_emotion:
        return IconRegistry.emotion_icon(color=color, color_on=color_on)
    elif setting == NovelSetting.Track_motivation:
        return IconRegistry.from_name('fa5s.fist-raised', color=color, color_on=color_on)
    elif setting == NovelSetting.Track_conflict:
        return IconRegistry.conflict_icon(color=color, color_on=color_on)
    elif setting == NovelSetting.Track_pov:
        return IconRegistry.eye_open_icon(color=color, color_on=color_on)
    elif setting == NovelSetting.World_building:
        return IconRegistry.world_building_icon(color=color, color_on=color_on)
    elif setting == NovelSetting.Manuscript:
        return IconRegistry.manuscript_icon(color=color, color_on=color_on)
    elif setting == NovelSetting.Documents:
        return IconRegistry.document_edition_icon(color=color, color_on=color_on)
    elif setting == NovelSetting.Management:
        return IconRegistry.board_icon(color, color_on)
    return QIcon()


def toggle_setting(source, novel: Novel, setting: NovelSetting, toggled: bool):
    novel.prefs.settings[setting.value] = toggled
    RepositoryPersistenceManager.instance().update_novel(novel)

    event_clazz = setting_events[setting]
    emit_event(novel, event_clazz(source, setting, toggled))


class Forms(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        vbox(self, 0, 0)
        self.wdgSettings = QWidget()
        self._layout = QFormLayout(self.wdgSettings)
        margins(self.wdgSettings, left=20)

        self.layout().addWidget(label(title, bold=True), alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.wdgSettings, alignment=Qt.AlignmentFlag.AlignLeft)

    def addSetting(self, text: str) -> SmallToggleButton:
        toggle = SmallToggleButton()
        self._layout.addRow(label(text, description=True), toggle)
        return toggle

    def setRowVisible(self, row: int, visible: bool):
        self._layout.setRowVisible(row, visible)


class SimpleToggleSetting(QWidget):
    def __init__(self, text: str, parent=None, checked: bool = False, alignLeft: bool = False,
                 alignRight: bool = False):
        super().__init__(parent)
        hbox(self)
        if alignRight:
            self.layout().addWidget(spacer())
        self.layout().addWidget(label(text, description=True))
        self.toggle = SmallToggleButton()
        self.toggle.setChecked(checked)
        self.layout().addWidget(self.toggle)

        if alignLeft:
            self.layout().addWidget(spacer())


class SettingBaseWidget(QWidget):
    def __init__(self, parent=None, enabled: bool = True):
        super().__init__(parent)
        self._title = QPushButton()
        apply_button_palette_color(self._title, PLOTLYST_SECONDARY_COLOR)
        transparent(self._title)
        incr_font(self._title, 2)

        self._description = label('', description=True)
        self._description.setWordWrap(True)
        sp(self._description).h_exp()

        self._wdgTitle = QWidget()
        vbox(self._wdgTitle)
        self._wdgTitle.layout().addWidget(self._title, alignment=Qt.AlignmentFlag.AlignLeft)
        self._wdgTitle.layout().addWidget(self._description)

        self._wdgChildren = QWidget()
        vbox(self._wdgChildren)
        margins(self._wdgChildren, left=20, right=20)
        self._wdgChildren.setHidden(True)

        if enabled:
            self._toggle = Toggle()
            self._toggle.setChecked(True)
            self._toggle.toggled.connect(self._toggled)
            self._toggle.clicked.connect(self._clicked)
        else:
            self._toggle = Icon()
            self._toggle.setIcon(IconRegistry.from_name('ei.lock'))

        self._wdgHeader = QWidget()
        self._wdgHeader.setObjectName('wdgHeader')
        hbox(self._wdgHeader)
        self._wdgHeader.layout().addWidget(self._wdgTitle)
        self._wdgHeader.layout().addWidget(self._toggle,
                                           alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        vbox(self, 0, 0)
        self.layout().addWidget(self._wdgHeader)
        self.layout().addWidget(self._wdgChildren)

    def setChecked(self, checked: bool):
        self._toggle.setChecked(checked)

    def addChild(self, child: QWidget):
        self._wdgChildren.setVisible(self._toggle.isChecked())
        self._wdgChildren.layout().addWidget(child)

    def _toggled(self, toggled: bool):
        if toggled:
            self._wdgTitle.setGraphicsEffect(None)
        else:
            translucent(self._wdgTitle)
        self._wdgChildren.setVisible(toggled)

    @abstractmethod
    def _clicked(self, toggled: bool):
        pass


class NovelSettingToggle(SettingBaseWidget):
    settingToggled = pyqtSignal(NovelSetting, bool)

    def __init__(self, novel: Novel, setting: NovelSetting, parent=None, enabled: bool = True):
        super().__init__(parent, enabled=enabled)
        self._novel = novel
        self._setting = setting

        self._title.setText(setting_titles[setting])
        self._title.setIcon(setting_icon(setting))

        self._description.setText(setting_descriptions[setting])

        self._toggle.setChecked(self._novel.prefs.toggled(self._setting))

    @overrides
    def _clicked(self, toggled: bool):
        self.settingToggled.emit(self._setting, toggled)


class NovelPovSettingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


class NovelPanelCustomizationToggle(QToolButton):
    def __init__(self, setting: NovelSetting, parent=None):
        super().__init__(parent)
        self._setting = setting

        pointy(self)
        self.setCheckable(True)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        self.setIcon(setting_icon(self._setting, 'grey', PLOTLYST_SECONDARY_COLOR))
        transparent(self)
        self.setIconSize(QSize(30, 30))
        self.setText(setting_titles[self._setting])
        incr_font(self, 2)

        sp(self).h_exp().v_exp()

        self.setMinimumWidth(150)
        self.setMaximumHeight(100)

        self.installEventFilter(ButtonPressResizeEventFilter(self))
        self.installEventFilter(OpacityEventFilter(self, ignoreCheckedButton=True))

        self.setStyleSheet(f'''
            QToolButton {{
                color: grey;
                background: lightgrey;
                border: 1px solid lightgrey;
                border-radius: 2px;
            }}
            QToolButton:checked {{
                color: black;
                background: {PLOTLYST_TERTIARY_COLOR};
            }}
        ''')

        self.clicked.connect(self._glow)

    def setting(self) -> NovelSetting:
        return self._setting

    def _glow(self, checked: bool):
        if checked:
            qtanim.glow(self, 150, color=QColor(PLOTLYST_SECONDARY_COLOR), radius=12)
        else:
            qtanim.glow(self, 150, color=QColor('grey'), radius=5)


class NovelPanelSettingsWidget(QWidget):
    clicked = pyqtSignal(NovelSetting, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._novel: Optional[Novel] = None
        self.setProperty('relaxed-white-bg', True)

        vbox(self)
        self._wdgCenter = QWidget()
        self._wdgBottom = QWidget()
        self._lblDesc = label('', wordWrap=True, description=True)
        incr_font(self._lblDesc, 2)
        self._lblDesc.setMinimumSize(400, 100)
        self._lblDesc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hbox(self._wdgBottom, margin=15).addWidget(self._lblDesc, alignment=Qt.AlignmentFlag.AlignCenter)

        self.layout().addWidget(label('Customize your experience:'),
                                alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._wdgCenter)
        self.layout().addWidget(self._wdgBottom)
        self._grid: QGridLayout = grid(self._wdgCenter)

        self._settings: Dict[NovelSetting, NovelPanelCustomizationToggle] = {}
        self._addSetting(NovelSetting.Manuscript, 0, 0)
        self._addSetting(NovelSetting.Characters, 0, 1)
        self._addSetting(NovelSetting.Scenes, 0, 2)

        self._addSetting(NovelSetting.Storylines, 1, 0, enabled=app_env.profile().get('storylines', False))
        self._addSetting(NovelSetting.Structure, 1, 2)

        self._addSetting(NovelSetting.Documents, 2, 0)
        self._addSetting(NovelSetting.World_building, 2, 1, enabled=app_env.profile().get('world-building', False))
        self._addSetting(NovelSetting.Management, 2, 2, enabled=app_env.profile().get('tasks', False))

    def setNovel(self, novel: Novel):
        self._novel = novel
        for toggle in self._settings.values():
            if not toggle.isEnabled():
                continue
            toggle.setChecked(self._novel.prefs.toggled(toggle.setting()))

    # def reset(self):
    #     event_dispatchers.instance(self._novel).deregister(self, *panel_events)
    #     self._novel = None

    @overrides
    def eventFilter(self, watched: 'QObject', event: QEvent) -> bool:
        if event.type() == QEvent.Type.Enter:
            self._lblDesc.setText(setting_descriptions[watched.setting()])
        return super().eventFilter(watched, event)

    def checkAllSettings(self, checked: bool):
        for k in self._settings.keys():
            self._settings[k].setChecked(checked)

    def checkSettings(self, settings: List[NovelSetting], checked: bool = True):
        self.checkAllSettings(not checked)

        for setting in settings:
            self._settings[setting].setChecked(checked)

    def toggledSettings(self) -> List[NovelSetting]:
        return [k for k, v in self._settings.items() if v.isChecked()]

    def _addSetting(self, setting: NovelSetting, row: int, col: int, enabled: bool = True):
        toggle = NovelPanelCustomizationToggle(setting)
        self._settings[setting] = toggle
        if not enabled:
            toggle.setIcon(IconRegistry.from_name('ei.lock'))
            toggle.setChecked(False)
            toggle.setDisabled(True)
        toggle.toggled.connect(partial(self._settingToggled, setting))
        toggle.clicked.connect(partial(self._settingChanged, setting))
        toggle.installEventFilter(self)
        self._grid.addWidget(toggle, row, col, 1, 1)

    def _settingToggled(self, setting: NovelSetting, toggled: bool):
        self._novel.prefs.settings[setting.value] = toggled

    def _settingChanged(self, setting: NovelSetting, toggled: bool):
        self.clicked.emit(setting, toggled)


class NovelQuickPanelCustomizationWidget(NovelPanelSettingsWidget, EventListener):
    def __init__(self, parent=None):
        super().__init__(parent)

    @overrides
    def setNovel(self, novel: Novel):
        super().setNovel(novel)
        event_dispatchers.instance(self._novel).register(self, *panel_events)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, NovelPanelCustomizationEvent):
            self._settings[event.setting].setChecked(event.toggled)

    @overrides
    def _settingToggled(self, setting: NovelSetting, toggled: bool):
        pass

    @overrides
    def _settingChanged(self, setting: NovelSetting, toggled: bool):
        toggle_setting(self, self._novel, setting, toggled)


class NovelQuickPanelCustomizationButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(IconRegistry.from_name('fa5s.cubes'))
        self.setToolTip('Customize what panels are visible')
        pointy(self)
        self.installEventFilter(ButtonPressResizeEventFilter(self))

        self._menu = MenuWidget(self)
        self._customizationWidget = NovelQuickPanelCustomizationWidget()
        apply_white_menu(self._menu)
        self._menu.addWidget(self._customizationWidget)

    def setNovel(self, novel: Novel):
        self._customizationWidget.setNovel(novel)

    # def reset(self):
    #     self._customizationWidget.reset()


class NovelSettingsWidget(QWidget, EventListener):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel

        vbox(self, spacing=10)
        self._settings: Dict[NovelSetting, NovelSettingToggle] = {}

        self._addSettingToggle(NovelSetting.Structure)

        wdgCharacters = self._addSettingToggle(NovelSetting.Characters)
        self._addSettingToggle(NovelSetting.Character_enneagram, wdgCharacters)
        self._addSettingToggle(NovelSetting.Character_mbti, wdgCharacters)
        self._addSettingToggle(NovelSetting.Character_love_style, wdgCharacters)
        self._addSettingToggle(NovelSetting.Character_work_style, wdgCharacters)

        wdgScenes = self._addSettingToggle(NovelSetting.Scenes)
        self._addSettingToggle(NovelSetting.Track_pov, wdgScenes)
        # wdgPov = NovelPovSettingWidget()
        # wdgScenes.addChild(wdgPov)
        # self._addSettingToggle(NovelSetting.Track_emotion, wdgScenes)
        # self._addSettingToggle(NovelSetting.Track_motivation, wdgScenes)
        # self._addSettingToggle(NovelSetting.Track_conflict, wdgScenes)
        self._addSettingToggle(NovelSetting.Manuscript)
        self._addSettingToggle(NovelSetting.Documents)

        if app_env.profile().get('license_type', 'FREE') == 'FREE':
            self.layout().addWidget(label('Premium panels', h5=True), alignment=Qt.AlignmentFlag.AlignLeft)
            btnPurchase = push_btn(IconRegistry.from_name('ei.shopping-cart', RELAXED_WHITE_COLOR),
                                   'Upgrade to gain access to these additional panels',
                                   properties=['confirm', 'positive'])
            btnPurchase.clicked.connect(lambda: open_url(DEFAULT_PREMIUM_LINK))
            btnPurchase.installEventFilter(OpacityEventFilter(btnPurchase, 0.8, 0.6))
            self.layout().addWidget(btnPurchase, alignment=Qt.AlignmentFlag.AlignLeft)
        wdg = self._addSettingToggle(NovelSetting.Storylines, enabled=app_env.profile().get('storylines', False))
        if not wdg.isEnabled():
            margins(wdg, left=20)
        wdg = self._addSettingToggle(NovelSetting.World_building,
                                     enabled=app_env.profile().get('world-building', False))
        if not wdg.isEnabled():
            margins(wdg, left=20)
        wdg = self._addSettingToggle(NovelSetting.Management, enabled=app_env.profile().get('tasks', False))
        if not wdg.isEnabled():
            margins(wdg, left=20)

        self.layout().addWidget(label('Advanced settings', h4=True), alignment=Qt.AlignmentFlag.AlignLeft)
        wdgScenesOrg = self._addSettingToggle(NovelSetting.Scenes_organization, insertLine=False,
                                              enabled=not novel.is_readonly())
        margins(wdgScenesOrg, bottom=20)

        self.layout().addWidget(vspacer())

        event_dispatchers.instance(self._novel).register(self, *panel_events)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, NovelPanelCustomizationEvent):
            self._settings[event.setting].setChecked(event.toggled)

    def _addSettingToggle(self, setting: NovelSetting,
                          parent: Optional[NovelSettingToggle] = None, enabled: bool = True,
                          insertLine: bool = True) -> NovelSettingToggle:
        toggle = NovelSettingToggle(self._novel, setting, enabled=enabled)
        if setting == NovelSetting.Scenes_organization:
            toggle.settingToggled.connect(partial(self._scenesOrganizationToggled, toggle))
        else:
            toggle.settingToggled.connect(self._toggled)
        toggle.setEnabled(enabled)
        self._settings[setting] = toggle
        if parent:
            parent.addChild(toggle)
        else:
            self.layout().addWidget(toggle)
            if insertLine:
                self.layout().addWidget(line())

        return toggle

    def _toggled(self, setting: NovelSetting, toggled: bool):
        toggle_setting(self, self._novel, setting, toggled)

    def _scenesOrganizationToggled(self, toggle: NovelSettingToggle, setting: NovelSetting, toggled: bool):
        if not toggled and self._novel.chapters:
            if asked(
                    "Are you sure you want to write and manage chapters directly? Your scenes will be transformed into chapters, and your current chapters will be removed.",
                    "Turn off scenes"):
                reset_scenes_organization(self._novel)
                emit_event(self._novel, ScenesOrganizationResetEvent(self))
            else:
                toggle.setChecked(True)
                return

        self._toggled(setting, toggled)
