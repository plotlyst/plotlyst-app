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
from enum import Enum
from functools import partial
from typing import Optional, Dict

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QSplitter
from overrides import overrides
from qthandy import vspacer, clear_layout, vbox, margins, hbox, incr_font, line

from plotlyst.view.common import frame, scroll_area, label, rows
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.kb.articles import PlotlystArticleWidget, FAQArticleWidget
from plotlyst.view.widget.patron import PatronsWidget
from plotlyst.view.widget.tree import ItemBasedTreeView, TreeSettings, ItemBasedNode


class ArticleType(Enum):
    Community = 'community'
    Plotlyst = 'plotlyst'
    FAQ = 'faq'
    Premise = 'premise'
    Genres = 'genres'
    Story_grid_genre_clover = 'genre_clover'

    def title(self) -> str:
        if self == ArticleType.Story_grid_genre_clover:
            return '©Story Grid Genre Clover'
        else:
            return self.value.capitalize().replace('_', ' ')


article_icons: Dict[ArticleType, str] = {
    ArticleType.Community: 'msc.organization',
    ArticleType.FAQ: 'ei.question',
    ArticleType.Premise: 'mdi.flower',
    ArticleType.Story_grid_genre_clover: 'mdi.clover',
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


class CommunityNode(ArticleNode):
    def __init__(self, articleType: ArticleType, parent=None, readOnly: bool = False,
                 settings: Optional[TreeSettings] = None):
        super().__init__(articleType, parent=parent, readOnly=readOnly, settings=settings)
        incr_font(self._lblTitle, 2)


class KnowledgeBaseTreeView(ItemBasedTreeView):
    articleSelected = pyqtSignal(ArticleType)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._readOnly = True
        self._settings = TreeSettings(font_incr=2)
        margins(self._centralWidget, top=20, left=15)

    def refresh(self):
        self.clearSelection()
        self._nodes.clear()
        clear_layout(self._centralWidget)

        wdgTitle = rows(0)
        wdgTitle.layout().addWidget(label('Knowledge Base', h3=True))
        wdgTitle.layout().addWidget(line())
        margins(wdgTitle, bottom=40)
        self._centralWidget.layout().addWidget(wdgTitle)

        commnunity_node = self._addType(ArticleType.Community)
        commnunity_node.containerWidget().setFixedHeight(20)
        commnunity_node.containerWidget().setVisible(True)
        plotlyst_node = self._addType(ArticleType.Plotlyst)
        self._addType(ArticleType.FAQ, plotlyst_node)

        self._centralWidget.layout().addWidget(vspacer())

        commnunity_node.select()
        self._selectionChanged(commnunity_node, True)
        self.articleSelected.emit(ArticleType.Community)

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
        self.wdgArticleArea = scroll_area(frameless=True)
        self.wdgArticleContainer = QWidget()
        self.wdgArticleArea.setWidget(self.wdgArticleContainer)
        self.wdgArticleContainer.setProperty('muted-bg', True)
        self.wdgDisplay = frame()
        self.wdgDisplay.setProperty('relaxed-white-bg', True)
        self.wdgDisplay.setProperty('large-rounded', True)
        self.wdgDisplay.setMaximumWidth(900)
        vbox(self.wdgDisplay)
        hbox(self.wdgArticleContainer, 25).addWidget(self.wdgDisplay)
        margins(self.wdgArticleContainer, top=40, bottom=40)

        self.splitter = QSplitter(self)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.browser)
        self.splitter.addWidget(self.wdgArticleArea)
        self.splitter.setSizes([150, 500])

        vbox(self).addWidget(self.splitter)

        self.browser.articleSelected.connect(self._articleSelected)
        self.browser.refresh()

    def _articleSelected(self, article: ArticleType):
        clear_layout(self.wdgDisplay)

        if article == ArticleType.Community:
            wdg = PatronsWidget()
        elif article == ArticleType.Plotlyst:
            wdg = PlotlystArticleWidget()
        elif article == ArticleType.FAQ:
            wdg = FAQArticleWidget()
        else:
            return

        self.wdgDisplay.layout().addWidget(wdg)
