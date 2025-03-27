from plotlyst.core.client import client
from plotlyst.test.common import go_to_home, patch_confirmed, go_to_novel, type_text
from plotlyst.view.home_view import HomeView
from plotlyst.view.main_window import MainWindow
from plotlyst.view.novel_view import NovelView


def test_delete_novel(qtbot, filled_window: MainWindow, monkeypatch):
    view: HomeView = go_to_home(filled_window)
    assert view.ui.stackWdgNovels.currentWidget() == view.ui.pageEmpty

    shelves = view.shelves()
    assert len(shelves.novels()) == 1
    shelves.novelSelected.emit(shelves.novels()[0])
    assert view.ui.stackWdgNovels.currentWidget() == view.ui.pageNovelDisplay

    patch_confirmed(monkeypatch)
    view.novelDisplayCard.btnNovelSettings.menu().actions()[0].trigger()

    assert len(shelves.novels()) == 0


def test_edit_novel(qtbot, filled_window: MainWindow):
    view: HomeView = go_to_home(filled_window)

    shelves = view.shelves()
    novel = shelves.novels()[0]
    assert len(shelves.novels()) == 1
    shelves.novelSelected.emit(novel)
    assert view.ui.stackWdgNovels.currentWidget() == view.ui.pageNovelDisplay

    assert view.novelDisplayCard.lineNovelTitle.text() == novel.title
    new_title = 'New title'
    view.novelDisplayCard.lineNovelTitle.clear()
    type_text(qtbot, view.novelDisplayCard.lineNovelTitle, new_title)
    assert client.novels()[0].title == new_title

    novel_view: NovelView = go_to_novel(filled_window)
    assert novel_view.wdgDescriptors.lineNovelTitle.text() == new_title
