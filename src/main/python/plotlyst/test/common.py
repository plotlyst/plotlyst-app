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
from typing import Any, List

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import Qt, QPoint, QAbstractItemModel, QCoreApplication, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QAbstractItemView, QMenu, QMessageBox, QDialog, QApplication

from src.main.python.plotlyst.model.common import SelectionItemsModel
from src.main.python.plotlyst.view.characters_view import CharactersView
from src.main.python.plotlyst.view.dialog.novel import NovelEditionDialog, PlotEditorDialog
from src.main.python.plotlyst.view.docs_view import DocumentsView
from src.main.python.plotlyst.view.home_view import HomeView
from src.main.python.plotlyst.view.main_window import MainWindow
from src.main.python.plotlyst.view.novel_view import NovelView
from src.main.python.plotlyst.view.reports_view import ReportsView
from src.main.python.plotlyst.view.scenes_view import ScenesOutlineView


def show_widget(qtbot, widget):
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget, timeout=5000)


def click_on_item(qtbot, view: QAbstractItemView, row: int, column: int = 0, parent=None, modifier=Qt.NoModifier):
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


def patch_confirmed(monkeypatch, answer=QMessageBox.StandardButton.Yes):
    monkeypatch.setattr(QMessageBox, "question", lambda *args: answer)  # confirm


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
    window.btnCharacters.setChecked(True)
    return window.characters_view


def go_to_novel(window: MainWindow) -> NovelView:
    window.btnNovel.setChecked(True)
    return window.novel_view


def go_to_home(window: MainWindow) -> HomeView:
    window.btnHome.setChecked(True)
    return window.home_view


def go_to_reports(window: MainWindow) -> ReportsView:
    window.reports_mode.setChecked(True)
    return window.reports_view


def go_to_docs(window: MainWindow) -> DocumentsView:
    window.btnNotes.setChecked(True)
    return window.notes_view


def edit_novel_dialog(new_title: str):
    dialog: QDialog = QApplication.instance().activeModalWidget()
    try:
        assert isinstance(dialog, NovelEditionDialog)
        edition_dialog: NovelEditionDialog = dialog
        edition_dialog.lineTitle.setText(new_title)
        edition_dialog.btnConfirm.click()
    finally:
        dialog.close()


def create_novel(window: MainWindow, title: str):
    view: HomeView = go_to_home(window)
    QTimer.singleShot(40, lambda: edit_novel_dialog(title))
    view.ui.btnAdd.click()


def create_character(qtbot, window: MainWindow, name: str):
    characters: CharactersView = go_to_characters(window)

    characters.ui.btnNew.click()
    assert characters.editor

    characters.editor.profile.setName(name)

    characters.editor.ui.btnClose.click()


def edit_plot_dialog(text: str):
    dialog: QDialog = QApplication.instance().activeModalWidget()
    try:
        assert isinstance(dialog, PlotEditorDialog)
        edition_dialog: PlotEditorDialog = dialog
        edition_dialog.lineKeyphrase.setText(text)
        edition_dialog.btnSave.click()
    finally:
        dialog.close()


def create_plot(qtbot, window: MainWindow, text: str):
    novels: NovelView = go_to_novel(window)

    QTimer.singleShot(40, lambda: edit_plot_dialog(text))
    novels.ui.wdgDramaticQuestions.btnAdd.click()
    # row = novels.ui.wdgDramaticQuestions.model.rowCount() - 1
    # index = novels.ui.wdgDramaticQuestions.model.index(row, SelectionItemsModel.ColName)
    # editor = novels.ui.wdgDramaticQuestions.tableView.indexWidget(index)
    # assert editor, "Editor should be open"
    # assert isinstance(editor, QLineEdit)

    # qtbot.keyClicks(editor, text)
    # novels.ui.wdgDramaticQuestions.tableView.itemDelegate().commitData.emit(editor)
    # novels.ui.wdgDramaticQuestions.tableView.itemDelegate().closeEditor.emit(editor)

    assert_data(novels.ui.wdgDramaticQuestions.model, text, novels.ui.wdgDramaticQuestions.model.rowCount() - 1,
                SelectionItemsModel.ColName)


def start_new_scene_editor(window: MainWindow) -> ScenesOutlineView:
    scenes: ScenesOutlineView = go_to_scenes(window)
    scenes.ui.btnNew.click()
    assert scenes.editor
    assert scenes.ui.stackedWidget.currentWidget() == scenes.ui.pageEditor
    return scenes
