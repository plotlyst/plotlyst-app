from PyQt6.QtCharts import QPieSeries
from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtWidgets import QSpinBox

from plotlyst.model.scenes_model import ScenesTableModel, ScenesStageTableModel
from plotlyst.test.common import create_character, start_new_scene_editor, assert_data, go_to_scenes, \
    click_on_item
from plotlyst.view.main_window import MainWindow
from plotlyst.view.scenes_view import ScenesOutlineView


def test_scene_characters(qtbot, filled_window: MainWindow):
    create_character(qtbot, filled_window, 'Tom')
    create_character(qtbot, filled_window, 'Bob')

    view: ScenesOutlineView = start_new_scene_editor(filled_window)
    qtbot.keyClicks(view.editor.ui.lineTitle, 'Scene 3')
    view.editor._povMenu.refresh()
    actions = view.editor.ui.wdgPov.btnAvatar.menu().actions()
    actions[5].trigger()
    view.editor.ui.btnClose.click()
    assert view.novel.scenes[2].pov == view.novel.characters[5]

    view: ScenesOutlineView = start_new_scene_editor(filled_window)
    qtbot.keyClicks(view.editor.ui.lineTitle, 'Scene 4')
    actions = view.editor.ui.wdgPov.btnAvatar.menu().actions()
    actions[6].trigger()
    view.editor.ui.btnClose.click()
    assert view.novel.scenes[3].pov == view.novel.characters[6]


def test_scene_edition(qtbot, filled_window: MainWindow):
    view: ScenesOutlineView = go_to_scenes(filled_window)
    view.ui.btnTableView.click()
    click_on_item(qtbot, view.ui.tblScenes, 0, ScenesTableModel.ColTitle)
    assert view.ui.btnEdit.isEnabled()

    view.ui.btnEdit.click()
    assert view.editor

    title = 'New scene title'
    view.editor.ui.lineTitle.clear()
    qtbot.keyClicks(view.editor.ui.lineTitle, title)
    view.editor.ui.btnClose.click()

    assert_data(view.tblModel, title, 0, ScenesTableModel.ColTitle)


def test_switch_views(qtbot, filled_window: MainWindow):
    view: ScenesOutlineView = go_to_scenes(filled_window)

    view.ui.btnTableView.click()
    assert view.ui.tblScenes.verticalHeader().isVisible()

    view.ui.btnStatusView.click()
    assert view.stagesModel
    assert view.stagesProgress
    assert view.ui.tblSceneStages.verticalHeader().isVisible()
    charts = view.stagesProgress.charts()
    assert len(charts) == 4
    pie_series: QPieSeries = charts[0].chart.series()[0]
    assert pie_series.count() == 2
    assert pie_series.slices()[0].percentage() == 0.5


def test_change_stage(qtbot, filled_window: MainWindow):
    view: ScenesOutlineView = go_to_scenes(filled_window)

    view.ui.btnStatusView.click()
    assert view.stagesModel
    assert view.stagesProgress

    click_on_item(qtbot, view.ui.tblSceneStages, 0, ScenesStageTableModel.ColNoneStage)

    assert view.novel.scenes[0].stage is None

    charts = view.stagesProgress.charts()
    assert len(charts) == 4
    pie_series: QPieSeries = charts[0].chart.series()[0]
    assert pie_series.count() == 2
    assert pie_series.slices()[0].percentage() == 0.0

    click_on_item(qtbot, view.ui.tblSceneStages, 0, ScenesStageTableModel.ColNoneStage + 2)
    assert view.novel.scenes[0].stage == view.novel.stages[1]

    pie_series = charts[0].chart.series()[0]
    assert pie_series.slices()[0].percentage() == 0.5

    click_on_item(qtbot, view.ui.tblSceneStages, 0, ScenesStageTableModel.ColNoneStage + 3)
    assert view.novel.scenes[0].stage == view.novel.stages[2]

    pie_series = charts[0].chart.series()[0]
    assert pie_series.slices()[0].percentage() == 0.5

    view.ui.btnStageSelector.menu().actions()[0].trigger()
    assert view.ui.btnStageSelector.text() == 'Outlined'
    assert view.stagesProgress.stage().text == 'Outlined'

    view.ui.btnStageSelector.menu().actions()[3].trigger()
    assert view.ui.btnStageSelector.text() == 'Mid-revision'
    assert view.stagesProgress.stage().text == 'Mid-revision'

    charts = view.stagesProgress.charts()
    pie_series: QPieSeries = charts[0].chart.series()[0]
    assert pie_series.slices()[0].percentage() == 0.0


def _edit_day(editor: QSpinBox):
    editor.setValue(3)


def test_character_distribution_display(qtbot, filled_window: MainWindow):
    def assert_painted(index: QModelIndex):
        assert index.data(role=Qt.ItemDataRole.BackgroundRole) is not None

    def assert_not_painted(index: QModelIndex):
        assert index.data(role=Qt.ItemDataRole.BackgroundRole) is None

    view: ScenesOutlineView = go_to_scenes(filled_window)
    view.ui.btnCharactersDistributionView.click()

    assert view.characters_distribution.spinAverage.value() == 3
    model = view.characters_distribution.tblSceneDistribution.model()
    assert_painted(model.index(0, 2))
    assert_painted(model.index(0, 3))
    assert_painted(model.index(1, 2))
    assert_painted(model.index(1, 3))
    assert_painted(model.index(2, 2))
    assert_not_painted(model.index(2, 3))
    assert_not_painted(model.index(3, 2))
    assert_painted(model.index(3, 3))
    assert_not_painted(model.index(4, 2))
    assert_not_painted(model.index(4, 3))

    # click brushed scene cell
    click_on_item(qtbot, view.characters_distribution.tblSceneDistribution, 0, 2)
    assert model.flags(model.index(3, 1)) == Qt.ItemFlag.NoItemFlags
    assert model.flags(model.index(4, 1)) == Qt.ItemFlag.NoItemFlags

    # click empty area
    click_on_item(qtbot, view.characters_distribution.tblSceneDistribution, 3, 2)
    assert model.flags(model.index(3, 1)) & Qt.ItemFlag.ItemIsEnabled
    assert model.flags(model.index(4, 1)) & Qt.ItemFlag.ItemIsEnabled

    view.characters_distribution.btnTags.click()
    model = view.characters_distribution.tblSceneDistribution.model()
    assert model.rowCount() == 7


def test_scene_cards_resize(qtbot, filled_window: MainWindow):
    view: ScenesOutlineView = go_to_scenes(filled_window)

    assert view.prefs_widget.sliderCards.value() == 175
    view.prefs_widget.sliderCards.setValue(200)
    card = view.ui.cards.cardAt(0)
    assert card.textSynopsis.isVisible()
    assert card.lineAfterTitle.isVisible()
