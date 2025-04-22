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

from enum import Enum
from functools import partial
from typing import Dict, Optional
from typing import List

from PyQt6.QtCore import QPoint, QTimeLine
from PyQt6.QtCore import Qt, QEvent, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPaintEvent, QPainter, \
    QPen, QPainterPath, QShowEvent
from PyQt6.QtWidgets import QSizePolicy, QWidget
from overrides import overrides
from qthandy import busy, margins
from qthandy import decr_font, transparent, clear_layout, hbox, spacer, vbox
from qtmenu import MenuWidget

from plotlyst.common import RELAXED_WHITE_COLOR, PLOTLYST_TERTIARY_COLOR, PLOTLYST_SECONDARY_COLOR
from plotlyst.common import truncate_string
from plotlyst.core.domain import Scene, Novel, Plot
from plotlyst.event.core import Event, EventListener, emit_event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import SceneOrderChangedEvent, SceneChangedEvent
from plotlyst.service.cache import acts_registry
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import action
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.button import WordWrappedPushButton


class StoryMapDisplayMode(Enum):
    DOTS = 0
    TITLE = 1
    DETAILED = 2


class StoryLinesMapWidget(QWidget):
    sceneSelected = pyqtSignal(Scene)

    def __init__(self, mode: StoryMapDisplayMode, acts_filter: Dict[int, bool], parent=None):
        super().__init__(parent=parent)
        hbox(self)
        self.setMouseTracking(True)
        self.novel: Optional[Novel] = None
        self._scene_coord_y: Dict[int, int] = {}
        self._clicked_scene: Optional[Scene] = None
        self._display_mode: StoryMapDisplayMode = mode
        self._acts_filter = acts_filter

        if mode == StoryMapDisplayMode.DOTS:
            self._scene_width = 25
            self._top_height = 50
        else:
            self._scene_width = 120
            self._top_height = 50
        self._line_height = 50
        self._first_paint_triggered: bool = False

        self._menuPlots = MenuWidget()

    def setNovel(self, novel: Novel, animated: bool = True):
        def changed(x: int):
            self._first_paint_triggered = True
            self.update(0, 0, x, self.minimumSizeHint().height())

        self.novel = novel
        if animated:
            timeline = QTimeLine(700, parent=self)
            timeline.setFrameRange(0, self.minimumSizeHint().width())
            timeline.frameChanged.connect(changed)

            timeline.start()
        else:
            self._first_paint_triggered = True

    def scenes(self) -> List[Scene]:
        return [x for x in self.novel.scenes if self._acts_filter.get(acts_registry.act(x), True)]

    @overrides
    def minimumSizeHint(self) -> QSize:
        if self.novel:
            x = self._scene_x(len(self.scenes()) - 1) + 50
            y = self._story_line_y(len(self.novel.plots)) * 2
            return QSize(x, y)
        return super().minimumSizeHint()

    @overrides
    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ToolTip:
            index = self._index_from_pos(event.pos())
            scenes = self.scenes()
            if index < len(scenes):
                self.setToolTip(scenes[index].title_or_index(self.novel))

            return super().event(event)
        return super().event(event)

    @overrides
    def mousePressEvent(self, event: QMouseEvent) -> None:
        index = self._index_from_pos(event.pos())
        scenes = self.scenes()
        if index < len(scenes):
            self._clicked_scene: Scene = scenes[index]
            self.sceneSelected.emit(self._clicked_scene)
            self._context_menu_requested(event.pos())
            self.update()

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(RELAXED_WHITE_COLOR))

        if not self._first_paint_triggered:
            painter.end()
            return

        scenes = self.scenes()

        self._scene_coord_y.clear()
        y = 0
        last_sc_x: Dict[int, int] = {}
        for sl_i, plot in enumerate(self.novel.plots):
            previous_y = 0
            previous_x = 0
            y = self._story_line_y(sl_i)
            path = QPainterPath()
            painter.setPen(QPen(QColor(plot.icon_color), 4, Qt.PenStyle.SolidLine))
            path.moveTo(0, y)
            IconRegistry.from_name(plot.icon, plot.icon_color).paint(painter, 0, y - 35, 24, 24)
            path.lineTo(5, y)
            painter.drawPath(path)

            for sc_i, scene in enumerate(scenes):
                x = self._scene_x(sc_i)
                if plot in scene.plots():
                    if sc_i not in self._scene_coord_y.keys():
                        self._scene_coord_y[sc_i] = y
                    if previous_y > self._scene_coord_y[sc_i] or (previous_y == 0 and y > self._scene_coord_y[sc_i]):
                        path.lineTo(x - self._scene_width // 2, y)
                    elif 0 < previous_y < self._scene_coord_y[sc_i]:
                        path.lineTo(previous_x + self._scene_width // 2, y)

                    if previous_y == self._scene_coord_y[sc_i] and previous_y != y:
                        path.arcTo(previous_x + 4, self._scene_coord_y[sc_i] - 3, x - previous_x,
                                   self._scene_coord_y[sc_i] - 25,
                                   -180, 180)
                    else:
                        path.lineTo(x, self._scene_coord_y[sc_i])

                    painter.drawPath(path)
                    previous_y = self._scene_coord_y[sc_i]
                    previous_x = x
                    last_sc_x[sl_i] = x

        for sc_i, scene in enumerate(scenes):
            if sc_i not in self._scene_coord_y.keys():
                continue
            self._draw_scene_ellipse(painter, scene, self._scene_x(sc_i), self._scene_coord_y[sc_i])

        for sc_i, scene in enumerate(scenes):
            if not scene.plots():
                self._draw_scene_ellipse(painter, scene, self._scene_x(sc_i), 3)

        if len(self.novel.plots) <= 1:
            return

        base_y = y
        for sl_i, plot in enumerate(self.novel.plots):
            y = 50 * (sl_i + 1) + 25 + base_y
            painter.setPen(QPen(QColor(plot.icon_color), 4, Qt.PenStyle.SolidLine))
            painter.drawLine(0, y, last_sc_x.get(sl_i, 15), y)
            painter.setPen(QPen(Qt.GlobalColor.black, 5, Qt.PenStyle.SolidLine))
            painter.drawPixmap(0, y - 35, IconRegistry.from_name(plot.icon, plot.icon_color).pixmap(24, 24))
            painter.drawText(26, y - 15, plot.text)

            for sc_i, scene in enumerate(scenes):
                if plot in scene.plots():
                    self._draw_scene_ellipse(painter, scene, self._scene_x(sc_i), y)

        painter.end()

    def _draw_scene_ellipse(self, painter: QPainter, scene: Scene, x: int, y: int):
        selected = scene is self._clicked_scene
        if scene.plot_values:
            pen_color = PLOTLYST_TERTIARY_COLOR if selected else Qt.GlobalColor.black
            if len(scene.plot_values) == 1:
                painter.setPen(QPen(QColor(pen_color), 3, Qt.PenStyle.SolidLine))
                painter.setBrush(Qt.GlobalColor.black)
                size = 22 if selected else 14
                x_diff = 4 if selected else 0
                painter.drawEllipse(x - x_diff, y - size // 2, size, size)
            else:
                painter.setPen(QPen(QColor(pen_color), 3, Qt.PenStyle.SolidLine))
                painter.setBrush(Qt.GlobalColor.white)
                painter.drawEllipse(x, y - 10, 20, 20)
        else:
            pen_color = PLOTLYST_SECONDARY_COLOR if scene is self._clicked_scene else Qt.GlobalColor.gray
            painter.setPen(QPen(QColor(pen_color), 3, Qt.PenStyle.SolidLine))
            painter.setBrush(Qt.GlobalColor.gray)
            size = 18 if selected else 14
            x_diff = 2 if selected else 0
            painter.drawEllipse(x - x_diff, y, size, size)

    def _story_line_y(self, index: int) -> int:
        return self._top_height + self._line_height * (index)

    def _scene_x(self, index: int) -> int:
        return self._scene_width * (index + 1)

    def _index_from_pos(self, pos: QPoint) -> int:
        return int((pos.x() / self._scene_width) - 1)

    def _context_menu_requested(self, pos: QPoint) -> None:
        index = self._index_from_pos(pos)
        scenes = self.scenes()
        if index < len(scenes):
            self._clicked_scene: Scene = scenes[index]
            self.update()

            self._menuPlots.clear()
            if self.novel.plots:
                for plot in self.novel.plots:
                    plot_action = action(truncate_string(plot.text, 70),
                                         IconRegistry.from_name(plot.icon, plot.icon_color),
                                         slot=partial(self._plot_changed, plot))
                    self._menuPlots.addAction(plot_action)
                    plot_action.setCheckable(True)
                    if plot in self._clicked_scene.plots():
                        plot_action.setChecked(True)
            else:
                self._menuPlots.addSection('No storylines were found')
            self._menuPlots.exec(self.mapToGlobal(pos))

    @busy
    def _plot_changed(self, plot: Plot, checked: bool):
        if checked:
            self._clicked_scene.link_plot(plot)
        else:
            self._clicked_scene.unlink_plot(plot)
        RepositoryPersistenceManager.instance().update_scene(self._clicked_scene)

        self.update()
        emit_event(self.novel, SceneChangedEvent(self, self._clicked_scene))


class StoryMap(QWidget, EventListener):
    sceneSelected = pyqtSignal(Scene)

    def __init__(self, parent=None):
        super(StoryMap, self).__init__(parent)
        self.novel: Optional[Novel] = None
        self._display_mode: StoryMapDisplayMode = StoryMapDisplayMode.DOTS
        self._orientation: int = Qt.Orientation.Horizontal
        self._acts_filter: Dict[int, bool] = {}
        vbox(self, spacing=0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # apply to every QWidget inside
        self.setStyleSheet(f'QWidget {{background-color: {RELAXED_WHITE_COLOR};}}')

        self._refreshOnShow = False

    def setNovel(self, novel: Novel):
        self.novel = novel
        dispatcher = event_dispatchers.instance(self.novel)
        dispatcher.register(self, SceneOrderChangedEvent)
        self.refresh()

    @overrides
    def event_received(self, event: Event):
        if self.isVisible():
            self.refresh()
        else:
            self._refreshOnShow = True

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        if self._refreshOnShow:
            self._refreshOnShow = False
            self.refresh()

    def refresh(self, animated: bool = True):
        if not self.novel:
            return
        clear_layout(self)

        wdg = StoryLinesMapWidget(self._display_mode, self._acts_filter, parent=self)
        self.layout().addWidget(wdg)
        wdg.setNovel(self.novel, animated=animated)
        if self._display_mode == StoryMapDisplayMode.TITLE:
            titles = QWidget(self)
            titles.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
            titles.setProperty('relaxed-white-bg', True)
            hbox(titles, 0, 0)
            margins(titles, left=70)
            self.layout().insertWidget(0, titles)
            for scene in wdg.scenes():
                btn = WordWrappedPushButton(parent=self)
                btn.setFixedWidth(120)
                btn.setText(scene.title_or_index(self.novel))
                decr_font(btn.label, step=2)
                transparent(btn)
                titles.layout().addWidget(btn)
            titles.layout().addWidget(spacer())
        wdg.sceneSelected.connect(self.sceneSelected)

    @busy
    def setMode(self, mode: StoryMapDisplayMode):
        if self._display_mode == mode:
            return
        self._display_mode = mode
        if self.novel:
            self.refresh()

    @busy
    def setOrientation(self, orientation: int):
        self._orientation = orientation
        if self._display_mode != StoryMapDisplayMode.DETAILED:
            return
        if self.novel:
            self.refresh()

    def setActsFilter(self, act: int, filtered: bool):
        self._acts_filter[act] = filtered
        if self.novel:
            self.refresh(animated=False)

    def resetActsFilter(self):
        self._acts_filter.clear()
        if self.novel:
            self.refresh(animated=False)
