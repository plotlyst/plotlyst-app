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
from overrides import overrides
from qthandy import bold, retain_when_hidden
from qthandy.filter import InstantTooltipEventFilter

from plotlyst.common import PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import Novel
from plotlyst.env import app_env
from plotlyst.view._view import AbstractNovelView
from plotlyst.view.common import scroll_to_bottom, ButtonPressResizeEventFilter
from plotlyst.view.generated.board_view_ui import Ui_BoardView
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.display import PremiumOverlayWidget
from plotlyst.view.widget.task import BoardWidget


class BoardView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel)
        self.ui = Ui_BoardView()
        self.ui.setupUi(self.widget)

        self.ui.btnNew.setIcon(IconRegistry.plus_icon('white'))
        self.ui.btnNew.installEventFilter(ButtonPressResizeEventFilter(self.ui.btnNew))
        self.ui.btnBoard.setIcon(IconRegistry.from_name('fa5s.columns', color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnChart.setIcon(IconRegistry.from_name('mdi.chart-areaspline', color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnSettings.setIcon(IconRegistry.cog_icon())
        self.ui.btnChart.installEventFilter(InstantTooltipEventFilter(self.ui.btnChart))
        self.ui.btnSettings.installEventFilter(InstantTooltipEventFilter(self.ui.btnSettings))

        retain_when_hidden(self.ui.wdgTop)
        self.ui.wdgTop.setHidden(True)

        bold(self.ui.lblTitle)
        self.ui.iconBoard.setIcon(IconRegistry.board_icon())

        self._board = BoardWidget(novel)
        self.ui.scrollAreaWidgetContents.layout().addWidget(self._board)
        self._board.taskAdded.connect(lambda: scroll_to_bottom(self.ui.scrollArea))

        self.ui.btnNew.clicked.connect(self._board.addNewTask)

        self.ui.btnBoard.setChecked(True)

        if not app_env.profile().get('tasks', False):
            PremiumOverlayWidget(self._board, 'Task management',
                                 icon='mdi6.clipboard-check-outline',
                                 alt_link='https://plotlyst.com/docs/task-management/')

    @overrides
    def refresh(self):
        pass
