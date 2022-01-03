from PyQt6.QtCore import QModelIndex

from src.main.python.plotlyst.core.client import json_client, client
from src.main.python.plotlyst.test.common import go_to_docs, click_on_item, trigger_action_on_popup
from src.main.python.plotlyst.view.docs_view import DocumentsView
from src.main.python.plotlyst.view.main_window import MainWindow


def test_docs_display(qtbot, filled_window: MainWindow):
    view: DocumentsView = go_to_docs(filled_window)

    click_on_item(qtbot, view.ui.treeDocuments, 0, 0, QModelIndex())
    qtbot.keyClicks(view.textEditor.textEditor, 'Test content')

    json_client.load_document(view.novel, view.novel.documents[0])
    assert 'Test content' in view.novel.documents[0].content


def test_add_new_doc(qtbot, filled_window: MainWindow):
    view: DocumentsView = go_to_docs(filled_window)
    previous_size = len(view.novel.documents)

    view.ui.btnAdd.click()
    click_on_item(qtbot, view.ui.treeDocuments, 0, 2, QModelIndex())
    trigger_action_on_popup(qtbot, 'Document')

    persisted_novel = client.fetch_novel(view.novel.id)
    assert previous_size + 1 == len(persisted_novel.documents)
    assert persisted_novel.documents[-1].title == 'New Document'

    assert len(persisted_novel.documents[0].children) == 1


def test_add_new_reversed_cause_and_effect_doc(qtbot, filled_window: MainWindow):
    view: DocumentsView = go_to_docs(filled_window)
    click_on_item(qtbot, view.ui.treeDocuments, 0, 2, QModelIndex())
    trigger_action_on_popup(qtbot, 'Reversed Cause and Effect')
