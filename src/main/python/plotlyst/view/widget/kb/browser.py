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
from enum import Enum
from functools import partial
from typing import Optional, Dict

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QSplitter
from overrides import overrides
from qthandy import vspacer, clear_layout, vbox

from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.tree import ItemBasedTreeView, TreeSettings, ItemBasedNode


class ArticleType(Enum):
    Premise = 'premise'
    Genres = 'genres'
    Story_grid_genre_clover = 'genre_clover'

    def title(self) -> str:
        if self == ArticleType.Story_grid_genre_clover:
            return '©Story Grid Genre Clover'
        else:
            return self.value.capitalize()


article_icons: Dict[ArticleType, str] = {
    ArticleType.Premise: 'mdi.flower',
    ArticleType.Story_grid_genre_clover: 'mdi.clover'
}


class ArticleNode(ItemBasedNode):
    added = pyqtSignal()

    def __init__(self, articleType: ArticleType, parent=None, readOnly: bool = False,
                 settings: Optional[TreeSettings] = None):
        super().__init__(articleType.title(),
                         icon=IconRegistry.from_name(article_icons.get(articleType, 'msc.debug-stackframe-dot')),
                         parent=parent, settings=settings)
        self._articleType = articleType
        self.setPlusButtonEnabled(not readOnly)
        self.setMenuEnabled(not readOnly)
        self.setTranslucentIconEnabled(True)
        self._actionChangeIcon.setVisible(True)
        self._btnAdd.clicked.connect(self.added)
        self.refresh()

    @overrides
    def item(self) -> ArticleType:
        return self._articleType


class KnowledgeBaseTreeView(ItemBasedTreeView):
    articleSelected = pyqtSignal(ArticleType)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._readOnly = True
        self._settings = TreeSettings(font_incr=2)

        self.refresh()

    def refresh(self):
        self.clearSelection()
        self._nodes.clear()
        clear_layout(self._centralWidget)

        self._addType(ArticleType.Premise)
        genre = self._addType(ArticleType.Genres)
        self._addType(ArticleType.Story_grid_genre_clover, genre)

        self._centralWidget.layout().addWidget(vspacer())

    def _addType(self, articleType: ArticleType, parent: Optional[ArticleNode] = None) -> ArticleNode:
        node = self._initNode(articleType)
        if parent:
            parent.addChild(node)
        else:
            self._centralWidget.layout().addWidget(node)

        return node

    @overrides
    def _emitSelectionChanged(self, article: ArticleType):
        self.articleSelected.emit(article)

    @overrides
    def _initNode(self, articleType: ArticleType) -> ArticleNode:
        node = ArticleNode(articleType, readOnly=self._readOnly, settings=self._settings)
        self._nodes[articleType] = node
        node.selectionChanged.connect(partial(self._selectionChanged, node))

        return node


class KnowledgeBaseWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.browser = KnowledgeBaseTreeView()
        self.wdgDisplay = QWidget()

        self.splitter = QSplitter(self)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.browser)
        self.splitter.addWidget(self.wdgDisplay)
        self.splitter.setSizes([150, 500])

        vbox(self).addWidget(self.splitter)
