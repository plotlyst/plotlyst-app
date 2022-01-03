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
from PyQt6.QtCore import Qt, QRect, QPoint, QSize
from PyQt6.QtGui import QPaintEvent, QPainter, QPen, QColor
from PyQt6.QtWidgets import QWidget
from overrides import overrides

from src.main.python.plotlyst.common import truncate_string
from src.main.python.plotlyst.core.domain import Novel, Scene
from src.main.python.plotlyst.view.icons import avatars


class TimelineWidget(QWidget):

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent=parent)
        self.novel: Novel = novel
        self.scene_start_x = 75
        self.scene_dist = 200

    @overrides
    def minimumSizeHint(self) -> QSize:
        x = self.scene_dist + self.scene_dist
        scene_per_line = self._scenesPerLine(self.rect().width())
        y = 275 + (len(self.novel.scenes) / scene_per_line) * 250
        return QSize(x, y)

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        width = event.rect().width()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), Qt.GlobalColor.white)

        scenes = [x for x in self.novel.scenes if x.day]
        scenes = sorted(scenes, key=lambda x: x.day)
        if not scenes:
            return

        y = 50
        forward = True
        scene_per_line = int((width - self.scene_start_x) / self.scene_dist)
        # for initial draw, the size might be too small
        if scene_per_line == 0:
            scene_per_line = 1
        painter.setPen(QPen(QColor('#02bcd4'), 20, Qt.PenStyle.SolidLine))
        painter.setBrush(QColor('#02bcd4'))
        painter.drawEllipse(15, y - 15, 30, 30)
        last_day = scenes[0].day
        for i, scene in enumerate(scenes):
            if i % scene_per_line == 0:
                self._drawLine(painter, width, y)
            last_scene_x = self._drawScene(painter, y, scene, i, scene_per_line, forward)
            if scene.day != last_day:
                self._drawDay(painter, last_scene_x, y, scene.day, forward)
                last_day = scene.day
            painter.setPen(QPen(QColor('#02bcd4'), 20, Qt.PenStyle.SolidLine))
            painter.setBrush(QColor('#02bcd4'))

            if i % scene_per_line == scene_per_line - 1:
                if i != len(scenes) - 1:
                    self._drawArc(painter, width, y, forward)
                    forward = not forward
                    y += 110

        if forward:
            painter.drawEllipse(width - 70, y - 15, 30, 30)
        else:
            painter.drawEllipse(15, y - 15, 30, 30)

        painter.end()

    def _scenesPerLine(self, width: int):
        return int((width - self.scene_start_x) / self.scene_dist)

    def _drawLine(self, painter: QPainter, width: int, y: int):
        painter.drawLine(60, y, width - 70, y)

    def _drawArc(self, painter: QPainter, width: int, y: int, forward: bool):
        if forward:
            painter.drawArc(QRect(width - 100, y, 90, 110), 90 * 16, -180 * 16)
        else:
            painter.drawArc(QRect(10, y, 90, 110), -270 * 16, 180 * 16)

    def _drawDay(self, painter: QPainter, last_scene_x: int, y: int, day: int, forward: bool):
        painter.setPen(QPen(QColor('#02bcd4'), 8, Qt.PenStyle.SolidLine))
        if forward:
            if last_scene_x == self.scene_start_x:
                x = self.scene_start_x - 15
            else:
                x = last_scene_x - 35
        else:
            x = last_scene_x + self.scene_dist - 35
        painter.drawLine(x, y + 20, x, y - 20)
        painter.setPen(QPen(Qt.GlobalColor.black, 13, Qt.PenStyle.SolidLine))
        painter.drawText(QPoint(x - 5, y - 28), str(day))

    def _drawScene(self, painter: QPainter, y: int, scene: Scene, index: int, scene_per_line: int,
                   forward: bool) -> int:
        painter.setPen(QPen(Qt.GlobalColor.black, 13, Qt.PenStyle.SolidLine))
        if forward:
            x = self.scene_start_x + self.scene_dist * (index % scene_per_line)
        else:
            x = self.scene_start_x + self.scene_dist * (scene_per_line - 1 - ((index % scene_per_line)))
        painter.drawText(QPoint(x, y - 15), truncate_string(scene.title, 20))

        if scene.pov:
            if scene.pov.avatar:
                painter.drawPixmap(QPoint(x, y - 10),
                                   avatars.pixmap(scene.pov).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio,
                                                                    Qt.TransformationMode.SmoothTransformation))
            else:
                painter.setPen(QPen(Qt.GlobalColor.white, 1, Qt.PenStyle.SolidLine))
                painter.setBrush(Qt.GlobalColor.white)
                painter.drawEllipse(x, y - 10, 24, 24)
                pixmap = avatars.name_initial_icon(scene.pov).pixmap(24, 24)
                painter.drawPixmap(QPoint(x, y - 10), pixmap)
        return x
