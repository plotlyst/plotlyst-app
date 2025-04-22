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
import math
from dataclasses import dataclass
from functools import partial
from typing import List, Dict

from PyQt6.QtCharts import QChart, QPieSeries, QBarSet, QBarCategoryAxis, QValueAxis, QBarSeries, QPolarChart, \
    QPieSlice, QCategoryAxis, QLineSeries, QAreaSeries
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QCursor, QIcon, QFont, QPen
from PyQt6.QtWidgets import QToolTip, QApplication
from overrides import overrides

from plotlyst.common import CHARACTER_MAJOR_COLOR, \
    CHARACTER_SECONDARY_COLOR, CHARACTER_MINOR_COLOR, RELAXED_WHITE_COLOR, PLOTLYST_TERTIARY_COLOR, \
    PLOTLYST_SECONDARY_COLOR, act_color
from plotlyst.core.domain import Character, MALE, FEMALE, TRANSGENDER, NON_BINARY, GENDERLESS, Novel
from plotlyst.core.template import enneagram_choices, supporter_role, guide_role, sidekick_role, \
    antagonist_role, contagonist_role, adversary_role, henchmen_role, confidant_role, tertiary_role, SelectionItem, \
    secondary_role
from plotlyst.service.cache import acts_registry
from plotlyst.view.common import icon_to_html_img
from plotlyst.view.icons import IconRegistry


class _AbstractChart:

    def __init__(self, _=None):
        self.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.setAnimationDuration(500)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.legend().hide()
        self.setBackgroundRoundness(0)

    def reset(self):
        if self.series():
            self.removeAllSeries()


class BaseChart(QChart, _AbstractChart):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QColor(RELAXED_WHITE_COLOR))

    @overrides
    def reset(self):
        super(BaseChart, self).reset()
        h_axis = self.axes(Qt.Orientation.Horizontal)
        if h_axis:
            self.removeAxis(h_axis[0])
        y_axis = self.axes(Qt.Orientation.Vertical)
        if y_axis:
            self.removeAxis(y_axis[0])


class PolarBaseChart(QPolarChart, _AbstractChart):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QColor(RELAXED_WHITE_COLOR))

    @overrides
    def reset(self):
        super(PolarBaseChart, self).reset()
        p_axis = self.axes(QPolarChart.PolarOrientation.PolarOrientationAngular)
        if p_axis:
            for ax in p_axis:
                self.removeAxis(ax)
        a_axis = self.axes(QPolarChart.PolarOrientation.PolarOrientationAngular)
        if a_axis:
            for ax in a_axis:
                self.removeAxis(ax)


@dataclass
class ChartItem:
    value: int
    text: str = ''
    description: str = ''
    icon: str = ''
    color: str = ''
    icon_color: str = 'black'


class PieChart(BaseChart):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._holeSize: float = 0.45

    def setHoleSize(self, size: float):
        self._holeSize = size

    def setItems(self, items: List[ChartItem]):
        series = QPieSeries()
        series.setHoleSize(self._holeSize)

        for item in items:
            slice_ = series.append(item.text, item.value)
            slice_.setLabelVisible()
            if item.icon:
                slice_.setLabel(icon_to_html_img(IconRegistry.from_name(item.icon, item.icon_color)))

            slice_.setLabelArmLengthFactor(0.2)
            if item.color:
                slice_.setColor(QColor(item.color))
            # slice_.hovered.connect(partial(self._hovered, item))

        if self.series():
            self.removeAllSeries()
        self.addSeries(series)


class PolarChart(PolarBaseChart):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._logarithmicScale: bool = False
        self._rad_axis = QValueAxis()
        self._rad_axis.setLabelsVisible(False)
        self._angular_axis = QCategoryAxis()

    def setAngularRange(self, min: int, max: int):
        self._angular_axis.setRange(min, max)

    # def setAngularLabels(self, labels: List[Tuple[str, float]]):
    #     for label in labels:
    #         self._angular_axis.append(f'{icon_to_html_img(IconRegistry.character_icon())}{label[0]}', label[1])

    def setLogarithmicScaleEnabled(self, enabled: bool):
        self._logarithmicScale = enabled

    def setItems(self, items: List[ChartItem]):
        self.reset()

        self.addAxis(self._rad_axis, QPolarChart.PolarOrientation.PolarOrientationRadial)
        self.addAxis(self._angular_axis, QPolarChart.PolarOrientation.PolarOrientationAngular)

        pen = QPen()
        pen.setWidth(2)
        pen.setColor(QColor(PLOTLYST_SECONDARY_COLOR))

        upper_series = QLineSeries()
        upper_series.setPen(pen)
        lower_series = QLineSeries()
        lower_series.setPen(pen)

        for i, item in enumerate(items):
            if item.icon:
                self._angular_axis.append(f'{icon_to_html_img(IconRegistry.from_name(item.icon))}{item.text}', i + 1)
            else:
                self._angular_axis.append(item.text, i + 1)

            value = math.log1p(item.value) if self._logarithmicScale else item.value
            # upper_series.append(i, value / 3)
            upper_series.append(i + 0.5, value)
            # if item.value > 1:
            #     upper_series.append(i + 1, value / 3)
            lower_series.append(i, 0.0)

        self.addSeries(upper_series)
        self.addSeries(lower_series)

        series = QAreaSeries(upper_series, lower_series)
        series.setColor(QColor(PLOTLYST_SECONDARY_COLOR))
        series.setPen(pen)

        self.addSeries(series)
        series.attachAxis(self._rad_axis)
        series.attachAxis(self._angular_axis)


class GenderCharacterChart(BaseChart):

    def __init__(self, parent=None):
        super(GenderCharacterChart, self).__init__(parent)
        self._labelsVisible: bool = True

    def setLabelsVisible(self, visible: bool):
        self._labelsVisible = visible

    def refresh(self, characters: List[Character]):
        series = QPieSeries()
        series.setHoleSize(0.45)

        genders: Dict[str, int] = {}
        for char in characters:
            if not char.gender:
                continue
            if char.gender not in genders.keys():
                genders[char.gender] = 0
            genders[char.gender] = genders[char.gender] + 1

        for k, v in genders.items():
            if v:
                slice_ = series.append(k, v)
                slice_.setLabelVisible(self._labelsVisible)
                slice_.setLabel(icon_to_html_img(self._iconForGender(k)))
                slice_.setLabelArmLengthFactor(0.2)
                slice_.hovered.connect(partial(self._hovered, k))
                slice_.setColor(QColor(self._colorForGender(k)))

        if self.series():
            self.removeAllSeries()
        self.addSeries(series)

    def _hovered(self, gender: str, state: bool):
        if state:
            QToolTip.showText(QCursor.pos(),
                              f'<b style="color: {self._colorForGender(gender)}">{gender.capitalize()}</b>')
        else:
            QToolTip.hideText()

    def _iconForGender(self, gender: str) -> QIcon:
        if gender == MALE:
            return IconRegistry.male_gender_icon(self._colorForGender(gender))
        elif gender == FEMALE:
            return IconRegistry.female_gender_icon(self._colorForGender(gender))
        elif gender == TRANSGENDER:
            return IconRegistry.transgender_icon(self._colorForGender(gender))
        elif gender == NON_BINARY:
            return IconRegistry.non_binary_gender_icon(self._colorForGender(gender))
        elif gender == GENDERLESS:
            return IconRegistry.genderless_icon(self._colorForGender(gender))
        else:
            IconRegistry.empty_icon()

    def _colorForGender(self, gender: str) -> str:
        if gender == MALE:
            return '#067bc2'
        elif gender == FEMALE:
            return '#832161'
        elif gender == TRANSGENDER:
            return '#f4a261'
        elif gender == NON_BINARY:
            return '#7209b7'
        elif gender == GENDERLESS:
            return '#6c757d'
        else:
            return 'black'


class RoleChart(BaseChart):
    def __init__(self, parent=None):
        super(RoleChart, self).__init__(parent)
        self.setTitle('<b>Importance</b>')

    def refresh(self, characters: List[Character]):
        self.reset()
        series = QPieSeries()
        series.setHoleSize(0.45)
        major = 0
        secondary = 0
        minor = 0
        for char in characters:
            if not char.role:
                continue
            if char.is_major():
                major += 1
            elif char.is_secondary():
                secondary += 1
            elif char.is_minor():
                minor += 1

        if major:
            self._addSlice(series, major, IconRegistry.major_character_icon(), CHARACTER_MAJOR_COLOR,
                           'Major characters')
        if secondary:
            self._addSlice(series, secondary, IconRegistry.secondary_character_icon(), CHARACTER_SECONDARY_COLOR,
                           'Secondary characters')
        if minor:
            self._addSlice(series, minor, IconRegistry.minor_character_icon(), CHARACTER_MINOR_COLOR,
                           'Minor characters')

        for slice_ in series.slices():
            slice_.setLabelVisible()
            slice_.setLabelArmLengthFactor(0.2)

        self.addSeries(series)

    def _addSlice(self, series: QPieSeries, value: int, icon: QIcon, color: str, tooltip: str):
        slice_ = series.append(
            icon_to_html_img(icon), value)
        slice_.setColor(QColor(color))
        slice_.hovered.connect(partial(self._hovered, color, tooltip))

    def _hovered(self, color: str, tooltip: str, state: bool):
        if state:
            QToolTip.showText(QCursor.pos(), f'<b style="color: {color}">{tooltip.capitalize()}</b>')
        else:
            QToolTip.hideText()


class SupporterRoleChart(BaseChart):

    def __init__(self, parent=None):
        super(SupporterRoleChart, self).__init__(parent)
        self.setTitle('<b>Supporter vs adversary</b>')

    def refresh(self, characters: List[Character]):
        series = QPieSeries()
        series.setHoleSize(0.45)

        supporter = 0
        adversary = 0
        secondary = 0
        tertiary = 0
        for char in characters:
            if not char.role:
                continue
            if char.role in [supporter_role, guide_role, sidekick_role, confidant_role]:
                supporter += 1
            elif char.role in [antagonist_role, contagonist_role, adversary_role, henchmen_role]:
                adversary += 1
            elif char.role is tertiary_role:
                tertiary += 1
            else:
                secondary += 1
        if supporter:
            self._addSlice(series, supporter_role, supporter)
        if adversary:
            self._addSlice(series, adversary_role, adversary)
        if tertiary:
            self._addSlice(series, tertiary_role, tertiary)
        if secondary:
            self._addSlice(series, secondary_role, secondary)

        for slice_ in series.slices():
            slice_.setLabelVisible()
            slice_.setLabelArmLengthFactor(0.2)

        if self.series():
            self.removeAllSeries()
        self.addSeries(series)

    def _addSlice(self, series: QPieSeries, role: SelectionItem, value: int):
        slice_ = series.append(
            icon_to_html_img(IconRegistry.from_name(role.icon, role.icon_color)), value)
        slice_.setColor(QColor(role.icon_color))
        slice_.hovered.connect(partial(self._hovered, role))

    def _hovered(self, role: SelectionItem, state: bool):
        if state:
            QToolTip.showText(QCursor.pos(), f'<b style="color: {role.icon_color}">{role.text.capitalize()}</b>')
        else:
            QToolTip.hideText()


class EnneagramChart(BaseChart):

    def __init__(self, parent=None):
        super(EnneagramChart, self).__init__(parent)
        self.setTitle('<b>Enneagram</b>')

    def refresh(self, characters: List[Character]):
        series = QPieSeries()
        series.setHoleSize(0.45)

        enneagrams: Dict[str, int] = {}
        for char in characters:
            enneagram = char.enneagram()
            if not enneagram:
                continue
            if enneagram.text not in enneagrams.keys():
                enneagrams[enneagram.text] = 0
            enneagrams[enneagram.text] = enneagrams[enneagram.text] + 1

        for k, v in enneagrams.items():
            slice_ = series.append(k, v)
            slice_.setLabelVisible()
            item = enneagram_choices[k]
            slice_.setLabel(icon_to_html_img(IconRegistry.from_name(item.icon, item.icon_color)))
            slice_.setLabelArmLengthFactor(0.2)
            slice_.setColor(QColor(item.icon_color))
            slice_.hovered.connect(partial(self._hovered, item))

        if self.series():
            self.removeAllSeries()
        self.addSeries(series)

    def _hovered(self, enneagram: SelectionItem, state: bool):
        if state:
            QToolTip.showText(QCursor.pos(),
                              f'<b style="color: {enneagram.icon_color}">{enneagram.text.capitalize()}</b>')
        else:
            QToolTip.hideText()


class ManuscriptLengthChart(BaseChart):
    def __init__(self, parent=None):
        super(ManuscriptLengthChart, self).__init__(parent)
        self._byScenes: bool = False

    def setDisplayByScenes(self, display: bool):
        self._byScenes = display

    def refresh(self, novel: Novel):
        self.reset()
        unit = "scenes" if self._byScenes and novel.prefs.is_scenes_organization() else "chapters"
        self.setTitle(f'<b>Manuscript length per {unit}</b>')

        self.setMinimumWidth(max(len(self._xData(novel)), 15) * 35)
        if self._byScenes:
            set_ = QBarSet('Scene')
            set_.hovered.connect(self._hovered)
            for scene in novel.scenes:
                scene_wc = 0
                if scene.manuscript and scene.manuscript.statistics:
                    scene_wc += scene.manuscript.statistics.wc
                set_.append(scene_wc)
        else:
            set_ = QBarSet('Chapter')
            set_.hovered.connect(self._hovered)
            for i, chapter in enumerate(novel.chapters):
                chapter_wc = 0
                for scene in novel.scenes_in_chapter(chapter):
                    if scene.manuscript and scene.manuscript.statistics:
                        chapter_wc += scene.manuscript.statistics.wc
                set_.append(chapter_wc)

        set_.setColor(QColor(PLOTLYST_SECONDARY_COLOR))

        series = QBarSeries()
        series.append(set_)
        if len(self._xData(novel)) < 5:
            series.setBarWidth(0.1)

        axis_x = QBarCategoryAxis()
        axis_x_values = [*range(1, len(self._xData(novel)) + 1)]
        axis_x_values = [str(x) for x in axis_x_values]
        axis_x.append(axis_x_values)
        self.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.0f")
        self.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

        self.addSeries(series)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

    def _xData(self, novel: Novel):
        if self._byScenes:
            return novel.scenes
        else:
            return novel.chapters

    def _hovered(self, status: bool, index: int):
        if status:
            barset: QBarSet = self.series()[0].barSets()[0]
            QToolTip.showText(QCursor.pos(), f' Word count: {int(barset.at(index))}')
        else:
            QToolTip.hideText()


class ActDistributionChart(BaseChart):

    def __init__(self, parent=None):
        super(ActDistributionChart, self).__init__(parent)
        self.legend().setVisible(True)
        self.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)

    def refresh(self, novel: Novel):
        self.reset()

        series = QPieSeries()
        series.setHoleSize(0.45)

        act_number = novel.active_story_structure.acts
        if act_number > 0:
            self._visualizeActs(novel, series)
        else:
            self._visualizeHalves(novel, series)

        self.addSeries(series)

    def _visualizeActs(self, novel: Novel, series: QPieSeries):
        self.setTitle('<b>Act distribution</b>')

        structure = novel.active_story_structure
        acts: Dict[int, int] = {}
        for scene in novel.scenes:
            act = acts_registry.act(scene)
            if act not in acts.keys():
                acts[act] = 0
            acts[act] = acts[act] + 1
        for k, v in acts.items():
            slice_ = series.append(structure.acts_text.get(k, f'Act {k}'), v)
            color = act_color(k, structure.acts)
            slice_.setColor(QColor(color))

    def _visualizeHalves(self, novel: Novel, series: QPieSeries):
        self.setTitle('<b>Scenes distribution</b>')
        first_half: int = 0
        second_half: int = 0
        in_second_half = False
        for scene in novel.scenes:
            if in_second_half:
                second_half += 1
            else:
                beat = scene.beat(novel)
                if beat and beat.percentage > 50:
                    in_second_half = True
                    second_half += 1
                else:
                    first_half += 1

        slice_ = series.append('First half', first_half)
        slice_.setColor(QColor(PLOTLYST_TERTIARY_COLOR))
        slice_ = series.append('Second half', second_half)
        slice_.setColor(QColor(PLOTLYST_SECONDARY_COLOR))


class SelectionItemPieSlice(QPieSlice):
    def __init__(self, item: SelectionItem, bgColor: str, parent=None,
                 labelPosition=QPieSlice.LabelPosition.LabelInsideNormal):
        super().__init__(parent)
        self.item = item
        self._bgColor = bgColor

        self.setLabelVisible()
        self.setLabel(self.item.text)
        font = QApplication.font()
        font.setPointSize(14)
        self.setLabelFont(font)
        self.setLabel(item.text)
        self.setLabelColor(QColor('grey'))
        self.setLabelPosition(labelPosition)
        self.setColor(QColor(self._bgColor))

    def highlight(self):
        self.setExplodeDistanceFactor(0.05)
        self.setColor(QColor(self.item.icon_color))
        color = QColor(RELAXED_WHITE_COLOR)
        color.setAlpha(205)
        self.setLabelColor(color)
        self.setExploded(True)

    def select(self):
        self.setExplodeDistanceFactor(0.2)
        font: QFont = self.labelFont()
        font.setBold(True)
        self.setLabelFont(font)

    def reset(self):
        self.setColor(QColor(self._bgColor))
        self.setExploded(False)
        self.setLabelColor(QColor('grey'))
        font = self.labelFont()
        font.setBold(False)
        self.setLabelFont(font)
