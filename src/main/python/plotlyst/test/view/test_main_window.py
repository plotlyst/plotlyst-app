from plotlyst.core.client import client
from plotlyst.view.main_window import MainWindow


def assert_views(window: MainWindow, visible: bool = True):
    assert window.btnNovel.isVisible() == visible, 'Novel'
    assert window.btnCharacters.isVisible() == visible, 'Characters'
    assert window.btnScenes.isVisible() == visible, 'Scenes'
    assert window.btnNotes.isVisible() == visible, 'Notes'

    if not visible:
        return

    assert window.btnNovel.isEnabled(), 'Novel enabled'
    assert window.btnCharacters.isEnabled(), 'Characters enabled'
    assert window.btnScenes.isEnabled(), 'Scenes enabled'
    assert window.btnNotes.isEnabled(), 'Notes enabled'


def test_empty_window(qtbot, window: MainWindow):
    assert not client.novels()

    assert window.home_mode.isChecked()
    assert not window.outline_mode.isEnabled()
    assert_views(window, visible=False)


# def test_load_new_empty_novel(qtbot, filled_window: MainWindow):
#     view: HomeView = go_to_home(filled_window)
#     assert len(view.novels()) == 1
#
#     new_title = 'New title'
#     create_novel(filled_window, new_title)
#
#     shelves = view.shelves()
#     assert len(shelves.novels()) == 2
#     shelves.novelSelected.emit(shelves.novels()[1])
#
#     view.ui.btnActivate.click()
#
#     assert_views(filled_window)
#
#     view.ui.btnActivate.click()
#     assert_views(filled_window)


def test_manuscript_mode(qtbot, filled_window: MainWindow):
    filled_window.btnManuscript.click()
