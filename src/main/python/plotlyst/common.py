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
import socket
from timeit import default_timer as timer
from typing import Any, NoReturn, Dict

from plotlyst.view.style.theme import BG_SECONDARY_COLOR

WIP_COLOR: str = '#f6cd61'

ACT_ONE_COLOR: str = '#02bcd4'
TRANS_ACT_ONE_COLOR: str = 'rgba(2, 188, 212, 45)'
ACT_TWO_COLOR: str = '#1bbc9c'
TRANS_ACT_TWO_COLOR: str = 'rgba(27, 188, 156, 45)'
ACT_TWO_COLOR_B: str = '#1B99A3'
TRANS_ACT_TWO_COLOR_B: str = 'rgba(27, 153, 163, 45)'
ACT_THREE_COLOR: str = '#ff7800'
TRANS_ACT_THREE_COLOR: str = 'rgba(255, 120, 0, 45)'
ACT_FOUR_COLOR: str = '#5A716A'
TRANS_ACT_FOUR_COLOR: str = 'rgba(90, 113, 106, 45)'
ACT_FIVE_COLOR: str = '#8B95C9'
TRANS_ACT_FIVE_COLOR: str = 'rgba(139, 149, 201, 45)'
ACT_SIX_COLOR: str = '#AD7A99'
TRANS_ACT_SIX_COLOR: str = 'rgba(173, 122, 153, 45)'

MAX_NUMBER_OF_ACTS: int = 7

CONFLICT_CHARACTER_COLOR: str = '#c1666b'
CONFLICT_SOCIETY_COLOR: str = '#69306d'
CONFLICT_NATURE_COLOR: str = '#157a6e'
CONFLICT_TECHNOLOGY_COLOR: str = '#4a5859'
CONFLICT_SUPERNATURAL_COLOR: str = '#ac7b84'
CONFLICT_SELF_COLOR: str = '#94b0da'

CHARACTER_MAJOR_COLOR: str = '#00798c'
CHARACTER_SECONDARY_COLOR: str = '#619b8a'
CHARACTER_MINOR_COLOR: str = '#886f68'

NEUTRAL_EMOTION_COLOR: str = '#ababab'
VERY_UNHAPPY_EMOTION_COLOR: str = '#ef0000'
UNHAPPY_EMOTION_COLOR: str = '#ff8e2b'
HAPPY_EMOTION_COLOR: str = '#93e5ab'
VERY_HAPPY_EMOTION_COLOR: str = '#00ca94'

IGNORE_CAPITALIZATION_PROPERTY = 'ignore_capitalization'

DEFAULT_PREMIUM_LINK: str = 'https://plotlyst.com/pricing/'

EMOTION_COLORS: Dict[int, str] = {
    0: '#f25c54',
    1: '#f25c54',
    2: '#f27059',
    3: '#f4845f',
    4: '#f79d65',
    5: NEUTRAL_EMOTION_COLOR,
    6: '#74c69d',
    7: '#52b788',
    8: '#40916c',
    9: '#2d6a4f',
    10: '#2d6a4f',
}

PLOTLYST_MAIN_COLOR: str = '#3C0764'  # Persian indigo, #4B0763: Indigo, #37065D: Russian violet
PLOTLYST_MAIN_COMPLEMENTARY_COLOR: str = '#2C5D06'  # Dark moss green
PLOTLYST_SECONDARY_COLOR: str = '#4B0763'  # indigo
PLOTLYST_TERTIARY_COLOR: str = '#D4B8E0'  # Thistle
TRANS_PLOTLYST_SECONDARY_COLOR = 'rgba(75, 7, 99, 45)'

ALT_BACKGROUND_COLOR: str = '#F0E6F4'

RELAXED_WHITE_COLOR: str = BG_SECONDARY_COLOR
WHITE_COLOR: str = '#FcFcFc'
BLACK_COLOR: str = '#040406'
RED_COLOR: str = '#ED6868'
DECONSTRUCTIVE_COLOR: str = '#E11D48'

PLACEHOLDER_TEXT_COLOR: str = '#5E6C84'

NAV_BAR_BUTTON_DEFAULT_COLOR: str = '#A89BC7'
NAV_BAR_BUTTON_CHECKED_COLOR: str = '#F9F9F9'

DEFAULT_MANUSCRIPT_LINE_SPACE: int = 130
DEFAULT_MANUSCRIPT_INDENT: int = 20

MAXIMUM_SIZE: int = 16777215


# def emotion_color(emotion_value: int) -> str:
#     if emotion_value == VERY_UNHAPPY:
#         return VERY_UNHAPPY_EMOTION_COLOR
#     elif emotion_value == UNHAPPY:
#         return UNHAPPY_EMOTION_COLOR
#     elif emotion_value == HAPPY:
#         return HAPPY_EMOTION_COLOR
#     elif emotion_value == VERY_HAPPY:
#         return VERY_HAPPY_EMOTION_COLOR
#     else:
#         return NEUTRAL_EMOTION_COLOR


def truncate_string(text: str, length: int = 25):
    return (text[:length] + '...') if len(text) > length else text


def act_color(act: int, all_acts: int, translucent: bool = False) -> str:
    if act == 1:
        return TRANS_ACT_ONE_COLOR if translucent else ACT_ONE_COLOR
    elif act == 2:
        return TRANS_ACT_TWO_COLOR if translucent else ACT_TWO_COLOR
    elif act == 3 and act < all_acts:
        return TRANS_ACT_TWO_COLOR_B if translucent else ACT_TWO_COLOR_B
    elif act == 4 and act < all_acts:
        return TRANS_ACT_FOUR_COLOR if translucent else ACT_FOUR_COLOR
    elif act == 5 and act < all_acts:
        return TRANS_ACT_FIVE_COLOR if translucent else ACT_FIVE_COLOR
    elif act == 6 and act < all_acts:
        return TRANS_ACT_SIX_COLOR if translucent else ACT_SIX_COLOR
    elif act == all_acts and all_acts > 2:
        return TRANS_ACT_THREE_COLOR if translucent else ACT_THREE_COLOR
    else:
        return TRANS_PLOTLYST_SECONDARY_COLOR if translucent else PLOTLYST_SECONDARY_COLOR


def recursive(parent, children_func, action, action_first: bool = True):
    for child in children_func(parent):
        if action_first:
            action(parent, child)

        recursive(child, children_func, action)

        if not action_first:
            action(parent, child)


class Timer:
    def __init__(self, prefix: str = 'Elapsed', auto_start: bool = True):
        self._prefix = prefix
        self._elapsed = 0
        self._start = 0

        if auto_start:
            self.start()

    def start(self):
        self._start = timer()

    def end(self, suffix: str = '') -> float:
        end = timer()
        self._elapsed = end - self._start
        if suffix:
            suffix = f'[{suffix}]'
        print(f'{self._prefix}: {self._elapsed} {suffix}')

        return self._elapsed


def camel_to_whitespace(text: str) -> str:
    """
    Converts a camel case string to a whitespace separated string.
    """
    words = []
    start = 0
    for i in range(len(text)):
        if text[i].isupper():
            words.append(text[start:i])
            start = i
    words.append(text[start:])
    new_text = ' '.join(words)
    new_text = new_text.strip()
    return new_text


def raise_unrecognized_arg(arg: Any) -> NoReturn:
    raise ValueError(f'Unrecognized argument {arg}')


def clamp(value, min_n, max_n):
    return max(min(max_n, value), min_n)


def has_internet() -> bool:
    remote_server = "www.google.com"
    port = 80
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        sock.connect((remote_server, port))
        return True
    except socket.error:
        return False
    finally:
        sock.close()
