from unittest.mock import create_autospec

from PyQt6 import QtCore
from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QMouseEvent

from src.main.python.plotlyst.core.domain import ProfileTemplate, fear_field, default_character_profiles
from src.main.python.plotlyst.view.dialog.template import CharacterProfileEditorDialog


def new_diag(qtbot, template: ProfileTemplate) -> CharacterProfileEditorDialog:
    diag = CharacterProfileEditorDialog(template)
    qtbot.addWidget(diag)
    diag.show()
    qtbot.waitExposed(diag, timeout=5000)

    return diag


def drop(qtbot, diag: CharacterProfileEditorDialog):
    qtbot.mouseMove(diag.wdgEditor, QPoint(50, 50))
    qtbot.mouseRelease(diag.wdgEditor, QtCore.Qt.MouseButton.LeftButton, delay=30)


def test_drop(qtbot):
    template = ProfileTemplate(title='Test Template')
    diag = new_diag(qtbot, template)

    for btn, field in [(diag.btnFear, fear_field)]:
        diag._dragged = btn
        event = create_autospec(QMouseEvent)
        event.pos.side_effect = lambda: diag.btnFear.pos()

        QtCore.QTimer.singleShot(30, lambda: drop(qtbot, diag))
        diag.mouseMoveEvent(event)

        qtbot.wait(50)

        assert not btn.isEnabled(), f'Expected disabled button for field {field.name}'
        assert diag.profile_editor.profile().elements
        assert len(diag.profile_editor.profile().elements) == 1
        assert field.id == diag.profile_editor.profile().elements[0].field.id, f'Expected field {field.name}'

        diag.btnRemove.click()

        assert btn.isEnabled()
        assert not diag.profile_editor.profile().elements


def test_default_template(qtbot):
    diag = new_diag(qtbot, default_character_profiles()[0])

    assert not diag.btnEnneagram.isEnabled()
    assert not diag.btnGender.isEnabled()
    assert not diag.btnRole.isEnabled()
    assert not diag.btnGoal.isEnabled()
    assert not diag.btnFear.isEnabled()
    assert not diag.btnDesire.isEnabled()
    assert not diag.btnTraits.isEnabled()
    assert diag.btnMisbelief.isEnabled()
    assert not diag.btnAge.isEnabled()
    assert not diag.btnMbti.isEnabled()

    assert diag.profile_editor.profile().elements
