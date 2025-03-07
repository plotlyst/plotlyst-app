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
from typing import Dict, Optional, Set, Union
from typing import List

from PyQt6.QtCore import QMimeData, QPointF
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QShowEvent, QIcon, QAction
from PyQt6.QtWidgets import QWidget
from overrides import overrides
from qthandy import gc, translucent, clear_layout, vbox
from qthandy import vspacer
from qthandy.filter import DragEventFilter, DropEventFilter
from qtmenu import MenuWidget

from plotlyst.core.domain import Scene, Novel, Chapter, ChapterType
from plotlyst.event.core import Event, EventListener, emit_event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import SceneDeletedEvent, \
    SceneChangedEvent, SceneAddedEvent, ScenesOrganizationResetEvent, NovelScenesOrganizationToggleEvent
from plotlyst.events import SceneOrderChangedEvent, ChapterChangedEvent
from plotlyst.service.persistence import RepositoryPersistenceManager, delete_scene
from plotlyst.view.common import action, insert_before_the_end
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.confirm import confirmed
from plotlyst.view.widget.tree import TreeView, ContainerNode, TreeSettings


class SceneNode(ContainerNode):

    def __init__(self, scene: Scene, novel: Novel, parent=None, readOnly: bool = False,
                 settings: Optional[TreeSettings] = None):
        super(SceneNode, self).__init__(scene.title_or_index(novel), parent=parent, settings=settings)
        self._scene = scene
        self._novel = novel
        self._readOnly = readOnly

        self.setPlusButtonEnabled(False)
        self.setMenuEnabled(not self._readOnly)
        IconRegistry.scene_icon()
        self._dotIcon = 'msc.debug-stackframe-dot'
        self._icon.setIcon(IconRegistry.from_name(self._dotIcon, 'lightgrey'))
        self._icon.setVisible(True)
        self._wdgTitle.layout().setSpacing(0)
        # margins(self._wdgTitle, left=0, top=0, bottom=0)
        # margins(self._wdgTitle, top=3, bottom=3)

        self.refresh()

    def scene(self) -> Scene:
        return self._scene

    def novel(self) -> Novel:
        return self._novel

    def refresh(self):
        # if self._scene.purpose:
        #     self._icon.setIcon(IconRegistry.scene_type_icon(self._scene))
        # self._icon.setVisible(self._scene.purpose is not None)

        # if self._scene.pov:
        #     avatar = avatars.avatar(self._scene.pov, fallback=False)
        #     if avatar:
        #         self._scenePovIcon.setIcon(avatar)
        # else:
        #     avatar = None
        # self._scenePovIcon.setVisible(avatar is not None)

        self.refreshTitle()

    def refreshTitle(self):
        self._lblTitle.setText(self._scene.title_or_index(self._novel))

    @overrides
    def _reStyle(self):
        super()._reStyle()
        if self._selected:
            self._icon.setIcon(IconRegistry.from_name(self._dotIcon, 'black'))
        else:
            self._icon.setIcon(IconRegistry.from_name(self._dotIcon, 'lightgrey'))


class ChapterNode(ContainerNode):
    deleted = pyqtSignal()
    addScene = pyqtSignal()
    addChapter = pyqtSignal()
    converted = pyqtSignal(ChapterType)
    resetType = pyqtSignal()

    def __init__(self, chapter: Chapter, novel: Novel, parent=None, readOnly: bool = False,
                 settings: Optional[TreeSettings] = None):
        super(ChapterNode, self).__init__(chapter.display_name(), IconRegistry.chapter_icon(), parent,
                                          settings=settings)
        self._chapter = chapter
        self._novel = novel
        self._readOnly = readOnly

        self.setPlusButtonEnabled(not self._readOnly)
        self.setMenuEnabled(not self._readOnly)
        if not self._readOnly:
            menu = MenuWidget(self._btnAdd)
            menu.addAction(action('Add chapter', IconRegistry.chapter_icon(), self.addChapter.emit))
            menu.addAction(action('Add scene', IconRegistry.scene_icon(), self.addScene.emit))
            self.setPlusMenu(menu)

        self._reStyle()
        if self._chapter.type is not None:
            self.refresh()

    def refresh(self):
        self._icon.setIcon(self._chapterIcon())
        self._lblTitle.setText(self._chapter.display_name())

    def chapter(self) -> Chapter:
        return self._chapter

    def novel(self) -> Novel:
        return self._novel

    def sceneWidgets(self) -> List[SceneNode]:
        return self.childrenWidgets()

    @overrides
    def _reStyle(self):
        super()._reStyle()
        self._icon.setIcon(self._chapterIcon())

    @overrides
    def _initMenuActions(self, menu: MenuWidget):
        convertMenu = MenuWidget()
        convertMenu.setTitle('Convert into')
        convertMenu.setIcon(IconRegistry.from_name('ph.arrows-left-right'))
        chapterConvertAction = action('Chapter', IconRegistry.chapter_icon(), slot=self.resetType)
        convertMenu.addAction(chapterConvertAction)
        convertMenu.addSeparator()
        convertMenu.addAction(
            action('Prologue', IconRegistry.prologue_icon(), slot=partial(self.converted.emit, ChapterType.Prologue)))
        convertMenu.addAction(
            action('Epilogue', IconRegistry.epilogue_icon(), slot=partial(self.converted.emit, ChapterType.Epilogue)))
        convertMenu.addAction(
            action('Interlude', IconRegistry.interlude_icon(),
                   slot=partial(self.converted.emit, ChapterType.Interlude)))
        convertMenu.aboutToShow.connect(partial(self._showConvertMenu, chapterConvertAction))
        menu.addMenu(convertMenu)
        menu.addSeparator()
        menu.addAction(self._actionDelete)

    def _chapterIcon(self) -> QIcon:
        color = 'black' if self._selected else 'grey'
        if self._chapter.type is None:
            return IconRegistry.chapter_icon(color=color)
        elif self._chapter.type == ChapterType.Prologue:
            return IconRegistry.prologue_icon(color=color)
        elif self._chapter.type == ChapterType.Epilogue:
            return IconRegistry.epilogue_icon(color=color)
        elif self._chapter.type == ChapterType.Interlude:
            return IconRegistry.interlude_icon(color=color)

    def _showConvertMenu(self, convertChapterAction: QAction):
        convertChapterAction.setDisabled(self._chapter.type is None)


class ScenesTreeView(TreeView, EventListener):
    SCENE_MIME_TYPE = 'application/tree-scene-widget'
    CHAPTER_MIME_TYPE = 'application/tree-chapter-widget'
    sceneSelected = pyqtSignal(Scene)
    sceneDoubleClicked = pyqtSignal(Scene)
    chapterSelected = pyqtSignal(Chapter)
    sceneAdded = pyqtSignal(Scene)

    # noinspection PyTypeChecker
    def __init__(self, parent=None, settings: Optional[TreeSettings] = None):
        super(ScenesTreeView, self).__init__(parent)
        self._novel: Optional[Novel] = None
        self._readOnly = False
        self._settings = settings

        self._refreshNeeded = False

        self._chapters: Dict[Chapter, ChapterNode] = {}
        self._scenes: Dict[Scene, SceneNode] = {}
        self._selectedScenes: Set[Scene] = set()
        self._selectedChapters: Set[Chapter] = set()
        self.setStyleSheet('ScenesTreeView {background-color: rgb(244, 244, 244);}')

        self._dummyWdg: Optional[Union[SceneNode, ChapterNode]] = None
        self._toBeRemoved: Optional[Union[SceneNode, ChapterNode]] = None
        self._spacer: QWidget = vspacer()
        vbox(self._spacer)
        self._spacer.setAcceptDrops(True)
        self._spacer.installEventFilter(
            DropEventFilter(self, [self.SCENE_MIME_TYPE], enteredSlot=self._dragEnteredForEnd,
                            leftSlot=self._dragLeftFromEnd, droppedSlot=self._drop))

        self._centralWidget.setAcceptDrops(True)
        self._centralWidget.installEventFilter(DropEventFilter(self, [self.SCENE_MIME_TYPE, self.CHAPTER_MIME_TYPE],
                                                               leftSlot=lambda: self._dummyWdg.setHidden(True)))

        self.repo = RepositoryPersistenceManager.instance()

    def setSettings(self, settings: TreeSettings):
        self._settings = settings

    def setNovel(self, novel: Novel, readOnly: bool = False):
        self._novel = novel
        dispatcher = event_dispatchers.instance(self._novel)
        dispatcher.register(self, SceneOrderChangedEvent, ChapterChangedEvent, SceneDeletedEvent, SceneAddedEvent,
                            SceneChangedEvent, ScenesOrganizationResetEvent, NovelScenesOrganizationToggleEvent)
        self._readOnly = readOnly

        self.refresh()

    def selectedScenes(self) -> List[Scene]:
        return list(self._selectedScenes)

    def selectedChapters(self) -> List[Chapter]:
        return list(self._selectedChapters)

    @overrides
    def showEvent(self, _: QShowEvent) -> None:
        if self._refreshNeeded:
            self.refresh()

    def refresh(self):
        self._refreshNeeded = False
        self.clearSelection()
        clear_layout(self._centralWidget, auto_delete=False)

        refreshTitles = False
        if self._scenes or self._chapters:
            refreshTitles = True

        for scene in self._novel.scenes:
            if scene not in self._scenes.keys():
                self.__initSceneWidget(scene)

            sceneWdg = self._scenes[scene]
            if scene.chapter:
                if scene.chapter not in self._chapters.keys():
                    chapter_wdg = self.__initChapterWidget(scene.chapter)
                else:
                    chapter_wdg = self._chapters[scene.chapter]
                self._centralWidget.layout().addWidget(chapter_wdg)
                chapter_wdg.addChild(sceneWdg)
            else:
                self._centralWidget.layout().addWidget(sceneWdg)

        chapter_index = 0
        for i, chapter in enumerate(self._novel.chapters):
            if chapter not in self._chapters.keys():
                chapter_wdg = self.__initChapterWidget(chapter)
            else:
                chapter_wdg = self._chapters[chapter]
            if i > 0:
                prev_chapter_wdg = self._chapters[self._novel.chapters[i - 1]]
                chapter_index = self._centralWidget.layout().indexOf(prev_chapter_wdg)
                chapter_index += 1
            self._centralWidget.layout().insertWidget(chapter_index, chapter_wdg)

        self._centralWidget.layout().addWidget(self._spacer)

        removed_chapters: List[ChapterNode] = [self._chapters[x] for x in self._chapters.keys() if
                                               x not in self._novel.chapters]
        self._chapters = {k: self._chapters[k] for k in self._chapters.keys() if k in self._novel.chapters}
        for chapterWdg in removed_chapters:
            chapterWdg.setHidden(True)
            gc(chapterWdg)

        if refreshTitles:
            self._refreshChapterTitles()
            self._refreshSceneTitles()

    def refreshScene(self, scene: Scene):
        if scene in self._scenes.keys():
            self._scenes[scene].refresh()

    def addChapter(self):
        wdg_i = 0
        chapter_i = -1

        if self._novel.chapters:
            for chapter in reversed(self._novel.chapters):
                if chapter.type != ChapterType.Epilogue:
                    wdg_i = self._centralWidget.layout().indexOf(self._chapters[chapter]) + 1
                    chapter_i = self._novel.chapters.index(chapter)
                    break

        chapter = Chapter('')
        self._novel.chapters.insert(chapter_i + 1, chapter)
        self._novel.update_chapter_titles()
        wdg = self.__initChapterWidget(chapter)
        self._centralWidget.layout().insertWidget(wdg_i, wdg)

        self.repo.update_novel(self._novel)
        self._emitChapterChange()

    def addScene(self):
        scene = self._novel.new_scene()
        self._novel.scenes.append(scene)
        wdg = self.__initSceneWidget(scene)
        insert_before_the_end(self._centralWidget, wdg)

        self.repo.insert_scene(self._novel, scene)
        emit_event(self._novel, SceneAddedEvent(self, scene), delay=10)
        self.sceneAdded.emit(scene)

    def removeChapter(self, chapter: Chapter):
        wdg = self._chapters.get(chapter)
        if wdg:
            self._deleteChapter(wdg)

    def addPrologue(self):
        pass

    def addEpilogue(self):
        pass

    def selectChapter(self, chapter: Chapter):
        self.clearSelection()
        self._chapters[chapter].select()
        if chapter not in self._selectedChapters:
            self._selectedChapters.add(chapter)

    def selectScene(self, scene: Scene):
        self.clearSelection()
        self._scenes[scene].select()
        if scene not in self._selectedScenes:
            self._selectedScenes.add(scene)

    def clearSelection(self):
        for scene in self._selectedScenes:
            self._scenes[scene].deselect()
        for chapter in self._selectedChapters:
            self._chapters[chapter].deselect()
        self._selectedScenes.clear()
        self._selectedChapters.clear()

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, SceneDeletedEvent):
            if event.scene in self._selectedScenes:
                self._selectedScenes.remove(event.scene)
            if event.scene in self._scenes.keys():
                wdg = self._scenes.pop(event.scene)
                if wdg.parent():
                    wdg.parent().layout().removeWidget(wdg)
                gc(wdg)
            self._refreshSceneTitles()
        elif isinstance(event, SceneChangedEvent):
            wdg = self._scenes.get(event.scene)
            if wdg is not None:
                wdg.refresh()
        elif isinstance(event,
                        (SceneAddedEvent, SceneOrderChangedEvent, ChapterChangedEvent, ScenesOrganizationResetEvent)):
            self._tryRefresh()
        elif isinstance(event, NovelScenesOrganizationToggleEvent):
            self._refreshSceneTitles()


    def _tryRefresh(self):
        if self.isVisible():
            self.refresh()
        else:
            self._refreshNeeded = True

    def _addScene(self, chapterWdg: ChapterNode):
        scene = self._novel.new_scene()
        scene.chapter = chapterWdg.chapter()
        self._novel.scenes.append(scene)

        self.repo.insert_scene(self._novel, scene)
        sceneWdg = self.__initSceneWidget(scene)
        chapterWdg.addChild(sceneWdg)

        emit_event(self._novel, SceneAddedEvent(self, scene), delay=10)
        self._reorderScenes()
        self.sceneAdded.emit(scene)

    def _insertChapter(self, chapterWdg: ChapterNode):
        i = self._centralWidget.layout().indexOf(chapterWdg) + 1
        chapter = Chapter('')
        self._novel.chapters.insert(i, chapter)
        wdg = self.__initChapterWidget(chapter)
        self._centralWidget.layout().insertWidget(i, wdg)

        self._novel.update_chapter_titles()
        self.repo.update_novel(self._novel)
        self._refreshChapterTitles()

    def _sceneSelectionChanged(self, sceneWdg: SceneNode, selected: bool):
        if selected:
            self.clearSelection()
            self._selectedScenes.add(sceneWdg.scene())
            self.sceneSelected.emit(sceneWdg.scene())
        elif sceneWdg.scene() in self._selectedScenes:
            self._selectedScenes.remove(sceneWdg.scene())

    def _chapterSelectionChanged(self, chapterWdg: ChapterNode, selected: bool):
        if selected:
            self.clearSelection()
            self._selectedChapters.add(chapterWdg.chapter())
            self.chapterSelected.emit(chapterWdg.chapter())
        elif chapterWdg.chapter() in self._selectedChapters:
            self._selectedChapters.remove(chapterWdg.chapter())

    def _deleteChapter(self, chapterWdg: ChapterNode):
        title = f'Are you sure you want to the delete the chapter "{chapterWdg.chapter().display_name()}"?'
        msg = "<html><ul><li>This action cannot be undone.</li><li>The scenes inside this chapter <b>WON'T</b> be deleted.</li>"
        if not confirmed(msg, title):
            return
        chapter = chapterWdg.chapter()
        if chapter in self._selectedChapters:
            self._selectedChapters.remove(chapter)
        self._chapters.pop(chapter)

        i = self._centralWidget.layout().indexOf(chapterWdg)
        for wdg in chapterWdg.sceneWidgets():
            chapterWdg.containerWidget().layout().removeWidget(wdg)
            wdg.setParent(self._centralWidget)
            self._centralWidget.layout().insertWidget(i, wdg)
            i += 1

            wdg.scene().chapter = None
            self.repo.update_scene(wdg.scene())

        chapterWdg.setHidden(True)
        gc(chapterWdg)

        self._novel.chapters.remove(chapter)
        self._novel.update_chapter_titles()
        self.repo.update_novel(self._novel)

        self._refreshChapterTitles()

        self._emitChapterChange()

    def _convertChapter(self, chapterWdg: ChapterNode, chapterType: Optional[ChapterType] = None):
        chapterWdg.chapter().type = chapterType
        self._novel.update_chapter_titles()

        self.repo.update_novel(self._novel)
        self._refreshChapterTitles()
        self._emitChapterChange()

    def _emitChapterChange(self):
        emit_event(self._novel, ChapterChangedEvent(self), delay=10)

    def _deleteScene(self, sceneWdg: SceneNode):
        scene = sceneWdg.scene()
        if delete_scene(self._novel, scene):
            if scene in self._selectedScenes:
                self._selectedScenes.remove(scene)
            self._scenes.pop(scene)

            sceneWdg.setHidden(True)
            gc(sceneWdg)

            self._refreshSceneTitles()
            emit_event(self._novel, SceneDeletedEvent(self, scene), delay=10)

    def _dragStarted(self, wdg: QWidget):
        wdg.setHidden(True)
        if isinstance(wdg, SceneNode):
            self._dummyWdg = SceneNode(wdg.scene(), wdg.novel(), settings=self._settings)
        elif isinstance(wdg, ChapterNode):
            self._dummyWdg = ChapterNode(wdg.chapter(), wdg.novel(), settings=self._settings)
            for v in self._scenes.values():
                v.setDisabled(True)
        else:
            return

        translucent(self._dummyWdg)
        self._dummyWdg.setHidden(True)
        self._dummyWdg.setParent(self._centralWidget)
        self._dummyWdg.setAcceptDrops(True)
        self._dummyWdg.installEventFilter(
            DropEventFilter(self._dummyWdg, [self.SCENE_MIME_TYPE, self.CHAPTER_MIME_TYPE], droppedSlot=self._drop))

    def _dragStopped(self, wdg: QWidget):
        if self._dummyWdg:
            gc(self._dummyWdg)
            self._dummyWdg = None

        if self._toBeRemoved:
            gc(self._toBeRemoved)
            self._toBeRemoved = None

            self._reorderScenes()
        else:
            wdg.setVisible(True)

        for v in self._scenes.values():
            v.setEnabled(True)

    def _dragEnteredForEnd(self, _: QMimeData):
        self._spacer.layout().addWidget(self._dummyWdg, alignment=Qt.AlignmentFlag.AlignTop)
        self._dummyWdg.setVisible(True)

    def _dragLeftFromEnd(self):
        self._dummyWdg.setHidden(True)
        self._spacer.layout().removeWidget(self._dummyWdg)
        self._dummyWdg.setParent(self._centralWidget)

    def _dragMovedOnChapter(self, chapterWdg: ChapterNode, edge: Qt.Edge, _: QPointF):
        if isinstance(self._dummyWdg, ChapterNode):
            i = self._centralWidget.layout().indexOf(chapterWdg)
            if edge == Qt.Edge.TopEdge:
                self._centralWidget.layout().insertWidget(i, self._dummyWdg)
            else:
                return
        else:
            chapterWdg.insertChild(0, self._dummyWdg)
        self._dummyWdg.setVisible(True)

    def _drop(self, mimeData: QMimeData):
        self.clearSelection()

        ref = mimeData.reference()
        if self._dummyWdg.isHidden():
            return
        if isinstance(ref, Scene):
            sceneWdg = self._scenes[ref]
            self._toBeRemoved = sceneWdg
            new_widget = self.__initSceneWidget(ref)
            if self._dummyWdg.parent() is self._centralWidget:
                ref.chapter = None
                new_widget.setParent(self._centralWidget)
                i = self._centralWidget.layout().indexOf(self._dummyWdg)
                self._centralWidget.layout().insertWidget(i, new_widget)
            elif self._dummyWdg.parent() is self._spacer:
                ref.chapter = None
                new_widget.setParent(self._centralWidget)
                self._centralWidget.layout().insertWidget(self._centralWidget.layout().count() - 1, new_widget)
            elif isinstance(self._dummyWdg.parent().parent(), ChapterNode):
                chapter_wdg: ChapterNode = self._dummyWdg.parent().parent()
                ref.chapter = chapter_wdg.chapter()
                new_widget.setParent(chapter_wdg)
                i = chapter_wdg.containerWidget().layout().indexOf(self._dummyWdg)
                chapter_wdg.insertChild(i, new_widget)
            self.repo.update_scene(ref)
        elif isinstance(ref, Chapter):
            chapter_wdg = self._chapters[ref]
            self._toBeRemoved = chapter_wdg
            new_widget = self.__initChapterWidget(ref)

            for wdg in chapter_wdg.sceneWidgets():
                new_widget.addChild(self.__initSceneWidget(wdg.scene()))

            new_widget.setParent(self._centralWidget)
            i = self._centralWidget.layout().indexOf(self._dummyWdg)
            self._centralWidget.layout().insertWidget(i, new_widget)
            # novel is saved later caught in dragStopped -> reorderScenes

        self._dummyWdg.setHidden(True)

    def _refreshChapterTitles(self):
        for wdg in self._chapters.values():
            wdg.refresh()

    def _refreshSceneTitles(self):
        for wdg in self._scenes.values():
            wdg.refreshTitle()

    def _reorderScenes(self):
        chapters = []
        scenes = []

        for i in range(self._centralWidget.layout().count()):
            item = self._centralWidget.layout().itemAt(i)
            if item is None:
                continue
            wdg = item.widget()
            if isinstance(wdg, ChapterNode):
                chapters.append(wdg.chapter())
                for scene_wdg in wdg.sceneWidgets():
                    scenes.append(scene_wdg.scene())
            elif isinstance(wdg, SceneNode):
                scenes.append(wdg.scene())

        self._novel.chapters[:] = chapters
        self._novel.scenes[:] = scenes

        self._novel.update_chapter_titles()
        self._refreshChapterTitles()
        self._refreshSceneTitles()

        self.repo.update_novel(self._novel)
        emit_event(self._novel, SceneOrderChangedEvent(self), delay=10)

    def _dragMovedOnScene(self, sceneWdg: SceneNode, edge: Qt.Edge, _: QPointF):
        i = sceneWdg.parent().layout().indexOf(sceneWdg)
        if edge == Qt.Edge.TopEdge:
            sceneWdg.parent().layout().insertWidget(i, self._dummyWdg)
        else:
            sceneWdg.parent().layout().insertWidget(i + 1, self._dummyWdg)
        self._dummyWdg.setVisible(True)

    # noinspection PyTypeChecker
    def __initChapterWidget(self, chapter: Chapter):
        chapterWdg = ChapterNode(chapter, self._novel, readOnly=self._readOnly, settings=self._settings)
        chapterWdg.selectionChanged.connect(partial(self._chapterSelectionChanged, chapterWdg))
        if not self._readOnly:
            chapterWdg.deleted.connect(partial(self._deleteChapter, chapterWdg))
            chapterWdg.converted.connect(partial(self._convertChapter, chapterWdg))
            chapterWdg.resetType.connect(partial(self._convertChapter, chapterWdg))
            chapterWdg.addScene.connect(partial(self._addScene, chapterWdg))
            chapterWdg.addChapter.connect(partial(self._insertChapter, chapterWdg))
            chapterWdg.installEventFilter(
                DragEventFilter(chapterWdg, self.CHAPTER_MIME_TYPE, dataFunc=lambda wdg: wdg.chapter(),
                                grabbed=chapterWdg.titleWidget(),
                                startedSlot=partial(self._dragStarted, chapterWdg),
                                finishedSlot=partial(self._dragStopped, chapterWdg)))
            chapterWdg.titleWidget().setAcceptDrops(True)
            chapterWdg.titleWidget().installEventFilter(
                DropEventFilter(chapterWdg, [self.SCENE_MIME_TYPE, self.CHAPTER_MIME_TYPE],
                                motionDetection=Qt.Orientation.Vertical,
                                motionSlot=partial(self._dragMovedOnChapter, chapterWdg),
                                droppedSlot=self._drop
                                )
            )
        self._chapters[chapter] = chapterWdg

        return chapterWdg

    # noinspection PyTypeChecker
    def __initSceneWidget(self, scene: Scene) -> SceneNode:
        sceneWdg = SceneNode(scene, self._novel, readOnly=self._readOnly, settings=self._settings)
        self._scenes[scene] = sceneWdg
        sceneWdg.selectionChanged.connect(partial(self._sceneSelectionChanged, sceneWdg))
        sceneWdg.doubleClicked.connect(partial(self.sceneDoubleClicked.emit, scene))
        if not self._readOnly:
            sceneWdg.deleted.connect(partial(self._deleteScene, sceneWdg))
            sceneWdg.installEventFilter(
                DragEventFilter(sceneWdg, self.SCENE_MIME_TYPE, dataFunc=lambda wdg: wdg.scene(),
                                startedSlot=partial(self._dragStarted, sceneWdg),
                                finishedSlot=partial(self._dragStopped, sceneWdg)))
            sceneWdg.setAcceptDrops(True)
            sceneWdg.installEventFilter(
                DropEventFilter(sceneWdg, [self.SCENE_MIME_TYPE],
                                motionDetection=Qt.Orientation.Vertical,
                                motionSlot=partial(self._dragMovedOnScene, sceneWdg),
                                droppedSlot=self._drop
                                )

            )
        return sceneWdg
