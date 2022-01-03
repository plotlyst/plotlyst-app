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
from functools import partial
from typing import Dict, Optional

from PyQt6.QtCore import Qt, QPoint, QEvent, pyqtSignal, QSize
from PyQt6.QtGui import QPaintEvent, QPainter, QPen, QPainterPath, QColor, QMouseEvent
from PyQt6.QtWidgets import QWidget
from overrides import overrides

from src.main.python.plotlyst.common import truncate_string
from src.main.python.plotlyst.core.domain import Scene, Novel, ScenePlotValue, Plot
from src.main.python.plotlyst.view.common import busy, PopupMenuBuilder
from src.main.python.plotlyst.worker.persistence import RepositoryPersistenceManager


class StoryLinesMapWidget(QWidget):
    scene_selected = pyqtSignal(Scene)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setMouseTracking(True)
        self.novel: Optional[Novel] = None
        self._scene_coord_y: Dict[int, int] = {}
        self._clicked_scene: Optional[Scene] = None

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu_requested)

    def setNovel(self, novel: Novel):
        self.novel = novel

    @overrides
    def minimumSizeHint(self) -> QSize:
        if self.novel:
            x = self._scene_x(len(self.novel.scenes) - 1) + 50
            y = self._story_line_y(len(self.novel.plots)) * 2
            return QSize(x, y)
        return super().minimumSizeHint()

    @overrides
    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ToolTip:
            index = self._index_from_pos(event.pos())
            if index < len(self.novel.scenes):
                self.setToolTip(self.novel.scenes[index].title)

            return super().event(event)
        return super().event(event)

    @overrides
    def mousePressEvent(self, event: QMouseEvent) -> None:
        index = self._index_from_pos(event.pos())
        if index < len(self.novel.scenes):
            self._clicked_scene: Scene = self.novel.scenes[index]
            self.update()

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), Qt.GlobalColor.white)
        self._scene_coord_y.clear()
        y = 0
        last_sc_x: Dict[int, int] = {}
        for sl_i, plot in enumerate(self.novel.plots):
            previous_y = 0
            previous_x = 0
            y = self._story_line_y(sl_i)
            path = QPainterPath()
            painter.setPen(QPen(QColor(plot.color_hexa), 4, Qt.PenStyle.SolidLine))
            path.moveTo(0, y)
            path.lineTo(5, y)

            for sc_i, scene in enumerate(self.novel.scenes):
                x = self._scene_x(sc_i)
                if plot in scene.plots():
                    if sc_i not in self._scene_coord_y.keys():
                        self._scene_coord_y[sc_i] = y
                    if previous_y > self._scene_coord_y[sc_i] or (previous_y == 0 and y > self._scene_coord_y[sc_i]):
                        path.lineTo(x - 25, y)
                    elif 0 < previous_y < self._scene_coord_y[sc_i]:
                        path.lineTo(previous_x + 25, y)

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

        for sc_i, scene in enumerate(self.novel.scenes):
            if sc_i not in self._scene_coord_y.keys():
                continue
            self._draw_scene_ellipse(painter, scene, self._scene_x(sc_i), self._scene_coord_y[sc_i])

        for sc_i, scene in enumerate(self.novel.scenes):
            if not scene.plots():
                self._draw_scene_ellipse(painter, scene, self._scene_x(sc_i), 3)

        if len(self.novel.plots) <= 1:
            return

        base_y = y
        for sl_i, plot in enumerate(self.novel.plots):
            y = 50 * (sl_i + 1) + 25 + base_y
            painter.setPen(QPen(QColor(plot.color_hexa), 4, Qt.PenStyle.SolidLine))
            painter.drawLine(0, y, last_sc_x.get(sl_i, 15), y)
            painter.setPen(QPen(Qt.GlobalColor.black, 5, Qt.PenStyle.SolidLine))
            painter.drawText(5, y - 15, plot.text)

            for sc_i, scene in enumerate(self.novel.scenes):
                if plot in scene.plots():
                    self._draw_scene_ellipse(painter, scene, self._scene_x(sc_i), y)

        painter.end()

    def _draw_scene_ellipse(self, painter: QPainter, scene: Scene, x: int, y: int):
        if scene.plot_values:
            pen = Qt.GlobalColor.red if scene is self._clicked_scene else Qt.GlobalColor.black
            if len(scene.plot_values) == 1:
                painter.setPen(QPen(pen, 3, Qt.PenStyle.SolidLine))
                painter.setBrush(Qt.GlobalColor.black)
                painter.drawEllipse(x, y - 7, 14, 14)
            else:
                painter.setPen(QPen(pen, 3, Qt.PenStyle.SolidLine))
                painter.setBrush(Qt.GlobalColor.white)
                painter.drawEllipse(x, y - 10, 20, 20)
        else:
            pen = Qt.GlobalColor.red if scene is self._clicked_scene else Qt.GlobalColor.gray
            painter.setPen(QPen(pen, 3, Qt.PenStyle.SolidLine))
            painter.setBrush(Qt.GlobalColor.gray)
            painter.drawEllipse(x, y, 14, 14)

    @staticmethod
    def _story_line_y(index: int) -> int:
        return 50 * (index + 1)

    @staticmethod
    def _scene_x(index: int) -> int:
        return 25 * (index + 1)

    @staticmethod
    def _index_from_pos(pos: QPoint) -> int:
        return int((pos.x() / 25) - 1)

    def _context_menu_requested(self, pos: QPoint) -> None:
        index = self._index_from_pos(pos)
        if index < len(self.novel.scenes):
            self._clicked_scene: Scene = self.novel.scenes[index]
            self.update()

            builder = PopupMenuBuilder.from_widget_position(self, pos)
            if self.novel.plots:
                for plot in self.novel.plots:
                    plot_action = builder.add_action(truncate_string(plot.text, 70),
                                                     slot=partial(self._plot_changed, plot))
                    plot_action.setCheckable(True)
                    if plot in self._clicked_scene.plots():
                        plot_action.setChecked(True)

                builder.popup()

    @busy
    def _plot_changed(self, plot: Plot, checked: bool):
        if checked:
            self._clicked_scene.plot_values.append(ScenePlotValue(plot))
        else:
            to_be_removed = None
            for plot_v in self._clicked_scene.plot_values:
                if plot_v.plot is plot:
                    to_be_removed = plot_v
                    break
            if to_be_removed:
                self._clicked_scene.plot_values.remove(to_be_removed)
        RepositoryPersistenceManager.instance().update_scene(self._clicked_scene)

        self.update()
