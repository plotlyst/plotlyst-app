from typing import List

from PyQt6.QtCharts import QPieSeries
from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMessageBox, QSpinBox

from src.main.python.plotlyst.core.client import client
from src.main.python.plotlyst.model.scenes_model import ScenesTableModel, ScenesStageTableModel
from src.main.python.plotlyst.test.common import create_character, start_new_scene_editor, assert_data, go_to_scenes, \
    click_on_item, popup_actions_on_item, trigger_popup_action_on_item, patch_confirmed
from src.main.python.plotlyst.view.comments_view import CommentWidget
from src.main.python.plotlyst.view.main_window import MainWindow
from src.main.python.plotlyst.view.scenes_view import ScenesOutlineView


def test_create_new_scene(qtbot, filled_window: MainWindow):
    scenes: ScenesOutlineView = start_new_scene_editor(filled_window)

    qtbot.keyClicks(scenes.editor.ui.lineTitle, 'New scene')
    scenes.editor.ui.sbDay.setValue(1)

    scenes.editor.ui.btnClose.click()

    row = scenes.ui.tblScenes.model().rowCount() - 1
    assert_data(scenes.ui.tblScenes.model(), 'New scene', row, 1)
    assert filled_window.novel.scenes
    assert filled_window.novel.scenes[row].title == 'New scene'
    assert filled_window.novel.scenes[row].purpose is None
    assert filled_window.novel.scenes[row].day == 1


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


def test_scene_deletion(qtbot, filled_window: MainWindow, monkeypatch):
    view: ScenesOutlineView = go_to_scenes(filled_window)
    view.ui.btnTableView.click()

    click_on_item(qtbot, view.ui.tblScenes, 0, ScenesTableModel.ColTitle)
    assert view.ui.btnEdit.isEnabled()
    assert view.ui.btnDelete.isEnabled()

    patch_confirmed(monkeypatch, False)
    view.ui.btnDelete.click()
    assert len(view.novel.scenes) == 2
    assert_data(view.tblModel, 'Scene 1', 0, ScenesTableModel.ColTitle)

    patch_confirmed(monkeypatch)
    view.ui.btnDelete.click()
    assert len(view.novel.scenes) == 1
    assert_data(view.tblModel, 'Scene 2', 0, ScenesTableModel.ColTitle)
    assert view.tblModel.rowCount() == 1


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


def test_context_menu(qtbot, filled_window: MainWindow):
    view: ScenesOutlineView = go_to_scenes(filled_window)
    actions: List[QAction] = popup_actions_on_item(qtbot, view.ui.tblScenes, 0, ScenesTableModel.ColTitle)
    assert actions[0].text() == 'Toggle WIP status'
    assert actions[1].text() == 'Insert new scene'
    assert actions[3].text() == 'Delete'


def test_toggle_wip_status(qtbot, filled_window: MainWindow):
    view: ScenesOutlineView = go_to_scenes(filled_window)
    trigger_popup_action_on_item(qtbot, view.ui.tblScenes, 0, ScenesTableModel.ColTitle, 'Toggle WIP status')
    assert view.novel.scenes[0].wip


def test_insert_new_scene_after(qtbot, filled_window: MainWindow):
    view: ScenesOutlineView = go_to_scenes(filled_window)
    trigger_popup_action_on_item(qtbot, view.ui.tblScenes, 0, ScenesTableModel.ColTitle, 'Insert new scene')

    assert len(view.novel.scenes) == 3
    assert_data(view.tblModel, 'Scene 1', 0, ScenesTableModel.ColTitle)
    assert_data(view.tblModel, 'Scene 2', 1, ScenesTableModel.ColTitle)
    assert_data(view.tblModel, 'Scene 2', 2, ScenesTableModel.ColTitle)


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

    view.ui.btnStorymap.click()
    view.storymap_view.grab().toImage()


def test_toggle_story_structure(qtbot, filled_window: MainWindow):
    view: ScenesOutlineView = go_to_scenes(filled_window)

    view.ui.btnStoryStructure.click()

    assert view.ui.wdgStoryStructureParent.isVisible()
    assert view.ui.wdgStoryStructure.isVisible()
    assert view.ui.wdgStoryStructure.novel is view.novel

    view.ui.btnStoryStructure.click()
    assert not view.ui.wdgStoryStructureParent.isVisible()
    assert not view.ui.wdgStoryStructure.isVisible()


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
    assert view.ui.btnStageSelector.text() == '3rd Draft'
    assert view.stagesProgress.stage().text == '3rd Draft'

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

    view.characters_distribution.btnConflicts.click()
    assert not view.characters_distribution.spinAverage.isVisible()

    model = view.characters_distribution.tblSceneDistribution.model()
    assert model.rowCount() == 1

    view.characters_distribution.btnTags.click()
    model = view.characters_distribution.tblSceneDistribution.model()
    assert model.rowCount() == 7


def _test_add_scene_comment(qtbot, filled_window: MainWindow):
    view: ScenesOutlineView = go_to_scenes(filled_window)

    card = view.ui.cards.cardAt(0)
    qtbot.mouseClick(card, Qt.MouseButton.LeftButton)

    filled_window.btnComments.click()
    assert filled_window.wdgSidebar.isVisible()

    filled_window.comments_view.ui.btnNewComment.click()
    assert filled_window.comments_view.ui.wdgComments.layout().count()
    item = filled_window.comments_view.ui.wdgComments.layout().itemAt(0)
    assert item
    assert item.widget()
    comment: CommentWidget = item.widget()

    qtbot.keyClicks(comment.textEditor, 'Comment content')
    assert comment.btnApply.isEnabled()
    comment.btnApply.click()
    assert view.novel.scenes[0].comments
    assert view.novel.scenes[0].comments[0].text == 'Comment content'

    persisted_novel = client.fetch_novel(view.novel.id)
    assert len(persisted_novel.scenes[0].comments) == 1
    assert persisted_novel.scenes[0].comments[0].text == 'Comment content'


def test_scene_cards_resize(qtbot, filled_window: MainWindow):
    view: ScenesOutlineView = go_to_scenes(filled_window)

    assert view.prefs_widget.sliderCards.value() == 175
    view.prefs_widget.sliderCards.setValue(200)
    card = view.ui.cards.cardAt(0)
    assert card.textSynopsis.isVisible()
    assert card.lineAfterTitle.isVisible()
