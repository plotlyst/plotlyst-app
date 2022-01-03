from functools import partial

from PyQt6.QtWidgets import QComboBox

from src.main.python.plotlyst.core.domain import VERY_UNHAPPY, UNHAPPY, NEUTRAL, VERY_HAPPY, HAPPY
from src.main.python.plotlyst.model.scenes_model import ScenesTableModel
from src.main.python.plotlyst.test.common import go_to_reports, edit_item, click_on_item
from src.main.python.plotlyst.view.main_window import MainWindow
from src.main.python.plotlyst.view.reports_view import ReportsView


def _test_reports_display(qtbot, filled_window: MainWindow):
    view: ReportsView = go_to_reports(filled_window)
    assert view.ui.tabWidget.currentWidget() == view.ui.tabStorylines
    assert view.ui.tabNestedStorylines.currentWidget() == view.ui.tabStoryMap

    view.ui.storyLinesMap.grab().toImage()
    view.ui.tabWidget.setCurrentWidget(view.ui.tabCharacters)
    # view.ui.tabWidget_2.setCurrentWidget(view.ui.tabCharacterArcs)
    view.ui.tabWidget.setCurrentWidget(view.ui.tabStoryDistribution)


def _edit_arc(value: int, editor: QComboBox):
    editor.setCurrentIndex(value)


def _test_edit_arc(qtbot, filled_window: MainWindow):
    view: ReportsView = go_to_reports(filled_window)

    view.ui.tabWidget.setCurrentWidget(view.ui.tabCharacters)
    view.ui.tabWidget_2.setCurrentWidget(view.ui.tabCharacterArcs)

    edit_item(qtbot, view.ui.tblScenes, 0, ScenesTableModel.ColArc, QComboBox, partial(_edit_arc, 0))
    assert view.novel.scenes[0].pov_arc() == VERY_UNHAPPY

    click_on_item(qtbot, view.ui.tblScenes, 0, ScenesTableModel.ColTitle)

    edit_item(qtbot, view.ui.tblScenes, 0, ScenesTableModel.ColArc, QComboBox, partial(_edit_arc, 1))
    assert view.novel.scenes[0].pov_arc() == UNHAPPY

    click_on_item(qtbot, view.ui.tblScenes, 0, ScenesTableModel.ColTitle)

    edit_item(qtbot, view.ui.tblScenes, 0, ScenesTableModel.ColArc, QComboBox, partial(_edit_arc, 2))
    assert view.novel.scenes[0].pov_arc() == NEUTRAL

    click_on_item(qtbot, view.ui.tblScenes, 0, ScenesTableModel.ColTitle)

    edit_item(qtbot, view.ui.tblScenes, 0, ScenesTableModel.ColArc, QComboBox, partial(_edit_arc, 3))
    assert view.novel.scenes[0].pov_arc() == HAPPY

    click_on_item(qtbot, view.ui.tblScenes, 0, ScenesTableModel.ColTitle)

    edit_item(qtbot, view.ui.tblScenes, 0, ScenesTableModel.ColArc, QComboBox, partial(_edit_arc, 4))
    assert view.novel.scenes[0].pov_arc() == VERY_HAPPY
