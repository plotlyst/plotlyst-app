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
import os

import pytest

from src.main.python.plotlyst.core.client import json_client
from src.main.python.plotlyst.core.domain import Character, Scene, Chapter, \
    Novel, Conflict, ConflictType, Plot, PlotType, ScenePlotValue, SceneType
from src.main.python.plotlyst.event.handler import event_dispatcher
from src.main.python.plotlyst.view.main_window import MainWindow
from src.main.python.plotlyst.view.stylesheet import APP_STYLESHEET


def pytest_generate_tests(metafunc):
    os.environ['PLOTLYST_TEST_ENV'] = '1'


@pytest.fixture
def test_client(tmp_path):
    json_client.init(tmp_path)


@pytest.fixture
def window(qtbot, test_client):
    return get_main_window(qtbot)


@pytest.fixture
def window_with_disk_db(qtbot, test_client):
    return get_main_window(qtbot)


@pytest.fixture
def filled_window(qtbot, test_client):
    init_project()
    return get_main_window(qtbot)


def get_main_window(qtbot):
    event_dispatcher.clear()

    main_window = MainWindow()
    main_window.setStyleSheet(APP_STYLESHEET)
    main_window.show()
    qtbot.addWidget(main_window)
    qtbot.waitExposed(main_window, timeout=5000)

    return main_window


def init_project():
    novel = Novel(title='Test Novel')
    char_a = Character(name='Alfred')
    char_b = Character(name='Babel')
    char_c = Character(name='Celine')
    char_d = Character(name='Delphine')
    char_e = Character(name='Edward')
    novel.characters.extend([char_a, char_b, char_c, char_d, char_e])

    mainplot = Plot(text='Main')
    internalplot = Plot(text='Lesser', plot_type=PlotType.Internal)
    subplot = Plot(text='Love', plot_type=PlotType.Subplot)
    novel.plots.extend([mainplot, internalplot, subplot])
    conflict = Conflict('Test', ConflictType.SOCIETY, character_id=char_a.id)
    novel.conflicts.append(conflict)

    chapter_1 = Chapter(title='1')
    chapter_2 = Chapter(title='2')
    novel.chapters.append(chapter_1)
    novel.chapters.append(chapter_2)
    scene_1 = Scene(title='Scene 1', synopsis='Scene 1 synopsis', pov=char_a, characters=[char_b, char_c],
                    plot_values=[ScenePlotValue(mainplot)], sequence=0, chapter=chapter_1, day=1, type=SceneType.ACTION,
                    stage=novel.stages[1])
    scene_2 = Scene(title='Scene 2', synopsis='Scene 2 synopsis', pov=char_d, characters=[char_c, char_a],
                    plot_values=[ScenePlotValue(internalplot), ScenePlotValue(subplot)], sequence=1, chapter=chapter_2,
                    day=2, type=SceneType.REACTION)
    novel.scenes.append(scene_1)
    novel.scenes.append(scene_2)

    json_client.insert_novel(novel)
    for char in novel.characters:
        json_client.insert_character(novel, char)
    for scene in novel.scenes:
        json_client.insert_scene(novel, scene)
