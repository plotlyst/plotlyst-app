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
import os

import pytest

from plotlyst.core.client import json_client
from plotlyst.core.domain import Character, Scene, Chapter, \
    Novel, Plot, PlotType, ScenePlotReference, CharacterAgency, ScenePurposeType
from plotlyst.env import app_env
from plotlyst.event.handler import global_event_dispatcher
from plotlyst.view.main_window import MainWindow
from plotlyst.view.stylesheet import APP_STYLESHEET


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
    novel = init_project()
    window = get_main_window(qtbot)
    window.home_view.loadNovel.emit(novel)
    return window


def get_main_window(qtbot):
    global_event_dispatcher.clear()

    main_window = MainWindow()
    main_window.setStyleSheet(APP_STYLESHEET)
    main_window.show()
    qtbot.addWidget(main_window)
    qtbot.waitExposed(main_window, timeout=5000)

    return main_window


def init_project():
    novel = Novel(title='Test Novel')
    app_env.novel = novel
    char_a = Character(name='Alfred')
    char_b = Character(name='Babel')
    char_c = Character(name='Celine')
    char_d = Character(name='Delphine')
    char_e = Character(name='Edward')
    novel.characters.extend([char_a, char_b, char_c, char_d, char_e])

    mainplot = Plot(text='Main', icon='fa5s.theater-masks')
    internalplot = Plot(text='Lesser', plot_type=PlotType.Internal, icon='mdi.mirror')
    subplot = Plot(text='Love', plot_type=PlotType.Subplot, icon='mdi.source-branch')
    novel.plots.extend([mainplot, internalplot, subplot])

    chapter_1 = Chapter(title='1')
    chapter_2 = Chapter(title='2')
    novel.chapters.append(chapter_1)
    novel.chapters.append(chapter_2)
    scene_1 = Scene(title='Scene 1', synopsis='Scene 1 synopsis', pov=char_a, characters=[char_b, char_c],
                    plot_values=[ScenePlotReference(mainplot)], chapter=chapter_1, day=1,
                    purpose=ScenePurposeType.Story,
                    stage=novel.stages[1], agency=[CharacterAgency()])
    scene_2 = Scene(title='Scene 2', synopsis='Scene 2 synopsis', pov=char_d, characters=[char_c, char_a],
                    plot_values=[ScenePlotReference(internalplot), ScenePlotReference(subplot)], chapter=chapter_2,
                    day=2, purpose=ScenePurposeType.Reaction, agency=[CharacterAgency()])
    novel.scenes.append(scene_1)
    novel.scenes.append(scene_2)

    json_client.insert_novel(novel)
    for char in novel.characters:
        json_client.insert_character(novel, char)
    for scene in novel.scenes:
        json_client.insert_scene(novel, scene)

    return novel
