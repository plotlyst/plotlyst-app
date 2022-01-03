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
from typing import Dict

import qtawesome
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QLabel

from src.main.python.plotlyst.common import ACT_ONE_COLOR, ACT_TWO_COLOR, ACT_THREE_COLOR
from src.main.python.plotlyst.core.domain import Character, VERY_UNHAPPY, UNHAPPY, HAPPY, VERY_HAPPY, ConflictType
from src.main.python.plotlyst.settings import CHARACTER_INITIAL_AVATAR_COLOR_CODES
from src.main.python.plotlyst.view.common import rounded_pixmap


class IconRegistry:

    @staticmethod
    def ok_icon(color: str = 'green') -> QIcon:
        return qtawesome.icon('ei.ok', color=color)

    @staticmethod
    def wrong_icon(color: str = 'red') -> QIcon:
        return qtawesome.icon('ei.remove', color=color)

    @staticmethod
    def cancel_icon() -> QIcon:
        return qtawesome.icon('mdi.backspace', color='red')

    @staticmethod
    def error_icon() -> QIcon:
        return qtawesome.icon('fa5s.exclamation-triangle', color='red')

    @staticmethod
    def empty_icon() -> QIcon:
        return QIcon('')

    # used to fill up space in models
    @staticmethod
    def invisible_white_icon():
        return qtawesome.icon('fa5.circle', color='white')

    @staticmethod
    def copy_icon() -> QIcon:
        return qtawesome.icon('fa5.copy')

    @staticmethod
    def paste_icon() -> QIcon:
        return qtawesome.icon('fa5s.paste')

    @staticmethod
    def cut_icon() -> QIcon:
        return qtawesome.icon('fa5s.cut')

    @staticmethod
    def increase_font_size_icon() -> QIcon:
        return IconRegistry.from_name('mdi.format-font-size-increase')

    @staticmethod
    def decrease_font_size_icon() -> QIcon:
        return IconRegistry.from_name('mdi.format-font-size-decrease')

    @staticmethod
    def filter_icon() -> QIcon:
        return qtawesome.icon('fa5s.filter')

    @staticmethod
    def edit_icon(color_on: str = 'black') -> QIcon:
        return IconRegistry.from_name('mdi.pencil', color_on=color_on)

    @staticmethod
    def plus_edit_icon() -> QIcon:
        return IconRegistry.from_name('mdi.pencil-plus', color='#004385')

    @staticmethod
    def plus_icon(color: str = 'green') -> QIcon:
        return qtawesome.icon('fa5s.plus', color=color)

    @staticmethod
    def plus_circle_icon(color: str = 'black') -> QIcon:
        return qtawesome.icon('ei.plus-sign', color=color)

    @staticmethod
    def minus_icon(color: str = 'red') -> QIcon:
        return qtawesome.icon('fa5s.minus', color=color)

    @staticmethod
    def history_icon() -> QIcon:
        return qtawesome.icon('fa5s.history')

    @staticmethod
    def character_icon(color: str = 'black', color_on: str = 'darkBlue') -> QIcon:
        return qtawesome.icon('fa5s.user', color=color, color_on=color_on)

    @staticmethod
    def location_icon() -> QIcon:
        return qtawesome.icon('fa5s.location-arrow', color_on='darkBlue')

    @staticmethod
    def scene_icon() -> QIcon:
        return qtawesome.icon('mdi.movie-open', color_on='darkBlue')

    @staticmethod
    def chapter_icon() -> QIcon:
        return qtawesome.icon('ei.book')

    @staticmethod
    def book_icon(color='black', color_on='darkBlue') -> QIcon:
        return qtawesome.icon('fa5s.book-open', color_on=color_on, color=color)

    @staticmethod
    def synopsis_icon() -> QIcon:
        return IconRegistry.from_name('mdi.file-document')

    @staticmethod
    def general_info_icon() -> QIcon:
        return qtawesome.icon('fa5s.info-circle', color='darkBlue')

    @staticmethod
    def action_scene_icon(resolved: bool = False, trade_off: bool = False) -> QIcon:
        if resolved:
            color = '#0b6e4f'
        elif trade_off:
            color = '#832161'
        else:
            color = '#fe4a49'
        return qtawesome.icon('fa5s.circle', 'fa5s.yin-yang',
                              options=[{'color': 'white', 'scale_factor': 1}, {'color': color}])

    @staticmethod
    def reaction_scene_icon() -> QIcon:
        return qtawesome.icon('fa5s.circle', 'fa5s.yin-yang',
                              options=[{'color': 'white', 'scale_factor': 1}, {'color': '#4b86b4'}])

    @staticmethod
    def hashtag_icon() -> QIcon:
        return qtawesome.icon('fa5s.hashtag')

    @staticmethod
    def tag_plus_icon() -> QIcon:
        return IconRegistry.from_name('mdi.tag-plus')

    @staticmethod
    def tags_icon() -> QIcon:
        return qtawesome.icon('ei.tags')

    @staticmethod
    def graph_icon() -> QIcon:
        return qtawesome.icon('ei.graph')

    @staticmethod
    def wip_icon() -> QIcon:
        return IconRegistry.from_name('mdi.progress-question')

    @staticmethod
    def tasks_icon() -> QIcon:
        return qtawesome.icon('fa5s.tasks')

    @staticmethod
    def timeline_icon() -> QIcon:
        return qtawesome.icon('mdi.chart-timeline-variant', color_on='darkBlue')

    @staticmethod
    def reports_icon() -> QIcon:
        return qtawesome.icon('fa5.chart-bar', color_on='darkBlue')

    @staticmethod
    def notes_icon() -> QIcon:
        return qtawesome.icon('mdi.notebook', color_on='darkBlue')

    @staticmethod
    def document_edition_icon(color: str = 'black', color_on='darkBlue') -> QIcon:
        return qtawesome.icon('ei.file-edit', color=color, color_on=color_on)

    @staticmethod
    def act_one_icon() -> QIcon:
        return IconRegistry.from_name('mdi.numeric-1-circle', color=ACT_ONE_COLOR)

    @staticmethod
    def act_two_icon() -> QIcon:
        return IconRegistry.from_name('mdi.numeric-2-circle', color=ACT_TWO_COLOR)

    @staticmethod
    def act_three_icon() -> QIcon:
        return IconRegistry.from_name('mdi.numeric-3-circle', color=ACT_THREE_COLOR)

    @staticmethod
    def table_icon() -> QIcon:
        return qtawesome.icon('fa5.list-alt')

    @staticmethod
    def goal_icon() -> QIcon:
        return IconRegistry.from_name('mdi.target', color='darkBlue')

    @staticmethod
    def decision_icon(color: str = '#3cdbd3', color_on='darkBlue') -> QIcon:
        return IconRegistry.from_name('fa5.lightbulb', color=color, color_on=color_on)

    @staticmethod
    def reaction_icon() -> QIcon:
        return qtawesome.icon('fa5s.shield-alt')

    @staticmethod
    def disaster_icon(color: str = '#f4442e', color_on: str = '#f4442e') -> QIcon:
        return qtawesome.icon('fa5s.bomb', color=color, color_on=color_on)

    @staticmethod
    def dilemma_icon() -> QIcon:
        return qtawesome.icon('fa5s.question-circle')

    @staticmethod
    def conflict_icon(color: str = '#f3a712') -> QIcon:
        return IconRegistry.from_name('mdi.sword-cross', color=color)

    @staticmethod
    def success_icon(color: str = '#6ba368', color_on: str = '#6ba368') -> QIcon:
        return qtawesome.icon('fa5s.trophy', color=color, color_on=color_on)

    @staticmethod
    def tradeoff_icon(color: str = '#832161', color_on: str = '#832161') -> QIcon:
        return qtawesome.icon('fa5s.balance-scale-left', color=color, color_on=color_on)

    @staticmethod
    def home_icon() -> QIcon:
        return qtawesome.icon('fa5s.home', color_on='darkBlue')

    @staticmethod
    def trash_can_icon(color: str = 'red') -> QIcon:
        return qtawesome.icon('fa5s.trash-alt', color=color)

    @staticmethod
    def arrow_right_thick_icon() -> QIcon:
        return qtawesome.icon('ei.arrow-right')

    @staticmethod
    def arrow_left_thick_icon() -> QIcon:
        return qtawesome.icon('ei.arrow-left')

    @staticmethod
    def return_icon() -> QIcon:
        return qtawesome.icon('ei.return-key')

    @staticmethod
    def eye_open_icon() -> QIcon:
        return qtawesome.icon('fa5.eye')

    @staticmethod
    def eye_closed_icon() -> QIcon:
        return qtawesome.icon('fa5.eye-slash')

    @staticmethod
    def emotion_icon_from_feeling(feeling: int) -> QIcon:
        if feeling == VERY_UNHAPPY:
            return qtawesome.icon('fa5s.sad-cry', color='red')
        if feeling == UNHAPPY:
            return qtawesome.icon('mdi.emoticon-sad', color='orange')
        if feeling == HAPPY:
            return qtawesome.icon('fa5s.smile', color='lightgreen')
        if feeling == VERY_HAPPY:
            return qtawesome.icon('fa5s.smile-beam', color='darkgreen')

        return qtawesome.icon('mdi.emoticon-neutral', color='grey')

    @staticmethod
    def upload_icon() -> QIcon:
        return qtawesome.icon('fa5s.file-upload')

    @staticmethod
    def portrait_icon() -> QIcon:
        return qtawesome.icon('fa5s.portrait')

    @staticmethod
    def progress_check_icon() -> QIcon:
        return IconRegistry.from_name('mdi.progress-check', color='darkblue')

    @staticmethod
    def customization_icon() -> QIcon:
        return qtawesome.icon('fa5s.sliders-h')

    @staticmethod
    def restore_alert_icon(color='black') -> QIcon:
        return IconRegistry.from_name('mdi.restore-alert', color=color)

    @staticmethod
    def cards_icon() -> QIcon:
        return IconRegistry.from_name('mdi.cards')

    @staticmethod
    def conflict_type_icon(type: ConflictType) -> QIcon:
        if type == ConflictType.CHARACTER:
            return IconRegistry.conflict_character_icon()
        elif type == ConflictType.SOCIETY:
            return IconRegistry.conflict_society_icon()
        elif type == ConflictType.NATURE:
            return IconRegistry.conflict_nature_icon()
        elif type == ConflictType.TECHNOLOGY:
            return IconRegistry.conflict_technology_icon()
        elif type == ConflictType.SUPERNATURAL:
            return IconRegistry.conflict_supernatural_icon()
        elif type == ConflictType.SELF:
            return IconRegistry.conflict_self_icon()

    @staticmethod
    def conflict_character_icon() -> QIcon:
        return IconRegistry.character_icon(color='#c1666b', color_on='#c1666b')

    @staticmethod
    def conflict_society_icon() -> QIcon:
        return IconRegistry.from_name('ei.group-alt', color='#69306d')

    @staticmethod
    def conflict_nature_icon() -> QIcon:
        return IconRegistry.from_name('mdi.weather-hurricane', color='#157a6e')

    @staticmethod
    def conflict_technology_icon() -> QIcon:
        return IconRegistry.from_name('ei.cogs', color='#4a5859')

    @staticmethod
    def conflict_supernatural_icon() -> QIcon:
        return IconRegistry.from_name('mdi.creation', color='#ac7b84')

    @staticmethod
    def conflict_self_icon() -> QIcon:
        return IconRegistry.from_name('mdi.mirror', color='#94b0da')

    @staticmethod
    def baby_icon() -> QIcon:
        return IconRegistry.from_name('fa5s.baby')

    @staticmethod
    def child_icon() -> QIcon:
        return IconRegistry.from_name('fa5s.child')

    @staticmethod
    def teenager_icon() -> QIcon:
        return IconRegistry.from_name('mdi.human')

    @staticmethod
    def adult_icon() -> QIcon:
        return IconRegistry.from_name('ei.adult')

    @staticmethod
    def cog_icon() -> QIcon:
        return IconRegistry.from_name('fa5s.cog')

    @staticmethod
    def cause_icon(color: str = 'black') -> QIcon:
        return IconRegistry.from_name('mdi.ray-start', color=color)

    @staticmethod
    def cause_and_effect_icon() -> QIcon:
        return IconRegistry.from_name('mdi.ray-start-arrow')

    @staticmethod
    def reversed_cause_and_effect_icon() -> QIcon:
        return IconRegistry.from_name('mdi.ray-end-arrow')

    @staticmethod
    def toggle_on_icon() -> QIcon:
        return IconRegistry.from_name('fa5s.toggle-on')

    @staticmethod
    def toggle_off_icon() -> QIcon:
        return IconRegistry.from_name('fa5s.toggle-off')

    @staticmethod
    def heading_1_icon() -> QIcon:
        return IconRegistry.from_name('mdi.format-header-1', mdi_scale=1.4)

    @staticmethod
    def heading_2_icon() -> QIcon:
        return IconRegistry.from_name('mdi.format-header-2')

    @staticmethod
    def dots_icon(color: str = 'black') -> QIcon:
        return IconRegistry.from_name('mdi.dots-horizontal', color)

    @staticmethod
    def icons_icon(color: str = 'black') -> QIcon:
        return IconRegistry.from_name('fa5s.icons', color)

    @staticmethod
    def heading_3_icon() -> QIcon:
        return IconRegistry.from_name('mdi.format-header-3', mdi_scale=1)

    @staticmethod
    def template_icon() -> QIcon:
        return IconRegistry.from_name('ei.magic', color='#35a7ff')

    @staticmethod
    def circle_icon() -> QIcon:
        return IconRegistry.from_name('mdi.circle-medium')

    @staticmethod
    def inciting_incident_icon() -> QIcon:
        return IconRegistry.from_name('mdi.bell-alert-outline', '#a2ad59')

    @staticmethod
    def rising_action_icon() -> QIcon:
        return IconRegistry.from_name('fa5s.chart-line', '#08605f')

    @staticmethod
    def crisis_icon() -> QIcon:
        return IconRegistry.from_name('mdi.arrow-decision-outline', '#ce2d4f')

    @staticmethod
    def tickling_clock_icon() -> QIcon:
        return IconRegistry.from_name('mdi.clock-alert-outline', '#f7cb15')

    @staticmethod
    def timer_icon() -> QIcon:
        return IconRegistry.from_name('mdi.timer-outline')

    @staticmethod
    def pause_icon() -> QIcon:
        return IconRegistry.from_name('fa5s.pause', '#3f37c9')

    @staticmethod
    def play_icon() -> QIcon:
        return IconRegistry.from_name('fa5s.play', '#2a9d8f')

    @staticmethod
    def from_name(name: str, color: str = 'black', color_on: str = '', mdi_scale: float = 1.2) -> QIcon:
        _color_on = color_on if color_on else color
        if name.startswith('md'):
            return QIcon(qtawesome.icon(name, color=color, color_on=_color_on, options=[{'scale_factor': mdi_scale}]))
        return QIcon(qtawesome.icon(name, color=color, color_on=_color_on))


class AvatarsRegistry:
    def __init__(self):
        self._avatars: Dict[str, QPixmap] = {}

    def pixmap(self, character: Character) -> QPixmap:
        if str(character.id) not in self._avatars:
            if character.avatar:
                array = character.avatar
                pixmap = QPixmap()
                if array:
                    pixmap.loadFromData(array)
                self._avatars[str(character.id)] = rounded_pixmap(pixmap)
            else:
                icon = self.name_initial_icon(character)
                self._avatars[str(character.id)] = icon.pixmap(QSize(64, 64))

        return self._avatars[str(character.id)]

    def name_initial_icon(self, character: Character) -> QIcon:
        _sum = sum([ord(x) for x in character.name])
        color = CHARACTER_INITIAL_AVATAR_COLOR_CODES[_sum % len(CHARACTER_INITIAL_AVATAR_COLOR_CODES)]

        if character.name[0].isnumeric():
            icon = f'mdi.numeric-{int(character.name[0])}-circle-outline'
        else:
            icon = f'mdi.alpha-{character.name[0].lower()}-circle-outline'

        return qtawesome.icon(icon, options=[{'scale_factor': 1.2}], color=color)

    def update(self, character: Character):
        if str(character.id) in self._avatars.keys():
            self._avatars.pop(str(character.id))
        self.pixmap(character)


avatars = AvatarsRegistry()


def set_avatar(label: QLabel, character: Character, size: int = 128):
    if character.avatar:
        label.setPixmap(
            avatars.pixmap(character).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation))
    elif character.name:
        label.setPixmap(avatars.name_initial_icon(character).pixmap(QSize(size, size)))
    else:
        label.setPixmap(IconRegistry.portrait_icon().pixmap(QSize(size, size)))
