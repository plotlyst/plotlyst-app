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
from typing import Union

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget

style = '''

QSlider:horizontal {
  min-height: 20px;
  max-height: 20px;
}

QSlider::groove:horizontal {
    border: 1px solid #adb5bd;
    border-radius: 2px;
    background: #dee2e6;
    height: 4px;
    margin: 0px 0;
}

QSlider::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4B0763, stop:1 #4B0763);
    border: 1px solid #4B0763;
    width: 13px;
    height: 13px;
    margin: -5px -2px;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #4B0763;
}

QSlider::handle:horizontal[conflict=true] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
    border: 1px solid #5c5c5c;
}

QSlider::add-page:horizontal[conflict=true] {
    background: lightgray;
}
QSlider::sub-page:horizontal[conflict=true] {
    background: #f3a712;
}

QSlider::add-page:horizontal[emotion_0=true] {
    background: #f25c54;
}
QSlider::sub-page:horizontal[emotion_0=true] {
    background: lightgray;
}

QSlider::add-page:horizontal[emotion_1=true] {
    background: #f25c54;
}
QSlider::sub-page:horizontal[emotion_1=true] {
    background: lightgray;
}

QSlider::add-page:horizontal[emotion_2=true] {
    background: #f27059;
}
QSlider::sub-page:horizontal[emotion_2=true] {
    background: lightgray;
}

QSlider::add-page:horizontal[emotion_3=true] {
    background: #f4845f;
}
QSlider::sub-page:horizontal[emotion_3=true] {
    background: lightgray;
}

QSlider::add-page:horizontal[emotion_4=true] {
    background: #f79d65;
}
QSlider::sub-page:horizontal[emotion_4=true] {
    background: lightgray;
}

QSlider::add-page:horizontal[emotion_5=true] {
    background: lightgray;
}
QSlider::sub-page:horizontal[emotion_5=true] {
    background: lightgray;
}

QSlider::add-page:horizontal[emotion_6=true] {
    background: lightgray;
}
QSlider::sub-page:horizontal[emotion_6=true] {
    background: #74c69d;
}

QSlider::add-page:horizontal[emotion_7=true] {
    background: lightgray;
}
QSlider::sub-page:horizontal[emotion_7=true] {
    background: #52b788;
}

QSlider::add-page:horizontal[emotion_8=true] {
    background: lightgray;
}
QSlider::sub-page:horizontal[emotion_8=true] {
    background: #40916c;
}

QSlider::add-page:horizontal[emotion_9=true] {
    background: lightgray;
}
QSlider::sub-page:horizontal[emotion_9=true] {
    background: #2d6a4f;
}

QSlider::add-page:horizontal[emotion_10=true] {
    background: lightgray;
}
QSlider::sub-page:horizontal[emotion_10=true] {
    background: #2d6a4f;
}

QSlider::add-page:horizontal[ally-enemy=true] {
    background: #9e1946;
}
QSlider::sub-page:horizontal[ally-enemy=true] {
    background: #266dd3;
}
QSlider::handle:horizontal[ally-enemy=true] {
    background: #266dd3;
    border: 1px solid #266dd3;
}

QSlider::add-page:horizontal[relationship=true] {
    background: lightgrey;
}
QSlider::sub-page:horizontal[relationship=true] {
    background: #f25c54;
}
QSlider::handle:horizontal[relationship=true] {
    background: #f25c54;
    border: 1px solid #f25c54;
}

'''


def apply_slider_color(wdg: QWidget, color: Union[str, QColor, Qt.GlobalColor]):
    if isinstance(color, QColor):
        color = color.name()
    wdg.setStyleSheet(f'''
                QSlider::add-page:horizontal {{
                    background: lightgray;
                }}
                QSlider::sub-page:horizontal {{
                    background: {color};
                }}
                QSlider::handle:horizontal {{
                    background: {color};
                    border: 1px solid {color};
                }}
            ''')
