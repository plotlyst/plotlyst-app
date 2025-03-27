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
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QWidget

from plotlyst.view.style.theme import BG_SECONDARY_COLOR, TEXT_COLOR_ON_DARK_BG, BG_MUTED_COLOR, \
    TEXT_SECONDARY_COLOR_ON_DARK_BG

label_style_description = """
    QLabel[description=true] {
        color: #5E6C84;
    }

    QLabel[description=true]:!enabled {
        color: #CED4DD;
    }
"""

label_style_error_night_mode = f"""
    QLabel[error=true] {{
        color: #e76f51;
    }}

    QLabel[night-mode=true] {{
        color: {TEXT_COLOR_ON_DARK_BG};
    }}
    
    QLabel[night-mode-secondary=true] {{
        color: {TEXT_SECONDARY_COLOR_ON_DARK_BG};
    }}
"""

label_style_headings = """
    QLabel[h1=true] {
        font-size: 30pt;
    }

    QLabel[h2=true] {
        font-size: 20pt;
    }

    QLabel[h3=true] {
        font-size: 18pt;
    }

    QLabel[h4=true] {
        font-size: 16pt;
    }
    
    QLabel[h5=true] {
        font-size: 14pt;
    }
    
    QLabel[small-body=true] {
        font-size: 14pt;
    }
"""

text_browser_styles = f"""
    QTextBrowser {{
        background-color: {BG_SECONDARY_COLOR};
    }}

    QTextBrowser[rounded=true] {{
        border-radius: 6px;
        padding: 4px;
        border: 1px solid lightgrey;
    }}
    
    QTextBrowser[error=true] {{
        color: #e76f51;
    }}
    
"""

line_edit_styles = f"""
    QLineEdit {{
        background-color: {BG_SECONDARY_COLOR};
    }}
    
    QLineEdit[white-bg=true] {{
        background-color: #FcFcFc;
    }}
    
    QLineEdit[muted-bg=true] {{
        background-color: {BG_MUTED_COLOR};
    }}
    
    QLineEdit[rounded=true] {{
        border-radius: 6px;
        padding: 4px;
        border: 1px solid lightgrey;
    }}
    
    QLineEdit[rounded=true]:focus {{
        border: 1px solid #D4B8E0;
    }}
    
    QLineEdit[transparent=true] {{
        border: 0px;
        background-color: rgba(0, 0, 0, 0);
    }}
"""

text_edit_styles = f"""
    QTextEdit {{
        background-color: {BG_SECONDARY_COLOR};
    }}

    QTextEdit[rounded=true] {{
        border-radius: 6px;
        padding: 4px;
        border: 1px solid lightgrey;
    }}
    
    QTextEdit[rounded=true]:focus {{
        border: 1px solid #D4B8E0;
    }}
    
    QTextEdit[white-bg=true] {{
        background-color: #FcFcFc;
    }}
    
    QTextEdit[night-mode=true] {{
        background-color: rgba(39, 39, 39, 200);
        color: {TEXT_COLOR_ON_DARK_BG};
    }}
    
    QTextEdit[transparent=true] {{
        border: 0px;
        background-color: rgba(0, 0, 0, 0);
    }}
    
    QTextEdit[description=true] {{
        color: #5E6C84;
    }}
    
    QTextEdit[borderless=true] {{
        border: 0px;
        background-color: {BG_SECONDARY_COLOR};
    }}
"""

widget_styles_hint_widget = """
    HintWidget {
        border: 2px solid #7209b7;
        border-radius: 4px;
        background-color: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #dec9e9);
    }
"""

style = "\n".join([
    label_style_description,
    label_style_error_night_mode,
    label_style_headings,
    text_browser_styles,
    line_edit_styles,
    text_edit_styles,
    widget_styles_hint_widget
])


def apply_texteditor_toolbar_style(widget: QWidget):
    widget.setStyleSheet(f'''
                            QFrame {{
                                background-color: {BG_SECONDARY_COLOR};
                            }}

                            QToolButton {{
                                border: 1px hidden black;
                            }}
                            QToolButton:checked {{
                                background-color: #ced4da;
                            }}
                        ''')


def apply_text_color(editor: QWidget, color: QColor):
    palette = editor.palette()
    palette.setColor(QPalette.ColorRole.Text, color)
    color.setAlpha(125)
    palette.setColor(QPalette.ColorRole.PlaceholderText, color)
    editor.setPalette(palette)
