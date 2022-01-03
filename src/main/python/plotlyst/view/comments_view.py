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
from typing import Optional

from PyQt6.QtCore import QEvent, pyqtSignal, Qt
from PyQt6.QtWidgets import QFrame
from overrides import overrides

from src.main.python.plotlyst.core.domain import Novel, Comment, Scene, Event
from src.main.python.plotlyst.events import SceneSelectedEvent, SceneSelectionClearedEvent
from src.main.python.plotlyst.view._view import AbstractNovelView
from src.main.python.plotlyst.view.common import ask_confirmation
from src.main.python.plotlyst.view.generated.comment_widget_ui import Ui_CommentWidget
from src.main.python.plotlyst.view.generated.comments_view_ui import Ui_CommentsView
from src.main.python.plotlyst.view.icons import IconRegistry


class CommentsView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super(CommentsView, self).__init__(novel, [SceneSelectedEvent, SceneSelectionClearedEvent])
        self.ui = Ui_CommentsView()
        self.ui.setupUi(self.widget)
        self.ui.btnNewComment.setIcon(IconRegistry.from_name('mdi.comment-plus-outline', color='#2e86ab'))
        self.ui.btnNewComment.clicked.connect(self._new_comment)
        self.ui.btnNewComment.setDisabled(True)
        self.ui.btnNewComment.setToolTip('Select a scene to add comment')

        self._selected_scene: Optional[Scene] = None
        self.ui.cbShowAll.toggled.connect(self._update_comments)
        self.ui.cbShowAll.setChecked(True)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, SceneSelectedEvent):
            self._selected_scene = event.scene
            self.ui.btnNewComment.setEnabled(True)
            self.ui.btnNewComment.setToolTip(f'Add scene comment to "{self._selected_scene.title}"')
            if not self.ui.cbShowAll.isChecked():
                self._update_comments()
        elif isinstance(event, SceneSelectionClearedEvent):
            self._selected_scene = None
            self.ui.btnNewComment.setEnabled(False)
            self.ui.btnNewComment.setToolTip('Select a scene to add comment')
            self._update_comments()
        else:
            super(CommentsView, self).event_received(event)

    @overrides
    def refresh(self):
        pass

    def _update_comments(self, show_all: bool = False):
        while self.ui.wdgComments.layout().count():
            item = self.ui.wdgComments.layout().takeAt(0)
            if item:
                item.widget().deleteLater()

        if show_all:
            for scene in self.novel.scenes:
                for comment in scene.comments:
                    self._addComment(comment, scene)
        elif self._selected_scene:
            for comment in self._selected_scene.comments:
                self._addComment(comment, self._selected_scene)

    def _new_comment(self):
        comment = Comment('')
        if self._selected_scene:
            self._selected_scene.comments.append(comment)
        wdg = self._addComment(comment, self._selected_scene)
        wdg.edit()

    def _addComment(self, comment: Comment, scene: Optional[Scene] = None) -> 'CommentWidget':
        comment_wdg = CommentWidget(self.novel, comment, scene)
        self.ui.wdgComments.layout().addWidget(comment_wdg, alignment=Qt.AlignmentFlag.AlignCenter)
        comment_wdg.changed.connect(self._comment_changed)
        comment_wdg.removed.connect(self._comment_removed)

        return comment_wdg

    def _comment_changed(self, comment_wdg: 'CommentWidget'):
        if comment_wdg.scene:
            self.repo.update_scene(comment_wdg.scene)

    def _comment_removed(self, comment_wdg: 'CommentWidget'):
        if not ask_confirmation('Remove comment?'):
            return
        self.ui.wdgComments.layout().removeWidget(comment_wdg)
        if comment_wdg.scene:
            comment_wdg.scene.comments.remove(comment_wdg.comment)
            self.repo.update_scene(comment_wdg.scene)
        comment_wdg.deleteLater()


class CommentWidget(QFrame, Ui_CommentWidget):
    removed = pyqtSignal(object)
    changed = pyqtSignal(object)

    width: int = 200
    height: int = 100

    def __init__(self, novel: Novel, comment: Comment, scene: Optional[Scene] = None, parent=None):
        super(CommentWidget, self).__init__(parent)
        self.setupUi(self)
        self.novel = novel
        self.comment = comment
        self.scene: Optional[Scene] = scene

        self._edit_mode: bool = False

        self.setFixedSize(self.width, self.height)

        self.btnResolve.setHidden(True)

        self.btnEdit.setIcon(IconRegistry.edit_icon())
        self.btnEdit.clicked.connect(self.edit)
        self.btnEdit.setHidden(True)

        self.btnDelete.setIcon(IconRegistry.wrong_icon())
        self.btnDelete.clicked.connect(self._remove)
        self.btnDelete.setHidden(True)

        self.btnMajor.setHidden(True)
        self.btnMajor.toggled.connect(self._major_toggled)
        self.btnMajor.setIcon(IconRegistry.from_name('fa5s.exclamation', color='#fb8b24'))

        self.btnApply.setIcon(IconRegistry.ok_icon())
        self.btnApply.clicked.connect(self._apply)
        self.btnApply.setHidden(True)

        self.btnCancel.setIcon(IconRegistry.cancel_icon())
        self.btnCancel.clicked.connect(self._toggle_editor_mode)
        self.btnCancel.setHidden(True)

        self.textEditor.setHidden(True)
        self.textEditor.textChanged.connect(lambda: self.btnApply.setEnabled(len(self.textEditor.toPlainText()) > 0))

        self.textComment.setText(self.comment.text)
        self.btnMajor.setChecked(self.comment.major)
        self.btnMajor.clicked.connect(self._updateStyleSheet)

        self._updateStyleSheet()

    def _updateStyleSheet(self):
        if self.btnMajor.isChecked():
            border = 2
            border_color = '#fb8b24'
        else:
            border = 1
            border_color = '#3066be'
        self.setStyleSheet(f'''
        QFrame[mainFrame=true] {{
               border: {border}px solid {border_color};
               border-radius: 15px;
               background-color: white;
           }}''')

    @overrides
    def enterEvent(self, event: QEvent) -> None:
        if self._edit_mode:
            return
        self.btnEdit.setVisible(True)
        self.btnDelete.setVisible(True)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        if self._edit_mode:
            return
        self.btnEdit.setHidden(True)
        self.btnDelete.setHidden(True)

    def edit(self):
        self._toggle_editor_mode(True)
        self.textEditor.setPlainText(self.textComment.toPlainText())
        self.textEditor.setVisible(True)
        self.textComment.setHidden(True)
        self.textEditor.setFocus()

    def _remove(self):
        self.removed.emit(self)

    def _major_toggled(self, toggled: bool):
        self.comment.major = toggled

    def _apply(self):
        self.comment.text = self.textEditor.toPlainText()
        self.comment.major = self.btnMajor.isChecked()
        self.textComment.setPlainText(self.comment.text)

        self._toggle_editor_mode()
        self.changed.emit(self)

    def _toggle_editor_mode(self, edit: bool = False):
        if edit:
            self.setFixedSize(self.width, self.height + 30)
        else:
            self.setFixedSize(self.width, self.height)
        self.btnApply.setVisible(edit)
        self.btnCancel.setVisible(edit)
        self.btnMajor.setVisible(edit)
        self.textEditor.setVisible(edit)
        self.textComment.setHidden(edit)
        self.btnEdit.setHidden(edit)
        self.btnDelete.setHidden(edit)
        self._edit_mode = edit

        if not edit and not self.textComment.toPlainText():
            self.removed.emit(self)
