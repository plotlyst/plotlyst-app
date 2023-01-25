from src.main.python.plotlyst.core.client import client
from src.main.python.plotlyst.test.common import go_to_home, patch_confirmed, go_to_novel, type_text
from src.main.python.plotlyst.view.home_view import HomeView
from src.main.python.plotlyst.view.main_window import MainWindow
from src.main.python.plotlyst.view.novel_view import NovelView


def test_delete_novel(qtbot, filled_window: MainWindow, monkeypatch):
    view: HomeView = go_to_home(filled_window)
    assert view.ui.stackWdgNovels.currentWidget() == view.ui.pageEmpty

    shelves = view.shelves()
    assert len(shelves.novels()) == 1
    shelves.novelSelected.emit(shelves.novels()[0])
    assert view.ui.stackWdgNovels.currentWidget() == view.ui.pageNovelDisplay

    patch_confirmed(monkeypatch)
    view.ui.btnNovelSettings.menu().actions()[0].trigger()

    assert len(shelves.novels()) == 0


def test_edit_novel(qtbot, filled_window: MainWindow):
    view: HomeView = go_to_home(filled_window)

    shelves = view.shelves()
    novel = shelves.novels()[0]
    assert len(shelves.novels()) == 1
    shelves.novelSelected.emit(novel)
    assert view.ui.stackWdgNovels.currentWidget() == view.ui.pageNovelDisplay

    assert view.ui.lineNovelTitle.text() == novel.title
    new_title = 'New title'
    view.ui.lineNovelTitle.clear()
    type_text(qtbot, view.ui.lineNovelTitle, new_title)
    assert client.novels()[0].title == new_title

    novel_view: NovelView = go_to_novel(filled_window)
    assert novel_view.ui.lblTitle.text() == new_title
