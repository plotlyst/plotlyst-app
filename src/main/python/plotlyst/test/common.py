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
from typing import Any, List
from unittest.mock import patch

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import Qt, QPoint, QAbstractItemModel, QCoreApplication
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QAbstractItemView, QMenu, QMessageBox
from qttextedit import RichTextEditor

from plotlyst.core.domain import PlotType
from plotlyst.view.characters_view import CharactersView
from plotlyst.view.docs_view import DocumentsView
from plotlyst.view.home_view import HomeView
from plotlyst.view.main_window import MainWindow
from plotlyst.view.novel_view import NovelView
from plotlyst.view.reports_view import ReportsView
from plotlyst.view.scenes_view import ScenesOutlineView
from plotlyst.view.widget.confirm import ConfirmationDialog


def show_widget(qtbot, widget):
    widget.show()
    qtbot.addWidget(widget)
    # qtbot.waitExposed(widget, timeout=5000)


def click_on_item(qtbot, view: QAbstractItemView, row: int, column: int = 0, parent=None,
                  modifier=Qt.KeyboardModifier.NoModifier):
    position: QPoint = _get_position_or_fail(view, row, column, parent)
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=position, modifier=modifier)


def _get_position_or_fail(view: QAbstractItemView, row: int, column: int = 0, parent=None) -> QPoint:
    _assert_row_and_column(row, column)

    if parent:
        index = view.model().index(row, column, parent)
    else:
        index = view.model().index(row, column)
    assert index.isValid(), f'The given row and column do not not have a valid index. Row: {row}, column: {column}'

    return view.visualRect(index).center()


def _assert_row_and_column(row: int, column: int):
    assert row >= 0, f'Row must not be negative: {row}'
    assert column >= 0, f'Column must not be negative: {column}'


def assert_data(model: QAbstractItemModel, value: Any, row: int, column: int = 0,
                role: int = Qt.ItemDataRole.DisplayRole,
                parent=None):
    _assert_row_and_column(row, column)
    if parent:
        assert model.rowCount(parent) > row
    else:
        assert model.rowCount() > row

    if parent:
        assert model.data(model.index(row, column, parent),
                          role) == value, f'{model.data(model.index(row, column, parent), role)} != {value}'
    else:
        assert model.data(model.index(row, column),
                          role) == value, f'{model.data(model.index(row, column), role)} != {value}'


def trigger_popup_action_on_item(qtbot, view: QAbstractItemView, row: int, column: int, action_name: str, parent=None):
    # Right-click doesn't trigger popup: https://github.com/pytest-dev/pytest-qt/issues/269
    view.customContextMenuRequested.emit(_get_position_or_fail(view, row, column, parent))
    trigger_action_on_popup(qtbot, action_name)


def trigger_action_on_popup(qtbot, action_name: str):
    app: QCoreApplication = QtWidgets.QApplication.instance()
    menu: QMenu = app.activePopupWidget()

    # for action_name in action_names:
    action: QAction = next((a for a in menu.actions() if a.text() == action_name), None)
    qtbot.mouseClick(menu, QtCore.Qt.MouseButton.LeftButton, pos=menu.actionGeometry(action).center())
    qtbot.wait(100)


def popup_actions_on_item(qtbot, view: QAbstractItemView, row: int, column: int) -> List[QAction]:
    view.customContextMenuRequested.emit(_get_position_or_fail(view, row, column))
    app: QCoreApplication = QtWidgets.QApplication.instance()
    menu: QMenu = app.activePopupWidget()
    return menu.actions()


def patch_confirmed(monkeypatch, confirmed: bool = True):
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(ConfirmationDialog, "confirm", lambda *args: confirmed)


def edit_item(qtbot, view: QAbstractItemView, row: int, col: int, type, set_value_func):
    index = view.model().index(row, col)
    click_on_item(qtbot, view, index.row(), index.column())
    editor = view.indexWidget(index)
    assert editor, "Editor should be open"
    assert isinstance(editor, type)

    set_value_func(editor)
    view.itemDelegate().commitData.emit(editor)
    view.itemDelegate().closeEditor.emit(editor)


def go_to_scenes(window: MainWindow) -> ScenesOutlineView:
    window.btnScenes.setChecked(True)
    return window.scenes_outline_view


def go_to_characters(window: MainWindow) -> CharactersView:
    if not window.outline_mode.isChecked():
        window.outline_mode.setChecked(True)
    window.btnCharacters.setChecked(True)
    return window.characters_view


def go_to_novel(window: MainWindow) -> NovelView:
    if not window.outline_mode.isChecked():
        window.outline_mode.setChecked(True)
    window.btnNovel.setChecked(True)
    return window.novel_view


def go_to_home(window: MainWindow) -> HomeView:
    window.home_mode.setChecked(True)
    return window.home_view


def go_to_reports(window: MainWindow) -> ReportsView:
    if not window.outline_mode.isChecked():
        window.outline_mode.setChecked(True)
    window.btnReports.setChecked(True)
    return window.reports_view


def go_to_docs(window: MainWindow) -> DocumentsView:
    if not window.outline_mode.isChecked():
        window.outline_mode.setChecked(True)
    window.btnNotes.setChecked(True)
    return window.notes_view


def create_character(qtbot, window: MainWindow, name: str):
    characters: CharactersView = go_to_characters(window)

    with patch("plotlyst.view.widget.character.profile.CharacterOnboardingPopup.popup", return_value=True):
        characters.ui.btnNew.click()
    assert characters.editor

    type_text(qtbot, characters.editor.ui.lineName, name)

    characters.editor.ui.btnClose.click()


def create_plot(qtbot, window: MainWindow):
    novels: NovelView = go_to_novel(window)

    novels.plot_editor.newPlot(PlotType.Main)


def start_new_scene_editor(window: MainWindow) -> ScenesOutlineView:
    scenes: ScenesOutlineView = go_to_scenes(window)
    scenes.ui.btnNew.click()
    assert scenes.editor
    assert scenes.ui.stackedWidget.currentWidget() == scenes.ui.pageEditor
    return scenes


def type_text(qtbot, editor, text: str):
    if isinstance(editor, RichTextEditor):
        textedit = editor.textEdit
    else:
        textedit = editor
    for c in text:
        qtbot.keyPress(textedit, c)
