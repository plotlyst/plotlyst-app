from plotlyst.core.client import client
from plotlyst.core.domain import SceneStoryBeat, save_the_cat
from plotlyst.test.common import create_plot, go_to_novel, patch_confirmed, go_to_scenes
from plotlyst.view.main_window import MainWindow
from plotlyst.view.novel_view import NovelView
from plotlyst.view.widget.structure.template import StoryStructureSelectorDialog


def test_create_plot(qtbot, filled_window: MainWindow):
    view: NovelView = go_to_novel(filled_window)
    create_plot(qtbot, filled_window)

    assert filled_window.novel.plots
    assert filled_window.novel.plots[-1].text == 'Main plot'

    persisted_novel = client.fetch_novel(view.novel.id)
    assert len(persisted_novel.plots) == len(view.novel.plots)
    assert persisted_novel.plots[-1].text == 'Main plot'


def test_delete_plot(qtbot, filled_window: MainWindow, monkeypatch):
    view: NovelView = go_to_novel(filled_window)

    assert len(view.novel.plots) == 3
    plot = view.novel.plots[0]
    assert plot == view.novel.scenes[0].plot_values[0].plot

    patch_confirmed(monkeypatch)
    view.plot_editor.widgetList().plotRemoved.emit(plot)

    assert len(view.novel.plots) == 2
    assert plot not in view.novel.plots
    assert not view.novel.scenes[0].plot_values


def test_change_structure(qtbot, filled_window: MainWindow, monkeypatch):
    view: NovelView = go_to_novel(filled_window)
    view.novel.scenes[0].beats.append(
        SceneStoryBeat(view.novel.active_story_structure.id, view.novel.active_story_structure.beats[0].id))

    btn = view.ui.wdgStructure.btnGroupStructure.buttons()[0]
    assert btn.isChecked() and btn.text() == 'Three Act Structure'

    monkeypatch.setattr(StoryStructureSelectorDialog, "popup", lambda *args: save_the_cat)
    view.ui.wdgStructure.btnNew.menu().actions()[0].trigger()
    btn = view.ui.wdgStructure.btnGroupStructure.buttons()[1]
    btn.click()

    assert view.novel.active_story_structure == save_the_cat

    for scene in view.novel.scenes:
        assert scene.beat(view.novel) is None

    go_to_scenes(filled_window)

    persisted_novel = client.fetch_novel(view.novel.id)
    assert persisted_novel.active_story_structure == view.novel.active_story_structure
