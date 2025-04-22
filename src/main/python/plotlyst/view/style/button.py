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
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QAbstractButton

from plotlyst.view.style.theme import TEXT_COLOR_ON_DARK_BG, BG_SECONDARY_COLOR

btn_style_no_menu = """
    QPushButton::menu-indicator[no-menu] {
        width:0px;
    }
"""

btn_style_base = """
    QPushButton[base=true] {
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #f6f7fa, stop: 1 #dadbde);
        border: 2px solid #8f8f91;
        border-radius: 6px;
        padding: 2px;
    }

    QPushButton:hover[base=true] {
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #c3c4c7, stop: 1 #f6f7fa);
    }

    QPushButton:pressed[base=true] {
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #d7d8db, stop: 1 #f6f7fa);
        border: 2px solid darkGrey;
    }

    QPushButton:checked[base=true] {
        background-color: lightgrey;
    }

    QPushButton:disabled[base=true] {
        opacity: 0.65;
    }
"""

btn_style_large = """
    QPushButton[large=true] {
        font-size: 24px;
    }
"""

btn_style_positive = """
    QPushButton[positive=true]:!disabled {
        background-color: #4B0763;
        border: 2px solid black;
        color: #fff;
        font: bold;
    }

    QPushButton[positive=true]:hover {
        background-color: #37065D;
    }
"""

btn_style_highlighted = """
    QPushButton[highlighted=true]:!disabled {
        background-color: #071064;
        color: #fff;
        font: bold;
    }

    QPushButton[highlighted=true]:hover {
        background-color: #060F5D;
    }
"""

btn_style_confirm = """
    QPushButton[confirm=true] {
        border: 1px solid lightgrey;
        border-radius: 6px;
        padding: 5px 15px 5px 15px;
    }
"""

btn_style_deconstructive = f"""
    QPushButton[deconstructive=true]:!disabled {{
        background: #E11D48;
        color: {TEXT_COLOR_ON_DARK_BG};
        font: bold;
    }}

    QPushButton[deconstructive=true]:hover {{
        background: #E84E6F;
    }}
"""

btn_style_cancel = f"""
    QPushButton[cancel=true]:!disabled {{
        background: #FcFcFc;
    }}
    QPushButton[cancel=true]:!disabled:hover {{
        background: {BG_SECONDARY_COLOR};
    }}
"""

btn_style_transparent = """
    QPushButton[transparent=true] {
        border: 0px;
        background-color: rgba(0, 0, 0, 0);
    }
"""

btn_style_plain = """
    QPushButton[plain=true] {
        border: 1px hidden black;
        background-color: rgba(0, 0, 0, 0);
        padding: 8px;
    }
"""

btn_style_secondary_field_attribute = """
    QPushButton[secondary-field-attribute=true] {
        border: 1px hidden black;
        border-radius: 6px;
        color: #343a40;
        padding: 2px;
    }
"""

btn_style_top_level_nav = """
    QPushButton[top-level-nav=true] {
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #89c2d9);
        border: 2px solid #2c7da0;
        border-radius: 6px;
        color: white;
        padding: 2px;
        padding-left: 4px;
        padding-right: 4px;
        font: bold;
    }

    QPushButton:disabled[top-level-nav=true] {
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 lightGray);
        border: 2px solid grey;
        color: grey;
        opacity: 0.45;
    }

    QPushButton:checked[top-level-nav=true] {
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #014f86);
        border: 2px solid #013a63;
    }
"""

btn_style_main_side_nav = """
    QPushButton[main-side-nav=true] {
        border: 0px;
        margin: 5px;
        padding: 5px;
        padding-top: 6px;
        padding-bottom: 6px;
    }

    QPushButton:hover[main-side-nav=true] {
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 0, stop: 0 #E9DEEE);
        border: 1px hidden black;
    }

    QPushButton:checked[main-side-nav=true] {
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 0, stop: 0 #7A548B);
        border: 1px solid #B096BB;
        color: white;
    }
"""

btn_style_lang_spellcheck_suggestion = f"""
    QPushButton[lang-spellcheck-suggestion=true] {{
        background: #4B0763;
        border: 1px solid #4B0763;
        border-radius: 5px;
        padding: 3px;
        color: {TEXT_COLOR_ON_DARK_BG};
        margin: 2px;
    }}
"""

btn_style_return = """
    QPushButton[return=true] {
        border: 0px;
        background-color: rgba(0, 0, 0, 0);
        font-size: 16px;
        color: #4B0763;
    }
"""

btn_style_find = f"""
    QPushButton[find=true] {{
        margin: 2px;
        padding: 2px;
        border-radius: 2px;
        border: 1px solid lightgrey;
        background: {BG_SECONDARY_COLOR};
    }}
    QPushButton[find=true]:pressed {{
        padding: 2px;
        margin: 1px;
    }}
    QPushButton[find=true]:disabled {{
        opacity: 0.65;
    }}
"""

btn_style_importer_sync = f"""
    QPushButton[importer-sync=true] {{
        padding: 2px;
        border-radius: 6px;
        border: 1px hidden #410253;
        background-color: rgba(0, 0, 0, 0);
        color: #410253;
    }}

    QPushButton:hover[importer-sync=true] {{
        border: 1px outset #410253;
        background-color: {BG_SECONDARY_COLOR};
    }}
"""

btn_style_structure_customization = """
    QPushButton[structure-customization=true] {
        border: none;
        padding: 2px;
    }

    QPushButton:hover[structure-customization=true] {
        background: lightgrey;
    }

    QPushButton[structure-customization=true][act-one=true] {
        border-bottom: 2px solid #02bcd4;
    }

    QPushButton[structure-customization=true][act-two=true] {
        border-bottom: 2px solid #1bbc9c;
    }

    QPushButton[structure-customization=true][act-three=true] {
        border-bottom: 2px solid #ff7800;
    }
"""

btn_style_tool_button_base = """
    QToolButton::menu-indicator {
        width:0px;
    }
    QToolButton[base=true] {
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #f6f7fa, stop: 1 #dadbde);
        border: 1px solid #8f8f91;
        border-radius: 6px;
        padding: 2px;
    }
    
    QToolButton[side-button-right=true] {
        border-bottom-right-radius: 0px;
        border-top-right-radius: 0px;
    }
    
    QToolButton[side-button-left=true] {
        border-bottom-left-radius: 0px;
        border-top-left-radius: 0px;
    }
    
    QToolButton:hover[base=true] {
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #c3c4c7, stop: 1 #f6f7fa);
    }

    QToolButton:pressed[base=true] {
        background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #d7d8db, stop: 1 #f6f7fa);
    }

    QToolButton:checked[base=true] {
        background-color: lightgrey;
    }

    QToolButton:disabled[base=true] {
        opacity: 0.65;
    }
"""

btn_style_tool_button_transparent = """
    QToolButton[transparent=true] {
        border: 0px;
        background-color: rgba(0, 0, 0, 0);
        border-radius: 4px;
    }

    QToolButton[transparent-clickable=true] {
        border: 0px;
        background-color: rgba(0, 0, 0, 0);
        border-radius: 4px;
    }

    QToolButton:pressed[transparent-clickable=true] {
        border: 1px solid grey;
    }

    QToolButton[transparent-circle-bg-on-hover=true] {
        border-radius: 12px;
        border: 1px hidden lightgrey;
        padding: 2px;
    }

    QToolButton::menu-indicator[transparent-circle-bg-on-hover=true] {
        width:0px;
    }

    QToolButton:hover[transparent-circle-bg-on-hover=true] {
        background: #EDEDED;
    }

    QToolButton:hover[transparent-circle-bg-on-hover=true][positive=true] {
        background: #d8f3dc;
    }

    QToolButton[transparent-circle-bg-on-hover=true][large=true] {
        border-radius: 18px;
        padding: 4px;
    }
"""

btn_style_abstract_button_transparent = """
    QAbstractButton[transparent-rounded-bg-on-hover=true] {
        border-radius: 4px;
        border: 1px hidden lightgrey;
        padding: 2px;
    }

    QAbstractButton::menu-indicator[transparent-rounded-bg-on-hover=true] {
        width:0px;
    }
    
    QAbstractButton:hover[transparent-rounded-bg-on-hover=true] {
        background: #EDEDED;
    }
    
    QAbstractButton:hover[transparent-magnolia-rounded-bg-on-hover=true] {
        background: #F0E6F4;
    }

    QAbstractButton:hover[top-selector=true] {
        background: lightgrey;
    }

    QAbstractButton:checked[top-selector=true] {
        background: #D4B8E0;
    }

    QAbstractButton:hover[secondary-selector=true] {
        border-bottom: 1px solid lightgrey;
    }

    QAbstractButton:checked[secondary-selector=true] {
        border-bottom: 2px solid #4B0763;
        border-radius: 0px;
        color: #4B0763;
    }
"""

btn_style_tool_button_emotion = """
    QToolButton:checked[emotion-very-unhappy=true] {
        background-color: rgb(239, 0, 0);
    }

    QToolButton:hover[emotion-very-unhappy=true] {
        border: 1px solid rgb(239, 0, 0);
    }

    QToolButton:checked[emotion-unhappy=true] {
        background-color: rgb(255, 142, 43);
    }

    QToolButton:hover[emotion-unhappy=true] {
        border: 1px solid rgb(255, 142, 43);
    }

    QToolButton::checked[emotion-neutral=true] {
        background-color: rgb(171, 171, 171);
    }

    QToolButton:hover[emotion-neutral=true] {
        border: 1px solid rgb(171, 171, 171);
    }

    QToolButton:checked[emotion-happy=true] {
        background-color: #93e5ab;
    }

    QToolButton:hover[emotion-happy=true] {
        border: 1px solid #93e5ab;
    }

    QToolButton:checked[emotion-very-happy=true] {
        background-color: rgb(0, 202, 148);
    }

    QToolButton:hover[emotion-very-happy=true] {
        border: 1px solid rgb(0, 202, 148);
    }
"""

btn_style_tool_button_conflict_selector = """
    QToolButton[conflict-selector=true] {
        border-radius: 15px;
        border: 1px hidden lightgrey;
        padding: 2px;
    }

    QToolButton:hover[conflict-selector=true] {
        background: lightgrey;
    }

    QToolButton:checked[conflict-selector=true] {
        background: #fce4c9;
    }
"""

btn_style_tool_button_gender = """
    QToolButton[gender-male=true] {
        border: 1px dashed grey;
        border-radius: 6px;
    }

    QToolButton:pressed[gender-male=true] {
        border: 1px solid grey;
    }

    QToolButton:checked[gender-male=true] {
        border: 2px solid #067bc2;	
    }

    QToolButton[gender-female=true] {
        border: 1px dashed grey;
        border-radius: 6px;
    }

    QToolButton:pressed[gender-female=true] {
        border: 1px solid grey;
    }

    QToolButton:checked[gender-female=true] {
        border: 2px solid #832161;	
    }

    QToolButton[gender-transgender=true] {
        border: 1px dashed grey;
        border-radius: 6px;
    }

    QToolButton:pressed[gender-transgender=true] {
        border: 1px solid grey;
    }

    QToolButton:checked[gender-transgender=true] {
        border: 2px solid #f4a261;	
    }

    QToolButton[gender-non-binary=true] {
        border: 1px dashed grey;
        border-radius: 6px;
    }

    QToolButton:pressed[gender-non-binary=true] {
        border: 1px solid grey;
    }

    QToolButton:checked[gender-non-binary=true] {
        border: 2px solid #7209b7;	
    }

    QToolButton[gender-genderless=true] {
        border: 1px dashed grey;
        border-radius: 6px;
    }

    QToolButton:pressed[gender-genderless=true] {
        border: 1px solid grey;
    }

    QToolButton:checked[gender-genderless=true] {
        border: 2px solid #6c757d;	
    }
"""

btn_style_tool_button_main_navbar = """
    QToolButton[main-navbar=true] {
        border: 1px hidden white;
        border-radius: 6px;
        padding: 2px;
    }

    QToolButton:hover[main-navbar=true] {
        background-color: #642A8B;
    }

    QToolButton:checked[main-navbar=true] {
        background-color: #82329A;
    }
"""

btn_style_tool_button_dark_toggle = """
    QToolButton[dark-mode-toggle=true] {
        border: 0px;
        color: lightgrey;
    }
    QToolButton:checked[dark-mode-toggle=true] {
        color: #D4B8E0;
    }
"""

radio_btn = """
    QRadioButton {
        background-color: transparent;
        color: black;
    }

    QRadioButton::indicator {
        width: 15px;
        height: 15px;
        border-radius:8px;
    }
    
    QRadioButton::indicator:checked {
        background-color:       #4B0763;
        border:                 1px solid #3C0764;
    }
    
    QRadioButton::indicator:unchecked {
        background-color:       transparent;
        border:                 1px solid lightgrey;
    }
    
    QRadioButton::indicator:unchecked:hover {
        background-color:       transparent;
        border:                 1px solid #D4B8E0;
    }
"""

style = "\n".join([
    btn_style_no_menu,
    btn_style_base,
    btn_style_large,
    btn_style_positive,
    btn_style_highlighted,
    btn_style_confirm,
    btn_style_deconstructive,
    btn_style_cancel,
    btn_style_transparent,
    btn_style_plain,
    btn_style_secondary_field_attribute,
    btn_style_top_level_nav,
    btn_style_main_side_nav,
    btn_style_lang_spellcheck_suggestion,
    btn_style_return,
    btn_style_find,
    btn_style_importer_sync,
    btn_style_structure_customization,
    btn_style_tool_button_base,
    btn_style_tool_button_transparent,
    btn_style_abstract_button_transparent,
    btn_style_tool_button_emotion,
    btn_style_tool_button_conflict_selector,
    btn_style_tool_button_gender,
    btn_style_tool_button_main_navbar,
    btn_style_tool_button_dark_toggle
])


def apply_button_palette_color(btn: QAbstractButton, color: Union[str, QColor, Qt.GlobalColor]):
    if isinstance(color, str):
        color = QColor(color)
    palette = btn.palette()
    palette.setColor(QPalette.ColorGroup.Active, QPalette.ColorRole.ButtonText, color)
    btn.setPalette(palette)
