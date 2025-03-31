"""
Plotlyst
Copyright (C) 2021-2024  Zsolt Kovari

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
from enum import Enum, auto
from functools import partial
from typing import Optional, Dict

import qtanim
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QResizeEvent, QAction, QIcon
from PyQt6.QtWidgets import QWidget, QButtonGroup, QStackedWidget, QTextEdit
from overrides import overrides
from qthandy import vbox, hbox, spacer, sp, flow, vline, clear_layout, bold, incr_font, italic, translucent, line, \
    vspacer, incr_icon, margins, retain_when_hidden, decr_icon, decr_font
from qthandy.filter import OpacityEventFilter, VisibilityToggleEventFilter, InstantTooltipEventFilter
from qtmenu import MenuWidget, ActionTooltipDisplayMode

from plotlyst.common import PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import Novel, Scene, ReaderQuestion, SceneReaderQuestion, ReaderQuestionType, \
    ReaderInformationType, SceneReaderInformation
from plotlyst.env import app_env
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import push_btn, link_buttons_to_pages, shadow, scroll_area, \
    insert_before_the_end, wrap, fade_out_and_gc, action, label, scrolled, tool_btn
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import apply_white_menu
from plotlyst.view.widget.button import DotsMenuButton
from plotlyst.view.widget.confirm import confirmed
from plotlyst.view.widget.display import LazyWidget, Icon, IconText
from plotlyst.view.widget.input import RemovalButton


class QuestionState(Enum):
    Raised_before = auto()
    Raised_now = auto()
    Resolved_before = auto()
    Resolved_now = auto()
    Detached = auto()


class ReaderQuestionTypeMenu(MenuWidget):
    selected = pyqtSignal(ReaderQuestionType)

    def __init__(self, parent=None):
        super().__init__(parent)

        apply_white_menu(self)

        self._actions: Dict[ReaderQuestionType, QAction] = {}
        self.addSection('Associate an optional tag to this question')
        self.addSeparator()
        self._addAction(ReaderQuestionType.General)
        self._addAction(ReaderQuestionType.Plot)
        self._addAction(ReaderQuestionType.Character_growth)
        self._addAction(ReaderQuestionType.Backstory)
        self._addAction(ReaderQuestionType.Internal_conflict)
        self._addAction(ReaderQuestionType.Relationship)
        self._addAction(ReaderQuestionType.Character_motivation)
        self._addAction(ReaderQuestionType.Wonder)
        # self._addAction(ReaderQuestionType.Conflict_resolution)

        self.setTooltipDisplayMode(ActionTooltipDisplayMode.DISPLAY_UNDER)

    def setTypeDisabled(self, type_: ReaderQuestionType):
        for v in self._actions.values():
            v.setEnabled(True)

        self._actions[type_].setDisabled(True)

    def _addAction(self, type_: ReaderQuestionType):
        action_ = action(type_.display_name(), icon=IconRegistry.from_name(type_.icon()), tooltip=type_.description(),
                         slot=partial(self.selected.emit, type_))
        self.addAction(action_)
        self._actions[type_] = action_
        return action_


class ReaderQuestionWidget(QWidget):
    resolved = pyqtSignal()
    unresolved = pyqtSignal()
    changed = pyqtSignal()
    detached = pyqtSignal()
    removed = pyqtSignal()
    resurrect = pyqtSignal()

    def __init__(self, question: ReaderQuestion, state: QuestionState, ref: Optional[SceneReaderQuestion] = None,
                 parent=None):
        super().__init__(parent)
        self.question = question
        self.scene_ref = ref
        self.state = state
        self.new = self.state in [QuestionState.Raised_now, QuestionState.Resolved_now]

        vbox(self, 10)
        self._label = push_btn(
            IconRegistry.from_name('ei.question-sign', PLOTLYST_SECONDARY_COLOR if self.new else 'black'), 'Question',
            transparent_=True)
        if self.state == QuestionState.Resolved_before:
            translucent(self._label)
        bold(self._label, self.new)
        self._label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._menuTypes = ReaderQuestionTypeMenu(self._label)
        self._menuTypes.selected.connect(self._typeChanged)

        self.textedit = QTextEdit(self)
        self.textedit.setProperty('white-bg', True)
        self.textedit.setProperty('rounded', True)
        self.textedit.setPlaceholderText("Describe what piques the reader's interest")
        self.textedit.setTabChangesFocus(True)
        if app_env.is_mac():
            incr_font(self.textedit)
        self.textedit.setMinimumSize(170, 100)
        self.textedit.setMaximumSize(190, 120)
        self.textedit.verticalScrollBar().setVisible(False)
        if self.new:
            shadow(self.textedit, color=QColor(PLOTLYST_SECONDARY_COLOR))
        elif self.state == QuestionState.Resolved_before:
            shadow(self.textedit, color=QColor('lightgrey'))
        else:
            shadow(self.textedit)
        self.textedit.setText(self.question.text)
        self.textedit.textChanged.connect(self._questionChanged)

        self.layout().addWidget(self._label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.textedit)

        self.badgeType = Icon(self)
        self.badgeType.setGeometry(10, 10, 17, 17)
        self._updateTypeIcon()

        if self.state == QuestionState.Raised_now or self.state == QuestionState.Resolved_now:
            badge = push_btn(IconRegistry.from_name('ei.star-alt', color=PLOTLYST_SECONDARY_COLOR), 'New!',
                             icon_resize=False, pointy_=False)
            badge.installEventFilter(InstantTooltipEventFilter(badge))
            badge.setStyleSheet(f'border: 0px; color: {PLOTLYST_SECONDARY_COLOR}')
            italic(badge)
            self.layout().addWidget(badge, alignment=Qt.AlignmentFlag.AlignLeft)
            if self.state == QuestionState.Resolved_now:
                badge.setToolTip("This question is being resolved in this scene")
                unresolve = push_btn(
                    IconRegistry.from_name('mdi.sticker-remove-outline', color='grey'), 'Unresolve', transparent_=True)
                unresolve.installEventFilter(OpacityEventFilter(unresolve))
                unresolve.clicked.connect(self.unresolved)
                self.layout().addWidget(unresolve, alignment=Qt.AlignmentFlag.AlignCenter)
            else:
                badge.setToolTip("This question is being raised in this scene")
        elif self.state == QuestionState.Raised_before:
            resolve = push_btn(
                IconRegistry.from_name('mdi.sticker-check-outline', color=PLOTLYST_SECONDARY_COLOR), 'Resolve')
            resolve.setStyleSheet(f'border:opx; color: {PLOTLYST_SECONDARY_COLOR};')
            resolve.installEventFilter(OpacityEventFilter(resolve, leaveOpacity=0.5))
            resolve.clicked.connect(self.resolved)
            self.layout().addWidget(resolve, alignment=Qt.AlignmentFlag.AlignCenter)
        elif self.state == QuestionState.Resolved_before:
            resurrect = push_btn(
                IconRegistry.from_name('mdi.progress-question', color=PLOTLYST_SECONDARY_COLOR), 'Resurrect')
            resurrect.setStyleSheet(f'border:opx; color: {PLOTLYST_SECONDARY_COLOR};')
            resurrect.installEventFilter(OpacityEventFilter(resurrect, leaveOpacity=0.5))
            resurrect.clicked.connect(self.resurrect)
            self.layout().addWidget(resurrect, alignment=Qt.AlignmentFlag.AlignCenter)

        if self.scene_ref:
            self.btnRemove = RemovalButton(self)
            self.btnRemove.setHidden(True)
            self.btnRemove.clicked.connect(self.detached)
            self.installEventFilter(VisibilityToggleEventFilter(self.btnRemove, self))
        else:
            self.btnOptions = DotsMenuButton(self)
            self.btnOptions.setHidden(True)
            menu = MenuWidget(self.btnOptions)
            menu.addAction(action('Delete', IconRegistry.trash_can_icon(), slot=self.removed))
            self.installEventFilter(VisibilityToggleEventFilter(self.btnOptions, self))

        sp(self).v_max()

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        if self.scene_ref:
            self.btnRemove.setGeometry(event.size().width() - 20, 1, 10, 10)
        else:
            self.btnOptions.setGeometry(event.size().width() - 25, 4, 20, 20)

    def _questionChanged(self):
        self.question.text = self.textedit.toPlainText()
        self.changed.emit()

    def _typeChanged(self, type_: ReaderQuestionType):
        self.question.type = type_
        self._updateTypeIcon()
        self.changed.emit()

    def _updateTypeIcon(self):
        if self.question.type == ReaderQuestionType.General:
            self.badgeType.setHidden(True)
        else:
            self.badgeType.setIcon(IconRegistry.from_name(self.question.type.icon(), PLOTLYST_SECONDARY_COLOR))
            self.badgeType.setVisible(True)

        self._menuTypes.setTypeDisabled(self.question.type)


class ReaderCuriosityEditor(LazyWidget):
    LABEL_RAISED_QUESTIONS = 'Raised questions'
    LABEL_RESOLVED_QUESTIONS = 'Resolved questions'
    LABEL_FUTURE_QUESTIONS = 'Future questions'

    DESC_RAISED_QUESTIONS = "Questions and mysteries that create narrative drive by raising curiosity in the reader. These questions were raised in this or prior scenes and yet remain unresolved."
    DESC_RESOLVED_QUESTIONS = "Questions that have been resolved in the narrative. They don't pique interest in the reader anymore. "
    DESC_FUTURE_QUESTIONS = "Questions that are introduced in later scenes. At this point, the reader is not aware of them."

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._scene: Optional[Scene] = None

        vbox(self, 10, 8)
        self.wdgHeader = QWidget()
        hbox(self.wdgHeader)

        self.btnUnresolved = push_btn(
            IconRegistry.from_name('ei.question-sign', 'lightgrey', color_on=PLOTLYST_SECONDARY_COLOR),
            text=self.LABEL_RAISED_QUESTIONS,
            properties=['secondary-selector', 'transparent-magnolia-rounded-bg-on-hover',
                        'transparent-rounded-bg-on-hover'],
            checkable=True)
        self.btnResolved = push_btn(
            IconRegistry.from_name('mdi.sticker-check', 'lightgrey', color_on=PLOTLYST_SECONDARY_COLOR),
            text=self.LABEL_RESOLVED_QUESTIONS,
            properties=['secondary-selector', 'transparent-magnolia-rounded-bg-on-hover',
                        'transparent-rounded-bg-on-hover'],
            checkable=True)
        self.btnOther = push_btn(
            IconRegistry.from_name('ph.link-simple-break-bold', 'lightgrey', color_on=PLOTLYST_SECONDARY_COLOR),
            text=self.LABEL_FUTURE_QUESTIONS,
            properties=['secondary-selector', 'transparent-magnolia-rounded-bg-on-hover',
                        'transparent-rounded-bg-on-hover'],
            checkable=True)

        self.btnGroup = QButtonGroup()
        self.btnGroup.setExclusive(True)
        self.btnGroup.addButton(self.btnUnresolved)
        self.btnGroup.addButton(self.btnResolved)
        self.btnGroup.addButton(self.btnOther)

        self.btnUnresolved.setChecked(True)

        self.wdgHeader.layout().addWidget(self.btnUnresolved)
        self.wdgHeader.layout().addWidget(self.btnResolved)
        self.wdgHeader.layout().addWidget(vline())
        self.wdgHeader.layout().addWidget(self.btnOther)
        self.wdgHeader.layout().addWidget(spacer())

        self.btnAddNew = push_btn(IconRegistry.plus_icon('grey'), 'Raise new question', transparent_=True)
        self.btnAddNew.installEventFilter(OpacityEventFilter(self.btnAddNew, 0.8, 0.5))
        self.btnAddNew.clicked.connect(self._addNew)

        self.wdgEditor = QStackedWidget()
        sp(self.wdgEditor).v_exp()

        self.pageQuestions = scroll_area(h_on=False, frameless=True)
        self.pageQuestionsEditor = QWidget()
        self.pageQuestionsEditor.setProperty('relaxed-white-bg', True)
        self.pageQuestions.setWidget(self.pageQuestionsEditor)
        flow(self.pageQuestionsEditor, 5, 7)
        self.wdgEditor.addWidget(self.pageQuestions)

        self.pageResolvedQuestions = scroll_area(h_on=False, frameless=True)
        self.pageResolvedQuestionsEditor = QWidget()
        self.pageResolvedQuestionsEditor.setProperty('relaxed-white-bg', True)
        self.pageResolvedQuestions.setWidget(self.pageResolvedQuestionsEditor)
        flow(self.pageResolvedQuestionsEditor, 5, 8)
        self.wdgEditor.addWidget(self.pageResolvedQuestions)

        self.pageDetachedQuestions = scroll_area(h_on=False, frameless=True)
        self.pageDetachedQuestionsEditor = QWidget()
        self.pageDetachedQuestionsEditor.setProperty('relaxed-white-bg', True)
        self.pageDetachedQuestions.setWidget(self.pageDetachedQuestionsEditor)
        flow(self.pageDetachedQuestionsEditor, 5, 8)
        self.wdgEditor.addWidget(self.pageDetachedQuestions)

        self.wdgEditor.setCurrentWidget(self.pageQuestions)

        self.layout().addWidget(self.wdgHeader)
        self.lblDesc = label(self.DESC_RAISED_QUESTIONS, description=True, wordWrap=True)
        self.layout().addWidget(self.lblDesc)
        self.layout().addWidget(line())
        self.layout().addWidget(self.wdgEditor)
        self.wdgEditor.currentChanged.connect(self._pageChanged)
        link_buttons_to_pages(self.wdgEditor, [
            (self.btnUnresolved, self.pageQuestions), (self.btnResolved, self.pageResolvedQuestions),
            (self.btnOther, self.pageDetachedQuestions)
        ])

        self.repo = RepositoryPersistenceManager.instance()

    def setScene(self, scene: Scene):
        self._scene = scene
        self._initialized = False
        if self.isVisible():
            self.refresh()

    @overrides
    def refresh(self):
        if not self._scene:
            return

        clear_layout(self.pageQuestionsEditor)
        clear_layout(self.pageResolvedQuestionsEditor)
        clear_layout(self.pageDetachedQuestionsEditor)

        found_questions: Dict[ReaderQuestion, Optional[bool]] = {}
        for scene in self._novel.scenes:
            for question_ref in scene.questions:
                question = self._novel.questions[question_ref.sid()]
                found_questions[question] = question_ref.resolved

            if scene is self._scene:
                break

        for question_ref in self._scene.questions:
            question = self._novel.questions[question_ref.sid()]
            found_questions[question] = None
            self._addQuestion(question,
                              QuestionState.Resolved_now if question_ref.resolved else QuestionState.Raised_now,
                              question_ref)

        for k, v in found_questions.items():
            if v is None:
                continue
            self._addQuestion(k, QuestionState.Resolved_before if v else QuestionState.Raised_before)

        for question in self._novel.questions.values():
            if question not in found_questions.keys():
                self._addQuestion(question, QuestionState.Detached)

        self.pageQuestionsEditor.layout().addWidget(wrap(self.btnAddNew, margin_top=80))

        self._updateLabels()

        super().refresh()

    def _pageChanged(self):
        if self.wdgEditor.currentWidget() is self.pageQuestions:
            self.lblDesc.setText(self.DESC_RAISED_QUESTIONS)
        elif self.wdgEditor.currentWidget() is self.pageResolvedQuestions:
            self.lblDesc.setText(self.DESC_RESOLVED_QUESTIONS)
        elif self.wdgEditor.currentWidget() is self.pageDetachedQuestions:
            self.lblDesc.setText(self.DESC_FUTURE_QUESTIONS)

    def _updateLabels(self):
        self.btnUnresolved.setText(f'{self.LABEL_RAISED_QUESTIONS} ({self.pageQuestionsEditor.layout().count() - 1})')
        self.btnResolved.setText(
            f'{self.LABEL_RESOLVED_QUESTIONS} ({self.pageResolvedQuestionsEditor.layout().count()})')
        self.btnOther.setText(f'{self.LABEL_FUTURE_QUESTIONS} ({self.pageDetachedQuestionsEditor.layout().count()})')

        self.btnOther.setVisible(self.pageDetachedQuestionsEditor.layout().count() > 0)
        if not self.btnOther.isVisible() and self.btnOther.isChecked():
            self.btnUnresolved.setChecked(True)

    def _addQuestion(self, question: ReaderQuestion, state: QuestionState, ref: Optional[SceneReaderQuestion] = None):
        wdg = self.__initQuestionWidget(question, state, ref)

        if state == QuestionState.Raised_before or state == QuestionState.Raised_now:
            self.pageQuestionsEditor.layout().addWidget(wdg)
        elif state == QuestionState.Resolved_before or state == QuestionState.Resolved_now:
            self.pageResolvedQuestionsEditor.layout().addWidget(wdg)
        else:
            self.pageDetachedQuestionsEditor.layout().addWidget(wdg)

    def _addNew(self):
        question = ReaderQuestion()

        self._novel.questions[question.sid()] = question
        ref = SceneReaderQuestion(question.id)
        self._scene.questions.append(ref)
        self.repo.update_novel(self._novel)

        wdg = self.__initQuestionWidget(question, QuestionState.Raised_now, ref)
        insert_before_the_end(self.pageQuestionsEditor, wdg)
        qtanim.fade_in(wdg, teardown=lambda: wdg.setGraphicsEffect(None))
        wdg.textedit.setFocus()

        self._updateLabels()

    def _resolve(self, wdg: ReaderQuestionWidget):
        def finish():
            self._addQuestion(question, QuestionState.Resolved_now, ref)
            qtanim.glow(self.btnResolved, color=QColor(PLOTLYST_SECONDARY_COLOR), loop=3)
            self._updateLabels()

        question = wdg.question
        ref = SceneReaderQuestion(question.id, resolved=True)
        fade_out_and_gc(self.pageQuestionsEditor, wdg, teardown=finish)
        self._scene.questions.append(ref)

    def _unresolve(self, wdg: ReaderQuestionWidget):
        def finish():
            self._addQuestion(question, QuestionState.Raised_before)
            qtanim.glow(self.btnUnresolved, color=QColor(PLOTLYST_SECONDARY_COLOR), loop=2)
            self._updateLabels()

        question = wdg.question
        self._scene.questions.remove(wdg.scene_ref)
        fade_out_and_gc(self.pageResolvedQuestionsEditor, wdg, teardown=finish)

    def _detach(self, wdg: ReaderQuestionWidget):
        def finish():
            if ref:
                self.refresh()
            else:
                self._updateLabels()

        if wdg.question.text and not confirmed("Remove this reader's question?"):
            return

        self._scene.questions.remove(wdg.scene_ref)
        question = wdg.question
        ref = self._find_ref(question)
        fade_out_and_gc(wdg.parent(), wdg, teardown=finish)
        if not ref:
            self._novel.questions.pop(question.sid())
            self.repo.update_novel(self._novel)

    def _remove(self, wdg: ReaderQuestionWidget):
        def finish():
            self.refresh()

        if not confirmed("Remove this reader's question and all its associations?"):
            return

        question = wdg.question

        for scene in self._novel.scenes:
            for ref in scene.questions[:]:
                if ref.id == question.id:
                    scene.questions.remove(ref)
                    self.repo.update_scene(scene)

        self._novel.questions.pop(question.sid())
        fade_out_and_gc(wdg.parent(), wdg, teardown=finish)
        self.repo.update_novel(self._novel)

    def _resurrect(self, wdg: ReaderQuestionWidget):
        def finish():
            self.refresh()
            qtanim.glow(self.btnUnresolved, color=QColor(PLOTLYST_SECONDARY_COLOR), loop=2)

        question = wdg.question
        ref = SceneReaderQuestion(question.id)
        self._scene.questions.append(ref)
        fade_out_and_gc(wdg.parent(), wdg, teardown=finish)

    def _find_ref(self, question: ReaderQuestion) -> Optional[SceneReaderQuestion]:
        for scene in self._novel.scenes:
            for ref in scene.questions:
                if ref.id == question.id:
                    return ref

    def __initQuestionWidget(self, question: ReaderQuestion,
                             state: QuestionState, ref: Optional[SceneReaderQuestion] = None) -> ReaderQuestionWidget:
        wdg = ReaderQuestionWidget(question, state, ref)
        wdg.resolved.connect(partial(self._resolve, wdg))
        wdg.unresolved.connect(partial(self._unresolve, wdg))
        wdg.changed.connect(lambda: self.repo.update_novel(self._novel))
        wdg.detached.connect(partial(self._detach, wdg))
        wdg.removed.connect(partial(self._remove, wdg))
        wdg.resurrect.connect(partial(self._resurrect, wdg))

        return wdg


class ReaderInformationWidget(QWidget):
    removed = pyqtSignal()

    def __init__(self, info: SceneReaderInformation, parent=None):
        super().__init__(parent)
        self.info = info
        vbox(self, 10)

        self._label = push_btn(
            IconRegistry.general_info_icon('black'), 'Information',
            transparent_=True, icon_resize=False, pointy_=False)
        self._label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        translucent(self._label, 0.6)

        self.btnRemove = RemovalButton(self)
        self.btnRemove.setHidden(True)
        self.btnRemove.clicked.connect(self.removed)
        self.installEventFilter(VisibilityToggleEventFilter(self.btnRemove, self))

        self.textedit = QTextEdit(self)
        self.textedit.setProperty('white-bg', True)
        self.textedit.setProperty('rounded', True)
        self.textedit.setTabChangesFocus(True)
        if app_env.is_mac():
            incr_font(self.textedit)
        self.textedit.setMinimumSize(170, 100)
        self.textedit.setMaximumSize(190, 120)
        self.textedit.verticalScrollBar().setVisible(False)
        shadow(self.textedit, offset=4 if self.info.revelation else 2, color=QColor(self.info.type.color()))
        self.textedit.setPlaceholderText('What new information is conveyed to the reader?')
        self.textedit.setText(self.info.text)
        self.textedit.textChanged.connect(self._infoChanged)

        self.btnRevelation = push_btn(IconRegistry.from_name('mdi.puzzle-star'), 'Mark as revelation',
                                      transparent_=True)
        self.btnRevelation.installEventFilter(OpacityEventFilter(self.btnRevelation))
        retain_when_hidden(self.btnRevelation)
        self.installEventFilter(VisibilityToggleEventFilter(self.btnRevelation, self))
        self.btnRevelation.clicked.connect(self._toggleRelevation)

        self.layout().addWidget(self._label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.textedit)
        self.layout().addWidget(self.btnRevelation, alignment=Qt.AlignmentFlag.AlignCenter)

        if self.info.revelation:
            self._refreshRevelation()

        sp(self).v_max()

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        self.btnRemove.setGeometry(event.size().width() - 20, 10, 10, 10)

    def _infoChanged(self):
        self.info.text = self.textedit.toPlainText()

    def _toggleRelevation(self):
        def finished():
            shadow(self.textedit, offset=4 if self.info.revelation else 2, color=QColor(self.info.type.color()))

        self.info.revelation = not self.info.revelation
        if self.info.revelation:
            qtanim.glow(self.textedit, 500, radius=15, color=QColor(self.info.type.color()), teardown=finished)
        else:
            qtanim.glow(self.textedit, duration=100, color=QColor('lightgrey'), teardown=finished)

        self._refreshRevelation()

    def _refreshRevelation(self):
        bold(self._label, self.info.revelation)
        italic(self.btnRevelation, self.info.revelation)
        if self.info.revelation:
            icon = IconRegistry.from_name('mdi.puzzle-star')
            title = 'Revelation'
            incr_icon(self._label, 4)
            incr_font(self._label, 2)
            self.btnRevelation.setText('Demote revelation')
            self.btnRevelation.setIcon(QIcon())

            self.textedit.setMinimumSize(195, 125)
            self.textedit.setMaximumSize(215, 135)
        else:
            icon = IconRegistry.general_info_icon('black')
            title = 'Information'
            decr_icon(self._label, 4)
            decr_font(self._label, 2)
            self.btnRevelation.setText('Mark as revelation')
            self.btnRevelation.setIcon(IconRegistry.from_name('mdi.puzzle-star'))

            self.textedit.setMinimumSize(170, 100)
            self.textedit.setMaximumSize(190, 120)

        self._label.setIcon(icon)
        self._label.setText(title)


class ReaderInformationColumn(QWidget):
    added = pyqtSignal(SceneReaderInformation)
    removed = pyqtSignal(SceneReaderInformation)

    def __init__(self, infoType: ReaderInformationType, parent=None):
        super().__init__(parent)
        vbox(self, spacing=5)
        self.infoType = infoType

        self.title = IconText()
        if self.infoType == ReaderInformationType.Story:
            self.title.setText('Plot')
            self.title.setIcon(
                IconRegistry.storylines_icon(color=self.infoType.color(), color_on=self.infoType.color()))
        elif self.infoType == ReaderInformationType.Character:
            self.title.setText('Character')
            self.title.setIcon(IconRegistry.character_icon(color=self.infoType.color(), color_on=self.infoType.color()))
        elif self.infoType == ReaderInformationType.World:
            self.title.setText('World')
            self.title.setIcon(
                IconRegistry.world_building_icon(color=self.infoType.color(), color_on=self.infoType.color()))
        # self.title.setStyleSheet(f'border:0px; color: {self.infoType.color()};')
        incr_font(self.title, 2)
        incr_icon(self.title, 4)
        translucent(self.title, 0.9)

        self.btnAdd = tool_btn(IconRegistry.plus_icon('grey'), transparent_=True)
        self.btnAdd.installEventFilter(OpacityEventFilter(self.btnAdd))
        self.btnAdd.clicked.connect(self._addNew)

        self.wdgEditor = QWidget()
        vbox(self.wdgEditor)

        self.layout().addWidget(self.title)
        self.layout().addWidget(self.btnAdd, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(line(color=self.infoType.color()))
        self.layout().addWidget(self.wdgEditor)
        self.layout().addWidget(vspacer())

        self.setMinimumWidth(150)
        self.setMaximumWidth(400)
        sp(self).h_exp()

    def clear(self):
        clear_layout(self.wdgEditor)

    def addInfo(self, info: SceneReaderInformation) -> ReaderInformationWidget:
        wdg = ReaderInformationWidget(info)
        wdg.removed.connect(partial(self._remove, wdg))
        self.wdgEditor.layout().addWidget(wdg, alignment=Qt.AlignmentFlag.AlignCenter)
        return wdg

    def _addNew(self):
        info = SceneReaderInformation(self.infoType)
        wdg = self.addInfo(info)
        qtanim.fade_in(wdg, teardown=lambda: wdg.setGraphicsEffect(None))
        self.added.emit(info)

    def _remove(self, wdg: ReaderInformationWidget):
        fade_out_and_gc(self.wdgEditor, wdg)
        self.removed.emit(wdg.info)


class ReaderInformationEditor(LazyWidget):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._scene: Optional[Scene] = None

        vbox(self, 10, 10)
        self.setProperty('muted-bg', True)
        margins(self, top=15)
        self.layout().addWidget(label(
            "Track what essential information is conveyed to the reader.", description=True),
            alignment=Qt.AlignmentFlag.AlignRight)
        self._scrollarea, self._wdgCenter = scrolled(self, frameless=True)
        self._wdgCenter.setProperty('muted-bg', True)
        hbox(self._wdgCenter)

        self.wdgStory = ReaderInformationColumn(ReaderInformationType.Story)
        self.wdgStory.added.connect(self._infoAdded)
        self.wdgStory.removed.connect(self._infoRemoved)

        self.wdgCharacters = ReaderInformationColumn(ReaderInformationType.Character)
        self.wdgCharacters.added.connect(self._infoAdded)
        self.wdgCharacters.removed.connect(self._infoRemoved)

        self.wdgWorld = ReaderInformationColumn(ReaderInformationType.World)
        self.wdgWorld.added.connect(self._infoAdded)
        self.wdgWorld.removed.connect(self._infoRemoved)

        self._wdgCenter.layout().addWidget(self.wdgStory)
        self._wdgCenter.layout().addWidget(self.wdgCharacters)
        self._wdgCenter.layout().addWidget(self.wdgWorld)
        spacer_ = spacer()
        sp(spacer_).h_preferred()
        self._wdgCenter.layout().addWidget(spacer_)

    def setScene(self, scene: Scene):
        self._scene = scene
        self._initialized = False
        if self.isVisible():
            self.refresh()

    @overrides
    def refresh(self):
        if not self._scene:
            return

        self.wdgStory.clear()
        self.wdgCharacters.clear()
        self.wdgWorld.clear()

        for info in self._scene.info:
            if info.type == ReaderInformationType.Story:
                self.wdgStory.addInfo(info)
            elif info.type == ReaderInformationType.Character:
                self.wdgCharacters.addInfo(info)
            elif info.type == ReaderInformationType.World:
                self.wdgWorld.addInfo(info)

        super().refresh()

    def _infoAdded(self, info: SceneReaderInformation):
        if self._scene:
            self._scene.info.append(info)

    def _infoRemoved(self, info: SceneReaderInformation):
        if self._scene:
            self._scene.info.remove(info)
