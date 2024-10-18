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
from functools import partial
from typing import Dict

import qtanim
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QObject, QEvent
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QFrame, QSizePolicy, QLabel, QToolButton, QPushButton
from overrides import overrides
from qthandy import vbox, hbox, transparent, vspacer, margins, spacer, bold, retain_when_hidden, incr_font, \
    gc, decr_icon, pointy
from qthandy.filter import VisibilityToggleEventFilter, OpacityEventFilter, DragEventFilter, DropEventFilter
from qtmenu import MenuWidget

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import TaskStatus, Task, Novel, Character, task_tags
from plotlyst.core.template import SelectionItem
from plotlyst.env import app_env
from plotlyst.event.core import Event, emit_event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import CharacterDeletedEvent, TaskChanged, TaskDeleted, TaskChangedToWip, \
    TaskChangedFromWip
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import ButtonPressResizeEventFilter, shadow, action, tool_btn, \
    any_menu_visible, insert_before_the_end
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.button import CollapseButton, TaskTagSelector
from plotlyst.view.widget.characters import CharacterSelectorButton
from plotlyst.view.widget.input import AutoAdjustableLineEdit

TASK_WIDGET_MAX_WIDTH = 350

TASK_MIME_TYPE: str = 'application/task'


class TaskWidget(QFrame):
    removalRequested = pyqtSignal(object)
    changed = pyqtSignal()
    resolved = pyqtSignal()

    def __init__(self, task: Task, parent=None):
        super(TaskWidget, self).__init__(parent)
        self._task: Task = task

        vbox(self, margin=5)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.setMinimumHeight(75)
        shadow(self, 3)

        self._lineTitle = AutoAdjustableLineEdit(self, defaultWidth=100)
        self._lineTitle.setPlaceholderText('New task')
        self._lineTitle.setText(task.title)
        self._lineTitle.setFrame(False)
        font = QFont(app_env.sans_serif_font())
        font.setWeight(QFont.Weight.Medium)
        self._lineTitle.setFont(font)
        incr_font(self._lineTitle)

        self._charSelector = CharacterSelectorButton(app_env.novel, self, opacityEffectEnabled=False, iconSize=24)
        self._charSelector.setToolTip('Link character')
        decr_icon(self._charSelector)
        if self._task.character_id:
            self._charSelector.setCharacter(self._task.character(app_env.novel))
        else:
            self._charSelector.setHidden(True)
        retain_when_hidden(self._charSelector)
        self._charSelector.characterSelected.connect(self._linkCharacter)
        self._charSelector.menu().aboutToHide.connect(self._onLeave)
        top_wdg = group(self._lineTitle, spacer(), self._charSelector, margin=0, spacing=1)
        self.layout().addWidget(top_wdg, alignment=Qt.AlignmentFlag.AlignTop)

        self._wdgBottom = QWidget()
        retain_when_hidden(self._wdgBottom)
        hbox(self._wdgBottom)

        self._btnTags = TaskTagSelector(self._wdgBottom)
        self._btnTags.tagSelected.connect(self._tagChanged)

        self._btnResolve = tool_btn(IconRegistry.from_name('fa5s.check', 'grey'), 'Resolve task',
                                    properties=['transparent-circle-bg-on-hover', 'positive'], parent=self._wdgBottom)
        decr_icon(self._btnResolve)
        self._btnResolve.clicked.connect(self.resolved.emit)

        self._btnMenu = tool_btn(IconRegistry.dots_icon('grey'), 'Menu', properties=['transparent-circle-bg-on-hover'],
                                 parent=self._wdgBottom)
        decr_icon(self._btnMenu)
        menu = MenuWidget(self._btnMenu)
        menu.addAction(action('Rename', IconRegistry.edit_icon(), self._lineTitle.setFocus))
        menu.addSeparator()
        menu.addAction(action('Delete', IconRegistry.trash_can_icon(), lambda: self.removalRequested.emit(self)))
        menu.aboutToHide.connect(self._onLeave)
        self._wdgBottom.layout().addWidget(self._btnTags)
        self._wdgBottom.layout().addWidget(spacer())
        self._wdgBottom.layout().addWidget(self._btnResolve, alignment=Qt.AlignmentFlag.AlignRight)
        self._wdgBottom.layout().addWidget(self._btnMenu, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(self._wdgBottom, alignment=Qt.AlignmentFlag.AlignBottom)

        if self._task.tags:
            tag = task_tags.get(self._task.tags[0], None)
            if tag:
                self._btnTags.select(tag)
        else:
            self._btnTags.setHidden(True)
        self._btnResolve.setHidden(True)
        self._btnMenu.setHidden(True)

        self.installEventFilter(self)
        self._lineTitle.textEdited.connect(self._titleEdited)
        self._lineTitle.editingFinished.connect(self._titleEditingFinished)

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Enter:
            if not self._task.character_id:
                self._charSelector.setVisible(True)
            self._btnMenu.setVisible(True)
            self._btnResolve.setVisible(True)
            self._btnTags.setVisible(True)
        elif event.type() == QEvent.Type.Leave:
            if any_menu_visible(self._charSelector, self._btnMenu, self._btnTags):
                return True
            self._onLeave()
        return super(TaskWidget, self).eventFilter(watched, event)

    def task(self) -> Task:
        return self._task

    def activate(self):
        anim = qtanim.fade_in(self, 150)
        anim.finished.connect(self._activated)

    def _titleEdited(self, text: str):
        self._task.title = text
        self.changed.emit()

    def _titleEditingFinished(self):
        if not self._task.title:
            self.removalRequested.emit(self)

    def _activated(self):
        self._lineTitle.setFocus()
        shadow(self, 3)

    def _tagChanged(self, tag: SelectionItem):
        self._task.tags.clear()
        self._task.tags.append(tag.text)

    def _onLeave(self):
        if not self._task.character_id:
            self._charSelector.setHidden(True)
        if not self._task.tags:
            self._btnTags.setHidden(True)
        self._btnMenu.setVisible(False)
        self._btnResolve.setVisible(False)

    def _linkCharacter(self, character: Character):
        self._task.set_character(character)
        self._charSelector.setVisible(True)
        self.changed.emit()

    def resetCharacter(self):
        self._task.reset_character()
        self._charSelector.clear()


class _StatusHeader(QFrame):
    collapseToggled = pyqtSignal(bool)
    addTask = pyqtSignal()

    def __init__(self, status: TaskStatus, parent=None, collapseEnabled: bool = True,
                 headerAdditionEnabled: bool = True):
        super(_StatusHeader, self).__init__(parent)
        self._status = status
        self.setStyleSheet(f'''_StatusHeader {{
                background-color: {RELAXED_WHITE_COLOR};
                border-bottom: 3px solid {self._status.color_hexa};
            }}''')
        hbox(self, margin=8)

        self._title = QLabel(self)
        bold(self._title)
        self.updateTitle()
        self._btnCollapse = CollapseButton(Qt.Edge.BottomEdge, Qt.Edge.LeftEdge, self)
        if collapseEnabled:
            self.installEventFilter(VisibilityToggleEventFilter(self._btnCollapse, self))
        else:
            self._btnCollapse.setHidden(True)
        shadow(self)

        self._btnAdd = QToolButton()
        self._btnAdd.setIcon(IconRegistry.plus_icon('grey'))
        transparent(self._btnAdd)
        retain_when_hidden(self._btnAdd)
        self._btnAdd.setStyleSheet('''
            QToolButton {
                border-radius: 12px;
                border: 1px hidden lightgrey;
                padding: 2px;
            }

            QToolButton:hover {
                background: lightgrey;
            }
        ''')
        pointy(self._btnAdd)
        self._btnAdd.installEventFilter(ButtonPressResizeEventFilter(self._btnAdd))
        if headerAdditionEnabled:
            self.installEventFilter(VisibilityToggleEventFilter(self._btnAdd, self))
        else:
            self._btnAdd.setHidden(True)

        self.layout().addWidget(self._title)
        self.layout().addWidget(self._btnCollapse)
        self.layout().addWidget(spacer())
        self.layout().addWidget(self._btnAdd)

        self._btnCollapse.clicked.connect(self.collapseToggled.emit)
        self._btnAdd.clicked.connect(self.addTask.emit)

    def toggled(self) -> bool:
        return self._btnCollapse.isChecked()

    def updateTitle(self, childrenCount: int = 0):
        suffix = f'({childrenCount})' if childrenCount else ''
        self._title.setText(f'{self._status.text.upper()} {suffix}')


class BaseStatusColumnWidget(QFrame):
    def __init__(self, status: TaskStatus, parent=None, collapseEnabled: bool = True,
                 headerAdditionEnabled: bool = True):
        super().__init__(parent)
        self._status = status

        vbox(self, 1, 20)
        self._header = _StatusHeader(self._status, collapseEnabled=collapseEnabled,
                                     headerAdditionEnabled=headerAdditionEnabled)
        self._header.collapseToggled.connect(self._collapseToggled)
        self._container = QFrame(self)
        self._container.setProperty('darker-bg', True)
        self._container.setProperty('rounded', True)
        spacing = 6 if app_env.is_mac() else 12
        vbox(self._container, margin=10, spacing=spacing)
        self._container.layout().addWidget(vspacer())

        self.setMaximumWidth(TASK_WIDGET_MAX_WIDTH)
        self.layout().addWidget(self._header)
        self.layout().addWidget(self._container)

    def _collapseToggled(self, toggled: bool):
        for i in range(self._container.layout().count()):
            item = self._container.layout().itemAt(i)
            if item.widget() and isinstance(item.widget(), TaskWidget):
                item.widget().setHidden(toggled)


class StatusColumnWidget(BaseStatusColumnWidget):
    taskChanged = pyqtSignal(Task)
    taskDeleted = pyqtSignal(Task)
    taskResolved = pyqtSignal(Task)

    def __init__(self, novel: Novel, status: TaskStatus, parent=None):
        super(StatusColumnWidget, self).__init__(status, parent)
        self._novel = novel

        self._btnAdd = QPushButton('New Task', self)
        self._btnAdd.setIcon(IconRegistry.plus_icon('grey'))
        retain_when_hidden(self._btnAdd)
        transparent(self._btnAdd)
        pointy(self._btnAdd)
        self._btnAdd.installEventFilter(ButtonPressResizeEventFilter(self._btnAdd))
        self._btnAdd.installEventFilter(OpacityEventFilter(self._btnAdd))

        insert_before_the_end(self._container, self._btnAdd, alignment=Qt.AlignmentFlag.AlignLeft)

        self.installEventFilter(VisibilityToggleEventFilter(self._btnAdd, self))
        self.setAcceptDrops(True)
        self.installEventFilter(
            DropEventFilter(self, [TASK_MIME_TYPE], enteredSlot=self._dragEntered, leftSlot=self._dragLeft,
                            droppedSlot=self._dropped))

        self._btnAdd.clicked.connect(self._addNewTask)
        self._header.addTask.connect(self._addNewTask)

        dispatcher = event_dispatchers.instance(self._novel)
        dispatcher.register(self, CharacterDeletedEvent)

    def event_received(self, event: Event):
        if isinstance(event, CharacterDeletedEvent):
            for i in range(self._container.layout().count() - 2):
                item = self._container.layout().itemAt(i)
                if item.widget():
                    taskWdg: TaskWidget = item.widget()
                    if taskWdg.task().character_id == event.character.id:
                        taskWdg.resetCharacter()
                        self.taskChanged.emit(taskWdg.task())

    def status(self) -> TaskStatus:
        return self._status

    def addTask(self, task: Task, edit: bool = False) -> TaskWidget:
        wdg = TaskWidget(task, self)
        self._container.layout().insertWidget(self._container.layout().count() - 2, wdg,
                                              alignment=Qt.AlignmentFlag.AlignTop)
        wdg.installEventFilter(
            DragEventFilter(self, mimeType=TASK_MIME_TYPE, dataFunc=self._grabbedTaskData,
                            startedSlot=lambda: wdg.setDisabled(True),
                            finishedSlot=lambda: self._dragFinished(wdg)))
        wdg.removalRequested.connect(self._deleteTask)
        wdg.changed.connect(partial(self.taskChanged.emit, task))
        wdg.resolved.connect(partial(self.__removeTaskWidget, wdg))
        wdg.resolved.connect(partial(self.taskResolved.emit, task))
        if edit:
            wdg.activate()

        if self._status.wip:
            emit_event(self._novel, TaskChangedToWip(self, task))

        self._header.updateTitle(self._container.layout().count() - 2)
        return wdg

    def _addNewTask(self):
        task = Task('', self._status.id)
        self._novel.board.tasks.append(task)
        self.addTask(task, edit=True)

    def _deleteTask(self, taskWidget: TaskWidget):
        task = taskWidget.task()
        self._novel.board.tasks.remove(task)
        self.__removeTaskWidget(taskWidget)
        self.taskDeleted.emit(task)

    def _grabbedTaskData(self, widget: TaskWidget):
        return widget.task()

    def _dragEntered(self, _: QMimeData):
        self.setStyleSheet(f'StatusColumnWidget {{border: 2px dashed {self._status.color_hexa};}}')

    def _dragLeft(self):
        self.setStyleSheet('')

    def _dragFinished(self, taskWidget: TaskWidget):
        if taskWidget.task().status_ref == self._status.id:
            taskWidget.setEnabled(True)
        else:
            self.__removeTaskWidget(taskWidget)

    def _dropped(self, mimeData: QMimeData):
        self.setStyleSheet('')
        task: Task = mimeData.reference()
        if task.status_ref == self._status.id:
            return
        task.status_ref = self._status.id
        if self._status.resolves:
            task.update_resolved_date()

        self.taskChanged.emit(task)
        wdg = self.addTask(task)
        wdg.setHidden(self._header.toggled())

    def __removeTaskWidget(self, taskWidget):
        if self._status.wip:
            emit_event(self._novel, TaskChangedFromWip(self, taskWidget.task()))

        taskWidget.setHidden(True)
        self._container.layout().removeWidget(taskWidget)
        gc(taskWidget)
        self._header.updateTitle(self._container.layout().count() - 2)


class BoardWidget(QWidget):
    taskAdded = pyqtSignal(Task)

    def __init__(self, novel: Novel, parent=None):
        super(BoardWidget, self).__init__(parent)
        self._novel = novel

        hbox(self, spacing=20)
        self._statusColumns: Dict[str, StatusColumnWidget] = {}
        for status in self._novel.board.statuses:
            column = StatusColumnWidget(novel, status)
            column.taskChanged.connect(self._taskChanged)
            column.taskDeleted.connect(self._taskDeleted)
            column.taskResolved.connect(self._taskResolved)
            self.layout().addWidget(column)
            self._statusColumns[str(status.id)] = column

        for task in novel.board.tasks:
            column = self._statusColumns.get(str(task.status_ref))
            if column is None:
                column = self._firstStatusColumn()
            column.addTask(task)

        _spacer = spacer()
        _spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.layout().addWidget(_spacer)
        margins(self, left=20)

        self.repo = RepositoryPersistenceManager.instance()

    def addNewTask(self):
        if self._statusColumns:
            column = self._firstStatusColumn()
            task = Task('', column.status().id)
            self._novel.board.tasks.append(task)
            column.addTask(task, edit=True)
            self.taskAdded.emit(task)

    def _firstStatusColumn(self) -> StatusColumnWidget:
        return self._statusColumns[str(self._novel.board.statuses[0].id)]

    def _taskChanged(self, task: Task):
        self._saveBoard()
        emit_event(self._novel, TaskChanged(self, task))

    def _taskDeleted(self, task: Task):
        self._saveBoard()
        emit_event(self._novel, TaskDeleted(self, task))

    def _taskResolved(self, task: Task):
        for status in self._novel.board.statuses:
            if status.resolves:
                task.status_ref = status.id
                task.update_resolved_date()
                wdg = self._statusColumns[str(status.id)]
                wdg.addTask(task)
                break
        self._saveBoard()

    def _saveBoard(self):
        self.repo.update_novel(self._novel)
