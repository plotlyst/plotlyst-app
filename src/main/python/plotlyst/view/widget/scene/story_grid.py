"""
Plotlyst
Copyright (C) 2021-2025  Zsolt Kovari

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
from typing import Dict, Optional

from PyQt6 import QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal, QEvent
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QTextEdit, QButtonGroup
from overrides import overrides
from qthandy import hbox, spacer, vbox, busy
from qthandy import margins, vspacer, line, incr_font, clear_layout, gc
from qthandy.filter import OpacityEventFilter

from plotlyst.common import PLOTLYST_MAIN_COLOR, RELAXED_WHITE_COLOR
from plotlyst.core.domain import Scene, Novel, Plot, \
    ScenePlotReference, NovelSetting, LayoutType
from plotlyst.event.core import emit_event, EventListener, Event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import SceneChangedEvent, StorylineCreatedEvent, SceneAddedEvent, SceneDeletedEvent, \
    StorylineRemovedEvent, StorylineChangedEvent, SceneEditRequested, SceneSelectedEvent, NovelSyncEvent
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import tool_btn, fade_out_and_gc, insert_before_the_end, \
    label, push_btn, shadow, fade_in
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.cards import SceneCard, CardsView, Card, CardFilter
from plotlyst.view.widget.input import RemovalButton
from plotlyst.view.widget.timeline import TimelineGridWidget, TimelineGridLine, TimelineGridPlaceholder

GRID_ITEM_WIDTH: int = 190
GRID_ITEM_HEIGHT: int = 120


class ScenesGridPlotHeader(QWidget):
    def __init__(self, plot: Plot, parent=None):
        super().__init__(parent)
        self.plot = plot
        self.lblPlot = push_btn(text=plot.text, transparent_=True)
        if plot.icon:
            self.lblPlot.setIcon(IconRegistry.from_name(plot.icon, plot.icon_color))
        incr_font(self.lblPlot, 1)
        vbox(self, 0, 0).addWidget(self.lblPlot)

    def refresh(self):
        self.lblPlot.setText(self.plot.text)
        self.lblPlot.setIcon(IconRegistry.from_name(self.plot.icon, self.plot.icon_color))


class SceneStorylineAssociation(QWidget):
    textChanged = pyqtSignal()
    removed = pyqtSignal()

    def __init__(self, plot: Plot, ref: ScenePlotReference, parent=None):
        super().__init__(parent)
        self.plot = plot
        self.ref = ref
        self.textedit = QTextEdit()
        self.textedit.setTabChangesFocus(True)
        self.textedit.setPlaceholderText('How does the story move forward')
        self.textedit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textedit.setStyleSheet(f'''
                 QTextEdit {{
                    border-radius: 8px;
                    padding: 4px;
                    background-color: {RELAXED_WHITE_COLOR};
                    border: 1px solid lightgrey;
                }}
                ''')
        # QTextEdit: focus
        # {{
        #     border: 1px inset {to_rgba_str(QColor(self.plot.icon_color), 125)};
        # }}
        qcolor = QColor(self.plot.icon_color)
        qcolor.setAlpha(75)
        shadow(self.textedit, color=qcolor)
        self.textedit.setText(self.ref.data.comment)
        # self.textedit.setAlignment(Qt.AlignmentFlag.AlignCenter)

        vbox(self, 2, 0).addWidget(self.textedit)

        self._btnRemove = RemovalButton(self)
        self._btnRemove.setHidden(True)
        self._btnRemove.clicked.connect(self.removed)

        self.textedit.textChanged.connect(self._textChanged)

    @overrides
    def enterEvent(self, event: QtGui.QEnterEvent) -> None:
        fade_in(self._btnRemove)
        self._btnRemove.raise_()

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        self._btnRemove.setHidden(True)

    @overrides
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._btnRemove.setGeometry(self.width() - 20, 5, 20, 20)

    def _textChanged(self):
        self.ref.data.comment = self.textedit.toPlainText()
        self.textChanged.emit()


class SceneGridCard(SceneCard):
    def __init__(self, scene: Scene, novel: Novel, parent=None):
        super().__init__(scene, novel, parent)
        self.wdgCharacters.setHidden(True)
        self.setSetting(NovelSetting.SCENE_CARD_PLOT_PROGRESS, True)
        self.setSetting(NovelSetting.SCENE_CARD_PURPOSE, False)
        self.setSetting(NovelSetting.SCENE_CARD_STAGE, False)
        self.layout().setSpacing(0)
        margins(self, 0, 0, 0, 0)

        self.textTitle.setFontPointSize(self.textTitle.font().pointSize() - 1)

        self.setFixedWidth(170)
        self.setDragEnabled(not self.novel.is_readonly() and not self.novel.tutorial)

    @overrides
    def copy(self) -> 'Card':
        return SceneGridCard(self.scene, self.novel)

    def setSelected(self, selected: bool):
        self._setStyleSheet(selected=selected)


class SceneGridCardsView(CardsView):
    def __init__(self, width: int, height: int, parent=None, layoutType: LayoutType = LayoutType.VERTICAL,
                 margin: int = 0, spacing: int = 15):
        super().__init__(parent, layoutType, margin, spacing)
        self._width = width
        self._height = height

    @overrides
    def remove(self, obj: Scene):
        if self._selected:
            self._selected.clearSelection()
        super().remove(obj)

    @overrides
    def selectCard(self, ref: Scene):
        if self._selected and self._selected.data() is not ref:
            self._selected.clearSelection()
        card = self._cards.get(ref, None)
        if card is not None:
            card.setSelected(True)
            self._selected = card

    @overrides
    def _cardSelected(self, card: Card):
        if self._selected and self._selected is not card:
            self._selected.clearSelection()
        super()._cardSelected(card)

    @overrides
    def _resizeCard(self, card: Card):
        card.setFixedSize(self._width, self._height)

    @overrides
    def _dragStarted(self, card: Card):
        super()._dragStarted(card)
        self._dragPlaceholder.setFixedSize(self._width, self._height)


class ScenesGridToolbar(QWidget):
    orientationChanged = pyqtSignal(Qt.Orientation)

    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self, 0, 0)

        self.lblScenes = label('Orientation:', description=True)
        self.btnRows = tool_btn(IconRegistry.from_name('ph.rows-fill', color_on=PLOTLYST_MAIN_COLOR), transparent_=True,
                                checkable=True)
        self.btnRows.installEventFilter(OpacityEventFilter(self.btnRows))
        self.btnColumns = tool_btn(IconRegistry.from_name('ph.columns-fill', color_on=PLOTLYST_MAIN_COLOR),
                                   transparent_=True, checkable=True)
        self.btnColumns.installEventFilter(OpacityEventFilter(self.btnColumns))
        self.btnGroup = QButtonGroup()
        self.btnGroup.addButton(self.btnRows)
        self.btnGroup.addButton(self.btnColumns)
        self.btnGroup.buttonClicked.connect(self._orientationClicked)
        self.btnColumns.setChecked(True)

        # self.layout().addWidget(spacer())
        self.layout().addWidget(self.lblScenes, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.layout().addWidget(self.btnRows)
        self.layout().addWidget(self.btnColumns)

    def _orientationClicked(self):
        if self.btnRows.isChecked():
            self.orientationChanged.emit(Qt.Orientation.Vertical)
        else:
            self.orientationChanged.emit(Qt.Orientation.Horizontal)


class ScenesGridWidget(TimelineGridWidget, EventListener):
    sceneCardSelected = pyqtSignal(Card)
    sceneOrderChanged = pyqtSignal(list, Card)

    def __init__(self, novel: Novel, parent=None):
        self._scenesInColumns = False
        super().__init__(parent, vertical=self._scenesInColumns)
        self._novel = novel
        self._plots: Dict[Plot, TimelineGridLine] = {}
        self._scenes: Dict[Scene, SceneGridCard] = {}

        self.setColumnWidth(170)
        self.setRowHeight(120)
        self.scrollRows.setFixedWidth(self._verticalHeaderWidth)

        self.wdgEditor.setProperty('large-rounded', True)
        self.wdgEditor.setProperty('muted-bg', True)

        self.cardsView = SceneGridCardsView(self._columnWidth, self._rowHeight, spacing=self._spacing)
        margins(self.cardsView, top=self._margins, left=self._margins, right=self._margins, bottom=self._margins)
        self.cardsView.cardSelected.connect(self.sceneCardSelected)
        self.cardsView.cardDoubleClicked.connect(self._cardDoubleClicked)
        self.cardsView.orderChanged.connect(self.sceneOrderChanged)

        for i, scene in enumerate(self._novel.scenes):
            sceneCard = SceneGridCard(scene, self._novel)
            self.cardsView.addCard(sceneCard, alignment=Qt.AlignmentFlag.AlignCenter)

        self.repo = RepositoryPersistenceManager.instance()
        self.refresh()

        dispatcher = event_dispatchers.instance(self._novel)
        dispatcher.register(self, SceneChangedEvent, SceneAddedEvent, SceneDeletedEvent,
                            SceneSelectedEvent, StorylineChangedEvent, StorylineCreatedEvent,
                            StorylineRemovedEvent)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, SceneChangedEvent):
            card = self.cardsView.card(event.scene)
            if card:
                card.refresh()
                self._updateSceneReferences(event.scene)
        elif isinstance(event, SceneAddedEvent):
            index = self._novel.scenes.index(event.scene)
            sceneCard = SceneGridCard(event.scene, self._novel)
            if index == len(self._novel.scenes) - 1:  # last one
                self.cardsView.addCard(sceneCard, alignment=Qt.AlignmentFlag.AlignCenter)
            else:
                self.cardsView.insertAt(index, sceneCard)
            sceneCard.setFixedSize(self._columnWidth, self._rowHeight)

            self._addSceneReferences(event.scene)
            for card in self.cardsView.cards():
                card.quickRefresh()
        elif isinstance(event, SceneDeletedEvent):
            card = self.cardsView.card(event.scene)
            index = self.cardsView.layout().indexOf(card)
            self._removeSceneReferences(index)
            self.cardsView.remove(event.scene)
        # elif isinstance(event, SceneOrderChangedEvent):
        #     for line in self._plots.values():
        #         clear_layout(line)
        #         spacer_wdg = spacer() if self._scenesInColumns else vspacer()
        #         line.layout().addWidget(spacer_wdg)
        #         for scene in self._novel.scenes:
        #             self._addPlaceholder(line, scene)
        #     self.initRefs()
        #     self.cardsView.reorderCards(self._novel.scenes)
        elif isinstance(event, SceneSelectedEvent):
            self.cardsView.selectCard(event.scene)
        elif isinstance(event, StorylineChangedEvent):
            self._handleStorylineChanged(event.storyline)
        elif isinstance(event, StorylineCreatedEvent):
            self._handleStorylineCreated(event.storyline)
        elif isinstance(event, StorylineRemovedEvent):
            self._handleStorylineRemoved(event.storyline)

    def sceneOrderChangedEvent(self):
        for line in self._plots.values():
            clear_layout(line)
            spacer_wdg = spacer() if self._scenesInColumns else vspacer()
            line.layout().addWidget(spacer_wdg)
            for scene in self._novel.scenes:
                self._addPlaceholder(line, scene)
        self.initRefs()
        self._applyFilterOnLines()

        self.cardsView.clearSelection()
        self.cardsView.reorderCards(self._novel.scenes)

    @busy
    def setOrientation(self, orientation: Qt.Orientation):
        clear_layout(self.wdgRows, auto_delete=self._scenesInColumns)  # delete plots
        clear_layout(self.wdgColumns, auto_delete=not self._scenesInColumns)  # delete plots
        clear_layout(self.wdgEditor)
        self._plots.clear()

        self._scenesInColumns = True if orientation == Qt.Orientation.Vertical else False
        self.wdgRows.layout().addWidget(vspacer())
        self.wdgColumns.layout().addWidget(spacer())

        self.cardsView.swapLayout(LayoutType.HORIZONTAL if self._scenesInColumns else LayoutType.VERTICAL,
                                  alignment=Qt.AlignmentFlag.AlignCenter)

        QWidget().setLayout(self.wdgEditor.layout())
        if self._scenesInColumns:
            vbox(self.wdgEditor, 0, self._spacing)
            margins(self.cardsView, self._margins, 0, 0, 0)
            self._headerHeight = 150
            self.wdgEditor.layout().addWidget(vspacer())
            margins(self.wdgColumns, 0)
        else:
            hbox(self.wdgEditor, 0, self._spacing)
            margins(self.cardsView, top=self._margins, left=self._margins, right=self._margins, bottom=self._margins)
            self._headerHeight = 40
            self.wdgEditor.layout().addWidget(spacer())
            margins(self.wdgColumns, left=self._margins)

        self.scrollColumns.setFixedHeight(self._headerHeight)
        margins(self.wdgRows, top=self._headerHeight, right=self._spacing)
        margins(self.wdgEditor, left=self._margins, top=self._margins)

        self._emptyPlaceholder.setGeometry(0, 0, self._verticalHeaderWidth, self._headerHeight)

        self.refresh()

    def refresh(self):
        for plot in self._novel.plots:
            self.addPlot(plot)

        if self._scenesInColumns:
            insert_before_the_end(self.wdgColumns, self.cardsView)
        else:
            insert_before_the_end(self.wdgRows, self.cardsView)

        self.initRefs()
        self._applyFilterOnLines()

    def sync(self, event: NovelSyncEvent):
        self.cardsView.clearSelection()

        for scene in event.new_scenes:
            sceneCard = SceneGridCard(scene, self._novel)
            self.cardsView.addCard(sceneCard, alignment=Qt.AlignmentFlag.AlignCenter)

        self.cardsView.reorderCards(self._novel.scenes)
        for card in self.cardsView.cards():
            card.quickRefresh()

        self.setOrientation(Qt.Orientation.Vertical if self._scenesInColumns else Qt.Orientation.Horizontal)

    def refreshBeatFor(self, scene: Scene):
        card = self.cardsView.card(scene)
        if card:
            card.refreshBeat()

    def initRefs(self):
        for i, scene in enumerate(self._novel.scenes):
            for plot_ref in scene.plot_values:
                self.addRef(i, scene, plot_ref)

    def addRef(self, i: int, scene: Scene, plot_ref: ScenePlotReference,
               removeOld: bool = True) -> SceneStorylineAssociation:
        wdg = self.__initRefWidget(scene, plot_ref)
        line = self._plots[plot_ref.plot]
        placeholder = line.layout().itemAt(i).widget()
        line.layout().insertWidget(i, wdg)
        if removeOld:
            line.layout().removeWidget(placeholder)
            gc(placeholder)

        return wdg

    def addPlot(self, plot: Plot):
        header = ScenesGridPlotHeader(plot)
        line = TimelineGridLine(plot, vertical=self._scenesInColumns)
        if self._scenesInColumns:
            header.setFixedSize(self._columnWidth, self._rowHeight)
            insert_before_the_end(self.wdgRows, header)
            line.setFixedHeight(self._rowHeight)
        else:
            header.setFixedSize(self._columnWidth, self._headerHeight)
            insert_before_the_end(self.wdgColumns, header, alignment=Qt.AlignmentFlag.AlignCenter)
            line.setFixedWidth(self._columnWidth)

        line.layout().setSpacing(self._spacing)
        spacer_wdg = spacer() if self._scenesInColumns else vspacer()
        line.layout().addWidget(spacer_wdg)

        self._plots[plot] = line
        for scene in self._novel.scenes:
            self._addPlaceholder(line, scene)

        insert_before_the_end(self.wdgEditor, line)

    def applyFilter(self, cardFilter: CardFilter):
        self.cardsView.applyFilter(cardFilter)
        self._applyFilterOnLines()

    def _applyFilterOnLines(self):
        for i, scene in enumerate(self._novel.scenes):
            card = self.cardsView.card(scene)
            for line in self._plots.values():
                wdg = line.layout().itemAt(i).widget()
                wdg.setHidden(card.isHidden())

    def save(self, scene: Scene):
        self.repo.update_scene(scene)

    @overrides
    def _placeholderClicked(self, line: TimelineGridLine, placeholder: TimelineGridPlaceholder):
        scene: Scene = placeholder.ref
        plot: Plot = line.ref

        ref = scene.link_plot(plot)
        wdg = self.addRef(self._novel.scenes.index(scene), scene, ref)
        fade_in(wdg)

        self._updateSceneType(scene)

        self.save(scene)
        emit_event(self._novel, SceneChangedEvent(self, scene))

    def _remove(self, widget: SceneStorylineAssociation, scene: Scene):
        def addPlaceholder():
            scene.unlink_plot(plot)
            placeholder = self._initPlaceholder(line, scene)
            line.layout().insertWidget(i, placeholder)

            self._updateSceneType(scene)

            self.save(scene)
            emit_event(self._novel, SceneChangedEvent(self, scene))

        plot = widget.plot
        line: TimelineGridLine = widget.parent()
        i = widget.parent().layout().indexOf(widget)

        fade_out_and_gc(line, widget, teardown=addPlaceholder)

    def _updateSceneType(self, scene: Scene):
        scene.update_purpose()

    def _addSceneReferences(self, scene: Scene):
        index = self._novel.scenes.index(scene)

        for plot_ref in scene.plot_values:
            self.addRef(index, scene, plot_ref, removeOld=False)

        scene_plots = scene.plots()
        for plot, line in self._plots.items():
            if plot not in scene_plots:
                self._insertPlaceholder(index, line, scene)

    def _updateSceneReferences(self, scene: Scene):
        index = self._novel.scenes.index(scene)

        for plot_ref in scene.plot_values:
            self.addRef(index, scene, plot_ref)

        scene_plots = scene.plots()
        for plot, line in self._plots.items():
            if plot not in scene_plots:
                self._replaceWithPlaceholder(index, line, scene)

    def _removeSceneReferences(self, index: int):
        for line in self._plots.values():
            self._removeWidget(line, index)

    def _handleStorylineRemoved(self, plot: Plot):
        line = self._plots.pop(plot)
        self.wdgEditor.layout().removeWidget(line)
        gc(line)

        header = self.__plotHeader(plot)
        fade_out_and_gc(header.parent(), header)

    def _handleStorylineChanged(self, plot: Plot):
        header = self.__plotHeader(plot)
        header.refresh()

    def _handleStorylineCreated(self, plot: Plot):
        self.addPlot(plot)

    def _cardDoubleClicked(self, card: SceneGridCard):
        emit_event(self._novel, SceneEditRequested(self, scene=card.scene))

    def __plotHeader(self, plot: Plot) -> Optional[ScenesGridPlotHeader]:
        wdg = self.wdgRows if self._scenesInColumns else self.wdgColumns

        for i in range(wdg.layout().count()):
            header = wdg.layout().itemAt(i).widget()
            if isinstance(header, ScenesGridPlotHeader):
                if header.plot.id == plot.id:
                    return header

    def __initRefWidget(self, scene: Scene, plot_ref: ScenePlotReference) -> SceneStorylineAssociation:
        wdg = SceneStorylineAssociation(plot_ref.plot, plot_ref)
        wdg.removed.connect(partial(self._remove, wdg, scene))
        wdg.textChanged.connect(partial(self.save, scene))
        wdg.setFixedSize(self._columnWidth, self._rowHeight)

        return wdg
